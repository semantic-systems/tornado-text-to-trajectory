#!/usr/bin/env python
"""Stage 23 — label the retrieved Media Cloud bodies, and compare with the headlines.

Stage 18 labelled Media Cloud from headline and URL alone. Stage 21 has since
retrieved the bodies of most ``EVENT`` stories, so they can now be labelled on
the same evidence as LexisNexis — with **stage 19's prompt, schema, evidence
window and temperature, unchanged** — and the two answers compared. That
comparison is the measurement of what headline-only labelling costs.

Typical run — forward the model's port first, then::

    ssh -N -L 8000:localhost:8000 you@your-server        # in another terminal
    python scripts/23_label_fulltext.py profile          # what will be sent; no LLM
    python scripts/23_label_fulltext.py run              # label + uncertainty + apply + compare
    python scripts/16_viewer.py --corpus mediacloud      # read the disagreements

Needs ``scripts/21_fetch_fulltext.py quality`` to have been run: by default only
bodies that pass every hard quality check are labelled, because a front page
served in place of an article would be labelled as though it were the article,
and every such case would surface as a spurious headline/full-text disagreement.

Subcommands
-----------
profile      population, quality pass rate, evidence cost; no LLM
label        label every distinct body at temperature 0
uncertainty  re-label a random subset k times at temperature 1.0
apply        propagate to every story, enforce the protect rule, write the table
compare      headline-only versus full-text labels; writes the report
run          label, uncertainty, apply and compare

Resumable and tag-isolated exactly like stage 19: answers are cached by (model,
prompt, temperature, sample), and ``--tag`` keeps an experiment's outputs apart.

**The comparison measures precision only.** The crawl covered headline-``EVENT``
stories, so this shows how many of those the full text overturns, not how many
real reports the headline labeller rejected.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tornado_dataset import config                              # noqa: E402
from tornado_dataset.dat.evaluate import wilson_interval        # noqa: E402
from tornado_dataset.llm import LLMClient, iter_progress        # noqa: E402
from tornado_dataset.text import fulltext, labelling            # noqa: E402
from tornado_dataset.text import fulltext_corpus as fc          # noqa: E402
from tornado_dataset.text import lexisnexis_filter as lf        # noqa: E402

HL, FT = fc.HL, fc.FT
MC_CONSISTENCY = config.INTERIM_DIR / "mediacloud_consistency.csv"
ATLAS_EDGES = config.INTERIM_DIR / "corpus_atlas_edges.csv"

LABELS = CONSISTENCY = LLM_CACHE = STORY_LABELS = REPORT = None


def set_paths(tag: str | None) -> None:
    global LABELS, CONSISTENCY, LLM_CACHE, STORY_LABELS, REPORT
    suffix = f"_{tag}" if tag else ""
    LABELS = config.INTERIM_DIR / f"mediacloud_fulltext_labels{suffix}.csv"
    CONSISTENCY = config.INTERIM_DIR / f"mediacloud_fulltext_consistency{suffix}.csv"
    # Shared across tags, as in stage 19.
    LLM_CACHE = config.INTERIM_DIR / "mediacloud_fulltext_llm_cache.jsonl"
    # Per story, both labels side by side, no text — what the viewer reads.
    STORY_LABELS = config.PROCESSED_DIR / f"mediacloud_fulltext_story_labels{suffix}.csv"
    REPORT = config.OUTPUT_DIR / f"mediacloud_fulltext_vs_headline_report{suffix}.md"


# ── shared plumbing ─────────────────────────────────────────────────────────
def load_corpus(args) -> pd.DataFrame:
    """Retrieved bodies with quality flags and headline labels, ready to label."""
    config.require_data(config.PROCESSED_DIR, fc.STORE)
    quality = fc.load_quality()
    if quality is None:
        sys.exit(f"missing {fc.QUALITY_CSV} — run "
                 "`python scripts/21_fetch_fulltext.py quality` first.")
    print("reading the full-text store…")
    df = fc.load_bodies(fulltext.load_store(fc.STORE), fc.load_population(), quality)
    unknown = int((~df.quality_known).sum())
    if unknown:
        print(f"  note: {unknown:,} bodies were retrieved after the last `quality` run "
              "and have no quality verdict; they are excluded. Re-run `quality` to "
              "include them.")
    if not args.include_flagged:
        df = df[df.quality_ok].copy()
    if args.limit:
        df = df.head(args.limit).copy()
    # Representatives must be chosen within the slice actually labelled: the
    # quality checks are partly per URL, so a body can pass under one headline
    # and fail under another.
    df["is_representative"] = labelling.pick_representatives(
        df, "body_key", df.body.str.len())
    df["dup_count"] = df.groupby("body_key").body_key.transform("size")
    return df


def make_client(args) -> LLMClient:
    client = LLMClient(api_base=args.api_base, model=args.model, cache_path=LLM_CACHE,
                       concurrency=args.concurrency, thinking=args.thinking)
    print(f"  LLM: {client.model} @ {client.api_base} "
          f"(concurrency {client.concurrency}, thinking={client.thinking})")
    return client


def run_llm(client: LLMClient, rows: pd.DataFrame, desc: str, mode: str,
            temperature: float | None = None, variant: str = "") -> pd.DataFrame:
    """Identical to stage 19's call: same system prompt, schema and token budget."""
    prompts, _ = lf.build_prompts(rows, mode=mode)
    before = dict(client.stats)
    update, close = iter_progress(len(prompts), desc)
    answers = client.complete_many(prompts, system=lf.LLM_SYSTEM,
                                   max_tokens=900 if client.thinking else 220,
                                   schema=lf.LLM_SCHEMA, progress=update,
                                   temperature=temperature, variant=variant)
    close()
    parsed = lf.parse_llm_answers(answers, lf.FLAGS)
    parsed.index = rows.index
    bad = int((~parsed["parsed"]).sum())
    delta = {k: client.stats[k] - before.get(k, 0) for k in client.stats}
    print(f"  cached {delta['cached']:,} | called {delta['called']:,} "
          f"| failed {delta['failed']:,} | unparseable {bad:,}")
    if bad:
        print(f"  note: {bad:,} rows had no usable answer, recorded UNCLEAR with "
              "parsed=False — they are not counted as judgements.")
    return parsed


def require(path: Path, what: str, flags=lf.FLAGS) -> pd.DataFrame:
    if not path.exists():
        sys.exit(f"missing {path} — run the `{what}` subcommand first.")
    return lf.restore_dtypes(pd.read_csv(path, keep_default_na=False,
                                         dtype={"headline": str}, low_memory=False),
                             flags)


# ── profile ─────────────────────────────────────────────────────────────────
def cmd_profile(args) -> None:
    args.include_flagged = True
    df = load_corpus(args)
    ok = df[df.quality_ok]
    reps = ok.drop_duplicates("body_key")
    print(f"\nretrieved stories {len(df):,} | pass the hard quality checks "
          f"{len(ok):,} ({len(ok)/max(len(df),1):.1%})")
    print(f"distinct bodies to label {len(reps):,} "
          f"(of {df.body_key.nunique():,} distinct bodies retrieved)")
    print(f"body words: median {reps.n_words.median():,.0f}, "
          f"total {reps.n_words.sum():,}")
    print("\nheadline labels in this population (stage 18)")
    for label, n in ok[HL + "primary"].value_counts().items():
        print(f"  {label:<20}{n:>8,}")
    print("\ntornado mentions per body")
    print(f"  median {reps.n_mentions.median():.0f} | exactly one "
          f"{(reps.n_mentions == 1).mean():.1%} | none {(reps.n_mentions == 0).mean():.1%}")
    print(f"protected (headline + lede) {reps.protected.mean():.1%}")
    print("\nevidence-window cost per mode (words sent, over distinct bodies)")
    sample = reps.sample(min(400, len(reps)), random_state=args.random_seed)
    for mode in lf.EVIDENCE_MODES:
        lens = [len(lf.render_evidence(r, mode)[0].split()) for _, r in sample.iterrows()]
        mean = float(np.mean(lens)) if lens else 0.0
        print(f"  {mode:<12} mean {mean:>6.0f} words  -> "
              f"~{mean * len(reps) * 1.35 / 1e6:>5.1f}M tokens"
              f"{'   <- stage 19 default' if mode == 'windows' else ''}")


# ── label ───────────────────────────────────────────────────────────────────
def cmd_label(args) -> pd.DataFrame:
    df = load_corpus(args)
    reps = df[df.is_representative].copy()
    print(f"\nlabelling {len(reps):,} distinct bodies ({len(df):,} stories) at "
          f"temperature 0 with stage 19's prompt (evidence mode: {args.mode})")
    client = make_client(args)
    parsed = run_llm(client, reps, "labelling", args.mode, temperature=0.0)
    out = pd.concat([reps.drop(columns=["body"]), parsed], axis=1)
    out["evidence_mode"] = args.mode

    coerced = lf.enforce_protect_invariant(out)
    if coerced:
        print(f"\nprotect rule overruled the model on {coerced:,} bodies")
    LABELS.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(LABELS, index=False)
    print(f"\nwrote {LABELS} ({len(out):,} rows)")
    print("\n" + lf.label_summary(out, lf.FLAGS))
    return out


# ── uncertainty ─────────────────────────────────────────────────────────────
def cmd_uncertainty(args) -> None:
    labels = require(LABELS, "label")
    df = load_corpus(args)
    reps = df[df.is_representative].set_index("body_key")
    labels = labels[labels.body_key.isin(reps.index)]
    rng = np.random.default_rng(args.random_seed)
    n = max(1, int(round(len(labels) * args.uncertainty_frac)))
    chosen = labels.loc[rng.choice(labels.index, size=min(n, len(labels)), replace=False)]
    subset = reps.loc[chosen.body_key].reset_index()
    print(f"\nre-labelling {len(subset):,} bodies ({args.uncertainty_frac:.0%}) "
          f"{args.k}x at temperature {labelling.UNCERTAINTY_TEMPERATURE}")
    client = make_client(args)
    draws = []
    for i in range(args.k):
        parsed = run_llm(client, subset, f"sample {i + 1}/{args.k}", args.mode,
                         temperature=labelling.UNCERTAINTY_TEMPERATURE, variant=f"sc{i}")
        draws.append(parsed["primary"].rename(f"sample_{i}"))
    scores = lf.consistency_scores(draws)
    out = pd.concat([subset[["body_key", "url", "headline", "n_mentions"]],
                     pd.concat(draws, axis=1), scores], axis=1)
    out["primary_t0"] = chosen.primary.to_numpy()
    out["agrees_with_t0"] = out.modal_label == out.primary_t0
    out.to_csv(CONSISTENCY, index=False)
    stable, total = int(out.stable.sum()), len(out)
    lo, hi = wilson_interval(stable, total)
    print(f"\nunanimous across {args.k} draws: {stable:,}/{total:,} = "
          f"{stable/total:.1%} [{lo:.1%}, {hi:.1%}]")
    for label, grp in out.groupby("primary_t0"):
        print(f"  {label:<20}{int(grp.stable.sum()):>6,}/{len(grp):<6,} "
              f"{grp.stable.mean():>6.1%}")
    print(f"\nwrote {CONSISTENCY}")


# ── apply ───────────────────────────────────────────────────────────────────
def cmd_apply(args) -> None:
    labels = require(LABELS, "label")
    df = load_corpus(args)
    carry = ["primary", "parsed", "conf", *lf.FLAGS]
    out = lf.propagate(df, labels, "body_key", carry)
    missing = int(out.primary.isna().sum())
    if missing:
        sys.exit(f"{missing:,} stories have no label — `label` ran on a different "
                 "slice than `apply` (another --limit, --include-flagged, or a "
                 "newer `quality` run). Re-run `label` with the same options.")
    coerced = lf.enforce_protect_invariant(out)
    if int((out.protected & out.nonmet_sense).sum()):
        sys.exit("protect invariant violated after propagation — refusing to write.")

    out["evidence_mode"] = labels.evidence_mode.iloc[0] if len(labels) else args.mode
    out = out.rename(columns={c: FT + c for c in [*carry, "evidence_mode"]})
    hl_flags = [c for c in out.columns if c.startswith(HL) and c != "hl_group"]
    keep = ["url", "headline", "page_title", "source", "pub_date", "via", "year_band",
            "domain_size", "n_words", "n_mentions", "quality_ok", "protected",
            "cue_single_mention", "cue_press_release", "cue_roundup", "body_key",
            "dup_count", "hl_group", *hl_flags, *[FT + c for c in carry],
            FT + "evidence_mode"]
    STORY_LABELS.parent.mkdir(parents=True, exist_ok=True)
    out[keep].to_csv(STORY_LABELS, index=False)
    agree = (out[HL + "primary"] == out[FT + "primary"]).mean()
    print(f"protect invariant holds ({coerced:,} repaired during propagation)")
    print(f"\nwrote {STORY_LABELS} ({len(out):,} stories, "
          f"{out.body_key.nunique():,} distinct bodies)")
    print(f"headline and full-text primary agree on {agree:.1%} — "
          "run `compare` for the breakdown")


# ── compare ─────────────────────────────────────────────────────────────────
def load_story_labels() -> pd.DataFrame:
    flags = [HL + f for f in labelling.BASE_FLAGS] + [FT + f for f in lf.FLAGS] + \
            [FT + "parsed", "quality_ok", "protected", "cue_single_mention",
             "cue_press_release", "cue_roundup"]
    df = require(STORY_LABELS, "apply", flags)
    for col in (HL + "conf", FT + "conf"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def ci(k: int, n: int) -> str:
    lo, hi = wilson_interval(k, n)
    return f"{k/n:.1%} [{lo:.1%}, {hi:.1%}]" if n else "—"


def strata_table(df: pd.DataFrame, by, label: str) -> list[str]:
    t = fc.agreement_by(df, by)
    lines = [f"| {label} | stories | agree | rate [95% CI] |", "|---|---:|---:|---|"]
    for r in t.itertuples():
        lines.append(f"| {r.key} | {r.n:,} | {r.agree:,} | {ci(int(r.agree), int(r.n))} |")
    return lines


def cmd_compare(args) -> None:
    df = load_story_labels()
    df = df[df[FT + "parsed"]].copy()
    n = len(df)
    if not n:
        sys.exit("no parsed full-text labels to compare")
    agree = df[HL + "primary"] == df[FT + "primary"]
    bodies = df.drop_duplicates("body_key")
    b_agree = bodies[HL + "primary"] == bodies[FT + "primary"]
    hl_labels = sorted(df[HL + "primary"].unique())

    print(f"\n{n:,} stories with both labels ({len(bodies):,} distinct bodies)")
    print(f"primary agreement: {ci(int(agree.sum()), n)} (stories), "
          f"{ci(int(b_agree.sum()), len(bodies))} (bodies)")
    print("\nheadline (rows) × full text (columns)")
    print(fc.primary_crosstab(df).to_string())
    print("\nflag agreement")
    print(fc.flag_agreement(df).to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    lines = [
        "# Media Cloud — full-text versus headline labels (Stage 23)", "",
        f"> **Scope: {n:,} Media Cloud stories** whose headline stage 18 labelled "
        f"{', '.join(f'`{l}`' for l in hl_labels)} and whose body stage 21 retrieved"
        f"{' and passed every hard quality check' if df.quality_ok.all() else ''}. "
        + ("Because only headline-`EVENT` stories were crawled, this measures the "
           "headline labeller's **precision**: how many of its `EVENT` calls the full "
           "text overturns. It says nothing about real reports it rejected."
           if hl_labels == ["EVENT"] else
           "Non-`EVENT` headline labels are present, so the crosstab also bears on recall "
           "— but only for the sample that was crawled, not the corpus."), "",
        f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}. "
        "Both labels come from the same locally hosted LLM; the full-text label uses "
        f"stage 19's prompt and evidence window (`{df[FT + 'evidence_mode'].iloc[0]}`) "
        "unchanged, the headline label stage 18's. Neither is ground truth.", "",
        "## Agreement", "",
        f"- **Stories:** {ci(int(agree.sum()), n)} keep the same primary label.",
        f"- **Distinct bodies:** {ci(int(b_agree.sum()), len(bodies))}. Lower or "
        "higher than the story figure tells you whether disagreement concentrates "
        "in wire copy carried under many headlines.", "",
        "| headline ↓ / full text → | " + " | ".join(f"`{c}`" for c in labelling.PRIMARY_LABELS)
        + " |", "|---|" + "---:|" * len(labelling.PRIMARY_LABELS),
    ]
    for label, row in fc.primary_crosstab(df).iterrows():
        lines.append(f"| `{label}` | " + " | ".join(f"{v:,}" for v in row) + " |")

    # ── what the full text says instead ─────────────────────────────────────
    moved = df[~agree]
    lines += ["", "## What the full text says instead", ""]
    if len(moved):
        lines += ["| change | stories | share of all |", "|---|---:|---:|"]
        for key, k in fc.transitions(df).items():
            lines.append(f"| {key} | {k:,} | {k/n:.1%} |")
        lines += ["", "Full-text flags on the stories whose label changed — the "
                  "reasons the body gives that the headline could not:", "",
                  "| full-text flag | changed stories | share | share among unchanged |",
                  "|---|---:|---:|---:|"]
        kept = df[agree]
        for flag in lf.FLAGS:
            col = FT + flag
            lines.append(f"| `{flag}` | {int(moved[col].sum()):,} | "
                         f"{moved[col].mean():.1%} | {kept[col].mean():.1%} |")
    else:
        lines.append("No story changed label.")

    # ── flags ───────────────────────────────────────────────────────────────
    fa = fc.flag_agreement(df)
    lines += ["", "## Flags both labellers set", "",
              "Raw agreement is dominated by the many rows where neither sets a flag; "
              "Cohen's κ corrects for that and is the figure to read.", "",
              "| flag | headline | full text | both | κ |", "|---|---:|---:|---:|---:|"]
    for r in fa.itertuples():
        lines.append(f"| `{r.flag}` | {r.headline:,} | {r.fulltext:,} | {r.both:,} | "
                     f"{'—' if pd.isna(r.kappa) else f'{r.kappa:.2f}'} |")
    lines += ["", "Flags only the full-text labeller has (`is_passing_mention`, "
              "`is_press_release`, `is_roundup`) appear in the previous section.", ""]

    # ── where disagreement concentrates ─────────────────────────────────────
    lines += ["## Where disagreement concentrates", "",
              "### By the headline labeller's self-reported confidence", "",
              "If agreement rises with `conf`, the headline confidence is usable as a "
              "cheap filter where no body is available.", ""]
    lines += strata_table(df, fc.conf_bins(df[HL + "conf"]), "headline conf") + [""]
    lines += ["### By tornado mentions in the body", ""]
    lines += strata_table(df, fc.mention_bins(df.n_mentions), "mentions") + [""]
    lines += ["### By year band", ""] + strata_table(df, "year_band", "year band") + [""]
    lines += ["### By domain size", ""] + strata_table(df, "domain_size", "domain size") + [""]
    lines += ["### By retrieval route", ""] + strata_table(df, "via", "route") + [""]

    # ── noise floor ─────────────────────────────────────────────────────────
    lines += ["## How much of this is labeller noise?", ""]
    noise = noise_floor(df)
    lines += noise + [""]

    # ── LexisNexis ──────────────────────────────────────────────────────────
    lines += ["## Against LexisNexis, on stories both corpora hold", ""]
    lines += lexis_section(df) + [""]

    # ── human verdicts ──────────────────────────────────────────────────────
    lines += ["## Against human verdicts from the inspection viewer", ""]
    lines += human_section(df) + [""]

    # ── examples ────────────────────────────────────────────────────────────
    lines += ["## Examples to inspect", "",
              "Five per change, by URL and headline only — open them in "
              "`python scripts/16_viewer.py --corpus mediacloud` with the matching "
              "filter to read the body next to both labels.", ""]
    for key in fc.transitions(df).index:
        h, f = key.split(" → ")
        sample = moved[(moved[HL + "primary"] == h) & (moved[FT + "primary"] == f)]
        sample = sample.sample(min(5, len(sample)), random_state=1)
        lines.append(f"**{key}**")
        lines.append("")
        for r in sample.itertuples():
            lines.append(f"- [{str(r.headline)[:90]}]({r.url})")
        lines.append("")

    lines += [
        "## Limitations", "",
        "1. **Neither label is ground truth.** Both come from the same model; the full "
        "text gives it better evidence, not infallibility. The human-verdict section "
        "is the only check against a person, and it is only as good as the sample "
        "behind it.",
        "2. **Precision only**, unless non-`EVENT` stories were crawled: see the scope "
        "note at the top.",
        "3. **Quality filtered.** Bodies failing a hard check in "
        "`fulltext_quality_report.md` are excluded, so the population is the "
        "retrievable, well-extracted part of the corpus — older and smaller-outlet "
        "stories are under-represented, as the coverage report shows.",
        "4. **Evidence windows.** The full-text label sees the lede and the context of "
        "up to six tornado mentions, not the whole body. Stage 19's window ablation is "
        "the measurement of what that costs.",
        "5. **Story versus body.** A body carried under several headlines gets one "
        "full-text label; if those headlines were labelled differently, the "
        "disagreement is counted once per story.", "",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nwrote {REPORT}")


def noise_floor(df: pd.DataFrame) -> list[str]:
    """Disagreement on rows where *both* labellers were unanimous across k draws.

    Disagreement among stable rows cannot be sampling noise; it is the evidence
    gap between headline and body.
    """
    out = []
    ft = None
    if CONSISTENCY.exists():
        ft = pd.read_csv(CONSISTENCY, keep_default_na=False)
        ft["stable"] = ft.stable.astype(str).str.lower() == "true"
        out.append(f"- Full-text labels unanimous across {ft.n_samples.iloc[0]} draws at "
                   f"T={labelling.UNCERTAINTY_TEMPERATURE}: "
                   f"{ci(int(ft.stable.sum()), len(ft))} of {len(ft):,} sampled bodies.")
    hl = None
    if MC_CONSISTENCY.exists():
        hl = pd.read_csv(MC_CONSISTENCY, keep_default_na=False, usecols=["url", "stable"])
        hl["stable"] = hl.stable.astype(str).str.lower() == "true"
        sub = df[df.url.isin(hl.url)]
        out.append(f"- Headline labels sampled by stage 18's uncertainty pass: "
                   f"{len(sub):,} of these stories.")
    if ft is not None and hl is not None:
        both = (df.merge(ft[["body_key", "stable"]].rename(columns={"stable": "ft_stable"}),
                         on="body_key")
                  .merge(hl.rename(columns={"stable": "hl_stable"}), on="url"))
        both = both[both.ft_stable & both.hl_stable]
        if len(both):
            k = int((both[HL + "primary"] == both[FT + "primary"]).sum())
            out.append(f"- On the **{len(both):,} stories where both labellers were "
                       f"unanimous**, agreement is {ci(k, len(both))}. Disagreement "
                       "here is not noise: it is what the body says that the headline "
                       "does not.")
        else:
            out.append("- The two uncertainty samples do not overlap; no doubly-stable "
                       "subset to report.")
    if not out:
        out.append("Run `uncertainty` here and in stage 18 to separate noise from "
                   "evidence.")
    return out


def lexis_section(df: pd.DataFrame) -> list[str]:
    from tornado_dataset.text import corpora
    if not ATLAS_EDGES.exists():
        return [f"Skipped: `{ATLAS_EDGES.name}` not found — run "
                "`python scripts/22_corpus_atlas.py` (full scope) first."]
    try:
        lexis = corpora.load_lexisnexis()
    except FileNotFoundError as exc:
        return [f"Skipped: {exc}"]
    edges = pd.read_csv(ATLAS_EDGES, keep_default_na=False)
    pairs = fc.cross_corpus(df, lexis, edges)
    if pairs.empty:
        return ["No matched LexisNexis–Media Cloud story has a full-text label."]
    n = len(pairs)
    k_hl = int((pairs.ln_primary == pairs[HL + "primary"]).sum())
    k_ft = int((pairs.ln_primary == pairs[FT + "primary"]).sum())
    ln_ev = pairs.ln_primary == lf.EVENT
    ft_ev = pairs[FT + "primary"] == lf.EVENT
    lines = [
        f"{n:,} matched story pairs from the corpus atlas whose Media Cloud side now has "
        "a full-text label. Both sides were labelled on a body with the **same prompt**, "
        "so on these pairs the comparison is like with like: two copies of one story, "
        "one from LexisNexis and one from the open web.", "",
        "| LexisNexis label agrees with | pairs | agreement |", "|---|---:|---|",
        f"| Media Cloud headline label | {n:,} | {ci(k_hl, n)} |",
        f"| Media Cloud full-text label | {n:,} | {ci(k_ft, n)} |", "",
    ]
    if (pairs[HL + "primary"] == lf.EVENT).all():
        lines += [
            "Only headline-`EVENT` stories were crawled, so the first row is just "
            "LexisNexis's `EVENT` rate on this subset and cannot be set against the "
            "atlas-wide agreement. The informative figures are these:", "",
            f"- **Same prompt on two copies of the story:** "
            f"{ci(int((ln_ev == ft_ev).sum()), n)} agree on `EVENT` versus not. This is a test–retest of the full-text labeller across sources; "
            "where it fails, the two copies differ (an update, a trimmed wire version, "
            "an extraction fault) or the atlas matched two different stories.",
            f"- **LexisNexis `EVENT`, Media Cloud full text not:** "
            f"{int((ln_ev & ~ft_ev).sum()):,} pairs. Read them in the viewer: they show "
            "whether the body the open web serves supports less than the LexisNexis copy.",
            f"- **LexisNexis not `EVENT`, full text agrees with LexisNexis against the "
            f"headline:** {int((~ln_ev & ~ft_ev).sum()):,} of {int((~ln_ev).sum()):,}. "
            "These are headline false positives that LexisNexis had already caught.", "",
        ]
    lines += [
        "| LexisNexis ↓ / Media Cloud full text → | "
        + " | ".join(f"`{c}`" for c in labelling.PRIMARY_LABELS) + " |",
        "|---|" + "---:|" * len(labelling.PRIMARY_LABELS),
    ]
    t = pd.crosstab(pairs.ln_primary, pairs[FT + "primary"])
    t = t.reindex(index=[l for l in labelling.PRIMARY_LABELS if l in t.index],
                  columns=list(labelling.PRIMARY_LABELS), fill_value=0)
    for label, row in t.iterrows():
        lines.append(f"| `{label}` | " + " | ".join(f"{v:,}" for v in row) + " |")
    return lines


def human_section(df: pd.DataFrame) -> list[str]:
    seen = fc.load_inspections()
    if seen.empty:
        return ["None yet. Verdicts given in the viewer are stored in "
                f"`{fc.INSPECTION_CSV.name}` and summarised here on the next `compare`."]
    labelled = seen[seen.label.isin(labelling.PRIMARY_LABELS)].merge(
        df[["url", HL + "primary", FT + "primary", "quality_ok"]], on="url", how="inner")
    lines = [f"{len(seen):,} articles inspected; {len(labelled):,} carry a human primary "
             "label and a full-text label.", ""]
    if len(labelled):
        lines += ["| verdicts | n | headline label correct | full-text label correct |",
                  "|---|---:|---|---|"]
        for name, part in [("drawn at random", labelled[labelled.via_random]),
                           ("all (includes targeted picks)", labelled)]:
            if not len(part):
                continue
            kh = int((part[HL + "primary"] == part.label).sum())
            kf = int((part[FT + "primary"] == part.label).sum())
            lines.append(f"| {name} | {len(part):,} | {ci(kh, len(part))} | "
                         f"{ci(kf, len(part))} |")
        lines += ["", "Only the random row estimates accuracy. Verdicts reached through "
                  "a filter — disagreements, say — are chosen *because* they are hard, "
                  "and overstate the error of both labellers."]
    bodies = seen[seen.body_verdict.isin(fc.BODY_VERDICTS)]
    if len(bodies):
        lines += ["", "Body verdicts (is this the article?):", "",
                  "| verdict | n |", "|---|---:|"]
        for v, k in bodies.body_verdict.value_counts().items():
            lines.append(f"| `{v}` | {k:,} |")
    return lines


def cmd_run(args) -> None:
    if LABELS.exists() and not args.relabel:
        print(f"reusing existing labels at {LABELS} (pass --relabel to redo)")
    else:
        cmd_label(args)
    if not args.no_uncertainty:
        cmd_uncertainty(args)
    cmd_apply(args)
    cmd_compare(args)


# ── CLI ─────────────────────────────────────────────────────────────────────
def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp, llm: bool = True):
        sp.add_argument("--limit", type=int, help="only read the first N stories")
        sp.add_argument("--tag", default=None,
                        help="suffix for this run's output files; use one for smoke tests")
        sp.add_argument("--include-flagged", action="store_true",
                        help="also label bodies that fail a hard quality check")
        sp.add_argument("--random-seed", type=int, default=20260807)
        sp.add_argument("--uncertainty-frac", type=float, default=0.10)
        sp.add_argument("--k", type=int, default=3)
        sp.add_argument("--mode", default="windows", choices=lf.EVIDENCE_MODES,
                        help="evidence sent to the model (default: windows, as stage 19)")
        if llm:
            sp.add_argument("--api-base", default=None)
            sp.add_argument("--model", default=None,
                            help="served model id (default: ask the server)")
            sp.add_argument("--concurrency", type=int, default=32)
            sp.add_argument("--thinking", action="store_true")

    for name, fn, helptext in [
        ("profile", cmd_profile, "population and evidence cost; no LLM"),
        ("label", cmd_label, "label every distinct body at T=0"),
        ("uncertainty", cmd_uncertainty, "k draws at T=1 on a random subset"),
        ("apply", cmd_apply, "propagate to stories, write the per-story table"),
        ("compare", cmd_compare, "headline versus full text; writes the report"),
        ("run", cmd_run, "label, uncertainty, apply and compare"),
    ]:
        sp = sub.add_parser(name, help=helptext)
        common(sp, llm=name not in ("profile", "apply", "compare"))
        if name == "run":
            sp.add_argument("--relabel", action="store_true")
            sp.add_argument("--no-uncertainty", action="store_true")
        sp.set_defaults(func=fn)

    args = p.parse_args()
    set_paths(args.tag)
    if getattr(args, "api_base", None) is None:
        from tornado_dataset.llm import DEFAULT_API_BASE
        args.api_base = DEFAULT_API_BASE
    args.func(args)


if __name__ == "__main__":
    main()

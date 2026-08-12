#!/usr/bin/env python
"""Stage 19 — filter the LexisNexis corpus to articles reporting real tornadoes.

Labels all 20,138 distinct article bodies with a locally hosted LLM and
propagates each answer to the 22,896 ``textref_uid``s that share them. Same
method and same label vocabulary as stage 18, so the two corpora stay comparable
for the overlap study; see :mod:`tornado_dataset.text.lexisnexis_filter` for what
this corpus needs done differently.

Typical run — forward the model's port first, then::

    ssh -N -L 8000:localhost:8000 you@your-server        # in another terminal
    python scripts/19_filter_lexisnexis.py profile       # corpus shape, no LLM
    python scripts/19_filter_lexisnexis.py window        # choose the evidence window
    python scripts/19_filter_lexisnexis.py run           # label + uncertainty + write

Resumable: every answer is cached on disk by (model, prompt, temperature,
sample), so an interrupted job re-reads what it already paid for.

Subcommands
-----------
profile      corpus shape and audit-cue coverage; no LLM, no model needed
window       label a sample under each evidence mode and compare — run this first
label        label every distinct body at temperature 0
uncertainty  re-label a random subset k times at temperature 1.0
apply        propagate to every article, enforce the protect rule, write the table
crosstab     compare labels with stage 11's existing link_status (validation)
run          label, uncertainty and apply

Use ``--tag`` for anything experimental. Output paths are derived from it, so a
smoke test cannot overwrite a real run — ``--limit`` bounds only how much of the
corpus is *read*, which is not the same protection.
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
from tornado_dataset.text import labelling                      # noqa: E402
from tornado_dataset.text import lexisnexis_filter as lf        # noqa: E402
from tornado_dataset.text.lexisnexis import textref_uid         # noqa: E402

SOURCE_JSONL = config.OUTPUT_DIR / "lexisnexis_articles.jsonl"
STATUS_CSV = config.PROCESSED_DIR / "article_status_2010-01-01_2025-12-31.csv"

LABELS = CONSISTENCY = ABLATION = LLM_CACHE = ARTICLE_LABELS = REPORT = None


def set_paths(tag: str | None) -> None:
    global LABELS, CONSISTENCY, ABLATION, LLM_CACHE, ARTICLE_LABELS, REPORT
    suffix = f"_{tag}" if tag else ""
    LABELS = config.INTERIM_DIR / f"lexisnexis_labels{suffix}.csv"
    CONSISTENCY = config.INTERIM_DIR / f"lexisnexis_consistency{suffix}.csv"
    ABLATION = config.INTERIM_DIR / f"lexisnexis_window_ablation{suffix}.csv"
    # Shared across tags: the cache is keyed by (model, prompt, temperature,
    # sample), so a tagged run inherits every answer already paid for.
    LLM_CACHE = config.INTERIM_DIR / "lexisnexis_llm_cache.jsonl"
    ARTICLE_LABELS = config.PROCESSED_DIR / f"lexisnexis_article_labels{suffix}.csv"
    REPORT = config.OUTPUT_DIR / f"lexisnexis_filter_report{suffix}.md"


# ── shared plumbing ─────────────────────────────────────────────────────────
def load_corpus(limit: int | None = None) -> pd.DataFrame:
    if not SOURCE_JSONL.exists():
        sys.exit(f"missing input: {SOURCE_JSONL}\n"
                 "Run `python -m tornado_dataset.text.lexisnexis` first.")
    df = pd.read_json(SOURCE_JSONL, lines=True)
    if limit:
        df = df.head(limit).copy()
    df["textref_uid"] = [textref_uid(r) for r in df.to_dict("records")]
    return lf.add_rule_cues(lf.add_dedup_groups(df))


def make_client(args) -> LLMClient:
    client = LLMClient(api_base=args.api_base, model=args.model, cache_path=LLM_CACHE,
                       concurrency=args.concurrency, thinking=args.thinking)
    print(f"  LLM: {client.model} @ {client.api_base} "
          f"(concurrency {client.concurrency}, thinking={client.thinking})")
    return client


def run_llm(client: LLMClient, rows: pd.DataFrame, desc: str, mode: str,
            temperature: float | None = None, variant: str = "") -> pd.DataFrame:
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


def require(path: Path, what: str) -> pd.DataFrame:
    if not path.exists():
        sys.exit(f"missing {path} — run the `{what}` subcommand first.")
    return lf.restore_dtypes(
        pd.read_csv(path, keep_default_na=False, dtype={"headline": str}), lf.FLAGS)


# ── profile ─────────────────────────────────────────────────────────────────
def cmd_profile(args) -> None:
    df = load_corpus(args.limit)
    reps = df[df.is_representative]
    print(f"\nrows {len(df):,} | distinct bodies {len(reps):,} "
          f"({1 - len(reps) / len(df):.1%} redundant) | textref_uid {df.textref_uid.nunique():,}")
    print(f"dates {str(df.pub_date.min())[:10]} .. {str(df.pub_date.max())[:10]} "
          f"| sources {df.source.nunique():,}")
    print(f"body words: median {reps.n_words.median():,.0f}, mean {reps.n_words.mean():,.0f}, "
          f"total {reps.n_words.sum():,}")

    print("\nprotect rule (headline + lede only — a full-body rule would be vacuous)")
    print(f"  protected            {reps.protected.sum():>7,}  ({reps.protected.mean():.1%})")

    print("\naudit cues over distinct bodies (descriptive only — these decide nothing)")
    for col in [c for c in reps.columns if c.startswith("cue_")]:
        print(f"  {col:<24}{reps[col].sum():>7,}  ({reps[col].mean():>5.1%})")

    print("\ntornado mentions per body")
    print(f"  median {reps.n_mentions.median():.0f} | "
          f"exactly one {(reps.n_mentions == 1).mean():.1%} "
          f"| none {(reps.n_mentions == 0).mean():.1%}")

    print("\nevidence-window cost per mode (words sent, over distinct bodies)")
    sample = reps.sample(min(400, len(reps)), random_state=args.random_seed)
    for mode in lf.EVIDENCE_MODES:
        lens = [len(lf.render_evidence(r, mode)[0].split()) for _, r in sample.iterrows()]
        mean = float(np.mean(lens))
        print(f"  {mode:<12} mean {mean:>6.0f} words  -> "
              f"~{mean * len(reps) * 1.35 / 1e6:>5.1f}M tokens for the corpus")


# ── window ablation ─────────────────────────────────────────────────────────
def cmd_window(args) -> None:
    """Label one sample under every evidence mode and compare.

    Run before the full pass. The evidence window bounds what the labeller can
    possibly know, so choosing it by intuition would silently bound recall; this
    measures the choice instead.
    """
    df = load_corpus(args.limit)
    reps = df[df.is_representative]
    rng = np.random.default_rng(args.random_seed)
    # Stratify on mention count: that is the axis the modes should differ on,
    # since a single-mention article is exactly where a prefix can miss it.
    strata = pd.cut(reps.n_mentions, [-1, 1, 3, 8, 10**6],
                    labels=["1 or none", "2-3", "4-8", "9+"])
    picks = []
    for _, idx in reps.groupby(strata, observed=True).groups.items():
        take = min(len(idx), max(1, args.window_size // 4))
        picks.append(rng.choice(np.asarray(idx), size=take, replace=False))
    subset = reps.loc[np.concatenate(picks)].copy()
    print(f"\nablation on {len(subset):,} bodies, stratified by mention count")
    print(subset.assign(s=strata.loc[subset.index]).s.value_counts().to_string())

    client = make_client(args)
    results = {}
    for mode in lf.EVIDENCE_MODES:
        parsed = run_llm(client, subset, f"mode={mode}", mode,
                         temperature=0.0, variant=f"win-{mode}")
        results[mode] = parsed["primary"].to_numpy()

    table = pd.DataFrame(results, index=subset.index)
    table["n_mentions"] = subset.n_mentions
    table["headline"] = subset.headline
    ABLATION.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(ABLATION, index=False)

    print("\nlabel distribution by evidence mode")
    dist = pd.DataFrame({m: pd.Series(v).value_counts(normalize=True)
                         for m, v in results.items()}).fillna(0.0)
    print((dist * 100).round(1).to_string())

    ref = "full2000"
    print(f"\nagreement with `{ref}` (the most evidence any mode gets)")
    for mode in lf.EVIDENCE_MODES:
        if mode == ref:
            continue
        agree = (table[mode] == table[ref])
        lo, hi = wilson_interval(int(agree.sum()), len(agree))
        print(f"  {mode:<12} {agree.mean():>6.1%}  [{lo:.1%}, {hi:.1%}]")
        low = table.n_mentions <= 1
        if low.any():
            sub = agree[low]
            print(f"               on single-mention bodies: {sub.mean():.1%} (n={len(sub)})")
    print(f"\nwrote {ABLATION}")
    print("Pick the mode on this table: prefer the cheapest whose agreement with "
          "full2000 is acceptable, and record the choice in the report.")


# ── label ───────────────────────────────────────────────────────────────────
def cmd_label(args) -> pd.DataFrame:
    df = load_corpus(args.limit)
    reps = df[df.is_representative].copy()
    print(f"\nlabelling {len(reps):,} distinct bodies at temperature 0 "
          f"(evidence mode: {args.mode})")

    client = make_client(args)
    parsed = run_llm(client, reps, "labelling", args.mode, temperature=0.0)
    out = pd.concat([reps.drop(columns=["body"]), parsed], axis=1)
    out["evidence_mode"] = args.mode

    coerced = lf.enforce_protect_invariant(out)
    if coerced:
        print(f"\nprotect rule overruled the model on {coerced:,} bodies it flagged "
              "nonmet_sense despite a protected weather term in headline or lede")

    LABELS.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(LABELS, index=False)
    print(f"\nwrote {LABELS} ({len(out):,} rows)")
    print("\n" + lf.label_summary(out, lf.FLAGS))
    return out


# ── uncertainty ─────────────────────────────────────────────────────────────
def cmd_uncertainty(args) -> None:
    labels = require(LABELS, "label")
    df = load_corpus(args.limit)
    reps = df[df.is_representative].set_index("body_key")
    rng = np.random.default_rng(args.random_seed)
    n = max(1, int(round(len(labels) * args.uncertainty_frac)))
    idx = rng.choice(labels.index, size=min(n, len(labels)), replace=False)
    chosen = labels.loc[idx]
    subset = reps.loc[chosen.body_key].reset_index()
    print(f"\nre-labelling {len(subset):,} bodies ({args.uncertainty_frac:.0%} of "
          f"{len(labels):,}) {args.k}x at temperature {labelling.UNCERTAINTY_TEMPERATURE}")

    client = make_client(args)
    draws = []
    for i in range(args.k):
        parsed = run_llm(client, subset, f"sample {i + 1}/{args.k}", args.mode,
                         temperature=labelling.UNCERTAINTY_TEMPERATURE, variant=f"sc{i}")
        draws.append(parsed["primary"].rename(f"sample_{i}"))

    scores = lf.consistency_scores(draws)
    out = pd.concat([subset[["body_key", "headline", "source", "n_mentions"]],
                     pd.concat(draws, axis=1), scores], axis=1)
    out["primary_t0"] = chosen.primary.to_numpy()
    out["agrees_with_t0"] = out.modal_label == out.primary_t0
    out.to_csv(CONSISTENCY, index=False)

    stable, total = int(out.stable.sum()), len(out)
    lo, hi = wilson_interval(stable, total)
    agree = int(out.agrees_with_t0.sum())
    alo, ahi = wilson_interval(agree, total)
    print(f"\nunanimous across {args.k} draws: {stable:,}/{total:,} = {stable/total:.1%} "
          f"[{lo:.1%}, {hi:.1%}]")
    print(f"T=0 label equals the T=1 modal label: {agree/total:.1%} [{alo:.1%}, {ahi:.1%}]")
    print("\nstability by T=0 label")
    for label, grp in out.groupby("primary_t0"):
        k = int(grp.stable.sum())
        blo, bhi = wilson_interval(k, len(grp))
        print(f"  {label:<20}{k:>6,}/{len(grp):<6,} {k/len(grp):>6.1%}  [{blo:.1%}, {bhi:.1%}]")
    print(f"\nwrote {CONSISTENCY}")


# ── apply ───────────────────────────────────────────────────────────────────
def cmd_apply(args) -> None:
    labels = require(LABELS, "label")
    df = load_corpus(args.limit)

    carry = ["primary", "parsed", "conf", *lf.FLAGS]
    out = lf.propagate(df, labels, "body_key", carry)
    out["is_event"] = out.primary == lf.EVENT

    missing = int(out.primary.isna().sum())
    if missing:
        sys.exit(f"{missing:,} articles have no label — `label` ran on a different "
                 "slice than `apply`. Re-run both with the same --limit.")

    coerced = lf.enforce_protect_invariant(out)
    leaked = int((out.protected & out.nonmet_sense).sum())
    if leaked:
        sys.exit(f"protect invariant violated on {leaked:,} written rows — refusing "
                 "to write a table that contradicts it.")
    print(f"protect invariant holds on all {len(out):,} articles "
          f"({coerced:,} repaired during propagation)")

    keep = ["textref_uid", "file", "headline", "source", "pub_date", "section",
            "n_words", "n_mentions", "primary", "is_event", *lf.FLAGS, "conf",
            "parsed", "protected", "cue_press_release", "cue_single_mention",
            "cue_roundup", "body_key", "dup_count", "is_representative"]
    ARTICLE_LABELS.parent.mkdir(parents=True, exist_ok=True)
    out[keep].to_csv(ARTICLE_LABELS, index=False)
    write_report(out, labels, args)

    ev = out[out.is_event]
    print(f"\nwrote {ARTICLE_LABELS} ({len(out):,} articles, "
          f"{out.textref_uid.nunique():,} distinct textref_uid)")
    print(f"  EVENT: {len(ev):,} articles ({ev.body_key.nunique():,} distinct bodies) "
          "— these are what stage 11 will link")
    print(f"wrote {REPORT}")


# ── crosstab against the existing linker run ────────────────────────────────
def cmd_crosstab(args) -> None:
    """Compare labels with stage 11's link_status from its pre-gate run.

    Gating stage 11 means filtered articles are never linked, so a filter false
    negative would be invisible from then on. Stage 11 has already run over the
    whole corpus once, ungated, so this comparison is available for free — but
    only until it is re-run under the gate. Do it now, and read both disagreement
    lists by hand.
    """
    if not ARTICLE_LABELS.exists():
        sys.exit(f"missing {ARTICLE_LABELS} — run `apply` first.")
    if not STATUS_CSV.exists():
        sys.exit(f"missing {STATUS_CSV} — nothing to compare against.")
    labels = lf.restore_dtypes(pd.read_csv(ARTICLE_LABELS, keep_default_na=False), lf.FLAGS)
    status = pd.read_csv(STATUS_CSV, keep_default_na=False)
    merged = labels.merge(status[["textref_uid", "link_status", "n_links"]],
                          on="textref_uid", how="inner")
    print(f"\nmatched {len(merged):,} articles against stage 11's ungated run\n")
    print(pd.crosstab(merged.primary, merged.link_status).to_string())

    fn = merged[(merged.primary != lf.EVENT) & (merged.link_status == "linked")
                & (merged.n_links > 0)]
    fp = merged[(merged.primary == lf.EVENT) & (merged.link_status == "no_link_above_floor")]
    print(f"\ncandidate filter false negatives — not EVENT, yet the linker linked "
          f"them: {len(fn):,} ({len(fn)/max(len(merged),1):.1%})")
    for _, r in fn.head(10).iterrows():
        print(f"   [{r.primary:<18}] {str(r.headline)[:78]}")
    print(f"\ncandidate linker misses — EVENT, but no link cleared the floor: "
          f"{len(fp):,}")
    for _, r in fp.head(10).iterrows():
        print(f"   {str(r.headline)[:96]}")
    print("\nBoth lists are worth reading in full before stage 11 is re-run gated.")


def cmd_run(args) -> None:
    if LABELS.exists() and not args.relabel:
        print(f"reusing existing labels at {LABELS} (pass --relabel to redo)")
    else:
        cmd_label(args)
    if not args.no_uncertainty:
        cmd_uncertainty(args)
    cmd_apply(args)


# ── report ──────────────────────────────────────────────────────────────────
def write_report(out: pd.DataFrame, labels: pd.DataFrame, args) -> None:
    n = len(out)
    ev = out[out.is_event]
    lines = [
        "# LexisNexis filter — Stage 19", "",
        f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} "
        f"from `{SOURCE_JSONL.relative_to(config.REPO_ROOT)}`.", "",
        "## What went in", "",
        f"- **{n:,} articles**, {labels.shape[0]:,} distinct bodies "
        f"({1 - labels.shape[0] / n:.1%} verbatim wire copy), "
        f"{out.textref_uid.nunique():,} distinct `textref_uid`.",
        f"- {str(out.pub_date.min())[:10]} to {str(out.pub_date.max())[:10]}, "
        f"{out.source.nunique():,} sources.",
        f"- Full body text, median {out.n_words.median():,.0f} words. Evidence sent "
        f"to the model: **{args.mode}** (see the window ablation).", "",
        "## What came out", "",
        f"- **{len(ev):,} articles labelled `EVENT`** ({len(ev) / n:.1%}), "
        f"{ev.body_key.nunique():,} distinct bodies. These are the articles stage 11 "
        "links; everything else is recorded with its reason and skipped.", "",
        "| primary label | articles | share |", "|---|---:|---:|",
    ]
    for label, cnt in out.primary.value_counts().items():
        lines.append(f"| `{label}` | {cnt:,} | {cnt / n:.1%} |")
    lines += ["", "| flag | articles | share |", "|---|---:|---:|"]
    for flag in lf.FLAGS:
        lines.append(f"| `{flag}` | {out[flag].sum():,} | {out[flag].mean():.1%} |")

    lines += [
        "", "## Method", "",
        "Every distinct article body was labelled by a locally hosted LLM at "
        "temperature 0 and the answer propagated to the articles sharing that "
        "body. Same label vocabulary as stage 18, so the two corpora remain "
        "comparable for the overlap study; the corpus-specific distinctions "
        "(`is_passing_mention`, `is_press_release`, `is_roundup`) are flags, not "
        "primary categories.",
        "",
        f"The decisive question here is *aboutness*: {(out.n_mentions <= 1).mean():.1%} "
        "of articles mention a tornado at most once, and those references are "
        "usually to a real tornado in an article about something else — a "
        "lawsuit, an obituary, a fundraiser. No keyword separates those from a "
        "report, which is why the rules were never given the decision.",
        "",
        "## Limitations", "",
        "1. **No human ground truth.** Every figure is model output. This corpus "
        "is where that should be fixed first: the annotation sheets, the codebook "
        "and the viewer already exist, and `is_passing_mention` plus the low "
        "`modal_share` rows are the strata a sample should concentrate on.",
        "2. **The evidence window bounds what is knowable.** An article whose only "
        "tornado content falls outside the window cannot be labelled on it; the "
        "`window` subcommand measures the size of that effect rather than "
        "assuming it away.",
        "3. **Exact-duplicate detection only.** Bodies are grouped by normalised "
        "identity, the cheap variant of `LexisNexisTools::lnt_similarity`, so "
        "lightly edited wire copy is counted as distinct.",
        "4. **Gating is one-directional.** Once stage 11 runs gated, filtered "
        "articles are not linked and a filter false negative becomes invisible. "
        "The `crosstab` subcommand is the only check on this, and only while "
        "stage 11's ungated run is still on disk.",
        "5. **The corpus is one LexisNexis query's complete export** — 22,896 "
        "unique articles, not truncated — but not a census of coverage: it is "
        "bounded by which outlets LexisNexis indexes and by the query terms.", "",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")


# ── CLI ─────────────────────────────────────────────────────────────────────
def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp, llm: bool = True):
        sp.add_argument("--limit", type=int, help="only read the first N articles")
        sp.add_argument("--tag", default=None,
                        help="suffix for this run's output files; use one for smoke "
                             "tests so they cannot overwrite a real run")
        sp.add_argument("--random-seed", type=int, default=20260807)
        sp.add_argument("--uncertainty-frac", type=float, default=0.10)
        sp.add_argument("--k", type=int, default=3)
        sp.add_argument("--mode", default="windows", choices=lf.EVIDENCE_MODES,
                        help="evidence sent to the model (default: windows)")
        if llm:
            sp.add_argument("--api-base", default=None)
            sp.add_argument("--model", default=None,
                            help="served model id (default: ask the server)")
            sp.add_argument("--concurrency", type=int, default=32)
            sp.add_argument("--thinking", action="store_true")

    for name, fn, helptext in [
        ("profile", cmd_profile, "corpus shape and cue coverage; no LLM"),
        ("window", cmd_window, "compare evidence modes on a sample"),
        ("label", cmd_label, "label every distinct body at T=0"),
        ("uncertainty", cmd_uncertainty, "k draws at T=1 on a random subset"),
        ("apply", cmd_apply, "propagate, guard, write the article table"),
        ("crosstab", cmd_crosstab, "compare with stage 11's ungated link_status"),
        ("run", cmd_run, "label, uncertainty and apply"),
    ]:
        sp = sub.add_parser(name, help=helptext)
        common(sp, llm=name not in ("profile", "crosstab"))
        if name == "window":
            sp.add_argument("--window-size", type=int, default=400)
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

#!/usr/bin/env python
"""Stage 18 — filter the Media Cloud export to articles reporting real tornadoes.

Labels all 266,215 distinct headlines with a locally hosted LLM and propagates
each answer to its syndicated copies. There is no rule-based decision stage and
no trained classifier; see :mod:`tornado_dataset.text.mediacloud` for the
measurements that removed them.

Typical run — forward the model's port first, then::

    ssh -N -L 8000:localhost:8000 you@your-server        # in another terminal
    python scripts/18_filter_media_cloud.py profile      # cue coverage, no LLM
    python scripts/18_filter_media_cloud.py run          # label + uncertainty + write

Resumable: every answer is cached on disk by (model, prompt, temperature,
sample), so an interrupted job re-reads what it already paid for.

Subcommands
-----------
profile      audit-cue coverage and corpus shape; no LLM, no model needed
label        label every distinct headline at temperature 0
uncertainty  re-label a random subset k times at temperature 1.0
sensitivity  label one subset across several temperatures (robustness check)
apply        propagate labels, enforce the protect rule, write the dataset
run          label, uncertainty and apply

Why two temperatures
--------------------
Labels are produced at **T=0**: classification wants the argmax, and greedy
decoding is what makes a rerun reproducible. (vLLM is not bitwise deterministic
even at T=0 — continuous batching changes floating-point reduction order — so the
response cache, not the temperature, is what actually guarantees reproducibility.)

Uncertainty is measured at **T=1.0**, the model's unmodified predictive
distribution. Sampling below 1.0 sharpens the very thing being measured, and
*varying* temperature across the k draws would confound the model's uncertainty
with temperature's effect on entropy — the draws would come from different
distributions, so their agreement would estimate nothing well-defined.

Outputs
-------
``data/interim/mediacloud_labels.csv``          one row per distinct headline
``data/interim/mediacloud_consistency.csv``     k-sample agreement on the subset
``data/interim/mediacloud_llm_cache.jsonl``     every raw model answer
``data/processed/mediacloud_filtered.csv.gz``   every row with its final label
``data/processed/mediacloud_events.csv.gz``     the EVENT subset — the deliverable
``outputs/mediacloud_filter_report.md``         what happened, with the numbers
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
from tornado_dataset.text import mediacloud as mc               # noqa: E402

SOURCE_CSV = config.RAW_DIR / "media_cloud" / "national_state_local_2010-2025.csv"

# Output paths are resolved from --tag, the convention the rest of the pipeline
# already uses (`hazards_march2025.csv`, `article_status_2010-…csv`). A smoke
# test therefore cannot write over a real run's results: `--limit` bounds only
# how much of the corpus is *read*, so without a separate tag a test run happily
# reuses a full labels file and then overwrites the processed outputs with a
# fraction of the corpus. That happened once; the tag is the fix.
LABELS = CONSISTENCY = SENSITIVITY = LLM_CACHE = None
FILTERED = EVENTS = REPORT = None


def set_paths(tag: str | None) -> None:
    """Bind the module's output paths for this run's tag."""
    global LABELS, CONSISTENCY, SENSITIVITY, LLM_CACHE, FILTERED, EVENTS, REPORT
    suffix = f"_{tag}" if tag else ""
    LABELS = config.INTERIM_DIR / f"mediacloud_labels{suffix}.csv"
    CONSISTENCY = config.INTERIM_DIR / f"mediacloud_consistency{suffix}.csv"
    SENSITIVITY = config.INTERIM_DIR / f"mediacloud_sensitivity{suffix}.csv"
    # The response cache is keyed by (model, prompt, temperature, sample) and a
    # tagged run asks the same questions, so it shares the untagged cache and
    # inherits every answer already paid for.
    LLM_CACHE = config.INTERIM_DIR / "mediacloud_llm_cache.jsonl"
    FILTERED = config.PROCESSED_DIR / f"mediacloud_filtered{suffix}.csv.gz"
    EVENTS = config.PROCESSED_DIR / f"mediacloud_events{suffix}.csv.gz"
    REPORT = config.OUTPUT_DIR / f"mediacloud_filter_report{suffix}.md"

UNCERTAINTY_TEMPERATURE = 1.0
SENSITIVITY_TEMPERATURES = (0.0, 0.3, 0.7, 1.0)


# ── shared plumbing ─────────────────────────────────────────────────────────
def load_corpus(limit: int | None = None, literal_protect: bool = False) -> pd.DataFrame:
    if not SOURCE_CSV.exists():
        sys.exit(f"missing input: {SOURCE_CSV}\nRun scripts/17_fetch_media_cloud.py first.")
    df = pd.read_csv(SOURCE_CSV, dtype=str, keep_default_na=False)
    if limit:
        df = df.head(limit).copy()
    return mc.add_rule_cues(mc.add_dedup_groups(df), literal_protect=literal_protect)


def make_client(args) -> LLMClient:
    client = LLMClient(api_base=args.api_base, model=args.model, cache_path=LLM_CACHE,
                       concurrency=args.concurrency, thinking=args.thinking)
    print(f"  LLM: {client.model} @ {client.api_base} "
          f"(concurrency {client.concurrency}, thinking={client.thinking})")
    return client


def run_llm(client: LLMClient, rows: pd.DataFrame, desc: str, provenance: bool,
            temperature: float | None = None, variant: str = "") -> pd.DataFrame:
    prompts = mc.build_prompts(rows, provenance=provenance)
    before = dict(client.stats)          # stats accumulate across passes
    update, close = iter_progress(len(prompts), desc)
    answers = client.complete_many(prompts, system=mc.LLM_SYSTEM,
                                   max_tokens=640 if client.thinking else 160,
                                   schema=mc.LLM_SCHEMA, progress=update,
                                   temperature=temperature, variant=variant)
    close()
    parsed = mc.parse_llm_answers(answers)
    parsed.index = rows.index
    bad = int((~parsed["parsed"]).sum())
    delta = {k: client.stats[k] - before.get(k, 0) for k in client.stats}
    print(f"  cached {delta['cached']:,} | called {delta['called']:,} "
          f"| failed {delta['failed']:,} | unparseable {bad:,}")
    if bad:
        print(f"  note: {bad:,} rows had no usable answer and are recorded UNCLEAR "
              "with parsed=False — they are not counted as judgements.")
    return parsed


def require(path: Path, what: str) -> pd.DataFrame:
    """Read a table back, restoring the dtypes a CSV round-trip flattens.

    ``keep_default_na=False`` is needed so a headline of "NA" or "null" survives
    as text, but it also turns an empty ``conf`` into ``""`` and the flags into
    strings — both of which fail silently later (a string ``"False"`` is truthy).
    """
    if not path.exists():
        sys.exit(f"missing {path} — run the `{what}` subcommand first.")
    df = pd.read_csv(path, keep_default_na=False, dtype={"title": str, "url": str})
    for col in [*mc.FLAGS, "parsed", "protected", "is_representative"]:
        if col in df.columns and df[col].dtype == object:
            df[col] = df[col].astype(str).str.lower().isin(("true", "1"))
    for col in ("conf", "modal_share"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# ── profile ─────────────────────────────────────────────────────────────────
def cmd_profile(args) -> None:
    df = load_corpus(args.limit, args.literal_protect)
    reps = df[df.is_representative]
    print(f"\nrows {len(df):,} | distinct headlines {len(reps):,} "
          f"({1 - len(reps) / len(df):.1%} redundant)")
    print(f"date range {df.publish_date.min()} .. {df.publish_date.max()} "
          f"| outlets {df.media_name.nunique():,}")
    non_en = (df.language != "en").sum()
    print(f"non-English rows {non_en:,} ({non_en / len(df):.2%}) — flagged, not dropped; "
          "the prompt and cues assume English")

    print(f"\nprotect rule (guards the nonmet_sense flag)")
    print(f"  protected              {reps.protected.sum():>8,}  ({reps.protected.mean():.1%})")
    print(f"  ...only via a synonym  {reps.protect_via_synonym.sum():>8,}"
          "   (twister/funnel cloud/EF-n; --literal-protect drops these)")

    print("\naudit cues over distinct headlines (descriptive only — these decide nothing)")
    for col in [c for c in reps.columns if c.startswith("cue_")]:
        print(f"  {col:<22}{reps[col].sum():>8,}  ({reps[col].mean():>5.1%})")

    print(f"\nLLM workload: {len(reps):,} calls at T=0"
          f"\n  + {int(len(reps) * args.uncertainty_frac):,} rows x {args.k} samples "
          f"at T={UNCERTAINTY_TEMPERATURE} for the uncertainty estimate")


# ── label ───────────────────────────────────────────────────────────────────
def cmd_label(args) -> pd.DataFrame:
    df = load_corpus(args.limit, args.literal_protect)
    reps = df[df.is_representative].copy()
    print(f"\nlabelling {len(reps):,} distinct headlines at temperature 0"
          f"{' (with provenance note)' if args.provenance else ''}")

    client = make_client(args)
    parsed = run_llm(client, reps, "labelling", args.provenance, temperature=0.0)
    out = pd.concat([reps, parsed], axis=1)

    coerced = mc.enforce_protect_invariant(out)
    if coerced:
        print(f"\nprotect rule overruled the model on {coerced:,} headlines it flagged "
              "nonmet_sense despite a protected weather term")

    LABELS.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(LABELS, index=False)
    print(f"\nwrote {LABELS} ({len(out):,} rows)")
    print("\nprimary label distribution")
    for lab, n in out.primary.value_counts().items():
        print(f"  {lab:<20}{n:>8,}  ({n / len(out):>5.1%})")
    print("\nflags")
    for flag in mc.FLAGS:
        print(f"  {flag:<20}{out[flag].sum():>8,}  ({out[flag].mean():>5.1%})")
    return out


# ── uncertainty ─────────────────────────────────────────────────────────────
def cmd_uncertainty(args) -> None:
    labels = require(LABELS, "label")
    rng = np.random.default_rng(args.random_seed)
    n = max(1, int(round(len(labels) * args.uncertainty_frac)))
    # A simple random sample, so the headline figure is an unbiased estimate of
    # corpus-wide instability with no reweighting needed. With only four primary
    # labels every one of them is well represented at this size.
    idx = rng.choice(labels.index, size=min(n, len(labels)), replace=False)
    subset = labels.loc[idx].copy()
    print(f"\nre-labelling {len(subset):,} headlines ({args.uncertainty_frac:.0%} of "
          f"{len(labels):,}) {args.k}x at temperature {UNCERTAINTY_TEMPERATURE}")

    client = make_client(args)
    draws = []
    for i in range(args.k):
        parsed = run_llm(client, subset, f"sample {i + 1}/{args.k}", args.provenance,
                         temperature=UNCERTAINTY_TEMPERATURE, variant=f"sc{i}")
        draws.append(parsed["primary"].rename(f"sample_{i}"))

    scores = mc.consistency_scores(draws)
    scores.index = subset.index
    out = pd.concat([subset[["id", "title", "url", "primary", "conf"]],
                     pd.concat(draws, axis=1), scores], axis=1)
    out["agrees_with_t0"] = out.modal_label == out.primary
    out.to_csv(CONSISTENCY, index=False)

    stable, total = int(out.stable.sum()), len(out)
    lo, hi = wilson_interval(stable, total)
    agree = int(out.agrees_with_t0.sum())
    alo, ahi = wilson_interval(agree, total)
    print(f"\nunanimous across {args.k} draws: {stable:,}/{total:,} = {stable/total:.1%} "
          f"[{lo:.1%}, {hi:.1%}]")
    print(f"T=0 label equals the T=1 modal label: {agree/total:.1%} [{alo:.1%}, {ahi:.1%}]")
    print("\nstability by T=0 label")
    for lab, grp in out.groupby("primary"):
        k = int(grp.stable.sum())
        blo, bhi = wilson_interval(k, len(grp))
        print(f"  {lab:<20}{k:>7,}/{len(grp):<7,} {k/len(grp):>6.1%}  [{blo:.1%}, {bhi:.1%}]")
    print(f"\nwrote {CONSISTENCY}")
    print("Rows with modal_share < 1.0 are the model's own uncertain set — the "
          "population to stratify human annotation on.")


# ── sensitivity ─────────────────────────────────────────────────────────────
def cmd_sensitivity(args) -> None:
    """Does the label distribution move with temperature? Justifies the T=0 choice.

    Distinct from `uncertainty`: this varies temperature *between* passes to ask
    whether our choice sits on a plateau, rather than measuring per-item spread.
    """
    labels = require(LABELS, "label")
    rng = np.random.default_rng(args.random_seed)
    idx = rng.choice(labels.index, size=min(args.sensitivity_size, len(labels)),
                     replace=False)
    subset = labels.loc[idx].copy()
    client = make_client(args)

    frames = {}
    for temp in SENSITIVITY_TEMPERATURES:
        parsed = run_llm(client, subset, f"T={temp}", args.provenance,
                         temperature=temp, variant=f"sens{temp:g}")
        frames[temp] = parsed["primary"].to_numpy()

    table = pd.DataFrame(frames, index=subset.index)
    table.to_csv(SENSITIVITY, index=False)
    print(f"\nlabel distribution by temperature (n={len(subset):,})")
    dist = pd.DataFrame({f"T={t}": pd.Series(v).value_counts(normalize=True)
                         for t, v in frames.items()}).fillna(0.0)
    print((dist * 100).round(1).to_string())
    base = table[SENSITIVITY_TEMPERATURES[0]]
    print("\nagreement with T=0")
    for temp in SENSITIVITY_TEMPERATURES[1:]:
        a = (table[temp] == base).mean()
        print(f"  T={temp}: {a:.1%}")
    print(f"\nwrote {SENSITIVITY}")


# ── apply ───────────────────────────────────────────────────────────────────
def cmd_apply(args) -> None:
    labels = require(LABELS, "label")
    df = load_corpus(args.limit, args.literal_protect)

    # Join on the normalised headline, not on dup_group. Group codes come from
    # factorize order, so they are only meaningful within one read of the corpus
    # — joining on them would silently mismatch if `label` and `apply` ran with
    # different --limit. The normalised headline is content-derived and stable.
    carry = ["primary", "parsed", "conf", *mc.FLAGS]
    mapped = labels.drop_duplicates("title_norm").set_index("title_norm")[carry]
    out = df.join(mapped, on="title_norm")
    out["is_event"] = out.primary == mc.EVENT

    missing = int(out.primary.isna().sum())
    if missing:
        sys.exit(f"{missing:,} rows have no label — `label` was run on a different "
                 "slice of the corpus than `apply`. Re-run both with the same --limit.")

    coerced = mc.enforce_protect_invariant(out)
    leaked = int((out.protected & out.nonmet_sense).sum())
    if leaked:
        sys.exit(f"protect invariant violated on {leaked:,} written rows — refusing to "
                 "write a dataset that contradicts it.")
    print(f"protect invariant holds on all {len(out):,} written rows "
          f"({coerced:,} repaired during propagation)")

    keep = ["id", "publish_date", "title", "url", "media_name", "language",
            "primary", "is_event", *mc.FLAGS, "conf", "parsed",
            "protected", "cue_tornado", "cue_event", "cue_prospect",
            "dup_group", "dup_count", "is_representative"]
    FILTERED.parent.mkdir(parents=True, exist_ok=True)
    out[keep].to_csv(FILTERED, index=False, compression="gzip")
    events = out[out.is_event]
    events[keep].to_csv(EVENTS, index=False, compression="gzip")

    write_report(out, labels, args)
    print(f"\nwrote {FILTERED} ({len(out):,} rows)")
    print(f"wrote {EVENTS} ({len(events):,} rows, "
          f"{events.dup_group.nunique():,} distinct headlines)")
    print(f"wrote {REPORT}")


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
        "# Media Cloud filter — Stage 18", "",
        f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} "
        f"from `{SOURCE_CSV.relative_to(config.REPO_ROOT)}`.", "",
        "## What went in", "",
        f"- **{n:,} rows**, {labels.shape[0]:,} distinct headlines "
        f"({1 - labels.shape[0] / n:.1%} of the export is syndicated copy).",
        f"- {out.publish_date.min()} to {out.publish_date.max()}, "
        f"{out.media_name.nunique():,} outlets.",
        "- Headline and URL only — no body text. Every row mentions a tornado "
        f"somewhere (full-text query), but only {out.cue_tornado.mean():.1%} say so "
        "in the headline or URL, which is all this stage can read.", "",
        "## What came out", "",
        f"- **{len(ev):,} rows labelled `EVENT`** ({len(ev) / n:.1%}), "
        f"{ev.dup_group.nunique():,} distinct headlines.", "",
        "| primary label | rows | share |", "|---|---:|---:|",
    ]
    for lab, cnt in out.primary.value_counts().items():
        lines.append(f"| `{lab}` | {cnt:,} | {cnt / n:.1%} |")

    lines += ["", "| flag | rows | share |", "|---|---:|---:|"]
    for flag in mc.FLAGS:
        lines.append(f"| `{flag}` | {out[flag].sum():,} | {out[flag].mean():.1%} |")

    lines += [
        "", "## Method", "",
        "Every distinct headline was labelled by a locally hosted LLM at "
        "temperature 0, and the answer propagated to its syndicated copies. There "
        "is no rule-based decision stage and no trained classifier: measured "
        "against LLM labels on a stratified sample of 385 headlines, the rules "
        "agreed 93.4% on the event/not decision after post-stratification, but "
        "*missed* ~14,106 headlines the model called events while wrongly calling "
        "~1,615 events — recovering roughly 70% of the event set, to save "
        "inference that a local GPU makes free.",
        "",
        "The regex cues are retained as audit columns (`cue_*`, `protected`) for "
        "stratifying validation and as a drift monitor, but they decide nothing.",
        "",
        "## Limitations", "",
        "1. **Headline and URL only.** An article headlined \"storm\" cannot be "
        "distinguished from one headlined \"tornado\" on the evidence available "
        f"here. `UNCLEAR` ({(out.primary == mc.UNCLEAR).mean():.1%} of rows) is the "
        "model's own estimate of how often that bites; it is a measured stratum, "
        "not a residual.",
        "2. **No human ground truth yet.** Every figure above is the model's "
        "output. Precision and recall against human labels require a blind, "
        "stratified annotation sample that has not been drawn.",
        "3. **`conf` is self-reported** and is not a calibrated probability. Use "
        "the self-consistency `modal_share` from "
        f"`{CONSISTENCY.relative_to(config.REPO_ROOT)}` for uncertainty instead.",
        "4. **Syndicated copies share one label.** Labels are computed per "
        "distinct normalised headline; an outlet-specific edit that changes the "
        "meaning would be missed.",
        "5. **The corpus is not a census.** Media Cloud covers a subset of US "
        "outlets, and per-year row counts vary by more than an order of magnitude "
        "(3,050 in 2010 vs 79,619 in 2019), reflecting collection growth at least "
        "as much as tornado activity.",
        f"6. **{(out.language != 'en').sum():,} non-English rows** were labelled "
        "with an English prompt and should be treated with caution.", "",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")


# ── CLI ─────────────────────────────────────────────────────────────────────
def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp, llm: bool = True):
        sp.add_argument("--limit", type=int, help="only read the first N rows (smoke test)")
        sp.add_argument("--literal-protect", action="store_true",
                        help="apply the protect list verbatim, without the "
                             "twister/funnel-cloud/EF-n extension")
        sp.add_argument("--random-seed", type=int, default=20260807)
        sp.add_argument("--tag", default=None,
                        help="suffix for this run's output files; use one for "
                             "smoke tests so they cannot overwrite a real run")
        sp.add_argument("--uncertainty-frac", type=float, default=0.10)
        sp.add_argument("--k", type=int, default=3, help="self-consistency draws")
        if llm:
            sp.add_argument("--api-base", default=None,
                            help="OpenAI-compatible base URL "
                                 "(default $TORNADO_LLM_BASE or http://127.0.0.1:8000/v1)")
            sp.add_argument("--model", default=None,
                            help="served model id (default: ask the server)")
            sp.add_argument("--concurrency", type=int, default=32)
            sp.add_argument("--thinking", action="store_true",
                            help="let the model reason before answering (slower)")
            sp.add_argument("--provenance", action="store_true",
                            help="add the 'matched a tornado full-text search' note to "
                                 "the prompt; off by default because it biases toward "
                                 "EVENT. Use it to run that ablation.")

    for name, fn, helptext in [
        ("profile", cmd_profile, "audit-cue coverage; no LLM needed"),
        ("label", cmd_label, "label every distinct headline at T=0"),
        ("uncertainty", cmd_uncertainty, "k draws at T=1 on a random subset"),
        ("sensitivity", cmd_sensitivity, "label distribution across temperatures"),
        ("apply", cmd_apply, "propagate, guard, write the dataset"),
        ("run", cmd_run, "label, uncertainty and apply"),
    ]:
        sp = sub.add_parser(name, help=helptext)
        common(sp, llm=(name != "profile"))
        if name == "sensitivity":
            sp.add_argument("--sensitivity-size", type=int, default=1000)
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

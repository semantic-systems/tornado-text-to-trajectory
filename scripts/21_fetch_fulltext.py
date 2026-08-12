#!/usr/bin/env python
"""Stage 21 — retrieve article full text for the Media Cloud corpus.

The Media Cloud export has no body text, which bounds what stage 18 can decide
and leaves 48,741 `EVENT` stories unlinkable, since stage 11 matches toponyms in
the body. This stage fills that in.

``pilot`` runs first and exists to answer one question before any full crawl is
built: **what fraction is actually retrievable, and is the loss random?** It is
not expected to be — 23% of the corpus predates 2016, 40% of URLs are still
``http://``, and whole domains have gone (714 stories sit on ``cbslocal.com``,
long since folded into cbsnews.com). Retrieval will favour large national
outlets with stable URLs over the small local ones that cover local tornadoes,
which is precisely backwards for this dataset. The pilot measures that bias on a
stratified sample so the decision to crawl, and the scope of it, rests on
numbers.

The Media Cloud API is **not** a route: it extracts and indexes article text so
that boolean search can run against it, but its Story Guide states the text "is
not available for download due to copyright restrictions", and the documented
response carries no ``text`` key. Crawling is the only option.

Usage::

    python scripts/21_fetch_fulltext.py pilot            # ~600 URLs, measure
    python scripts/21_fetch_fulltext.py crawl            # the full pass
    python scripts/21_fetch_fulltext.py crawl --retry-failed   # transients only
    python scripts/21_fetch_fulltext.py status           # progress so far

``crawl`` is resumable: every outcome is appended to the store as soon as it is
known, and a restart skips what is already there. Expect it to take **well over
a day** — the archive interval that avoids connection errors is 5 s, serialised
globally, and roughly half the corpus routes through the archive. That is the
price of the difference between ~26,000 and ~41,000 retrieved articles.

Politeness and legality are not optional extras here: ``robots.txt`` is honoured
per domain including ``Crawl-delay``, requests to one domain are serialised, and
nothing circumvents a paywall or a block. See
:mod:`tornado_dataset.text.fulltext` for the §60d UrhG basis on which the
retrieved text may be stored for research.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tornado_dataset import config                              # noqa: E402
from tornado_dataset.dat.evaluate import wilson_interval        # noqa: E402
from tornado_dataset.llm import iter_progress                   # noqa: E402
from tornado_dataset.text import fulltext                       # noqa: E402

MC_LABELS = config.PROCESSED_DIR / "mediacloud_filtered.csv.gz"
PILOT_CSV = config.INTERIM_DIR / "fulltext_pilot.csv"
PILOT_TEXT = config.INTERIM_DIR / "fulltext_pilot_texts.jsonl"
REPORT = config.OUTPUT_DIR / "fulltext_pilot_report.md"
# Append-only, one JSON record per attempted URL, text included. Lives under
# data/raw/ because it is retrieved material, not a derived table.
STORE = config.RAW_DIR / "fulltext" / "retrievals.jsonl"
CRAWL_REPORT = config.OUTPUT_DIR / "fulltext_coverage_report.md"

YEAR_BANDS = [(2010, 2015, "2010-2015"), (2016, 2020, "2016-2020"),
              (2021, 2025, "2021-2025")]


def load_events() -> pd.DataFrame:
    if not MC_LABELS.exists():
        sys.exit(f"missing {MC_LABELS} — run scripts/18_filter_media_cloud.py apply")
    df = pd.read_csv(MC_LABELS, keep_default_na=False, low_memory=False)
    df = df[(df.primary == "EVENT")
            & (df.is_representative.astype(str).str.lower() == "true")].copy()
    df["year"] = pd.to_numeric(df.publish_date.str[:4], errors="coerce")
    counts = df.media_name.value_counts()
    # Domain size matters because it predicts both survival (large outlets keep
    # their URL structure) and paywalls, in opposite directions.
    df["domain_size"] = pd.cut(df.media_name.map(counts), [0, 5, 50, 10**9],
                               labels=["small (≤5)", "medium (6-50)", "large (>50)"])
    df["year_band"] = "other"
    for lo, hi, name in YEAR_BANDS:
        df.loc[df.year.between(lo, hi), "year_band"] = name
    return df


def draw_sample(df: pd.DataFrame, size: int, seed: int) -> pd.DataFrame:
    """Stratified by year band × domain size, equally per cell.

    Equal cells, not proportional: the point is to estimate a rate *within* each
    stratum, and the small/old cells are both the most uncertain and the ones
    that decide whether the crawl is worth building.
    """
    rng = np.random.default_rng(seed)
    cells = [(b, s) for _, _, b in YEAR_BANDS
             for s in ["small (≤5)", "medium (6-50)", "large (>50)"]]
    per_cell = max(10, size // len(cells))
    picks = []
    for band, dsize in cells:
        pool = df[(df.year_band == band) & (df.domain_size == dsize)]
        if pool.empty:
            continue
        take = min(len(pool), per_cell)
        picks.append(pool.iloc[rng.choice(len(pool), size=take, replace=False)])
    out = pd.concat(picks).reset_index(drop=True)
    out["cell"] = out.year_band.astype(str) + " / " + out.domain_size.astype(str)
    return out


def rate_table(frame: pd.DataFrame, by: str, label: str) -> str:
    lines = [f"| {label} | sampled | retrieved | rate | 95% CI |",
             "|---|---:|---:|---:|---|"]
    for key, grp in frame.groupby(by, observed=True):
        ok = int((grp.status == "ok").sum())
        lo, hi = wilson_interval(ok, len(grp))
        lines.append(f"| {key} | {len(grp)} | {ok} | {ok/len(grp):.0%} "
                     f"| [{lo:.0%}, {hi:.0%}] |")
    return "\n".join(lines)


def cmd_pilot(args) -> None:
    events = load_events()
    sample = draw_sample(events, args.size, args.random_seed)
    print(f"population: {len(events):,} EVENT stories, "
          f"{events.media_name.nunique():,} domains")
    print(f"pilot sample: {len(sample):,} URLs across "
          f"{sample.media_name.nunique():,} domains, "
          f"stratified by year band x domain size\n")
    print(sample.groupby(["year_band", "domain_size"], observed=True)
                .size().unstack(fill_value=0).to_string())

    # ── arm B: direct fetch + archive fallback ──────────────────────────────
    print(f"\narm B — direct fetch (robots-aware, {args.workers} domains in flight, "
          f"wayback fallback {'on' if not args.no_wayback else 'off'})")
    items = [{"url": r.url, "publish_date": r.publish_date}
             for r in sample.itertuples()]
    update, close = iter_progress(len(items), "fetching")
    results = fulltext.retrieve_many(items, workers=args.workers,
                                     use_wayback=not args.no_wayback,
                                     timeout=args.timeout, progress=update)
    close()

    rows = pd.DataFrame([r.row() for r in results])
    merged = sample.merge(rows, on="url", how="left")
    merged["status"] = merged.status.fillna("not_attempted")

    PILOT_CSV.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(PILOT_CSV, index=False)
    with PILOT_TEXT.open("w", encoding="utf-8") as fh:
        for r in results:
            if r.status == "ok":
                fh.write(pd.Series({"url": r.url, "via": r.via, "title": r.title,
                                    "n_words": r.n_words, "text": r.text}
                                   ).to_json() + "\n")

    ok = int((merged.status == "ok").sum())
    lo, hi = wilson_interval(ok, len(merged))
    print(f"\n{'=' * 70}\nOVERALL: {ok}/{len(merged)} = {ok/len(merged):.0%} "
          f"[{lo:.0%}, {hi:.0%}]\n{'=' * 70}")
    print("\noutcome breakdown")
    for status, n in merged.status.value_counts().items():
        print(f"  {status:<22}{n:>5,}  ({n/len(merged):>5.0%})")
    got = merged[merged.status == "ok"]
    if len(got):
        print(f"\nroute taken (of the {len(got)} retrieved)")
        for via, n in got.via.value_counts().items():
            print(f"  {via:<22}{n:>5,}  ({n/len(got):>5.0%})")
        print(f"\nextracted length: median {got.n_words.median():,.0f} words, "
              f"p10 {got.n_words.quantile(.1):,.0f}, p90 {got.n_words.quantile(.9):,.0f}")

    print("\nretrieval rate by year band")
    print(rate_table(merged, "year_band", "year band"))
    print("\nretrieval rate by domain size")
    print(rate_table(merged, "domain_size", "domain size"))

    write_report(events, merged, args)
    print(f"\nwrote {PILOT_CSV}\nwrote {PILOT_TEXT}\nwrote {REPORT}")


def write_report(events, merged, args) -> None:
    ok = int((merged.status == "ok").sum())
    lo, hi = wilson_interval(ok, len(merged))
    got = merged[merged.status == "ok"]
    lines = [
        "# Full-text retrieval pilot — Stage 21", "",
        f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}.", "",
        "## Question", "",
        f"The Media Cloud corpus has {len(events):,} distinct `EVENT` stories with "
        "no body text. Retrieving it would let those articles be labelled on the "
        "same evidence as the LexisNexis corpus and, more importantly, make them "
        "**linkable** — stage 11 matches toponyms in the body, so without text they "
        "cannot enter the dataset at all.",
        "",
        "This pilot asks what fraction is retrievable and, since the answer will not "
        "be uniform, where the loss falls.", "",
        "## Result", "",
        f"**{ok} of {len(merged)} = {ok/len(merged):.0%}** [{lo:.0%}, {hi:.0%}] "
        f"retrieved, from a sample stratified by year band × domain size across "
        f"{merged.media_name.nunique():,} domains.", "",
        "### By year band", "", rate_table(merged, "year_band", "year band"), "",
        "### By domain size", "", rate_table(merged, "domain_size", "domain size"), "",
        "### Outcomes", "", "| outcome | n | share |", "|---|---:|---:|",
    ]
    for status, n in merged.status.value_counts().items():
        lines.append(f"| `{status}` | {n:,} | {n/len(merged):.0%} |")
    if len(got):
        lines += ["", "### Route taken", "", "| route | n | share |", "|---|---:|---:|"]
        for via, n in got.via.value_counts().items():
            lines.append(f"| {via} | {n:,} | {n/len(got):.0%} |")
        lines += ["", f"Extracted length: median **{got.n_words.median():,.0f} words** "
                  f"(p10 {got.n_words.quantile(.1):,.0f}, "
                  f"p90 {got.n_words.quantile(.9):,.0f}).", ""]

    lines += [
        "## What this means for the full crawl", "",
        f"- At {ok/len(merged):.0%} overall, a full pass over {len(events):,} stories "
        f"would yield roughly **{int(len(events) * ok / max(len(merged), 1)):,}** "
        "articles with usable text.",
        "- **The loss is not random.** Read the two rate tables above as a coverage "
        "bias statement, not a technical footnote: whatever they show about old and "
        "small-outlet articles carries into every downstream figure computed on the "
        "retrieved subset.",
        "- Retrieval failure and article existence are different things. A story that "
        "cannot be fetched still happened and still appeared; excluding it changes "
        "what the corpus represents.", "",
        "## Method notes", "",
        "- `robots.txt` honoured per domain, including `Crawl-delay`; disallowed URLs "
        "are recorded and never fetched.",
        "- Requests to one domain are serialised; domains run in parallel.",
        "- Paywall teasers and bot-blocks are detected and counted as failures rather "
        "than accepted as short articles — a 180-word 'subscribe to continue' stub "
        "that entered the corpus would be labelled as though it were the article.",
        f"- Extraction by trafilatura, `favor_precision`, minimum "
        f"{fulltext.MIN_ARTICLE_WORDS} words.", "",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def crawl_items(events: pd.DataFrame) -> list[dict]:
    return [{"url": r.url, "publish_date": r.publish_date} for r in events.itertuples()]


def cmd_status(args) -> None:
    """What the store already holds — safe to run while a crawl is going."""
    events = load_events()
    store = fulltext.load_store(STORE)
    items = crawl_items(events)
    done = sum(1 for i in items if i["url"] in store)
    ok = sum(1 for i in items if store.get(i["url"], {}).get("status") == "ok")
    todo = len(fulltext.pending(items, store))
    retry = len(fulltext.pending(items, store, retry_failed=True))
    print(f"population {len(items):,} EVENT stories")
    print(f"  attempted   {done:>8,}  ({done/len(items):.1%})")
    print(f"  retrieved   {ok:>8,}  ({ok/max(done,1):.1%} of attempted)")
    print(f"  never tried {todo:>8,}")
    print(f"  + retryable {retry - todo:>8,}  (transient failures worth a second pass)")
    if store:
        counts = pd.Series([v.get("status", "?") for v in store.values()]).value_counts()
        print("\noutcomes so far")
        for status, n in counts.items():
            print(f"  {status:<26}{n:>8,}  ({n/len(store):>5.1%})")


def cmd_crawl(args) -> None:
    events = load_events()
    if args.limit:
        events = events.head(args.limit)
    fulltext.set_archive_interval(args.archive_interval)

    store = fulltext.load_store(STORE)
    items = crawl_items(events)
    todo = fulltext.pending(items, store, retry_failed=args.retry_failed)
    already = len(items) - len([i for i in items if i["url"] not in store])

    print(f"population {len(items):,} EVENT stories")
    print(f"  already in the store : {already:,}")
    print(f"  to attempt now       : {len(todo):,}"
          f"{' (including retryable failures)' if args.retry_failed else ''}")
    if not todo:
        print("\nnothing to do — the store already covers this population.")
        return
    # Roughly half the corpus routes through the archive, and that half is
    # serialised globally; the direct half parallelises across domains.
    hours = len(todo) * 0.5 * args.archive_interval / 3600
    print(f"  archive interval     : {args.archive_interval:g}s "
          f"(~{hours:.1f}h of archive time alone)")
    print(f"\nresumable: outcomes append to {STORE} as they happen.\n")

    update, close = iter_progress(len(todo), "crawling")
    fulltext.retrieve_many(todo, workers=args.workers,
                           use_wayback=not args.no_wayback, timeout=args.timeout,
                           progress=update, store_path=STORE)
    close()
    cmd_status(args)
    write_coverage_report(events)


def write_coverage_report(events: pd.DataFrame) -> None:
    """Coverage of the crawl so far, by the strata the pilot showed matter."""
    store = fulltext.load_store(STORE)
    if not store:
        return
    rows = pd.DataFrame([{"url": k, "status": v.get("status"), "via": v.get("via"),
                          "n_words": v.get("n_words", 0)} for k, v in store.items()])
    merged = events.merge(rows, on="url", how="inner")
    if merged.empty:
        return
    ok = int((merged.status == "ok").sum())
    lo, hi = wilson_interval(ok, len(merged))
    got = merged[merged.status == "ok"]
    lines = [
        "# Full-text coverage — Stage 21", "",
        f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}.", "",
        f"**{ok:,} of {len(merged):,} attempted** = {ok/len(merged):.1%} "
        f"[{lo:.1%}, {hi:.1%}], out of {len(events):,} `EVENT` stories in the "
        "population.", "",
        "Retrieval failure and article existence are different things. A story that "
        "cannot be fetched still happened and still appeared; excluding it changes "
        "what the corpus represents, so the tables below are a coverage-bias "
        "statement rather than a technical footnote.", "",
        "## By year band", "", rate_table(merged, "year_band", "year band"), "",
        "## By domain size", "", rate_table(merged, "domain_size", "domain size"), "",
        "## Outcomes", "", "| outcome | n | share |", "|---|---:|---:|",
    ]
    for status, n in merged.status.value_counts().items():
        lines.append(f"| `{status}` | {n:,} | {n/len(merged):.1%} |")
    if len(got):
        lines += ["", "## Route", "", "| route | n | share |", "|---|---:|---:|"]
        for via, n in got.via.value_counts().items():
            lines.append(f"| {via} | {n:,} | {n/len(got):.1%} |")
        lines += ["", f"Extracted length: median **{got.n_words.median():,.0f} words** "
                  f"(p10 {got.n_words.quantile(.1):,.0f}, "
                  f"p90 {got.n_words.quantile(.9):,.0f}).", ""]
    lines += [
        "## Method", "",
        "- `robots.txt` honoured per domain including `Crawl-delay`; a domain asking "
        f"for more than {fulltext.MAX_CRAWL_DELAY:g}s yields one article and the rest "
        "are recorded as skipped.",
        "- Requests to one domain are serialised; domains run in parallel; "
        "archive.org is throttled globally because it is one host regardless of "
        "which publisher an article came from.",
        "- Paywall teasers and bot-blocks are counted as failures, not short articles.",
        f"- Extraction by trafilatura, minimum {fulltext.MIN_ARTICLE_WORDS} words.",
        "- Text is stored locally for TDM under §60d UrhG; the published dataset "
        "carries links and derived annotations only.", "",
    ]
    CRAWL_REPORT.parent.mkdir(parents=True, exist_ok=True)
    CRAWL_REPORT.write_text("\n".join(lines), encoding="utf-8")



def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)
    sp = sub.add_parser("pilot", help="measure retrievability on a stratified sample")
    sp.add_argument("--size", type=int, default=600)
    sp.add_argument("--workers", type=int, default=12,
                    help="domains fetched in parallel (requests within a domain "
                         "are always serialised)")
    sp.add_argument("--timeout", type=int, default=20)
    sp.add_argument("--no-wayback", action="store_true")
    sp.add_argument("--random-seed", type=int, default=20260807)
    sp.set_defaults(func=cmd_pilot)

    sp = sub.add_parser("crawl", help="the full, resumable pass")
    sp.add_argument("--limit", type=int)
    sp.add_argument("--workers", type=int, default=14)
    sp.add_argument("--timeout", type=int, default=20)
    sp.add_argument("--archive-interval", type=float, default=fulltext.ARCHIVE_INTERVAL,
                    help="seconds between archive.org requests, globally. 5s is the "
                         "measured rate at which connection errors stop; lower it "
                         "only if you are prepared to lose articles to 429s.")
    sp.add_argument("--retry-failed", action="store_true",
                    help="also re-attempt transient failures already in the store")
    sp.add_argument("--no-wayback", action="store_true")
    sp.add_argument("--random-seed", type=int, default=20260807)
    sp.set_defaults(func=cmd_crawl)

    sp = sub.add_parser("status", help="what the store holds; safe during a crawl")
    sp.add_argument("--random-seed", type=int, default=20260807)
    sp.set_defaults(func=cmd_status)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

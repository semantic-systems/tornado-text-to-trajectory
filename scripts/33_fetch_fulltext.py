#!/usr/bin/env python
"""Stage 33 — retrieve article full text for the Media Cloud corpus.

The Media Cloud export has no body text, which bounds what stage 30 can decide
and leaves 48,741 `EVENT` stories unlinkable, since stage 31 matches toponyms in
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

    python scripts/33_fetch_fulltext.py pilot            # ~600 URLs, measure
    python scripts/33_fetch_fulltext.py crawl            # the full pass
    python scripts/33_fetch_fulltext.py crawl --retry-failed   # transients only
    python scripts/33_fetch_fulltext.py status           # progress so far
    python scripts/33_fetch_fulltext.py report           # coverage report, offline
    python scripts/33_fetch_fulltext.py quality          # text quality, offline
    python scripts/33_fetch_fulltext.py refetch --dry-run   # what the archive could fix
    python scripts/33_fetch_fulltext.py refetch          # archive copies for failed bodies

``crawl`` is resumable: every outcome is appended to the store as soon as it is
known, and a restart skips what is already there. Expect it to take **well over
a day** — the archive interval that avoids connection errors is 5 s, serialised
globally, and roughly half the corpus routes through the archive.

Politeness and legality are not optional extras here: ``robots.txt`` is honoured
per domain including ``Crawl-delay``, requests to one domain are serialised, and
nothing circumvents a paywall or a block. See
:mod:`tornado_dataset.text.fulltext` for the §60d UrhG basis on which the
retrieved text may be stored for research.
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
from tornado_dataset.llm import iter_progress                   # noqa: E402
from tornado_dataset.text import fulltext                       # noqa: E402
from tornado_dataset.text import fulltext_corpus                # noqa: E402

MC_LABELS = config.PROCESSED_DIR / "mediacloud_filtered.csv.gz"
PILOT_CSV = config.INTERIM_DIR / "fulltext_pilot.csv"
PILOT_TEXT = config.INTERIM_DIR / "fulltext_pilot_texts.jsonl"
REPORT = config.OUTPUT_DIR / "fulltext_pilot_report.md"
# Append-only, one JSON record per attempted URL, text included. Lives under
# data/raw/ because it is retrieved material, not a derived table.
STORE = config.RAW_DIR / "fulltext" / "retrievals.jsonl"
CRAWL_REPORT = config.OUTPUT_DIR / "fulltext_coverage_report.md"
QUALITY_CSV = config.INTERIM_DIR / "fulltext_quality.csv"
QUALITY_REPORT = config.OUTPUT_DIR / "fulltext_quality_report.md"
# Every archive re-fetch attempt, successful or not; no text. Lets `refetch`
# resume and skip what is settled without touching the store on failure.
REFETCH_LOG = config.RAW_DIR / "fulltext" / "archive_refetch.jsonl"

YEAR_BANDS = fulltext_corpus.YEAR_BANDS


def load_events() -> pd.DataFrame:
    """The crawl population; shared with stage 34 so the two cannot drift."""
    config.require_data(config.PROCESSED_DIR)
    if not MC_LABELS.exists():
        sys.exit(f"missing {MC_LABELS} — run scripts/30_filter_media_cloud.py apply")
    return fulltext_corpus.load_population(MC_LABELS)


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
        "# Full-text retrieval pilot — Stage 33", "",
        f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}.", "",
        "## Question", "",
        f"The Media Cloud corpus has {len(events):,} distinct `EVENT` stories with "
        "no body text. Retrieving it would let those articles be labelled on the "
        "same evidence as the LexisNexis corpus and, more importantly, make them "
        "**linkable** — stage 31 matches toponyms in the body, so without text they "
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
    log = fulltext.load_refetch_log(REFETCH_LOG)
    if log:
        counts = pd.Series([v.get("outcome", "?") for v in log.values()]).value_counts()
        print(f"\narchive re-fetch of failed direct bodies: {len(log):,} attempted")
        for outcome, n in counts.items():
            print(f"  {outcome:<26}{n:>8,}  ({n/len(log):>5.1%})")


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


def refetch_candidates(events: pd.DataFrame, store: dict,
                       flags: list[str] | None) -> list[dict]:
    """Direct retrievals that fail a hard quality check, as crawl items.

    Read against the *current* store: a record that has since been replaced (by a
    retry or an earlier re-fetch) is no longer a direct body and is skipped, even
    if the quality table predates the change.
    """
    q = fulltext_corpus.load_quality(QUALITY_CSV)
    if q is None:
        sys.exit(f"missing {QUALITY_CSV} — run `quality` first; it decides which "
                 "bodies are worth re-fetching.")
    hard = [f for f in fulltext.HARD_FLAGS if f in q.columns]
    for col in ["quality_ok", *hard]:
        q[col] = q[col].astype(str).str.lower().isin(("true", "1"))
    q = q[~q.quality_ok]
    if flags:
        q = q[q[flags].any(axis=1)]
    published = dict(zip(events.url, events.publish_date))
    items = []
    for row in q.itertuples(index=False):
        rec = store.get(row.url, {})
        if rec.get("status") != "ok" or rec.get("via") != "direct":
            continue
        items.append({"url": row.url, "publish_date": published.get(row.url),
                      "domain": row.domain,
                      "flags": [f for f in hard if getattr(row, f)]})
    return items


def cmd_refetch(args) -> None:
    """Try the archive for direct bodies that fail a hard quality check.

    A successful archive copy is appended to the store and supersedes the direct
    record; a failure is only logged, so the direct body stays the record. Re-run
    `quality` afterwards — the replaced bodies have not been scored yet.
    """
    events = load_events()
    fulltext.set_archive_interval(args.archive_interval)
    store = fulltext.load_store(STORE)
    candidates = refetch_candidates(events, store, args.flags)
    log = fulltext.load_refetch_log(REFETCH_LOG)
    todo = fulltext.refetch_pending(candidates, log)
    if args.limit:
        todo = todo[:args.limit]

    print(f"direct bodies failing a hard check : {len(candidates):,}"
          f"{' (restricted to ' + ', '.join(args.flags) + ')' if args.flags else ''}")
    print(f"  already settled in the re-fetch log: {len(candidates) - len(fulltext.refetch_pending(candidates, log)):,}")
    print(f"  to attempt now                     : {len(todo):,}")
    flag_counts = pd.Series([f for i in todo for f in i["flags"]]).value_counts()
    for flag, n in flag_counts.items():
        print(f"    {flag:<22}{n:>7,}")
    domains = pd.Series([i["domain"] for i in todo]).value_counts().head(8)
    if len(domains):
        print("  largest domains: " + ", ".join(f"{d} {n:,}" for d, n in domains.items()))
    hours = len(todo) * args.archive_interval / 3600
    print(f"  archive interval {args.archive_interval:g}s, serialised -> ~{hours:.1f}h")
    if args.dry_run or not todo:
        print("\ndry run — nothing fetched." if args.dry_run else "\nnothing to do.")
        return

    print(f"\nresumable: successes append to {STORE.name}, every attempt to "
          f"{REFETCH_LOG.name}.\n")
    update, close = iter_progress(len(todo), "archive re-fetch")
    counts = fulltext.refetch_many(todo, store_path=STORE, log_path=REFETCH_LOG,
                                   timeout=args.timeout, progress=update)
    close()
    ok = counts.get("ok", 0)
    print(f"\narchive copy retrieved for {ok:,} of {len(todo):,} "
          f"({ok/len(todo):.1%}); outcomes:")
    for outcome, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {outcome:<34}{n:>7,}")
    print("\nNext: `python scripts/33_fetch_fulltext.py quality` to score the replaced "
          "bodies, then re-run stage 34 — only the new bodies cost model calls.")


def write_coverage_report(events: pd.DataFrame) -> None:
    """Coverage of the crawl so far, by the strata the pilot showed matter."""
    store = fulltext.load_store(STORE)
    if not store:
        return
    rows = pd.DataFrame([{"url": k, "status": v.get("status"), "via": v.get("via"),
                          "n_words": v.get("n_words", 0),
                          "refetched": str(v.get("note", "")).startswith("archive_refetch")}
                         for k, v in store.items()])
    merged = events.merge(rows, on="url", how="inner")
    if merged.empty:
        return
    ok = int((merged.status == "ok").sum())
    lo, hi = wilson_interval(ok, len(merged))
    got = merged[merged.status == "ok"]
    lines = [
        "# Full-text coverage — Stage 33", "",
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
        refetched = int(got.refetched.sum())
        if refetched:
            lines += ["", f"{refetched:,} of the archive copies replaced a direct body "
                      "that had failed a hard quality check (`refetch`)."]
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



def cmd_report(args) -> None:
    """Regenerate the coverage report from the store, without crawling.

    It used to be written only at the end of an uninterrupted `crawl`, so a run
    that was resumed or stopped left the previous report in place.
    """
    events = load_events()
    write_coverage_report(events)
    print(f"wrote {CRAWL_REPORT}")


def cmd_quality(args) -> None:
    """Is each retrieved body the article its headline names?

    Offline: reads only the store and the stage 30 table. Writes a per-article
    table to data/interim/ and a report to outputs/. The report is tracked in
    git, so it names articles by URL and headline only and never quotes a body.
    """
    events = load_events()
    store = fulltext.load_store(STORE)
    print(f"store: {len(store):,} records; scoring the retrieved bodies…")
    q = fulltext.quality_table(store, events)
    if q.empty:
        sys.exit("no retrieved articles in the store — run `crawl` first")
    QUALITY_CSV.parent.mkdir(parents=True, exist_ok=True)
    q.to_csv(QUALITY_CSV, index=False)

    n, good = len(q), int(q.quality_ok.sum())
    lo, hi = wilson_interval(good, n)
    print(f"\nretrieved {n:,} | pass every hard check {good:,} = {good/n:.1%} "
          f"[{lo:.1%}, {hi:.1%}]")
    print(f"usable against the population: {good:,}/{len(events):,} = "
          f"{good/len(events):.1%}\n")
    print("flags (hard flags decide quality_ok; soft flags are informational)")
    for flag in (*fulltext.HARD_FLAGS, *fulltext.SOFT_FLAGS):
        kind = "hard" if flag in fulltext.HARD_FLAGS else "soft"
        print(f"  {kind}  {flag:<20}{int(q[flag].sum()):>7,}  ({q[flag].mean():>5.1%})")
    print(f"\ndistinct bodies {q.body_key.nunique():,} under {q.dup_group.nunique():,} "
          f"distinct headlines")
    write_quality_report(q, events)
    print(f"\nwrote {QUALITY_CSV}\nwrote {QUALITY_REPORT}")


def write_quality_report(q: pd.DataFrame, events: pd.DataFrame) -> None:
    n, good = len(q), int(q.quality_ok.sum())
    lo, hi = wilson_interval(good, n)

    def flag_rows(by: str, label: str) -> list[str]:
        out = [f"| {label} | retrieved | quality ok | rate | 95% CI |",
               "|---|---:|---:|---:|---|"]
        for key, grp in q.groupby(by, observed=True):
            k = int(grp.quality_ok.sum())
            a, b = wilson_interval(k, len(grp))
            out.append(f"| {key} | {len(grp):,} | {k:,} | {k/len(grp):.0%} | "
                       f"[{a:.0%}, {b:.0%}] |")
        return out

    lines = [
        "# Full-text quality — Stage 33", "",
        f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} from "
        f"`{STORE.name}`.", "",
        "> Retrieval `ok` means extraction produced at least "
        f"{fulltext.MIN_ARTICLE_WORDS} words that are not an obvious paywall or bot "
        "wall. This report asks the harder question: **is the body the article the "
        "headline names?** Every check is a flag with a stated threshold, reported "
        "with its rate, rather than a silent filter.", "",
        "## Result", "",
        f"- **{n:,}** bodies retrieved; **{good:,}** pass every hard check "
        f"= **{good/n:.1%}** [{lo:.1%}, {hi:.1%}].",
        f"- Against the {len(events):,} `EVENT` stories crawled, that is "
        f"**{good/len(events):.1%} usable full text**.", "",
        "## Flags", "",
        "| flag | kind | articles | share | what it catches |", "|---|---|---:|---:|---|",
    ]
    meaning = {
        "no_tornado_mention": "Media Cloud's own `tornado*` query matched this page, so a "
                              "correct body should mention one; most often a wrong page or a "
                              "truncated extraction, occasionally a mention trafilatura "
                              "dropped with a caption",
        "title_mismatch": f"retrieved page title shares < {fulltext.TITLE_MISMATCH_CONTAINMENT:.0%} "
                          "of the headline's content words. **Soft**: these bodies mention "
                          "tornadoes more than passing ones — mostly the right article, "
                          "retitled after indexing",
        "redirected_home": "direct fetch landed on the site's front page",
        "template_body": f"one body under ≥{fulltext.TEMPLATE_MIN_HEADLINES} headlines that "
                         "disagree with it *and* never mentions a tornado — an error or "
                         "landing page served for many URLs",
        "not_english": f"English stopword share < {fulltext.MIN_ENGLISH_STOPWORD_SHARE:.0%}",
        "high_boilerplate": f"≥{fulltext.HIGH_BOILERPLATE_SHARE:.0%} of the words are "
                            "paragraphs that recur across most of the domain's pages",
        "very_long": f"≥{fulltext.VERY_LONG_WORDS:,} words — live blogs and page dumps",
    }
    for flag in (*fulltext.HARD_FLAGS, *fulltext.SOFT_FLAGS):
        kind = "hard" if flag in fulltext.HARD_FLAGS else "soft"
        lines.append(f"| `{flag}` | {kind} | {int(q[flag].sum()):,} | "
                     f"{q[flag].mean():.1%} | {meaning[flag]} |")
    lines += ["", "Flags overlap; the shares do not sum to the failure rate.", ""]

    lines += ["## By route", ""] + flag_rows("via", "route") + [""]
    lines += ["## By year band", ""] + flag_rows("year_band", "year band") + [""]
    lines += ["## By domain size", ""] + flag_rows("domain_size", "domain size") + [""]

    body_groups = q.groupby("body_key").dup_group.nunique()
    shared = body_groups[body_groups > 1]
    lines += [
        "## Shared bodies", "",
        f"{q.body_key.nunique():,} distinct bodies sit under {q.dup_group.nunique():,} "
        f"distinct headlines. {len(shared):,} bodies appear under more than one "
        f"headline (largest: {int(body_groups.max()):,}). Media Cloud deduplicates by "
        "*headline*, so syndicated copies retitled by each outlet survive as separate "
        "stories; **count articles by body, not by headline, wherever the text is "
        "what matters.** Shared bodies whose headlines disagree with them are flagged "
        "`template_body` above; the rest are ordinary wire copy.", "",
        "## Length", "",
        f"Median {q.n_words.median():,.0f} words (p10 {q.n_words.quantile(.1):,.0f}, "
        f"p90 {q.n_words.quantile(.9):,.0f}) for all retrieved; median "
        f"{q[q.quality_ok].n_words.median():,.0f} for those passing.", "",
        "## Examples to inspect", "",
        "Five per hard flag, by URL and headline only. Open them before trusting a "
        "threshold.", "",
    ]
    for flag in fulltext.HARD_FLAGS:
        sample = q[q[flag]].sample(min(5, int(q[flag].sum())), random_state=1)
        if not len(sample):
            continue
        lines.append(f"**`{flag}`**")
        lines.append("")
        for r in sample.itertuples():
            lines.append(f"- [{str(r.headline)[:90]}]({r.url})")
        lines.append("")

    lines += [
        "## Limitations", "",
        "1. **Thresholds are judgement, not measurement.** None has been calibrated "
        "against a human check. The per-article table "
        f"(`{QUALITY_CSV.relative_to(config.DATA_DIR.parent) if QUALITY_CSV.is_relative_to(config.DATA_DIR.parent) else QUALITY_CSV.name}`) "
        "carries every raw measure, so a threshold can be moved without re-reading "
        "the bodies.",
        "2. **`no_tornado_mention` has a known false-positive mode**: Media Cloud's "
        "extraction may have kept a caption or related-links box that trafilatura "
        "drops. The examples above are the way to estimate how often.",
        "3. **`title_mismatch` is soft, on evidence.** As a hard flag it rejected "
        "articles whose bodies mentioned tornadoes more often than passing ones: "
        "pages are retitled as stories develop. A flag that removes the most on-topic "
        "text is not measuring what it claims to.",
        "4. **`not_english` also catches video pages** with little prose, not only "
        "foreign-language articles. Both are unusable by the English-only stages "
        "downstream, but they are different reasons.",
        "5. **Boilerplate detection needs volume**: domains with fewer than "
        f"{fulltext.BOILERPLATE_DOMAIN_MIN_DOCS} retrieved pages are never scored.",
        "",
    ]
    QUALITY_REPORT.parent.mkdir(parents=True, exist_ok=True)
    QUALITY_REPORT.write_text("\n".join(lines), encoding="utf-8")


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

    sp = sub.add_parser("report", help="regenerate the coverage report; no network")
    sp.add_argument("--random-seed", type=int, default=20260807)
    sp.set_defaults(func=cmd_report)

    sp = sub.add_parser("refetch", help="archive copies for direct bodies that fail a "
                                       "hard quality check")
    sp.add_argument("--dry-run", action="store_true",
                    help="count and break down the candidates; fetch nothing")
    sp.add_argument("--flags", nargs="+", choices=fulltext.HARD_FLAGS,
                    help="only bodies failing one of these (default: any hard flag)")
    sp.add_argument("--limit", type=int, help="attempt at most N this run")
    sp.add_argument("--timeout", type=int, default=20)
    sp.add_argument("--archive-interval", type=float, default=fulltext.ARCHIVE_INTERVAL)
    sp.add_argument("--random-seed", type=int, default=20260807)
    sp.set_defaults(func=cmd_refetch)

    sp = sub.add_parser("quality", help="is each body the article its headline names? "
                                       "No network")
    sp.add_argument("--random-seed", type=int, default=20260807)
    sp.set_defaults(func=cmd_quality)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

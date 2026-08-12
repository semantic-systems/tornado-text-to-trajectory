#!/usr/bin/env python
"""Stage 22 — one three-way view of the news corpora.

Supersedes the pairwise comparisons in stages 13 and 20, which answered "do these
two overlap" in two different units by two different methods, and could not answer
the question the dataset has to state: **how many distinct tornado stories do we
hold, and what does each source uniquely contribute?**

What this does that a pair cannot:

* **Seven-region membership** — the three "only" regions, the three pairwise
  intersections, and the all-three core.
* **A union computed from connected components**, so a story matched
  transitively (LexisNexis → Media Cloud → GDELT) counts once. Subtracting
  pairwise intersections from a total gets this wrong.
* **Capture–recapture**, which is only possible with overlapping samples: an
  estimate of how much tornado coverage *none* of the three caught.

Everything is counted in one unit — see :data:`tornado_dataset.text.corpora.STORY_UNIT`
— because the corpora natively dedup by body, by title and not at all, and mixing
those produced a published figure comparing URLs against titles.

Usage::

    python scripts/22_corpus_atlas.py                  # all three
    python scripts/22_corpus_atlas.py --corpora lexisnexis mediacloud
    python scripts/22_corpus_atlas.py --events-only    # restrict to EVENT stories

GDELT contributes to the structural figures whether or not it has been labelled;
it is omitted from label-conditioned figures until `scripts/18_filter_media_cloud.py
--source gdelt` has run, rather than having "unlabelled" treated as a label.
"""

from __future__ import annotations

import argparse
import itertools
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tornado_dataset import config                              # noqa: E402
from tornado_dataset.dat.evaluate import wilson_interval        # noqa: E402
from tornado_dataset.text import corpora, matching, overlap     # noqa: E402

EDGES_CSV = STORIES_CSV = REPORT = None
EVENT = "EVENT"


def set_paths(events_only: bool) -> None:
    """Bind outputs to the scope. The two runs answer different questions —
    "what did we collect" and "what is usable" — so they must not share a file.
    """
    global EDGES_CSV, STORIES_CSV, REPORT
    stem = "corpus_atlas_events" if events_only else "corpus_atlas"
    EDGES_CSV = config.INTERIM_DIR / f"{stem}_edges.csv"
    STORIES_CSV = config.INTERIM_DIR / f"{stem}_stories.csv"
    REPORT = config.OUTPUT_DIR / f"{stem}_report.md"


def build(names: list[str], events_only: bool) -> tuple[dict, pd.DataFrame]:
    frames = {}
    for name in names:
        frame = corpora.load(name)
        if events_only:
            if not corpora.is_labelled(frame):
                print(f"  {name}: unlabelled — cannot restrict to EVENT, skipping")
                continue
            frame = frame[frame.primary == EVENT]
        frames[name] = frame
        n_story = frame.story_id.nunique()
        n_native = frame.native_key.nunique()
        print(f"  {name:<12} {len(frame):>8,} rows | {n_story:>8,} stories "
              f"| {n_native:>8,} native units "
              f"| labels {'yes' if corpora.is_labelled(frame) else 'NO'}")

    # The LexisNexis outlet->domain map is learned from bodies, which only the
    # LexisNexis loader has; build it once and reuse for every edge involving it.
    domain_map = {}
    if "lexisnexis" in frames:
        try:
            raw = pd.read_json(config.OUTPUT_DIR / "lexisnexis_articles.jsonl", lines=True)
            domain_map = matching.build_source_domain_map(raw.to_dict("records"))
            print(f"\n  outlet map: {len(domain_map):,} LexisNexis source names -> domains")
        except (FileNotFoundError, ValueError):
            print("\n  outlet map: unavailable (lexisnexis_articles.jsonl missing); "
                  "LexisNexis edges will rely on headline agreement alone")

    print("\nbuilding edges")
    all_edges = []
    for left, right in itertools.combinations(frames, 2):
        edges = corpora.match_edges(frames[left], frames[right], domain_map=domain_map)
        method = edges.method.iloc[0] if len(edges) else "—"
        edges["left_corpus"], edges["right_corpus"] = left, right
        all_edges.append(edges)
        print(f"  {left:>11} x {right:<11} {len(edges):>7,} story edges  ({method})")
    edges = (pd.concat(all_edges, ignore_index=True) if all_edges
             else pd.DataFrame(columns=["left_story", "right_story", "method", "score",
                                        "left_corpus", "right_corpus"]))
    return frames, edges


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpora", nargs="+", default=list(corpora.LOADERS),
                    choices=list(corpora.LOADERS))
    ap.add_argument("--events-only", action="store_true",
                    help="restrict to stories labelled EVENT (drops unlabelled corpora)")
    ap.add_argument("--probe", action="store_true",
                    help="ask GDELT directly whether it holds LexisNexis stories "
                         "our episode queries missed. Rate-limited network calls "
                         "at one per five seconds; the only part that leaves the "
                         "machine.")
    ap.add_argument("--probe-size", type=int, default=60)
    args = ap.parse_args()
    set_paths(args.events_only)
    config.require_data(config.PROCESSED_DIR)

    scope = ("stories labelled EVENT" if args.events_only
             else "all retrieved stories, whatever their label")
    print(f"scope: {scope}")
    print(f"unit: {corpora.STORY_UNIT}\n")
    frames, edges = build(args.corpora, args.events_only)
    if len(frames) < 2:
        sys.exit("need at least two corpora to compare")

    if len(edges):
        hubs = (edges.groupby(["left_corpus", "right_corpus", "right_story"])
                     .left_story.nunique().sort_values(ascending=False))
        big = hubs[hubs > 5]
        if len(big):
            print(f"\n  note: {len(big):,} story pairs where one story matches >5 on the "
                  f"other side (max {hubs.max()}). Components merge transitively, so a "
                  "hub\n        collapses everything it touches into one story. Inspect "
                  f"{EDGES_CSV} if the union looks low.")

    member = corpora.membership(frames, edges)
    names = list(frames)
    total = len(member)

    print("\n" + "=" * 72)
    print("MEMBERSHIP — distinct stories, by which corpora hold them")
    print("=" * 72)
    rows = []
    for r in range(len(names), 0, -1):
        for combo in itertools.combinations(names, r):
            mask = pd.Series(True, index=member.index)
            for n in names:
                mask &= member[n] if n in combo else ~member[n]
            n_stories = int(mask.sum())
            if n_stories:
                rows.append({"region": " + ".join(combo), "stories": n_stories,
                             "share": n_stories / total})
    region = pd.DataFrame(rows).sort_values("stories", ascending=False)
    for r in region.itertuples():
        print(f"  {r.region:<40}{r.stories:>9,}  ({r.share:>5.1%})")
    print(f"  {'UNION (distinct stories)':<40}{total:>9,}")

    print("\nper-corpus contribution")
    for n in names:
        held = int(member[n].sum())
        uniq = int((member[n] & ~member[[c for c in names if c != n]].any(axis=1)).sum())
        print(f"  {n:<12} holds {held:>8,} | unique to it {uniq:>8,} "
              f"({uniq / max(held, 1):>5.1%} of its own)")

    # ── label agreement, for every pair where both sides are labelled ──────
    labelled = [n for n in names if corpora.is_labelled(frames[n])]
    if len(labelled) >= 2 and len(edges) and not args.events_only:
        print("\n" + "=" * 72)
        print("LABEL AGREEMENT ON SHARED STORIES")
        print("=" * 72)
        print("  The same story, labelled twice from different evidence and without")
        print("  either run seeing the other. Not ground truth, but unlike a")
        print("  self-consistency figure it is not the model agreeing with itself")
        print("  under identical conditions.\n")
        story_label = {n: (frames[n].drop_duplicates("story_id")
                                    .set_index("story_id").primary)
                       for n in labelled}
        for a, b in itertools.combinations(labelled, 2):
            sub = edges[((edges.left_corpus == a) & (edges.right_corpus == b))
                        | ((edges.left_corpus == b) & (edges.right_corpus == a))]
            if not len(sub):
                continue
            left = sub.apply(lambda r: r.left_story if r.left_corpus == a
                             else r.right_story, axis=1)
            right = sub.apply(lambda r: r.right_story if r.right_corpus == b
                              else r.left_story, axis=1)
            pairs = pd.DataFrame({a: left.map(story_label[a]),
                                  b: right.map(story_label[b])}).dropna()
            pairs = pairs[(pairs[a] != "") & (pairs[b] != "")]
            if not len(pairs):
                continue
            agree = (pairs[a] == pairs[b])
            lo, hi = wilson_interval(int(agree.sum()), len(pairs))
            print(f"  {a} x {b}: {agree.sum():,}/{len(pairs):,} = {agree.mean():.1%} "
                  f"[{lo:.1%}, {hi:.1%}]")
            print("  " + pd.crosstab(pairs[a], pairs[b]).to_string().replace("\n", "\n  "))
            print()

    # ── capture–recapture, on the pair that shares an identifier ────────────
    print("\n" + "=" * 72)
    print("CAPTURE–RECAPTURE — how much did all three miss?")
    print("=" * 72)
    for a, b in itertools.combinations(names, 2):
        n1, n2 = int(member[a].sum()), int(member[b].sum())
        m = int((member[a] & member[b]).sum())
        est, se = corpora.lincoln_petersen(n1, n2, m)
        if est == est:      # not NaN
            print(f"  {a} x {b}: N̂ = {est:,.0f} ± {se:,.0f}  "
                  f"(observed together {n1 + n2 - m:,})")
    print("  NOT a population estimate. The estimator assumes one shared sampling")
    print("  frame, and these three have partly disjoint ones — Media Cloud is US web,")
    print("  GDELT is a different index from 2017 only, LexisNexis adds wire, print and")
    print("  broadcast that neither web corpus can hold. Small overlap then reflects how")
    print("  differently the corpora were built, not how much coverage exists, and it")
    print("  sends N̂ toward infinity. Read the spread between pairs, not the values.")

    # ── structural context ─────────────────────────────────────────────────
    print("\ncoverage by year (a corpus absent from a year cannot overlap in it)")
    years = pd.DataFrame({n: pd.to_datetime(f.date, errors="coerce").dt.year.value_counts()
                          for n, f in frames.items()}).fillna(0).astype(int).sort_index()
    print("  " + years.to_string().replace("\n", "\n  "))

    if "lexisnexis" in frames:
        print("\nLexisNexis reachability by outlet class "
              "(a transcript has no URL for a web corpus to index)")
        lx = frames["lexisnexis"].copy()
        lx["klass"] = lx.outlet.map(overlap.classify_source)
        matched = set(edges.loc[edges.left_corpus == "lexisnexis", "left_story"]) | \
                  set(edges.loc[edges.right_corpus == "lexisnexis", "right_story"])
        for klass, grp in lx.groupby("klass"):
            stories = set(grp.story_id)
            hit = len(stories & matched)
            lo, hi = wilson_interval(hit, max(len(stories), 1))
            print(f"  {klass:<24}{hit:>6,}/{len(stories):<7,} {hit/max(len(stories),1):>6.1%}"
                  f"  [{lo:.1%}, {hi:.1%}]")

    if args.probe and "lexisnexis" in frames and "gdelt" in frames:
        print("\n" + "=" * 72)
        print(f"INDEX PROBE — is an unmatched story in GDELT's index at all?")
        print("=" * 72)
        matched_lx = set(edges.loc[edges.left_corpus == "lexisnexis", "left_story"]) | \
                     set(edges.loc[edges.right_corpus == "lexisnexis", "right_story"])
        lx = frames["lexisnexis"]
        unmatched = [{"headline": r.title, "date": r.date.date() if pd.notna(r.date) else None,
                      "domain": ""} for r in lx[~lx.story_id.isin(matched_lx)].itertuples()]
        result = overlap.level2_probe(unmatched, cache_dir=config.RAW_DIR / "gdelt_probe",
                                      sample_size=args.probe_size)
        print(f"  in the index anyway: {result['in_index']}/{result['sampled']} "
              f"({result['in_index'] / max(result['sampled'], 1):.0%})")
        print("  A story found here was retrievable and our episode query missed it —")
        print("  that separates a retrieval gap from an index gap. Refused probes are")
        print("  counted separately and never read as 'not in GDELT'.")

    EDGES_CSV.parent.mkdir(parents=True, exist_ok=True)
    edges.to_csv(EDGES_CSV, index=False)
    member.to_csv(STORIES_CSV, index=False)
    write_report(frames, edges, member, region, total, args)
    print(f"\nwrote {EDGES_CSV}\nwrote {STORIES_CSV}\nwrote {REPORT}")


def write_report(frames, edges, member, region, total, args) -> None:
    names = list(frames)
    lines = [
        "# Corpus atlas — the three news corpora as a set", "",
        f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}.", "",
        ("> **Scope: stories labelled `EVENT` only.** These are the articles that "
         "report a tornado actually occurring — the usable corpus. For what was "
         "*collected* regardless of label, see `corpus_atlas_report.md`."
         if args.events_only else
         "> **Scope: every retrieved story, whatever its label.** This describes "
         "what was collected, not what is usable. For the tornado-event subset — "
         "usually the more relevant view — see `corpus_atlas_events_report.md`."), "",
        f"**Unit: {corpora.STORY_UNIT}.** The corpora natively deduplicate by body "
        "(LexisNexis), by title (Media Cloud) and not at all (GDELT); comparing "
        "them in their native units produced a published figure that measured "
        "URLs against titles. Every number here uses the one unit all three can "
        "produce. Native counts are kept in the table below for within-corpus use.", "",
        "## What went in", "",
        "| corpus | rows | stories | native units | labelled |",
        "|---|---:|---:|---:|---|",
    ]
    for n, f in frames.items():
        lines.append(f"| {n} | {len(f):,} | {f.story_id.nunique():,} | "
                     f"{f.native_key.nunique():,} | "
                     f"{'yes' if corpora.is_labelled(f) else '**no**'} |")

    lines += ["", "## How many distinct stories", "",
              "| region | stories | share |", "|---|---:|---:|"]
    for r in region.itertuples():
        lines.append(f"| {r.region} | {r.stories:,} | {r.share:.1%} |")
    lines += [f"| **union** | **{total:,}** | 100% |", "",
              "The union is the number of **connected components** of the match "
              "graph, not a sum minus pairwise intersections. Matching is "
              "many-to-many and transitive across three corpora, so a story "
              "reached through an intermediate corpus must count once.", ""]

    lines += ["## Method per edge", "", "| pair | edges | method |", "|---|---:|---|"]
    if len(edges):
        for (l, r), grp in edges.groupby(["left_corpus", "right_corpus"]):
            lines.append(f"| {l} × {r} | {len(grp):,} | `{grp.method.iloc[0]}` |")
    lines += ["", "Exact-URL and inferred edges are **not comparable** and are never "
              "pooled. Media Cloud and GDELT both publish URLs, so their identity is "
              "read directly. LexisNexis publishes none, so its edges are inferred "
              "from headline, date and outlet — strictly weaker, and a lower bound.", ""]

    lines += ["## Limitations", "",
              "1. **Overlap is a lower bound, the union an upper bound.** Rewritten "
              "headlines and outlets absent from one collection cannot match.",
              "2. **The corpora have different frames.** GDELT holds nothing before "
              "2017-01-01; Media Cloud covers US national/state/local collections; "
              "the LexisNexis export includes wire services, broadcast transcripts "
              "and non-US outlets that neither web corpus sampled.",
              "3. **Capture–recapture is reported but not usable as a population "
              "estimate.** It assumes one shared sampling frame; these three have "
              "partly disjoint frames, so the small overlaps reflect how differently "
              "the corpora were built rather than how much coverage exists, and they "
              "send the estimate toward infinity. The spread between pairs is "
              "informative; the values are not.",
              "5. **Transitive merging can over-collapse.** A story matching many on "
              "the other side pulls all of them into one component. The run prints a "
              "hub count; large hubs usually mean a template URL or a generic "
              "headline, not one very widely syndicated story.",
              "4. **Labels are model output** and, for the corpora that have them, "
              "unvalidated against humans.", ""]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()

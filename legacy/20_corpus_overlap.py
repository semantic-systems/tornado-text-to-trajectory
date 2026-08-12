#!/usr/bin/env python
"""Stage 20 — how much do the LexisNexis and Media Cloud corpora overlap?

Answers two questions the dataset has to state:

1. **How many distinct tornado-event news articles do we actually have?** The two
   corpora were collected independently — LexisNexis Uni full-text exports and
   Media Cloud's US national/state/local collections — so their union is the
   dataset's news layer, and their intersection is double counting.
2. **Do the two labellings agree on the stories they share?** A story present in
   both was labelled twice from *different evidence*: stage 19 read the article
   body, stage 18 saw only a headline and URL. Where they disagree, the gap
   measures what headline-only labelling costs — an independent check that
   neither corpus's self-consistency figure can provide.

Matching reuses :mod:`tornado_dataset.text.matching`, built for the LexisNexis ↔
GDELT study: same-day-±3 blocking, content-token title similarity, and an outlet
identity map learned from the LexisNexis bodies that print their own URL. Media
Cloud rows carry ``url`` / ``title`` / ``media_name`` / ``publish_date``, which is
the same shape the GDELT side had.

**The overlap is a lower bound and the union an upper bound.** LexisNexis has no
URLs and Media Cloud has no bodies, so the only evidence linking a pair is the
headline, the date and the outlet. Two desk edits of one wire story do not match,
and an outlet in one collection but not the other cannot match at all. The report
quantifies both effects rather than leaving them implicit.

Usage::

    python scripts/20_corpus_overlap.py                    # both corpora, EVENT-focused
    python scripts/20_corpus_overlap.py --all-labels       # match regardless of label
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tornado_dataset import config                              # noqa: E402
from tornado_dataset.dat.evaluate import wilson_interval        # noqa: E402
from tornado_dataset.text import matching, overlap              # noqa: E402
from tornado_dataset.text import lexisnexis_filter as lf        # noqa: E402
from tornado_dataset.text.linking import as_date                # noqa: E402

LEXIS_ARTICLES = config.OUTPUT_DIR / "lexisnexis_articles.jsonl"
LEXIS_LABELS = config.PROCESSED_DIR / "lexisnexis_article_labels.csv"
MC_LABELS = config.PROCESSED_DIR / "mediacloud_filtered.csv.gz"
MATCHES_CSV = config.INTERIM_DIR / "corpus_overlap_matches.csv"
REPORT = config.OUTPUT_DIR / "corpus_overlap_report.md"

EVENT = lf.EVENT


def count_components(pairs: pd.DataFrame) -> int:
    """Distinct stories represented by a bipartite set of matched pairs.

    Matching is many-to-many: one LexisNexis body can match several Media Cloud
    headlines (a story rewritten across editions) and one Media Cloud headline
    can match several LexisNexis bodies. So "shared stories" is neither side's
    count — it is the number of connected components once every matched pair is
    joined, which is what a union of the two corpora actually contains.
    """
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for left, right in zip(pairs.lexis_story, pairs.mc_story):
        a, b = find(f"L{left}"), find(f"M{right}")
        if a != b:
            parent[a] = b
    return len({find(k) for k in parent})


def load_lexis() -> pd.DataFrame:
    """LexisNexis articles with their stage 19 label, one row per textref_uid."""
    for path in (LEXIS_ARTICLES, LEXIS_LABELS):
        if not path.exists():
            sys.exit(f"missing {path}")
    bodies = pd.read_json(LEXIS_ARTICLES, lines=True)
    labels = lf.restore_dtypes(
        pd.read_csv(LEXIS_LABELS, keep_default_na=False, dtype={"headline": str}),
        lf.FLAGS)
    # Bodies are needed only to learn the outlet -> domain map; join them on the
    # body identity the labels already carry.
    bodies["body_key"] = lf.body_key(bodies["body"])
    body_by_key = bodies.drop_duplicates("body_key").set_index("body_key")["body"]
    out = labels.drop_duplicates("textref_uid").copy()
    out["body"] = out.body_key.map(body_by_key).fillna("")
    out["date"] = [as_date(d) for d in
                   pd.to_datetime(out.pub_date, errors="coerce").dt.tz_localize(None)]
    return out


def load_mediacloud() -> pd.DataFrame:
    if not MC_LABELS.exists():
        sys.exit(f"missing {MC_LABELS} — run scripts/18_filter_media_cloud.py apply")
    df = pd.read_csv(MC_LABELS, keep_default_na=False, low_memory=False)
    df["date"] = [as_date(d) for d in
                  pd.to_datetime(df.publish_date, errors="coerce")]
    df["domain"] = df.media_name.astype(str).str.lower().str.removeprefix("www.")
    return df



def load_gdelt() -> pd.DataFrame:
    """GDELT news links, from whatever the last stage-07 run wrote.

    GDELT carries no relevance label — nothing has ever labelled it — so `primary`
    is left empty and label-agreement figures skip this corpus.
    """
    tag = f"{config.WINDOW_START.isoformat()}_{config.WINDOW_END.isoformat()}"
    path = config.PROCESSED_DIR / f"textrefs_news_{tag}.csv"
    if not path.exists():
        sys.exit(f"missing {path} — run scripts/07_fetch_gdelt.py --cache-only")
    df = pd.read_csv(path, keep_default_na=False, low_memory=False)
    df["date"] = [as_date(d) for d in
                  pd.to_datetime(df.published_at, errors="coerce", utc=True).dt.tz_localize(None)]
    df["domain"] = df.url.map(matching.domain_of)
    df["primary"] = ""
    return df


def normalise_url(series: pd.Series) -> pd.Series:
    """Comparable form of a URL: no scheme, no www, no query, no trailing slash."""
    return (series.fillna("").astype(str).str.lower()
                  .str.replace(r"^https?://(www\.)?", "", regex=True)
                  .str.replace(r"[?#].*$", "", regex=True)
                  .str.rstrip("/"))


def url_overlap(left: pd.DataFrame, right: pd.DataFrame,
                left_name: str, right_name: str,
                left_story: str, right_story: str) -> None:
    """Exact-URL comparison, for two corpora that both carry URLs.

    Where both sides have a URL there is no reason to infer identity from titles:
    the URL *is* the identity. This is a different and stricter method than the
    LexisNexis pairing, which has to go through headline, date and outlet because
    LexisNexis publishes no URL — so the two sets of numbers are not comparable
    and the report says which method produced each.
    """
    left = left.assign(_u=normalise_url(left.url))
    right = right.assign(_u=normalise_url(right.url))
    shared = set(left._u) & set(right._u)

    print("\n" + "=" * 74)
    print(f"EXACT URL OVERLAP — {left_name} x {right_name}")
    print("=" * 74)
    for name, frame, story in ((left_name, left, left_story), (right_name, right, right_story)):
        hit = frame[frame._u.isin(shared)]
        n_story = frame[story].nunique() if story in frame.columns else frame._u.nunique()
        hit_story = hit[story].nunique() if story in frame.columns else hit._u.nunique()
        lo, hi = wilson_interval(hit_story, max(n_story, 1))
        print(f"  {name:<12} {hit_story:>7,}/{n_story:<9,} = {hit_story/max(n_story,1):>5.1%} "
              f"[{lo:.1%}, {hi:.1%}]  of its distinct stories")
    print(f"  shared URLs  {len(shared):>7,}")
    print(f"  union (URLs) {len(set(left._u) | set(right._u)):>7,}")

    ld = set(left.domain.str.lower().str.removeprefix("www."))
    rd = set(right.domain.str.lower().str.removeprefix("www."))
    print(f"\n  domains: {left_name} {len(ld):,} | {right_name} {len(rd):,} | "
          f"shared {len(ld & rd):,} | {left_name}-only {len(ld - rd):,} | "
          f"{right_name}-only {len(rd - ld):,}")

    lyr = pd.to_datetime(left.date, errors="coerce").dt.year.value_counts()
    ryr = pd.to_datetime(right.date, errors="coerce").dt.year.value_counts()
    cov = (pd.DataFrame({left_name: lyr, right_name: ryr})
             .fillna(0).astype(int).sort_index())
    print(f"\n  coverage by year (a corpus absent from a year cannot overlap in it)")
    print("  " + cov.to_string().replace("\n", "\n  "))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--all-labels", action="store_true",
                    help="match every article, not only those labelled EVENT in "
                         "at least one corpus (slower; needed for label agreement)")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--pair", default="lexisnexis-mediacloud",
                    choices=["lexisnexis-mediacloud", "gdelt-mediacloud",
                             "lexisnexis-gdelt"],
                    help="which two corpora to compare. The gdelt-mediacloud pair "
                         "is matched on exact URLs, since both carry them; the "
                         "LexisNexis pairs go through headline, date and outlet "
                         "because LexisNexis publishes no URL.")
    args = ap.parse_args()

    if args.pair == "gdelt-mediacloud":
        gd, mc = load_gdelt(), load_mediacloud()
        if args.limit:
            gd, mc = gd.head(args.limit), mc.head(args.limit * 10)
        print(f"GDELT      : {len(gd):,} URLs")
        print(f"Media Cloud: {len(mc):,} rows, {mc.dup_group.nunique():,} distinct headlines")
        gd["story"] = normalise_url(gd.url)   # GDELT has no dedup notion of its own
        url_overlap(gd, mc, "GDELT", "MediaCloud", "story", "dup_group")
        print("\nNo report written for this pair — GDELT carries no relevance "
              "label, so there is no EVENT subset to count or agreement to measure.")
        return
    if args.pair == "lexisnexis-gdelt":
        sys.exit("use scripts/13_overlap_report.py for LexisNexis x GDELT")

    lexis = load_lexis()
    mc = load_mediacloud()
    if args.limit:
        lexis, mc = lexis.head(args.limit), mc.head(args.limit * 10)

    print(f"LexisNexis : {len(lexis):,} articles "
          f"({(lexis.primary == EVENT).sum():,} EVENT)")
    print(f"Media Cloud: {len(mc):,} rows, {mc.dup_group.nunique():,} distinct headlines "
          f"({(mc.primary == EVENT).sum():,} EVENT rows)")

    # Match on everything, so label agreement can be measured on the shared
    # stories. Restricting to EVENT first would condition the agreement estimate
    # on the very thing being tested.
    mapping = matching.build_source_domain_map(lexis.to_dict("records"))
    print(f"\noutlet map: {len(mapping):,} source names -> domains "
          f"({sum(1 for v in mapping.values() if v['evidence'] == 'url_in_body'):,} "
          "learned from URLs printed in article bodies)")

    lexis_records = [{"textref_uid": r.textref_uid, "headline": r.headline,
                      "source": r.source, "date": r.date}
                     for r in lexis.itertuples()]
    mc_records = [{"url": r.url, "title": r.title, "domain": r.domain, "date": r.date}
                  for r in mc.itertuples()]

    print("\nmatching (±3 days, content-token title similarity, outlet identity)…")
    # Matching runs on *rows*, deliberately: syndicated copies of one story carry
    # slightly different dates, and matching each of them gives the ±3-day window
    # more chances to connect. Counting then collapses to stories — see below.
    #
    # `overlap.level1` is not reused here. Its denominators are the number of
    # LexisNexis articles and the number of distinct GDELT URLs, which was right
    # for GDELT (one URL per story, no syndication dedup) but wrong for Media
    # Cloud: 491,432 rows collapse to 266,258 distinct headlines, so a URL-level
    # rate counts one wire story once per outlet that ran it.
    raw = matching.match_pairs(lexis_records, mc_records, mapping)
    matches = pd.DataFrame(raw)
    if matches.empty:
        sys.exit("no matches found — check the date parsing on both sides")

    matches = matches.rename(columns={"gdelt_url": "mc_url", "gdelt_title": "mc_title",
                                      "gdelt_domain": "mc_domain",
                                      "gdelt_date": "mc_date"})
    # Collapse both sides to their story identity: LexisNexis groups by body,
    # Media Cloud by normalised headline. These are the only units in which
    # "how many articles do we have" has an answer that is not inflated by
    # syndication.
    uid_to_story = lexis.drop_duplicates("textref_uid").set_index("textref_uid").body_key
    url_to_story = mc.drop_duplicates("url").set_index("url").dup_group
    matches["lexis_story"] = matches.textref_uid_lexis.map(uid_to_story)
    matches["mc_story"] = matches.mc_url.map(url_to_story)
    MATCHES_CSV.parent.mkdir(parents=True, exist_ok=True)
    matches.to_csv(MATCHES_CSV, index=False)

    # ── the headline numbers, all at story level ────────────────────────────
    lx_story = lexis.drop_duplicates("body_key").set_index("body_key").primary
    mc_story = mc.drop_duplicates("dup_group").set_index("dup_group").primary

    lx_total = lexis.body_key.nunique()
    mc_total = mc.dup_group.nunique()
    matched_lx = set(matches.lexis_story.dropna())
    matched_mc = set(matches.mc_story.dropna())

    lx_event = set(lx_story.index[lx_story == EVENT])
    mc_event = set(mc_story.index[mc_story == EVENT])

    # A shared *event* story: matched, and labelled EVENT on both sides.
    ev_pairs = matches[matches.lexis_story.isin(lx_event) & matches.mc_story.isin(mc_event)]
    shared_event = set(ev_pairs.lexis_story)
    shared_event_mc = set(ev_pairs.mc_story)
    # The match is many-to-many — one LexisNexis body can match several Media
    # Cloud headlines and vice versa — so neither side's count is the number of
    # real-world stories they represent, and subtracting either one from the
    # total would still double-count. The distinct stories in the shared region
    # are the connected components of the bipartite match graph.
    n_components = count_components(ev_pairs)

    print("\n" + "=" * 74)
    print("OVERLAP  (distinct stories, not rows — syndicated copies collapsed)")
    print("=" * 74)
    lo, hi = wilson_interval(len(matched_lx), lx_total)
    print(f"  LexisNexis bodies with a Media Cloud counterpart  : "
          f"{len(matched_lx):,}/{lx_total:,} = {len(matched_lx)/lx_total:.1%} "
          f"[{lo:.1%}, {hi:.1%}]")
    mlo, mhi = wilson_interval(len(matched_mc), mc_total)
    print(f"  Media Cloud headlines with a LexisNexis counterpart: "
          f"{len(matched_mc):,}/{mc_total:,} = {len(matched_mc)/mc_total:.1%} "
          f"[{mlo:.1%}, {mhi:.1%}]")
    print(f"  (row level, for comparison: {matches.mc_url.nunique():,} Media Cloud URLs "
          f"— inflated by syndication, not a story count)")

    print("\n" + "=" * 74)
    print("DISTINCT TORNADO-EVENT ARTICLES")
    print("=" * 74)
    print(f"  LexisNexis EVENT (distinct bodies)     {len(lx_event):>8,}")
    print(f"  Media Cloud EVENT (distinct headlines) {len(mc_event):>8,}")
    print(f"  Shared region: {len(shared_event):,} LexisNexis bodies <-> "
          f"{len(shared_event_mc):,} Media Cloud headlines,")
    print(f"                 which are {n_components:,} distinct stories "
          "(connected components)")
    union_stories = (len(lx_event) - len(shared_event)) + \
                    (len(mc_event) - len(shared_event_mc)) + n_components
    print(f"  UNION                                  {union_stories:>8,}   <- the answer")
    print("    Upper bound: matching sees only headline, date and outlet, so two desk")
    print("    edits of one wire story stay separate. The true figure is lower.")

    # ── label agreement on shared stories ───────────────────────────────────
    # One pair per LexisNexis story: its highest-scoring Media Cloud counterpart.
    # Without this a wire story matching 200 outlet copies would contribute 200
    # rows to the agreement estimate and swamp everything else.
    best = (matches.sort_values("jaccard", ascending=False)
                   .drop_duplicates("lexis_story"))
    if not best.empty:
        pairs = pd.DataFrame({
            "lexis": best.lexis_story.map(lx_story).to_numpy(),
            "mediacloud": best.mc_story.map(mc_story).to_numpy(),
        }).dropna()
        agree = (pairs.lexis == pairs.mediacloud)
        alo, ahi = wilson_interval(int(agree.sum()), len(pairs))
        print("\n" + "=" * 74)
        print("LABEL AGREEMENT ON SHARED STORIES")
        print("=" * 74)
        print(f"  same primary label: {agree.sum():,}/{len(pairs):,} = {agree.mean():.1%} "
              f"[{alo:.1%}, {ahi:.1%}]")
        print("  (stage 19 read the body; stage 18 saw only headline + URL, so this"
              "\n   measures what headline-only evidence costs)\n")
        print(pd.crosstab(pairs.lexis, pairs.mediacloud).to_string())
        ln_ev_mc_not = int(((pairs.lexis == EVENT) & (pairs.mediacloud != EVENT)).sum())
        mc_ev_ln_not = int(((pairs.mediacloud == EVENT) & (pairs.lexis != EVENT)).sum())
        print(f"\n  body says EVENT, headline does not: {ln_ev_mc_not:,}")
        print(f"  headline says EVENT, body does not: {mc_ev_ln_not:,}")

    # Where overlap is even possible, per outlet class — also at story level.
    lx_reps = lexis.drop_duplicates("body_key")
    by_class: dict[str, dict[str, int]] = {}
    for row in lx_reps.itertuples():
        klass = overlap.classify_source(row.source)
        bucket = by_class.setdefault(klass, {"stories": 0, "matched": 0})
        bucket["stories"] += 1
        bucket["matched"] += int(row.body_key in matched_lx)
    print("\nwhere overlap is possible, by outlet class (distinct LexisNexis bodies)")
    for klass, bucket in sorted(by_class.items(), key=lambda kv: -kv[1]["stories"]):
        print(f"  {klass:<24}{bucket['matched']:>6,}/{bucket['stories']:<7,} "
              f"{bucket['matched']/max(bucket['stories'],1):>6.1%}")

    write_report(lexis, mc, matches, by_class, lx_total, mc_total, matched_lx,
                 matched_mc, lx_event, mc_event, shared_event, shared_event_mc,
                 n_components, union_stories, pairs if not best.empty else None)
    print(f"\nwrote {MATCHES_CSV}")
    print(f"wrote {REPORT}")


def write_report(lexis, mc, matches, by_class, lx_total, mc_total, matched_lx,
                 matched_mc, lx_event, mc_event, shared_event, shared_event_mc,
                 n_components, union_stories, pairs) -> None:
    lines = [
        "# Corpus overlap — LexisNexis × Media Cloud", "",
        f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}.", "",
        "**Every figure below counts distinct stories, never rows.** A wire story "
        "that ran on 200 outlets is one story. On the Media Cloud side that means "
        f"distinct normalised headlines ({mc_total:,}, from {len(mc):,} rows); on "
        f"the LexisNexis side, distinct article bodies ({lx_total:,}, from "
        f"{len(lexis):,} rows).", "",
        "## How many distinct tornado-event news articles are there?", "",
        "| | stories |",
        "|---|---:|",
        f"| LexisNexis `EVENT` (distinct bodies) | {len(lx_event):,} |",
        f"| Media Cloud `EVENT` (distinct headlines) | {len(mc_event):,} |",
        f"| Shared — `EVENT` in both ({len(shared_event):,} LexisNexis bodies ↔ "
        f"{len(shared_event_mc):,} Media Cloud headlines) | {n_components:,} |",
        f"| **Union** | **{union_stories:,}** |", "",
        "The shared row is the number of **connected components** of the match "
        "graph, not either side's count. Matching is many-to-many — one body can "
        "match several headlines and vice versa — so subtracting either side "
        "alone would still double-count.", "",
        "The union is an **upper bound**. Matching uses the headline, the date and "
        "the outlet, because LexisNexis carries no URL and Media Cloud carries no "
        "body — so two desk edits of one wire story remain separate and inflate "
        "the count.", "",
        "## Retrieval overlap", "",
        f"- **{len(matched_lx):,} of {lx_total:,}** LexisNexis stories "
        f"({len(matched_lx)/lx_total:.1%}) have a Media Cloud counterpart.",
        f"- **{len(matched_mc):,} of {mc_total:,}** Media Cloud stories "
        f"({len(matched_mc)/mc_total:.1%}) have a LexisNexis one.", "",
        f"For contrast, the same matches touch {matches.mc_url.nunique():,} Media "
        f"Cloud *URLs* — that figure counts one wire story once per outlet that "
        "ran it and is not a story count.", "",
        "The asymmetry between the two rates is expected: Media Cloud holds "
        f"{mc_total/lx_total:.0f}× more distinct stories, and the two corpora were "
        "built from different sampling frames.", "",
        "### Where overlap is and is not possible", "",
        "| source class | LexisNexis stories | matched | rate |",
        "|---|---:|---:|---:|",
    ]
    for klass, bucket in sorted(by_class.items(), key=lambda kv: -kv[1]["stories"]):
        rate = bucket["matched"] / max(bucket["stories"], 1)
        lines.append(f"| {klass} | {bucket['stories']:,} | {bucket['matched']:,} "
                     f"| {rate:.1%} |")
    lines += [
        "", "Broadcast transcripts and press-release wires have no web article to "
        "match, so a low rate there is a property of the source class rather than a "
        "failure of the matcher.", "",
    ]

    if pairs is not None and len(pairs):
        agree = (pairs.lexis == pairs.mediacloud)
        lo, hi = wilson_interval(int(agree.sum()), len(pairs))
        lines += [
            "## Do the two labellings agree?", "",
            f"On the {len(pairs):,} stories present in both corpora, the primary "
            f"label agrees **{agree.mean():.1%}** of the time [{lo:.1%}, {hi:.1%}].",
            "",
            "This is the most useful validation available so far: the same story was "
            "labelled twice from different evidence — stage 19 read the article body, "
            "stage 18 saw only a headline and a URL — by the same model, with neither "
            "run able to see the other. It is not ground truth, but unlike a "
            "self-consistency figure it is not a measure of the model agreeing with "
            "itself under identical conditions.", "",
            "```",
            pd.crosstab(pairs.lexis, pairs.mediacloud).to_string(),
            "```", "",
        ]

    lines += [
        "## Limitations", "",
        "1. **Matching is a lower bound.** No shared identifier exists; the only "
        "evidence is headline, date and outlet. Rewritten headlines and outlets "
        "absent from one collection cannot match.",
        "2. **The corpora have different frames.** Media Cloud covers US "
        "national/state/local collections; the LexisNexis export includes wire "
        "services, broadcast transcripts and non-US outlets that Media Cloud never "
        "sampled.",
        "3. **Both label sets are model output.** No human ground truth has been "
        "annotated for either corpus, so the agreement figure above bounds "
        "consistency, not correctness.", "",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()

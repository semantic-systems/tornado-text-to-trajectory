"""Stage 13 — how much of the LexisNexis full text is reachable from GDELT?

Two levels, because "is this article in GDELT?" is two questions (see
`text/overlap.py`): whether *our* episode queries returned it, and whether GDELT
holds it at all. Only the second distinguishes a gap in the index from a gap in our
retrieval, and reporting the first alone would flatter our own method.

    python scripts/13_overlap_report.py --news-suffix march2025   # while the sweep runs
    python scripts/13_overlap_report.py --probe                   # includes level 2
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib

import _bootstrap  # noqa: F401

import pandas as pd

from tornado_dataset import config
from tornado_dataset.ids import uid, write_manifest
from tornado_dataset.text import lexisnexis, linking, matching, overlap


def pct(numerator: float, denominator: float) -> str:
    return f"{numerator / denominator:.1%}" if denominator else "n/a"


def main() -> None:
    default_tag = f"{config.WINDOW_START.isoformat()}_{config.WINDOW_END.isoformat()}"
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", default=default_tag)
    parser.add_argument("--news-suffix", default=None)
    parser.add_argument("--probe", action="store_true",
                        help="run the level-2 index probe (rate-limited GDELT queries)")
    parser.add_argument("--probe-size", type=int, default=60)
    args = parser.parse_args()

    articles = pd.read_json(config.OUTPUT_DIR / "lexisnexis_articles.jsonl", lines=True)
    # as_date rather than .dt.date: a missing date must become None, not NaT,
    # which is truthy and would slip past every guard downstream.
    articles["date"] = [linking.as_date(d) for d in
                        pd.to_datetime(articles.pub_date, errors="coerce").dt.tz_localize(None)]

    news_tag = args.news_suffix or args.tag
    news_path = config.PROCESSED_DIR / f"textrefs_news_{news_tag}.csv"
    if not news_path.exists():
        raise SystemExit(f"missing {news_path} — run scripts/07_fetch_gdelt.py, "
                         f"or pass --news-suffix for a pilot file")
    news = pd.read_csv(news_path)
    news["date"] = [linking.as_date(d) for d in
                    pd.to_datetime(news.published_at, errors="coerce", format="ISO8601",
                                   utc=True).dt.tz_localize(None)]

    # The source→domain map is learned from the articles that print their own URL,
    # so most of it comes from the corpus rather than from assertion.
    mapping = matching.build_source_domain_map(articles.to_dict("records"))
    learned = sum(1 for v in mapping.values() if v["evidence"] == "url_in_body")

    lexis_records = [{
        "textref_uid": lexisnexis.textref_uid(row),
        "headline": row.get("headline"), "source": row.get("source"),
        "date": row["date"], "is_duplicate": bool(row.get("is_duplicate")),
        "domain": (mapping.get(str(row.get("source", "")).strip().lower()) or {}).get("domain"),
    } for row in articles.to_dict("records")]
    gdelt_records = [{"url": row.get("url"), "title": row.get("title"),
                      "domain": row.get("source_name"), "date": row["date"]}
                     for row in news.to_dict("records") if row.get("url")]

    print(f"LexisNexis: {len(lexis_records)} articles | GDELT: {len(gdelt_records)} URLs")
    print(f"source→domain map: {len(mapping)} entries ({learned} learned from URLs in bodies)")

    level1 = overlap.level1(lexis_records, gdelt_records, mapping)
    matches = pd.DataFrame(level1["matches"])
    print(f"\nlevel 1 — retrieval overlap")
    print(f"  LexisNexis articles with a GDELT counterpart: {level1['lexis_matched']}"
          f"/{level1['lexis_total']} ({pct(level1['lexis_matched'], level1['lexis_total'])})")
    print(f"  GDELT URLs with a LexisNexis counterpart:     {level1['gdelt_matched']}"
          f"/{level1['gdelt_total']} ({pct(level1['gdelt_matched'], level1['gdelt_total'])})")

    unmatched = [r for r in lexis_records if r["textref_uid"] not in level1["best_per_article"]]
    level2 = None
    if args.probe:
        print(f"\nlevel 2 — probing GDELT directly for {min(args.probe_size, len(unmatched))} "
              f"of {len(unmatched)} unmatched articles (1 query / 5 s) …")
        level2 = overlap.level2_probe(unmatched, cache_dir=config.RAW_DIR / "gdelt_probe",
                                      sample_size=args.probe_size)
        print(f"  found in the index anyway: {level2['in_index']}/{level2['sampled']} "
              f"({pct(level2['in_index'], level2['sampled'])})")

    # ── report ──
    by_class = pd.DataFrame([
        {"source class": klass, "articles": v["articles"], "matched": v["matched"],
         "share": pct(v["matched"], v["articles"])}
        for klass, v in sorted(level1["by_source_class"].items())])

    lines = [
        "# LexisNexis ↔ GDELT overlap",
        "",
        f"Generated by `scripts/13_overlap_report.py` on {dt.date.today()}; "
        f"GDELT side from `textrefs_news_{news_tag}.csv`.",
        "",
        "## What is being compared",
        "",
        f"- **{level1['lexis_total']}** LexisNexis articles (licensed full text, "
        f"{int(sum(r['is_duplicate'] for r in lexis_records))} of them verbatim wire duplicates)",
        f"- **{level1['gdelt_total']}** distinct URLs retrieved by our GDELT episode queries",
        f"- outlet identity resolved through a source→domain map of {len(mapping)} entries, "
        f"{learned} of them **learned from the {learned} articles that print their own URL** "
        f"rather than asserted",
        "",
        "## Level 1 — retrieval overlap",
        "",
        "How much of each corpus the other one would have found.",
        "",
        "| direction | matched | total | share | 95% CI |",
        "|---|---|---|---|---|",
        f"| LexisNexis article found in our GDELT results | {level1['lexis_matched']} | "
        f"{level1['lexis_total']} | {pct(level1['lexis_matched'], level1['lexis_total'])} | "
        f"[{level1['lexis_matched_ci'][0]:.1%}, {level1['lexis_matched_ci'][1]:.1%}] |",
        f"| GDELT URL found in LexisNexis | {level1['gdelt_matched']} | "
        f"{level1['gdelt_total']} | {pct(level1['gdelt_matched'], level1['gdelt_total'])} | "
        f"[{level1['gdelt_matched_ci'][0]:.1%}, {level1['gdelt_matched_ci'][1]:.1%}] |",
        "",
        "### By outlet class",
        "",
        "The overlap is not uniform, and it cannot be: broadcast transcripts and "
        "print-only editions have no public URL for GDELT to index, so their "
        "non-overlap is structural rather than a retrieval failure.",
        "",
        by_class.to_markdown(index=False) if len(by_class) else "(no articles)",
        "",
    ]

    if level2:
        lines += [
            "## Level 2 — is the story in GDELT at all?",
            "",
            "For a random sample of the articles level 1 did not match, GDELT was "
            "queried directly by outlet and headline terms. This separates *GDELT "
            "does not index this outlet* from *our episode queries missed it* — the "
            "second is our limitation, and conflating the two would overstate the "
            "index's gaps.",
            "",
            f"| | value |",
            f"|---|---|",
            f"| unmatched articles (population) | {level2['population']} |",
            f"| sampled | {level2['sampled']} |",
            f"| probes that got an answer | {level2['answered']} "
            f"(excluded: {level2['failed_probes']} rate-limited) |",
            f"| found in the index anyway | {level2['in_index']} "
            f"({pct(level2['in_index'], level2['sampled'])}) |",
            f"| 95% CI | [{level2['in_index_ci'][0]:.1%}, {level2['in_index_ci'][1]:.1%}] |",
            "",
            f"Found-anyway by outlet class: `{level2['in_index_by_class']}`",
            "",
            "Read the *found in the index anyway* share as the recall loss of our "
            "episode-query strategy; the remainder is coverage GDELT does not have.",
            "",
        ]
    else:
        lines += ["## Level 2 — is the story in GDELT at all?", "",
                  "Not run. Re-run with `--probe` once the GDELT sweep has finished "
                  "(it shares the same one-request-per-five-seconds budget).", ""]

    lines += [
        "## Limitations",
        "",
        "1. **The GDELT side is only what our queries returned**, not the whole index; "
        "level 2 is what quantifies that difference.",
        "2. **Title matching is fuzzy.** Desk edits, translated headlines and "
        "truncation all reduce similarity; both a Jaccard and a containment score are "
        "recorded per pair so a reviewer can see which carried the match.",
        "3. **The source→domain map is incomplete** for outlets that never print a URL; "
        f"it currently covers {level1['domain_map_coverage']:.0%} of articles. Unmapped "
        "outlets can still match on a strong headline agreement alone.",
        "4. **LexisNexis is a convenience sample** — one Lexis query, capped at the most "
        "recent 1,000 hits — so these shares describe this corpus, not news coverage "
        "of tornadoes in general.",
    ]

    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = config.OUTPUT_DIR / "overlap_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    matches_path = config.PROCESSED_DIR / f"overlap_matches_{news_tag}.csv"
    matches.to_csv(matches_path, index=False)
    outputs = [report_path, matches_path]
    if level2:
        probe_path = config.PROCESSED_DIR / f"overlap_index_probe_{news_tag}.csv"
        pd.DataFrame(level2["results"]).to_csv(probe_path, index=False)
        outputs.append(probe_path)

    counts = {"lexis_total": level1["lexis_total"], "lexis_matched": level1["lexis_matched"],
              "gdelt_total": level1["gdelt_total"], "gdelt_matched": level1["gdelt_matched"],
              "by_source_class": level1["by_source_class"],
              "domain_map_entries": len(mapping), "domain_map_learned": learned,
              "level2": {k: v for k, v in (level2 or {}).items() if k != "results"}}
    write_manifest(config.PROCESSED_DIR / f"manifest_overlap_{news_tag}.json",
                   "13_overlap_report", counts=counts, outputs=outputs)
    print(f"\nwrote {report_path.name}, {matches_path.name}")


if __name__ == "__main__":
    main()

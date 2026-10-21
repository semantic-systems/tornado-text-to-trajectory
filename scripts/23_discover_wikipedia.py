#!/usr/bin/env python
"""Stage 23 — find every English Wikipedia article about a US tornado or outbreak.

Two uses downstream: the articles' own text (dedicated tornado articles and the
per-tornado sections of outbreak articles) becomes a text source, and their
news references are checked against the corpora to measure coverage. Both are
only as good as the article list, so this stage measures its own completeness
instead of asserting it: five independent discovery channels (see
:mod:`tornado_dataset.text.wikipedia`) are run separately, and the report says
what each one finds and what each one *alone* finds.

Each in-scope page is pinned to the revision it had at discovery and that
revision's wikitext is stored, so every later stage reads the same text.

Usage::

    python scripts/23_discover_wikipedia.py            # from cache where possible
    python scripts/23_discover_wikipedia.py --refresh  # re-ask Wikipedia

Outputs ``data/interim/wikipedia_pages.csv`` (every candidate, with the reason
it is in or out), ``data/interim/wikipedia_sections.csv`` (per-tornado sections
of in-scope outbreak articles) and ``outputs/wikipedia_discovery_report.md``.
"""

from __future__ import annotations

import argparse
import itertools
from collections import Counter
from datetime import datetime, timezone

import pandas as pd
from tqdm import tqdm

import _bootstrap  # noqa: F401

from tornado_dataset import config
from tornado_dataset.ids import write_manifest
from tornado_dataset.text import wikipedia as wp

PAGES_CSV = config.INTERIM_DIR / "wikipedia_pages.csv"
SECTIONS_CSV = config.INTERIM_DIR / "wikipedia_sections.csv"
REPORT = config.OUTPUT_DIR / "wikipedia_discovery_report.md"
SEARCH_CHANNELS = [c for c in wp.CHANNELS if c != "main_link"]


def build_pages(hits: dict[str, set[str]], years: range, refresh: bool,
                pages: dict[int, dict] | None = None) -> dict[int, dict]:
    """Resolve raw channel hits to pages, merging channels onto each page."""
    pages = {} if pages is None else pages
    titles = set().union(*hits.values())
    canonical, records = wp.resolve(titles, refresh=refresh)
    by_title = {}
    for record in records:
        page = pages.setdefault(record["pageid"], {**record, "channels": set(),
                                                   "via_section_redirect": False})
        by_title[record["title"]] = page
    for p in pages.values():
        by_title.setdefault(p["title"], p)
    for channel, found in hits.items():
        for title in found:
            target = canonical.get(title, title)
            page = by_title.get(target.split("#")[0])
            if page is None:
                continue
            page["channels"].add(channel)
            if "#" in target:
                page["via_section_redirect"] = True
    for page in pages.values():
        page["kind"] = wp.classify(page)
        page["year"] = wp.event_year(page)
        page["us_states"] = wp.us_states(page)
        page["scope"] = wp.scope(page, years)
    return pages


def collect_sections(pages: dict[int, dict], refresh: bool) -> list[dict]:
    """Store pinned revisions of in-scope pages and read outbreak sections."""
    rows = []
    todo = [p for p in pages.values() if p["scope"] == "in_scope" and not p.get("stored")]
    for page in tqdm(todo, desc="revisions", unit="page"):
        record = wp.fetch_revision(page["pageid"], page["revid"], refresh=refresh)
        page["stored"] = True
        page["rev_timestamp"] = record["rev_timestamp"]
        page["prose_words"] = len(wp.plain_text(record["wikitext"]).split())
        if page["kind"] != "outbreak":
            continue
        sections = wp.tornado_sections(record["wikitext"])
        page["n_sections"] = len(sections)
        for i, s in enumerate(sections):
            rows.append({"pageid": page["pageid"], "revid": page["revid"],
                         "page_title": page["title"], "year": page["year"],
                         "section_no": i, **s})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--refresh", action="store_true",
                    help="re-query Wikipedia instead of reading the response cache "
                         "(re-pins every page to its current revision)")
    args = ap.parse_args()

    years = range(config.WINDOW_START.year, config.WINDOW_END.year + 1)
    bar = tqdm(desc="discovery", bar_format="{desc}")
    hits = wp.discover(years, refresh=args.refresh,
                       progress=lambda s: bar.set_description_str(f"discovery: {s}"))
    bar.close()
    pages = build_pages(hits, years, args.refresh)
    section_rows = collect_sections(pages, args.refresh)

    # Sixth channel: dedicated articles that outbreak sections point to. Pages
    # already found get the channel too, so overlap counts stay comparable.
    main_hits = {t for row in section_rows for t in row["main_article"].split("|") if t}
    hits["main_link"] = main_hits
    before = {pid for pid, p in pages.items() if p["scope"] == "in_scope"}
    pages = build_pages({"main_link": main_hits}, years, args.refresh, pages)
    section_rows += collect_sections(pages, args.refresh)
    added_by_main = {pid for pid, p in pages.items() if p["scope"] == "in_scope"} - before

    frame = pd.DataFrame([{
        "pageid": p["pageid"], "title": p["title"], "revid": p["revid"],
        "rev_timestamp": p.get("rev_timestamp"), "wikibase_item": p["wikibase_item"],
        "kind": p["kind"], "year": p["year"], "us_states": "|".join(p["us_states"]),
        "scope": p["scope"], "channels": "|".join(sorted(p["channels"])),
        "n_channels": len(p["channels"] & set(SEARCH_CHANNELS)),
        "via_section_redirect": p["via_section_redirect"],
        "n_sections": p.get("n_sections"), "prose_words": p.get("prose_words"),
        "length_bytes": p["length"],
    } for p in pages.values()]).astype({"year": "Int64", "n_sections": "Int64",
                                        "prose_words": "Int64"})
    frame = frame.sort_values(["scope", "year", "title"])
    sections = pd.DataFrame(section_rows)
    config.INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_csv(PAGES_CSV, index=False)
    sections.to_csv(SECTIONS_CSV, index=False)

    write_report(frame, sections, hits, added_by_main, pages)
    inscope = frame[frame.scope == "in_scope"]
    write_manifest(config.PROCESSED_DIR / "manifest_wikipedia_discovery.json",
                   "23_discover_wikipedia",
                   counts={"candidates": len(frame), "in_scope": len(inscope),
                           "by_kind": inscope.kind.value_counts().to_dict(),
                           "sections": sections.section_type.value_counts().to_dict()
                                       if len(sections) else {},
                           "raw_hits": {c: len(h) for c, h in hits.items()}},
                   outputs=[PAGES_CSV, SECTIONS_CSV],
                   extra={"parameters": {
                       "search_queries": list(config.WIKIPEDIA_SEARCH_QUERIES),
                       "wikidata_classes": list(config.WIKIDATA_CLASSES),
                       "section_parents": list(config.WIKIPEDIA_TORNADO_SECTION_PARENTS)}})
    print(f"{len(inscope)} in-scope pages "
          f"({inscope.kind.value_counts().to_dict()}), "
          f"sections {sections.section_type.value_counts().to_dict() if len(sections) else {}}")
    print(f"wrote {PAGES_CSV.name}, {SECTIONS_CSV.name}, {REPORT.name}")


def _table(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False)


def write_report(frame, sections, hits, added_by_main, pages) -> None:
    inscope = frame[frame.scope == "in_scope"].copy()
    tornado_secs = sections[sections.section_type == "tornado"] if len(sections) else sections
    day_secs = sections[sections.section_type == "day"] if len(sections) else sections
    chans = {c: inscope.channels.str.split("|").apply(lambda s, c=c: c in s)
             for c in wp.CHANNELS}
    lines = [
        "# Wikipedia discovery — US tornado and outbreak articles",
        "",
        f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}. "
        f"Window {config.WINDOW_START.year}–{config.WINDOW_END.year}, English Wikipedia, "
        "US only. Produced by `scripts/23_discover_wikipedia.py`.",
        "",
        "> **Scope.** Text sources are dedicated tornado articles and the per-tornado "
        "sections of outbreak articles. `List of …` pages are excluded as text — their "
        "rows paraphrase the NCEI narrative they cite — and kept for lookup only.",
        "",
        "## What was found",
        "",
        f"{len(frame):,} distinct pages were returned by at least one channel; "
        f"**{len(inscope):,} are in scope**.",
        "",
        _table(inscope.groupby("kind").agg(pages=("pageid", "size"),
                                           median_words=("prose_words", "median"))
               .round().reset_index().astype({"median_words": "Int64"})),
        "",
        f"The {inscope[inscope.kind == 'outbreak'].shape[0]} outbreak articles hold "
        f"**{len(tornado_secs):,} per-tornado sections** with a median of "
        f"{int(tornado_secs.prose_words.median()) if len(tornado_secs) else 0} words, "
        f"{(tornado_secs.prose_words == 0).sum()} of them empty apart from a "
        "`{{Main}}` pointer or a table. "
        f"{(tornado_secs.main_article != '').sum() if len(tornado_secs) else 0:,} point "
        "to a dedicated article with `{{Main}}`, so a tornado can appear both as a "
        "section and as its own article. Linking will treat those as two texts about "
        "one hazard, not as two hazards.",
        "",
        f"Besides these, {len(day_secs)} **day sections** (\"April 13 event\") group the "
        "confirmed-tornado tables by day. "
        f"{(day_secs.prose_words > 0).sum()} of them carry prose — a narrative over "
        "several tornadoes, linkable to an episode but not to one hazard; the rest "
        "are tables only.",
        "",
        "### By year",
        "",
        _table(inscope.pivot_table(index="year", columns="kind", values="pageid",
                                   aggfunc="count", fill_value=0)
               .join(tornado_secs.groupby("year").size().rename("tornado sections")
                     if len(tornado_secs) else pd.Series(name="tornado sections", dtype=int))
               .fillna(0).astype(int).reset_index()),
        "",
        "## What each channel contributes",
        "",
        "A page found by one channel only is the kind of page a different run would "
        "miss, so the *only* column is the measure of how much each channel matters.",
        "",
    ]
    rows = []
    for c in wp.CHANNELS:
        found = chans[c]
        others = pd.concat([chans[o] for o in wp.CHANNELS if o != c], axis=1).any(axis=1)
        rows.append({"channel": c, "raw hits": len(hits.get(c, ())),
                     "in-scope pages": int(found.sum()),
                     "share of in-scope": f"{found.mean():.0%}",
                     "only this channel": int((found & ~others).sum())})
    lines += [_table(pd.DataFrame(rows)), ""]
    dist = Counter(inscope.n_channels)
    lines += [
        "Pages by number of the five search channels that found them: "
        + ", ".join(f"{k} → {dist[k]}" for k in sorted(dist)) + ".",
        "",
    ]
    if added_by_main:
        added = frame[frame.pageid.isin(added_by_main)]
        lines += [
            f"**{len(added)} in-scope pages were found only through `{{{{Main}}}}` links** "
            "from outbreak sections — misses of the five search channels, measured:",
            "",
            *[f"- {t} ({y})" for t, y in zip(added.title, added.year)],
            "",
        ]
    pair_rows = []
    for a, b in itertools.combinations(SEARCH_CHANNELS, 2):
        both = (chans[a] & chans[b]).sum()
        either = (chans[a] | chans[b]).sum()
        pair_rows.append({"pair": f"{a} × {b}", "both": int(both),
                          "jaccard": f"{both / either:.2f}" if either else "–"})
    lines += ["### Pairwise agreement", "", _table(pd.DataFrame(pair_rows)), ""]

    single = inscope[inscope.n_channels <= 1].sort_values(["year", "title"])
    if len(single):
        lines += ["### Found by at most one search channel — worth a look", "",
                  _table(single[["title", "kind", "year", "channels"]]), ""]

    lines += ["## What was excluded, and why", ""]
    out = frame[frame.scope != "in_scope"]
    reason_rows = []
    for reason, group in out.groupby("scope"):
        reason_rows.append({"reason": reason, "pages": len(group),
                            "examples": "; ".join(group.title.head(4))})
    lines += [_table(pd.DataFrame(reason_rows).sort_values("pages", ascending=False)), ""]
    near = out[(out.scope == "not_us") & out.kind.isin(config.WIKIPEDIA_TEXT_KINDS)
               & out.year.between(config.WINDOW_START.year, config.WINDOW_END.year)]
    if len(near):
        lines += [
            f"**{len(near)} tornado/outbreak pages in the window were excluded as not "
            "US**, because none of their categories names a state or the United States. "
            "Most should be Canadian or European; check the list for US pages with "
            "missing categories:",
            "",
            *[f"- {t} ({y})" for t, y in zip(near.title, near.year)],
            "",
        ]
    redirects = frame[(frame.scope == "in_scope") & frame.via_section_redirect]
    lines += [
        f"{len(redirects)} in-scope pages were reached at least once through a "
        "redirect to a section — a tornado with a name but no article of its own, "
        "covered as a section of the page listed.",
        "",
    ]
    outbreak = inscope[inscope.kind == "outbreak"]
    empty = outbreak[outbreak.n_sections.fillna(0) == 0]
    if len(empty):
        lines += [
            f"## Outbreak articles with no per-tornado sections ({len(empty)})",
            "",
            "No level-2 heading matched `config.WIKIPEDIA_TORNADO_SECTION_PARENTS`. "
            "Either the article describes its tornadoes in running prose only, or it "
            "uses a heading the parser does not know; the second kind is a fixable miss.",
            "",
            *[f"- {t} ({y}, {w or 0:,} words)" for t, y, w in
              zip(empty.title, empty.year, empty.prose_words.fillna(0).astype(int))],
            "",
        ]
    lines += [
        "## Limitations",
        "",
        "1. **Completeness is estimated, not known.** Agreement between channels bounds "
        "how much a single channel misses; it cannot see a page that *every* channel "
        "misses. The check that can — every EF4+ or fatal DAT hazard should have a "
        "section or article — needs the hazard tables and runs at the linking stage.",
        "2. **The Wikidata channel does not follow subclasses** (it uses the search API "
        "because the query service was rate-limiting), so its share understates what "
        "Wikidata holds.",
        "3. **US membership comes from categories.** A US page whose editors gave it no "
        "state category is excluded; the not-US list above is where to look.",
        "4. **Pinned revisions.** Text is read from the revision current at first "
        "discovery. `--refresh` re-pins every page; the revision id is in "
        "`wikipedia_pages.csv`.",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

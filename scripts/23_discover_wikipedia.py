#!/usr/bin/env python
"""Stage 23 — Wikipedia's US tornado text sources, and the census to measure them by.

Three kinds of text: dedicated tornado articles, the per-tornado sections of
outbreak articles, and the US event sections of the yearly "Tornadoes of
<year>" pages — the only prose Wikipedia holds about many episodes. Downstream,
that text becomes a source and its news references are checked against the
corpora; both are only as good as what is found here.

So this stage measures its own completeness two ways. Six independent
discovery channels (see :mod:`tornado_dataset.text.wikipedia`) are run
separately, and the report says what each finds *alone*. And the monthly and
per-outbreak list pages are parsed into a **census** — one row per confirmed
tornado, with its NCEI event id — so the report can say, per significant
tornado, whether Wikipedia has prose about it at all. List rows are lookup
only, never text: they paraphrase the NCEI narrative they cite.

Each in-scope page is pinned to the revision it had at discovery and that
revision's wikitext is stored, so every later stage reads the same text.

Usage::

    python scripts/23_discover_wikipedia.py            # from cache where possible
    python scripts/23_discover_wikipedia.py --refresh  # re-ask Wikipedia

Outputs ``data/interim/wikipedia_pages.csv`` (every candidate, with the reason
it is in or out), ``data/interim/wikipedia_sections.csv`` (per-tornado and day
sections of outbreak articles, US event sections of yearly pages),
``data/interim/wikipedia_census.csv`` (one row per listed tornado) and
``outputs/wikipedia_discovery_report.md``.
"""

from __future__ import annotations

import argparse
import itertools
import re
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
CENSUS_CSV = config.INTERIM_DIR / "wikipedia_census.csv"
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
        if page["kind"] == "yearly":
            sections = wp.yearly_sections(record["wikitext"])
            page["prose_words"] = sum(s["prose_words"] for s in sections)   # US sections only
        elif page["kind"] == "outbreak":
            page["prose_words"] = len(wp.plain_text(record["wikitext"]).split())
            sections = wp.tornado_sections(record["wikitext"])
        else:
            page["prose_words"] = len(wp.plain_text(record["wikitext"]).split())
            continue
        page["n_sections"] = len(sections)
        for i, s in enumerate(sections):
            rows.append({"pageid": page["pageid"], "revid": page["revid"],
                         "page_title": page["title"], "year": page["year"],
                         "section_no": i, **s})
    return rows


def build_census(years: range, refresh: bool,
                 found: set[str]) -> tuple[pd.DataFrame, set[str], int]:
    """Parse every census list into tornado rows; return them, the event links
    found on the lists and hub pages (the ``list_links`` channel), and the
    number of list pages read.

    The lists are the two census categories plus every tornado list title the
    discovery channels turned up (``found``): several per-outbreak lists are in
    neither category. Non-US rows are kept and flagged, not dropped."""
    lists = wp.census_lists(years, refresh=refresh)
    for title in found:
        y = [int(v) for v in re.findall(r"\b((?:19|20)\d{2})\b", title)]
        if (title.startswith(("List of tornadoes", "List of United States tornadoes"))
                and y and max(y) in years):
            lists.add(title)
    titles = lists | set(config.WIKIPEDIA_HUB_PAGES)
    canonical, records = wp.resolve(titles, refresh=refresh)
    # A category member can be a redirect to the list under its current name.
    lists = {canonical.get(t, t).split("#")[0] for t in lists}
    rows, links = [], set()
    for rec in tqdm(records, desc="census lists", unit="page"):
        text = wp.fetch_revision(rec["pageid"], rec["revid"], refresh=refresh)["wikitext"]
        links |= wp.event_links(text)
        if rec["title"] not in lists:
            continue                                   # a hub: links only
        year = max(int(y) for y in re.findall(r"\b((?:19|20)\d{2})\b", rec["title"]))
        for row in wp.list_census(text, year):
            rows.append({"list_title": rec["title"], "list_pageid": rec["pageid"],
                         "list_revid": rec["revid"], **row})
    return pd.DataFrame(rows), links, len(lists)


def add_outbreak_tables(census: pd.DataFrame, pages: dict[int, dict]) -> pd.DataFrame:
    """Confirmed-tornado tables inside outbreak articles, appended to the census.

    Many outbreaks keep their table in the article itself (the "day sections")
    instead of a separate list page, and those tornadoes appear in no list.
    The revisions are the pinned ones stage 23 already stored."""
    rows = []
    for page in pages.values():
        if page["scope"] != "in_scope" or page["kind"] != "outbreak":
            continue
        text = wp.fetch_revision(page["pageid"], page["revid"])["wikitext"]
        for row in wp.list_census(text, page["year"]):
            rows.append({"list_title": page["title"], "list_pageid": page["pageid"],
                         "list_revid": page["revid"], **row})
    return pd.concat([census, pd.DataFrame(rows)], ignore_index=True)


def dedupe(census: pd.DataFrame) -> pd.DataFrame:
    """A tornado listed in two places (a monthly page and an outbreak list or
    article) counts once: same NCEI event id, or same date and start point to
    about a kilometre. The first listing is kept; the rest are flagged."""
    census = census.copy()
    census["year"] = pd.to_datetime(census.date, errors="coerce").dt.year.astype("Int64")
    key = census.date.astype(str) + "|" + census.lat.round(2).astype(str) + "|" + census.lon.round(2).astype(str)
    key = key.where(census.lat.notna(), census.date.astype(str) + "|" + census.location.fillna("")
                    + "|" + census.county.fillna(""))
    dup_coord = key.duplicated() & census.date.notna()
    seen: set[str] = set()
    dup_ncei = []
    for value in census.ncei_event_ids.fillna(""):
        parts = {i for i in value.split("|") if i}
        dup_ncei.append(bool(parts & seen))
        seen |= parts
    census["duplicate"] = dup_coord | pd.Series(dup_ncei, index=census.index)
    return census


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
    census, list_links, n_lists = build_census(years, args.refresh, set().union(*hits.values()))
    hits["list_links"] = list_links
    pages = build_pages(hits, years, args.refresh)
    section_rows = collect_sections(pages, args.refresh)

    # Sixth channel: dedicated articles that outbreak sections point to. Pages
    # already found get the channel too, so overlap counts stay comparable.
    main_hits = {t for row in section_rows for t in row["main_article"].split("|") if t}
    hits["main_link"] = main_hits
    before = {pid for pid, p in pages.items() if p["scope"] == "in_scope"}
    pages = build_pages({"main_link": main_hits}, years, args.refresh, pages)
    section_rows += collect_sections(pages, args.refresh)
    census = dedupe(add_outbreak_tables(census, pages))
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
    census.to_csv(CENSUS_CSV, index=False)

    write_report(frame, sections, hits, added_by_main, pages, census, n_lists)
    inscope = frame[frame.scope == "in_scope"]
    write_manifest(config.PROCESSED_DIR / "manifest_wikipedia_discovery.json",
                   "23_discover_wikipedia",
                   counts={"candidates": len(frame), "in_scope": len(inscope),
                           "by_kind": inscope.kind.value_counts().to_dict(),
                           "sections": sections.section_type.value_counts().to_dict()
                                       if len(sections) else {},
                           "raw_hits": {c: len(h) for c, h in hits.items()},
                           "census_lists": n_lists,
                           "census_rows_us_unique": int((census.is_us & ~census.duplicate).sum())},
                   outputs=[PAGES_CSV, SECTIONS_CSV, CENSUS_CSV],
                   extra={"parameters": {
                       "search_queries": list(config.WIKIPEDIA_SEARCH_QUERIES),
                       "wikidata_classes": list(config.WIKIDATA_CLASSES),
                       "section_parents": list(config.WIKIPEDIA_TORNADO_SECTION_PARENTS),
                       "census_categories": list(config.WIKIPEDIA_CENSUS_CATEGORIES),
                       "hub_pages": list(config.WIKIPEDIA_HUB_PAGES)}})
    print(f"{len(inscope)} in-scope pages "
          f"({inscope.kind.value_counts().to_dict()}), "
          f"sections {sections.section_type.value_counts().to_dict() if len(sections) else {}}")
    print(f"wrote {PAGES_CSV.name}, {SECTIONS_CSV.name}, {REPORT.name}")


def _table(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False)


_DIRECTIONS = {"of", "to", "and", "the", "area", "near", "into", "from", "city",
               "northern", "southern", "eastern", "western", "northeastern", "northwestern",
               "southeastern", "southwestern", "central", "downtown", "rural", "county"}
_COMPASS = re.compile(r"^[nsew]{1,3}$")


def _towns(location: str) -> set[str]:
    words = re.findall(r"[a-z][a-z.'-]+", str(location or "").lower())
    return {w for w in words if len(w) > 2 and w not in _DIRECTIONS and not _COMPASS.match(w)}


def prose_location(census: pd.DataFrame, frame: pd.DataFrame) -> pd.DataFrame:
    """Where Wikipedia's prose about each EF3+ census tornado lives — a
    *heuristic* until the linking stage: a town of the row's location named in
    a dedicated article's title, an outbreak section's heading, or a yearly
    event section's prose, in the same year. First match wins, in that order."""
    sig = census[census.is_us & ~census.duplicate
                 & census.rating.isin(["EF3", "EF4", "EF5"])].copy()
    inscope = frame[frame.scope == "in_scope"]
    dedicated = [(_towns(t), y) for t, y in zip(inscope[inscope.kind == "tornado"].title,
                                                inscope[inscope.kind == "tornado"].year)]
    secs, yearly = [], []
    for page in inscope[inscope.kind.isin(["outbreak", "yearly"])].itertuples():
        text = wp.fetch_revision(page.pageid, page.revid)["wikitext"]
        if page.kind == "outbreak":
            secs += [(_towns(f"{s['heading']} {s['main_article']}"), page.year)
                     for s in wp.tornado_sections(text) if s["section_type"] == "tornado"]
        else:
            yearly += [(s["text"].lower(), page.year) for s in wp.yearly_sections(text, with_text=True)]

    def where(row) -> str:
        towns = _towns(row.location)
        if not towns:
            return "list row only"
        if any(row.year == y and towns & t for t, y in dedicated):
            return "dedicated article"
        if any(row.year == y and towns & t for t, y in secs):
            return "outbreak section"
        if any(row.year == y and any(re.search(rf"\b{re.escape(w)}\b", txt) for w in towns)
               for txt, y in yearly):
            return "yearly event section"
        return "list row only"

    sig["prose"] = sig.apply(where, axis=1)
    return sig


def write_report(frame, sections, hits, added_by_main, pages, census, n_lists) -> None:
    inscope = frame[frame.scope == "in_scope"].copy()
    yearly_secs = sections[sections.section_type == "yearly_event"] if len(sections) else sections
    tornado_secs = sections[sections.section_type == "tornado"] if len(sections) else sections
    day_secs = sections[sections.section_type == "day"] if len(sections) else sections
    chans = {c: inscope.channels.str.split("|").apply(lambda s, c=c: c in s)
             for c in wp.CHANNELS}
    lines = [
        "# Wikipedia discovery — US tornado text sources and list census",
        "",
        f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}. "
        f"Window {config.WINDOW_START.year}–{config.WINDOW_END.year}, English Wikipedia, "
        "US only. Produced by `scripts/23_discover_wikipedia.py`.",
        "",
        "> **Scope.** Text sources are dedicated tornado articles, the per-tornado "
        "sections of outbreak articles, and the US event sections of the yearly "
        "`Tornadoes of <year>` pages. `List of …` pages are not text — their rows "
        "paraphrase the NCEI narrative they cite — but they are parsed into a census of "
        "every listed tornado, which is what the text sources are measured against.",
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
        f"The {inscope[inscope.kind == 'yearly'].shape[0]} yearly pages hold "
        f"**{len(yearly_secs):,} US event sections** "
        f"({int(yearly_secs.prose_words.sum()) if len(yearly_secs) else 0:,} words, median "
        f"{int(yearly_secs.prose_words.median()) if len(yearly_secs) else 0}). Each is a "
        "narrative over one episode, usually several tornadoes; "
        f"{(yearly_secs.main_article == '').sum() if len(yearly_secs) else 0} have no "
        "`{{Main}}` article of their own, so for those episodes this is the only "
        "Wikipedia prose there is. US membership is read from the heading's region "
        + (f"({(yearly_secs.us_basis == 'region').sum()}), or from the prose naming a "
           f"state for storm-named or region-less events ({(yearly_secs.us_basis != 'region').sum()})."
           if len(yearly_secs) else "."),
        "",
        "### By year",
        "",
        _table(inscope.pivot_table(index="year", columns="kind", values="pageid",
                                   aggfunc="count", fill_value=0)
               .join(tornado_secs.groupby("year").size().rename("tornado sections")
                     if len(tornado_secs) else pd.Series(name="tornado sections", dtype=int))
               .join(yearly_secs.groupby("year").size().rename("yearly event sections")
                     if len(yearly_secs) else pd.Series(name="yearly event sections", dtype=int))
               .fillna(0).astype(int).reset_index()),
        "",
    ]
    us = census[census.is_us & ~census.duplicate]
    by_year = us.groupby("year").agg(
        tornadoes=("rating", "size"),
        ef2=("rating", lambda r: (r == "EF2").sum()),
        ef3_plus=("rating", lambda r: r.isin(["EF3", "EF4", "EF5"]).sum()),
        with_ncei_id=("ncei_event_ids", lambda v: f"{(v.fillna('') != '').mean():.0%}"),
        with_start_point=("lat", lambda v: f"{v.notna().mean():.0%}"),
    ).reset_index()
    lines += [
        "## The census",
        "",
        f"{n_lists} list pages (monthly US lists and per-outbreak lists) and the tables "
        f"inside {census[~census.list_title.str.startswith('List')].list_title.nunique()} "
        "outbreak articles give "
        f"**{len(us):,} distinct US tornadoes** — {int(census.duplicate.sum())} rows listed "
        f"twice and {int((~census.is_us).sum())} non-US rows removed. This is Wikipedia "
        "counting itself; the annual totals are of the order of the official US counts, "
        "and the check against DAT/SPC belongs to the linking stage.",
        "",
        _table(by_year),
        "",
        "NCEI event ids are the bridge to DAT. Lists that cite survey statements or the "
        "SPC instead of NCEI leave them empty, which is why some years have few.",
        "",
    ]
    sig = prose_location(census, frame)
    if len(sig):
        table = pd.crosstab(sig.year, sig.prose, margins=True, margins_name="all")
        order = [c for c in ["dedicated article", "outbreak section", "yearly event section",
                             "list row only", "all"] if c in table.columns]
        counts = sig.prose.value_counts()
        lines += [
            "## Where the prose about significant tornadoes lives",
            "",
            f"For each of the **{len(sig)} EF3+ tornadoes** in the census: the most "
            "specific Wikipedia prose that mentions it. **Heuristic** — a town from the "
            "row's location named in a dedicated article's title, an outbreak section's "
            "heading, or a yearly event section's text, in the same year — until the "
            "linking stage replaces it with NCEI ids and geometry.",
            "",
            _table(table[order].reset_index()),
            "",
            f"{counts.get('dedicated article', 0) + counts.get('outbreak section', 0)} have "
            "per-tornado prose; "
            f"{counts.get('yearly event section', 0)} are covered only inside an episode "
            "narrative on a yearly page; "
            f"**{counts.get('list row only', 0)} have no Wikipedia prose beyond their list "
            "row.** That last group is a property of Wikipedia, not of discovery: every "
            "in-scope page the hub lists link to is already found (see `list_links`).",
            "",
        ]
    lines += [
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
        f"Pages by number of the {len(SEARCH_CHANNELS)} search channels that found them: "
        + ", ".join(f"{k} → {dist[k]}" for k in sorted(dist)) + ".",
        "",
    ]
    if added_by_main:
        added = frame[frame.pageid.isin(added_by_main)]
        lines += [
            f"**{len(added)} in-scope pages were found only through `{{{{Main}}}}` links** "
            "from outbreak sections — misses of the search channels, measured:",
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

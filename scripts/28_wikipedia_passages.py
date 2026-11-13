#!/usr/bin/env python
"""Stage 28 — Wikipedia passages as text records.

Cuts the pinned revisions from stage 26 into the units the dataset keeps as
text, one record each:

``tornado_article``    a dedicated article about one tornado      → links to a hazard
``tornado_section``    an outbreak article's section on one tornado → links to a hazard
``outbreak_overview``  the rest of an outbreak article: lead, synopsis,
                       impact, aftermath (tables and per-tornado sections out)
                                                                    → links to an episode
``yearly_event``       a US event section of a "Tornadoes of <year>" page
                                                                    → links to an episode

Each record carries the plain text (path lengths and widths kept — see
``wikipedia.plain_text``), the revision and section it came from, the event
date, the infobox facts, the NCEI event ids its own references cite (the exact
bridge to a DAT hazard, for the linker), and the two independence axes.

Wikipedia is CC BY-SA 4.0, so unlike news the text itself may be kept, with
attribution: every record names its revision permalink and licence.

Usage::

    python scripts/28_wikipedia_passages.py

Reads ``data/interim/wikipedia_pages.csv``, the stored revisions and
``data/interim/wikipedia_refs.csv`` (stage 27 extract); writes
``data/processed/wikipedia_passages.jsonl`` (with text),
``data/processed/wikipedia_textrefs.csv`` (without) and
``outputs/wikipedia_passages_report.md``. Needs no network.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone

import pandas as pd
from tqdm import tqdm

import _bootstrap  # noqa: F401

from tornado_dataset import config
from tornado_dataset.ids import uid, write_manifest
from tornado_dataset.text import refcoverage as rc
from tornado_dataset.text import tiering
from tornado_dataset.text import wikifacts as wf
from tornado_dataset.text import wikipedia as wp

PAGES_CSV = config.INTERIM_DIR / "wikipedia_pages.csv"
REFS_CSV = config.INTERIM_DIR / "wikipedia_refs.csv"
CENSUS_CSV = config.INTERIM_DIR / "wikipedia_census.csv"
PASSAGES_JSONL = config.PROCESSED_DIR / "wikipedia_passages.jsonl"
FACTS_CSV = config.PROCESSED_DIR / "wikipedia_facts.csv"
FACT_LINKS_CSV = config.PROCESSED_DIR / "wikipedia_fact_links.csv"
TEXTREFS_CSV = config.PROCESSED_DIR / "wikipedia_textrefs.csv"
REPORT = config.OUTPUT_DIR / "wikipedia_passages_report.md"

TIER_RULE = f"{tiering.TIER_RULE_VERSION}+wikipedia_revision_{config.WIKI_SURVEY_LAG_DAYS}d"
ORACLE_RULE = f"nws_citation_share_{config.WIKI_ORACLE_REF_SHARE}"
LINK_LEVEL = {"tornado_article": "hazard", "tornado_section": "hazard",
              "outbreak_overview": "episode", "yearly_event": "episode"}
OUTBREAK_FACTS = ("rating", "n_tornadoes", "fatalities", "injuries", "damage", "duration")
FACT_COLUMNS = ("rating", "path_length", "path_width", "fatalities", "injuries",
                "n_tornadoes", "damage")


# ── units ────────────────────────────────────────────────────────────────────
def _year(year: int) -> tuple[str, str]:
    return f"{year}-01-01", f"{year}-12-31"


def _anchor(heading: str) -> str:
    return re.sub(r"\s+", "_", heading.strip())


def units(page, wikitext: str) -> list[dict]:
    """The passages of one page, before references and classification."""
    year = int(page.year) if str(page.year).isdigit() else None
    out = []
    if page.kind == "tornado":
        text, spans, _ = wp.article_prose(wikitext)
        box = wp.infobox(wikitext, prefer="/tornado")
        # The tornado's own "formed" before the page's "date", which on a storm
        # page with a tornado sub-box is the storm's start.
        date, basis = (wp.first_date(box.get("formed", ""), year)
                       or wp.first_date(box.get("date", ""), year)), "infobox"
        if not date:
            date, basis = wp.first_date(page.title, year), "title"
        if not date and year:
            date, basis = wp.first_date(text, year, within=_year(year)), "prose"
        out.append({"unit_kind": "tornado_article", "section_path": "", "heading": "",
                    "text": text, "section_spans": spans, "cited_from": None,
                    "facts": box, "infobox": box, "event_date": date, "event_date_basis": basis})
    elif page.kind == "outbreak":
        text, spans, kept = wp.article_prose(wikitext, skip_tornado_sections=True)
        # The lead's infobox only: the tornado sections carry infoboxes of their own.
        first_heading = re.search(r"^==", wikitext, re.M)
        box = wp.infobox(wikitext[:first_heading.start()] if first_heading else wikitext)
        start = (wp.first_date(box.get("duration", ""), year)
                 or wp.first_date(box.get("date", ""), year)
                 or wp.first_date(box.get("formed", ""), year))
        basis = "infobox"
        if not start:
            start, basis = wp.first_date(page.title, year), "title"
        if not start and year:
            start, basis = wp.first_date(text, year, within=_year(year)), "prose"
        out.append({"unit_kind": "outbreak_overview", "section_path": "", "heading": "",
                    "text": text, "section_spans": spans, "cited_from": kept,
                    "facts": {k: v for k, v in box.items() if k in OUTBREAK_FACTS},
                    "infobox": box, "event_date": start, "event_date_basis": basis})
        for s in wp.tornado_sections(wikitext, with_text=True):
            if s["section_type"] != "tornado":
                continue
            path = f"{s['parent']} > {s['heading']}"
            # The section's own date lies within the outbreak (allowing for a
            # long-lived system); any other date is a comparison.
            window = (start, (dt.date.fromisoformat(start) + dt.timedelta(days=14)).isoformat()) \
                if start else (_year(year) if year else None)
            date = wp.first_date(s["text"], year, within=window) if window else None
            out.append({"unit_kind": "tornado_section", "section_path": path,
                        "heading": s["heading"], "text": s["text"], "section_spans": [],
                        "cited_from": {path}, "facts": {}, "infobox": s["infobox"],
                        "main_article": s["main_article"],
                        "event_date": date or start,
                        "event_date_basis": "section_prose" if date else "outbreak_start"})
    elif page.kind == "yearly":
        for s in wp.yearly_sections(wikitext, with_text=True):
            path = f"{s['parent']} > {s['heading']}"
            out.append({"unit_kind": "yearly_event", "section_path": path,
                        "heading": s["heading"], "text": s["text"], "section_spans": [],
                        "cited_from": {path}, "facts": {},
                        "main_article": s["main_article"], "region": s["region"],
                        "us_basis": s["us_basis"],
                        "event_date": wp.first_date(s["heading"], year),
                        "event_date_basis": "heading"})
    return out


def cited(unit: dict, page_refs: pd.DataFrame, context: str = "prose") -> pd.DataFrame:
    """The page's references cited from inside this unit, in one context.

    ``prose``: cited in the unit's running text, the text's own sources.
    ``table``: cited inside a table in the unit's sections — evidence for a
    table row (a fact), not for the prose. ``infobox``: cited by an infobox in
    the unit's sections (the page's own in the lead; a tornado section's own).
    A tornado article's unit is the whole page.
    """
    if page_refs.empty:
        return page_refs
    column = page_refs[f"{context}_sections"]
    if unit["cited_from"] is None:
        return page_refs[column != ""]
    inside = column.map(lambda s: any(part in unit["cited_from"] for part in s.split(" | ") if part))
    return page_refs[inside]


def ncei_ids(refs: pd.DataFrame) -> list[str]:
    found = set()
    for url in list(refs.url) + list(refs.archive_url):
        found.update(wp._NCEI_ID.findall(str(url)))
    return sorted(found, key=int)


def classify(published_at: str, event_date: str | None) -> dict:
    """The independence axes. Wikipedia is never the surveying organisation;
    a revision well after the event is written with the survey in hand."""
    same_org = False
    if event_date and published_at:
        lag = (dt.date.fromisoformat(published_at[:10]) - dt.date.fromisoformat(event_date)).days
        tclass = "post_survey" if lag >= config.WIKI_SURVEY_LAG_DAYS else "post_event_pre_survey"
    else:
        tclass = "post_event_pre_survey"           # tiering's conservative default
    role = tiering.TEXT_ROLES[(same_org, tclass == "post_survey")]
    return {"same_org_as_geometry": same_org, "temporal_class": tclass, "text_role": role,
            "independence_tier": tiering.INDEPENDENCE_TIER[role], "tier_rule_version": TIER_RULE}


def _news_keys(refs: pd.DataFrame) -> set[str]:
    return {rc.article_key(u, t, w) for u, t, w, c in
            zip(refs.url, refs.title, refs.work, refs.ref_class) if c == "news"}


def record(page, rev: dict, unit: dict, by_context: dict[str, pd.DataFrame]) -> dict:
    """One passage. Its references, ids and source shares are those of its own
    prose; ids cited in its tables go to ``ncei_event_ids_tables`` (they are the
    rows' evidence), and the news its infobox cites count as cited by it."""
    refs = by_context["prose"]
    text = unit["text"]
    path = unit["section_path"]
    anchor = f"#{_anchor(unit['heading'])}" if unit["heading"] else ""
    nws = refs.ref_class.eq("nws") | refs.template.eq("cite dat")
    ids = ncei_ids(refs)
    table_ids = sorted(set(ncei_ids(by_context["table"])) - set(ids), key=int)
    mentioned = wp.ratings_mentioned(text)
    cues = wp.path_cues(text)
    share = round(nws.mean(), 3) if len(refs) else None
    facts = unit["facts"]
    return {
        "textref_uid": uid("textref", "wikipedia", page.pageid, page.revid,
                           unit["unit_kind"], path),
        "unit_kind": unit["unit_kind"],
        "link_level": LINK_LEVEL[unit["unit_kind"]],
        "pageid": int(page.pageid), "revid": int(page.revid),
        "page_title": page.title, "section_path": path, "heading": unit["heading"],
        "title": f"{page.title} § {unit['heading']}" if unit["heading"] else page.title,
        "url": f"https://en.wikipedia.org/w/index.php?oldid={page.revid}{anchor}",
        "page_url": "https://en.wikipedia.org/wiki/" + _anchor(page.title),
        "source_name": "English Wikipedia", "source_type": "encyclopedic",
        "author_org": "Wikipedia contributors", "language": "en",
        "license": rev.get("license", "CC BY-SA 4.0"),
        "published_at": rev.get("rev_timestamp") or page.rev_timestamp,
        "retrieved_at": rev.get("retrieved_at", ""),
        "event_date": unit["event_date"] or "", "event_date_basis": unit["event_date_basis"]
        if unit["event_date"] else "none",
        "year": page.year, "us_states": page.us_states,
        "wikidata_item": getattr(page, "wikibase_item", "") or "",
        "region": unit.get("region", ""), "us_basis": unit.get("us_basis", ""),
        "main_article": unit.get("main_article", ""),
        **{f"infobox_{c}": facts.get(c, "") for c in FACT_COLUMNS},
        "ratings_mentioned": "|".join(f"EF{r}" for r in mentioned),
        "max_rating_mentioned": max(mentioned) if mentioned else None,
        "path_cues": "|".join(cues), "path_like": len(cues) >= 3,
        "words": len(text.split()),
        "n_refs": len(refs), "n_nws_refs": int(nws.sum()),
        "n_news_refs": int(refs.ref_class.eq("news").sum()),
        # The cited news articles, keyed as stage 27 keys them (stage 29 reads
        # this back to know which passage cites which article). News cited only
        # inside a table is a row's source, not the passage's.
        "cited_article_keys": sorted(_news_keys(refs) | _news_keys(by_context["infobox"])),
        "ncei_event_ids": "|".join(ids), "n_ncei_ids": len(ids),
        "ncei_event_ids_tables": "|".join(table_ids),
        "nws_ref_share": share,
        "derived_from_oracle": bool(share is not None and share >= config.WIKI_ORACLE_REF_SHARE),
        "oracle_rule": ORACLE_RULE,
        **classify(rev.get("rev_timestamp") or page.rev_timestamp, unit["event_date"]),
        "snippet": " ".join(text.split()[:40]),
        "content_hash": hashlib.sha1(text.encode("utf-8")).hexdigest()[:16],
        "text": text,
        "section_spans": unit["section_spans"],
        "infobox_raw": unit.get("infobox") or {},
        "infobox_ncei_ids": ncei_ids(by_context["infobox"]),
    }


def build() -> tuple[pd.DataFrame, Counter, pd.DataFrame, pd.DataFrame]:
    config.require_data(PAGES_CSV, REFS_CSV)
    pages = pd.read_csv(PAGES_CSV, keep_default_na=False)
    pages = pages[(pages.scope == "in_scope") & pages.kind.isin(config.WIKIPEDIA_TEXT_KINDS)]
    refs = pd.read_csv(REFS_CSV, keep_default_na=False)
    if "prose_sections" not in refs.columns:
        raise SystemExit(f"{REFS_CSV.name} predates citation contexts — rerun "
                         "scripts/27_wikipedia_reference_coverage.py extract")
    by_page = {pid: g for pid, g in refs.groupby("pageid")}
    empty = refs.iloc[0:0]
    rows, dropped = [], Counter()
    for page in tqdm(list(pages.itertuples()), unit="page"):
        rev = json.loads(wp.store_path(page.pageid, page.revid).read_text(encoding="utf-8"))
        page_refs = by_page.get(page.pageid, empty)
        for unit in units(page, rev["wikitext"]):
            if len(unit["text"].split()) < config.WIKI_MIN_PASSAGE_WORDS:
                dropped[unit["unit_kind"]] += 1
                continue
            rows.append(record(page, rev, unit, {c: cited(unit, page_refs, c)
                                                 for c in ("prose", "table", "infobox")}))
    frame = pd.DataFrame(rows)
    # A section with {{Main}} pointing at a dedicated article summarises it.
    articles = frame[frame.unit_kind == "tornado_article"].set_index("page_title").textref_uid
    frame["summarises"] = [
        "|".join(articles[t] for t in str(m).split("|") if t in articles) if m else ""
        for m in frame.main_article]
    facts, links = build_facts(frame)
    frame = apply_facts(frame, facts, links)
    return frame.drop(columns=["infobox_raw", "infobox_ncei_ids"]), dropped, facts, links


# ── facts: infoboxes and table rows, apart from the prose ────────────────────
FACT_FIELDS = ["date", "time_utc", "rating", "location", "county", "state", "lat", "lon",
               "path_length", "path_width", "fatalities", "injuries", "damage",
               "n_tornadoes", "summary"]


def load_table_rows() -> pd.DataFrame:
    """Every US row of the census tables (list pages and outbreak articles), as facts."""
    config.require_data(CENSUS_CSV)
    census = pd.read_csv(CENSUS_CSV, keep_default_na=False,
                         dtype={"ncei_event_ids": str, "list_pageid": str, "list_revid": str})
    if "table_no" not in census.columns:
        raise SystemExit(f"{CENSUS_CSV.name} predates table sections — rerun "
                         "scripts/26_discover_wikipedia.py")
    census = census[census.is_us.astype(str) == "True"].copy()
    census["fact_uid"] = [uid("fact", "wikipedia_table", r.list_pageid, r.list_revid, r.table_no,
                              r.date, r.location, r.time_utc, r.lat, r.lon)
                          for r in census.itertuples()]
    census = census.drop_duplicates("fact_uid")
    return census.rename(columns={"max_width": "path_width"})


def _window(date: str, before: int, after: int) -> tuple[str, str]:
    d = dt.date.fromisoformat(date)
    return ((d - dt.timedelta(days=before)).isoformat(), (d + dt.timedelta(days=after)).isoformat())


def build_facts(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fact records and their links to passages.

    Relations: ``infobox_of`` (the infobox of an article or tornado section),
    ``listed_in_outbreak`` (a row of an outbreak article's own tables),
    ``same_tornado`` (the row about the tornado a section or article describes,
    with ``match`` saying how it was found — see :func:`wikifacts.match_rows`).
    A passage with no row, or an ambiguous one, gets a ``none`` link carrying
    the verdict, and no id moves.
    """
    rows = load_table_rows()
    qid = dict(zip(frame.pageid.astype(str), frame.wikidata_item))
    table = pd.DataFrame({
        "fact_uid": rows.fact_uid, "fact_kind": "table_row",
        "source_title": rows.list_title, "source_pageid": rows.list_pageid,
        "source_revid": rows.list_revid, "section": rows.section,
        "wikidata_item": rows.list_pageid.map(qid).fillna(""),
        **{f: rows.get(f, "") for f in FACT_FIELDS},
        "ncei_event_ids": rows.ncei_event_ids, "duplicate": rows.duplicate,
    })
    boxes = []
    for p in frame.itertuples():
        box = p.infobox_raw
        if not box:
            continue
        boxes.append({
            "fact_uid": uid("fact", "wikipedia_infobox", p.pageid, p.revid, p.section_path),
            "fact_kind": "infobox", "source_title": p.page_title, "source_pageid": str(p.pageid),
            "source_revid": str(p.revid), "section": p.section_path or "(lead)",
            "wikidata_item": p.wikidata_item,
            "date": wp.first_date(box.get("formed", "") or box.get("date", "")
                                  or box.get("duration", ""), int(p.year)) or "",
            **{f: box.get(f, "") for f in FACT_FIELDS if f != "date"},
            "ncei_event_ids": "|".join(p.infobox_ncei_ids), "duplicate": False,
            "_passage": p.textref_uid})
    facts = pd.concat([table, pd.DataFrame(boxes)], ignore_index=True)
    links = [{"fact_uid": b["fact_uid"], "passage_uid": b["_passage"], "relation": "infobox_of",
              "match": "", "place_share": None} for b in boxes]
    facts = facts.drop(columns=["_passage"], errors="ignore")

    # Rows of an outbreak article's own tables are the tornadoes of that outbreak.
    overview = frame[frame.unit_kind == "outbreak_overview"]
    overview = overview.set_index(overview.pageid.astype(str))
    for r in rows[rows.list_pageid.isin(overview.index)].itertuples():
        links.append({"fact_uid": r.fact_uid, "passage_uid": overview.textref_uid[r.list_pageid],
                      "relation": "listed_in_outbreak", "match": "", "place_share": None})

    # Each tornado section and article: the row(s) describing the same tornado.
    candidates = rows.to_dict("records")
    by_date: dict[str, list[dict]] = {}
    for r in candidates:
        by_date.setdefault(r["date"], []).append(r)
    starts = dict(zip(overview.index, overview.event_date))
    for p in frame[frame.link_level == "hazard"].itertuples():
        if p.unit_kind == "tornado_section":
            heading, start = p.heading, starts.get(str(p.pageid)) or p.event_date
            window = _window(start, 1, 14) if start else (f"{p.year}-01-01", f"{p.year}-12-31")
            states = wf.states_in(heading) or wf.states_in(p.us_states)
        else:
            heading = p.page_title
            window = (_window(p.event_date, 1, 1) if p.event_date and p.event_date_basis
                      in ("infobox", "title") else (f"{p.year}-01-01", f"{p.year}-12-31"))
            states = wf.states_in(heading) | wf.states_in(p.us_states)
        pool = [r for d, rs in by_date.items() if d and window[0] <= d <= window[1] for r in rs]
        own_ids = (set(p.ncei_event_ids.split("|")) | set(p.infobox_ncei_ids)) - {""}
        best, verdict = wf.match_rows(heading, states, window, pool,
                                      rating=p.infobox_raw.get("rating", ""), ids=own_ids)
        relation = "same_tornado"
        for r in best:
            share, _ = wf.place_share(wf.place_names(heading), f"{r['location']} {r['county']}")
            links.append({"fact_uid": r["fact_uid"], "passage_uid": p.textref_uid,
                          "relation": relation, "match": verdict, "place_share": round(share, 3)})
        if not best:
            links.append({"fact_uid": "", "passage_uid": p.textref_uid, "relation": "none",
                          "match": verdict, "place_share": None})
    return facts, pd.DataFrame(links)


def apply_facts(frame: pd.DataFrame, facts: pd.DataFrame, links: pd.DataFrame) -> pd.DataFrame:
    """Give each passage its facts: their ids, and a section the date of its row."""
    facts_by_uid = facts.set_index("fact_uid")
    own = links[links.relation.isin(["same_tornado", "infobox_of"])]
    match = links[links.relation.isin(["same_tornado", "none"])] \
        .drop_duplicates("passage_uid").set_index("passage_uid").match
    frame = frame.copy()
    fact_uids, fact_ids, dates, bases = [], [], [], []
    for p in frame.itertuples():
        mine = own[own.passage_uid == p.textref_uid]
        fact_uids.append("|".join(sorted(mine.fact_uid)))
        ids = set()
        for value in facts_by_uid.loc[mine.fact_uid, "ncei_event_ids"] if len(mine) else []:
            ids |= set(str(value).split("|")) - {""}
        fact_ids.append("|".join(sorted(ids, key=int)))
        rows = mine[mine.relation == "same_tornado"].fact_uid
        row_dates = set(facts_by_uid.loc[rows, "date"]) - {""} if len(rows) else set()
        # The row's date is the tornado's own (local) date; a section's prose may
        # give none, and then fell back to the outbreak's start.
        if len(row_dates) == 1 and (p.unit_kind == "tornado_section"
                                    or p.event_date_basis in ("prose", "none", "")):
            dates.append(row_dates.pop()); bases.append("table_row")
        else:
            dates.append(p.event_date); bases.append(p.event_date_basis)
    frame["fact_uids"] = fact_uids
    frame["ncei_event_ids_facts"] = fact_ids
    frame["table_match"] = frame.textref_uid.map(match).fillna("")
    changed = frame.event_date.ne(dates)
    frame["event_date"], frame["event_date_basis"] = dates, bases
    for i in frame.index[changed]:
        axes = classify(frame.at[i, "published_at"], frame.at[i, "event_date"] or None)
        for key, value in axes.items():
            frame.at[i, key] = value
    return frame


# ── report ───────────────────────────────────────────────────────────────────
def _pct(n: float) -> str:
    return f"{n:.0%}"


def facts_lines(frame: pd.DataFrame, facts: pd.DataFrame, links: pd.DataFrame) -> list[str]:
    hazard = frame[frame.link_level == "hazard"]
    match = hazard.groupby(["unit_kind", "table_match"]).size().unstack(fill_value=0)
    prose = hazard.ncei_event_ids != ""
    via = hazard.ncei_event_ids_facts != ""
    rel = links[links.relation != "none"].relation.value_counts()
    return [
        "## Facts: infoboxes and table rows",
        "",
        f"Tables and infoboxes are kept out of the passage text. They are **{len(facts):,} fact "
        f"records** of their own in `{FACTS_CSV.relative_to(config.REPO_ROOT)}` "
        f"({(facts.fact_kind == 'table_row').sum():,} table rows, "
        f"{(facts.fact_kind == 'infobox').sum()} infoboxes), linked to passages in "
        f"`{FACT_LINKS_CSV.relative_to(config.REPO_ROOT)}`. They are copied from NWS surveys and "
        "NCEI, so they are **oracle** data: for labelling and checking links, never as the "
        "linker's input.",
        "",
        pd.DataFrame({"relation": rel.index, "links": rel.values}).to_markdown(index=False),
        "",
        "- `infobox_of`: the infobox of an article, or of a tornado section (outbreak articles "
        "give significant tornadoes their own). `listed_in_outbreak`: a row of the outbreak "
        "article's own tables, one of its tornadoes. `same_tornado`: the table row about the "
        "tornado a section or article describes, in a state it names, within its dates; "
        "`match` says how: `by_id` (the row cites an NCEI id the passage cites), `by_places` "
        "(half or more of the heading's places, at least two), `by_one_place` (the only tornado "
        "in the window naming one of them, or the only one with the passage's rating). "
        "`ambiguous` passages get no row.",
        "",
        "How each hazard-level passage matched a table row:",
        "",
        match.reset_index().to_markdown(index=False),
        "",
        f"**NCEI ids.** A passage's `ncei_event_ids` are those its own prose cites "
        f"({int(prose.sum())} of {len(hazard)} hazard-level passages); ids cited in the "
        "passage's tables are in `ncei_event_ids_tables`, and the ids of its matched facts in "
        f"`ncei_event_ids_facts` ({int(via.sum())} passages; "
        f"{int((via & ~prose).sum())} of them have none in their prose). Sections whose prose "
        "gave no date of their own take the matched row's date "
        f"(`event_date_basis = table_row`: {int((frame.event_date_basis == 'table_row').sum())}).",
        "",
    ]


def write_report(frame: pd.DataFrame, dropped: Counter, facts: pd.DataFrame,
                 links: pd.DataFrame) -> None:
    g = frame.groupby("unit_kind")
    order = ["tornado_article", "tornado_section", "outbreak_overview", "yearly_event"]
    table = pd.DataFrame({
        "unit": order,
        "links to": [LINK_LEVEL[k] for k in order],
        "passages": [int(g.size().get(k, 0)) for k in order],
        "dropped (< 30 words)": [dropped.get(k, 0) for k in order],
        "median words": [int(g.words.median().get(k, 0)) for k in order],
        "path-like": [_pct(g.path_like.mean().get(k, 0)) for k in order],
        "cite an NCEI event id": [_pct((g.n_ncei_ids.apply(lambda s: (s > 0).mean())).get(k, 0))
                                  for k in order],
        "flagged derived_from_oracle": [_pct(g.derived_from_oracle.mean().get(k, 0)) for k in order],
        "post-survey": [_pct(g.temporal_class.apply(lambda s: (s == "post_survey").mean()).get(k, 0))
                        for k in order],
    })
    hazard = frame[frame.link_level == "hazard"]
    lines = [
        "# Wikipedia passages",
        "",
        f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} by "
        "`scripts/28_wikipedia_passages.py`.",
        "",
        f"**{len(frame):,} passages, {frame.words.sum():,} words** from "
        f"{frame.pageid.nunique()} pinned revisions, each a text record in "
        f"`{TEXTREFS_CSV.relative_to(config.REPO_ROOT)}` (text in "
        f"`{PASSAGES_JSONL.relative_to(config.REPO_ROOT)}`). Wikipedia is CC BY-SA 4.0; "
        "every record carries its revision permalink and licence.",
        "",
        table.to_markdown(index=False),
        "",
        "- **Path-like** is a heuristic: at least three of touchdown, direction of "
        "motion, a length or width, and lifting appear in the passage. It describes "
        "the units, it filters nothing.",
        "- **NCEI event ids** are read from the passage's own references (NCEI "
        "Storm Events links). They are the exact bridge to a DAT hazard for the "
        "linker; a passage without one has to be linked by date, place and rating.",
        f"- **derived_from_oracle** (rule `{ORACLE_RULE}`) flags passages where at least "
        f"{config.WIKI_ORACLE_REF_SHARE:.0%} of the references cited are NWS/NOAA products. "
        "Provisional: the real test is text overlap with the NCEI narrative, which needs "
        "the hazard tables from the server.",
        f"- **Post-survey** (rule `{TIER_RULE}`): the pinned revision is at least "
        f"{config.WIKI_SURVEY_LAG_DAYS} days after the event. Wikipedia is never the "
        "surveying organisation, so post-survey passages are `independent_retrospective`; "
        "the rest, revisions of very recent events, fall to tiering's conservative "
        "pre-survey default.",
        "",
    ]
    summarised = hazard[(hazard.unit_kind == "tornado_section") & (hazard.summarises != "")]
    lines += [
        "## Overlap between units",
        "",
        f"- {len(summarised)} of {(hazard.unit_kind == 'tornado_section').sum()} tornado "
        "sections point (`{{Main}}`) to a dedicated article that is also a passage; the "
        "section is then a summary of that article. Both are kept; `summarises` names the "
        "article's `textref_uid` so an experiment can keep one.",
        f"- {(frame[frame.unit_kind == 'yearly_event'].main_article != '').sum()} yearly event "
        "sections point to an outbreak article; they are the year page's summary of it.",
        "",
    ]
    lines += facts_lines(frame, facts, links)
    if CENSUS_CSV.exists():
        census = pd.read_csv(CENSUS_CSV, keep_default_na=False, dtype={"ncei_event_ids": str})
        census = census[(census.is_us.astype(str) == "True") & (census.duplicate.astype(str) != "True")]
        strong = census[census.rating.str.match(r"^E?F[3-5]$")]
        cited_ids = set("|".join(hazard.ncei_event_ids).split("|")) - {""}
        has = strong.ncei_event_ids.map(lambda s: bool(set(str(s).split("|")) & cited_ids))
        with_id = (strong.ncei_event_ids != "").sum()
        lines += [
            "## Against the census",
            "",
            f"Of the {len(strong)} EF3+ tornadoes in the list census, {with_id} carry an NCEI "
            f"event id there, and **{int(has.sum())}** of those are cited by a tornado article "
            "or tornado section. That is the floor of what the linker can join exactly; "
            "passages that cite no id still describe tornadoes and are linked by date and place.",
            "",
            pd.DataFrame({
                "rating": ["EF3", "EF4", "EF5"],
                "in census": [int(strong.rating.str.endswith(r).sum()) for r in "345"],
                "cited by a hazard-level passage": [
                    int((has & strong.rating.str.endswith(r)).sum()) for r in "345"],
            }).to_markdown(index=False),
            "",
        ]
    years = frame.groupby(["year", "unit_kind"]).size().unstack(fill_value=0)
    lines += ["## By year", "", years.reindex(columns=order, fill_value=0)
              .reset_index().to_markdown(index=False), ""]
    no_date = frame[frame.event_date == ""]
    lines += [
        "## Caveats",
        "",
        f"1. **Event dates** come from the infobox, the heading, the section's first "
        f"date, or the title, in that order; {len(no_date)} passages have none. A tornado "
        "section's first date is usually its own, but can be a date it compares with.",
        "2. **A tornado section** may describe a family of tornadoes from one storm; "
        "it links to a hazard only when the linker finds exactly one.",
        "3. **Revisions are pinned** at discovery (stage 26). Re-running discovery "
        "pins newer ones and changes the `textref_uid`s, by design.",
        "",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    frame, dropped, facts, links = build()
    PASSAGES_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with PASSAGES_JSONL.open("w", encoding="utf-8") as fh:
        for row in frame.to_dict("records"):
            fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    frame.drop(columns=["text", "section_spans", "cited_article_keys"]).to_csv(TEXTREFS_CSV, index=False)
    facts.to_csv(FACTS_CSV, index=False)
    links.to_csv(FACT_LINKS_CSV, index=False)
    write_report(frame, dropped, facts, links)
    write_manifest(config.PROCESSED_DIR / "manifest_wikipedia_passages.json",
                   "28_wikipedia_passages",
                   counts={"passages": len(frame), "words": int(frame.words.sum()),
                           **frame.unit_kind.value_counts().to_dict(),
                           "dropped_short": sum(dropped.values()),
                           "facts": len(facts), "fact_links": len(links)},
                   outputs=[PASSAGES_JSONL, TEXTREFS_CSV, FACTS_CSV, FACT_LINKS_CSV])
    print(frame.unit_kind.value_counts().to_string())
    print(links.relation.value_counts().to_string())
    print(f"wrote {PASSAGES_JSONL.name}, {TEXTREFS_CSV.name}, {FACTS_CSV.name}, "
          f"{FACT_LINKS_CSV.name}, {REPORT.name}")


if __name__ == "__main__":
    main()

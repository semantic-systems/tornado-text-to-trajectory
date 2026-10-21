"""English Wikipedia as a text source: discovery, revision store, tornado sections.

Wikipedia describes a US tornado in three kinds of page, and only two of them
are text sources here (:data:`config.WIKIPEDIA_TEXT_KINDS`):

========== ============================================ ==========================
kind       example                                      used as
========== ============================================ ==========================
tornado    "2011 Tuscaloosa–Birmingham tornado"         text (one hazard)
outbreak   "Tornado outbreak of April 25–28, 2024"      text, per-tornado sections
list       "List of United States tornadoes in May …"   lookup only
========== ============================================ ==========================

A list row paraphrases the NCEI narrative it cites, so it would be oracle text
counted as independent text. Lists are still worth reading for the NCEI event
ids they cite, which is the bridge from a section to a DAT hazard.

Discovery, and why it has five channels
---------------------------------------
No single way of enumerating articles is complete. Categories are the backbone
but editors forget them; navboxes are curated per year but only list what the
editor of that navbox knew about; Wikidata misses new articles; search misses
articles that do not use the infobox. Each channel is run on its own and its
hits are kept, so the report can say what each one *adds* — and a page found by
one channel only is exactly the kind of page another run would miss.

=========== ==================================================================
channel     what it reads
=========== ==================================================================
category    ``Category:Tornadoes of <year>`` and its subcategories (depth 1)
navbox      ``Template:<year> tornado outbreaks``
yearly      ``{{Main}}`` / ``{{Further}}`` targets in ``Tornadoes of <year>``
search      :data:`config.WIKIPEDIA_SEARCH_QUERIES`
wikidata    items of class :data:`config.WIKIDATA_CLASSES` with an enwiki page
main_link   ``{{Main}}`` targets inside an outbreak's tornado sections
=========== ==================================================================

``main_link`` is a sixth, derived channel: an outbreak section that points to a
dedicated article the other five missed is a measured miss, not a guess.

Every page is pinned to the revision it had when discovered, and that revision's
wikitext is stored verbatim under ``data/raw/wikipedia/pages/<pageid>/<revid>.json``
— Wikipedia text is CC BY-SA, so unlike news the body may be kept.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable, Iterator

import mwparserfromhell

from .. import config
from ..http import cache_key, get_json, utcnow_iso

RAW_DIR = config.RAW_DIR / "wikipedia"
API_CACHE = RAW_DIR / "api"
PAGE_STORE = RAW_DIR / "pages"

CHANNELS = ("category", "navbox", "yearly", "search", "wikidata", "main_link")

US_STATES = (
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois",
    "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland",
    "Massachusetts", "Michigan", "Minnesota", "Mississippi", "Missouri", "Montana",
    "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico", "New York",
    "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
    "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah",
    "Vermont", "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming",
    "Washington, D.C.", "Puerto Rico",
)

# A category puts a page in the US if it names the country or a state. "Georgia"
# is both; "Tornadoes in Georgia (country)" exists, and the parenthesis keeps it out.
_US_CATEGORY = re.compile(
    r"^Category:(?:Tornadoes|Tornado outbreaks|Derechos|\d{4} natural disasters|"
    r"[A-Z][a-z]+ \d{4}|\d{4}) in (?:the )?(?P<where>United States|"
    + "|".join(re.escape(s) for s in US_STATES) + r")$")
_YEAR = re.compile(r"\b(19|20)\d{2}\b")
_YEAR_CATEGORY = re.compile(r"^Category:Tornadoes of (\d{4})$")
_OUTBREAK_WORDS = re.compile(
    r"outbreak|derecho|storm complex|severe weather sequence|tornadoes of \w+ \d", re.I)
_TORNADO_TITLE = re.compile(r"tornado(es)?$", re.I)
# "April 13 event", "June 16": older outbreak articles group the confirmed-
# tornado tables by day, as siblings of the per-tornado subsections.
_DAY_HEADING = re.compile(
    r"^(January|February|March|April|May|June|July|August|September|October|"
    r"November|December) \d{1,2}(?:\s*[–-]\s*\d{1,2})?(?: event)?$")


# ── API access ───────────────────────────────────────────────────────────────
def _call(api: str, params: dict[str, Any], *, refresh: bool) -> dict[str, Any]:
    params = {**params, "format": "json", "formatversion": 2}
    interval = (config.WIKIDATA_MIN_REQUEST_INTERVAL if "wikidata" in api
                else config.WIKIPEDIA_MIN_REQUEST_INTERVAL)
    host = "wikidata" if "wikidata" in api else "enwiki"
    path = API_CACHE / host / f"{cache_key(api, params)}.json"
    return get_json(api, params, cache_path=path, refresh=refresh, min_interval=interval)


def query(params: dict[str, Any], *, api: str = config.WIKIPEDIA_API,
          refresh: bool = False) -> Iterator[dict[str, Any]]:
    """Every page of an ``action=query`` result, following ``continue``.

    Each continuation is its own cached response, so an interrupted discovery
    resumes where it stopped and a rerun is the same run.
    """
    cont: dict[str, Any] = {}
    while True:
        payload = _call(api, {"action": "query", **params, **cont}, refresh=refresh)
        yield payload
        if "continue" not in payload:
            return
        cont = payload["continue"]


# ── channels ─────────────────────────────────────────────────────────────────
def category_members(title: str, *, depth: int = 1, refresh: bool = False) -> set[str]:
    """Article titles in a category and, to ``depth``, its subcategories."""
    titles: set[str] = set()
    seen: set[str] = set()
    frontier = [(title, 0)]
    while frontier:
        cat, level = frontier.pop()
        if cat in seen:
            continue
        seen.add(cat)
        for payload in query({"list": "categorymembers", "cmtitle": cat,
                              "cmlimit": 500, "cmtype": "page|subcat"}, refresh=refresh):
            for member in payload.get("query", {}).get("categorymembers", []):
                if member["ns"] == 14:
                    if level < depth:
                        frontier.append((member["title"], level + 1))
                elif member["ns"] == 0:
                    titles.add(member["title"])
    return titles


def page_links(title: str, *, refresh: bool = False) -> set[str]:
    """Main-namespace links on a page (used for navbox templates)."""
    out: set[str] = set()
    for payload in query({"prop": "links", "titles": title, "pllimit": 500,
                          "plnamespace": 0}, refresh=refresh):
        for page in payload.get("query", {}).get("pages", []):
            out.update(link["title"] for link in page.get("links", []))
    return out


def wikitext(title: str, *, refresh: bool = False) -> str:
    """Current wikitext of one page, or "" if it does not exist."""
    for payload in query({"prop": "revisions", "titles": title, "rvprop": "content",
                          "rvslots": "main", "redirects": 1}, refresh=refresh):
        for page in payload.get("query", {}).get("pages", []):
            revs = page.get("revisions") or []
            if revs:
                return revs[0]["slots"]["main"]["content"]
    return ""


def main_targets(text: str) -> set[str]:
    """Targets of ``{{Main}}``, ``{{Further}}`` and ``{{Main article}}`` templates."""
    out: set[str] = set()
    for template in mwparserfromhell.parse(text).filter_templates():
        name = str(template.name).strip().lower()
        if name in {"main", "main article", "further", "further information"}:
            for param in template.params:
                if not param.showkey:
                    target = str(param.value).strip().split("#")[0]
                    if target:
                        out.add(target[0].upper() + target[1:])
    return out


def search_titles(srsearch: str, *, refresh: bool = False) -> set[str]:
    out: set[str] = set()
    for payload in query({"list": "search", "srsearch": srsearch, "srnamespace": 0,
                          "srlimit": 500, "srprop": ""}, refresh=refresh):
        out.update(hit["title"] for hit in payload.get("query", {}).get("search", []))
    return out


def wikidata_titles(classes: Iterable[str] = config.WIKIDATA_CLASSES, *,
                    refresh: bool = False) -> set[str]:
    """enwiki titles of Wikidata items that are instances of ``classes``.

    Uses the Wikidata *search* API (``haswbstatement``) rather than the SPARQL
    query service, which was rate-limiting to one request per minute when this
    was written. Subclasses are therefore not followed — the report shows what
    the channel contributes, so an incomplete channel is visible as such.
    """
    qids: set[str] = set()
    for cls in classes:
        for payload in query({"list": "search", "srsearch": f"haswbstatement:P31={cls}",
                              "srnamespace": 0, "srlimit": 500, "srprop": ""},
                             api=config.WIKIDATA_API, refresh=refresh):
            qids.update(hit["title"] for hit in payload.get("query", {}).get("search", []))
    titles: set[str] = set()
    ordered = sorted(qids)
    for i in range(0, len(ordered), 50):
        payload = _call(config.WIKIDATA_API,
                        {"action": "wbgetentities", "ids": "|".join(ordered[i:i + 50]),
                         "props": "sitelinks", "sitefilter": "enwiki"}, refresh=refresh)
        for entity in payload.get("entities", {}).values():
            link = entity.get("sitelinks", {}).get("enwiki")
            if link:
                titles.add(link["title"])
    return titles


def discover(years: Iterable[int], *, refresh: bool = False,
             progress=None) -> dict[str, set[str]]:
    """Raw titles per channel (before redirects are resolved). ``main_link`` is
    filled later, from the sections of the outbreak pages found here."""
    years = list(years)
    hits: dict[str, set[str]] = {c: set() for c in CHANNELS}
    for year in years:
        if progress:
            progress(f"year {year}")
        hits["category"] |= category_members(f"Category:Tornadoes of {year}", refresh=refresh)
        hits["navbox"] |= page_links(f"Template:{year} tornado outbreaks", refresh=refresh)
        hits["yearly"] |= main_targets(wikitext(f"Tornadoes of {year}", refresh=refresh))
    if progress:
        progress("search")
    for q in config.WIKIPEDIA_SEARCH_QUERIES:
        hits["search"] |= search_titles(q, refresh=refresh)
    if progress:
        progress("wikidata")
    hits["wikidata"] = wikidata_titles(refresh=refresh)
    return hits


# ── resolving and classifying ────────────────────────────────────────────────
def resolve(titles: Iterable[str], *, refresh: bool = False) -> tuple[dict[str, str], list[dict]]:
    """Follow redirects and fetch the metadata classification needs.

    Returns ``(title → canonical title, page records)``. A redirect to a
    *section* ("2011 Tuscaloosa–Birmingham tornado" once pointed into the
    outbreak article) resolves to the page that holds the section; the fragment
    is kept on the mapping so the report can count section-only tornadoes.
    """
    canonical: dict[str, str] = {}
    pages: dict[int, dict] = {}
    ordered = sorted(set(titles))
    for i in range(0, len(ordered), 50):
        batch = ordered[i:i + 50]
        for payload in query({"titles": "|".join(batch), "redirects": 1,
                              "prop": "info|pageprops|categories|templates",
                              "ppprop": "wikibase_item", "cllimit": 500,
                              "clshow": "!hidden", "tllimit": 500, "tlnamespace": 10,
                              "tltemplates": "Template:Infobox weather event|"
                                             "Template:Infobox weather event/Tornado"},
                             refresh=refresh):
            q = payload.get("query", {})
            rename = {n["from"]: n["to"] for n in q.get("normalized", [])}
            redirect = {r["from"]: (r["to"], r.get("tofragment", "")) for r in q.get("redirects", [])}
            for title in batch:
                t = rename.get(title, title)
                if t in redirect:
                    target, fragment = redirect[t]
                    canonical[title] = target + (f"#{fragment}" if fragment else "")
                else:
                    canonical[title] = t
            for page in q.get("pages", []):
                if page.get("missing") or page.get("invalid") or page.get("ns") != 0:
                    continue
                record = pages.setdefault(page["pageid"], {
                    "pageid": page["pageid"], "title": page["title"],
                    "revid": page.get("lastrevid"), "touched": page.get("touched"),
                    "length": page.get("length"),
                    "wikibase_item": page.get("pageprops", {}).get("wikibase_item"),
                    "categories": set(), "templates": set(),
                })
                record["categories"].update(c["title"] for c in page.get("categories", []))
                record["templates"].update(t["title"] for t in page.get("templates", []))
    return canonical, list(pages.values())


def classify(page: dict) -> str:
    """``list`` · ``index`` · ``outbreak`` · ``tornado`` · ``other``.

    By title first — Wikipedia's naming conventions for these pages are strict —
    then by infobox. A hurricane or a town article that mentions a tornado is
    ``other``: its tornado text is a paragraph inside something else.
    """
    title = page["title"]
    if "Category:Disambiguation pages" in page.get("categories", ()):
        return "disambiguation"
    if "Category:Set index articles" in page.get("categories", ()):
        return "index"
    if title.startswith("List of") or title.startswith("Lists of"):
        return "list"
    if re.match(r"^Tornadoes of \d{4}$", title) or title.startswith("Tornadoes in "):
        return "index"
    if _OUTBREAK_WORDS.search(title):
        return "outbreak"
    if _TORNADO_TITLE.search(title):
        return "tornado"
    if "Template:Infobox weather event/Tornado" in page["templates"]:
        return "tornado"
    return "other"


def us_states(page: dict) -> list[str]:
    """States (or "United States") named by the page's categories."""
    found = []
    for cat in page["categories"]:
        m = _US_CATEGORY.match(cat)
        if m:
            found.append(m.group("where"))
    return sorted(set(found))


def event_year(page: dict) -> int | None:
    """The year of the event: the title's year, else a ``Tornadoes of <year>``
    category. Category years win only when the title has none, because a page
    about an anniversary sits in both."""
    m = _YEAR.search(page["title"])
    if m:
        return int(m.group(0))
    years = sorted(int(y.group(1)) for c in page["categories"]
                   if (y := _YEAR_CATEGORY.match(c)))
    return years[0] if years else None


def scope(page: dict, years: range) -> str:
    """Why a page is in or out — "in_scope" or the first reason it is not."""
    if page["kind"] not in config.WIKIPEDIA_TEXT_KINDS:
        return f"kind:{page['kind']}"
    if page["year"] is None:
        return "no_year"
    if page["year"] not in years:
        return "out_of_window"
    if not page["us_states"]:
        return "not_us"
    return "in_scope"


# ── revision store ───────────────────────────────────────────────────────────
def store_path(pageid: int, revid: int) -> Path:
    return PAGE_STORE / str(pageid) / f"{revid}.json"


def fetch_revision(pageid: int, revid: int, *, refresh: bool = False) -> dict[str, Any]:
    """Wikitext of one pinned revision, stored verbatim with its provenance."""
    path = store_path(pageid, revid)
    if path.exists() and not refresh:
        return json.loads(path.read_text(encoding="utf-8"))
    params = {"action": "query", "prop": "revisions", "revids": revid,
              "rvprop": "ids|timestamp|content", "rvslots": "main",
              "format": "json", "formatversion": 2}
    payload = get_json(config.WIKIPEDIA_API, params,
                       min_interval=config.WIKIPEDIA_MIN_REQUEST_INTERVAL)
    page = payload["query"]["pages"][0]
    rev = page["revisions"][0]
    record = {"pageid": pageid, "revid": revid, "title": page["title"],
              "rev_timestamp": rev["timestamp"],
              "wikitext": rev["slots"]["main"]["content"],
              "source_url": f"https://en.wikipedia.org/w/index.php?oldid={revid}",
              "license": "CC BY-SA 4.0", "retrieved_at": utcnow_iso()}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    return record


# ── per-tornado sections ─────────────────────────────────────────────────────
def tornado_sections(text: str) -> list[dict[str, Any]]:
    """The subsections an outbreak article gives individual tornadoes.

    They sit one level below a parent heading such as "Confirmed tornadoes"
    (:data:`config.WIKIPEDIA_TORNADO_SECTION_PARENTS`) and are titled with the
    path ("Tuscaloosa–Birmingham, Alabama"). Prose length is counted after
    stripping markup, references and templates, so a section that is only a
    ``{{Main}}`` pointer and a table shows up as near-zero rather than as long.

    ``section_type`` separates the two things that sit at that level: a
    ``tornado`` section (one tornado, occasionally a named family of them) and a
    ``day`` section ("April 13 event"), which usually holds only that day's table
    and sometimes a narrative covering several tornadoes. A day section can link
    to an episode, never to a single hazard.
    """
    code = mwparserfromhell.parse(text)
    sections = code.get_sections(levels=[2], include_headings=True)
    out: list[dict[str, Any]] = []
    for parent in sections:
        headings = parent.filter_headings(recursive=False)
        if not headings:
            continue
        parent_title = headings[0].title.strip_code().strip()
        if parent_title.lower() not in config.WIKIPEDIA_TORNADO_SECTION_PARENTS:
            continue
        for sub in parent.get_sections(levels=[3], include_headings=True):
            heading = sub.filter_headings(recursive=False)[0]
            title = heading.title.strip_code().strip()
            body = str(sub)[len(str(heading)):]
            # The level-3 section includes its own level-4 children, which are
            # part of the same tornado's description.
            out.append({
                "parent": parent_title,
                "heading": title,
                "section_type": "day" if _DAY_HEADING.match(title) else "tornado",
                "main_article": "|".join(sorted(main_targets(body))),
                "prose_words": len(plain_text(body).split()),
            })
    return out


def plain_text(text: str) -> str:
    """Readable prose from wikitext: no refs, templates, tables, files or markup."""
    text = re.sub(r"<ref[^>]*/>", "", text)
    text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.S)
    text = re.sub(r"\{\|.*?\|\}", "", text, flags=re.S)          # tables
    code = mwparserfromhell.parse(text)
    for template in code.filter_templates(recursive=False):
        try:
            code.remove(template)
        except ValueError:
            pass
    plain = code.strip_code(normalize=True, collapse=True)
    plain = re.sub(r"^\s*(?:File|Image):.*$", "", plain, flags=re.M)
    return re.sub(r"[ \t]+", " ", plain).strip()

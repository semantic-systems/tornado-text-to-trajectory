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
Besides articles, the ``Tornadoes of <year>`` pages are a text source too
(kind ``yearly``): their US event sections are the only prose Wikipedia holds
about many episodes. And the list pages are read in full as a *census* of
tornadoes (:func:`list_census`) — the yardstick the text sources are measured
against.

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
list_links  event links in the census lists and :data:`config.WIKIPEDIA_HUB_PAGES`
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

CHANNELS = ("category", "navbox", "yearly", "search", "wikidata", "list_links", "main_link")

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


def census_lists(years: Iterable[int], *, refresh: bool = False) -> set[str]:
    """Monthly and per-outbreak tornado list pages whose year is in ``years``."""
    years = set(years)
    titles: set[str] = set()
    for cat in config.WIKIPEDIA_CENSUS_CATEGORIES:
        for title in category_members(cat, depth=2, refresh=refresh):
            found = [int(y) for y in re.findall(r"\b((?:19|20)\d{2})\b", title)]
            if title.startswith("List") and found and max(found) in years:
                titles.add(title)
    return titles


_EVENT_LINK = re.compile(r"tornado|outbreak|derecho|storm complex|severe weather|"
                         r"hurricane|tropical storm|supercell", re.I)


def event_links(text: str) -> set[str]:
    """Wikilink targets that could be an event page, sections stripped.

    List pages link every town and county on every row; resolving all of them
    would cost thousands of requests to learn nothing, since a page whose
    title names no weather event is classified ``other`` anyway.
    """
    out = set()
    for m in re.finditer(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]", text):
        target = m.group(1).strip()
        if target and ":" not in target and _EVENT_LINK.search(target):
            out.add(target[0].upper() + target[1:])
    return out


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
    """``list`` · ``yearly`` · ``index`` · ``outbreak`` · ``tornado`` · ``other``.

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
    if re.match(r"^Tornadoes of \d{4}$", title):
        return "yearly"
    if title.startswith("Tornadoes in "):
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
    # A yearly page is global; which of its sections are US is decided per
    # section (see yearly_sections), not by the page's categories.
    if page["kind"] != "yearly" and not page["us_states"]:
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
def tornado_sections(text: str, *, with_text: bool = False) -> list[dict[str, Any]]:
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
                **({"text": plain_text(body), "infobox": infobox(body, prefer="/tornado")}
                   if with_text else {}),
            })
    return out


_MONTH_NAMES = {m.capitalize() for m in (
    "january february march april may june july august september october "
    "november december").split()}
_REGION = re.compile(r"^(?P<when>.*?)\s*\((?P<region>[^()]*)\)\s*$")
_US_REGION = re.compile(r"United States|\bU\.?S\.?\b|" + "|".join(
    re.escape(s) for s in US_STATES))
_STORM_REGION = re.compile(r"^(?:Hurricane|Tropical Storm|Tropical Depression|"
                           r"Post-Tropical|Remnants of|Subtropical)", re.I)
_STATE_IN_PROSE = re.compile(r"\b(?:" + "|".join(
    re.escape(s) for s in US_STATES if s not in {"Washington", "Georgia"}) + r")\b")


def yearly_sections(text: str, *, with_text: bool = False) -> list[dict[str, Any]]:
    """US event sections of a ``Tornadoes of <year>`` page.

    The page is laid out by month (level 2) and event (level 3, "April 9–11
    (United States)"); each event section is a narrative over one episode —
    usually several tornadoes, sometimes one — and many episodes have no
    article of their own, so this is the only prose Wikipedia holds about
    them. The year-level overviews ("United States yearly total") sit outside
    the month headings and are skipped.

    US membership, from the heading's region: a region naming the US or a state
    is US; a storm name ("Hurricane Ida") or no region at all (common on the
    2010 page) is US when the prose names a state; any other region is not.
    Georgia and Washington are not counted from prose, being a country and a
    capital as often as a state.
    """
    out: list[dict[str, Any]] = []
    code = mwparserfromhell.parse(text)
    for month in code.get_sections(levels=[2], include_headings=True):
        headings = month.filter_headings(recursive=False)
        if not headings or headings[0].title.strip_code().strip() not in _MONTH_NAMES:
            continue
        month_title = headings[0].title.strip_code().strip()
        for sub in month.get_sections(levels=[3], include_headings=True):
            heading = sub.filter_headings(recursive=False)[0]
            title = heading.title.strip_code().strip()
            body = str(sub)[len(str(heading)):]
            prose = plain_text(body)
            m = _REGION.match(title)
            region = m.group("region").strip() if m else ""
            if region and _US_REGION.search(region):
                basis = "region"
            elif (not region or _STORM_REGION.match(region)) and _STATE_IN_PROSE.search(prose):
                basis = "storm_prose" if region else "prose"
            else:
                continue
            out.append({
                "parent": month_title,
                "heading": title,
                "section_type": "yearly_event",
                "region": region,
                "us_basis": basis,
                "main_article": "|".join(sorted(main_targets(body))),
                "prose_words": len(prose.split()),
                **({"text": prose} if with_text else {}),
            })
    return out


def plain_text(text: str) -> str:
    """Readable prose from wikitext: no refs, tables, files or markup.

    Templates are dropped except the few that carry words of the sentence —
    above all ``{{convert}}``, which is how Wikipedia writes every path length
    and width ("travelled {{convert|80|mi|km}}"); dropping it would delete the
    numbers a path description is made of.
    """
    text = re.sub(r"<ref[^>]*/>", "", text)
    text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.S)
    text = re.sub(r"\{\|.*?\|\}", "", text, flags=re.S)          # tables
    text = re.sub(r"<gallery[^>]*>.*?</gallery>", "", text, flags=re.S | re.I)
    text = re.sub(r"</?(?:noinclude|includeonly|onlyinclude)[^>]*>", "", text, flags=re.I)
    code = mwparserfromhell.parse(text)
    for template in code.filter_templates(recursive=False):
        try:
            code.replace(template, render_inline(template))
        except ValueError:
            pass
    for link in code.filter_wikilinks(recursive=False):    # images and their captions
        if re.match(r"\s*:?\s*(?:File|Image)\s*:", str(link.title), re.I):
            try:
                code.remove(link)
            except ValueError:
                pass
    plain = code.strip_code(normalize=True, collapse=True)
    plain = re.sub(r"^\s*(?:File|Image):.*$", "", plain, flags=re.M)
    # Rows of a table opened by a template ({{Tornado table start}} … |}) escape
    # the {| … |} rule; their lines start with table syntax, which prose never does.
    plain = re.sub(r"^[ \t]*(?:[|!}]|\{\|).*$\n?", "", plain, flags=re.M)
    plain = re.sub(r"\n{3,}", "\n\n", plain)
    return re.sub(r"[ \t\xa0]+", " ", plain).strip()


# Range words of {{convert|120|-|135|mph}}, as they read in the sentence.
_CONVERT_RANGE = {"-": "–", "–": "–", "to": " to ", "and": " and ", "or": " or ",
                  "x": " by ", "by": " by ", "+/-": " ± ", "&": " and ", "to(-)": " to "}
UNIT_WORDS = {"mi": "miles", "km": "kilometers", "yd": "yards", "m": "meters",
              "ft": "feet", "in": "inches", "cm": "centimeters", "mm": "millimeters",
              "mph": "mph", "km/h": "km/h", "kn": "knots", "kmh": "km/h",
              "sqmi": "square miles", "km2": "square kilometers", "acre": "acres",
              "ha": "hectares", "lb": "pounds", "kg": "kilograms", "F": "°F", "C": "°C"}
_SINGULAR = {"miles": "mile", "kilometers": "kilometer", "yards": "yard", "meters": "meter",
             "feet": "foot", "inches": "inch", "acres": "acre"}
_INLINE_TEXT = {"nowrap": 0, "nobr": 0, "abbr": 0, "lang": 1, "small": 0, "smaller": 0}


def _positional(template) -> list[str]:
    return [str(p.value).strip() for p in template.params if not p.showkey]


def render_inline(template) -> str:
    """What a template contributes to the sentence it sits in ("" for most)."""
    name = str(template.name).strip().lower()
    args = _positional(template)
    if name in {"convert", "cvt"} and args:
        if len(args) >= 3 and args[1].lower() in _CONVERT_RANGE:
            number, unit = args[0] + _CONVERT_RANGE[args[1].lower()] + args[2], \
                (args[3] if len(args) > 3 else "")
        else:
            number, unit = args[0], (args[1] if len(args) > 1 else "")
        word = UNIT_WORDS.get(unit, unit)
        adjective = template.has("adj") and str(template.get("adj").value).strip() == "on"
        if number in {"1", "1.0"} or adjective:
            word = _SINGULAR.get(word, word)
        return f"{number}-{word}" if adjective and word else f"{number} {word}".strip()
    if name in {"nbsp", "spaces"}:
        return " "
    if name in {"ndash", "snd"}:
        return "–"
    if name in {"blockquote", "quote", "quotation"}:
        body = template.get("text").value if template.has("text") else (
            template.params[0].value if template.params else "")
        return plain_text(str(body))
    if name in _INLINE_TEXT and len(args) > _INLINE_TEXT[name]:
        return plain_text(args[_INLINE_TEXT[name]])
    if name in {"start date", "start date and age", "end date", "end date and age"} and args:
        # {{start date|2020|8|10}} or {{start date and age|August 10, 2020}}
        parts = [a.strip() for a in args[:3]]
        if all(p.isdigit() for p in parts) and len(parts) == 3 and 1 <= int(parts[1]) <= 12:
            return f"{_MONTH_RE.split('|')[int(parts[1]) - 1]} {int(parts[2])}, {parts[0]}"
        if len(parts) == 2 and all(p.isdigit() for p in parts) and 1 <= int(parts[1]) <= 12:
            return f"{_MONTH_RE.split('|')[int(parts[1]) - 1]} {parts[0]}"
        return parts[0] if not parts[0].isdigit() else " ".join(parts)
    return ""


# ── passages: the text units the dataset keeps ───────────────────────────────
# Sections that are apparatus, not prose about the event.
BOILERPLATE_SECTIONS = {
    "see also", "references", "notes", "external links", "further reading",
    "sources", "bibliography", "gallery", "footnotes", "citations", "works cited",
    "explanatory notes", "notes and references", "references and notes", "note",
}
_MONTH_RE = ("January|February|March|April|May|June|July|August|September|"
             "October|November|December")
# The day is one or two digits *not followed by another*: "February 2025" is
# a month and a year, not February 20.
_DATE = re.compile(rf"\b({_MONTH_RE})\s+(\d{{1,2}})(?!\d)(?:\s*[–-]\s*(?:(?:{_MONTH_RE})\s+)?"
                   rf"\d{{1,2}}(?!\d))?(?:,?\s*((?:19|20)\d{{2}}))?")
# Day-month-year, as some articles write it: "19 December 2013", "20–23 December".
_DATE_DMY = re.compile(rf"(?<![\d–-])\b(\d{{1,2}})(?:\s*[–-]\s*\d{{1,2}})?\s+({_MONTH_RE})\b"
                       rf"(?:,?\s*((?:19|20)\d{{2}}))?")
_MONTH_NO = {m: i + 1 for i, m in enumerate(_MONTH_RE.split("|"))}


def _date_matches(text: str):
    """``(position, month, day, year or None)`` for both date orders, in text order."""
    found = [(m.start(), m.group(1), m.group(2), m.group(3)) for m in _DATE.finditer(text)]
    found += [(m.start(), m.group(2), m.group(1), m.group(3)) for m in _DATE_DMY.finditer(text)]
    return sorted(found)


def first_date(text: str, year: int | None = None, *,
               within: tuple[str, str] | None = None) -> str | None:
    """The first "Month D[, YYYY]" (or "D Month YYYY") in ``text`` as an ISO
    date (start of a range).

    A date without a year takes ``year``. With ``within`` (two ISO dates), dates
    outside that window are passed over — prose compares a tornado with earlier
    ones ("the 1991 Andover tornado"), and those dates are not its own.
    """
    import datetime as _dt
    for _, month, day, given in _date_matches(text or ""):
        y = int(given) if given else year
        if not y:
            continue
        try:
            found = _dt.date(y, _MONTH_NO[month], int(day)).isoformat()
        except ValueError:
            continue
        if within is None or within[0] <= found <= within[1]:
            return found
    return None


INFOBOX_FIELDS = {           # parameter → column; the first one present wins
    "formed": "formed", "date": "date", "dissipated": "dissipated",
    "duration": "duration", "fujita-scale": "rating", "fujitascale": "rating",
    "fscale": "rating", "winds": "winds", "path-length": "path_length", "path-width": "path_width",
    "width": "path_width", "fatalities": "fatalities", "deaths": "fatalities",
    "injuries": "injuries", "tornadoes": "n_tornadoes", "damages": "damage",
    "damage": "damage", "areas": "areas",
}


def infobox(text: str, prefer: str | None = None) -> dict[str, str]:
    """Facts from the ``{{Infobox weather event}}`` family (and ``{{Infobox
    derecho}}``), as plain text; the first box to give a field wins.

    Boxes come in groups: a main box and the sub-boxes after it
    (``…/Tornado``, ``…/Effects``). ``prefer`` (e.g. ``"/tornado"``) reads the
    one group that holds such a sub-box first: a storm page about one tornado
    has a group for the storm and one for the tornado, and its "formed" is the
    tornado's. A main box's ``width`` is the image's, never the path's.
    """
    groups: list[list] = []
    for t in mwparserfromhell.parse(text).filter_templates(recursive=False):
        name = str(t.name).strip().lower()
        if not name.startswith(("infobox weather event", "infobox derecho")):
            continue
        if "/" not in name or not groups:
            groups.append([])
        groups[-1].append(t)
    def _has(g):
        return any(str(t.name).strip().lower().endswith(prefer) for t in g)
    # Only a single such group is "the" tornado; with several (a tornado
    # family), the page-level box summarises them and stays first.
    if prefer and sum(map(_has, groups)) == 1:
        groups.sort(key=lambda g: not _has(g))
    out: dict[str, str] = {}
    for template in (t for g in groups for t in g):
        main = "/" not in str(template.name)
        for param in template.params:
            key = str(param.name).strip().lower()
            column = INFOBOX_FIELDS.get(key)
            if main and key == "width":
                continue
            value = plain_text(str(param.value))
            if column and value and column not in out:
                out[column] = value
    return out


def _flat_sections(text: str) -> Iterator[tuple[int, str, str]]:
    """(level, heading, body) for the lead (level 0) and every section, flat."""
    code = mwparserfromhell.parse(text)
    for section in code.get_sections(include_lead=True, flat=True):
        headings = section.filter_headings(recursive=False)
        if headings and str(section).startswith(str(headings[0])):
            h = headings[0]
            yield h.level, h.title.strip_code().strip(), str(section)[len(str(h)):]
        else:
            yield 0, "", str(section)


def article_prose(text: str, *, skip_tornado_sections: bool = False
                  ) -> tuple[str, list[dict[str, Any]], set[str]]:
    """The prose of a whole article, with where each section starts and ends.

    Apparatus sections (references, see also, …) and tables are dropped.
    ``skip_tornado_sections`` leaves out the per-tornado subsections of an
    outbreak article — they are passages of their own — so what remains is the
    outbreak's overview: lead, synopsis, impact, aftermath. Returns the text,
    the section spans, and the "L2 > L3" paths that were kept (to attach the
    references cited from them).
    """
    parts: list[str] = []
    spans: list[dict[str, Any]] = []
    kept: set[str] = set()
    pos = 0
    l2 = l3 = ""
    skipping = False
    for level, heading, body in _flat_sections(text):
        if level == 2:
            l2, l3 = heading, ""
            skipping = heading.lower() in BOILERPLATE_SECTIONS
        elif level == 3:
            l3 = heading
        if skipping:
            continue
        if (skip_tornado_sections and level >= 3 and l3
                and l2.lower() in config.WIKIPEDIA_TORNADO_SECTION_PARENTS
                and not _DAY_HEADING.match(l3)):
            continue
        prose = plain_text(body)
        kept.add("(lead)" if level == 0 else (f"{l2} > {l3}" if l3 else l2))
        if not prose:
            continue
        block = f"{heading}\n{prose}" if heading else prose
        spans.append({"heading": heading or "(lead)", "level": level,
                      "start": pos, "end": pos + len(block)})
        parts.append(block)
        pos += len(block) + 2
    return "\n\n".join(parts), spans, kept


# Cues that a passage traces a path rather than tallying an event. A heuristic
# for the report, not a filter: a passage is path-like with three of the four.
PATH_CUES = {
    "touchdown": re.compile(r"\b(?:touched down|touching down|touchdown|formed|developed)\b", re.I),
    "motion": re.compile(r"\b(?:(?:north|south)?(?:east|west)|north|south)(?:-?(?:north|south)?"
                         r"(?:east|west))?(?:ward)?\b.{0,40}?\b(?:mov|track|travel|continu|"
                         r"cross|head|curv|turn)|\b(?:mov|track|travel|continu|cross|head|curv|"
                         r"turn)\w*\b.{0,40}?\b(?:north|south|east|west)", re.I),
    "dimension": re.compile(r"\b\d+(?:\.\d+)?(?:[–-]\d+(?:\.\d+)?)?\s*(?:miles?|yards?|"
                            r"kilometers?|meters?|feet|foot)\b", re.I),
    "lifting": re.compile(r"\b(?:lifted|dissipated|roped out|ended)\b", re.I),
}
_RATING_MENTION = re.compile(r"\b(?:EF|IF|F)-?([0-5])\b")


def path_cues(text: str) -> list[str]:
    return [name for name, regex in PATH_CUES.items() if regex.search(text or "")]


def ratings_mentioned(text: str) -> list[int]:
    return sorted({int(m) for m in _RATING_MENTION.findall(text or "")})


# ── list census ──────────────────────────────────────────────────────────────
# The monthly "List of United States tornadoes in …" pages and the per-outbreak
# "List of tornadoes in …" pages together enumerate every confirmed US tornado,
# one table row each. They are not text sources (a row paraphrases the NCEI
# narrative it cites); they are the spine: a complete count of tornadoes to
# measure the text sources against, and — through the NCEI event ids the rows
# cite — the bridge from a Wikipedia mention to a DAT hazard.
_RATING = re.compile(r"\b(EF[0-5]|EFU|F[0-5]|IF[0-5])\s*$")
_CAPTION_DATE = re.compile(
    r"(January|February|March|April|May|June|July|August|September|October|November|"
    r"December)\s+(\d{1,2})(?:,\s*(\d{4}))?")
_NCEI_ID = re.compile(r"(?:event-details/|eventdetails\.jsp\?id=|event_id=)(\d{4,})")
_COORD = re.compile(r"coord\s*\|\s*(-?\d+(?:\.\d+)?)\s*\|\s*(-?\d+(?:\.\d+)?)", re.I)
_CONVERT = re.compile(r"\{\{\s*convert\s*\|\s*([^|}]+)\|\s*([^|}]+)[^}]*\}\}", re.I)
US_STATE_ABBR = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN",
    "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV",
    "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN",
    "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC", "PR"}
CENSUS_FIELDS = {          # header text (lower-cased, stripped) → column
    "ef#": "rating", "f#": "rating", "if#": "rating", "location": "location",
    "county": "county", "county / parish": "county", "county/parish": "county",
    "parish": "county", "state": "state", "start coord.": "start_coord",
    "start coord": "start_coord", "coord.": "start_coord", "coord": "start_coord",
    "time (utc)": "time_utc", "path length": "path_length",
    "max width": "max_width", "max. width": "max_width", "summary": "summary",
    "comments/damage": "summary", "comments": "summary",
}


def _split_top(text: str, sep: str) -> list[str]:
    """Split on ``sep`` where it is not inside ``[[…]]`` or ``{{…}}``."""
    parts, depth, start, i = [], 0, 0, 0
    while i < len(text):
        two = text[i:i + 2]
        if two in ("[[", "{{"):
            depth, i = depth + 1, i + 2
            continue
        if two in ("]]", "}}"):
            depth, i = max(0, depth - 1), i + 2
            continue
        if depth == 0 and text.startswith(sep, i):
            parts.append(text[start:i])
            i += len(sep)
            start = i
            continue
        i += 1
    parts.append(text[start:])
    return parts


def _cells(line: str) -> list[str]:
    """Raw cell values of one table line, attributes ("style=… |") removed."""
    out = []
    # Header lines separate cells with "!!" by the book, but some lists use "||".
    parts = _split_top(line[1:], "||")
    if line.startswith("!"):
        parts = [q for p in parts for q in _split_top(p, "!!")]
    for raw in parts:
        head = _split_top(raw, "|")
        if len(head) > 1 and "=" in head[0]:
            raw = "|".join(head[1:])
        out.append(raw.strip())
    return out


def _clean(raw: str) -> str:
    raw = _CONVERT.sub(lambda m: f"{m.group(1).strip()} {m.group(2).strip()}", raw)
    raw = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", "", raw, flags=re.S)
    return re.sub(r"\s+", " ", mwparserfromhell.parse(raw).strip_code()).strip()


def list_census(text: str, list_year: int | None = None) -> list[dict[str, Any]]:
    """One record per tornado row in every confirmed-tornado table of a list page.

    Columns are mapped from each table's own header row, because the layout
    changed over the years: until about 2012 the date sits in a ``!colspan``
    title row and the state in separator rows (``|colspan=7|[[Colorado]]``)
    rather than a column; around 2015 the summary moved from a column into a
    separate "expand-child" row. The NCEI event ids are read from the references
    wherever they are. The date comes from the caption or title row ("List of
    confirmed tornadoes – Wednesday, April 27, 2011"), with the list's year when
    it gives none.
    """
    rows: list[dict[str, Any]] = []
    headings = [(m.start(), m.group(2)) for m in _HEADING_RE.finditer(text)]
    levels = [(m.start(), len(m.group(1)), mwparserfromhell.parse(m.group(2)).strip_code().strip())
              for m in _HEADING_RE.finditer(text)]
    for table_no, match in enumerate(re.finditer(r"^\{\|.*?^\s*\|\}", text, re.S | re.M)):
        l2, l3 = _section_at(levels, match.start())
        section = f"{l2} > {l3}" if l3 else l2
        # MediaWiki tolerates leading spaces on table lines; so must we.
        table = "\n".join(l.lstrip() for l in match.group(0).split("\n"))
        lines = table.split("\n")
        caption = next((l for l in lines if l.startswith("|+")
                        or (l.startswith("!") and "colspan" in l and "tornadoes" in l.lower())), "")
        m = _CAPTION_DATE.search(mwparserfromhell.parse(caption).strip_code())
        if not m:
            # No caption: the date is in the heading above ("===July 4 event===").
            above = [h for pos, h in headings if pos < match.start()]
            m = _CAPTION_DATE.search(above[-1]) if above else None
        date = None
        if m and (m.group(3) or list_year):
            date, _ = parse_cite_date(f"{m.group(1)} {m.group(2)}, {m.group(3) or list_year}")
        chunks = re.split(r"^\|-(.*)$", table, flags=re.M)
        # Some years put the header straight after the caption, with no "|-"
        # before it, so it sits in the preamble rather than in a row of its own.
        preamble = [l for l in chunks[0].split("\n") if l.startswith("!")]
        header: list[str] = [_clean(c).lower() for l in preamble for c in _cells(l)]
        if not any(CENSUS_FIELDS.get(h) == "rating" for h in header):
            header = []                                    # a title row, not the header
        current: dict[str, Any] | None = None
        section_state = ""
        # chunks = [preamble, attrs1, body1, attrs2, body2, …]
        for attrs, body in zip(chunks[1::2], chunks[2::2]):
            cell_lines = [l for l in body.split("\n") if l[:1] in ("|", "!")
                          and not l.startswith(("|}", "|+"))]
            if not cell_lines:
                continue
            if not header and all(l.startswith("!") for l in cell_lines) and \
                    not any("scope=\"row\"" in l for l in cell_lines):
                header = [_clean(c).lower() for l in cell_lines for c in _cells(l)]
                if not any(CENSUS_FIELDS.get(h) == "rating" for h in header):
                    break                                  # not a tornado table
                continue
            if "expand-child" in attrs and current is not None:
                text_ = " ".join(_clean(c) for l in cell_lines for c in _cells(l))
                current["summary"] = (current.get("summary", "") + " " + text_).strip()
                current["ncei_event_ids"] |= set(_NCEI_ID.findall(body))
                continue
            values = [c for l in cell_lines for c in _cells(l)]
            if not header or not values:
                continue
            if len(values) == 1 and "colspan" in body:     # a state separator row
                section_state = _clean(values[0])
                continue
            record: dict[str, Any] = {"date": date, "section": section, "table_no": table_no,
                                      "ncei_event_ids": set(_NCEI_ID.findall(body))}
            for name, raw in zip(header, values):
                field = CENSUS_FIELDS.get(name)
                if field == "start_coord":
                    c = _COORD.search(raw)
                    record["lat"], record["lon"] = (float(c.group(1)), float(c.group(2))) if c else (None, None)
                elif field == "rating":
                    r = _RATING.search(_clean(raw))
                    record["rating"] = r.group(1) if r else ""
                elif field:
                    record[field] = _clean(raw)
            if not record.get("rating"):
                continue
            record.setdefault("state", section_state)
            states = set(re.findall(r"\b[A-Z]{2}\b", record.get("state", "")))
            record["is_us"] = bool(states & US_STATE_ABBR) or any(
                s in record.get("state", "") for s in US_STATES)
            rows.append(record)
            current = record
    for r in rows:
        r["ncei_event_ids"] = "|".join(sorted(r["ncei_event_ids"]))
    return rows


# ── references ───────────────────────────────────────────────────────────────
# Every reference is attributed to the section it is cited from, because that
# is what says which tornado it is evidence about: a reference cited only in the
# "Cullman–Arab, Alabama" section is about that tornado, not the outbreak.
_REF_RE = re.compile(
    r"<ref(?P<attrs>\s[^>]*?)?(?:/>|>(?P<body>.*?)</ref\s*>)", re.S | re.I)
_REF_NAME = re.compile(r"""name\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s/>]+))""", re.I)
_REF_GROUP = re.compile(r"""group\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s/>]+))""", re.I)
_HEADING_RE = re.compile(r"^(={2,6})\s*(.+?)\s*\1\s*$", re.M)
_BARE_URL = re.compile(r"https?://[^\s\]|<>{}]+")
_WAYBACK = re.compile(r"^https?://(?:web\.)?archive\.org/web/(\d+)[a-z_]*/(.+)$", re.I)
_MONTHS = ("january february march april may june july august september october "
           "november december").split()

CITE_FIELDS = {
    "url": ("url",),
    "archive_url": ("archive-url", "archiveurl"),
    "archive_date": ("archive-date", "archivedate"),
    "title": ("title", "script-title"),
    "work": ("work", "newspaper", "website", "magazine", "periodical", "journal"),
    "publisher": ("publisher",),
    "agency": ("agency",),
    "via": ("via",),
    "date": ("date", "publication-date"),
    "year": ("year",),
    "access_date": ("access-date", "accessdate"),
}
_AUTHOR_KEY = re.compile(r"^(?:author|last|first|authors)\d*$")


def _attr(regex: re.Pattern, attrs: str) -> str:
    m = regex.search(attrs or "")
    return next((g for g in m.groups() if g), "").strip() if m else ""


def _value(template, keys: tuple[str, ...]) -> str:
    for key in keys:
        if template.has(key):
            text = template.get(key).value.strip_code().strip()
            if text:
                return text
    return ""


def unwrap_archive(url: str) -> tuple[str, str]:
    """``(original url, archive url)`` for a Wayback link given as the url itself."""
    m = _WAYBACK.match(url or "")
    if not m:
        return url, ""
    original = m.group(2)
    if not original.startswith("http"):
        original = "http://" + original
    return original, url


def parse_cite_date(text: str) -> tuple[str | None, str]:
    """ISO date and its precision (``day`` · ``month`` · ``year`` · ``none``).

    Citation dates come as "April 28, 2011", "28 April 2011", "2011-04-28",
    "April 2011" or "2011". A month-only date must not be read as the 1st, or a
    ±3-day window would look for the article in the wrong week.
    """
    import pandas as pd

    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if not text:
        return None, "none"
    if re.fullmatch(r"\d{4}", text):
        return f"{text}-01-01", "year"
    month_only = re.fullmatch(r"([A-Za-z]+),? (\d{4})", text)
    if month_only and month_only.group(1).lower() in _MONTHS:
        return f"{month_only.group(2)}-{_MONTHS.index(month_only.group(1).lower()) + 1:02d}-01", "month"
    parsed = pd.to_datetime(text, errors="coerce")
    if pd.isna(parsed):
        return None, "none"
    return parsed.date().isoformat(), "day"


def _section_at(headings: list[tuple[int, int, str]], pos: int) -> tuple[str, str]:
    """(level-2 heading, level-3 heading) in force at character ``pos``."""
    l2 = l3 = ""
    for start, level, title in headings:
        if start > pos:
            break
        if level == 2:
            l2, l3 = title, ""
        elif level == 3:
            l3 = title
    return l2 or "(lead)", l3


_TABLE_SPAN = re.compile(r"^[ \t]*\{\|.*?^[ \t]*\|\}", re.S | re.M)


def markup_spans(text: str) -> list[tuple[int, int, str]]:
    """``(start, end, kind)`` of the tables and infoboxes in a page's wikitext.

    A citation inside one of these is evidence for a *fact* (a table row, an
    infobox field), not for the prose around it: the day tables of an outbreak
    article cite the NCEI record of every tornado they list, which the prose
    of that section never mentions.
    """
    spans = [(m.start(), m.end(), "table") for m in _TABLE_SPAN.finditer(text)]
    pos = 0
    for node in mwparserfromhell.parse(text).nodes:       # top level; round-trips exactly
        length = len(str(node))
        if isinstance(node, mwparserfromhell.nodes.Template) and \
                str(node.name).strip().lower().startswith("infobox"):
            spans.append((pos, pos + length, "infobox"))
        pos += length
    return sorted(spans)


def context_at(spans: list[tuple[int, int, str]], pos: int) -> str:
    """``prose`` · ``table`` · ``infobox`` for a character position."""
    for start, end, kind in spans:
        if start <= pos < end:
            return kind
        if start > pos:
            break
    return "prose"


def extract_references(text: str) -> list[dict[str, Any]]:
    """Every distinct reference on a page, with the sections it is cited from.

    A named reference is defined once and reused (``<ref name=x />``); all of
    its uses count, and its sections are the union over them. Footnote groups
    (``group=note``) hold editorial prose, not sources, and are skipped.

    Each use also has a context (:func:`context_at`): ``prose_sections`` are
    the sections where it is cited in running text, ``table_sections`` where
    it is cited inside a table, and ``infobox_sections`` where an infobox cites
    it — the page's own in the lead, or a tornado section's (outbreak articles
    give each significant tornado an infobox of its own).
    """
    headings = [(m.start(), len(m.group(1)), mwparserfromhell.parse(m.group(2)).strip_code().strip())
                for m in _HEADING_RE.finditer(text)]
    spans = markup_spans(text)
    refs: dict[str, dict[str, Any]] = {}
    for m in _REF_RE.finditer(text):
        attrs, body = m.group("attrs") or "", m.group("body")
        if _attr(_REF_GROUP, attrs):
            continue
        name = _attr(_REF_NAME, attrs)
        key = f"name:{name}" if name else f"anon:{m.start()}"
        ref = refs.setdefault(key, {"ref_key": key, "body": None, "sections": [],
                                    "prose": [], "table": [], "infobox": [],
                                    "n_citations": 0})
        if body and body.strip() and ref["body"] is None:
            ref["body"] = body.strip()
        l2, l3 = _section_at(headings, m.start())
        ref["n_citations"] += 1
        section = f"{l2} > {l3}" if l3 else l2
        if section not in ref["sections"]:
            ref["sections"].append(section)
        context = context_at(spans, m.start())
        if section not in ref[context]:
            ref[context].append(section)

    out = []
    for ref in refs.values():
        if not ref["body"]:
            continue                      # a reuse whose definition we never saw
        out.append({"ref_key": ref["ref_key"], "n_citations": ref["n_citations"],
                    "sections": " | ".join(ref["sections"]),
                    "prose_sections": " | ".join(ref["prose"]),
                    "table_sections": " | ".join(ref["table"]),
                    "infobox_sections": " | ".join(ref["infobox"]),
                    **parse_reference(ref["body"])})
    return out


def parse_reference(body: str) -> dict[str, Any]:
    """Structured fields of one ``<ref>`` body: a citation template or a bare link."""
    code = mwparserfromhell.parse(body)
    cite = None
    for template in code.filter_templates(recursive=False):
        name = str(template.name).strip().lower()
        if name.startswith("cite") or name.startswith("citation"):
            cite, kind = template, name
            break
        if name.startswith("#invoke:cite") and template.params:
            cite, kind = template, "cite " + str(template.params[0].value).strip().lower()
            break
    record: dict[str, Any] = {k: "" for k in CITE_FIELDS}
    if cite is not None:
        record["template"] = kind
        for field, keys in CITE_FIELDS.items():
            record[field] = _value(cite, keys)
        record["authors"] = "; ".join(
            p.value.strip_code().strip() for p in cite.params
            if _AUTHOR_KEY.match(str(p.name).strip()) and p.value.strip_code().strip())
    else:
        record["template"] = "bare"
        url = _BARE_URL.search(body)
        record["url"] = url.group(0) if url else ""
        link = re.search(r"\[https?://\S+\s+([^\]]+)\]", body)
        record["title"] = mwparserfromhell.parse(link.group(1)).strip_code().strip() if link else ""
        tail = re.sub(r"\[https?://[^\]]*\]", "", body)
        record["work"] = mwparserfromhell.parse(tail).strip_code().strip(" .,;–-")[:120]
        record["authors"] = ""
    record["url"], wrapped = unwrap_archive(record["url"])
    record["archive_url"] = record["archive_url"] or wrapped
    date, precision = parse_cite_date(record["date"] or record["year"])
    record["pub_date"], record["date_precision"] = date, precision
    record["domain"] = re.sub(r"^www\d?\.", "", (re.match(r"https?://([^/:?#]+)", record["url"])
                                                or [None, ""])[1].lower())
    return record


# Domains whose references are not news. NWS/NOAA first, with the two academic
# mirrors of NWS products (IEM, College of DuPage) that Wikipedia cites for them.
NWS_DOMAINS = ("noaa.gov", "weather.gov", "mesonet.agron.iastate.edu", "kamala.cod.edu",
               "weather.cod.edu", "nssl.noaa.gov")
SOCIAL_DOMAINS = ("twitter.com", "x.com", "facebook.com", "youtube.com", "youtu.be",
                  "instagram.com", "tiktok.com", "reddit.com", "threads.net",
                  "bsky.app", "flickr.com")
REFERENCE_DOMAINS = ("wikipedia.org", "wikimedia.org", "storymaps.arcgis.com",
                     "arcgis.com", "google.com", "books.google.com", "doi.org",
                     "ams.confex.com", "journals.ametsoc.org", "ametsoc.org",
                     "researchgate.net", "jstor.org", "tornadoproject.com",
                     "tornadohistoryproject.com", "findagrave.com", "census.gov",
                     "data.census.gov")
_NON_NEWS_TEMPLATES = {"cite report", "cite dat", "cite journal", "cite book",
                       "cite conference", "cite tweet", "cite thesis", "cite map",
                       "cite encyclopedia", "cite tech report"}


def _under(domain: str, suffixes: Iterable[str]) -> bool:
    return any(domain == s or domain.endswith("." + s) for s in suffixes)


def classify_reference(ref: dict[str, Any]) -> str:
    """``nws`` · ``government`` · ``social`` · ``reference`` · ``news`` · ``other_web``.

    Only ``news`` enters the coverage denominator. A reference is news when the
    citation itself says so (``cite news``, a newspaper or agency field) or when
    a ``cite web`` names a publication on a domain that is none of the above;
    ``other_web`` is the remainder, listed in the report so misclassified
    outlets are visible.
    """
    domain, template = ref.get("domain", ""), ref.get("template", "")
    if _under(domain, NWS_DOMAINS) or re.search(r"national weather service|storm prediction center|"
                                                r"national centers for environmental|noaa",
                                                f"{ref.get('publisher')} {ref.get('work')}", re.I):
        return "nws"
    if _under(domain, SOCIAL_DOMAINS) or template in {"cite tweet"}:
        return "social"
    if (domain.endswith(".gov") or ".gov." in domain or domain.endswith(".mil")
            or re.search(r"\.(state|k12)\.[a-z]{2}\.us$", domain)):
        return "government"
    if (_under(domain, REFERENCE_DOMAINS) or domain.endswith(".edu")
            or template in _NON_NEWS_TEMPLATES):
        return "reference"
    if template in {"cite news", "cite newspaper", "cite press release"} or ref.get("agency"):
        return "news"
    if template == "cite av media" and domain:
        return "news"
    if domain and (ref.get("work") or ref.get("publisher")):
        return "news"
    return "other_web"

"""Facts about a tornado from Wikipedia's tables and infoboxes, kept apart from its prose.

A Wikipedia page says what happened twice: in prose, and in structured markup —
the infobox at the top and the confirmed-tornado tables (one row per tornado:
date, UTC time, rating, location, counties, path length and width, and usually
a citation of the tornado's NCEI Storm Events record). The prose is a text
source; the markup is a **fact record**, copied from the NWS survey and NCEI,
so it is oracle data: it may label or check a link, never be the linker's
input.

This module matches the two. A table row and a prose passage describe the same
tornado when the row's location names the places in the passage's heading
("Rolling Fork–Midnight–Silver City, Mississippi" ↔ "SW of Rolling Fork to
Midnight to NE of Silver City"), in a state the heading names, on a date the
passage allows. The match is what moves an NCEI id from a table into evidence
about a passage, and gives a section its own date where its prose has none.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable

STATE_ABBR = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire",
    "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee",
    "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
    "PR": "Puerto Rico",
}
STATE_NAMES = set(STATE_ABBR.values())
_STATE_WORD = re.compile(r"\b(?:" + "|".join(sorted(map(re.escape, STATE_NAMES), key=len,
                                                     reverse=True)) + r")\b")
# Words in a heading or title that name no place.
_NOT_PLACE = re.compile(r"\b(?:(?:19|20)\d{2}|tornado(?:es)?|tornado family|outbreak|"
                        r"E?F[0-5]|IF[0-5]|the|of|and|area|metro(?:politan)?|region|"
                        r"county|counties|parish)\b", re.I)
# A direction on its own ("Western Kentucky") is a region, not a place a row names.
_DIRECTION = re.compile(r"^(?:north|south|east|west|central|(?:north|south)?(?:east|west)?(?:ern)?"
                        r"|northern|southern|eastern|western)$")
RATING_RANK = {f"{p}{n}": n for p in ("EF", "F", "IF") for n in range(6)}

MIN_SHARE = 0.5          # share of the heading's place names the row must name


def fold(text: str) -> str:
    """Lower case, no accents, anything but letters and digits as one space.

    Names and the texts they are looked for in are folded alike, so a name is
    found as whole words whatever punctuation follows it ("Greenfield, Iowa",
    "Perryton." and "St. Louis" ↔ "st louis").
    """
    text = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def states_in(text: str) -> set[str]:
    """US states named in a heading, title or table cell ("MS", "Mississippi")."""
    text = str(text or "")
    found = set(_STATE_WORD.findall(text))
    found |= {STATE_ABBR[a] for a in re.findall(r"\b([A-Z]{2})\b", text) if a in STATE_ABBR}
    return found


def place_names(heading: str) -> list[str]:
    """The places a tornado heading or article title names, in order.

    "Rolling Fork–Midnight–Silver City, Mississippi" → Rolling Fork, Midnight,
    Silver City; "2011 Joplin tornado" → Joplin. States are dropped: they are
    matched separately, and nearly every row names one.
    """
    text = re.sub(r"\([^)]*\)", " ", str(heading or ""))
    text = _STATE_WORD.sub(" ", text.split(",")[0] if "," in text else text)
    names = []
    for part in re.split(r"\s*[–—]\s*|\s+-\s+|\s*/\s*|\s+to\s+|\s+and\s+", text):
        part = _NOT_PLACE.sub(" ", part)
        part = re.sub(r"\s+", " ", part).strip(" ,.;:-")
        if len(part) >= 3 and fold(part) not in names and not _DIRECTION.match(fold(part)):
            names.append(fold(part))
    return names


def place_share(names: Iterable[str], row_text: str) -> tuple[float, int]:
    """``(share, count)`` of ``names`` found as whole words in ``row_text``."""
    names = list(names)
    if not names:
        return 0.0, 0
    hay = f" {fold(row_text)} "
    hits = sum(any(f" {v} " in hay for v in _variants(n)) for n in names)
    return hits / len(names), hits


_LEADING_DIRECTION = re.compile(r"^(?:north|south|east|west|northern|southern|eastern|western|"
                                r"(?:north|south)(?:east|west)(?:ern)?) (?=\w)")


def _variants(name: str) -> list[str]:
    """A name, and the name without a leading direction: a heading's "North
    West Point" is the row's "NW of West Point"."""
    bare = _LEADING_DIRECTION.sub("", name)
    return [name] if bare == name else [name, bare]


def rating_rank(rating: str) -> int:
    m = re.search(r"\b(E?F|IF)([0-5])\b", str(rating or ""))
    return int(m.group(2)) if m else -1


def match_rows(heading: str, states: set[str], window: tuple[str, str] | None,
               rows: list[dict], *, rating: str = "", ids: Iterable[str] = ()
               ) -> tuple[list[dict], str]:
    """The table rows that describe the tornado a passage is about.

    ``rows`` carry ``date``, ``location``, ``county``, ``state``, ``rating``,
    ``ncei_event_ids``. The verdict says how strong the match is, strongest
    first:

    ``by_id``          the row cites an NCEI id the passage itself cites
    ``by_places``      the row names at least half of the heading's places
                       (two or more, or the only one a title names)
    ``by_one_place``   only one tornado in the window names any of them — a
                       row names a track's ends, a heading the towns it hit —
                       or only one of those also has the passage's rating
    ``ambiguous``      several tornadoes fit equally; nothing is returned
    ``no_match``       no row in the window names any of the places

    The same tornado listed on two pages (outbreak table and monthly list) is
    one answer (:func:`tornado_key`).
    """
    pool = []
    for row in rows:
        if window and not (row.get("date") and window[0] <= row["date"] <= window[1]):
            continue
        row_states = states_in(row.get("state", ""))
        if states and row_states and not (states & row_states):
            continue
        pool.append(row)
    ids = set(ids) - {""}
    if ids:
        hit = [r for r in pool if ids & (set(str(r.get("ncei_event_ids", "")).split("|")) - {""})]
        if hit:
            return _one(hit, "by_id")
    names = place_names(heading)
    if not names:
        return [], "no_places"
    scored = []
    for row in pool:
        share, hits = place_share(names, f"{row.get('location', '')} {row.get('county', '')}")
        if hits:
            scored.append((share, hits, row))
    strong = [(s, h, r) for s, h, r in scored
              if s >= MIN_SHARE and (h >= 2 or len(names) == 1)]
    if strong:
        top = max((s, h) for s, h, _ in strong)
        return _one([r for s, h, r in strong if (s, h) == top], "by_places")
    if not scored:
        return [], "no_match"
    best, verdict = _one([r for _, _, r in scored], "by_one_place")
    if verdict == "ambiguous" and rating_rank(rating) >= 0:
        same = [r for _, _, r in scored if rating_rank(r.get("rating", "")) == rating_rank(rating)]
        if same:
            return _one(same, "by_one_place")
    return best, verdict


def _one(rows: list[dict], verdict: str) -> tuple[list[dict], str]:
    """``rows`` if they are all one tornado, else nothing and ``ambiguous``."""
    if len({tornado_key(r) for r in rows}) == 1:
        return rows, verdict
    return [], "ambiguous"


def tornado_key(row: dict) -> tuple:
    """Same date and start point (to ~1 km) is the same tornado, wherever listed."""
    lat, lon = row.get("lat"), row.get("lon")
    try:
        return (row.get("date"), round(float(lat), 2), round(float(lon), 2))
    except (TypeError, ValueError):
        return (row.get("date"), fold(row.get("location", ""))[:40])

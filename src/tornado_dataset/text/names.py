"""Names the official records give a tornado (stage 26).

No authoritative database has a name field: SPC's list has none, and the names
the media use ("the Joplin tornado") are a convention outside it. Two official
sources label tornadoes all the same, as free text:

* ``pns_section`` — the heading of a storm-survey statement's section
  ("Gum Springs Tornado", "Tornado #3: Burlington Tornado (Elmore County)"), for
  the hazard the section is the primary survey of (stage 20). Only structured
  statements: for the older free-text ones the title is ours, built from place
  names, not the office's.
* ``dat_event_id`` — DAT's ``event_id``, which the surveying office fills in as
  it likes ("Toomsuba Tornado", "GlenEllyn-Lombard", but also "19Jul2018_Tor15").

Storm Events narratives are left out: "the X tornado" occurs in 448 of 23,189,
mostly not a name ("the Enhanced Fujita", "the Red River. The").

Each label is kept as written (``name_raw``) and cleaned conservatively
(:func:`clean_name`: rating, counter, date and the word "tornado" dropped);
``name_kind`` says whether what is left is a ``name`` or a ``code``.
``place_match`` says whether it contains a populated place within
``PLACE_RADIUS_M`` of the track or a county the track crosses (stage 16) — the
automatic check that the label names where the tornado was. One row per hazard
is ``is_preferred`` (:func:`choose`).
"""

from __future__ import annotations

import re

import pandas as pd

SOURCES = ("pns_section", "dat_event_id")
PLACE_RADIUS_M = 50_000.0
# Words that say what a label is, not where: a label of only these is no name.
_GENERIC = {"tornado", "tornadoes", "tor", "survey", "damage", "storm", "nws", "event",
            "events", "summary", "preliminary", "update", "updated", "corrected", "and",
            "the", "of", "for", "near", "in", "track", "path", "segment", "part", "county",
            "parish", "touchdown", "brief", "weak", "line", "polygon", "contour", "s", "n",
            "e", "w", "ne", "nw", "se", "sw", "nne", "ene", "ese", "sse", "ssw", "wsw", "wnw",
            "nnw", "north", "south", "east", "west", "northern", "southern", "eastern",
            "western", "central", "reference", "newly", "confirmed", "new", "first",
            "second", "third", "fourth", "fifth", "th", "st", "nd", "rd"}
_MONTHS = ("jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec|january|february|march|"
           "april|june|july|august|september|october|november|december")
_GENERIC |= set(_MONTHS.split("|"))
_DIRECTIONS = {"n", "s", "e", "w", "ne", "nw", "se", "sw", "nne", "ene", "ese", "sse", "ssw",
               "wsw", "wnw", "nnw"}
_STATES = {s.lower() for s in (
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH "
    "NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC PR").split()}

_DROP = [
    re.compile(r"^\s*tornado\s*#?\s*\d+[a-z]?\s*[:.\-–]\s*", re.I),       # "Tornado #3: "
    re.compile(r"\b(?i:EF|F)[\s\-]?(?:[0-5]\+?(?=\b|[a-z])|U\b)"),       # ratings
    re.compile(r"(?<=[a-z])(?:Tornado|TORNADO|Tor|TOR)(?=\d*\b|_)"),       # "HufTor"
    re.compile(r"\b\d+(?:st|nd|rd|th)\b", re.I),                          # "17th"
    re.compile(r"#\s*\d+[a-z]?\b", re.I),                                # counters
    re.compile(r"\b\d{1,4}[/\-.]\d{1,2}(?:[/\-.]\d{2,4})?\b"),           # 6/25/2012
    re.compile(rf"\b\d{{1,2}}\s*(?:{_MONTHS})\.?\s*\d{{0,4}}\b", re.I),  # 19Jul2018
    re.compile(rf"\b(?:{_MONTHS})\.?\s*\d{{1,2}}(?:,?\s*\d{{4}})?\b", re.I),
    re.compile(r"\btor(?:nado(?:es|s)?)?\s*\d*\b", re.I),                # Tornado, Tor15
    re.compile(r"\b\d+\b"),                                              # bare numbers
    re.compile(r"(?<=[a-z])\d+\b"),                                       # "Garza5"
]
_LEADING = re.compile(r"^(?:(?:in|near|of|the|at)\s+)+", re.I)


def clean_name(raw: str) -> str:
    """A label without rating, counter, date or the word "tornado"; place names,
    states and counties kept. ALL-CAPS labels are title-cased."""
    text = re.sub(r"[_\s]+", " ", str(raw or "")).strip()
    for pattern in _DROP:
        text = pattern.sub(" ", text)
    text = re.sub(r"\(\s*\)", " ", text)
    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r"\s*/\s*", "/", text)
    text = re.sub(r"\s+", " ", text).strip(" -–:;,./(")
    if text.count(")") > text.count("("):
        text = text.rstrip(")").strip()
    elif text.count("(") > text.count(")"):
        text += ")"
    text = _LEADING.sub("", text).strip()
    if text.isupper():
        small = {"of", "and", "the", "in", "near", "to"}
        text = re.sub(r"[A-Z]+", lambda m: m.group().lower() if m.group().lower() in small
                      else m.group() if m.group().lower() in _STATES | _DIRECTIONS
                      or (len(m.group()) <= 3 and not re.search("[AEIOUY]", m.group()))
                      else m.group().capitalize(), text)
        text = text[:1].upper() + text[1:]
    return text


def words(text: str, camel: bool = False) -> list[str]:
    """Lower-case words of a label; with ``camel``, CamelCase split too
    ("NorthOaks" -> north, oaks), which a place written together needs."""
    text = str(text or "")
    if camel:
        text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    return re.findall(r"[a-z]+", text.lower())


def _no_state(text: str) -> list[str]:
    """Words without two-letter state codes written as such (upper case): "MS" goes,
    the "La" of "La Motte" stays."""
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", str(text or ""))
    kept = [w for w in re.findall(r"[A-Za-z]+", text)
            if not (len(w) == 2 and w.isupper() and w.lower() in _STATES)]
    return [w.lower() for w in kept]


def name_kind(cleaned: str) -> str:
    """``name`` if a word of three letters or more is left that is not generic,
    ``code`` otherwise."""
    return "name" if any(len(w) >= 3 and w not in _GENERIC
                         for w in words(cleaned, camel=True)) else "code"


def name_key(cleaned: str) -> str:
    """For comparing labels: lower-case words without generic words and states."""
    return " ".join(w for w in _no_state(cleaned) if w not in _GENERIC)


def place_match(cleaned: str, place_keys: set[str]) -> bool:
    """Whether the label contains one of ``place_keys`` (lower-case words, as
    :func:`name_key` gives them) as whole words."""
    texts = {f" {' '.join(words(cleaned, camel=c))} " for c in (False, True)}
    texts |= {f" {''.join(words(cleaned))} "}          # "La Grange" written "LaGrange"
    return any(k and f" {k} " in t for k in place_keys for t in texts)


def _agrees(a: str, b: str) -> bool:
    wa, wb = set(a.split()), set(b.split())
    return bool(wa) and bool(wb) and (wa <= wb or wb <= wa)


def choose(rows: pd.DataFrame) -> pd.Series:
    """``is_preferred`` for one hazard's candidates.

    Among names (not codes) that match a place, or that another source agrees
    with: the one most candidates agree with, then a survey heading before
    DAT's label (the published statement), then the shorter. At most one.
    """
    keys = rows.name_key.tolist()
    agree = [sum(_agrees(k, o) for j, o in enumerate(keys) if j != i)
             for i, k in enumerate(keys)]
    other_source = [any(_agrees(k, o) and s != rows.source.iloc[j]
                        for j, o in enumerate(keys) if j != i)
                    for i, (k, s) in enumerate(zip(keys, rows.source))]
    ok = (rows.name_kind == "name") & (rows.place_match | pd.Series(other_source,
                                                                     index=rows.index))
    out = pd.Series(False, index=rows.index)
    if not ok.any():
        return out
    rank = pd.DataFrame({"agree": agree, "src": rows.source.map(SOURCES.index),
                         "len": rows.name.str.len()}, index=rows.index)[ok]
    best = rank.sort_values(["agree", "src", "len"], ascending=[False, True, True]).index[0]
    out[best] = True
    return out


def candidates(dat_event_ids: pd.DataFrame, sections: pd.DataFrame) -> pd.DataFrame:
    """One row per label: ``hazard_uid``, ``source``, ``textref_uid``, ``name_raw``.

    ``dat_event_ids`` has ``hazard_uid`` and stage 12's ``dat_event_ids`` (several
    joined by ";"); ``sections`` has ``hazard_uid``, ``textref_uid`` and the
    section's ``title``.
    """
    dat = dat_event_ids.dropna(subset=["dat_event_ids"]).assign(
        name_raw=lambda f: f.dat_event_ids.str.split(";")).explode("name_raw")
    dat = dat.assign(source="dat_event_id", textref_uid=None)
    pns = sections.rename(columns={"title": "name_raw"}).assign(source="pns_section")
    out = pd.concat([dat[["hazard_uid", "source", "textref_uid", "name_raw"]],
                     pns[["hazard_uid", "source", "textref_uid", "name_raw"]]],
                    ignore_index=True)
    out["name_raw"] = out.name_raw.astype(str).str.strip()
    out = out[out.name_raw != ""]
    return out.drop_duplicates(["hazard_uid", "source", "name_raw"]).reset_index(drop=True)


def annotate(cands: pd.DataFrame, place_keys: dict[str, set[str]]) -> pd.DataFrame:
    """Clean each label, classify it, check it against the hazard's places, and
    mark one preferred row per hazard."""
    out = cands.copy()
    out["name"] = out.name_raw.map(clean_name)
    out["name_kind"] = out.name.map(name_kind)
    out["name_key"] = out.name.map(name_key)
    out["place_match"] = [place_match(n, place_keys.get(u, set()))
                          for n, u in zip(out.name, out.hazard_uid)]
    out["is_preferred"] = False
    for _, rows in out.groupby("hazard_uid"):
        out.loc[rows.index, "is_preferred"] = choose(rows)
    return out[["hazard_uid", "source", "textref_uid", "name", "name_raw", "name_kind",
                "place_match", "is_preferred", "name_key"]]


# Tornadoes known by a media name, to show what the official labels give them:
# (name, convective day, state); the deadliest hazard of that day in that state.
WELL_KNOWN = (("Joplin", "2011-05-22", "MO"), ("Hackleburg–Phil Campbell", "2011-04-27", "AL"),
              ("Moore", "2013-05-20", "OK"), ("El Reno", "2013-05-31", "OK"),
              ("Mayflower–Vilonia", "2014-04-27", "AR"), ("Pilger", "2014-06-16", "NE"),
              ("Cookeville", "2020-03-02", "TN"), ("Mayfield", "2021-12-10", "KY"),
              ("Rolling Fork", "2023-03-24", "MS"), ("Greenfield", "2024-05-21", "IA"))


def well_known(table: pd.DataFrame, member: pd.DataFrame, geography: pd.DataFrame
               ) -> pd.DataFrame:
    """For each of ``WELL_KNOWN``, the hazard and the labels the records give it."""
    m = member.merge(geography[["hazard_uid", "states"]], on="hazard_uid", how="left")
    rows = []
    for name, day, state in WELL_KNOWN:
        pick = m[(m.convective_day == day) & m.states.fillna("").str.contains(state)]
        pick = pick.sort_values(["deaths", "rating"], ascending=False).head(1)
        if not len(pick):
            rows.append({"tornado": name, "day": day})
            continue
        h = pick.iloc[0]
        labels = table[table.hazard_uid == h.hazard_uid]
        pref = labels.name[labels.is_preferred]
        rows.append({"tornado": name, "day": day, "hazard_source": h.hazard_source,
                     "deaths": h.deaths, "preferred": pref.iloc[0] if len(pref) else None,
                     "labels": "; ".join(labels.name_raw)})
    return pd.DataFrame(rows)

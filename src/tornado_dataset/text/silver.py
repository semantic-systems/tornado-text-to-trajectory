"""Silver links: Wikipedia text, and the news it cites, to a tornado through NCEI ids.

A Wikipedia passage about one tornado usually cites that tornado's NCEI Storm
Events record, in its prose or in its own infobox, or is matched to a table row
that does (``wikifacts``). The id names a county segment; Storm Events chains
the segments into whole tornadoes (``TORNADO_KEY``, stage 14), and stage 14
links them to DAT hazards. That is a link from text to geometry made by an
editor who never saw this dataset: a **silver** label — evidence, not truth, so
every link carries how it was made and whether it checks out.

**The checks** compare the tornado's Storm Events record with what the passage
itself says: its date (±1 day), its state, a place it names (a heading's towns
among the record's counties, its begin and end towns, or in its narrative), its
rating. They catch the ways an id goes wrong: a passage that cites another
tornado for comparison, a section that cites the outbreak's record rather than
its own, and an editor's wrong id (the 2025 Marion, Illinois article cites
Enderlin's record and never names Enderlin).

**News** inherits a link from the passages that cite it, only when every
hazard-level passage citing it points at the same tornado; it is then checked
on its own: published from the day before the event on, and naming a place of
the tornado's. An article whose text was retrieved intact and names none of
them is **rejected**: Wikipedia cites it for something else — a comparison
("deadliest since the 1978 Elgin tornado"), a whole outbreak, a winter storm
the page is about — and no linker could tie it to this tornado.
"""

from __future__ import annotations

import datetime as dt
import re
import unicodedata
from typing import Iterable

import pandas as pd

from . import wikifacts as wf

STRENGTHS = ("strong", "medium", "weak", "rejected")
NEWS_MAX_DAYS = 60            # a news article this long after the event is a retrospective


def local_date(begin_date_time: str) -> str:
    """Storm Data's "27-APR-11 15:43:00" (local standard time) as an ISO date."""
    try:
        return dt.datetime.strptime(str(begin_date_time)[:9], "%d-%b-%y").date().isoformat()
    except ValueError:
        return ""


def tornadoes(storm_events: pd.DataFrame) -> dict[str, dict]:
    """One summary per Storm Events tornado (``TORNADO_KEY``): its county rows'
    ids, first local date, states, counties, highest rating, and narratives."""
    out: dict[str, dict] = {}
    se = storm_events.assign(_date=storm_events.BEGIN_DATE_TIME.map(local_date))
    for key, g in se.sort_values("begin_utc").groupby("TORNADO_KEY", sort=False):
        ratings = [wf.rating_rank(r) for r in g.TOR_F_SCALE.astype(str)]
        out[key] = {
            "tornado_key": key,
            "event_ids": sorted(g.EVENT_ID.astype(int).astype(str), key=int),
            "date": g["_date"].iloc[0],
            "states": {s.title() for s in g.STATE.astype(str)},
            "counties": {wf.fold(c) for c in g.CZ_NAME.astype(str)},
            # Storm Data's begin and end towns ("2W ENDERLIN" is the place ENDERLIN).
            "places": {wf.fold(re.sub(r"^\d+(?:\.\d+)?\s*[NSEW]{1,3}\s+", "", str(v)))
                       for c in ("BEGIN_LOCATION", "END_LOCATION") if c in g
                       for v in g[c].dropna() if str(v).strip()} - {""},
            "rating_rank": max(ratings) if ratings else -1,
            "rating": g.TOR_F_SCALE.astype(str).iloc[ratings.index(max(ratings))] if ratings else "",
            "length_mi": round(float(pd.to_numeric(g.TOR_LENGTH, errors="coerce").sum()), 1),
            "deaths": int(pd.to_numeric(g.DEATHS_DIRECT, errors="coerce").fillna(0).sum()),
            "narrative": wf.fold(" ".join(g.EVENT_NARRATIVE.fillna("").astype(str))),
        }
    return out


def checks(*, date: str, states: set[str], places: Iterable[str], rating: str,
           tornado: dict, within_days: int = 0) -> dict:
    """Whether a passage's date, state, places and rating agree with a tornado.

    The date agrees within ±1 day; ``within_days`` widens it forward, for a
    section whose date is only its outbreak's start (the tornado may be any
    day of the outbreak).

    Each check is True, False, or None when the passage gives nothing to check.
    ``consistency``: ``conflict`` when the date or state disagrees,
    ``consistent`` when nothing disagrees and a place or the rating agrees,
    ``partly`` when nothing disagrees and nothing more could be checked.
    """
    date_ok = None
    if date and tornado["date"]:
        gap = (dt.date.fromisoformat(tornado["date"]) - dt.date.fromisoformat(date)).days
        date_ok = -1 <= gap <= max(1, within_days)
    state_ok = bool(states & tornado["states"]) if states else None
    places = [p for p in places if p]
    place_ok = None
    if places:
        hay = (f" {' '.join(sorted(tornado['counties']))} | "
               f"{' | '.join(sorted(tornado.get('places', ())))} | {tornado['narrative']} ")
        place_ok = any(f" {v} " in hay for p in places for v in wf._variants(p))
    rank = wf.rating_rank(rating)
    rating_ok = (rank == tornado["rating_rank"]) if rank >= 0 and tornado["rating_rank"] >= 0 else None
    if date_ok is False or state_ok is False:
        consistency = "conflict"
    elif place_ok or rating_ok:
        consistency = "consistent"
    else:
        consistency = "partly"
    return {"date_ok": date_ok, "state_ok": state_ok, "place_ok": place_ok,
            "rating_ok": rating_ok, "consistency": consistency}


_RANK = {"consistent": 0, "partly": 1, "conflict": 2}


def choose(candidates: dict[str, dict]) -> tuple[str | None, str]:
    """The passage's tornado among those its ids name.

    ``candidates``: ``{tornado_key: {"evidence": set, "consistency": str}}``.
    One tornado: that one (``single``). Several — a comparison, or a section
    that also cites a neighbouring tornado — the one that alone is best by
    consistency, then by how many checks agree (the Perryton article cites an
    EF2 that ended at Perryton's airport beside its EF3), then by kinds of
    evidence naming it (``chosen``); else none (``ambiguous``).
    """
    if not candidates:
        return None, "no_tornado"
    if len(candidates) == 1:
        return next(iter(candidates)), "single"
    score = {k: (_RANK[c["consistency"]],
                 -sum(c.get(f) is True for f in ("date_ok", "state_ok", "place_ok", "rating_ok")),
                 -len(c["evidence"])) for k, c in candidates.items()}
    best = min(score.values())
    top = [k for k, s in score.items() if s == best]
    return (top[0], "chosen") if len(top) == 1 else (None, "ambiguous")


def strength(how: str, check: dict) -> str:
    """``strong`` · ``medium`` · ``weak`` · ``rejected`` for a passage's link.

    strong: the passage names one tornado and its date, state and a place
    all agree. medium: one tornado (or one chosen), nothing disagrees, and a
    place or the rating agrees. weak: nothing disagrees but nothing more could
    be checked, or the tornado had to be chosen among several. rejected: the
    date or state disagrees.
    """
    if check["consistency"] == "conflict":
        return "rejected"
    if how == "single" and check["consistency"] == "consistent" and check["date_ok"] \
            and check["state_ok"] and check["place_ok"]:
        return "strong"
    if check["consistency"] == "consistent" and how in ("single", "chosen"):
        return "medium" if how == "single" else "weak"
    return "weak"


def names_in_prose(names: Iterable[str], text: str) -> bool:
    """Whether a proper name occurs in ``text`` as one: capitalised as given,
    whole words, and not as a sentence's first word. For gazetteer towns,
    many of which are also words ("Power", North Dakota; "Liberty")."""
    text = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode()
    for name in names:
        if len(name) < 4 or not name[:1].isupper():
            continue
        for m in re.finditer(rf"(?<![\w-]){re.escape(name)}(?![\w-])", text):
            before = text[:m.start()].rstrip()
            if before and before[-1] not in '.!?"\u201c\u2018\'(:\n':
                return True
    return False


def news_checks(*, published: str, event_date: str, text: str, places: Iterable[str],
                counties: Iterable[str], towns: Iterable[str] = (), title: str = "",
                path_towns: Iterable[str] = ()) -> dict:
    """A cited article's own fit: its date relative to the tornado's, and
    whether its headline or text names a place of the tornado's: a heading
    town, a county or Storm Data's begin or end town anywhere; a gazetteer
    town on or near the path (``path_towns``, as GNIS spells them) only as a
    proper name in the headline or text (:func:`names_in_prose`). ``text`` is "" when there
    is no intact text to check: a headline naming a place still counts, but
    one naming none says nothing (``mentions_place`` None)."""
    days = None
    if published and event_date and re.fullmatch(r"\d{4}-\d{2}-\d{2}", published[:10]):
        days = (dt.date.fromisoformat(published[:10]) - dt.date.fromisoformat(event_date)).days
    names = ([v for p in places if p for v in wf._variants(p)]
             + [c for c in (*counties, *towns) if len(c) > 3])
    hay = f" {wf.fold(title)} {wf.fold(text)} "
    mentions = any(f" {n} " in hay for n in names) or names_in_prose(path_towns, f"{title}\n{text}")
    if not text and not mentions:
        mentions = None
    return {"days_after_event": days,
            "date_ok": None if days is None else -1 <= days <= NEWS_MAX_DAYS,
            "mentions_place": mentions}


def news_strength(passage_strengths: Iterable[str], check: dict) -> str:
    """The weakest citing passage's strength; ``rejected`` when the article's
    intact text names none of the tornado's places; one step down when it was
    published before the event or is a retrospective."""
    order = {s: i for i, s in enumerate(STRENGTHS)}
    base = max(passage_strengths, key=order.__getitem__)
    if base == "rejected" or check["mentions_place"] is False:
        return "rejected"
    if check["date_ok"] is False:
        return STRENGTHS[min(order[base] + 1, order["weak"])]
    return base


def reject_reason(kind: str, check: dict) -> str:
    """Why a link was rejected, for the report and the viewer."""
    if kind == "wikipedia_passage":
        parts = [n for n, k in (("date", "date_ok"), ("state", "state_ok")) if check.get(k) is False]
        return f"{' and '.join(parts)} disagree with the cited record" if parts else ""
    if check.get("mentions_place") is False:
        return "names none of the tornado's places"
    return ""


def corpus_items(links: pd.DataFrame, ids_col: str) -> tuple[pd.DataFrame, int]:
    """One row per item of another corpus that tornado-level links name.

    ``ids_col`` holds "|"-joined item ids (Media Cloud story ids, say). Several
    cited articles can be one item — wire copy cited from two outlets, both
    found as one Media Cloud story — so an item takes its tornado only when
    every link naming it agrees, and the weakest of their strengths. Rejected
    links name nothing. Returns the items and the number dropped because their
    links disagree.
    """
    h = links[(links.link_level == "hazard") & (links.strength != "rejected")
              & (links[ids_col].fillna("") != "")]
    if h.empty:
        return pd.DataFrame(columns=["item_id", "tornado_key", "strength", "n_links",
                                     "text_uids"]), 0
    rows = h.assign(item_id=h[ids_col].str.split("|")).explode("item_id")
    order = {s: i for i, s in enumerate(STRENGTHS)}
    out, conflicts = [], 0
    for item, g in rows.groupby("item_id", sort=False):
        if g.tornado_key.nunique() > 1:
            conflicts += 1
            continue
        out.append({"item_id": item, "tornado_key": g.tornado_key.iloc[0],
                    "strength": max(g.strength, key=order.__getitem__), "n_links": len(g),
                    "text_uids": "|".join(sorted(set(g.text_uid)))})
    return pd.DataFrame(out), conflicts

"""SPC's tornado database — one reviewed record per whole tornado track.

The Storm Prediction Center keeps its own tornado database, compiled from the
same *Storm Data* submissions as NCEI Storm Events but reviewed by SPC and NCEI
and stitched into whole tracks (Schaefer & Edwards 1999, "The SPC
tornado/severe thunderstorm database", 11th Conf. Applied Climatology,
215–220). ``YYYY-YYYY_actual_tornadoes.csv`` at :data:`SPC_DIR` holds one
record per tornado; the ``all_tornadoes`` file keeps state and county segments.

It is the tornado-level reference here: an official version of what
:func:`storm_events.chain_segments` reconstructs from ``TOR_OTHER_*`` pointers,
back to 1950. It has **no episodes**, so it says nothing about grouping.

Format, from SPC's specification (last revised 2010 — check the header of a
new file before trusting field meanings):

* ``om`` is the tornado number *within a year* up to September 2007;
  ``yr``+``om`` identifies one. From October 2007 it is a text identifier,
  ``YYMMDDHHMM-NN`` — the start time (CST) and a sequence number for tornadoes
  starting in the same minute — so it is kept as a string, never cast to int.
* ``ns``/``sn``/``sg`` mark whole-track (``sg == 1``), state-segment (2) and
  continuing-county (−9) records. The "actual" file should hold ``sg == 1``
  only; anything else is dropped and counted.
* ``tz`` 3 means CST (UTC−6), 9 means GMT, and SPC converts nearly every record
  to CST. Like Storm Data, there is no daylight saving.
* An end coordinate of 0.0 means unknown: the track is then a point.
* ``mag`` is the (E)F rating, −9 unknown; ``edat``/``etime``, added after the
  2010 specification, are an end date and time where given.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

SPC_PAGE = "https://www.spc.noaa.gov/wcm/"
SPC_DIR = SPC_PAGE + "data/"
_ACTUAL_RE = re.compile(r"(\d{4})-(\d{4})_actual_tornadoes\.csv")
_TZ_OFFSET_H = {"3": -6, "9": 0}


def latest_file(listing_html: str) -> str | None:
    """The ``actual_tornadoes`` file with the latest end year on the page."""
    names = {m.group(0): int(m.group(2)) for m in _ACTUAL_RE.finditer(listing_html)}
    return max(names, key=names.get) if names else None


def download(dest: Path, *, session=None) -> dict:
    """Fetch the newest ``actual_tornadoes`` file into ``dest``; skip if present."""
    import requests
    from ..http import utcnow_iso

    session = session or requests.Session()
    session.headers.setdefault("User-Agent",
                               "tornado-text-to-trajectory/0.1 (academic research)")
    page = session.get(SPC_PAGE, timeout=60)
    page.raise_for_status()
    name = latest_file(page.text)
    if name is None:
        return {"file": None, "status": "not_found_on_page"}
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / name
    if target.exists():
        return {"file": name, "status": "present"}
    response = session.get(SPC_DIR + name, timeout=300)
    response.raise_for_status()
    tmp = target.with_suffix(".part")
    tmp.write_bytes(response.content)
    tmp.rename(target)
    return {"file": name, "status": "downloaded", "url": SPC_DIR + name,
            "retrieved_at": utcnow_iso(), "bytes": len(response.content)}


def local_file(directory: Path) -> Path | None:
    name = latest_file("\n".join(p.name for p in directory.glob("*_actual_tornadoes.csv")))
    return directory / name if name else None


def load(path: Path, years: range | list[int] | None = None) -> tuple[pd.DataFrame, dict]:
    """Whole-track records with UTC times and a stable ``spc_id``.

    Returns the frame and a dict of counts of what was dropped and why, so the
    report can say so rather than silently shrinking the reference.
    """
    raw = pd.read_csv(path, dtype={"tz": str}, low_memory=False)
    notes = {"rows": len(raw)}
    df = raw if years is None else raw[raw.yr.isin(list(years))]
    notes["in_window"] = len(df)
    if "sg" in df.columns:
        notes["dropped_not_whole_track"] = int((df.sg != 1).sum())
        df = df[df.sg == 1]
    offset = df.tz.astype(str).str.strip().map(_TZ_OFFSET_H)
    notes["dropped_unknown_tz"] = int(offset.isna().sum())
    df = df[offset.notna()].copy()
    offset = offset[offset.notna()]
    local = pd.to_datetime(df.date.astype(str) + " " + df.time.astype(str), errors="coerce")
    df["begin_utc"] = (local - pd.to_timedelta(offset, unit="h")).dt.tz_localize("UTC")
    end_utc = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns, UTC]")
    if {"edat", "etime"} <= set(df.columns):
        end_local = pd.to_datetime(df.edat.astype(str) + " " + df.etime.astype(str),
                                   errors="coerce")
        end_utc = (end_local - pd.to_timedelta(offset, unit="h")).dt.tz_localize("UTC")
    # Same guard as DAT's: an end before the start, or hours later, is not an end.
    span = (end_utc - df.begin_utc).dt.total_seconds()
    df["end_utc"] = end_utc.where((span >= 0) & (span <= 5 * 3600), df.begin_utc)
    df["spc_id"] = ("spc_" + df.yr.astype(int).astype(str) + "_"
                    + df.om.astype(str).str.strip())
    notes["duplicate_ids"] = int(df.spc_id.duplicated().sum())
    df = df.drop_duplicates("spc_id").reset_index(drop=True)
    notes["kept"] = len(df)
    return df, notes


def track_geometries(df: pd.DataFrame, project) -> list:
    """Start→end segment per tornado, projected; a point when the end is unknown."""
    from shapely.geometry import LineString, Point
    out = []
    for a, b, c, d in zip(df.slon, df.slat, df.elon, df.elat):
        if pd.isna(a) or pd.isna(b) or (a == 0 and b == 0):
            out.append(None)
        elif pd.isna(c) or pd.isna(d) or (c == 0 and d == 0) or (a, b) == (c, d):
            out.append(project(Point(a, b)))
        else:
            out.append(project(LineString([(a, b), (c, d)])))
    return out


# ── matching ────────────────────────────────────────────────────────────────
def join_hazards(spc: pd.DataFrame, geoms: list, hazards: pd.DataFrame, **tol) -> pd.DataFrame:
    """SPC tornado ↔ DAT hazard pairs, by the same rule as Storm Events."""
    from .storm_events import match_pairs

    pairs = match_pairs(spc.begin_utc, spc.end_utc, geoms, hazards, **tol)
    cols = ["spc_id", "hazard_uid", "distance_m", "gap_s", "rank_for_event",
            "rank_for_hazard", "link_method"]
    if pairs.empty:
        return pd.DataFrame(columns=cols)
    pairs["spc_id"] = spc.spc_id.to_numpy()[pairs.row]
    pairs["hazard_uid"] = hazards.hazard_uid.to_numpy()[pairs.hz]
    pairs["link_method"] = "spatial_temporal_join"
    return pairs[cols].sort_values(["hazard_uid", "rank_for_hazard"])


# ── second pass: DAT clock and date errors ──────────────────────────────────
# A DAT hazard that the strict rule leaves unmatched very often has an SPC
# track within metres whose start differs by a whole number of hours, to the
# minute: the survey's time was saved in the wrong zone (local time stored as
# UTC, +4…+7 h), off by daylight saving (±1 h), or on the wrong date (±24 h).
# Random coincidences fall anywhere in the hour; these pile up on it.
REPAIR_MAX_OFFSET_H = 48
REPAIR_MAX_RESIDUAL_MIN = 10.0
_HOUR_PART = {0: "", 1: "dst", -1: "dst", **{k: "local_as_utc" for k in range(4, 8)},
              **{-k: "utc_as_local" for k in range(4, 8)}}


def offset_class(k: int) -> str:
    """Name a whole-hour offset (SPC start − DAT start) by its likely cause.

    Split into whole days and the remaining hours, each named on its own:
    ``date±n`` for the days; ``dst`` (±1 h), ``local_as_utc`` (+4…+7 h:
    the local clock saved as if it were UTC, so DAT is early) or
    ``utc_as_local`` (−4…−7 h: converted twice) for the hours; any other
    hour count is ``unexplained``.
    """
    days = int(round(k / 24))
    hours = int(k - 24 * days)
    parts = [f"date{days:+d}"] if days else []
    hour_part = _HOUR_PART.get(hours, "unexplained")
    if hour_part:
        parts.append(hour_part)
    return "+".join(parts) or "none"


_EF_DIGIT = re.compile(r"(\d)")


def ef_number(value) -> float:
    """DAT's ``efscale`` text ("EF2", "EFU") as a number; NaN when unrated."""
    m = _EF_DIGIT.search(str(value)) if pd.notna(value) else None
    return float(m.group(1)) if m else np.nan


def repair_time_links(spc: pd.DataFrame, geoms: list, hazards: pd.DataFrame,
                      links: pd.DataFrame, *,
                      max_distance_m: float | None = None,
                      max_offset_h: int = REPAIR_MAX_OFFSET_H,
                      max_residual_min: float = REPAIR_MAX_RESIDUAL_MIN,
                      ) -> tuple[pd.DataFrame, dict]:
    """Second pass for DAT hazards the strict rule left without an SPC track.

    A pair qualifies when the SPC track is within ``max_distance_m`` of the
    hazard's track (the same distance as the first pass) and the two starts
    differ by a whole number of hours, ``1 ≤ |k| ≤ max_offset_h``, to within
    ``max_residual_min``. Each hazard's candidates are ranked by distance, then
    residual; ``rank_for_hazard == 1`` is the link consumers take. DAT's own
    times are never changed — the offset is recorded on the link.

    Returns the links (``link_method`` ``time_repaired``, with ``time_offset_h``,
    ``offset_class``, ``residual_min``, ``spc_already_linked`` — the SPC track
    also has a first-pass DAT hazard, so this one is probably a second survey
    of it — and ``ef_agrees``) and a dict for the report: the candidate counts
    by residual, from which a chance rate is estimated.
    """
    from shapely import STRtree
    from .storm_events import MATCH_DISTANCE_M

    max_distance_m = MATCH_DISTANCE_M if max_distance_m is None else max_distance_m
    cols = ["spc_id", "hazard_uid", "distance_m", "gap_s", "rank_for_event",
            "rank_for_hazard", "link_method", "time_offset_h", "offset_class",
            "residual_min", "spc_already_linked", "ef_agrees"]
    todo = hazards[~hazards.hazard_uid.isin(set(links.hazard_uid))
                   & hazards.track.notna() & hazards.t0.notna()]
    valid = [i for i, g in enumerate(geoms) if g is not None]
    tree = STRtree([geoms[i] for i in valid])
    begin = spc.begin_utc.to_numpy()
    rows = []
    for r in todo.itertuples():
        for hit in tree.query(r.track.buffer(max_distance_m)):
            i = valid[int(hit)]
            dist = r.track.distance(geoms[i])
            if dist > max_distance_m:
                continue
            diff_h = (pd.Timestamp(begin[i]) - r.t0).total_seconds() / 3600
            k = int(round(diff_h))
            if 1 <= abs(k) <= max_offset_h:
                rows.append((i, r.hazard_uid, dist, k, (diff_h - k) * 60, r.efscale))
    cand = pd.DataFrame(rows, columns=["i", "hazard_uid", "distance_m", "time_offset_h",
                                       "residual_min", "efscale"])
    res = cand.residual_min.abs()
    stats = {"hazards_tried": len(todo), "candidates": len(cand),
             "max_residual_min": max_residual_min, "max_offset_h": max_offset_h,
             "max_distance_m": max_distance_m,
             "candidates_residual_le_2": int((res <= 2).sum()),
             "candidates_residual_le_tol": int((res <= max_residual_min).sum()),
             "candidates_residual_20_30": int((res > 20).sum())}
    # Pairs that are not one tornado fall anywhere in the hour; their density
    # far from it (20–30 min) times the window kept estimates how many of the
    # kept candidates are chance. An upper bound: it counts candidates, and
    # most hazards with a chance candidate also have a real one.
    stats["chance_candidates_est"] = stats["candidates_residual_20_30"] / 10 * max_residual_min
    cand = cand[res <= max_residual_min].copy()
    if cand.empty:
        return pd.DataFrame(columns=cols), stats
    cand["spc_id"] = spc.spc_id.to_numpy()[cand.i]
    cand["gap_s"] = cand.residual_min.abs() * 60
    cand["_abs_k"] = cand.time_offset_h.abs()
    order = ["distance_m", "gap_s", "_abs_k"]
    cand = cand.sort_values(order)
    cand["rank_for_hazard"] = cand.groupby("hazard_uid").cumcount() + 1
    cand["rank_for_event"] = cand.groupby("spc_id").cumcount() + 1
    cand["link_method"] = "time_repaired"
    cand["offset_class"] = cand.time_offset_h.map(offset_class)
    cand["spc_already_linked"] = cand.spc_id.isin(set(links.spc_id))
    cand["ef_agrees"] = ef_agrees(cand, spc, hazards)
    return cand[cols].sort_values(["hazard_uid", "rank_for_hazard"]), stats


def ef_agrees(links: pd.DataFrame, spc: pd.DataFrame, hazards: pd.DataFrame) -> pd.Series:
    """Per link: do DAT's rating and SPC's agree? Missing when either is unrated."""
    ef = links.hazard_uid.map(hazards.set_index("hazard_uid").efscale.map(ef_number))
    mag = links.spc_id.map(spc.set_index("spc_id").mag).astype(float)
    known = ef.notna() & mag.notna() & (mag >= 0)
    return (ef == mag).astype(object).where(known)


def with_first_pass_columns(links: pd.DataFrame, spc: pd.DataFrame,
                            hazards: pd.DataFrame) -> pd.DataFrame:
    """First-pass links in the shape of :func:`repair_time_links`'s, so both stack."""
    return links.assign(time_offset_h=0, offset_class="none",
                        residual_min=links.gap_s / 60, spc_already_linked=False,
                        ef_agrees=ef_agrees(links, spc, hazards))


def chance_ef_agreement(spc: pd.DataFrame, hazards: pd.DataFrame) -> float:
    """How often two ratings drawn independently from DAT's and SPC's mix agree.

    The floor for the second pass's rating agreement: links between unrelated
    tornadoes would agree about this often; links between the same tornado
    about as often as the first pass's do.
    """
    pe = hazards.efscale.map(ef_number).value_counts(normalize=True)
    pm = spc.mag[spc.mag >= 0].value_counts(normalize=True)
    return float(sum(pe.get(k, 0) * pm.get(k, 0) for k in range(6)))


# DAT's ``event_id`` is free text that offices fill as they like; some put the
# date in it ("greenwood_20200112", "UNR-2019-0629-Allen", "7/12/16 Chip
# Falls"). Where it does, it is a check on a date repair that does not depend
# on DAT's time field. Only unambiguous forms are read.
_ID_DATES = [
    (re.compile(r"(?<!\d)(20[0-2]\d)[-_]?([01]\d)[-_]?([0-3]\d)(?!\d)"), (1, 2, 3)),
    (re.compile(r"(?<!\d)([01]\d)([0-3]\d)(20[0-2]\d)(?!\d)"), (3, 1, 2)),
    (re.compile(r"(?<!\d)(\d{1,2})/(\d{1,2})/(\d{2}|\d{4})(?!\d)"), (3, 1, 2)),
]


def event_id_dates(text) -> set:
    """Calendar dates written in a DAT ``event_id``; empty when none is legible."""
    import datetime as dt
    out = set()
    if not isinstance(text, str):
        return out
    for pattern, (yi, mi, di) in _ID_DATES:
        for m in pattern.finditer(text):
            y, mo, d = int(m.group(yi)), int(m.group(mi)), int(m.group(di))
            y = y + 2000 if y < 100 else y
            try:
                out.add(dt.date(y, mo, d))
            except ValueError:
                pass
    return out


def event_id_date_check(links: pd.DataFrame, spc: pd.DataFrame,
                        hazards: pd.DataFrame) -> pd.Series:
    """Per link: does a date in DAT's ``event_id`` side with SPC or with DAT?

    ``spc`` when it is SPC's start date in local standard time (CST, as SPC
    records it) and not DAT's, ``dat`` the reverse, ``both`` / ``neither``, and
    missing when the ``event_id`` holds no legible date. Local dates either way,
    since an office writes its own date; CST is within an hour of every zone
    with many tornadoes.
    """
    cst = pd.Timedelta(hours=6)
    spc_day = links.spc_id.map(spc.set_index("spc_id").begin_utc).sub(cst).dt.date
    hz = hazards.set_index("hazard_uid")
    dat_day = links.hazard_uid.map(hz.t0).sub(cst).dt.date
    ids = links.hazard_uid.map(hz.dat_event_ids)
    out = []
    for text, a, b in zip(ids, spc_day, dat_day):
        days = event_id_dates(text)
        if not days:
            out.append(None)
            continue
        out.append({(True, False): "spc", (False, True): "dat",
                    (True, True): "both", (False, False): "neither"}[(a in days, b in days)])
    return pd.Series(out, index=links.index, dtype=object)


def nearest_unlinked(spc: pd.DataFrame, geoms: list, hazards: pd.DataFrame,
                     links: pd.DataFrame, *, within_m: float = 20_000.0,
                     within_h: float = 72.0) -> pd.DataFrame:
    """DAT hazards with no SPC track after both passes, and their nearest one.

    For the hand check of what is left: the nearest SPC track within
    ``within_m`` and ``within_h`` (nearest in space, then time), or none. A
    hazard with nothing near is a candidate for "not in the official record" —
    reclassified, never submitted, or a duplicate or test entry in DAT.
    """
    from shapely import STRtree

    left = hazards[~hazards.hazard_uid.isin(set(links.hazard_uid))]
    valid = [i for i, g in enumerate(geoms) if g is not None]
    tree = STRtree([geoms[i] for i in valid])
    begin = spc.begin_utc.to_numpy()
    rows = []
    for r in left.itertuples():
        best = (None, np.nan, np.nan)
        if r.track is not None and pd.notna(r.t0):
            for hit in tree.query(r.track.buffer(within_m)):
                i = valid[int(hit)]
                dt_h = (pd.Timestamp(begin[i]) - r.t0).total_seconds() / 3600
                d = r.track.distance(geoms[i])
                if abs(dt_h) <= within_h and d <= within_m and (
                        best[0] is None or (d, abs(dt_h)) < (best[1], abs(best[2]))):
                    best = (spc.spc_id.iat[i], d, dt_h)
        rows.append({"hazard_uid": r.hazard_uid, "year": r.t0.year if pd.notna(r.t0) else None,
                     "time_begin_utc": r.time_begin_utc, "efscale": r.efscale,
                     "path_length_mi": r.path_length_mi, "wfo": r.wfo,
                     "dat_event_ids": r.dat_event_ids, "nearest_spc_id": best[0],
                     "nearest_distance_km": best[1] / 1000, "nearest_offset_h": best[2]})
    return pd.DataFrame(rows)


def join_storm_events(se: pd.DataFrame, se_geoms: list, spc: pd.DataFrame,
                      spc_geoms: list, **tol) -> pd.DataFrame:
    """Storm Events row ↔ SPC track pairs, by the same rule as DAT.

    Columns as :func:`storm_events.join_hazards`, with ``spc_id`` in place of
    ``hazard_uid``: ``rank_for_event`` 1 is each row's closest SPC track,
    ``rank_for_hazard`` 1 each SPC track's closest row. These pairs carry the
    Storm Events episodes to SPC tracks for stage 51, and feed the chaining check.
    """
    from .storm_events import join_hazards

    targets = pd.DataFrame({"hazard_uid": spc.spc_id.to_numpy(), "geom": spc_geoms,
                            "t0": spc.begin_utc.to_numpy(), "t1": spc.end_utc.to_numpy()})
    return join_hazards(se, se_geoms, targets, **tol).rename(columns={"hazard_uid": "spc_id"})


def crosscheck_chains(links: pd.DataFrame, se: pd.DataFrame) -> dict[str, float]:
    """Do Storm Events chains and SPC whole tracks describe the same tornadoes?

    ``links`` from :func:`join_storm_events`. Each Storm Events row is taken at
    its closest SPC track. A chain (``TORNADO_KEY``) agrees when all its rows
    land on one SPC tornado and no other chain lands there too. A chain spread
    over two SPC tornadoes is an over-chain (or two SPC records for one
    tornado); two chains on one SPC tornado is a missed link — usually an
    unresolved ``TOR_OTHER_*`` pointer.
    """
    best = links[links.rank_for_event == 1]
    m = pd.DataFrame({"chain": best.TORNADO_KEY.to_numpy(), "spc": best.spc_id.to_numpy()})
    per_chain = m.groupby("chain").spc.nunique()
    per_spc = m.groupby("spc").chain.nunique()
    one_to_one = per_chain[per_chain == 1].index
    agree = m[m.chain.isin(one_to_one)].groupby("chain").spc.first()
    agree = agree[agree.map(per_spc) == 1]
    chains = se.TORNADO_KEY.nunique()
    return {
        "se_chains": chains,
        "se_chains_matched": int(m.chain.nunique()),
        "chains_one_to_one": int(len(agree)),
        "chains_split_over_spc": int((per_chain > 1).sum()),
        "spc_with_several_chains": int((per_spc > 1).sum()),
        "share_one_to_one": len(agree) / max(int(m.chain.nunique()), 1),
    }

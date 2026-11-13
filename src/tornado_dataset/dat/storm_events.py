"""NCEI Storm Events — the NWS's own tornado records, as a reference for DAT.

The Storm Events Database is compiled from *Storm Data*, which each NWS forecast
office files for its own area. It is the reference DAT is checked against here,
for two things DAT cannot tell us about itself:

* **completeness** — DAT was adopted unevenly by the offices, so the earlier
  years hold a fraction of the tornadoes. Matched against Storm Events, 2015 DAT
  holds 459 hazards where Storm Events lists 1,320 tornado rows, and 2025 DAT
  1,162 against 1,591; and
* **an independent grouping** — ``EPISODE_ID``, the forecaster's own judgement
  of which events belong to one weather system, used by
  ``scripts/51_compare_episodes.py`` as the reference partition.

Three properties shape every use of it:

1. **One row per tornado per county.** A tornado crossing a county line gets a
   row in each, and each row names the county it continued into in
   ``TOR_OTHER_*``. :func:`chain_segments` follows those pointers to rebuild whole
   tornadoes (``TORNADO_KEY``); raw row counts are county segments.
2. **Local standard time all year**, with the offset in ``CZ_TIMEZONE``
   (``"CST-6"``). Daylight saving is never applied; :func:`to_utc` relies on that.
3. **Episodes are per office.** No ``EPISODE_ID`` spans two WFOs, because each
   office files its own. A tornado that crosses into another office's area
   ties the two offices' episodes together; :func:`link_episodes` joins them
   into ``LINKED_EPISODE``. That reconnects only offices a tornado physically
   crossed between — on the 2015 and 2025 files, 5% fewer episodes and ~3% of
   them multi-office — so a multi-state outbreak remains several episodes. They
   can check a grouping (an episode should rarely be split) but not define one.

The files are published per year at :data:`NCEI_DIR` and revised in place — the
creation stamp in the filename (``_c20260819``) changes — so the latest version
is discovered from the directory listing, never hard-coded.
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

NCEI_DIR = "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/"
_DETAILS_RE = re.compile(r"StormEvents_details-ftp_v1\.0_d(\d{4})_c(\d{8})\.csv\.gz")

# Bare abbreviations appear in some older files; the offsets are standard time.
_TZ_OFFSET = {"EST": -5, "CST": -6, "MST": -7, "PST": -8, "AKST": -9, "HST": -10,
              "AST": -4, "SST": -11, "GST": 10}

# A TOR_OTHER_* pointer names a county, not a row; the continuation row is the
# one in that office and county whose time is within this of the pointing row.
CONTINUATION_GAP_S = 1_800.0

# Matching a Storm Events row to a DAT hazard. Both are surveys of the same
# tornado by the same office, so a correct pair is usually metres apart and
# minutes apart; the tolerances absorb rounding of coordinates and times.
MATCH_DISTANCE_M = 5_000.0
MATCH_GAP_S = 1_800.0
# For DAT hazards with a date but no time (damage polygons surveyed without one):
# the official record's UTC start date within this many days of it.
MATCH_DATE_DAYS = 1

KEEP = ["EVENT_ID", "EPISODE_ID", "WFO", "STATE", "CZ_FIPS", "CZ_NAME",
        "BEGIN_DATE_TIME",
        "END_DATE_TIME", "CZ_TIMEZONE", "TOR_F_SCALE", "TOR_LENGTH", "TOR_WIDTH",
        "TOR_OTHER_WFO", "TOR_OTHER_CZ_STATE", "TOR_OTHER_CZ_FIPS",
        "TOR_OTHER_CZ_NAME", "BEGIN_LAT",
        "BEGIN_LON", "END_LAT", "END_LON", "BEGIN_LOCATION", "END_LOCATION",
        "INJURIES_DIRECT", "DEATHS_DIRECT",
        "DAMAGE_PROPERTY", "EPISODE_NARRATIVE", "EVENT_NARRATIVE"]


# ── download ────────────────────────────────────────────────────────────────
def latest_files(listing_html: str) -> dict[int, str]:
    """Newest details file per data year, from the NCEI directory listing."""
    best: dict[int, tuple[str, str]] = {}
    for match in _DETAILS_RE.finditer(listing_html):
        name, (year, stamp) = match.group(0), match.groups()
        if int(year) not in best or stamp > best[int(year)][1]:
            best[int(year)] = (name, stamp)
    return {year: name for year, (name, _) in best.items()}


def download(years: Iterable[int], dest: Path, *, session=None,
             pause_s: float = 1.0) -> list[dict]:
    """Fetch the newest details file for each year into ``dest``.

    A file already present under the same name is not fetched again; a newer
    revision is fetched alongside it, and :func:`details_paths` picks the newest.
    Returns one provenance record per file.
    """
    import requests
    from ..http import utcnow_iso

    session = session or requests.Session()
    session.headers.setdefault("User-Agent",
                               "tornado-text-to-trajectory/0.1 (academic research)")
    listing = session.get(NCEI_DIR, timeout=60)
    listing.raise_for_status()
    available = latest_files(listing.text)
    dest.mkdir(parents=True, exist_ok=True)
    records = []
    for year in years:
        name = available.get(year)
        if name is None:
            records.append({"year": year, "file": None, "status": "not_published"})
            continue
        target = dest / name
        if target.exists():
            records.append({"year": year, "file": name, "status": "present"})
            continue
        response = session.get(NCEI_DIR + name, timeout=300)
        response.raise_for_status()
        tmp = target.with_suffix(".part")
        tmp.write_bytes(response.content)
        tmp.rename(target)
        records.append({"year": year, "file": name, "status": "downloaded",
                        "url": NCEI_DIR + name, "retrieved_at": utcnow_iso(),
                        "bytes": len(response.content)})
        time.sleep(pause_s)
    return records


def details_paths(directory: Path) -> dict[int, Path]:
    """Newest local details file per year."""
    return {year: directory / name
            for year, name in latest_files("\n".join(p.name for p in directory.glob(
                "StormEvents_details-*.csv.gz"))).items()}


# ── normalisation ───────────────────────────────────────────────────────────
def to_utc(local: pd.Series, zone: pd.Series) -> pd.Series:
    """Storm Data's local *standard* time to UTC, using ``CZ_TIMEZONE``."""
    offset = pd.to_numeric(zone.astype(str).str.extract(r"([+-]\d+)$")[0], errors="coerce")
    bare = zone.astype(str).str.extract(r"^([A-Z]+)")[0].map(_TZ_OFFSET)
    offset = offset.fillna(bare)
    moment = pd.to_datetime(local, format="%d-%b-%y %H:%M:%S", errors="coerce")
    return (moment - pd.to_timedelta(offset, unit="h")).dt.tz_localize("UTC")


def load_tornadoes(paths: Iterable[Path]) -> pd.DataFrame:
    """Tornado rows from the given details files, with UTC times."""
    frames = []
    for path in paths:
        d = pd.read_csv(path, low_memory=False)
        d = d[d.EVENT_TYPE == "Tornado"]
        frames.append(d[[c for c in KEEP if c in d.columns]])
    if not frames:
        return pd.DataFrame(columns=KEEP)
    t = pd.concat(frames, ignore_index=True)
    t["begin_utc"] = to_utc(t.BEGIN_DATE_TIME, t.CZ_TIMEZONE)
    t["end_utc"] = to_utc(t.END_DATE_TIME, t.CZ_TIMEZONE).fillna(t.begin_utc)
    t = t.drop_duplicates("EVENT_ID").reset_index(drop=True)
    t["TORNADO_KEY"] = chain_segments(t)
    t["LINKED_EPISODE"] = link_episodes(t)
    return t


# ── segments → tornadoes → linked episodes ──────────────────────────────────
def _county_key(wfo, state, fips) -> str | None:
    if pd.isna(wfo) or pd.isna(state) or pd.isna(fips):
        return None
    return f"{str(wfo).upper()}|{str(state).upper()}|{int(fips)}"


def chain_segments(t: pd.DataFrame, max_gap_s: float = CONTINUATION_GAP_S) -> pd.Series:
    """Whole-tornado key per row, by following ``TOR_OTHER_*`` pointers.

    A pointer gives the office, state and county the tornado continued into.
    The continuation is the row there whose begin or end lies within
    ``max_gap_s`` of this row's interval, closest to where this row ends.
    Unresolved pointers (no such row — usually a timing or coding difference)
    leave the row as its own tornado. The key is the smallest ``EVENT_ID`` of
    the chain, so it is stable across reruns on the same file.
    """
    from ..text.linking import STATE_ABBREV
    from .hazards import UnionFind

    abbrev = t.STATE.astype(str).str.lower().map(STATE_ABBREV)
    own = [_county_key(w, s, f) for w, s, f in zip(t.WFO, abbrev, t.CZ_FIPS)]
    rows_at: dict[str, list[int]] = {}
    for i, key in enumerate(own):
        if key:
            rows_at.setdefault(key, []).append(i)

    b = t.begin_utc.to_numpy()
    e = t.end_utc.to_numpy()
    uf = UnionFind(len(t))
    for i in np.nonzero(t.TOR_OTHER_WFO.notna().to_numpy())[0]:
        target = _county_key(t.TOR_OTHER_WFO.iat[i], t.TOR_OTHER_CZ_STATE.iat[i],
                             t.TOR_OTHER_CZ_FIPS.iat[i])
        best, best_d = None, None
        for j in rows_at.get(target, []):
            if j == i:
                continue
            gap = min(abs((b[j] - e[i]) / np.timedelta64(1, "s")),
                      abs((e[j] - b[i]) / np.timedelta64(1, "s")),
                      abs((b[j] - b[i]) / np.timedelta64(1, "s")))
            if gap > max_gap_s:
                continue
            d = np.hypot(t.BEGIN_LAT.iat[j] - t.END_LAT.iat[i],
                         t.BEGIN_LON.iat[j] - t.END_LON.iat[i])
            if best is None or d < best_d:
                best, best_d = j, d
        if best is not None:
            uf.union(i, best, "tor_other")
    root = pd.Series([uf.find(i) for i in range(len(t))])
    smallest = t.EVENT_ID.groupby(root).transform("min")
    return "setor_" + smallest.astype("int64").astype(str)


def link_episodes(t: pd.DataFrame) -> pd.Series:
    """Episodes joined wherever one tornado has segments in both.

    Keyed by the smallest ``EPISODE_ID`` in the linked group. Only tornadoes
    that cross an office boundary can join two offices' episodes, since a
    county crossing inside one office stays inside one episode.
    """
    from .hazards import UnionFind

    episodes = pd.unique(t.EPISODE_ID)
    pos = {ep: k for k, ep in enumerate(episodes)}
    uf = UnionFind(len(episodes))
    for _, eps in t.groupby("TORNADO_KEY").EPISODE_ID:
        first = pos[eps.iat[0]]
        for other in eps.iloc[1:]:
            uf.union(first, pos[other], "shared_tornado")
    root = pd.Series({ep: uf.find(k) for ep, k in pos.items()})
    smallest = pd.Series(episodes, index=episodes).groupby(root).transform("min")
    return "selep_" + t.EPISODE_ID.map(smallest).astype("int64").astype(str)


def row_geometries(tornadoes: pd.DataFrame, project) -> list:
    """Begin→end segment per row, projected; a point when they coincide."""
    from shapely.geometry import LineString, Point
    out = []
    for a, b, c, d in zip(tornadoes.BEGIN_LON, tornadoes.BEGIN_LAT,
                          tornadoes.END_LON, tornadoes.END_LAT):
        if pd.isna(a) or pd.isna(b):
            out.append(None)
            continue
        if pd.isna(c) or pd.isna(d) or (a, b) == (c, d):
            out.append(project(Point(a, b)))
        else:
            out.append(project(LineString([(a, b), (c, d)])))
    return out


# ── join to DAT hazards ─────────────────────────────────────────────────────
def match_pairs(begin: pd.Series, end: pd.Series, geoms: list, targets: pd.DataFrame, *,
                max_distance_m: float = MATCH_DISTANCE_M,
                max_gap_s: float = MATCH_GAP_S,
                max_days: int = MATCH_DATE_DAYS) -> pd.DataFrame:
    """Every (record, target) pair within a distance and a time gap.

    ``targets`` needs ``geom`` (projected, metres), ``t0`` and ``t1`` (UTC).
    Returns positional ``row`` and ``hz`` indices with ``distance_m`` and
    ``gap_s``. Shared by every source matched against DAT, so they are matched
    by the same rule.

    A target with no time but a ``date`` (a DAT damage polygon whose survey
    gives only the date) is matched by the same distance and a date within
    ``max_days`` of the record's UTC start date instead; its ``gap_s`` is
    missing and ``by_date`` true. It ranks after timed pairs at the same
    distance.
    """
    from shapely import STRtree

    valid = [i for i, g in enumerate(targets.geom) if g is not None]
    tree = STRtree([targets.geom.iloc[i] for i in valid])
    t0 = targets.t0.to_numpy()
    t1 = targets.t1.to_numpy()
    dates = targets["date"].to_numpy() if "date" in targets.columns else [None] * len(targets)
    rows = []
    for k, geom in enumerate(geoms):
        if geom is None:
            continue
        b, e = begin.iloc[k], end.iloc[k]
        if pd.isna(b):
            continue
        for hit in tree.query(geom.buffer(max_distance_m)):
            j = valid[int(hit)]
            dist = geom.distance(targets.geom.iloc[j])
            if dist > max_distance_m:
                continue
            if pd.isna(t0[j]):
                day = dates[j]
                if day is not None and not pd.isna(day) \
                        and abs((b.date() - day).days) <= max_days:
                    rows.append((k, j, dist, np.nan, True))
                continue
            gap = max((b - pd.Timestamp(t1[j])).total_seconds(),
                      (pd.Timestamp(t0[j]) - e).total_seconds(), 0.0)
            if gap <= max_gap_s:
                rows.append((k, j, dist, gap, False))
    pairs = pd.DataFrame(rows, columns=["row", "hz", "distance_m", "gap_s", "by_date"])
    order = ["distance_m", "gap_s"]
    if len(pairs):
        pairs["rank_for_event"] = pairs.sort_values(order).groupby("row").cumcount() + 1
        pairs["rank_for_hazard"] = pairs.sort_values(order).groupby("hz").cumcount() + 1
    else:
        pairs["rank_for_event"] = pairs["rank_for_hazard"] = []
    return pairs


def join_hazards(tornadoes: pd.DataFrame, se_geoms: list, hazards: pd.DataFrame, *,
                 max_distance_m: float = MATCH_DISTANCE_M,
                 max_gap_s: float = MATCH_GAP_S) -> pd.DataFrame:
    """Every (Storm Events row, DAT hazard) pair within the tolerances.

    ``hazards`` needs ``hazard_uid``, ``geom`` (projected, metres), ``t0`` and
    ``t1`` (UTC). ``rank_for_event`` is 1 for the closest hazard of each row and
    ``rank_for_hazard`` 1 for the closest row of each hazard — a hazard crossing
    counties legitimately has several rows, a row should have one hazard.
    """
    pairs = match_pairs(tornadoes.begin_utc, tornadoes.end_utc, se_geoms, hazards,
                        max_distance_m=max_distance_m, max_gap_s=max_gap_s)
    if pairs.empty:
        return pd.DataFrame(columns=["EVENT_ID", "EPISODE_ID", "WFO", "hazard_uid",
                                     "distance_m", "gap_s", "rank_for_event",
                                     "rank_for_hazard", "link_method"])
    pairs["EVENT_ID"] = tornadoes.EVENT_ID.to_numpy()[pairs.row]
    pairs["EPISODE_ID"] = tornadoes.EPISODE_ID.to_numpy()[pairs.row]
    pairs["WFO"] = tornadoes.WFO.to_numpy()[pairs.row]
    for col in ("TORNADO_KEY", "LINKED_EPISODE"):
        if col in tornadoes.columns:
            pairs[col] = tornadoes[col].to_numpy()[pairs.row]
    pairs["hazard_uid"] = hazards.hazard_uid.to_numpy()[pairs.hz]
    pairs["link_method"] = np.where(pairs.by_date, "date_only", "spatial_temporal_join")
    return pairs.drop(columns=["row", "hz", "by_date"]).sort_values(
        ["hazard_uid", "rank_for_hazard"])


def hazard_episode_reference(links: pd.DataFrame) -> pd.DataFrame:
    """One Storm Events episode and office per hazard: its closest matched row's."""
    best = links[links.rank_for_hazard == 1]
    cols = ["hazard_uid", "EPISODE_ID", "WFO", "EVENT_ID",
            *[c for c in ("TORNADO_KEY", "LINKED_EPISODE") if c in best.columns]]
    return best[cols].reset_index(drop=True)


def coverage_by_year(tornadoes: pd.DataFrame, hazards: pd.DataFrame,
                     links: pd.DataFrame) -> pd.DataFrame:
    """Both directions of the match, per year — DAT completeness in one table."""
    se_year = tornadoes.begin_utc.dt.year
    hz_year = hazards.t0.dt.year
    if "convective_day" in hazards.columns:    # hazards with a date but no time
        hz_year = hz_year.fillna(pd.to_datetime(hazards.convective_day, errors="coerce").dt.year)
    matched_rows = set(links.EVENT_ID)
    matched_hz = set(links.hazard_uid)
    years = sorted(set(se_year.dropna().astype(int)) | set(hz_year.dropna().astype(int)))
    out = []
    for y in years:
        se = tornadoes[se_year == y]
        hz = hazards[hz_year == y]
        tor_matched = set(links.loc[links.EVENT_ID.isin(se.EVENT_ID), "TORNADO_KEY"]) \
            if "TORNADO_KEY" in links.columns else set()
        out.append({
            "year": y,
            "se_rows": len(se),
            "se_tornadoes": se.TORNADO_KEY.nunique() if "TORNADO_KEY" in se else None,
            "se_tornadoes_matched": len(tor_matched),
            "se_episodes": se.EPISODE_ID.nunique(),
            "se_linked_episodes": se.LINKED_EPISODE.nunique() if "LINKED_EPISODE" in se else None,
            "dat_hazards": len(hz),
            "se_rows_matched": int(se.EVENT_ID.isin(matched_rows).sum()),
            "dat_hazards_matched": int(hz.hazard_uid.isin(matched_hz).sum()),
        })
    t = pd.DataFrame(out)
    if len(t):
        t["share_se_in_dat"] = t.se_rows_matched / t.se_rows.where(t.se_rows > 0)
        t["share_tornadoes_in_dat"] = (t.se_tornadoes_matched
                                       / t.se_tornadoes.where(t.se_tornadoes > 0))
        t["share_dat_in_se"] = t.dat_hazards_matched / t.dat_hazards.where(t.dat_hazards > 0)
    return t

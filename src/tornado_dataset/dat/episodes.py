"""Alternative ways to group tornadoes into episodes, and how to score them.

Stage 3 groups hazards by **convective day** (SPC's 1200–1159 UTC reporting
day) and joins those within 200 km by single linkage. Both choices are
conventions rather than findings, and the fixed day cuts overnight outbreaks
in two. This module implements the alternatives from the literature so they can
be compared on the same hazards, against the same reference:

``convective_day``   stage 3's rule, re-implemented so the comparison is like
                     for like (a check asserts it reproduces stage 3 exactly).
``space_time``       single linkage on distance *and* time gap, with no day
                     boundary. With an unlimited distance and a 6 h gap this is
                     a variant of the outbreak-sequence rule of Fuhrmann et al.
                     (2014), ≤6 h between consecutive tornadoes. It differs in
                     that all ratings chain (they used F/EF1+), the gap runs from
                     one tornado's end to the next one's start (theirs, on SPC's
                     start times, from start to start), and neither their ≥6
                     tornadoes nor their common synoptic system is required.
                     A count threshold is a filter on :func:`episode_counts`.
``st_dbscan``        ST-DBSCAN (Birant & Kut 2007): density-based, so a chain of
                     isolated tornadoes does not join two outbreaks unless the
                     link points are themselves in dense neighbourhoods.
``kde``              Shafer & Doswell (2011): kernel density of tornado
                     locations per convective day, with each connected region
                     above a density threshold one event. ``kde_overlap`` is the
                     Shafer, Grondin & Doswell (2015) extension: overlapping
                     windows, with regions that intersect in consecutive windows
                     joined, so a multi-day outbreak is not cut at 12 UTC.

Neither KDE variant is a replication: Shafer and Doswell clustered all severe
reports to rank outbreaks, and kept only dense clusters. Here every tornado
must belong to an episode, so the threshold is set *below* one tornado's own
peak density — an isolated tornado is its own episode, never noise.

Scoring uses NCEI Storm Events ``EPISODE_ID`` (see :mod:`.storm_events`), which
is per forecast office. Hence two different measures:

* **recall** — of hazard pairs a forecaster put in one episode, the share a
  method also puts together. Should be near 1: a method that splits an office's
  episode is almost certainly cutting a weather system.
* **within-office precision** — of hazard pairs a method puts together *and*
  that one office reported, the share that office also put in one episode. A
  proxy for over-merging; it cannot see merges across offices, and offices
  differ in how finely they split episodes.

Together with the descriptive extent of the episodes (duration, size, offices),
these describe a trade-off rather than declare a winner.
"""

from __future__ import annotations

import json
from typing import Callable

import numpy as np
import pandas as pd

from .. import config
from .hazards import UnionFind

HOUR = 3600.0
_EPOCH = pd.Timestamp("1970-01-01", tz="UTC")


def _seconds(ts: pd.Series) -> np.ndarray:
    """UTC timestamps as float seconds — independent of the column's resolution,
    which pandas 3 infers (s, ms, us or ns) and ``astype("int64")`` exposes raw."""
    return (ts - _EPOCH).dt.total_seconds().to_numpy()


# ── the hazard frame ────────────────────────────────────────────────────────
def load_hazard_frame(tag: str) -> pd.DataFrame:
    """Hazards with projected track geometry, UTC interval and a representative point.

    ``geom`` is the geometry stage 3 measures episode distance on: the single
    track line, or the convex hull of all vertices when a hazard has several.
    ``track`` is the actual line(s), for matching against other records;
    ``point`` is the track midpoint, used by the density methods.
    """
    from pyproj import Transformer
    from shapely import line_interpolate_point
    from shapely.geometry import MultiLineString, MultiPoint, shape
    from shapely.ops import transform

    hazards = pd.read_csv(config.PROCESSED_DIR / f"hazards_{tag}.csv", low_memory=False)
    geoms = pd.read_csv(config.PROCESSED_DIR / f"geometries_{tag}.csv")
    geoms = geoms[geoms.geom_role == "track_line"]
    to_m = Transformer.from_crs(config.CRS_WGS84, config.CRS_EQUAL_AREA, always_xy=True)
    lines: dict[str, list] = {}
    for uid, gj in zip(geoms.hazard_uid, geoms.geojson):
        lines.setdefault(uid, []).append(transform(to_m.transform, shape(json.loads(gj))))

    geom, point, tracks = [], [], []
    for uid in hazards.hazard_uid:
        parts = lines.get(uid, [])
        flat = [p for g in parts for p in (g.geoms if hasattr(g, "geoms") else [g])]
        if not flat:
            geom.append(None)
            point.append(None)
            tracks.append(None)
            continue
        geom.append(parts[0] if len(parts) == 1 else
                    MultiPoint([c for g in flat for c in g.coords]).convex_hull)
        tracks.append(flat[0] if len(flat) == 1 else MultiLineString(flat))
        # Midpoint of the longest segment: for a track surveyed in pieces, the
        # bulk of the path rather than the gap between pieces.
        point.append(line_interpolate_point(max(flat, key=lambda g: g.length), 0.5,
                                            normalized=True))
    hazards["track"] = tracks
    hazards["geom"] = geom
    hazards["point"] = point
    hazards["t0"] = pd.to_datetime(hazards.time_begin_utc, utc=True, errors="coerce")
    end = pd.to_datetime(hazards.time_end_utc, utc=True, errors="coerce")
    hazards["t1"], hazards["end_repaired"] = repair_end_times(hazards.t0, end)
    return hazards


def load_spc_frame(tracks_csv, se_links_csv=None) -> pd.DataFrame:
    """SPC whole tracks (stage 24) in the shape of :func:`load_hazard_frame`.

    The methods then run on the complete, reviewed tornado list instead of the
    surveyed subset in DAT. ``hazard_uid`` holds the ``spc_id`` so every method
    and score works unchanged. The geometry is SPC's straight start→end line;
    ``convective_day`` follows stage 3's rule on the start time; ``wfo_all``
    comes from the matched Storm Events rows, since SPC records no office.
    """
    from pyproj import Transformer
    from shapely import line_interpolate_point
    from shapely.ops import transform

    from . import spc_tornadoes

    tracks = pd.read_csv(tracks_csv, low_memory=False)
    to_m = Transformer.from_crs(config.CRS_WGS84, config.CRS_EQUAL_AREA, always_xy=True)
    geoms = spc_tornadoes.track_geometries(tracks, lambda g: transform(to_m.transform, g))
    t0 = pd.to_datetime(tracks.begin_utc, utc=True)
    frame = pd.DataFrame({
        "hazard_uid": tracks.spc_id,
        "geom": geoms, "track": geoms,
        "point": [None if g is None else g if g.geom_type == "Point"
                  else line_interpolate_point(g, 0.5, normalized=True) for g in geoms],
        "t0": t0,
        "t1": pd.to_datetime(tracks.end_utc, utc=True).fillna(t0),
        "convective_day": (t0 - pd.Timedelta(hours=config.CONVECTIVE_DAY_START_HOUR)
                           ).dt.date.astype(str),
        "mag": tracks.mag,
    })
    frame["wfo_all"] = None
    if se_links_csv is not None:
        links = pd.read_csv(se_links_csv, usecols=["spc_id", "WFO"])
        wfos = links.groupby("spc_id").WFO.agg(lambda s: ";".join(sorted(set(s.dropna()))))
        frame["wfo_all"] = frame.hazard_uid.map(wfos)
    frame["end_repaired"] = False
    return frame


REF_COLUMNS = ["EPISODE_ID", "WFO", "EVENT_ID", "TORNADO_KEY", "LINKED_EPISODE"]


def reference_via_spc(dat_uid: pd.Series, spc_links: pd.DataFrame,
                      spc_se_links: pd.DataFrame) -> pd.DataFrame:
    """Each DAT hazard's Storm Events reference, reached through its SPC track.

    DAT hazard → closest SPC track (stage 24's SPC ↔ DAT links, including the
    time-repaired ones) → that track's closest Storm Events row (stage 24's
    Storm Events ↔ SPC links). SPC and Storm Events share their times, so this
    reaches the hazards whose own DAT time is off by hours and that therefore
    never matched a Storm Events row directly. Indexed like ``dat_uid``.
    """
    from .storm_events import hazard_episode_reference

    best = spc_links[spc_links.rank_for_hazard == 1].drop_duplicates("hazard_uid")
    via = dat_uid.map(best.set_index("hazard_uid").spc_id)
    ref = hazard_episode_reference(spc_se_links.rename(columns={"spc_id": "hazard_uid"}))
    ref = ref.set_index("hazard_uid")
    out = pd.DataFrame({"hazard_uid": dat_uid.to_numpy()}, index=dat_uid.index)
    for col in REF_COLUMNS:
        if col in ref.columns:
            out[col] = via.map(ref[col]).to_numpy()
    return out


def combine_references(direct: pd.DataFrame, via: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """A hazard's own Storm Events match where it has one, else the one through SPC.

    Adds ``ref_source`` (``direct``, ``via_spc`` or missing) and returns counts
    for the report, among them how often the two routes name the same Storm
    Events episode where both exist — the check that going through SPC does not
    change the reference, only extends it.
    """
    has_d, has_v = direct.EPISODE_ID.notna(), via.EPISODE_ID.notna()
    out = direct.copy()
    fill = ~has_d & has_v
    for col in REF_COLUMNS:
        if col in via.columns:
            if col not in out.columns:
                out[col] = None
            out.loc[fill, col] = via.loc[fill, col]
    source = pd.Series(None, index=out.index, dtype=object)
    source[has_v] = "via_spc"
    source[has_d] = "direct"
    out["ref_source"] = source
    both = has_d & has_v
    stats = {"direct": int(has_d.sum()), "via_spc_only": int(fill.sum()),
             "both": int(both.sum()),
             "agree_episode": float((direct.EPISODE_ID[both] == via.EPISODE_ID[both]).mean())
             if both.any() else float("nan"),
             "neither": int((~has_d & ~has_v).sum())}
    return out, stats


def project_labels(labels: pd.Series, anchor_uid: pd.Series, dat_uid: pd.Series,
                   links: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Carry episodes built on SPC tracks to DAT hazards.

    ``links`` are stage 24's SPC ↔ DAT pairs; each DAT hazard takes the episode
    of its closest SPC track (``rank_for_hazard == 1``). A DAT hazard with no
    SPC match becomes its own episode — it is still in the dataset, but nothing
    official groups it. Returns the labels, indexed like ``dat_uid``, and a mask
    of which hazards were matched.
    """
    best = links[links.rank_for_hazard == 1].drop_duplicates("hazard_uid")
    spc_label = pd.Series(labels.to_numpy(), index=anchor_uid.to_numpy())
    via = dat_uid.map(best.set_index("hazard_uid").spc_id)
    out = via.map(spc_label)
    matched = out.notna()
    start = int(labels.max()) + 1 if len(labels) else 0
    out[~matched] = np.arange(start, start + int((~matched).sum()))
    return out.astype(int), matched


# No tornado on record has lasted this long; the longest-lived are 3-4 hours.
MAX_TORNADO_DURATION_H = 5.0


def repair_end_times(t0: pd.Series, t1: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Implausible DAT end times, repaired; and which ones were.

    DAT's ``endtime`` is entered by hand and the *date* is often wrong while the
    clock time is right — 2013-03-18 17:11 to 2015-01-23 17:18 is a 7-minute
    tornado with a mistyped end date. 427 hazards last over a day and 61 end
    before they start. Time-gap methods would chain anything overlapping such an
    interval, so: if the clock times alone give a plausible duration, keep that;
    otherwise the end is unknown and set to the start.
    """
    span = (t1 - t0).dt.total_seconds() / HOUR
    bad = t1.isna() | (span < 0) | (span > MAX_TORNADO_DURATION_H)
    clock = ((t1.dt.hour * 60 + t1.dt.minute) - (t0.dt.hour * 60 + t0.dt.minute)) % 1440
    plausible = bad & t1.notna() & (clock <= MAX_TORNADO_DURATION_H * 60)
    fixed = t1.copy()
    fixed[plausible] = t0[plausible] + pd.to_timedelta(clock[plausible], unit="min")
    fixed[bad & ~plausible] = t0[bad & ~plausible]
    return fixed, bad


# ── neighbourhoods ──────────────────────────────────────────────────────────
def neighbour_pairs(h: pd.DataFrame, max_distance_m: float | None,
                    max_gap_s: float) -> pd.DataFrame:
    """All hazard pairs within a time gap and (optionally) a distance.

    The gap is between intervals: zero when two tornadoes overlap in time. Pairs
    are found by a sweep over start times, so the cost scales with how many
    tornadoes fall inside one gap, not with the square of the corpus.
    """
    import shapely

    ok = h.index[h.t0.notna() & h.geom.notna()].to_numpy()
    order = ok[np.argsort(h.t0.loc[ok].to_numpy())]
    t0 = _seconds(h.t0.loc[order])
    t1 = _seconds(h.t1.loc[order])
    # For a pair in start order the gap is max(t0_b - t1_a, 0), so scanning
    # forward from each hazard to t1_a + gap finds every pair exactly once.
    left, right = [], []
    for a in range(len(order)):
        stop = np.searchsorted(t0, t1[a] + max_gap_s, side="right")
        if stop > a + 1:
            left.append(np.full(stop - a - 1, a))
            right.append(np.arange(a + 1, stop))
    if not left:
        return pd.DataFrame(columns=["a", "b", "gap_s", "distance_m"])
    ia, ib = np.concatenate(left), np.concatenate(right)
    gap = np.maximum(t0[ib] - t1[ia], 0.0)
    pairs = pd.DataFrame({"a": order[ia], "b": order[ib], "gap_s": gap})
    pairs = pairs[pairs.gap_s <= max_gap_s]
    ga = h.geom.loc[pairs.a].to_numpy()
    gb = h.geom.loc[pairs.b].to_numpy()
    pairs["distance_m"] = shapely.distance(ga, gb)
    if max_distance_m is not None:
        pairs = pairs[pairs.distance_m <= max_distance_m]
    return pairs.reset_index(drop=True)


def _labels_from_unions(h: pd.DataFrame, unions) -> pd.Series:
    position = {idx: k for k, idx in enumerate(h.index)}
    uf = UnionFind(len(h))
    for a, b in unions:
        uf.union(position[a], position[b], "")
    root = [uf.find(k) for k in range(len(h))]
    return pd.Series(pd.factorize(pd.Series(root))[0], index=h.index)


# ── methods ─────────────────────────────────────────────────────────────────
def convective_day(h: pd.DataFrame, distance_m: float = config.EPISODE_LINK_DISTANCE_M
                   ) -> pd.Series:
    """Stage 3: same convective day, single linkage within ``distance_m``."""
    from shapely import STRtree

    unions = []
    for _, day in h[h.convective_day.notna() & h.geom.notna()].groupby("convective_day"):
        idx = day.index.to_numpy()
        geoms = day.geom.to_list()
        tree = STRtree(geoms)
        for a, g in enumerate(geoms):
            for b in tree.query(g.buffer(distance_m)):
                if a != b and g.distance(geoms[b]) <= distance_m:
                    unions.append((idx[a], idx[int(b)]))
    return _labels_from_unions(h, unions)


def space_time(h: pd.DataFrame, distance_m: float | None, gap_s: float) -> pd.Series:
    """Single linkage on distance and time gap; no day boundary."""
    pairs = neighbour_pairs(h, distance_m, gap_s)
    return _labels_from_unions(h, zip(pairs.a, pairs.b))


def st_dbscan(h: pd.DataFrame, distance_m: float, gap_s: float, min_pts: int) -> pd.Series:
    """ST-DBSCAN (Birant & Kut 2007) with noise points kept as singletons.

    A hazard is a *core* point when at least ``min_pts`` hazards, itself
    included, lie within both thresholds. Core points within reach of each other
    form a cluster; a non-core point joins the cluster of a core neighbour (the
    first one found, as in DBSCAN). ``min_pts=1`` makes every point core and is
    identical to :func:`space_time`.
    """
    pairs = neighbour_pairs(h, distance_m, gap_s)
    degree = pd.concat([pairs.a, pairs.b]).value_counts().reindex(h.index, fill_value=0) + 1
    core = degree >= min_pts
    both = pairs[core.loc[pairs.a].to_numpy() & core.loc[pairs.b].to_numpy()]
    unions = list(zip(both.a, both.b))
    border = pairs[core.loc[pairs.a].to_numpy() ^ core.loc[pairs.b].to_numpy()]
    attached: set = set()
    for a, b in zip(border.a, border.b):
        point, anchor = (b, a) if core.loc[a] else (a, b)
        if point not in attached:
            attached.add(point)
            unions.append((point, anchor))
    return _labels_from_unions(h, unions)


def _kde_regions(points: np.ndarray, bandwidth_m: float, level: float,
                 cell_m: float) -> tuple[np.ndarray, dict[int, set]]:
    """Region label of each point, and the global cells each region covers.

    Density is normalised so one isolated point peaks at 1.0; ``level < 1``
    therefore guarantees every point lies inside a region.
    """
    from scipy import ndimage

    sigma = bandwidth_m / cell_m
    margin = int(np.ceil(4 * sigma)) + 1
    cells = np.floor(points / cell_m).astype(int)
    lo = cells.min(axis=0) - margin
    shape = cells.max(axis=0) - lo + margin + 1
    grid = np.zeros(shape[::-1])
    for x, y in cells - lo:
        grid[y, x] += 1.0
    density = ndimage.gaussian_filter(grid, sigma, mode="constant") * (2 * np.pi * sigma ** 2)
    labels, _ = ndimage.label(density >= level, structure=np.ones((3, 3)))
    local = cells - lo
    point_region = labels[local[:, 1], local[:, 0]]
    region_cells: dict[int, set] = {}
    ys, xs = np.nonzero(labels)
    for y, x, r in zip(ys, xs, labels[ys, xs]):
        region_cells.setdefault(int(r), set()).add((int(x + lo[0]), int(y + lo[1])))
    return point_region, region_cells


def kde(h: pd.DataFrame, bandwidth_m: float, level: float = 0.5,
        window_h: float = 24.0, step_h: float = 24.0, cell_m: float = 10_000.0
        ) -> pd.Series:
    """Kernel-density regions per time window (Shafer & Doswell 2011; 2015).

    Windows start at 12 UTC. With ``step_h == window_h`` they tile time — one
    convective day each, the 2011 method. With ``step_h < window_h`` they
    overlap, and two hazards are joined if they share a region in any window,
    or if their regions intersect in consecutive windows — the 2015 extension.
    """
    ok = h[h.t0.notna() & h.point.notna()]
    t = _seconds(ok.t0)
    xy = np.array([[p.x, p.y] for p in ok.point])
    idx = ok.index.to_numpy()
    origin = np.floor((t.min() - 12 * HOUR) / 86400) * 86400 + 12 * HOUR
    unions: list[tuple] = []
    previous: dict[int, tuple[set, int]] | None = None
    start = origin
    while start <= t.max():
        inside = np.nonzero((t >= start) & (t < start + window_h * HOUR))[0]
        current: dict[int, tuple[set, int]] = {}
        if len(inside):
            region, cells = _kde_regions(xy[inside], bandwidth_m, level, cell_m)
            for r in np.unique(region):
                if r == 0:          # below the threshold: stays a singleton
                    continue
                members = idx[inside[region == r]]
                unions.extend((members[0], m) for m in members[1:])
                current[int(r)] = (cells[int(r)], members[0])
            if previous and step_h < window_h:
                for cells_now, anchor_now in current.values():
                    for cells_before, anchor_before in previous.values():
                        if cells_now & cells_before:
                            unions.append((anchor_now, anchor_before))
        previous = current if len(inside) else None
        start += step_h * HOUR
    return _labels_from_unions(h, unions)


# ── scoring ─────────────────────────────────────────────────────────────────
def _pairs(counts: pd.Series) -> float:
    n = counts.to_numpy(dtype=float)
    return float((n * (n - 1) / 2).sum())


def adjusted_rand(a: pd.Series, b: pd.Series) -> float:
    """Adjusted Rand index between two labellings of the same items."""
    n = len(a)
    if n < 2:
        return float("nan")
    joint = _pairs(pd.crosstab(a, b).stack())
    pa, pb = _pairs(a.value_counts()), _pairs(b.value_counts())
    total = n * (n - 1) / 2
    expected = pa * pb / total
    top = (pa + pb) / 2 - expected
    return (joint - expected) / top if top else float("nan")


def score(labels: pd.Series, reference: pd.DataFrame,
          episode: str = "EPISODE_ID") -> dict[str, float]:
    """Agreement with Storm Events episodes, on hazards that have a reference.

    ``reference`` is indexed like ``labels`` with the ``episode`` column and
    ``WFO`` (see :func:`storm_events.hazard_episode_reference`). With
    ``episode="LINKED_EPISODE"`` the reference joins offices that share a
    crossing tornado, so recall and splitting are judged across those offices
    too; office precision is always within one office.
    """
    ref = reference.dropna(subset=[episode])
    lab = labels.loc[ref.index]
    together_ref = _pairs(ref[episode].value_counts())
    together_both = _pairs(pd.crosstab(lab, ref[episode]).stack())
    same_office = _pairs(pd.crosstab(lab, ref.WFO).stack())
    together_office = _pairs(pd.crosstab([lab, ref.WFO], ref[episode]).stack())
    sizes = ref.groupby(episode).size()
    multi = sizes[sizes >= 2].index
    split = ref[ref[episode].isin(multi)].assign(m=lab).groupby(episode).m.nunique()
    return {
        "scored_hazards": len(ref),
        "recall": together_both / together_ref if together_ref else float("nan"),
        "office_precision": together_office / same_office if same_office else float("nan"),
        "se_episodes_split": float((split > 1).mean()) if len(split) else float("nan"),
        "ari": adjusted_rand(lab, ref[episode]),
    }


def score_watch(labels: pd.Series, system: pd.Series, wfo: pd.Series | None = None
                ) -> dict[str, float]:
    """Agreement with SPC watch systems (stage 26), on tornadoes that were in a watch.

    Unlike Storm Events episodes, watch systems span offices, so precision is
    meaningful here:

    * **recall** — of pairs SPC kept in one system, the share the method groups;
    * **precision** — of pairs the method groups, the share in one system;
    * **cross-office precision** — the same, on grouped pairs whose two
      tornadoes were reported by *different* offices (``wfo``): the over-merging
      the office episodes cannot see;
    * **f1** — the harmonic mean of recall and precision;
    * **systems split** — share of systems (≥2 scored tornadoes) the method
      spreads over several episodes.

    ``system`` is indexed like ``labels``, missing for unwatched tornadoes,
    which are left out.
    """
    ok = system.notna()
    lab, sysid = labels[ok], system[ok]
    together_sys = _pairs(sysid.value_counts())
    together_lab = _pairs(lab.value_counts())
    both = _pairs(pd.crosstab(lab, sysid).stack())
    recall = both / together_sys if together_sys else float("nan")
    precision = both / together_lab if together_lab else float("nan")
    sizes = sysid.value_counts()
    multi = sizes[sizes >= 2].index
    split = pd.DataFrame({"s": sysid, "m": lab})[sysid.isin(multi)].groupby("s").m.nunique()
    out = {
        "scored": int(ok.sum()),
        "recall": recall, "precision": precision,
        "f1": (2 * recall * precision / (recall + precision)
               if recall and precision and not np.isnan(recall + precision) else float("nan")),
        "systems_split": float((split > 1).mean()) if len(split) else float("nan"),
        "ari": adjusted_rand(lab, sysid),
    }
    if wfo is not None:
        k = wfo[ok].notna()
        lw, sw_, ww = lab[k], sysid[k], wfo[ok][k]
        grouped = _pairs(lw.value_counts()) - _pairs(pd.crosstab(lw, ww).stack())
        agreed = (_pairs(pd.crosstab(lw, sw_).stack())
                  - _pairs(pd.crosstab([lw, sw_], ww).stack()))
        out["cross_office_pairs"] = grouped
        out["cross_office_precision"] = agreed / grouped if grouped else float("nan")
    return out


def describe(labels: pd.Series, h: pd.DataFrame) -> dict[str, float]:
    """Size and extent of the episodes a method produces."""
    frame = h.assign(ep=labels)
    sizes = frame.groupby("ep").size()
    dur = frame.groupby("ep").apply(
        lambda g: (g.t1.max() - g.t0.min()).total_seconds() / HOUR, include_groups=False)

    def extent(g) -> float:
        b = np.array([geom.bounds for geom in g.geom if geom is not None])
        if not len(b):
            return float("nan")
        return float(np.hypot(b[:, 2].max() - b[:, 0].min(), b[:, 3].max() - b[:, 1].min()) / 1000)

    size_km = frame.groupby("ep").apply(extent, include_groups=False)
    wfos = frame.groupby("ep").wfo_all.apply(
        lambda s: len({w for v in s.dropna() for w in str(v).split(";") if w}))
    multi = sizes[sizes > 1].index
    cdays = frame.groupby("ep").convective_day.nunique()
    return {
        "episodes": int(len(sizes)),
        "singleton_share": float((sizes == 1).mean()),
        "largest": int(sizes.max()),
        "hazards_in_outbreaks_6plus": float(sizes[sizes >= 6].sum() / len(frame)),
        "duration_h_p95": float(dur.loc[multi].quantile(.95)) if len(multi) else 0.0,
        "duration_h_max": float(dur.max()),
        "extent_km_p95": float(size_km.loc[multi].quantile(.95)) if len(multi) else 0.0,
        "extent_km_max": float(size_km.max()),
        "wfos_max": int(wfos.max()),
        "multi_day_episodes": int((cdays > 1).sum()),
    }


def episode_counts(labels: pd.Series, h: pd.DataFrame,
                   dat_spc_id: pd.Series | None = None) -> pd.DataFrame:
    """Per episode built on SPC tracks: its tornadoes, by rating, and its DAT hazards.

    These are the counts a user of the dataset cannot recompute: DAT is a subset
    of SPC, so counting an episode's DAT hazards undercounts its tornadoes. An
    outbreak threshold is then a filter, e.g. ``n_spc_ef1plus >= 6`` after
    Fuhrmann et al. (2014) — close to, not identical with, their outbreaks when
    EF0 tornadoes chain the episode. ``n_spc_unrated`` counts EF-U tornadoes
    (SPC magnitude −9), which ``n_spc_ef1plus`` leaves out. ``labels`` is
    indexed like ``h`` (a :func:`load_spc_frame`); ``dat_spc_id`` is each DAT
    hazard's closest SPC track, missing where it has none.
    """
    mag = h.mag.to_numpy(dtype=float)
    out = pd.DataFrame({"episode": labels.to_numpy(), "n_spc": 1,
                        "n_spc_ef1plus": (mag >= 1).astype(int),
                        "n_spc_unrated": (mag < 0).astype(int)}).groupby("episode").sum()
    if dat_spc_id is not None:
        spc_label = pd.Series(labels.to_numpy(), index=h.hazard_uid.to_numpy())
        n_dat = dat_spc_id.dropna().map(spc_label).value_counts()
        out["n_dat"] = n_dat.reindex(out.index, fill_value=0).astype(int)
    return out.reset_index()


MethodFn = Callable[[pd.DataFrame], pd.Series]

# The time-only rule; see the module docstring for how it differs from Fuhrmann's.
FUHRMANN_VARIANT = "time-gap 6h, all ratings (Fuhrmann variant)"
# Earlier names of methods, for outputs written before a rename.
LEGACY_NAMES = {"time-gap 6h, no distance (Fuhrmann-style)": FUHRMANN_VARIANT}


def method_grid() -> dict[str, MethodFn]:
    """The configurations the comparison runs, keyed by a readable name."""
    km = 1000.0
    grid: dict[str, MethodFn] = {
        "convective_day 200km (stage 3)": lambda h: convective_day(h, 200 * km),
        "convective_day 100km": lambda h: convective_day(h, 100 * km),
        "convective_day 400km": lambda h: convective_day(h, 400 * km),
        FUHRMANN_VARIANT: lambda h: space_time(h, None, 6 * HOUR),
    }
    for d in (100, 200, 400):
        for g in (1, 3, 6):
            grid[f"space_time {d}km {g}h"] = (lambda h, d=d, g=g: space_time(h, d * km, g * HOUR))
    for d, g in ((200, 3), (400, 3)):
        for p in (3, 5):
            grid[f"st_dbscan {d}km {g}h minpts={p}"] = (
                lambda h, d=d, g=g, p=p: st_dbscan(h, d * km, g * HOUR, p))
    for bw in (50, 100):
        grid[f"kde day bw={bw}km"] = (lambda h, bw=bw: kde(h, bw * km))
        grid[f"kde overlap 24h/12h bw={bw}km"] = (
            lambda h, bw=bw: kde(h, bw * km, window_h=24, step_h=12))
    return grid

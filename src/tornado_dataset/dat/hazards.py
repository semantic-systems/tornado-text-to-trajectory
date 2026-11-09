"""Assemble DAT features into hazards (tornado tracks) and episodes (outbreaks).

A DAT record is not a tornado. One tornado can be drawn as several line segments
(surveys are done piecewise, and adjacent WFOs survey their own portion), and its
damage may be covered by several polygons. The dataset's unit of analysis — the
thing a text is supposed to describe and a model is supposed to predict — is the
**hazard**: one tornado, its track geometry, and its damage polygons.

Merging is done by union-find over line features, and *every* merge records why
it happened:

``path_guid``        the polygon's foreign key ties two lines together
``spatial_link``     both lines link to the same polygon above the confidence floor
``event_id+date``    identical non-empty free-text event_id on the same storm date
``endpoint_gap``     an endpoint of one line lies within a few km of the other's,
                     same convective day (segments of one continuing track)

This is stricter than the previous bounding-box overlap heuristic: a bbox in
degrees says nothing about how far apart two tracks actually are, and it cannot
distinguish two parallel tornadoes in the same outbreak from one interrupted
track. Where evidence is weak the features stay separate — an over-merged hazard
silently corrupts the ground truth, a split one is visible in the counts.

A damage polygon joins the hazard of the line it is linked to. Polygons with no
accepted link are surveyed tornadoes whose track DAT never drew; they become
hazards of their own (``geometry_source = polygon``), polygons of one day that
touch forming one hazard. Features whose rating says they are not a tornado
(:data:`config.NON_TORNADO_RATINGS`, i.e. thunderstorm wind) are left out on
both sides before any of this, so a wind polygon lying on a tornado track is not
taken for that tornado's damage.

Episodes group hazards by convective day (12Z-12Z, the NWS convention that keeps
a night-time outbreak on one date) and spatial proximity.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Iterable

from shapely import STRtree, unary_union
from shapely.geometry import MultiPoint

from .. import config
from ..ids import uid
from .geometry import endpoints
from .link import real_path_guid


class UnionFind:
    """Disjoint set over feature indices, with the reason for each union kept."""

    def __init__(self, size: int) -> None:
        self.parent = list(range(size))
        self.reasons: list[tuple[int, int, str]] = []

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int, reason: str) -> bool:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        self.parent[ra] = rb
        self.reasons.append((a, b, reason))
        return True

    def groups(self) -> dict[int, list[int]]:
        out: dict[int, list[int]] = {}
        for i in range(len(self.parent)):
            out.setdefault(self.find(i), []).append(i)
        return out


# ── attribute helpers ────────────────────────────────────────────────────────
_EF_ORDER = {f"EF{d}": d for d in range(6)}


def is_tornado_rating(value: Any) -> bool:
    """False only where DAT says explicitly that a feature is not a tornado."""
    return str(value or "").strip().upper() not in config.NON_TORNADO_RATINGS


def split_by_rating(features: list[dict[str, Any]]
                    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Prepared DAT features as (tornado, explicitly not a tornado)."""
    kept, excluded = [], []
    for f in features:
        (kept if is_tornado_rating(f["properties"].get("efscale")) else excluded).append(f)
    return kept, excluded


def ef_rank(value: Any) -> float:
    """Order EF ratings so the most severe wins; non-EF labels rank below EF0."""
    text = str(value or "").upper().replace(" ", "").replace("-", "")
    for label, rank in _EF_ORDER.items():
        if label in text:
            return rank
    return -1 if text else -2


def clean_text(value: Any) -> str | None:
    """Return real text, or None for blanks and DAT's placeholder strings."""
    text = str(value or "").strip()
    if not text or text.upper() in config.PLACEHOLDER_TEXT_VALUES:
        return None
    return text


def _numbers(field: str, props: list[dict[str, Any]]) -> list[float]:
    """Numeric values, dropping NOAA's negative missing-data sentinels (-99)."""
    return [v for p in props if isinstance(v := p.get(field), (int, float)) and v >= 0]


def _max(field: str, props: list[dict[str, Any]]) -> float | None:
    values = _numbers(field, props)
    return max(values) if values else None


def _sum(field: str, props: list[dict[str, Any]]) -> float | None:
    values = _numbers(field, props)
    return sum(values) if values else None


def parse_datetime(value: Any) -> dt.datetime | None:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def convective_day(moment: dt.datetime | None) -> dt.date | None:
    """Storm date under the 12Z-12Z convention (a 3am tornado belongs to the 'day' before)."""
    if moment is None:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=dt.timezone.utc)
    shifted = moment - dt.timedelta(hours=config.CONVECTIVE_DAY_START_HOUR)
    return shifted.date()


# ── hazard assembly ──────────────────────────────────────────────────────────
def merge_lines(lines: list[dict[str, Any]], links: list[dict[str, Any]], *,
                min_link_confidence: float = config.HAZARD_MIN_LINK_CONFIDENCE,
                endpoint_gap_m: float = config.HAZARD_ENDPOINT_GAP_M) -> UnionFind:
    """Union line features that belong to the same tornado, recording evidence."""
    index_by_guid = {line["globalid"]: i for i, line in enumerate(lines) if line["globalid"]}
    uf = UnionFind(len(lines))

    # 1. Two lines sharing a polygon (either by the polygon's foreign key or by a
    #    confident spatial link) are segments of the same track.
    lines_by_polygon: dict[Any, list[tuple[int, str]]] = {}
    for record in links:
        idx = index_by_guid.get(str(record.get("line_globalid") or "").upper())
        if idx is None:
            continue
        if record.get("path_guid_match"):
            reason = "path_guid"
        elif float(record.get("link_confidence") or 0) >= min_link_confidence:
            reason = "spatial_link"
        else:
            continue
        lines_by_polygon.setdefault(record["polygon_oid"], []).append((idx, reason))
    for members in lines_by_polygon.values():
        first, first_reason = members[0]
        for other, reason in members[1:]:
            uf.union(first, other, "path_guid" if "path_guid" in (first_reason, reason)
                     else "spatial_link")

    # 2. Identical non-empty free-text event_id on the same storm date. The string
    #    alone is unreliable (WFO-local, uncontrolled), so the date must agree too.
    by_event: dict[tuple[str, Any], list[int]] = {}
    for i, line in enumerate(lines):
        if line["event_id"] and line["date"]:
            by_event.setdefault((line["event_id"], line["date"]), []).append(i)
    for members in by_event.values():
        for other in members[1:]:
            uf.union(members[0], other, "event_id+date")

    # 3. Endpoint continuity: a track surveyed in pieces. Restricted to the same
    #    convective day and a few km, so distinct tornadoes do not chain together.
    points, owners = [], []
    for i, line in enumerate(lines):
        for point in endpoints(line["proj"]):
            points.append(point)
            owners.append(i)
    if points:
        tree = STRtree([MultiPoint([p]).geoms[0] for p in points])
        for pos, point in enumerate(points):
            i = owners[pos]
            for hit in tree.query(MultiPoint([point]).geoms[0].buffer(endpoint_gap_m)):
                j = owners[hit]
                if i == j or uf.find(i) == uf.find(j):
                    continue
                if lines[i]["cday"] and lines[i]["cday"] == lines[j]["cday"]:
                    uf.union(i, j, "endpoint_gap")
    return uf


def build_hazards(lines: list[dict[str, Any]], polygons: list[dict[str, Any]],
                  links: list[dict[str, Any]], *,
                  min_link_confidence: float = config.HAZARD_MIN_LINK_CONFIDENCE,
                  ) -> list[dict[str, Any]]:
    """Group lines into hazards and attach their polygons and attributes."""
    for line in lines:
        line["cday"] = convective_day(parse_datetime(line["properties"].get("stormdate")))

    uf = merge_lines(lines, links, min_link_confidence=min_link_confidence)
    reason_by_pair = {(a, b): r for a, b, r in uf.reasons}

    polygon_by_oid = {p["objectid"]: p for p in polygons}
    index_by_guid = {line["globalid"]: i for i, line in enumerate(lines) if line["globalid"]}

    # Best accepted link per polygon decides which hazard a polygon joins.
    best_for_polygon: dict[Any, dict[str, Any]] = {}
    for record in links:
        if float(record.get("link_confidence") or 0) < min_link_confidence \
                and not record.get("path_guid_match"):
            continue
        key = record["polygon_oid"]
        current = best_for_polygon.get(key)
        if current is None or (record["frac_line_in_polygon"], -record["gap_m"]) > (
                current["frac_line_in_polygon"], -current["gap_m"]):
            best_for_polygon[key] = record

    polygons_for_line: dict[int, list[tuple[Any, dict[str, Any]]]] = {}
    for oid, record in best_for_polygon.items():
        idx = index_by_guid.get(str(record.get("line_globalid") or "").upper())
        if idx is not None:
            polygons_for_line.setdefault(idx, []).append((oid, record))

    hazards = []
    for members in uf.groups().values():
        member_lines = [lines[i] for i in members]
        line_props = [line["properties"] for line in member_lines]

        attached = [(polygon_by_oid[oid], record)
                    for i in members
                    for oid, record in polygons_for_line.get(i, [])
                    if oid in polygon_by_oid]
        polygon_props = [p["properties"] for p, _ in attached]
        all_props = line_props + polygon_props

        starts = [parse_datetime(p.get("starttime")) or parse_datetime(p.get("stormdate"))
                  for p in line_props]
        starts = [s for s in starts if s]
        ends = [parse_datetime(p.get("endtime")) for p in line_props]
        ends = [e for e in ends if e]

        comments = []
        for props in all_props:
            comment = clean_text(props.get("comments"))
            if comment and comment not in comments:
                comments.append(comment)

        event_ids = sorted({str(p["event_id"]).strip() for p in all_props
                            if clean_text(p.get("event_id"))})
        ef_values = [p.get("efscale") for p in all_props if p.get("efscale")]
        # A line's wfo can list several offices ("LZK,MEG") when a track crossed a
        # CWA boundary; split them so Stage B can query each office's products.
        wfos = sorted({part.strip().upper()
                       for p in line_props if clean_text(p.get("wfo"))
                       for part in str(p["wfo"]).replace(";", ",").split(",")
                       if part.strip()})
        cdays = sorted({line["cday"] for line in member_lines if line["cday"]})

        merge_reasons = sorted({reason for (a, b), reason in reason_by_pair.items()
                                if a in members and b in members})

        hazard_uid = uid("hazard", *[line["globalid"] or f"oid:{line['objectid']}"
                                     for line in member_lines])
        hazards.append({
            "hazard_uid": hazard_uid,
            "hazard_type": "tornado",
            "convective_day": cdays[0].isoformat() if cdays else None,
            "time_begin_utc": min(starts).isoformat() if starts else None,
            "time_end_utc": max(ends).isoformat() if ends else None,
            "efscale": max(ef_values, key=ef_rank) if ef_values else None,
            "peak_wind_mph": _max("maxwind", line_props),
            "path_length_mi": _sum("length", line_props),
            "path_width_yd": _max("width", all_props),
            "injuries": _max("injuries", all_props),
            "fatalities": _max("fatalities", all_props),
            "propdamage": _max("propdamage", line_props),
            "cropdamage": _max("cropdamage", line_props),
            "wfo": wfos[0] if wfos else None,
            "wfo_all": ";".join(wfos),
            "dat_event_ids": ";".join(event_ids),
            "oracle_text": " | ".join(comments) if comments else None,
            "has_oracle_text": bool(comments),
            "n_lines": len(member_lines),
            "n_polygons": len(attached),
            "line_objectids": ";".join(str(line["objectid"]) for line in member_lines),
            "polygon_objectids": ";".join(str(p["objectid"]) for p, _ in attached),
            "line_globalids": ";".join(line["globalid"] for line in member_lines),
            "merge_evidence": ";".join(merge_reasons),
            "geometry_source": "line+polygon" if attached else "line",
            "max_link_confidence": max((r["link_confidence"] for _, r in attached), default=None),
            "min_link_confidence": min((r["link_confidence"] for _, r in attached), default=None),
            "_line_geoms": [line["geom"] for line in member_lines],
            "_polygon_geoms": [p["geom"] for p, _ in attached],
            "_proj": [line["proj"] for line in member_lines],
        })
    return hazards


def polygon_time(polygon: dict[str, Any]) -> dt.datetime | None:
    """A polygon's time, or None where ``stormdate`` holds only a date.

    DAT stores the date of a date-only entry as midnight UTC; a real time of
    exactly 00:00:00 is rare enough to be treated the same way.
    """
    moment = parse_datetime(polygon["properties"].get("stormdate"))
    if moment is None or (moment.hour, moment.minute, moment.second) == (0, 0, 0):
        return None
    return moment


def build_polygon_hazards(polygons: list[dict[str, Any]], links: list[dict[str, Any]], *,
                          touch_m: float = config.LINK_GAP_THRESHOLD_M,
                          max_time_gap_s: float = 3600.0
                          ) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Hazards from damage polygons that no line claims.

    ``polygons`` and ``links`` are the tornado-rated ones that entered
    :func:`build_hazards`. A polygon with any accepted link to a line is that
    line's (attached, or left out below the confidence floor), so only polygons
    without one become hazards here. Polygons of the same day within
    ``touch_m`` of each other — nested intensity contours, a track drawn in
    pieces — form one hazard, unless both carry a time and the times are more
    than ``max_time_gap_s`` apart (a second tornado over the same ground). The
    day is the convective day of the polygon's time, or its date where DAT
    gives only a date; the hazard's start is the earliest time, and its end is
    unknown.
    """
    linked = {record["polygon_oid"] for record in links}
    free = [p for p in polygons if p["objectid"] not in linked]
    times = [polygon_time(p) for p in free]
    days = [convective_day(t) if t else p["date"] for p, t in zip(free, times)]

    uf = UnionFind(len(free))
    if free:
        tree = STRtree([p["proj"] for p in free])
        for a, polygon in enumerate(free):
            for b in tree.query(polygon["proj"].buffer(touch_m)):
                b = int(b)
                apart = (abs((times[a] - times[b]).total_seconds())
                         if times[a] and times[b] else 0.0)
                if a < b and days[a] and days[a] == days[b] and apart <= max_time_gap_s \
                        and polygon["proj"].distance(free[b]["proj"]) <= touch_m:
                    uf.union(a, b, "polygon_adjacent")

    hazards = []
    for members in uf.groups().values():
        member = [free[i] for i in members]
        props = [p["properties"] for p in member]
        timed = sorted(times[i] for i in members if times[i])
        comments = []
        for p in props:
            comment = clean_text(p.get("comments"))
            if comment and comment not in comments:
                comments.append(comment)
        ef_values = [p.get("efscale") for p in props if p.get("efscale")]
        event_ids = sorted({str(p["event_id"]).strip() for p in props
                            if clean_text(p.get("event_id"))})
        day = min((days[i] for i in members if days[i]), default=None)
        hazards.append({
            "hazard_uid": uid("hazard", *[f"polygon:{p['globalid'] or p['objectid']}"
                                          for p in member]),
            "hazard_type": "tornado",
            "convective_day": day.isoformat() if day else None,
            "time_begin_utc": timed[0].isoformat() if timed else None,
            "time_end_utc": None,
            "efscale": max(ef_values, key=ef_rank) if ef_values else None,
            "peak_wind_mph": None, "path_length_mi": None,
            "path_width_yd": _max("width", props),
            "injuries": _max("injuries", props), "fatalities": _max("fatalities", props),
            "propdamage": None, "cropdamage": None,
            "wfo": None, "wfo_all": "",
            "dat_event_ids": ";".join(event_ids),
            "oracle_text": " | ".join(comments) if comments else None,
            "has_oracle_text": bool(comments),
            "n_lines": 0, "n_polygons": len(member),
            "line_objectids": "",
            "polygon_objectids": ";".join(str(p["objectid"]) for p in member),
            "line_globalids": "",
            "merge_evidence": "polygon_adjacent" if len(member) > 1 else "",
            "geometry_source": "polygon",
            "max_link_confidence": None, "min_link_confidence": None,
            "_line_geoms": [], "_polygon_geoms": [p["geom"] for p in member],
            "_proj": [p["proj"] for p in member],
        })
    stats = {"polygons_without_link": len(free), "polygon_hazards": len(hazards),
             "polygon_hazards_date_only": sum(1 for h in hazards if not h["time_begin_utc"])}
    return hazards, stats


# ── episode assembly ─────────────────────────────────────────────────────────
def build_episodes(hazards: list[dict[str, Any]], *,
                   link_distance_m: float = config.EPISODE_LINK_DISTANCE_M
                   ) -> list[dict[str, Any]]:
    """Cluster hazards of one convective day into spatially coherent outbreaks."""
    by_day: dict[str, list[int]] = {}
    for i, hazard in enumerate(hazards):
        if hazard["convective_day"]:
            by_day.setdefault(hazard["convective_day"], []).append(i)

    episodes = []
    for day, indices in sorted(by_day.items()):
        geoms = []
        for i in indices:
            parts = hazards[i]["_proj"]
            # Several parts: their convex hull (for lines, that of all vertices).
            geoms.append(parts[0] if len(parts) == 1 else unary_union(parts).convex_hull)
        uf = UnionFind(len(indices))
        tree = STRtree(geoms)
        for a, geom in enumerate(geoms):
            for b in tree.query(geom.buffer(link_distance_m)):
                if a != b and geom.distance(geoms[b]) <= link_distance_m:
                    uf.union(a, b, "same_day_proximity")

        for members in uf.groups().values():
            member_hazards = [hazards[indices[m]] for m in members]
            episode_uid = uid("episode", day, *[h["hazard_uid"] for h in member_hazards])
            starts = [h["time_begin_utc"] for h in member_hazards if h["time_begin_utc"]]
            ends = [h["time_end_utc"] for h in member_hazards if h["time_end_utc"]]
            wfos = sorted({w for h in member_hazards for w in (h["wfo_all"] or "").split(";") if w})
            for hazard in member_hazards:
                hazard["episode_uid"] = episode_uid
            episodes.append({
                "episode_uid": episode_uid,
                "hazard_family": "tornado",
                "convective_day": day,
                "time_begin_utc": min(starts) if starts else None,
                "time_end_utc": max(ends) if ends else None,
                "n_hazards": len(member_hazards),
                "max_efscale": max((h["efscale"] for h in member_hazards if h["efscale"]),
                                   key=ef_rank, default=None),
                "fatalities": sum(h["fatalities"] or 0 for h in member_hazards),
                "injuries": sum(h["injuries"] or 0 for h in member_hazards),
                "wfos": ";".join(wfos),
                "episode_method": "convective_day+spatial_proximity",
                "hazard_uids": ";".join(h["hazard_uid"] for h in member_hazards),
            })
    return episodes

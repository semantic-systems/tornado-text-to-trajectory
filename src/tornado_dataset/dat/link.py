"""Link DAT damage lines to damage polygons, recording the evidence.

The dataset's ground truth needs to know which damage polygon belongs to which
tornado track. DAT offers three signals, of very different quality:

* ``path_guid`` on a polygon — a real foreign key to a line's ``globalid``, but
  populated on only ~38% of polygons.
* ``event_id`` — free text typed per WFO, populated on about half the records
  and not a controlled vocabulary.
* the geometries themselves.

This module links on **geometry and time only**, and stores the other two beside
the result rather than folding them in. That separation is what allows
``evaluate.py`` to use ``path_guid`` as an untouched gold standard, and it keeps
``shared_event_id`` usable as an independent audit column.

Scale: 11.5k lines x 10k polygons is 115M pairs, so candidates come from an
STRtree over the polygons instead of an all-pairs sweep.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Iterable

from shapely import STRtree

from .. import config
from .geometry import to_equal_area, to_shapely


# DAT writes an all-zero GUID where a polygon has no parent path. It passes a
# naive "IS NOT NULL AND <> ''" filter but references nothing: of 9,989 polygons
# in 2010-2025, 3,467 carry this placeholder and only 289 a real reference.
NULL_GUID = "{00000000-0000-0000-0000-000000000000}"


def real_path_guid(value: Any) -> str | None:
    """The polygon's parent-line GUID, or None if absent/placeholder."""
    text = str(value or "").strip().upper()
    return None if text in ("", NULL_GUID) else text


def _parse_date(value: Any) -> dt.date | None:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _ef_number(value: Any) -> int | None:
    """Numeric EF rating, or None for EFU/UNKNOWN/TSTM-style labels."""
    text = str(value or "").upper()
    for digit in "012345":
        if f"EF{digit}" in text.replace(" ", "").replace("-", ""):
            return int(digit)
    return None


def prepare(features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach projected geometry and parsed fields to GeoJSON features.

    Features whose geometry cannot be made valid are dropped and reported by the
    caller; they cannot participate in a metric linkage either way.
    """
    prepared = []
    for feature in features:
        geom = to_shapely(feature.get("geometry"))
        if geom is None:
            continue
        props = feature.get("properties", {})
        prepared.append({
            "properties": props,
            "geom": geom,
            "proj": to_equal_area(geom),
            "objectid": props.get("objectid"),
            "globalid": str(props.get("globalid") or "").upper(),
            "event_id": str(props.get("event_id") or "").strip().lower(),
            "path_guid": real_path_guid(props.get("path_guid")),
            "date": _parse_date(props.get("stormdate")),
            "ef": _ef_number(props.get("efscale")),
        })
    return prepared


def _confidence(gap_m: float, frac_inside: float, gap_threshold_m: float) -> float:
    """Geometric link confidence in [0, 1].

    Half the score is how much of the track lies inside the polygon, half is
    proximity. Deliberately *not* a function of event_id or path_guid: those stay
    independent so they can validate this number.
    """
    proximity = 1.0 if gap_m <= 0 else max(0.0, 1.0 - gap_m / gap_threshold_m)
    return round(min(1.0, 0.5 * frac_inside + 0.5 * proximity), 4)


def link_lines_to_polygons(
    lines: list[dict[str, Any]], polygons: list[dict[str, Any]], *,
    search_radius_m: float = config.LINK_SEARCH_RADIUS_M,
    confidence_scale_m: float = config.LINK_GAP_THRESHOLD_M,
    buffer_m: float = config.LINK_BUFFER_M,
    max_date_delta_days: int | None = config.LINK_SEARCH_MAX_DATE_DELTA_DAYS,
    progress: bool = True,
) -> list[dict[str, Any]]:
    """All candidate (line, polygon) pairs within ``search_radius_m``.

    The radius is wider than the accepted-link threshold on purpose: the sweep in
    ``evaluate.py`` needs near-misses to score operating points, and a pair just
    outside the threshold is information, not noise. Acceptance is a downstream
    filter on ``gap_m`` / ``date_delta_days``, not a decision taken here.

    ``max_date_delta_days`` guards against linking a polygon to a line from a
    different tornado at the same place years apart — harmless on a
    single-outbreak prototype, essential over a 16-year national window. Pairs
    with a missing stormdate on either side are kept and flagged via
    ``date_known`` rather than silently dropped.
    """
    if not lines or not polygons:
        return []

    tree = STRtree([p["proj"] for p in polygons])
    records: list[dict[str, Any]] = []

    for i, line in enumerate(lines):
        line_proj = line["proj"]
        length = line_proj.length
        for index in tree.query(line_proj.buffer(search_radius_m)):
            polygon = polygons[index]

            date_delta = None
            if line["date"] and polygon["date"]:
                date_delta = abs((line["date"] - polygon["date"]).days)
                if max_date_delta_days is not None and date_delta > max_date_delta_days:
                    continue

            gap = line_proj.distance(polygon["proj"])
            if gap > search_radius_m:
                continue

            inside = line_proj.intersection(polygon["proj"].buffer(buffer_m))
            frac_inside = (inside.length / length) if length else 0.0
            records.append({
                "line_oid": line["objectid"],
                "line_globalid": line["globalid"],
                "line_event_id": line["properties"].get("event_id"),
                "line_efscale": line["properties"].get("efscale"),
                "line_stormdate": line["properties"].get("stormdate"),
                "line_wfo": line["properties"].get("wfo"),
                "polygon_oid": polygon["objectid"],
                "polygon_globalid": polygon["globalid"],
                "polygon_event_id": polygon["properties"].get("event_id"),
                "polygon_efscale": polygon["properties"].get("efscale"),
                "polygon_stormdate": polygon["properties"].get("stormdate"),
                # ── geometric + temporal evidence (drives link_confidence) ──
                "gap_m": round(gap, 1),
                "frac_line_in_polygon": round(frac_inside, 4),
                "centroid_dist_m": round(line_proj.distance(polygon["proj"].centroid), 1),
                "polygon_area_m2": round(polygon["proj"].area, 1),
                "line_length_m": round(length, 1),
                "date_delta_days": date_delta,
                "date_known": bool(line["date"] and polygon["date"]),
                "link_method": "spatial_temporal_join",
                "link_confidence": _confidence(gap, frac_inside, confidence_scale_m),
                # ── independent signals, recorded but never used above ──
                "shared_event_id": bool(line["event_id"]) and line["event_id"] == polygon["event_id"],
                "path_guid_match": polygon["path_guid"] == line["globalid"] if polygon["path_guid"] else False,
                "ef_agreement": (None if line["ef"] is None or polygon["ef"] is None
                                 else line["ef"] == polygon["ef"]),
            })

        if progress and (i + 1) % 500 == 0:
            print(f"  linked {i + 1}/{len(lines)} lines, {len(records)} candidates",
                  end="\r", flush=True)

    if progress:
        print(f"  linked {len(lines)}/{len(lines)} lines, {len(records)} candidates")
    return records


def accepted(records: Iterable[dict[str, Any]], *,
             gap_threshold_m: float = config.LINK_GAP_THRESHOLD_M,
             max_date_delta_days: int | None = config.LINK_MAX_DATE_DELTA_DAYS,
             ) -> list[dict[str, Any]]:
    """Candidates that meet the accepted-link thresholds (see config)."""
    out = []
    for record in records:
        if record["gap_m"] > gap_threshold_m:
            continue
        delta = record["date_delta_days"]
        if (max_date_delta_days is not None and delta is not None
                and delta > max_date_delta_days):
            continue
        out.append(record)
    return out


def best_line_per_polygon(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Reduce candidates to one line per polygon: most containment, then least gap."""
    best: dict[Any, dict[str, Any]] = {}
    for record in records:
        key = record["polygon_oid"]
        current = best.get(key)
        if current is None or ((record["frac_line_in_polygon"], -record["gap_m"])
                               > (current["frac_line_in_polygon"], -current["gap_m"])):
            best[key] = record
    return list(best.values())

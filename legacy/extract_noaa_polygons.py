from __future__ import annotations

import csv
import json
import re
import time
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import requests
from tqdm import tqdm

# ============================================================
# CONFIGURATION
# ============================================================

CONFIG: Dict[str, object] = {
    "geometry_type": "both",          # "polygons" | "lines" | "both"
    "start_date": date(1976, 3, 1),
    "end_date": date(2026, 6, 14),
    "non_empty_field": "comments",    # None to disable
    "exclude_placeholder_text": True, # also drop 'None'/'N/A'/'NULL' values of non_empty_field
    "extent": None,                   # (xmin, ymin, xmax, ymax) in EPSG:3857 or None
    "output_dir": "data",            # resolved relative to the repo root
    "output_format": "geojson",       # "json" | "csv" | "geojson"
    "chunk_size": 200,
    "sleep_seconds": 0.2,
    "group_into_events": True,        # also emit an events_*.geojson grouping
    "event_cluster_buffer_deg": 0.05, # bbox buffer (~5 km) for events without event_id
    "event_cluster_max_hours": 24,    # max stormdate gap for events without event_id
}

# Placeholder strings used by the DAT editor in place of an actual NULL.
PLACEHOLDER_TEXT_VALUES: Tuple[str, ...] = ("NONE", "N/A", "NULL")

# ============================================================
# INTERNAL CONSTANTS
# ============================================================

BASE_URL: str = (
    "https://services.dat.noaa.gov/arcgis/rest/services/"
    "nws_damageassessmenttoolkit/DamageViewer/FeatureServer"
)

LAYERS: Dict[str, int] = {
    "lines": 1,
    "polygons": 2,
}

SESSION: requests.Session = requests.Session()

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def build_where_clause() -> str:
    """Build an ArcGIS SQL WHERE clause for server-side filtering from CONFIG."""
    clauses: List[str] = [
        f"stormdate >= DATE '{CONFIG['start_date']}'",
        f"stormdate < DATE '{CONFIG['end_date']}'",
    ]

    field: Optional[str] = CONFIG.get("non_empty_field")  # type: ignore
    if field:
        clauses.append(f"{field} IS NOT NULL")
        clauses.append(f"{field} <> ''")

        if CONFIG.get("exclude_placeholder_text", True):
            placeholders = ", ".join(f"'{v}'" for v in PLACEHOLDER_TEXT_VALUES)
            clauses.append(f"UPPER({field}) NOT IN ({placeholders})")

    return " AND ".join(clauses)


def selected_layers() -> Iterable[Tuple[str, int]]:
    """Return the (layer_name, layer_id) pairs to query, per CONFIG['geometry_type']."""
    geometry_type: str = CONFIG["geometry_type"]  # type: ignore

    if geometry_type == "both":
        return LAYERS.items()

    return [(geometry_type, LAYERS[geometry_type])]


def get_object_ids(layer_id: int, where: str) -> List[int]:
    """Query the FeatureServer for all object IDs matching ``where``.

    ``returnIdsOnly`` is not subject to the server's maxRecordCount, so this
    returns the full result set in a single request.
    """
    params: Dict[str, object] = {
        "where": where,
        "returnIdsOnly": "true",
        "f": "json",
    }

    extent: Optional[Tuple[float, float, float, float]] = CONFIG.get("extent")  # type: ignore
    if extent:
        xmin, ymin, xmax, ymax = extent
        params.update({
            "geometryType": "esriGeometryEnvelope",
            "geometry": f"{xmin},{ymin},{xmax},{ymax}",
            "inSR": 3857,
            "spatialRel": "esriSpatialRelIntersects",
        })

    url: str = f"{BASE_URL}/{layer_id}/query"
    response: requests.Response = SESSION.get(url, params=params, timeout=60)
    response.raise_for_status()
    data: Dict[str, object] = response.json()

    if "error" in data:
        raise RuntimeError(data["error"])

    return data.get("objectIds", [])  # type: ignore


def fetch_features(layer_id: int, object_ids: List[int]) -> List[Dict[str, object]]:
    """Fetch Esri JSON features for ``object_ids`` in chunks of CONFIG['chunk_size'].

    When the output format is GeoJSON, the server is asked to return
    coordinates in WGS 84 (EPSG:4326) as required by RFC 7946.
    """
    features: List[Dict[str, object]] = []
    url: str = f"{BASE_URL}/{layer_id}/query"
    chunk_size: int = CONFIG["chunk_size"]  # type: ignore

    for i in tqdm(range(0, len(object_ids), chunk_size)):
        chunk: List[int] = object_ids[i:i + chunk_size]

        params: Dict[str, object] = {
            "objectIds": ",".join(map(str, chunk)),
            "outFields": "*",
            "returnGeometry": "true",
            "f": "json",
        }

        # GeoJSON requires WGS 84 coordinates
        if CONFIG.get("output_format") == "geojson":
            params["outSR"] = 4326

        response: requests.Response = SESSION.get(url, params=params, timeout=60)
        response.raise_for_status()
        data: Dict[str, object] = response.json()

        features.extend(data.get("features", []))  # type: ignore
        time.sleep(CONFIG["sleep_seconds"])  # type: ignore

    return features


Ring = List[List[float]]
BBox = Tuple[float, float, float, float]


def _signed_area(ring: Ring) -> float:
    """Twice the signed area of ``ring`` (shoelace formula).

    Positive for counterclockwise rings, negative for clockwise rings
    (standard x/y orientation, which matches lon/lat coordinates).
    """
    total = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        total += x1 * y2 - x2 * y1
    return total / 2.0


def _close_ring(ring: Ring) -> Ring:
    if ring and ring[0] != ring[-1]:
        return ring + [ring[0]]
    return ring


def _ring_bbox(ring: Ring) -> BBox:
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    return min(xs), min(ys), max(xs), max(ys)


def _bbox_contains(outer: BBox, inner: BBox) -> bool:
    return (
        outer[0] <= inner[0]
        and outer[1] <= inner[1]
        and outer[2] >= inner[2]
        and outer[3] >= inner[3]
    )


def _oriented(ring: Ring, clockwise: bool) -> Ring:
    is_clockwise = _signed_area(ring) < 0
    return ring if is_clockwise == clockwise else ring[::-1]


def rings_to_geojson_geometry(rings: List[Ring]) -> Optional[Dict[str, object]]:
    """
    Convert Esri ``rings`` to an RFC 7946 compliant Polygon/MultiPolygon.

    Esri rings carry no explicit shell/hole flag; orientation alone
    distinguishes them, and that orientation is the opposite of what
    GeoJSON requires. This groups each ring with the smallest ring that
    fully encloses it (by bounding box) as its exterior shell, then
    re-orients exterior rings counterclockwise and holes clockwise.
    """
    closed: List[Ring] = [_close_ring(r) for r in rings if len(r) >= 4]
    if not closed:
        return None

    by_area = sorted(
        ({"ring": r, "bbox": _ring_bbox(r), "area": abs(_signed_area(r))} for r in closed),
        key=lambda item: item["area"],
        reverse=True,
    )

    shells: List[Dict[str, object]] = []
    for item in by_area:
        host = next(
            (
                shell
                for shell in shells
                if shell["bbox"] != item["bbox"] and _bbox_contains(shell["bbox"], item["bbox"])
            ),
            None,
        )
        if host is None:
            shells.append({"ring": item["ring"], "bbox": item["bbox"], "holes": []})
        else:
            host["holes"].append(item["ring"])

    polygons = [
        [_oriented(shell["ring"], clockwise=False)]
        + [_oriented(hole, clockwise=True) for hole in shell["holes"]]
        for shell in shells
    ]

    if len(polygons) == 1:
        return {"type": "Polygon", "coordinates": polygons[0]}
    return {"type": "MultiPolygon", "coordinates": polygons}


def esri_feature_to_geojson(
    feature: Dict[str, object],
    layer_name: str,
) -> Dict[str, object]:
    """Convert one Esri JSON feature (``attributes`` + ``geometry``) to an RFC 7946 GeoJSON Feature.

    ``layer_name`` is ``"polygons"`` or ``"lines"`` and selects the geometry mapping.
    """
    properties: Dict[str, object] = dict(feature.get("attributes", {}))
    esri_geom: Optional[Dict] = feature.get("geometry")

    geojson_geom: Optional[Dict[str, object]] = None

    if esri_geom is not None:
        if layer_name == "polygons":
            rings = esri_geom.get("rings")
            if rings:
                geojson_geom = rings_to_geojson_geometry(rings)

        elif layer_name == "lines":
            paths = esri_geom.get("paths")
            if paths:
                geojson_geom = (
                    {"type": "LineString", "coordinates": paths[0]}
                    if len(paths) == 1
                    else {"type": "MultiLineString", "coordinates": paths}
                )

    return {
        "type": "Feature",
        "geometry": geojson_geom,
        "properties": properties,
    }


def output_filename(layer_name: str) -> str:
    """Build a descriptive output filename for ``layer_name`` from CONFIG."""
    parts: List[str] = [
        layer_name,
        CONFIG["start_date"].isoformat(),  # type: ignore
        CONFIG["end_date"].isoformat(),    # type: ignore
    ]

    if CONFIG.get("non_empty_field"):
        parts.append(f"nonempty-{CONFIG['non_empty_field']}")

    if CONFIG.get("extent"):
        parts.append("bbox")

    return "_".join(parts) + "." + CONFIG.get("output_format", "json")  # type: ignore


def save_geojson(outfile: Path, geojson_features: List[Dict[str, object]]) -> None:
    """Write a list of GeoJSON Features as a FeatureCollection."""
    feature_collection: Dict[str, object] = {
        "type": "FeatureCollection",
        "features": geojson_features,
    }
    with outfile.open("w", encoding="utf-8") as fh:
        json.dump(feature_collection, fh, indent=2)


def save_features(
    outfile: Path,
    layer_name: str,
    layer_id: int,
    features: List[Dict[str, object]],
) -> None:
    """
    Persist raw Esri JSON features as CSV or JSON (see CONFIG['output_format']).

    * **csv** — attribute columns plus a ``geometry`` column containing the
      Esri JSON geometry serialised as a JSON string.
    * **json** — the original Esri JSON features wrapped in an envelope that
      records the layer name, id, date range and feature count.

    GeoJSON output is handled separately via :func:`save_geojson`.
    """
    fmt: str = CONFIG.get("output_format", "json")  # type: ignore

    if fmt == "csv":
        rows: List[Dict[str, object]] = []
        for feat in features:
            row: Dict[str, object] = dict(feat.get("attributes", {}))
            geom = feat.get("geometry")
            row["geometry"] = json.dumps(geom) if geom is not None else ""
            rows.append(row)

        if not rows:
            outfile.write_text("", encoding="utf-8")
            return

        fieldnames: List[str] = list(dict.fromkeys(k for row in rows for k in row))

        with outfile.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

    else:  # json (default / original behaviour)
        payload: Dict[str, object] = {
            "layer": layer_name,
            "layer_id": layer_id,
            "start_date": CONFIG["start_date"].isoformat(),  # type: ignore
            "end_date": CONFIG["end_date"].isoformat(),      # type: ignore
            "feature_count": len(features),
            "features": features,
        }
        with outfile.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)


# ============================================================
# EVENT GROUPING
# ============================================================

# event_id is free text entered per-WFO: only ~50% of records have one, and
# it is not a controlled vocabulary. It is still the best grouping signal
# when present, so records sharing a non-empty event_id are merged first.
# Everything else is clustered by stormdate proximity + bbox overlap.

_EF_PATTERN = re.compile(r"EF\s*(\d)", re.IGNORECASE)


def _ef_rank(value: object) -> float:
    """Rank an ``efscale`` value so the most severe rating can be picked.

    Non-EF ratings ("TSTM/Wind", "UNKNOWN", "N/A", "Tropical", "EFU", ...)
    rank below any numbered EF rating but above a missing value.
    """
    if not value:
        return -2
    match = _EF_PATTERN.search(str(value))
    if not match:
        return -1
    rank = float(match.group(1))
    return rank + 0.5 if "+" in str(value) else rank


def _clean_comment(value: object) -> Optional[str]:
    """Return ``value`` if it is a real comment, else ``None``.

    Filters out blanks and the ``'None'``/``'N/A'``/``'NULL'`` placeholder
    text the DAT editor writes in place of an actual NULL.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.upper() in PLACEHOLDER_TEXT_VALUES:
        return None
    return text


def _iter_points(coords: List) -> Iterable[List[float]]:
    """Recursively yield every [x, y] point nested within a coordinates array."""
    if not coords:
        return
    if isinstance(coords[0], (int, float)):
        yield coords
    else:
        for sub in coords:
            yield from _iter_points(sub)


def _feature_bbox(feature: Dict[str, object]) -> Optional[BBox]:
    geometry: Optional[Dict] = feature.get("geometry")  # type: ignore
    if not geometry:
        return None

    geometries = geometry["geometries"] if geometry["type"] == "GeometryCollection" else [geometry]
    points = [p for g in geometries for p in _iter_points(g["coordinates"])]
    if not points:
        return None

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def _bboxes_overlap(a: Optional[BBox], b: Optional[BBox], buffer: float) -> bool:
    if a is None or b is None:
        return False
    return not (
        a[2] + buffer < b[0]
        or b[2] + buffer < a[0]
        or a[3] + buffer < b[1]
        or b[3] + buffer < a[1]
    )


class _UnionFind:
    def __init__(self, size: int) -> None:
        self.parent: List[int] = list(range(size))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def _valid_numeric_values(field: str, props_list: List[Dict[str, object]]) -> List[float]:
    """Numeric values for ``field``, dropping NOAA's ``-99`` "missing" sentinel.

    width/length/injuries/fatalities/cropdamage/propdamage/maxwind are all
    non-negative quantities, so any negative value is a missing-data code
    rather than a real measurement.
    """
    return [
        v
        for p in props_list
        if isinstance(v := p.get(field), (int, float)) and v >= 0
    ]


def _max_numeric(field: str, props_list: List[Dict[str, object]]) -> Optional[float]:
    values = _valid_numeric_values(field, props_list)
    return max(values) if values else None


def _sum_numeric(field: str, props_list: List[Dict[str, object]]) -> Optional[float]:
    values = _valid_numeric_values(field, props_list)
    return sum(values) if values else None


def _aggregate_event(
    members: List[Tuple[str, Dict[str, object]]]
) -> Dict[str, object]:
    """
    Combine the polygon/line members of one tornado event into a single
    GeoJSON Feature.

    Attribute combination rules:

    * ``event_id`` — the shared, non-empty event_id (members without one
      contribute nothing).
    * ``stormdate`` — earliest value among members.
    * ``efscale`` — the most severe rating found (numeric EF ratings beat
      non-EF labels like "UNKNOWN" or "TSTM/Wind").
    * ``injuries`` / ``fatalities`` — max across members. These totals are
      typically repeated on every segment of the same event, so summing
      would multiply-count them.
    * ``cropdamage`` / ``propdamage`` / ``maxwind`` — max across the line
      members that carry these fields.
    * ``total_track_length`` — sum of the line segments' ``length``
      (distinct path segments genuinely add up to the total track length).
    * ``max_damage_width`` — max of the polygons' ``width``.
    * ``comments`` — all distinct, non-placeholder comments concatenated
      with " | ".
    * geometry — the single member geometry, or a GeometryCollection of
      all member geometries if there is more than one.
    """
    polys = [f for kind, f in members if kind == "polygons"]
    lines = [f for kind, f in members if kind == "lines"]
    props_list: List[Dict[str, object]] = [f["properties"] for _, f in members]  # type: ignore
    poly_props = [f["properties"] for f in polys]  # type: ignore
    line_props = [f["properties"] for f in lines]  # type: ignore

    event_ids = {
        str(p["event_id"]).strip()
        for p in props_list
        if p.get("event_id") and str(p["event_id"]).strip()
    }

    stormdates = [p["stormdate"] for p in props_list if p.get("stormdate") is not None]

    comments: List[str] = []
    for p in props_list:
        comment = _clean_comment(p.get("comments"))
        if comment and comment not in comments:
            comments.append(comment)

    ef_values = [p.get("efscale") for p in props_list if p.get("efscale")]
    best_ef = max(ef_values, key=_ef_rank) if ef_values else None

    wfo = next((p["wfo"] for p in line_props if p.get("wfo")), None)

    properties: Dict[str, object] = {
        "event_id": sorted(event_ids)[0] if event_ids else None,
        "stormdate": min(stormdates) if stormdates else None,
        "efscale": best_ef,
        "injuries": _max_numeric("injuries", props_list),
        "fatalities": _max_numeric("fatalities", props_list),
        "cropdamage": _max_numeric("cropdamage", line_props),
        "propdamage": _max_numeric("propdamage", line_props),
        "maxwind": _max_numeric("maxwind", line_props),
        "total_track_length": _sum_numeric("length", line_props),
        "max_damage_width": _max_numeric("width", poly_props),
        "comments": " | ".join(comments) if comments else None,
        "wfo": wfo,
        "n_polygons": len(polys),
        "n_lines": len(lines),
        "polygon_objectids": [p.get("objectid") for p in poly_props],
        "line_objectids": [p.get("objectid") for p in line_props],
        "polygon_globalids": [p.get("globalid") for p in poly_props],
        "line_globalids": [p.get("globalid") for p in line_props],
    }

    geometries = [f["geometry"] for _, f in members if f.get("geometry")]  # type: ignore
    if not geometries:
        geometry: Optional[Dict[str, object]] = None
    elif len(geometries) == 1:
        geometry = geometries[0]
    else:
        geometry = {"type": "GeometryCollection", "geometries": geometries}

    return {"type": "Feature", "geometry": geometry, "properties": properties}


def group_features_into_events(
    layer_features: Dict[str, List[Dict[str, object]]]
) -> List[Dict[str, object]]:
    """
    Group GeoJSON polygon/line features into tornado "events".

    Records sharing a non-empty ``event_id`` are merged first. Remaining
    records (about half of them have a blank ``event_id``) are clustered
    with any other record whose ``stormdate`` is within
    ``event_cluster_max_hours`` and whose bounding box overlaps within
    ``event_cluster_buffer_deg``.
    """
    items: List[Tuple[str, Dict[str, object]]] = [
        (layer_name, feature)
        for layer_name, features in layer_features.items()
        for feature in features
    ]
    n = len(items)
    uf = _UnionFind(n)

    eid_groups: Dict[str, List[int]] = {}
    for i, (_, feature) in enumerate(items):
        eid = feature["properties"].get("event_id")  # type: ignore
        if eid and str(eid).strip():
            eid_groups.setdefault(str(eid).strip(), []).append(i)
    for idxs in eid_groups.values():
        for j in idxs[1:]:
            uf.union(idxs[0], j)

    bboxes = [_feature_bbox(feature) for _, feature in items]
    stormdates = [feature["properties"].get("stormdate") for _, feature in items]  # type: ignore

    buffer_deg: float = CONFIG.get("event_cluster_buffer_deg", 0.05)  # type: ignore
    max_gap_ms: float = CONFIG.get("event_cluster_max_hours", 24) * 3600 * 1000  # type: ignore

    unlinked = [
        i
        for i, (_, feature) in enumerate(items)
        if not str(feature["properties"].get("event_id") or "").strip()  # type: ignore
        and stormdates[i] is not None
    ]
    unlinked.sort(key=lambda i: stormdates[i])

    for a in range(len(unlinked)):
        i = unlinked[a]
        for b in range(a + 1, len(unlinked)):
            j = unlinked[b]
            if stormdates[j] - stormdates[i] > max_gap_ms:
                break
            if uf.find(i) == uf.find(j):
                continue
            if _bboxes_overlap(bboxes[i], bboxes[j], buffer_deg):
                uf.union(i, j)

    clusters: Dict[int, List[int]] = {}
    for i in range(n):
        clusters.setdefault(uf.find(i), []).append(i)

    return [_aggregate_event([items[i] for i in idxs]) for idxs in clusters.values()]


# ============================================================
# MAIN
# ============================================================


def main() -> None:
    """
    Main entry point for the NOAA DAT extraction workflow.
    """
    fmt: str = CONFIG.get("output_format", "json")  # type: ignore
    if fmt not in {"json", "csv", "geojson"}:
        raise ValueError(
            f"output_format must be 'json', 'csv', or 'geojson', got '{fmt}'"
        )

    repo_root: Path = Path(__file__).resolve().parent.parent
    output_dir: Path = repo_root / str(CONFIG["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    where: str = build_where_clause()

    layer_geojson_features: Dict[str, List[Dict[str, object]]] = {}

    for layer_name, layer_id in selected_layers():
        print(f"\nExtracting {layer_name.upper()} (layer {layer_id})")

        object_ids: List[int] = get_object_ids(layer_id, where)
        print(f"  Found {len(object_ids)} features")

        if not object_ids:
            continue

        features: List[Dict[str, object]] = fetch_features(layer_id, object_ids)

        outfile: Path = output_dir / output_filename(layer_name)

        if fmt == "geojson":
            geojson_features = [esri_feature_to_geojson(f, layer_name) for f in features]
            save_geojson(outfile, geojson_features)
            layer_geojson_features[layer_name] = geojson_features
        else:
            save_features(outfile, layer_name, layer_id, features)

        print(f"  Saved {len(features)} features → {outfile}  [{fmt.upper()}]")

    if (
        CONFIG.get("group_into_events")
        and fmt == "geojson"
        and "polygons" in layer_geojson_features
        and "lines" in layer_geojson_features
    ):
        print("\nGrouping polygons and lines into events")

        events = group_features_into_events(layer_geojson_features)

        events_file: Path = output_dir / output_filename("events")
        save_geojson(events_file, events)

        total_members = sum(len(f) for f in layer_geojson_features.values())
        print(f"  Grouped {total_members} features into {len(events)} events → {events_file}")


if __name__ == "__main__":
    main()
"""Esri JSON -> GeoJSON -> shapely, plus the equal-area projection.

Esri rings carry no explicit shell/hole flag: orientation alone distinguishes
them, and that orientation is the *opposite* of what RFC 7946 requires. The
conversion here groups each ring with the smallest ring enclosing it and then
re-orients shells counterclockwise and holes clockwise. (Ported from
``src/extract_noaa_polygons.py``, which is where this was first worked out.)

Metric work happens in EPSG:5070 (CONUS Albers Equal Area) so that gaps and
containment fractions are metres rather than degrees.
"""

from __future__ import annotations

from typing import Any

import pyproj
from shapely.geometry import LineString, MultiLineString, MultiPolygon, Polygon, shape
from shapely.ops import transform

from .. import config

Ring = list[list[float]]
BBox = tuple[float, float, float, float]

_TO_EQUAL_AREA = pyproj.Transformer.from_crs(
    config.CRS_WGS84, config.CRS_EQUAL_AREA, always_xy=True).transform


def to_equal_area(geom):
    """Project a WGS84 shapely geometry to EPSG:5070 (metres)."""
    return transform(_TO_EQUAL_AREA, geom)


# ── ring handling ────────────────────────────────────────────────────────────
def _signed_area(ring: Ring) -> float:
    """Twice the signed area (shoelace): positive counterclockwise."""
    total = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        total += x1 * y2 - x2 * y1
    return total / 2.0


def _close_ring(ring: Ring) -> Ring:
    return ring + [ring[0]] if ring and ring[0] != ring[-1] else ring


def _ring_bbox(ring: Ring) -> BBox:
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    return min(xs), min(ys), max(xs), max(ys)


def _bbox_contains(outer: BBox, inner: BBox) -> bool:
    return (outer[0] <= inner[0] and outer[1] <= inner[1]
            and outer[2] >= inner[2] and outer[3] >= inner[3])


def _oriented(ring: Ring, clockwise: bool) -> Ring:
    is_clockwise = _signed_area(ring) < 0
    return ring if is_clockwise == clockwise else ring[::-1]


def rings_to_geojson(rings: list[Ring]) -> dict[str, Any] | None:
    """Convert Esri ``rings`` to an RFC 7946 Polygon/MultiPolygon."""
    closed = [_close_ring(r) for r in rings if len(r) >= 4]
    if not closed:
        return None

    by_area = sorted(
        ({"ring": r, "bbox": _ring_bbox(r), "area": abs(_signed_area(r))} for r in closed),
        key=lambda item: item["area"], reverse=True)

    shells: list[dict[str, Any]] = []
    for item in by_area:
        host = next((shell for shell in shells
                     if shell["bbox"] != item["bbox"]
                     and _bbox_contains(shell["bbox"], item["bbox"])), None)
        if host is None:
            shells.append({"ring": item["ring"], "bbox": item["bbox"], "holes": []})
        else:
            host["holes"].append(item["ring"])

    polygons = [[_oriented(shell["ring"], clockwise=False)]
                + [_oriented(hole, clockwise=True) for hole in shell["holes"]]
                for shell in shells]

    if len(polygons) == 1:
        return {"type": "Polygon", "coordinates": polygons[0]}
    return {"type": "MultiPolygon", "coordinates": polygons}


def paths_to_geojson(paths: list[Ring]) -> dict[str, Any] | None:
    """Convert Esri ``paths`` to a GeoJSON LineString/MultiLineString."""
    usable = [p for p in paths if len(p) >= 2]
    if not usable:
        return None
    if len(usable) == 1:
        return {"type": "LineString", "coordinates": usable[0]}
    return {"type": "MultiLineString", "coordinates": usable}


def esri_to_geojson_geometry(esri_geometry: dict[str, Any] | None) -> dict[str, Any] | None:
    """Convert either flavour of DAT geometry (rings or paths) to GeoJSON."""
    if not esri_geometry:
        return None
    if "rings" in esri_geometry:
        return rings_to_geojson(esri_geometry["rings"])
    if "paths" in esri_geometry:
        return paths_to_geojson(esri_geometry["paths"])
    if "x" in esri_geometry and "y" in esri_geometry:
        return {"type": "Point", "coordinates": [esri_geometry["x"], esri_geometry["y"]]}
    return None


def to_shapely(geojson_geometry: dict[str, Any] | None):
    """Build a valid shapely geometry, repairing self-intersections.

    DAT features are hand-digitised and a small share are self-intersecting.
    ``buffer(0)`` fixes those; an unfixable geometry returns None so the caller
    can count it rather than crash mid-run.
    """
    if not geojson_geometry:
        return None
    try:
        geom = shape(geojson_geometry)
    except Exception:
        return None
    if geom.is_empty:
        return None
    if not geom.is_valid:
        geom = geom.buffer(0)
        if geom.is_empty or not geom.is_valid:
            return None
    if isinstance(geom, (Polygon, MultiPolygon, LineString, MultiLineString)):
        return geom
    return geom


def endpoints(geom) -> list[tuple[float, float]]:
    """First and last vertex of a (multi)line — used for track continuity."""
    if isinstance(geom, LineString):
        return [geom.coords[0], geom.coords[-1]]
    if isinstance(geom, MultiLineString):
        points: list[tuple[float, float]] = []
        for part in geom.geoms:
            points.extend([part.coords[0], part.coords[-1]])
        return points
    return []

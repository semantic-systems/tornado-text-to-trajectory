"""Projected metres -> integer screen coordinates, shared by everything that draws.

Both the national hazard map and the viewer's per-event thumbnails have to agree
on how a track becomes pixels, so the transform lives here rather than in either
of them. The national map fixes ``BOUNDS`` to CONUS; the viewer passes the bounds
of a single episode instead, which is the only difference between the two uses.

Coordinates are emitted as integers in **sub-pixel units** (``PRECISION`` per
pixel). Rounding straight to whole pixels looks fine at the scale it was rounded
for and turns into a staircase the moment anything zooms in, because the detail
is already gone by then.
"""

from __future__ import annotations

from typing import Callable, Iterable, Sequence

# CONUS plus a margin, in EPSG:5070 metres. Fixed so the national map's cached
# output is reproducible between runs.
CONUS_BOUNDS = (-2_400_000.0, 100_000.0, 2_550_000.0, 3_250_000.0)
PRECISION = 32


def make_projector(width: int, height: int,
                   bounds: Sequence[float] = CONUS_BOUNDS,
                   precision: int = PRECISION) -> Callable[[float, float], tuple[int, int]]:
    """Build a metres -> sub-pixel transform, y flipped, aspect preserved."""
    minx, miny, maxx, maxy = bounds
    span_x = max(maxx - minx, 1e-9)
    span_y = max(maxy - miny, 1e-9)
    scale = min(width / span_x, height / span_y)
    offset_x = (width - span_x * scale) / 2
    offset_y = (height - span_y * scale) / 2

    def to_world(x: float, y: float) -> tuple[int, int]:
        return (round(((x - minx) * scale + offset_x) * precision),
                round((height - ((y - miny) * scale + offset_y)) * precision))

    return to_world


def ring_to_world(coords: Iterable[Sequence[float]], to_world, project) -> list[int]:
    """Flatten a WGS84 ring/path to a flat ``[x0, y0, x1, y1, …]`` list."""
    flat: list[int] = []
    last: tuple[int, int] | None = None
    for lon, lat in coords:
        x, y = to_world(*project(lon, lat))
        if (x, y) != last:                      # drop coincident vertices
            flat.extend((x, y))
            last = (x, y)
    return flat


def bounds_of(paths: Iterable[Sequence[int]]) -> list[int]:
    """Bounding box of a set of flat paths, for viewport culling."""
    xs = [p[i] for p in paths for i in range(0, len(p), 2)]
    ys = [p[i] for p in paths for i in range(1, len(p), 2)]
    return [min(xs), min(ys), max(xs), max(ys)]


# ── Web Mercator, for drawing over map tiles ─────────────────────────────────
# Tiles (OpenStreetMap) come in Web Mercator, so a map drawn over them has to use
# it too. Coordinates are Leaflet's "world pixels" at a fixed reference zoom:
# at zoom 14 one unit is about 7.5 m at 38°N, finer than any simplification
# tolerance used, and the browser scales by 2^(zoom - MERCATOR_ZOOM).
MERCATOR_ZOOM = 14


def mercator_world(lon: float, lat: float, zoom: int = MERCATOR_ZOOM) -> tuple[int, int]:
    """WGS84 -> integer Web Mercator pixel at ``zoom`` (Leaflet's ``map.project``)."""
    import math
    size = 256 * 2 ** zoom
    lat = max(min(lat, 85.0511287798), -85.0511287798)
    s = math.sin(math.radians(lat))
    x = (lon + 180.0) / 360.0 * size
    y = (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * size
    return round(x), round(y)


def ring_to_mercator(coords: Iterable[Sequence[float]], zoom: int = MERCATOR_ZOOM) -> list[int]:
    """Flatten a WGS84 ring/path to Web Mercator ``[x0, y0, x1, y1, …]``."""
    flat: list[int] = []
    last: tuple[int, int] | None = None
    for lon, lat in coords:
        xy = mercator_world(lon, lat, zoom)
        if xy != last:                          # drop coincident vertices
            flat.extend(xy)
            last = xy
    return flat

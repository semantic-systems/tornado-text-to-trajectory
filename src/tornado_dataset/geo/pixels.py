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

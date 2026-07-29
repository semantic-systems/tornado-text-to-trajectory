"""Where a hazard happened: counties, states, WFO, and nearby place names.

Two reference sources, both authoritative and both cached locally so a rerun
needs no network:

**NWS county UGC polygons** (Iowa Environmental Mesonet, ``/api/1/nws/ugcs``)
carry the Weather Forecast Office that serves each county. DAT records a ``wfo``
on only ~45% of hazards, and Stage B's NWS text retrieval needs one for all of
them, so the office is filled in by intersecting the hazard geometry with these
polygons. The assignment is *dated*: UGC-to-WFO mappings change as offices are
reorganised, so a yearly snapshot is fetched and the hazard is matched against
the snapshot for its own year rather than against today's map.

**GNIS Domestic Names** (USGS) supplies populated places. County names alone make
poor news queries — reporting says "a tornado hit Cave City", not "Sharp County"
— so each hazard also gets the populated places nearest its track.

Both layers exist to serve retrieval and linking, and neither is treated as
ground truth: what they produce is recorded per hazard with its provenance
(``wfo_source``, distances) so a later stage can audit or override it.
"""

from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path
from typing import Any, Iterable

from shapely import STRtree
from shapely.geometry import shape

from .. import config
from ..http import get_json
from .. import http as http_module

IEM_UGC_URL = "https://mesonet.agron.iastate.edu/api/1/nws/ugcs.geojson"
GNIS_URL = ("https://prd-tnm.s3.amazonaws.com/StagedProducts/GeographicNames/"
            "DomesticNames/DomesticNames_National_Text.zip")
GNIS_ARCHIVE_MEMBER = "Text/DomesticNames_National.txt"

# GNIS classes worth querying news for. "Populated Place" is the settlement
# class; "Civil" (townships, boroughs) is deliberately excluded — those names
# rarely appear in reporting and add noise to a place-name query.
GNIS_CLASSES = ("Populated Place",)


# ── NWS county / WFO polygons ────────────────────────────────────────────────
def ugc_snapshot_path(year: int) -> Path:
    return config.RAW_DIR / "gazetteer" / f"ugc_counties_{year}.geojson"


def fetch_ugc_snapshot(year: int, *, refresh: bool = False) -> dict[str, Any]:
    """County-level UGC polygons with their WFO, as of mid-``year``.

    Mid-year (1 June) is used as the reference date because it sits inside the
    US tornado season, so the snapshot reflects the office assignment in force
    for most of that year's events.
    """
    return get_json(IEM_UGC_URL, {"valid": f"{year}-06-01T00:00Z"},
                    cache_path=ugc_snapshot_path(year), refresh=refresh,
                    min_interval=1.0, timeout=600)


def load_counties(year: int, *, refresh: bool = False) -> list[dict[str, Any]]:
    """Prepared county records for one snapshot year (projected to metres)."""
    from ..dat.geometry import to_equal_area

    payload = fetch_ugc_snapshot(year, refresh=refresh)
    counties = []
    for feature in payload.get("features", []):
        props = feature.get("properties", {})
        ugc = str(props.get("ugc") or "")
        if len(ugc) < 3 or ugc[2] != "C":     # keep counties, drop forecast zones
            continue
        try:
            geom = shape(feature["geometry"])
        except Exception:
            continue
        if geom.is_empty:
            continue
        if not geom.is_valid:
            geom = geom.buffer(0)
        counties.append({
            "ugc": ugc, "county": props.get("name"), "state": props.get("state"),
            "wfo": props.get("wfo"), "geom": geom, "proj": to_equal_area(geom),
        })
    return counties


class CountyIndex:
    """Year-aware spatial index over NWS county polygons."""

    def __init__(self, years: Iterable[int], *, refresh: bool = False) -> None:
        self.by_year: dict[int, tuple[list[dict[str, Any]], STRtree]] = {}
        for year in sorted(set(years)):
            counties = load_counties(year, refresh=refresh)
            self.by_year[year] = (counties, STRtree([c["proj"] for c in counties]))

    def _nearest_year(self, year: int | None) -> int:
        available = sorted(self.by_year)
        if year is None:
            return available[-1]
        return min(available, key=lambda y: abs(y - year))

    def lookup(self, geom_proj, year: int | None) -> list[dict[str, Any]]:
        """Counties intersecting a projected geometry, in the right year's map."""
        counties, tree = self.by_year[self._nearest_year(year)]
        hits = []
        for index in tree.query(geom_proj):
            county = counties[index]
            if geom_proj.intersects(county["proj"]):
                hits.append(county)
        if not hits:  # a track that misses every polygon (offshore, or a gap)
            counties, tree = self.by_year[self._nearest_year(year)]
            nearest = tree.nearest(geom_proj)
            if nearest is not None:
                hits = [counties[int(nearest)]]
        return hits


# ── GNIS populated places ────────────────────────────────────────────────────
def gnis_archive_path() -> Path:
    return config.RAW_DIR / "gazetteer" / "DomesticNames_National_Text.zip"


def download_gnis(*, refresh: bool = False) -> Path:
    """Download the USGS national names file once (~37 MB)."""
    import requests

    path = gnis_archive_path()
    if path.exists() and not refresh:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(GNIS_URL, stream=True, timeout=900) as response:
        response.raise_for_status()
        with path.open("wb") as handle:
            for chunk in response.iter_content(1 << 20):
                handle.write(chunk)
    path.with_suffix(".meta.json").write_text(
        json.dumps({"url": GNIS_URL, "retrieved_at": http_module.utcnow_iso()}, indent=2),
        encoding="utf-8")
    return path


def load_places(classes: tuple[str, ...] = GNIS_CLASSES) -> list[dict[str, Any]]:
    """Populated places as ``{name, state, county, lat, lon}`` records."""
    archive = download_gnis()
    places = []
    with zipfile.ZipFile(archive) as bundle, bundle.open(GNIS_ARCHIVE_MEMBER) as handle:
        reader = csv.DictReader(io.TextIOWrapper(handle, encoding="utf-8-sig"),
                                delimiter="|")
        for row in reader:
            if row.get("feature_class") not in classes:
                continue
            try:
                lat = float(row["prim_lat_dec"])
                lon = float(row["prim_long_dec"])
            except (TypeError, ValueError):
                continue
            if not lat and not lon:
                continue
            places.append({"name": row["feature_name"], "state": row["state_name"],
                           "county": row["county_name"], "lat": lat, "lon": lon})
    return places


class PlaceIndex:
    """Nearest-populated-place lookup in equal-area metres."""

    def __init__(self, places: list[dict[str, Any]] | None = None) -> None:
        from ..dat.geometry import to_equal_area
        from shapely.geometry import Point

        self.places = places if places is not None else load_places()
        self.points = [to_equal_area(Point(p["lon"], p["lat"])) for p in self.places]
        self.tree = STRtree(self.points)

    def nearby(self, geom_proj, radius_m: float, limit: int = 8) -> list[dict[str, Any]]:
        """Places within ``radius_m`` of a projected geometry, nearest first."""
        hits = []
        for index in self.tree.query(geom_proj.buffer(radius_m)):
            distance = geom_proj.distance(self.points[index])
            if distance <= radius_m:
                hits.append({**self.places[index], "distance_m": round(distance, 1)})
        hits.sort(key=lambda p: p["distance_m"])
        return hits[:limit]

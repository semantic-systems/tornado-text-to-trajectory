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
import re
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
# Census sub-county population estimates: place name, state and population. GNIS
# carries no population at all, and without one there is no way to tell the town
# a newspaper names from the hamlet next to it.
CENSUS_POPULATION_URL = ("https://www2.census.gov/programs-surveys/popest/datasets/"
                         "2020-2024/cities/totals/sub-est2024.csv")
CENSUS_POPULATION_FIELD = "POPESTIMATE2024"

# Legal-status suffixes Census appends to a place name ("Tuscaloosa city").
_LEGAL_SUFFIXES = (
    " city", " town", " village", " borough", " township", " municipality",
    " cdp", " comunidad", " zona urbana", " urbana", " plantation", " gore",
    " grant", " location", " reservation", " charter township", " unified government",
    " metro government", " consolidated government", " metropolitan government",
)
# Abbreviations that differ between the gazetteer and how anyone writes them.
# GNIS stores "Saint Louis"; every newspaper writes "St. Louis"; Census writes
# "St. Louis city". One canonical form joins all three, and both surface forms
# are indexed so an article matches whichever it uses.
_ALIAS_EXPANSIONS = {"saint": "st", "fort": "ft", "mount": "mt"}

# GNIS classes worth querying news for. "Populated Place" is the settlement
# class; "Civil" (townships, boroughs) is deliberately excluded — those names
# rarely appear in reporting and add noise to a place-name query.
GNIS_CLASSES = ("Populated Place",)


# ── place-name normalisation and aliases ─────────────────────────────────────
_WORD_RE = re.compile(r"[a-z0-9]+")


def canonical_place_key(name: str) -> str:
    """One key per real place, whichever way the name is written or suffixed.

    Strips parenthetical qualifiers and Census legal suffixes, then folds the
    Saint/St., Fort/Ft. and Mount/Mt. variants together, so GNIS's "Saint Louis",
    Census's "St. Louis city" and a newspaper's "St. Louis" all reduce to the same
    thing.
    """
    text = re.sub(r"\s*\([^)]*\)", " ", str(name or "")).lower().strip()
    for suffix in _LEGAL_SUFFIXES:
        if text.endswith(suffix):
            text = text[: -len(suffix)]
            break
    words = _WORD_RE.findall(text)
    return " ".join(_ALIAS_EXPANSIONS.get(w, w) for w in words)


def alias_forms(name: str) -> set[str]:
    """Surface forms an article might use for this place, lowercased.

    Both the expanded and abbreviated spellings are produced, because which one
    appears is a house-style decision we cannot predict per outlet.
    """
    cleaned = re.sub(r"\s*\([^)]*\)", " ", str(name or "")).lower()
    words = _WORD_RE.findall(cleaned)
    if not words:
        return set()
    forms = {" ".join(words)}
    swaps = {**_ALIAS_EXPANSIONS, **{v: k for k, v in _ALIAS_EXPANSIONS.items()}}
    for i, word in enumerate(words):
        if word in swaps:
            variant = list(words)
            variant[i] = swaps[word]
            forms.add(" ".join(variant))
    return forms


# ── place population (prominence) ────────────────────────────────────────────
def population_path() -> Path:
    return config.RAW_DIR / "gazetteer" / "census_sub_est_population.csv"


def download_place_population(*, refresh: bool = False) -> Path:
    """Census sub-county population estimates, cached once (~7 MB)."""
    import requests

    path = population_path()
    if path.exists() and not refresh:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(CENSUS_POPULATION_URL, timeout=600)
    response.raise_for_status()
    path.write_bytes(response.content)
    path.with_suffix(".meta.json").write_text(
        json.dumps({"url": CENSUS_POPULATION_URL, "field": CENSUS_POPULATION_FIELD,
                    "retrieved_at": http_module.utcnow_iso()}, indent=2), encoding="utf-8")
    return path


def load_place_population() -> dict[tuple[str, str], int]:
    """``(canonical name, state name) -> population`` for incorporated places."""
    path = download_place_population()
    populations: dict[tuple[str, str], int] = {}
    # Census publishes this one in Latin-1, not UTF-8: Spanish place names
    # ("Peñasco") are what give it away.
    with path.open(encoding="latin-1", newline="") as handle:
        for row in csv.DictReader(handle):
            # 162 = incorporated place. State and county rows would otherwise
            # attach a state's population to a same-named town.
            if row.get("SUMLEV") != "162":
                continue
            try:
                population = int(row.get(CENSUS_POPULATION_FIELD) or 0)
            except ValueError:
                continue
            key = (canonical_place_key(row.get("NAME", "")),
                   str(row.get("STNAME", "")).strip().lower())
            if population > populations.get(key, 0):
                populations[key] = population
    return populations


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


def state_outlines(year: int, *, simplify_deg: float = 0.02,
                   refresh: bool = False) -> dict[str, Any]:
    """State boundaries, dissolved from the cached county polygons.

    Built from the same NWS county layer the WFO assignment uses, so the basemap
    and the analysis agree by construction and no extra download is needed. The
    result is cached because dissolving ~3,300 polygons is slow, and simplified
    because a map drawn at screen scale cannot show the detail anyway.
    """
    from shapely.geometry import mapping
    from shapely.ops import unary_union

    cache_path = config.INTERIM_DIR / f"state_outlines_{year}_{simplify_deg}.geojson"
    if cache_path.exists() and not refresh:
        return json.loads(cache_path.read_text(encoding="utf-8"))

    by_state: dict[str, list[Any]] = {}
    for county in load_counties(year):
        if county["state"]:
            by_state.setdefault(county["state"], []).append(county["geom"])

    # The UGC polygons are generalised for web display, so neighbouring counties
    # do not share exact edges and a plain union leaves every internal boundary
    # behind as a sliver. Dilating before the union and eroding afterwards closes
    # those gaps, which is what makes this a state outline rather than 3,300
    # county outlines.
    snap = simplify_deg / 2
    features = []
    for state, geoms in sorted(by_state.items()):
        merged = unary_union([g.buffer(snap) for g in geoms]).buffer(-snap)
        merged = merged.simplify(simplify_deg, preserve_topology=True)
        if merged.is_empty:
            continue
        features.append({"type": "Feature", "properties": {"state": state},
                         "geometry": mapping(merged)})
    payload = {"type": "FeatureCollection", "features": features}
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


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


def load_places(classes: tuple[str, ...] = GNIS_CLASSES,
                with_population: bool = True) -> list[dict[str, Any]]:
    """Populated places as ``{name, state, county, lat, lon, population}`` records.

    Population comes from the Census join and is 0 where the place is
    unincorporated — which is the normal case for the hamlets that dominate GNIS
    and exactly the signal needed to rank them below a real town.
    """
    archive = download_gnis()
    populations = load_place_population() if with_population else {}
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
            name = row["feature_name"]
            state = row["state_name"]
            places.append({
                "name": name, "state": state, "county": row["county_name"],
                "lat": lat, "lon": lon,
                "population": populations.get(
                    (canonical_place_key(name), str(state).strip().lower()), 0),
            })
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
        """Places within ``radius_m`` of a projected geometry, nearest first.

        This is what builds the GDELT query terms. Its behaviour is deliberately
        frozen: the query strings are cache keys for a multi-day sweep, so
        changing the selection here would invalidate every cached response.
        """
        hits = []
        for index in self.tree.query(geom_proj.buffer(radius_m)):
            distance = geom_proj.distance(self.points[index])
            if distance <= radius_m:
                hits.append({**self.places[index], "distance_m": round(distance, 1)})
        hits.sort(key=lambda p: p["distance_m"])
        return hits[:limit]

    def nearby_for_matching(
        self, geom_proj, *,
        radius_m: float = config.PLACE_MATCH_RADIUS_M,
        prominent_radius_m: float = config.PLACE_PROMINENT_RADIUS_M,
        prominent_min_population: int = config.PLACE_PROMINENT_MIN_POPULATION,
        limit: int = config.MAX_MATCH_PLACES_PER_HAZARD,
    ) -> list[dict[str, Any]]:
        """Every name an article might plausibly use for this event.

        Three sources, because coverage names places for three different reasons:
        everything close by (the damage), any sizeable city somewhat further out
        (the dateline and the "near X" framing), and — via
        :meth:`county_largest` — the county's main town.

        Ranked by population then proximity, so the cap trims hamlets rather than
        cities if it binds at all.
        """
        hits: dict[int, dict[str, Any]] = {}
        search = max(radius_m, prominent_radius_m)
        for index in self.tree.query(geom_proj.buffer(search)):
            distance = geom_proj.distance(self.points[index])
            place = self.places[index]
            near_enough = distance <= radius_m
            prominent = (distance <= prominent_radius_m
                         and place.get("population", 0) >= prominent_min_population)
            if near_enough or prominent:
                hits[index] = {**place, "distance_m": round(distance, 1),
                               "reason": "near" if near_enough else "prominent"}
        ranked = sorted(hits.values(),
                        key=lambda p: (-p.get("population", 0), p["distance_m"]))
        return ranked[:limit]

    def county_largest(self, county: str, state: str) -> dict[str, Any] | None:
        """The most populous place in a county — a county-seat proxy."""
        if not hasattr(self, "_by_county"):
            self._by_county: dict[tuple[str, str], dict[str, Any]] = {}
            for place in self.places:
                key = (str(place.get("county") or "").strip().lower(),
                       str(place.get("state") or "").strip().lower())
                current = self._by_county.get(key)
                if current is None or place.get("population", 0) > current.get("population", 0):
                    self._by_county[key] = place
        return self._by_county.get((str(county).strip().lower(),
                                    str(state).strip().lower()))

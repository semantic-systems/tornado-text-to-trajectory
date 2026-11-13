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

**Census population estimates** say which of those places is a town a newspaper
would name. GNIS carries no population, and a name is not unique within a state
(Mississippi has several Oxfords), so each incorporated place's population goes
to the same-named GNIS place nearest its Census Gazetteer point, not to every
place of that name.

All three are today's files: names and populations are current, not those of the
event year.

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
# Census Gazetteer: an interior point and the land area of every Census place, by
# the same GEOID (state + place code), so a population can be put on the map.
CENSUS_GAZETTEER_URL = ("https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
                        "2024_Gazetteer/2024_Gaz_place_national.zip")
# A GNIS point is accepted as the Census place when it lies within this distance
# plus three times the radius of a circle of the place's land area: GNIS puts a
# city's point at its historic centre, the Census at an interior point, and for
# large or elongated cities (Los Angeles, Galveston) the two are 15-20 km apart.
POPULATION_MATCH_BASE_M = 5_000.0

# Legal-status suffixes Census appends to a place name ("Tuscaloosa city"). Only
# Census names carry them: in GNIS and in an article "Oklahoma City" is the name.
_LEGAL_SUFFIXES = (
    " city", " town", " village", " borough", " township", " municipality",
    " cdp", " comunidad", " zona urbana", " urbana", " plantation", " gore",
    " grant", " location", " reservation", " charter township", " unified government",
    " metro government", " consolidated government", " metropolitan government",
    " urban county", " metro township", " city and borough",
)
# Consolidated city-county governments: GNIS and the news name the city, which is
# the first part ("Lexington-Fayette urban county" is Lexington).
_GOVERNMENT_SUFFIXES = (" urban county", " unified government", " metro government",
                        " consolidated government", " metropolitan government", "(balance)")
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


def canonical_place_key(name: str, *, census: bool = False) -> str:
    """One key per real place, whichever way the name is written.

    Strips parenthetical qualifiers and folds the Saint/St., Fort/Ft. and
    Mount/Mt. variants together, so GNIS's "Saint Louis", Census's "St. Louis
    city" (with ``census=True``) and a newspaper's "St. Louis" all reduce to the
    same thing. Census legal suffixes are stripped only from Census names:
    stripping " city" from GNIS's "Oklahoma City" left "oklahoma", which matched
    no Census place and shared its key with the state.
    """
    text = re.sub(r"\s*\([^)]*\)", " ", str(name or "")).lower().strip()
    if census:
        # Longest first, so " charter township" is not cut to " charter".
        for suffix in sorted(_LEGAL_SUFFIXES, key=len, reverse=True):
            if text.endswith(suffix):
                text = text[: -len(suffix)]
                break
    words = _WORD_RE.findall(text)
    return " ".join(_ALIAS_EXPANSIONS.get(w, w) for w in words)


def county_key(name: str) -> str:
    """One key per county, across the NWS UGC and GNIS spellings.

    Folds case, accents, spacing and punctuation ("De Kalb"/"DeKalb", "Prince
    Georges"/"Prince George's", "Dona Ana"/"Doña Ana", "St."/"Saint") and the
    independent-city forms ("City of Richmond", "Richmond (city)", "Baltimore
    City" all end in "city"). NWS splits a few coastal counties ("Mainland
    Dare"); the prefix is dropped.
    """
    import unicodedata

    text = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode()
    text = text.lower().strip()
    text = re.sub(r"^mainland\s+", "", text)
    city = text.startswith("city of ") or text.endswith("(city)")
    text = re.sub(r"^city of\s+|\s*\(city\)$", "", text)
    text = re.sub(r"\bsaint\b", "st", text)
    key = re.sub(r"[^a-z]", "", text)
    return key + "city" if city and not key.endswith("city") else key


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


def place_gazetteer_path() -> Path:
    return config.RAW_DIR / "gazetteer" / "census_place_gazetteer_2024.zip"


def download_place_gazetteer(*, refresh: bool = False) -> Path:
    """Census Gazetteer place file (points and land areas), cached once (~1 MB)."""
    import requests

    path = place_gazetteer_path()
    if path.exists() and not refresh:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(CENSUS_GAZETTEER_URL, timeout=600)
    response.raise_for_status()
    path.write_bytes(response.content)
    path.with_suffix(".meta.json").write_text(
        json.dumps({"url": CENSUS_GAZETTEER_URL,
                    "retrieved_at": http_module.utcnow_iso()}, indent=2), encoding="utf-8")
    return path


def load_place_points() -> dict[str, dict[str, float]]:
    """``GEOID -> {lat, lon, aland_m2}`` for every Census place."""
    points = {}
    with zipfile.ZipFile(download_place_gazetteer()) as bundle:
        member = next(n for n in bundle.namelist() if n.endswith(".txt"))
        with bundle.open(member) as handle:
            reader = csv.DictReader(io.TextIOWrapper(handle, encoding="utf-8"),
                                    delimiter="\t")
            for row in reader:
                row = {k.strip(): (v or "").strip() for k, v in row.items() if k}
                try:
                    points[row["GEOID"]] = {"lat": float(row["INTPTLAT"]),
                                            "lon": float(row["INTPTLONG"]),
                                            "aland_m2": float(row["ALAND"] or 0)}
                except (KeyError, ValueError):
                    continue
    return points


def load_place_population() -> list[dict[str, Any]]:
    """Incorporated places with name, state, population, point and land area."""
    path = download_place_population()
    points = load_place_points()
    records = []
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
            point = points.get(f"{row.get('STATE', '')}{row.get('PLACE', '')}")
            if point is None:
                continue
            records.append({"name": row.get("NAME", ""),
                            "state": str(row.get("STNAME", "")).strip().lower(),
                            "population": population, **point})
    return records


def _census_keys(name: str) -> list[str]:
    """Keys to look a Census name up by, most specific first.

    Census writes "Weymouth Town city", "Boise City city", "Carson City" (no
    suffix), "San Buenaventura (Ventura) city" and "Lexington-Fayette urban
    county"; GNIS writes Weymouth, Boise, Carson City, Ventura and Lexington. So:
    the name without its legal suffix, without all of them, as written, the
    alternative in parentheses, and the first part of a hyphenated or slashed
    name — that one first for consolidated city-county governments.
    """
    raw = str(name or "")
    plain = re.sub(r"\s*\([^)]*\)", "", raw).strip()
    once = canonical_place_key(raw, census=True)
    stripped = once
    while True:
        shorter = canonical_place_key(stripped, census=True)
        if shorter == stripped:
            break
        stripped = shorter
    keys = [once, stripped, canonical_place_key(plain)]
    keys += [canonical_place_key(alt, census=True) for alt in re.findall(r"\(([^)]*)\)", raw)]
    first = canonical_place_key(re.split(r"[-/]", plain)[0], census=True)
    if raw.lower().endswith(_GOVERNMENT_SUFFIXES):
        keys.insert(0, first)
    else:
        keys.append(first)
    return [k for k in dict.fromkeys(keys) if k]


def assign_population(places: list[dict[str, Any]],
                      census: list[dict[str, Any]]) -> dict[str, int]:
    """Set each GNIS place's ``population`` from the Census place it is.

    A Census place goes to the GNIS place of the same name and state nearest its
    Gazetteer point, if that lies within ``POPULATION_MATCH_BASE_M`` plus
    three times the radius of the place's land area; every other place of that name
    keeps 0.
    Returns counts for the manifest.
    """
    import math

    by_key: dict[tuple[str, str], list[int]] = {}
    for i, place in enumerate(places):
        place["population"] = 0
        key = canonical_place_key(place["name"])
        state = str(place["state"]).strip().lower()
        by_key.setdefault((key, state), []).append(i)
        # "LaGrange"/"La Grange", "Lees Summit"/"Lee's Summit": also without spaces.
        squeezed = key.replace(" ", "")
        if squeezed != key:
            by_key.setdefault((squeezed, state), []).append(i)
    stats = {"census_places": len(census), "assigned": 0, "no_gnis_name": 0,
             "gnis_too_far": 0, "ambiguous_names_resolved": 0}
    for record in census:
        candidates = []
        for key in _census_keys(record["name"]):
            candidates = (by_key.get((key, record["state"]))
                          or by_key.get((key.replace(" ", ""), record["state"]), []))
            if candidates:
                break
        if not candidates:
            stats["no_gnis_name"] += 1
            continue
        cos = math.cos(math.radians(record["lat"]))

        def distance_m(i: int) -> float:
            dx = (places[i]["lon"] - record["lon"]) * cos
            dy = places[i]["lat"] - record["lat"]
            return math.hypot(dx, dy) * 111_195.0

        best = min(candidates, key=distance_m)
        limit = POPULATION_MATCH_BASE_M + 3 * math.sqrt(record["aland_m2"] / math.pi)
        if distance_m(best) > limit:
            stats["gnis_too_far"] += 1
            continue
        stats["assigned"] += 1
        stats["ambiguous_names_resolved"] += len(candidates) > 1
        places[best]["population"] = max(places[best]["population"], record["population"])
    return stats


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

    def match(self, geom_proj, year: int | None) -> tuple[list[tuple[dict, float]], bool]:
        """The counties a hazard is in, with their share, and whether none intersected.

        Applies :func:`keep_counties` to the intersecting counties. With none (a
        track offshore or in a gap between outlines) it falls back to the nearest
        county and says so.
        """
        hits = self.lookup(geom_proj, year)
        fallback = bool(hits) and not geom_proj.intersects(hits[0]["proj"])
        if fallback:
            return [(hits[0], 0.0)], True
        shares, unit = county_shares(geom_proj, hits)
        kept = {id(c) for c in keep_counties(shares, unit)}
        return [(c, share) for c, share, _ in shares if id(c) in kept], False

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


def county_shares(geom_proj, counties: list[dict[str, Any]]
                  ) -> tuple[list[tuple[dict, float, float]], str]:
    """``(county, share, amount)`` for each county, largest share first, and the unit.

    Measured on the track lines where the hazard has any (unit ``length``,
    metres), else on its polygons (``area``, square metres), else by
    containment of the point (``point``).
    """
    from shapely.geometry import GeometryCollection

    parts = list(geom_proj.geoms) if isinstance(geom_proj, GeometryCollection) else [geom_proj]
    flat = []
    for part in parts:
        flat += list(part.geoms) if hasattr(part, "geoms") else [part]
    lines = [g for g in flat if g.geom_type in ("LineString", "LinearRing") and g.length > 0]
    polys = [g for g in flat if g.geom_type == "Polygon" and g.area > 0]
    if lines:
        unit, total = "length", sum(g.length for g in lines)
        amounts = [sum(g.intersection(c["proj"]).length for g in lines) for c in counties]
    elif polys:
        unit, total = "area", sum(g.area for g in polys)
        amounts = [sum(g.intersection(c["proj"]).area for g in polys) for c in counties]
    else:
        unit, total = "point", 1.0
        amounts = [1.0 if geom_proj.intersects(c["proj"]) else 0.0 for c in counties]
    out = [(c, a / total if total else 0.0, a) for c, a in zip(counties, amounts)]
    return sorted(out, key=lambda t: -t[1]), unit


def keep_counties(shares: list[tuple[dict, float, float]], unit: str) -> list[dict]:
    """The counties a hazard is in: ``config.COUNTY_MIN_SHARE`` of it, or
    ``COUNTY_MIN_TRACK_M`` / ``COUNTY_MIN_AREA_M2`` inside, and always the largest."""
    floor = config.COUNTY_MIN_AREA_M2 if unit == "area" else config.COUNTY_MIN_TRACK_M
    kept = [c for i, (c, share, amount) in enumerate(shares)
            if i == 0 or share >= config.COUNTY_MIN_SHARE or amount >= floor]
    return kept


def choose_wfo(dat: list[str], storm_events: list[str],
               spatial: list[str]) -> tuple[str | None, str, list[str]]:
    """The hazard's office, where it came from, and every office of every source.

    Sources in order of authority: DAT's own field (the surveying office), the
    linked Storm Events segments (the office that entered each; ``storm_events``
    ordered by segment start), the county join (``spatial`` ordered by share of
    the track). When DAT names several offices, the one where the tornado began
    by Storm Events, else the one with most of the track, is the primary.
    """
    if dat:
        ranked = [w for w in storm_events + spatial if w in dat] + dat
        primary, source = ranked[0], "dat"
    elif storm_events:
        primary, source = storm_events[0], "storm_events"
    elif spatial:
        primary, source = spatial[0], "spatial_join"
    else:
        return None, "none", []
    return primary, source, list(dict.fromkeys([primary] + dat + storm_events + spatial))


# US Census Bureau divisions (Census Regions and Divisions of the United States),
# for grouping tornadoes by area with a fixed, official mapping. Territories are
# kept apart rather than forced into a division.
CENSUS_DIVISIONS = {
    "New England": ("CT", "ME", "MA", "NH", "RI", "VT"),
    "Middle Atlantic": ("NJ", "NY", "PA"),
    "East North Central": ("IL", "IN", "MI", "OH", "WI"),
    "West North Central": ("IA", "KS", "MN", "MO", "NE", "ND", "SD"),
    "South Atlantic": ("DE", "DC", "FL", "GA", "MD", "NC", "SC", "VA", "WV"),
    "East South Central": ("AL", "KY", "MS", "TN"),
    "West South Central": ("AR", "LA", "OK", "TX"),
    "Mountain": ("AZ", "CO", "ID", "MT", "NV", "NM", "UT", "WY"),
    "Pacific": ("AK", "CA", "HI", "OR", "WA"),
}
_DIVISION_OF = {st: div for div, states in CENSUS_DIVISIONS.items() for st in states}


def census_division(state: str | None) -> str:
    """Census division of a two-letter state code; ``territory`` otherwise."""
    return _DIVISION_OF.get(str(state or "").strip().upper(), "territory")


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

    Population comes from :func:`assign_population` and is 0 where the place is
    unincorporated — which is the normal case for the hamlets that dominate GNIS
    and exactly the signal needed to rank them below a real town. The join's
    counts are on ``load_places.population_stats``.
    """
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
            places.append({
                "name": row["feature_name"], "state": row["state_name"],
                "county": row["county_name"], "lat": lat, "lon": lon, "population": 0,
            })
    load_places.population_stats = (assign_population(places, load_place_population())
                                    if with_population else {})
    return places


class PlaceIndex:
    """Nearest-populated-place lookup in equal-area metres."""

    def __init__(self, places: list[dict[str, Any]] | None = None) -> None:
        from ..dat.geometry import to_equal_area
        from shapely.geometry import Point

        self.places = places if places is not None else load_places()
        self.population_stats = (getattr(load_places, "population_stats", {})
                                 if places is None else {})
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
        """The most populous place in a county — a county-seat proxy.

        Counties are matched by :func:`county_key`, since NWS and GNIS spell
        them differently. A county where no place has a population returns
        None rather than an arbitrary hamlet.
        """
        if not hasattr(self, "_by_county"):
            self._by_county: dict[tuple[str, str], dict[str, Any]] = {}
            for place in self.places:
                if not place.get("population"):
                    continue
                key = (county_key(place.get("county") or ""),
                       str(place.get("state") or "").strip().lower())
                current = self._by_county.get(key)
                if current is None or place["population"] > current["population"]:
                    self._by_county[key] = place
        return self._by_county.get((county_key(county), str(state).strip().lower()))

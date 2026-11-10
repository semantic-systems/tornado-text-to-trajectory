"""Stage 16 — attach counties, states, WFO and place names to each hazard.

For every hazard of stage 15 — DAT hazards (stage 12) and SPC hazards (SPC
tornadoes with no DAT survey, straight SPC line) — in equal-area metres:

* **Counties** from the NWS county polygons of the hazard's own year: those
  holding ``config.COUNTY_MIN_SHARE`` of the track (or 1 km of it; of the damage
  area for a hazard with no track line), always the largest. With none
  intersecting, the nearest county, flagged ``county_fallback``.
* **WFO** from DAT's own field, else the linked Storm Events segments (stage 14),
  else the county join; ``wfo_all`` keeps every office of every source and
  ``wfo_source`` says where the primary came from (``gazetteer.choose_wfo``).
* **Places** from GNIS: ``places``, the eight nearest within 25 km (the GDELT
  query terms, kept unchanged because they are its cache keys), and
  ``places_matching``, the wide set stage 31 matches articles against —
  everything within 25 km, towns of 20,000+ within 50 km, and each county's
  largest place, ranked by Census population joined by location.

It also checks how well a straight SPC line stands in for a surveyed track: for
the DAT hazards with an SPC track, the counties and places from the SPC line are
compared with those from the DAT geometry.

    python scripts/16_enrich_geography.py

Needs stages 12, 14 and 15. Reads cached reference files from data/raw/gazetteer/
and downloads any that are missing (NWS county polygons per year, GNIS, Census
population and Gazetteer). Writes ``data/processed/hazard_geography_<tag>.csv``.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter

import _bootstrap  # noqa: F401

import numpy as np
import pandas as pd

from tornado_dataset import config
from tornado_dataset.dat import episode_table
from tornado_dataset.dat import references as refs
from tornado_dataset.dat.geometry import to_equal_area, to_shapely
from tornado_dataset.geo.gazetteer import CountyIndex, PlaceIndex, choose_wfo
from tornado_dataset.ids import write_manifest


def hazard_year(hazard: dict) -> int | None:
    day = hazard.get("convective_day")
    return int(str(day)[:4]) if day else None


def _state_name(code: str | None) -> str:
    """Two-letter code to the full state name GNIS uses."""
    from tornado_dataset.text.linking import STATE_NAMES

    return STATE_NAMES.get(str(code or "").upper(), "")


def _split(value) -> list[str]:
    return [w for w in str(value or "").split(";") if w and w != "nan"]


def storm_event_offices(tag: str) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Storm Events offices per DAT hazard and per SPC track, earliest segment first.

    A Storm Events row counts for the hazard (or track) it is best linked to
    (``rank_for_event == 1``).
    """
    begin = {}
    if refs.SE_TORNADOES.exists():
        se = pd.read_csv(refs.SE_TORNADOES, usecols=["EVENT_ID", "begin_utc"])
        begin = dict(zip(se.EVENT_ID, pd.to_datetime(se.begin_utc, utc=True, errors="coerce")))
    out = []
    for path, key in ((refs.se_links_path(tag), "hazard_uid"),
                      (refs.spc_se_links_path(tag), "spc_id")):
        offices: dict[str, list[str]] = {}
        if path.exists():
            links = pd.read_csv(path)
            links = links[(links.rank_for_event == 1) & links.WFO.notna()].copy()
            links["begin"] = links.EVENT_ID.map(begin)
            for k, g in links.sort_values("begin", na_position="last").groupby(key, sort=False):
                offices[k] = list(dict.fromkeys(g.WFO))
        out.append(offices)
    return out[0], out[1]


class Enricher:
    """Counties, office and places for one projected geometry."""

    def __init__(self, counties: CountyIndex, places: PlaceIndex, radius_m: float):
        self.counties, self.places, self.radius_m = counties, places, radius_m

    def __call__(self, proj, year: int | None) -> dict:
        matched, fallback = self.counties.match(proj, year)
        county_hits = [c for c, _ in matched]
        # `places` feeds the GDELT query strings and must stay byte-identical
        # to what the running sweep used, or every cache key changes.
        place_hits = self.places.nearby(proj, self.radius_m, limit=config.MAX_PLACES_PER_HAZARD)
        # `places_matching` is the wide set used to recognise an event in an
        # article: everything nearby, plus prominent cities further out, plus
        # each county's largest town.
        match_hits = self.places.nearby_for_matching(proj)
        if config.INCLUDE_COUNTY_LARGEST_PLACE:
            seen = {p["name"] for p in match_hits}
            for county in county_hits:
                largest = self.places.county_largest(county.get("county") or "",
                                                     _state_name(county.get("state")))
                if largest and largest["name"] not in seen:
                    match_hits.append({**largest, "distance_m": None, "reason": "county_largest"})
                    seen.add(largest["name"])
        spatial = list(dict.fromkeys(c["wfo"] for c in county_hits if c.get("wfo")))
        return {"county_hits": county_hits, "fallback": fallback, "place_hits": place_hits,
                "match_hits": match_hits, "spatial_wfos": spatial}


def load_features(tag: str) -> list[tuple[dict, str]]:
    """``(feature, hazard_source)`` for every DAT and SPC hazard."""
    dat_path = config.PROCESSED_DIR / f"hazards_{tag}.geojson"
    spc_path = episode_table.spc_hazards_path(tag, "geojson")
    for path, stage in ((dat_path, "12_build_hazards"), (spc_path, "15_build_episodes")):
        if not path.exists():
            raise SystemExit(f"missing {path.name} — run scripts/{stage}.py first")
    dat = json.loads(dat_path.read_text(encoding="utf-8"))["features"]
    spc = json.loads(spc_path.read_text(encoding="utf-8"))["features"]
    return [(f, "dat") for f in dat] + [(f, "spc") for f in spc]


def spc_line_check(tag: str, table: pd.DataFrame, enrich: Enricher) -> dict:
    """How well the straight SPC line reproduces the geography of the surveyed track.

    For each DAT hazard with an SPC track: the share of its counties and of its
    matching places (and of its places within 25 km) that the SPC line also
    yields, and whether the county join gives the same primary office.
    """
    from pyproj import Transformer
    from shapely.ops import transform

    from tornado_dataset.dat import spc_tornadoes

    member = episode_table.membership(tag)
    pairs = member[(member.hazard_source == "dat") & member.spc_id.notna()]
    tracks = pd.read_csv(refs.SPC_TRACKS, low_memory=False).set_index("spc_id")
    rows = tracks.loc[pairs.spc_id].reset_index()
    to_m = Transformer.from_crs(config.CRS_WGS84, config.CRS_EQUAL_AREA, always_xy=True)
    geoms = spc_tornadoes.track_geometries(rows, lambda g: transform(to_m.transform, g))
    dat = table.set_index("hazard_uid")
    near_radius = config.PLACE_MATCH_RADIUS_M
    out = []
    for hazard_uid, geom, day in zip(pairs.hazard_uid, geoms, rows.date):
        if geom is None or hazard_uid not in dat.index:
            continue
        mine = dat.loc[hazard_uid]
        result = enrich(geom, int(str(day)[:4]))
        counties = set(_split(mine.county_ugcs))
        spc_counties = {c["ugc"] for c in result["county_hits"]}
        places = set(_split(mine.places_matching))
        spc_places = {p["name"] for p in result["match_hits"]}
        near = set(_split(mine.places_near))
        spc_near = {p["name"] for p in result["match_hits"]
                    if p.get("distance_m") is not None and p["distance_m"] <= near_radius}
        out.append({
            "point": geom.geom_type == "Point",
            "county_recall": len(counties & spc_counties) / len(counties) if counties else np.nan,
            "county_equal": counties == spc_counties,
            "place_recall": len(places & spc_places) / len(places) if places else np.nan,
            "near_recall": len(near & spc_near) / len(near) if near else np.nan,
            "wfo_equal": (_split(mine.wfo_spatial)[:1] == result["spatial_wfos"][:1]),
        })
    frame = pd.DataFrame(out)

    def summary(f: pd.DataFrame) -> dict:
        return {"pairs": len(f),
                "county_recall_mean": round(float(f.county_recall.mean()), 4),
                "county_sets_equal": round(float(f.county_equal.mean()), 4),
                "matching_place_recall_mean": round(float(f.place_recall.mean()), 4),
                "near_place_recall_mean": round(float(f.near_recall.mean()), 4),
                "near_place_recall_median": round(float(f.near_recall.median()), 4),
                "spatial_wfo_equal": round(float(f.wfo_equal.mean()), 4)}

    return {"all": summary(frame), "spc_lines": summary(frame[~frame.point]),
            "spc_points": summary(frame[frame.point])}


def agreement(table: pd.DataFrame) -> dict:
    """Pairwise agreement of the three office sources, where both have one."""
    cols = {"dat": "wfo_dat", "storm_events": "wfo_storm_events", "spatial_join": "wfo_spatial"}
    lists = {k: table[c].map(_split) for k, c in cols.items()}
    out = {}
    for a, b in (("dat", "storm_events"), ("dat", "spatial_join"),
                 ("storm_events", "spatial_join")):
        both = lists[a].map(bool) & lists[b].map(bool)
        la, lb = lists[a][both], lists[b][both]
        out[f"{a}_vs_{b}"] = {
            "hazards": int(both.sum()),
            "any_office_shared": round(float(np.mean([bool(set(x) & set(y))
                                                      for x, y in zip(la, lb)])), 4)
            if both.any() else None,
            "same_offices": round(float(np.mean([set(x) == set(y) for x, y in zip(la, lb)])), 4)
            if both.any() else None,
        }
    out["several_offices"] = {k: int((v.map(len) > 1).sum()) for k, v in lists.items()}
    return out


def main() -> None:
    default_tag = f"{config.WINDOW_START.isoformat()}_{config.WINDOW_END.isoformat()}"
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", default=default_tag)
    parser.add_argument("--place-radius-m", type=float, default=config.PLACE_RADIUS_M)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    features = load_features(args.tag)
    member = episode_table.membership(args.tag).set_index("hazard_uid")
    spc_id_of = member.spc_id.to_dict()
    se_dat, se_spc = storm_event_offices(args.tag)

    years = {hazard_year(f["properties"]) for f, _ in features} - {None}
    print(f"loading NWS county polygons for {len(years)} snapshot years …")
    counties = CountyIndex(sorted(years), refresh=args.refresh)
    print("loading GNIS populated places and Census populations …")
    places = PlaceIndex()
    print(f"  {len(places.places)} populated places indexed; population join: "
          f"{places.population_stats}")
    enrich = Enricher(counties, places, args.place_radius_m)

    rows, wfo_sources = [], Counter()
    for i, (feature, source) in enumerate(features, 1):
        props = feature["properties"]
        uid_ = props["hazard_uid"]
        geom = to_shapely(feature.get("geometry"))
        result = (enrich(to_equal_area(geom), hazard_year(props)) if geom is not None else
                  {"county_hits": [], "fallback": False, "place_hits": [], "match_hits": [],
                   "spatial_wfos": []})
        county_hits, match_hits = result["county_hits"], result["match_hits"]
        place_hits = result["place_hits"]

        dat_wfos = _split(props.get("wfo_all")) if source == "dat" else []
        se_wfos = (se_dat.get(uid_, []) if source == "dat"
                   else se_spc.get(spc_id_of.get(uid_), []))
        wfo, wfo_source, wfo_all = choose_wfo(dat_wfos, se_wfos, result["spatial_wfos"])
        wfo_sources[(source, wfo_source)] += 1

        rows.append({
            "hazard_uid": uid_,
            "hazard_source": source,
            "geometry_source": props.get("geometry_source"),
            "convective_day": props.get("convective_day"),
            "wfo": wfo,
            "wfo_source": wfo_source,
            "wfo_all": ";".join(wfo_all),
            "wfo_dat": ";".join(dat_wfos),
            "wfo_storm_events": ";".join(se_wfos),
            "wfo_spatial": ";".join(result["spatial_wfos"]),
            "counties": ";".join(f"{c['county']}, {c['state']}" for c in county_hits),
            "county_ugcs": ";".join(c["ugc"] for c in county_hits),
            "states": ";".join(sorted({c["state"] for c in county_hits if c.get("state")})),
            "n_counties": len(county_hits),
            "county_fallback": result["fallback"],
            "places": ";".join(p["name"] for p in place_hits),
            "place_states": ";".join(sorted({p["state"] for p in place_hits})),
            "nearest_place": place_hits[0]["name"] if place_hits else None,
            "nearest_place_m": place_hits[0]["distance_m"] if place_hits else None,
            "n_places": len(place_hits),
            "places_matching": ";".join(p["name"] for p in match_hits),
            "n_places_matching": len(match_hits),
            # The matching set's places within its radius, for the SPC-line check.
            "places_near": ";".join(p["name"] for p in match_hits if p.get("reason") == "near"),
            "largest_place": max(match_hits, key=lambda p: p.get("population", 0))["name"]
                             if match_hits else None,
            "largest_place_population": max(
                (p.get("population", 0) for p in match_hits), default=0),
        })
        if i % 500 == 0:
            print(f"  enriched {i}/{len(features)}", end="\r", flush=True)
    print(f"  enriched {len(features)}/{len(features)}")

    table = pd.DataFrame(rows)
    out_path = config.PROCESSED_DIR / f"hazard_geography_{args.tag}.csv"
    print("checking SPC lines against the surveyed tracks …")
    check = spc_line_check(args.tag, table[table.hazard_source == "dat"], enrich)
    table.to_csv(out_path, index=False)

    counts = {"hazards": len(table)}
    for source, part in table.groupby("hazard_source"):
        counts[source] = {
            "hazards": len(part),
            "wfo_known": int(part.wfo.notna().sum()),
            "wfo_source": {k[1]: v for k, v in wfo_sources.items() if k[0] == source},
            "county_fallback": int(part.county_fallback.sum()),
            "several_counties": int((part.n_counties > 1).sum()),
            "hazards_with_places": int((part.n_places > 0).sum()),
            "mean_places_query": round(float(part.n_places.mean()), 1),
            "mean_places_matching": round(float(part.n_places_matching.mean()), 1),
            "hazards_with_a_town_over_20k": int((part.largest_place_population >= 20_000).sum()),
        }
    counts["wfo_agreement_dat_hazards"] = agreement(table[table.hazard_source == "dat"])
    counts["spc_line_check"] = check
    counts["population_join"] = places.population_stats
    counts["settings"] = {
        "place_radius_m": args.place_radius_m,
        "place_match_radius_m": config.PLACE_MATCH_RADIUS_M,
        "place_prominent_radius_m": config.PLACE_PROMINENT_RADIUS_M,
        "place_prominent_min_population": config.PLACE_PROMINENT_MIN_POPULATION,
        "county_min_share": config.COUNTY_MIN_SHARE,
        "county_min_track_m": config.COUNTY_MIN_TRACK_M,
        "county_min_area_m2": config.COUNTY_MIN_AREA_M2,
        "ugc_snapshot_years": sorted(years),
    }
    write_manifest(config.PROCESSED_DIR / f"manifest_geography_{args.tag}.json",
                   "16_enrich_geography", counts=counts, outputs=[out_path])

    for source in ("dat", "spc"):
        c = counts.get(source)
        if c:
            print(f"\n{source.upper()} hazards: {c['hazards']:,}; WFO known for {c['wfo_known']:,} "
                  f"({c['wfo_source']}); county fallback {c['county_fallback']}; "
                  f"place names for {c['hazards_with_places']:,}; "
                  f"a town over 20k for {c['hazards_with_a_town_over_20k']:,}")
    for pair, v in counts["wfo_agreement_dat_hazards"].items():
        print(f"  {pair}: {v}")
    print(f"SPC line vs surveyed track: {check['all']}")
    print(f"wrote {out_path.name}")


if __name__ == "__main__":
    main()

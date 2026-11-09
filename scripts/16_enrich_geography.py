"""Stage 16 — attach counties, states, WFO and place names to each hazard.

Fills the gap that blocks NWS text retrieval: DAT records a WFO on under half of
the hazards, so the office is derived from the NWS county polygons for the
hazard's own year. Every hazard also gets the populated places nearest its track,
which is what news queries and article matching actually key on.

    python scripts/16_enrich_geography.py
    python scripts/16_enrich_geography.py --tag march2025
"""

from __future__ import annotations

import argparse
import json
from collections import Counter

import _bootstrap  # noqa: F401

import pandas as pd

from tornado_dataset import config
from tornado_dataset.dat.geometry import to_equal_area, to_shapely
from tornado_dataset.geo.gazetteer import CountyIndex, PlaceIndex
from tornado_dataset.ids import write_manifest


def hazard_year(hazard: dict) -> int | None:
    day = hazard.get("convective_day")
    return int(str(day)[:4]) if day else None


def _state_name(code: str | None) -> str:
    """Two-letter code to the full state name GNIS uses."""
    from tornado_dataset.text.linking import STATE_NAMES

    return STATE_NAMES.get(str(code or "").upper(), "")


def main() -> None:
    default_tag = f"{config.WINDOW_START.isoformat()}_{config.WINDOW_END.isoformat()}"
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", default=default_tag)
    parser.add_argument("--place-radius-m", type=float, default=config.PLACE_RADIUS_M)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    hazards_path = config.PROCESSED_DIR / f"hazards_{args.tag}.geojson"
    if not hazards_path.exists():
        raise SystemExit(f"missing {hazards_path} — run scripts/12_build_hazards.py first")
    features = json.loads(hazards_path.read_text(encoding="utf-8"))["features"]

    years = {hazard_year(f["properties"]) for f in features} - {None}
    print(f"loading NWS county polygons for {len(years)} snapshot years …")
    counties = CountyIndex(sorted(years), refresh=args.refresh)
    print("loading GNIS populated places …")
    places = PlaceIndex()
    print(f"  {len(places.places)} populated places indexed")

    rows, wfo_sources = [], Counter()
    for i, feature in enumerate(features, 1):
        props = feature["properties"]
        geom = to_shapely(feature.get("geometry"))
        year = hazard_year(props)

        county_hits, place_hits, match_hits = [], [], []
        if geom is not None:
            proj = to_equal_area(geom)
            county_hits = counties.lookup(proj, year)
            # `places` feeds the GDELT query strings and must stay byte-identical
            # to what the running sweep used, or every cache key changes.
            place_hits = places.nearby(proj, args.place_radius_m,
                                       limit=config.MAX_PLACES_PER_HAZARD)
            # `places_matching` is the wide set used to recognise an event in an
            # article: everything nearby, plus prominent cities further out, plus
            # each county's largest town.
            match_hits = places.nearby_for_matching(proj)
            if config.INCLUDE_COUNTY_LARGEST_PLACE:
                seen = {p["name"] for p in match_hits}
                for county in county_hits:
                    largest = places.county_largest(county.get("county") or "",
                                                    _state_name(county.get("state")))
                    if largest and largest["name"] not in seen:
                        match_hits.append({**largest, "distance_m": None,
                                           "reason": "county_largest"})
                        seen.add(largest["name"])

        spatial_wfos = sorted({c["wfo"] for c in county_hits if c.get("wfo")})
        dat_wfos = [w for w in str(props.get("wfo_all") or "").split(";") if w]
        if dat_wfos:
            wfo, source = dat_wfos[0], "dat"
        elif spatial_wfos:
            wfo, source = spatial_wfos[0], "spatial_join"
        else:
            wfo, source = None, "none"
        wfo_sources[source] += 1

        rows.append({
            "hazard_uid": props["hazard_uid"],
            "episode_uid": props.get("episode_uid"),
            "convective_day": props.get("convective_day"),
            "wfo": wfo,
            "wfo_source": source,
            "wfo_dat": ";".join(dat_wfos),
            "wfo_spatial": ";".join(spatial_wfos),
            # Both are kept: agreement between them is a free check on the join.
            "wfo_agrees": bool(dat_wfos and spatial_wfos
                               and set(dat_wfos) & set(spatial_wfos)),
            "counties": ";".join(f"{c['county']}, {c['state']}" for c in county_hits),
            "county_ugcs": ";".join(c["ugc"] for c in county_hits),
            "states": ";".join(sorted({c["state"] for c in county_hits if c.get("state")})),
            "n_counties": len(county_hits),
            "places": ";".join(p["name"] for p in place_hits),
            "place_states": ";".join(sorted({p["state"] for p in place_hits})),
            "nearest_place": place_hits[0]["name"] if place_hits else None,
            "nearest_place_m": place_hits[0]["distance_m"] if place_hits else None,
            "n_places": len(place_hits),
            "places_matching": ";".join(p["name"] for p in match_hits),
            "n_places_matching": len(match_hits),
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
    table.to_csv(out_path, index=False)

    checkable = table[(table.wfo_dat != "") & (table.wfo_spatial != "")]
    counts = {
        "hazards": len(table),
        "wfo_known": int(table.wfo.notna().sum()),
        "wfo_source": dict(wfo_sources),
        "wfo_checkable": len(checkable),
        "wfo_agreement": float(checkable.wfo_agrees.mean()) if len(checkable) else None,
        "hazards_with_places": int((table.n_places > 0).sum()),
        "hazards_with_counties": int((table.n_counties > 0).sum()),
        "mean_places_query": round(float(table.n_places.mean()), 1),
        "mean_places_matching": round(float(table.n_places_matching.mean()), 1),
        "hazards_with_a_town_over_20k": int((table.largest_place_population >= 20_000).sum()),
        "place_radius_m": args.place_radius_m,
        "place_match_radius_m": config.PLACE_MATCH_RADIUS_M,
        "place_prominent_radius_m": config.PLACE_PROMINENT_RADIUS_M,
        "place_prominent_min_population": config.PLACE_PROMINENT_MIN_POPULATION,
        "ugc_snapshot_years": sorted(years),
    }
    write_manifest(config.PROCESSED_DIR / f"manifest_geography_{args.tag}.json",
                   "16_enrich_geography", counts=counts, outputs=[out_path])

    print(f"\nWFO known for {counts['wfo_known']}/{len(table)} hazards "
          f"({counts['wfo_known'] / max(1, len(table)):.1%}); sources: {dict(wfo_sources)}")
    if counts["wfo_agreement"] is not None:
        print(f"  DAT and spatial join agree on {counts['wfo_agreement']:.1%} "
              f"of the {len(checkable)} hazards where both are available")
    print(f"  place names for {counts['hazards_with_places']}/{len(table)} hazards")
    print(f"  query set: {counts['mean_places_query']} names/hazard  |  "
          f"matching set: {counts['mean_places_matching']} names/hazard")
    print(f"  hazards with a town over 20k people nearby: "
          f"{counts['hazards_with_a_town_over_20k']} "
          f"({counts['hazards_with_a_town_over_20k'] / max(1, len(table)):.1%})")
    print(f"wrote {out_path.name}")


if __name__ == "__main__":
    main()

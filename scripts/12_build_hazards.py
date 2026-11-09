"""Stage 12 — assemble hazards (tornado tracks) and episodes (outbreaks).

Turns the linked DAT features into the dataset's unit of analysis: one hazard per
tornado, carrying its track line(s), damage polygon(s), attributes, the DAT survey
``comments`` as oracle text, and flags describing what evidence it rests on.

Lines and polygons rated as not a tornado (``config.NON_TORNADO_RATINGS``:
thunderstorm wind) are left out first. A hazard is then built from each group of
track lines, with the polygons linked to them; polygons no line claims become
hazards of their own. ``geometry_source`` says which: ``line``,
``line+polygon`` or ``polygon``.

    python scripts/12_build_hazards.py
    python scripts/12_build_hazards.py --tag march2025
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import _bootstrap  # noqa: F401

import pandas as pd
from shapely.geometry import mapping

from tornado_dataset import config
from tornado_dataset.dat import hazards as hz
from tornado_dataset.dat import link
from tornado_dataset.ids import uid, write_manifest


def geometry_records(hazard: dict) -> list[dict]:
    """One row per ground-truth geometry, keeping line and polygon roles apart."""
    rows = []
    for role, geoms in (("track_line", hazard["_line_geoms"]),
                        ("damage_polygon", hazard["_polygon_geoms"])):
        for geom in geoms:
            rows.append({
                "geometry_uid": uid("geom", hazard["hazard_uid"], role, geom.wkt[:120]),
                "hazard_uid": hazard["hazard_uid"],
                "geom_role": role,
                "source": "noaa_dat",
                "crs": config.CRS_WGS84,
                "geojson": json.dumps(mapping(geom)),
            })
    return rows


def main() -> None:
    default_tag = f"{config.WINDOW_START.isoformat()}_{config.WINDOW_END.isoformat()}"
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", default=default_tag)
    parser.add_argument("--min-link-confidence", type=float,
                        default=config.HAZARD_MIN_LINK_CONFIDENCE)
    args = parser.parse_args()

    lines_path = config.INTERIM_DIR / f"dat_lines_{args.tag}.geojson"
    polygons_path = config.INTERIM_DIR / f"dat_polygons_{args.tag}.geojson"
    links_path = config.INTERIM_DIR / f"dat_links_{args.tag}.csv"
    for path in (lines_path, polygons_path, links_path):
        if not path.exists():
            raise SystemExit(f"missing {path} — run stages 10 and 11 first")

    lines = link.prepare(json.loads(lines_path.read_text(encoding="utf-8"))["features"])
    polygons = link.prepare(json.loads(polygons_path.read_text(encoding="utf-8"))["features"])
    lines, wind_lines = hz.split_by_rating(lines)
    polygons, wind_polygons = hz.split_by_rating(polygons)
    kept_lines = {line["globalid"] for line in lines}
    kept_polygons = {polygon["objectid"] for polygon in polygons}
    all_links = link.accepted(pd.read_csv(links_path).to_dict("records"))
    links = [r for r in all_links
             if str(r.get("line_globalid") or "").upper() in kept_lines
             and r["polygon_oid"] in kept_polygons]
    print(f"left out as not a tornado: {len(wind_lines)} lines, {len(wind_polygons)} polygons "
          f"({', '.join(sorted(config.NON_TORNADO_RATINGS))})")

    built = hz.build_hazards(lines, polygons, links,
                             min_link_confidence=args.min_link_confidence)
    polygon_hazards, polygon_stats = hz.build_polygon_hazards(polygons, links)
    built += polygon_hazards
    episodes = hz.build_episodes(built)
    print(f"{len(lines)} lines + {len(polygons)} polygons -> "
          f"{len(built)} hazards ({len(polygon_hazards)} from polygons alone) "
          f"in {len(episodes)} episodes")

    gdelt_start = config.GDELT_COVERAGE_START.isoformat()
    features, geometry_rows = [], []
    for hazard in built:
        geometry_rows.extend(geometry_records(hazard))
        geoms = hazard["_line_geoms"] + hazard["_polygon_geoms"]
        geometry = (mapping(geoms[0]) if len(geoms) == 1 else
                    {"type": "GeometryCollection",
                     "geometries": [mapping(g) for g in geoms]} if geoms else None)
        props = {k: v for k, v in hazard.items() if not k.startswith("_")}
        props["gdelt_coverage"] = bool(hazard["convective_day"]
                                       and hazard["convective_day"] >= gdelt_start)
        props["wfo_known"] = bool(hazard["wfo"])
        props["has_polygon"] = hazard["n_polygons"] > 0
        features.append({"type": "Feature", "geometry": geometry, "properties": props})

    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    hazards_path = config.PROCESSED_DIR / f"hazards_{args.tag}.geojson"
    hazards_table = config.PROCESSED_DIR / f"hazards_{args.tag}.csv"
    episodes_path = config.PROCESSED_DIR / f"episodes_{args.tag}.csv"
    geometries_path = config.PROCESSED_DIR / f"geometries_{args.tag}.csv"

    hazards_path.write_text(json.dumps({"type": "FeatureCollection", "features": features}),
                            encoding="utf-8")
    table = pd.DataFrame([f["properties"] for f in features])
    table.to_csv(hazards_table, index=False)
    pd.DataFrame(episodes).to_csv(episodes_path, index=False)
    pd.DataFrame(geometry_rows).to_csv(geometries_path, index=False)

    # Polygons linked in stage 11 but below the hazard confidence floor are left
    # unattached on purpose; the gap between these two numbers is the price of
    # that floor and belongs in the record.
    counts = {
        "hazards": len(built),
        "episodes": len(episodes),
        "geometries": len(geometry_rows),
        "polygons_linked_stage2": len({r["polygon_oid"] for r in all_links}),
        "polygons_linked_to_tornado_lines": len({r["polygon_oid"] for r in links}),
        "polygons_attached_to_hazards": int(table.n_polygons[table.n_lines > 0].sum()),
        "lines_excluded_not_tornado": len(wind_lines),
        "polygons_excluded_not_tornado": len(wind_polygons),
        "non_tornado_ratings": sorted(config.NON_TORNADO_RATINGS),
        "polygons_in_polygon_hazards": int(table.n_polygons[table.n_lines == 0].sum()),
        **polygon_stats,
        "hazards_by_geometry_source": table.geometry_source.value_counts().to_dict(),
        "hazards_with_polygon": int(table.has_polygon.sum()),
        "hazards_with_oracle_text": int(table.has_oracle_text.sum()),
        "hazards_with_wfo": int(table.wfo_known.sum()),
        "hazards_in_gdelt_window": int(table.gdelt_coverage.sum()),
        "multi_line_hazards": int((table.n_lines > 1).sum()),
        "merge_evidence": table.merge_evidence.replace("", "single_line_hazard")
                               .value_counts().to_dict(),
        "min_link_confidence": args.min_link_confidence,
    }
    write_manifest(config.PROCESSED_DIR / f"manifest_hazards_{args.tag}.json",
                   "12_build_hazards", counts=counts,
                   outputs=[hazards_path, hazards_table, episodes_path, geometries_path])

    print(f"  with a damage polygon: {counts['hazards_with_polygon']} "
          f"({counts['hazards_with_polygon'] / max(1, len(built)):.1%})")
    print(f"  with oracle survey text: {counts['hazards_with_oracle_text']} "
          f"({counts['hazards_with_oracle_text'] / max(1, len(built)):.1%})")
    print(f"  inside the GDELT window: {counts['hazards_in_gdelt_window']} "
          f"({counts['hazards_in_gdelt_window'] / max(1, len(built)):.1%})")
    print(f"  assembled from >1 line: {counts['multi_line_hazards']}")
    print(f"wrote {hazards_path.name}, {hazards_table.name}, "
          f"{episodes_path.name}, {geometries_path.name}")


if __name__ == "__main__":
    main()

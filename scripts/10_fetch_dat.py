"""Stage 10 — download NOAA DAT damage geometry for the configured window.

Writes GeoJSON FeatureCollections to ``data/interim/`` and keeps every raw API
response under ``data/raw/dat/`` so later stages (and reviewers) can rebuild the
tables without touching the network. Re-running is idempotent: cached chunks are
reused unless ``--refresh`` is given.

    python scripts/10_fetch_dat.py
    python scripts/10_fetch_dat.py --start 2025-03-14 --end 2025-03-16 --tag march2025
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import _bootstrap  # noqa: F401  (path setup)

from tornado_dataset import config
from tornado_dataset.dat import fetch
from tornado_dataset.dat.geometry import esri_to_geojson_geometry
from tornado_dataset.ids import write_manifest


def to_feature_collection(features: list[dict]) -> dict:
    """Esri features -> RFC 7946 FeatureCollection (properties kept verbatim)."""
    out = []
    for feature in features:
        out.append({
            "type": "Feature",
            "geometry": esri_to_geojson_geometry(feature.get("geometry")),
            "properties": feature.get("attributes", {}),
        })
    return {"type": "FeatureCollection", "features": out}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--start", type=dt.date.fromisoformat, default=config.WINDOW_START)
    parser.add_argument("--end", type=dt.date.fromisoformat, default=config.WINDOW_END)
    parser.add_argument("--tag", default=None,
                        help="suffix for output files (default: the date window)")
    parser.add_argument("--include-points", action="store_true",
                        help="also fetch the damage-point layer (~218k features)")
    parser.add_argument("--refresh", action="store_true", help="ignore the response cache")
    args = parser.parse_args()

    tag = args.tag or f"{args.start.isoformat()}_{args.end.isoformat()}"
    where = fetch.date_where(args.start, args.end)
    cache_dir = config.RAW_DIR / "dat" / tag
    config.INTERIM_DIR.mkdir(parents=True, exist_ok=True)

    layers = ["lines", "polygons"] + (["points"] if args.include_points else [])
    counts: dict[str, object] = {"where": where}
    outputs: list[Path] = []

    for name in layers:
        layer = config.DAT_LAYERS[name]
        expected = fetch.count_features(layer, where)
        print(f"\n{name} (layer {layer}): server reports {expected} features")

        features = fetch.fetch_layer(layer, where, cache_dir=cache_dir, refresh=args.refresh)
        collection = to_feature_collection(features)
        missing_geometry = sum(1 for f in collection["features"] if f["geometry"] is None)
        reduced = sum(1 for f in features if f["attributes"].get("_fields_reduced"))

        path = config.INTERIM_DIR / f"dat_{name}_{tag}.geojson"
        path.write_text(json.dumps(collection), encoding="utf-8")
        outputs.append(path)

        counts[name] = {"expected": expected, "fetched": len(features),
                        "complete": expected == len(features),
                        "missing_geometry": missing_geometry,
                        "fields_reduced": reduced}
        status = "complete" if expected == len(features) else "INCOMPLETE"
        print(f"  fetched {len(features)}/{expected} ({status}); "
              f"{missing_geometry} without usable geometry, {reduced} with reduced fields")
        print(f"  wrote {path}")

    write_manifest(config.INTERIM_DIR / f"manifest_fetch_{tag}.json", "10_fetch_dat",
                   counts=counts, outputs=outputs,
                   extra={"window": {"start": args.start.isoformat(),
                                     "end": args.end.isoformat()},
                          "raw_cache": str(cache_dir.relative_to(config.REPO_ROOT))})


if __name__ == "__main__":
    main()

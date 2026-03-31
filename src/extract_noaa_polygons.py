from __future__ import annotations

import csv
import json
import time
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import requests
from tqdm import tqdm

# ============================================================
# CONFIGURATION
# ============================================================

CONFIG: Dict[str, object] = {
    "geometry_type": "both",          # "polygons" | "lines" | "both"
    "start_date": date(1976, 3, 1),
    "end_date": date(2026, 3, 1),
    "non_empty_field": "comments",    # None to disable
    "extent": None,                   # (xmin, ymin, xmax, ymax) in EPSG:3857 or None
    "output_dir": "noaa_dat_exports",
    "output_format": "geojson",       # "json" | "csv" | "geojson"
    "chunk_size": 200,
    "sleep_seconds": 0.2,
}

# ============================================================
# INTERNAL CONSTANTS
# ============================================================

BASE_URL: str = (
    "https://services.dat.noaa.gov/arcgis/rest/services/"
    "nws_damageassessmenttoolkit/DamageViewer/FeatureServer"
)

LAYERS: Dict[str, int] = {
    "lines": 1,
    "polygons": 2,
}

SESSION: requests.Session = requests.Session()

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def build_where_clause() -> str:
    """
    Build an ArcGIS SQL WHERE clause based on CONFIG settings.

    Returns
    -------
    str
        SQL WHERE clause string for server-side filtering.
    """
    clauses: List[str] = [
        f"stormdate >= DATE '{CONFIG['start_date']}'",
        f"stormdate < DATE '{CONFIG['end_date']}'",
    ]

    field: Optional[str] = CONFIG.get("non_empty_field")  # type: ignore
    if field:
        clauses.append(f"{field} IS NOT NULL")
        clauses.append(f"{field} <> ''")

    return " AND ".join(clauses)


def selected_layers() -> Iterable[Tuple[str, int]]:
    """
    Determine which FeatureServer layers to query.

    Returns
    -------
    Iterable[Tuple[str, int]]
        Iterable of (layer_name, layer_id) tuples.
    """
    geometry_type: str = CONFIG["geometry_type"]  # type: ignore

    if geometry_type == "both":
        return LAYERS.items()

    return [(geometry_type, LAYERS[geometry_type])]


def get_object_ids(layer_id: int, where: str) -> List[int]:
    """
    Query the FeatureServer for all object IDs matching a WHERE clause.

    Parameters
    ----------
    layer_id : int
        FeatureServer layer ID.
    where : str
        SQL WHERE clause.

    Returns
    -------
    List[int]
        List of object IDs.
    """
    params: Dict[str, object] = {
        "where": where,
        "returnIdsOnly": "true",
        "f": "json",
    }

    extent: Optional[Tuple[float, float, float, float]] = CONFIG.get("extent")  # type: ignore
    if extent:
        xmin, ymin, xmax, ymax = extent
        params.update({
            "geometryType": "esriGeometryEnvelope",
            "geometry": f"{xmin},{ymin},{xmax},{ymax}",
            "inSR": 3857,
            "spatialRel": "esriSpatialRelIntersects",
        })

    url: str = f"{BASE_URL}/{layer_id}/query"
    response: requests.Response = SESSION.get(url, params=params, timeout=60)
    response.raise_for_status()
    data: Dict[str, object] = response.json()

    if "error" in data:
        raise RuntimeError(data["error"])

    return data.get("objectIds", [])  # type: ignore


def fetch_features(layer_id: int, object_ids: List[int]) -> List[Dict[str, object]]:
    """
    Fetch features from a FeatureServer layer in paginated chunks.

    When the output format is GeoJSON the server is asked to return
    coordinates in WGS 84 (EPSG:4326) as required by RFC 7946.

    Parameters
    ----------
    layer_id : int
        FeatureServer layer ID.
    object_ids : List[int]
        Object IDs to fetch.

    Returns
    -------
    List[Dict[str, object]]
        List of Esri JSON feature objects.
    """
    features: List[Dict[str, object]] = []
    url: str = f"{BASE_URL}/{layer_id}/query"
    chunk_size: int = CONFIG["chunk_size"]  # type: ignore

    for i in tqdm(range(0, len(object_ids), chunk_size)):
        chunk: List[int] = object_ids[i:i + chunk_size]

        params: Dict[str, object] = {
            "objectIds": ",".join(map(str, chunk)),
            "outFields": "*",
            "returnGeometry": "true",
            "f": "json",
        }

        # GeoJSON requires WGS 84 coordinates
        if CONFIG.get("output_format") == "geojson":
            params["outSR"] = 4326

        response: requests.Response = SESSION.get(url, params=params, timeout=60)
        response.raise_for_status()
        data: Dict[str, object] = response.json()

        features.extend(data.get("features", []))  # type: ignore
        time.sleep(CONFIG["sleep_seconds"])  # type: ignore

    return features


def esri_feature_to_geojson(
    feature: Dict[str, object],
    layer_name: str,
) -> Dict[str, object]:
    """
    Convert a single Esri JSON feature to a GeoJSON Feature.

    Parameters
    ----------
    feature : dict
        Raw Esri JSON feature with ``attributes`` and ``geometry`` keys.
    layer_name : str
        ``"polygons"`` or ``"lines"`` — used to select the correct
        geometry mapping.

    Returns
    -------
    dict
        A GeoJSON Feature object conforming to RFC 7946.
    """
    properties: Dict[str, object] = dict(feature.get("attributes", {}))
    esri_geom: Optional[Dict] = feature.get("geometry")

    geojson_geom: Optional[Dict[str, object]] = None

    if esri_geom is not None:
        if layer_name == "polygons":
            rings = esri_geom.get("rings")
            if rings:
                if len(rings) == 1:
                    geojson_geom = {
                        "type": "Polygon",
                        "coordinates": rings,
                    }
                else:
                    # Multiple rings — wrap each as its own polygon inside
                    # a MultiPolygon.  A full implementation would inspect
                    # winding order to distinguish shells from holes.
                    geojson_geom = {
                        "type": "MultiPolygon",
                        "coordinates": [[ring] for ring in rings],
                    }

        elif layer_name == "lines":
            paths = esri_geom.get("paths")
            if paths:
                if len(paths) == 1:
                    geojson_geom = {
                        "type": "LineString",
                        "coordinates": paths[0],
                    }
                else:
                    geojson_geom = {
                        "type": "MultiLineString",
                        "coordinates": paths,
                    }

    return {
        "type": "Feature",
        "geometry": geojson_geom,
        "properties": properties,
    }


def output_filename(layer_name: str) -> str:
    """
    Construct a descriptive output filename based on CONFIG.

    Parameters
    ----------
    layer_name : str
        Logical layer name ("polygons" or "lines").

    Returns
    -------
    str
        Output filename (extension reflects output_format).
    """
    parts: List[str] = [
        layer_name,
        CONFIG["start_date"].isoformat(),  # type: ignore
        CONFIG["end_date"].isoformat(),    # type: ignore
    ]

    if CONFIG.get("non_empty_field"):
        parts.append(f"nonempty-{CONFIG['non_empty_field']}")

    if CONFIG.get("extent"):
        parts.append("bbox")

    ext_map: Dict[str, str] = {
        "csv": ".csv",
        "json": ".json",
        "geojson": ".geojson",
    }
    ext: str = ext_map.get(CONFIG.get("output_format", "json"), ".json")  # type: ignore

    return "_".join(parts) + ext


def save_features(
    outfile: Path,
    layer_name: str,
    layer_id: int,
    features: List[Dict[str, object]],
) -> None:
    """
    Persist features to disk in the format specified by CONFIG['output_format'].

    * **csv** — attribute columns plus a ``geometry`` column containing the
      Esri JSON geometry serialised as a JSON string.
    * **json** — the original Esri JSON features wrapped in a simple envelope
      that records the layer name, id, date range and feature count.
    * **geojson** — an RFC 7946 FeatureCollection with geometry converted
      from Esri JSON to GeoJSON.

    Parameters
    ----------
    outfile : Path
        Destination file path.
    layer_name : str
        Logical layer name used in the JSON / GeoJSON envelope.
    layer_id : int
        FeatureServer layer ID used in the JSON envelope.
    features : List[Dict[str, object]]
        Raw Esri JSON feature objects.
    """
    fmt: str = CONFIG.get("output_format", "json")  # type: ignore

    if fmt == "csv":
        rows: List[Dict[str, object]] = []
        for feat in features:
            row: Dict[str, object] = dict(feat.get("attributes", {}))
            geom = feat.get("geometry")
            row["geometry"] = json.dumps(geom) if geom is not None else ""
            rows.append(row)

        if not rows:
            outfile.write_text("", encoding="utf-8")
            return

        fieldnames: List[str] = list(rows[0].keys())
        for row in rows[1:]:
            for k in row:
                if k not in fieldnames:
                    fieldnames.append(k)

        with outfile.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

    elif fmt == "geojson":
        geojson_features: List[Dict[str, object]] = [
            esri_feature_to_geojson(f, layer_name) for f in features
        ]

        feature_collection: Dict[str, object] = {
            "type": "FeatureCollection",
            "features": geojson_features,
        }

        with outfile.open("w", encoding="utf-8") as fh:
            json.dump(feature_collection, fh, indent=2)

    else:  # json (default / original behaviour)
        payload: Dict[str, object] = {
            "layer": layer_name,
            "layer_id": layer_id,
            "start_date": CONFIG["start_date"].isoformat(),  # type: ignore
            "end_date": CONFIG["end_date"].isoformat(),      # type: ignore
            "feature_count": len(features),
            "features": features,
        }
        with outfile.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)


# ============================================================
# MAIN
# ============================================================


def main() -> None:
    """
    Main entry point for the NOAA DAT extraction workflow.
    """
    fmt: str = CONFIG.get("output_format", "json")  # type: ignore
    if fmt not in {"json", "csv", "geojson"}:
        raise ValueError(
            f"output_format must be 'json', 'csv', or 'geojson', got '{fmt}'"
        )

    output_dir: Path = Path(CONFIG["output_dir"])  # type: ignore
    output_dir.mkdir(parents=True, exist_ok=True)

    where: str = build_where_clause()

    for layer_name, layer_id in selected_layers():
        print(f"\nExtracting {layer_name.upper()} (layer {layer_id})")

        object_ids: List[int] = get_object_ids(layer_id, where)
        print(f"  Found {len(object_ids)} features")

        if not object_ids:
            continue

        features: List[Dict[str, object]] = fetch_features(layer_id, object_ids)

        outfile: Path = output_dir / output_filename(layer_name)
        save_features(outfile, layer_name, layer_id, features)

        print(f"  Saved {len(features)} features → {outfile}  [{fmt.upper()}]")


if __name__ == "__main__":
    main()
from __future__ import annotations

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
    "geometry_type": "both",  # "polygons" | "lines" | "both"
    "start_date": date(2025, 1, 1),
    "end_date": date(2026, 1, 1),
    "non_empty_field": "comments",  # None to disable
    "extent": None,  # (xmin, ymin, xmax, ymax) in EPSG:3857 or None
    "output_dir": "noaa_dat_exports",
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

        response: requests.Response = SESSION.get(url, params=params, timeout=60)
        response.raise_for_status()
        data: Dict[str, object] = response.json()

        features.extend(data.get("features", []))  # type: ignore
        time.sleep(CONFIG["sleep_seconds"])  # type: ignore

    return features


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
        Output filename.
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

    return "_".join(parts) + ".json"


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    """
    Main entry point for the NOAA DAT extraction workflow.
    """
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

        payload: Dict[str, object] = {
            "layer": layer_name,
            "layer_id": layer_id,
            "start_date": CONFIG["start_date"].isoformat(),  # type: ignore
            "end_date": CONFIG["end_date"].isoformat(),    # type: ignore
            "feature_count": len(features),
            "features": features,
        }

        outfile: Path = output_dir / output_filename(layer_name)
        with outfile.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        print(f"Saved {outfile}")


if __name__ == "__main__":
    main()
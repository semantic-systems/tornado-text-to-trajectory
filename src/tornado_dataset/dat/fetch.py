"""Fetch NOAA Damage Assessment Toolkit (DAT) features at national scale.

The DamageViewer FeatureServer exposes 0 = damage points, 1 = damage lines
(tornado tracks), 2 = damage polygons. Two properties of this SDE-backed service
shape the code:

* ``returnIdsOnly`` is not subject to ``maxRecordCount`` (2000), so the object
  ids for a whole decade come back in one request; attributes and geometry are
  then fetched in chunks of those ids.
* A chunk occasionally fails with HTTP 400 ("Unable to complete operation") for
  certain field/geometry combinations. Rather than dropping those features, the
  chunk is retried per objectId with a reduced field set, and the reduction is
  recorded on the feature so the loss is visible in the data.

No attribute filter is applied. Restricting to features with survey ``comments``
— as the earlier extract did — would drop 68% of damage polygons and bias the
geometry sample; the comment-bearing subset is derived later as a flagged view.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any, Iterable

from .. import config
from ..http import get_json


def date_where(start: dt.date, end: dt.date) -> str:
    """ArcGIS WHERE clause selecting one closed stormdate window."""
    return (f"stormdate >= DATE '{start.isoformat()}' "
            f"AND stormdate <= DATE '{end.isoformat()}'")


def count_features(layer: int, where: str) -> int:
    """Server-side count, used to verify a download is complete."""
    payload = get_json(f"{config.DAT_BASE_URL}/{layer}/query",
                       {"where": where, "returnCountOnly": "true", "f": "json"})
    return int(payload.get("count", 0))


def object_ids(layer: int, where: str, *, cache_dir: Path,
               refresh: bool = False) -> list[int]:
    """All objectIds matching ``where`` (one request, no record cap)."""
    payload = get_json(
        f"{config.DAT_BASE_URL}/{layer}/query",
        {"where": where, "returnIdsOnly": "true", "f": "json"},
        cache_path=cache_dir / f"layer{layer}_objectids.json", refresh=refresh)
    return list(payload.get("objectIds") or [])


def _epoch_ms_to_iso(value: Any) -> Any:
    """Convert an Esri epoch-millisecond timestamp to ISO 8601 UTC."""
    if value in (None, ""):
        return None
    try:
        return dt.datetime.fromtimestamp(value / 1000, dt.timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return value


def normalise_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
    """Copy of ``attributes`` with DAT date fields as ISO strings."""
    return {key: (_epoch_ms_to_iso(value) if key in config.DAT_DATE_FIELDS else value)
            for key, value in attributes.items()}


def _query_ids(layer: int, ids: Iterable[int], fields: str, *,
               cache_path: Path | None, refresh: bool) -> dict[str, Any]:
    return get_json(f"{config.DAT_BASE_URL}/{layer}/query", {
        "objectIds": ",".join(map(str, ids)),
        "outFields": fields,
        "returnGeometry": "true",
        "outSR": 4326,
        "f": "json",
    }, cache_path=cache_path, refresh=refresh, min_interval=config.DAT_SLEEP)


def fetch_layer(layer: int, where: str, *, cache_dir: Path, refresh: bool = False,
                chunk_size: int = config.DAT_CHUNK_SIZE,
                progress: bool = True) -> list[dict[str, Any]]:
    """Fetch every feature of ``layer`` matching ``where``, with geometry.

    Returns raw Esri features (``attributes`` + ``geometry``) with date fields
    normalised to ISO 8601 and a ``_fields_reduced`` marker on any feature that
    had to fall back to the safe field set.
    """
    ids = object_ids(layer, where, cache_dir=cache_dir, refresh=refresh)
    features: list[dict[str, Any]] = []

    for start in range(0, len(ids), chunk_size):
        chunk = ids[start:start + chunk_size]
        cache_path = cache_dir / f"layer{layer}_chunk{start:06d}.json"
        try:
            payload = _query_ids(layer, chunk, "*", cache_path=cache_path, refresh=refresh)
            got = payload.get("features")
            if got is None:
                raise RuntimeError("response carried no features array")
        except Exception:
            # Fall back to one request per objectId with the reduced field set,
            # so a single poisoned record cannot cost us the whole chunk.
            got = []
            for oid in chunk:
                try:
                    single = _query_ids(
                        layer, [oid], config.DAT_SAFE_FIELDS[layer],
                        cache_path=cache_dir / f"layer{layer}_oid{oid}.json",
                        refresh=refresh)
                except Exception:
                    continue
                for feature in single.get("features", []) or []:
                    feature.setdefault("attributes", {})["_fields_reduced"] = True
                    got.append(feature)

        for feature in got:
            feature["attributes"] = normalise_attributes(feature.get("attributes", {}))
        features.extend(got)

        if progress:
            print(f"  layer {layer}: {min(start + chunk_size, len(ids))}/{len(ids)}",
                  end="\r", flush=True)

    if progress:
        print()
    return features

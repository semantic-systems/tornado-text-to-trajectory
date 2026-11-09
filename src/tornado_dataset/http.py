"""HTTP access with retries, rate limiting and an on-disk response cache.

Every remote read in this pipeline goes through :func:`get_json`, so that

* a rerun works from cache and does not hammer a public service,
* the verbatim response is kept next to a sidecar recording *when* and *from
  which URL* it was retrieved — the provenance the dataset has to publish, and
* a transient 5xx never silently truncates a national-scale download.
"""

from __future__ import annotations

import hashlib
import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests

from . import config

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": "tornado-text-to-trajectory/0.1 (academic research; contact via repository)",
})

# Per-host timestamp of the last request, for the minimum-interval throttle.
_last_request: dict[str, float] = {}


def utcnow_iso() -> str:
    """Current UTC time as an ISO 8601 string (used for retrieved_at)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def cache_key(url: str, params: dict[str, Any]) -> str:
    """Stable hash of a request, independent of dict ordering."""
    canonical = url + "?" + urlencode(sorted((k, str(v)) for k, v in params.items()))
    return hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:16]


def _throttle(url: str, min_interval: float) -> None:
    if min_interval <= 0:
        return
    host = url.split("/")[2] if "://" in url else url
    elapsed = time.monotonic() - _last_request.get(host, 0.0)
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    _last_request[host] = time.monotonic()


def get_json(url: str, params: dict[str, Any], *, cache_path: Path | None = None,
             refresh: bool = False, min_interval: float = 0.0,
             retries: int = config.HTTP_RETRIES,
             timeout: int = config.HTTP_TIMEOUT) -> dict[str, Any]:
    """GET ``url`` and return parsed JSON, caching the raw body when asked.

    A cached response is returned untouched unless ``refresh`` is set. Failures
    are retried with linear backoff; the last error is raised so a caller can
    decide whether to fall back (see the DAT per-objectId fallback).
    """
    if cache_path is not None and cache_path.exists() and not refresh:
        return json.loads(cache_path.read_text(encoding="utf-8"))

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        _throttle(url, min_interval)
        try:
            response = _SESSION.get(url, params=params, timeout=timeout)
            # A rate limiter needs its own, much longer backoff. Retrying a 429
            # a couple of seconds later just spends another request on the same
            # refusal — which is how a sweep can look like it is working while
            # a third of its queries quietly return nothing.
            if response.status_code == 429 or (
                    response.status_code == 200
                    and response.text.lstrip().startswith("Please limit requests")):
                last_error = RuntimeError(f"rate limited (HTTP {response.status_code})")
                time.sleep(config.HTTP_RATE_LIMIT_BACKOFF * attempt
                           + random.uniform(0, 5))
                continue
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:  # network error, non-2xx, or non-JSON body
            last_error = exc
            time.sleep(config.HTTP_BACKOFF * attempt)
            continue

        # ArcGIS reports application-level failures inside a 200 response.
        if isinstance(payload, dict) and "error" in payload:
            last_error = RuntimeError(f"service error: {payload['error']}")
            time.sleep(config.HTTP_BACKOFF * attempt)
            continue

        if cache_path is not None:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(payload), encoding="utf-8")
            cache_path.with_suffix(".meta.json").write_text(
                json.dumps({"url": response.url, "retrieved_at": utcnow_iso(),
                            "status": response.status_code}, indent=2),
                encoding="utf-8")
        return payload

    raise RuntimeError(f"GET failed after {retries} attempts: {url}\n  {last_error}")


def get_text(url: str, params: dict[str, Any], *, cache_path: Path | None = None,
             refresh: bool = False, min_interval: float = 0.0,
             retries: int = config.HTTP_RETRIES,
             timeout: int = config.HTTP_TIMEOUT) -> str:
    """:func:`get_json` for CSV and plain-text services; same cache and sidecar."""
    if cache_path is not None and cache_path.exists() and not refresh:
        return cache_path.read_text(encoding="utf-8")

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        _throttle(url, min_interval)
        try:
            response = _SESSION.get(url, params=params, timeout=timeout)
            if response.status_code == 429:
                last_error = RuntimeError("rate limited (HTTP 429)")
                time.sleep(config.HTTP_RATE_LIMIT_BACKOFF * attempt
                           + random.uniform(0, 5))
                continue
            response.raise_for_status()
            body = response.text
        except Exception as exc:  # network error or non-2xx
            last_error = exc
            time.sleep(config.HTTP_BACKOFF * attempt)
            continue

        if cache_path is not None:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(body, encoding="utf-8")
            cache_path.with_name(cache_path.name + ".meta.json").write_text(
                json.dumps({"url": response.url, "retrieved_at": utcnow_iso(),
                            "status": response.status_code}, indent=2),
                encoding="utf-8")
        return body

    raise RuntimeError(f"GET failed after {retries} attempts: {url}\n  {last_error}")

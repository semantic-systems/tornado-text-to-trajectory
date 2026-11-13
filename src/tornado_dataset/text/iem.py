"""NWS text from the Iowa Environmental Mesonet: LSRs and storm-survey PNS.

Two same-org streams, at opposite ends of the timeline the dataset studies:

* **Local Storm Reports** — issued during and just after the event by spotters
  and the WFO. Timely, public domain, and thin: the first report of a killer
  tornado is often a place name and "possible tornado". ``text_role`` =
  ``official_timely``.
* **Public Information Statement storm surveys** — the write-up of the same field
  survey that produced the DAT geometry, issued days later with EF rating, path
  length and fatalities. This is the **oracle text**: near-circular with the
  ground truth by construction, which is precisely why it establishes the
  ceiling for the text->geometry experiment.

Both are US-government works, so their full text may be stored and redistributed.

Retrieval is shaped by what scales. LSRs come as one bulk CSV per year (16
requests for the whole window) and are matched to hazards locally. PNS products
are listed nationally per date — one request covers every office — and only the
products belonging to a hazard's WFO are then downloaded, which is why Stage 16's
WFO backfill runs first.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import re
import time
from pathlib import Path
from typing import Any, Callable, Iterable

from .. import config
from ..http import get_json, session_get, utcnow_iso

LSR_REQUEST_URL = f"{config.IEM_BASE}/cgi-bin/request/gis/lsr.py"
AFOS_LIST_URL = f"{config.IEM_BASE}/api/1/nws/afos/list.json"
NWSTEXT_URL = f"{config.IEM_BASE}/api/1/nwstext"


# ── Local Storm Reports ──────────────────────────────────────────────────────
def fetch_lsr_year(year: int, *, cache_dir: Path, refresh: bool = False, offline: bool = False,
                   types: Iterable[str] = config.LSR_TORNADO_TYPES) -> list[dict[str, Any]] | None:
    """All tornado-family LSRs for one calendar year (one bulk request).

    ``offline``: ``None`` when the year is not cached, instead of fetching it.
    """
    cache_path = cache_dir / f"lsr_{year}.csv"
    if cache_path.exists() and not refresh:
        text = cache_path.read_text(encoding="utf-8")
    elif offline:
        return None
    else:
        response = session_get(LSR_REQUEST_URL, params={
            "sts": f"{year}-01-01T00:00Z", "ets": f"{year + 1}-01-01T00:00Z",
            "fmt": "csv", "type": list(types)}, timeout=900,
            min_interval=config.IEM_MIN_REQUEST_INTERVAL)
        response.raise_for_status()
        text = response.text
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(text, encoding="utf-8")
        cache_path.with_suffix(".meta.json").write_text(
            f'{{"url": "{response.url}", "retrieved_at": "{utcnow_iso()}"}}',
            encoding="utf-8")

    rows = []
    for row in csv.DictReader(io.StringIO(text)):
        try:
            lat, lon = float(row["LAT"]), float(row["LON"])
        except (TypeError, ValueError, KeyError):
            continue
        valid = _parse_lsr_time(row.get("VALID"))
        rows.append({
            "valid_utc": valid.isoformat() if valid else None,
            "lat": lat, "lon": lon,
            "wfo": row.get("WFO"), "typetext": row.get("TYPETEXT"),
            "city": row.get("CITY"), "county": row.get("COUNTY"),
            "state": row.get("STATE"), "source": row.get("SOURCE"),
            "remark": (row.get("REMARK") or "").strip(),
            "magnitude": row.get("MAG"),
        })
    return rows


def lsr_time_gap_min(valid: dt.datetime, begin: dt.datetime,
                     end: dt.datetime | None) -> float:
    """Minutes from the hazard's begin-end to the report; 0 inside it.

    A hazard without an end is the moment it began.
    """
    end = end if end and end >= begin else begin
    if valid < begin:
        return (begin - valid).total_seconds() / 60
    if valid > end:
        return (valid - end).total_seconds() / 60
    return 0.0


LSR_ASSIGNMENTS = ("sole", "clear", "time", "touching", "unclear")


def assign_lsr(candidates: list[dict[str, Any]],
               apart: Callable[[str, str], float]) -> tuple[str, str]:
    """The hazard one LSR is about, and on what basis.

    ``candidates``: the hazards within reach of the report, each a dict with
    ``uid``, ``distance_m`` and ``gap_min`` (:func:`lsr_time_gap_min`).
    ``apart(uid_a, uid_b)``: the distance between two hazards' tracks in metres.

    The best match is the nearest track; tracks within ``LSR_NEAR_FACTOR`` times
    its distance (at least ``LSR_NEAR_FLOOR_M``) compete with it, and of those
    the one closest in time wins. The basis says how sure that is:

    * ``sole`` — the only candidate;
    * ``clear`` — every other track is farther than that;
    * ``time`` — of the competing tracks, the report falls within one's begin-end;
    * ``touching`` — the competing tracks lie within ``LSR_TOUCH_M`` of the
      nearest: pieces of one tornado, or tracks that cross;
    * ``unclear`` — none of these: the pick is the closest in time, but a guess.
    """
    ranked = sorted(candidates, key=lambda c: (c["distance_m"], c["uid"]))
    nearest = ranked[0]
    reach = max(config.LSR_NEAR_FACTOR * nearest["distance_m"], config.LSR_NEAR_FLOOR_M)
    close = [c for c in ranked if c["distance_m"] <= reach]
    best = min(close, key=lambda c: (c["gap_min"], c["distance_m"], c["uid"]))["uid"]
    if len(ranked) == 1:
        return best, "sole"
    if len(close) == 1:
        return best, "clear"
    if sum(c["gap_min"] == 0 for c in close) == 1:
        return best, "time"
    if all(apart(nearest["uid"], c["uid"]) <= config.LSR_TOUCH_M for c in close[1:]):
        return best, "touching"
    return best, "unclear"


def _parse_lsr_time(value: Any) -> dt.datetime | None:
    """LSR VALID is 'YYYYMMDDHHMM' in UTC."""
    text = str(value or "").strip()
    if len(text) != 12 or not text.isdigit():
        return None
    return dt.datetime.strptime(text, "%Y%m%d%H%M").replace(tzinfo=dt.timezone.utc)


# ── Public Information Statements (storm surveys) ────────────────────────────
def list_pns_products(date: dt.date, *, cache_dir: Path, refresh: bool = False,
                      offline: bool = False) -> list[dict[str, Any]] | None:
    """Every PNS product issued nationally on ``date`` (one request).

    ``offline``: ``None`` when the list is not cached, instead of fetching it.
    """
    cache_path = cache_dir / f"pns_list_{date.isoformat()}.json"
    if offline and (refresh or not cache_path.exists()):
        return None
    payload = get_json(AFOS_LIST_URL, {"pil": "PNS", "date": date.isoformat()},
                       cache_path=cache_path,
                       refresh=refresh, min_interval=config.IEM_MIN_REQUEST_INTERVAL)
    return payload.get("data", []) or []


def fetch_product_text(product_id: str, *, cache_dir: Path, refresh: bool = False,
                       retries: int = 4, offline: bool = False) -> str | None:
    """Raw text of one NWS product, cached by product id.

    Retries on transient failures and gives up quietly rather than raising: this
    is called tens of thousands of times in one sweep, and a single dropped
    connection must not end the run. An empty result is cached as empty, which
    the caller counts. ``offline``: ``None`` when not cached, instead of fetching.
    Requests are spaced like the list requests (``config.IEM_MIN_REQUEST_INTERVAL``).
    """
    cache_path = cache_dir / f"{product_id}.txt"
    if cache_path.exists() and not refresh:
        return cache_path.read_text(encoding="utf-8", errors="replace")
    if offline:
        return None

    text = ""
    for attempt in range(1, retries + 1):
        try:
            response = session_get(f"{NWSTEXT_URL}/{product_id}", timeout=120,
                                   min_interval=config.IEM_MIN_REQUEST_INTERVAL)
            if response.status_code == 200:
                text = response.text
            break
        except Exception:
            if attempt == retries:
                return ""          # not cached, so a later run retries it
            time.sleep(1.5 * attempt)

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(text, encoding="utf-8")
    return text


def stated_point(lat: float | None, lon: float | None) -> tuple[float, float] | None:
    """A coordinate a survey section states, as a point in the US, or ``None``.

    A western longitude written without its minus sign ("42.79 / 92.78") is
    restored; a coordinate still outside the US after that is a typo and unusable.
    """
    if lat is None or lon is None:
        return None
    if 60 <= lon <= 180:
        lon = -lon
    return (lat, lon) if 15 <= lat <= 72 and -180 <= lon <= -60 else None


# A storm-survey PNS announces itself in the product header. PNS is also used for
# spotter-training notices, service changes and staffing, so classification is by
# content rather than by product type.
SURVEY_HEADER_RE = re.compile(
    r"(NWS\s+DAMAGE\s+SURVEY|PUBLIC\s+INFORMATION\s+STATEMENT.{0,400}?DAMAGE\s+SURVEY"
    r"|DAMAGE\s+SURVEY\s+FOR|STORM\s+SURVEY|TORNADO\s+SUMMARY)", re.IGNORECASE | re.DOTALL)
EF_RATING_RE = re.compile(r"\bEF[\s-]?([0-5U])\b", re.IGNORECASE)
TORNADO_RE = re.compile(r"\bTORNADO(ES)?\b", re.IGNORECASE)


def classify_pns(text: str) -> dict[str, Any]:
    """Is this PNS a tornado storm survey, and what does it assert?"""
    is_survey = bool(SURVEY_HEADER_RE.search(text))
    mentions_tornado = bool(TORNADO_RE.search(text))
    ratings = sorted({m.group(1).upper() for m in EF_RATING_RE.finditer(text)})
    return {
        "is_storm_survey": is_survey,
        "mentions_tornado": mentions_tornado,
        "ef_ratings": ";".join(f"EF{r}" for r in ratings),
        # The pairing that makes a product usable as oracle text: it is a survey
        # write-up *and* it concerns a tornado with a rating attached.
        "is_tornado_survey": is_survey and mentions_tornado,
    }


# A storm-survey PNS is a compendium: one product covers every tornado an office
# surveyed, each as its own section headed ".<Name> Tornado...". Attaching the
# whole product to a hazard would hand the model text about other tornadoes, so
# sections are split apart and matched individually.
SEGMENT_HEADER_RE = re.compile(r"^\.(?P<title>[^\n]{1,120}?)\.\.\.\s*$", re.MULTILINE)
FIELD_RE = re.compile(r"^(?P<key>[A-Za-z][A-Za-z /]{2,40}?):\s+(?P<value>.+?)\s*$", re.MULTILINE)
LATLON_RE = re.compile(r"(-?\d+\.\d+)\s*/\s*(-?\d+\.\d+)")
NUMBER_RE = re.compile(r"(-?\d+(?:\.\d+)?)")


def _number(value: str | None) -> float | None:
    match = NUMBER_RE.search(str(value or ""))
    return float(match.group(1)) if match else None


def _latlon(value: str | None) -> tuple[float, float] | None:
    match = LATLON_RE.search(str(value or ""))
    return (float(match.group(1)), float(match.group(2))) if match else None


def parse_survey_segments(text: str) -> list[dict[str, Any]]:
    """Split a storm-survey PNS into per-tornado sections with their fields.

    The structured fields (rating, path length, start/end lat-lon) are what let a
    segment be matched to a DAT hazard geometrically and then cross-checked
    against DAT's own attributes — two independent descriptions of the same
    survey, which is worth having as data rather than assuming they agree.
    """
    headers = list(SEGMENT_HEADER_RE.finditer(text))
    segments = []
    for i, header in enumerate(headers):
        title = header.group("title").strip(". \t")
        if "tornado" not in title.lower():
            continue                      # skip .Overview..., .Discussion..., etc.
        body = text[header.end():headers[i + 1].start() if i + 1 < len(headers) else len(text)]
        fields = {m.group("key").strip().lower(): m.group("value").strip()
                  for m in FIELD_RE.finditer(body)}

        summary = ""
        marker = re.search(r"^Survey Summary:\s*$", body, re.MULTILINE)
        if marker:
            summary = body[marker.end():].strip()

        start = _latlon(fields.get("start lat/lon"))
        end = _latlon(fields.get("end lat/lon"))
        # Offices write EF3, EF-3 and "EF 3" interchangeably.
        rating = re.sub(r"[\s-]+", "", fields.get("rating", "")).upper() or None
        if not rating and start is None:
            continue      # the product's own headline, not a tornado section
        segments.append({
            "title": title,
            "ef_rating": rating,
            "peak_wind_mph": _number(fields.get("estimated peak wind")),
            "path_length_mi": _number(fields.get("path length /statute/")
                                      or fields.get("path length")),
            "path_width_yd": _number(fields.get("path width /maximum/")
                                     or fields.get("path width")),
            "fatalities": _number(fields.get("fatalities")),
            "injuries": _number(fields.get("injuries")),
            "start_date": fields.get("start date"),
            "start_time": fields.get("start time"),
            "start_location": fields.get("start location"),
            "end_location": fields.get("end location"),
            "start_lat": start[0] if start else None,
            "start_lon": start[1] if start else None,
            "end_lat": end[0] if end else None,
            "end_lon": end[1] if end else None,
            "summary": summary,
            "text": body.strip(),
        })
    return segments


# Before roughly 2012 there was no common survey template: products are all-caps
# free text with office-specific bullet fields ("*EF-SCALE RATING...EF-0",
# "* INTENSITY: EF SCALE...2"), no per-tornado sections and no coordinates. The
# text is still the survey — and still the oracle — so it is kept, but it can
# only be matched to a hazard by office, date and place name, and it is labelled
# so that nobody mistakes it for a coordinate-matched section.
LEGACY_EF_RE = re.compile(
    r"EF[\s.-]*(?:SCALE)?[\s.:-]*(?:RATING)?[\s.:-]*(?:EF[\s-]*)?([0-5])\b", re.IGNORECASE)
LEGACY_LENGTH_RE = re.compile(
    r"PATH\s+LENGTH[\s.:]*(?:APPROX(?:IMATELY)?)?[\s.:]*([\d.]+)\s*(MILE|MI|YARD|YD|FEET|FT)",
    re.IGNORECASE)

_LENGTH_TO_MILES = {"MILE": 1.0, "MI": 1.0, "YARD": 1 / 1760, "YD": 1 / 1760,
                    "FEET": 1 / 5280, "FT": 1 / 5280}


def parse_legacy_survey(text: str) -> dict[str, Any]:
    """Best-effort attributes from a pre-template survey product."""
    ef = LEGACY_EF_RE.search(text)
    length_match = LEGACY_LENGTH_RE.search(text)
    length_mi = None
    if length_match:
        unit = length_match.group(2).upper()
        length_mi = round(float(length_match.group(1)) * _LENGTH_TO_MILES.get(unit, 1.0), 3)
    return {
        "ef_rating": f"EF{ef.group(1)}" if ef else None,
        "path_length_mi": length_mi,
        "survey_format": "legacy_unstructured",
    }


def parse_product_time(product_id: str) -> dt.datetime | None:
    """Issue time from an IEM product id ('202503172014-KLZK-NOUS44-PNSLZK')."""
    stamp = product_id.split("-")[0]
    if len(stamp) != 12 or not stamp.isdigit():
        return None
    return dt.datetime.strptime(stamp, "%Y%m%d%H%M").replace(tzinfo=dt.timezone.utc)


def product_wfo(product_id: str) -> str | None:
    """WFO from the trailing PIL of a product id (PNSLZK -> LZK)."""
    parts = product_id.split("-")
    pil = parts[-1] if parts else ""
    return pil[3:6].upper() if len(pil) >= 6 and pil.upper().startswith("PNS") else None

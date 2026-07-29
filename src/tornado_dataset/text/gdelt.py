"""Independent news coverage via the GDELT DOC 2.0 API.

GDELT returns URLs and metadata — never article bodies — which is what the
dataset's links-only design for copyrighted news requires. News publishers are
not the NWS, so every article here is ``same_org_as_geometry = False``; its
``temporal_class`` follows from publication time against the event and the survey.

Two constraints are properties of the service, verified against it rather than
assumed, and they shape everything above:

* **No coverage before 2017-01-01.** Earlier ``startdatetime`` values are rejected
  ("Invalid query start date"), so pre-2017 episodes get no news links and are
  flagged rather than silently left empty.
* **One request per five seconds**, enforced with HTTP 429. Queries are therefore
  issued per *episode* (an outbreak) rather than per hazard, cached on disk, and
  resumable — a full sweep is hours of wall-clock and must survive interruption.

Query construction was settled by measurement, not assumption. The prototype
queried place names alone, having found that adding a hazard word to a *single*
place name collapsed the result set. With an OR-group of a dozen places the
opposite holds: on the March 2025 outbreak, places alone returned 250 articles of
which 2% were about the storm, while the same group plus the term ``tornado``
returned 250 of which 95% were. The hazard term is therefore part of the query,
and the title filter is a second pass rather than the only one.

The window is queried in slices for the same reason. GDELT caps a response at
250 articles and ``sort=datedesc`` fills that quota from the end of the window,
so a single 8-day query returns only follow-up coverage — precisely the
``independent_timely`` articles the dataset most needs would be truncated away.
"""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path
from typing import Any, Iterable

from .. import config
from ..http import cache_key, get_json

# Words that mark a headline as being about severe weather. Deliberately broad:
# recall matters here, and precision is recovered later by linking evidence.
RELEVANCE_KEYWORDS = (
    "tornado", "twister", "storm", "severe weather", "ef-", "ef0", "ef1", "ef2",
    "ef3", "ef4", "ef5", "damage", "destroyed", "devastat", "killed", "death",
    "fatalit", "injur", "disaster", "fema", "emergency", "wreckage", "debris",
    "cleanup", "recovery", "shelter", "hail", "supercell", "funnel",
)


def to_gdelt_time(moment: dt.date | dt.datetime) -> str:
    """GDELT wants YYYYMMDDHHMMSS."""
    if isinstance(moment, dt.datetime):
        return moment.strftime("%Y%m%d%H%M%S")
    return dt.datetime.combine(moment, dt.time.min).strftime("%Y%m%d%H%M%S")


def parse_seendate(value: str) -> str | None:
    """GDELT seendate ('20250315T041500Z') to ISO 8601."""
    try:
        return dt.datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(
            tzinfo=dt.timezone.utc).isoformat()
    except (TypeError, ValueError):
        return None


def build_query(toponyms: Iterable[str], max_terms: int = 12,
                hazard_term: str = "tornado") -> str:
    """``(place OR place OR …) tornado`` — an OR-group narrowed by one hazard word.

    ``hazard_term`` can be set to "" to query places alone, which is what the
    strategy comparison in outputs/text_qa_report.md measures against.
    """
    seen, terms = set(), []
    for name in toponyms:
        cleaned = re.sub(r"\s+", " ", str(name or "")).strip()
        # Parenthetical qualifiers such as "Davidsonville (historical)" are
        # gazetteer bookkeeping and break the query syntax.
        cleaned = re.sub(r"\s*\([^)]*\)", "", cleaned).strip()
        if len(cleaned) < 3 or cleaned.lower() in seen:
            continue
        seen.add(cleaned.lower())
        terms.append(f'"{cleaned}"' if " " in cleaned else cleaned)
        if len(terms) >= max_terms:
            break
    if not terms:
        return ""
    group = f"({' OR '.join(terms)})" if len(terms) > 1 else terms[0]
    return f"{group} {hazard_term}".strip()


def query_articles(query: str, start: dt.date | dt.datetime, end: dt.date | dt.datetime, *,
                   cache_dir: Path, refresh: bool = False,
                   max_records: int = config.GDELT_MAX_RECORDS) -> list[dict[str, Any]]:
    """De-duplicated article records for ``query`` within the window.

    A result of exactly ``max_records`` means the response was truncated; callers
    record that as ``hit_record_cap`` so incomplete coverage stays visible in the
    data instead of looking like an exhaustive result.
    """
    if not query:
        return []
    params = {
        "query": query, "mode": "artlist", "maxrecords": str(max_records),
        "startdatetime": to_gdelt_time(start), "enddatetime": to_gdelt_time(end),
        "format": "json", "sort": "datedesc",
    }
    cache_path = cache_dir / f"gdelt_{cache_key(config.GDELT_DOC_API, params)}.json"
    try:
        payload = get_json(config.GDELT_DOC_API, params, cache_path=cache_path,
                           refresh=refresh, min_interval=config.GDELT_MIN_REQUEST_INTERVAL,
                           timeout=120)
    except Exception:
        # A query that keeps failing (unparsable syntax, service hiccup) must not
        # abort a multi-hour sweep; the empty result is visible in the counts.
        return []

    seen, articles = set(), []
    for article in payload.get("articles", []) or []:
        url = article.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        articles.append(article)
    return articles


def is_relevant(article: dict[str, Any],
                keywords: Iterable[str] = RELEVANCE_KEYWORDS) -> bool:
    """Does the headline mention severe weather at all?"""
    title = str(article.get("title") or "").lower()
    return any(keyword in title for keyword in keywords)


def wayback_snapshot(url: str, timestamp: str, *, cache_dir: Path,
                     refresh: bool = False) -> str | None:
    """Closest Internet Archive snapshot, captured *at collection time*.

    Snapshots are looked up while the corpus is being built rather than assumed
    to exist later: on the prototype's sample only ~40% of news URLs were
    archived, and an unarchived page can disappear before anyone checks.
    """
    params = {"url": url, "timestamp": timestamp}
    cache_path = cache_dir / f"wb_{cache_key(config.WAYBACK_AVAILABILITY_URL, params)}.json"
    try:
        payload = get_json(config.WAYBACK_AVAILABILITY_URL, params,
                           cache_path=cache_path, refresh=refresh,
                           min_interval=1.0, retries=2, timeout=45)
    except Exception:
        return None
    closest = (payload.get("archived_snapshots") or {}).get("closest") or {}
    return closest.get("url") if closest.get("available") else None

"""How much of the licensed full text is reachable from the open URL feed?

"How many LexisNexis articles are in GDELT?" is two questions wearing one coat,
and answering only the convenient one would mislead:

**Level 1 — retrieval overlap.** Of the articles LexisNexis gave us, how many turn
up among the URLs *our* GDELT episode queries returned, and vice versa? This is the
number that matters operationally: it says how much of the corpus the open pipeline
would have found on its own.

**Level 2 — index presence.** For articles with no counterpart at level 1, ask
GDELT directly, by outlet and date, whether it holds the story at all. This
separates "GDELT does not index this outlet" from "our episode queries missed it".
The first is a property of GDELT; the second is a limitation of our retrieval, and
conflating them would flatter our own method.

Both numbers are reported with Wilson intervals and broken down by source type,
because the expected non-overlap is structural: broadcast transcripts, print-only
editions and paywalled wire copy have no public URL for GDELT to index, and no
amount of query tuning changes that.
"""

from __future__ import annotations

import datetime as dt
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from .. import config
from ..dat.evaluate import wilson_interval
from . import gdelt, matching

# Source-name markers for outlets that cannot have a web URL in the feed. Used to
# explain non-overlap, never to exclude anything from the counts.
TRANSCRIPT_MARKERS = ("transcript", "news transcript", "cbs news", "abc news transcript",
                      "nbc news", "cnn transcripts", "npr", "radio")
WIRE_MARKERS = ("associated press", "agence france presse", "reuters", "wire",
                "targeted news service", "states news service", "pr newswire",
                "business wire", "enp newswire", "newstex", "contify")
PRINT_MARKERS = ("edition", "post-dispatch", "daily herald", "kernel", "university wire")


def classify_source(source: str) -> str:
    """Coarse outlet class, for explaining where overlap is and is not possible."""
    text = str(source or "").lower()
    if any(m in text for m in TRANSCRIPT_MARKERS):
        return "broadcast_transcript"
    if any(m in text for m in WIRE_MARKERS):
        return "wire_or_syndicated"
    if any(m in text for m in PRINT_MARKERS):
        return "print_or_campus"
    return "web_native_or_other"


def level1(lexis: list[dict[str, Any]], gdelt_records: list[dict[str, Any]],
           mapping: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Retrieval overlap in both directions, with a per-source-class breakdown."""
    matches = matching.match_pairs(lexis, gdelt_records, mapping)
    best = matching.best_per_article(matches)

    matched_lexis = set(best)
    matched_urls = {m["gdelt_url"] for m in matches}
    lexis_total = len(lexis)
    gdelt_total = len({r.get("url") for r in gdelt_records if r.get("url")})

    by_class: dict[str, dict[str, int]] = {}
    for article in lexis:
        klass = classify_source(article.get("source", ""))
        bucket = by_class.setdefault(klass, {"articles": 0, "matched": 0})
        bucket["articles"] += 1
        bucket["matched"] += int(article.get("textref_uid") in matched_lexis)

    return {
        "matches": matches,
        "best_per_article": best,
        "lexis_total": lexis_total,
        "lexis_matched": len(matched_lexis),
        "lexis_matched_ci": wilson_interval(len(matched_lexis), lexis_total),
        "gdelt_total": gdelt_total,
        "gdelt_matched": len(matched_urls),
        "gdelt_matched_ci": wilson_interval(len(matched_urls), gdelt_total),
        "by_source_class": by_class,
        "domain_map_coverage": sum(
            1 for a in lexis
            if str(a.get("source", "")).strip().lower() in mapping) / max(1, lexis_total),
    }


def level2_probe(unmatched: list[dict[str, Any]], *, cache_dir: Path,
                 sample_size: int = 60, seed: int = 11,
                 refresh: bool = False) -> dict[str, Any]:
    """Ask GDELT directly whether it holds a story our episode queries missed.

    One query per sampled article, at the API's one-per-five-seconds pace, so the
    sample is deliberately small. The query is the article's most distinctive
    headline tokens restricted to its own outlet's domain where we know it — which
    is the narrowest honest test of "is this story in the index at all?".
    """
    import random

    population = [a for a in unmatched if a.get("date")]
    sample = random.Random(seed).sample(population, min(sample_size, len(population)))
    results = []
    for article in sample:
        published: dt.date = article["date"]
        terms = matching.normalise_title(article.get("headline", ""))[:6]
        domain = article.get("domain") or ""
        query = " ".join(f'"{t}"' if " " in t else t for t in terms)
        if domain:
            query = f"{query} domain:{domain}"
        found = gdelt.query_articles(
            query, published - dt.timedelta(days=config.OVERLAP_DATE_TOLERANCE_DAYS),
            published + dt.timedelta(days=config.OVERLAP_DATE_TOLERANCE_DAYS),
            cache_dir=cache_dir, refresh=refresh, max_records=50)
        if found is None:
            # A refused probe says nothing about the index and must not be
            # counted as "not in GDELT" — that would inflate the very number
            # this probe exists to measure.
            results.append({
                "textref_uid_lexis": article.get("textref_uid"),
                "headline": article.get("headline"), "source": article.get("source"),
                "source_class": classify_source(article.get("source", "")),
                "date": published.isoformat(), "query": query,
                "candidates_returned": None, "in_index": None,
                "matched_url": None, "jaccard": None, "probe_failed": True,
            })
            continue
        hit = None
        for candidate in found:
            scores = matching.title_similarity(article.get("headline", ""),
                                               candidate.get("title", ""))
            if scores["min_tokens"] >= 3 and (
                    scores["jaccard"] >= config.OVERLAP_TITLE_SIMILARITY
                    or scores["containment"] >= config.OVERLAP_TITLE_SIMILARITY_STRICT):
                hit = {**scores, "url": candidate.get("url"),
                       "domain": candidate.get("domain")}
                break
        results.append({
            "textref_uid_lexis": article.get("textref_uid"),
            "headline": article.get("headline"),
            "source": article.get("source"),
            "source_class": classify_source(article.get("source", "")),
            "date": published.isoformat(),
            "query": query,
            "candidates_returned": len(found),
            "in_index": hit is not None,
            "matched_url": (hit or {}).get("url"),
            "jaccard": (hit or {}).get("jaccard"),
        })

    # Probes that never got an answer are excluded from the denominator rather
    # than counted as absences.
    answered = [r for r in results if r["in_index"] is not None]
    in_index = sum(1 for r in answered if r["in_index"])
    by_class = Counter(r["source_class"] for r in answered if r["in_index"])
    return {
        "results": results,
        "sampled": len(results),
        "answered": len(answered),
        "failed_probes": len(results) - len(answered),
        "in_index": in_index,
        "in_index_ci": wilson_interval(in_index, len(answered)) if answered else (0.0, 0.0),
        "in_index_by_class": dict(by_class),
        "population": len(population),
    }

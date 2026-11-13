"""Match the same news story across two very different records.

A LexisNexis export gives a publication name and a clean headline; GDELT gives a
domain and a headline that has been through its own pipeline (punctuation spaced
out, occasionally truncated, sometimes suffixed with the outlet). Deciding whether
the two describe the same article is therefore a fuzzy comparison of three things:
headline, publication date, and outlet.

Two title measures are kept rather than one, because the failure modes differ:

* **Jaccard** over content tokens — symmetric, the honest default.
* **Containment** over the shorter title — catches the case where one side is a
  truncation or a subheaded variant of the other, which Jaccard punishes unfairly.

Both are reported on every pair, so a reader can see which one carried the match.
"""

from __future__ import annotations

import datetime as dt
import re
from collections import Counter, defaultdict
from typing import Any, Iterable

from .. import config

_TOKEN_RE = re.compile(r"[a-z0-9]+")
# Words that carry no identity: they inflate similarity between unrelated
# headlines about the same topic ("tornado", "storm") or are pure grammar.
_STOPWORDS = {
    "a", "an", "the", "of", "in", "on", "at", "to", "for", "and", "or", "as", "by",
    "with", "from", "after", "before", "is", "are", "was", "were", "be", "been",
    "it", "its", "this", "that", "these", "those", "his", "her", "their", "s",
    "says", "say", "said", "new", "more", "amid", "into", "over", "up", "out",
}
_URL_RE = re.compile(r"https?://([^/\s\"'<>]+)")
# Outlet names appended to a headline by the feed ("… - Kentucky Kernel").
_TRAILING_SOURCE_RE = re.compile(r"\s+[-–|]\s+[^-–|]{3,40}$")


def normalise_title(title: str, *, strip_trailing_source: bool = True) -> list[str]:
    """Headline -> content tokens, with grammar and topic words removed."""
    text = str(title or "")
    if strip_trailing_source:
        text = _TRAILING_SOURCE_RE.sub("", text)
    words = _TOKEN_RE.findall(text.lower())
    return [w for w in words if w not in _STOPWORDS and len(w) > 1]


def title_similarity(left: str, right: str) -> dict[str, float]:
    """Jaccard and containment over content tokens, plus the token counts.

    Short titles are reported with their length so a caller can refuse to trust a
    high score computed from three words.
    """
    a, b = set(normalise_title(left)), set(normalise_title(right))
    if not a or not b:
        return {"jaccard": 0.0, "containment": 0.0, "min_tokens": 0}
    shared = len(a & b)
    return {
        "jaccard": round(shared / len(a | b), 4),
        "containment": round(shared / min(len(a), len(b)), 4),
        "min_tokens": min(len(a), len(b)),
    }


# ── outlet identity ──────────────────────────────────────────────────────────
def domain_of(url: str) -> str:
    """Bare host of a URL, without 'www.'."""
    match = _URL_RE.search(str(url or ""))
    if not match:
        return ""
    return match.group(1).lower().removeprefix("www.")


def domains_in_text(text: str) -> list[str]:
    """Every host mentioned in a body — LexisNexis often prints the source URL."""
    return [d.removeprefix("www.") for d in
            (m.group(1).lower() for m in _URL_RE.finditer(str(text or "")))]


# A seed for outlets whose LexisNexis name cannot be derived from a domain string.
# Deliberately small: the map is built mostly from the corpus itself (see
# build_source_domain_map), and this only covers frequent titles that never print
# their own URL. Extend it rather than guessing inside the matcher.
SEED_SOURCE_DOMAINS = {
    "usa today online": "usatoday.com",
    "usa today": "usatoday.com",
    "newsweek.com": "newsweek.com",
    "cnn wire": "cnn.com",
    "cnn.com": "cnn.com",
    "the independent (united kingdom)": "independent.co.uk",
    "daily star online": "dailystar.co.uk",
    "mailonline": "dailymail.co.uk",
    "st. louis post-dispatch (missouri)": "stltoday.com",
    "chicago daily herald": "dailyherald.com",
    "times now": "timesnownews.com",
    "mediaite": "mediaite.com",
    "cbc (news)": "cbc.ca",
    "the associated press": "apnews.com",
    "associated press international": "apnews.com",
    "associated press state & local": "apnews.com",
    "agence france presse -- english": "afp.com",
    "the new york times": "nytimes.com",
    "the washington post": "washingtonpost.com",
    "usa today (online)": "usatoday.com",
    "axios": "axios.com",
    "the hill": "thehill.com",
    "newsweek": "newsweek.com",
}


def build_source_domain_map(articles: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Learn source name -> domain from the articles that print their own URL.

    Roughly one article in eight carries its URL in the body, which is enough to
    derive the mapping for those outlets from the data instead of asserting it.
    The seed table fills in frequent titles that never print one; anything still
    unmapped is reported rather than guessed.
    """
    votes: dict[str, Counter[str]] = defaultdict(Counter)
    for article in articles:
        source = str(article.get("source") or "").strip().lower()
        if not source:
            continue
        for domain in domains_in_text(article.get("body", "")):
            # Ignore aggregators and social links that appear in boilerplate.
            if any(x in domain for x in ("twitter", "facebook", "instagram", "youtube",
                                         "google", "bit.ly", "t.co", "archive.org")):
                continue
            votes[source][domain] += 1

    mapping: dict[str, dict[str, Any]] = {}
    for source, counter in votes.items():
        domain, count = counter.most_common(1)[0]
        mapping[source] = {"domain": domain, "evidence": "url_in_body",
                           "support": count, "alternatives": len(counter)}
    for source, domain in SEED_SOURCE_DOMAINS.items():
        mapping.setdefault(source, {"domain": domain, "evidence": "seed_table",
                                    "support": 0, "alternatives": 0})
    return mapping


def same_outlet(source: str, domain: str, mapping: dict[str, dict[str, Any]]) -> bool:
    """Does a LexisNexis publication name correspond to a GDELT domain?"""
    known = mapping.get(str(source or "").strip().lower())
    if known and known["domain"] == domain:
        return True
    # Fall back to a name/host token overlap ("Newsweek.com" ↔ newsweek.com).
    host = set(_TOKEN_RE.findall(domain.rsplit(".", 1)[0])) if domain else set()
    name = set(normalise_title(source, strip_trailing_source=False))
    return bool(host and name and host & name)


# ── pairing ──────────────────────────────────────────────────────────────────
def match_pairs(lexis: list[dict[str, Any]], gdelt: list[dict[str, Any]],
                mapping: dict[str, dict[str, Any]], *,
                date_tolerance: int = config.OVERLAP_DATE_TOLERANCE_DAYS,
                similarity: float = config.OVERLAP_TITLE_SIMILARITY,
                strict_similarity: float = config.OVERLAP_TITLE_SIMILARITY_STRICT,
                ) -> list[dict[str, Any]]:
    """Candidate same-story pairs, blocked by date so this stays cheap.

    A pair is accepted when the titles agree *and* the outlets agree, or when the
    titles agree so strongly that syndication is the obvious explanation and the
    outlet does not need to.
    """
    by_day: dict[dt.date, list[dict[str, Any]]] = defaultdict(list)
    for record in gdelt:
        if record.get("date"):
            by_day[record["date"]].append(record)

    matches = []
    for article in lexis:
        published = article.get("date")
        if not published:
            continue
        seen: set[str] = set()
        for offset in range(-date_tolerance, date_tolerance + 1):
            for candidate in by_day.get(published + dt.timedelta(days=offset), []):
                key = candidate.get("url", "")
                if key in seen:
                    continue
                seen.add(key)
                scores = title_similarity(article.get("headline", ""),
                                          candidate.get("title", ""))
                if scores["min_tokens"] < 3:
                    continue
                outlet = same_outlet(article.get("source", ""), candidate.get("domain", ""),
                                     mapping)
                strong = (scores["jaccard"] >= similarity
                          or scores["containment"] >= strict_similarity)
                if not strong:
                    continue
                if not outlet and scores["jaccard"] < strict_similarity:
                    continue
                matches.append({
                    "textref_uid_lexis": article.get("textref_uid"),
                    "lexis_headline": article.get("headline"),
                    "lexis_source": article.get("source"),
                    "lexis_date": published.isoformat(),
                    "gdelt_url": candidate.get("url"),
                    "gdelt_title": candidate.get("title"),
                    "gdelt_domain": candidate.get("domain"),
                    "gdelt_date": candidate["date"].isoformat(),
                    "day_difference": offset,
                    "outlet_match": outlet,
                    **scores,
                })
    return matches


def best_per_article(matches: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Keep the strongest GDELT counterpart per LexisNexis article."""
    best: dict[str, dict[str, Any]] = {}
    for match in matches:
        key = match["textref_uid_lexis"]
        current = best.get(key)
        rank = (match["outlet_match"], match["jaccard"], match["containment"])
        if current is None or rank > (current["outlet_match"], current["jaccard"],
                                     current["containment"]):
            best[key] = match
    return best

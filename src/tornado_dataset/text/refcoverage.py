"""How much of what Wikipedia cites do we hold? Wikipedia news references vs LexisNexis.

Wikipedia's tornado articles cite a few thousand news articles, chosen by
editors who had no idea this corpus existed. That makes them an independent
sample of "tornado news that mattered", and the share of them we already hold
is a recall estimate the three news corpora cannot give about themselves.

LexisNexis publishes no URL, so identity is inferred. Four tiers, from the
strongest evidence to the weakest, each reported on its own and never pooled:

=================== ==========================================================
tier                accepted when
=================== ==========================================================
``title_outlet``    same outlet, dates within ±3 days, headlines agree
``title_syndicated`` another outlet, ±3 days, headlines near-identical (wire copy)
``content``         the cited article's own text is contained in a LexisNexis body
``title_fuzzy``     same outlet, ±7 days, headlines partly agree — the weak tier
=================== ==========================================================

``content`` needs the cited article's text, retrieved from the publisher or the
Wayback Machine (:mod:`tornado_dataset.text.fulltext`). It is the only tier that
sees through a rewritten print headline, and it doubles as a check on the title
tiers: a title match whose text does not overlap is a false positive.

The denominator, two ways
-------------------------
*Overall* recall counts every news reference. *In-universe* recall counts only
references from outlets LexisNexis carries — approximated as "the outlet appears
at least once in our export", because no LexisNexis source list exists for the
search. An outlet LexisNexis carries but that never matched the tornado/storm
search is counted out of universe, so in-universe recall is **optimistic**;
overall recall is the conservative figure.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import re
from collections import defaultdict
from typing import Any, Iterable

import pandas as pd

from .. import config
from . import matching

TIERS = ("title_outlet", "title_syndicated", "content", "title_fuzzy")
STRONG_TIERS = ("title_outlet", "title_syndicated", "content")

# ── outlet identity ──────────────────────────────────────────────────────────
_PAREN = re.compile(r"\([^)]*\)")
_NON_WORD = re.compile(r"[^a-z0-9]+")
# Words that name no outlet on their own. A single-token outlet name made of one
# of these ("News", "Times") would match half the export by containment.
_GENERIC = {"news", "times", "herald", "journal", "tribune", "gazette", "post",
            "daily", "online", "press", "report", "weather", "the", "today",
            "star", "record", "sun", "observer", "register", "courier", "wire",
            "network", "radio", "tv", "media", "com", "magazine"}
_TLD = re.compile(r"\.(com|org|net|gov|edu|us|co\.uk|ca|tv|fm|info|news)$")


def outlet_key(name: str) -> str:
    """Comparable outlet name: no article, no location suffix, no punctuation.

    "The Courier-Journal (Louisville, Kentucky)" and "Courier Journal" both
    become "courier journal"; "USA Today (Online)" becomes "usa today".
    """
    text = _PAREN.sub(" ", str(name or "").lower())
    text = re.sub(r"\.com\b", " ", text)
    text = _NON_WORD.sub(" ", text).strip()
    text = re.sub(r"^the ", "", text)
    text = re.sub(r"\b(online|website|web edition|digital)\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def host_label(domain: str) -> str:
    """"courier-journal.com" -> "courierjournal"; "abcnews.go.com" -> "abcnews"."""
    domain = re.sub(r"^(www\d?|m|amp|edition|eu|uk|us)\.", "", domain or "")
    domain = re.sub(r"\.go\.com$", ".com", domain)
    label = _TLD.sub("", domain).split(".")[-1] if domain else ""
    return _NON_WORD.sub("", label)


def _contains(short: str, long: str) -> bool:
    """``long`` is ``short`` plus a suffix: an edition, a product, a place.

    "Associated Press" → "Associated Press State & Local" and "New York Times"
    → "New York Times - International Edition" are the cases this is for. The
    shorter name must lead, have two words and one of them non-generic, because
    everything looser matched a different paper on the first run: "Leader" took
    the Lexington Herald-Leader, "Daily News (New York)" the Dayton Daily News.
    """
    tokens = short.split() if short else []
    if len(tokens) < 2 or all(t in _GENERIC for t in tokens) or not long:
        return False
    return f"{long} ".startswith(f"{short} ")


def _equal(name: str, key: str) -> bool:
    """Equal names, unless the name is one generic word ("Gazette" is a dozen papers)."""
    return bool(name) and name == key and not (len(name.split()) == 1 and name in _GENERIC)


# LexisNexis files a network's broadcast transcripts under the network's name
# ("CBS News Transcripts CBS EVENING NEWS 6:30 PM EST"). They are a different
# product from the network's web articles, so they must not put a cbsnews.com
# citation inside the universe.
_TRANSCRIPT = re.compile(r"transcript|\b\d{1,2}:\d{2}\s*(?:am|pm)\b", re.I)


class OutletIndex:
    """Which LexisNexis source names can a Wikipedia citation's outlet be?

    Evidence, in order: the domain map learned from LexisNexis bodies that print
    their own URL (:func:`matching.build_source_domain_map`) — but only where the
    domain resembles the name, since a body's most frequent URL is often someone
    else's (AP copy printing theguardian.com, an aggregator printing cnn.com) —
    plus its hand-made seed table; equal or contained names; and a host label
    equal to a name with its spaces removed ("desmoinesregister" ↔ "Des Moines
    Register"). Broadcast transcripts are left out (see ``_TRANSCRIPT``). Every LexisNexis source is
    tried, so the answer for one citation is a set — "AP" legitimately maps to
    The Associated Press *and* Associated Press State & Local.
    """

    def __init__(self, lexis: pd.DataFrame):
        sources = sorted(s for s in set(lexis.source.fillna("").astype(str)) - {""}
                         if not _TRANSCRIPT.search(s))
        mapping = matching.build_source_domain_map(
            lexis[["source", "body"]].to_dict("records"))
        self.keys = {source: outlet_key(source) for source in sources}
        self.compact = {source: key.replace(" ", "") for source, key in self.keys.items()}
        self.by_domain: dict[str, set[str]] = defaultdict(set)
        for source in sources:
            known = mapping.get(source.strip().lower())
            if not known:
                continue
            label, compact = host_label(known["domain"]), self.compact[source]
            plausible = len(label) >= 3 and (label in compact or compact in label)
            if known["evidence"] == "seed_table" or plausible:
                self.by_domain[known["domain"]].add(source)
        self._cache: dict[tuple, frozenset[str]] = {}

    def sources_for(self, domain: str, names: Iterable[str]) -> frozenset[str]:
        names = tuple(sorted({outlet_key(n) for n in names if outlet_key(n)}))
        cache_key = (domain, names)
        if cache_key in self._cache:
            return self._cache[cache_key]
        found = set(self.by_domain.get(domain, ()))
        label = host_label(domain)
        for source, key in self.keys.items():
            if any(_equal(n, key) or _contains(n, key) or _contains(key, n) for n in names):
                found.add(source)
            elif label and len(label) >= 5 and label == self.compact[source]:
                found.add(source)
        result = frozenset(found)
        self._cache[cache_key] = result
        return result


# ── references → the news-article unit ───────────────────────────────────────
PRECISION_RANK = {"day": 0, "month": 1, "year": 2, "none": 3}


def fetch_date(pub_date: str, page_years: str) -> str:
    """The date the archive copy is requested for: the citation's own date, or
    mid-year of the citing page's event year when the citation is undated."""
    if pub_date:
        return pub_date
    years = [y for y in str(page_years or "").split("|") if y]
    return f"{years[0]}-06-01" if years else ""


def article_key(url: str, title: str, work: str) -> str:
    """One cited news article. URL where there is one, else outlet + headline
    (print citations); a story cited from three pages is one article."""
    if url:
        from .corpora import normalise_url
        return "url:" + normalise_url(pd.Series([url])).iloc[0]
    return "print:" + outlet_key(work) + "|" + " ".join(matching.normalise_title(title))


def news_articles(refs: pd.DataFrame) -> pd.DataFrame:
    """Collapse news references to distinct cited articles, keeping where each
    was cited from (pages, sections) so coverage can be reported per tornado."""
    news = refs[refs.ref_class == "news"].copy()
    news["article_key"] = [article_key(u, t, w) for u, t, w in
                           zip(news.url, news.title, news.work)]
    # The most precise citation date wins ("none" would sort before "year").
    rank = news.date_precision.map(PRECISION_RANK).fillna(len(PRECISION_RANK))
    first = news.assign(_rank=rank).sort_values(["_rank", "pageid"]) \
        .groupby("article_key").first()
    agg = news.groupby("article_key").agg(
        n_pages=("pageid", "nunique"),
        pages=("page_title", lambda s: " | ".join(sorted(set(s)))),
        page_years=("page_year", lambda s: "|".join(str(int(y)) for y in sorted(set(s)))),
        sections=("passage", lambda s: " | ".join(sorted(set(s)))),
    )
    cols = ["url", "archive_url", "title", "work", "publisher", "agency", "via",
            "authors", "pub_date", "date_precision", "domain", "template"]
    return first[cols].join(agg).reset_index()


# ── title tiers ──────────────────────────────────────────────────────────────
def _scores(left: str, right: str) -> dict[str, float]:
    return matching.title_similarity(left, right)


def title_matches(articles: pd.DataFrame, lexis: pd.DataFrame,
                  outlets: OutletIndex) -> pd.DataFrame:
    """Every LexisNexis candidate that passes a title tier, one row per pair.

    Blocking is by date where the citation is dated to the day, and by outlet
    where it is not — an undated citation compared against every article of its
    year would match recurring headlines ("Storms knock out power") across
    events. Undated citations therefore only reach ``title_outlet`` and
    ``title_fuzzy``, and only within the cited page's event year or the next.
    """
    lex = lexis.assign(lex_day=pd.to_datetime(lexis.pub_date, errors="coerce").dt.date)
    lex = lex[lex.lex_day.notna()]
    by_day: dict[dt.date, list] = defaultdict(list)
    by_source: dict[str, list] = defaultdict(list)
    for row in lex[["textref_uid", "headline", "source", "lex_day"]].itertuples(index=False):
        by_day[row.lex_day].append(row)
        by_source[row.source].append(row)

    tol = config.OVERLAP_DATE_TOLERANCE_DAYS
    fuzzy_tol = config.WIKI_REF_FUZZY_DATE_DAYS
    rows = []
    for art in articles.itertuples(index=False):
        sources = outlets.sources_for(art.domain, [art.work, art.publisher,
                                                   art.agency, art.via])
        dated = art.date_precision == "day" and art.pub_date
        if dated:
            day = dt.date.fromisoformat(art.pub_date)
            candidates = [c for off in range(-fuzzy_tol, fuzzy_tol + 1)
                          for c in by_day.get(day + dt.timedelta(days=off), [])]
        else:
            years = {int(y) for y in str(art.page_years).split("|") if y}
            years |= {y + 1 for y in years}
            candidates = [c for s in sources for c in by_source.get(s, [])
                          if c.lex_day.year in years]
        for cand in candidates:
            s = _scores(art.title, cand.headline)
            if s["min_tokens"] < 3:
                continue
            same = cand.source in sources
            gap = abs((cand.lex_day - day).days) if dated else None
            tier = None
            if same and (gap is None or gap <= tol) and (
                    s["jaccard"] >= config.OVERLAP_TITLE_SIMILARITY
                    or s["containment"] >= config.OVERLAP_TITLE_SIMILARITY_STRICT):
                tier = "title_outlet"
            elif (not same and gap is not None and gap <= tol
                  and s["jaccard"] >= config.OVERLAP_TITLE_SIMILARITY_STRICT
                  and s["min_tokens"] >= config.WIKI_REF_SYNDICATED_MIN_TOKENS):
                tier = "title_syndicated"
            elif same and s["min_tokens"] >= 4 and (
                    s["jaccard"] >= config.WIKI_REF_FUZZY_JACCARD
                    or s["containment"] >= config.WIKI_REF_FUZZY_CONTAINMENT):
                tier = "title_fuzzy"
            if tier:
                rows.append({"article_key": art.article_key, "tier": tier,
                             "textref_uid": cand.textref_uid,
                             "lexis_headline": cand.headline, "lexis_source": cand.source,
                             "lexis_date": cand.lex_day.isoformat(), "day_gap": gap,
                             "outlet_match": same, **s})
    return pd.DataFrame(rows, columns=["article_key", "tier", "textref_uid",
                                       "lexis_headline", "lexis_source", "lexis_date",
                                       "day_gap", "outlet_match", "jaccard",
                                       "containment", "min_tokens"])


# ── content tier ─────────────────────────────────────────────────────────────
_WORD = re.compile(r"[a-z0-9]+")


def shingles(text: str, k: int = config.WIKI_REF_SHINGLE_WORDS,
             sample: int = config.WIKI_REF_SHINGLE_SAMPLE) -> set[int]:
    """Hashed ``k``-word shingles, keeping one in ``sample`` by hash value.

    Keeping by hash (not by position) means both sides keep the *same* shingles,
    so containment estimated on the sample is unbiased — and the LexisNexis index
    fits in memory at 1/``sample`` of its size.
    """
    words = _WORD.findall(str(text or "").lower())
    out = set()
    for i in range(len(words) - k + 1):
        h = int.from_bytes(hashlib.blake2b(" ".join(words[i:i + k]).encode(),
                                           digest_size=8).digest(), "big")
        if h % sample == 0:
            out.add(h)
    return out


class ShingleIndex:
    """Inverted index of sampled LexisNexis body shingles."""

    def __init__(self, lexis: pd.DataFrame):
        self.index: dict[int, list[int]] = defaultdict(list)
        self.rows = lexis[["textref_uid", "headline", "source", "pub_date"]].reset_index(drop=True)
        self.sizes = []
        for i, body in enumerate(lexis.body.fillna("")):
            sh = shingles(body)
            self.sizes.append(len(sh))
            for h in sh:
                self.index[h].append(i)

    def best(self, text: str) -> dict[str, Any] | None:
        """The LexisNexis article holding the largest share of ``text``'s shingles."""
        sh = shingles(text)
        if len(sh) < config.WIKI_REF_MIN_SHINGLES:
            return None
        hits: dict[int, int] = defaultdict(int)
        for h in sh:
            for i in self.index.get(h, ()):
                hits[i] += 1
        if not hits:
            return {"containment": 0.0, "n_shingles": len(sh)}
        i, shared = max(hits.items(), key=lambda kv: kv[1])
        row = self.rows.iloc[i]
        day = str(row.pub_date)[:10]
        return {"containment": round(shared / len(sh), 4), "n_shingles": len(sh),
                "textref_uid": row.textref_uid, "lexis_headline": row.headline,
                "lexis_source": row.source,
                "lexis_date": day if re.fullmatch(r"\d{4}-\d{2}-\d{2}", day) else ""}


def content_matches(articles: pd.DataFrame, texts: dict[str, str],
                    index: ShingleIndex) -> pd.DataFrame:
    """Best content match per retrieved article; ``tier`` set when it passes."""
    rows = []
    for art in articles.itertuples(index=False):
        text = texts.get(art.url)
        if not text:
            continue
        best = index.best(text)
        if best is None:
            continue
        passed = best["containment"] >= config.WIKI_REF_CONTENT_CONTAINMENT
        if passed and art.date_precision == "day" and best.get("lexis_date"):
            gap = abs((dt.date.fromisoformat(best["lexis_date"])
                       - dt.date.fromisoformat(art.pub_date)).days)
            passed = gap <= config.WIKI_REF_CONTENT_DATE_DAYS
            best["day_gap"] = gap
        rows.append({"article_key": art.article_key,
                     "tier": "content" if passed else None, **best})
    return pd.DataFrame(rows)


# ── outlet type, for the breakdown ───────────────────────────────────────────
WIRE_DOMAINS = {"apnews.com", "reuters.com", "afp.com", "upi.com"}
NATIONAL_DOMAINS = {
    "cnn.com", "nytimes.com", "washingtonpost.com", "usatoday.com", "nbcnews.com",
    "cbsnews.com", "abcnews.go.com", "foxnews.com", "npr.org", "latimes.com",
    "wsj.com", "theguardian.com", "bbc.com", "bbc.co.uk", "newsweek.com",
    "time.com", "politico.com", "thehill.com", "axios.com", "nypost.com",
    "msn.com", "yahoo.com", "huffpost.com", "huffingtonpost.com", "insider.com",
    "businessinsider.com", "bloomberg.com", "cnbc.com", "theatlantic.com",
    "vox.com", "slate.com", "dailymail.co.uk", "independent.co.uk", "people.com",
}
WEATHER_DOMAINS = {"weather.com", "accuweather.com", "foxweather.com",
                   "wunderground.com", "severe-weather.eu", "theweathernetwork.com",
                   "weathernation.com"}
_CALLSIGN = re.compile(r"^(?:[a-z0-9-]+\.)?[kw][a-z]{2,3}(?:\d+|tv|news\d*|-?tv)?\.(?:com|org|net|tv)$")


def outlet_type(domain: str, agency: str = "") -> str:
    """``wire`` · ``national`` · ``weather_media`` · ``local_broadcast`` · ``local_other``."""
    if domain in WIRE_DOMAINS or (agency and not domain):
        return "wire"
    if domain in NATIONAL_DOMAINS:
        return "national"
    if domain in WEATHER_DOMAINS:
        return "weather_media"
    if _CALLSIGN.match(domain or "") or re.search(r"(news|tv)\d+\.com$", domain or ""):
        return "local_broadcast"
    return "local_other"

"""Link news articles to the tornado, or outbreak, they describe.

The problem in one line: an article published on 17 March 2025 could be about any
of roughly 125 tornadoes surveyed in the preceding fortnight, and we have to say
which — or say honestly that it is about the outbreak rather than one tornado, or
about no event at all.

The approach, cheapest and most reliable first:

1. **Date window.** Keep events whose convective day falls in
   ``[published − 14 days, published + 3 days]``. Forward, because forecast and
   watch coverage precedes the event; backward, because the aftermath reporting
   runs about two weeks.

2. **Toponym scoring**, which does the actual deciding. Every hazard carries
   authoritative place names from the gazetteer stage, so the question is not the
   hard one ("which places does this article mention?") but the easy one ("does it
   mention *these* places?").

   Names are not equal, and the data says by how much: of 29,447 distinct place
   names, half belong to exactly one hazard, while "Midway" belongs to 172. Each
   name is therefore weighted by its inverse document frequency across the
   gazetteer — derived from the data rather than from a hand-written stoplist —
   and further by where it appears (headline and dateline over body) and how
   specific it is (place over county over state).

3. **Corroboration**: EF rating, casualty counts, explicit dates and weekdays,
   source locality. These break the ties the toponyms leave behind, which is the
   common case when two outbreaks hit the same region inside a fortnight.

4. **Descent to the individual tornado**, only where the evidence supports it.

Every component of every score is written to the output. The weights here are
provisional; the thresholds that decide what gets *published* as a link come from
the hand-annotated sample, not from this file.
"""

from __future__ import annotations

import datetime as dt
import math
import re
from collections import Counter, defaultdict
from typing import Any, Iterable

from .. import config
from ..geo.gazetteer import alias_forms, canonical_place_key

# ── text normalisation ───────────────────────────────────────────────────────
_TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z]+)?")

# Gazetteer names that are also ordinary English words. Inverse document frequency
# cannot catch these: the US has exactly one town called Enough (Missouri) and one
# called Hurricane (West Virginia), so both look *maximally* distinctive among
# places while being common in prose. Matching is therefore case-sensitive — a
# place is capitalised in news writing — and these are refused even then, because
# they are also capitalised at the start of a sentence or in a headline.
_STOP_NAMES = {
    "city", "town", "village", "county", "north", "south", "east", "west",
    "center", "centre", "union", "midway", "eureka", "sunrise", "enough",
    "hurricane", "tornado", "storm", "ark", "why", "what", "only", "many",
    "home", "hope", "friendship", "liberty", "independence", "protection",
    "energy", "advance", "index", "level", "summit", "climax", "welcome",
    "gravity", "hazard", "commerce", "industry", "utility", "national",
    "american", "america", "canada", "mexico", "york", "christian", "warren",
    "jackson", "washington", "franklin", "jefferson", "lincoln", "monroe",
    "homeland", "security", "defiance", "surprise", "paradise", "eden",
    # Month and weekday names are all real US place names *and* appear
    # capitalised in every date reference, so they are pure noise here.
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
}
# 8,160 UGC entries collapse to ~135 forecast offices, so a bare two-letter state
# code is both useless as evidence and dangerous as a string: "IN" is Indiana.
_MIN_NAME_LENGTH = 4


def tokens(text: str, *, lower: bool = True) -> list[str]:
    found = _TOKEN_RE.findall(str(text or ""))
    return [t.lower() for t in found] if lower else found


def ngram_set(text: str, max_tokens: int = config.LINK_MAX_NAME_TOKENS,
              proper_only: bool = False) -> set[str]:
    """All 1..n token n-grams, optionally only those written as proper nouns.

    Place names run to three tokens ("Cave City", "Land Between The Lakes"), so a
    set of n-grams turns "does this article mention any of these 300 names?" into
    a few hundred dictionary probes instead of a few hundred regex scans.

    ``proper_only`` keeps n-grams whose every token is capitalised, which is what
    separates the town of Hurricane, West Virginia from hurricane season.
    """
    words = tokens(text, lower=False)
    grams: set[str] = set()
    for size in range(1, max_tokens + 1):
        for i in range(len(words) - size + 1):
            span = words[i:i + size]
            if proper_only and not all(w[:1].isupper() for w in span):
                continue
            grams.add(" ".join(w.lower() for w in span))
    return grams


def allcaps_tokens(text: str) -> set[str]:
    """Short all-caps tokens, where a state code like 'AR' actually looks like one."""
    return {t.lower() for t in tokens(text, lower=False)
            if t.isupper() and 2 <= len(t) <= 5}


def normalise_name(name: str) -> str:
    """Gazetteer name -> comparable key ('Davidsonville (historical)' -> 'davidsonville')."""
    cleaned = re.sub(r"\s*\([^)]*\)", " ", str(name or ""))
    return " ".join(tokens(cleaned))


def usable_name(key: str) -> bool:
    """Is this gazetteer name safe to match against prose at all?"""
    if not key or key in _STOP_NAMES:
        return False
    parts = key.split()
    # Multi-token names are safe even when a part is generic ("Cave City").
    if len(parts) > 1:
        return True
    return len(key) >= _MIN_NAME_LENGTH


# ── the gazetteer index ──────────────────────────────────────────────────────
class ToponymIndex:
    """Place / county / state names per hazard and episode, with IDF weights."""

    def __init__(self, geography_rows: Iterable[dict[str, Any]]) -> None:
        self.hazard_names: dict[str, dict[str, str]] = {}   # hazard -> {name: level}
        self.episode_names: dict[str, dict[str, str]] = defaultdict(dict)
        self.hazard_episode: dict[str, str] = {}
        # Alias surface form -> the one key its document frequency is counted on,
        # so "St. Louis" and "Saint Louis" share one IDF instead of each looking
        # half as common as the place really is.
        canonical: dict[str, str] = {}
        document_frequency: Counter[str] = Counter()
        hazard_count = 0

        for row in geography_rows:
            hazard = row.get("hazard_uid")
            if not hazard:
                continue
            hazard_count += 1
            episode = row.get("episode_uid")
            if episode:
                self.hazard_episode[hazard] = episode

            names: dict[str, str] = {}
            # The wide matching set where Stage 16 has produced one, falling back
            # to the query set for older geography files. Every surface form of a
            # name is indexed ("Saint Louis" and "St. Louis"), because which one
            # an outlet uses is house style, not information.
            source_column = row.get("places_matching") or row.get("places")
            for raw in str(source_column or "").split(";"):
                for form in alias_forms(raw):
                    key = normalise_name(form)
                    if usable_name(key):
                        names[key] = "place"
                        canonical[key] = canonical_place_key(raw)
            for raw in str(row.get("counties") or "").split(";"):
                key = normalise_name(raw.split(",")[0])
                if usable_name(key):
                    # Several states share a name with one of their own counties
                    # (Arkansas County, Arkansas). Treat the string at its weakest
                    # reading, or a state mention scores as a county hit.
                    names.setdefault(key, "state" if key in STATE_ABBREV else "county")
            # The geography table stores two-letter codes; those are matched as
            # all-caps tokens, while the spelled-out name is matched as text.
            for raw in str(row.get("states") or "").split(";"):
                code = str(raw).strip().upper()
                if len(code) == 2:
                    names.setdefault(code.lower(), "state")
                    spelled = STATE_NAMES.get(code)
                    if spelled:
                        names.setdefault(spelled, "state")

            self.hazard_names[hazard] = names
            # Count each place once per hazard, on its canonical key.
            document_frequency.update({canonical.get(k, k) for k in names})
            if episode:
                for key, level in names.items():
                    # Keep the most specific level seen for the episode.
                    current = self.episode_names[episode].get(key)
                    if current is None or config.LINK_LEVEL_WEIGHTS[level] > \
                            config.LINK_LEVEL_WEIGHTS[current]:
                        self.episode_names[episode][key] = level

        self.hazard_count = max(1, hazard_count)
        self.document_frequency = document_frequency
        self.canonical = canonical
        # Normalised IDF in [0, 1]: a name unique to one hazard scores 1, a name
        # shared by every hazard scores ~0.
        self._max_idf = math.log(self.hazard_count / 1)

    def idf(self, name: str) -> float:
        frequency = self.document_frequency.get(self.canonical.get(name, name), 0)
        if frequency <= 0:
            return 0.0
        return math.log(self.hazard_count / frequency) / self._max_idf


# ── article representation ───────────────────────────────────────────────────
class ArticleText:
    """An article's searchable surfaces, prepared once."""

    def __init__(self, *, headline: str = "", dateline: str = "", body: str = "",
                 title_only: bool = False) -> None:
        self.headline = str(headline or "")
        self.dateline = str(dateline or "")
        self.body = str(body or "")
        self.title_only = title_only

        paragraphs = [p for p in self.body.split("\n\n") if p.strip()]
        lede = "\n\n".join(paragraphs[:config.LINK_LEDE_PARAGRAPHS])
        parts = {"headline": self.headline, "dateline": self.dateline,
                 "lede": lede, "body": self.body}
        # Proper-noun n-grams only: a place name is capitalised in news prose, and
        # matching case-insensitively turns every common word that happens to also
        # be a town into a false match.
        self.surfaces = {name: ngram_set(text, proper_only=True)
                         for name, text in parts.items()}
        self.caps = {name: allcaps_tokens(text) for name, text in parts.items()}
        self.full_text = " \n ".join([self.headline, self.dateline, self.body])

    def position_of(self, name: str, level: str) -> str | None:
        """Strongest surface the name appears in, or None.

        A two-letter state code has to look like one — "AR", not "ar" — otherwise
        it matches ordinary words; everything else has to be capitalised.
        """
        is_code = level == "state" and len(name) == 2
        for surface in ("headline", "dateline", "lede", "body"):
            pool = self.caps[surface] if is_code else self.surfaces[surface]
            if name in pool:
                return surface
        return None


# ── toponym score ────────────────────────────────────────────────────────────
def score_toponyms(article: ArticleText, names: dict[str, str],
                   index: ToponymIndex) -> dict[str, Any]:
    """Weighted evidence that this article is about a place in ``names``."""
    total = 0.0
    matches: list[dict[str, Any]] = []
    best_specific = 0.0
    for name, level in names.items():
        position = article.position_of(name, level)
        if position is None:
            continue
        weight = (index.idf(name)
                  * config.LINK_LEVEL_WEIGHTS[level]
                  * config.LINK_POSITION_WEIGHTS[position])
        total += weight
        matches.append({"name": name, "level": level, "position": position,
                        "idf": round(index.idf(name), 3), "weight": round(weight, 3)})
        # A link should never rest on a generic name or a bare state.
        if level != "state" and name not in _STOP_NAMES and index.idf(name) > 0.25:
            best_specific = max(best_specific, weight)

    matches.sort(key=lambda m: -m["weight"])
    saturated = 1 - math.exp(-total / config.LINK_TOPONYM_SATURATION)
    # Where the strongest name sits matters as much as that it appears at all: a
    # town in the headline or opening paragraphs is what the article is about, one
    # buried in paragraph 30 is context. Used to gate the coarser passes.
    prominent = any(m["level"] != "state" and m["position"] != "body"
                    and m["name"] not in _STOP_NAMES and index.idf(m["name"]) > 0.25
                    for m in matches)
    return {
        "toponym_score": round(saturated, 4),
        "toponym_raw": round(total, 4),
        "n_matches": len(matches),
        "has_specific_match": best_specific > 0,
        "has_prominent_match": prominent,
        "best_match_weight": round(best_specific, 3),
        "matches": matches[:8],
    }


# ── corroborating signals ────────────────────────────────────────────────────
_EF_RE = re.compile(r"\bEF[\s-]?([0-5])\b", re.IGNORECASE)
_NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
                 "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
                 "twelve": 12, "dozen": 12}
_DEATH_RE = re.compile(
    r"\b(\d{1,4}|" + "|".join(_NUMBER_WORDS) + r")\b[^.]{0,40}?"
    r"\b(dead|died|killed|fatalit\w*|deaths?|lives lost)\b", re.IGNORECASE)
_DEATH_RE_REVERSED = re.compile(
    r"\b(killed|claimed|took)\b[^.]{0,25}?\b(\d{1,4}|" + "|".join(_NUMBER_WORDS) + r")\b",
    re.IGNORECASE)
MONTHS = ("january february march april may june july august september october "
          "november december").split()
# The (?!\d) guard is load-bearing: without it "May 2024" parses as day 20 of May,
# silently inventing a day of month out of a year.
_MONTH_DAY_RE = re.compile(
    r"\b(" + "|".join(MONTHS) + r")\s+(\d{1,2})(?!\d)(?:st|nd|rd|th)?"
    r"(?:\s*,?\s*(\d{4}))?\b", re.IGNORECASE)
# "May 2024", "the March 2025 outbreak" — a month and year with no day. Coarse, but
# it is how retrospectives refer back ("to remember May 2024 tornado").
_MONTH_YEAR_RE = re.compile(
    r"\b(" + "|".join(MONTHS) + r")\s+(\d{4})\b", re.IGNORECASE)
_WEEKDAY_RE = re.compile(
    r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.IGNORECASE)
_YEARS_AGO_RE = re.compile(
    r"\b(\d{1,3}|" + "|".join(_NUMBER_WORDS) + r")\s+years?\s+(?:ago|after|later|since)\b",
    re.IGNORECASE)
# A year sitting next to the word tornado/storm/twister — "the 2011 tornado",
# "tornado of 2011". A year on its own anywhere in a story would match far too
# much (dates, ages, statistics), so the hazard word has to be adjacent.
_YEAR_NEAR_TORNADO_RE = re.compile(
    r"\b(?:(?P<year>(?:19|20)\d{2})\s+(?:ef[\s-]?\d\s+)?(?:tornado|twister|storms?|outbreak)"
    r"|(?:tornado|twister|storms?|outbreak)\s+(?:of|in|from)\s+(?P<year2>(?:19|20)\d{2}))\b",
    re.IGNORECASE)
_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _as_int(value: str) -> int | None:
    text = str(value).lower()
    if text.isdigit():
        return int(text)
    return _NUMBER_WORDS.get(text)


def as_date(value: Any) -> dt.date | None:
    """Coerce anything date-shaped to a ``date``, and anything missing to None.

    Guards specifically against pandas' ``NaT``, which is a trap here: it is
    *truthy*, so ``if published:`` passes, and its ``.year`` is ``nan`` — a float —
    so it reaches ``date()`` and fails there instead of at the check. One
    LexisNexis article in ten thousand carries no publication date, which is
    enough to stop a whole run.
    """
    if value is None:
        return None
    # The missing check must come first: pandas' NaT is an *instance of*
    # datetime.datetime, so an isinstance test matches it and NaT.date() hands
    # back another NaT. Self-inequality is what actually identifies NaN and NaT.
    try:
        if value != value:
            return None
    except Exception:
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    year = getattr(value, "year", None)
    if isinstance(year, int):
        try:
            return dt.date(year, value.month, value.day)
        except (TypeError, ValueError):
            return None
    return None


def stated_ef_ratings(text: str) -> set[int]:
    return {int(m.group(1)) for m in _EF_RE.finditer(text)}


def stated_death_counts(text: str) -> set[int]:
    counts = set()
    for pattern in (_DEATH_RE, _DEATH_RE_REVERSED):
        for match in pattern.finditer(text):
            for group in match.groups():
                value = _as_int(group)
                if value is not None and 0 < value < 2000:
                    counts.add(value)
    return counts


def stated_dates_typed(text: str, published: dt.date | None) -> list[tuple[dt.date, str]]:
    """Dates the article names, each tagged with how firmly it was stated.

    The tag matters. A bare "March 14" only means a date once you assume a year,
    and assuming *both* candidate years — as a first version of this did — invents
    a reference to the same date a year earlier and drags a whole unrelated
    outbreak into the candidate set. So a bare month/day resolves to exactly one
    year: the one that puts it at or shortly before publication, since newsrooms
    write about what just happened. Only ``month_day_year`` and ``years_ago`` are
    firm enough to justify looking outside the publication window.
    """
    published = as_date(published)
    found: list[tuple[dt.date, str]] = []
    for match in _MONTH_DAY_RE.finditer(text):
        month = MONTHS.index(match.group(1).lower()) + 1
        day = int(match.group(2))
        if match.group(3):
            try:
                found.append((dt.date(int(match.group(3)), month, day), "month_day_year"))
            except ValueError:
                pass
            continue
        if published is None:
            continue
        for year in (published.year, published.year - 1):
            try:
                candidate = dt.date(year, month, day)
            except ValueError:
                continue
            # Accept the first year that is not meaningfully in the future; a few
            # days' slack allows forecast coverage ("storms expected March 20").
            if (candidate - published).days <= 3:
                found.append((candidate, "month_day"))
                break

    for match in _MONTH_YEAR_RE.finditer(text):
        month = MONTHS.index(match.group(1).lower()) + 1
        try:
            found.append((dt.date(int(match.group(2)), month, 1), "month_year"))
        except ValueError:
            pass

    if published is None:
        return found

    for match in _WEEKDAY_RE.finditer(text):
        target = _WEEKDAYS.index(match.group(1).lower())
        back = (published.weekday() - target) % 7 or 7   # "Friday" on a Friday = last week
        found.append((published - dt.timedelta(days=back), "weekday"))

    for match in _YEARS_AGO_RE.finditer(text):
        years = _as_int(match.group(1))
        if years and 0 < years < 200:
            # Only the year is really known, so this is deliberately coarse; the
            # month is carried over and callers widen the day tolerance.
            found.append((dt.date(published.year - years, published.month, 1), "years_ago"))

    # "the 2011 tornado", "the May 2011 storms" already covered above; this is the
    # bare-year reference that anniversary coverage often uses instead. It pins a
    # year and nothing more, so callers admit it only behind a strong place match.
    for match in _YEAR_NEAR_TORNADO_RE.finditer(text):
        year = int(match.group("year") or match.group("year2"))
        if 1950 <= year <= published.year and year != published.year:
            found.append((dt.date(year, 1, 1), "year_only"))
    return found


def stated_dates(text: str, published: dt.date | None) -> set[dt.date]:
    """All dates named by the article, regardless of how firmly (corroboration use)."""
    return {date for date, _ in stated_dates_typed(text, published)}


# Kinds firm enough to justify looking outside the publication window, and how
# wide a net each one casts: a full date is worth ±1 day, a month or an
# anniversary only identifies a month.
RETROSPECTIVE_KINDS = {"month_day_year": "day", "month_year": "month",
                       "years_ago": "month", "year_only": "year"}


def explicit_dates(text: str, published: dt.date | None) -> list[tuple[dt.date, str]]:
    """Firmly stated dates, each with the granularity it actually pins down."""
    return [(date, RETROSPECTIVE_KINDS[kind])
            for date, kind in stated_dates_typed(text, published)
            if kind in RETROSPECTIVE_KINDS]


def score_corroboration(article: ArticleText, event: dict[str, Any], *,
                        published: dt.date | None,
                        source_states: set[str]) -> dict[str, Any]:
    """Non-geographic agreement between the article and the event record."""
    text = article.full_text
    published = as_date(published)
    signals: dict[str, Any] = {}

    ratings = stated_ef_ratings(text)
    event_ef = event.get("ef_numbers") or set()
    if ratings and event_ef:
        signals["ef_match"] = bool(ratings & event_ef)
    deaths = stated_death_counts(text)
    recorded = event.get("fatalities")
    # Missing for a few polygon-only hazards; NaN is truthy, so ``or 0`` misses it.
    event_deaths = 0 if recorded is None or recorded != recorded else int(recorded)
    if deaths and event_deaths:
        signals["fatalities_match"] = event_deaths in deaths
    event_day = event.get("day")
    if published and event_day:
        named = stated_dates(text, published)
        signals["date_match"] = any(abs((d - event_day).days) <= 1 for d in named)
    if source_states and event.get("states"):
        signals["source_locality"] = bool(source_states & set(event["states"]))

    present = [v for v in signals.values() if isinstance(v, bool)]
    agree = [v for v in present if v]
    return {
        "corroboration_score": round(len(agree) / len(present), 4) if present else 0.0,
        "corroboration_signals": len(present),
        "corroboration_agree": len(agree),
        **{f"sig_{k}": v for k, v in signals.items()},
    }


# ── where a source is based ──────────────────────────────────────────────────
STATE_ABBREV = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI",
    "south carolina": "SC", "south dakota": "SD", "tennessee": "TN", "texas": "TX",
    "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
    "district of columbia": "DC",
}
STATE_NAMES = {code: name for name, code in STATE_ABBREV.items()}
_PAREN_RE = re.compile(r"\(([^)]+)\)")


def source_states(source: str = "", dateline: str = "") -> set[str]:
    """States a source is plausibly local to, from what the export already says.

    LexisNexis qualifies regional titles in parentheses — "St. Louis Post-Dispatch
    (Missouri)" — and datelines name the place a correspondent filed from
    ("LIVONIA, Michigan, U.S.A."). Both are stated in the record, so neither
    requires guessing at editorial geography.
    """
    found: set[str] = set()
    for fragment in _PAREN_RE.findall(str(source or "")):
        code = STATE_ABBREV.get(" ".join(tokens(fragment)))
        if code:
            found.add(code)
    dateline_text = " ".join(tokens(dateline))
    for name, code in STATE_ABBREV.items():
        if name in dateline_text:
            found.add(code)
    return found


# ── candidate generation and combination ─────────────────────────────────────
def candidate_events(published: dt.date, events_by_day: dict[dt.date, list[str]], *,
                     days_before: int = config.LINK_DAYS_BEFORE_EVENT,
                     days_after: int = config.LINK_DAYS_AFTER_EVENT) -> list[tuple[str, int]]:
    """Events whose day lies in the window, with the article's day offset.

    ``days_before`` is how far the article may precede the event (forecast
    coverage), ``days_after`` how far it may follow it (aftermath coverage).
    An article with no usable publication date has no window, and so no candidates.
    """
    published = as_date(published)
    if published is None:
        return []
    out = []
    for offset in range(-days_after, days_before + 1):
        day = published + dt.timedelta(days=offset)
        for uid in events_by_day.get(day, []):
            out.append((uid, -offset))     # +ve: article published after the event
    return out


def combine(toponym: dict[str, Any], corroboration: dict[str, Any]) -> float:
    """Blend the two halves of the evidence into one provisional score."""
    return round(config.LINK_WEIGHT_TOPONYM * toponym["toponym_score"]
                 + config.LINK_WEIGHT_CORROBORATION * corroboration["corroboration_score"], 4)


def score_pair(article: ArticleText, names: dict[str, str], event: dict[str, Any],
               index: ToponymIndex, *, published: dt.date | None,
               source_states: set[str]) -> dict[str, Any]:
    """Full, auditable evidence record for one (article, event) pair."""
    toponym = score_toponyms(article, names, index)
    corroboration = score_corroboration(article, event, published=published,
                                        source_states=source_states)
    record = {**{k: v for k, v in toponym.items() if k != "matches"}, **corroboration}
    record["matched_names"] = ";".join(
        f"{m['name']}({m['level']},{m['position']},{m['weight']})" for m in toponym["matches"])
    record["link_score"] = combine(toponym, corroboration)
    return record


def decide(scored: list[dict[str, Any]], *,
           min_score: float = config.LINK_MIN_SCORE,
           max_links: int = config.LINK_MAX_PER_ARTICLE) -> list[dict[str, Any]]:
    """Turn scored candidates for one article into relations.

    The best qualifying candidate is what the article is *about* (``describes``);
    others that clear the bar are ``mentions``. An article published before onset
    can only ever mention an event — it cannot describe damage that has not
    happened yet — and a candidate resting on nothing more specific than a state
    name is not a link at all.
    """
    qualifying = [s for s in scored
                  if s["link_score"] >= min_score and s["has_specific_match"]]
    qualifying.sort(key=lambda s: -s["link_score"])
    # An article is about a handful of events at most. Without a cap, a wire
    # round-up ("Today in History") or a piece naming dozens of towns collects
    # over a hundred weak links, which is noise in the candidate file and would
    # dominate any sample drawn from it.
    qualifying = qualifying[:max_links]
    for rank, record in enumerate(qualifying):
        forecast = (record.get("day_offset") is not None and record["day_offset"] < 0)
        record["link_rank"] = rank
        record["link_relation"] = "mentions" if (rank > 0 or forecast) else "describes"
    return qualifying


def refine_to_hazard(article: ArticleText, hazard_uids: list[str], index: ToponymIndex,
                     hazard_events: dict[str, dict[str, Any]], *,
                     published: dt.date | None, source_states: set[str],
                     margin: float = config.LINK_HAZARD_MARGIN,
                     min_score: float = config.LINK_HAZARD_MIN_SCORE
                     ) -> dict[str, Any] | None:
    """Pick the single tornado an article is about, or None to stay at episode level.

    Returning None is a real answer: most coverage of a big outbreak is about the
    outbreak, and forcing it onto one track would invent precision.
    """
    scored = []
    for hazard in hazard_uids:
        names = index.hazard_names.get(hazard, {})
        if not names:
            continue
        record = score_pair(article, names, hazard_events.get(hazard, {}), index,
                            published=published, source_states=source_states)
        record["hazard_uid"] = hazard
        scored.append(record)
    if not scored:
        return None
    scored.sort(key=lambda s: -s["link_score"])
    best = scored[0]
    if best["link_score"] < min_score or not best["has_specific_match"]:
        return None
    runner_up = scored[1]["link_score"] if len(scored) > 1 else 0.0
    if runner_up > 0 and best["link_score"] < margin * runner_up:
        return None
    best["hazard_margin"] = round(best["link_score"] / runner_up, 3) if runner_up else None
    return best

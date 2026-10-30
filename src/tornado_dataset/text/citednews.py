"""News articles cited by Wikipedia, as text records: quality and story groups.

Stage 21's crawler fetched every news article the tornado pages cite (publisher
first, archive.org second). What came back is not always the article:

* a **consent or cookie wall** ("Before you continue to YouTube") or a video
  page, where the article is a clip and the text is the player's chrome;
* a **site homepage or section front**, when the article URL now redirects
  there: the same text comes back for several different citations;
* an archive copy of a **live page captured later**, under a newer headline;
* a page that is mostly **navigation**, or another article altogether.

Nothing is dropped for any of these. Each record gets ``text_quality``
(``good`` · ``doubtful`` · ``unusable`` · ``none``) and the ``quality_reasons``
behind it, so an experiment chooses its own threshold.

The main evidence is the **cited headline**: Wikipedia's citation records the
title the editor saw, so a fetched text that contains most of that title's
words (or whose own title matches it) is the article. A text that contains
neither is ``doubtful`` — often the right story under a later headline, but
not checkably so.

**Story groups** collapse syndicated copies (one AP story on five local sites)
the way ``corpora`` does for the other corpora: same headline on the same day,
or texts that share at least half of the shorter one's 8-word shingles.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Iterable

from . import refcoverage as rc

# Video hosts: the cited "article" is a clip; any text is the player's chrome.
VIDEO_DOMAINS = {"youtube.com", "youtu.be", "m.youtube.com", "vimeo.com",
                 "facebook.com", "fb.watch"}
# Text that is a wall or a site front, not an article. Checked at the start.
WALL_RE = re.compile(
    r"^(?:before you continue to youtube|before you continue|we use cookies and data|"
    r"your privacy is important to us|your privacy choices|"
    r"skip to (?:main )?content\s*top headlines)", re.I)
# Citations Wikipedia's archive bots titled for them; the editor's title is lost.
GENERIC_TITLES = {"", "archived copy", "untitled", "home", "news", "index",
                  "page not found", "404", "title"}
STORM_RE = re.compile(r"tornad|twister|funnel cloud|storm|severe weather|derecho", re.I)

TITLE_IN_TEXT_MIN = 0.5        # share of the cited title's words found in the text
TITLE_MATCH_MIN = 0.6          # share found in the page's own extracted title
NAVIGATION_MAX = 0.5           # share of lines shorter than six words
SAME_SITE_OVERLAP = 0.8        # both-way overlap that makes two pages one site front
STORY_OVERLAP = 0.5            # shorter text's shingles found in the longer one
STORY_DAYS = 14
TITLE_HEAD_CHARS = 3000        # the title should appear near the top

_WORD = re.compile(r"[a-z0-9]+")


def _words(text: str) -> set[str]:
    return {w for w in _WORD.findall(str(text or "").lower()) if len(w) > 2}


def title_share(title: str, other: str) -> float | None:
    """Share of ``title``'s words (three letters or more) found in ``other``."""
    words = _words(title)
    if not words:
        return None
    return round(len(words & _words(other)) / len(words), 3)


def is_generic_title(title: str) -> bool:
    return str(title or "").strip().lower() in GENERIC_TITLES


def navigation_share(text: str) -> float:
    lines = [ln for ln in str(text or "").split("\n") if ln.strip()]
    if not lines:
        return 0.0
    return round(sum(len(ln.split()) < 6 for ln in lines) / len(lines), 3)


def is_video(domain: str) -> bool:
    d = str(domain or "").lower()
    return d in VIDEO_DOMAINS or any(d.endswith("." + v) for v in VIDEO_DOMAINS)


def assess(cited_title: str, extracted_title: str, text: str, domain: str,
           shared_with: int = 0, same_site_front: bool = False) -> dict:
    """``text_quality`` and its reasons for one fetched text.

    ``shared_with``: how many *other* citations, with different headlines,
    came back with exactly this text. ``same_site_front``: a near-identical
    text came back for a differently titled citation on the same site.
    """
    if not text:
        return {"text_quality": "none", "quality_reasons": "no_text",
                "title_in_text": None, "title_match": None, "navigation_share": None,
                "mentions_storm": False}
    reasons, fatal = [], False
    if is_video(domain):
        reasons.append("video_page"); fatal = True
    if WALL_RE.search(text[:200].lstrip()):
        reasons.append("wall_or_homepage"); fatal = True
    if shared_with:
        reasons.append("same_text_as_other_citations"); fatal = True
    if same_site_front:
        reasons.append("near_same_text_as_other_citation")
    in_text = title_share(cited_title, text[:TITLE_HEAD_CHARS])
    match = title_share(cited_title, extracted_title)
    if is_generic_title(cited_title) or in_text is None:
        reasons.append("title_unknown")
    elif in_text < TITLE_IN_TEXT_MIN and (match or 0) < TITLE_MATCH_MIN:
        reasons.append("title_not_found")
    nav = navigation_share(text)
    storm = bool(STORM_RE.search(text))
    # Short lines alone are not a problem (a list of victims, of school
    # closings); with the headline missing from the body they are a page of
    # links around an article that was not extracted.
    if nav >= NAVIGATION_MAX and (in_text or 0) < TITLE_IN_TEXT_MIN:
        reasons.append("navigation_heavy")
    # Headline missing and no storm anywhere: another article altogether.
    if "title_not_found" in reasons and not storm:
        reasons.append("different_article"); fatal = True
    if fatal:
        quality = "unusable"
    elif {"title_not_found", "navigation_heavy",
          "near_same_text_as_other_citation"} & set(reasons):
        quality = "doubtful"
    else:
        quality = "good"
    return {"text_quality": quality, "quality_reasons": "|".join(reasons),
            "title_in_text": in_text, "title_match": match, "navigation_share": nav,
            "mentions_storm": storm}


# ── overlap between the fetched texts ────────────────────────────────────────
def overlaps(texts: dict[str, str], *, sample: int = 1, max_df: int = 25
             ) -> dict[tuple[str, str], tuple[float, float]]:
    """Two-way shingle overlap for every pair of texts that share any.

    Returns ``{(a, b): (share of a in b, share of b in a)}`` with ``a < b``.
    Shingles found in more than ``max_df`` texts (site footers, disclaimers)
    are ignored: they say two pages come from one site, not one story.
    """
    sets = {k: rc.shingles(t, sample=sample) for k, t in texts.items() if t}
    index: dict[int, list[str]] = defaultdict(list)
    for key, sh in sets.items():
        for h in sh:
            index[h].append(key)
    shared: dict[tuple[str, str], int] = defaultdict(int)
    for keys in index.values():
        if len(keys) < 2 or len(keys) > max_df:
            continue
        keys = sorted(keys)
        for i, a in enumerate(keys):
            for b in keys[i + 1:]:
                shared[(a, b)] += 1
    return {(a, b): (round(n / len(sets[a]), 3), round(n / len(sets[b]), 3))
            for (a, b), n in shared.items() if sets[a] and sets[b]}


class _Union:
    def __init__(self, items: Iterable[str]):
        self.parent = {i: i for i in items}

    def find(self, x: str) -> str:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def join(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def story_groups(keys: list[str], titles: dict[str, str], dates: dict[str, str],
                 pairs: dict[tuple[str, str], tuple[float, float]],
                 exclude: set[str] = frozenset()) -> dict[str, tuple[str, str]]:
    """``{key: (root key, how it joined)}``: one root per story.

    Two articles are one story when they carry the same headline (five words
    or more) on the same day, or when the shorter text's shingles are at least
    ``STORY_OVERLAP`` inside the longer one and the dates are within
    ``STORY_DAYS`` (or one is undated). ``exclude`` (walls, site fronts) never
    joins anything.
    """
    import datetime as dt

    u = _Union(keys)
    how: dict[str, str] = {}
    by_title: dict[str, list[str]] = defaultdict(list)
    for k in keys:
        norm = " ".join(_WORD.findall(str(titles.get(k, "")).lower()))
        if k not in exclude and len(norm.split()) >= 5 and dates.get(k):
            by_title[f"{norm}|{dates[k]}"].append(k)
    for group in by_title.values():
        for other in group[1:]:
            u.join(group[0], other)
            how[group[0]] = how[other] = "same_title_same_day"

    def _close(a: str, b: str) -> bool:
        da, db = dates.get(a), dates.get(b)
        if not da or not db:
            return True
        return abs((dt.date.fromisoformat(da) - dt.date.fromisoformat(db)).days) <= STORY_DAYS

    for (a, b), (ab, ba) in pairs.items():
        if a in exclude or b in exclude:
            continue
        if max(ab, ba) >= STORY_OVERLAP and _close(a, b):
            u.join(a, b)
            how.setdefault(a, "shared_text"); how.setdefault(b, "shared_text")
    return {k: (u.find(k), how.get(k, "")) for k in keys}

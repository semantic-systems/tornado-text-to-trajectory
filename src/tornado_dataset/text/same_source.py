"""Which official texts of one tornado are edits of the same account.

A tornado's official texts are rarely independent. The survey statement (PNS)
is written first; the Storm Data narrative is often an edited copy of it, the
DAT comments excerpts of it, a survey LSR a short version. Counting them as four
descriptions would overstate the evidence, and a model trained on one and tested
on another would be tested on wording it has seen. This module finds, per
hazard, which texts share their wording, and records the groups.

**What counts as the same account.** Two texts share an account when they share
verbatim wording that is specific to their tornado. That is reuse of *wording*,
not of facts: independent descriptions of one tornado share facts, place names
and stock phrases, but rarely identical runs of words found nowhere else. The
idea is that of text-reuse detection in journalism (the METER corpus, Clough et
al. 2002) and of document containment (Broder 1997). Paraphrase is not detected.

**Tornado-specific wording.** Texts are lower-cased and split into word tokens
("EF-1" and "EF 1" become "ef1"). A run of ``k`` consecutive tokens shared by
two texts is evidence of copying only when it is rare in the texts of *other*
tornadoes: found in fewer than ``min_hazards - 1`` hazards besides the pair's
own. For two texts of one hazard that is fewer than ``min_hazards`` hazards in
all. A run found in the texts of three or more tornadoes is a phrase of the
language or a formula of the office ("an nws storm survey found that an ef1
tornado began"), not a trace of one account. Each text counts for one hazard,
an LSR within reach of several for the nearest, so that one LSR does not count
as several tornadoes. One other hazard is allowed because the hazard list holds
a few pieces and duplicates of one tornado.

**Link.** Two texts of one hazard are linked when at least ``min_shared`` of
their tokens lie in specific runs they share (counted in both texts, the lower
count used). ``coverage(A, B)`` is the share of A's specific tokens that do. It
is asymmetric (an excerpt is covered by its source, not the reverse),
indifferent to sentence order, and one edit breaks only the runs overlapping it.
It measures how much is shared, and decides nothing.

**Calibration, without hand labels.** ``min_shared`` is the smallest value from
a floor of two runs' worth (so one shared phrase never links) at which few pairs
of texts that are *not* copies would be linked. Two comparison sets stand in
for such pairs, each text of a within-hazard pair paired with a stand-in of the
other's source type and office:

* *other episode*, same year: no copy, but also no shared topic. This gives a
  lower bound on false links.
* *same episode*, another hazard: the same day, office and weather, with the
  office's templates of that day. It also holds real copies, between pieces of
  one tornado and through LSRs linked to the wrong tornado. This gives an upper
  bound. Texts identical to the kept text are excluded, as the same text
  attached to two hazards.

A comparison pair's texts belong to two hazards, so a run it shares is already
in two; it is held to the same rule (at most one hazard besides its own), not
to a stricter one. Multiplied by the number of within-hazard pairs, the two
rates bound the expected number of false links.

**Groups.** Linked texts of one hazard form connected groups: if A and C each
excerpt a different part of B, all three go back to one account. A group is
``bridged`` when some of its members are not linked directly.

**No origin is inferred.** An excerpt, an expansion and a shared unrecorded draft
leave the same evidence. Narratives and DAT comments carry no time, an LSR's time
is the event's, and a hazard has one primary survey statement, so no linked pair
has two publication times to compare. What is recorded is what can be observed:
the member a text is ``contained_in`` (that member covers almost all of it),
and the group's representative. The representative is the member covering most
of the other members' wording, with ties broken by a fixed source order: a
convention, not a claim of origin.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import Iterable

import numpy as np

_TOKEN = re.compile(r"[a-z0-9]+")
_EF = re.compile(r"\b(e?f)[\s-]+(\d|u)\b")
_SENTENCE = re.compile(r"(?<=[.!?])\s+|\.{3,}\s*")
_NUMBER = re.compile(r"\d+(?:\.\d+)?")

# Ties between equally complete versions go to the earlier type in this list: a
# convention for "which version to show", not a statement of origin.
SOURCE_ORDER = ("pns", "storm_events_narrative", "dat_comment", "lsr")


def tokens(text: str) -> list[str]:
    """Lower-case word tokens, with the EF/F rating written as one token."""
    return _TOKEN.findall(_EF.sub(r"\1\2", str(text or "").lower()))


_SPAN = re.compile(r"\b(e?f)[\s-]+(\d|u)\b|[a-z0-9]+")


def token_spans(text: str) -> list[tuple[str, int, int]]:
    """``tokens(text)`` with each token's character span in ``text`` (for display)."""
    out = []
    for m in _SPAN.finditer(str(text or "").lower()):
        tok = m.group(1) + m.group(2) if m.group(1) else m.group()
        out.append((tok, m.start(), m.end()))
    return out


def runs(toks: list[str], k: int) -> list[int]:
    """The ``k``-token runs of a text, hashed, by position."""
    return [hash(tuple(toks[i:i + k])) for i in range(len(toks) - k + 1)]


def hazard_counts(run_sets: Iterable[tuple[set[int], Iterable[str]]]) -> dict[int, int]:
    """For each run, the number of distinct hazards whose texts contain it.

    ``run_sets`` yields each text's runs with the hazard(s) it counts for.
    """
    by_hazard: dict[str, set[int]] = {}
    for rs, hazards in run_sets:
        for h in hazards:
            by_hazard.setdefault(h, set()).update(rs)
    counts: dict[int, int] = {}
    for rs in by_hazard.values():
        for r in rs:
            counts[r] = counts.get(r, 0) + 1
    return counts


def common_runs(counts: dict[int, int], min_hazards: int | None) -> set[int]:
    """Runs in the texts of at least ``min_hazards`` hazards; ``None``: none are."""
    if min_hazards is None:
        return set()
    return {r for r, n in counts.items() if n >= min_hazards}


@dataclass
class Profile:
    """A text reduced to what the comparison needs."""
    n_tokens: int
    runs: list[int]            # hashed k-runs by position
    specific: np.ndarray       # per run: specific to few hazards
    run_set: frozenset[int]    # the specific runs
    k: int
    n_specific: int            # tokens inside at least one specific run


def profile(text: str, k: int, common: set[int] | frozenset[int]) -> Profile:
    toks = tokens(text)
    rs = runs(toks, k)
    specific = np.array([r not in common for r in rs], dtype=bool)
    inside = np.zeros(len(toks), dtype=bool)
    for i in np.flatnonzero(specific):
        inside[i:i + k] = True
    return Profile(len(toks), rs, specific,
                   frozenset(r for r, s in zip(rs, specific) if s), k, int(inside.sum()))


def covered(a: Profile, b: Profile) -> int:
    """A's tokens inside a specific run that also occurs in B."""
    if not a.n_specific or not b.run_set:
        return 0
    mask = np.zeros(a.n_tokens, dtype=bool)
    for i, (r, s) in enumerate(zip(a.runs, a.specific)):
        if s and r in b.run_set:
            mask[i:i + a.k] = True
    return int(mask.sum())


@dataclass
class Score:
    a_shared: int              # A's tokens in runs shared with B
    b_shared: int
    a_specific: int
    b_specific: int

    @property
    def a_in_b(self) -> float:
        return self.a_shared / self.a_specific if self.a_specific else 0.0

    @property
    def b_in_a(self) -> float:
        return self.b_shared / self.b_specific if self.b_specific else 0.0

    @property
    def shared(self) -> int:
        """Shared tokens, the lower of the two counts (a repeated run counts once)."""
        return min(self.a_shared, self.b_shared)


def compare(a: Profile, b: Profile) -> Score:
    return Score(covered(a, b), covered(b, a), a.n_specific, b.n_specific)


def comparable(p: Profile, min_shared: int) -> bool:
    """Whether a text has enough specific tokens to be linked at all."""
    return p.n_specific >= min_shared


def choose_min_shared(other: Iterable[int], same: Iterable[int], floor: int,
                      target_other: float, target_same: float, ceiling: int = 40
                      ) -> tuple[int, str]:
    """Smallest ``min_shared`` from ``floor`` meeting both comparison targets.

    Returns the value and how it was decided: ``calibrated``, or ``floor`` when
    there are too few comparison pairs to measure the target rates.
    """
    other, same = np.asarray(list(other)), np.asarray(list(same))
    if len(other) < 1 / target_other or len(same) < 1 / target_same:
        return floor, "floor_too_few_comparison_pairs"
    for m in range(floor, ceiling + 1):
        if (other >= m).mean() <= target_other and (same >= m).mean() <= target_same:
            return m, "calibrated"
    return ceiling, "ceiling"


def stand_ins(pairs: list[tuple[str, str]], meta: dict[str, dict], rng: random.Random,
              scope: str, tries: int = 20) -> list[tuple[str, str, str]]:
    """For each pair, each text with a random stand-in for the other.

    The stand-in has the replaced text's source type and office and is linked to
    none of the kept text's hazards. ``scope="other_episode"``: same year, none
    of the kept text's episodes. ``scope="same_episode"``: one of the kept text's
    episodes, with wording not identical to it. Returns
    ``(kept, stand_in, replaced)``. ``meta[uid]`` holds ``source_type``,
    ``office``, ``year``, ``episodes``, ``hazards``, ``body_key`` and
    ``comparable``.
    """
    pool: dict[tuple, list[str]] = {}
    for u in sorted(meta):
        m = meta[u]
        if not (m["comparable"] and m["office"]):
            continue
        if scope == "other_episode":
            pool.setdefault((m["source_type"], m["office"], m["year"]), []).append(u)
        else:
            for e in sorted(m["episodes"]):
                pool.setdefault((m["source_type"], m["office"], e), []).append(u)
    out = []
    for a, b in pairs:
        for kept, replaced in ((a, b), (b, a)):
            k, r = meta[kept], meta[replaced]
            if scope == "other_episode":
                candidates = pool.get((r["source_type"], r["office"], k["year"]), [])
            else:
                candidates = [c for e in sorted(k["episodes"])
                              for c in pool.get((r["source_type"], r["office"], e), [])]
            if not candidates:
                continue
            for _ in range(tries):
                c = rng.choice(candidates)
                m = meta[c]
                if m["hazards"] & k["hazards"]:
                    continue
                if scope == "other_episode" and m["episodes"] & k["episodes"]:
                    continue
                if scope == "same_episode" and m["body_key"] == k["body_key"]:
                    continue
                out.append((kept, c, replaced))
                break
    return out


def groups(members: list[str], links: Iterable[tuple[str, str]]) -> dict[str, int]:
    """Connected components: ``uid -> group number``."""
    parent = {m: m for m in members}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in links:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    roots: dict[str, int] = {}
    return {m: roots.setdefault(find(m), len(roots)) for m in sorted(members)}


def order_key(source_type: str, n_specific: int, uid: str) -> tuple:
    rank = SOURCE_ORDER.index(source_type) if source_type in SOURCE_ORDER else len(SOURCE_ORDER)
    return (rank, -n_specific, uid)


# ── recall: copies with known edits ────────────────────────────────────────

def sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE.split(str(text or "")) if s and s.strip()]


def derive(text: str, kind: str, rng: random.Random, *, other: str = "",
           vocabulary: list[str] | None = None) -> str | None:
    """An edited copy of ``text``; ``None`` when the edit does not apply.

    ``truncate_170`` cuts at 170 characters and appends an office tag, as SPC
    does with LSR remarks; ``one_sentence`` keeps one sentence of at least eight
    words, as DAT comments excerpt the survey; ``drop_sentence``, ``reorder``;
    ``numbers`` changes every number; ``insert_sentence`` adds a sentence of an
    unrelated text; ``substitute_<pct>`` replaces that share of words at random,
    rewording at which verbatim reuse fades out.
    """
    sents = sentences(text)
    if kind == "truncate_170":
        if len(text) <= 200:
            return None
        return text[:170].rsplit(" ", 1)[0] + " (XXX)"
    if kind == "one_sentence":
        long = [s for s in sents if len(s.split()) >= 8]
        return rng.choice(long) if len(long) >= 2 else None
    if kind == "drop_sentence":
        if len(sents) < 3:
            return None
        i = rng.randrange(len(sents))
        return ". ".join(sents[:i] + sents[i + 1:])
    if kind == "reorder":
        if len(sents) < 3:
            return None
        shuffled = sents[:]
        while shuffled == sents:
            rng.shuffle(shuffled)
        return ". ".join(shuffled)
    if kind == "numbers":
        if not _NUMBER.search(text):
            return None
        return _NUMBER.sub(lambda m: str(int(float(m.group()) * 2 + 1)), text)
    if kind == "insert_sentence":
        foreign = [s for s in sentences(other) if len(s.split()) >= 8]
        if not foreign or len(sents) < 2:
            return None
        i = rng.randrange(len(sents) + 1)
        return ". ".join(sents[:i] + [rng.choice(foreign)] + sents[i:])
    if kind.startswith("substitute_"):
        share = int(kind.split("_")[1]) / 100
        vocab = vocabulary or ["word"]
        return " ".join(rng.choice(vocab) if rng.random() < share else w
                        for w in str(text).split())
    raise ValueError(kind)


DERIVATIONS = ("truncate_170", "one_sentence", "drop_sentence", "reorder", "numbers",
               "insert_sentence", "substitute_5", "substitute_10", "substitute_20",
               "substitute_30")

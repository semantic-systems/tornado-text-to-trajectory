"""Relevance labelling for the LexisNexis full-text corpus.

Same method as the Media Cloud filter (stage 30) and the same label vocabulary,
so the two corpora stay comparable for the overlap study — everything shared
lives in :mod:`tornado_dataset.text.labelling`. What differs is what a row looks
like, and it differs enough to change three design decisions.

What this corpus is
-------------------
========================================== ==========
Export rows                                    24,917
Unique bodies (the labelling unit)             20,138
``textref_uid`` (the downstream join key)      22,896
Body length                    median 540 words, 21.3M total
``tornad*`` in body / first 150 words / headline   99.8% / 81.8% / 49.9%
Articles mentioning a tornado exactly **once**      17.1%
Press-release and financial wire                    20.6%
========================================== ==========

1. **Full body text is available**, so the headline under-determination that made
   ``UNCLEAR`` load-bearing in stage 30 largely disappears here. If ``UNCLEAR``
   stays common in this corpus, that is a signal something is wrong with the
   evidence window or the prompt — not a fact about the corpus.

2. **The hard question is aboutness, not detection.** 17.1% of articles mention a
   tornado exactly once: a lawsuit over failed sirens, a politician's speech,
   and literally *"The Week contest: Tornado wedding"*, a caption competition.
   Every one of them is *about* something else. No keyword separates them from a
   report, and the tornado they mention is usually real, so this is not a
   relevance question but a centrality question. It gets its own flag,
   ``is_passing_mention``, rather than a primary category, so the primary axis
   stays aligned with Media Cloud's.

3. **A fifth of the corpus is press-release and wire boilerplate** — CE Noticias
   Financieras English, States News Service, US Fed News, Targeted News, PR
   Newswire, Business Wire — a content class Media Cloud did not contain, and
   structurally unlike journalism. Hence ``is_press_release``.

LexisNexis's own index terms would have helped, but the Uni export strips them:
``subject``, ``geographic`` and ``industry`` are 0% populated across all 24,917
rows, so there is no controlled vocabulary to exploit and the body is all there
is.
"""

from __future__ import annotations

import hashlib
import re
from typing import Sequence

import numpy as np
import pandas as pd

from .labelling import (                                          # noqa: F401
    EVENT, PROSPECTIVE, NOT_TORNADO_EVENT, UNCLEAR, PRIMARY_LABELS,
    BASE_FLAGS, build_schema, consistency_scores, enforce_protect_invariant,
    label_summary, parse_llm_answers, pick_representatives, promote_to_group,
    propagate, restore_dtypes,
)
from .linking import STATE_ABBREV

# Base flags plus the three this corpus needs.
FLAGS = [*BASE_FLAGS, "is_passing_mention", "is_press_release", "is_roundup"]
LLM_SCHEMA = build_schema(FLAGS)

# ── regexes ─────────────────────────────────────────────────────────────────
TORNADO_RE = re.compile(
    r"\btornad\w*|\btwister\b|\bfunnel clouds?\b|\bwaterspouts?\b|\bef-? ?[0-5]\b", re.I)
# The protect rule, transcribed from the owner's review of the Media Cloud
# corpus. It is evaluated on headline + lede only — see `add_rule_cues`.
PROTECT_RE = re.compile(
    r"\btornad\w*|\bsevere weather\b|\binclement weather\b|\bwinds?\b|"
    r"\bstorm\w*|\bflooding\b", re.I)
POWER_OUTAGE_RE = re.compile(r"\bpower outage", re.I)
POWER_CONTEXT_RE = re.compile(r"\bweather\b|\bstorms?\b|\bwinds?\b|\btornad\w*", re.I)

# Outlets that publish press releases and syndicated financial copy rather than
# reporting. Used as an audit cue; the model reports `is_press_release` itself.
PRESS_RELEASE_SOURCE_RE = re.compile(
    r"news service|us fed news|targeted news|states news|newstex|"
    r"noticias financieras|pr newswire|business wire|globe newswire|"
    r"press release|marketwired|accesswire|newswire", re.I)

EVENT_RE = re.compile(
    r"\btouch(?:ed|es)? down\b|\bripped through\b|\btore through\b|"
    r"\bswept through\b|\bdamag\w*|\bdestroy\w*|\bkill\w*|\binjur\w*|"
    r"\bfatalit\w*|\bcasualt\w*|\bdeath toll\b|\baftermath\b|\bdebris\b|"
    r"\bef-? ?[0-5]\b|\bsurvivors?\b|\bstate of emergency\b", re.I)
PROSPECT_RE = re.compile(
    r"\bwatch(?:es)? issued\b|\bwarning(?:s)? issued\b|\bforecast\w*|"
    r"\brisk of\b|\bthreat\b|\bbrac(?:e|es|ing) for\b|\bexpected to\b|"
    r"\bpotential\b|\bon alert\b|\bprepare for\b", re.I)
RETRO_RE = re.compile(
    r"\ba look back\b|\byears? (?:ago|after|later|since)\b|\banniversar\w*|"
    r"\bon this day\b|\bdecades? (?:ago|later)\b|\bback in (?:19|20)\d\d\b", re.I)
FACT_CHECK_RE = re.compile(
    r"\bfact[\s-]?check\w*|\bdebunk\w*|\bai[-\s]generated\b|\bmiscaption\w*|"
    r"\bdeepfake\b|\bhoax\b|\bfalsely\b", re.I)
NONMET_CONTEXT_RE = re.compile(
    r"\btornado cash\b|\bcrypto\w*|\broller ?coaster\b|\bmascot\b|"
    r"\b(?:basketball|football|baseball|hockey|soccer|softball|volleyball)\b|"
    r"\bvarsity\b|\bplayoffs?\b|\btournament\b", re.I)

_STATE_RE = re.compile(
    r"\b(" + "|".join(sorted(STATE_ABBREV, key=len, reverse=True)) + r")\b", re.I)

WS_RE = re.compile(r"\s+")


# ── evidence windows ────────────────────────────────────────────────────────
# Sending whole bodies is 28.8M tokens and mostly wasted. Blind prefix truncation
# is cheap but 18.2% of articles never say "tornad*" in their first 150 words, so
# a prefix can miss the only evidence that matters. `windows` shows the model the
# *context of each mention* instead, which is exactly what the aboutness question
# needs. Which mode is actually best is measured by the `window` subcommand of
# scripts/32_filter_lexisnexis.py rather than assumed here.
EVIDENCE_MODES = ("windows", "lede150", "prefix400", "full2000")

WINDOW_RADIUS = 40      # words either side of a mention
MAX_WINDOWS = 6         # windows per article, spread across the body
LEDE_WORDS = 80         # always included, as an anchor
FULL_CAP = 2000         # word cap for the `full2000` ablation arm
ELLIPSIS = " […] "


def _words(text: str) -> list[str]:
    return str(text or "").split()


def mention_positions(words: Sequence[str]) -> list[int]:
    """Word indices whose token matches the tornado vocabulary."""
    return [i for i, w in enumerate(words) if TORNADO_RE.search(w)]


def _merge(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge overlapping or touching (start, end) spans."""
    out: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        if out and start <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], end))
        else:
            out.append((start, end))
    return out


def evidence_windows(body: str, radius: int = WINDOW_RADIUS,
                     max_windows: int = MAX_WINDOWS,
                     lede_words: int = LEDE_WORDS) -> tuple[str, int]:
    """Lede anchor plus context around the tornado mentions.

    Returns ``(text, n_mentions)``. When there are more mentions than
    ``max_windows``, the kept ones are spread evenly over the article rather than
    taken from the front: an article's later mentions are what distinguish a
    round-up or a retrospective from a single-event report, and taking the first
    six would systematically hide them.

    Omissions are marked with an ellipsis so the model can tell that it is seeing
    excerpts and does not read two distant sentences as adjacent.
    """
    words = _words(body)
    if not words:
        return "", 0
    hits = mention_positions(words)
    spans = [(0, min(lede_words, len(words)))]
    if hits:
        chosen = hits
        if len(hits) > max_windows:
            picks = np.linspace(0, len(hits) - 1, max_windows).round().astype(int)
            chosen = [hits[i] for i in sorted(set(picks.tolist()))]
        spans += [(max(0, h - radius), min(len(words), h + radius + 1)) for h in chosen]

    merged = _merge(spans)
    parts, cursor = [], 0
    for start, end in merged:
        if start > cursor:
            parts.append(ELLIPSIS.strip())
        parts.append(" ".join(words[start:end]))
        cursor = end
    if cursor < len(words):
        parts.append(ELLIPSIS.strip())
    return " ".join(parts), len(hits)


def render_evidence(row: pd.Series | dict, mode: str = "windows") -> tuple[str, int]:
    """Produce the body evidence for one article under the given mode."""
    body = str((row.get("body") if isinstance(row, dict) else row["body"]) or "")
    words = _words(body)
    n = len(mention_positions(words))
    if mode == "windows":
        return evidence_windows(body)
    if mode == "lede150":
        return " ".join(words[:150]) + (ELLIPSIS.strip() if len(words) > 150 else ""), n
    if mode == "prefix400":
        return " ".join(words[:400]) + (ELLIPSIS.strip() if len(words) > 400 else ""), n
    if mode == "full2000":
        return " ".join(words[:FULL_CAP]) + (ELLIPSIS.strip() if len(words) > FULL_CAP else ""), n
    raise ValueError(f"unknown evidence mode {mode!r}; expected one of {EVIDENCE_MODES}")


# ── deduplication ───────────────────────────────────────────────────────────
def body_key(body: pd.Series) -> pd.Series:
    """Content-derived identity for a body, stable across processes.

    ``lexisnexis.add_duplicate_flags`` already groups identical bodies, but it
    keys on ``factorize`` order, which is only meaningful within one read of the
    corpus. ``apply`` joins labels written by an earlier process, so it needs a
    key derived from the text itself.
    """
    normalised = (body.fillna("").astype(str).str.lower()
                      .str.replace(r"\W+", " ", regex=True).str.strip())
    return normalised.map(
        lambda t: hashlib.sha1(t.encode("utf-8")).hexdigest()[:16] if t else "empty")


def add_dedup_groups(df: pd.DataFrame) -> pd.DataFrame:
    """Group identical bodies and pick the richest member of each group.

    Wire copy is republished verbatim by many outlets — one group here holds up
    to 37 articles — and whether a body describes a real tornado does not depend
    on which outlet ran it. The representative is the *longest* body in the
    group, which for near-ties means the copy that kept the most text.

    Known limitation: this is exact identity after normalisation, the cheap
    variant of ``LexisNexisTools::lnt_similarity``. Lightly edited wire copy is
    not caught, so the group count is an upper bound on distinct stories.
    """
    out = df.copy()
    out["body_key"] = body_key(out["body"])
    out["dup_count"] = out.groupby("body_key")["body_key"].transform("size")
    out["is_representative"] = pick_representatives(
        out, "body_key", out["body"].fillna("").astype(str).str.len())
    return out


# ── audit cues ──────────────────────────────────────────────────────────────
def lede(df: pd.DataFrame, words: int = LEDE_WORDS) -> pd.Series:
    return df["body"].fillna("").astype(str).str.split().str[:words].str.join(" ")


def add_rule_cues(df: pd.DataFrame) -> pd.DataFrame:
    """Attach regex cues and the protect flag as *descriptive* columns.

    None of these decide a label. They exist to stratify validation, to break the
    report down by evidence type, and as a drift monitor — a sharp change in
    cue-versus-model agreement is how a prompt regression would announce itself.
    """
    out = df.copy()
    headline = out["headline"].fillna("").astype(str)
    body = out["body"].fillna("").astype(str)
    source = out["source"].fillna("").astype(str)
    head_lede = headline + " . " + lede(out)

    # The protect rule is evaluated on headline + lede, never the full body:
    # across 540 median words virtually every article contains "storm", so a
    # full-body protect rule is vacuously true and stops being a guard at all.
    protected = head_lede.str.contains(PROTECT_RE) | (
        head_lede.str.contains(POWER_OUTAGE_RE) & head_lede.str.contains(POWER_CONTEXT_RE))
    if "body_key" in out.columns:
        protected = promote_to_group(protected, out["body_key"])
    out["protected"] = protected

    out["n_mentions"] = body.map(lambda b: len(mention_positions(_words(b))))
    out["cue_tornado_headline"] = headline.str.contains(TORNADO_RE)
    out["cue_single_mention"] = out["n_mentions"] <= 1
    out["cue_event"] = head_lede.str.contains(EVENT_RE)
    out["cue_prospect"] = head_lede.str.contains(PROSPECT_RE)
    out["cue_retrospective"] = head_lede.str.contains(RETRO_RE)
    out["cue_fact_check"] = head_lede.str.contains(FACT_CHECK_RE)
    out["cue_nonmet_context"] = head_lede.str.contains(NONMET_CONTEXT_RE)
    out["cue_press_release"] = source.str.contains(PRESS_RELEASE_SOURCE_RE)
    # A round-up names many places; the linker caps an article at
    # LINK_MAX_PER_ARTICLE=12 links, so knowing which articles are round-ups
    # explains fan-out rather than leaving it a surprise.
    out["n_states"] = body.map(lambda b: len(set(m.lower() for m in _STATE_RE.findall(b))))
    out["cue_roundup"] = out["n_states"] >= 4
    return out


# ── the prompt ──────────────────────────────────────────────────────────────
LLM_SYSTEM = (
    "You label news articles for a scientific tornado dataset. "
    "You answer with one JSON object and nothing else."
)

LLM_PROMPT = """\
Classify this news article for a tornado dataset. You see the headline, the
publication details, and excerpts from the article body. Where text has been
omitted it is marked […] — do not assume omitted text supports anything.

Choose exactly one primary category:

EVENT              The article reports that a tornado actually occurred, and that
                   occurrence is what the article is about — touchdown, damage,
                   casualties, aftermath, clean-up, recovery, a damage survey, or
                   an EF rating.
PROSPECTIVE        Only a forecast, watch, warning, risk or threat. No tornado has
                   occurred yet at the time of writing.
NOT_TORNADO_EVENT  Not a report of a tornado occurring: safety advice, an
                   explainer, opinion, a different hazard, policy, insurance or
                   business news, "Tornado" as the name of a team, band or
                   product — or an article that merely *mentions* a tornado while
                   being about something else.
UNCLEAR            The excerpts genuinely do not settle it.

The decisive question for this corpus is what the article is ABOUT. Many articles
refer to a real tornado only in passing — a lawsuit over storm sirens, an
obituary, a politician's speech, a charity fundraiser, a sports report. Those are
NOT_TORNADO_EVENT with is_passing_mention true, even though the tornado is real.
An article about the aftermath, recovery or investigation of a specific tornado
is EVENT, not a passing mention.

Set these flags independently of the category, each true or false:

is_outbreak        several tornadoes, or a named outbreak.
is_retrospective   an anniversary, history or "look back" piece about a tornado
                   from an earlier year, rather than current coverage.
is_fact_check      a fact-check or debunk of fabricated, AI-generated or
                   miscaptioned tornado material.
nonmet_sense       "Tornado" is used as a name or metaphor, not as weather.
other_hazard       centred on a hurricane, flood, wildfire or winter storm.
is_passing_mention a tornado is referred to, but the article is about something
                   else.
is_press_release   a press release, government announcement or corporate wire
                   item rather than journalism.
is_roundup         covers many separate events or places rather than one.

conf               your confidence in the primary category, 0.0 to 1.0.

HEADLINE: {headline}
SOURCE: {source}
DATE: {date}
{highlight}ARTICLE: {evidence}
"""


def build_prompts(df: pd.DataFrame, mode: str = "windows") -> tuple[list[str], list[int]]:
    """Render one prompt per row; also returns the mention count per row."""
    prompts, mentions = [], []
    for _, row in df.iterrows():
        evidence, n = render_evidence(row, mode)
        highlight = str(row.get("highlight") or "").strip()
        highlight = f"SUMMARY: {highlight[:400]}\n" if highlight else ""
        date = str(row.get("pub_date") or "")[:10]
        prompts.append(LLM_PROMPT.format(
            headline=str(row.get("headline") or "")[:300],
            source=str(row.get("source") or "")[:120],
            date=date, highlight=highlight, evidence=evidence))
        mentions.append(n)
    return prompts, mentions

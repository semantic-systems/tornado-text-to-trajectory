"""Filter the Media Cloud export down to articles reporting *actual* tornadoes.

The export (``data/raw/media_cloud/national_state_local_2010-2025.csv``,
491,432 rows, 2010-2025) was collected with the full-text query
``tornado* AND (wind? OR storm? OR rain? OR damage? OR emergency)``. Two facts
about it shape everything here:

* **Only headline and URL are available** — no body, no lead paragraph. Every row
  mentions a tornado *somewhere*, but only 29.5% say so in the headline or URL.
  A headline reading "Storm rips through Marshall County" may or may not be a
  tornado report, and from the headline there is no way to tell.
* **45.8% of the export is syndicated repeat copy** — one wire headline ran on up
  to 370 outlets in a single day.

How labelling works, and why
----------------------------
Every distinct headline is labelled by an LLM. There is no rule-based decision
stage and no trained classifier, and both were removed on evidence rather than
taste:

*The rules* were measured against LLM labels on a stratified sample of 385
headlines (:mod:`scripts/18_filter_media_cloud.py` history, 2026-08). Collapsed
to the decision that matters — tornado event or not — the two agreed 93.4% after
post-stratifying to corpus frequency, but the disagreement was almost entirely
one-directional: the rules called ~1,615 headlines an event that the LLM did not,
and *missed ~14,106* that the LLM did call events. The rules recovered roughly
70% of the event set. That recall gap existed only to save inference the project
no longer needs to save.

*The classifier* was trained on LLM labels, which makes it a lossy approximation
of the LLM with the LLM's accuracy as its ceiling. On a local, already-running
GPU the whole corpus labels in about 2.5 hours, so there is nothing to distil.

What survives from the rules is everything that was never a decision: the protect
invariant (below), and the regex cues, which are still computed as **audit
columns** for stratifying validation, for the report, and as a drift monitor
against the model.

Label design
------------
An exclusive **primary** label carries the decision; independent **flags** carry
the detail. The earlier design used nine mutually-exclusive categories and that
was a mistake — "Opinion: how to prepare for hurricane season" is simultaneously
opinion, advisory and other-hazard, so forcing one choice manufactures
disagreement and makes an inter-annotator κ uninterpretable.

``EVENT``              headline/URL indicate a tornado actually occurred.
``PROSPECTIVE``        forecast, watch, warning or risk only; nothing has occurred.
``NOT_TORNADO_EVENT``  clearly not a report of a tornado occurring.
``UNCLEAR``            headline and URL genuinely do not settle it.

``UNCLEAR`` is load-bearing. The corpus's central difficulty is that headlines
under-determine the answer, and without an abstention the model must guess —
turning a knowable quantity into a silent error. With it, "cannot be decided from
a headline" becomes a measured stratum, which is both an honest denominator for
any recall claim and the obvious population to hand a human annotator.

Flags: ``is_outbreak``, ``is_retrospective`` (an anniversary or history piece —
a real 1925 tornado is an event, but not one this dataset can link),
``is_fact_check``, ``nonmet_sense`` ("Tornado" as a team, band or product), and
``other_hazard``.

The protect invariant
---------------------
From the project owner's review of the corpus: a row containing ``tornado*``,
``severe weather``, ``inclement weather``, ``winds``, ``storm*``, ``flooding``,
or a weather word together with ``power outage``, in the headline *or* the URL,
is about weather. It is enforced here as a guard on the ``nonmet_sense`` flag —
the model never gets the last word on it — and re-checked on what is written to
disk. Protection is promoted to the *headline group*, because labels are computed
per distinct headline and propagated to syndicated copies whose URLs differ.
"""

from __future__ import annotations

import re
from typing import Iterable

import numpy as np
import pandas as pd

# The label vocabulary, the protect invariant, answer parsing and the
# self-consistency estimator are shared with the LexisNexis filter and live in
# `labelling`. They are re-exported here so this module stays the single import
# for anything working with the Media Cloud corpus.
from .labelling import (                                          # noqa: F401
    EVENT, PROSPECTIVE, NOT_TORNADO_EVENT, UNCLEAR, PRIMARY_LABELS,
    BASE_FLAGS, build_schema, consistency_scores, enforce_protect_invariant,
    label_summary, parse_llm_answers, pick_representatives, promote_to_group,
    propagate, restore_dtypes,
)

# Media Cloud reports exactly the base flags — it has no corpus-specific ones.
FLAGS = list(BASE_FLAGS)

# ── protect rule ────────────────────────────────────────────────────────────
# `winds?` also matches the singular, so "wind damage" is protected as well as
# "winds"; over-protecting is the safe error, since protection only ever forbids
# one flag.
PROTECT_RE = re.compile(
    r"\btornad\w*|\bsevere weather\b|\binclement weather\b|\bwinds?\b|"
    r"\bstorm\w*|\bflooding\b", re.I)
POWER_OUTAGE_RE = re.compile(r"\bpower outage", re.I)
POWER_CONTEXT_RE = re.compile(r"\bweather\b|\bstorms?\b|\bwinds?\b|\btornad\w*", re.I)

# Unambiguous tornado vocabulary the owner's literal list does not name. Kept
# separate so the report can say how many rows the extension rescues, and so
# --literal-protect can switch it off.
TORNADO_SYNONYM_RE = re.compile(
    r"\btwister\b|\bfunnel cloud\b|\bwaterspout\b|\bef-? ?[0-5]\b|\bsupercell\b", re.I)
TORNADO_RE = re.compile(r"\btornad\w*|\btwister\b|\bwaterspout\b|\bef-? ?[0-5]\b", re.I)

# ── audit cues (no longer decide anything) ──────────────────────────────────
ADVISORY_RE = re.compile(
    r"\btips\b|\bplanning\b|\bhow to\b|\bexplained\b|\bresilience\b", re.I)
OPINION_RE = re.compile(r"\bopinion\b|\bop-?ed\b|\beditorial\b|\bcommentary\b", re.I)
HURRICANE_RE = re.compile(r"\bhurricanes?\b|\btropical storm\b|\btropical depression\b", re.I)
EVENT_RE = re.compile(
    r"\btouch(?:ed|es)? down\b|\btouchdown\b|\bripped through\b|\btore through\b|"
    r"\bswept through\b|\bplowed through\b|\bdamag\w*|\bdestroy\w*|\bkill\w*|"
    r"\binjur\w*|\bfatalit\w*|\bcasualt\w*|\bdeath toll\b|\bdead\b|\bvictims?\b|"
    r"\bleveled\b|\bflattened\b|\baftermath\b|\bclean-? ?up\b|\brebuild\w*|"
    r"\brecovery\b|\bsurvey\w*|\bconfirm\w*|\bstruck\b|\bhit by\b|\bdebris\b|"
    r"\bstate of emergency\b|\bdisaster declaration\b|\bsurvivors?\b|"
    r"\bhomes? (?:were )?(?:damaged|destroyed)\b|\bef-? ?[0-5]\b|\btrapped\b|"
    r"\bwreckage\b|\bleft (?:behind )?a trail\b|\brescue\w*", re.I)
PROSPECT_RE = re.compile(
    r"\bwatch(?:es)? issued\b|\bwarning(?:s)? issued\b|\bunder a (?:tornado |severe )?watch\b|"
    r"\bcould (?:hit|impact|bring|see)\b|\bthreat\b|\brisk of\b|\bbrac(?:e|es|ing) for\b|"
    r"\bforecast\w*|\bexpected to\b|\bmay (?:bring|hit|see)\b|\bpotential\b|"
    r"\boutlook\b|\bon alert\b|\bprepare for\b|\bpossible\b|\blikely\b|"
    r"\bahead of\b|\bwhat to expect\b", re.I)
FAKE_RE = re.compile(
    r"\bfact[\s-]?check\w*|\bdebunk\w*|\bdigitally (?:generated|altered)\b|"
    r"\bai[-\s]generated\b|\bmiscaption\w*|\bmisleading\b|\bdeepfake\b|"
    r"\bpurported\w*|\bfalsely\b|\bhoax\b|\bviral (?:video|image|photo)\b", re.I)
OUTBREAK_RE = re.compile(
    r"\boutbreak\b|\bmultiple tornado\w*|\bseveral tornado\w*|\b\d+\s+tornado\w*|"
    r"\btornado\w*\s+(?:touch|confirm|report)|\bswarm\b|\bspate\b", re.I)
RETRO_RE = re.compile(
    r"\ba look back\b|\byears? (?:ago|after|later|since)\b|\banniversar\w*|"
    r"\bremember\w*|\bhistor\w*|\bon this day\b|\bdecades? (?:ago|later)\b|"
    r"\bback in (?:19|20)\d\d\b|\b(?:19[0-9]\d|200\d)\b", re.I)
NONMET_CONTEXT_RE = re.compile(
    r"\btornado cash\b|\bcrypto\w*|\bhonda\b|\byamaha\b|\bsuzuki\b|\bkawasaki\b|"
    r"\bmotorcycle\b|\broller ?coaster\b|\bcasino\b|\bslot machine\b|\bnerf\b|"
    r"\bvideo ?game\b|\balbum\b|\bband\b|\bmixtape\b|"
    r"\b(?:basketball|football|baseball|hockey|soccer|softball|volleyball)\b|"
    r"\bmascot\b|\bvarsity\b|\bplayoffs?\b|\btournament\b|\bcoach\b", re.I)

SLUG_SPLIT_RE = re.compile(r"[-_/+.?=&#%0-9]+")
WS_RE = re.compile(r"\s+")


# ── text preparation ────────────────────────────────────────────────────────
def deslug(url: pd.Series) -> pd.Series:
    """Turn a URL into readable words.

    The slug is often *richer* than the headline: the row titled "August 6th,
    2020:Tornado in Harriston" has ``national-weather-service-confirms-tornado``
    in its URL, and the "confirms" is what decides the label. 6,994 rows carry a
    protect term in the URL that the headline omits entirely.
    """
    return (url.fillna("")
               .str.replace(r"^https?://", " ", regex=True)
               .str.replace(SLUG_SPLIT_RE, " ", regex=True)
               .str.replace(WS_RE, " ", regex=True)
               .str.strip())


def haystack(df: pd.DataFrame) -> pd.Series:
    """Headline + de-slugged URL: everything this stage is allowed to see."""
    return df["title"].fillna("").astype(str) + " . " + deslug(df["url"].astype(str))


def normalise_title(title: pd.Series) -> pd.Series:
    """Key for collapsing syndicated copies of one headline."""
    return (title.fillna("").astype(str).str.lower()
                 .str.replace(r"\s*[|–—-]\s*[a-z0-9. ]{0,24}$", "", regex=True)
                 .str.replace(r"[^\w\s]", " ", regex=True)
                 .str.replace(WS_RE, " ", regex=True)
                 .str.strip())


def add_dedup_groups(df: pd.DataFrame) -> pd.DataFrame:
    """Group identical headlines and pick one representative per group.

    Whether a headline describes a real tornado does not depend on which outlet
    ran it, so each distinct headline is labelled once and the answer propagates
    to its copies. That halves the work and stops one viral headline from
    dominating any distribution computed over the corpus.

    The representative is the copy with the **longest URL slug**, not the first
    row encountered. Copies share a headline but not a URL, and the slug is where
    the deciding word often lives, so this hands the model the most informative
    member of the group for free.
    """
    out = df.copy()
    out["title_norm"] = normalise_title(out["title"])
    # Empty headlines must not collapse into one group; fall back to the URL.
    # The sentinel has to survive a CSV round-trip, because `apply` joins labels
    # back on this key — a NUL byte does not, and silently orphaned exactly the
    # rows it was meant to keep distinct. A colon is safe: `normalise_title`
    # strips every non-word character, so no real key can contain one.
    blank = out["title_norm"] == ""
    out.loc[blank, "title_norm"] = "urlkey:" + out.loc[blank, "url"].astype(str)
    codes, _ = pd.factorize(out["title_norm"])
    out["dup_group"] = codes
    out["dup_count"] = out.groupby("dup_group")["dup_group"].transform("size")

    slug_len = deslug(out["url"].astype(str)).str.len()
    out["is_representative"] = pick_representatives(out, "dup_group", slug_len)
    return out


# ── audit cues + the protect flag ───────────────────────────────────────────
def add_rule_cues(df: pd.DataFrame, literal_protect: bool = False) -> pd.DataFrame:
    """Attach the regex cues and the protect flag as *descriptive* columns.

    None of these decide a label any more. They are kept because they are free,
    interpretable and useful for three things: stratifying the validation sample,
    breaking the report down by evidence type, and monitoring drift — a sharp
    change in cue-vs-model agreement is how a prompt regression or a swapped
    model would announce itself.
    """
    hay = haystack(df)
    title = df["title"].fillna("").astype(str)

    protected = hay.str.contains(PROTECT_RE) | (
        hay.str.contains(POWER_OUTAGE_RE) & hay.str.contains(POWER_CONTEXT_RE))
    synonym = hay.str.contains(TORNADO_SYNONYM_RE)
    if not literal_protect:
        protected = protected | synonym

    out = df.copy()
    # Protection is a property of the headline *group*: only the representative
    # is labelled, and its copies have different URLs, so a per-row flag would
    # let an unprotected representative hand a `nonmet_sense` to a protected
    # sibling. Taking the group maximum can only ever forbid a flag, never
    # invent one, so the direction of the error is the safe one.
    if "dup_group" in out.columns:
        protected = promote_to_group(protected, out["dup_group"])
        synonym = promote_to_group(synonym, out["dup_group"])

    out["protected"] = protected
    out["protect_via_synonym"] = synonym & ~hay.str.contains(PROTECT_RE)
    out["cue_tornado"] = hay.str.contains(TORNADO_RE)
    out["cue_event"] = hay.str.contains(EVENT_RE)
    out["cue_prospect"] = hay.str.contains(PROSPECT_RE)
    out["cue_fake"] = hay.str.contains(FAKE_RE)
    out["cue_outbreak"] = hay.str.contains(OUTBREAK_RE)
    out["cue_retrospective"] = hay.str.contains(RETRO_RE)
    out["cue_nonmet_context"] = hay.str.contains(NONMET_CONTEXT_RE)
    out["cue_advisory"] = title.str.contains(ADVISORY_RE)
    out["cue_opinion"] = title.str.contains(OPINION_RE)
    out["cue_hurricane"] = title.str.contains(HURRICANE_RE)
    return out


# ── the prompt ──────────────────────────────────────────────────────────────
LLM_SYSTEM = (
    "You label news headlines for a scientific tornado dataset. "
    "You answer with one JSON object and nothing else."
)

# The provenance sentence is a *variant*, not a default. Telling the model that
# every item matched a full-text search for "tornado" invites it to assume a
# tornado angle that the headline does not support, and that is the leading
# suspect for the ~11,000 storm-damage headlines where the rules and the model
# most disagreed. Keeping it switchable makes that an ablation we can measure
# rather than a confound we argue about.
PROVENANCE_NOTE = (
    "\nThese items were retrieved by a full-text search for \"tornado\", so the "
    "article mentions a tornado somewhere. A mention is not evidence that a "
    "tornado occurred.\n")

LLM_PROMPT = """\
Classify this news item for a tornado dataset. You can see the headline and the \
URL slug only; the article body is not available to you.{provenance}
Choose exactly one primary category:

EVENT              The headline or URL indicate a tornado actually occurred —
                   touchdown, damage caused by a tornado, casualties, aftermath,
                   clean-up, a damage survey, or an EF rating.
PROSPECTIVE        Only a forecast, watch, warning, risk or threat. Nothing has
                   happened yet.
NOT_TORNADO_EVENT  Clearly not a report of a tornado occurring: safety advice,
                   preparedness, an explainer, opinion or commentary, a different
                   hazard, policy or insurance news, or "Tornado" used as the name
                   of a team, band, film, product or company.
UNCLEAR            The headline and URL genuinely do not settle it.

Choose UNCLEAR rather than guessing. In particular, a headline reporting storm,
wind or hail damage with no indication that a tornado was involved is UNCLEAR,
not EVENT — straight-line winds cause damage too.

Also set these flags independently of the category, each true or false:

is_outbreak       several tornadoes, or a named outbreak.
is_retrospective  an anniversary, history or "look back" piece about a tornado
                  from an earlier year, rather than current coverage.
is_fact_check     a fact-check or debunk of fabricated, AI-generated or
                  miscaptioned tornado imagery.
nonmet_sense      "Tornado" is used as a name or metaphor, not as weather.
other_hazard      the item is centred on a hurricane, flood, wildfire or winter
                  storm.

conf              your confidence in the primary category, 0.0 to 1.0.

HEADLINE: {title}
URL: {url}
DATE: {date}
"""

LLM_SCHEMA = build_schema(FLAGS)


def build_prompts(df: pd.DataFrame, provenance: bool = False) -> list[str]:
    slug = deslug(df["url"].astype(str))
    note = PROVENANCE_NOTE if provenance else "\n"
    return [LLM_PROMPT.format(provenance=note, title=str(t)[:300],
                              url=str(u)[:300], date=str(d)[:10])
            for t, u, d in zip(df["title"].fillna(""), slug, df["publish_date"])]

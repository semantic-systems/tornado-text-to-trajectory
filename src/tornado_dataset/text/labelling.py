"""Corpus-agnostic machinery for LLM relevance labelling of a news corpus.

Two corpora are labelled by the same method and must stay comparable — the
Media Cloud headline export (stage 18) and the LexisNexis full-text export
(stage 19) — so everything that does not depend on *what a row looks like* lives
here: the label vocabulary, answer parsing, the protect invariant, the
deduplicate-label-propagate pattern, and the self-consistency estimator.

What stays in the per-corpus modules is only what differs: the regexes, how a row
becomes prompt text, and the prompt itself.

Label design
------------
An exclusive **primary** label carries the decision; independent **flags** carry
the detail. Nine mutually-exclusive categories were tried first and were a
mistake — "Opinion: how to prepare for hurricane season" is simultaneously
opinion, advisory and other-hazard, so forcing one choice manufactures
disagreement and makes an inter-annotator κ uninterpretable.

``EVENT``              the text indicates a tornado actually occurred.
``PROSPECTIVE``        forecast, watch, warning or risk only; nothing occurred.
``NOT_TORNADO_EVENT``  clearly not a report of a tornado occurring.
``UNCLEAR``            the available evidence genuinely does not settle it.

The vocabulary is deliberately identical across corpora, because the LexisNexis ↔
GDELT ↔ Media Cloud overlap study compares them directly. Corpus-specific
distinctions belong in flags, never in the primary axis.

Temperature
-----------
Labels are produced at **T=0**: classification wants the argmax, and greedy
decoding is what makes a rerun reproducible. vLLM is not bitwise deterministic
even at T=0 — continuous batching changes floating-point reduction order — so the
response cache in :mod:`tornado_dataset.llm`, not the temperature, is what
actually guarantees reproducibility.

Uncertainty is measured at **T=1.0**, the model's unmodified predictive
distribution. Sampling below 1.0 sharpens the very thing being measured, and
*varying* temperature across the k draws would confound the model's uncertainty
with temperature's effect on entropy: the draws would come from different
distributions, so their agreement would estimate nothing well-defined.
"""

from __future__ import annotations

from typing import Iterable, Sequence

import numpy as np
import pandas as pd

# ── primary label vocabulary (exclusive) ────────────────────────────────────
EVENT = "EVENT"
PROSPECTIVE = "PROSPECTIVE"
NOT_TORNADO_EVENT = "NOT_TORNADO_EVENT"
UNCLEAR = "UNCLEAR"

PRIMARY_LABELS = [EVENT, PROSPECTIVE, NOT_TORNADO_EVENT, UNCLEAR]

# Flags every corpus reports. A corpus may extend this list; it may not shorten
# it, so that a flag means the same thing wherever it appears.
BASE_FLAGS = ["is_outbreak", "is_retrospective", "is_fact_check", "nonmet_sense",
              "other_hazard"]

UNCERTAINTY_TEMPERATURE = 1.0
SENSITIVITY_TEMPERATURES = (0.0, 0.3, 0.7, 1.0)


# ── schema ──────────────────────────────────────────────────────────────────
def build_schema(flags: Sequence[str] = tuple(BASE_FLAGS)) -> dict:
    """JSON schema for one labelling answer, for guided decoding."""
    properties: dict[str, dict] = {
        "primary": {"type": "string", "enum": PRIMARY_LABELS},
        **{flag: {"type": "boolean"} for flag in flags},
        "conf": {"type": "number"},
    }
    return {"type": "object", "properties": properties,
            "required": ["primary", *flags, "conf"], "additionalProperties": False}


def parse_llm_answers(answers: Iterable[str | None],
                      flags: Sequence[str] = tuple(BASE_FLAGS)) -> pd.DataFrame:
    """Turn raw model answers into primary + flags + confidence.

    A missing or unparseable answer becomes ``UNCLEAR`` with ``conf`` NaN and
    ``parsed`` False, so a row the model never actually judged is never counted
    as a judgement. Flags default to False rather than NaN because they are
    assertions — absent evidence is not a positive flag.
    """
    from ..llm import extract_json

    valid = set(PRIMARY_LABELS)
    rows = []
    for raw in answers:
        obj = extract_json(raw) or {}
        primary = obj.get("primary")
        primary = primary.strip().upper() if isinstance(primary, str) else None
        ok = primary in valid
        rec: dict[str, object] = {"primary": primary if ok else UNCLEAR, "parsed": ok}
        for flag in flags:
            value = obj.get(flag)
            rec[flag] = bool(value) if isinstance(value, bool) else False
        conf = obj.get("conf")
        rec["conf"] = float(conf) if isinstance(conf, (int, float)) else np.nan
        rows.append(rec)
    return pd.DataFrame(rows)


# ── the protect invariant ───────────────────────────────────────────────────
def enforce_protect_invariant(df: pd.DataFrame, column: str = "nonmet_sense",
                              protected_column: str = "protected") -> int:
    """Guarantee the protect rule in place; return how many rows were repaired.

    The rule — text naming weather is about weather, and can never be flagged as
    a non-meteorological use of the word "tornado" — is the project owner's
    specification, not a heuristic. The model has not read it and never gets the
    last word on it, so this is re-checked after every stage rather than trusted.
    """
    violating = df[protected_column].fillna(False) & df[column].fillna(False)
    n = int(violating.sum())
    if n:
        df.loc[violating, column] = False
    return n


def promote_to_group(values: pd.Series, groups: pd.Series) -> pd.Series:
    """Raise a boolean flag to the maximum over its deduplication group.

    Only one row per group is labelled and its answer propagates to the rest, so
    a guard computed per row can be handed to a sibling it does not describe.
    Taking the group maximum of a *protective* flag can only ever forbid a label,
    never invent one, so the direction of the error is the safe one.
    """
    return values.groupby(groups).transform("max").astype(bool)


# ── deduplicate → label → propagate ─────────────────────────────────────────
def pick_representatives(df: pd.DataFrame, group_column: str,
                         richness: pd.Series) -> pd.Series:
    """Mark one row per group: the one with the most evidence to offer.

    ``richness`` is whatever the corpus considers informative — URL slug length
    for headline data, body length for full text. ``idxmax`` returns exactly one
    index per group and breaks ties by first occurrence, so this is one
    representative per group by construction.
    """
    flags = pd.Series(False, index=df.index)
    flags.loc[richness.groupby(df[group_column]).idxmax()] = True
    return flags


def propagate(df: pd.DataFrame, labels: pd.DataFrame, key: str,
              carry: Sequence[str]) -> pd.DataFrame:
    """Join per-group labels back onto every row.

    ``key`` must be *content-derived* (a normalised headline, a body hash), never
    a positional group code: factorize order is only meaningful within one read
    of a corpus, so joining on it silently mismatches whenever the two stages saw
    different slices.
    """
    mapped = labels.drop_duplicates(key).set_index(key)[list(carry)]
    return df.join(mapped, on=key)


# ── self-consistency ────────────────────────────────────────────────────────
def consistency_scores(samples: list[pd.Series]) -> pd.DataFrame:
    """Summarise k repeated labels per row into an agreement measure.

    ``modal_share`` is the fraction of the k draws agreeing with the most common
    answer: 1.0 when unanimous, 1/k when every draw differs. Draws are taken at
    :data:`UNCERTAINTY_TEMPERATURE`, so the spread estimates the model's own
    uncertainty rather than an artefact of a sharpened distribution.

    This is the uncertainty signal to use. The ``conf`` the model reports about
    itself is not a calibrated probability and nothing should rest on it until it
    has been checked against human labels.
    """
    stacked = pd.concat(samples, axis=1)
    modal = stacked.mode(axis=1)[0]
    share = stacked.eq(modal, axis=0).sum(axis=1) / stacked.shape[1]
    return pd.DataFrame({"modal_label": modal, "modal_share": share,
                         "stable": share >= 1.0, "n_samples": stacked.shape[1]})


# ── shared I/O ──────────────────────────────────────────────────────────────
def restore_dtypes(df: pd.DataFrame, flags: Sequence[str] = tuple(BASE_FLAGS)
                   ) -> pd.DataFrame:
    """Restore the dtypes a CSV round-trip flattens.

    Tables are read with ``keep_default_na=False`` so a headline of "NA" or
    "null" survives as text, but that also turns an empty ``conf`` into ``""``
    and the booleans into strings — and a string ``"False"`` is truthy, which
    fails silently everywhere it matters.
    """
    for col in [*flags, "parsed", "protected", "is_representative", "is_duplicate"]:
        if col in df.columns and df[col].dtype == object:
            df[col] = df[col].astype(str).str.lower().isin(("true", "1"))
    for col in ("conf", "modal_share"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def label_summary(df: pd.DataFrame, flags: Sequence[str] = tuple(BASE_FLAGS)) -> str:
    """Human-readable distribution of primaries and flags, for stdout."""
    lines = ["primary label distribution"]
    for label, n in df.primary.value_counts().items():
        lines.append(f"  {label:<20}{n:>8,}  ({n / len(df):>5.1%})")
    lines.append("flags")
    for flag in flags:
        if flag in df.columns:
            lines.append(f"  {flag:<20}{df[flag].sum():>8,}  ({df[flag].mean():>5.1%})")
    return "\n".join(lines)

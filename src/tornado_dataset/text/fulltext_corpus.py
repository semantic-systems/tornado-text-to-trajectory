"""The retrieved Media Cloud full texts as a labelled corpus.

Stage 33 retrieves bodies for the Media Cloud ``EVENT`` stories; this module
turns its store into something the rest of the pipeline can use:

* :func:`load_population` — the stories the crawl was asked for, with the strata
  every coverage table is broken down by. Stage 33 and stage 34 share it, so the
  two cannot disagree about what "the population" was.
* :func:`load_bodies` — retrieved bodies in the shape the LexisNexis labeller
  expects (``headline``, ``source``, ``pub_date``, ``body``), so stage 34 can
  apply stage 32's prompt **unchanged**. The headline labels from stage 30 ride
  along under an ``hl_`` prefix; the full-text labels are added under ``ft_``.
* the comparison functions — headline-only versus full-text labels, per story,
  per flag, per stratum, and against LexisNexis on stories both corpora hold.

What the comparison can and cannot show
---------------------------------------
The crawl covered only stories whose *headline* was labelled ``EVENT``. So the
comparison measures how many headline ``EVENT`` calls the full text overturns —
the headline labeller's **precision** — but says nothing about stories the
headline labeller rejected, i.e. its recall. Every function here is written for
the general case, so crawling a sample of non-``EVENT`` stories would fill in
the other rows of the crosstab without code changes.

The full-text label is better evidence, not ground truth. Where the two
disagree, the inspection viewer (``scripts/viewer.py --corpus mediacloud``)
is the way to find out which one is right.
"""

from __future__ import annotations

from typing import Iterable, Sequence

import numpy as np
import pandas as pd

from .. import config
from . import lexisnexis_filter as lf
from .labelling import BASE_FLAGS, PRIMARY_LABELS

# Same files stage 33 reads and writes.
MC_LABELS = config.PROCESSED_DIR / "mediacloud_filtered.csv.gz"
STORE = config.RAW_DIR / "fulltext" / "retrievals.jsonl"
QUALITY_CSV = config.INTERIM_DIR / "fulltext_quality.csv"
# Written by the inspection viewer: one row per verdict, URL and headline only.
INSPECTION_CSV = config.INTERIM_DIR / "fulltext_inspection.csv"

YEAR_BANDS = [(2010, 2015, "2010-2015"), (2016, 2020, "2016-2020"),
              (2021, 2025, "2021-2025")]

# Columns the comparison is about; everything else is context.
HL, FT = "hl_", "ft_"


# ── population ──────────────────────────────────────────────────────────────
def load_population(path=None) -> pd.DataFrame:
    """Distinct Media Cloud ``EVENT`` stories — what stage 33 was asked to crawl."""
    df = pd.read_csv(path or MC_LABELS, keep_default_na=False, low_memory=False)
    df = df[(df.primary == "EVENT")
            & (df.is_representative.astype(str).str.lower() == "true")].copy()
    df["year"] = pd.to_numeric(df.publish_date.str[:4], errors="coerce")
    counts = df.media_name.value_counts()
    # Domain size matters because it predicts both survival (large outlets keep
    # their URL structure) and paywalls, in opposite directions.
    df["domain_size"] = pd.cut(df.media_name.map(counts), [0, 5, 50, 10**9],
                               labels=["small (≤5)", "medium (6-50)", "large (>50)"])
    df["year_band"] = "other"
    for lo, hi, name in YEAR_BANDS:
        df.loc[df.year.between(lo, hi), "year_band"] = name
    return df


# ── bodies ──────────────────────────────────────────────────────────────────
def load_bodies(store: dict, population: pd.DataFrame,
                quality: pd.DataFrame | None = None) -> pd.DataFrame:
    """One row per retrieved story, shaped for :mod:`lexisnexis_filter`.

    Rows are sorted by URL before deduplication so the representative of a
    shared body — and therefore the headline the model sees — does not depend
    on the order the crawl happened to finish in.
    """
    from .fulltext import HARD_FLAGS, SOFT_FLAGS

    docs = pd.DataFrame([
        {"url": url, "body": rec.get("text") or "", "page_title": rec.get("title") or "",
         "via": rec.get("via") or "", "final_url": rec.get("final_url") or "",
         "retrieved_at": rec.get("retrieved_at") or ""}
        for url, rec in store.items() if rec.get("status") == "ok"])
    if docs.empty:
        return docs

    flags = [f for f in BASE_FLAGS if f in population.columns]
    meta = population[["url", "title", "publish_date", "media_name", "dup_group",
                       "year_band", "domain_size", "primary", "conf", *flags]].rename(
        columns={"title": "headline", "media_name": "source", "publish_date": "pub_date",
                 "dup_group": "hl_group", "primary": HL + "primary", "conf": HL + "conf",
                 **{f: HL + f for f in flags}})
    df = docs.merge(meta, on="url", how="inner")
    df["n_words"] = df.body.str.split().str.len()

    if quality is not None and len(quality):
        measures = [c for c in ("title_containment", "stopword_share",
                                "boilerplate_share", "body_headlines") if c in quality]
        q = quality[["url", "quality_ok", *HARD_FLAGS, *SOFT_FLAGS, *measures]]
        df = df.merge(q, on="url", how="left")
        df["quality_known"] = df.quality_ok.notna()
        for col in ["quality_ok", *HARD_FLAGS, *SOFT_FLAGS]:
            df[col] = df[col].astype(str).str.lower().isin(("true", "1"))
    else:
        df["quality_known"] = False
        df["quality_ok"] = False

    df = df.sort_values("url").reset_index(drop=True)
    df = lf.add_rule_cues(lf.add_dedup_groups(df))
    return lf.restore_dtypes(df, [HL + f for f in flags])


def load_quality(path=None) -> pd.DataFrame | None:
    path = path or QUALITY_CSV
    if not path.exists():
        return None
    return pd.read_csv(path, keep_default_na=False, low_memory=False)


# ── comparison ──────────────────────────────────────────────────────────────
def cohen_kappa(a: Sequence, b: Sequence) -> float:
    """Chance-corrected agreement. For rare flags raw agreement is meaningless:
    two labellers who never set ``is_fact_check`` agree 99.9% of the time."""
    a, b = pd.Series(list(a)), pd.Series(list(b))
    if not len(a):
        return float("nan")
    observed = float((a == b).mean())
    cats = sorted(set(a) | set(b), key=str)
    expected = sum(float((a == c).mean()) * float((b == c).mean()) for c in cats)
    if expected >= 1.0:
        return float("nan")            # one category only: kappa is undefined
    return (observed - expected) / (1.0 - expected)


def primary_crosstab(df: pd.DataFrame) -> pd.DataFrame:
    """Headline label (rows) × full-text label (columns), all four labels shown."""
    table = pd.crosstab(df[HL + "primary"], df[FT + "primary"])
    table = table.reindex(index=[l for l in PRIMARY_LABELS if l in table.index],
                          columns=list(PRIMARY_LABELS), fill_value=0)
    return table


def flag_agreement(df: pd.DataFrame, flags: Iterable[str] = BASE_FLAGS) -> pd.DataFrame:
    """Per shared flag: how often each side sets it, and whether they agree."""
    rows = []
    for flag in flags:
        h, f = HL + flag, FT + flag
        if h not in df.columns or f not in df.columns:
            continue
        a, b = df[h].astype(bool), df[f].astype(bool)
        rows.append({"flag": flag, "headline": int(a.sum()), "fulltext": int(b.sum()),
                     "both": int((a & b).sum()), "headline_only": int((a & ~b).sum()),
                     "fulltext_only": int((~a & b).sum()),
                     "agreement": float((a == b).mean()), "kappa": cohen_kappa(a, b)})
    return pd.DataFrame(rows)


def agreement_by(df: pd.DataFrame, by: str | pd.Series) -> pd.DataFrame:
    """Primary-label agreement per stratum, as counts, so callers add intervals."""
    agree = df[HL + "primary"] == df[FT + "primary"]
    key = df[by] if isinstance(by, str) else by
    out = (pd.DataFrame({"key": key, "agree": agree})
             .groupby("key", observed=True).agree.agg(["size", "sum"])
             .rename(columns={"size": "n", "sum": "agree"}))
    out["rate"] = out.agree / out.n
    return out.reset_index()


def conf_bins(conf: pd.Series) -> pd.Series:
    return pd.cut(pd.to_numeric(conf, errors="coerce"), [-0.01, 0.6, 0.8, 0.9, 1.0],
                  labels=["≤0.6", "0.6-0.8", "0.8-0.9", ">0.9"])


def mention_bins(n: pd.Series) -> pd.Series:
    return pd.cut(n, [-1, 0, 1, 3, 8, 10**6], labels=["0", "1", "2-3", "4-8", "9+"])


def transitions(df: pd.DataFrame) -> pd.Series:
    """``"EVENT → NOT_TORNADO_EVENT"`` style keys for every disagreement."""
    d = df[df[HL + "primary"] != df[FT + "primary"]]
    return (d[HL + "primary"] + " → " + d[FT + "primary"]).value_counts()


def cross_corpus(stories: pd.DataFrame, lexis: pd.DataFrame,
                 edges: pd.DataFrame) -> pd.DataFrame:
    """LexisNexis label next to both Media Cloud labels, on matched stories.

    The atlas found LexisNexis and Media Cloud agree on only 74.8% of shared
    stories. That is either because one side saw a body and the other a
    headline, or because the two labellers behave differently. With full text on
    both sides and the *same* prompt, the evidence gap is closed, so whatever
    disagreement remains belongs to the labeller or to the bodies themselves.

    ``stories`` is the per-story table stage 34 writes; ``lexis`` is
    :func:`corpora.load_lexisnexis`; ``edges`` is the atlas edge table.
    """
    from .corpora import _story_id

    corp = {frozenset(("lexisnexis", "mediacloud"))}
    pair = edges[[frozenset(p) in corp
                  for p in zip(edges.left_corpus, edges.right_corpus)]]
    flip = (pair.left_corpus == "mediacloud").to_numpy()
    pairs = pd.DataFrame({
        "ln_story": np.where(flip, pair.right_story, pair.left_story),
        "mc_story": np.where(flip, pair.left_story, pair.right_story),
    }).drop_duplicates()

    def modal(frame: pd.DataFrame, key: str, col: str) -> pd.Series:
        return frame.groupby(key)[col].agg(lambda s: s.value_counts().index[0])

    ln_label = modal(lexis, "story_id", "primary").rename("ln_primary")
    s = stories.assign(mc_story=_story_id(stories.headline, stories.pub_date))
    hl = modal(s, "mc_story", HL + "primary").rename(HL + "primary")
    ft = modal(s, "mc_story", FT + "primary").rename(FT + "primary")
    out = (pairs.join(ln_label, on="ln_story").join(hl, on="mc_story")
                .join(ft, on="mc_story"))
    return out.dropna(subset=["ln_primary", FT + "primary"]).reset_index(drop=True)


# ── human inspection ────────────────────────────────────────────────────────
INSPECTION_COLUMNS = ["inspected_at", "url", "headline", "body_verdict", "label",
                      "note", "via_random", "filter"]
BODY_VERDICTS = ("right_article", "wrong_page", "partial")


def load_inspections(path=None) -> pd.DataFrame:
    """Latest verdict per URL; an empty frame when nothing has been inspected."""
    path = path or INSPECTION_CSV
    if not path.exists():
        return pd.DataFrame(columns=INSPECTION_COLUMNS)
    df = pd.read_csv(path, keep_default_na=False, dtype=str)
    if df.empty:
        return df
    df["via_random"] = df.via_random.str.lower().isin(("true", "1"))
    return df.sort_values("inspected_at").drop_duplicates("url", keep="last")

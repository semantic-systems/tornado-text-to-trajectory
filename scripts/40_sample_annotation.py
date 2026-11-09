"""Stage 40 — draw the blind annotation samples that validate the links.

Three sheets, each answering a different question:

* **precision** — of the links the pipeline produced, how many are right? Pairs are
  stratified across score bands so the marginal links are measured too, not just
  the comfortable ones, and the score is withheld so it cannot anchor judgement.
* **recall** — of the events articles are actually about, how many does the
  pipeline find? Sampled over *articles*, and you record the true event from the
  text before seeing any candidate. Measuring recall on the pipeline's own output
  is impossible by construction.
* **agreement** — a subset of the precision pairs repeated, to report κ. Without
  it, a precision figure rests on one person's unexamined judgement.

    python scripts/40_sample_annotation.py
    python scripts/40_sample_annotation.py --precision 100 --recall 50 --agreement 30
"""

from __future__ import annotations

import argparse
import textwrap

import _bootstrap  # noqa: F401

import pandas as pd

from tornado_dataset import config
from tornado_dataset.ids import write_manifest

# Score bands for stratification. Equal-width rather than equal-count, so the
# sample covers the whole range of confidence the pipeline actually emits.
BANDS = [(0.0, 0.35), (0.35, 0.5), (0.5, 0.65), (0.65, 0.8), (0.8, 1.01)]

LABELS = textwrap.dedent("""\
    describes  = the article is mainly about this event
    mentions   = the article refers to this event, but is mainly about something else
    unrelated  = this event is not the one the article is about
    no_event   = the article is not about any specific tornado (explainer, policy, season outlook)
    cannot_tell = the article does not say enough to decide
""")


def excerpt(body: str, width: int = 700) -> str:
    text = " ".join(str(body or "").split())
    return text[:width] + ("…" if len(text) > width else "")


def main() -> None:
    default_tag = f"{config.WINDOW_START.isoformat()}_{config.WINDOW_END.isoformat()}"
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", default=default_tag)
    parser.add_argument("--precision", type=int, default=200)
    parser.add_argument("--recall", type=int, default=100)
    parser.add_argument("--agreement", type=int, default=50)
    parser.add_argument("--seed", type=int, default=20260730)
    parser.add_argument("--corpus", default="lexisnexis", choices=("lexisnexis", "gdelt"))
    args = parser.parse_args()

    links = pd.read_csv(config.PROCESSED_DIR / f"article_links_{args.tag}.csv")
    links = links[links.corpus == args.corpus]
    refs = pd.read_csv(config.PROCESSED_DIR / f"textrefs_lexisnexis_{args.tag}.csv")
    articles = pd.read_json(config.OUTPUT_DIR / "lexisnexis_articles.jsonl", lines=True)
    bodies = dict(zip(articles.file, articles.body))
    episodes = pd.read_csv(config.PROCESSED_DIR / f"episodes_{args.tag}.csv").set_index(
        "episode_uid")
    geography = pd.read_csv(config.PROCESSED_DIR / f"hazard_geography_{args.tag}.csv")
    places_by_episode = (geography.groupby("episode_uid")
                         .apply(lambda g: "; ".join(
                             sorted({p for row in g.places.dropna()
                                     for p in str(row).split(";") if p})[:10]),
                                include_groups=False)
                         .to_dict())
    counties_by_episode = (geography.groupby("episode_uid")
                           .apply(lambda g: "; ".join(
                               sorted({c for row in g.counties.dropna()
                                       for c in str(row).split(";") if c})[:8]),
                                  include_groups=False)
                           .to_dict())

    merged = links.merge(refs, on="textref_uid", how="left", suffixes=("", "_ref"))
    merged["body"] = merged.file.map(bodies) if "file" in merged else ""

    # ── precision sheet ──
    rng_state = args.seed
    per_band = max(1, args.precision // len(BANDS))
    chunks = []
    for low, high in BANDS:
        band = merged[(merged.link_score >= low) & (merged.link_score < high)]
        if not len(band):
            continue
        take = min(per_band, len(band))
        chunks.append(band.sample(take, random_state=rng_state).assign(
            score_band=f"{low:.2f}-{high:.2f}"))
    precision = pd.concat(chunks).sample(frac=1, random_state=rng_state)

    def event_summary(uid_: str) -> dict:
        if uid_ not in episodes.index:
            return {}
        row = episodes.loc[uid_]
        return {
            "event_day": row.convective_day,
            "event_tornadoes": row.n_hazards,
            "event_max_rating": row.max_efscale,
            "event_fatalities": row.fatalities,
            "event_places": places_by_episode.get(uid_, ""),
            "event_counties": counties_by_episode.get(uid_, ""),
        }

    sheet = []
    for i, row in enumerate(precision.itertuples(), 1):
        sheet.append({
            "pair_id": f"P{i:04d}",
            "article_headline": row.headline,
            "article_source": row.source_name,
            "article_date": row.date,
            "article_excerpt": excerpt(getattr(row, "body", "")),
            **event_summary(row.episode_uid),
            "label": "",          # ← you fill this in
            "notes": "",
        })
    precision_sheet = pd.DataFrame(sheet)

    # The key is written separately so the sheet itself carries no score, uid or
    # relation that could anchor the judgement.
    key = precision.assign(pair_id=[f"P{i:04d}" for i in range(1, len(precision) + 1)])[
        ["pair_id", "textref_uid", "episode_uid", "hazard_uid", "link_relation",
         "link_level", "link_score", "score_band", "toponym_score",
         "corroboration_score", "day_offset", "from_retrospective_pass",
         "matched_names"]]

    # ── recall sheet: articles, no candidates shown ──
    sampled_articles = refs.sample(min(args.recall, len(refs)), random_state=rng_state + 1)
    recall_sheet = pd.DataFrame([{
        "article_id": f"R{i:04d}",
        "article_headline": row.headline,
        "article_source": row.source_name,
        "article_date": row.date,
        "article_excerpt": excerpt(bodies.get(row.file, "")),
        "true_event_date": "",        # ← you fill these in from the text alone
        "true_event_place": "",
        "is_about_one_event": "",     # yes / no / cannot_tell
        "notes": "",
    } for i, row in enumerate(sampled_articles.itertuples(), 1)])
    recall_key = sampled_articles.assign(
        article_id=[f"R{i:04d}" for i in range(1, len(sampled_articles) + 1)])[
        ["article_id", "textref_uid", "headline", "date"]]

    # ── agreement sheet: a repeated subset, shuffled and re-identified ──
    agreement = precision_sheet.sample(min(args.agreement, len(precision_sheet)),
                                       random_state=rng_state + 2).copy()
    agreement["pair_id"] = [f"A{i:04d}" for i in range(1, len(agreement) + 1)]
    agreement_key = pd.DataFrame({
        "agreement_id": agreement.pair_id.values,
        "original_pair_id": precision_sheet.loc[agreement.index, "pair_id"].values,
    })

    out_dir = config.OUTPUT_DIR / "annotation"
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "precision_sheet": out_dir / "precision_sheet.csv",
        "precision_key": out_dir / "precision_key.csv",
        "recall_sheet": out_dir / "recall_sheet.csv",
        "recall_key": out_dir / "recall_key.csv",
        "agreement_sheet": out_dir / "agreement_sheet.csv",
        "agreement_key": out_dir / "agreement_key.csv",
    }
    precision_sheet.to_csv(paths["precision_sheet"], index=False)
    key.to_csv(paths["precision_key"], index=False)
    recall_sheet.to_csv(paths["recall_sheet"], index=False)
    recall_key.to_csv(paths["recall_key"], index=False)
    agreement.to_csv(paths["agreement_sheet"], index=False)
    agreement_key.to_csv(paths["agreement_key"], index=False)

    (out_dir / "HOW_TO_ANNOTATE.txt").write_text(
        "Fill in the 'label' column of precision_sheet.csv and agreement_sheet.csv\n"
        "using exactly these values:\n\n" + LABELS +
        "\nFor recall_sheet.csv, read the article and record the event it is about\n"
        "(date and place) from the text alone — do not consult the dataset.\n\n"
        "Full rules and worked examples: docs/annotation_codebook.md\n"
        "When done, run: python scripts/41_qa_links.py\n", encoding="utf-8")

    counts = {
        "corpus": args.corpus,
        "precision_pairs": len(precision_sheet),
        "precision_by_band": precision.score_band.value_counts().to_dict(),
        "recall_articles": len(recall_sheet),
        "agreement_pairs": len(agreement),
        "seed": args.seed,
    }
    write_manifest(out_dir / f"manifest_annotation_{args.corpus}.json",
                   "40_sample_annotation", counts=counts, outputs=list(paths.values()))

    print(f"precision sheet: {len(precision_sheet)} pairs across "
          f"{precision.score_band.nunique()} score bands")
    print(precision.score_band.value_counts().sort_index().to_string())
    print(f"recall sheet: {len(recall_sheet)} articles")
    print(f"agreement sheet: {len(agreement)} repeated pairs")
    print(f"\nwrote {out_dir}/ — start with HOW_TO_ANNOTATE.txt")


if __name__ == "__main__":
    main()

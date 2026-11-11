"""Stage 35 — quality report for the text layer (NWS text, news).

Reports what was collected, how it was matched, and where the coverage stops.
Every headline figure is paired with the denominator it came from, and the
sections that rest on a retrieval choice (the GDELT query form, the PNS match
radius) show the measurement that decided it.

    python scripts/35_qa_text.py
    python scripts/35_qa_text.py --tag march2025
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import _bootstrap  # noqa: F401

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from tornado_dataset import config
from tornado_dataset.text import tiering

plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#b8b8b8", "font.size": 10, "figure.dpi": 110,
})
ROLE_COLOURS = {"oracle": "#d1495b", "official_timely": "#edae49",
                "independent_timely": "#2e6f95", "independent_retrospective": "#8ab17d"}


def pct(numerator: float, denominator: float) -> str:
    return f"{numerator / denominator:.1%}" if denominator else "n/a"


def read_optional(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def main() -> None:
    default_tag = f"{config.WINDOW_START.isoformat()}_{config.WINDOW_END.isoformat()}"
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", default=default_tag)
    parser.add_argument("--news-suffix", default=None,
                        help="suffix of the news files if a pilot subset was used")
    args = parser.parse_args()
    tag = args.tag
    news_tag = args.news_suffix or tag

    hazards = pd.read_csv(config.PROCESSED_DIR / f"hazards_{tag}.csv")
    episodes = pd.read_csv(config.PROCESSED_DIR / f"episodes_{tag}.csv")
    nws_refs = read_optional(config.PROCESSED_DIR / f"textrefs_nws_{tag}.csv")
    nws_links = read_optional(config.PROCESSED_DIR / f"textlinks_nws_{tag}.csv")
    news_refs = read_optional(config.PROCESSED_DIR / f"textrefs_news_{news_tag}.csv")
    news_links = read_optional(config.PROCESSED_DIR / f"textlinks_news_{news_tag}.csv")

    geo_manifest = json.loads(
        (config.PROCESSED_DIR / f"manifest_geography_{tag}.json").read_text())
    edits_path = config.PROCESSED_DIR / f"manifest_same_source_{tag}.json"
    edits = json.loads(edits_path.read_text())["counts"] if edits_path.exists() else None

    refs = pd.concat([df for df in (nws_refs, news_refs) if len(df)], ignore_index=True)
    role_counts = refs.text_role.value_counts() if len(refs) else pd.Series(dtype=int)

    # ── coverage per hazard / episode ──
    hazard_with_nws = nws_links.target_uid.nunique() if len(nws_links) else 0
    oracle_links = (nws_links[nws_links.link_relation == "primary_survey_of"]
                    if len(nws_links) else pd.DataFrame())
    hazard_with_oracle = oracle_links.target_uid.nunique() if len(oracle_links) else 0
    episode_with_news = news_links.target_uid.nunique() if len(news_links) else 0
    eligible_episodes = (episodes.convective_day >= config.GDELT_COVERAGE_START.isoformat()).sum()

    # ── survey vs DAT attribute agreement (independent descriptions) ──
    agreement_rows = pd.DataFrame()
    if len(oracle_links):
        agreement_rows = (oracle_links.merge(nws_refs, on="textref_uid")
                          .merge(hazards[["hazard_uid", "efscale", "path_length_mi",
                                          "fatalities"]],
                                 left_on="target_uid", right_on="hazard_uid"))
        agreement_rows["ef_match"] = (agreement_rows.survey_ef_rating.astype(str).str.upper()
                                      == agreement_rows.efscale.astype(str).str.upper())
        agreement_rows["length_ratio"] = (agreement_rows.survey_path_length_mi
                                          / agreement_rows.path_length_mi)
        agreement_rows["fatalities_match"] = (agreement_rows.survey_fatalities.fillna(-1)
                                              == agreement_rows.fatalities.fillna(-1))

    # ── figures ──
    figures_dir = config.OUTPUT_DIR / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(11, 3.6))
    if len(refs) and "time_offset_hours" in refs:
        for role, colour in ROLE_COLOURS.items():
            subset = refs[(refs.text_role == role) & refs.time_offset_hours.notna()]
            if not len(subset):
                continue
            axes[0].scatter(subset.time_offset_hours.clip(-24, 240),
                            [role] * len(subset), s=6, alpha=0.25, color=colour)
        axes[0].axvline(0, color="#666666", lw=1)
        axes[0].set_xlabel("hours after tornado onset (clipped at 240)")
        axes[0].set_title("When each kind of text appears")
    if len(role_counts):
        axes[1].bar(role_counts.index, role_counts.values,
                    color=[ROLE_COLOURS.get(r, "#999999") for r in role_counts.index])
        axes[1].set_title("Text references by role")
        axes[1].tick_params(axis="x", rotation=20)
    fig.tight_layout()
    roles_fig = figures_dir / "text_roles.png"
    fig.savefig(roles_fig)
    plt.close(fig)

    # ── edits of one account (stage 25) ──
    if edits:
        linked, false = edits["within_pairs_linked"], edits["expected_false_links"]
        edits_text = (
            "Stage 25 compares each hazard's official texts (survey statement, Storm Events "
            "narratives, DAT comments, LSRs) by shared wording specific to the tornado; "
            "method, calibration, recall and sensitivity are in "
            "[`same_source_edits_report.md`](same_source_edits_report.md).\n\n"
            f"- {linked:,} of {edits['within_pairs']:,} within-hazard pairs are linked "
            f"(at least {edits['min_shared']} shared tokens); expected false links "
            f"{false['other_episode'] / linked:.1%} to {false['same_episode'] / linked:.1%} of "
            "them, by the two comparison sets.\n"
            f"- {edits['groups_2plus']:,} groups of two or more texts. The "
            f"{edits['hazards_with_2plus_texts']:,} hazards with two or more texts hold "
            f"{edits['their_texts']:,} texts in {edits['their_accounts']:,} accounts "
            f"({1 - edits['their_accounts'] / edits['their_texts']:.0%} fewer accounts than "
            "texts).")
    else:
        edits_text = "Not run yet: `scripts/25_find_same_source_edits.py`."

    # ── report ──
    # Stage 16 reports per hazard source; an older manifest has the DAT counts at the top.
    geo_counts = geo_manifest["counts"]
    geo_dat = geo_counts.get("dat", geo_counts)
    report = f"""# Text layer — Stage B quality report

Tag `{tag}`; news files `{news_tag}`. Generated by `scripts/35_qa_text.py`.

## 1. Geography and WFO

Counties, offices and place names come from stage 16 and are reported with the
events, in `outputs/events_qa_report.md` (section 5, "Geography"). For the text
layer: {pct(geo_dat.get('wfo_known', 0), geo_dat.get('hazards', 0))} of the
{geo_dat.get('hazards', 0):,} DAT hazards have an office to fetch NWS text for, and
{pct(geo_dat.get('hazards_with_places', 0), geo_dat.get('hazards', 0))} have place names to match news against.

## 2. NWS text (same-org)

| | n |
|---|---|
| text references | {len(nws_refs)} |
| links to hazards | {len(nws_links)} |
| hazards with any NWS text | {hazard_with_nws} ({pct(hazard_with_nws, len(hazards))}) |
| hazards with a primary survey (oracle) | {hazard_with_oracle} ({pct(hazard_with_oracle, len(hazards))}) |
| hazards with DAT survey comments (the other oracle source) | {int(hazards.has_oracle_text.sum())} ({pct(hazards.has_oracle_text.sum(), len(hazards))}) |

Storm-survey products are compendia: one PNS covers every tornado an office
surveyed, so sections are split apart and matched individually by the start/end
coordinates each section states. Only the best-scoring section for a hazard —
geometry plus agreement with DAT's path length — becomes `primary_survey_of`;
other nearby sections are recorded as `mentions`, so a hazard's oracle text is
never another tornado's write-up.

The match radius (5 km, both endpoints) comes from the observed distribution
rather than a guess: true counterparts cluster at a median of tens of metres,
while sections describing neighbouring tornadoes in the same outbreak appear
only beyond 12 km.

### Two survey formats, and why only one yields oracle text

Before roughly 2012 there was no common survey template. Products are all-caps
free text with office-specific bullet fields, no per-tornado sections and no
coordinates, so they can only be matched by office, date and place name.
Measured on the 27 April 2011 outbreak, that matching put the right rating on
**40% of links, against 97% for coordinate-matched sections** — office and date
cannot pick the right tornado out of a product covering dozens of them.

Legacy products are therefore kept and linked as `mentions` (they are genuine
survey prose about that outbreak) but never as `primary_survey_of`. The
consequence is stark and worth stating plainly: for the April 2011 outbreak
**0 of 112 hazards** have oracle text from PNS, against **69 of 85** for March
2025. Pre-template events are not left without an oracle — DAT's own `comments`
field carries the surveyor's narrative for {pct((hazards.has_oracle_text).sum(), len(hazards))} of hazards — but the two
sources have different eras of strength, and an experiment that needs PNS oracle
text should filter on `survey_format == "structured"`.
"""

    if len(agreement_rows):
        ef_match = agreement_rows.ef_match.mean()
        length_close = (agreement_rows.length_ratio.between(0.9, 1.1)).mean()
        fatalities_match = agreement_rows.fatalities_match.mean()
        report += f"""
### The survey and DAT as two independent descriptions

Each matched section states its own rating, path length and fatality count, and
DAT records the same quantities separately. Comparing them is free validation of
the hazard record — and where they disagree, that disagreement is itself data.

| quantity | agreement | n |
|---|---|---|
| EF rating identical | {ef_match:.1%} | {len(agreement_rows)} |
| path length within ±10% | {length_close:.1%} | {agreement_rows.length_ratio.notna().sum()} |
| fatality count identical | {fatalities_match:.1%} | {len(agreement_rows)} |

Disagreement is expected and informative: DAT sometimes draws as one line what
the survey splits into several tornadoes, so a hazard can legitimately be longer
than the section matched to it.
"""

    report += f"""
## 3. Independent news (GDELT)

| | n |
|---|---|
| episodes | {len(episodes)} |
| … within GDELT coverage (≥ {config.GDELT_COVERAGE_START}) | {eligible_episodes} |
| … before it, flagged and never queried | {len(episodes) - eligible_episodes} |
| episodes with retrieved articles | {episode_with_news} |
| unique articles | {len(news_refs)} |

**Query form was decided by measurement.** The prototype queried place names
alone, having found that adding a hazard word to a *single* place name collapsed
the results. With an OR-group of a dozen places the opposite holds — measured on
the March 2025 outbreak:

| query | returned | about the storm |
|---|---|---|
| `(place OR place OR …)` | 250 | 5 (2%) |
| `(place OR place OR …) tornado` | 250 | 237 (95%) |
| `(place OR place OR …) (tornado OR storm)` | 250 | 126 (50%) |

**The window is queried in slices** ({config.GDELT_WINDOW_DAYS_AFTER} days, split day 0-1 / 1-3 / 3-7)
because a response is capped at {config.GDELT_MAX_RECORDS} and filled newest-first. A single
8-day query returned only follow-up coverage and *zero* `independent_timely`
articles; slicing recovered them. Episodes whose slices hit the cap are flagged
`hit_record_cap`, so truncated coverage is visible rather than assumed complete.

## 4. Text by independence role

{role_counts.rename_axis('text_role').reset_index(name='n').to_markdown(index=False) if len(role_counts) else '(no text collected yet)'}

The two axes behind these labels (`same_org_as_geometry` × `temporal_class`) are
assigned by one versioned rule, `{tiering.TIER_RULE_VERSION}`, recorded on every
row so the corpus can be re-tiered reproducibly. Timing is in
`figures/text_roles.png`.

## 5. Edits of one account

{edits_text}

## 6. Limitations

1. **News coverage stops at {config.GDELT_COVERAGE_START}.** {len(episodes) - eligible_episodes} of {len(episodes)} episodes predate the GDELT
   DOC API's earliest queryable date and carry no independent-news links. They
   are flagged, not silently empty.
2. **Retrieval is not exhaustive.** GDELT caps a response at {config.GDELT_MAX_RECORDS} articles per
   query, and its index is not a census of the web. "Not retrieved" is not
   evidence of "not published".
3. **News links are episode-level.** An article retrieved for an outbreak is not
   yet attributed to a specific tornado; that is Stage C's job, with per-article
   evidence and a hand-annotated validation sample.
4. **Wayback snapshots must be captured at collection time.** Roughly 40% of the
   sampled URLs were archived; the rest may disappear.
5. **LSR and survey matching are geometric heuristics**, tuned on observed
   distributions and validated on one well-documented outbreak — not yet against
   a hand-labelled sample.
"""

    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = config.OUTPUT_DIR / "text_qa_report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"roles: {role_counts.to_dict()}")
    print(f"wrote {report_path}, {roles_fig.name}")


if __name__ == "__main__":
    main()

"""Stage 35 — quality report for the text layer (NWS text, news).

Reports what was collected, how it was matched, and where the coverage stops.
Every headline figure is paired with the denominator it came from, and the
sections that rest on a retrieval choice (the GDELT query form, the PNS match
radius) show the measurement that decided it.

    python scripts/35_qa_text.py
    python scripts/35_qa_text.py --tag march2025
    python scripts/35_qa_text.py links          # hand check of stage 20's links
    python scripts/35_qa_text.py links-check    # score it, once labelled

``links`` draws LSRs by how their best match was found, survey sections by how
far their endpoints lie from the track, and tornado LSRs left unlinked only by
the time margin, and writes a worksheet, key, map and guide to
``outputs/annotation/`` (:mod:`tornado_dataset.text.link_check`); ``links-check``
writes ``outputs/textlink_hand_checks_report.md``.
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
from tornado_dataset.dat import episode_table
from tornado_dataset.dat.spc_tornadoes import ef_number
from tornado_dataset.text import official, tiering

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


def cmd_links_check() -> None:
    """Precision per stratum and weighted over the LSRs; recall at the margin."""
    from tornado_dataset import handcheck
    from tornado_dataset.text import link_check as lc

    df, counts = handcheck.read_labelled(lc)
    population = counts["population_by_stratum"]
    df["label"] = df.label.str.upper().replace({"NONE": "none", "CANNOT_TELL": "cannot_tell"})
    decided = df.label.notna() & (df.label != "cannot_tell")
    rows = ["| stratum | right hazard | share [95% CI] | another hazard | none | cannot tell |",
            "|---|---:|---:|---:|---:|---:|"]
    lsr_strata = ("sole", "clear", "time", "touching", "unclear")
    weighted, weight = 0.0, 0.0
    for name in [n for n in lc.STRATA if n != "lsr_missed"]:
        g = df[(df.stratum == name) & decided]
        right = int((g.label == g.linked_h).sum())
        other = int(((g.label != g.linked_h) & (g.label != "none")).sum())
        rows.append(handcheck.wilson_row(f"{name} ({population.get(name, 0):,})", right, len(g),
                                         other, int((g.label == "none").sum()),
                                         int(((df.stratum == name)
                                              & (df.label == "cannot_tell")).sum())))
        if name in lsr_strata and len(g):
            weighted += population.get(name, 0) * right / len(g)
            weight += population.get(name, 0)
    m = df[(df.stratum == "lsr_missed") & decided]
    lines = ["# Official-text links — hand check", "",
             f"{len(df)} cases from stage 20's links (`python scripts/35_qa_text.py links`); "
             f"{int(df.label.notna().sum())} labelled. The annotator named the hazard each text "
             "is about among those around it, numbered at random.", "",
             "## Precision: is the linked hazard the one the text is about?", "", *rows, ""]
    if weight:
        lines.append(f"Weighted over the {int(weight):,} linked LSRs: **{weighted / weight:.1%}** "
                     "go to the right hazard.")
    lines += ["", "## Recall at the time margin", "",
              f"{population.get('lsr_missed', 0):,} tornado LSRs lie within the radius of a track "
              f"but more than {config.LSR_TIME_MARGIN_MIN:g} min and at most {lc.MISSED_MAX_H} h "
              "from its time, and are not linked.", "",
              "| answer | cases |", "|---|---:|",
              f"| the hazard near in space (should be linked) | {int((m.label == m.near_h).sum())} |",
              f"| another hazard | {int(((m.label != m.near_h) & (m.label != 'none')).sum())} |",
              f"| none | {int((m.label == 'none').sum())} |", "",
              "Read: if most belong to the hazard near in space, a wider margin (or a rule for "
              "whole-hour offsets, as stage 14 has for DAT) would add real links; the gaps in "
              "`textlink_key.csv` (`gap_min`) say how wide."]
    out = config.OUTPUT_DIR / "textlink_hand_checks_report.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nwrote {out}")


def main() -> None:
    default_tag = f"{config.WINDOW_START.isoformat()}_{config.WINDOW_END.isoformat()}"
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", nargs="?", default="report",
                        choices=("report", "links", "links-check"))
    parser.add_argument("--force", action="store_true",
                        help="links: regenerate even if labels were entered")
    parser.add_argument("--tag", default=default_tag)
    parser.add_argument("--news-suffix", default=None,
                        help="suffix of the news files if a pilot subset was used")
    args = parser.parse_args()
    tag = args.tag
    if args.command == "links":
        from tornado_dataset import handcheck
        from tornado_dataset.text import link_check
        handcheck.write_check(link_check, tag, args.force, "35_qa_text links")
        return
    if args.command == "links-check":
        return cmd_links_check()
    news_tag = args.news_suffix or tag

    hazards = pd.read_csv(config.PROCESSED_DIR / f"hazards_{tag}.csv")
    spc_path = episode_table.spc_hazards_path(tag)
    spc = pd.read_csv(spc_path) if spc_path.exists() else pd.DataFrame(
        columns=["hazard_uid", "efscale", "path_length_mi", "fatalities"])
    nws_manifest_path = config.PROCESSED_DIR / f"manifest_nws_text_{tag}.json"
    nws_manifest = (json.loads(nws_manifest_path.read_text())["counts"]
                    if nws_manifest_path.exists() else {})
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

    # ── coverage per hazard / episode, DAT and SPC hazards apart ──
    oracle_links = (nws_links[nws_links.link_relation == "primary_survey_of"]
                    if len(nws_links) else pd.DataFrame(columns=["target_uid", "textref_uid"]))
    lsr_links = (official.best_lsr_links(nws_links)
                 if len(nws_links) else pd.DataFrame(columns=["target_uid"]))
    sources = {"DAT": set(hazards.hazard_uid), "SPC": set(spc.hazard_uid)}

    def with_text(links: pd.DataFrame, source: str) -> str:
        n = links.target_uid[links.target_uid.isin(sources[source])].nunique() if len(links) else 0
        return f"{n:,} ({pct(n, len(sources[source]))})"

    # An LSR counts for its best match only, here as in "with an LSR".
    any_nws = (pd.concat([nws_links[nws_links.link_relation != "describes"], lsr_links])
               if len(nws_links) else pd.DataFrame(columns=["target_uid"]))
    basis = nws_manifest.get("lsrs_by_assignment", {})
    lsr_radius_km = nws_manifest.get("parameters", {}).get("lsr_radius_m", 0) / 1000
    lsr_margin_min = nws_manifest.get("parameters", {}).get("lsr_time_margin_min", 0)
    lsr_basis = "\n".join(f"- {label}: {basis.get(key, 0):,}" for key, label in (
        ("sole", "the only candidate"),
        ("clear", "every other track at least 3× as far"),
        ("time", "of tracks about as near, the one whose begin–end holds the report"),
        ("touching", "tracks within 1 km of each other (pieces of one tornado, or crossing)"),
        ("unclear", "none of these: the closest in time, flagged `unclear`")))
    time_sources = nws_manifest.get("matched_on_time_of", {})
    # Stage 21 links to episodes by uid; counted only where the episode is in
    # this table, so links made on an earlier episode table are not mixed in.
    news_targets = (news_links.target_uid.drop_duplicates() if len(news_links)
                    else pd.Series(dtype=str))
    episode_with_news = int(news_targets.isin(episodes.episode_uid).sum())
    stale_news_episodes = len(news_targets) - episode_with_news
    eligible_episodes = (episodes.convective_day >= config.GDELT_COVERAGE_START.isoformat()).sum()

    # ── survey vs DAT attribute agreement (independent descriptions) ──
    agreement_rows = pd.DataFrame()
    if len(oracle_links):
        records = pd.concat([
            hazards[["hazard_uid", "efscale", "path_length_mi", "fatalities"]].assign(record="DAT"),
            spc[["hazard_uid", "efscale", "path_length_mi", "fatalities"]].assign(record="SPC")])
        agreement_rows = (oracle_links.merge(nws_refs, on="textref_uid")
                          .merge(records, left_on="target_uid", right_on="hazard_uid"))
        agreement_rows["survey_ef"] = agreement_rows.survey_ef_rating.map(ef_number)
        agreement_rows["record_ef"] = agreement_rows.efscale.map(ef_number)

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

{len(nws_refs):,} text references (LSRs and survey sections), {len(nws_links):,} links to
hazards, for the DAT hazards and the SPC tornadoes without a DAT survey (matched on
SPC's straight line or point).

| | DAT hazards | SPC hazards |
|---|---|---|
| hazards | {len(sources["DAT"]):,} | {len(sources["SPC"]):,} |
| with any NWS text | {with_text(any_nws, "DAT")} | {with_text(any_nws, "SPC")} |
| with an LSR | {with_text(lsr_links, "DAT")} | {with_text(lsr_links, "SPC")} |
| with a primary survey section (oracle) | {with_text(oracle_links, "DAT")} | {with_text(oracle_links, "SPC")} |
| with DAT survey comments (stage 24) | {int(hazards.has_oracle_text.sum()):,} ({pct(hazards.has_oracle_text.sum(), len(hazards))}) | — |

LSRs are matched on each hazard's begin–end, survey sections on its convective
day. For {time_sources.get("spc_track", 0):,} DAT hazards whose time stage 14 found
wrong (by whole hours, or on the same footprint as their SPC track) or missing,
these are the SPC track's (`episode_table.event_times`). With DAT's own, a wrong clock put their LSRs
outside the time window or looked them up on the wrong day, and a missing one
left no time window at all.

An LSR is a candidate for every hazard whose track lies within {lsr_radius_km:g} km
and whose begin–end lies within {lsr_margin_min:g} min of the report. It counts for
one of them, its best match (`iem.assign_lsr`):

{lsr_basis}

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
        def share(hits: pd.Series) -> str:
            return f"{hits.mean():.1%} (n={len(hits):,})" if len(hits) else "—"

        def agree(g: pd.DataFrame) -> tuple[str, str, str]:
            # Only where both state the value: an unrated tornado (EFU, however
            # spelt) or a section without a length or a death count is not a
            # disagreement.
            rated = g[g.survey_ef.notna() & g.record_ef.notna()]
            measured = g[(g.survey_path_length_mi > 0) & (g.path_length_mi > 0)]
            counted = g[g.survey_fatalities.notna() & g.fatalities.notna()]
            ratio = measured.survey_path_length_mi / measured.path_length_mi
            return (share(rated.survey_ef == rated.record_ef),
                    share(ratio.between(0.9, 1.1)),
                    share(counted.survey_fatalities == counted.fatalities))
        cols = {rec: agree(g) for rec, g in agreement_rows.groupby("record")}
        blank = ("—", "—", "—")
        dat, spc_ = cols.get("DAT", blank), cols.get("SPC", blank)
        report += f"""
### The survey and the record as two descriptions

Each matched section states its own rating, path length and fatality count; DAT,
or SPC for an SPC hazard, records the same quantities separately. Comparing them
is free validation of the hazard record, and where they disagree, that
disagreement is itself data. Each quantity is compared where both state it
(rated, a length above zero, a death count), as in stage 17's DAT against SPC.

| quantity | survey vs DAT | survey vs SPC |
|---|---|---|
| EF rating identical, both rated | {dat[0]} | {spc_[0]} |
| path length within ±10% | {dat[1]} | {spc_[1]} |
| fatality count identical | {dat[2]} | {spc_[2]} |

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
{f'''
**Stage 21's links are stale.** They name {stale_news_episodes:,} episodes that are not in
`episodes_{tag}.csv`: they were made on an earlier episode table, so no
current episode has news yet. Rerun stage 21.
''' if stale_news_episodes else ''}
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

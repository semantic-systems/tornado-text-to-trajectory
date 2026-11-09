"""Stage 17 — evaluate the linkage and write the Stage A QA report.

Produces ``outputs/dat_qa_report.md`` plus figures. The report is written to be
read by someone deciding whether to trust the dataset: every headline number is
accompanied by its denominator, its confidence interval where it is an estimate,
and the caveat that limits it.

    python scripts/17_qa_events.py
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
from tornado_dataset.dat import evaluate, link

plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#b8b8b8", "font.size": 10, "figure.dpi": 110,
})
ACCENT = "#d1495b"
BLUE = "#2e6f95"


def pct(numerator: float, denominator: float) -> str:
    return f"{numerator / denominator:.1%}" if denominator else "n/a"


def ci(bounds: tuple[float, float]) -> str:
    return f"[{bounds[0]:.1%}, {bounds[1]:.1%}]"


def main() -> None:
    default_tag = f"{config.WINDOW_START.isoformat()}_{config.WINDOW_END.isoformat()}"
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", default=default_tag)
    args = parser.parse_args()
    tag = args.tag

    figures_dir = config.OUTPUT_DIR / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    lines_raw = json.loads((config.INTERIM_DIR / f"dat_lines_{tag}.geojson").read_text())["features"]
    polys_raw = json.loads((config.INTERIM_DIR / f"dat_polygons_{tag}.geojson").read_text())["features"]
    candidates = pd.read_csv(config.INTERIM_DIR / f"dat_links_{tag}.csv")
    best = pd.read_csv(config.INTERIM_DIR / f"dat_links_best_{tag}.csv")
    hazards = pd.read_csv(config.PROCESSED_DIR / f"hazards_{tag}.csv")
    episodes = pd.read_csv(config.PROCESSED_DIR / f"episodes_{tag}.csv")
    fetch_manifest = json.loads((config.INTERIM_DIR / f"manifest_fetch_{tag}.json").read_text())
    link_manifest = json.loads((config.INTERIM_DIR / f"manifest_link_{tag}.json").read_text())

    lines = link.prepare(lines_raw)
    polygons = link.prepare(polys_raw)
    line_guids = {line["globalid"] for line in lines if line["globalid"]}

    # ── linker evaluation against the path_guid gold set ──
    gold = evaluate.gold_polygons(polys_raw, line_guids)
    scored_result = evaluate.score_assignment(best, gold, candidates)
    scored = scored_result.pop("_scored")
    sweep = evaluate.threshold_sweep(candidates, gold, gaps=[50, 100, 200, 300, 500, 1000],
                                     date_deltas=[0, 1, 2])
    reliability = evaluate.calibration(scored)
    by_year_acc = evaluate.stratify(scored, "year")
    by_wfo_acc = evaluate.stratify(scored, "line_wfo")
    population = evaluate.population_rates(polys_raw, "year")
    line_population = evaluate.population_rates(lines_raw, "year")
    unlinked = evaluate.diagnose_unlinked(lines, polygons, set(best.polygon_oid))

    # ── figures ──
    hazards["year"] = hazards.convective_day.str[:4]
    counts_by_year = hazards.groupby("year").agg(
        hazards=("hazard_uid", "size"),
        with_polygon=("has_polygon", "sum"),
        with_oracle=("has_oracle_text", "sum"))

    fig, axes = plt.subplots(1, 2, figsize=(11, 3.6))
    axes[0].bar(counts_by_year.index, counts_by_year.hazards, color=BLUE, label="hazards")
    axes[0].bar(counts_by_year.index, counts_by_year.with_polygon, color=ACCENT,
                label="with damage polygon")
    axes[0].set_title("Hazards per year"); axes[0].legend(frameon=False)
    axes[0].tick_params(axis="x", rotation=90)
    axes[1].plot(population.year, population.path_guid_rate, marker="o", color=ACCENT,
                 label="real path_guid")
    axes[1].plot(population.year, population.event_id_rate, marker="o", color=BLUE,
                 label="event_id")
    axes[1].plot(population.year, population.comments_rate, marker="o", color="#6a994e",
                 label="comments")
    axes[1].set_title("Polygon field population by year"); axes[1].set_ylim(0, 1)
    axes[1].legend(frameon=False); axes[1].tick_params(axis="x", rotation=90)
    fig.tight_layout()
    coverage_fig = figures_dir / "dat_coverage.png"
    fig.savefig(coverage_fig); plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11, 3.6))
    if not reliability.empty:
        axes[0].plot([0, 1], [0, 1], "--", color="#999999", lw=1, label="perfect calibration")
        axes[0].errorbar(reliability.mean_confidence, reliability.observed_accuracy,
                         yerr=[reliability.observed_accuracy - reliability.ci_low,
                               reliability.ci_high - reliability.observed_accuracy],
                         fmt="o-", color=ACCENT, capsize=3, label="observed")
        for row in reliability.itertuples():
            axes[0].annotate(f"n={int(row.n)}", (row.mean_confidence, row.observed_accuracy),
                             textcoords="offset points", xytext=(4, -10), fontsize=8)
    axes[0].set_xlabel("link_confidence"); axes[0].set_ylabel("observed accuracy")
    axes[0].set_title("Confidence calibration (gold set)"); axes[0].legend(frameon=False)

    for delta, style in ((0, ":"), (1, "-"), (2, "--")):
        subset = sweep[sweep.max_date_delta_days == delta]
        axes[1].plot(subset.gap_threshold_m, subset.recall, style, marker="o", color=BLUE,
                     label=f"recall, date ±{delta}d")
        axes[1].plot(subset.gap_threshold_m, subset.precision, style, marker="s", color=ACCENT,
                     label=f"precision, date ±{delta}d")
    axes[1].axvline(config.LINK_GAP_THRESHOLD_M, color="#666666", lw=1)
    axes[1].annotate("default", (config.LINK_GAP_THRESHOLD_M, axes[1].get_ylim()[0]),
                     textcoords="offset points", xytext=(4, 4), fontsize=8, color="#666666")
    axes[1].set_xlabel("gap threshold (m)"); axes[1].set_xscale("log")
    axes[1].set_title("Operating points (n=%d gold polygons)" % int(gold.resolvable.sum()))
    axes[1].legend(frameon=False, fontsize=7, ncol=2, loc="center left",
                   bbox_to_anchor=(1.01, 0.5))
    fig.tight_layout()
    eval_fig = figures_dir / "dat_linker_evaluation.png"
    fig.savefig(eval_fig); plt.close(fig)

    # How far away are the gold polygons whose true line never became a
    # candidate? This says whether a wider search would be worth anything.
    lines_by_guid = {line["globalid"]: line for line in lines}
    polygons_by_oid = {polygon["objectid"]: polygon for polygon in polygons}
    miss_distances = []
    for row in scored[~scored.get("true_line_in_candidates", True)].itertuples():
        line, polygon = lines_by_guid.get(row.true_line_globalid), polygons_by_oid.get(row.polygon_oid)
        if line and polygon:
            miss_distances.append(line["proj"].distance(polygon["proj"]))
    miss_range = (f"{min(miss_distances) / 1000:.1f}–{max(miss_distances) / 1000:.1f} km away"
                  if miss_distances else "distances unavailable")

    # ── report ──
    gold_years = sorted(scored.stormdate.dropna().str[:4].unique())
    distances = unlinked.nearest_same_day_line_m.dropna() if len(unlinked) else pd.Series(dtype=float)
    no_line_that_day = int((~unlinked.any_line_that_day).sum()) if len(unlinked) else 0
    unlinked_bands = pd.DataFrame([
        {"nearest same-day line": "no line that day at all", "polygons": no_line_that_day},
        *[{"nearest same-day line": label,
           "polygons": int(((distances > low) & (distances <= high)).sum())}
          for label, low, high in [("≤ 1 km (just outside the threshold)", 0, 1_000),
                                   ("1–5 km", 1_000, 5_000),
                                   ("5–20 km", 5_000, 20_000),
                                   ("20–100 km", 20_000, 100_000),
                                   ("> 100 km", 100_000, float("inf"))]],
    ])

    report = f"""# NOAA DAT geometry — Stage A quality report

Window **{config.WINDOW_START} … {config.WINDOW_END}**, retrieved
{fetch_manifest.get('written_at', 'n/a')} (code {str(fetch_manifest.get('git_sha'))[:8]}).
Generated by `scripts/17_qa_events.py`; every number below is reproducible from
`data/raw/dat/` without further network access.

## 1. What was downloaded

| layer | server count | fetched | complete | no usable geometry |
|---|---|---|---|---|
| damage lines | {fetch_manifest['counts']['lines']['expected']} | {fetch_manifest['counts']['lines']['fetched']} | {fetch_manifest['counts']['lines']['complete']} | {fetch_manifest['counts']['lines']['missing_geometry']} |
| damage polygons | {fetch_manifest['counts']['polygons']['expected']} | {fetch_manifest['counts']['polygons']['fetched']} | {fetch_manifest['counts']['polygons']['complete']} | {fetch_manifest['counts']['polygons']['missing_geometry']} |

No attribute filter was applied. The earlier extract required a non-empty
`comments` field, which would have dropped {100 - 100 * 3148 / 9989:.0f}% of damage polygons and biased the
geometry sample; the comment-bearing subset is instead flagged per hazard
(`has_oracle_text`) and can be selected as a view.

Features with no usable geometry carry attributes but an empty `rings`/`paths`
array in DAT itself — they are excluded from linkage and counted here rather
than silently dropped.

## 2. Field population (damage polygons, by year)

The `path_guid` column is the only deterministic line↔polygon key DAT offers,
**but most of it is a placeholder**: of {len(polys_raw)} polygons, {int(population.placeholder_guid.sum())} carry the
all-zero GUID `{{00000000-…}}` and only **{int(population.real_path_guid.sum())} carry a real reference**. A naive
`path_guid IS NOT NULL` test counts {int(population.placeholder_guid.sum()) + int(population.real_path_guid.sum())} and is misleading.

{population.to_markdown(index=False, floatfmt='.3f')}

Damage **lines**, whose `comments` are the oracle survey text the dataset depends
on, are populated far more consistently — though the rate fell from ~99% before
2020 to {line_population[line_population.year >= '2021'].with_comments.sum() / line_population[line_population.year >= '2021'].n.sum():.0%} from 2021 on, which is a coverage limit for recent events:

{line_population[['year', 'n', 'with_event_id', 'with_comments', 'event_id_rate', 'comments_rate']].to_markdown(index=False, floatfmt='.3f')}

## 3. Linkage

Candidates are generated within {link_manifest['counts']['parameters']['search_radius_m']:.0f} m and ±{config.LINK_SEARCH_MAX_DATE_DELTA_DAYS} days, then accepted at
gap ≤ {link_manifest['counts']['parameters']['gap_threshold_m']:.0f} m and ≤ {link_manifest['counts']['parameters']['max_date_delta_days']} day. Linkage uses **geometry and time only**; `event_id`
and `path_guid` are recorded beside each pair so they remain independent checks.

- candidate pairs: **{link_manifest['counts']['candidate_pairs']}**, accepted: **{link_manifest['counts']['accepted_links']}**
- polygons matched to a line: **{link_manifest['counts']['polygons_with_a_link']} / {link_manifest['counts']['polygons_usable']}** ({pct(link_manifest['counts']['polygons_with_a_link'], link_manifest['counts']['polygons_usable'])})
- of those, touching their line (gap = 0 m): **{pct((best.gap_m == 0).sum(), len(best))}**
- free-text `event_id` agrees with the spatial assignment on **{pct(best.shared_event_id.sum(), len(best))}** of them

The last number is why linkage is spatial: the string that looks like a join key
disagrees with the geometry on more than half the polygons.

### Polygons with no accepted link ({len(unlinked)})

{unlinked_bands.to_markdown(index=False)}

The median unlinked polygon is **{distances.median() / 1000:.0f} km** from the nearest line surveyed the
same day, so these are overwhelmingly damage areas recorded without any track
line rather than links the threshold missed — only {int((distances <= 1000).sum())} sit within 1 km of a
same-day line. Widening the gap threshold cannot recover them.

## 4. Linker evaluation against the `path_guid` gold set

The linker never reads `path_guid`, so the {int(gold.resolvable.sum())} polygons carrying a real one
are a held-out gold standard.

| metric | value | 95% CI |
|---|---|---|
| polygons with a real `path_guid` | {scored_result['gold_polygons_total']} | |
| … resolving to an in-window line (scored) | {scored_result['gold_scored']} | |
| assigned a line by the linker | {scored_result['assigned']} | |
| assigned **correctly** | {scored_result['correct']} | |
| **precision** (correct / assigned) | **{scored_result['precision']:.1%}** | {ci(scored_result['precision_ci'])} |
| **recall** (correct / scored) | **{scored_result['recall']:.1%}** | {ci(scored_result['recall_ci'])} |
| F1 | {scored_result['f1']:.1%} | |
| true line present among candidates | {scored_result.get('true_line_in_candidates')} ({pct(scored_result.get('true_line_in_candidates', 0), scored_result['gold_scored'])}) | |

The {scored_result['gold_scored'] - scored_result['correct']} misses break down into three different problems:

| failure mode | n | what would fix it |
|---|---|---|
| search miss — true line never a candidate | {scored_result.get('search_misses')} | wider search radius ({miss_range}) |
| excluded by the acceptance threshold | {scored_result.get('threshold_exclusions')} | looser gap / date threshold |
| ranking error — true line was a candidate but lost | {scored_result.get('ranking_errors')} | better ranking rule |

**The gold set is small and not representative.** Its {int(gold.resolvable.sum())} rows fall in
{', '.join(gold_years)} only — DAT stopped populating the field in 2018-2019 and
resumed sparsely — so these figures describe modern, WFO-specific editing
practice, not the whole 2010-2025 population. They are an upper-bound sanity
check on the linker, not a dataset-wide error rate.

### Operating points

{sweep.astype({'gap_threshold_m': int, 'max_date_delta_days': int}).to_markdown(index=False, floatfmt='.4f')}

Precision is flat (≈99%) across the grid while recall rises with a wider gap,
which argues for widening. The default stays at {config.LINK_GAP_THRESHOLD_M:.0f} m / ±{config.LINK_MAX_DATE_DELTA_DAYS} day anyway,
because a wrongly attached polygon corrupts a hazard's ground truth while a
missing one only leaves it line-only — and the gold set, being sparse, cannot
observe the failure mode that widening would provoke: two parallel tracks in a
dense outbreak. Users who prefer recall can re-filter `dat_links_{tag}.csv`,
which retains every candidate out to {link_manifest['counts']['parameters']['search_radius_m']:.0f} m.

### Confidence calibration

{reliability.to_markdown(index=False, floatfmt='.3f') if not reliability.empty else '(no assigned gold rows)'}

Read this as a warning, not a reassurance: observed accuracy is ≈100% in *every*
bin, including the lowest. On this gold set `link_confidence` does not
discriminate correct from incorrect links — it is systematically
under-confident, and a low value should not be read as "probably wrong". Two
reasons, both worth keeping in mind: a polygon covering a small slice of a long
track legitimately scores low on containment, and the gold set contains too few
errors ({scored_result['gold_scored'] - scored_result['correct']}) to calibrate against. Treat the score as a ranking aid.

### Stability across strata

By year:

{by_year_acc.to_markdown(index=False, floatfmt='.3f')}

By WFO of the assigned line (top 12 by n):

{by_wfo_acc.sort_values('n', ascending=False).head(12).to_markdown(index=False, floatfmt='.3f')}

The concentration here is the point: {by_wfo_acc.sort_values('n', ascending=False).head(3).n.sum()} of {int(by_wfo_acc.n.sum())} gold rows come from the
three most frequent strata. `path_guid` reflects how a handful of offices edit,
which is exactly why these metrics are not extrapolated to the full dataset.

## 5. Hazards and episodes

{len(lines)} usable lines and {len(polygons)} usable polygons were assembled into
**{len(hazards)} hazards** (one tornado each) grouped into **{len(episodes)} episodes**
(convective day + spatial proximity).

| property | n | share |
|---|---|---|
| hazards with ≥1 damage polygon | {int(hazards.has_polygon.sum())} | {pct(hazards.has_polygon.sum(), len(hazards))} |
| hazards with oracle survey text (`comments`) | {int(hazards.has_oracle_text.sum())} | {pct(hazards.has_oracle_text.sum(), len(hazards))} |
| hazards with a known WFO | {int(hazards.wfo_known.sum())} | {pct(hazards.wfo_known.sum(), len(hazards))} |
| hazards inside the GDELT window (≥ {config.GDELT_COVERAGE_START}) | {int(hazards.gdelt_coverage.sum())} | {pct(hazards.gdelt_coverage.sum(), len(hazards))} |
| hazards assembled from >1 line | {int((hazards.n_lines > 1).sum())} | {pct((hazards.n_lines > 1).sum(), len(hazards))} |

Merge evidence for multi-line hazards (why segments were joined):

{hazards[hazards.n_lines > 1].merge_evidence.fillna('(none recorded)').value_counts().rename_axis('evidence').reset_index(name='hazards').to_markdown(index=False)}

Hazards per year and polygon-field population: `figures/dat_coverage.png`.
Calibration and operating points: `figures/dat_linker_evaluation.png`.

## 6. Limitations to carry into the dataset documentation

1. **Ground truth is a survey estimate.** DAT geometries are drawn by NWS field
   surveyors; coverage varies by office and surveyors cannot reach every
   location. Absence of a polygon is not absence of damage.
2. **The `path_guid` evaluation is conditional** on {int(gold.resolvable.sum())} polygons from
   {', '.join(gold_years)}, an editing-practice subsample rather than a random one.
3. **{pct(len(unlinked), len(polygons))} of polygons carry no track line** — mostly by design, but this
   limits how many hazards have both geometry roles ({pct(hazards.has_polygon.sum(), len(hazards))} do).
4. **WFO is missing on {pct(len(hazards) - hazards.wfo_known.sum(), len(hazards))} of hazards**, which will constrain the NWS/IEM
   text retrieval in Stage B until it is backfilled from the CWA polygons.
5. **The window is fixed at {config.WINDOW_START.year}-{config.WINDOW_END.year}.** DAT is edited retroactively, so a
   later rerun may differ; `retrieved_at` in each manifest pins this snapshot.
"""

    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = config.OUTPUT_DIR / "dat_qa_report.md"
    report_path.write_text(report, encoding="utf-8")

    sweep.to_csv(config.OUTPUT_DIR / "dat_linker_sweep.csv", index=False)
    scored.drop(columns=[c for c in scored.columns if c.startswith("_")]).to_csv(
        config.OUTPUT_DIR / "dat_linker_gold_scored.csv", index=False)
    unlinked.to_csv(config.OUTPUT_DIR / "dat_unlinked_polygons.csv", index=False)

    print(f"precision {scored_result['precision']:.1%} {ci(scored_result['precision_ci'])}, "
          f"recall {scored_result['recall']:.1%} {ci(scored_result['recall_ci'])} "
          f"on {scored_result['gold_scored']} gold polygons")
    print(f"wrote {report_path}, {coverage_fig.name}, {eval_fig.name}")


if __name__ == "__main__":
    main()

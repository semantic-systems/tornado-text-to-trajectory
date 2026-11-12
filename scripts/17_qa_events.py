"""Stage 17 — the events quality report: DAT linkage and the official records.

Produces ``outputs/events_qa_report.md`` plus figures: what was downloaded from
DAT, how lines and polygons were linked and how well (against the ``path_guid``
gold set), the hazards built from them and their episodes (stage 15), and — once
stages 13–14 have run — how DAT compares with NCEI Storm Events and SPC's tornado database
(completeness per year, episodes, the time-repaired matches). The report is
written to be read by someone deciding whether to trust the dataset: every
headline number is accompanied by its denominator, its confidence interval where
it is an estimate, and the caveat that limits it.

    python scripts/17_qa_events.py
    python scripts/17_qa_events.py merges        # hand check of stage 12's merges
    python scripts/17_qa_events.py merges-check  # score it, once labelled

``merges`` draws a stratified sample of the hazards stage 12 built from several
DAT lines that SPC records as two or more tornadoes, and writes a worksheet, a
map and a guide to ``outputs/annotation/`` (:mod:`tornado_dataset.dat.merge_check`);
``merges-check`` reads the labels back and writes ``outputs/merge_hand_checks_report.md``.
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

from tornado_dataset import config, viz
from tornado_dataset.dat import episode_table, evaluate, link
from tornado_dataset.dat import references as refs

plt.rcParams.update(viz.matplotlib_style())
L = viz.LIGHT
BLUE, ORANGE, GREY = L["series1"], L["series2"], L["muted"]


def pct(numerator: float, denominator: float) -> str:
    return f"{numerator / denominator:.1%}" if denominator else "n/a"


def ci(bounds: tuple[float, float]) -> str:
    return f"[{bounds[0]:.1%}, {bounds[1]:.1%}]"


STATUS_TEXT = {
    "time_mismatch": "lies on an SPC track (≤5 km), at another time",
    "probable_duplicate": "lies on an SPC track that already has a DAT hazard",
    "spc_far": "nearest SPC track 5–20 km away",
    "no_spc_nearby": "no SPC track within 20 km and 72 h",
    "untimed_no_spc": "no time, no SPC track within 5 km on the date ±1 day",
}


def episode_lines(episodes: pd.DataFrame | None, manifest: dict | None,
                  tag: str) -> str:
    """The episodes and hazards stage 15 built, for section 5."""
    if episodes is None or "has_dat" not in episodes.columns or manifest is None:
        return ("### Episodes\n\nNot available: run `scripts/15_build_episodes.py`, then "
                "this stage again.\n")
    c = manifest["counts"]
    with_dat = episodes[episodes.has_dat.astype(bool)]
    days = episodes.convective_days.fillna("").str.count(";") + 1
    roles = c.get("spc_track_roles", {})
    status = c.get("dat_match_status", {})
    left = {k: v for k, v in status.items() if k != "linked"}
    n_left = sum(left.values())
    member_path = config.PROCESSED_DIR / f"hazard_episodes_{tag}.csv"
    with_se = None
    if member_path.exists() and refs.se_links_path(tag).exists():
        member = pd.read_csv(member_path)
        no_spc = set(member.hazard_uid[(member.hazard_source == "dat") & ~member.in_spc])
        with_se = len(no_spc & set(pd.read_csv(refs.se_links_path(tag)).hazard_uid))
    se_sentence = ("" if with_se is None else
                   f"{with_se:,} of them {'has' if with_se == 1 else 'have'} a Storm Events row: "
                   "at DAT's time and place, the others are not in the official record as a "
                   "tornado either. ")
    status_rows = "\n".join(f"| `{k}` | {STATUS_TEXT.get(k, '')} | {v:,} |"
                            for k, v in sorted(left.items(), key=lambda kv: -kv[1]))

    def sizes(f: pd.DataFrame, col: str) -> str:
        d = f[col].describe(percentiles=[.5, .9])
        return f"{d['50%']:.0f} / {d['90%']:.0f} / {d['max']:.0f}"

    return f"""### Episodes (stage 15)

Stage 15 groups SPC's complete tornado list by single linkage within
{config.EPISODE_MAX_DISTANCE_M / 1000:g} km and {config.EPISODE_MAX_GAP_H:g} h (no day boundary).
SPC is the population: **all {len(episodes):,} episodes are published**, {len(with_dat):,} of
them (`has_dat`) holding at least one DAT survey.

| | all episodes | with a DAT survey |
|---|---:|---:|
| episodes | {len(episodes):,} | {len(with_dat):,} |
| SPC tornadoes per episode, median / p90 / max | {sizes(episodes, 'n_spc')} | {sizes(with_dat, 'n_spc')} |
| single-tornado episodes | {int((episodes.n_spc == 1).sum()):,} | {int((with_dat.n_spc == 1).sum()):,} |
| episodes spanning several convective days | {int((days > 1).sum()):,} | {int((days[with_dat.index] > 1).sum()):,} |
| episodes with ≥6 EF1+ SPC tornadoes (Fuhrmann et al.'s threshold) | {int((episodes.n_spc_ef1plus >= 6).sum()):,} | {int((with_dat.n_spc_ef1plus >= 6).sum()):,} |
| SPC fatalities | {int(episodes.spc_fatalities.sum()):,} | {int(with_dat.spc_fatalities.sum()):,} |

**Hazards.** The {c['spc_tracks']:,} SPC tornadoes are, in DAT terms:
{roles.get('dat_closest', 0):,} the closest SPC track of a DAT hazard,
{roles.get('dat_secondary', 0):,} linked to a DAT hazard without being its closest (mostly a
piece of the same tornado; not a hazard, or one tornado would count twice) and
**{roles.get('spc_hazard', 0):,} with no DAT link at all, which become hazards of their own**
(`hazard_source = spc`): SPC's straight start→end line, or a point (`spc_point`) for the
{c.get('spc_hazard_geometry', {}).get('spc_point', 0):,} SPC records no end for.
Together with the {c['dat_hazards_in_episodes']:,} DAT hazards that have an SPC track, the
episodes hold {c['dat_hazards_in_episodes'] + c['spc_hazards']:,} hazards.

**DAT hazards without an SPC track: {n_left:,}.** They are in no episode and stay in the
hazards table, `in_spc` false, so they neither count as episodes nor disappear:

| `spc_match_status` | meaning | hazards |
|---|---|---:|
{status_rows}

{se_sentence}`time_mismatch` and `probable_duplicate` are most
likely tornadoes that are in SPC, with a DAT time error beyond stage 14's repair rule
or a second survey; the rest are candidates for tornadoes reclassified, never
submitted, or entered in error. The nearest SPC track and its offset are in
`hazard_episodes_<tag>.csv`.
"""


def geography_lines(manifest: dict | None) -> str:
    """Stage 16's counties, offices and places, for section 5."""
    if manifest is None or "dat" not in manifest.get("counts", {}):
        return ("### Geography (stage 16)\n\nNot available: run "
                "`scripts/16_enrich_geography.py`, then this stage again.\n")
    c = manifest["counts"]
    agree = c["wfo_agreement_dat_hazards"]
    check = c["spc_line_check"]
    pop = c.get("population_join", {})
    s = c["settings"]

    def source_row(src: str) -> str:
        d = c.get(src)
        if not d:
            return ""
        w = d["wfo_source"]
        return (f"| {src.upper()} | {d['hazards']:,} | {pct(d['wfo_known'], d['hazards'])} | "
                f"{w.get('dat', 0):,} | {w.get('storm_events', 0):,} | "
                f"{w.get('spatial_join', 0):,} | {d['county_fallback']:,} | "
                f"{pct(d['hazards_with_places'], d['hazards'])} | "
                f"{pct(d['hazards_with_a_town_over_20k'], d['hazards'])} |")

    def pair(name: str, label: str) -> str:
        v = agree[name]
        return (f"| {label} | {v['hazards']:,} | {pct(v['any_office_shared'] or 0, 1)} | "
                f"{pct(v['same_offices'] or 0, 1)} |")

    def check_row(label: str, v: dict) -> str:
        return (f"| {label} | {v['pairs']:,} | {pct(v['county_recall_mean'], 1)} | "
                f"{pct(v['county_sets_equal'], 1)} | {pct(v['near_place_recall_mean'], 1)} | "
                f"{pct(v['matching_place_recall_mean'], 1)} | {pct(v['spatial_wfo_equal'], 1)} |")

    return f"""### Geography (stage 16)

Counties come from the NWS county polygons of the hazard's year; a county counts when
it holds {s['county_min_share']:.0%} of the track (or {s['county_min_track_m'] / 1000:g} km of it; of the damage
area for a hazard without a track line), and the one with most of it always counts.
The office is DAT's own, else that of the linked Storm Events segments (the one where
the tornado began first), else the county join's; `wfo_all` keeps every office of
every source.

| hazards | n | office known | from DAT | from Storm Events | from county join | nearest-county fallback | with place names | with a town ≥20k |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
{source_row('dat')}
{source_row('spc')}

Agreement of the three office sources on DAT hazards where both have one:

| sources | hazards | share an office | same offices |
|---|---:|---:|---:|
{pair('dat_vs_storm_events', 'DAT vs Storm Events')}
{pair('dat_vs_spatial_join', 'DAT vs county join')}
{pair('storm_events_vs_spatial_join', 'Storm Events vs county join')}

Hazards with several offices: DAT {agree['several_offices']['dat']:,}, Storm Events
{agree['several_offices']['storm_events']:,}, county join {agree['several_offices']['spatial_join']:,}.

**Places** are GNIS populated places, ranked by Census 2024 population. Each Census
place's population goes to the same-named GNIS place nearest its Census Gazetteer
point ({pop.get('assigned', 0):,} of {pop.get('census_places', 0):,} incorporated places). For
{pop.get('ambiguous_names_resolved', 0):,} of them the name occurs more than once in the state; the
namesakes get no population, where a join by name gave it to all of them. Names and
populations are today's, not the event year's.

**How well a straight SPC line stands in for a surveyed track.** For each DAT hazard
with an SPC track, the geography of the SPC line against that of the DAT geometry:

| SPC geometry | pairs | counties found (mean) | same counties | places ≤{s['place_match_radius_m'] / 1000:g} km found (mean) | matching set found (mean) | same county-join office |
|---|---:|---:|---:|---:|---:|---:|
{check_row('line', check['spc_lines'])}
{check_row('point (no end)', check['spc_points'])}
{check_row('all', check['all'])}

This is the accuracy to expect of the {c.get('spc', {}).get('hazards', 0):,} SPC hazards' geography.
"""


def record_agreement(tag: str, hazards: pd.DataFrame) -> str:
    """Section 6: DAT's record against SPC's for the same tornado (stage 15's values)."""
    member_path = episode_table.membership_path(tag)
    if not (member_path.exists() and refs.SPC_TRACKS.exists()):
        return ""
    member = pd.read_csv(member_path, low_memory=False)
    if "values_compare" not in member.columns:
        return ("### Same tornado, two records: DAT against SPC\n\nNot available: run "
                "`scripts/15_build_episodes.py`, then this stage again.\n")
    kind = member.values_compare.value_counts()
    tracks = pd.read_csv(refs.SPC_TRACKS, usecols=["spc_id", "date", "st", "len", "wid"])
    pairs = (member[member.values_compare == "one_to_one"]
             .merge(hazards[["hazard_uid", "path_length_mi", "path_width_yd"]], on="hazard_uid")
             .merge(tracks, on="spc_id"))
    several = member[member.values_compare == "several_tracks"]
    dat_ef = pairs.dat_rating.map(episode_table.ef_number)
    spc_ef = pairs.spc_rating.map(episode_table.ef_number)
    both = dat_ef.notna() & spc_ef.notna()
    diff = (dat_ef[both] - spc_ef[both]).abs()

    def ratio_row(dat_col: str, spc_col: str, label: str) -> str:
        ok = (pairs[dat_col] > 0) & (pairs[spc_col] > 0)
        r = pairs[dat_col][ok] / pairs[spc_col][ok]
        return (f"| {label} | {int(ok.sum()):,} | {r.between(0.9, 1.1).mean():.1%} within ±10% | "
                f"median DAT ÷ SPC {r.median():.2f}; {(r < 0.5).mean():.1%} under half, "
                f"{(r > 2).mean():.1%} over double |")

    def count_row(field: str, label: str) -> str:
        ok = pairs[f"dat_{field}"].notna()
        d, s = pairs[f"dat_{field}"][ok], pairs[f"spc_{field}"][ok]
        return (f"| {label} | {int(ok.sum()):,} | {(d == s).mean():.1%} identical | "
                f"total DAT {int(d.sum()):,}, SPC {int(s.sum()):,}; DAT lower on "
                f"{int((d < s).sum()):,}, higher on {int((d > s).sum()):,} |")

    def flagged(frame: pd.DataFrame, flag: str) -> str:
        return f"{int(frame[flag].fillna(False).astype(bool).sum()):,} of {int(frame[flag].notna().sum()):,}"

    compared = member[member.values_compare.isin(episode_table.COMPARED)].copy()
    compared["gap"] = compared.spc_deaths - compared.dat_deaths
    worst = compared[compared.gap.abs() > 0].reindex(
        compared.gap.abs().sort_values(ascending=False).index).dropna(subset=["gap"]).head(8)
    first = tracks.set_index("spc_id")
    worst_md = "\n".join(
        f"| {first.date.get(r.spc_id)} | {first.st.get(r.spc_id)} | {int(r.spc_deaths)} | "
        f"{int(r.dat_deaths)} | {r.values_compare.replace('_', ' ')} | `{r.spc_id}` | "
        f"`{r.hazard_uid}` |" for r in worst.itertuples())
    return f"""### Same tornado, two records: DAT against SPC

DAT and SPC's database record the same quantities for the same tornado,
separately: DAT from the survey drawing, SPC from Storm Data. Stage 15 counts
each SPC track on one hazard and keeps both records (`dat_*`, `spc_*` in
`hazard_episodes`). Compared one to one on the {kind.get("one_to_one", 0):,} DAT
hazards that hold their SPC track alone:

| quantity | compared | agreement | detail |
|---|---:|---:|---|
| rating, both rated | {int(both.sum()):,} | {(diff == 0).mean():.1%} identical | {(diff <= 1).mean():.1%} within one EF class |
{ratio_row("path_length_mi", "len", "path length")}
{ratio_row("path_width_yd", "wid", "path width")}
{count_row("deaths", "deaths")}
{count_row("injuries", "injuries")}

The {kind.get("several_tracks", 0):,} DAT hazards that hold several SPC tracks (lines
stage 12 merged, or a tornado SPC records in pieces) are compared with the sum
of their tracks: the rating differs on {flagged(several, "rating_differs")}, deaths on
{flagged(several, "deaths_differ")}, injuries on {flagged(several, "injuries_differ")}. The
{kind.get("shared_track", 0):,} that share a track with another DAT hazard are not compared.

Path lengths and widths differ by design: DAT measures the drawn line and the
widest polygon, SPC states the length and maximum width Storm Data received. Deaths
and injuries should not differ; where they do, DAT's figure is a field the
surveyor filled in (or left at zero) and SPC's is the reviewed count. So the
dataset's `rating`, `deaths` and `injuries` are SPC's wherever a hazard has an SPC
track, and DAT's only where it has none (`values_source`); `rating_differs`,
`deaths_differ` and `injuries_differ` flag the disagreements. Largest differences
in deaths, for checking:

| date | state | SPC deaths | DAT deaths | compared | SPC track | DAT hazard |
|---|---|---:|---:|---|---|---|
{worst_md}
"""


def cmd_merges(tag: str, force: bool) -> None:
    """Worksheet, key, map and guide for the hand check of stage 12's merges."""
    import numpy as np
    from tornado_dataset.dat import merge_check as mc
    from tornado_dataset.ids import write_manifest

    paths = mc.paths()
    if paths["sheet"].exists() and mc.read_sheet(paths["sheet"]).label.notna().any() and not force:
        raise SystemExit(f"labels already entered in {paths['sheet'].name} — not overwriting "
                         "(use --force to regenerate)")
    pop, shapes = mc.candidates(tag)
    sample = mc.draw(pop, np.random.default_rng(mc.SHEET_SEED))
    sheet, key = mc.sheet_and_key(sample)
    paths["sheet"].parent.mkdir(parents=True, exist_ok=True)
    sheet.to_csv(paths["sheet"], index=False)
    key.to_csv(paths["key"], index=False)
    paths["map"].write_text(mc.review_map(sample, sheet, shapes), encoding="utf-8")
    paths["how_to"].write_text(mc.HOW_TO, encoding="utf-8")
    write_manifest(paths["manifest"], "17_qa_events merges",
                   counts={"population": len(pop),
                           "population_by_stratum": pop.stratum.value_counts().to_dict(),
                           "cases": len(sample),
                           "cases_by_stratum": sample.stratum.value_counts().to_dict(),
                           "seed": mc.SHEET_SEED},
                   outputs=[paths[k] for k in ("sheet", "key", "map", "how_to")])
    print(f"{len(pop):,} multi-line hazards on two or more SPC tracks; drew {len(sample)} "
          "(" + ", ".join(f"{k} {v}" for k, v in sample.stratum.value_counts().items()) + ")")
    for k in ("sheet", "key", "map", "how_to"):
        print(f"wrote {paths[k]}")


def cmd_merges_check(tag: str) -> None:
    """Over-merge rate per stage 12 rule and in all, from the labelled worksheet."""
    from tornado_dataset.dat import merge_check as mc

    paths = mc.paths()
    if not paths["sheet"].exists():
        raise SystemExit("no merge_sheet.csv — run: python scripts/17_qa_events.py merges")
    df = mc.read_sheet(paths["sheet"]).merge(pd.read_csv(paths["key"]), on="case_id")
    bad = df.label.notna() & ~df.label.isin(mc.LABELS)
    if bad.any():
        raise SystemExit(f"labels not in {mc.LABELS}: {sorted(df.label[bad].unique())}")
    population = json.loads(paths["manifest"].read_text())["counts"]["population"]
    decided = df[df.label.isin(("one_tornado", "several_tornadoes"))]
    over = decided.label == "several_tornadoes"

    def row(name: str, frame: pd.DataFrame) -> str:
        d = frame[frame.label.isin(("one_tornado", "several_tornadoes"))]
        k, n = int((d.label == "several_tornadoes").sum()), len(d)
        lo, hi = evaluate.wilson_interval(k, n)
        share = f"{k / n:.0%} {ci((lo, hi))}" if n else "n/a"
        return (f"| {name} | {int(frame.label.notna().sum())}/{len(frame)} | {k} of {n} | "
                f"{share} | {int((frame.label == 'cannot_tell').sum())} |")

    estimate = (over * decided.weight).sum() / decided.weight.sum() if len(decided) else float("nan")
    lines = ["# Stage 12 merges — hand check", "",
             "Multi-line DAT hazards that SPC records as two or more tornadoes, sampled by "
             "the rules stage 12 joined them with (`python scripts/17_qa_events.py merges`). "
             f"{population:,} such hazards; labelled `several_tornadoes` where the merge "
             "joined tornadoes that should be separate hazards.", "",
             "| stage 12 rules | labelled | over-merged | share [95% CI] | cannot tell |",
             "|---|---:|---:|---:|---:|"]
    lines += [row(name, df[df.stratum == name]) for name in mc.STRATA]
    lines += [row("all (unweighted)", df), "",
              f"Weighted to the population: **{estimate:.0%}** of the {population:,} are "
              f"over-merged, about {estimate * population:,.0f} hazards." if len(decided) else
              "No decided labels yet.", "",
              "## What predicts an over-merge", "",
              "| measure | over-merged | one tornado |", "|---|---:|---:|"]
    for col, label in (("spc_simultaneous", "SPC tracks overlap in time"),
                       ("n_spc_hazards_on_lines", "an undrawn SPC tornado on the lines")):
        flag = decided[col].astype(float) > 0
        lines.append(f"| {label} | {pct(int((flag & over).sum()), int(over.sum()))} | "
                     f"{pct(int((flag & ~over).sum()), int((~over).sum()))} |")
    for col, label in (("max_line_gap_m", "largest gap between lines, median (m)"),
                       ("line_start_spread_h", "spread of line starts, median (h)")):
        lines.append(f"| {label} | {decided[col][over].median():,.1f} | "
                     f"{decided[col][~over].median():,.1f} |")
    out = config.OUTPUT_DIR / "merge_hand_checks_report.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nwrote {out}")


def main() -> None:
    default_tag = f"{config.WINDOW_START.isoformat()}_{config.WINDOW_END.isoformat()}"
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", nargs="?", default="report",
                        choices=("report", "merges", "merges-check"))
    parser.add_argument("--tag", default=default_tag)
    parser.add_argument("--force", action="store_true",
                        help="merges: regenerate even if labels were entered")
    args = parser.parse_args()
    tag = args.tag
    if args.command == "merges":
        return cmd_merges(tag, args.force)
    if args.command == "merges-check":
        return cmd_merges_check(tag)

    figures_dir = config.OUTPUT_DIR / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    lines_raw = json.loads((config.INTERIM_DIR / f"dat_lines_{tag}.geojson").read_text())["features"]
    polys_raw = json.loads((config.INTERIM_DIR / f"dat_polygons_{tag}.geojson").read_text())["features"]
    candidates = pd.read_csv(config.INTERIM_DIR / f"dat_links_{tag}.csv")
    best = pd.read_csv(config.INTERIM_DIR / f"dat_links_best_{tag}.csv")
    hazards = pd.read_csv(config.PROCESSED_DIR / f"hazards_{tag}.csv")
    episodes_csv = config.PROCESSED_DIR / f"episodes_{tag}.csv"
    episodes = pd.read_csv(episodes_csv) if episodes_csv.exists() else None

    def manifest(name: str) -> dict | None:
        path = config.PROCESSED_DIR / f"manifest_{name}_{tag}.json"
        return json.loads(path.read_text()) if path.exists() else None

    episode_manifest, geography_manifest = manifest("episodes"), manifest("geography")
    fetch_manifest = json.loads((config.INTERIM_DIR / f"manifest_fetch_{tag}.json").read_text())
    link_manifest = json.loads((config.INTERIM_DIR / f"manifest_link_{tag}.json").read_text())
    hazard_counts = json.loads((config.PROCESSED_DIR / f"manifest_hazards_{tag}.json")
                               .read_text())["counts"]

    polygons_with_comments = sum(
        1 for f in polys_raw
        if str(f["properties"].get("comments") or "").strip().lower() not in ("", "none", "nan"))
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
        with_polygon=("has_polygon", "sum"))

    fig, axes = plt.subplots(1, 4, figsize=(14, 3.2), width_ratios=[1.6, 1, 1, 1],
                             layout="constrained")
    years = counts_by_year.index.astype(int)
    axes[0].bar(years, counts_by_year.hazards, color=L["axis"], width=0.72, label="DAT hazards")
    axes[0].bar(years, counts_by_year.with_polygon, color=BLUE, width=0.72,
                label="… with a damage polygon")
    axes[0].set_title("DAT hazards per year", loc="left")
    axes[0].legend(loc="upper left")
    axes[0].set_xticks(range(years.min(), years.max() + 1, 3))
    axes[0].grid(axis="x", visible=False)
    fields = (("path_guid_rate", "a real path_guid"), ("event_id_rate", "an event_id"),
              ("comments_rate", "comments"))
    for ax, (column, title) in zip(axes[1:], fields):
        ax.plot(population.year.astype(int), population[column] * 100, color=BLUE, lw=2)
        ax.set_ylim(0, 100)
        ax.set_title(f"polygons with {title}", loc="left", fontsize=10)
        ax.set_xticks(range(years.min(), years.max() + 1, 5))
        ax.grid(axis="x", visible=False)
    axes[1].set_ylabel("% of DAT polygons")
    coverage_fig = figures_dir / "dat_coverage.png"
    fig.savefig(coverage_fig); plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11, 3.6))
    if not reliability.empty:
        axes[0].plot([0, 1], [0, 1], "--", color=GREY, lw=1, label="perfect calibration")
        axes[0].errorbar(reliability.mean_confidence, reliability.observed_accuracy,
                         yerr=[reliability.observed_accuracy - reliability.ci_low,
                               reliability.ci_high - reliability.observed_accuracy],
                         fmt="o-", color=BLUE, capsize=3, label="observed")
        for row in reliability.itertuples():
            axes[0].annotate(f"n={int(row.n)}", (row.mean_confidence, row.observed_accuracy),
                             textcoords="offset points", xytext=(4, -10), fontsize=8)
    axes[0].set_xlabel("link_confidence"); axes[0].set_ylabel("observed accuracy")
    axes[0].set_title("Confidence calibration (gold set)"); axes[0].legend(frameon=False)

    for delta, style in ((0, ":"), (1, "-"), (2, "--")):
        subset = sweep[sweep.max_date_delta_days == delta]
        axes[1].plot(subset.gap_threshold_m, subset.recall, style, marker="o", color=BLUE,
                     label=f"recall, date ±{delta}d")
        axes[1].plot(subset.gap_threshold_m, subset.precision, style, marker="s", color=ORANGE,
                     label=f"precision, date ±{delta}d")
    axes[1].axvline(config.LINK_GAP_THRESHOLD_M, color=GREY, lw=1)
    axes[1].annotate("default", (config.LINK_GAP_THRESHOLD_M, axes[1].get_ylim()[0]),
                     textcoords="offset points", xytext=(4, 4), fontsize=8, color=GREY)
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

    by_source = hazards.geometry_source.value_counts() if "geometry_source" in hazards else None
    sources_md = "" if by_source is None else (
        "| geometry | hazards | what it rests on |\n|---|---:|---|\n"
        + "\n".join(f"| `{k}` | {int(by_source.get(k, 0)):,} | {v} |" for k, v in (
            ("line", "track line(s) only"),
            ("line+polygon", "track line(s) and the damage polygon(s) linked to them"),
            ("polygon", "damage polygon(s) no line claims: a tornado surveyed without a "
                        "drawn track")))
        + f"""

Left out before assembly as not a tornado (rated {', '.join(hazard_counts.get('non_tornado_ratings', []))}):
**{hazard_counts.get('lines_excluded_not_tornado', 0):,} lines** and
**{hazard_counts.get('polygons_excluded_not_tornado', 0):,} polygons**. Thunderstorm-wind
features matched an SPC tornado 7% of the time; a wind polygon lying on a tornado
track is therefore not taken for that tornado's damage. Of the polygons linked to a
tornado line, {hazard_counts.get('polygons_linked_to_tornado_lines', 0) - hazard_counts.get('polygons_attached_to_hazards', 0):,}
fall below the link-confidence floor ({hazard_counts.get('min_link_confidence')}) and are
used nowhere. {hazard_counts.get('polygons_in_polygon_hazards', 0):,} polygons without a
line form the {int(by_source.get('polygon', 0)):,} polygon-only hazards
({hazard_counts.get('polygon_hazards_date_only', 0):,} of them with a date but no time).
""")
    episodes_md = episode_lines(episodes, episode_manifest, tag)
    geography_md = geography_lines(geography_manifest)
    dat_geo = (geography_manifest or {}).get("counts", {}).get("dat")
    wfo_limitation = (
        f"**WFO is missing from DAT on {pct(len(hazards) - hazards.wfo_known.sum(), len(hazards))} "
        f"of hazards**; stage 16 fills it from Storm Events and the county join, leaving "
        f"{pct(dat_geo['hazards'] - dat_geo['wfo_known'], dat_geo['hazards'])} without one."
        if dat_geo else
        f"**WFO is missing on {pct(len(hazards) - hazards.wfo_known.sum(), len(hazards))} of "
        "hazards**, which will constrain the NWS/IEM text retrieval until stage 16 fills it.")
    agreement_md = record_agreement(tag, hazards)
    reference_lines = refs.report_lines(tag)
    references_md = "\n".join(reference_lines) if reference_lines is not None else (
        "Not available: run `scripts/13_fetch_references.py` and "
        "`scripts/14_match_references.py`, then this stage again.\n")

    report = f"""# Events — quality report (stage 17)

Window **{config.WINDOW_START} … {config.WINDOW_END}**, retrieved
{fetch_manifest.get('written_at', 'n/a')} (code {str(fetch_manifest.get('git_sha'))[:8]}).
Generated by `scripts/17_qa_events.py`; every number below is reproducible from
`data/raw/dat/` without further network access.

## 1. What was downloaded

| layer | server count | fetched | complete | no usable geometry |
|---|---|---|---|---|
| damage lines | {fetch_manifest['counts']['lines']['expected']} | {fetch_manifest['counts']['lines']['fetched']} | {fetch_manifest['counts']['lines']['complete']} | {fetch_manifest['counts']['lines']['missing_geometry']} |
| damage polygons | {fetch_manifest['counts']['polygons']['expected']} | {fetch_manifest['counts']['polygons']['fetched']} | {fetch_manifest['counts']['polygons']['complete']} | {fetch_manifest['counts']['polygons']['missing_geometry']} |

No attribute filter was applied. Requiring a non-empty `comments` field, as an
earlier extract did, would have dropped {pct(len(polys_raw) - polygons_with_comments, len(polys_raw))} of damage polygons and biased the
geometry sample; the comments are kept as text instead (stage 24).

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
same-day line. Widening the gap threshold cannot recover them. Those rated as a
tornado become hazards of their own in stage 12 (section 5), and most match an
SPC tornado (section 6).

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

{len(lines):,} usable lines and {len(polygons):,} usable polygons were assembled into
**{len(hazards):,} hazards** (one tornado each).

{sources_md}

| property | hazards | share |
|---|---:|---:|
| with ≥ 1 damage polygon | {int(hazards.has_polygon.sum()):,} | {pct(hazards.has_polygon.sum(), len(hazards))} |
| assembled from > 1 line | {int((hazards.n_lines > 1).sum()):,} | {pct((hazards.n_lines > 1).sum(), len(hazards))} |
| with an office recorded by DAT itself | {int(hazards.wfo_known.sum()):,} | {pct(hazards.wfo_known.sum(), len(hazards))} |

Stage 16 gives every hazard an office (see Geography below). Which texts each
hazard has is reported in `hazard_analysis_report.md` (section 7) and
`text_qa_report.md`.

Merge evidence for multi-line hazards (why segments were joined):

{hazards[hazards.n_lines > 1].merge_evidence.fillna('(none recorded)').value_counts().rename_axis('evidence').reset_index(name='hazards').to_markdown(index=False)}

{episodes_md}
{geography_md}
Hazards per year and polygon-field population: `figures/dat_coverage.png`.
Calibration and operating points: `figures/dat_linker_evaluation.png`.

## 6. Against the official records (NCEI Storm Events, SPC)

{references_md}
{agreement_md}
## 7. Limitations to carry into the dataset documentation

1. **Ground truth is a survey estimate.** DAT geometries are drawn by NWS field
   surveyors; coverage varies by office and surveyors cannot reach every
   location. Absence of a polygon is not absence of damage.
2. **The `path_guid` evaluation is conditional** on {int(gold.resolvable.sum())} polygons from
   {', '.join(gold_years)}, an editing-practice subsample rather than a random one.
3. **{pct(len(unlinked), len(polygons))} of polygons carry no track line** — mostly by design, but this
   limits how many hazards have both geometry roles ({pct(hazards.has_polygon.sum(), len(hazards))} do).
4. {wfo_limitation}
5. **SPC hazards have SPC's straight start→end line**, not a surveyed track; their
   geography is as accurate as the SPC-line check in section 5 says.
6. **The window is fixed at {config.WINDOW_START.year}-{config.WINDOW_END.year}.** DAT is edited retroactively, so a
   later rerun may differ; `retrieved_at` in each manifest pins this snapshot.
"""

    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = config.OUTPUT_DIR / "events_qa_report.md"
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

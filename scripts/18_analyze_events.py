"""Stage 18 — descriptive analysis of the assembled hazard dataset.

Writes `outputs/hazard_analysis_report.md` and figures describing what the
dataset contains: how many tornadoes and outbreaks per year, how they are rated,
when in the year and the day they happen, how long their tracks are, what they
cost in lives, where they cluster, and how well each text source covers them.

Every count here is a property of the *dataset*, not of US tornado climatology:
DAT holds what NWS offices surveyed and drew, and that effort has grown over the
period. The report says so where it matters.

    python scripts/18_analyze_events.py
"""

from __future__ import annotations

import argparse
import json

import _bootstrap  # noqa: F401

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from tornado_dataset import config, viz
from tornado_dataset.dat.geometry import to_shapely

plt.rcParams.update(viz.matplotlib_style())
L = viz.LIGHT


def annotate_last(ax, x, y, label: str, colour: str) -> None:
    """Direct-label a series at its endpoint instead of on every point."""
    ax.annotate(f" {label}", (x[-1], y[-1]), color=colour, fontsize=9,
                fontweight="bold", va="center", ha="left",
                xycoords="data", annotation_clip=False)


def main() -> None:
    default_tag = f"{config.WINDOW_START.isoformat()}_{config.WINDOW_END.isoformat()}"
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", default=default_tag)
    args = parser.parse_args()

    figures = config.OUTPUT_DIR / "figures"
    figures.mkdir(parents=True, exist_ok=True)

    hazards = pd.read_csv(config.PROCESSED_DIR / f"hazards_{args.tag}.csv")
    episodes = pd.read_csv(config.PROCESSED_DIR / f"episodes_{args.tag}.csv")
    geography = pd.read_csv(config.PROCESSED_DIR / f"hazard_geography_{args.tag}.csv")
    features = json.loads(
        (config.PROCESSED_DIR / f"hazards_{args.tag}.geojson").read_text())["features"]

    hazards["ef"] = hazards.efscale.map(viz.ef_class)
    hazards["year"] = hazards.convective_day.str[:4].astype("Int64")
    hazards["month"] = hazards.convective_day.str[5:7].astype("Int64")
    begin = pd.to_datetime(hazards.time_begin_utc, errors="coerce", format="ISO8601", utc=True)
    hazards["hour_utc"] = begin.dt.hour + begin.dt.minute / 60
    episodes["year"] = episodes.convective_day.str[:4].astype("Int64")

    # Track midpoints, for the diurnal correction and the density map.
    centroids = {}
    for feature in features:
        geom = to_shapely(feature.get("geometry"))
        if geom is not None and not geom.is_empty:
            point = geom.centroid
            centroids[feature["properties"]["hazard_uid"]] = (point.x, point.y)
    hazards["lon"] = hazards.hazard_uid.map(lambda u: centroids.get(u, (np.nan,) * 2)[0])
    hazards["lat"] = hazards.hazard_uid.map(lambda u: centroids.get(u, (np.nan,) * 2)[1])
    # Solar-time correction: a UTC hour histogram smears the diurnal cycle across
    # four US time zones, which is the one thing this figure is meant to show.
    hazards["hour_solar"] = (hazards.hour_utc + hazards.lon / 15.0) % 24

    # ── figure 1: counts per year ──
    per_year = pd.DataFrame({
        "hazards": hazards.groupby("year").size(),
        "episodes": episodes.groupby("year").size(),
    }).fillna(0)
    fig, ax = plt.subplots(figsize=(7.6, 3.6))
    x = per_year.index.astype(int).tolist()
    ax.plot(x, per_year.hazards, lw=2, color=L["series1"], marker="o", ms=4)
    ax.plot(x, per_year.episodes, lw=2, color=L["series2"], marker="o", ms=4)
    annotate_last(ax, x, per_year.hazards.tolist(), "tornado tracks", L["series1"])
    annotate_last(ax, x, per_year.episodes.tolist(), "episodes", L["series2"])
    ax.set_title("Surveyed tornado tracks and episodes per year")
    ax.set_ylabel("count")
    ax.set_xlim(min(x) - 0.4, max(x) + 2.6)
    ax.set_ylim(0, None)
    ax.legend(["tornado tracks", "episodes"], loc="upper left")
    fig.savefig(figures / "hz_counts_per_year.png")
    plt.close(fig)

    # ── figure 2: EF distribution + strength mix over time ──
    order = viz.EF_CLASSES + [viz.UNRATED]
    counts = hazards.ef.value_counts().reindex(order).fillna(0)
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.6), width_ratios=[1, 1.35])
    labels = [viz.EF_CLASS_LABELS.get(k, "unrated") for k in order]
    # One series, one colour: the bar length is the magnitude, so colouring each
    # bar by its own value would double-encode. Unrated is grey, not a ramp step.
    bar_colours = [L["series1"] if k in viz.EF_CLASSES else L["unrated"] for k in order]
    bars = axes[0].bar(labels, counts.values, color=bar_colours, width=0.68)
    for bar, value in zip(bars, counts.values):
        axes[0].annotate(f"{int(value):,}", (bar.get_x() + bar.get_width() / 2, value),
                         ha="center", va="bottom", fontsize=9, color=L["secondary"])
    axes[0].set_title("Rating distribution")
    axes[0].set_ylabel("tornado tracks")
    axes[0].set_ylim(0, counts.max() * 1.15)
    axes[0].grid(axis="x", visible=False)

    # Strength mix per year: share of each ordered class, ordinal ramp.
    mix = (hazards[hazards.ef != viz.UNRATED].groupby(["year", "ef"]).size()
           .unstack(fill_value=0).reindex(columns=viz.EF_CLASSES, fill_value=0))
    share = mix.div(mix.sum(axis=1), axis=0) * 100
    bottom = np.zeros(len(share))
    for ef in viz.EF_CLASSES:
        axes[1].bar(share.index.astype(int), share[ef], bottom=bottom, width=0.72,
                    color=viz.ef_colour(ef), label=viz.EF_CLASS_LABELS[ef],
                    edgecolor=L["surface"], linewidth=1.2)
        bottom += share[ef].values
    axes[1].set_title("Rating mix per year (share of rated tracks)")
    axes[1].set_ylabel("% of rated tracks")
    axes[1].set_ylim(0, 100)
    axes[1].grid(axis="x", visible=False)
    axes[1].legend(ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.16))
    fig.savefig(figures / "hz_ef_distribution.png")
    plt.close(fig)

    # ── figure 3: seasonality and time of day ──
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.4))
    by_month = hazards.groupby("month").size().reindex(range(1, 13), fill_value=0)
    axes[0].bar(range(1, 13), by_month.values, color=L["series1"], width=0.68)
    axes[0].set_xticks(range(1, 13))
    axes[0].set_xticklabels(["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"])
    axes[0].set_title("Season")
    axes[0].set_ylabel("tornado tracks")
    axes[0].grid(axis="x", visible=False)

    hours = hazards.hour_solar.dropna()
    axes[1].hist(hours, bins=np.arange(0, 25, 1), color=L["series1"], rwidth=0.88)
    axes[1].set_xticks(range(0, 25, 3))
    axes[1].set_xlabel("hour of day (local solar time)")
    axes[1].set_title("Time of day")
    axes[1].set_ylabel("tornado tracks")
    axes[1].grid(axis="x", visible=False)
    fig.savefig(figures / "hz_seasonality.png")
    plt.close(fig)

    # ── figure 4: track geometry ──
    lengths = hazards.path_length_mi.dropna()
    lengths = lengths[lengths > 0]
    widths = hazards.path_width_yd.dropna()
    widths = widths[widths > 0]
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.4))
    axes[0].hist(lengths, bins=np.logspace(np.log10(0.05), np.log10(max(lengths)), 40),
                 color=L["series1"])
    axes[0].set_xscale("log")
    axes[0].set_xlabel("path length (miles, log scale)")
    axes[0].set_ylabel("tornado tracks")
    axes[0].set_title(f"Track length — median {lengths.median():.1f} mi")
    axes[0].grid(axis="x", visible=False)
    axes[1].hist(widths, bins=np.logspace(np.log10(1), np.log10(max(widths)), 40),
                 color=L["series1"])
    axes[1].set_xscale("log")
    axes[1].set_xlabel("damage width (yards, log scale)")
    axes[1].set_title(f"Damage width — median {widths.median():.0f} yd")
    axes[1].grid(axis="x", visible=False)
    fig.savefig(figures / "hz_track_geometry.png")
    plt.close(fig)

    # ── figure 5: human impact by rating ──
    impact = (hazards.groupby("ef")[["fatalities", "injuries"]].sum()
              .reindex(order).fillna(0))
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.4))
    for ax, column, title in ((axes[0], "fatalities", "Fatalities by rating"),
                              (axes[1], "injuries", "Injuries by rating")):
        colours = [L["series1"] if k in viz.EF_CLASSES else L["unrated"] for k in order]
        bars = ax.bar(labels, impact[column].values, color=colours, width=0.68)
        for bar, value in zip(bars, impact[column].values):
            if value > 0:
                ax.annotate(f"{int(value):,}", (bar.get_x() + bar.get_width() / 2, value),
                            ha="center", va="bottom", fontsize=9, color=L["secondary"])
        ax.set_title(title)
        ax.set_ylim(0, max(impact[column].max() * 1.15, 1))
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("people")
    fig.savefig(figures / "hz_human_impact.png")
    plt.close(fig)

    # ── figure 6: where they happen ──
    # Drawn in EPSG:5070 (CONUS Albers), the same equal-area projection the
    # linkage uses. Plotting raw degrees would stretch the north and make the
    # density read as denser in the north than it is.
    import pyproj

    from tornado_dataset.geo.gazetteer import state_outlines
    project = pyproj.Transformer.from_crs(config.CRS_WGS84, config.CRS_EQUAL_AREA,
                                          always_xy=True).transform
    outlines = state_outlines(2025)
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    for feature in outlines["features"]:
        geometry = feature["geometry"]
        polygons = (geometry["coordinates"] if geometry["type"] == "Polygon"
                    else [ring for poly in geometry["coordinates"] for ring in poly])
        for ring in polygons:
            xs, ys = project(*zip(*[(p[0], p[1]) for p in ring]))
            ax.plot(xs, ys, lw=0.6, color=L["axis"], zorder=1)
    points = hazards.dropna(subset=["lon", "lat"])
    px, py = project(points.lon.to_numpy(), points.lat.to_numpy())
    hexes = ax.hexbin(px, py, gridsize=58, mincnt=1, bins="log",
                      cmap=matplotlib.colors.LinearSegmentedColormap.from_list(
                          "seq", viz.SEQUENTIAL_LIGHT), zorder=2, linewidths=0)
    xlim = project([-125, -66], [39, 39])
    ylim = project([-96, -96], [23.5, 50])
    ax.set_xlim(xlim[0][0], xlim[0][1])
    ax.set_ylim(ylim[1][0], ylim[1][1])
    ax.set_aspect("equal")
    ax.set_title("Where the surveyed tracks are")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.grid(visible=False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    bar = fig.colorbar(hexes, ax=ax, shrink=0.72, pad=0.02)
    bar.set_label("tracks per cell (log)", color=L["secondary"], fontsize=9)
    bar.outline.set_visible(False)
    bar.ax.tick_params(colors=L["muted"], labelsize=8)
    fig.savefig(figures / "hz_geography.png")
    plt.close(fig)

    # ── figure 7: text and geometry coverage per year (small multiples) ──
    # `wfo_known` is DAT's *own* field, which is the reason Stage 16 exists — the
    # spatial backfill lifts it to 100%, so the panel is labelled for what it
    # actually measures rather than for the dataset's final state.
    coverage_columns = [("has_polygon", "has a damage polygon"),
                        ("has_oracle_text", "has DAT survey comments"),
                        ("wfo_known", "WFO recorded in DAT"),
                        ("gdelt_coverage", "inside GDELT news window")]
    fig, axes = plt.subplots(1, 4, figsize=(13, 2.9), sharey=True)
    for ax, (column, title) in zip(axes, coverage_columns):
        series = hazards.groupby("year")[column].mean() * 100
        ax.plot(series.index.astype(int), series.values, lw=2, color=L["series1"])
        ax.fill_between(series.index.astype(int), series.values, color=L["series1"], alpha=0.12)
        ax.set_title(title, fontsize=10)
        ax.set_ylim(0, 100)
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("% of tracks")
    fig.suptitle("Coverage of each layer over time", fontsize=12, fontweight="bold", y=1.06)
    fig.savefig(figures / "hz_coverage.png")
    plt.close(fig)

    # ── report ──
    rated = hazards[hazards.ef != viz.UNRATED]
    deadliest = hazards.nlargest(8, "fatalities")[
        ["convective_day", "efscale", "path_length_mi", "fatalities", "injuries", "wfo"]]
    deadliest = deadliest.merge(
        geography[["hazard_uid", "nearest_place", "states"]].assign(
            hazard_uid=geography.hazard_uid),
        left_on=hazards.nlargest(8, "fatalities").hazard_uid, right_on="hazard_uid",
        how="left").drop(columns=["hazard_uid", "key_0"], errors="ignore")

    longest = hazards.nlargest(5, "path_length_mi")[
        ["convective_day", "efscale", "path_length_mi", "n_lines", "fatalities"]]

    report = f"""# Hazard dataset — descriptive analysis

{len(hazards):,} surveyed tornado tracks in {len(episodes):,} episodes,
{config.WINDOW_START} to {config.WINDOW_END}. Generated by
`scripts/18_analyze_events.py`.

> **These are counts of what was surveyed, not of what occurred.** DAT holds the
> damage geometry NWS offices chose to draw, and that effort has grown markedly
> over the period — the rise in the yearly counts below is substantially a change
> in surveying and digitising practice, not in tornado frequency. Nothing here
> should be read as a climatological trend.

## Scale

| | count |
|---|---|
| tornado tracks (hazards) | {len(hazards):,} |
| episodes (stage 15) | {len(episodes):,} |
| tracks with a damage polygon | {int(hazards.has_polygon.sum()):,} ({hazards.has_polygon.mean():.1%}) |
| tracks with a rating | {len(rated):,} ({len(rated) / len(hazards):.1%}) |
| tracks assembled from >1 DAT line | {int((hazards.n_lines > 1).sum()):,} |
| total fatalities recorded | {int(hazards.fatalities.fillna(0).sum()):,} |
| total injuries recorded | {int(hazards.injuries.fillna(0).sum()):,} |
| busiest year | {int(per_year.hazards.idxmax())} ({int(per_year.hazards.max()):,} tracks) |
| largest episode | {episodes.loc[episodes.n_hazards.idxmax(), 'convective_days'].replace(';', ', ')} ({int(episodes.n_hazards.max())} tracks) |

![counts per year](figures/hz_counts_per_year.png)

## Ratings

{counts.rename('tracks').rename_axis('class').reset_index().assign(share=lambda d: (d.tracks / len(hazards)).map('{{:.1%}}'.format)).to_markdown(index=False)}

Ratings are encoded throughout with a single-hue ordinal ramp, and EF4/EF5 share
the top class — {int((hazards.ef == 'EF4+').sum())} tracks in total, of which {int(hazards.efscale.eq('EF5').sum())} are EF5. `unrated`
collects `UNKNOWN`, `EFU`, `TSTM/Wind` and missing values; it is grey rather than
a ramp step, because a missing rating is not a weak one.

![ratings](figures/hz_ef_distribution.png)

## Season and time of day

Peak month: **{int(by_month.idxmax())}** ({int(by_month.max()):,} tracks). The diurnal figure uses
**local solar time** (UTC shifted by longitude): a UTC histogram would smear the
late-afternoon peak across four US time zones, which is the one thing that figure
exists to show. Median onset {hazards.hour_solar.median():.1f}h solar.

![season and time of day](figures/hz_seasonality.png)

## Track geometry

Median track {lengths.median():.1f} miles (mean {lengths.mean():.1f}, longest {lengths.max():.0f}); median damage
width {widths.median():.0f} yards. Both distributions are heavy-tailed, hence the log axes.

![track geometry](figures/hz_track_geometry.png)

### Longest tracks

{longest.to_markdown(index=False)}

Long tracks are where DAT's line-drawing convention shows: some are a single
surveyed path, others are several segments the pipeline merged into one hazard
(`n_lines` > 1), and the survey products sometimes split them differently again.

## Human impact

![human impact](figures/hz_human_impact.png)

Fatalities concentrate in the strongest classes: {viz.EF_CLASS_LABELS['EF4+']} tracks are
{(hazards.ef == 'EF4+').mean():.1%} of the dataset but carry
{impact.loc['EF4+', 'fatalities'] / max(1, impact.fatalities.sum()):.0%} of the recorded deaths.

### Deadliest tracks

{deadliest.to_markdown(index=False)}

## Geography

![geography](figures/hz_geography.png)

## Coverage of each layer

![coverage](figures/hz_coverage.png)

The panels are the practical limits on what can be studied for a given year:
a damage polygon, DAT's own survey comments (the fallback oracle text), a WFO
recorded by DAT (needed to retrieve that office's NWS products), and whether the
event falls inside the GDELT news window.

The WFO panel is the case for Stage 16: DAT records an office for as little as 7%
of a year's tracks, and `scripts/16_enrich_geography.py` raises that to **100%**
by intersecting each track with the NWS county polygons for its own year —
agreeing with DAT on 99.8% of the tracks where DAT does record one. See
`outputs/text_qa_report.md` for the text layers themselves.

## Interactive map

`outputs/hazard_map.html` (built by `scripts/19_event_map.py`) shows every track
on a US map with a month slider, rating filter and hover details.
"""
    (config.OUTPUT_DIR / "hazard_analysis_report.md").write_text(report, encoding="utf-8")
    print(f"{len(hazards):,} hazards, {len(episodes):,} episodes")
    print(f"wrote {config.OUTPUT_DIR / 'hazard_analysis_report.md'} and 7 figures")


if __name__ == "__main__":
    main()

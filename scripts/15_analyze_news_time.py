"""Stage 15 — the LexisNexis corpus in the time dimension.

The question the dataset is built around is *when* text about a tornado appears:
what a reader could have known at T+1 hour differs from what the survey publishes
three days later, and the gap between them is the thing a nowcasting system has to
work in. The early prototype (`local/artifacts/gdelt_news.py`,
`TEXT_TIER_SUMMARY.md`) worked that out for a single outbreak and 89 texts. This
runs the same analysis over the full corpus.

Writes `outputs/news_time_report.md` and `outputs/figures/nt_*.png`.

    python scripts/15_analyze_news_time.py
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from collections import Counter

import _bootstrap  # noqa: F401

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from tornado_dataset import config, viz
from tornado_dataset.text import tiering

plt.rcParams.update(viz.matplotlib_style())
L = viz.LIGHT

# Coverage is dominated by a handful of events, so severity bands are used
# throughout rather than raw counts.
SEVERITY_BANDS = [(0, 0, "no deaths"), (1, 9, "1–9 deaths"), (10, 10_000, "10+ deaths")]


def severity_band(fatalities: float) -> str:
    value = 0 if pd.isna(fatalities) else float(fatalities)
    for low, high, label in SEVERITY_BANDS:
        if low <= value <= high:
            return label
    return "no deaths"


def survey_times(tag: str) -> dict[str, dt.datetime]:
    """First primary-survey publication per episode (the oracle boundary).

    Same derivation Stage 7 uses; it defines when text stops being independent of
    the survey and starts being downstream of it.
    """
    refs_path = config.PROCESSED_DIR / f"textrefs_nws_{tag}.csv"
    links_path = config.PROCESSED_DIR / f"textlinks_nws_{tag}.csv"
    hazards_path = config.PROCESSED_DIR / f"hazards_{tag}.csv"
    if not (refs_path.exists() and links_path.exists()):
        return {}
    refs = pd.read_csv(refs_path, usecols=["textref_uid", "published_at"])
    links = pd.read_csv(links_path, usecols=["textref_uid", "target_uid", "link_relation"])
    hazards = pd.read_csv(hazards_path, usecols=["hazard_uid", "episode_uid"])
    surveys = (links[links.link_relation == "primary_survey_of"]
               .merge(refs, on="textref_uid")
               .merge(hazards, left_on="target_uid", right_on="hazard_uid"))
    out: dict[str, dt.datetime] = {}
    for row in surveys.itertuples():
        moment = tiering._as_datetime(row.published_at)
        if moment and (row.episode_uid not in out or moment < out[row.episode_uid]):
            out[row.episode_uid] = moment
    return out


def main() -> None:
    default_tag = f"{config.WINDOW_START.isoformat()}_{config.WINDOW_END.isoformat()}"
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", default=default_tag)
    args = parser.parse_args()
    tag = args.tag

    figures = config.OUTPUT_DIR / "figures"
    figures.mkdir(parents=True, exist_ok=True)

    print("loading corpus and links …")
    articles = pd.read_json(config.OUTPUT_DIR / "lexisnexis_articles.jsonl", lines=True)
    links = pd.read_csv(config.PROCESSED_DIR / f"article_links_{tag}.csv")
    links = links[links.corpus == "lexisnexis"]
    status = pd.read_csv(config.PROCESSED_DIR / f"article_status_{tag}.csv")
    episodes = pd.read_csv(config.PROCESSED_DIR / f"episodes_{tag}.csv")
    manifest = json.loads(
        (config.PROCESSED_DIR / f"manifest_article_links_{tag}.json").read_text())["counts"]

    articles["published"] = pd.to_datetime(articles.pub_date, errors="coerce")
    articles["year"] = articles.published.dt.year
    articles["month"] = articles.published.dt.to_period("M").dt.to_timestamp()
    # The export repeats byte-identical rows where download batches overlapped, so
    # every corpus count here is over unique articles.
    unique = articles.drop_duplicates(subset=["file", "headline", "pub_date", "body"])
    print(f"  {len(articles):,} export rows -> {len(unique):,} unique articles")

    describes = links[links.link_relation == "describes"].copy()
    describes["event_day"] = pd.to_datetime(describes.event_day, errors="coerce")
    episode_meta = episodes.set_index("episode_uid")

    # ── 1. corpus volume over time ──
    per_month = unique.groupby("month").size()
    top_sources = unique.source.value_counts().head(6).index.tolist()
    share = (unique.assign(bucket=unique.source.where(unique.source.isin(top_sources), "other"))
             .pivot_table(index="year", columns="bucket", values="file", aggfunc="count")
             .fillna(0))
    share = share.div(share.sum(axis=1), axis=0) * 100

    fig, axes = plt.subplots(1, 2, figsize=(12, 3.6), width_ratios=[1.3, 1])
    axes[0].fill_between(per_month.index, per_month.values, color=L["series1"], alpha=0.25)
    axes[0].plot(per_month.index, per_month.values, lw=1.6, color=L["series1"])
    axes[0].set_title("Articles per month")
    axes[0].set_ylabel("articles")
    axes[0].grid(axis="x", visible=False)

    bottom = np.zeros(len(share))
    ramp = viz.EF_RAMP_LIGHT + [L["unrated"], L["series2"]]
    for i, column in enumerate(share.columns):
        axes[1].bar(share.index.astype(int), share[column], bottom=bottom, width=0.8,
                    color=ramp[i % len(ramp)], label=str(column)[:26],
                    edgecolor=L["surface"], linewidth=0.8)
        bottom += share[column].values
    axes[1].set_title("Where the articles come from (% per year)")
    axes[1].set_ylim(0, 100)
    axes[1].grid(axis="x", visible=False)
    axes[1].legend(fontsize=7, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.18))
    fig.tight_layout()
    fig.savefig(figures / "nt_volume.png")
    plt.close(fig)

    # ── 2. latency and decay ──
    # day_offset is the article date minus the event day: positive means the
    # article came after the tornado.
    offsets = describes.day_offset.dropna()
    near = offsets[(offsets >= -3) & (offsets <= 30)]
    describes["band"] = describes.event_fatalities.map(severity_band)

    fig, axes = plt.subplots(1, 2, figsize=(12, 3.6))
    axes[0].hist(near, bins=np.arange(-3.5, 31.5, 1), color=L["series1"], rwidth=0.85)
    axes[0].axvline(0, color=L["series2"], lw=1.2)
    axes[0].annotate(" tornado", (0, axes[0].get_ylim()[1] * 0.92), color=L["series2"],
                     fontsize=9)
    axes[0].set_xlabel("days after the tornado")
    axes[0].set_ylabel("articles")
    axes[0].set_title(f"When coverage appears (median {offsets.median():.0f} d)")
    axes[0].grid(axis="x", visible=False)

    for band, colour in zip([b[2] for b in SEVERITY_BANDS],
                            [viz.EF_RAMP_LIGHT[0], viz.EF_RAMP_LIGHT[2], viz.EF_RAMP_LIGHT[4]]):
        subset = describes[(describes.band == band) & describes.day_offset.between(0, 21)]
        if not len(subset):
            continue
        counts = subset.groupby("day_offset").size()
        counts = counts / counts.sum() * 100
        axes[1].plot(counts.index, counts.values, lw=2, marker="o", ms=3.5,
                     color=colour, label=band)
    axes[1].set_xlabel("days after the tornado")
    axes[1].set_ylabel("% of that band's articles")
    axes[1].set_title("Deadly outbreaks are covered for longer")
    axes[1].legend(frameon=False)
    axes[1].grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(figures / "nt_latency.png")
    plt.close(fig)

    # Measured rather than asserted: the bands differ in how long coverage runs,
    # so the claim in the report is computed here and quoted from this table.
    inside_window = describes[describes.day_offset.between(0, 14)]
    decay_table = inside_window.groupby("band").day_offset.agg(
        articles="size", median_days="median",
        within_2d=lambda s: (s <= 2).mean(), after_7d=lambda s: (s > 7).mean())
    decay_table = decay_table.reindex([b[2] for b in SEVERITY_BANDS]).dropna(how="all")

    # ── 3. the long tail: anniversaries ──
    far = offsets[(offsets > 30) & (offsets <= 800)]
    fig, ax = plt.subplots(figsize=(7.6, 3.2))
    ax.hist(far, bins=np.arange(30, 801, 10), color=L["series1"])
    for anniversary in (365, 730):
        ax.axvline(anniversary, color=L["series2"], lw=1.2, ls="-")
        ax.annotate(f" {anniversary // 365} year", (anniversary, ax.get_ylim()[1] * 0.85),
                    color=L["series2"], fontsize=9)
    ax.set_xlabel("days after the tornado")
    ax.set_ylabel("articles")
    ax.set_title("The retrospective tail")
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(figures / "nt_anniversary.png")
    plt.close(fig)

    # ── 4. which events get covered ──
    per_episode = describes.groupby("episode_uid").size().rename("articles")
    episode_frame = episode_meta.join(per_episode).fillna({"articles": 0})
    episode_frame["band"] = episode_frame.fatalities.map(severity_band)
    episode_frame["year"] = episode_frame.convective_day.str[:4].astype(int)
    covered_by_year = episode_frame.groupby("year").articles.apply(lambda s: (s > 0).mean() * 100)

    fig, axes = plt.subplots(1, 2, figsize=(12, 3.6))
    band_stats = episode_frame.groupby("band").articles.agg(["median", "mean", "size"])
    band_stats = band_stats.reindex([b[2] for b in SEVERITY_BANDS]).dropna()
    axes[0].bar(band_stats.index, band_stats["mean"], color=L["series1"], width=0.6)
    for i, row in enumerate(band_stats.itertuples()):
        axes[0].annotate(f"{row.mean:.1f}\n(n={int(row.size)})", (i, row.mean),
                         ha="center", va="bottom", fontsize=9, color=L["secondary"])
    axes[0].set_ylabel("articles per outbreak (mean)")
    axes[0].set_title("Coverage follows the death toll")
    axes[0].set_ylim(0, band_stats["mean"].max() * 1.35)
    axes[0].grid(axis="x", visible=False)

    axes[1].plot(covered_by_year.index, covered_by_year.values, lw=2, marker="o", ms=4,
                 color=L["series1"])
    axes[1].set_ylim(0, 100)
    axes[1].set_ylabel("% of outbreaks with ≥1 article")
    axes[1].set_title("Event-side coverage per year")
    axes[1].grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(figures / "nt_coverage.png")
    plt.close(fig)

    # ── 5. the independence timeline (the prototype's analysis, at scale) ──
    # LexisNexis articles carry no text_role: Stage 11 records when they appeared
    # but never classifies them. Deriving it here puts news on the same axis as the
    # NWS products, which is the comparison the dataset exists to support.
    surveys = survey_times(tag)
    print(f"  survey times known for {len(surveys):,} episodes")
    roles = []
    for row in describes.itertuples():
        episode = episode_meta.loc[row.episode_uid] if row.episode_uid in episode_meta.index else None
        if episode is None:
            continue
        classification = tiering.derive(
            author_org=None, source_type="news",
            published_at=row.event_day + pd.Timedelta(days=float(row.day_offset))
            if pd.notna(row.day_offset) else None,
            event_begin=episode.time_begin_utc,
            survey_at=surveys.get(row.episode_uid))
        roles.append({"episode_uid": row.episode_uid, **classification})
    role_frame = pd.DataFrame(roles)

    nws_offsets = pd.DataFrame()
    nws_links_path = config.PROCESSED_DIR / f"textlinks_nws_{tag}.csv"
    if nws_links_path.exists():
        nws_links = pd.read_csv(nws_links_path,
                                usecols=["textref_uid", "link_relation", "time_offset_hours"])
        nws_refs = pd.read_csv(config.PROCESSED_DIR / f"textrefs_nws_{tag}.csv",
                               usecols=["textref_uid", "source_type", "text_role"])
        nws_offsets = nws_links.merge(nws_refs, on="textref_uid")

    timeline = []
    if len(role_frame):
        for role, group in role_frame.groupby("text_role"):
            hours = group.time_offset_hours.dropna()
            if len(hours):
                timeline.append({"stream": "LexisNexis news", "role": role, "n": len(hours),
                                 "median_h": hours.median(), "p10": hours.quantile(0.1),
                                 "p90": hours.quantile(0.9)})
    if len(nws_offsets):
        for role, group in nws_offsets.groupby("text_role"):
            hours = group.time_offset_hours.dropna()
            if len(hours):
                timeline.append({"stream": "NWS products", "role": role, "n": len(hours),
                                 "median_h": hours.median(), "p10": hours.quantile(0.1),
                                 "p90": hours.quantile(0.9)})
    timeline_frame = pd.DataFrame(timeline).sort_values("median_h") if timeline else pd.DataFrame()

    if len(timeline_frame):
        fig, ax = plt.subplots(figsize=(8.6, 3.4))
        colours = {"oracle": viz.EF_RAMP_LIGHT[4], "official_timely": L["series2"],
                   "independent_timely": viz.EF_RAMP_LIGHT[1],
                   "independent_retrospective": viz.EF_RAMP_LIGHT[3]}
        for i, row in enumerate(timeline_frame.itertuples()):
            ax.plot([row.p10, row.p90], [i, i], lw=3,
                    color=colours.get(row.role, L["muted"]), alpha=0.35,
                    solid_capstyle="round")
            ax.plot([row.median_h], [i], "o", ms=8, color=colours.get(row.role, L["muted"]))
            ax.annotate(f"  {row.median_h:.0f} h  (n={row.n:,})", (row.median_h, i),
                        va="center", fontsize=9, color=L["secondary"])
        ax.set_yticks(range(len(timeline_frame)))
        ax.set_yticklabels([f"{r.stream}\n{r.role}" for r in timeline_frame.itertuples()],
                           fontsize=8)
        ax.axvline(0, color=L["axis"], lw=1)
        ax.set_xscale("symlog")
        ax.set_xlabel("hours after tornado onset (symlog; bar = 10th–90th percentile)")
        ax.set_title("When each kind of text arrives")
        ax.grid(axis="y", visible=False)
        fig.tight_layout()
        fig.savefig(figures / "nt_timeline.png")
        plt.close(fig)

    # ── report ──
    first_per_episode = describes[describes.day_offset >= 0].groupby("episode_uid").day_offset.min()
    same_day = (first_per_episode == 0).mean() if len(first_per_episode) else float("nan")
    within_2 = (first_per_episode <= 2).mean() if len(first_per_episode) else float("nan")

    report = f"""# The news corpus in time

{len(unique):,} unique LexisNexis articles ({len(articles):,} export rows,
{len(articles) - len(unique):,} byte-identical duplicates), {unique.published.min():%Y-%m-%d} to
{unique.published.max():%Y-%m-%d}. Generated by `scripts/15_analyze_news_time.py`.

> **Every figure here is conditional on unvalidated links.** {manifest['lexis_articles_with_a_link']:,}
> of {manifest['lexis_articles']:,} articles carry a candidate link, and the precision of those
> links has not been measured yet (`outputs/link_qa_report.md`). Read the shapes,
> not the absolute levels.

## 1. What is in the corpus, and when

![volume](figures/nt_volume.png)

Article volume is **not** a measure of how much tornado news existed: the corpus
is the result of capped LexisNexis queries, so the growth after 2018 partly
reflects how the export was assembled. The composition panel is the more useful
one — it shows how much of the corpus is wire copy versus original reporting, and
that mix changes materially across the period.

## 2. How quickly coverage appears

![latency](figures/nt_latency.png)

For articles that *describe* an outbreak, the median appears **{offsets.median():.0f} days** after it.
Of the outbreaks with any coverage, **{same_day:.0%}** have an article on the day itself and
**{within_2:.0%}** within two days.

The severity bands differ in shape, not just in height. Within the first
fortnight, {decay_table.loc['1–9 deaths', 'within_2d']:.0%} of the coverage of outbreaks killing 1–9 people has arrived
within two days, against {decay_table.loc['10+ deaths', 'within_2d']:.0%} for those killing ten or more — the deadliest
events peak lower and stay in the news longer, which is what a rolling death toll,
a federal declaration and a funeral cycle look like in aggregate.

{decay_table.to_markdown(floatfmt=".2f")}

**The curve is censored by construction.** The linker's candidate window ends at
+14 days, so everything past it comes only from the retrospective passes
({int((describes.day_offset > 14).sum()):,} links). The decline visible here is partly the shape of
coverage and partly the shape of the window; the two cannot be separated from
this figure alone.

## 3. The retrospective tail

![anniversary](figures/nt_anniversary.png)

{len(far):,} articles describe an event more than 30 days old. Spikes at the one- and
two-year marks are anniversary journalism — a distinct genre from breaking
coverage, and the reason the linker needs its retrospective pass at all
(`from_retrospective_pass` marks {int(describes.from_retrospective_pass.sum()):,} of these links).

## 4. Which events get covered

![coverage](figures/nt_coverage.png)

{band_stats.to_markdown(floatfmt=".1f")}

Coverage is concentrated on the deadliest events, which is the single most
important bias in the text side of this dataset: a model trained or evaluated on
linked articles sees a sample skewed towards fatal, urban, photogenic tornadoes.
The per-year panel mixes two effects and should not be read as a trend — DAT
surveyed far fewer events early in the period, so the denominator changes.

## 5. When each kind of text arrives

![timeline](figures/nt_timeline.png)

{timeline_frame.to_markdown(index=False, floatfmt=".1f") if len(timeline_frame) else "(no timeline data)"}

This is the prototype's tier analysis (`TEXT_TIER_SUMMARY.md`, 89 texts, one
outbreak) recomputed over the whole corpus. The ordering is what matters: NWS
Local Storm Reports land within the hour, independent news within the first day,
and the survey product — the oracle — days later. Anything a system infers from
text before the survey exists has to come from the first two.

LexisNexis roles are derived here rather than stored: Stage 11 records *when* an
article appeared but never classifies it, so `text/tiering.py:derive()` is applied
with the episode's onset and its first survey publication as boundaries.

## Limitations

1. **Links are candidates, not facts.** Precision is unmeasured; the annotation
   phase sets it.
2. **The corpus is a convenience sample** — capped Lexis queries, not a census.
3. **The news hours in §5 are date-resolution.** LexisNexis gives a publication
   *date* for most articles, so an article's time is taken as midnight of that
   date while the tornado's onset is a real timestamp. An article published the
   same calendar day as a 22:00 onset therefore lands *before* it — which is why
   the `independent_timely` band starts negative. The NWS rows carry true
   timestamps. Compare the streams by their order and rough scale, not by the
   hour; the day-level medians elsewhere in this report are the robust figures.
4. **Event-side coverage per year confounds** news coverage with DAT's own
   growth, and some tornadoes have no DAT geometry at all, so they cannot be
   linked however well covered they were.
"""
    (config.OUTPUT_DIR / "news_time_report.md").write_text(report, encoding="utf-8")
    print(f"median day_offset {offsets.median():.0f} d | "
          f"{len(far):,} retrospective articles | timeline rows {len(timeline_frame)}")
    print(f"wrote {config.OUTPUT_DIR / 'news_time_report.md'} and 5 figures")


if __name__ == "__main__":
    main()

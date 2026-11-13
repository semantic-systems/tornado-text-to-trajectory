#!/usr/bin/env python
"""Figures for the Wikipedia write-up (docs/WIKIPEDIA.md, docs/methods_wikipedia.md).

A tool, not a pipeline stage: it reads what stages 27 and 44 wrote and draws

* ``wikipedia_coverage_by_year`` — cited articles per year, and the share held
  by LexisNexis, by Media Cloud and by either (stage 27);
* ``wikipedia_coverage_by_outlet`` — the same shares by kind of outlet;
* ``wikipedia_silver_set`` — the silver links by kind and strength, and the
  linked tornadoes by best geometry (stage 44).

    python scripts/figures_wikipedia.py

Writes PNG (300 dpi) and SVG to ``docs/figures/``. The figures hold counts and
shares only, no article text, so they may live in git.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from tornado_dataset import config  # noqa: E402

OUT = config.REPO_ROOT / "docs" / "figures"
ARTICLES_CSV = config.INTERIM_DIR / "wikipedia_news_articles.csv"
SILVER_CSV = config.PROCESSED_DIR / "wikipedia_silver_links.csv"
SILVER_MC_CSV = config.PROCESSED_DIR / "wikipedia_silver_mediacloud.csv"

# Reference palette (dataviz skill): categorical slots 1-3, a blue ramp for the
# ordered strengths, and the neutral chrome.
SURFACE, INK, INK_2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
LEXIS, MEDIACLOUD, EITHER = "#2a78d6", "#eb6834", "#1baf7a"
STRENGTH = {"strong": "#1c5cab", "medium": "#5598e7", "weak": "#9ec5f4", "rejected": "#c3c2b7"}
GEOMETRY = {"dat_polygon": "#1c5cab", "dat_line": "#5598e7", "spc_track": "#9ec5f4"}

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.size": 9, "axes.edgecolor": GRID, "axes.labelcolor": INK_2, "text.color": INK,
    "xtick.color": INK_2, "ytick.color": INK_2, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": False, "legend.frameon": False,
})


def _year(row) -> str:
    if str(row.pub_date)[:4].isdigit():
        return str(row.pub_date)[:4]
    years = [y for y in str(row.page_years).split("|") if y]
    return years[0] if years else ""


def _flag(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().eq("true")


def _save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg"):
        fig.savefig(OUT / f"{name}.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote docs/figures/{name}.png/.svg")


def coverage(articles: pd.DataFrame) -> None:
    a = articles.assign(year=[_year(r) for r in articles.itertuples()],
                        lexis=_flag(articles.matched_strong),
                        mc=_flag(articles.mc_matched_strong))
    a["either"] = a.lexis | a.mc
    a = a[a.year.between(str(config.WINDOW_START.year), str(config.WINDOW_END.year))]
    by = a.groupby("year").agg(cited=("article_key", "size"), lexis=("lexis", "mean"),
                               mc=("mc", "mean"), either=("either", "mean"))
    years = by.index.astype(int)

    fig, (top, bottom) = plt.subplots(2, 1, figsize=(6.6, 4.4), sharex=True,
                                      gridspec_kw={"height_ratios": [1, 2.4], "hspace": 0.12})
    top.bar(years, by.cited, width=0.62, color="#c3c2b7")
    top.set_ylabel("cited\narticles")
    top.yaxis.grid(True, color=GRID, linewidth=0.6)
    top.set_axisbelow(True)
    nudge = {"either": 5, "mc": -5, "lexis": 0}       # end labels clear of each other
    for series, color, label in (("either", EITHER, "either corpus"),
                                 ("mc", MEDIACLOUD, "Media Cloud"),
                                 ("lexis", LEXIS, "LexisNexis")):
        bottom.plot(years, by[series] * 100, color=color, linewidth=2, marker="o",
                    markersize=4, label=label)
        bottom.annotate(f"{label} {by[series].iloc[-1]:.0%}",
                        (years[-1], by[series].iloc[-1] * 100), xytext=(6, nudge[series]),
                        textcoords="offset points", va="center", color=INK_2, fontsize=8)
    bottom.set_ylabel("share held (%)")
    bottom.set_ylim(0, max(45, by.either.max() * 110))
    bottom.yaxis.grid(True, color=GRID, linewidth=0.6)
    bottom.set_axisbelow(True)
    bottom.set_xticks(years)
    bottom.set_xticklabels([str(y) if y % 2 == 0 else "" for y in years])
    bottom.legend(loc="upper left", fontsize=8, ncol=3)
    fig.suptitle("News articles cited by Wikipedia's US tornado pages: share in our corpora",
                 x=0.0, ha="left", fontsize=10)
    _save(fig, "wikipedia_coverage_by_year")


def coverage_by_outlet(articles: pd.DataFrame) -> None:
    a = articles.assign(lexis=_flag(articles.matched_strong), mc=_flag(articles.mc_matched_strong))
    by = a.groupby("outlet_type").agg(cited=("article_key", "size"), lexis=("lexis", "mean"),
                                      mc=("mc", "mean")).sort_values("cited")
    names = {"local_other": "local, other", "local_broadcast": "local broadcast",
             "national": "national", "weather_media": "weather media", "wire": "wire"}
    labels = [f"{names.get(k, k)} (n={n:,})" for k, n in zip(by.index, by.cited)]
    fig, ax = plt.subplots(figsize=(6.2, 2.9))
    y = range(len(by))
    h = 0.36
    for offset, series, color, label in ((h / 2 + 0.01, "lexis", LEXIS, "LexisNexis"),
                                         (-h / 2 - 0.01, "mc", MEDIACLOUD, "Media Cloud")):
        pos = [i + offset for i in y]
        ax.barh(pos, by[series] * 100, height=h, color=color, label=label)
        for p, v in zip(pos, by[series]):
            ax.text(v * 100 + 1, p, f"{v:.0%}", va="center", fontsize=7.5, color=INK_2)
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels)
    ax.set_xlabel("share of cited articles held (%)")
    ax.set_xlim(0, 75)
    ax.xaxis.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.legend(loc="upper right", fontsize=8)
    ax.set_title("By kind of outlet", loc="left", fontsize=10)
    _save(fig, "wikipedia_coverage_by_outlet")


def silver_set(links: pd.DataFrame, mc: pd.DataFrame | None) -> None:
    hz = links[links.link_level == "hazard"]
    rows = {"Wikipedia passages": hz[hz.text_kind == "wikipedia_passage"].strength,
            "cited news (web)": hz[hz.text_kind == "cited_news"].strength,
            "LexisNexis articles": hz[hz.text_kind == "lexisnexis"].strength}
    if mc is not None and len(mc):
        rows["Media Cloud headlines"] = mc.drop_duplicates("mc_dup_group").strength
    order = ["strong", "medium", "weak", "rejected"]
    counts = pd.DataFrame({k: v.value_counts() for k, v in rows.items()}).T \
        .reindex(columns=order).fillna(0).astype(int).iloc[::-1]

    kept = hz[hz.strength != "rejected"]
    geo = kept.drop_duplicates("tornado_key").geometry.value_counts() \
        .reindex(list(GEOMETRY)).fillna(0).astype(int)

    fig, (left, right) = plt.subplots(1, 2, figsize=(7.8, 2.7),
                                      gridspec_kw={"width_ratios": [3.2, 1], "wspace": 0.95})
    # Shares, so a few hundred passages compare with two thousand news articles;
    # each row's count is printed beside it.
    for i, (name, row) in enumerate(counts.iterrows()):
        start, total = 0.0, row.sum()
        for s in order:
            share = row[s] / total * 100
            if not row[s]:
                continue
            left.barh(i, share, left=start, height=0.62, color=STRENGTH[s],
                      edgecolor=SURFACE, linewidth=1)
            if share >= 8:
                left.text(start + share / 2, i, f"{row[s]:,}", ha="center", va="center",
                          fontsize=7.5, color="#ffffff" if s in ("strong", "medium") else INK)
            start += share
        rejected = f" (+{row['rejected']:,} rejected)" if row["rejected"] else ""
        left.text(101.5, i, f"n = {total - row['rejected']:,}{rejected}", va="center",
                  fontsize=7.5, color=INK_2)
    left.set_yticks(range(len(counts)))
    left.set_yticklabels(counts.index)
    left.set_xlabel("share of tornado-level links (%)")
    left.set_xlim(0, 100)
    handles = [plt.Rectangle((0, 0), 1, 1, color=STRENGTH[s]) for s in order]
    left.legend(handles, order, loc="upper center", bbox_to_anchor=(0.45, -0.28), ncol=4,
                fontsize=8)
    left.set_title("Silver links by strength", loc="left", fontsize=10)

    names = {"dat_polygon": "DAT polygon", "dat_line": "DAT line only",
             "spc_track": "SPC track only"}
    start = 0
    for g, n in geo.items():
        right.bar(0, n, bottom=start, width=0.55, color=GEOMETRY[g], edgecolor=SURFACE, linewidth=1)
        right.text(0.36, start + n / 2, f"{names[g]}  {n}", va="center", fontsize=7.5, color=INK_2)
        start += n
    right.set_xlim(-0.4, 1.9)
    right.set_xticks([])
    right.spines["bottom"].set_visible(False)
    right.set_title(f"{geo.sum()} linked tornadoes,\nby best geometry", loc="left", fontsize=10)
    _save(fig, "wikipedia_silver_set")


def main() -> None:
    config.require_data(ARTICLES_CSV, SILVER_CSV)
    articles = pd.read_csv(ARTICLES_CSV, keep_default_na=False, low_memory=False)
    if "mc_matched_strong" not in articles:
        raise SystemExit("no Media Cloud columns — run scripts/27_wikipedia_reference_coverage.py match")
    links = pd.read_csv(SILVER_CSV, keep_default_na=False, low_memory=False)
    mc = (pd.read_csv(SILVER_MC_CSV, keep_default_na=False, dtype=str)
          if SILVER_MC_CSV.exists() else None)
    coverage(articles)
    coverage_by_outlet(articles)
    silver_set(links, mc)


if __name__ == "__main__":
    main()

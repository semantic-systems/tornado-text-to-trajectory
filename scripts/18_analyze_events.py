"""Stage 18 — what the dataset contains, and how representative its surveys are.

Writes ``outputs/hazard_analysis_report.md`` and figures. SPC's tornado list is
the population (stage 15); DAT, the source of the surveyed geometry, covers a
subset that grew from a few percent of tornadoes in 2010 to most of them in
2025. The report therefore describes the population and the subset side by side
and measures where the subset differs:

1. the way from SPC's 20,000-odd tornadoes to the dataset's hazards (every
   count reconciles);
2. DAT coverage per year;
3. whether DAT is representative: the share of tornadoes with a DAT survey by
   rating, season, time of day, track length, deaths and area, within three eras,
   so that adoption over time does not masquerade as a property of the stratum;
4. season, time of day and track length of all tornadoes, with the DAT subset;
5. where tornadoes are, and where DAT covers them;
6. deaths, from SPC's record;
7. which official texts each hazard has (stages 20, 24, 25; news is left out).

Times, ratings, lengths and casualties come from SPC's record for every
tornado: the same source for population and subset, and free of DAT's clock
errors (stage 14). Every number in the report is computed; none is typed in.

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
from tornado_dataset.dat import episode_table
from tornado_dataset.dat import references as refs
from tornado_dataset.geo.gazetteer import CENSUS_DIVISIONS, census_division, state_outlines
from tornado_dataset.text import official

plt.rcParams.update(viz.matplotlib_style())
L = viz.LIGHT
ALL = L["axis"]                  # all tornadoes: the recessive backdrop
DAT = L["series1"]               # DAT-surveyed tornadoes, DAT hazards
SPC = L["series2"]               # SPC hazards (no DAT survey)
ERAS = [(2010, 2014), (2015, 2019), (2020, 2025)]
ERA_COLOURS = [viz.EF_RAMP_LIGHT[0], viz.EF_RAMP_LIGHT[2], viz.EF_RAMP_LIGHT[4]]
SURVEYED_ROLES = ("dat_closest", "dat_secondary")
TEXT_KINDS = list(official.KINDS.items())
ORACLE = official.ORACLE


def pct(n: float, d: float) -> str:
    return f"{n / d:.1%}" if d else "—"


def share(x: float) -> str:
    """A share for prose: whole percent, but never a rounded 0% or 100%."""
    if x != x:
        return "—"
    if 0 < x < 0.005:
        return "<1%"
    if 0.995 <= x < 1:
        return ">99%"
    return f"{x:.0%}"


def era_of(year: int) -> str:
    for a, b in ERAS:
        if a <= year <= b:
            return f"{a}–{b}"
    return "other"


def md_table(df: pd.DataFrame, align: str | None = None) -> str:
    """A markdown table; ``align`` per column, ``l`` or ``r`` (numbers right)."""
    cols = list(df.columns)
    align = align or "l" + "r" * (len(cols) - 1)
    head = "| " + " | ".join(str(c) for c in cols) + " |"
    rule = "|" + "|".join("---:" if a == "r" else "---" for a in align) + "|"
    body = ["| " + " | ".join(str(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join([head, rule, *body])


def details(summary: str, body: str) -> str:
    return f"<details><summary>{summary}</summary>\n\n{body}\n\n</details>"


def finish(ax, title: str, ylabel: str | None = None) -> None:
    ax.set_title(title, loc="left")
    if ylabel:
        ax.set_ylabel(ylabel)
    ax.grid(axis="x", visible=False)


# ── data ───────────────────────────────────────────────────────────────────

def load_tornadoes(tag: str) -> pd.DataFrame:
    """SPC's tornadoes in the window, with stage 15's role and what the strata need."""
    t = pd.read_csv(refs.SPC_TRACKS, low_memory=False)
    t = t[(t.yr >= config.WINDOW_START.year) & (t.yr <= config.WINDOW_END.year)].copy()
    roles = pd.read_csv(episode_table.spc_episodes_path(tag))[["spc_id", "role", "episode_uid"]]
    t = t.merge(roles, on="spc_id", how="left")
    t["surveyed"] = t.role.isin(SURVEYED_ROLES)
    begin = pd.to_datetime(t.begin_utc, utc=True)
    t["year"] = t.yr.astype(int)
    t["era"] = t.year.map(era_of)
    t["month"] = t.mo.astype(int)
    # Local solar time: UTC shifted by the start longitude, so the diurnal cycle is
    # not smeared across four time zones.
    t["hour_solar"] = (begin.dt.hour + begin.dt.minute / 60 + t.slon / 15) % 24
    t["ef"] = np.where(t.mag >= 0, t.mag.clip(upper=4).map(
        lambda m: "EF4+" if m >= 4 else f"EF{int(m)}"), viz.UNRATED)
    t["division"] = t.st.map(census_division)
    return t


def strata(t: pd.DataFrame) -> list[tuple[str, pd.Series, list[str]]]:
    """``(factor, category per tornado, category order)`` for the coverage figure."""
    season = t.month.map(lambda m: {12: "winter", 1: "winter", 2: "winter", 3: "spring",
                                    4: "spring", 5: "spring", 6: "summer", 7: "summer",
                                    8: "summer"}.get(m, "autumn"))
    tod = pd.cut(t.hour_solar, [0, 6, 12, 18, 24], right=False,
                 labels=["night 0–6", "morning 6–12", "afternoon 12–18", "evening 18–24"])
    length = pd.cut(t.len, [-0.01, 1, 5, 15, np.inf], labels=["< 1 mi", "1–5 mi", "5–15 mi",
                                                             "≥ 15 mi"])
    deaths = np.where(t.fat > 0, "killed someone", "no deaths")
    divisions = [d for d in CENSUS_DIVISIONS if (t.division == d).sum() >= 50]
    return [
        ("rating", t.ef, viz.EF_CLASSES + [viz.UNRATED]),
        ("season", season, ["winter", "spring", "summer", "autumn"]),
        ("time of day (solar)", tod.astype(str),
         ["night 0–6", "morning 6–12", "afternoon 12–18", "evening 18–24"]),
        ("track length", length.astype(str), ["< 1 mi", "1–5 mi", "5–15 mi", "≥ 15 mi"]),
        ("deaths", pd.Series(deaths, index=t.index), ["no deaths", "killed someone"]),
        ("census division", t.division, divisions),
    ]


def text_coverage(tag: str, hazards: pd.DataFrame) -> pd.DataFrame | None:
    """Per hazard: which official texts it has (stages 20 and 24); ``None`` if neither ran."""
    table = official.counts(tag)
    if table is None:
        return None
    out = hazards.join(table > 0, on="hazard_uid")
    for kind, _ in TEXT_KINDS:
        out[kind] = out[kind].fillna(False).astype(bool)
    out["any_official"] = out[[k for k, _ in TEXT_KINDS]].any(axis=1)
    out["any_oracle"] = out[list(ORACLE)].any(axis=1)
    return out


def oracle_accounts(tag: str) -> pd.Series | None:
    """Per hazard: distinct accounts among its oracle texts (stage 25)."""
    path = config.PROCESSED_DIR / f"same_source_edits_{tag}.csv"
    if not path.exists():
        return None
    rows = pd.read_csv(path, usecols=["hazard_uid", "source_type", "edit_group"])
    rows = rows[rows.source_type.isin(["pns", "storm_events_narrative", "dat_comment"])]
    return rows.groupby("hazard_uid").edit_group.nunique()


# ── figures ────────────────────────────────────────────────────────────────

def fig_coverage_per_year(t: pd.DataFrame, path) -> pd.DataFrame:
    per = t.groupby("year").agg(all=("spc_id", "size"), surveyed=("surveyed", "sum"))
    per["share"] = per.surveyed / per["all"]
    x = per.index.to_numpy()
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.5), width_ratios=[1.5, 1])
    axes[0].bar(x, per["all"], color=ALL, width=0.72, label="all tornadoes (SPC)")
    axes[0].bar(x, per.surveyed, color=DAT, width=0.72, label="with a DAT survey")
    axes[0].legend(loc="upper left", ncol=2)
    axes[0].set_ylim(0, per["all"].max() * 1.18)
    finish(axes[0], "Tornadoes per year, and those DAT surveyed", "tornadoes")
    axes[1].plot(x, per.share * 100, color=DAT, lw=2, marker="o", ms=4)
    for i in (0, len(x) - 1):
        axes[1].annotate(f"{per.share.iloc[i]:.0%}", (x[i], per.share.iloc[i] * 100),
                         textcoords="offset points", xytext=(0, 8), ha="center",
                         fontsize=9, color=L["secondary"])
    axes[1].set_ylim(0, 100)
    for ax in axes:
        ax.set_xticks(range(int(x.min()), int(x.max()) + 1, 3))
    finish(axes[1], "Share with a DAT survey", "% of tornadoes")
    fig.savefig(path)
    plt.close(fig)
    return per


def fig_representativeness(t: pd.DataFrame, path) -> pd.DataFrame:
    """Dot plot: % with a DAT survey per category, one dot per era."""
    rows = []
    for factor, cat, order in strata(t):
        for c in order:
            for a, b in ERAS:
                sel = (cat == c) & t.year.between(a, b)
                n = int(sel.sum())
                rows.append({"factor": factor, "category": c, "era": f"{a}–{b}", "n": n,
                             "surveyed": int(t.surveyed[sel].sum()),
                             "share": t.surveyed[sel].mean() if n else np.nan})
    table = pd.DataFrame(rows)
    factors = list(dict.fromkeys(table.factor))
    heights = [table[table.factor == f].category.nunique() for f in factors]
    fig, axes = plt.subplots(len(factors), 1, figsize=(8.6, 0.34 * sum(heights) + 2.2),
                             height_ratios=heights, sharex=True, layout="constrained")
    for ax, factor in zip(axes, factors):
        sub = table[table.factor == factor]
        cats = list(dict.fromkeys(sub.category))
        y = {c: i for i, c in enumerate(cats)}
        for c in cats:
            s = sub[sub.category == c].share * 100
            ax.plot([s.min(), s.max()], [y[c]] * 2, color=L["grid"], lw=3, zorder=1)
        for (era, colour) in zip(dict.fromkeys(sub.era), ERA_COLOURS):
            e = sub[(sub.era == era) & (sub.n >= 20)]
            ax.scatter(e.share * 100, e.category.map(y), s=46, color=colour, zorder=2,
                       edgecolor=L["surface"], linewidth=1.2, clip_on=False,
                       label=f"{era}" if factor == factors[0] else None)
        ax.set_yticks(range(len(cats)), cats)
        ax.invert_yaxis()
        ax.set_ylim(len(cats) - 0.4, -0.6)
        ax.set_title(factor, loc="left", fontsize=10.5)
        ax.grid(axis="y", visible=False)
    axes[-1].set_xlim(0, 100)
    axes[-1].set_xlabel("% of tornadoes with a DAT survey (categories with ≥ 20 tornadoes)")
    fig.legend(*axes[0].get_legend_handles_labels(), title="era", loc="outside upper right",
               ncol=3, fontsize=8.5, title_fontsize=8.5)
    fig.suptitle("Which tornadoes DAT surveyed, within each era", x=0.01, ha="left",
                 fontsize=12, fontweight="bold")
    fig.savefig(path)
    plt.close(fig)
    return table


def fig_climatology(t: pd.DataFrame, path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.3))
    months = range(1, 13)
    for data, colour, label in ((t, ALL, "all tornadoes"), (t[t.surveyed], DAT, "DAT survey")):
        counts = data.groupby("month").size().reindex(months, fill_value=0)
        axes[0].bar(months, counts, color=colour, width=0.72, label=label)
    axes[0].set_xticks(months, list("JFMAMJJASOND"))
    axes[0].legend(loc="upper right")
    finish(axes[0], "Month", "tornadoes")
    bins = np.arange(0, 25, 1)
    axes[1].hist(t.hour_solar.dropna(), bins=bins, color=ALL, rwidth=0.86)
    axes[1].hist(t.hour_solar[t.surveyed].dropna(), bins=bins, color=DAT, rwidth=0.86)
    axes[1].set_xticks(range(0, 25, 6))
    axes[1].set_xlabel("start, local solar hour")
    finish(axes[1], "Time of day")
    lengths = t.len[t.len > 0]
    bins = np.logspace(np.log10(0.01), np.log10(lengths.max()), 40)
    axes[2].hist(lengths, bins=bins, color=ALL)
    axes[2].hist(t.len[t.surveyed & (t.len > 0)], bins=bins, color=DAT)
    axes[2].set_xscale("log")
    axes[2].set_xlabel("track length, miles (log)")
    finish(axes[2], "Track length")
    fig.savefig(path)
    plt.close(fig)


def fig_geography(t: pd.DataFrame, path) -> None:
    import pyproj
    project = pyproj.Transformer.from_crs(config.CRS_WGS84, config.CRS_EQUAL_AREA,
                                          always_xy=True).transform
    conus = t[t.slon.between(-125, -66) & t.slat.between(24, 50)]
    x, y = project(conus.slon.to_numpy(), conus.slat.to_numpy())
    xlim = project([-125, -66], [39, 39])[0]
    ylim = project([-96, -96], [23.5, 50])[1]
    extent = (xlim[0], xlim[1], ylim[0], ylim[1])
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("seq", viz.SEQUENTIAL_LIGHT)
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.4))
    outlines = state_outlines(2025)["features"]
    for ax in axes:
        for feature in outlines:
            g = feature["geometry"]
            rings = g["coordinates"] if g["type"] == "Polygon" else [
                r for poly in g["coordinates"] for r in poly]
            for ring in rings:
                xs, ys = project(*zip(*[(p[0], p[1]) for p in ring]))
                ax.plot(xs, ys, lw=0.5, color=L["axis"], zorder=3)
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])
        ax.grid(visible=False)
        for spine in ax.spines.values():
            spine.set_visible(False)
    density = axes[0].hexbin(x, y, gridsize=46, extent=extent, mincnt=1, bins="log",
                             cmap=cmap, linewidths=0, zorder=2)
    share = axes[1].hexbin(x, y, C=conus.surveyed.astype(float) * 100, gridsize=46,
                           extent=extent, mincnt=10, reduce_C_function=np.mean,
                           cmap=cmap, vmin=0, vmax=100, linewidths=0, zorder=2)
    axes[0].set_title("All tornadoes, 2010–2025", loc="left")
    axes[1].set_title("Share with a DAT survey (cells with ≥ 10 tornadoes)", loc="left")
    for ax, mappable, label in ((axes[0], density, "tornadoes per cell (log)"),
                                (axes[1], share, "% with a DAT survey")):
        bar = fig.colorbar(mappable, ax=ax, shrink=0.7, pad=0.01)
        bar.set_label(label, color=L["secondary"], fontsize=9)
        bar.outline.set_visible(False)
        bar.ax.tick_params(colors=L["muted"], labelsize=8)
    fig.savefig(path)
    plt.close(fig)


def fig_text_per_year(cov: pd.DataFrame, path) -> None:
    kinds = TEXT_KINDS
    fig, axes = plt.subplots(1, len(kinds), figsize=(14, 2.9), sharey=True)
    for ax, (kind, title) in zip(axes, kinds):
        for source, colour, label in (("dat", DAT, "DAT hazards"), ("spc", SPC, "SPC hazards")):
            sub = cov[cov.hazard_source == source]
            if not len(sub) or (kind == "dat_comment" and source == "spc"):
                continue                # no DAT comment can exist for an SPC hazard
            s = sub.groupby("year")[kind].mean() * 100
            ax.plot(s.index, s.values, color=colour, lw=2, label=label)
        ax.set_title(title, loc="left", fontsize=10)
        ax.set_ylim(0, 100)
        ax.set_xticks([2010, 2015, 2020, 2025])
        if kind == "dat_comment":
            ax.annotate("SPC hazards: none,\nby construction", (2010.5, 8), fontsize=8.5,
                        color=L["muted"])
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("% of hazards")
    axes[0].legend(loc="upper left", fontsize=8.5)
    fig.suptitle("Official text per hazard, by year", x=0.01, ha="left", fontsize=12,
                 fontweight="bold", y=1.04)
    fig.savefig(path)
    plt.close(fig)


# ── report ─────────────────────────────────────────────────────────────────

def main() -> None:
    default_tag = f"{config.WINDOW_START.isoformat()}_{config.WINDOW_END.isoformat()}"
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", default=default_tag)
    args = parser.parse_args()
    tag = args.tag
    P = config.PROCESSED_DIR
    for path, stage in ((refs.SPC_TRACKS, "13_fetch_references"),
                        (episode_table.spc_episodes_path(tag), "15_build_episodes"),
                        (episode_table.membership_path(tag), "15_build_episodes")):
        if not path.exists():
            raise SystemExit(f"no {path.name} — run scripts/{stage}.py")
    figures = config.OUTPUT_DIR / "figures"
    figures.mkdir(parents=True, exist_ok=True)

    t = load_tornadoes(tag)
    member = episode_table.membership(tag)
    episodes = pd.read_csv(episode_table.episodes_path(tag))
    dat_h = pd.read_csv(P / f"hazards_{tag}.csv",
                        usecols=["hazard_uid", "geometry_source", "time_begin_utc",
                                 "convective_day"]).assign(hazard_source="dat")
    spc_h = episode_table.spc_hazards(tag).assign(hazard_source="spc")
    spc_geom = (pd.DataFrame([f["properties"] for f in json.loads(
        episode_table.spc_hazards_path(tag, "geojson").read_text())["features"]])
        [["hazard_uid", "geometry_source"]])
    spc_h = spc_h.drop(columns=["geometry_source"], errors="ignore").merge(spc_geom,
                                                                           on="hazard_uid")
    hazards = pd.concat([dat_h, spc_h[["hazard_uid", "geometry_source", "time_begin_utc",
                                       "convective_day", "hazard_source"]]], ignore_index=True)
    times = episode_table.event_times(hazards, member,
                                      pd.read_csv(refs.SPC_TRACKS, usecols=["spc_id",
                                                                            "begin_utc"]))
    hazards = hazards.merge(times[["hazard_uid", "convective_day"]].rename(
        columns={"convective_day": "day"}), on="hazard_uid")
    hazards["year"] = hazards.day.str[:4].astype(int)

    # ── 1. reconciliation ──
    roles = t.role.value_counts()
    dat_member = member[member.hazard_source == "dat"]
    on_track = dat_member.spc_id.notna()
    multi = int((dat_member[on_track].spc_id.value_counts() > 1).sum())
    reconcile = pd.DataFrame([
        ("SPC tornadoes in the window (the population)", f"{len(t):,}", ""),
        ("… the closest SPC track of a DAT hazard", f"{roles.get('dat_closest', 0):,}",
         "with a DAT survey"),
        ("… a further piece of a DAT-surveyed tornado", f"{roles.get('dat_secondary', 0):,}",
         "with a DAT survey; counted through that DAT hazard, not again"),
        ("… no DAT survey: an SPC hazard", f"{roles.get('spc_hazard', 0):,}",
         "SPC's straight start–end line, or a point"),
        ("DAT hazards on an SPC track", f"{int(on_track.sum()):,}",
         f"on {dat_member.spc_id.nunique():,} tracks; {multi:,} tracks hold more than one"),
        ("DAT hazards with no SPC track", f"{int((~on_track).sum()):,}",
         "in no episode; `spc_match_status` says why (stage 17)"),
        ("**Hazards in the dataset**", f"**{len(hazards):,}**",
         f"{(hazards.hazard_source == 'dat').sum():,} DAT + "
         f"{(hazards.hazard_source == 'spc').sum():,} SPC"),
    ], columns=["", "count", "note"])
    geom = (hazards.groupby(["hazard_source", "geometry_source"]).size()
            .rename("hazards").reset_index())
    geom_md = md_table(pd.DataFrame({
        "hazard source": geom.hazard_source.str.upper(),
        "geometry": geom.geometry_source.map(lambda g: f"`{g}`"),
        "hazards": geom.hazards.map("{:,}".format)}), "llr")

    # ── 2.–6. figures ──
    per_year = fig_coverage_per_year(t, figures / "hz_coverage_per_year.png")
    rep = fig_representativeness(t, figures / "hz_representativeness.png")
    fig_climatology(t, figures / "hz_climatology.png")
    fig_geography(t, figures / "hz_geography.png")

    surveyed_share = t.surveyed.mean()
    first, last = per_year.index.min(), per_year.index.max()
    latest = rep[rep.era == f"{ERAS[-1][0]}–{ERAS[-1][1]}"].set_index(["factor", "category"])

    def share_of(factor: str, category: str) -> float:
        return latest.loc[(factor, category), "share"]

    rep_md = rep.assign(cell=[f"{s:.0%} of {n:,}" if n else "—"
                              for s, n in zip(rep.share, rep.n)])
    wide = rep_md.pivot_table(index=["factor", "category"], columns="era", values="cell",
                              aggfunc="first", sort=False).reset_index()
    wide.columns.name = None
    rep_table = md_table(wide, "ll" + "r" * len(ERAS))

    # ── deaths ──
    deaths = int(t.fat.sum())
    deaths_surveyed = int(t.fat[t.surveyed].sum())
    top = t.nlargest(10, "fat").copy()
    geography_path = P / f"hazard_geography_{tag}.csv"
    track_counties = {}
    if geography_path.exists():
        # All hazards on a track: one tornado can be several DAT hazards (stage 17).
        geo = pd.read_csv(geography_path, usecols=["hazard_uid", "counties"])
        on = member[["spc_id", "hazard_uid"]].dropna().merge(geo, on="hazard_uid")
        track_counties = {
            sid: "; ".join(dict.fromkeys(c for cs in g.counties.dropna() for c in cs.split(";")))
            for sid, g in on.groupby("spc_id")}
    top_md = md_table(pd.DataFrame({
        "date (SPC)": top.date,
        "rating": top.mag.map(lambda m: f"EF{int(m)}" if m >= 0 else "unrated"),
        "counties (stage 16, all hazards on the track)": top.spc_id.map(track_counties)
        .fillna("—"),
        "length (mi)": top.len.round(1), "deaths": top.fat.astype(int),
        "injuries": top.inj.astype(int),
        "DAT survey": np.where(top.surveyed, "yes", "**no**")}), "lllrrrl")

    # ── 7. official text ──
    cov = text_coverage(tag, hazards)
    accounts = oracle_accounts(tag)
    if cov is not None:
        fig_text_per_year(cov, figures / "hz_text_per_year.png")
        rows = []
        for kind, label in TEXT_KINDS + [("any_oracle", "any oracle text (first three)"),
                                         ("any_official", "any official text")]:
            row = {"text": label}
            for source in ("dat", "spc"):
                sub = cov[cov.hazard_source == source]
                row[f"{source.upper()} hazards ({len(sub):,})"] = (
                    f"{int(sub[kind].sum()):,} ({pct(sub[kind].sum(), len(sub))})")
            rows.append(row)
        text_md = md_table(pd.DataFrame(rows), "lrr")
        acc_md = ""
        if accounts is not None:
            acc = cov.assign(accounts=cov.hazard_uid.map(accounts).fillna(0).astype(int))
            acc["band"] = acc.accounts.clip(upper=3).map({0: "none", 1: "1", 2: "2",
                                                          3: "3 or more"})
            tab = (acc.groupby(["band", "hazard_source"]).size().unstack(fill_value=0)
                   .reindex(["none", "1", "2", "3 or more"], fill_value=0))
            acc_md = (
                "\n\nIndependent accounts among a hazard's oracle texts (stage 25: texts "
                "that share tornado-specific wording count once):\n\n"
                + md_table(pd.DataFrame({
                    "accounts": tab.index,
                    **{f"{s.upper()} hazards": [f"{v:,} ({pct(v, tab[s].sum())})"
                                                 for v in tab[s]] for s in tab.columns}}),
                    "l" + "r" * len(tab.columns)))
        dat_cov = cov[cov.hazard_source == "dat"]
        spc_cov = cov[cov.hazard_source == "spc"]
        text_section = f"""**Finding:** {pct(dat_cov.any_oracle.sum(), len(dat_cov))} of DAT hazards and
{pct(spc_cov.any_oracle.sum(), len(spc_cov))} of SPC hazards have at least one oracle text; a survey
statement (PNS) exists for {pct(dat_cov.pns.sum(), len(dat_cov))} of DAT hazards and
{pct(spc_cov.pns.sum(), len(spc_cov))} of SPC hazards.

{text_md}{acc_md}

![Share of hazards with each kind of official text, per year](figures/hz_text_per_year.png)

Oracle texts are written by the surveying office from its survey (survey
statement, narrative, DAT comment); LSRs are the office's reports during and just
after the event. News is not part of this report: it is independent text and
enters the pipeline later (stages 21–23, 30–34). Text matching: `text_qa_report.md`;
which texts are edits of one account: `same_source_edits_report.md`."""
    else:
        text_section = ("Not available: run `scripts/20_fetch_nws_text.py` and "
                        "`scripts/24_import_record_text.py`, then this stage again.")

    with_dat = episodes.has_dat.astype(bool)
    era_last = f"{ERAS[-1][0]}–{ERAS[-1][1]}"
    rated = latest.loc["rating"].drop(viz.UNRATED, errors="ignore").share
    shown = latest[latest.n >= 20]
    low, high = shown.share.idxmin(), shown.share.idxmax()
    rep_finding = (
        f"by rating, the share with a DAT survey runs from {share(rated.min())} "
        f"({rated.idxmin()}) to {share(rated.max())} ({rated.idxmax()}); tornadoes that killed "
        f"someone {share(share_of('deaths', 'killed someone'))}, others "
        f"{share(share_of('deaths', 'no deaths'))}; tracks under 1 mile "
        f"{share(share_of('track length', '< 1 mi'))}, of 15 miles or more "
        f"{share(share_of('track length', '≥ 15 mi'))}. Across all categories shown, the lowest "
        f"is {low[1]} ({low[0]}, {share(shown.share.min())}), the highest {high[1]} "
        f"({high[0]}, {share(shown.share.max())}). A result on DAT geometry describes the "
        "categories DAT covers more fully.")
    peak_all = int(t.groupby("month").size().idxmax())
    peak_dat = int(t[t.surveyed].groupby("month").size().idxmax())
    hour_all, hour_dat = t.hour_solar.median(), t.hour_solar[t.surveyed].median()
    len_all, len_dat = t.len[t.len > 0].median(), t.len[t.surveyed & (t.len > 0)].median()
    month_name = "January February March April May June July August September October November December".split()
    clim_finding = (
        f"busiest month {month_name[peak_all - 1]} for all tornadoes and "
        f"{month_name[peak_dat - 1]} for the DAT subset; median start {hour_all:.1f} h and "
        f"{hour_dat:.1f} h solar time; median track {len_all:.1f} and {len_dat:.1f} miles.")

    report = f"""# The tornado dataset: what it holds, and how representative its surveys are

Tag `{tag}`. Generated by `scripts/18_analyze_events.py` from stages 13–16, 20 and
24–25; every number below is computed, none typed in. Quality of the linkage and
of the records themselves: `events_qa_report.md`.

## At a glance

| | |
|---|---:|
| Tornadoes in SPC's record, {first}–{last} (the population) | {len(t):,} |
| … with a DAT survey (surveyed track or damage polygon) | {int(t.surveyed.sum()):,} ({surveyed_share:.1%}) |
| … with a DAT survey in {first} and in {last} | {share(per_year.share.iloc[0])} → {share(per_year.share.iloc[-1])} |
| Hazards in the dataset | {len(hazards):,} ({(hazards.hazard_source == 'dat').sum():,} DAT, {(hazards.hazard_source == 'spc').sum():,} SPC) |
| Episodes | {len(episodes):,} ({int(with_dat.sum()):,} with a DAT survey) |
| Deaths in SPC's record | {deaths:,} ({pct(deaths_surveyed, deaths)} in DAT-surveyed tornadoes) |

> **How to read this report.** SPC's tornado list is the population; DAT, which
> supplies the surveyed geometry, covers a subset that grew with the offices'
> adoption of the toolkit. Every figure shows the population in grey and the DAT
> subset in blue. Attributes (time, rating, length, casualties) are SPC's for
> both, so the two are compared on one record. Counts describe the record, not
> climate: the rise in DAT coverage is a change in practice.

## 1. From SPC's record to the dataset's hazards

**Finding:** every SPC tornado is either a DAT hazard, a piece of one, or an SPC
hazard of its own, so no tornado is missing and none counts twice.

{md_table(reconcile, "lrl")}

{geom_md}

## 2. DAT coverage over time

**Finding:** {share(per_year.share.iloc[0])} of tornadoes have a DAT survey in {first},
{share(per_year.share.iloc[-1])} in {last}. Any result that uses DAT geometry describes
the later years far more than the earlier ones.

![Tornadoes per year and the share with a DAT survey](figures/hz_coverage_per_year.png)

{details("Per year", md_table(pd.DataFrame({"year": per_year.index, "SPC tornadoes": per_year['all'].map('{:,}'.format), "with a DAT survey": per_year.surveyed.map('{:,}'.format), "share": per_year.share.map('{:.0%}'.format)}), "lrrr"))}

## 3. Is the DAT subset representative?

**Finding ({era_last}):** {rep_finding}

Each dot is the share of a category's tornadoes that have a DAT survey, in one
era; comparing within an era keeps the toolkit's adoption over time from looking
like a property of the category. The grey bar spans the eras.

![Share of tornadoes with a DAT survey, by category and era](figures/hz_representativeness.png)

{details("The numbers behind the figure", rep_table)}

## 4. Season, time of day and track length

**Finding:** {clim_finding}

![Month, time of day and track length: all tornadoes and those DAT surveyed](figures/hz_climatology.png)

Time of day is local solar time (UTC shifted by the start longitude), so the
late-afternoon peak is not smeared across four time zones. Track lengths are
SPC's stated lengths for both.

## 5. Where

![Tornado density, and the share with a DAT survey](figures/hz_geography.png)

Equal-area projection (EPSG:5070), start points, contiguous US. The right panel
shows only cells with at least 10 tornadoes, so a single surveyed tornado does not
paint a cell dark.

## 6. Deaths

**Finding:** SPC's record holds {deaths:,} deaths; {pct(deaths_surveyed, deaths)} were in
tornadoes DAT surveyed. DAT keeps its own death counts; they agree with SPC's for
most of the same tornadoes but differ widely for a few, so this report uses SPC's
throughout (comparison: `events_qa_report.md`, section 6).

The ten deadliest tornadoes (SPC's record):

{top_md}

## 7. Official text per hazard

{text_section}

## 8. Notes for users

- **Population and subset.** Filter on `hazard_source` (DAT or SPC hazard) and
  `has_dat` (episodes); report which you used. Section 3 says what a DAT-only
  analysis leaves out.
- **SPC hazards have SPC's straight start–end line**, or a point, not a surveyed
  track; stage 16 measures how well such a line finds the counties and places of a
  surveyed track.
- **Ratings** are grouped EF0–EF3 and EF4–EF5; unrated records (`-9`, EFU) are their
  own class, not the weakest one.
- **Interactive map:** `outputs/hazard_map.html` (`scripts/19_event_map.py`), every
  hazard with its source, episode and official texts.
"""
    (config.OUTPUT_DIR / "hazard_analysis_report.md").write_text(report, encoding="utf-8")
    print(f"{len(t):,} SPC tornadoes ({surveyed_share:.1%} with a DAT survey), "
          f"{len(hazards):,} hazards, {len(episodes):,} episodes")
    print(f"wrote {config.OUTPUT_DIR / 'hazard_analysis_report.md'} and "
          f"{5 if cov is not None else 4} figures")


if __name__ == "__main__":
    main()

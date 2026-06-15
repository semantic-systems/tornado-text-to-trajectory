"""Generate a visual analysis report for the NOAA DAT tornado event dataset.

Reads the most recent ``events_*.geojson`` produced by
``extract_noaa_polygons.py`` (one feature per grouped tornado event, with
aggregated attributes and RFC 7946 geometry) and writes a Markdown report
with polished matplotlib figures to ``report_figures/``.
"""

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import spacy

# ── paths ────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
OUTPUT_DIR = REPO_ROOT / "outputs"
FIGURE_DIR = OUTPUT_DIR / "figures"
REPORT_PATH = OUTPUT_DIR / "tornado_analysis_report.md"
GEOREF_PATH = OUTPUT_DIR / "georeferenceable_events.geojson"
FIGURE_DIR.mkdir(parents=True, exist_ok=True)

# ── styling ──────────────────────────────────────────────────────────────────
# Instead of a conventional background grid we draw the grid *on top* of the
# bars in white (see `white_grid`). Because the axes background is also white,
# the gridlines are only visible where they cross a filled element — a clean,
# ink-light way to keep the value scale readable inside the bars themselves.
plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": "#b8b8b8",
    "axes.linewidth": 0.9,
    "axes.grid": False,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.titlepad": 12,
    "axes.labelsize": 11,
    "axes.labelcolor": "#333333",
    "xtick.color": "#555555",
    "ytick.color": "#555555",
    "xtick.labelcolor": "#333333",
    "ytick.labelcolor": "#333333",
    "font.family": "sans-serif",
    "font.size": 10.5,
    "legend.fontsize": 9,
    "figure.dpi": 110,
})

GRID_WHITE = "#ffffff"
ACCENT = "#d1495b"  # muted crimson for median / reference markers

# ── spaCy NER for toponym detection ─────────────────────────────────────────
TOPONYM_LABELS = {"GPE", "LOC", "FAC"}  # geo-political entity, location, facility
try:
    _nlp = spacy.load("en_core_web_sm", disable=["tagger", "parser", "lemmatizer", "attribute_ruler"])
except OSError:
    import subprocess
    subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"], check=True)
    _nlp = spacy.load("en_core_web_sm", disable=["tagger", "parser", "lemmatizer", "attribute_ruler"])

EF_ORDER = ["EF0", "EF1", "EF2", "EF3", "EF4", "EF5", "Other", "Unknown"]
EF_COLORS = {
    "EF0": "#4caf50", "EF1": "#a3d977", "EF2": "#ffd54f",
    "EF3": "#ff9800", "EF4": "#e64a3b", "EF5": "#8e24aa",
    "Other": "#42a5f5", "Unknown": "#bdbdbd",
}
# Collapse the many non-standard `efscale` values seen in the DAT data.
EF_ALIASES = {
    "EF3+": "EF3", "TSTM/Wind": "Other", "Tropical": "Other",
    "EFU": "Unknown", "UNKNOWN": "Unknown", "N/A": "Unknown",
    None: "Unknown",
}

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

CONUS_BOUNDS = dict(lon=(-180, -60), lat=(15, 72))  # incl. AK / HI / PR


# ── helpers ──────────────────────────────────────────────────────────────────

def latest_events_file() -> Path:
    candidates = sorted(DATA_DIR.glob("events_*.geojson"))
    if not candidates:
        raise SystemExit(f"No events_*.geojson found in {DATA_DIR}")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def normalize_ef(raw) -> str:
    if raw in EF_ORDER:
        return raw
    return EF_ALIASES.get(raw, "Unknown")


def iter_coords(geom):
    """Yield all [lon, lat] pairs of a GeoJSON geometry, any type."""
    if geom is None:
        return
    t, c = geom["type"], geom.get("coordinates")
    if t == "Point":
        yield c
    elif t in ("MultiPoint", "LineString"):
        yield from c
    elif t in ("MultiLineString", "Polygon"):
        for part in c:
            yield from part
    elif t == "MultiPolygon":
        for poly in c:
            for ring in poly:
                yield from ring
    elif t == "GeometryCollection":
        for sub in geom["geometries"]:
            yield from iter_coords(sub)


def centroid(geom):
    pts = list(iter_coords(geom))
    if not pts:
        return None, None
    lons, lats = zip(*pts)
    return sum(lons) / len(lons), sum(lats) / len(lats)


def save_fig(name: str) -> str:
    path = FIGURE_DIR / f"{name}.png"
    plt.savefig(path, dpi=160, bbox_inches="tight")
    plt.close()
    return path.relative_to(OUTPUT_DIR).as_posix()  # relative to the report file


def white_grid(ax, axis="y", lw=1.3):
    """Draw a white grid *on top* of the plotted bars.

    With ``set_axisbelow(False)`` matplotlib renders the gridlines above the
    bars; matplotlib recomputes them at the final tick positions on every
    draw, so (unlike manually drawn segments) they always land correctly.
    Over the white axes background the lines vanish, leaving visible marks
    only where they cross a filled bar.
    """
    ax.set_axisbelow(False)
    ax.grid(axis=axis, color=GRID_WHITE, linewidth=lw, zorder=3)


def polar_white_grid(ax, lw=1.3):
    """White radial gridlines drawn on top of polar bars (circles only)."""
    ax.set_axisbelow(False)
    ax.xaxis.grid(False)                              # no radial spokes
    ax.yaxis.grid(True, color=GRID_WHITE, linewidth=lw, zorder=3)


# ── load data ────────────────────────────────────────────────────────────────
DATA_FILE = latest_events_file()
with open(DATA_FILE, encoding="utf-8") as fh:
    geojson = json.load(fh)
features = geojson["features"]

records = []
for feat in features:
    p = feat["properties"]
    sd = p.get("stormdate")
    dt = datetime.fromtimestamp(sd / 1000, tz=timezone.utc) if sd else None
    lon, lat = centroid(feat["geometry"])
    records.append({
        "efscale": normalize_ef(p.get("efscale")),
        "dt": dt,
        "injuries": p.get("injuries") or 0,
        "fatalities": p.get("fatalities") or 0,
        "cropdamage": p.get("cropdamage"),
        "propdamage": p.get("propdamage"),
        "maxwind": p.get("maxwind"),
        "track_length": p.get("total_track_length"),
        "max_width": p.get("max_damage_width"),
        "wfo": p.get("wfo"),
        "lon": lon, "lat": lat,
        "comments": p.get("comments") or "",
        "n_polygons": p.get("n_polygons", 0),
        "n_lines": p.get("n_lines", 0),
    })

N = len(records)
n_raw_polygons = sum(r["n_polygons"] for r in records)
n_raw_lines = sum(r["n_lines"] for r in records)
dated = [r for r in records if r["dt"]]
ef_counts = Counter(r["efscale"] for r in records)

# ── comment NER: which events can be georeferenced from their description ──
print(f"Running spaCy NER on {N:,} comments ...")
for r, doc in zip(records, _nlp.pipe((r["comments"] for r in records), batch_size=128)):
    r["word_count"] = len(r["comments"].split())
    r["has_toponym"] = any(ent.label_ in TOPONYM_LABELS for ent in doc.ents)

n_with_comments = sum(1 for r in records if r["comments"])
n_toponym = sum(1 for r in records if r["has_toponym"])

georeferenceable = [feat for feat, r in zip(features, records) if r["has_toponym"]]
with open(GEOREF_PATH, "w", encoding="utf-8") as fh:
    json.dump({"type": "FeatureCollection", "features": georeferenceable}, fh)


# ── Figure 1: EF-scale distribution ─────────────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 4.5))
labels = [e for e in EF_ORDER if ef_counts.get(e)]
values = [ef_counts[e] for e in labels]
colors = [EF_COLORS[e] for e in labels]
bars = ax.bar(labels, values, color=colors, zorder=2)
ax.set_ylabel("Number of events")
ax.set_title("Tornado Events by EF-Scale Rating")
ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
ax.margins(y=0.14)
ax.tick_params(bottom=False)
white_grid(ax)
for bar, val in zip(bars, values):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(values) * 0.012,
            f"{val:,}\n{val / N:.1%}", ha="center", va="bottom", fontsize=9,
            color="#333333", zorder=4, linespacing=1.3)
plt.tight_layout()
fig_ef = save_fig("ef_scale_distribution")


# ── Figure 2: events per year, stacked by EF-scale ──────────────────────────
years = sorted({r["dt"].year for r in dated})
year_ef = {e: [sum(1 for r in dated if r["dt"].year == y and r["efscale"] == e) for y in years]
           for e in EF_ORDER if ef_counts.get(e)}

fig, ax = plt.subplots(figsize=(max(9, len(years) * 0.32), 5))
bottom = np.zeros(len(years))
for e, counts in year_ef.items():
    counts = np.array(counts)
    ax.bar(years, counts, bottom=bottom, color=EF_COLORS[e], label=e, width=0.82, zorder=2)
    bottom += counts
ax.set_title("Tornado Events per Year, by EF-Scale")
ax.set_xlabel("Year")
ax.set_ylabel("Number of events")
ax.legend(ncols=len(year_ef), loc="upper left", frameon=False,
          handlelength=1.0, columnspacing=1.2)
ax.set_xlim(min(years) - 1, max(years) + 1)
ax.margins(y=0.12)
ax.tick_params(bottom=False)
white_grid(ax)
plt.tight_layout()
fig_year = save_fig("events_per_year")


# ── Figure 3: seasonal distribution (polar bar chart) ───────────────────────
month_counts = Counter(r["dt"].month for r in dated)
theta = np.linspace(0, 2 * np.pi, 12, endpoint=False)
radii = [month_counts.get(m, 0) for m in range(1, 13)]
cmap = plt.get_cmap("twilight_shifted")
bar_colors = [cmap(i / 12) for i in range(12)]

fig = plt.figure(figsize=(6.5, 6.5))
ax = fig.add_subplot(projection="polar")
ax.bar(theta, radii, width=2 * np.pi / 12 * 0.9, color=bar_colors,
       align="edge", zorder=2)
ax.set_xticks(theta + (2 * np.pi / 12 * 0.45))
ax.set_xticklabels(MONTH_NAMES)
ax.set_theta_zero_location("N")
ax.set_theta_direction(-1)
ax.set_title("Seasonal Distribution of Tornado Events", pad=24)
ax.set_rlabel_position(135)
ax.tick_params(axis="y", labelsize=8, colors="#777777")
ax.spines["polar"].set_color("#dddddd")
polar_white_grid(ax)
plt.tight_layout()
fig_season = save_fig("seasonal_distribution")


# ── Figure 4: geographic distribution ───────────────────────────────────────
located = [r for r in records if r["lon"] is not None
           and CONUS_BOUNDS["lon"][0] <= r["lon"] <= CONUS_BOUNDS["lon"][1]
           and CONUS_BOUNDS["lat"][0] <= r["lat"] <= CONUS_BOUNDS["lat"][1]]

fig, axes = plt.subplots(1, 2, figsize=(13, 6))

# Left: significant (EF2+) events highlighted over a light "weak/unknown" base
strong = ["EF2", "EF3", "EF4", "EF5"]
ax = axes[0]
weak_pts = [(r["lon"], r["lat"]) for r in located if r["efscale"] not in strong]
if weak_pts:
    xs, ys = zip(*weak_pts)
    ax.scatter(xs, ys, s=5, color="#d9d9d9", alpha=0.5, linewidths=0,
               label="EF0–EF1 / other", zorder=1)
for e in strong:
    pts = [(r["lon"], r["lat"]) for r in located if r["efscale"] == e]
    if not pts:
        continue
    xs, ys = zip(*pts)
    ax.scatter(xs, ys, s=16, color=EF_COLORS[e], alpha=0.85, label=e,
               linewidths=0.3, edgecolors="white", zorder=2)
ax.set_title("Significant (EF2+) Tornado Locations")
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.set_aspect("equal")
ax.legend(markerscale=1.8, frameon=False, loc="lower left")

# Right: overall event density
ax = axes[1]
hb = ax.hexbin([r["lon"] for r in located], [r["lat"] for r in located],
               gridsize=60, cmap="magma", mincnt=1, bins="log",
               linewidths=0.2, edgecolors="#2a2a2a")
ax.set_title("Event Density")
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.set_aspect("equal")
ax.set_facecolor("#f2efe9")
cb = fig.colorbar(hb, ax=ax, label="Events (log scale)", shrink=0.82)
cb.outline.set_visible(False)

for ax in axes:
    for spine in ax.spines.values():
        spine.set_color("#dddddd")

plt.tight_layout()
fig_geo = save_fig("geographic_distribution")


# ── Figure 5: track length & damage width distributions ─────────────────────
lengths = [r["track_length"] for r in records if r["track_length"] and r["track_length"] > 0]
widths = [r["max_width"] for r in records if r["max_width"] and r["max_width"] > 0]

fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

ax = axes[0]
bins = np.logspace(np.log10(min(lengths)), np.log10(max(lengths)), 30)
ax.hist(lengths, bins=bins, color="#4a89c4", zorder=2)
ax.axvline(np.median(lengths), color=ACCENT, ls="--", lw=1.8, zorder=4,
           label=f"Median: {np.median(lengths):.2f} mi")
ax.set_xscale("log")
ax.set_xlabel("Track length (miles)")
ax.set_ylabel("Number of events")
ax.set_title("Track Length Distribution")
ax.legend(frameon=False)
white_grid(ax)

ax = axes[1]
bins = np.logspace(np.log10(min(widths)), np.log10(max(widths)), 30)
ax.hist(widths, bins=bins, color="#e8943a", zorder=2)
ax.axvline(np.median(widths), color=ACCENT, ls="--", lw=1.8, zorder=4,
           label=f"Median: {np.median(widths):.0f} yd")
ax.set_xscale("log")
ax.set_xlabel("Max damage width (yards)")
ax.set_ylabel("Number of events")
ax.set_title("Damage Width Distribution")
ax.legend(frameon=False)
white_grid(ax)

plt.tight_layout()
fig_geom = save_fig("track_geometry")


# ── Figure 6: human impact by EF-scale ──────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
inj_by_ef = [sum(r["injuries"] for r in records if r["efscale"] == e) for e in labels]
fat_by_ef = [sum(r["fatalities"] for r in records if r["efscale"] == e) for e in labels]

def impact_panel(ax, totals, title, ylabel):
    bars = ax.bar(labels, totals, color=colors, zorder=2)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_yscale("log")
    ax.set_ylim(top=max(totals) * 2.2)
    ax.tick_params(bottom=False)
    white_grid(ax)
    for bar, val in zip(bars, totals):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() * 1.15,
                    f"{val:,}", ha="center", va="bottom", fontsize=8.5,
                    color="#333333", zorder=4)

impact_panel(axes[0], inj_by_ef, "Total Injuries by EF-Scale", "Injuries")
impact_panel(axes[1], fat_by_ef, "Total Fatalities by EF-Scale", "Fatalities")

plt.tight_layout()
fig_impact = save_fig("human_impact")


# ── Figure 7: comment length distribution ───────────────────────────────────
wc_vals = [r["word_count"] for r in records if r["word_count"] > 0]
p95 = np.percentile(wc_vals, 95)
bins = np.arange(0, p95 + 5, 5)

fig, ax = plt.subplots(figsize=(9, 4.5))
ax.hist([v for v in wc_vals if v <= p95], bins=bins, color="#7e57c2", zorder=2)
ax.axvline(np.median(wc_vals), color=ACCENT, ls="--", lw=1.8, zorder=4,
           label=f"Median: {np.median(wc_vals):.0f} words")
ax.set_xlabel("Comment word count")
ax.set_ylabel("Number of events")
ax.set_title("Comment Length Distribution (≤95th percentile)")
ax.legend(frameon=False)
white_grid(ax)
plt.tight_layout()
fig_comments = save_fig("comment_word_count")


# ── summary stats ────────────────────────────────────────────────────────────
total_injuries = sum(r["injuries"] for r in records)
total_fatalities = sum(r["fatalities"] for r in records)
total_propdamage = sum(r["propdamage"] for r in records if r["propdamage"])
total_cropdamage = sum(r["cropdamage"] for r in records if r["cropdamage"])

deadliest = sorted(records, key=lambda r: (r["fatalities"], r["injuries"]), reverse=True)[:10]
costliest = sorted(
    (r for r in records if r["propdamage"] or r["cropdamage"]),
    key=lambda r: (r["propdamage"] or 0) + (r["cropdamage"] or 0), reverse=True,
)[:10]


# ── build report ─────────────────────────────────────────────────────────────
lines = [
    "# NOAA Tornado Damage Assessment — Analysis Report",
    "",
    f"> Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} "
    f"from `{DATA_FILE.relative_to(REPO_ROOT).as_posix()}`",
    "",
    "## Overview",
    "",
    "| | |",
    "|---|---|",
    f"| Tornado events | {N:,} |",
    f"| Built from | {n_raw_polygons:,} damage polygons + {n_raw_lines:,} path lines |",
    f"| Date range | {min(r['dt'] for r in dated).date() if dated else 'n/a'} – "
    f"{max(r['dt'] for r in dated).date() if dated else 'n/a'} |",
    f"| Total injuries | {total_injuries:,} |",
    f"| Total fatalities | {total_fatalities:,} |",
    f"| Total property damage | ${total_propdamage:,.0f} |",
    f"| Total crop damage | ${total_cropdamage:,.0f} |",
    "",
    "---",
    "",
    "## EF-Scale Distribution",
    "",
    "Non-standard ratings reported by NOAA (`EFU`, `UNKNOWN`, `N/A`) are grouped as "
    "**Unknown**; `TSTM/Wind` and `Tropical` are grouped as **Other**; `EF3+` is "
    "counted as **EF3**.",
    "",
    f"![EF-scale distribution]({fig_ef})",
    "",
    "---",
    "",
    "## Temporal Patterns",
    "",
    f"![Events per year]({fig_year})",
    "",
    f"![Seasonal distribution]({fig_season})",
    "",
    "---",
    "",
    "## Geographic Distribution",
    "",
    f"_{len(located):,} of {N:,} events have a usable centroid within the "
    f"continental US / Alaska / Hawaii / Puerto Rico bounding box._",
    "",
    f"![Geographic distribution]({fig_geo})",
    "",
    "---",
    "",
    "## Track Geometry",
    "",
    f"_{len(lengths):,} events with a known track length, {len(widths):,} with a "
    f"known max damage width._",
    "",
    f"![Track geometry]({fig_geom})",
    "",
    "---",
    "",
    "## Human Impact",
    "",
    f"![Human impact by EF-scale]({fig_impact})",
    "",
    "### 10 Deadliest Events",
    "",
    "| Date | EF | Fatalities | Injuries | WFO |",
    "|---|---|---|---|---|",
]
for r in deadliest:
    lines.append(
        f"| {r['dt'].date() if r['dt'] else 'n/a'} | {r['efscale']} | "
        f"{r['fatalities']} | {r['injuries']} | {r['wfo'] or 'n/a'} |"
    )

lines += [
    "",
    "### 10 Costliest Events",
    "",
    "| Date | EF | Property Damage | Crop Damage | WFO |",
    "|---|---|---|---|---|",
]
for r in costliest:
    lines.append(
        f"| {r['dt'].date() if r['dt'] else 'n/a'} | {r['efscale']} | "
        f"${r['propdamage'] or 0:,.0f} | ${r['cropdamage'] or 0:,.0f} | {r['wfo'] or 'n/a'} |"
    )

lines += [
    "",
    "---",
    "",
    "## Comment & Georeferencing Analysis",
    "",
    "Each event's `comments` field is run through spaCy NER "
    "(`en_core_web_sm`). Comments containing at least one entity tagged "
    "`GPE` (geo-political entity), `LOC` (location), or `FAC` (facility) are "
    "considered to describe a place that could be used to georeference the "
    "event's track/polygon from text alone.",
    "",
    "| | |",
    "|---|---|",
    f"| Events with a comment | {n_with_comments:,} ({n_with_comments / N:.1%}) |",
    f"| **Events with a georeferenceable description** | **{n_toponym:,} "
    f"({n_toponym / N:.1%})** |",
    "",
    f"![Comment length distribution]({fig_comments})",
    "",
    f"_The {n_toponym:,} georeferenceable events were written to "
    f"`{GEOREF_PATH.relative_to(REPO_ROOT).as_posix()}`._",
    "",
]

REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
print(f"Report  -> {REPORT_PATH.relative_to(REPO_ROOT)}")
print(f"Figures -> {FIGURE_DIR.relative_to(REPO_ROOT)}/")

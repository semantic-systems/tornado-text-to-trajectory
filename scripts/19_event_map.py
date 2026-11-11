"""Stage 19 — build a self-contained interactive map of every hazard.

Writes `outputs/hazard_map.html`: one file, no build step. Leaflet (vendored in
the viewer, embedded here) gives the OpenStreetMap basemap, zoom and pan; the
hazards are drawn on one canvas above it. Tracks are simplified and projected to
Web Mercator in Python, so the page ships integer coordinates and the browser
only has to scale them, which keeps ~20,000 hazards interactive. Only the
basemap tiles come over the network; the page works without them (switch the
basemap off, or offline), with state outlines instead.

Web Mercator, because the tiles use it, is not equal-area: stage 18's density
maps are, and are the place to compare areas.

Every hazard of stage 15: DAT's surveyed tracks (solid) and SPC tornadoes
without a DAT survey (dashed: SPC's straight start–end line, or a hollow dot).
Controls: a slider by month or by day (days with tornadoes) with play/pause and
a date to jump to, a window mode (this month or day / so far this year or month
/ everything so far), filters for rating, hazard source and official text,
hover details (source, episode, texts) and a table of the hazards shown.
Clicking a hazard shows its whole episode, for checking how tornadoes were
grouped; Esc or the chip's × returns to the month view. News is not shown.

    python scripts/19_event_map.py
    python scripts/19_event_map.py --simplify-m 150

Open it through a local web server (``python -m http.server 8791 --directory
outputs``): the OpenStreetMap tile servers refuse requests without a referring
page, which a file opened from disk does not send.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import _bootstrap  # noqa: F401

import pandas as pd
from shapely.geometry import LineString, MultiLineString

from tornado_dataset import config, viz
from tornado_dataset.dat import episode_table
from tornado_dataset.dat import references as refs
from tornado_dataset.dat.geometry import to_shapely
from tornado_dataset.geo import pixels
from tornado_dataset.geo.gazetteer import state_outlines
from tornado_dataset.text import official

bounds_of = pixels.bounds_of
LEAFLET = Path(__file__).resolve().parent.parent / "src" / "tornado_dataset" / "viewer" / "static" / "vendor"


def main() -> None:
    default_tag = f"{config.WINDOW_START.isoformat()}_{config.WINDOW_END.isoformat()}"
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", default=default_tag)
    # Tracks are short — the median is 1.3 miles — so the tolerance has to stay
    # well under that or half the dataset simplifies away to a single point. It
    # also sets how far the reader can usefully zoom: 60 m is roughly one screen
    # pixel at 70x, past which the geometry, not the screen, is the limit.
    parser.add_argument("--simplify-m", type=float, default=60.0,
                        help="track simplification tolerance in metres")
    args = parser.parse_args()

    tag = args.tag
    P = config.PROCESSED_DIR
    cols = ["hazard_uid", "convective_day", "time_begin_utc", "efscale", "path_length_mi",
            "fatalities", "injuries"]
    dat = pd.read_csv(P / f"hazards_{tag}.csv", usecols=cols + ["has_polygon"])
    spc = episode_table.spc_hazards(tag)[cols].assign(has_polygon=False)
    hazards = pd.concat([dat.assign(hazard_source="dat"), spc.assign(hazard_source="spc")],
                        ignore_index=True)
    features = (json.loads((P / f"hazards_{tag}.geojson").read_text())["features"]
                + json.loads(episode_table.spc_hazards_path(tag, "geojson")
                             .read_text())["features"])
    member = episode_table.membership(tag)
    # The convective day the hazard is matched on: SPC's where DAT's clock was wrong.
    times = episode_table.event_times(hazards, member,
                                      pd.read_csv(refs.SPC_TRACKS, usecols=["spc_id",
                                                                            "begin_utc"]))
    hazards = hazards.drop(columns="convective_day").merge(
        times[["hazard_uid", "convective_day"]], on="hazard_uid")
    geography = episode_table.geography(tag, ("dat", "spc"))
    place = geography.set_index("hazard_uid")[["nearest_place", "counties", "states", "wfo"]]
    attributes = hazards.set_index("hazard_uid")

    episode_uids = sorted(member.episode_uid.dropna().unique())
    episode_index = {u: i for i, u in enumerate(episode_uids)}
    episode_of = dict(zip(member.hazard_uid, member.episode_uid))
    episode_size = member.episode_uid.value_counts()
    texts = official.counts(tag)
    text_kinds = list(official.KINDS)
    accounts_path = P / f"same_source_edits_{tag}.csv"
    accounts = {}
    if accounts_path.exists():
        rows = pd.read_csv(accounts_path, usecols=["hazard_uid", "source_type", "edit_group"])
        rows = rows[rows.source_type.isin(["pns", "storm_events_narrative", "dat_comment"])]
        accounts = rows.groupby("hazard_uid").edit_group.nunique().to_dict()

    # ── basemap ──
    outlines = []
    for feature in state_outlines(2025, simplify_deg=0.02)["features"]:
        geometry = feature["geometry"]
        rings = (geometry["coordinates"] if geometry["type"] == "Polygon"
                 else [ring for polygon in geometry["coordinates"] for ring in polygon])
        for ring in rings:
            flat = pixels.ring_to_mercator(ring)
            if len(flat) >= 6:
                outlines.append(flat)

    # ── tracks ──
    tracks, skipped = [], 0
    for feature in features:
        uid = feature["properties"]["hazard_uid"]
        geom = to_shapely(feature.get("geometry"))
        if geom is None or geom.is_empty:
            skipped += 1
            continue

        # A hazard's geometry can be a track line, a damage polygon, or a
        # collection of both. The trajectory is the subject, so lines are drawn at
        # every zoom; the damage polygons are kept separately and revealed once
        # the reader zooms in far enough for their shape to mean anything.
        parts = list(geom.geoms) if geom.geom_type.startswith(("Multi", "Geometry")) else [geom]
        # An SPC tornado with no recorded end is a point: drawn as a dot, like a
        # surveyed track too short for one screen pixel.
        lines = [p for p in parts
                 if isinstance(p, (LineString, MultiLineString)) or p.geom_type == "Point"]
        polygons = [p for p in parts if p.geom_type in ("Polygon", "MultiPolygon")]
        tolerance = args.simplify_m / 111_000

        def flatten(geometries) -> list[list[int]]:
            out = []
            for part in geometries:
                simplified = part.simplify(tolerance, preserve_topology=False)
                if simplified.is_empty:
                    # A footprint smaller than the tolerance collapses: keep it as a
                    # dot rather than lose the tornado.
                    simplified = part.representative_point()
                segments = (list(simplified.geoms)
                            if simplified.geom_type.startswith("Multi") else [simplified])
                for segment in segments:
                    if segment.is_empty:
                        continue
                    coords = (list(segment.exterior.coords)
                              if segment.geom_type == "Polygon" else list(segment.coords))
                    flat = pixels.ring_to_mercator(coords)
                    # A track shorter than one screen pixel becomes a single
                    # point. It is kept and drawn as a dot: a brief tornado that
                    # leaves no visible line is still a tornado, and dropping it
                    # would quietly bias the map towards long tracks.
                    if len(flat) >= 2:
                        out.append(flat)
            return out

        drawn = flatten(lines or polygons)
        rings = flatten(polygons) if lines else []
        if not drawn:
            skipped += 1
            continue

        row = attributes.loc[uid]
        day = str(row.convective_day or "")
        info = place.loc[uid] if uid in place.index else None
        length = row.path_length_mi
        episode = episode_of.get(uid)
        count = ([int(texts.at[uid, k]) for k in text_kinds]
                 if texts is not None and uid in texts.index else [0] * len(text_kinds))
        tracks.append({
            "u": uid,
            "src": 0 if row.hazard_source == "dat" else 1,
            "ep": episode_index.get(episode, -1),
            "tx": count,
            "ac": accounts.get(uid),
            "m": (int(day[:4]) - config.WINDOW_START.year) * 12 + int(day[5:7]) - 1,
            "d": day,
            "e": viz.ef_class(row.efscale),
            "p": drawn,
            "q": rings,
            "b": bounds_of(drawn + rings),
            "l": None if pd.isna(length) else round(float(length), 1),
            "f": int(row.fatalities) if pd.notna(row.fatalities) else 0,
            "i": int(row.injuries) if pd.notna(row.injuries) else 0,
            "w": info.wfo if info is not None and pd.notna(info.wfo) else "",
            "n": (info.nearest_place if info is not None and pd.notna(info.nearest_place)
                  else ""),
            "s": (info.states if info is not None and pd.notna(info.states) else ""),
            "g": bool(row.has_polygon),
        })

    months = [f"{config.WINDOW_START.year + i // 12}-{i % 12 + 1:02d}"
              for i in range((config.WINDOW_END.year - config.WINDOW_START.year + 1) * 12)]
    # Day steps run over the convective days that have a hazard: stepping through
    # 5,800 calendar days, most of them empty, would make playback unusable.
    days = sorted({t["d"] for t in tracks if t["d"]})
    day_index = {d: i for i, d in enumerate(days)}
    for t in tracks:
        t["di"] = day_index.get(t["d"], -1)
    payload = {
        "z0": pixels.MERCATOR_ZOOM,
        "outlines": outlines, "tracks": tracks, "months": months, "days": days,
        "efClasses": viz.EF_CLASSES + [viz.UNRATED],
        "efLabels": {**viz.EF_CLASS_LABELS, viz.UNRATED: "unrated"},
        "rampLight": viz.EF_RAMP_LIGHT + [viz.LIGHT["unrated"]],
        "rampDark": viz.EF_RAMP_DARK + [viz.DARK["unrated"]],
        "episodes": [[u, int(episode_size.get(u, 0))] for u in episode_uids],
        "textKinds": [official.KINDS[k] for k in text_kinds],
        "hasTexts": texts is not None,
    }

    html = (HTML_TEMPLATE
            .replace("__LEAFLET_CSS__", (LEAFLET / "leaflet.css").read_text(encoding="utf-8"))
            .replace("__LEAFLET_JS__", (LEAFLET / "leaflet.js").read_text(encoding="utf-8"))
            .replace("__DATA__", json.dumps(payload, separators=(",", ":"))))
    out_path = config.OUTPUT_DIR / "hazard_map.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    size_mb = out_path.stat().st_size / 1e6
    by_source = pd.Series([t["src"] for t in tracks]).map({0: "DAT", 1: "SPC"}).value_counts()
    print(f"{len(tracks):,} hazards drawn ({by_source.to_dict()}; {skipped} without usable "
          f"geometry), {len(outlines)} basemap rings")
    print(f"wrote {out_path} ({size_mb:.1f} MB, self-contained)")


HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tornado hazards, 2010–2025</title>
<style>__LEAFLET_CSS__</style>
<style>
  :root {
    color-scheme: light dark;
    --surface: #fcfcfb; --plane: #f9f9f7; --primary: #0b0b0b; --secondary: #52514e;
    --muted: #898781; --grid: #e1e0d9; --axis: #c3c2b7; --accent: #2a78d6;
    --border: rgba(11,11,11,0.10);
    --tiles: grayscale(1) contrast(0.92) opacity(0.7);
  }
  @media (prefers-color-scheme: dark) {
    :root:where(:not([data-theme="light"])) {
      --surface: #1a1a19; --plane: #0d0d0d; --primary: #ffffff; --secondary: #c3c2b7;
      --muted: #898781; --grid: #2c2c2a; --axis: #383835; --accent: #3987e5;
      --border: rgba(255,255,255,0.10);
      --tiles: grayscale(1) invert(1) contrast(0.85) brightness(0.85) opacity(0.75);
    }
  }
  :root[data-theme="dark"] {
    --surface: #1a1a19; --plane: #0d0d0d; --primary: #ffffff; --secondary: #c3c2b7;
    --muted: #898781; --grid: #2c2c2a; --axis: #383835; --accent: #3987e5;
    --border: rgba(255,255,255,0.10);
    --tiles: grayscale(1) invert(1) contrast(0.85) brightness(0.85) opacity(0.75);
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--plane); color: var(--primary);
    font: 14px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif;
  }
  .wrap { max-width: 1180px; margin: 0 auto; padding: 24px 16px 48px; }
  h1 { font-size: 20px; margin: 0 0 4px; }
  .sub { color: var(--secondary); margin: 0 0 20px; max-width: 75ch; }
  .card {
    background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
    padding: 16px;
  }
  .controls {
    display: flex; flex-wrap: wrap; gap: 10px 18px; align-items: center; margin-bottom: 12px;
  }
  .controls label { color: var(--secondary); font-size: 13px; display: flex; gap: 6px;
    align-items: center; }
  select, button, input[type=date] {
    font: inherit; font-size: 13px; color: var(--primary); background: var(--surface);
    border: 1px solid var(--axis); border-radius: 6px; padding: 5px 9px; cursor: pointer;
  }
  button.play { min-width: 78px; font-weight: 600; }
  .seg { display: inline-flex; border: 1px solid var(--axis); border-radius: 6px; overflow: hidden; }
  .seg button { border: 0; border-radius: 0; padding: 5px 11px; }
  .seg button[aria-pressed="true"] { background: var(--accent); color: #fff; }
  .slider-row { display: flex; align-items: center; gap: 12px; margin: 4px 0 12px; }
  input[type=range] { flex: 1; accent-color: var(--accent); }
  .when { font-variant-numeric: tabular-nums; font-weight: 600; min-width: 15ch; }
  .count { color: var(--secondary); font-variant-numeric: tabular-nums; }
  .map-holder { position: relative; }
  #map { height: 640px; border-radius: 6px; background: var(--surface); }
  .leaflet-container { font: inherit; background: var(--surface); }
  #map .leaflet-tile-pane { filter: var(--tiles); }
  #tracks { position: absolute; left: 0; top: 0; pointer-events: none; z-index: 450; }
  .leaflet-control-attribution { font-size: 11px; }
  .tip {
    position: absolute; pointer-events: none; opacity: 0; transition: opacity .1s;
    background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
    padding: 8px 10px; font-size: 12.5px; box-shadow: 0 4px 14px rgba(0,0,0,.14);
    max-width: 280px; z-index: 900; color: var(--primary);
  }
  .tip b { font-size: 13px; }
  .tip .row { color: var(--secondary); }
  .tip .tag { color: var(--muted); }
  .basemap-note { color: var(--muted); font-size: 12.5px; margin: 8px 0 0; }
  .legend { display: flex; flex-wrap: wrap; gap: 6px 16px; margin: 12px 0 0; }
  .legend button {
    display: flex; align-items: center; gap: 7px; border: 1px solid transparent;
    background: none; padding: 3px 7px; color: var(--secondary);
  }
  .legend button[aria-pressed="false"] { opacity: 0.38; }
  .legend button:hover { border-color: var(--axis); }
  .swatch { width: 22px; height: 4px; border-radius: 2px; }
  .linesample { width: 26px; height: 0; border-top: 3px solid var(--secondary); }
  .linesample.dashed { border-top-style: dashed; }
  .focus {
    display: flex; align-items: center; gap: 12px; margin: 0 0 12px; padding: 7px 10px;
    border: 1px solid var(--accent); border-radius: 8px; font-size: 13px;
  }
  .focus[hidden] { display: none; }
  table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }
  th, td { text-align: left; padding: 5px 8px; border-bottom: 1px solid var(--grid); }
  th { color: var(--secondary); font-weight: 600; }
  td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
  details { margin-top: 18px; }
  summary { cursor: pointer; color: var(--secondary); }
  .note { color: var(--muted); font-size: 12.5px; margin-top: 12px; }
  .scroll { overflow-x: auto; }
</style>
</head>
<body>
<div class="wrap">
  <h1>Tornado hazards, 2010–2025</h1>
  <p class="sub">Every tornado in the dataset, one line each. <b>Solid</b>: a track
  surveyed and drawn in NOAA's Damage Assessment Toolkit (DAT). <b>Dashed</b>: a
  tornado in SPC's record that DAT has no survey for, drawn as SPC's straight
  start–end line, or as a hollow dot where SPC records no end.
  <span id="ramp-note"></span></p>

  <div class="card">
    <div class="controls">
      <span class="seg" role="group" aria-label="Step">
        <button id="step-month" aria-pressed="true">by month</button>
        <button id="step-day" aria-pressed="false">by day</button>
      </span>
      <label>Show <select id="mode"></select></label>
      <label>Jump to <input type="date" id="jump"></label>
      <label>Speed
        <select id="speed">
          <option value="420">slow</option>
          <option value="200" selected>normal</option>
          <option value="80">fast</option>
        </select>
      </label>
      <button class="play" id="play">▶ Play</button>
    </div>
    <div class="controls">
      <label>Official text <select id="textFilter"></select></label>
      <label><input type="checkbox" id="basemap" checked> OpenStreetMap basemap</label>
      <span class="count" id="count"></span>
    </div>
    <div class="focus" id="focus" hidden>
      <span id="focus-text"></span>
      <button id="focus-clear">× back to the time view</button>
    </div>

    <div class="slider-row">
      <span class="when" id="label"></span>
      <input type="range" id="slider" min="0" value="0" step="1" aria-label="time step">
    </div>

    <div class="map-holder">
      <div id="map"></div>
      <canvas id="tracks"></canvas>
      <div class="tip" id="tip"></div>
    </div>
    <p class="basemap-note" id="basemap-note" hidden></p>

    <div class="legend" id="legend"></div>
    <div class="legend" id="sources"></div>
    <p class="note">Web Mercator, as the basemap tiles require; it enlarges northern
    areas, so compare densities on the equal-area maps of the analysis report. Scroll
    or pinch to zoom, drag to pan; surveyed damage footprints appear from street
    scale. Hover a hazard for details; <b>click it to show its whole episode</b>
    (Esc to return). ← → step through time. Click a rating or a source to show or
    hide it. Deaths and injuries are each hazard's own record: DAT's for a DAT
    hazard, SPC's for an SPC hazard. Basemap © OpenStreetMap contributors.</p>
  </div>

  <details open>
    <summary>Deadliest and strongest hazards currently shown</summary>
    <div class="scroll"><table id="table"></table></div>
  </details>
</div>

<script>__LEAFLET_JS__</script>
<script id="payload" type="application/json">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById('payload').textContent);
const $ = id => document.getElementById(id);
const canvas = $('tracks'), ctx = canvas.getContext('2d');
const slider = $('slider'), label = $('label'), countEl = $('count'), tip = $('tip');
const modeSel = $('mode'), speedSel = $('speed'), playBtn = $('play'), jump = $('jump');
const legendEl = $('legend'), sourcesEl = $('sources'), tableEl = $('table');
const textSel = $('textFilter'), focusEl = $('focus'), focusText = $('focus-text');

// Official text kinds, in the order of each track's counts (t.tx).
const TX_SHORT = ['PNS', 'narrative', 'DAT comment', 'survey LSR', 'real-time LSR'];
const SOURCE_NAMES = ['DAT survey (drawn track)', 'SPC record (straight line or dot)'];
const TEXT_FILTERS = [['all', 'all hazards'], ['oracle', 'with any oracle text'],
  ...DATA.textKinds.map((k, i) => ['k' + i, 'with a ' + k]), ['none', 'with no official text']];
const WINDOWS = {
  month: [['this', 'this month'], ['span', 'this year so far'], ['all', 'everything so far']],
  day: [['this', 'this day'], ['span', 'this month so far'], ['all', 'everything so far']],
};
const WEEKDAY = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const Z0 = DATA.z0;                 // track coordinates are world pixels at this zoom
const POLYGON_ZOOM = 11;            // damage footprints from here on: a few pixels across

if (DATA.hasTexts) {
  for (const [value, text] of TEXT_FILTERS) textSel.add(new Option(text, value));
} else {
  textSel.add(new Option('not available: run stages 20 and 24', 'all'));
  textSel.disabled = true;
}
jump.min = DATA.days[0];
jump.max = DATA.days.at(-1);

const hidden = new Set(), hiddenSources = new Set();
let step = 'month';
let focus = null;                   // index of the episode shown whole, or null
let visible = [];

const isDark = () => {
  const stamped = document.documentElement.dataset.theme;
  if (stamped) return stamped === 'dark';
  return window.matchMedia('(prefers-color-scheme: dark)').matches;
};
const ramp = () => (isDark() ? DATA.rampDark : DATA.rampLight);
const ink = k => getComputedStyle(document.documentElement).getPropertyValue(k).trim();

// ── map ──
// No zoom animation: the canvas is redrawn on every move, and a CSS-animated tile
// zoom underneath it would let tracks and streets drift apart for a moment.
const map = L.map('map', {zoomAnimation: false, zoomSnap: 0.25, wheelPxPerZoomLevel: 90,
                          minZoom: 3, maxZoom: 17, worldCopyJump: false});
map.attributionControl.setPrefix('<a href="https://leafletjs.com">Leaflet</a>');
const CONUS = L.latLngBounds([24, -125], [50, -66]);
map.fitBounds(CONUS);
const tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
});
let tileLoads = 0, tileErrors = 0;
tiles.on('tileload', () => { tileLoads++; $('basemap-note').hidden = true; });
tiles.on('tileerror', () => {
  tileErrors++;
  if (!tileLoads) {
    const note = $('basemap-note');
    note.textContent = 'The basemap tiles did not load: offline, or the page was opened '
      + 'from disk. Serve it with "python -m http.server 8791 --directory outputs" and '
      + 'open http://localhost:8791/hazard_map.html; meanwhile state outlines are drawn.';
    note.hidden = false;
    draw();
  }
});
const basemapOn = () => $('basemap').checked && map.hasLayer(tiles) && tileLoads > 0;
if ($('basemap').checked) tiles.addTo(map);
$('basemap').onchange = e => {
  e.target.checked ? tiles.addTo(map) : map.removeLayer(tiles);
  draw();
};

function sizeCanvas() {
  const size = map.getSize(), dpr = window.devicePixelRatio || 1;
  canvas.width = Math.round(size.x * dpr);
  canvas.height = Math.round(size.y * dpr);
  canvas.style.width = size.x + 'px';
  canvas.style.height = size.y + 'px';
}

/** World pixels at Z0 per screen pixel, and the view's top-left in world pixels. */
function viewTransform() {
  const s = Math.pow(2, map.getZoom() - Z0);
  const origin = map.getPixelBounds().min;           // world pixels at the current zoom
  return {s, ox: origin.x / s, oy: origin.y / s};
}
const intersects = (box, rect) =>
  box[0] <= rect[2] && box[2] >= rect[0] && box[1] <= rect[3] && box[3] >= rect[1];

// ── time ──
const monthOfDay = d => (+d.slice(0, 4) - +DATA.months[0].slice(0, 4)) * 12 + +d.slice(5, 7) - 1;
function setStep(next, keepPosition = true) {
  const cur = +slider.value;
  let pos = 0;
  if (keepPosition && next !== step) {
    if (next === 'day') {             // first day with tornadoes in this month, or later
      const m = DATA.months[cur];
      pos = Math.max(0, DATA.days.findIndex(d => d.slice(0, 7) >= m));
    } else {
      pos = monthOfDay(DATA.days[cur]);
    }
  } else {
    pos = cur;
  }
  step = next;
  $('step-month').setAttribute('aria-pressed', String(step === 'month'));
  $('step-day').setAttribute('aria-pressed', String(step === 'day'));
  const keep = modeSel.selectedIndex >= 0 ? modeSel.selectedIndex : 0;
  modeSel.innerHTML = '';
  for (const [value, text] of WINDOWS[step]) modeSel.add(new Option(text, value));
  modeSel.selectedIndex = keep;
  slider.max = (step === 'month' ? DATA.months.length : DATA.days.length) - 1;
  slider.value = Math.min(pos, +slider.max);
  focus = null;
  focusEl.hidden = true;
  draw();
}
$('step-month').onclick = () => setStep('month');
$('step-day').onclick = () => setStep('day');

jump.onchange = () => {
  const v = jump.value;
  if (!v) return;
  if (step === 'day') {
    let i = DATA.days.findIndex(d => d >= v);
    slider.value = i < 0 ? DATA.days.length - 1 : i;
  } else {
    slider.value = Math.max(0, Math.min(monthOfDay(v), DATA.months.length - 1));
  }
  focus = null;
  focusEl.hidden = true;
  draw();
};

function textOk(t) {
  const f = textSel.value;
  if (f === 'all') return true;
  if (f === 'none') return t.tx.every(c => c === 0);
  if (f === 'oracle') return t.tx[0] + t.tx[1] + t.tx[2] > 0;
  return t.tx[+f.slice(1)] > 0;
}

function selectedTracks() {
  const i = +slider.value, mode = modeSel.value;
  return DATA.tracks.filter(t => {
    if (hidden.has(t.e) || hiddenSources.has(t.src) || !textOk(t)) return false;
    if (focus !== null) return t.ep === focus;
    if (step === 'month') {
      if (mode === 'this') return t.m === i;
      if (mode === 'span') return Math.floor(t.m / 12) === Math.floor(i / 12) && t.m <= i;
      return t.m <= i;
    }
    if (t.di < 0) return false;
    if (mode === 'this') return t.di === i;
    if (mode === 'span') return t.d.slice(0, 7) === DATA.days[i].slice(0, 7) && t.di <= i;
    return t.di <= i;
  });
}

function timeLabel() {
  if (focus !== null) return 'one episode';
  const i = +slider.value;
  if (step === 'month') return DATA.months[i];
  const d = DATA.days[i];
  return WEEKDAY[new Date(d + 'T12:00:00Z').getUTCDay()] + ' ' + d;
}

// ── drawing ──
function draw() {
  const colours = ramp();
  const dpr = window.devicePixelRatio || 1;
  const {s, ox, oy} = viewTransform();
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  // Everything below is drawn in world pixels at Z0; one transform maps them to the
  // screen, and widths are divided by the scale so lines keep their screen width.
  ctx.setTransform(s * dpr, 0, 0, s * dpr, -ox * s * dpr, -oy * s * dpr);
  const px = 1 / s;
  const size = map.getSize();
  const rect = [ox, oy, ox + size.x * px, oy + size.y * px];

  // Without the basemap, state outlines give the reader a frame.
  if (!basemapOn()) {
    ctx.strokeStyle = ink('--axis');
    ctx.lineWidth = px;
    ctx.beginPath();
    for (const ring of DATA.outlines) {
      ctx.moveTo(ring[0], ring[1]);
      for (let i = 2; i < ring.length; i += 2) ctx.lineTo(ring[i], ring[i + 1]);
    }
    ctx.stroke();
  }

  visible = selectedTracks();
  const onScreen = visible.filter(t => intersects(t.b, rect));
  const showPolygons = map.getZoom() >= POLYGON_ZOOM;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  // Weakest first, so the strongest tracks are never hidden underneath.
  DATA.efClasses.forEach((ef, ci) => {
    const group = onScreen.filter(t => t.e === ef);
    if (!group.length) return;
    const width = (ef === 'EF4+' ? 2.6 : ef === 'EF3' ? 2.2 : 2)
      * (showPolygons ? 0.55 : 1) * px;
    ctx.strokeStyle = colours[ci];
    ctx.fillStyle = colours[ci];
    if (showPolygons) {
      ctx.beginPath();
      for (const t of group) {
        for (const ring of t.q) {
          if (ring.length < 6) continue;
          ctx.moveTo(ring[0], ring[1]);
          for (let i = 2; i < ring.length; i += 2) ctx.lineTo(ring[i], ring[i + 1]);
          ctx.closePath();
        }
      }
      ctx.globalAlpha = 0.3;
      ctx.fill();
      ctx.globalAlpha = 0.8;
      ctx.lineWidth = px;
      ctx.stroke();
      ctx.globalAlpha = 1;
    }
    // Source is carried by the line style, so colour stays the rating: DAT's
    // surveyed tracks solid, SPC's straight lines dashed.
    for (const src of [0, 1]) {
      const part = group.filter(t => t.src === src);
      if (!part.length) continue;
      ctx.lineWidth = width;
      ctx.setLineDash(src === 1 ? [4 * px, 3 * px] : []);
      ctx.beginPath();
      const dots = [];
      for (const t of part) {
        for (const p of t.p) {
          if (p.length === 2) { dots.push(p); continue; }
          ctx.moveTo(p[0], p[1]);
          for (let i = 2; i < p.length; i += 2) ctx.lineTo(p[i], p[i + 1]);
        }
      }
      ctx.stroke();
      ctx.setLineDash([]);
      // Tracks too short for a line, and SPC points, become dots sized like the
      // stroke: filled for DAT, a ring for SPC.
      if (dots.length) {
        const r = src === 1 ? width : width / 2;
        ctx.beginPath();
        for (const p of dots) {
          ctx.moveTo(p[0] + r, p[1]);
          ctx.arc(p[0], p[1], r, 0, Math.PI * 2);
        }
        if (src === 0) ctx.fill();
        else { ctx.lineWidth = width * 0.6; ctx.stroke(); }
      }
    }
  });

  const spcShown = visible.filter(t => t.src === 1).length;
  countEl.textContent = visible.length.toLocaleString() + ' hazards shown ('
    + (visible.length - spcShown).toLocaleString() + ' DAT, ' + spcShown.toLocaleString()
    + ' SPC)';
  label.textContent = timeLabel();
  renderTable();
}

// ── table, text, episodes ──
function textSummary(t) {
  if (!DATA.hasTexts) return 'n/a';
  const parts = t.tx.map((c, i) => c === 0 ? null
    : (c > 1 ? c + ' ' + TX_SHORT[i] + 's' : TX_SHORT[i])).filter(Boolean);
  return parts.length ? parts.join(' · ') : 'none';
}

function renderTable() {
  const rank = {'EF4+': 5, EF3: 4, EF2: 3, EF1: 2, EF0: 1, unrated: 0};
  const rows = visible.slice()
    .sort((a, b) => (b.f - a.f) || (rank[b.e] - rank[a.e]) || ((b.l || 0) - (a.l || 0)))
    .slice(0, 12);
  const head = '<thead><tr><th>date</th><th>rating</th><th>source</th><th>near</th>'
    + '<th class="num">length&nbsp;(mi)</th><th class="num">deaths</th>'
    + '<th class="num">injuries</th><th>official text</th><th>WFO</th></tr></thead>';
  const body = rows.map(t => `<tr><td>${t.d}</td><td>${DATA.efLabels[t.e]}</td>`
    + `<td>${t.src ? 'SPC' : 'DAT'}</td>`
    + `<td>${t.n ? t.n + (t.s ? ', ' + t.s : '') : '—'}</td>`
    + `<td class="num">${t.l ?? '—'}</td><td class="num">${t.f || ''}</td>`
    + `<td class="num">${t.i || ''}</td><td>${textSummary(t)}</td>`
    + `<td>${t.w || '—'}</td></tr>`).join('');
  tableEl.innerHTML = head + '<tbody>' + (body ||
    '<tr><td colspan="9">no hazards in this selection</td></tr>') + '</tbody>';
}

function episodeLine(t) {
  if (t.ep < 0) return 'in no episode (no SPC track)';
  const [uid, size] = DATA.episodes[t.ep];
  return `episode ${uid.slice(-6)} · ${size} hazard${size === 1 ? '' : 's'}`;
}

/** Show one episode whole, whatever the time step, and zoom to it. */
function focusEpisode(index) {
  focus = index;
  if (timer) stop();
  const members = DATA.tracks.filter(t => t.ep === index);
  const box = members.reduce((b, t) => [Math.min(b[0], t.b[0]), Math.min(b[1], t.b[1]),
    Math.max(b[2], t.b[2]), Math.max(b[3], t.b[3])], [Infinity, Infinity, -Infinity, -Infinity]);
  map.fitBounds(L.latLngBounds(map.unproject([box[0], box[3]], Z0),
                               map.unproject([box[2], box[1]], Z0)),
                {padding: [40, 40], maxZoom: 12});
  const [uid, size] = DATA.episodes[index];
  const days = [...new Set(members.map(t => t.d))].sort();
  focusText.innerHTML = `<b>Episode ${uid.slice(-6)}</b> · ${size} hazard`
    + `${size === 1 ? '' : 's'} · ${days[0]}${days.length > 1 ? ' to ' + days.at(-1) : ''}`
    + ` · <code title="${uid}">${uid}</code>`;
  focusEl.hidden = false;
  draw();
}
function clearFocus() {
  if (focus === null) return;
  focus = null;
  focusEl.hidden = true;
  draw();
}
$('focus-clear').onclick = clearFocus;

// ── hover and click: nearest hazard within ~12 screen pixels ──
function nearest(containerPoint) {
  const {s, ox, oy} = viewTransform();
  const wx = ox + containerPoint.x / s, wy = oy + containerPoint.y / s;
  const tolerance = 12 / s;
  let best = null, bestDist = tolerance * tolerance;
  const box = [wx - tolerance, wy - tolerance, wx + tolerance, wy + tolerance];
  for (const t of visible) {
    if (!intersects(t.b, box)) continue;
    for (const p of t.p) {
      for (let i = 0; i < p.length; i += 2) {
        const dx = p[i] - wx, dy = p[i + 1] - wy;
        const d = dx * dx + dy * dy;
        if (d < bestDist) { bestDist = d; best = t; }
      }
    }
  }
  return best;
}

map.on('mousemove', e => {
  const hit = nearest(e.containerPoint);
  map.getContainer().style.cursor = hit ? 'pointer' : '';
  if (!hit) { tip.style.opacity = 0; return; }
  tip.innerHTML = `<b>${DATA.efLabels[hit.e]}</b> · ${hit.d}`
    + `<div class="row">${hit.src ? 'SPC record: straight start–end line, no DAT survey'
        : 'DAT survey: ' + (hit.g ? 'track and damage polygon' : 'track line')}</div>`
    + (hit.n ? `<div class="row">near ${hit.n}${hit.s ? ', ' + hit.s : ''}</div>` : '')
    + `<div class="row">${hit.l != null ? hit.l + ' mi' : 'length unrecorded'}`
    + `${hit.w ? ' · office ' + hit.w : ''}</div>`
    + (hit.f || hit.i ? `<div class="row">${hit.f} killed · ${hit.i} injured `
        + `<span class="tag">(${hit.src ? 'SPC' : 'DAT'} record)</span></div>` : '')
    + `<div class="row">${episodeLine(hit)}</div>`
    + `<div class="row">texts: ${textSummary(hit)}`
    + (hit.ac != null ? ` <span class="tag">· oracle texts in ${hit.ac} account`
        + `${hit.ac === 1 ? '' : 's'}</span>` : '') + '</div>'
    + (hit.ep >= 0 && focus === null ? '<div class="row tag">click: show the episode</div>' : '');
  tip.style.opacity = 1;
  const holder = canvas.parentElement.getBoundingClientRect();
  let left = e.containerPoint.x + 14;
  if (left + tip.offsetWidth > holder.width) left = e.containerPoint.x - tip.offsetWidth - 14;
  tip.style.left = left + 'px';
  tip.style.top = (e.containerPoint.y + 14) + 'px';
});
map.on('mouseout', () => { tip.style.opacity = 0; });
map.on('click', e => {
  const hit = nearest(e.containerPoint);
  if (hit && hit.ep >= 0 && hit.ep !== focus) focusEpisode(hit.ep);
});
map.on('move zoom', draw);
map.on('resize', () => { sizeCanvas(); draw(); });

// ── legends double as filters ──
// The two ramps run in opposite directions (the dark-mode steps are chosen for the
// dark surface), so the caption follows the active theme.
function updateRampNote() {
  $('ramp-note').textContent = isDark()
    ? 'Brighter lines are stronger tornadoes.' : 'Darker lines are stronger tornadoes.';
}
function buildLegend() {
  const colours = ramp();
  legendEl.innerHTML = '';
  DATA.efClasses.forEach((ef, i) => {
    const button = document.createElement('button');
    button.setAttribute('aria-pressed', hidden.has(ef) ? 'false' : 'true');
    button.innerHTML = `<span class="swatch" style="background:${colours[i]}"></span>`
      + `<span>${DATA.efLabels[ef]}</span>`;
    button.onclick = () => {
      hidden.has(ef) ? hidden.delete(ef) : hidden.add(ef);
      button.setAttribute('aria-pressed', hidden.has(ef) ? 'false' : 'true');
      draw();
    };
    legendEl.appendChild(button);
  });
  sourcesEl.innerHTML = '';
  SOURCE_NAMES.forEach((name, src) => {
    const button = document.createElement('button');
    button.setAttribute('aria-pressed', hiddenSources.has(src) ? 'false' : 'true');
    button.innerHTML = `<span class="linesample${src ? ' dashed' : ''}"></span><span>${name}</span>`;
    button.onclick = () => {
      hiddenSources.has(src) ? hiddenSources.delete(src) : hiddenSources.add(src);
      button.setAttribute('aria-pressed', hiddenSources.has(src) ? 'false' : 'true');
      draw();
    };
    sourcesEl.appendChild(button);
  });
}

// ── playback and keys ──
let timer = null;
function stop() { clearInterval(timer); timer = null; playBtn.textContent = '▶ Play'; }
playBtn.onclick = () => {
  if (timer) return stop();
  clearFocus();
  playBtn.textContent = '❚❚ Pause';
  timer = setInterval(() => {
    const next = (+slider.value + 1) % (+slider.max + 1);
    slider.value = next;
    draw();
    if (next === +slider.max) stop();
  }, +speedSel.value);
};
speedSel.onchange = () => { if (timer) { stop(); playBtn.click(); } };
slider.oninput = () => { focus = null; focusEl.hidden = true; draw(); };
modeSel.onchange = draw;
textSel.onchange = draw;
window.addEventListener('keydown', e => {
  if (['INPUT', 'SELECT', 'TEXTAREA'].includes(e.target.tagName) && e.target !== slider) return;
  if (e.key === 'Escape') clearFocus();
  else if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
    if (e.target === slider) return;          // the slider moves itself
    slider.value = Math.max(0, Math.min(+slider.max, +slider.value + (e.key === 'ArrowRight' ? 1 : -1)));
    slider.oninput();
  }
});

function themeChanged() { updateRampNote(); buildLegend(); draw(); }
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', themeChanged);
// A viewer's explicit theme choice is stamped on <html>, and must win over the OS
// setting in both directions.
new MutationObserver(themeChanged).observe(document.documentElement,
  { attributes: true, attributeFilter: ['data-theme'] });

sizeCanvas();
updateRampNote();
buildLegend();
setStep('month', false);
slider.value = slider.max;          // open on the latest month
draw();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()

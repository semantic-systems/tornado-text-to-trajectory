"""Stage 19 — build a self-contained interactive map of every hazard.

Writes `outputs/hazard_map.html`: one file, no network at view time, no build
step. Tracks are pre-projected to CONUS Albers and simplified in Python, so the
page ships integer pixel coordinates and the browser only has to draw them —
which is what keeps ~10,000 tracks interactive on a canvas.

Controls: a month slider with play/pause, a rating filter, a window mode
(one month / whole year / everything up to now), hover details, and a table of
the strongest tracks currently shown.

    python scripts/19_event_map.py
    python scripts/19_event_map.py --width 1180 --simplify-m 1500
"""

from __future__ import annotations

import argparse
import json

import _bootstrap  # noqa: F401

import pandas as pd
from shapely.geometry import LineString, MultiLineString

from tornado_dataset import config, viz
from tornado_dataset.dat.geometry import to_equal_area, to_shapely
from tornado_dataset.geo import pixels
from tornado_dataset.geo.gazetteer import state_outlines

# Projection and pixel transform live in the package so the national map and the
# viewer's per-event thumbnails cannot drift apart.
BOUNDS = pixels.CONUS_BOUNDS
PRECISION = pixels.PRECISION


def make_projector(width: int, height: int):
    """Albers metres -> integer sub-pixel world units (see geo/pixels.py)."""
    return pixels.make_projector(width, height, BOUNDS, PRECISION)


ring_to_world = pixels.ring_to_world
bounds_of = pixels.bounds_of


def main() -> None:
    default_tag = f"{config.WINDOW_START.isoformat()}_{config.WINDOW_END.isoformat()}"
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", default=default_tag)
    parser.add_argument("--width", type=int, default=1120)
    parser.add_argument("--height", type=int, default=680)
    # Tracks are short — the median is 1.3 miles — so the tolerance has to stay
    # well under that or half the dataset simplifies away to a single point. It
    # also sets how far the reader can usefully zoom: 60 m is roughly one screen
    # pixel at 70x, past which the geometry, not the screen, is the limit.
    parser.add_argument("--simplify-m", type=float, default=60.0,
                        help="track simplification tolerance in metres")
    args = parser.parse_args()

    import pyproj
    project = pyproj.Transformer.from_crs(config.CRS_WGS84, config.CRS_EQUAL_AREA,
                                          always_xy=True).transform
    to_world = make_projector(args.width, args.height)

    hazards = pd.read_csv(config.PROCESSED_DIR / f"hazards_{args.tag}.csv")
    geography = pd.read_csv(config.PROCESSED_DIR / f"hazard_geography_{args.tag}.csv")
    features = json.loads(
        (config.PROCESSED_DIR / f"hazards_{args.tag}.geojson").read_text())["features"]

    place = geography.set_index("hazard_uid")[["nearest_place", "counties", "states"]]
    attributes = hazards.set_index("hazard_uid")

    # ── basemap ──
    outlines = []
    for feature in state_outlines(2025, simplify_deg=0.02)["features"]:
        geometry = feature["geometry"]
        rings = (geometry["coordinates"] if geometry["type"] == "Polygon"
                 else [ring for polygon in geometry["coordinates"] for ring in polygon])
        for ring in rings:
            flat = ring_to_world(ring, to_world, project)
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
        lines = [p for p in parts if isinstance(p, (LineString, MultiLineString))]
        polygons = [p for p in parts if p.geom_type in ("Polygon", "MultiPolygon")]
        tolerance = args.simplify_m / 111_000

        def flatten(geometries) -> list[list[int]]:
            out = []
            for part in geometries:
                simplified = part.simplify(tolerance, preserve_topology=False)
                segments = (list(simplified.geoms)
                            if simplified.geom_type.startswith("Multi") else [simplified])
                for segment in segments:
                    if segment.is_empty:
                        continue
                    coords = (list(segment.exterior.coords)
                              if segment.geom_type == "Polygon" else list(segment.coords))
                    flat = ring_to_world(coords, to_world, project)
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
        tracks.append({
            "m": (int(day[:4]) - config.WINDOW_START.year) * 12 + int(day[5:7]) - 1,
            "d": day,
            "e": viz.ef_class(row.efscale),
            "p": drawn,
            "q": rings,
            "b": bounds_of(drawn + rings),
            "l": None if pd.isna(length) else round(float(length), 1),
            "f": int(row.fatalities) if pd.notna(row.fatalities) else 0,
            "i": int(row.injuries) if pd.notna(row.injuries) else 0,
            "w": row.wfo if pd.notna(row.wfo) else "",
            "n": (info.nearest_place if info is not None and pd.notna(info.nearest_place)
                  else ""),
            "s": (info.states if info is not None and pd.notna(info.states) else ""),
            "o": bool(row.has_oracle_text),
            "g": bool(row.has_polygon),
        })

    months = [f"{config.WINDOW_START.year + i // 12}-{i % 12 + 1:02d}"
              for i in range((config.WINDOW_END.year - config.WINDOW_START.year + 1) * 12)]
    payload = {
        "width": args.width, "height": args.height, "precision": PRECISION,
        "outlines": outlines, "tracks": tracks, "months": months,
        "efClasses": viz.EF_CLASSES + [viz.UNRATED],
        "efLabels": {**viz.EF_CLASS_LABELS, viz.UNRATED: "unrated"},
        "rampLight": viz.EF_RAMP_LIGHT + [viz.LIGHT["unrated"]],
        "rampDark": viz.EF_RAMP_DARK + [viz.DARK["unrated"]],
    }

    html = HTML_TEMPLATE.replace("__DATA__", json.dumps(payload, separators=(",", ":")))
    out_path = config.OUTPUT_DIR / "hazard_map.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    size_mb = out_path.stat().st_size / 1e6
    print(f"{len(tracks):,} tracks drawn ({skipped} without usable geometry), "
          f"{len(outlines)} basemap rings")
    print(f"wrote {out_path} ({size_mb:.1f} MB, self-contained)")


HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Surveyed tornado tracks, 2010-2025</title>
<style>
  :root {
    color-scheme: light dark;
    --surface: #fcfcfb; --plane: #f9f9f7; --primary: #0b0b0b; --secondary: #52514e;
    --muted: #898781; --grid: #e1e0d9; --axis: #c3c2b7; --accent: #2a78d6;
    --border: rgba(11,11,11,0.10);
  }
  @media (prefers-color-scheme: dark) {
    :root:where(:not([data-theme="light"])) {
      --surface: #1a1a19; --plane: #0d0d0d; --primary: #ffffff; --secondary: #c3c2b7;
      --muted: #898781; --grid: #2c2c2a; --axis: #383835; --accent: #3987e5;
      --border: rgba(255,255,255,0.10);
    }
  }
  :root[data-theme="dark"] {
    --surface: #1a1a19; --plane: #0d0d0d; --primary: #ffffff; --secondary: #c3c2b7;
    --muted: #898781; --grid: #2c2c2a; --axis: #383835; --accent: #3987e5;
    --border: rgba(255,255,255,0.10);
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--plane); color: var(--primary);
    font: 14px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif;
  }
  .wrap { max-width: 1180px; margin: 0 auto; padding: 24px 16px 48px; }
  h1 { font-size: 20px; margin: 0 0 4px; }
  .sub { color: var(--secondary); margin: 0 0 20px; max-width: 70ch; }
  .card {
    background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
    padding: 16px;
  }
  .controls {
    display: flex; flex-wrap: wrap; gap: 12px 18px; align-items: center;
    margin-bottom: 14px;
  }
  .controls label { color: var(--secondary); font-size: 13px; }
  select, button {
    font: inherit; font-size: 13px; color: var(--primary); background: var(--surface);
    border: 1px solid var(--axis); border-radius: 6px; padding: 5px 9px; cursor: pointer;
  }
  button.play { min-width: 78px; font-weight: 600; }
  .slider-row { display: flex; align-items: center; gap: 12px; margin: 6px 0 14px; }
  input[type=range] { flex: 1; accent-color: var(--accent); }
  .month {
    font-variant-numeric: tabular-nums; font-weight: 600; min-width: 8ch;
  }
  .count { color: var(--secondary); font-variant-numeric: tabular-nums; }
  .canvas-holder { position: relative; }
  canvas {
    width: 100%; height: auto; display: block; border-radius: 6px;
    cursor: grab; touch-action: none;
  }
  canvas.dragging { cursor: grabbing; }
  .zoom-controls {
    position: absolute; top: 10px; right: 10px; display: flex; flex-direction: column;
    gap: 4px; z-index: 4;
  }
  .zoom-controls button {
    width: 30px; height: 28px; padding: 0; font-size: 15px; line-height: 1;
    background: var(--surface); opacity: 0.94;
  }
  .zoom-controls button.reset { font-size: 11px; }
  .zoom-level {
    position: absolute; bottom: 10px; right: 12px; font-size: 11.5px;
    color: var(--muted); font-variant-numeric: tabular-nums; z-index: 4;
  }
  .legend { display: flex; flex-wrap: wrap; gap: 6px 16px; margin: 14px 0 0; }
  .legend button {
    display: flex; align-items: center; gap: 7px; border: 1px solid transparent;
    background: none; padding: 3px 7px; color: var(--secondary);
  }
  .legend button[aria-pressed="false"] { opacity: 0.38; }
  .legend button:hover { border-color: var(--axis); }
  .swatch { width: 22px; height: 4px; border-radius: 2px; }
  .tip {
    position: absolute; pointer-events: none; opacity: 0; transition: opacity .1s;
    background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
    padding: 8px 10px; font-size: 12.5px; box-shadow: 0 4px 14px rgba(0,0,0,.14);
    max-width: 260px; z-index: 5;
  }
  .tip b { font-size: 13px; }
  .tip .row { color: var(--secondary); }
  table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }
  th, td { text-align: left; padding: 5px 8px; border-bottom: 1px solid var(--grid); }
  th { color: var(--secondary); font-weight: 600; }
  td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
  details { margin-top: 18px; }
  summary { cursor: pointer; color: var(--secondary); }
  .note { color: var(--muted); font-size: 12.5px; margin-top: 14px; }
  .scroll { overflow-x: auto; }
</style>
</head>
<body>
<div class="wrap">
  <h1>Surveyed tornado tracks, 2010–2025</h1>
  <p class="sub">Every damage track NOAA's Damage Assessment Toolkit holds for the
  period, assembled into one record per tornado. <span id="ramp-note"></span>
  These are tracks that were <em>surveyed and drawn</em> — not every tornado that
  occurred.</p>

  <div class="card">
    <div class="controls">
      <label>Window
        <select id="mode">
          <option value="month">this month</option>
          <option value="year">this year</option>
          <option value="all">everything up to here</option>
        </select>
      </label>
      <label>Speed
        <select id="speed">
          <option value="420">slow</option>
          <option value="200" selected>normal</option>
          <option value="80">fast</option>
        </select>
      </label>
      <button class="play" id="play">▶ Play</button>
      <span class="count" id="count"></span>
    </div>

    <div class="slider-row">
      <span class="month" id="label"></span>
      <input type="range" id="slider" min="0" value="0" step="1" aria-label="month">
    </div>

    <div class="canvas-holder">
      <canvas id="map"></canvas>
      <div class="zoom-controls">
        <button id="zoom-in" title="Zoom in" aria-label="Zoom in">+</button>
        <button id="zoom-out" title="Zoom out" aria-label="Zoom out">−</button>
        <button id="zoom-reset" class="reset" title="Reset view" aria-label="Reset view">⤾</button>
      </div>
      <div class="zoom-level" id="zoom-level"></div>
      <div class="tip" id="tip"></div>
    </div>

    <div class="legend" id="legend"></div>
    <p class="note">Equal-area projection (EPSG:5070). Scroll or pinch to zoom,
    drag to pan, double-click to zoom in; surveyed damage footprints appear from
    20× for the tracks that have one. Hover a track for details; click a rating to
    show or hide it.</p>
  </div>

  <details open>
    <summary>Strongest tracks currently shown</summary>
    <div class="scroll"><table id="table"></table></div>
  </details>
</div>

<script id="payload" type="application/json">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById('payload').textContent);
const canvas = document.getElementById('map');
const ctx = canvas.getContext('2d');
const slider = document.getElementById('slider');
const label = document.getElementById('label');
const countEl = document.getElementById('count');
const tip = document.getElementById('tip');
const modeSel = document.getElementById('mode');
const speedSel = document.getElementById('speed');
const playBtn = document.getElementById('play');
const legendEl = document.getElementById('legend');
const tableEl = document.getElementById('table');

slider.max = DATA.months.length - 1;
slider.value = DATA.months.length - 1;

const isDark = () => {
  const stamped = document.documentElement.dataset.theme;
  if (stamped) return stamped === 'dark';
  return window.matchMedia('(prefers-color-scheme: dark)').matches;
};
const ramp = () => (isDark() ? DATA.rampDark : DATA.rampLight);
const ink = k => getComputedStyle(document.documentElement).getPropertyValue(k).trim();

const hidden = new Set();
let visible = [];

// World units are sub-pixels: PR world units make one base pixel at zoom 1, so
// the geometry keeps its detail when the reader zooms past 1:1.
const PR = DATA.precision;
const MIN_ZOOM = 1, MAX_ZOOM = 120;
// Damage polygons only carry meaning once they are more than a smudge. A typical
// footprint is a few hundred metres across and one base pixel is ~4.4 km, so
// below roughly 20x they would merely thicken the track line and hide it.
const POLYGON_ZOOM = 20;
const view = { k: 1, x: 0, y: 0 };     // scale and translation in base pixels

function setupCanvas() {
  const dpr = window.devicePixelRatio || 1;
  const cssWidth = canvas.parentElement.clientWidth;
  const scale = cssWidth / DATA.width;
  canvas.style.height = (DATA.height * scale) + 'px';
  canvas.width = Math.round(DATA.width * scale * dpr);
  canvas.height = Math.round(DATA.height * scale * dpr);
  return scale;
}
let cssScale = 1, devicePixels = 1;

/** Keep the view inside the map: never scroll the whole country off-screen. */
function clampView() {
  view.k = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, view.k));
  const overflowX = DATA.width * (view.k - 1);
  const overflowY = DATA.height * (view.k - 1);
  view.x = Math.min(0, Math.max(-overflowX, view.x));
  view.y = Math.min(0, Math.max(-overflowY, view.y));
}

/** Zoom by a factor, holding the given base-pixel point still under the cursor. */
function zoomAt(factor, px, py) {
  const before = view.k;
  view.k = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, view.k * factor));
  const applied = view.k / before;
  view.x = px - (px - view.x) * applied;
  view.y = py - (py - view.y) * applied;
  clampView();
  draw();
}

const screenToBase = event => {
  const rect = canvas.getBoundingClientRect();
  return [(event.clientX - rect.left) / cssScale, (event.clientY - rect.top) / cssScale];
};
/** Base pixels -> world units, i.e. undo the current pan/zoom. */
const baseToWorld = (px, py) => [((px - view.x) / view.k) * PR, ((py - view.y) / view.k) * PR];

/** Visible world rectangle, for culling tracks that cannot be on screen. */
function viewportWorld() {
  const [x0, y0] = baseToWorld(0, 0);
  const [x1, y1] = baseToWorld(DATA.width, DATA.height);
  return [x0, y0, x1, y1];
}
const intersects = (box, rect) =>
  box[0] <= rect[2] && box[2] >= rect[0] && box[1] <= rect[3] && box[3] >= rect[1];

function selectedTracks() {
  const m = +slider.value, mode = modeSel.value;
  const year = Math.floor(m / 12);
  return DATA.tracks.filter(t => {
    if (hidden.has(t.e)) return false;
    if (mode === 'month') return t.m === m;
    if (mode === 'year') return Math.floor(t.m / 12) === year && t.m <= m;
    return t.m <= m;
  });
}

function draw() {
  const colours = ramp();
  // One transform does device pixels, the CSS fit, the zoom, and the world->pixel
  // scale, so every path below is drawn in raw world units.
  const unit = (cssScale * devicePixels * view.k) / PR;
  ctx.setTransform(cssScale * devicePixels, 0, 0, cssScale * devicePixels, 0, 0);
  ctx.fillStyle = ink('--surface');
  ctx.fillRect(0, 0, DATA.width, DATA.height);
  ctx.setTransform(unit, 0, 0, unit,
                   view.x * cssScale * devicePixels, view.y * cssScale * devicePixels);

  // Stroke widths are divided by the zoom so a line stays the same thickness on
  // screen: scaling them would turn a 40x view into a few fat blobs.
  const px = PR / view.k;
  const rect = viewportWorld();

  // Basemap: hairline state outlines. Uses the axis shade rather than the
  // gridline shade — a grid can afford to be nearly invisible, but a reader has
  // to be able to tell which state a track is in.
  ctx.strokeStyle = ink('--axis');
  ctx.lineWidth = px;
  ctx.beginPath();
  for (const ring of DATA.outlines) {
    ctx.moveTo(ring[0], ring[1]);
    for (let i = 2; i < ring.length; i += 2) ctx.lineTo(ring[i], ring[i + 1]);
  }
  ctx.stroke();

  visible = selectedTracks();
  const onScreen = visible.filter(t => intersects(t.b, rect));
  // Draw weakest first so the strongest tracks are never hidden underneath.
  const order = DATA.efClasses;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  const showPolygons = view.k >= POLYGON_ZOOM;

  for (let ci = 0; ci < order.length; ci++) {
    const ef = order[ci];
    const group = onScreen.filter(t => t.e === ef);
    if (!group.length) continue;
    // Once footprints are on screen the centreline is thinned, so the polygon is
    // read rather than covered by the line that runs down its middle.
    const width = (ef === 'EF4+' ? 2.6 : ef === 'EF3' ? 2.2 : 2)
      * (showPolygons ? 0.55 : 1) * px;
    ctx.strokeStyle = colours[ci];
    ctx.fillStyle = colours[ci];

    // Damage polygons, once they are big enough to read: a translucent fill plus
    // a hairline edge, both in the track's own colour, so the surveyed footprint
    // reads as belonging to that track rather than as a separate object.
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

    ctx.lineWidth = width;
    ctx.beginPath();
    const dots = [];
    for (const t of group) {
      for (const p of t.p) {
        if (p.length === 2) { dots.push(p); continue; }   // sub-pixel track
        ctx.moveTo(p[0], p[1]);
        for (let i = 2; i < p.length; i += 2) ctx.lineTo(p[i], p[i + 1]);
      }
    }
    ctx.stroke();
    // Tracks too short to draw as a line become dots, sized like the stroke so
    // they carry the same visual weight as their rating.
    if (dots.length) {
      ctx.beginPath();
      for (const p of dots) {
        ctx.moveTo(p[0] + width / 2, p[1]);
        ctx.arc(p[0], p[1], width / 2, 0, Math.PI * 2);
      }
      ctx.fill();
    }
  }

  const deaths = visible.reduce((s, t) => s + t.f, 0);
  countEl.textContent = visible.length.toLocaleString() + ' tracks shown'
    + (deaths ? ' · ' + deaths.toLocaleString() + ' fatalities' : '');
  label.textContent = DATA.months[+slider.value];
  document.getElementById('zoom-level').textContent =
    view.k > 1.01 ? view.k.toFixed(view.k < 10 ? 1 : 0) + '× zoom' : '';
  renderTable();
}

function renderTable() {
  const rank = { 'EF4+': 5, EF3: 4, EF2: 3, EF1: 2, EF0: 1, unrated: 0 };
  const rows = visible.slice()
    .sort((a, b) => (b.f - a.f) || (rank[b.e] - rank[a.e]) || ((b.l || 0) - (a.l || 0)))
    .slice(0, 12);
  const head = '<thead><tr><th>date</th><th>rating</th><th>near</th>'
    + '<th class="num">length&nbsp;(mi)</th><th class="num">deaths</th>'
    + '<th class="num">injuries</th><th>WFO</th></tr></thead>';
  const body = rows.map(t => `<tr><td>${t.d}</td><td>${DATA.efLabels[t.e]}</td>`
    + `<td>${t.n ? t.n + (t.s ? ', ' + t.s : '') : '—'}</td>`
    + `<td class="num">${t.l ?? '—'}</td><td class="num">${t.f || ''}</td>`
    + `<td class="num">${t.i || ''}</td><td>${t.w || '—'}</td></tr>`).join('');
  tableEl.innerHTML = head + '<tbody>' + (body ||
    '<tr><td colspan="7">no tracks in this selection</td></tr>') + '</tbody>';
}

// ── hover: nearest track within a forgiving radius ──
// The tolerance is defined in screen pixels and converted to world units, so it
// stays a comfortable ~12px target at every zoom level rather than covering half
// a state when zoomed out or becoming unhittable when zoomed in.
function nearest(wx, wy) {
  const tolerance = 12 * PR / view.k;
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

canvas.addEventListener('mousemove', event => {
  if (drag) {                       // panning: move the view, no tooltip
    const [bx, by] = screenToBase(event);
    view.x = drag.viewX + (bx - drag.baseX);
    view.y = drag.viewY + (by - drag.baseY);
    clampView();
    tip.style.opacity = 0;
    draw();
    return;
  }
  const hit = nearest(...baseToWorld(...screenToBase(event)));
  if (!hit) { tip.style.opacity = 0; return; }
  tip.innerHTML = `<b>${DATA.efLabels[hit.e]}</b> · ${hit.d}`
    + (hit.n ? `<div class="row">near ${hit.n}${hit.s ? ', ' + hit.s : ''}</div>` : '')
    + `<div class="row">${hit.l != null ? hit.l + ' mi track' : 'length unrecorded'}`
    + `${hit.w ? ' · ' + hit.w : ''}</div>`
    + (hit.f || hit.i ? `<div class="row">${hit.f} killed · ${hit.i} injured</div>` : '')
    + `<div class="row">${hit.g ? 'damage polygon' : 'track line only'}`
    + `${hit.o ? ' · survey text' : ''}</div>`;
  tip.style.opacity = 1;
  const holder = canvas.parentElement.getBoundingClientRect();
  let left = event.clientX - holder.left + 14;
  if (left + tip.offsetWidth > holder.width) left = event.clientX - holder.left - tip.offsetWidth - 14;
  tip.style.left = left + 'px';
  tip.style.top = (event.clientY - holder.top + 14) + 'px';
});
canvas.addEventListener('mouseleave', () => { tip.style.opacity = 0; });

// ── zoom and pan ──
let drag = null;

canvas.addEventListener('wheel', event => {
  event.preventDefault();
  const [bx, by] = screenToBase(event);
  // Trackpads report small deltas and mice large ones; the exponent keeps both
  // feeling proportional instead of jumping.
  zoomAt(Math.pow(1.0016, -event.deltaY), bx, by);
}, { passive: false });

canvas.addEventListener('mousedown', event => {
  const [bx, by] = screenToBase(event);
  drag = { baseX: bx, baseY: by, viewX: view.x, viewY: view.y, moved: false };
  canvas.classList.add('dragging');
});
window.addEventListener('mouseup', () => { drag = null; canvas.classList.remove('dragging'); });
canvas.addEventListener('dblclick', event => {
  const [bx, by] = screenToBase(event);
  zoomAt(2, bx, by);
});

document.getElementById('zoom-in').onclick = () => zoomAt(1.6, DATA.width / 2, DATA.height / 2);
document.getElementById('zoom-out').onclick = () => zoomAt(1 / 1.6, DATA.width / 2, DATA.height / 2);
document.getElementById('zoom-reset').onclick = () => {
  view.k = 1; view.x = 0; view.y = 0; draw();
};

// Pinch-zoom on a trackpad or touchscreen.
const pointers = new Map();
let pinch = null;
canvas.addEventListener('pointerdown', event => {
  if (event.pointerType === 'touch') pointers.set(event.pointerId, event);
});
canvas.addEventListener('pointermove', event => {
  if (event.pointerType !== 'touch' || !pointers.has(event.pointerId)) return;
  pointers.set(event.pointerId, event);
  if (pointers.size !== 2) return;
  const [a, b] = [...pointers.values()];
  const distance = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
  const rect = canvas.getBoundingClientRect();
  const midX = ((a.clientX + b.clientX) / 2 - rect.left) / cssScale;
  const midY = ((a.clientY + b.clientY) / 2 - rect.top) / cssScale;
  if (pinch) zoomAt(distance / pinch, midX, midY);
  pinch = distance;
});
const endPointer = event => {
  pointers.delete(event.pointerId);
  if (pointers.size < 2) pinch = null;
};
canvas.addEventListener('pointerup', endPointer);
canvas.addEventListener('pointercancel', endPointer);

// The two ramps run in opposite directions — the dark-mode steps are chosen for
// the dark surface rather than being the light ramp flipped — so which end means
// "stronger" depends on the mode, and the caption has to follow it.
function updateRampNote() {
  document.getElementById('ramp-note').textContent = isDark()
    ? 'Brighter lines are stronger tornadoes.'
    : 'Darker lines are stronger tornadoes.';
}

// ── legend doubles as a rating filter ──
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
}

// ── playback ──
let timer = null;
function stop() { clearInterval(timer); timer = null; playBtn.textContent = '▶ Play'; }
playBtn.onclick = () => {
  if (timer) return stop();
  playBtn.textContent = '❚❚ Pause';
  timer = setInterval(() => {
    const next = (+slider.value + 1) % DATA.months.length;
    slider.value = next;
    draw();
    if (next === DATA.months.length - 1) stop();
  }, +speedSel.value);
};
speedSel.onchange = () => { if (timer) { stop(); playBtn.click(); } };
slider.oninput = draw;
modeSel.onchange = draw;

window.addEventListener('resize', () => { cssScale = setupCanvas(); draw(); });

function themeChanged() { updateRampNote(); buildLegend(); draw(); }
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', themeChanged);
// A viewer's explicit theme choice is stamped on <html>, and must win over the OS
// setting in both directions.
new MutationObserver(themeChanged).observe(document.documentElement,
  { attributes: true, attributeFilter: ['data-theme'] });

devicePixels = window.devicePixelRatio || 1;
cssScale = setupCanvas();
updateRampNote();
buildLegend();
draw();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()

"""Hand check of stage 12's merges: does a hazard built from several DAT lines
join tornadoes that should stay apart? (stage 17 ``merges``).

Stage 12 joins DAT lines by union-find (:func:`hazards.merge_lines`): a shared
polygon, the same ``event_id`` on the same date, or an endpoint within a few km on
the same convective day. Chains of such unions can join neighbouring tornadoes.
The candidates are the multi-line hazards that stage 14 links to two or more SPC
tracks: SPC sees more than one tornado there, either because the hazard joins
several (an over-merge) or because SPC records one tornado in pieces.

The sample is stratified by the rules that made the hazard (``STRATA``), so each
rule's error rate can be read off; the check weights the strata back to the
population. What the annotator sees (``merge_sheet.csv`` and the map
``merge_review.html``) holds the DAT lines and SPC tracks; the measures that might
predict an over-merge (simultaneous SPC tracks, the largest gap between lines,
the spread of start times) go to ``merge_key.csv``, for the check to test.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.ops import unary_union

from .. import config
from . import episode_table
from . import references as refs
from .geometry import to_equal_area, to_shapely
from .spc_tornadoes import track_geometries

ANNOTATION = config.OUTPUT_DIR / "annotation"
SHEET_SEED = 20261112
LABELS = ("one_tornado", "several_tornadoes", "cannot_tell")
# Stage 12's rules behind a hazard, and how many of each the sheet draws.
STRATA = {"endpoint_gap": 30, "event_id": 20, "polygon": 15, "mixed": 10}
# An SPC hazard (a tornado with no DAT link) this close to a candidate's lines on
# its day is shown: the merge may have swallowed its ground without its record.
NEARBY_M = 1_000.0


def stratum(merge_evidence: str) -> str:
    """The stage 12 rules behind a hazard, as one of ``STRATA``."""
    rules = set(str(merge_evidence or "").split(";")) - {""}
    if rules == {"endpoint_gap"}:
        return "endpoint_gap"
    if rules == {"event_id+date"}:
        return "event_id"
    if rules and rules <= {"spatial_link", "path_guid"}:
        return "polygon"
    return "mixed"


def paths() -> dict[str, Path]:
    return {"sheet": ANNOTATION / "merge_sheet.csv", "key": ANNOTATION / "merge_key.csv",
            "map": ANNOTATION / "merge_review.html",
            "how_to": ANNOTATION / "HOW_TO_ANNOTATE_merges.txt",
            "manifest": ANNOTATION / "manifest_annotation_merges.json"}


def _iso_hm(value) -> str:
    t = pd.to_datetime(value, utc=True, errors="coerce")
    return "?" if pd.isna(t) else f"{t:%Y-%m-%d %H:%M}"


def _features(path: Path) -> dict[str, dict]:
    """DAT features by ``objectid`` (as text)."""
    features = json.loads(path.read_text(encoding="utf-8"))["features"]
    return {str(f["properties"].get("objectid")): f for f in features}


def _lines_of(geom) -> list[list[list[float]]]:
    """[[lat, lon], ...] per part of a (multi)line, for Leaflet."""
    parts = getattr(geom, "geoms", [geom])
    return [[[round(y, 5), round(x, 5)] for x, y in part.coords] for part in parts
            if part.geom_type == "LineString"]


def _rings_of(geom) -> list[list[list[float]]]:
    parts = getattr(geom, "geoms", [geom])
    return [[[round(y, 5), round(x, 5)] for x, y in part.exterior.coords] for part in parts
            if part.geom_type == "Polygon"]


def _track_parts(geom) -> list[list[list[float]]]:
    """An SPC track for Leaflet: its line, or its start point when it has no end."""
    if geom is None:
        return []
    if geom.geom_type == "Point":
        return [[[round(geom.y, 5), round(geom.x, 5)]]]
    return _lines_of(geom)


def candidates(tag: str) -> tuple[pd.DataFrame, dict[str, dict]]:
    """Every multi-line DAT hazard on two or more SPC tracks, with what the sheet,
    the key and the map need (the last by ``hazard_uid``)."""
    hazards = pd.read_csv(config.PROCESSED_DIR / f"hazards_{tag}.csv", low_memory=False)
    links = pd.read_csv(refs.spc_links_path(tag))
    tracks = pd.read_csv(refs.SPC_TRACKS, low_memory=False)
    member = episode_table.membership(tag)
    lines = _features(config.INTERIM_DIR / f"dat_lines_{tag}.geojson")
    polygons = _features(config.INTERIM_DIR / f"dat_polygons_{tag}.geojson")

    n_spc = links.groupby("hazard_uid").spc_id.nunique()
    hazards["n_spc"] = hazards.hazard_uid.map(n_spc).fillna(0).astype(int)
    pop = hazards[(hazards.n_lines > 1) & (hazards.n_spc >= 2)].copy()
    pop["stratum"] = pop.merge_evidence.map(stratum)

    t = tracks.set_index("spc_id")
    t_geo = dict(zip(tracks.spc_id, track_geometries(tracks, lambda g: g)))
    t["t0"] = pd.to_datetime(t.begin_utc, utc=True, errors="coerce")
    t["t1"] = pd.to_datetime(t.end_utc, utc=True, errors="coerce").fillna(t.t0)
    own = member[member.hazard_source == "spc"].set_index("spc_id").hazard_uid
    own_day = t.t0.dt.date[t.index.isin(own.index)]
    by_hazard = links.groupby("hazard_uid").spc_id.agg(lambda s: sorted(set(s)))

    rows, shapes = [], {}
    for h in pop.itertuples():
        feats = [lines[o] for o in str(h.line_objectids).split(";") if o in lines]
        feats.sort(key=lambda f: str(f["properties"].get("starttime") or ""))
        geoms = [to_shapely(f["geometry"]) for f in feats]
        proj = [to_equal_area(g) for g in geoms]
        line_text = []
        for k, f in enumerate(feats, 1):
            p = f["properties"]
            length = p.get("length")
            line_text.append(
                f"L{k}: {_iso_hm(p.get('starttime'))}–{_iso_hm(p.get('endtime'))[11:]} UTC, "
                f"{p.get('efscale') or '?'}, "
                f"{length if isinstance(length, (int, float)) and length >= 0 else '?'} mi"
                + (f", {p['wfo']}" if p.get("wfo") else "")
                + (f", event_id {p['event_id']}" if str(p.get("event_id") or "").strip() else ""))
        gaps = [min(a.distance(b) for j, b in enumerate(proj) if j != i)
                for i, a in enumerate(proj)] if len(proj) > 1 else [0.0]
        starts = pd.to_datetime([f["properties"].get("starttime") for f in feats],
                                utc=True, errors="coerce").dropna()

        ids = [s for s in by_hazard.get(h.hazard_uid, []) if s in t.index]
        ids.sort(key=lambda s: (t.t0.get(s), s))
        spc_text = [f"S{k}: {_iso_hm(t.t0[s])}–{_iso_hm(t.t1[s])[11:]} UTC, "
                    f"{'EF' + str(int(t.mag[s])) if t.mag[s] >= 0 else 'EFU'}, "
                    f"{t.len[s]} mi, {t.st[s]}, {int(t.fat[s])} deaths ({s})"
                    for k, s in enumerate(ids, 1)]
        spans = sorted((t.t0[s], t.t1[s]) for s in ids if pd.notna(t.t0[s]))
        simultaneous = any(b0 < a1 for (a0, a1), (b0, b1) in zip(spans, spans[1:]))

        day = dt.date.fromisoformat(h.convective_day) if isinstance(h.convective_day, str) else None
        near = []
        if day is not None and proj:
            union = unary_union(proj)
            one = dt.timedelta(days=1)
            for s in own_day.index[(own_day >= day - one) & (own_day <= day + one)]:
                g = t_geo.get(s)
                if g is not None and to_equal_area(g).distance(union) <= NEARBY_M:
                    near.append(s)
        near_text = [f"{_iso_hm(t.t0[s])} UTC, "
                     f"{'EF' + str(int(t.mag[s])) if t.mag[s] >= 0 else 'EFU'}, {t.len[s]} mi ({s})"
                     for s in near]

        polys = [to_shapely(polygons[o]["geometry"])
                 for o in str(h.polygon_objectids or "").split(";") if o in polygons]
        shapes[h.hazard_uid] = {
            "lines": [_lines_of(g) for g in geoms if g is not None],
            "polygons": [r for g in polys if g is not None for r in _rings_of(g)],
            "spc": [_track_parts(t_geo.get(s)) for s in ids],
            "nearby": [_track_parts(t_geo.get(s)) for s in near],
            "line_text": line_text, "spc_text": spc_text, "near_text": near_text}
        rows.append({
            "hazard_uid": h.hazard_uid, "stratum": h.stratum,
            "merge_evidence": h.merge_evidence, "convective_day": h.convective_day,
            "states": ";".join(sorted({str(t.st[s]) for s in ids})), "wfo_all": h.wfo_all,
            "efscale": h.efscale, "n_lines": int(h.n_lines), "n_spc": len(ids),
            "dat_lines": " | ".join(line_text), "spc_tracks": " | ".join(spc_text),
            "spc_hazards_on_lines": " | ".join(near_text),
            "spc_simultaneous": simultaneous, "max_line_gap_m": round(max(gaps), 1),
            "line_start_spread_h": (round((starts.max() - starts.min()).total_seconds() / 3600, 2)
                                    if len(starts) > 1 else 0.0),
            "n_spc_hazards_on_lines": len(near)})
    return pd.DataFrame(rows), shapes


def draw(pop: pd.DataFrame, rng: np.random.Generator,
         sizes: dict[str, int] = STRATA) -> pd.DataFrame:
    """A stratified sample, in random order, with each case's weight."""
    picked = []
    for name, n in sizes.items():
        group = pop[pop.stratum == name]
        take = group.iloc[rng.choice(len(group), size=min(n, len(group)), replace=False)] \
            if len(group) else group
        picked.append(take.assign(weight=len(group) / max(len(take), 1)))
    sample = pd.concat(picked, ignore_index=True)
    sample = sample.iloc[rng.permutation(len(sample))].reset_index(drop=True)
    sample.insert(0, "case_id", [f"M{k:03d}" for k in range(1, len(sample) + 1)])
    return sample


SHEET_COLUMNS = ["case_id", "convective_day", "states", "wfo_all", "efscale", "n_lines",
                 "dat_lines", "n_spc", "spc_tracks", "spc_hazards_on_lines", "spc_reports",
                 "label", "notes"]
KEY_COLUMNS = ["case_id", "hazard_uid", "stratum", "weight", "merge_evidence",
               "spc_simultaneous", "max_line_gap_m", "line_start_spread_h",
               "n_spc_hazards_on_lines"]


def sheet_and_key(sample: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    sheet = sample.assign(
        spc_reports=[f"https://www.spc.noaa.gov/climo/reports/{pd.Timestamp(d):%y%m%d}_rpts.html"
                     if isinstance(d, str) else "" for d in sample.convective_day],
        label="", notes="")
    return sheet[SHEET_COLUMNS], sample[KEY_COLUMNS]


def read_sheet(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"label": str, "notes": str})
    df["label"] = df.label.str.strip().str.lower().replace("", None)
    return df


HOW_TO = """How to check stage 12's merges (stage 17)
=========================================

Each case is one hazard that stage 12 built from several DAT lines, where SPC's
database has two or more tornadoes. Question: is it ONE tornado, or did the
merge join SEVERAL that should be separate hazards?

1. Open the map: python -m http.server 8792 --directory outputs/annotation
   then http://127.0.0.1:8792/merge_review.html  (the basemap tiles need the
   server; the map works without them). Keys: n / p for next / previous case.
2. On the map: DAT lines in colour, numbered L1, L2, ... in order of start time
   (as in the sheet); DAT damage polygons shaded; SPC's tornadoes as dashed black
   start-end lines S1, S2, ...; SPC tornadoes with no DAT survey that lie on the
   lines dashed grey. The panel lists each line's and track's time, rating,
   length and office.
3. Decide, in merge_sheet.csv:
   one_tornado        the lines continue one track (end of one near the start
                      of the next, times in sequence, one parent storm); SPC
                      splitting it (at a state or office line) is fine
   several_tornadoes  at least one line is a separate tornado: side by side
                      (parallel tracks), at overlapping times, or a gap in
                      space and time that a single tornado would not leave
   cannot_tell        the map and the times do not settle it
   In notes, say which lines belong apart (e.g. "L3 separate, parallel to L1").
   The SPC report page (spc_reports) and the NWS event pages can help.
4. Do not open merge_key.csv before you are done.

When done:  python scripts/17_qa_events.py merges-check
"""


# ── the map ─────────────────────────────────────────────────────────────────
MAP_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Stage 12 merge check</title>
<style>__LEAFLET_CSS__</style>
<style>
  :root { --bg:#fff; --fg:#1d1d1f; --muted:#6b6b70; --line:#d9d9de; --link:#1f5fd1; }
  @media (prefers-color-scheme: dark) { :root { --bg:#17171a; --fg:#ececf0; --muted:#9a9aa3;
    --line:#33333a; --link:#8ab4ff; } }
  a { color:var(--link); }
  html, body { margin:0; height:100%; background:var(--bg); color:var(--fg);
    font:14px/1.45 system-ui, sans-serif; }
  #wrap { display:grid; grid-template-columns: 380px 1fr; height:100%; }
  #side { overflow:auto; border-right:1px solid var(--line); padding:12px 14px; }
  #map { height:100%; }
  #map .leaflet-tile-pane { filter: grayscale(1) opacity(0.75); }
  h1 { font-size:15px; margin:0 0 6px; }
  .nav { display:flex; gap:6px; align-items:center; margin:8px 0; }
  button, select { font:inherit; }
  ul { padding-left:18px; margin:4px 0 10px; }
  li { margin:2px 0; }
  .muted { color:var(--muted); }
  .sw { display:inline-block; width:12px; height:3px; vertical-align:middle; margin-right:4px; }
  @media (max-width: 760px) { #wrap { grid-template-columns: 1fr; grid-template-rows: 45% 55%; } }
</style></head>
<body><div id="wrap"><div id="side">
<h1>Stage 12 merge check</h1>
<div class="nav"><button id="prev">◀ p</button><select id="pick"></select>
<button id="next">n ▶</button></div>
<div id="info"></div>
<p class="muted">Label in merge_sheet.csv: one_tornado, several_tornadoes, cannot_tell.</p>
</div><div id="map"></div></div>
<script>__LEAFLET_JS__</script>
<script>
const CASES = __CASES__;
const COLORS = ['#2f6fdb','#d9480f','#2b8a3e','#ae3ec9','#c92a2a','#0b7285','#e67700','#5f3dc4'];
const map = L.map('map', {zoomAnimation:false});
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom:18,
  attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}).addTo(map);
let layer = L.layerGroup().addTo(map);
const pick = document.getElementById('pick');
CASES.forEach((c, i) => pick.add(new Option(c.case_id + '  ' + c.day, i)));
const esc = s => String(s).replace(/[&<>]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[ch]));
function show(i) {
  i = (i + CASES.length) % CASES.length; pick.value = i;
  const c = CASES[i]; layer.clearLayers(); const all = [];
  c.polygons.forEach(r => L.polygon(r, {color:'#868e96', weight:1, fillOpacity:0.15}).addTo(layer));
  c.nearby.forEach(parts => parts.forEach(p => { all.push(...p);
    (p.length > 1 ? L.polyline(p, {color:'#868e96', weight:3, dashArray:'4 6'})
                  : L.circleMarker(p[0], {radius:5, color:'#868e96'})).addTo(layer); }));
  c.spc.forEach((parts, k) => parts.forEach(p => { all.push(...p);
    const m = p.length > 1 ? L.polyline(p, {color:'#111', weight:2, dashArray:'6 6'})
                           : L.circleMarker(p[0], {radius:5, color:'#111'});
    m.bindTooltip('S' + (k + 1), {permanent:true, direction:'right', opacity:0.8}).addTo(layer); }));
  c.lines.forEach((parts, k) => parts.forEach((p, j) => { all.push(...p);
    const m = L.polyline(p, {color:COLORS[k % COLORS.length], weight:4, opacity:0.9}).addTo(layer);
    if (j === 0) m.bindTooltip('L' + (k + 1), {permanent:true, direction:'left', opacity:0.9}); }));
  map.invalidateSize();
  if (all.length) map.fitBounds(L.latLngBounds(all).pad(0.25), {maxZoom: 15});
  const li = (xs, colour) => xs.map((x, k) => '<li>' + (colour ? '<span class="sw" style="background:'
      + COLORS[k % COLORS.length] + '"></span>' : '') + esc(x) + '</li>').join('');
  document.getElementById('info').innerHTML =
    '<p><b>' + esc(c.case_id) + '</b> · ' + esc(c.day) + ' · ' + esc(c.states) + '</p>'
    + '<p class="muted">DAT lines</p><ul>' + li(c.line_text, true) + '</ul>'
    + '<p class="muted">SPC tornadoes linked to this hazard</p><ul>' + li(c.spc_text) + '</ul>'
    + (c.near_text.length ? '<p class="muted">SPC tornadoes without DAT survey on the lines</p><ul>'
       + li(c.near_text) + '</ul>' : '')
    + '<p><a href="' + c.report + '" target="_blank" rel="noopener">SPC reports of the day</a></p>';
}
pick.onchange = () => show(+pick.value);
document.getElementById('prev').onclick = () => show(+pick.value - 1);
document.getElementById('next').onclick = () => show(+pick.value + 1);
document.addEventListener('keydown', e => { if (e.key === 'n') show(+pick.value + 1);
  if (e.key === 'p') show(+pick.value - 1); });
map.setView([38, -95], 4);
window.addEventListener('load', () => show(0));
</script></body></html>
"""

LEAFLET = Path(__file__).resolve().parent.parent / "viewer" / "static" / "vendor"


def review_map(sample: pd.DataFrame, sheet: pd.DataFrame, shapes: dict[str, dict]) -> str:
    """One self-contained page showing every sampled case."""
    cases = []
    for (s, r) in zip(sample.itertuples(), sheet.itertuples()):
        cases.append({"case_id": s.case_id, "day": s.convective_day, "states": s.states,
                      "report": r.spc_reports, **shapes[s.hazard_uid]})
    return (MAP_TEMPLATE
            .replace("__LEAFLET_CSS__", (LEAFLET / "leaflet.css").read_text(encoding="utf-8"))
            .replace("__LEAFLET_JS__", (LEAFLET / "leaflet.js").read_text(encoding="utf-8"))
            .replace("__CASES__", json.dumps(cases).replace("</", "<\\/")))

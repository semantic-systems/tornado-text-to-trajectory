"""Shared pieces of the hand checks: stratified samples, worksheets, and one
self-contained review map per check.

A hand check writes, into ``outputs/annotation/``, a worksheet the annotator
fills in (``label``, ``notes``), a key with what the annotator should not see
while labelling (the hazard IDs, the stratum, the sampling weight, the measures
the check tests), a guide, and a review page: Leaflet over OpenStreetMap, one
case at a time, with the case's details beside the map (:func:`review_map`).
The page needs a local web server for the basemap tiles
(``python -m http.server 8792 --directory outputs/annotation``).

Used by :mod:`.dat.merge_check`, :mod:`.dat.unmatched_check` and
:mod:`.text.link_check`.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import config

ANNOTATION = config.OUTPUT_DIR / "annotation"
LEAFLET = Path(__file__).resolve().parent / "viewer" / "static" / "vendor"


# ── samples and sheets ──────────────────────────────────────────────────────
def draw(pop: pd.DataFrame, rng: np.random.Generator, sizes: dict[str, int],
         prefix: str) -> pd.DataFrame:
    """A sample of ``pop`` per ``stratum`` (``sizes``; all where fewer), in random
    order, with each case's ``weight`` (stratum size / cases drawn) and a
    ``case_id`` ``<prefix>001``…"""
    picked = []
    for name, n in sizes.items():
        group = pop[pop.stratum == name]
        take = (group.iloc[rng.choice(len(group), size=min(n, len(group)), replace=False)]
                if len(group) else group)
        picked.append(take.assign(weight=len(group) / max(len(take), 1)))
    sample = pd.concat(picked, ignore_index=True)
    sample = sample.iloc[rng.permutation(len(sample))].reset_index(drop=True)
    sample.insert(0, "case_id", [f"{prefix}{k:03d}" for k in range(1, len(sample) + 1)])
    return sample


def read_sheet(path: Path) -> pd.DataFrame:
    """A worksheet with ``label`` and ``notes`` as text, labels lower-cased."""
    df = pd.read_csv(path, dtype={"label": str, "notes": str})
    df["label"] = df.label.str.strip().str.lower().replace("", None)
    return df


def has_labels(path: Path) -> bool:
    return path.exists() and read_sheet(path).label.notna().any()


def wilson_row(name: str, k: int, n: int, *extra) -> str:
    """A markdown row: name, k of n, share with its Wilson 95% interval."""
    from .dat.evaluate import wilson_interval
    lo, hi = wilson_interval(k, n)
    share = f"{k / n:.0%} [{lo:.0%}, {hi:.0%}]" if n else "n/a"
    return "| " + " | ".join([name, f"{k} of {n}", share, *map(str, extra)]) + " |"


# ── geometry for the map ────────────────────────────────────────────────────
def latlon_parts(geom) -> list[dict]:
    """A shapely geometry (WGS84) as map layers: lines, polygon rings, points."""
    if geom is None or geom.is_empty:
        return []
    parts = getattr(geom, "geoms", [geom])
    out = []
    for part in parts:
        if part.geom_type == "LineString":
            out.append({"kind": "line",
                        "coords": [[round(y, 5), round(x, 5)] for x, y in part.coords]})
        elif part.geom_type == "Polygon":
            out.append({"kind": "polygon",
                        "coords": [[round(y, 5), round(x, 5)] for x, y in part.exterior.coords]})
        elif part.geom_type == "Point":
            out.append({"kind": "point", "coords": [[round(part.y, 5), round(part.x, 5)]]})
        else:
            out += latlon_parts(part)
    return out


def layers(geom, style: str, label: str | None = None) -> list[dict]:
    """Map layers for one object: ``style`` is ``c0``–``c7`` (numbered colours),
    ``spc`` (black dashed), ``grey`` (grey dashed), ``area`` (shaded polygon) or
    ``report`` (a red point). The label goes on the first part."""
    out = []
    for k, part in enumerate(latlon_parts(geom)):
        out.append({**part, "style": style, "label": label if k == 0 else None})
    return out


def iso_hm(value) -> str:
    t = pd.to_datetime(value, utc=True, errors="coerce")
    return "?" if pd.isna(t) else f"{t:%Y-%m-%d %H:%M}"


# ── the review page ─────────────────────────────────────────────────────────
MAP_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>__LEAFLET_CSS__</style>
<style>
  :root { --bg:#fff; --fg:#1d1d1f; --muted:#6b6b70; --line:#d9d9de; --link:#1f5fd1;
    --pre:#f4f4f6; }
  @media (prefers-color-scheme: dark) { :root { --bg:#17171a; --fg:#ececf0; --muted:#9a9aa3;
    --line:#33333a; --link:#8ab4ff; --pre:#222227; } }
  html, body { margin:0; height:100%; background:var(--bg); color:var(--fg);
    font:14px/1.45 system-ui, sans-serif; }
  a { color:var(--link); }
  #wrap { display:grid; grid-template-columns: 420px 1fr; height:100%; }
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
  pre { white-space:pre-wrap; background:var(--pre); padding:8px; border-radius:4px;
    font:12px/1.4 ui-monospace, monospace; max-height:45vh; overflow:auto; }
  @media (max-width: 760px) { #wrap { grid-template-columns: 1fr; grid-template-rows: 45% 55%; } }
</style></head>
<body><div id="wrap"><div id="side">
<h1>__TITLE__</h1>
<div class="nav"><button id="prev">◀ p</button><select id="pick"></select>
<button id="next">n ▶</button></div>
<div id="info"></div>
<p class="muted">__FOOTER__</p>
</div><div id="map"></div></div>
<script>__LEAFLET_JS__</script>
<script>
const CASES = __CASES__;
const COLORS = ['#2f6fdb','#d9480f','#2b8a3e','#ae3ec9','#c92a2a','#0b7285','#e67700','#5f3dc4'];
const STYLE = s => s === 'spc' ? {color:'#111', weight:2, dashArray:'6 6'}
  : s === 'grey' ? {color:'#868e96', weight:3, dashArray:'4 6'}
  : s === 'area' ? {color:'#868e96', weight:1, fillOpacity:0.15}
  : s === 'report' ? {color:'#c92a2a', weight:2, fillOpacity:0.8, radius:6}
  : {color:COLORS[+s.slice(1) % COLORS.length], weight:4, opacity:0.9};
const map = L.map('map', {zoomAnimation:false});
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom:18,
  attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}).addTo(map);
const layer = L.layerGroup().addTo(map);
const pick = document.getElementById('pick');
CASES.forEach((c, i) => pick.add(new Option(c.case_id + '  ' + c.subtitle, i)));
const esc = s => String(s).replace(/[&<>]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[ch]));
const ORDER = {area:0, grey:1, spc:2, report:4};
function show(i) {
  i = (i + CASES.length) % CASES.length; pick.value = i;
  const c = CASES[i]; layer.clearLayers(); const all = [];
  [...c.layers].sort((a, b) => (ORDER[a.style] ?? 3) - (ORDER[b.style] ?? 3)).forEach(l => {
    all.push(...l.coords); const st = STYLE(l.style);
    const m = l.kind === 'polygon' ? L.polygon(l.coords, st)
      : l.kind === 'point' ? L.circleMarker(l.coords[0], {radius:6, ...st})
      : L.polyline(l.coords, st);
    if (l.label) m.bindTooltip(l.label, {permanent:true, direction:'right', opacity:0.85});
    m.addTo(layer); });
  map.invalidateSize();
  if (all.length) map.fitBounds(L.latLngBounds(all).pad(0.25), {maxZoom: 15});
  const items = sec => sec.items.map(x => '<li>' + (x.colour != null ?
      '<span class="sw" style="background:' + COLORS[x.colour % COLORS.length] + '"></span>' : '')
      + esc(x.text) + '</li>').join('');
  document.getElementById('info').innerHTML =
    '<p><b>' + esc(c.case_id) + '</b> · ' + esc(c.subtitle) + '</p>'
    + c.sections.filter(s => s.items.length).map(s => '<p class="muted">' + esc(s.heading)
      + '</p><ul>' + items(s) + '</ul>').join('')
    + (c.text ? '<p class="muted">' + esc(c.text_heading || 'Text') + '</p><pre>'
       + esc(c.text) + '</pre>' : '')
    + c.links.map(l => '<p><a href="' + l.url + '" target="_blank" rel="noopener">'
      + esc(l.text) + '</a></p>').join('');
}
pick.onchange = () => show(+pick.value);
document.getElementById('prev').onclick = () => show(+pick.value - 1);
document.getElementById('next').onclick = () => show(+pick.value + 1);
document.addEventListener('keydown', e => { if (e.target.tagName === 'SELECT') return;
  if (e.key === 'n') show(+pick.value + 1); if (e.key === 'p') show(+pick.value - 1); });
map.setView([38, -95], 4);
window.addEventListener('load', () => show(0));
</script></body></html>
"""


def case(case_id: str, subtitle: str, sections: list[tuple[str, list]], map_layers: list[dict],
         links: list[tuple[str, str]] = (), text: str | None = None,
         text_heading: str | None = None) -> dict:
    """One case for :func:`review_map`. A section item is a string, or
    ``(text, colour index)`` to show the colour it is drawn in."""
    return {"case_id": case_id, "subtitle": subtitle,
            "sections": [{"heading": h, "items": [
                {"text": x[0], "colour": x[1]} if isinstance(x, tuple) else {"text": x}
                for x in items]} for h, items in sections],
            "layers": map_layers, "links": [{"text": t, "url": u} for t, u in links if u],
            "text": text, "text_heading": text_heading}


def review_map(title: str, cases: list[dict], footer: str) -> str:
    """One self-contained page for every case of a hand check."""
    return (MAP_TEMPLATE
            .replace("__LEAFLET_CSS__", (LEAFLET / "leaflet.css").read_text(encoding="utf-8"))
            .replace("__LEAFLET_JS__", (LEAFLET / "leaflet.js").read_text(encoding="utf-8"))
            .replace("__TITLE__", title).replace("__FOOTER__", footer)
            .replace("__CASES__", json.dumps(cases).replace("</", "<\\/")))


# ── hazards, for the checks that show several ───────────────────────────────
def load_hazards(tag: str) -> pd.DataFrame:
    """Every DAT and SPC hazard with its geometry (WGS84 and projected), times
    and values as stage 15 wrote them (``hazard_episodes``)."""
    from .dat import episode_table
    from .dat.geometry import to_equal_area, to_shapely

    rows = []
    for path in (config.PROCESSED_DIR / f"hazards_{tag}.geojson",
                 episode_table.spc_hazards_path(tag, "geojson")):
        for f in json.loads(path.read_text(encoding="utf-8"))["features"]:
            geom = to_shapely(f.get("geometry"))
            if geom is None:
                continue
            p = f["properties"]
            rows.append({"hazard_uid": p["hazard_uid"], "geom": geom,
                         "proj": to_equal_area(geom), "length_mi": p.get("path_length_mi"),
                         "wfo": p.get("wfo") or p.get("states")})
    out = pd.DataFrame(rows)
    member = episode_table.membership(tag)
    cols = ["hazard_uid", "hazard_source", "begin_utc", "end_utc", "convective_day", "rating",
            "deaths", "spc_id"]
    return out.merge(member[[c for c in cols if c in member.columns]], on="hazard_uid",
                     how="left").reset_index(drop=True)


def describe_hazard(h, distance_m: float | None = None) -> str:
    """One line for the panel and the sheet: source, time, rating, length."""
    source = "DAT survey" if h.hazard_source == "dat" else "SPC record, no DAT survey"
    if isinstance(h.begin_utc, str):
        end = iso_hm(h.end_utc)[11:] if isinstance(h.end_utc, str) else "?"
        when = f"{iso_hm(h.begin_utc)}–{end} UTC"
    else:
        when = f"time unknown (day {h.convective_day})"
    length = (f", {h.length_mi:.1f} mi" if isinstance(h.length_mi, (int, float))
              and h.length_mi == h.length_mi else "")
    far = f", {distance_m / 1000:.1f} km away" if distance_m is not None else ""
    return f"{source}, {when}, {h.rating if isinstance(h.rating, str) else '?'}{length}{far}"


# ── running a check ─────────────────────────────────────────────────────────
def write_check(check, tag: str, force: bool, stage: str) -> pd.DataFrame:
    """Draw ``check``'s sample and write its sheet, key, map, guide and manifest.

    ``check`` is a module with ``paths()``, ``candidates(tag)`` -> (population,
    shapes, or a function of the sample that builds them; they are also put in
    ``sample.attrs["shapes"]``), ``STRATA``, ``PREFIX``, ``SHEET_SEED``, ``sheet_and_key(sample)``,
    ``review_map(sample, sheet, shapes)`` and ``HOW_TO``. Refuses to overwrite a
    sheet that has labels unless ``force``. Returns the sample.
    """
    from .ids import write_manifest

    paths = check.paths()
    if has_labels(paths["sheet"]) and not force:
        raise SystemExit(f"labels already entered in {paths['sheet'].name} — not overwriting "
                         "(use --force to regenerate)")
    pop, shapes = check.candidates(tag)
    sample = draw(pop, np.random.default_rng(check.SHEET_SEED), check.STRATA, check.PREFIX)
    if callable(shapes):          # built for the sampled cases only
        shapes = shapes(sample)
    sample.attrs["shapes"] = shapes
    sheet, key = check.sheet_and_key(sample)
    paths["sheet"].parent.mkdir(parents=True, exist_ok=True)
    sheet.to_csv(paths["sheet"], index=False)
    key.to_csv(paths["key"], index=False)
    paths["map"].write_text(check.review_map(sample, sheet, shapes), encoding="utf-8")
    paths["how_to"].write_text(check.HOW_TO, encoding="utf-8")
    write_manifest(paths["manifest"], stage,
                   counts={"population": len(pop),
                           "population_by_stratum": pop.stratum.value_counts().to_dict(),
                           "cases": len(sample),
                           "cases_by_stratum": sample.stratum.value_counts().to_dict(),
                           "seed": check.SHEET_SEED},
                   outputs=[paths[k] for k in ("sheet", "key", "map", "how_to")])
    print(f"{len(pop):,} candidates; drew {len(sample)} ("
          + ", ".join(f"{k} {v}" for k, v in sample.stratum.value_counts().items()) + ")")
    for k in ("sheet", "key", "map", "how_to"):
        print(f"wrote {paths[k]}")
    return sample


def read_labelled(check) -> tuple[pd.DataFrame, dict]:
    """The sheet joined to its key, labels validated; and the manifest counts."""
    paths = check.paths()
    if not paths["sheet"].exists():
        raise SystemExit(f"no {paths['sheet'].name} — draw the sheet first")
    df = read_sheet(paths["sheet"]).merge(pd.read_csv(paths["key"]), on="case_id")
    allowed = getattr(check, "LABELS", None)
    if allowed is not None:
        bad = df.label.notna() & ~df.label.isin(allowed)
        if bad.any():
            raise SystemExit(f"labels not in {allowed}: {sorted(df.label[bad].unique())}")
    counts = json.loads(paths["manifest"].read_text())["counts"]
    return df, counts


def label_table(df: pd.DataFrame, labels: tuple[str, ...], strata: list[str],
                population: dict[str, int]) -> list[str]:
    """Labels per stratum, and each label's share weighted to the population."""
    head = "| stratum | labelled | " + " | ".join(l.replace("_", " ") for l in labels) + " |"
    lines = [head, "|---|---:|" + "---:|" * len(labels)]
    for name in strata:
        g = df[df.stratum == name]
        c = g.label.value_counts()
        lines.append(f"| {name} ({population.get(name, 0):,}) | {int(g.label.notna().sum())}/"
                     f"{len(g)} | " + " | ".join(str(int(c.get(l, 0))) for l in labels) + " |")
    done = df[df.label.notna()]
    if len(done):
        total = done.weight.sum()
        lines.append("| **weighted to all** | " + f"{len(done)}/{len(df)} | " + " | ".join(
            f"{(done.weight * (done.label == l)).sum() / total:.0%}" for l in labels) + " |")
    return lines

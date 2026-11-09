'use strict';
/* Watch hand checks: outbreaks grouped A–I, watch pairs the motion check kept
   apart, and — once the outbreak labels are in — a side-by-side comparison of
   named groupings. Everything is drawn from /api; labels POST back to the sheets. */

const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g,
  c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const H = 3600e3;

// Categorical colours for groups, ordered so neighbours differ; small groups grey.
const PALETTE = ['#2a78d6', '#e8590c', '#2f9e44', '#c2255c', '#7048e8', '#0c8599',
                 '#b08900', '#d6336c', '#5c940d', '#1864ab', '#a61e4d', '#862e9c'];
const SMALL = '#8a8a8a';
const A_COL = getComputedStyle(document.documentElement).getPropertyValue('--accent').trim() || '#2a78d6';
const B_COL = getComputedStyle(document.documentElement).getPropertyValue('--accent-2').trim() || '#d9561f';
const LABEL_TEXT = {
  matches: 'matches', too_coarse: 'too coarse', too_fine: 'too fine', cannot_tell: 'cannot tell',
  separate_systems: 'separate systems', should_link: 'should link',
};
const LABEL_HELP = {
  matches: 'groups correspond to the event(s) the summaries describe',
  too_coarse: 'merges what the summaries treat as separate',
  too_fine: 'splits what the summaries treat as one event',
  cannot_tell: 'the summaries / pages do not settle it',
  separate_systems: 'B covers a different system — rejection right',
  should_link: 'B continues or replaces A — rejection wrong',
};

const S = {
  mode: 'outbreak', st: null, idx: 0, letter: 'A', data: null,
  t: null, domain: [0, 1], playing: null, showWatches: false, hl: null,
  ref: 0, diff: false, cmp: [], colours: null,   // compare view
  req: 0,   // the latest select(); an older one still loading must not draw over it
};

// ── time helpers ────────────────────────────────────────────────────────────
const ms = iso => (iso ? Date.parse(iso) : NaN);
const pad = n => String(n).padStart(2, '0');
const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
function fmt(t, withCst = false) {
  if (!isFinite(t)) return '—';
  const d = new Date(t);
  const s = `${d.getUTCDate()} ${MON[d.getUTCMonth()]} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}Z`;
  if (!withCst) return s;
  const c = new Date(t - 6 * H);
  return `${s} (${pad(c.getUTCHours())}:${pad(c.getUTCMinutes())} CST)`;
}
const fmtDay = t => { const d = new Date(t); return `${d.getUTCDate()} ${MON[d.getUTCMonth()]} ${d.getUTCFullYear()}`; };

function visibleAt(start, end) {
  const mode = $('window').value;
  if (mode === 'all' || S.t == null) return true;
  if (mode === 'cum') return start <= S.t;
  const w = +mode * H;
  return start <= S.t + w && (isFinite(end) ? end : start) >= S.t - w;
}

// ── map ─────────────────────────────────────────────────────────────────────
const map = L.map('map', {zoomControl: true, preferCanvas: true}).setView([38, -94], 5);
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 18,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
}).addTo(map);
const layers = {
  context: L.layerGroup().addTo(map), counties: L.layerGroup().addTo(map),
  watches: L.layerGroup().addTo(map), tracks: L.layerGroup().addTo(map),
  motion: L.layerGroup().addTo(map),
};
let drawn = [];   // {layer, start, end, base:{...style}, kind, g}

function clearMap() {
  Object.values(layers).forEach(l => l.clearLayers());
  for (const c of S.cmp) Object.values(c.layers).forEach(l => l.clearLayers());
  drawn = [];
}

function trackPopup(t, extra = '') {
  const ef = t.mag == null || t.mag < 0 ? 'EF?' : `EF${t.mag}`;
  const bits = [
    `<b>${esc(t.id)}</b> · ${ef}`,
    `${fmt(ms(t.t0), true)} – ${fmt(ms(t.t1))}`,
    esc([t.county, t.county ? null : t.st].filter(Boolean).join(', ')),
    [t.length_mi != null ? `${t.length_mi} mi` : null, t.width_yd ? `${t.width_yd} yd` : null,
     t.fat ? `${t.fat} killed` : null, t.inj ? `${t.inj} injured` : null].filter(Boolean).join(' · '),
    t.watches && t.watches.length ? `watches: ${t.watches.map(esc).join(', ')}` : 'no watch',
    extra,
  ];
  return bits.filter(Boolean).join('<br>');
}

function addTrack(t, color, opts = {}) {
  const pts = t.coords;
  const style = {color, weight: opts.weight || 3.5, opacity: 0.95, fillOpacity: 0.9};
  const layer = pts.length > 1
    ? L.polyline(pts, style)
    : L.circleMarker(pts[0], {...style, radius: 4, fillColor: color, weight: 1});
  layer.bindPopup(trackPopup(t, opts.popup || ''));
  layer.addTo(opts.layer || layers.tracks);
  drawn.push({layer, start: ms(t.t0), end: ms(t.t1), base: style, kind: 'track', g: opts.g,
              agree: opts.agree, panel: opts.panel});
  return layer;
}

function addShape(geom, style, layerGroup, start, end, popup, kind = 'shape') {
  if (!geom) return null;
  const layer = L.geoJSON(geom, {style: () => style});
  if (popup) layer.bindPopup(popup);
  layer.addTo(layerGroup);
  drawn.push({layer, start, end, base: style, kind});
  return layer;
}

function applyTime() {
  applyStyles();
  drawTimeline();
}

function applyStyles() {
  const hide = $('hide').checked;
  for (const d of drawn) {
    const on = visibleAt(d.start, d.end);
    const hl = S.hl != null && d.kind === 'track' ? d.g === S.hl : true;
    const f = (on ? (hl ? 1 : 0.18) : (hide ? 0 : 0.1)) * (S.diff && d.agree ? 0.15 : 1);
    const st = {opacity: (d.base.opacity ?? 1) * f};
    if (d.base.fillOpacity != null) st.fillOpacity = d.base.fillOpacity * f;
    d.layer.setStyle(st);
  }
  $('time-label').textContent = S.t == null ? '—' : fmt(S.t, true);
}

function fit() {
  if (S.mode === 'compare') return fitCompare();
  map.invalidateSize();
  const b = L.latLngBounds([]);
  for (const d of drawn) {
    if (d.kind === 'context') continue;
    try { b.extend(d.layer.getBounds ? d.layer.getBounds() : d.layer.getLatLng()); } catch (e) { /* empty */ }
  }
  if (b.isValid()) map.fitBounds(b, {padding: [24, 24], maxZoom: 9});
}

// ── time controls ───────────────────────────────────────────────────────────
function setDomain(lo, hi, t) {
  S.domain = [lo, hi];
  S.t = t ?? hi;
  $('time').value = Math.round((S.t - lo) / (hi - lo) * 1000);
}
$('time').addEventListener('input', e => {
  const [lo, hi] = S.domain;
  S.t = lo + (+e.target.value / 1000) * (hi - lo);
  applyTime();
});
$('window').addEventListener('change', applyTime);
$('hide').addEventListener('change', applyTime);
$('fit').addEventListener('click', fit);
function step(h) {
  const [lo, hi] = S.domain;
  S.t = Math.min(hi, Math.max(lo, (S.t ?? lo) + h * H));
  $('time').value = Math.round((S.t - lo) / (hi - lo) * 1000);
  applyTime();
}
function togglePlay() {
  if (S.playing) { clearInterval(S.playing); S.playing = null; $('play').textContent = '▶'; return; }
  if ($('window').value === 'all') $('window').value = '3';
  if (S.t >= S.domain[1]) S.t = S.domain[0];
  $('play').textContent = '❚❚';
  const stepH = Math.max(0.25, (S.domain[1] - S.domain[0]) / H / 160);
  S.playing = setInterval(() => {
    if (S.t >= S.domain[1]) { togglePlay(); return; }
    step(stepH);
  }, 120);
}
$('play').addEventListener('click', togglePlay);

// ── timeline (SVG) ──────────────────────────────────────────────────────────
function drawTimeline() {
  if (S.mode === 'compare') {
    S.cmp.forEach((c, i) => { if (S.data && S.colours) drawTimelineInto(c.svg, compareRows(i), 104, 64); });
    return;
  }
  drawTimelineInto($('timeline'), timelineRows(), 150, 96);
}

function drawTimelineInto(svg, rows, maxH, L0) {
  const W = svg.clientWidth || 800;
  const rowH = Math.max(7, Math.min(18, (maxH - 22) / Math.max(rows.length, 1)));
  const Ht = 22 + rows.length * rowH + 6;
  svg.setAttribute('viewBox', `0 0 ${W} ${Ht}`);
  svg.style.height = `${Math.min(Ht, maxH + 80)}px`;
  const R0 = 10;
  const [lo, hi] = S.domain;
  const x = t => L0 + (t - lo) / (hi - lo) * (W - L0 - R0);
  let out = '<g class="axis">';
  const span = (hi - lo) / H;
  const every = span > 96 ? 24 : span > 48 ? 12 : span > 24 ? 6 : span > 10 ? 3 : 1;
  const first = Math.ceil(lo / (every * H)) * every * H;
  for (let t = first; t <= hi; t += every * H) {
    const d = new Date(t);
    const lab = d.getUTCHours() === 0 ? `${d.getUTCDate()} ${MON[d.getUTCMonth()]}` : `${pad(d.getUTCHours())}Z`;
    out += `<line x1="${x(t)}" x2="${x(t)}" y1="14" y2="${Ht}"/><text x="${x(t) + 2}" y="11">${lab}</text>`;
  }
  if (S.mode !== 'review') {
    // 12 UTC: where a convective day — and stage 3's rule — cuts.
    for (let t = Math.ceil((lo - 12 * H) / (24 * H)) * 24 * H + 12 * H; t <= hi; t += 24 * H) {
      if (t < lo) continue;
      out += `<line class="cday" x1="${x(t)}" x2="${x(t)}" y1="14" y2="${Ht}"><title>12Z: convective-day boundary</title></line>`;
      if (every > 12) out += `<text class="cday-l" x="${x(t) + 2}" y="11">12Z</text>`;
    }
  }
  out += '</g>';
  if (S.mode !== 'review' && S.data) {
    const [a, b] = S.data.window.map(ms);
    out += `<rect class="sheetwin" x="${x(a)}" y="15" width="${x(b) - x(a)}" height="${Ht - 18}"><title>outbreak window of the sheet</title></rect>`;
  }
  const mode = $('window').value;
  if (S.t != null && mode !== 'all') {
    const w = mode === 'cum' ? null : +mode * H;
    const a = w == null ? lo : S.t - w, b = w == null ? S.t : S.t + w;
    out += `<rect class="win" x="${x(Math.max(a, lo))}" y="15" width="${Math.max(0, x(Math.min(b, hi)) - x(Math.max(a, lo)))}" height="${Ht - 18}"/>`;
  }
  rows.forEach((r, i) => {
    const y = 20 + i * rowH;
    out += `<g class="row" data-g="${r.g ?? ''}"><rect class="bg" x="0" y="${y}" width="${W}" height="${rowH}"/>`;
    out += `<text x="4" y="${y + rowH * 0.72}">${esc(r.label)}</text>`;
    for (const bar of r.bars || []) {
      out += `<rect x="${x(bar[0])}" y="${y + rowH * 0.25}" width="${Math.max(1.5, x(bar[1]) - x(bar[0]))}" height="${rowH * 0.5}" fill="${r.color}" opacity="${bar[2] ?? 0.55}" rx="2"/>`;
    }
    for (const t of r.ticks || []) {
      out += `<rect x="${x(t) - 0.9}" y="${y + 2}" width="1.8" height="${rowH - 4}" fill="${r.color}"/>`;
    }
    out += '</g>';
  });
  if (S.t != null) out += `<line class="now" x1="${x(S.t)}" x2="${x(S.t)}" y1="14" y2="${Ht}"/>`;
  svg.innerHTML = out;
  // Press and drag on the timeline to scrub through time.
  const scrub = e => {
    const box = svg.getBoundingClientRect();
    const px = (e.clientX - box.left) * (W / box.width);
    if (px < L0) return;
    S.t = Math.min(hi, Math.max(lo, lo + (px - L0) / (W - L0 - R0) * (hi - lo)));
    $('time').value = Math.round((S.t - lo) / (hi - lo) * 1000);
    applyTime();
  };
  svg.onpointerdown = e => { svg.setPointerCapture(e.pointerId); svg.dataset.drag = '1'; scrub(e); };
  svg.onpointermove = e => { if (svg.dataset.drag) scrub(e); };
  svg.onpointerup = svg.onpointercancel = e => { delete svg.dataset.drag; svg.releasePointerCapture(e.pointerId); };
  svg.querySelectorAll('.row').forEach(el => {
    if (el.dataset.g === '') return;
    el.onmouseenter = () => highlight(+el.dataset.g);
    el.onmouseleave = () => highlight(null);
  });
}

function timelineRows() {
  const d = S.data;
  if (!d) return [];
  if (S.mode === 'outbreak') {
    const G = d.groupings[S.letter];
    const rows = [];
    const big = G.groups.filter(g => !g.small).slice(0, 14);
    for (const g of big) {
      rows.push({g: g.g, label: `${g.g + 1} · ${g.n}`, color: groupColor(g),
                 ticks: d.tracks.filter(t => t.g[S.letter] === g.g).map(t => ms(t.t0))});
    }
    const rest = d.tracks.filter(t => {
      const g = t.g[S.letter];
      return g == null || !big.some(b => b.g === g);
    });
    if (rest.length) rows.push({label: `other · ${rest.length}`, color: SMALL, ticks: rest.map(t => ms(t.t0))});
    return rows;
  }
  const rows = [
    {label: `A ${d.a.wid.slice(5)}`, color: A_COL,
     bars: [[ms(d.a.start), ms(d.a.end), 0.75], ...d.a.counties.map(c => [ms(c.start), ms(c.end), 0.12])]},
    {label: `B ${d.b.wid.slice(5)}`, color: B_COL,
     bars: [[ms(d.b.start), ms(d.b.end), 0.75], ...d.b.counties.map(c => [ms(c.start), ms(c.end), 0.12])]},
  ];
  for (const c of d.context.slice(0, 8)) {
    rows.push({label: `${c.wid.slice(5)} ${c.type}`, color: SMALL, bars: [[ms(c.start), ms(c.end), 0.45]]});
  }
  rows.push({label: `tornadoes · ${d.tracks.length}`, color: 'currentColor', ticks: d.tracks.map(t => ms(t.t0))});
  return rows;
}

function groupColor(g) {
  return g.small ? SMALL : PALETTE[g.g % PALETTE.length];
}

function highlight(g) {
  if (S.hl === g) return;
  S.hl = g;
  document.querySelectorAll('.group').forEach(el => el.classList.toggle('hl', g != null && +el.dataset.g === g));
  applyStyles();
}

// ── data ────────────────────────────────────────────────────────────────────
async function api(path, body) {
  const r = await fetch(path, body ? {method: 'POST', headers: {'Content-Type': 'application/json'},
                                      body: JSON.stringify(body)} : {});
  const j = await r.json();
  if (!r.ok) throw new Error(j.error || r.statusText);
  return j;
}

function items() { return S.mode === 'review' ? S.st.pairs : S.st.outbreaks; }

function progress() {
  const o = S.st.outbreaks.flatMap(x => x.rows);
  $('prog-outbreak').textContent = `${o.filter(r => r.label).length}/${o.length}`;
  $('prog-outbreak').title = `groupings labelled: ${S.st.outbreaks.length} outbreaks × ${S.st.outbreaks[0]?.rows.length || 0} groupings`;
  $('prog-review').textContent = `${S.st.pairs.filter(r => r.label).length}/${S.st.pairs.length}`;
  $('prog-compare').textContent = S.st.compare.ready ? '' : '🔒';
  $('prog-compare').title = S.st.compare.ready ? '' : 'opens once every outbreak grouping is labelled';
  const no = S.st.outbreaks.length, ng = S.st.outbreaks[0]?.rows.length || 0;
  const last = String.fromCharCode(64 + ng);
  $('guide-counts').textContent = `outbreaks ${no} × ${ng} groupings = ${no * ng}, watch pairs ${S.st.pairs.length}`;
  document.querySelectorAll('.guide-letters').forEach(el => { el.textContent = `A–${last}`; });
  document.querySelectorAll('.guide-keys').forEach(el => { el.textContent = `a–${last.toLowerCase()}`; });
}

function renderList() {
  progress();
  const el = $('list');
  if (S.mode === 'outbreak') {
    const n = S.st.outbreaks[0]?.rows.length || 0;
    el.innerHTML = `<div class="list-head">${S.st.outbreaks.length} outbreaks × ${n} groupings — label every grouping (A–${String.fromCharCode(64 + n)}) of each outbreak</div>` + S.st.outbreaks.map((o, i) => `
      <div class="item" data-i="${i}" aria-selected="${i === S.idx}">
        <div class="t">${esc(o.title)}</div>
        <div class="s">${o.tornadoes} tornadoes in the window</div>
        <div class="dots">${o.rows.map(r => `<span class="dot ${r.label ? 'done lab-' + r.label : ''}"
             title="${esc(r.label || 'unlabelled')}">${r.letter}</span>`).join('')}</div>
      </div>`).join('');
  } else if (S.mode === 'compare') {
    el.innerHTML = `<div class="list-head">${S.st.outbreaks.length} outbreaks — ${S.st.compare.n} groupings side by side, read-only</div>` + S.st.outbreaks.map((o, i) => `
      <div class="item" data-i="${i}" aria-selected="${i === S.idx}">
        <div class="t">${esc(o.title)}</div>
        <div class="s">${o.tornadoes} tornadoes in the window</div>
      </div>`).join('');
  } else {
    el.innerHTML = `<div class="list-head">${S.st.pairs.length} watch pairs — one label each</div>` + S.st.pairs.map((p, i) => `
      <div class="item" data-i="${i}" aria-selected="${i === S.idx}">
        <div class="t">${esc(p.pair_id)} <span class="chip ${p.label ? 'done lab-' + p.label : ''}">${esc(LABEL_TEXT[p.label] || 'open')}</span></div>
        <div class="s">${esc(p.a)} ${esc(p.a_type)} → ${esc(p.b)} ${esc(p.b_type)}</div>
      </div>`).join('');
  }
  el.querySelectorAll('.item').forEach(n => { n.onclick = () => select(+n.dataset.i); });
  const cur = el.querySelector(`.item[data-i="${S.idx}"]`);
  if (cur) cur.scrollIntoView({block: 'nearest'});
}

function saveHash() {
  const it = items()[S.idx];
  if (!it) return;
  history.replaceState(null, '', S.mode === 'outbreak' ? `#outbreak/${it.id}/${S.letter}`
    : S.mode === 'compare' ? `#compare/${it.id}` : `#review/${it.pair_id}`);
}

async function select(i, letter) {
  if (i < 0 || i >= items().length) return;
  if (S.playing) togglePlay();
  const req = ++S.req;
  S.idx = i;
  S.hl = null;
  renderList();
  $('panel').innerHTML = '<p class="empty">Loading…</p>';
  clearMap();
  if (S.mode === 'outbreak') {
    const o = S.st.outbreaks[i];
    S.letter = letter || (o.rows.find(r => !r.label) || o.rows[0]).letter;
    const data = await api(`/api/outbreak/${o.id}`);
    if (req !== S.req) return;
    S.data = data;
    setDomain(ms(S.data.extent[0]) - H, ms(S.data.extent[1]) + H);
    drawOutbreak();
  } else if (S.mode === 'compare') {
    if (!S.st.compare.ready) {
      $('panel').innerHTML = `<h2>Compare</h2><p class="empty">Opens once every outbreak grouping carries a
        label: this view names the groupings, so the blind labels have to be fixed first.</p>`;
      return;
    }
    const data = await api(`/api/compare/${S.st.outbreaks[i].id}`);
    if (req !== S.req) return;
    S.data = data;
    S.ref = Math.min(S.ref, S.data.panels.length - 1);
    setDomain(ms(S.data.extent[0]) - H, ms(S.data.extent[1]) + H);
    drawCompare();
  } else {
    const p = S.st.pairs[i];
    const data = await api(`/api/pair/${p.pair_id}`);
    if (req !== S.req) return;
    S.data = data;
    const [lo, hi] = S.data.window.map(ms);
    setDomain(lo, hi, ms(S.data.b.start));
    if ($('window').value === 'all') $('window').value = '1';
    drawPair();
  }
  saveHash();
  fit();
}

// ── outbreak view ───────────────────────────────────────────────────────────
function drawOutbreak() {
  clearMap();
  const d = S.data, G = d.groupings[S.letter];
  const byG = Object.fromEntries(G.groups.map(g => [g.g, g]));
  if (S.showWatches) {
    for (const w of d.watches) {
      const col = w.type === 'TOR' ? '#c92a2a' : '#e67700';
      addShape(w.geometry, {color: col, weight: 1.2, opacity: 0.8, fill: false, dashArray: w.type === 'TOR' ? null : '4 3'},
               layers.watches, ms(w.start), ms(w.end),
               `<b>${w.type === 'TOR' ? 'Tornado' : 'Severe thunderstorm'} watch ${esc(w.wid.slice(5))}</b>${w.pds ? ' (PDS)' : ''}<br>${fmt(ms(w.start))} – ${fmt(ms(w.end))}<br>${esc(w.offices || '')}`,
               'watch');
    }
  }
  // Ungrouped and small groups first, so the large groups draw on top.
  const order = [...d.tracks].sort((a, b) => {
    const ga = byG[a.g[S.letter]], gb = byG[b.g[S.letter]];
    return (gb ? gb.g : 1e9) - (ga ? ga.g : 1e9);
  });
  for (const t of order) {
    const g = byG[t.g[S.letter]];
    const color = g ? groupColor(g) : SMALL;
    const popup = `grouping ${S.letter}: ${g ? 'group ' + (g.g + 1) : 'not grouped'}${t.inside ? '' : ' · outside the outbreak window'}`;
    const layer = addTrack(t, color, {g: g ? g.g : -1, popup, weight: t.inside ? 3.5 : 2});
    if (!t.inside) layer.setStyle({dashArray: '4 4'});
  }
  renderOutbreakPanel();
  applyTime();
}

function renderOutbreakPanel() {
  const o = S.st.outbreaks[S.idx], d = S.data, G = d.groupings[S.letter];
  const row = o.rows.find(r => r.letter === S.letter);
  const big = G.groups.filter(g => !g.small);
  const small = G.groups.filter(g => g.small);
  $('panel').innerHTML = `
    <h2>${esc(d.title)}</h2>
    <div class="sub">${o.tornadoes} SPC tornadoes in the window · ${fmt(ms(d.window[0]))} – ${fmt(ms(d.window[1]))}</div>
    <div class="links">${d.reports.map(u => `<a href="${esc(u)}" target="_blank" rel="noopener">SPC reports ${esc(u.match(/(\d{6})_rpts/)?.[1] || '')}</a>`).join('')}
      <a href="${wikiSearch(d.window[0])}" target="_blank" rel="noopener">Wikipedia search</a></div>
    <div class="section">Grouping</div>
    <div class="letters">${o.rows.map(r => `<button data-l="${r.letter}" aria-pressed="${r.letter === S.letter}" title="${esc(r.label || 'unlabelled')}">${r.letter}<span class="mini ${r.label ? 'lab-' + r.label : ''}"></span></button>`).join('')}</div>
    <div class="section">Label grouping ${S.letter}</div>
    ${labelButtons('outbreak', row.label)}
    <div class="section">Notes</div>
    <textarea id="notes" placeholder="What decided it, e.g. “25 Apr separate system in the summaries”">${esc(row.notes)}</textarea>
    <div class="saved" id="saved"></div>
    <div class="section">Groups under ${S.letter} — ${big.length} with ≥ 3 tornadoes in the window</div>
    <div class="groups">${big.map(g => groupRow(g)).join('')}</div>
    <p class="note">${small.length ? `${small.length} smaller group${small.length > 1 ? 's' : ''} (grey)` : ''}${G.not_grouped ? ` · ${G.not_grouped} tornadoes in no group (grey)` : ''}.
      Dashed tracks belong to a group but lie outside the outbreak window.</p>
    <label class="check wrap"><input type="checkbox" id="show-watches" ${S.showWatches ? 'checked' : ''}> show watch outlines (<kbd>w</kbd>) — may give away the watch-based groupings</label>`;
  $('panel').querySelectorAll('.letters button').forEach(b => { b.onclick = () => setLetter(b.dataset.l); });
  $('panel').querySelectorAll('.group').forEach(el => {
    el.onmouseenter = () => highlight(+el.dataset.g);
    el.onmouseleave = () => highlight(null);
    el.onclick = () => zoomGroup(+el.dataset.g);
  });
  $('show-watches').onchange = e => { S.showWatches = e.target.checked; drawOutbreak(); };
  wireLabels('outbreak', row.row_id);
}

function wikiSearch(iso) {
  const d = new Date(ms(iso));
  const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
                  'September', 'October', 'November', 'December'];
  const q = `tornado outbreak ${months[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
  return `https://en.wikipedia.org/w/index.php?search=${encodeURIComponent(q)}`;
}

function groupRow(g) {
  const span = `${fmt(ms(g.start))} – ${fmt(ms(g.end))}`;
  return `<div class="group" data-g="${g.g}">
    <span class="swatch" style="background:${groupColor(g)}"></span>
    <span><span class="n">${g.g + 1}</span> · ${g.n} tornadoes${g.outside ? ` <span class="m">(${g.outside} outside)</span>` : ''}<br>
      <span class="m">${span} · max EF${g.max_ef ?? '?'} · ${esc(g.states.join(' '))}</span></span></div>`;
}

function zoomGroup(g) {
  const b = L.latLngBounds([]);
  for (const d of drawn) if (d.kind === 'track' && d.g === g) {
    b.extend(d.layer.getBounds ? d.layer.getBounds() : d.layer.getLatLng());
  }
  if (b.isValid()) map.fitBounds(b, {padding: [30, 30], maxZoom: 9});
}

function setLetter(l) {
  if (S.mode !== 'outbreak' || !S.data || !S.data.groupings[l]) return;
  S.letter = l;
  S.hl = null;
  drawOutbreak();
  saveHash();
}

// ── compare view ────────────────────────────────────────────────────────────
// One synced map per named grouping. Colours follow the reference grouping: each
// group with ≥ 3 tornadoes in the window takes the colour of the reference group
// it shares most of them with (greedy, largest overlap first); a group left over
// gets a colour of its own. A split therefore shows as a new colour, a merge as
// two reference colours turning into one.
let syncing = false;
function buildCompare() {
  const box = $('compare');
  if (S.cmp.length === S.st.compare.n) return;
  box.innerHTML = '';
  S.cmp = [];
  for (let i = 0; i < S.st.compare.n; i++) {
    const cell = document.createElement('div');
    cell.className = 'cmp-cell';
    cell.innerHTML = `<div class="cmp-head"></div><div class="cmp-map"></div><svg class="cmp-tl" role="img" aria-label="timeline"></svg>`;
    box.appendChild(cell);
    const m = L.map(cell.querySelector('.cmp-map'), {zoomControl: i === 0, preferCanvas: true, attributionControl: i === S.st.compare.n - 1})
      .setView([38, -94], 4);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(m);
    const lg = {watches: L.layerGroup().addTo(m), tracks: L.layerGroup().addTo(m)};
    m.on('move', () => {
      if (syncing) return;
      syncing = true;
      for (const c of S.cmp) if (c.map !== m) c.map.setView(m.getCenter(), m.getZoom(), {animate: false});
      syncing = false;
    });
    S.cmp.push({map: m, layers: lg, svg: cell.querySelector('.cmp-tl'), head: cell.querySelector('.cmp-head')});
  }
}

function matchColours(d) {
  const names = d.panels.map(p => p.name), ref = names[S.ref];
  const big = n => d.groupings[n].groups.filter(g => !g.small);
  const out = {[ref]: Object.fromEntries(big(ref).map(g => [g.g, g.g]))};
  const fresh0 = big(ref).length;
  const inside = d.tracks.filter(t => t.inside);
  for (const n of names) {
    if (n === ref) continue;
    const isBig = new Set(big(n).map(g => g.g)), refBig = new Set(big(ref).map(g => g.g));
    const overlap = {};
    for (const t of inside) {
      const a = t.g[n], b = t.g[ref];
      if (a == null || b == null || !isBig.has(a) || !refBig.has(b)) continue;
      const k = `${a}|${b}`;
      overlap[k] = (overlap[k] || 0) + 1;
    }
    const pairs = Object.entries(overlap).sort((x, y) => y[1] - x[1]);
    const map = {}, taken = new Set();
    for (const [k] of pairs) {
      const [a, b] = k.split('|').map(Number);
      if (a in map || taken.has(b)) continue;
      map[a] = b;
      taken.add(b);
    }
    let fresh = fresh0;
    for (const g of big(n)) if (!(g.g in map)) map[g.g] = fresh++;
    out[n] = map;
  }
  return out;
}

const cid = (name, t) => {
  const g = t.g[name];
  return g == null ? null : (S.colours[name][g] ?? null);
};
const cColor = c => (c == null ? SMALL : PALETTE[c % PALETTE.length]);

function agreement(d) {
  // Share of window tornadoes drawn in the same colour as under the reference.
  const ref = d.panels[S.ref].name, inside = d.tracks.filter(t => t.inside);
  const out = {};
  for (const p of d.panels) {
    out[p.name] = inside.length ? inside.filter(t => cid(p.name, t) === cid(ref, t)).length / inside.length : 1;
  }
  return out;
}

function drawCompare() {
  clearMap();
  const d = S.data;
  S.colours = matchColours(d);
  const ref = d.panels[S.ref].name;
  const share = agreement(d);
  d.panels.forEach((p, i) => {
    const c = S.cmp[i];
    c.head.innerHTML = `<b>${esc(p.name)}</b>${i === S.ref ? ' <span class="chip">reference</span>' : ` <span class="m">${Math.round(share[p.name] * 100)}% same as reference</span>`}
      <span class="chip done lab-${esc(p.label)}" title="your blind label (grouping ${esc(p.letter)})${p.notes ? ': ' + esc(p.notes) : ''}">${esc(LABEL_TEXT[p.label] || 'unlabelled')}</span>`;
    if (S.showWatches) {
      for (const w of d.watches) {
        const col = w.type === 'TOR' ? '#c92a2a' : '#e67700';
        addShape(w.geometry, {color: col, weight: 1, opacity: 0.7, fill: false, dashArray: w.type === 'TOR' ? null : '4 3'},
                 c.layers.watches, ms(w.start), ms(w.end),
                 `<b>${w.type} watch ${esc(w.wid.slice(5))}</b><br>${fmt(ms(w.start))} – ${fmt(ms(w.end))}`, 'watch');
      }
    }
    const order = [...d.tracks].sort((a, b) => (cid(p.name, b) ?? 1e9) - (cid(p.name, a) ?? 1e9));
    for (const t of order) {
      const k = cid(p.name, t);
      const agree = i === S.ref
        ? d.panels.every(q => cid(q.name, t) === k)
        : k === cid(ref, t);
      const g = t.g[p.name];
      const layer = addTrack(t, cColor(k), {
        layer: c.layers.tracks, g: k ?? -1, agree, panel: i, weight: t.inside ? 3 : 1.8,
        popup: `${esc(p.name)}: ${g == null ? 'not grouped' : 'group ' + (g + 1)}${agree ? '' : ' · differs from the reference'}${t.inside ? '' : ' · outside the outbreak window'}`});
      if (!t.inside) layer.setStyle({dashArray: '4 4'});
    }
  });
  renderComparePanel(share);
  applyTime();
}

function compareRows(i) {
  const d = S.data, name = d.panels[i].name;
  const big = d.groupings[name].groups.filter(g => !g.small);
  const shown = big.slice(0, 10);
  const rows = shown.map(g => {
    const k = S.colours[name][g.g];
    return {g: k, label: `${g.g + 1} · ${g.n}`, color: cColor(k),
            ticks: d.tracks.filter(t => t.g[name] === g.g).map(t => ms(t.t0))};
  });
  const ids = new Set(shown.map(g => g.g));
  const rest = d.tracks.filter(t => t.g[name] == null || !ids.has(t.g[name]));
  if (rest.length) rows.push({label: `other · ${rest.length}`, color: SMALL, ticks: rest.map(t => ms(t.t0))});
  return rows;
}

function renderComparePanel(share) {
  const d = S.data, o = S.st.outbreaks[S.idx];
  $('panel').innerHTML = `
    <h2>${esc(d.title)}</h2>
    <div class="sub">${o.tornadoes} SPC tornadoes in the window · ${fmt(ms(d.window[0]))} – ${fmt(ms(d.window[1]))}</div>
    <div class="links">${d.reports.map(u => `<a href="${esc(u)}" target="_blank" rel="noopener">SPC reports ${esc(u.match(/(\d{6})_rpts/)?.[1] || '')}</a>`).join('')}
      <a href="${wikiSearch(d.window[0])}" target="_blank" rel="noopener">Wikipedia search</a></div>
    <div class="section">Colours follow (<kbd>r</kbd>)</div>
    <div class="refs">${d.panels.map((p, i) => `<button data-i="${i}" aria-pressed="${i === S.ref}">${esc(p.name)}</button>`).join('')}</div>
    <label class="check wrap"><input type="checkbox" id="cmp-diff" ${S.diff ? 'checked' : ''}> fade tracks that agree with the reference (<kbd>d</kbd>)</label>
    <label class="check wrap"><input type="checkbox" id="show-watches" ${S.showWatches ? 'checked' : ''}> watch outlines (<kbd>w</kbd>)</label>
    ${d.panels.map(p => {
      const G = d.groupings[p.name], big = G.groups.filter(g => !g.small);
      return `<div class="section">${esc(p.name)} — ${big.length} groups ≥ 3</div>
        <div class="r cmp-lab"><span class="chip done lab-${esc(p.label)}">${esc(LABEL_TEXT[p.label] || 'unlabelled')}</span>
          <span class="m">blind label (${esc(p.letter)})${p.name === d.panels[S.ref].name ? '' : ` · ${Math.round(share[p.name] * 100)}% of tornadoes same colour as the reference`}</span></div>
        ${p.notes ? `<div class="note">${esc(p.notes)}</div>` : ''}
        <div class="groups">${big.map(g => {
          const k = S.colours[p.name][g.g];
          return `<div class="group" data-g="${k}"><span class="swatch" style="background:${cColor(k)}"></span>
            <span><span class="n">${g.g + 1}</span> · ${g.n} tornadoes${g.outside ? ` <span class="m">(${g.outside} outside)</span>` : ''}<br>
            <span class="m">${fmt(ms(g.start))} – ${fmt(ms(g.end))} · ${esc(g.states.join(' '))}</span></span></div>`;
        }).join('')}</div>`;
    }).join('')}
    <p class="note">Same colour across maps = the same tornadoes grouped together. A new colour in a map is a
      group the reference does not have (a split); a reference colour missing from a map has been merged
      into another. Hover a group to light it up in every map. Read-only: nothing here changes the labels.</p>`;
  $('panel').querySelectorAll('.refs button').forEach(b => { b.onclick = () => setRef(+b.dataset.i); });
  $('cmp-diff').onchange = e => { S.diff = e.target.checked; applyStyles(); };
  $('show-watches').onchange = e => { S.showWatches = e.target.checked; drawCompare(); };
  $('panel').querySelectorAll('.group').forEach(el => {
    el.onmouseenter = () => highlight(+el.dataset.g);
    el.onmouseleave = () => highlight(null);
  });
}

function setRef(i) {
  if (!S.data || !S.data.panels[i]) return;
  S.ref = i;
  S.hl = null;
  drawCompare();
}

function fitCompare() {
  if (!S.cmp.length) return;
  S.cmp.forEach(c => c.map.invalidateSize());
  const b = L.latLngBounds([]);
  for (const d of drawn) if (d.kind === 'track' && d.panel === 0) {
    b.extend(d.layer.getBounds ? d.layer.getBounds() : d.layer.getLatLng());
  }
  if (b.isValid()) S.cmp[0].map.fitBounds(b, {padding: [12, 12], maxZoom: 9});
}

// ── pair view ───────────────────────────────────────────────────────────────
function destination(lat, lon, bearingDeg, km) {
  const R = 6371, d = km / R, b = bearingDeg * Math.PI / 180;
  const p1 = lat * Math.PI / 180, l1 = lon * Math.PI / 180;
  const p2 = Math.asin(Math.sin(p1) * Math.cos(d) + Math.cos(p1) * Math.sin(d) * Math.cos(b));
  const l2 = l1 + Math.atan2(Math.sin(b) * Math.sin(d) * Math.cos(p1), Math.cos(d) - Math.sin(p1) * Math.sin(p2));
  return [p2 * 180 / Math.PI, l2 * 180 / Math.PI];
}

function motionArrow(w, color) {
  if (!w.geometry || w.motion_from_deg == null || !w.motion_kt) return;
  const c = L.geoJSON(w.geometry).getBounds().getCenter();
  const to = (w.motion_from_deg + 180) % 360;
  const km = w.motion_kt * 1.852 * 2;          // two hours of motion
  const tip = destination(c.lat, c.lng, to, km);
  const style = {color, weight: 3, opacity: 0.95};
  L.polyline([[c.lat, c.lng], tip], style).addTo(layers.motion)
    .bindPopup(`storm motion of ${esc(w.wid)}: from ${w.motion_from_deg}° at ${w.motion_kt} kt<br>arrow = 2 h of motion (${Math.round(km)} km)`);
  for (const side of [150, -150]) {
    L.polyline([tip, destination(tip[0], tip[1], (to + side + 360) % 360, km * 0.12)], style).addTo(layers.motion);
  }
  L.circleMarker([c.lat, c.lng], {radius: 3, color, fillColor: color, fillOpacity: 1}).addTo(layers.motion);
}

function timeColor(t, lo, hi) {
  const f = Math.min(1, Math.max(0, (t - lo) / (hi - lo)));
  const stops = [[54, 33, 120], [183, 55, 121], [246, 133, 82]];
  const k = f < 0.5 ? 0 : 1, u = f < 0.5 ? f * 2 : (f - 0.5) * 2;
  const c = stops[k].map((v, j) => Math.round(v + (stops[k + 1][j] - v) * u));
  return `rgb(${c.join(',')})`;
}

function drawPair() {
  clearMap();
  const d = S.data;
  for (const c of d.context) {
    addShape(c.geometry, {color: '#777', weight: 1, opacity: 0.7, fill: false, dashArray: c.type === 'TOR' ? null : '4 3'},
             layers.context, ms(c.start), ms(c.end),
             `<b>${c.type} watch ${esc(c.wid.slice(5))}</b>${c.pds ? ' (PDS)' : ''}<br>${fmt(ms(c.start))} – ${fmt(ms(c.end))}<br>${esc(c.offices || '')}<br>(neither A nor B)`,
             'context');
  }
  for (const [w, col, name] of [[d.a, A_COL, 'A'], [d.b, B_COL, 'B']]) {
    for (const c of w.counties) {
      addShape(c.geometry, {color: col, weight: 0.6, opacity: 0.6, fillColor: col, fillOpacity: 0.22},
               layers.counties, ms(c.start), ms(c.end),
               `<b>${esc(c.name)}</b> (${esc(c.ugc)})<br>in watch ${name} ${esc(w.wid)}: ${fmt(ms(c.start))} – ${fmt(ms(c.end))}<br>office ${esc(c.wfo || '?')}`,
               'county');
    }
    addShape(w.geometry, {color: col, weight: 2.5, opacity: 1, fill: false},
             layers.watches, ms(w.start), ms(w.end),
             `<b>Watch ${name}: ${esc(w.wid)}</b> ${esc(w.type)}`, 'watch');
    motionArrow(w, col);
  }
  const [lo, hi] = d.window.map(ms);
  for (const t of d.tracks) {
    const inA = t.watches.includes(d.a.wid), inB = t.watches.includes(d.b.wid);
    addTrack(t, timeColor(ms(t.t0), lo, hi),
             {popup: inA || inB ? `in ${[inA ? 'A' : null, inB ? 'B' : null].filter(Boolean).join(' and ')}` : ''});
  }
  renderPairPanel();
  applyTime();
}

function watchCard(w, cls, name) {
  const type = w.type === 'TOR' ? 'Tornado' : 'Severe thunderstorm';
  return `<div class="card ${cls}">
    <div class="h">${name} · ${type} watch ${w.num} (${w.wid.slice(0, 4)})${w.pds ? ' · PDS' : ''}</div>
    <div class="r">${fmt(ms(w.start))} – ${fmt(ms(w.end))} · ${w.counties.length} counties · ${esc(w.offices || '')}</div>
    <div class="r">motion from ${w.motion_from_deg ?? '?'}° at ${w.motion_kt ?? '?'} kt${w.replaces ? ` · replaces ${esc(w.replaces)}` : ''}</div>
    <div class="r"><a href="${esc(w.url)}" target="_blank" rel="noopener">SPC watch page</a></div>
    ${w.text ? `<details><summary>SEL text</summary><pre>${esc(w.text)}</pre></details>` : ''}
  </div>`;
}

function renderPairPanel() {
  const p = S.st.pairs[S.idx], d = S.data;
  const gap = d.gap_min;
  const gapText = gap >= 0 ? `B starts ${gap} min after A ends` : `B starts ${-gap} min before A ends (they overlap)`;
  $('panel').innerHTML = `
    <h2>${esc(p.pair_id)}</h2>
    <div class="sub">${gapText}. The motion check kept B apart from A because B lies upstream of A's storm motion.</div>
    ${watchCard(d.a, 'a', 'A')}
    ${watchCard(d.b, 'b', 'B')}
    <div class="section">Label</div>
    ${labelButtons('review', p.label)}
    <div class="section">Notes</div>
    <textarea id="notes" placeholder="What decided it, e.g. “new development behind the line”">${esc(p.notes)}</textarea>
    <div class="saved" id="saved"></div>
    <p class="note">Filled counties are each watch's counties, drawn while in effect at the selected time;
      outlines are the watch polygons; arrows are two hours of each watch's storm motion. Grey: other
      watches in effect nearby. Tornadoes are coloured from early (purple) to late (orange).</p>`;
  wireLabels('review', p.pair_id);
}

// ── labels ──────────────────────────────────────────────────────────────────
function labelButtons(kind, current) {
  return `<div class="labels">${S.st.labels[kind].map((l, i) => `
    <button data-label="${l}" aria-pressed="${l === current}" class="${l === current ? 'lab-' + l : ''}" title="${esc(LABEL_HELP[l] || '')}">
      <kbd>${i + 1}</kbd>${esc(LABEL_TEXT[l] || l)}</button>`).join('')}</div>`;
}

let notesTimer = null;
function wireLabels(kind, id) {
  $('panel').querySelectorAll('.labels button').forEach(b => {
    b.onclick = () => setLabel(b.dataset.label);
  });
  $('notes').oninput = () => {
    clearTimeout(notesTimer);
    $('saved').textContent = '…';
    const row = currentRow(), text = $('notes').value;
    notesTimer = setTimeout(() => save(kind, id, row, row.label, text), 700);
  };
}

function currentRow() {
  if (S.mode === 'outbreak') return S.st.outbreaks[S.idx].rows.find(r => r.letter === S.letter);
  return S.st.pairs[S.idx];
}

// ``row`` is the item's entry in S.st, captured before the request: the user
// may have moved on to another item or grouping by the time it returns.
async function save(kind, id, row, label, notes) {
  const shown = () => currentRow() === row && $('saved');
  try {
    await api('/api/label', {kind, id, label, notes});
    row.label = label || '';
    row.notes = notes;
    if (shown()) $('saved').textContent = `saved ${new Date().toLocaleTimeString()}`;
    renderList();
    return true;
  } catch (e) {
    if (shown()) $('saved').textContent = `not saved: ${e.message}`;
    else alert(`Label for ${id} not saved: ${e.message}`);
    return false;
  }
}

async function setLabel(label) {
  const row = currentRow();
  if (!row) return;
  const next = row.label === label ? '' : label;
  const kind = S.mode === 'outbreak' ? 'outbreak' : 'review';
  const id = S.mode === 'outbreak' ? row.row_id : row.pair_id;
  clearTimeout(notesTimer);
  const ok = await save(kind, id, row, next, $('notes') ? $('notes').value : row.notes);
  if (!ok || currentRow() !== row) return;
  // Update the buttons in place: re-rendering the panel would drop notes typed meanwhile.
  $('panel').querySelectorAll('.labels button').forEach(b => {
    const on = b.dataset.label === row.label;
    b.setAttribute('aria-pressed', on);
    b.className = on ? `lab-${row.label}` : '';
  });
  $('panel').querySelectorAll('.letters button').forEach(b => {
    const r = S.st.outbreaks[S.idx].rows.find(x => x.letter === b.dataset.l);
    b.querySelector('.mini').className = `mini ${r && r.label ? 'lab-' + r.label : ''}`;
  });
  $('saved').textContent = next ? `saved: ${LABEL_TEXT[next]}` : 'label cleared';
}

function nextUnlabelled() {
  if (S.mode === 'outbreak') {
    const flat = S.st.outbreaks.flatMap((o, i) => o.rows.map(r => ({i, r})));
    const pos = flat.findIndex(x => x.i === S.idx && x.r.letter === S.letter);
    for (let k = 1; k <= flat.length; k++) {
      const x = flat[(pos + k) % flat.length];
      if (!x.r.label) {
        if (x.i === S.idx) setLetter(x.r.letter); else select(x.i, x.r.letter);
        return;
      }
    }
  } else {
    const n = S.st.pairs.length;
    for (let k = 1; k <= n; k++) {
      const j = (S.idx + k) % n;
      if (!S.st.pairs[j].label) { select(j); return; }
    }
  }
}

// ── modes, keys, start ──────────────────────────────────────────────────────
async function setMode(mode, idx = 0, letter) {
  if (S.mode !== mode) S.hl = null;
  S.mode = mode;
  document.querySelectorAll('.tabs button').forEach(b => b.setAttribute('aria-selected', b.dataset.mode === mode));
  const cmp = mode === 'compare';
  $('compare').hidden = !cmp;
  $('map').hidden = cmp;
  $('timeline').style.display = cmp ? 'none' : '';
  if (cmp) {
    if (!S.st.compare.ready) S.st = await api('/api/state');   // labels may have been finished just now
    if (S.st.compare.ready) buildCompare();
  } else {
    map.invalidateSize();
  }
  select(idx, letter);
}
document.querySelectorAll('.tabs button').forEach(b => { b.onclick = () => setMode(b.dataset.mode); });
$('help-btn').onclick = () => { $('help').hidden = false; };
$('guide-btn').onclick = () => { $('guide').hidden = false; };
$('guide-close').onclick = () => { $('guide').hidden = true; };
$('guide').onclick = e => { if (e.target.id === 'guide') $('guide').hidden = true; };
// Show the guide once, on the first visit in this browser.
try {
  if (!localStorage.getItem('watch-review-guide-seen')) {
    $('guide').hidden = false;
    localStorage.setItem('watch-review-guide-seen', '1');
  }
} catch (e) { /* storage blocked: the Guide button still works */ }
$('help-close').onclick = () => { $('help').hidden = true; };
$('help').onclick = e => { if (e.target.id === 'help') $('help').hidden = true; };

document.addEventListener('keydown', e => {
  if (e.target.matches?.('textarea, input[type=text], select') || e.metaKey || e.ctrlKey || e.altKey) return;
  const k = e.key;
  if (k === '?') { $('help').hidden = !$('help').hidden; return; }
  if (k === 'G') { $('guide').hidden = !$('guide').hidden; return; }
  if (k === 'Escape') { $('help').hidden = true; $('guide').hidden = true; return; }
  if (S.mode === 'compare') {
    if (k === 'd') { S.diff = !S.diff; if ($('cmp-diff')) $('cmp-diff').checked = S.diff; applyStyles(); e.preventDefault(); return; }
    if (k === 'r' && S.data?.panels) { setRef((S.ref + 1) % S.data.panels.length); e.preventDefault(); return; }
    if (k === 'w') { S.showWatches = !S.showWatches; drawCompare(); e.preventDefault(); return; }
    if (/^[1-4a-i]$/.test(k)) return;
  }
  if (/^[1-4]$/.test(k)) {
    const l = S.st.labels[S.mode === 'outbreak' ? 'outbreak' : 'review'][+k - 1];
    if (l) setLabel(l);
  } else if (/^[a-i]$/.test(k) && S.mode === 'outbreak' && S.data?.groupings?.[k.toUpperCase()]) {
    setLetter(k.toUpperCase());
  }
  else if (k === 'j' || k === 'ArrowDown') select(S.idx + 1);
  else if (k === 'k' || k === 'ArrowUp') select(S.idx - 1);
  else if (k === 'n') nextUnlabelled();
  else if (k === 'ArrowRight') step(e.shiftKey ? 3 : 0.5);
  else if (k === 'ArrowLeft') step(e.shiftKey ? -3 : -0.5);
  else if (k === ' ') togglePlay();
  else if (k === 'z') fit();
  else if (k === 'w' && S.mode === 'outbreak') { S.showWatches = !S.showWatches; drawOutbreak(); }
  else return;
  e.preventDefault();
});
window.addEventListener('resize', () => { map.invalidateSize(); S.cmp.forEach(c => c.map.invalidateSize()); drawTimeline(); });

(async function start() {
  S.st = await api('/api/state');
  const [mode, id, letter] = location.hash.slice(1).split('/');
  if (mode === 'review') {
    setMode('review', Math.max(0, S.st.pairs.findIndex(p => p.pair_id === id)));
  } else if (mode === 'compare') {
    setMode('compare', Math.max(0, S.st.outbreaks.findIndex(o => o.id === id)));
  } else {
    setMode('outbreak', Math.max(0, S.st.outbreaks.findIndex(o => o.id === id)), letter);
  }
})();

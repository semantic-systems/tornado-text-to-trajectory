// Silver-links view: a tornado list, and per tornado its path and linked texts.
'use strict';

const $ = id => document.getElementById(id);
const FILTERS = ['q', 'year', 'geometry', 'strength', 'has', 'sort'];
let rows = [], current = null, map = null;

function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, c =>
    ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
}
const css = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const store = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* private mode */ } },
};

// ── blind mode: strengths and checks hidden until asked for ──
function setBlind(on) {
  document.body.classList.toggle('blind', on);
  $('blind').setAttribute('aria-pressed', String(on));
  $('blind').textContent = on ? 'strengths hidden' : 'strengths shown';
  store.set('silver.blind', on ? '1' : '0');
  if (on && $('strength').value) { $('strength').value = ''; load(); }
}

// ── list ──
async function load() {
  const params = new URLSearchParams();
  FILTERS.forEach(f => { const v = $(f).value.trim(); if (v) params.set(f, v); });
  const data = await (await fetch('/api/tornadoes?' + params)).json();
  rows = data.rows;
  $('count').textContent = `${data.total} tornadoes`;
  $('list').innerHTML = rows.length ? rows.map(rowHtml).join('')
    : '<div class="empty" style="padding:14px">No tornado matches.</div>';
  $('list').querySelectorAll('.row').forEach(el =>
    el.addEventListener('click', () => select(el.dataset.key)));
  markSelected();
}

function rowHtml(t) {
  const geo = {dat_polygon: 'polygon', dat_line: 'DAT line', spc_track: 'SPC track', none: 'no path'}[t.geometry];
  return `<div class="row" data-key="${escapeHtml(t.key)}" role="option">
    <div class="h"><span>${escapeHtml(t.name)}</span>
      <span class="pill strength-only s-${t.passage_strength}">${t.passage_strength}</span></div>
    <div class="m"><span>${t.date}</span><span>${escapeHtml(t.rating)}</span>
      <span>${escapeHtml(t.states.join(', '))}</span>
      <span class="pill geo-${t.geometry}">${geo}</span>
      <span>${t.n_passages} wiki · ${t.n_news} news${t.n_rejected ? ` · ${t.n_rejected} rejected` : ''}</span>
      ${t.sheet_rows.length ? `<span class="pill sheet" title="rows of the hand-check sheet">${t.sheet_rows.join(' ')}</span>` : ''}
    </div></div>`;
}

function markSelected() {
  $('list').querySelectorAll('.row').forEach(el =>
    el.setAttribute('aria-selected', String(el.dataset.key === current)));
  const sel = $('list').querySelector('.row[aria-selected="true"]');
  if (sel) {                                    // scroll the list only, never the page
    const list = $('list'), top = sel.offsetTop - list.offsetTop;
    if (top < list.scrollTop || top + sel.offsetHeight > list.scrollTop + list.clientHeight) {
      list.scrollTop = top - list.clientHeight / 3;
    }
  }
}

// ── one tornado ──
async function select(key) {
  if (!key) return;
  current = key;
  if (location.hash.slice(1) !== key) history.replaceState(null, '', '#' + key);
  markSelected();
  const res = await fetch('/api/tornado/' + encodeURIComponent(key));
  if (!res.ok) { $('detail').innerHTML = '<div class="empty">Unknown tornado.</div>'; return; }
  const t = await res.json();
  if (t.key !== current) return;               // a newer click won
  render(t);
}

function render(t) {
  const kept = t.texts.filter(x => x.strength !== 'rejected');
  const rejected = t.texts.filter(x => x.strength === 'rejected');
  const wiki = kept.filter(x => x.kind === 'wikipedia_passage');
  const news = kept.filter(x => x.kind !== 'wikipedia_passage');
  const terms = buildTerms(t.terms);
  const geo = {dat_polygon: 'DAT damage polygon', dat_line: 'DAT track line (no polygon)',
               spc_track: 'SPC straight track only (no DAT survey)', none: 'no path'}[t.geometry];
  $('detail').innerHTML = `
    <section class="tor-head">
      <h2>${escapeHtml(t.name)}</h2>
      <div class="m"><span>${t.date}</span><span>${escapeHtml(t.rating)}</span>
        <span>${escapeHtml(t.states.join(', '))}</span><span>${t.length_mi} mi</span>
        <span>${t.deaths} killed${t.injuries != null ? ` · ${t.injuries} injured` : ''}</span>
        <span class="pill geo-${t.geometry}">${geo}</span>
        ${t.dat_via === 'spc' ? '<span class="pill" title="DAT hazard found through the SPC track">DAT via SPC</span>' : ''}</div>
      <div class="m" style="margin-top:4px"><span>counties: ${escapeHtml(t.counties.join(', '))}</span></div>
      <div class="ids">NCEI events:
        ${t.event_ids.map(i => `<a href="${t.ncei_url.replace('{}', i)}" target="_blank" rel="noopener">${i}</a>`).join(' ')}
        ${t.episode_uids.length ? `<span>· episode ${escapeHtml(t.episode_uids.join(', '))}</span>` : ''}
        ${t.spc_ids.length ? `<span>· SPC ${escapeHtml(t.spc_ids.join(', '))}</span>` : ''}</div>
    </section>
    <div class="map-wrap"><div id="map"></div></div>
    <div class="legend">
      <span><i class="poly"></i>DAT damage polygon</span><span><i></i>DAT track line</span>
      <span><i class="spc"></i>SPC track</span><span><i class="seg"></i>Storm Events county segment</span>
      <button id="fit">fit path</button>
    </div>
    ${t.narratives.length ? `<details class="narr"><summary>Storm Events narrative
      (${t.narratives.length} county segment${t.narratives.length > 1 ? 's' : ''}) — the official record, for comparison</summary>
      ${t.narratives.map(n => `<p><b>${escapeHtml(n.county)}</b> (${n.event_id}): ${highlight(n.text, terms)}</p>`).join('')}
    </details>` : ''}
    <h3 class="section">Wikipedia passages <span class="muted">${wiki.length}</span></h3>
    ${wiki.map(x => cardHtml(x, terms)).join('')}
    <h3 class="section">News <span class="muted">${news.length} — cited by the passages
      (${news.filter(x => x.kind === 'lexisnexis').length} found in LexisNexis)</span></h3>
    ${news.map(x => cardHtml(x, terms)).join('') || '<p class="muted">No news article inherits this tornado.</p>'}
    ${rejected.length ? `<details class="rejected"><summary>Rejected by the checks
      <span class="muted">${rejected.length} — cite this tornado's record, but are not about it;
      not in the silver set</span></summary>${rejected.map(x => cardHtml(x, terms)).join('')}</details>` : ''}`;
  $('detail').scrollTop = 0;
  $('detail').querySelectorAll('.toggle').forEach(b => b.addEventListener('click', () => {
    const body = b.previousElementSibling;
    const open = body.classList.toggle('collapsed') === false;
    b.textContent = open ? 'collapse' : 'show full text';
  }));
  drawMap(t.map);
}

const CHECKS = {date_ok: 'date', state_ok: 'state', place_ok: 'place', rating_ok: 'rating'};
function cardHtml(x, terms) {
  const kind = {wikipedia_passage: x.unit_kind === 'tornado_article' ? 'Wikipedia article'
                : x.unit_kind === 'tornado_section' ? 'Wikipedia section' : 'Wikipedia',
                cited_news: 'cited news', lexisnexis: 'LexisNexis'}[x.kind];
  const days = x.days_after_event != null ? `${x.days_after_event >= 0 ? '+' : ''}${x.days_after_event} days` : '';
  const checks = Object.entries(CHECKS).map(([k, label]) => {
    const v = x.checks[k];
    return `<span class="${v === true ? 'ok' : v === false ? 'no' : 'na'}">${label} ${v === true ? '✓' : v === false ? '✗' : '–'}</span>`;
  }).join('');
  const title = x.kind === 'wikipedia_passage' && x.heading
    ? `${x.page_title} § ${x.heading}` : (x.title || '(untitled)');
  const paras = String(x.text || '').split(/\n\s*\n|\n/).map(s => s.trim()).filter(Boolean);
  const long = paras.join(' ').length > 700;
  return `<article class="text-card">
    <div class="card-head">
      ${x.url ? `<a class="t" href="${escapeHtml(x.url)}" target="_blank" rel="noopener">${escapeHtml(title)}</a>`
              : `<span class="t" style="font-weight:600;flex:1 1 300px">${escapeHtml(title)}</span>`}
      <span class="pill strength-only s-${x.strength}">${x.strength}</span>
      ${x.sheet_row ? `<span class="pill sheet" title="row of the hand-check sheet">${x.sheet_row}</span>` : ''}
    </div>
    <div class="m"><span>${kind}</span>${x.source && x.kind !== 'wikipedia_passage' ? `<span>${escapeHtml(x.source)}</span>` : ''}
      ${x.published ? `<span>${escapeHtml(x.published)}</span>` : ''}${days ? `<span>${days}</span>` : ''}
      ${x.text_quality && x.kind === 'cited_news' ? `<span class="pill">text: ${escapeHtml(x.text_quality)}</span>` : ''}
      ${x.kind === 'wikipedia_passage' && x.event_date ? `<span>event date ${x.event_date} (${escapeHtml(x.event_date_basis || '')})</span>` : ''}
      ${x.mediacloud && x.mediacloud.n ? `<span class="pill mc" title="also in our Media Cloud export: found by ${escapeHtml(x.mediacloud.tier)}; stage 30 label ${escapeHtml(x.mediacloud.label || 'none')}">Media Cloud · ${escapeHtml({url: 'same URL', title_outlet: 'same headline', title_syndicated: 'wire copy'}[x.mediacloud.tier] || x.mediacloud.tier)} · ${escapeHtml(x.mediacloud.label || '?')}${x.mediacloud.n > 1 ? ` · ${x.mediacloud.n} copies` : ''}</span>` : ''}
      ${x.url ? `<a href="${escapeHtml(x.url)}" target="_blank" rel="noopener">open</a>` : ''}
      ${x.archive_url ? `<a href="${escapeHtml(x.archive_url)}" target="_blank" rel="noopener">archive</a>` : ''}
    </div>
    <div class="checks strength-only">${checks}<span>how: ${escapeHtml(x.how)}</span>
      ${x.evidence ? `<span>evidence: ${escapeHtml(x.evidence)}</span>` : ''}
      ${x.table_match ? `<span>table row: ${escapeHtml(x.table_match)}</span>` : ''}
      ${x.ncei_ids && x.ncei_ids.length ? `<span>NCEI ids: ${x.ncei_ids.join(', ')}</span>` : ''}</div>
    ${x.reject_reason ? `<div class="reason">Rejected: ${escapeHtml(x.reject_reason)}.</div>` : ''}
    ${x.citing && x.citing.length ? `<div class="citing">cited by: ${x.citing.map(c =>
      c.url ? `<a href="${escapeHtml(c.url)}" target="_blank" rel="noopener">${escapeHtml(c.title)}</a>` : escapeHtml(c.title)).join(' · ')}</div>` : ''}
    ${paras.length ? `<div class="body${long ? ' collapsed' : ''}">${paras.map(p => `<p>${highlight(p, terms)}</p>`).join('')}</div>
      ${long ? '<button class="toggle">show full text</button>' : ''}`
      : `<div class="notext">No text retrieved${x.text_quality ? ` (${escapeHtml(x.text_quality)})` : ''} — open the URL${x.archive_url ? ' or the archive copy' : ''}.</div>`}
  </article>`;
}

// Counties and heading places, as typed in any case, with spaces or hyphens.
function buildTerms(terms) {
  const parts = (terms || []).filter(Boolean).map(t =>
    t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/\s+/g, '[\\W_]+'));
  return parts.length ? new RegExp(`\\b(${parts.join('|')})\\b`, 'gi') : null;
}
function highlight(text, re) {
  const safe = escapeHtml(text);
  return re ? safe.replace(re, '<mark>$1</mark>') : safe;
}

// ── map ──
let pathLayer = null;
function drawMap(fc) {
  if (map) { map.remove(); map = null; }
  map = L.map('map', {scrollWheelZoom: true});
  // OpenStreetMap standard tiles; the attribution is required by the ODbL licence.
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map);
  const accent = css('--accent') || '#2a78d6', accent2 = css('--accent-2') || '#eb6834';
  const secondary = css('--secondary') || '#52514e', primary = css('--primary') || '#0b0b0b';
  const style = f => ({
    dat_polygon: {color: accent, weight: 1.5, fillColor: accent, fillOpacity: 0.35},
    dat_line: {color: primary, weight: 2, opacity: 0.9},
    spc_track: {color: accent2, weight: 3, dashArray: '8 6', opacity: 0.95},
    se_segment: {color: secondary, weight: 2, dashArray: '2 5', opacity: 0.9},
  }[f.properties.role]);
  const order = {dat_polygon: 0, spc_track: 1, se_segment: 2, dat_line: 3};
  const feats = [...fc.features].sort((a, b) => order[a.properties.role] - order[b.properties.role]);
  pathLayer = L.geoJSON({type: 'FeatureCollection', features: feats}, {
    style,
    pointToLayer: (f, latlng) => L.circleMarker(latlng, {...style(f), radius: 5, fillOpacity: 0.6,
                                                           dashArray: null}),
    onEachFeature: (f, layer) => layer.bindPopup(popup(f.properties)),
  }).addTo(map);
  $('fit').onclick = fit;
  // The container was just inserted: measure it once layout has settled.
  requestAnimationFrame(() => fit());
  new ResizeObserver(() => map && map.invalidateSize()).observe($('map'));
}
function fit() {
  if (!map) return;
  map.invalidateSize();
  const b = pathLayer && pathLayer.getBounds();
  if (b && b.isValid()) map.fitBounds(b, {padding: [30, 30], maxZoom: 13});
  else map.setView([39.5, -95], 4);
}
function popup(p) {
  if (p.role === 'se_segment') {
    return `<b>Storm Events segment</b><br>${escapeHtml(p.county)} · ${escapeHtml(p.rating)}<br>
      ${p.length_mi ?? '?'} mi · ${p.width_yd ?? '?'} yd<br>event ${p.event_id}`;
  }
  const label = {dat_polygon: 'DAT damage polygon', dat_line: 'DAT track line', spc_track: 'SPC track'}[p.role];
  return `<b>${label}</b><br><code>${escapeHtml(p.hazard_uid)}</code>`;
}

// ── wiring ──
let timer = null;
$('q').addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(load, 200); });
$('q').addEventListener('search', load);       // Esc or the clear button empties the box
FILTERS.filter(f => f !== 'q').forEach(f => $(f).addEventListener('change', load));
$('blind').addEventListener('click', () => setBlind(!document.body.classList.contains('blind')));
document.addEventListener('keydown', e => {
  if (e.target.matches('input, select, textarea') || e.metaKey || e.ctrlKey || e.altKey) {
    if (e.key === 'Escape') e.target.blur();
    return;
  }
  if (e.key === '/') { e.preventDefault(); $('q').focus(); }
  else if (e.key === 'b') setBlind(!document.body.classList.contains('blind'));
  else if (e.key === 'j' || e.key === 'k') {
    const i = rows.findIndex(r => r.key === current);
    const next = rows[Math.max(0, Math.min(rows.length - 1, i < 0 ? 0 : i + (e.key === 'j' ? 1 : -1)))];
    if (next) select(next.key);
  }
});
window.addEventListener('hashchange', () => select(location.hash.slice(1)));

setBlind(store.get('silver.blind') !== '0');
load().then(() => select(location.hash.slice(1) || (rows[0] && rows[0].key)));

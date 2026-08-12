'use strict';

const listEl = document.getElementById('list');
const detailEl = document.getElementById('detail');
const countEl = document.getElementById('count');
const controls = {
  q: document.getElementById('q'),
  year: document.getElementById('year'),
  status: document.getElementById('status'),
  relation: document.getElementById('relation'),
  has_links: document.getElementById('has_links'),
  min_score: document.getElementById('min_score'),
};

let rows = [];
let selected = -1;
let offset = 0;
let total = 0;
let loading = false;
const PAGE = 60;

const escapeHtml = s => String(s ?? '').replace(/[&<>"']/g,
  c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));

function params(extra = {}) {
  const p = new URLSearchParams();
  for (const [key, el] of Object.entries(controls)) {
    if (el.value) p.set(key === 'q' ? 'q' : key, el.value);
  }
  for (const [k, v] of Object.entries(extra)) p.set(k, v);
  return p;
}

async function load(reset = true) {
  if (loading) return;
  loading = true;
  if (reset) { offset = 0; rows = []; listEl.innerHTML = '<div class="spinner">loading…</div>'; }
  const response = await fetch('/api/articles?' + params({offset, limit: PAGE}));
  const data = await response.json();
  total = data.total;
  rows = reset ? data.rows : rows.concat(data.rows);
  offset = rows.length;
  countEl.textContent = `${total.toLocaleString()} articles`;
  renderList();
  loading = false;
}

function renderList() {
  if (!rows.length) {
    listEl.innerHTML = '<div class="empty" style="padding:20px">nothing matches those filters</div>';
    return;
  }
  listEl.innerHTML = rows.map((r, i) => {
    const linkPill = r.n_links
      ? `<span class="pill linked">${r.n_links} link${r.n_links > 1 ? 's' : ''}${
           r.best_score != null ? ' · ' + r.best_score.toFixed(2) : ''}</span>`
      : `<span class="pill none">${escapeHtml(r.link_status || 'no link')}</span>`;
    return `<div class="row" data-i="${i}" data-uid="${r.textref_uid}"
                 aria-selected="${i === selected}">
      <div class="h">${escapeHtml(r.headline || '(no headline)')}</div>
      <div class="m">
        <span>${escapeHtml(r.date || '—')}</span>
        <span>${escapeHtml((r.source || '').slice(0, 38))}</span>
        ${linkPill}
        ${r.is_duplicate ? '<span class="pill">wire copy</span>' : ''}
      </div>
    </div>`;
  }).join('') + (rows.length < total
    ? `<div class="spinner" style="text-align:center;cursor:pointer" id="more">load ${
         Math.min(PAGE, total - rows.length)} more of ${total.toLocaleString()}…</div>` : '');

  listEl.querySelectorAll('.row').forEach(el => {
    el.onclick = () => select(+el.dataset.i);
  });
  const more = document.getElementById('more');
  if (more) more.onclick = () => load(false);
}

async function select(i) {
  if (i < 0 || i >= rows.length) return;
  selected = i;
  listEl.querySelectorAll('.row').forEach(el => {
    el.setAttribute('aria-selected', +el.dataset.i === i);
  });
  const row = listEl.querySelector(`.row[data-i="${i}"]`);
  if (row) row.scrollIntoView({block: 'nearest'});
  const uid = rows[i].textref_uid;
  history.replaceState(null, '', '#' + uid);
  detailEl.innerHTML = '<div class="spinner">loading article…</div>';
  const article = await (await fetch('/api/article/' + uid)).json();
  renderDetail(article);
}

// Highlight every name the linker matched, longest first so "Cave City" wins
// over "Cave". This is the whole point of the view: see what the score was
// built from rather than infer it.
function highlight(text, names) {
  let html = escapeHtml(text);
  if (!names || !names.length) return html;
  const pattern = names
    .filter(n => n && n.length > 2)
    .map(n => n.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
    .join('|');
  if (!pattern) return html;
  return html.replace(new RegExp(`\\b(${pattern})\\b`, 'gi'), '<mark>$1</mark>');
}

const FIELD_ORDER = ['source', 'pub_date', 'pub_date_raw', 'weekday', 'pub_time', 'byline',
  'dateline', 'section', 'edition', 'highlight', 'length_words', 'n_words', 'n_paragraphs',
  'subject', 'company', 'industry', 'geographic', 'graphic', 'notes', 'load_date',
  'copyright', 'meta', 'warnings', 'dup_group', 'is_duplicate', 'file'];

function renderDetail(a) {
  currentArticle = a;
  const fields = FIELD_ORDER
    .filter(k => a.fields[k] !== null && a.fields[k] !== undefined && a.fields[k] !== '')
    .map(k => `<div class="field"><span class="k">${k}</span><span class="v">${
      escapeHtml(String(a.fields[k]).slice(0, 400))}</span></div>`).join('');

  const links = a.links.length ? a.links.map((l, i) => linkCard(l, i)).join('')
    : `<p class="empty">No candidate links. Status: <b>${escapeHtml(a.link_status || '—')}</b>${
        a.n_candidate_episodes != null
          ? ` — ${a.n_candidate_episodes} episodes were in the date window` : ''}.</p>`;

  detailEl.innerHTML = `
    <h2>${escapeHtml(a.headline || '(no headline)')}</h2>
    <div class="meta">${escapeHtml(a.source || '')} · ${escapeHtml(a.date || 'no date')}
      · <span title="link status">${escapeHtml(a.link_status || '')}</span></div>

    ${a.links.length ? `
      <div class="section-title">Where the linked event happened</div>
      <div class="map-wrap">
        <div id="map"></div>
        <div class="map-bar">
          <span id="map-caption">—</span>
          <span class="map-actions">
            <button id="map-fit" title="Zoom back to the whole event">fit event</button>
            <label><input type="checkbox" id="map-basemap" checked> basemap</label>
          </span>
        </div>
      </div>` : ''}

    <div class="section-title">Linked events (${a.links.length})</div>
    ${links}

    <div class="section-title">Article fields</div>
    <div class="fields">${fields}</div>

    <div class="section-title">Body — matched place names highlighted</div>
    <div class="body">${a.paragraphs.map(p => `<p>${highlight(p, a.highlights)}</p>`).join('')}</div>`;

  detailEl.querySelectorAll('.link-card').forEach(card => {
    card.onclick = () => showOnMap(+card.dataset.i);
  });
  if (a.links.length) {
    ensureMap();
    showOnMap(0);                       // the describes link, i.e. the best one
  }
}

function chip(label, value) {
  if (value === null || value === undefined || value === '') return '';
  const state = value === true ? 'yes' : value === false ? 'no' : '';
  const text = typeof value === 'boolean' ? label : `${label} ${value}`;
  return `<span class="chip ${state}">${escapeHtml(text)}</span>`;
}

function linkCard(l, i) {
  const e = l.event || {};
  const ev = l.evidence || {};
  return `<div class="link-card ${l.link_relation}" data-i="${i}" title="Show this event on the map">
    <div>
      <div class="link-head">
        <span class="rel">${escapeHtml(l.link_relation)}</span>
        <span class="pill">${escapeHtml(l.link_level)}</span>
        <span class="score">score ${Number(ev.link_score ?? 0).toFixed(3)}
          (place ${Number(ev.toponym_score ?? 0).toFixed(2)},
           corrob ${Number(ev.corroboration_score ?? 0).toFixed(2)})</span>
      </div>
      <div class="event-facts">
        <b>${escapeHtml(e.convective_day || '?')}</b> ·
        ${e.n_hazards ?? '?'} tornado(es) · max <b>${escapeHtml(e.max_efscale || '—')}</b> ·
        ${e.fatalities ?? 0} killed, ${e.injuries ?? 0} injured ·
        ${escapeHtml((e.states || []).join(', '))}
        <div>${escapeHtml((e.counties || []).slice(0, 6).join(' · '))}</div>
        <div style="color:var(--muted)">${escapeHtml((e.places || []).slice(0, 10).join(' · '))}</div>
      </div>
      <div class="evidence">
        ${chip('day offset', ev.day_offset)}
        ${chip('matches', ev.n_matches)}
        ${chip('EF agrees', ev.sig_ef_match)}
        ${chip('deaths agree', ev.sig_fatalities_match)}
        ${chip('date agrees', ev.sig_date_match)}
        ${chip('local outlet', ev.sig_source_locality)}
        ${ev.from_retrospective_pass ? chip('retrospective pass', true) : ''}
        ${ev.from_year_only_pass ? chip('year-only pass', true) : ''}
        ${l.hazard_uid ? chip('single tornado', true) : ''}
      </div>
      <div class="evidence" style="margin-top:4px">
        ${String(ev.matched_names || '').split(';').filter(Boolean).slice(0, 10)
          .map(m => `<span class="chip">${escapeHtml(m)}</span>`).join('')}
      </div>
    </div>
  </div>`;
}

// ── the map ──
// One Leaflet instance reused across links: a dozen live maps on one page is a
// dozen tile budgets and a lot of memory, and only one is ever being read.
const episodeCache = new Map();
let map = null, basemap = null, eventLayer = null, currentArticle = null, mapIndex = -1;

function ensureMap() {
  const host = document.getElementById('map');
  if (!host) return null;
  if (map) { map.remove(); map = null; }      // the container is rebuilt per article
  map = L.map(host, {scrollWheelZoom: true, zoomControl: true});
  // OpenStreetMap standard tiles. Attribution is required by the ODbL licence
  // and must stay visible.
  basemap = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map);
  map.setView([39.5, -95], 4);
  document.getElementById('map-fit').onclick = () => fitEvent();
  document.getElementById('map-basemap').onchange = event => {
    if (event.target.checked) basemap.addTo(map); else map.removeLayer(basemap);
  };
  return map;
}

function trackPopup(p) {
  const rows = [
    ['rating', p.efscale],
    ['path length', p.path_length_mi != null ? p.path_length_mi.toFixed(1) + ' mi' : null],
    ['damage width', p.path_width_yd != null ? p.path_width_yd + ' yd' : null],
    ['killed / injured', `${p.fatalities ?? 0} / ${p.injuries ?? 0}`],
    ['began', p.time_begin_utc ? String(p.time_begin_utc).replace('T', ' ').slice(0, 16) + ' UTC' : null],
    ['nearest place', p.nearest_place],
    ['counties', p.counties ? String(p.counties).split(';').slice(0, 4).join(', ') : null],
    ['office', p.wfo],
  ].filter(([, v]) => v !== null && v !== undefined && v !== '');
  return `<b>${escapeHtml(p.efscale || 'unrated')} tornado</b><br>` +
    rows.map(([k, v]) => `<span style="color:#666">${k}:</span> ${escapeHtml(String(v))}`).join('<br>');
}

async function showOnMap(i) {
  const article = currentArticle;
  if (!article || !article.links[i]) return;
  mapIndex = i;
  detailEl.querySelectorAll('.link-card').forEach(card => {
    card.classList.toggle('active', +card.dataset.i === i);
  });
  const link = article.links[i];
  if (!link.episode_uid || !map) return;

  let data = episodeCache.get(link.episode_uid);
  if (!data) {
    data = await (await fetch('/api/episode/' + link.episode_uid)).json();
    episodeCache.set(link.episode_uid, data);
  }
  if (eventLayer) { map.removeLayer(eventLayer); eventLayer = null; }

  const focusHazard = link.hazard_uid;
  eventLayer = L.geoJSON(data.geojson, {
    style: feature => {
      const p = feature.properties;
      // A hazard-level link names one tornado; the rest of the outbreak stays on
      // the map as context but recedes, so the claim being judged is obvious.
      const focused = !focusHazard || p.hazard_uid === focusHazard;
      return {color: p.colour, weight: focused ? 4 : 2.5,
              opacity: focused ? 0.95 : 0.35, fillOpacity: focused ? 0.25 : 0.1};
    },
    onEachFeature: (feature, layer) => {
      layer.bindPopup(trackPopup(feature.properties));
      layer.on('mouseover', () => layer.setStyle({weight: 6}));
      layer.on('mouseout', () => eventLayer.resetStyle(layer));
    },
  }).addTo(map);

  fitEvent();
  const e = link.event || {};
  document.getElementById('map-caption').innerHTML =
    `<b>${escapeHtml(e.convective_day || '?')}</b> · ${data.n_features} track(s) drawn` +
    (focusHazard ? ' · <b>one tornado highlighted</b>' : '') +
    ` · ${escapeHtml((e.states || []).join(', '))}`;
}

function fitEvent() {
  if (!map || !eventLayer) return;
  const bounds = eventLayer.getBounds();
  if (bounds.isValid()) map.fitBounds(bounds, {padding: [24, 24], maxZoom: 13});
}

// ── controls ──
let debounce;
controls.q.oninput = () => { clearTimeout(debounce); debounce = setTimeout(() => load(), 220); };
for (const key of ['year', 'status', 'relation', 'has_links', 'min_score']) {
  controls[key].onchange = () => load();
}
document.addEventListener('keydown', event => {
  if (event.target.tagName === 'INPUT' || event.target.tagName === 'SELECT') {
    if (event.key === 'Escape') event.target.blur();
    return;
  }
  if (event.key === 'j' || event.key === 'ArrowDown') { event.preventDefault(); select(selected + 1); }
  if (event.key === 'k' || event.key === 'ArrowUp') { event.preventDefault(); select(selected - 1); }
  if (event.key === '/') { event.preventDefault(); controls.q.focus(); }
});

// Deep link: #<uid> opens that article directly.
async function start() {
  await load();
  const uid = location.hash.slice(1);
  if (uid) {
    const i = rows.findIndex(r => r.textref_uid === uid);
    if (i >= 0) { select(i); return; }
    const article = await (await fetch('/api/article/' + uid)).json();
    if (!article.error) renderDetail(article);
  }
}
start();

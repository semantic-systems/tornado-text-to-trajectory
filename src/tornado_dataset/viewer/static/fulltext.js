'use strict';

const listEl = document.getElementById('list');
const detailEl = document.getElementById('detail');
const countEl = document.getElementById('count');
const keysEl = document.getElementById('keys');
const FILTERS = ['q', 'quality', 'ft', 'compare', 'via', 'year_band', 'shared', 'inspected'];
const controls = Object.fromEntries(FILTERS.map(k => [k, document.getElementById(k)]));

let rows = [];
let selected = -1;
let total = 0;
let loading = false;
let current = null;          // the article on screen
let viaRandom = false;       // was it drawn with `r`? recorded with the verdict
let modelView = false;       // body as the model saw it, or the whole text
let mentionCursor = -1;
const PAGE = 60;

// The labeller's tornado vocabulary (lexisnexis_filter.TORNADO_RE), so what is
// highlighted is what the evidence windows were centred on.
const TORNADO_RE = /\b(tornad\w*|twisters?|funnel clouds?|waterspouts?|ef-? ?[0-5])\b/gi;

const escapeHtml = s => String(s ?? '').replace(/[&<>"']/g,
  c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const fmt = v => (v === null || v === undefined) ? '—'
  : (typeof v === 'number' && !Number.isInteger(v)) ? v.toFixed(2) : String(v);

function params(extra = {}) {
  const p = new URLSearchParams();
  for (const [k, el] of Object.entries(controls)) if (el.value) p.set(k, el.value);
  for (const [k, v] of Object.entries(extra)) p.set(k, v);
  return p;
}
const filterString = () => params().toString();

async function load(reset = true) {
  if (loading) return;
  loading = true;
  if (reset) { rows = []; selected = -1; listEl.innerHTML = '<div class="spinner">loading…</div>'; }
  const data = await (await fetch('/api/articles?' + params({offset: rows.length, limit: PAGE}))).json();
  total = data.total;
  rows = rows.concat(data.rows);
  countEl.textContent = `${total.toLocaleString()} articles`;
  renderList();
  loading = false;
}

function pills(r) {
  const out = [];
  out.push(r.quality_ok ? '<span class="pill ok">quality ok</span>'
    : `<span class="pill bad">${escapeHtml(r.hard.join(', ') || 'quality unknown')}</span>`);
  if (r.ft) {
    out.push(r.ft === r.hl
      ? `<span class="pill">${escapeHtml(r.ft)}</span>`
      : `<span class="pill diff">${escapeHtml(r.hl)} → ${escapeHtml(r.ft)}</span>`);
  }
  if (r.shared) out.push(`<span class="pill">body ×${r.shared}</span>`);
  if (r.verdict) out.push(`<span class="pill done">✓ ${escapeHtml(r.verdict)}</span>`);
  return out.join('');
}

function renderList() {
  if (!rows.length) {
    listEl.innerHTML = '<div class="empty" style="padding:20px">nothing matches those filters</div>';
    return;
  }
  listEl.innerHTML = rows.map((r, i) => `
    <div class="row" data-i="${i}" aria-selected="${i === selected}">
      <div class="h">${escapeHtml(r.headline || '(no headline)')}</div>
      <div class="m"><span>${escapeHtml(r.date)}</span>
        <span>${escapeHtml((r.source || '').slice(0, 34))}</span>${pills(r)}</div>
    </div>`).join('') + (rows.length < total
      ? `<div class="spinner" style="text-align:center;cursor:pointer" id="more">load ${
          Math.min(PAGE, total - rows.length)} more of ${total.toLocaleString()}…</div>` : '');
  listEl.querySelectorAll('.row').forEach(el => { el.onclick = () => select(+el.dataset.i); });
  const more = document.getElementById('more');
  if (more) more.onclick = () => load(false);
}

async function select(i) {
  if (i < 0 || i >= rows.length) return;
  selected = i;
  viaRandom = false;
  listEl.querySelectorAll('.row').forEach(el => el.setAttribute('aria-selected', +el.dataset.i === i));
  const el = listEl.querySelector(`.row[data-i="${i}"]`);
  if (el) el.scrollIntoView({block: 'nearest'});
  await show(rows[i].id);
}

async function show(id) {
  history.replaceState(null, '', '#' + id);
  detailEl.innerHTML = '<div class="spinner">loading article…</div>';
  const a = await (await fetch('/api/article/' + id)).json();
  current = a;
  mentionCursor = -1;
  renderDetail();
}

async function randomPick() {
  const data = await (await fetch('/api/articles?' + params({random: 1}))).json();
  if (data.random === null || data.random === undefined) return;
  await show(data.random);
  viaRandom = true;
  renderVerdict();
  listEl.querySelectorAll('.row').forEach(el => el.setAttribute('aria-selected', false));
}

function labelCard(who, l, other) {
  if (!l) return `<div class="label-card"><div class="who">${who}</div>
    <div class="what muted">not labelled</div></div>`;
  const differs = other && other.primary && other.primary !== l.primary;
  return `<div class="label-card ${differs ? 'differs' : ''}">
    <div class="who">${who}</div>
    <div class="what">${escapeHtml(l.primary)}
      <span class="muted" style="font-weight:400;font-size:13px">conf ${fmt(l.conf)}</span></div>
    <div class="flaglist">${l.flags.length ? l.flags.map(f => `<span class="chip yes">${f}</span>`).join('')
      : '<span class="chip">no flags</span>'}</div></div>`;
}

function bodyHtml() {
  const text = modelView ? current.evidence : current.text;
  return text.split(/\n+/).filter(p => p.trim()).map(p =>
    `<p>${escapeHtml(p).replace(TORNADO_RE, '<mark>$1</mark>')}</p>`).join('');
}

function renderDetail() {
  const a = current;
  const hard = Object.entries(a.quality_flags).filter(([, v]) => v).map(([k]) => k);
  const m = a.measures;
  const sib = a.n_siblings ? `
    <div class="section-title">same body under ${a.n_siblings.toLocaleString()} other headline${
      a.n_siblings > 1 ? 's' : ''}${a.n_siblings > 12 ? ' — first 12 shown' : ''}</div>
    ${a.siblings.slice(0, 12).map(s => `<div class="field"><span class="k">${escapeHtml(s.date)}</span>
      <span class="v"><a href="#" data-show="${s.id}">${escapeHtml(s.headline)}</a>
      <span class="muted">· ${escapeHtml(s.source)}${s.hl ? ' · headline ' + escapeHtml(s.hl) : ''}</span></span></div>`).join('')}` : '';

  detailEl.innerHTML = `
    <h2>${escapeHtml(a.headline)}</h2>
    <div class="meta">${escapeHtml(a.source)} · ${escapeHtml(a.date)} · ${escapeHtml(a.year_band)} ·
      ${escapeHtml(a.domain_size)} outlet · retrieved via <b>${escapeHtml(a.via)}</b></div>
    <div class="toolbar">
      <a href="${escapeHtml(a.url)}" target="_blank" rel="noopener noreferrer">original ↗</a>
      <a href="${escapeHtml(a.archive_url)}" target="_blank" rel="noopener noreferrer">archive copy ↗</a>
      ${a.final_url && a.final_url !== a.url ? `<span class="muted">landed on ${escapeHtml(a.final_url.slice(0, 90))}</span>` : ''}
    </div>

    <div class="labels">
      ${labelCard('headline only — stage 30', a.headline_label, a.fulltext_label)}
      ${labelCard('full text — stage 34', a.fulltext_label, a.headline_label)}
    </div>

    <div id="verdict"></div>

    <div class="section-title">is this the article? — stage 33 quality</div>
    <div class="flaglist" style="margin-bottom:8px">
      ${Object.entries(a.quality_flags).map(([k, v]) =>
        `<span class="chip ${!v ? 'no' : a.hard.includes(k) ? 'bad' : 'yes'}"
               title="${a.hard.includes(k) || !v ? '' : 'soft flag: informational'}">${k}</span>`).join('')}
    </div>
    <div class="muted" style="font-size:12.5px;margin-bottom:8px">
      ${a.quality_ok ? 'Passes every hard check.' : 'Fails a hard check — excluded from stage 34 labelling.'}
      Struck-through flags did not fire; orange ones are hard failures, blue ones soft.
    </div>
    <div class="fields">
      <div class="field"><span class="k">page title</span><span class="v">${escapeHtml(a.page_title || '—')}</span></div>
      <div class="field"><span class="k">title overlap</span><span class="v">${fmt(m.title_containment)}</span></div>
      <div class="field"><span class="k">words</span><span class="v">${fmt(m.n_words)}</span></div>
      <div class="field"><span class="k">tornado mentions</span><span class="v">${fmt(m.n_mentions)}</span></div>
      <div class="field"><span class="k">English stopwords</span><span class="v">${fmt(m.stopword_share)}</span></div>
      <div class="field"><span class="k">boilerplate share</span><span class="v">${fmt(m.boilerplate_share)}</span></div>
      <div class="field"><span class="k">states named</span><span class="v">${fmt(m.n_states)}</span></div>
      <div class="field"><span class="k">protected (rule)</span><span class="v">${fmt(m.protected)}</span></div>
    </div>
    ${sib}

    <div class="section-title">${modelView ? 'what the model saw' : 'full text'}
      <span style="text-transform:none;letter-spacing:0">· <a href="#" id="toggle">${
        modelView ? 'show full text' : 'show what the model saw'}</a> (v)</span></div>
    ${modelView ? `<div class="mode-note">Lede plus ±40 words around up to six tornado mentions,
      exactly as rendered into stage 32's prompt; […] marks omitted text.</div>` : ''}
    <div class="body">${bodyHtml()}</div>`;

  detailEl.querySelectorAll('[data-show]').forEach(el => {
    el.onclick = e => { e.preventDefault(); viaRandom = false; show(+el.dataset.show); };
  });
  document.getElementById('toggle').onclick = e => { e.preventDefault(); toggleView(); };
  renderVerdict();
  detailEl.scrollTop = 0;
}

function renderVerdict() {
  const box = document.getElementById('verdict');
  if (!box || !current) return;
  const v = current.inspection || {};
  const b = (field, value, key, text) =>
    `<button data-f="${field}" data-v="${value}" aria-pressed="${v[field] === value}"
             title="${key}">${text} <kbd>${key}</kbd></button>`;
  box.innerHTML = `<div class="verdict">
    <div class="group"><span class="muted">body</span>
      ${b('body_verdict', 'right_article', '1', 'right article')}
      ${b('body_verdict', 'wrong_page', '2', 'wrong page')}
      ${b('body_verdict', 'partial', '3', 'partial')}</div>
    <span class="sep"></span>
    <div class="group"><span class="muted">your label</span>
      ${b('label', 'EVENT', 'e', 'EVENT')}
      ${b('label', 'PROSPECTIVE', 'p', 'PROSP.')}
      ${b('label', 'NOT_TORNADO_EVENT', 'n', 'NOT')}
      ${b('label', 'UNCLEAR', 'u', 'UNCLEAR')}</div>
    <input type="text" id="note" placeholder="note (optional, saved on Enter)" value="${escapeHtml(v.note || '')}">
    <span class="saved">${v.inspected_at ? 'saved ' + escapeHtml(new Date(v.inspected_at).toLocaleString())
      + (v.via_random ? ' · random draw' : '') : (viaRandom ? 'random draw — unsaved' : 'not yet inspected')}</span>
  </div>`;
  box.querySelectorAll('button[data-f]').forEach(el => {
    el.onclick = () => save({[el.dataset.f]: el.dataset.v});
  });
  const note = document.getElementById('note');
  note.onkeydown = e => {
    if (e.key === 'Enter') { save({note: note.value}); note.blur(); }
    if (e.key === 'Escape') note.blur();
    e.stopPropagation();
  };
}

async function save(fields) {
  if (!current) return;
  const payload = {id: current.id, ...fields, filter: filterString()};
  // A verdict counts as randomly drawn only if *this* article came from `r`;
  // an earlier random flag is kept by the server, never set retroactively.
  if (viaRandom) payload.via_random = true;
  const res = await fetch('/api/verdict', {method: 'POST',
    headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)});
  const row = await res.json();
  if (row.error) { alert(row.error); return; }
  current.inspection = row;
  const listed = rows.find(r => r.id === current.id);
  if (listed) { listed.verdict = row.label || row.body_verdict; renderList(); }
  renderVerdict();
}

function toggleView() {
  if (!current) return;
  modelView = !modelView;
  renderDetail();
}

function nextMention() {
  const marks = detailEl.querySelectorAll('.body mark');
  if (!marks.length) return;
  marks.forEach(m => m.classList.remove('current'));
  mentionCursor = (mentionCursor + 1) % marks.length;
  marks[mentionCursor].classList.add('current');
  marks[mentionCursor].scrollIntoView({block: 'center'});
}

const KEYMAP = {
  '1': {body_verdict: 'right_article'}, '2': {body_verdict: 'wrong_page'},
  '3': {body_verdict: 'partial'},
  'e': {label: 'EVENT'}, 'p': {label: 'PROSPECTIVE'},
  'n': {label: 'NOT_TORNADO_EVENT'}, 'u': {label: 'UNCLEAR'},
};

document.addEventListener('keydown', e => {
  if (!keysEl.hidden) { keysEl.hidden = true; e.preventDefault(); return; }
  const t = e.target;
  if (t.tagName === 'INPUT' || t.tagName === 'SELECT' || t.tagName === 'TEXTAREA') {
    if (e.key === 'Escape') t.blur();
    return;
  }
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  if (e.key === 'j') select(Math.min(selected + 1, rows.length - 1));
  else if (e.key === 'k') select(Math.max(selected - 1, 0));
  else if (e.key === 'r') randomPick();
  else if (e.key === 'v') toggleView();
  else if (e.key === 'm') nextMention();
  else if (e.key === '/') { e.preventDefault(); controls.q.focus(); }
  else if (e.key === '?') keysEl.hidden = false;
  else if (e.key === 'o' && current) window.open(current.url, '_blank', 'noopener');
  else if (e.key === 'a' && current) window.open(current.archive_url, '_blank', 'noopener');
  else if (KEYMAP[e.key] && current) save(KEYMAP[e.key]);
  else return;
  e.preventDefault();
});
keysEl.onclick = () => { keysEl.hidden = true; };

let debounce;
for (const el of Object.values(controls)) {
  el.addEventListener(el.tagName === 'INPUT' ? 'input' : 'change', () => {
    clearTimeout(debounce);
    debounce = setTimeout(() => load(true), el.tagName === 'INPUT' ? 250 : 0);
  });
}
document.getElementById('random').onclick = randomPick;

load(true).then(() => {
  const id = parseInt(location.hash.slice(1), 10);
  if (!Number.isNaN(id)) show(id);
});

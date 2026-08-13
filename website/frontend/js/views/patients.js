/* HELIXA — patient cohort table with global filters */
import { loadAll, filterPatients, fmtNum } from '../api.js';
import { h, card, section, badge, esc } from '../ui.js';
import { donut, barsV, legend } from '../charts.js';

const PAGE = 25;

export default async function patients({ query }) {
  const [clusters, all] = await loadAll(['clusters', 'patients']);
  const cmap = Object.fromEntries(clusters.map(c => [c.id, c]));

  const f = { clusters: [], q: '', confidence: '', batch: '', verhaak: '' };
  const pre = query.get('cluster');
  if (pre != null && pre !== '') f.clusters = [Number(pre)];

  let sortKey = 'consensus_membership', sortDir = -1, page = 1;

  const root = h('div', { class: 'wrap section' });
  root.appendChild(section('Cohort', 'Patients',
    `${all.length} glioblastoma patients from the TCGA/GDC cohort, each assigned by consensus ` +
    `clustering with a per-patient confidence value.`));

  const kpiHost = h('div', { class: 'grid g4', style: { marginBottom: '20px' } });
  const chartHost = h('div', { class: 'grid g2', style: { marginBottom: '20px' } });
  const tblHost = h('div');
  const pagHost = h('div', { style: { display: 'flex', gap: '9px', alignItems: 'center',
    justifyContent: 'space-between', marginTop: '16px', flexWrap: 'wrap' } });

  /* ── filter bar ─────────────────────────────────────────────── */
  const search = h('input', { class: 'inp', placeholder: 'Search patient ID, sample UUID, subtype…',
    oninput: e => { f.q = e.target.value; page = 1; draw(); } });
  const selConf = h('select', { class: 'inp', onchange: e => { f.confidence = e.target.value; page = 1; draw(); } },
    h('option', { value: '' }, 'All confidence levels'),
    h('option', { value: 'core' }, 'High-confidence (core) only'),
    h('option', { value: 'boundary' }, 'Boundary tumours only'));
  const selBatch = h('select', { class: 'inp', onchange: e => { f.batch = e.target.value; page = 1; draw(); } },
    h('option', { value: '' }, 'All library protocols'),
    ...[...new Set(all.map(p => p.library_batch))].map(b => h('option', { value: b }, b)));
  const selVer = h('select', { class: 'inp', onchange: e => { f.verhaak = e.target.value; page = 1; draw(); } },
    h('option', { value: '' }, 'All Verhaak identities'),
    ...[...new Set(all.map(p => p.verhaak_nearest))].filter(Boolean).sort()
      .map(v => h('option', { value: v }, v)));

  const chipRow = h('div', { style: { display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '13px' } },
    clusters.map(c => h('button', { class: 'chip' + (f.clusters.includes(c.id) ? ' on' : ''),
      'data-c': c.id, type: 'button',
      onclick: () => { f.clusters = f.clusters.includes(c.id)
          ? f.clusters.filter(x => x !== c.id) : [...f.clusters, c.id];
        chipRow.querySelectorAll('[data-c]').forEach(b =>
          b.classList.toggle('on', f.clusters.includes(+b.dataset.c)));
        page = 1; draw(); } },
      h('span', { class: 'dot', style: { background: c.color } }), `${c.label} · ${c.n_patients}`)),
    h('button', { class: 'chip', type: 'button', onclick: () => {
      f.clusters = []; f.q = ''; f.confidence = ''; f.batch = ''; f.verhaak = '';
      search.value = ''; selConf.value = ''; selBatch.value = ''; selVer.value = '';
      chipRow.querySelectorAll('[data-c]').forEach(b => b.classList.remove('on'));
      page = 1; draw(); } }, 'Clear all filters'));

  root.appendChild(card('Filters', 'Every statistic, chart and row below updates together',
    h('div', {},
      h('div', { class: 'grid g4', style: { gap: '11px' } }, search, selConf, selBatch, selVer),
      chipRow)));
  root.appendChild(h('div', { style: { height: '20px' } }));
  root.appendChild(kpiHost);
  root.appendChild(chartHost);
  root.appendChild(tblHost);
  root.appendChild(pagHost);

  /* ── draw ───────────────────────────────────────────────────── */
  function draw() {
    const rows = filterPatients(all, f);
    const core = rows.filter(p => p.is_core).length;
    const mm = rows.reduce((a, p) => a + (p.consensus_membership || 0), 0) / (rows.length || 1);

    kpiHost.replaceChildren(
      kpi(String(rows.length), 'Patients matching'),
      kpi(`${core}`, 'High-confidence', rows.length ? `${(core / rows.length * 100).toFixed(1)}%` : ''),
      kpi(`${rows.length - core}`, 'Boundary tumours'),
      kpi(fmtNum(mm, 3), 'Mean consensus'));

    const byC = clusters.map(c => ({ label: c.title, value: rows.filter(p => p.cluster === c.id).length,
      color: c.color }));
    const byV = [...new Set(rows.map(p => p.verhaak_nearest))].filter(Boolean).map((v, i) => ({
      label: v, value: rows.filter(p => p.verhaak_nearest === v).length,
      color: ['#0EAE8F', '#F0883E', '#2A9D8F', '#C79A2C'][i % 4] }));

    chartHost.replaceChildren(
      card('Subtype distribution', 'Within the current filter',
        h('div', { style: { display: 'grid', placeItems: 'center' } },
          donut(byC.filter(d => d.value > 0), { size: 214, thick: 30,
            center: { value: String(rows.length), label: 'patients' } }),
          legend(byC.filter(d => d.value > 0).map(d => ({ label: `${d.label} (${d.value})`, color: d.color }))))),
      card('Nearest Verhaak identity', 'Independent literature signature, per patient',
        barsV(byV, { w: 520, h: 246 })));

    /* table */
    const sorted = [...rows].sort((a, b) => {
      const x = a[sortKey], y = b[sortKey];
      if (typeof x === 'string') return sortDir * x.localeCompare(y);
      return sortDir * ((x ?? -Infinity) - (y ?? -Infinity));
    });
    const pages = Math.max(1, Math.ceil(sorted.length / PAGE));
    page = Math.min(page, pages);
    const slice = sorted.slice((page - 1) * PAGE, page * PAGE);

    const th = (key, label) => h('th', { class: 'srt',
      onclick: () => { if (sortKey === key) sortDir *= -1; else { sortKey = key; sortDir = -1; } draw(); } },
      label + (sortKey === key ? (sortDir === -1 ? ' ↓' : ' ↑') : ''));

    tblHost.replaceChildren(h('div', { class: 'tbl-wrap' },
      h('table', {},
        h('thead', {}, h('tr', {},
          th('id', 'Patient ID'), th('short_id', 'Sample'), th('cluster', 'Subtype'),
          th('consensus_membership', 'Consensus'), th('silhouette', 'Silhouette'),
          th('verhaak_nearest', 'Verhaak'), th('is_core', 'Status'), h('th', {}, ''))),
        h('tbody', {}, slice.length ? slice.map(p => {
          const c = cmap[p.cluster];
          return h('tr', { class: 'clk', onclick: () => location.hash = `#/patient/${p.id}` },
            h('td', { class: 'mono', style: { fontWeight: '600' } }, p.id),
            h('td', { class: 'mono', style: { color: 'var(--ink-3)' } }, p.short_id),
            h('td', {}, h('div', { style: { display: 'flex', alignItems: 'center', gap: '8px' } },
              h('span', { style: { width: '9px', height: '9px', borderRadius: '3px',
                background: c.color, flexShrink: '0' } }), c.label)),
            h('td', { class: 'mono' }, fmtNum(p.consensus_membership, 3)),
            h('td', { class: 'mono' }, fmtNum(p.silhouette, 4)),
            h('td', { style: { fontSize: '12.5px' } }, p.verhaak_nearest || '—'),
            h('td', {}, p.is_core ? badge('ok', 'core') : badge('warn', 'boundary')),
            h('td', { style: { textAlign: 'right', color: 'var(--ink-3)' } }, '›'));
        }) : [h('tr', {}, h('td', { colspan: '8', style: { textAlign: 'center', padding: '40px',
          color: 'var(--ink-3)' } }, 'No patients match these filters.'))]))));

    pagHost.replaceChildren(
      h('div', { style: { fontSize: '13px', color: 'var(--ink-3)' } },
        rows.length ? `Showing ${(page - 1) * PAGE + 1}–${Math.min(page * PAGE, sorted.length)} of ${sorted.length}` : ''),
      h('div', { style: { display: 'flex', gap: '7px' } },
        h('button', { class: 'btn btn-sm btn-s', disabled: page <= 1,
          onclick: () => { page--; draw(); } }, '‹ Previous'),
        h('span', { style: { padding: '8px 13px', fontSize: '13px', color: 'var(--ink-2)' } },
          `Page ${page} / ${pages}`),
        h('button', { class: 'btn btn-sm btn-s', disabled: page >= pages,
          onclick: () => { page++; draw(); } }, 'Next ›')));
  }

  draw();
  return root;
}

function kpi(v, l, s) {
  return h('div', { class: 'card' },
    h('div', { class: 'stat-v', style: { fontSize: '27px' } }, v),
    h('div', { class: 'stat-l' }, l),
    s ? h('div', { class: 'stat-sub' }, s) : null);
}

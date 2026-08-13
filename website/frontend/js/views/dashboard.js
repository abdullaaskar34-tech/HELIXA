/* HELIXA — dashboard */
import { loadAll, state, fmtPct, fmtInt, fmtNum } from '../api.js';
import { h, card, stat, section, badge, banner, kv, esc } from '../ui.js';
import { donut, barsH, barsV, scatter, legend, gauge, PALETTE } from '../charts.js';

export default async function dashboard() {
  const [clusters, patients, metrics, model, emb, ext] =
    await loadAll(['clusters', 'patients', 'global_metrics', 'model', 'embedding', 'external_validation']);

  const root = h('div', { class: 'wrap section' });
  const cmap = Object.fromEntries(clusters.map(c => [c.id, c]));
  let active = new Set();               // cluster filter

  root.appendChild(section('Overview', 'Cohort Dashboard',
    `${metrics.n_patients} glioblastoma patients · ${metrics.n_clusters} molecular subtypes · ` +
    `every figure on this page is computed from the project's real output files.`));

  /* KPI row */
  root.appendChild(h('div', { class: 'grid g4', style: { marginBottom: '20px' } },
    stat(fmtInt(metrics.n_patients), 'Total patients', 'TCGA / GDC cohort', { hover: true }),
    stat(fmtInt(metrics.n_core), 'High-confidence', `${metrics.pct_core}% of the cohort`, { hover: true }),
    stat(fmtInt(metrics.n_boundary), 'Boundary tumours',
      `${(100 - metrics.pct_core).toFixed(1)}% reported as intermediate`, { hover: true }),
    stat(String(metrics.n_clusters), 'Molecular subtypes', 'consensus k, PAC = ' + metrics.PAC_selected_k,
      { hover: true, dark: true })));

  /* live engine banner */
  const eng = h('div', { style: { marginBottom: '20px' } });
  const paint = () => eng.replaceChildren(state.live
    ? banner('ok', `<b>Live inference engine connected.</b> ${esc(state.engine.model_name)} · ` +
        `${(state.engine.cv_accuracy * 100).toFixed(2)}% cross-validated accuracy · ` +
        `<a href="#/analyze">Analyze a new patient →</a>`)
    : banner('info', `<b>Static science mode.</b> The Python inference API is not reachable from this ` +
        `browser, so live prediction is disabled. Everything shown on this page is the project's ` +
        `real recorded output. To enable live prediction, run the backend locally ` +
        `(<code>uvicorn app:app --port 8000</code>).`));
  paint(); document.addEventListener('helixa:api', paint, { once: true });
  root.appendChild(eng);

  /* ── distribution + map row ─────────────────────────────────── */
  const scatterHost = h('div');
  const distHost = h('div');
  const statsHost = h('div');

  function drawAll() {
    const sel = active.size ? [...active] : clusters.map(c => c.id);
    const dim = new Set(active.size ? clusters.filter(c => !active.has(c.id)).map(c => c.id) : []);

    distHost.replaceChildren(
      donut(clusters.map(c => ({
        label: c.title, value: c.n_patients, color: c.color,
        onClick: () => { toggle(c.id); },
      })), { size: 232, thick: 32,
        center: { value: String(sel.reduce((a, i) => a + cmap[i].n_patients, 0)), label: 'selected' } }),
      legend(clusters.map(c => ({ label: `${c.label} (${c.n_patients})`, color: c.color }))));

    scatterHost.replaceChildren(scatter(
      emb.points.map(p => ({ ...p, name: cmap[p.c].title })),
      { w: 660, h: 430, colors: clusters.map(c => c.color), dim,
        onPick: p => { const pt = patients.find(x => x.sample_id.startsWith(p.sid));
                       if (pt) location.hash = `#/patient/${pt.id}`; } }));

    const sub = patients.filter(p => !active.size || active.has(p.cluster));
    const core = sub.filter(p => p.is_core).length;
    const mm = sub.reduce((a, p) => a + (p.consensus_membership || 0), 0) / (sub.length || 1);
    const pa = sub.filter(p => p.library_batch.startsWith('polyA')).length;
    statsHost.replaceChildren(
      kv('Patients in selection', fmtInt(sub.length)),
      kv('High-confidence (core)', `${fmtInt(core)} · ${((core / (sub.length || 1)) * 100).toFixed(1)}%`),
      kv('Mean consensus membership', fmtNum(mm, 3)),
      kv('poly(A) / total-RNA libraries', `${pa} / ${sub.length - pa}`),
      kv('Subtypes shown', String(sel.length)));
  }
  function toggle(id) {
    active.has(id) ? active.delete(id) : active.add(id);
    root.querySelectorAll('[data-chip]').forEach(b =>
      b.classList.toggle('on', active.has(+b.dataset.chip)));
    drawAll();
  }

  const chipRow = h('div', { style: { display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '16px' } },
    clusters.map(c => h('button', { class: 'chip', 'data-chip': c.id, type: 'button',
      onclick: () => toggle(c.id) },
      h('span', { class: 'dot', style: { background: c.color } }), `${c.label} · ${c.n_patients}`)),
    h('button', { class: 'chip', type: 'button', onclick: () => { active.clear();
      root.querySelectorAll('[data-chip]').forEach(b => b.classList.remove('on')); drawAll(); } },
      'Reset'));

  root.appendChild(h('div', { style: { marginBottom: '8px' } },
    h('div', { class: 'card-t', style: { marginBottom: '10px' } },
      'Filter by subtype — every chart below responds')));
  root.appendChild(chipRow);

  root.appendChild(h('div', { class: 'grid', style: { gridTemplateColumns: '1.35fr 1fr', gap: '18px' } },
    card('Patient Map — principal component space',
      'Each point is one patient. Hollow points are boundary tumours. Click a point to open the profile.',
      scatterHost),
    h('div', { class: 'grid', style: { gap: '18px', alignContent: 'start' } },
      card('Subtype distribution', 'Click a segment to filter', distHost),
      card('Selection summary', null, statsHost))));

  drawAll();

  /* ── model + validation row ─────────────────────────────────── */
  const verdictColor = v => v.startsWith('CONFIRMED (strong') ? '#12855F'
    : v.startsWith('CONFIRMED') ? '#1BA37E' : v.startsWith('PARTIALLY') ? '#B57200' : '#C0392B';

  root.appendChild(h('div', { class: 'grid g3', style: { marginTop: '20px' } },
    card('Classifier performance', 'Cross-validated on the 273 high-confidence patients',
      h('div', {},
        gauge(model.metrics.cv_balanced_accuracy, { label: 'Balanced accuracy', size: 210 }),
        h('div', { style: { marginTop: '6px' } },
          kv('Leave-one-out accuracy', fmtPct(model.metrics.loo_accuracy, 2)),
          kv('ROC-AUC (macro, OvR)', model.metrics.roc_auc_ovr.toFixed(4)),
          kv('Cohen\'s κ', model.metrics.cohen_kappa.toFixed(4)),
          kv('Algorithm', model.metrics.best_model)))),
    card('Null test', 'Labels shuffled 300× and the model retrained',
      h('div', {},
        barsH([
          { label: 'Real model', value: model.robustness.perm_real, color: '#12855F' },
          { label: 'Shuffled labels', value: model.robustness.perm_null_mean, color: '#9FB6B2' },
          { label: 'Random guess (1/6)', value: 1 / 6, color: '#C2DED6' },
        ], { w: 420, rowH: 44, pad: { t: 6, r: 58, b: 24, l: 132 }, max: 1,
             fmt: v => (v * 100).toFixed(1) + '%' }),
        h('p', { class: 'card-d', style: { marginTop: '10px' } },
          `p = ${model.robustness.perm_p.toExponential(1)} — the performance is not chance.`))),
    card('Independent literature validation', '4 published sources, none used during clustering',
      h('div', {},
        ext.verdict.map(v => h('div', { class: 'kv' },
          h('span', { class: 'k' },
            h('span', { style: { display: 'inline-block', width: '9px', height: '9px', borderRadius: '3px',
              background: cmap[v.cluster].color, marginRight: '8px' } }),
            cmap[v.cluster].label),
          h('span', { class: 'v', style: { color: verdictColor(v.VERDICT), fontSize: '12px' } },
            `${v.mean_enrichment_over_chance}× · ${v.VERDICT.replace('CONFIRMED ', '').replace(/[()]/g, '')}`)))))));

  /* ── subtype table ──────────────────────────────────────────── */
  root.appendChild(h('div', { style: { marginTop: '34px' } },
    section(null, 'Subtype profiles', null),
    h('div', { class: 'tbl-wrap' },
      h('table', {},
        h('thead', {}, h('tr', {},
          ['Subtype', 'Patients', 'Core', 'Silhouette', 'Consensus', 'Verhaak identity', 'Pathway identity']
            .map(t => h('th', {}, t)))),
        h('tbody', {}, clusters.map(c => h('tr', { class: 'clk',
          onclick: () => location.hash = `#/patients?cluster=${c.id}` },
          h('td', {}, h('div', { style: { display: 'flex', alignItems: 'center', gap: '9px' } },
            h('span', { style: { width: '10px', height: '10px', borderRadius: '3px', background: c.color } }),
            h('div', {}, h('div', { style: { fontWeight: '640' } }, c.title),
              h('div', { style: { fontSize: '11.5px', color: 'var(--ink-3)' } }, c.name)))),
          h('td', { class: 'mono' }, String(c.n_patients)),
          h('td', { class: 'mono' }, `${c.n_core} / ${c.n_patients}`),
          h('td', { class: 'mono' }, c.mean_silhouette.toFixed(4)),
          h('td', { class: 'mono' }, c.mean_consensus_membership.toFixed(3)),
          h('td', {}, badge('mut', c.verhaak_identity)),
          h('td', {}, badge('info', c.pathway_identity.replace(/_/g, ' '))))))))));

  return root;
}

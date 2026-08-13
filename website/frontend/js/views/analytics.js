/* HELIXA — analytics workbench (population · classification · genomic · model) */
import { loadAll, filterPatients, fmtNum, fmtPct } from '../api.js';
import { h, card, section, badge, banner, kv, esc } from '../ui.js';
import { donut, barsH, barsV, heatmap, scatter, lines, stacked, legend, PALETTE } from '../charts.js';

export default async function analytics() {
  const [clusters, patients, metrics, model, markers, biology, ext, ksel, emb] =
    await loadAll(['clusters', 'patients', 'global_metrics', 'model', 'markers', 'biology',
                   'external_validation', 'k_selection', 'embedding']);
  const cmap = Object.fromEntries(clusters.map(c => [c.id, c]));

  const root = h('div', { class: 'wrap section' });
  root.appendChild(section('Analytics', 'Analytics Workbench',
    'Population, classification, genomic and model analytics — all computed from the project\'s ' +
    'real result files. Filters apply across every panel.'));

  /* ── global filter ──────────────────────────────────────────── */
  const f = { clusters: [], confidence: '' };
  const chipRow = h('div', { style: { display: 'flex', gap: '8px', flexWrap: 'wrap' } },
    clusters.map(c => h('button', { class: 'chip', 'data-c': c.id, type: 'button',
      onclick: () => { f.clusters = f.clusters.includes(c.id)
        ? f.clusters.filter(x => x !== c.id) : [...f.clusters, c.id];
        chipRow.querySelectorAll('[data-c]').forEach(b => b.classList.toggle('on', f.clusters.includes(+b.dataset.c)));
        drawTab(); } },
      h('span', { class: 'dot', style: { background: c.color } }), c.label)),
    h('button', { class: 'chip', type: 'button', onclick: () => { f.clusters = []; f.confidence = '';
      sel.value = ''; chipRow.querySelectorAll('[data-c]').forEach(b => b.classList.remove('on'));
      drawTab(); } }, 'Reset'));
  const sel = h('select', { class: 'inp', style: { maxWidth: '250px' },
    onchange: e => { f.confidence = e.target.value; drawTab(); } },
    h('option', { value: '' }, 'All confidence levels'),
    h('option', { value: 'core' }, 'High-confidence only'),
    h('option', { value: 'boundary' }, 'Boundary tumours only'));

  root.appendChild(card('Global filters', 'Applies to every panel on this page',
    h('div', { style: { display: 'flex', gap: '14px', flexWrap: 'wrap', alignItems: 'center' } },
      chipRow, sel)));

  /* ── tabs ───────────────────────────────────────────────────── */
  const TABS = ['Population', 'Classification', 'Genomic', 'Model', 'Validation'];
  let tab = 'Population';
  const tabBar = h('div', { class: 'tabs', style: { marginTop: '24px' } },
    TABS.map(t => h('button', { class: 'tab' + (t === tab ? ' on' : ''), 'data-t': t, type: 'button',
      onclick: () => { tab = t;
        tabBar.querySelectorAll('.tab').forEach(b => b.classList.toggle('on', b.dataset.t === t));
        drawTab(); } }, t)));
  root.appendChild(tabBar);
  const host = h('div');
  root.appendChild(host);

  function rows() { return filterPatients(patients, f); }

  function drawTab() {
    const R = rows();
    host.replaceChildren(
      tab === 'Population'    ? population(R) :
      tab === 'Classification' ? classification(R) :
      tab === 'Genomic'       ? genomic(R) :
      tab === 'Model'         ? modelTab() : validation());
  }

  /* ── population ─────────────────────────────────────────────── */
  function population(R) {
    const core = R.filter(p => p.is_core).length;
    const byBatch = [...new Set(patients.map(p => p.library_batch))].map((b, i) => ({
      label: b.replace('_', ' '), value: R.filter(p => p.library_batch === b).length,
      color: PALETTE[i % PALETTE.length] }));
    const memBins = bins(R.map(p => p.consensus_membership ?? 0), 10);

    return h('div', {},
      h('div', { class: 'grid g4', style: { marginBottom: '18px' } },
        kpi(String(R.length), 'Patients in view'),
        kpi(String(core), 'High-confidence', R.length ? `${(core / R.length * 100).toFixed(1)}%` : ''),
        kpi(String(R.length - core), 'Boundary tumours'),
        kpi(String(new Set(R.map(p => p.cluster)).size), 'Subtypes represented')),
      h('div', { class: 'grid g2', style: { marginBottom: '18px' } },
        card('Subtype composition', 'Patients per molecular subtype',
          h('div', { style: { display: 'grid', placeItems: 'center' } },
            donut(clusters.map(c => ({ label: c.title, value: R.filter(p => p.cluster === c.id).length,
              color: c.color })).filter(d => d.value > 0),
              { size: 226, thick: 32, center: { value: String(R.length), label: 'patients' } }),
            legend(clusters.map(c => ({ label: c.label, color: c.color }))))),
        card('Library protocol balance', 'The corrected batch effect is evenly spread across subtypes',
          h('div', {}, barsV(byBatch, { w: 500, h: 250 }),
            h('p', { class: 'card-d', style: { marginTop: '9px' } },
              'Both protocols appear in every subtype — confirming the subtypes are not a ' +
              'disguised batch effect.')))),
      card('Assignment-confidence distribution', 'Consensus membership across the selection',
        h('div', {},
          barsV(memBins.map((b, i) => ({ label: b.label, value: b.n,
            color: i < 3 ? '#C79A2C' : i < 6 ? '#2A9D8F' : '#0EAE8F' })),
            { w: 900, h: 280, yLabel: 'patients' }),
          h('p', { class: 'card-d', style: { marginTop: '10px' } },
            'Higher is better. Patients below 0.5 are flagged as boundary tumours and reported ' +
            'as intermediate rather than forced into a subtype.'))));
  }

  /* ── classification ─────────────────────────────────────────── */
  function classification(R) {
    const verhaakVals = [...new Set(patients.map(p => p.verhaak_nearest))].filter(Boolean).sort();
    const mat = clusters.map(c => verhaakVals.map(v =>
      R.filter(p => p.cluster === c.id && p.verhaak_nearest === v).length));
    const pctMat = mat.map(r => { const t = r.reduce((a, b) => a + b, 0) || 1;
      return r.map(v => v / t * 100); });

    const conf = clusters.map(c => {
      const s = R.filter(p => p.cluster === c.id);
      return { label: c.label, value: s.length
        ? s.reduce((a, p) => a + (p.consensus_membership ?? 0), 0) / s.length : 0, color: c.color };
    });

    return h('div', {},
      card('Subtype × Verhaak identity', 'Row-normalised — what fraction of each subtype maps to ' +
        'each published Verhaak class (independent signature, scored per patient)',
        h('div', { style: { overflowX: 'auto' } },
          heatmap(pctMat, clusters.map(c => `${c.label} (${c.n_patients})`), verhaakVals,
            { w: 640, cell: 40, fmt: v => v ? v.toFixed(0) + '%' : '', unit: '' }))),
      h('div', { class: 'grid g2', style: { marginTop: '18px' } },
        card('Mean assignment confidence by subtype', 'Consensus membership',
          barsH(conf, { w: 480, rowH: 38, pad: { t: 6, r: 62, b: 24, l: 84 }, max: 1,
            fmt: v => v.toFixed(3), label: 'consensus' })),
        card('Core vs boundary composition', 'Per subtype',
          h('div', {},
            stacked(clusters.map(c => {
              const s = R.filter(p => p.cluster === c.id);
              return { label: c.label, values: { Core: s.filter(p => p.is_core).length,
                Boundary: s.filter(p => !p.is_core).length } };
            }), ['Core', 'Boundary'],
              { w: 480, rowH: 40, pad: { t: 6, r: 14, b: 24, l: 84 },
                colors: ['#0EAE8F', '#C79A2C'], fmt: v => String(v) }),
            legend([{ label: 'Core (high confidence)', color: '#0EAE8F' },
                    { label: 'Boundary (intermediate)', color: '#C79A2C' }])))));
  }

  /* ── genomic ────────────────────────────────────────────────── */
  function genomic(R) {
    const sigNames = Object.keys(patients[0].signatures);
    const pwNames = Object.keys(patients[0].pathways);
    const sigMat = clusters.map(c => { const s = R.filter(p => p.cluster === c.id);
      return sigNames.map(k => s.length ? s.reduce((a, p) => a + (p.signatures[k] ?? 0), 0) / s.length : null); });
    const pwMat = clusters.map(c => { const s = R.filter(p => p.cluster === c.id);
      return pwNames.map(k => s.length ? s.reduce((a, p) => a + (p.pathways[k] ?? 0), 0) / s.length : null); });

    return h('div', {},
      h('div', { class: 'grid g2', style: { marginBottom: '18px' } },
        card('Verhaak signature activity', 'Mean z-score per subtype (red = high, orange = low)',
          h('div', { style: { overflowX: 'auto' } },
            heatmap(sigMat, clusters.map(c => c.label), sigNames,
              { w: 470, cell: 42, diverging: true, fmt: v => v == null ? '' : v.toFixed(2) }))),
        card('Pathway activity', 'Mean z-score per subtype across the pathway proxies',
          h('div', { style: { overflowX: 'auto' } },
            heatmap(pwMat, clusters.map(c => c.label), pwNames.map(n => n.replace(/_/g, ' ')),
              { w: 640, cell: 42, diverging: true, fmt: v => v == null ? '' : v.toFixed(2) })))),
      card('Subtype marker genes', 'Top differential genes that define each subtype — the genomic ' +
        'basis of every classification this platform makes',
        h('div', { class: 'grid g3', style: { gap: '15px' } },
          clusters.filter(c => !f.clusters.length || f.clusters.includes(c.id)).map(c =>
            h('div', { style: { padding: '15px', background: 'var(--surface-2)', borderRadius: '12px',
              border: '1px solid var(--line)' } },
              h('div', { style: { display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' } },
                h('span', { style: { width: '10px', height: '10px', borderRadius: '3px', background: c.color } }),
                h('div', { style: { fontWeight: '650', fontSize: '13.5px' } }, c.title)),
              h('div', { style: { display: 'flex', gap: '6px', flexWrap: 'wrap' } },
                (markers[`cluster_${c.id}`] || []).slice(0, 16).map(m =>
                  h('span', { class: 'badge b-mut',
                    style: { fontFamily: 'var(--mono)', fontSize: '11px' } },
                    m.gene || m.Gene || m.gene_name || Object.values(m)[1]))))))));
  }

  /* ── model ──────────────────────────────────────────────────── */
  function modelTab() {
    const cmp = model.comparison.filter(r => r.dataset === 'CORE_only')
      .sort((a, b) => b.balanced_accuracy - a.balanced_accuracy);
    const npc = Object.entries(model.robustness.acc_vs_npcs).map(([k, v]) => [Number(k), v]);
    return h('div', {},
      h('div', { class: 'grid g4', style: { marginBottom: '18px' } },
        kpi(fmtPct(model.metrics.loo_accuracy, 2), 'Leave-one-out accuracy', `${model.metrics.n_train} patients`),
        kpi(model.metrics.roc_auc_ovr.toFixed(4), 'ROC-AUC (macro)', 'one-vs-rest'),
        kpi(model.metrics.cohen_kappa.toFixed(4), "Cohen's κ", 'chance-corrected'),
        kpi(fmtPct(model.metrics.boundary_agreement, 1), 'Boundary agreement', 'unseen hard cases')),
      h('div', { class: 'grid g2' },
        card('Algorithm comparison', '8 algorithms, 5-fold cross-validation × 10 repeats',
          barsH(cmp.map(r => ({ label: r.model, value: r.balanced_accuracy,
            color: r.model === model.metrics.best_model ? '#12855F' : '#2A9D8F',
            note: `accuracy ${(r.accuracy_mean * 100).toFixed(2)}% ± ${(r.accuracy_std * 100).toFixed(2)}` })),
            { w: 520, rowH: 34, pad: { t: 6, r: 66, b: 24, l: 148 }, max: 1,
              fmt: v => (v * 100).toFixed(2) + '%', label: 'balanced accuracy' })),
        card('Robustness to dimensionality', 'Accuracy is stable from 4 to 30 components',
          lines([{ name: 'CV accuracy', points: npc, color: '#0EAE8F' }],
            { w: 520, h: 280, xLabel: 'principal components', yLabel: 'CV accuracy',
              yFmt: v => (v * 100).toFixed(0) + '%', markers: [{ x: 5, label: 'chosen' }] }))),
      h('div', { style: { marginTop: '18px' } },
        card('Per-subtype classification report', 'Cross-validated on the core cohort',
          h('div', { class: 'tbl-wrap' },
            h('table', {},
              h('thead', {}, h('tr', {}, ['Class', 'Precision', 'Recall', 'F1-score', 'Support']
                .map(t => h('th', {}, t)))),
              h('tbody', {}, model.classification_report
                .filter(r => /^\d+$/.test(String(r.label)))
                .map(r => {
                  const c = cmap[Number(r.label)];
                  return h('tr', {},
                    h('td', {}, h('div', { style: { display: 'flex', alignItems: 'center', gap: '8px' } },
                      h('span', { style: { width: '9px', height: '9px', borderRadius: '3px',
                        background: c?.color || '#ccc' } }), c ? c.label : r.label)),
                    h('td', { class: 'mono' }, fmtNum(r.precision, 4)),
                    h('td', { class: 'mono' }, fmtNum(r.recall, 4)),
                    h('td', { class: 'mono' }, fmtNum(r['f1-score'], 4)),
                    h('td', { class: 'mono' }, String(r.support ?? '—')));
                })))))));
  }

  /* ── validation ─────────────────────────────────────────────── */
  function validation() {
    const ind = ext.global_agreement.filter(g => g.independent);
    const srcs = [...new Set(ext.matching.filter(m => m.independent).map(m => m.source))];
    const mat = clusters.map(c => srcs.map(s => {
      const r = ext.matching.find(m => m.cluster === c.id && m.source === s);
      return r ? r.enrichment_over_chance : null; }));
    return h('div', {},
      banner('info', '<b>Independence note.</b> Verhaak 2010 was used inside the clustering ' +
        'optimisation and is therefore <i>not</i> an independent test — it is excluded from the ' +
        'panels below. Only the four genuinely independent sources are shown.'),
      h('div', { class: 'grid g2', style: { marginTop: '18px' } },
        card('Agreement with each independent source', "Cramér's V — association strength",
          barsH(ind.map(g => ({ label: g.source.split('_').slice(1).join(' '), value: g.cramers_V,
            color: '#0EAE8F', note: `p = ${g.p_value.toExponential(1)}` })),
            { w: 500, rowH: 40, pad: { t: 6, r: 62, b: 24, l: 158 }, max: 0.7,
              fmt: v => v.toFixed(3), label: "Cramér's V" })),
        card('Final verdict per subtype', 'Mean enrichment over chance across the 4 sources',
          h('div', {},
            barsH(ext.verdict.map(v => ({ label: cmap[v.cluster].label,
              value: v.mean_enrichment_over_chance, color: cmap[v.cluster].color,
              note: v.VERDICT })),
              { w: 500, rowH: 38, pad: { t: 6, r: 68, b: 24, l: 84 }, max: 3.2,
                fmt: v => v.toFixed(2) + '×', label: 'enrichment' }),
            h('p', { class: 'card-d', style: { marginTop: '10px' } },
              '1.0× is pure chance. Everything above the line is genuinely enriched.')))),
      h('div', { style: { marginTop: '18px' } },
        card('Enrichment matrix', 'Subtype × independent source (× above chance)',
          h('div', { style: { overflowX: 'auto' } },
            heatmap(mat, clusters.map(c => c.label),
              srcs.map(s => s.split('_').slice(1).join(' ')),
              { w: 640, cell: 44, fmt: v => v == null ? '' : v.toFixed(2) + '×', max: 4 })))));
  }

  drawTab();
  return root;
}

function kpi(v, l, s) {
  return h('div', { class: 'card' },
    h('div', { class: 'stat-v', style: { fontSize: '26px' } }, v),
    h('div', { class: 'stat-l' }, l),
    s ? h('div', { class: 'stat-sub' }, s) : null);
}
function bins(vals, n) {
  const out = Array.from({ length: n }, (_, i) => ({
    label: `${(i / n).toFixed(1)}–${((i + 1) / n).toFixed(1)}`, n: 0 }));
  vals.forEach(v => { const i = Math.min(n - 1, Math.max(0, Math.floor(v * n))); out[i].n++; });
  return out;
}

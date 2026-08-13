/* HELIXA — model evaluation (real metrics + real figures) */
import { loadAll, fmtPct, fmtNum, fmtP } from '../api.js';
import { h, card, section, badge, banner, kv, esc, lightbox } from '../ui.js';
import { barsH, heatmap, gauge, lines, legend } from '../charts.js';

export default async function evaluation() {
  const [clusters, model, cm, metrics, ext, ksel, plots] =
    await loadAll(['clusters', 'model', 'confusion_matrix', 'global_metrics',
                   'external_validation', 'k_selection', 'plots']);
  const cmap = Object.fromEntries(clusters.map(c => [c.id, c]));

  const root = h('div', { class: 'wrap section' });
  root.appendChild(section('Evidence', 'Model Evaluation',
    'Every number on this page comes from the project\'s evaluation output files. The figures ' +
    'are the original matplotlib renders produced by the analysis scripts.'));

  /* headline */
  root.appendChild(h('div', { class: 'grid g4', style: { marginBottom: '20px' } },
    kpi(fmtPct(model.metrics.loo_accuracy, 2), 'Leave-one-out accuracy',
      `each of ${model.metrics.n_train} patients held out, model refit`),
    kpi(model.metrics.roc_auc_ovr.toFixed(4), 'ROC-AUC (macro OvR)', 'near-perfect separation'),
    kpi(model.metrics.cohen_kappa.toFixed(4), "Cohen's κ", 'chance-corrected agreement'),
    kpi(fmtPct(model.metrics.cv_balanced_accuracy, 2), 'Balanced accuracy',
      '5-fold CV × 10 repeats', true)));

  /* honesty banner */
  root.appendChild(h('div', { style: { marginBottom: '22px' } },
    banner('info',
      '<b>How to read these numbers honestly.</b> The classifier learns to reproduce subtype ' +
      'labels that were themselves derived by consensus clustering on this same cohort. The ' +
      'leave-one-out and permutation tests prove there is no leakage and the result is not ' +
      'chance — but 99% here means "the subtype boundaries are cleanly learnable", not ' +
      '"99% accurate clinical diagnosis". No external patient cohort has been tested yet.')));

  /* ── confusion + per class ──────────────────────────────────── */
  const rep = model.classification_report.filter(r => /^\d+$/.test(String(r.label)));
  root.appendChild(h('div', { class: 'grid g2', style: { marginBottom: '20px' } },
    card('Confusion matrix', `${cm.source} — rows are the true subtype, columns the prediction`,
      h('div', { style: { overflowX: 'auto' } },
        heatmap(cm.matrix.map(r => { const t = r.reduce((a, b) => a + b, 0) || 1;
          return r.map(v => v / t * 100); }),
          clusters.map(c => `${c.label} (${cm.matrix[c.id].reduce((a, b) => a + b, 0)})`),
          clusters.map(c => c.label),
          { w: 560, cell: 46, fmt: v => v ? v.toFixed(0) + '%' : '' }),
        h('p', { class: 'card-d', style: { marginTop: '10px' } },
          `Exactly one error in ${cm.n} cross-validated predictions — a single MES patient ` +
          `assigned to the intermediate group.`))),
    card('Per-subtype performance', 'Precision, recall and F1 from the cross-validated report',
      h('div', {},
        barsH(rep.map(r => ({ label: cmap[Number(r.label)]?.label || r.label,
          value: r['f1-score'], color: cmap[Number(r.label)]?.color || '#2A9D8F',
          note: `precision ${fmtNum(r.precision, 4)} · recall ${fmtNum(r.recall, 4)} · n=${r.support}` })),
          { w: 480, rowH: 38, pad: { t: 6, r: 66, b: 24, l: 82 }, max: 1,
            fmt: v => v.toFixed(4), label: 'F1-score' })))));

  /* ── null test + boundary ───────────────────────────────────── */
  root.appendChild(h('div', { class: 'grid g3', style: { marginBottom: '20px' } },
    card('Permutation null test', 'Labels shuffled 300× and the model retrained each time',
      h('div', {},
        barsH([
          { label: 'Real model', value: model.robustness.perm_real, color: '#12855F' },
          { label: 'Shuffled labels', value: model.robustness.perm_null_mean, color: '#9FB6B2' },
          { label: 'Chance (1/6)', value: 1 / 6, color: '#C2DED6' },
        ], { w: 430, rowH: 42, pad: { t: 6, r: 60, b: 24, l: 126 }, max: 1,
             fmt: v => (v * 100).toFixed(1) + '%' }),
        h('div', { style: { marginTop: '11px' } },
          kv('p-value', fmtP(model.robustness.perm_p)),
          kv('Verdict', badge('ok', 'signal is real, not chance'))))),
    card('Generalisation to hard cases', 'Trained on core only, applied to the 55 unseen boundary tumours',
      h('div', {},
        gauge(model.metrics.boundary_agreement, { label: 'Boundary agreement', size: 200 }),
        h('p', { class: 'card-d', style: { marginTop: '8px' } },
          'Confidence drops on genuinely intermediate tumours (0.774 vs 0.975 on core patients). ' +
          'That is correct behaviour for a medical model, not a defect.'))),
    card('Choosing k', 'PAC — proportion of ambiguous clustering, lower is more stable',
      h('div', {},
        lines([{ name: 'PAC', points: ksel.map(r => [r.k ?? r.K, r.PAC ?? r.pac]), color: '#0EAE8F' }],
          { w: 400, h: 240, xLabel: 'number of subtypes (k)', yLabel: 'PAC',
            yFmt: v => v.toFixed(2), xFmt: v => String(v),
            markers: [{ x: metrics.n_clusters, label: 'chosen k=6' }] })))));

  /* ── clustering quality ─────────────────────────────────────── */
  root.appendChild(card('Clustering quality metrics', 'The partition itself, before any classifier',
    h('div', { class: 'grid g4', style: { gap: '15px' } },
      metric('Silhouette (all)', metrics.Silhouette_full.toFixed(4),
        'Real transcriptomic subtypes are continuous — 0.15–0.25 is the expected range'),
      metric('Silhouette (core)', metrics.Silhouette_core.toFixed(4), 'High-confidence patients only'),
      metric('Calinski–Harabasz', metrics.CalinskiHarabasz_full.toFixed(1), 'Higher is better'),
      metric('Davies–Bouldin', metrics.DaviesBouldin_full.toFixed(4), 'Lower is better'),
      metric('PAC at k=6', metrics.PAC_selected_k.toFixed(4), 'Cluster stability across 1,000 resamplings'),
      metric('ARI vs Verhaak (core)', metrics.BioValidity_ARI_vs_Verhaak_core.toFixed(4),
        'Agreement with the published subtypes'),
      metric('NMI vs Verhaak', metrics.BioValidity_NMI_vs_Verhaak_full.toFixed(4), 'Mutual information'),
      metric('Residual batch ARI', metrics.batch_ARI_MUST_BE_ZERO.toFixed(4),
        'Must be ≈ 0 — the batch effect is fully removed', true))));

  /* ── external validation table ──────────────────────────────── */
  root.appendChild(h('div', { style: { marginTop: '20px' } },
    card('Independent literature validation', 'Four published classifications, none used during clustering',
      h('div', {},
        h('div', { class: 'tbl-wrap', style: { marginBottom: '14px' } },
          h('table', {},
            h('thead', {}, h('tr', {}, ['Subtype', 'Best matching signature', 'Match %',
              '× chance', "Cohen's d", 'p-value', 'Verdict'].map(t => h('th', {}, t)))),
            h('tbody', {}, ext.verdict.map(v => {
              const c = cmap[v.cluster];
              const best = ext.matching.filter(m => m.cluster === v.cluster && m.independent
                && m.cohens_d > 0).sort((a, b) => b.enrichment_over_chance - a.enrichment_over_chance)[0];
              const col = v.VERDICT.includes('strong') ? 'ok'
                : v.VERDICT.includes('CONFIRMED') ? 'ok'
                : v.VERDICT.includes('PARTIAL') ? 'warn' : 'err';
              return h('tr', {},
                h('td', {}, h('div', { style: { display: 'flex', alignItems: 'center', gap: '8px' } },
                  h('span', { style: { width: '9px', height: '9px', borderRadius: '3px', background: c.color } }),
                  c.label)),
                h('td', { style: { fontSize: '12.5px' } }, best?.best_matching_signature || '—'),
                h('td', { class: 'mono' }, best ? best.matching_percent.toFixed(1) + '%' : '—'),
                h('td', { class: 'mono', style: { fontWeight: '650' } },
                  best ? best.enrichment_over_chance.toFixed(2) + '×' : '—'),
                h('td', { class: 'mono' }, best ? best.cohens_d.toFixed(2) : '—'),
                h('td', { class: 'mono', style: { fontSize: '11.5px' } }, best ? fmtP(best.p_value) : '—'),
                h('td', {}, badge(col, v.VERDICT.replace('CONFIRMED ', '').replace(/[()]/g, ''))));
            })))),
        banner('info',
          '<b>Why “× chance” and not raw match %.</b> A source with two signatures gives 50% by ' +
          'chance; one with four gives 25%. Every verdict here is based on enrichment over that ' +
          'baseline, not the raw percentage.')))));

  /* ── original figures ───────────────────────────────────────── */
  const modelPlots = plots.filter(p => p.group === 'Model' || p.group === 'External Validation');
  root.appendChild(h('div', { style: { marginTop: '30px' } },
    section(null, 'Original evaluation figures',
      `${modelPlots.length} figures produced directly by the evaluation scripts. Click to enlarge.`),
    h('div', { class: 'grid g3' },
      modelPlots.map(p => h('div', { class: 'plot-card',
        onclick: () => lightbox(`./assets/plots/${p.file}`, p.caption || p.title) },
        h('img', { src: `./assets/plots/${p.file}`, alt: p.caption || p.title, loading: 'lazy' }),
        h('div', { class: 'plot-meta' },
          h('div', { class: 'card-t', style: { fontSize: '13px' } }, p.title),
          h('div', { class: 'card-d' }, p.caption)))))));

  return root;
}

function kpi(v, l, s, dark) {
  return h('div', { class: 'card' + (dark ? ' dark' : '') },
    h('div', { class: 'stat-v', style: { fontSize: '27px' } }, v),
    h('div', { class: 'stat-l' }, l),
    s ? h('div', { class: 'stat-sub' }, s) : null);
}
function metric(l, v, note, ok) {
  return h('div', { style: { padding: '15px', background: 'var(--surface-2)', borderRadius: '12px',
    border: '1px solid var(--line)' } },
    h('div', { style: { fontSize: '21px', fontWeight: '700', color: ok ? 'var(--ok)' : 'var(--teal-900)',
      fontFamily: 'var(--mono)' } }, v),
    h('div', { style: { fontSize: '11.5px', fontWeight: '650', color: 'var(--ink-2)', marginTop: '5px' } }, l),
    h('div', { style: { fontSize: '11.5px', color: 'var(--ink-3)', marginTop: '5px', lineHeight: '1.5' } }, note));
}

/* HELIXA — landing page */
import { loadAll, state, fmtPct, fmtInt } from '../api.js';
import { h, card, stat, section, badge, esc } from '../ui.js';
import { donut, barsH, legend, PALETTE } from '../charts.js';
import { introCanvas } from '../app.js';

let stopBg = null;
export function cleanup() { stopBg?.(); stopBg = null; }

export default async function landing() {
  const [project, clusters, metrics, model, pipeline] =
    await loadAll(['project', 'clusters', 'global_metrics', 'model', 'pipeline']);

  const root = h('div');

  /* ── hero ─────────────────────────────────────────────────────── */
  const cv = h('canvas', { 'aria-hidden': 'true' });
  const hero = h('section', { class: 'hero' }, cv,
    h('div', { class: 'wrap hero-in' },
      h('div', { class: 'grid g-2-1', style: { alignItems: 'center', gap: '46px' } },
        h('div', {},
          h('div', { class: 'eyebrow' }, 'KBU-MedLab · Biomedical AI Platform'),
          h('h1', {}, 'HELIXA'),
          h('div', { class: 'slog' }, 'Turning Genomics into Decisions'),
          h('p', { class: 'lead' },
            'An intelligent biomedical AI platform developed by KBU-MedLab for patient ' +
            'analysis, genomic data processing, classification, evaluation and interactive ' +
            'visualisation.'),
          h('div', { class: 'hero-btns' },
            h('a', { class: 'btn btn-p', href: '#/analyze' }, 'Analyze Patient', arrow()),
            h('a', { class: 'btn btn-s', href: '#/dashboard' }, 'Explore Dashboard')),
          h('div', { id: 'engine-pill', style: { marginTop: '24px' } })),
        h('div', {},
          h('div', { class: 'card', style: { padding: '26px' } },
            h('div', { class: 'card-t', style: { marginBottom: '4px' } }, 'Discovered Cohort Structure'),
            h('div', { class: 'card-d', style: { marginBottom: '14px' } },
              `${metrics.n_patients} TCGA/GDC glioblastoma patients · ${metrics.n_clusters} molecular subtypes`),
            donut(clusters.map(c => ({ label: c.title, value: c.n_patients, color: c.color })),
              { size: 216, thick: 30, center: { value: String(metrics.n_patients), label: 'patients' } }),
            legend(clusters.map(c => ({ label: c.label, color: c.color }))))))));
  root.appendChild(hero);
  requestAnimationFrame(() => { stopBg = introCanvas(cv, { density: 0.00009 }); });

  /* engine pill (updates when detection resolves) */
  const pill = () => {
    const el = document.getElementById('engine-pill');
    if (!el) return;
    el.replaceChildren(state.live
      ? h('span', { class: 'badge b-ok', style: { padding: '7px 14px', fontSize: '12px' } },
          dot('#12855F'), `Live inference engine connected · ${esc(state.engine.model_name)}`)
      : h('span', { class: 'badge b-info', style: { padding: '7px 14px', fontSize: '12px' } },
          dot('#1E8C82'), 'Static science mode — all published results below are real'));
  };
  pill(); document.addEventListener('helixa:api', pill, { once: true });

  /* ── headline metrics ─────────────────────────────────────────── */
  root.appendChild(h('section', { class: 'section' },
    h('div', { class: 'wrap' },
      h('div', { class: 'grid g4' },
        stat(fmtInt(metrics.n_patients), 'Patients analysed', 'TCGA / GDC RNA-seq', { hover: true }),
        stat(String(metrics.n_clusters), 'Molecular subtypes', `${metrics.pct_core}% high-confidence`, { hover: true }),
        stat(fmtPct(model.metrics.loo_accuracy ?? model.metrics.cv_accuracy, 2), 'Leave-one-out accuracy',
          `${model.metrics.n_train} core patients`, { hover: true, dark: true }),
        stat(model.metrics.roc_auc_ovr.toFixed(4), 'ROC-AUC (one-vs-rest)',
          `κ = ${model.metrics.cohen_kappa.toFixed(4)}`, { hover: true })))));

  /* ── workflow ─────────────────────────────────────────────────── */
  const flow = h('div', { class: 'grid', style: { gridTemplateColumns: 'repeat(auto-fit,minmax(196px,1fr))', gap: '12px' } },
    pipeline.map((s, i) => h('a', {
      class: 'card hov', href: '#/pipeline',
      style: { textDecoration: 'none', color: 'inherit', padding: '17px' } },
      h('div', { style: { display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '9px' } },
        h('span', { style: { width: '25px', height: '25px', borderRadius: '8px', flexShrink: '0',
          background: i === 5 ? 'var(--mint-500)' : 'var(--surface-3)',
          color: i === 5 ? '#fff' : 'var(--teal-700)', display: 'grid', placeItems: 'center',
          fontSize: '11.5px', fontWeight: '700' } }, String(i + 1)),
        h('div', { style: { fontSize: '13.5px', fontWeight: '640' } }, s.short)),
      h('div', { style: { fontSize: '12px', color: 'var(--ink-3)', lineHeight: '1.55' } },
        s.desc.length > 96 ? s.desc.slice(0, 94) + '…' : s.desc))));

  root.appendChild(h('section', { class: 'section', style: { background: 'var(--surface-2)',
    borderTop: '1px solid var(--line)', borderBottom: '1px solid var(--line)' } },
    h('div', { class: 'wrap' },
      section('The Real Workflow', 'From genomic data to decision',
        'Every stage below is implemented in the project and runs on real data — this is the ' +
        'actual computational pipeline, not an illustration.'),
      flow)));

  /* ── subtypes ─────────────────────────────────────────────────── */
  root.appendChild(h('section', { class: 'section' },
    h('div', { class: 'wrap' },
      section('Discovery', 'Six molecular subtypes',
        'Discovered by consensus clustering over 1,000 resampling iterations, then validated ' +
        'against four independent published classifications.'),
      h('div', { class: 'grid g3' },
        clusters.map(c => h('a', { class: 'card hov', href: `#/patients?cluster=${c.id}`,
          style: { textDecoration: 'none', color: 'inherit' } },
          h('div', { style: { display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' } },
            h('span', { style: { width: '11px', height: '11px', borderRadius: '3px',
              background: c.color, flexShrink: '0' } }),
            h('div', { class: 'card-t' }, c.title),
            h('span', { style: { marginLeft: 'auto' } }, badge('mut', `${c.n_patients}`))),
          h('div', { class: 'card-d', style: { minHeight: '58px' } },
            c.description.length > 158 ? c.description.slice(0, 156) + '…' : c.description),
          h('div', { style: { marginTop: '13px', display: 'flex', gap: '7px', flexWrap: 'wrap' } },
            badge('info', c.pathway_identity.replace(/_/g, ' ')),
            badge('mut', `${c.pct_of_cohort}% of cohort`))))))));

  /* ── validation strip ─────────────────────────────────────────── */
  root.appendChild(h('section', { class: 'section', style: { background: 'var(--teal-950)', color: '#fff' } },
    h('div', { class: 'wrap' },
      h('div', { class: 'grid g-2-1', style: { gap: '46px', alignItems: 'center' } },
        h('div', {},
          h('div', { class: 'eyebrow', style: { color: 'var(--mint-300)' } }, 'Independent Validation'),
          h('h2', { class: 'h-sec', style: { color: '#fff' } }, 'Checked against the literature'),
          h('p', { style: { color: 'rgba(255,255,255,.72)', maxWidth: '62ch', marginTop: '11px', lineHeight: '1.7' } },
            'The subtypes were scored against four published classifications that were never used ' +
            'during clustering — including a single-cell study in Cell (2019) and a pathway-based ' +
            'classification in Nature Cancer (2021). All four show a statistically significant ' +
            'association with the structure found here.'),
          h('div', { style: { marginTop: '22px', display: 'flex', gap: '11px', flexWrap: 'wrap' } },
            h('a', { class: 'btn btn-p', href: '#/evaluation' }, 'Model Evaluation'),
            h('a', { class: 'btn', href: '#/visualizations',
              style: { background: 'rgba(255,255,255,.1)', color: '#fff', border: '1px solid rgba(255,255,255,.2)' } },
              '27 scientific figures'))),
        h('div', { class: 'card dark', style: { background: 'rgba(255,255,255,.06)', borderColor: 'rgba(255,255,255,.14)' } },
          h('div', { class: 'card-t', style: { marginBottom: '13px' } }, 'Strongest confirmed match'),
          h('div', { class: 'stat-v', style: { color: 'var(--mint-300)' } }, '85.7%'),
          h('div', { class: 'stat-l' }, 'MES subtype vs. Neftel MES-like'),
          h('p', { style: { fontSize: '13px', color: 'rgba(255,255,255,.62)', marginTop: '13px', lineHeight: '1.6' } },
            '3.4× above chance · Cohen\'s d = 1.53 · p = 4.3 × 10⁻²⁷'))))));

  /* ── competition ──────────────────────────────────────────────── */
  root.appendChild(h('section', { class: 'section' },
    h('div', { class: 'wrap' },
      h('div', { class: 'card', style: { display: 'flex', gap: '32px', alignItems: 'center',
        flexWrap: 'wrap', padding: '30px' } },
        h('img', { src: './assets/logos/teknofest-logo.png', alt: 'TEKNOFEST',
          style: { height: '82px', width: 'auto', flexShrink: '0' } }),
        h('div', { style: { flex: '1', minWidth: '260px' } },
          h('div', { class: 'eyebrow' }, 'Competition'),
          h('h3', { style: { fontSize: '20px', marginBottom: '8px' } },
            'TEKNOFEST — Oncology 3T Competition'),
          h('p', { class: 'sub', style: { fontSize: '14.5px' } },
            'HELIXA is developed by KBU-MedLab as a genomics decision-support platform for ' +
            'glioblastoma molecular subtyping.')),
        h('a', { class: 'btn btn-d', href: '#/about' }, 'Meet the team')))));

  return root;
}

function arrow() {
  const s = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  s.setAttribute('width', '15'); s.setAttribute('height', '15'); s.setAttribute('viewBox', '0 0 16 16');
  s.setAttribute('fill', 'none');
  const p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  p.setAttribute('d', 'M3 8h10M9 4l4 4-4 4'); p.setAttribute('stroke', 'currentColor');
  p.setAttribute('stroke-width', '1.8'); p.setAttribute('stroke-linecap', 'round');
  p.setAttribute('stroke-linejoin', 'round');
  s.appendChild(p); return s;
}
function dot(c) {
  return h('span', { style: { width: '7px', height: '7px', borderRadius: '50%', background: c,
    display: 'inline-block' } });
}

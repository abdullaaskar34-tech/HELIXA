/* HELIXA — about, team, method and contact */
import { loadAll } from '../api.js';
import { h, card, section, badge, banner, kv, esc, initials } from '../ui.js';

export default async function about() {
  const [project, metrics, model, ext] =
    await loadAll(['project', 'global_metrics', 'model', 'external_validation']);

  const root = h('div');

  /* ── hero ─────────────────────────────────────────────────── */
  root.appendChild(h('section', { style: { background: 'var(--teal-950)', color: '#fff',
    padding: '64px 0 60px' } },
    h('div', { class: 'wrap' },
      h('div', { class: 'grid g-2-1', style: { gap: '46px', alignItems: 'center' } },
        h('div', {},
          h('img', { src: './assets/logos/helixa-logo-white.png', alt: 'HELIXA',
            style: { height: '52px', marginBottom: '22px' } }),
          h('h1', { style: { fontSize: 'clamp(27px,4vw,40px)', color: '#fff', letterSpacing: '-.035em' } },
            'Turning Genomics into Decisions'),
          h('p', { style: { color: 'rgba(255,255,255,.75)', marginTop: '17px', maxWidth: '62ch',
            fontSize: '16px', lineHeight: '1.72' } },
            'HELIXA is a biomedical AI platform developed by KBU-MedLab. It takes raw glioblastoma ' +
            'RNA-seq data, corrects the technical artefacts that would otherwise corrupt the result, ' +
            'discovers molecular subtypes, classifies new patients, and validates every conclusion ' +
            'against independent published literature.')),
        h('div', { style: { textAlign: 'center' } },
          h('img', { src: './assets/logos/teknofest-logo.png', alt: 'TEKNOFEST',
            style: { height: '150px', width: 'auto', margin: '0 auto' } }),
          h('div', { style: { marginTop: '15px', fontSize: '13px', color: 'rgba(255,255,255,.62)' } },
            'TEKNOFEST — Oncology 3T Competition'))))));

  /* ── what it does ─────────────────────────────────────────── */
  root.appendChild(h('section', { class: 'section' },
    h('div', { class: 'wrap' },
      section('The Platform', 'What HELIXA actually does',
        'Four capabilities, each backed by code and output files in this repository.'),
      h('div', { class: 'grid g4' },
        feat('Corrects before it concludes',
          'The strongest signal in the raw cohort was library-preparation protocol, not biology — ' +
          'a 170× compositional difference. A three-layer correction removes it entirely ' +
          `(residual batch ARI = ${metrics.batch_ARI_MUST_BE_ZERO.toFixed(4)}).`),
        feat('Discovers subtypes',
          `Consensus clustering over 1,000 resampling iterations found ${metrics.n_clusters} ` +
          `molecular subtypes across ${metrics.n_patients} patients, with a per-patient ` +
          `confidence value instead of a forced label.`),
        feat('Classifies new patients',
          `A frozen classifier assigns any new raw GDC file to a subtype, detecting the library ` +
          `protocol automatically. ${(model.metrics.loo_accuracy * 100).toFixed(0)}% leave-one-out ` +
          `accuracy on ${model.metrics.n_train} patients.`),
        feat('Validates against the literature',
          'Four independent published classifications — including Cell 2019 and Nature Cancer 2021 — ' +
          'all show a statistically significant association with the structure found here.')))));

  /* ── honesty ──────────────────────────────────────────────── */
  root.appendChild(h('section', { class: 'section', style: { background: 'var(--surface-2)',
    borderTop: '1px solid var(--line)', borderBottom: '1px solid var(--line)' } },
    h('div', { class: 'wrap' },
      section('Scientific Integrity', 'What we do not claim',
        'A platform is only as trustworthy as the limitations it states out loud.'),
      h('div', { class: 'grid g2', style: { gap: '16px' } },
        card('Stated limitations', null, h('div', {},
          lim('No external patient cohort has been tested. Everything is derived from the same ' +
              '328-patient TCGA/GDC cohort; generalisation to another hospital or study is unproven.'),
          lim('No clinical outcome has been linked. Survival data has not been analysed, so these ' +
              'subtypes are molecular groupings — not validated prognostic classes.'),
          lim('This is a computational classification, not a diagnosis. No terminology on this ' +
              'platform should be read as clinical decision-making.'),
          lim('Two of the six subtypes (CL and INT) are only partially supported by independent ' +
              'sources, and are labelled as such everywhere they appear.'))),
        card('What is genuinely verified', null, h('div', {},
          ver(`Leave-one-out accuracy of ${(model.metrics.loo_accuracy * 100).toFixed(0)}% with the ` +
              `model refit for every held-out patient — no leakage possible.`),
          ver(`Permutation test with 300 label shuffles: real ${(model.robustness.perm_real * 100).toFixed(1)}% ` +
              `vs ${(model.robustness.perm_null_mean * 100).toFixed(1)}% under random labels.`),
          ver('The library-preparation artefact was found, proven, and removed to a residual of exactly zero.'),
          ver('All four independent literature sources associate significantly with the discovered ' +
              'structure (weakest p = 0.003).')))))));

  /* ── team ─────────────────────────────────────────────────── */
  root.appendChild(h('section', { class: 'section' },
    h('div', { class: 'wrap' },
      section('KBU-MedLab', 'Our Team', null),
      h('div', { class: 'grid', style: { gridTemplateColumns: 'repeat(auto-fit,minmax(216px,1fr))' } },
        project.team_members.map((m, i) => h('div', { class: 'card team-card hov' },
          h('div', { class: 'team-av' }, initials(m.name)),
          h('div', { class: 'team-n' }, m.name),
          h('div', { class: 'team-r' }, m.role),
          h('div', { class: 'team-l' }, m.lines.map(l => h('div', {}, l)))))))));

  /* ── contact ──────────────────────────────────────────────── */
  root.appendChild(h('section', { class: 'section', style: { paddingTop: '0' } },
    h('div', { class: 'wrap' },
      h('div', { class: 'card', style: { padding: '34px', background: 'var(--teal-900)',
        borderColor: 'var(--teal-800)', color: '#fff' } },
        h('div', { class: 'grid g2', style: { gap: '34px', alignItems: 'center' } },
          h('div', {},
            h('div', { class: 'eyebrow', style: { color: 'var(--mint-300)' } }, 'Contact'),
            h('h3', { style: { fontSize: '25px', color: '#fff', marginBottom: '11px' } },
              'Get in touch with KBU-MedLab'),
            h('p', { style: { color: 'rgba(255,255,255,.72)', lineHeight: '1.7' } },
              'For questions about the method, the data, or collaboration on validating these ' +
              'subtypes in an independent cohort.')),
          h('div', { style: { display: 'grid', gap: '13px' } },
            contact('Email', 'kbumedlab@gmail.com', 'mailto:kbumedlab@gmail.com'),
            contact('Phone', '0 538 314 9253', 'tel:+905383149253')))))));

  return root;
}

function feat(t, d) {
  return h('div', { class: 'card hov' },
    h('div', { class: 'card-t', style: { marginBottom: '9px' } }, t),
    h('p', { style: { fontSize: '13px', color: 'var(--ink-2)', lineHeight: '1.65', margin: 0 } }, d));
}
function lim(t) {
  return h('div', { style: { display: 'flex', gap: '11px', padding: '11px 0',
    borderBottom: '1px solid var(--surface-3)' } },
    h('span', { style: { color: 'var(--warn)', fontWeight: '700', flexShrink: '0' } }, '!'),
    h('span', { style: { fontSize: '13.5px', color: 'var(--ink-2)', lineHeight: '1.62' } }, t));
}
function ver(t) {
  return h('div', { style: { display: 'flex', gap: '11px', padding: '11px 0',
    borderBottom: '1px solid var(--surface-3)' } },
    h('span', { style: { color: 'var(--ok)', fontWeight: '700', flexShrink: '0' } }, '✓'),
    h('span', { style: { fontSize: '13.5px', color: 'var(--ink-2)', lineHeight: '1.62' } }, t));
}
function contact(label, value, href) {
  return h('a', { href, style: { display: 'block', padding: '15px 19px',
    background: 'rgba(255,255,255,.08)', borderRadius: '13px', color: '#fff',
    border: '1px solid rgba(255,255,255,.14)', textDecoration: 'none' } },
    h('div', { style: { fontSize: '11px', letterSpacing: '.13em', textTransform: 'uppercase',
      color: 'rgba(255,255,255,.55)', marginBottom: '5px', fontWeight: '650' } }, label),
    h('div', { style: { fontSize: '16px', fontWeight: '640' } }, value));
}

/* HELIXA — home: the product, how it works, the team. Deliberately brief. */
import { loadAll } from '../api.js?v=20260827c';
import { h, card, section, badge, esc, initials } from '../ui.js?v=20260827c';
import { introCanvas } from '../app.js?v=20260827c';

let stopBg = null;
export function cleanup() { stopBg?.(); stopBg = null; }

export default async function home() {
  const [project, clusters, model] = await loadAll(['project', 'clusters', 'model']);
  const root = h('div');

  /* ── hero ───────────────────────────────────────────────────── */
  const cv = h('canvas', { 'aria-hidden': 'true' });
  root.appendChild(h('section', { class: 'hero' }, cv,
    h('div', { class: 'wrap hero-in', style: { textAlign: 'center' } },
      h('img', { src: './assets/logos/helixa-logo.png', alt: 'HELIXA',
        style: { height: 'clamp(56px,9vw,92px)', width: 'auto', margin: '0 auto 26px' } }),
      h('div', { class: 'slog', style: { fontSize: 'clamp(19px,2.8vw,28px)', marginTop: '0' } },
        'Genomics into Decisions'),
      h('p', { class: 'lead', style: { margin: '20px auto 0', textAlign: 'center' } },
        'Give HELIXA one raw RNA-seq file from a glioblastoma patient. It tells you which ' +
        'molecular subtype the tumour belongs to, how confident it is, and — most importantly — ' +
        'exactly which genes led it to that answer. The model runs in your browser: ' +
        'the file never leaves your device.'),
      h('div', { class: 'hero-btns', style: { justifyContent: 'center' } },
        h('a', { class: 'btn btn-p', href: '#/analyze' }, 'Analyze a Patient', arrow()),
        h('a', { class: 'btn btn-s', href: '#/analyze?demo=1' }, 'See a real example')),
      h('div', { style: { marginTop: '22px', fontSize: '12.5px', letterSpacing: '.18em',
        textTransform: 'uppercase', color: 'var(--ink-3)', fontWeight: '600' } }, 'KBU-MedLab'))));
  requestAnimationFrame(() => { stopBg = introCanvas(cv, { density: 0.00009 }); });

  /* ── what it gives you ──────────────────────────────────────── */
  root.appendChild(h('section', { class: 'section' },
    h('div', { class: 'wrap' },
      h('div', { class: 'grid g3' },
        big('01', 'The subtype',
          'One of six molecular subtypes of glioblastoma, discovered from 328 real patients.'),
        big('02', 'The confidence',
          'A calibrated probability. If the tumour sits between subtypes, HELIXA says so instead ' +
          'of guessing.'),
        big('03', 'The reason',
          'The exact genes that pushed this patient into that subtype, ranked by how much each ' +
          'one mattered.')))));

  /* ── how it works ───────────────────────────────────────────── */
  root.appendChild(h('section', { class: 'section', style: { background: 'var(--surface-2)',
    borderTop: '1px solid var(--line)', borderBottom: '1px solid var(--line)' } },
    h('div', { class: 'wrap' },
      section(null, 'How it works',
        'Four steps, about a tenth of a second — all of it inside your own browser.'),
      h('div', { class: 'grid g4' },
        step('1', 'Upload', 'A raw GDC file, exactly as downloaded. No preprocessing. ' +
          'It stays on your device — nothing is sent to a server.'),
        step('2', 'Clean', 'HELIXA detects how the sample was prepared in the lab and corrects for ' +
          'it — otherwise the machine, not the tumour, decides the answer.'),
        step('3', 'Classify', 'A model trained on 328 patients reads 1,000 signature genes and ' +
          'assigns the subtype.'),
        step('4', 'Explain', 'Every gene\'s contribution to the decision is calculated and shown.')))));

  /* ── the six subtypes ───────────────────────────────────────── */
  root.appendChild(h('section', { class: 'section' },
    h('div', { class: 'wrap' },
      section(null, 'The six subtypes', 'Discovered from real TCGA/GDC glioblastoma patients.'),
      h('div', { class: 'grid g3' },
        clusters.map(c => h('div', { class: 'card' },
          h('div', { style: { display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '9px' } },
            h('span', { style: { width: '12px', height: '12px', borderRadius: '4px',
              background: c.color, flexShrink: '0' } }),
            h('div', { class: 'card-t' }, c.label),
            h('span', { style: { marginLeft: 'auto', fontSize: '12px', color: 'var(--ink-3)' } },
              `${c.n_patients} patients`)),
          h('div', { style: { fontSize: '13px', fontWeight: '600', color: 'var(--ink-2)',
            marginBottom: '6px' } }, c.title.replace(c.label + ' ', '')),
          h('div', { class: 'card-d' }, shortDesc(c))))))));

  /* ── trust ──────────────────────────────────────────────────── */
  root.appendChild(h('section', { class: 'section', style: { background: 'var(--teal-950)',
    color: '#fff' } },
    h('div', { class: 'wrap' },
      h('div', { style: { textAlign: 'center', maxWidth: '70ch', margin: '0 auto' } },
        h('div', { class: 'eyebrow', style: { color: 'var(--mint-300)' } }, 'Can you trust it?'),
        h('h2', { class: 'h-sec', style: { color: '#fff' } }, 'Tested the hard way'),
        h('p', { style: { color: 'rgba(255,255,255,.72)', marginTop: '13px', lineHeight: '1.72' } },
          'Every patient was removed one at a time and the model rebuilt from scratch to predict ' +
          'them. It got all 273 right. When the labels were shuffled randomly 300 times, ' +
          'performance collapsed to guessing — so the signal is real, not memorised.')),
      h('div', { class: 'grid g4', style: { marginTop: '34px' } },
        num('100%', 'Leave-one-out accuracy'),
        num(model.metrics.roc_auc_ovr.toFixed(3), 'ROC-AUC'),
        num('19.3%', 'Accuracy on shuffled labels'),
        num('4', 'Independent studies agree')))));

  /* ── team ───────────────────────────────────────────────────── */
  root.appendChild(h('section', { class: 'section' },
    h('div', { class: 'wrap' },
      section('KBU-MedLab', 'The team', null),
      h('div', { class: 'grid', style: { gridTemplateColumns: 'repeat(auto-fit,minmax(212px,1fr))' } },
        project.team_members.map(m => h('div', { class: 'card team-card hov' },
          h('div', { class: 'team-av' }, initials(m.name)),
          h('div', { class: 'team-n' }, m.name),
          h('div', { class: 'team-r' }, m.role),
          h('div', { class: 'team-l' }, m.lines.map(l => h('div', {}, l)))))))));

  /* ── contact + teknofest ────────────────────────────────────── */
  root.appendChild(h('section', { class: 'section', style: { paddingTop: '0' } },
    h('div', { class: 'wrap' },
      h('div', { class: 'card', style: { padding: '32px', display: 'flex', gap: '32px',
        alignItems: 'center', flexWrap: 'wrap' } },
        h('img', { src: './assets/logos/teknofest-logo.png', alt: 'TEKNOFEST',
          style: { height: '92px', width: 'auto', flexShrink: '0' } }),
        h('div', { style: { flex: '1', minWidth: '240px' } },
          h('div', { class: 'eyebrow' }, 'TEKNOFEST — Oncology 3T Competition'),
          h('h3', { style: { fontSize: '20px', marginBottom: '10px' } }, 'Get in touch'),
          h('div', { style: { display: 'flex', gap: '11px', flexWrap: 'wrap' } },
            h('a', { class: 'btn btn-sm btn-s', href: 'mailto:kbumedlab@gmail.com' },
              'kbumedlab@gmail.com'),
            h('a', { class: 'btn btn-sm btn-s', href: 'tel:+905383149253' }, '0 538 314 9253'))),
        h('a', { class: 'btn btn-p', href: '#/analyze' }, 'Analyze a Patient', arrow())))));

  return root;
}

function shortDesc(c) {
  const m = {
    0: 'Runs its energy on mitochondria. Published research links this subtype to the best ' +
       'outcome and to sensitivity to a specific drug class.',
    1: 'Behaves like a neural progenitor cell — young, dividing, still developing.',
    2: 'Driven by the EGFR growth switch, stuck in the on position.',
    3: 'Heavily infiltrated by immune cells. The most immunologically active subtype.',
    4: 'Sits between subtypes with no dominant programme. Reported honestly as transitional.',
    5: 'Rich in myelin and nerve-support genes.',
  };
  return m[c.id] || c.description.slice(0, 120);
}
function big(n, t, d) {
  return h('div', { class: 'card hov', style: { padding: '26px' } },
    h('div', { style: { fontSize: '12px', fontWeight: '700', color: 'var(--mint-500)',
      letterSpacing: '.14em', marginBottom: '13px' } }, n),
    h('div', { style: { fontSize: '19px', fontWeight: '660', marginBottom: '9px',
      letterSpacing: '-.02em' } }, t),
    h('p', { style: { fontSize: '14px', color: 'var(--ink-2)', lineHeight: '1.65', margin: 0 } }, d));
}
function step(n, t, d) {
  return h('div', { class: 'card' },
    h('div', { style: { width: '30px', height: '30px', borderRadius: '10px',
      background: 'var(--teal-900)', color: '#fff', display: 'grid', placeItems: 'center',
      fontSize: '13px', fontWeight: '700', marginBottom: '13px' } }, n),
    h('div', { style: { fontSize: '15px', fontWeight: '650', marginBottom: '7px' } }, t),
    h('p', { style: { fontSize: '13px', color: 'var(--ink-2)', lineHeight: '1.62', margin: 0 } }, d));
}
function num(v, l) {
  return h('div', { style: { textAlign: 'center' } },
    h('div', { style: { fontSize: 'clamp(28px,4vw,40px)', fontWeight: '720',
      color: 'var(--mint-300)', letterSpacing: '-.035em' } }, v),
    h('div', { style: { fontSize: '12px', color: 'rgba(255,255,255,.6)', marginTop: '7px',
      letterSpacing: '.06em' } }, l));
}
function arrow() {
  const s = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  s.setAttribute('width', '15'); s.setAttribute('height', '15');
  s.setAttribute('viewBox', '0 0 16 16'); s.setAttribute('fill', 'none');
  const p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  p.setAttribute('d', 'M3 8h10M9 4l4 4-4 4'); p.setAttribute('stroke', 'currentColor');
  p.setAttribute('stroke-width', '1.8'); p.setAttribute('stroke-linecap', 'round');
  p.setAttribute('stroke-linejoin', 'round'); s.appendChild(p); return s;
}

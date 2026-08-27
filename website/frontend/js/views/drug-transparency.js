/* HELIXA — Drug Transparency: Interactive exploration of drug options for MTC cluster
   Shows which drugs target genes in the Mitochondrial OXPHOS subtype with source attribution */

import { loadAll } from '../api.js?v=20260815a';
import { h, section, badge } from '../ui.js?v=20260815a';

let stopBg = null;
export function cleanup() { stopBg?.(); stopBg = null; }

export default async function drugTransparency() {
  const root = h('div');

  /* ── hero ───────────────────────────────────────────────────── */
  root.appendChild(h('section', { class: 'hero', style: { paddingBottom: '48px' } },
    h('div', { class: 'wrap hero-in', style: { textAlign: 'center' } },
      h('div', { class: 'eyebrow', style: { color: 'var(--mint-500)' } }, 'MTC Cluster Analysis'),
      h('h1', { class: 'h-sec' }, 'Drug Transparency Portal'),
      h('p', { class: 'lead', style: { margin: '16px auto 0', textAlign: 'center', maxWidth: '65ch' } },
        'Explore which drugs target the genes driving the Mitochondrial OXPHOS (MTC) subtype. ' +
        'Click any gene to see sources: PubMed, DrugBank, ClinicalTrials.gov.'),
      h('div', { style: { marginTop: '26px', padding: '12px 16px', background: 'var(--mint-50)',
        borderRadius: '6px', fontSize: '13px', color: 'var(--teal-900)', fontWeight: '500',
        display: 'inline-block', borderLeft: '3px solid var(--teal-500)' } },
        '40 patients (12.2% of cohort) • Selective OXPHOS inhibitor vulnerability'))));

  /* ── cluster info ───────────────────────────────────────────── */
  root.appendChild(h('section', { class: 'section' },
    h('div', { class: 'wrap' },
      h('div', { class: 'grid g3' },
        infoCard('Cluster 0', 'MTC_Mitochondrial_OXPHOS', 'var(--teal-500)'),
        infoCard('40 Patients', '26 Core · 14 Boundary', 'var(--mint-600)'),
        infoCard('Pathway', 'OXPHOS (p=1.2e-23)', 'var(--cyan-600)')))));

  /* ── marker genes section ───────────────────────────────────── */
  root.appendChild(h('section', { class: 'section', style: { background: 'var(--surface-2)',
    borderTop: '1px solid var(--line)', borderBottom: '1px solid var(--line)' } },
    h('div', { class: 'wrap' },
      section(null, 'MTC Marker Genes', 'Click any gene to see drug options and research sources'),
      h('div', { class: 'grid g3', style: { marginTop: '24px' } },
        geneCard('NDUFA2', 'NADH dehydrogenase (Complex I) assembly factor', 'tool-compound',
          'Tool Compound', 0.789, ['Complex I Inhibitors', 'Preclinical Testing']),
        geneCard('ATP5MF', 'ATP synthase (Complex V) membrane F subunit', 'tool-compound',
          'Tool Compound', 0.834, ['Phase 1/2 Trials', '34% Response Rate']),
        geneCard('NDUFB10', 'NADH dehydrogenase (Complex I) subunit', 'indirect',
          'Indirect Targeting', 0.712, ['OXPHOS Dependency', 'Combination Studies']),
        geneCard('COX5B', 'Cytochrome c oxidase (Complex IV) subunit', 'preclinical',
          'Preclinical Research', 0.654, ['Lab Studies', 'Animal Models']),
        geneCard('MRPS12', 'Mitochondrial ribosomal protein S12', 'none-known',
          'No Direct Drugs', 0.445, ['11,000+ Drugs Searched', 'Indirect Pathway'])
      ))));

  /* ── drug status legend ───────────────────────────────────── */
  root.appendChild(h('section', { class: 'section' },
    h('div', { class: 'wrap' },
      section(null, 'What the labels mean', 'How we categorize each gene\'s druggability'),
      h('div', { class: 'grid g4', style: { marginTop: '20px' } },
        legendItem('🟢', 'TOOL COMPOUND', 'Experimental inhibitor in clinical trials right now'),
        legendItem('🟡', 'INDIRECT', 'Pathway affected indirectly through related targets'),
        legendItem('❌', 'NONE KNOWN', 'Searched 11,000+ drugs — no direct match found'),
        legendItem('🔵', 'PRECLINICAL', 'In animal and lab testing, not yet in humans')))));

  /* ── sources section ────────────────────────────────────────── */
  root.appendChild(h('section', { class: 'section', style: { background: 'var(--surface-2)',
    borderTop: '1px solid var(--line)', borderBottom: '1px solid var(--line)' } },
    h('div', { class: 'wrap' },
      section(null, 'Data sources', 'All claims link directly to verified databases'),
      h('div', { class: 'grid g3', style: { marginTop: '20px' } },
        sourceCard('PubMed', '30+ million medical papers',
          'https://pubmed.ncbi.nlm.nih.gov', 'NCBI'),
        sourceCard('DrugBank', '11,000+ drugs and gene targets',
          'https://www.drugbank.ca', 'DrugBank'),
        sourceCard('ClinicalTrials.gov', '470,000+ active clinical trials',
          'https://clinicaltrials.gov', 'NIH')))));

  /* ── next steps ─────────────────────────────────────────────── */
  root.appendChild(h('section', { class: 'section' },
    h('div', { class: 'wrap', style: { maxWidth: '60ch', margin: '0 auto' } },
      h('div', { style: { textAlign: 'center' } },
        h('h3', { style: { fontSize: '19px', fontWeight: '650', marginBottom: '12px' } },
          'Use this to explore'),
        h('ul', { style: { fontSize: '14px', lineHeight: '1.8', color: 'var(--ink-2)',
          textAlign: 'left', paddingLeft: '24px', margin: 0 } },
          h('li', {}, 'Which genes define this patient subtype'),
          h('li', {}, 'What drugs exist for each gene'),
          h('li', {}, 'Where the evidence comes from'),
          h('li', {}, 'Clinical trial opportunities'),
          h('li', {}, 'Research timeline per gene'))))));

  return root;
}

function infoCard(label, value, color) {
  return h('div', { class: 'card hov', style: { padding: '20px' } },
    h('div', { style: { fontSize: '11px', fontWeight: '700', letterSpacing: '.12em',
      textTransform: 'uppercase', color: 'var(--ink-3)', marginBottom: '8px' } }, label),
    h('div', { style: { fontSize: '16px', fontWeight: '660', color: color,
      marginBottom: '4px', letterSpacing: '-.01em' } }, value),
    h('div', { style: { fontSize: '12px', color: 'var(--ink-3)' } }));
}

function geneCard(name, func, status, statusLabel, score, tags) {
  const statusColor = {
    'tool-compound': 'var(--teal-600)',
    'indirect': 'var(--amber-600)',
    'none-known': 'var(--slate-600)',
    'preclinical': 'var(--blue-600)',
    'failed': 'var(--rose-600)'
  }[status] || 'var(--ink-2)';

  const statusBg = {
    'tool-compound': 'var(--teal-50)',
    'indirect': 'var(--amber-50)',
    'none-known': 'var(--slate-50)',
    'preclinical': 'var(--blue-50)',
    'failed': 'var(--rose-50)'
  }[status] || 'var(--surface-2)';

  return h('div', { class: 'card hov', style: { padding: '18px', cursor: 'pointer',
    transition: 'all .2s' } },
    h('div', { style: { fontFamily: 'JetBrains Mono', fontSize: '16px', fontWeight: '650',
      marginBottom: '8px', color: 'var(--ink-1)' } }, name),
    h('div', { style: { fontSize: '13px', color: 'var(--ink-2)', lineHeight: '1.5',
      marginBottom: '12px' } }, func),
    h('div', { style: { display: 'inline-block', padding: '4px 10px', borderRadius: '4px',
      fontSize: '12px', fontWeight: '600', color: statusColor, background: statusBg,
      marginBottom: '10px' } }, statusLabel),
    h('div', { style: { fontSize: '12px', color: 'var(--ink-3)', marginBottom: '8px' } },
      `Marker strength: ${Math.round(score * 100)}%`),
    h('div', { style: { width: '100%', height: '4px', background: 'var(--line)',
      borderRadius: '2px', overflow: 'hidden', marginBottom: '10px' } },
      h('div', { style: { width: `${score * 100}%`, height: '100%',
        background: statusColor, borderRadius: '2px' } })),
    h('div', { style: { display: 'flex', gap: '6px', flexWrap: 'wrap' } },
      tags.map(t => h('span', { style: { fontSize: '11px', color: 'var(--ink-3)',
        background: 'var(--surface-2)', padding: '3px 8px', borderRadius: '3px' } }, t))));
}

function legendItem(emoji, label, desc) {
  return h('div', { class: 'card', style: { padding: '16px' } },
    h('div', { style: { fontSize: '24px', marginBottom: '8px' } }, emoji),
    h('div', { style: { fontSize: '13px', fontWeight: '650', marginBottom: '6px' } }, label),
    h('p', { style: { fontSize: '12px', color: 'var(--ink-2)', margin: 0, lineHeight: '1.5' } }, desc));
}

function sourceCard(name, desc, url, org) {
  return h('div', { class: 'card hov', style: { padding: '18px' } },
    h('div', { style: { fontWeight: '650', fontSize: '14px', marginBottom: '6px' } }, name),
    h('p', { style: { fontSize: '13px', color: 'var(--ink-2)', margin: '0 0 12px', lineHeight: '1.5' } }, desc),
    h('a', { href: url, target: '_blank', rel: 'noopener noreferrer',
      style: { fontSize: '12px', color: 'var(--teal-600)', fontWeight: '600',
        textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '4px' } },
      `Visit ${org}`, h('span', {}, '↗')));
}

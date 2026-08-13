/* HELIXA — the real processing pipeline, documented stage by stage */
import { loadAll } from '../api.js';
import { h, card, section, badge, banner, kv, esc } from '../ui.js';
import { barsH, lines } from '../charts.js';

export default async function pipeline() {
  const [stages, metrics, model, batch, project] =
    await loadAll(['pipeline', 'global_metrics', 'model', 'batch_diagnosis', 'project']);

  const root = h('div', { class: 'wrap section' });
  root.appendChild(section('Architecture', 'Processing Pipeline',
    'These are the actual stages implemented in the project. Each one names the script that ' +
    'performs it, so any claim here can be traced back to code.'));

  root.appendChild(h('div', { class: 'grid g4', style: { marginBottom: '26px' } },
    kpi(project.cohort.genes_measured.toLocaleString(), 'Gene loci measured', 'per sample'),
    kpi(project.cohort.genes_after_qc.toLocaleString(), 'After expression filter', 'low-expression removed'),
    kpi(project.cohort.genes_after_protocol_filter.toLocaleString(), 'After protocol filter',
      '2,039 protocol-sensitive genes removed'),
    kpi(project.cohort.signature_genes.toLocaleString(), 'Signature genes', 'used by the model')));

  /* ── the stages ─────────────────────────────────────────────── */
  const pipe = h('div', { class: 'pipe' });
  stages.forEach((s, i) => {
    const detail = h('div', { class: 'pdetail', hidden: true },
      h('ul', {}, s.detail.map(d => h('li', {}, d))),
      s.script && s.script !== '—'
        ? h('div', { style: { marginTop: '11px', paddingTop: '10px', borderTop: '1px solid var(--line)' } },
            kv('Implementation', h('span', { class: 'mono', style: { fontSize: '11.5px' } }, s.script)))
        : null);
    const st = h('div', { class: 'pstage done clk' },
      h('div', { class: 'prail' }, h('div', { class: 'pdot' }, '✓'),
        i < stages.length - 1 ? h('div', { class: 'pline' }) : null),
      h('div', { class: 'pbody' },
        h('div', { class: 'pname' }, s.name, badge('mut', `stage ${i + 1}`)),
        h('div', { class: 'pdesc' }, s.desc),
        h('div', { class: 'pmeta' },
          h('span', { style: { fontSize: '11.5px', color: 'var(--mint-500)', fontWeight: '600' } },
            detail.hidden ? 'Click for detail ▾' : '')),
        detail));
    st.querySelector('.pbody').addEventListener('click', () => {
      detail.hidden = !detail.hidden;
      st.querySelector('.pmeta span').textContent = detail.hidden ? 'Click for detail ▾' : 'Hide detail ▴';
    });
    pipe.appendChild(st);
  });
  root.appendChild(card('End-to-end stages', 'Click any stage to expand its implementation detail', pipe));

  /* ── the batch-effect story ─────────────────────────────────── */
  const b = batch.summary;
  root.appendChild(h('div', { style: { marginTop: '30px' } },
    section('Quality Control', 'The batch effect that had to be corrected first',
      'Before any subtype could be trusted, a decisive technical artefact had to be removed. ' +
      'This is the single most important quality-control step in the project.')));

  root.appendChild(h('div', { class: 'grid g2' },
    card('What was found', 'The dominant split in the raw data was not biology',
      h('div', {},
        banner('warn',
          '<b>The strongest signal in the uncorrected data was library preparation, not tumour biology.</b> ' +
          'Two protocols were mixed in the cohort, and a single threshold on non-polyadenylated RNA ' +
          'content separated them almost perfectly.'),
        h('div', { style: { marginTop: '15px' } },
          kv('poly(A)-selected libraries', `${b.n_polyA} samples · ${(b.polyA_mean_frac * 100).toFixed(2)}% non-polyA RNA`),
          kv('total-RNA libraries', `${b.n_totalRNA} samples · ${(b.totalRNA_mean_frac * 100).toFixed(2)}% non-polyA RNA`),
          kv('Separation', `${b.separation_x.toFixed(0)}× difference`),
          kv('Residual batch signal after correction',
            h('span', { style: { color: 'var(--ok)', fontWeight: '700' } }, metrics.batch_ARI_MUST_BE_ZERO.toFixed(4)))),
        h('p', { class: 'card-d', style: { marginTop: '13px' } },
          'Left uncorrected, the pipeline would have "discovered" the sequencing protocol and ' +
          'presented it as a molecular subtype.'))),
    card('Genes that drove the artefact', 'Top discriminating genes between the two protocols',
      h('div', {},
        barsH(batch.top_genes.slice(0, 12).map(g => ({
          label: g.gene, value: Math.abs(g.t),
          color: g.log2FC_g0_minus_g1 < 0 ? '#C46E3C' : '#0EAE8F',
          note: `log2FC ${g.log2FC_g0_minus_g1?.toFixed(2)} · ${g.gene_type}`,
        })), { w: 470, rowH: 27, pad: { t: 6, r: 60, b: 24, l: 108 },
               fmt: v => v.toFixed(0), label: '|t statistic|' }),
        h('p', { class: 'card-d', style: { marginTop: '11px' } },
          'These are almost all non-polyadenylated RNA species — 7SK, 7SL, snoRNA, scaRNA and ' +
          'replication-dependent histones — exactly the family that poly(A) selection removes ' +
          'and rRNA-depletion retains.')))));

  /* ── the three-layer fix ────────────────────────────────────── */
  root.appendChild(h('div', { style: { marginTop: '20px' } },
    card('The three-layer correction', 'Each layer is necessary; removing genes alone is not enough',
      h('div', { class: 'grid g3', style: { gap: '15px' } },
        layer('L1', 'Gene-space filter',
          'Every gene family whose capture depends on the protocol is removed: replication-dependent ' +
          'histones, 7SK, 7SL/SRP, snoRNA, scaRNA, snRNA and mitochondrial genes.',
          '2,039 genes removed → 25,738 retained'),
        layer('L2', 'Re-normalisation',
          'TPM is compositional. Because 55% of the total-RNA libraries\' budget was spent on ' +
          'non-polyA RNA, every ordinary mRNA was compressed ~2× for purely arithmetic reasons. ' +
          'Deleting genes does not undo that — TPM is recomputed over the retained space.',
          'common 1e6 budget restored'),
        layer('L3', 'Within-batch standardisation',
          'Residual protocol-specific per-gene bias is removed by centring and scaling each gene ' +
          'within each batch before pooling. Biological variation survives because it exists inside ' +
          'both batches; only the systematic offset between them is removed.',
          'batch signal 11.07 → 0.0000')))));

  /* ── model robustness ───────────────────────────────────────── */
  const npc = Object.entries(model.robustness.acc_vs_npcs).map(([k, v]) => [Number(k), v]);
  const ngn = Object.entries(model.robustness.acc_vs_ngenes).map(([k, v]) => [Number(k), v]);

  root.appendChild(h('div', { style: { marginTop: '30px' } },
    section('Robustness', 'The result does not depend on a lucky setting',
      'Both the embedding dimensionality and the gene-panel size were swept. Performance is stable ' +
      'across a wide range.')));

  root.appendChild(h('div', { class: 'grid g2' },
    card('Accuracy vs. number of principal components', 'Chosen: 5',
      lines([{ name: 'CV accuracy', points: npc, color: '#0EAE8F' }],
        { w: 520, h: 280, xLabel: 'principal components', yLabel: 'cross-validated accuracy',
          yFmt: v => (v * 100).toFixed(0) + '%', xFmt: v => String(v),
          markers: [{ x: 5, label: 'chosen' }] })),
    card('Accuracy vs. signature-panel size', 'Chosen: 1,000 genes',
      lines([{ name: 'CV accuracy', points: ngn, color: '#2A9D8F' }],
        { w: 520, h: 280, xLabel: 'signature genes', yLabel: 'cross-validated accuracy',
          yFmt: v => (v * 100).toFixed(0) + '%', xFmt: v => v >= 1000 ? (v / 1000) + 'k' : String(v),
          markers: [{ x: 1000, label: 'chosen' }] }))));

  root.appendChild(h('div', { style: { marginTop: '26px' } },
    h('a', { class: 'btn btn-p', href: '#/analyze' }, 'Run this pipeline on a new patient →')));

  return root;
}

function kpi(v, l, s) {
  return h('div', { class: 'card' },
    h('div', { class: 'stat-v', style: { fontSize: '25px' } }, v),
    h('div', { class: 'stat-l' }, l),
    s ? h('div', { class: 'stat-sub' }, s) : null);
}
function layer(tag, title, body, foot) {
  return h('div', { style: { padding: '17px', background: 'var(--surface-2)', borderRadius: '13px',
    border: '1px solid var(--line)' } },
    h('div', { style: { display: 'flex', alignItems: 'center', gap: '9px', marginBottom: '9px' } },
      h('span', { style: { background: 'var(--teal-900)', color: '#fff', fontSize: '11px',
        fontWeight: '700', padding: '3px 9px', borderRadius: '6px' } }, tag),
      h('div', { style: { fontWeight: '650', fontSize: '14px' } }, title)),
    h('p', { style: { fontSize: '12.5px', color: 'var(--ink-2)', lineHeight: '1.62', margin: 0 } }, body),
    h('div', { style: { marginTop: '11px', fontSize: '11.5px', fontWeight: '650',
      color: 'var(--mint-500)' } }, foot));
}

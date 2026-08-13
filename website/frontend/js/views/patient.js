/* HELIXA — single patient profile */
import { loadAll, fmtNum } from '../api.js';
import { h, card, section, badge, banner, kv, esc } from '../ui.js';
import { barsH, gauge, scatter, legend, heatmap } from '../charts.js';

export default async function patient({ param }) {
  const [clusters, all, emb, markers] = await loadAll(['clusters', 'patients', 'embedding', 'markers']);
  const cmap = Object.fromEntries(clusters.map(c => [c.id, c]));
  const p = all.find(x => x.id === param || x.sample_id === param || x.short_id === param);

  const root = h('div', { class: 'wrap section' });
  if (!p) {
    root.appendChild(banner('err', `<b>Patient not found.</b> No record matches “${esc(param)}”.`));
    root.appendChild(h('div', { style: { marginTop: '16px' } },
      h('a', { class: 'btn btn-s', href: '#/patients' }, '← Back to the cohort')));
    return root;
  }
  const c = cmap[p.cluster];
  const idx = all.indexOf(p);
  const pt = emb.points[idx];

  root.appendChild(h('a', { href: '#/patients',
    style: { fontSize: '13.5px', color: 'var(--ink-3)', display: 'inline-block', marginBottom: '14px' } },
    '← Back to the cohort'));

  root.appendChild(h('div', { style: { display: 'flex', alignItems: 'flex-start', gap: '18px',
    flexWrap: 'wrap', marginBottom: '26px' } },
    h('div', { style: { flex: '1', minWidth: '260px' } },
      h('div', { class: 'eyebrow' }, 'Patient profile'),
      h('h2', { class: 'h-sec', style: { marginBottom: '7px' } }, p.id),
      h('div', { class: 'mono', style: { color: 'var(--ink-3)', fontSize: '13px', wordBreak: 'break-all' } },
        p.sample_id)),
    h('div', { style: { display: 'flex', gap: '8px', flexWrap: 'wrap' } },
      p.is_core ? badge('ok', 'High-confidence assignment') : badge('warn', 'Boundary tumour'),
      badge('info', p.library_batch))));

  /* ── headline: type / class / confidence ────────────────────── */
  root.appendChild(h('div', { class: 'grid g3', style: { marginBottom: '20px' } },
    card('Patient Type', 'Tumour programme',
      h('div', {},
        h('div', { style: { display: 'flex', alignItems: 'center', gap: '11px' } },
          h('span', { style: { width: '15px', height: '15px', borderRadius: '4px', background: c.color } }),
          h('div', { class: 'stat-v', style: { fontSize: '23px' } }, c.title)),
        h('div', { class: 'stat-l', style: { marginTop: '9px' } }, c.pathway_identity.replace(/_/g, ' ')))),
    card('Patient Class', 'Assigned molecular subtype',
      h('div', {},
        h('div', { class: 'stat-v', style: { fontSize: '23px' } }, `${c.label} · cluster_${c.id}`),
        h('div', { class: 'stat-l' }, c.name),
        h('div', { style: { marginTop: '11px' } },
          kv('Nearest Verhaak', p.verhaak_nearest || '—'),
          kv('Cohort prevalence', `${c.n_patients} · ${c.pct_of_cohort}%`)))),
    card('Assignment confidence', 'Consensus membership over 1,000 resamplings',
      h('div', {},
        gauge(p.consensus_membership ?? 0, { label: 'Consensus membership', size: 206 }),
        h('div', { style: { marginTop: '4px' } },
          kv('Own-cluster consensus', fmtNum(p.consensus_own, 4)),
          kv('Best other cluster', fmtNum(p.consensus_best_other, 4)),
          kv('Silhouette', fmtNum(p.silhouette, 4)))))));

  /* ── genomic signatures ─────────────────────────────────────── */
  const sigRows = Object.entries(p.signatures).map(([k, v], i) => ({
    label: k, value: Math.abs(v ?? 0), color: (v ?? 0) >= 0 ? '#0EAE8F' : '#C46E3C',
    note: `z = ${fmtNum(v, 3)}${(v ?? 0) >= 0 ? ' (elevated)' : ' (reduced)'}`,
  })).sort((a, b) => b.value - a.value);

  const pwRows = Object.entries(p.pathways).map(([k, v]) => ({
    label: k.replace(/_/g, ' '), value: Math.abs(v ?? 0),
    color: (v ?? 0) >= 0 ? '#0EAE8F' : '#C46E3C',
    note: `z = ${fmtNum(v, 3)}${(v ?? 0) >= 0 ? ' (elevated)' : ' (reduced)'}`,
  })).sort((a, b) => b.value - a.value);

  root.appendChild(h('div', { class: 'grid g2', style: { marginBottom: '20px' } },
    card('Molecular subtype signatures', 'Published Verhaak signature scores for this patient (|z|)',
      h('div', {}, barsH(sigRows, { w: 470, rowH: 36, pad: { t: 6, r: 66, b: 24, l: 108 },
        fmt: v => v.toFixed(3), label: '|z-score|' }),
        h('p', { class: 'card-d', style: { marginTop: '10px' } },
          'Teal = elevated, amber = reduced relative to the cohort. Hover for the signed z-score.'))),
    card('Pathway activity profile', 'Hallmark / lineage pathway proxies for this patient (|z|)',
      h('div', {}, barsH(pwRows, { w: 470, rowH: 34, pad: { t: 6, r: 66, b: 24, l: 150 },
        fmt: v => v.toFixed(3), label: '|z-score|' })))));

  /* ── position on the map ────────────────────────────────────── */
  root.appendChild(h('div', { class: 'grid g2', style: { marginBottom: '20px' } },
    card('Position in the cohort', 'This patient highlighted on the real principal-component map',
      h('div', {},
        scatter(emb.points.map(q => ({ ...q, name: cmap[q.c].title })),
          { w: 560, h: 380, colors: clusters.map(x => x.color),
            highlight: pt ? { x: pt.x, y: pt.y, label: p.id } : null,
            onPick: q => { const t = all.find(x => x.sample_id.startsWith(q.sid));
                           if (t && t.id !== p.id) location.hash = `#/patient/${t.id}`; } }),
        legend(clusters.map(x => ({ label: x.label, color: x.color }))))),
    h('div', { class: 'grid', style: { gap: '18px', alignContent: 'start' } },
      card('Subtype marker genes', `Top differential genes defining ${c.label}`,
        h('div', { style: { display: 'flex', gap: '7px', flexWrap: 'wrap' } },
          (markers[`cluster_${c.id}`] || []).slice(0, 22).map(m =>
            h('span', { class: 'badge b-mut', style: { fontFamily: 'var(--mono)', fontSize: '11.5px' } },
              m.gene || m.Gene || m.gene_name || Object.values(m)[1])))),
      card('Technical record', null,
        h('div', {},
          kv('Sample UUID', h('span', { class: 'mono', style: { fontSize: '11.5px' } }, p.sample_id)),
          kv('Library protocol', p.library_batch),
          kv('Core / boundary', p.is_core ? 'core (high confidence)' : 'boundary (intermediate)'),
          kv('Processing status', badge('ok', 'analysed')),
          pt ? kv('PC coordinates', `${pt.x}, ${pt.y}, ${pt.z}`) : null)))));

  /* ── subtype context ────────────────────────────────────────── */
  root.appendChild(card('Subtype characterisation',
    'From the project\'s own biological validation of this subtype',
    h('div', {},
      h('p', { style: { fontSize: '14px', lineHeight: '1.72', color: 'var(--ink-2)' } }, c.description),
      h('div', { style: { display: 'flex', gap: '9px', flexWrap: 'wrap', marginTop: '15px' } },
        badge('info', `Verhaak: ${c.verhaak_identity}`),
        badge('info', `Pathway: ${c.pathway_identity.replace(/_/g, ' ')}`),
        badge('mut', `Mean silhouette ${c.mean_silhouette.toFixed(4)}`),
        badge('mut', `${c.n_core} core / ${c.n_boundary} boundary`)),
      !p.is_core ? h('div', { style: { marginTop: '15px' } },
        banner('warn', '<b>Boundary tumour.</b> This patient sits between subtypes. The assignment ' +
          'is reported with reduced confidence rather than forced — roughly 17% of the cohort is ' +
          'genuinely intermediate.')) : null)));

  return root;
}

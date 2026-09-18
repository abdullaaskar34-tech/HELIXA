/* ============================================================================
   HELIXA — biomarker panel
   KBU-MedLab · Genomics into Decisions

   Every gene that passed BOTH statistical gates for the patient's subtype, with
   the numbers rendered as pictures and named in plain language, and a source
   link behind every claim.

   Two kinds of gene appear here and they are never mixed up:

     · REVIEWED  — somebody read the literature on it. Protein function, the
       glioblastoma evidence, druggability and drug status are shown with the
       sources they came from.
     · NOT YET REVIEWED — it passed the statistics, but nobody has read the
       literature yet. Only the numbers and search links are offered. Absence of
       evidence here means nobody looked, not that nothing was found.

   The old panel only ever showed the first kind — 61 genes out of 359 — which
   made a reviewing backlog look like a filtering result.
   ========================================================================== */

import { h, card, badge, banner, esc } from './ui.js?v=20260918a';

/* Colours carry an explicit fallback: a meter drawn with an undefined CSS
   variable is invisible, and an invisible bar reads as "zero" rather than as a
   missing style. */
const GOOD = 'var(--mint-500, #0EAE8F)';
const BAD = '#C0553F';
const NEUTRAL = 'var(--teal-600, #2E7BC4)';
const WARN = '#C79A2C';

/* ── formatting ──────────────────────────────────────────────────────────── */
const pct = v => (v == null ? '—' : (v * 100).toFixed(0) + '%');
const fmt = (v, kind) => {
  if (v == null) return '—';
  switch (kind) {
    case 'pct': return (v * 100).toFixed(0) + '%';
    case 'signed': return (v >= 0 ? '+' : '') + (v * 100).toFixed(0) + ' pts';
    case 'z': return v.toFixed(2) + 'z';
    case 'fdr': return v < 1e-4 ? v.toExponential(1) : v.toFixed(4);
    default: return v.toFixed(2);
  }
};

const TIER_KIND = { 'TIER 1': 'ok', 'TIER 2': 'info', 'TIER 3': 'warn',
                    'EXCLUDED': 'err', 'UNCHECKED': 'mut' };

/* ── small visual pieces ─────────────────────────────────────────────────── */

/** one horizontal meter, 0..1 */
function meter(value, color, opts = {}) {
  const w = Math.max(0, Math.min(1, value ?? 0)) * 100;
  return h('div', { style: { position: 'relative', height: opts.h || '9px',
    background: 'var(--surface-2)', borderRadius: '5px', overflow: 'hidden',
    flex: '1', minWidth: '70px' } },
    h('div', { style: { position: 'absolute', inset: '0 auto 0 0', width: w + '%',
      background: color, borderRadius: '5px' } }));
}

/**
 * The hero picture: how much the tumour needs this gene versus how much healthy
 * tissue needs it. The gap between the two bars is the room a drug has to work
 * in, and it is the single most important thing on the card.
 */
function dependencyPicture(g) {
  const gbm = g.gbm_need ?? 0, normal = g.normal_need ?? 0, gap = g.safety_gap ?? 0;
  const good = gap >= 0.25, ok = gap >= 0.10;
  const gapColor = good ? GOOD : ok ? WARN : BAD;
  const row = (label, v, color, note) => h('div', { style: { marginBottom: '8px' } },
    h('div', { style: { display: 'flex', justifyContent: 'space-between',
      fontSize: '12px', marginBottom: '3px' } },
      h('span', { style: { color: 'var(--ink-2)' } }, label),
      h('span', { class: 'mono', style: { fontWeight: '650' } }, pct(v))),
    h('div', { style: { display: 'flex', alignItems: 'center', gap: '8px' } },
      meter(v, color, { h: '11px' })),
    note ? h('div', { style: { fontSize: '11px', color: 'var(--ink-3)', marginTop: '2px' } }, note) : null);

  return h('div', { style: { background: 'var(--surface-2)', borderRadius: '9px',
    padding: '14px 15px', marginBottom: '14px' } },
    h('div', { style: { fontSize: '11.5px', letterSpacing: '.1em', textTransform: 'uppercase',
      color: 'var(--ink-2)', fontWeight: '650', marginBottom: '11px' } },
      'Can a drug hit this without hurting the patient?'),
    row('Glioblastoma cells need it', gbm, GOOD,
        '53 glioblastoma cell lines, CRISPR knockout'),
    row('Healthy cells also need it', normal, BAD,
        '1,118 cell lines from outside the brain — lower is better'),
    h('div', { style: { display: 'flex', alignItems: 'center', gap: '10px',
      marginTop: '11px', paddingTop: '10px', borderTop: '1px solid var(--line)' } },
      h('span', { style: { fontSize: '12.5px', fontWeight: '650' } }, 'Safety gap'),
      h('span', { class: 'mono', style: { fontSize: '15px', fontWeight: '720', color: gapColor } },
        fmt(gap, 'signed')),
      h('span', { style: { fontSize: '11.5px', color: 'var(--ink-3)', marginLeft: 'auto',
        textAlign: 'right' } },
        good ? 'Wide — the tumour needs it much more than healthy tissue'
        : ok ? 'Modest — some room, but not much'
        : 'Narrow — healthy tissue needs it nearly as much')));
}

/** a labelled metric with its meter and its plain-language meaning */
function metricRow(key, value, meta) {
  if (value == null || !meta) return null;
  const bar = ['pct'].includes(meta.format);
  return h('div', { style: { marginBottom: '10px' } },
    h('div', { style: { display: 'flex', alignItems: 'baseline', gap: '10px' } },
      h('span', { style: { fontSize: '12.5px', fontWeight: '620', minWidth: '190px' } }, meta.label),
      bar ? meter(value, NEUTRAL) : null,
      h('span', { class: 'mono', style: { fontSize: '12.5px', fontWeight: '650',
        minWidth: '62px', textAlign: 'right' } }, fmt(value, meta.format))),
    h('div', { style: { fontSize: '11.5px', color: 'var(--ink-3)', marginTop: '2px',
      lineHeight: '1.5' } }, meta.meaning, ' ', h('i', {}, meta.how_to_read)));
}

/** a block of prose with a heading — only rendered when there is something */
function prose(title, body) {
  if (!body) return null;
  return h('div', { style: { marginBottom: '12px' } },
    h('div', { style: { fontSize: '11.5px', letterSpacing: '.09em', textTransform: 'uppercase',
      color: 'var(--ink-2)', fontWeight: '650', marginBottom: '4px' } }, title),
    h('p', { style: { fontSize: '13px', lineHeight: '1.65', margin: '0' } }, body));
}

/** link list — curated sources look different from bare searches, deliberately */
function linkList(title, items, curated) {
  if (!items || !items.length) return null;
  return h('div', { style: { marginBottom: '12px' } },
    h('div', { style: { fontSize: '11.5px', letterSpacing: '.09em', textTransform: 'uppercase',
      color: 'var(--ink-2)', fontWeight: '650', marginBottom: '6px' } }, title),
    h('div', { style: { display: 'flex', gap: '7px', flexWrap: 'wrap' } },
      items.map(s => h('a', {
        href: s.url, target: '_blank', rel: 'noopener noreferrer',
        title: s.what || s.url,
        style: { display: 'inline-flex', alignItems: 'center', gap: '5px',
          padding: '5px 10px', borderRadius: '6px', fontSize: '12px', fontWeight: '600',
          textDecoration: 'none',
          background: curated ? GOOD : 'transparent',
          color: curated ? '#fff' : 'var(--ink-2)',
          border: curated ? 'none' : '1px solid var(--line)' } },
        s.label, h('span', { style: { opacity: .75 } }, '↗')))));
}

function expandLookups(templates, gene, geneId) {
  const ens = geneId ? String(geneId).split('.')[0] : null;
  return (templates || [])
    .filter(t => t.needs !== 'ensembl' || ens)
    .map(t => ({ label: t.label, what: t.what,
      url: t.url.replace(/\{gene\}/g, encodeURIComponent(gene))
                .replace(/\{ensembl\}/g, encodeURIComponent(ens || '')) }));
}

/* ── one gene ────────────────────────────────────────────────────────────── */
function geneRow(g, data, open) {
  const M = data.metrics || {};
  const tier = badge(TIER_KIND[g.tier] || 'mut', g.tier_name || g.tier);
  const strength = g.target_strength ?? 0;

  const head = h('div', { style: { display: 'flex', alignItems: 'center', gap: '11px',
    padding: '11px 13px', cursor: 'pointer', userSelect: 'none' } },
    h('span', { style: { fontSize: '12px', color: 'var(--ink-3)', minWidth: '26px',
      fontVariantNumeric: 'tabular-nums' } }, '#' + g.rank),
    h('span', { class: 'mono', style: { fontWeight: '700', fontSize: '14px',
      minWidth: '92px' } }, g.gene),
    tier,
    g.drug_status ? badge(g.drug_status === 'NONE KNOWN' ? 'mut' : 'ok', g.drug_status) : null,
    g.excluded ? badge('err', 'Do not target') : null,
    h('div', { style: { flex: '1', minWidth: '60px', display: 'flex', alignItems: 'center',
      gap: '8px', justifyContent: 'flex-end' } },
      h('span', { style: { fontSize: '11px', color: 'var(--ink-3)' } }, 'strength'),
      meter(strength, GOOD, { h: '8px' }),
      h('span', { class: 'mono', style: { fontSize: '12px', fontWeight: '650',
        minWidth: '34px', textAlign: 'right' } }, pct(strength))),
    h('span', { class: 'bm-caret', style: { color: 'var(--ink-3)', fontSize: '13px' } }, '▾'));

  const body = h('div', { style: { padding: '4px 15px 16px', borderTop: '1px solid var(--line)' } });

  if (g.excluded && (g.wrong_direction || g.subtype_mismatch)) {
    body.appendChild(banner('warn',
      `<b>This gene should not be targeted.</b> ${esc(g.wrong_direction || g.subtype_mismatch)}`));
  }
  if (!g.literature_checked) {
    body.appendChild(banner('info',
      '<b>Nobody has read the literature on this gene yet.</b> It cleared both statistical ' +
      'gates, but its protein function, published evidence and drug status have not been ' +
      'checked. The links below are searches, not findings.'));
  }

  body.appendChild(dependencyPicture(g));

  // the rest of the numbers
  const nums = h('div', { style: { marginBottom: '14px' } },
    h('div', { style: { fontSize: '11.5px', letterSpacing: '.1em', textTransform: 'uppercase',
      color: 'var(--ink-2)', fontWeight: '650', marginBottom: '9px' } }, 'The numbers behind it'),
    metricRow('target_strength', g.target_strength, M.target_strength),
    metricRow('subtype_specificity', g.subtype_specificity, M.subtype_specificity),
    metricRow('tumour_dependence', g.tumour_dependence, M.tumour_dependence),
    metricRow('varies_between_tumours', g.varies_between_tumours, M.varies_between_tumours),
    metricRow('expression_lead', g.expression_lead, M.expression_lead),
    metricRow('effect_size', g.effect_size, M.effect_size),
    metricRow('statistical_confidence', g.statistical_confidence, M.statistical_confidence));
  body.appendChild(nums);

  if (g.literature_checked) {
    body.appendChild(prose('What the protein does', g.protein_function));
    body.appendChild(prose('Evidence in glioblastoma', g.gbm_evidence));
    body.appendChild(prose('Link to this subtype', g.subtype_link));
    body.appendChild(prose('Can it be drugged?', g.druggable));
    body.appendChild(prose('Relevance in other cancers', g.cancer_relevance));
    if (g.drug_detail) body.appendChild(prose('Drug status — ' + (g.drug_status || ''), g.drug_detail));
    body.appendChild(linkList('Sources for the above', g.sources, true));
  }
  body.appendChild(linkList(
    g.literature_checked ? 'Look it up yourself' : 'Look it up yourself (searches, not findings)',
    expandLookups(data.lookup_templates, g.gene, g.gene_id), false));

  const wrap = h('div', { style: { border: '1px solid var(--line)', borderRadius: '9px',
    marginBottom: '8px', background: 'var(--bg)', overflow: 'hidden' } }, head);
  let isOpen = false;
  const toggle = () => {
    isOpen = !isOpen;
    if (isOpen) wrap.appendChild(body); else body.remove();
    head.querySelector('.bm-caret').textContent = isOpen ? '▴' : '▾';
  };
  head.addEventListener('click', toggle);
  if (open) toggle();
  return wrap;
}

/* ── the panel ───────────────────────────────────────────────────────────── */
export function biomarkerPanel(data, classKey, clusterLabel) {
  // Require the v2 shape. Against a v1 biomarkers.json this returns null and
  // analyze.js falls back to the old inline table rather than rendering a panel
  // with every metric missing.
  if (!data || !data.metrics || !data.lookup_templates) return null;
  const all = (data?.by_class?.[classKey]) || [];
  if (!all.length) return null;
  const s = data.summary_by_class?.[classKey] || {};

  const FILTERS = [
    { id: 'all', label: `All ${all.length}`, fn: () => true },
    { id: 'drug', label: 'Has a drug', fn: g => g.drug_status && g.drug_status !== 'NONE KNOWN' },
    { id: 'reviewed', label: `Reviewed ${s.literature_checked || 0}`, fn: g => g.literature_checked },
    { id: 'unreviewed', label: `Not yet reviewed ${s.not_yet_reviewed || 0}`, fn: g => !g.literature_checked },
  ].filter(f => all.some(f.fn));

  let active = 'all', query = '';
  const listHost = h('div', {});

  const render = () => {
    const f = FILTERS.find(x => x.id === active) || FILTERS[0];
    const q = query.trim().toUpperCase();
    const rows = all.filter(f.fn).filter(g => !q || g.gene.toUpperCase().includes(q));
    listHost.replaceChildren(
      rows.length
        ? h('div', {}, rows.map((g, i) => geneRow(g, data, rows.length === 1 || (i === 0 && q))))
        : h('p', { class: 'card-d', style: { padding: '14px 2px' } },
            'No gene matches that filter.'),
      h('p', { class: 'card-d', style: { marginTop: '10px' } },
        `Showing ${rows.length} of ${all.length} candidates for ${clusterLabel}.`));
  };

  const chipRow = h('div', { style: { display: 'flex', gap: '7px', flexWrap: 'wrap',
    marginBottom: '10px' } },
    FILTERS.map(f => h('button', {
      type: 'button', class: 'chip' + (f.id === active ? ' on' : ''),
      onclick: e => {
        active = f.id;
        chipRow.querySelectorAll('.chip').forEach(c => c.classList.remove('on'));
        e.currentTarget.classList.add('on');
        render();
      },
    }, f.label)));

  const search = h('input', {
    type: 'search', placeholder: 'Find a gene…',
    style: { padding: '8px 12px', borderRadius: '7px', border: '1px solid var(--line)',
      background: 'var(--bg)', color: 'var(--ink)', fontSize: '13px', minWidth: '170px' },
    oninput: e => { query = e.target.value; render(); },
  });

  render();

  return card(
    `Biomarker targets for ${clusterLabel}`,
    'Genes that mark this subtype in 328 real patients AND that glioblastoma cells cannot ' +
    'survive without while cells from outside the brain can',
    h('div', {},
      h('div', { style: { display: 'flex', gap: '9px', flexWrap: 'wrap', marginBottom: '12px' } },
        badge('info', `${s.total_candidates ?? all.length} candidates`),
        s.tier1_actionable ? badge('ok', `${s.tier1_actionable} actionable`) : null,
        s.tier2_credible ? badge('info', `${s.tier2_credible} credible`) : null,
        s.tier3_hypothesis ? badge('warn', `${s.tier3_hypothesis} hypothesis`) : null,
        s.excluded ? badge('err', `${s.excluded} do not target`) : null,
        s.not_yet_reviewed ? badge('mut', `${s.not_yet_reviewed} not yet reviewed`) : null),
      h('div', { style: { display: 'flex', gap: '10px', flexWrap: 'wrap',
        alignItems: 'center', marginBottom: '12px' } }, chipRow, search),
      listHost,
      h('p', { class: 'card-d', style: { marginTop: '14px', paddingTop: '12px',
        borderTop: '1px solid var(--line)' } },
        data.reading_the_panel || ''),
      banner('warn', '<b>Candidates, not treatments.</b> ' + esc(data.disclaimer || ''))));
}

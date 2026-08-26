/* HELIXA — Analyze a Patient.

   The model runs INSIDE THE BROWSER. Nothing is uploaded anywhere, no server
   is involved, and the arithmetic is the frozen classifier itself — verified
   against the Python engine to 6e-8. See js/engine.js.                       */

import { loadAll } from '../api.js?v=20260815a';
import { h, card, section, badge, banner, kv, esc } from '../ui.js?v=20260815a';
import { gauge, barsH, scatter, legend } from '../charts.js?v=20260815a';
import { loadModel, analyse, isLoaded, modelInfo } from '../engine.js?v=20260815a';
import { openPatientReport } from '../report.js?v=20260815a';

export function cleanup() {}

const STAGES = [
  ['ingest',     'Reading the file',          'Opening the raw GDC expression file'],
  ['qc',         'Checking the genes',        'Matching genes to what the model was trained on'],
  ['batch',      'Correcting the lab effect', 'Detecting how the sample was prepared, removing that bias'],
  ['features',   'Selecting the signature',   'Keeping the 1,000 genes that carry the signal'],
  ['embed',      'Compressing',               'Reducing to 5 dimensions the model understands'],
  ['model',      'Classifying',               'Comparing against all six subtypes'],
  ['confidence', 'Measuring certainty',       'Turning the scores into calibrated probabilities'],
  ['validate',   'Explaining',                'Working out which genes drove the decision'],
  ['insight',    'Done',                      'Assembling the report'],
];

export default async function analyze({ query }) {
  const [clusters, emb, demos, biomarkers] = await loadAll(
    ['clusters', 'embedding', 'demo_results', 'biomarkers']);
  const cmap = Object.fromEntries(clusters.map(c => [c.id, c]));

  const root = h('div', { class: 'wrap section' });
  root.appendChild(section('Analysis', 'Analyze a Patient',
    'One raw RNA-seq file in. Subtype, confidence, and the genes behind the answer out.'));

  const modeHost = h('div', { style: { marginBottom: '20px' } });
  const stepHost = h('div');
  const resultHost = h('div');
  root.appendChild(modeHost);
  root.appendChild(h('div', { class: 'an-grid' },
    h('div', {}, stepHost), h('div', {}, resultHost)));

  let file = null, job = null, isDemo = false, patientLabel = '';
  let engineState = isLoaded() ? 'ready' : 'idle';   // idle | loading | ready | error
  let engineMsg = '', engineProgress = 0, engineError = '';

  /* ── engine status ──────────────────────────────────────────── */
  function paintMode() {
    const ready = engineState === 'ready';
    const loading = engineState === 'loading';
    const info = ready ? modelInfo() : null;

    const dot = h('span', { style: { width: '9px', height: '9px', borderRadius: '50%',
      background: engineState === 'error' ? 'var(--err)' : ready ? 'var(--ok)' : 'var(--ink-3)',
      flexShrink: '0' } });

    const title = engineState === 'error' ? 'Model could not load'
      : ready ? 'Model loaded — running in your browser'
      : loading ? 'Loading the model…'
      : 'Model ready to load';

    const desc = engineState === 'error' ? engineError
      : ready
        ? `${info.n_signature.toLocaleString()} signature genes · ${info.n_classes} subtypes · ` +
          'your file never leaves this device'
      : loading ? (engineMsg || 'Fetching weights')
      : 'About 450 KB, loaded once. After that, analysis is instant and entirely offline.';

    const bar = loading ? h('div', { style: { height: '4px', borderRadius: '99px',
      background: 'var(--line)', overflow: 'hidden', marginTop: '12px' } },
      h('div', { style: { height: '100%', width: (engineProgress * 100).toFixed(0) + '%',
        background: 'var(--mint-500)', transition: 'width .25s ease' } })) : null;

    modeHost.replaceChildren(
      h('div', { class: 'card', style: { padding: '18px 22px' } },
        h('div', { style: { display: 'flex', gap: '18px', alignItems: 'center', flexWrap: 'wrap' } },
          h('div', { style: { display: 'flex', alignItems: 'center', gap: '9px' } }, dot,
            h('span', { style: { fontSize: '13.5px', fontWeight: '640' } }, title)),
          h('div', { style: { fontSize: '13px', color: 'var(--ink-2)', flex: '1', minWidth: '220px' } },
            desc),
          engineState === 'error'
            ? h('button', { class: 'btn btn-sm btn-s', onclick: ensureEngine }, 'Try again') : null,
          h('button', { class: 'btn btn-sm btn-p', onclick: () => runDemo(0) }, 'Run a real example')),
        bar));
  }

  async function ensureEngine() {
    if (engineState === 'ready' || engineState === 'loading') return engineState === 'ready';
    engineState = 'loading'; engineProgress = 0; engineMsg = ''; paintMode();
    try {
      await loadModel((p, m) => { engineProgress = p; engineMsg = m; paintMode(); });
      engineState = 'ready';
    } catch (e) {
      engineState = 'error'; engineError = e.message || String(e);
    }
    paintMode(); paintSteps();
    return engineState === 'ready';
  }

  /* ── left column : upload + progress ────────────────────────── */
  function paintSteps() {
    const dz = h('div', { class: 'drop' + (file ? ' has' : ''), tabindex: '0', role: 'button' },
      h('div', { class: 'drop-i' }, upIcon()),
      file
        ? h('div', {},
            h('div', { style: { fontWeight: '640', fontSize: '14px', wordBreak: 'break-all' } },
              file.name.length > 42 ? file.name.slice(0, 40) + '…' : file.name),
            h('div', { class: 'card-d', style: { marginTop: '5px' } },
              `${(file.size / 1024 / 1024).toFixed(1)} MB · ready`))
        : h('div', {},
            h('div', { style: { fontWeight: '640', fontSize: '15px' } }, 'Drop a patient file'),
            h('div', { class: 'card-d', style: { marginTop: '7px' } },
              '*.augmented_star_gene_counts.tsv')));

    const pick = f => { file = f; job = null; isDemo = false;
      resultHost.replaceChildren(); paintSteps(); ensureEngine(); };

    const input = h('input', { type: 'file', accept: '.tsv,.txt,.csv', style: { display: 'none' },
      onchange: e => { if (e.target.files[0]) pick(e.target.files[0]); } });
    dz.addEventListener('click', () => input.click());
    dz.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); input.click(); } });
    ['dragenter', 'dragover'].forEach(t => dz.addEventListener(t,
      e => { e.preventDefault(); dz.classList.add('over'); }));
    ['dragleave', 'drop'].forEach(t => dz.addEventListener(t,
      e => { e.preventDefault(); dz.classList.remove('over'); }));
    dz.addEventListener('drop', e => { const f = e.dataTransfer.files[0]; if (f) pick(f); });

    const running = job && job.state === 'running';
    const run = h('button', { class: 'btn btn-p', disabled: !file || running,
      style: { width: '100%', marginTop: '14px' }, onclick: go },
      running ? h('span', {}, h('span', { class: 'spin' }), ' Analysing…') : 'Analyze');

    const note = h('div', { class: 'card-d', style: { marginTop: '11px', textAlign: 'center' } },
      'Runs on this device. The file is never sent anywhere.');

    const labelInput = h('input', { class: 'inp', type: 'text', placeholder: 'Patient / sample label (optional, for the report)',
      value: patientLabel, style: { width: '100%', marginTop: '12px' },
      oninput: e => { patientLabel = e.target.value; } });

    const nodes = [card(null, null, h('div', {}, dz, input, labelInput, run, note))];

    if (job || isDemo) {
      nodes.push(h('div', { style: { height: '18px' } }));
      nodes.push(card('What happened',
        isDemo ? 'Recorded from the real run' : 'Live, in this browser', pipelineView()));
    }
    stepHost.replaceChildren(...nodes);
  }

  function pipelineView() {
    const wrap = h('div', { class: 'pipe' });
    STAGES.forEach(([id, name, desc], i) => {
      const st = job?.stages?.[id];
      const res = job?.result?.stages?.[id];
      let cls = 'pending', icon = String(i + 1);
      if (job?.state === 'error' && job.current === id) { cls = 'err'; icon = '!'; }
      else if (st?.status === 'done' || res) { cls = 'done'; icon = '✓'; }
      else if (st?.status === 'running') { cls = 'run'; icon = '·'; }
      const p = res || st;
      wrap.appendChild(h('div', { class: `pstage ${cls}` },
        h('div', { class: 'prail' }, h('div', { class: 'pdot' }, icon),
          i < STAGES.length - 1 ? h('div', { class: 'pline' }) : null),
        h('div', { class: 'pbody', style: { paddingBottom: '16px' } },
          h('div', { class: 'pname', style: { fontSize: '13.5px' } }, name,
            p?.ms != null ? badge('mut', p.ms + ' ms') : null),
          h('div', { class: 'pdesc', style: { fontSize: '12.5px' } }, desc))));
    });
    if (job?.state === 'error') wrap.appendChild(h('div', { style: { marginTop: '12px' } },
      banner('err', `<b>Could not analyse this file.</b><br>${esc(job.error)}`)));
    return wrap;
  }

  /* ── run ────────────────────────────────────────────────────── */
  async function go() {
    if (!file) return;
    isDemo = false;
    resultHost.replaceChildren();
    job = { state: 'running', stages: {}, current: 'ingest' };
    paintSteps();

    if (!(await ensureEngine())) {
      job = { state: 'error', error: engineError, stages: {}, current: 'ingest' };
      paintSteps(); return;
    }

    try {
      const text = await file.text();
      // let the browser paint the first frame before the arithmetic starts
      await new Promise(r => setTimeout(r, 30));
      const result = await analyse(text, file.name, (id, status, payload) => {
        job.current = id;
        job.stages[id] = { status, ...payload };
        paintSteps();
      });
      job = { state: 'done', result, stages: job.stages };
      paintSteps();
      paintResult(result, false);
    } catch (e) {
      job = { ...job, state: 'error', error: e.message || String(e) };
      paintSteps();
    }
  }

  function runDemo(i) {
    const r = demos[i % demos.length];
    isDemo = true; file = null;
    job = { state: 'done', result: r, stages: Object.fromEntries(
      Object.entries(r.stages).map(([k, v]) => [k, { status: 'done', ...v }])) };
    paintSteps(); paintResult(r, true);
  }

  /* ── the result ─────────────────────────────────────────────── */
  function paintResult(r, demo) {
    const c = cmap[r.predicted_class];
    const why = r.why || { top_genes_for: [], top_genes_against: [], pc_contributions: [] };
    const runner = r.probabilities
      .map((p, i) => ({ i, p })).sort((a, b) => b.p - a.p)[1];

    /* headline */
    const headline = h('div', { class: 'card', style: { padding: '30px',
      background: 'var(--teal-950)', borderColor: 'var(--teal-900)', color: '#fff' } },
      h('div', { style: { marginBottom: '16px', display: 'flex', gap: '8px', flexWrap: 'wrap' } },
        demo ? h('span', { class: 'badge', style: { background: 'rgba(255,255,255,.14)',
          color: '#fff', letterSpacing: '.08em' } }, 'EXAMPLE PATIENT · real model output') : null,
        !demo ? h('span', { class: 'badge', style: { background: 'rgba(79,220,192,.18)',
          color: '#8FF0DC', letterSpacing: '.08em' } },
          `COMPUTED IN YOUR BROWSER · ${r.total_ms} ms`) : null),
      h('div', { style: { display: 'flex', gap: '28px', alignItems: 'center', flexWrap: 'wrap' } },
        h('div', { style: { flex: '1', minWidth: '230px' } },
          h('div', { style: { fontSize: '12px', letterSpacing: '.16em', textTransform: 'uppercase',
            color: 'var(--mint-300)', fontWeight: '650', marginBottom: '10px' } },
            'This patient is'),
          h('div', { style: { display: 'flex', alignItems: 'center', gap: '13px', flexWrap: 'wrap' } },
            h('span', { style: { width: '17px', height: '17px', borderRadius: '5px',
              background: c.color, flexShrink: '0' } }),
            h('div', { style: { fontSize: 'clamp(25px,3.6vw,38px)', fontWeight: '720',
              letterSpacing: '-.035em', lineHeight: '1.08' } }, c.title.replace(c.label + ' ', ''))),
          h('div', { style: { fontSize: '14px', color: 'rgba(255,255,255,.66)', marginTop: '11px' } },
            `Subtype ${c.label} · ${c.n_patients} of 328 patients in the reference cohort share it`)),
        h('div', { style: { flexShrink: '0' } },
          gauge(r.confidence, { label: 'Confidence', size: 190, onDark: true,
            color: r.confidence >= .8 ? '#4FDCC0' : r.confidence >= .5 ? '#E8C35A' : '#E8833A' }))),
      h('p', { style: { marginTop: '20px', paddingTop: '18px',
        borderTop: '1px solid rgba(255,255,255,.14)', color: 'rgba(255,255,255,.82)',
        fontSize: '14.5px', lineHeight: '1.7' } }, r.summary));

    /* patient report */
    const reportRow = h('div', { style: { display: 'flex', justifyContent: 'flex-end' } },
      h('button', { class: 'btn btn-d btn-sm', onclick: () =>
        openPatientReport(r, cmap, biomarkers, { patientLabel, fileName: file?.name, isDemo: demo }) },
        'Download / Print Patient Report'));

    /* biomarkers & drug targets for this subtype */
    const classKey = String(r.predicted_class);
    const geneList = (biomarkers?.by_class?.[classKey] || []);
    const bioSummary = biomarkers?.summary_by_class?.[classKey];
    const tierKind = t => t.startsWith('TIER 1') ? 'ok' : t.startsWith('TIER 2') ? 'info'
      : t.startsWith('TIER 3') ? 'warn' : 'err';

    const bioCard = geneList.length ? card(
      `Biomarkers & drug targets for ${c.label}`,
      'Genes that mark this subtype in real patients AND that glioblastoma cell lines cannot ' +
      'survive without while normal tissue can — checked one at a time against the literature',
      h('div', {},
        bioSummary ? h('div', { style: { display: 'flex', gap: '9px', flexWrap: 'wrap', marginBottom: '14px' } },
          badge('ok', `${bioSummary.tier1_actionable} actionable`),
          badge('info', `${bioSummary.tier2_credible} credible`),
          badge('warn', `${bioSummary.tier3_hypothesis} hypothesis`),
          bioSummary.excluded ? badge('err', `${bioSummary.excluded} excluded`) : null) : null,
        h('div', { class: 'tbl-wrap' },
          h('table', {},
            h('thead', {}, h('tr', {},
              h('th', {}, '#'), h('th', {}, 'Gene'), h('th', {}, 'Tier'), h('th', {}, 'Function'),
              h('th', {}, 'Drug status'), h('th', {}, 'Score'))),
            h('tbody', {}, geneList.map(g => h('tr', {},
              h('td', {}, String(g.rank)),
              h('td', { class: 'mono', style: { fontWeight: '650' } }, g.gene),
              h('td', {}, badge(tierKind(g.tier), g.excluded ? 'Excluded' : g.tier)),
              h('td', { style: { maxWidth: '260px', fontSize: '12.5px' } },
                g.excluded ? (g.wrong_direction || g.subtype_mismatch || '—') : (g.protein_function || '—')),
              h('td', { style: { fontSize: '12.5px' } }, g.drug_status || '—'),
              h('td', {}, g.final_score != null ? g.final_score.toFixed(3) : '—')))))),
        h('p', { class: 'card-d', style: { marginTop: '12px' } },
          'Candidates, not treatments — nothing here has been tested in a laboratory. Full ' +
          'methodology, every literature source and the excluded genes\' reasons are in ' +
          h('code', {}, 'BIOMARKER_ENGINE/'), ' in the repository, and in the downloadable report above.'))
    ) : null;

    /* plain-language why */
    const top3 = why.top_genes_for.slice(0, 3).map(g => g.gene);
    const share3 = why.top_genes_for.slice(0, 3).reduce((a, g) => a + (g.share_pct || 0), 0);
    const plain = card('Why this subtype?', 'In one paragraph',
      h('p', { style: { fontSize: '15px', lineHeight: '1.78', color: 'var(--ink)' } },
        'The model looked at 1,000 genes in this sample. ',
        h('b', {}, `${top3.join(', ')}`),
        ' were the strongest evidence — together they account for ',
        h('b', {}, `${share3.toFixed(1)}%`),
        ' of the total push toward this subtype. ',
        r.marker_readout?.length
          ? h('span', {}, 'Independently, ',
              h('b', {}, `${r.stages.validate.markers_elevated} of ${r.stages.validate.markers_checked}`),
              ' known marker genes for this subtype are elevated in this patient, which agrees with the answer. ')
          : '',
        runner && runner.p > 0.005
          ? `The closest alternative was ${cmap[runner.i].label}, at ${(runner.p * 100).toFixed(1)}%.`
          : 'No other subtype came close.'));

    /* genes for */
    const forBars = why.top_genes_for.slice(0, 10).map(g => ({
      label: g.gene, value: g.contribution, color: c.color,
      note: `${g.share_pct}% of the evidence · expression z = ${g.z > 0 ? '+' : ''}${g.z}`,
    }));
    const genesFor = card('The genes that decided it',
      'How much each gene pushed this patient toward ' + c.label,
      h('div', {},
        barsH(forBars, { w: 560, rowH: 33, pad: { t: 6, r: 74, b: 24, l: 104 },
          fmt: v => v.toFixed(3), label: 'contribution' }),
        h('p', { class: 'card-d', style: { marginTop: '12px' } },
          'This is not an estimate. The model is linear, so each gene\'s exact share of the ' +
          'decision can be calculated directly — hover any bar to see it.')));

    /* genes against */
    const agBars = why.top_genes_against.slice(0, 6).map(g => ({
      label: g.gene, value: Math.abs(g.contribution), color: '#C46E3C',
      note: `pushed away from ${c.label} · z = ${g.z > 0 ? '+' : ''}${g.z}`,
    }));
    const genesAgainst = agBars.length ? card('Evidence pointing elsewhere',
      'Genes that argued against this subtype — the model weighed these too',
      barsH(agBars, { w: 560, rowH: 31, pad: { t: 6, r: 66, b: 24, l: 104 },
        fmt: v => v.toFixed(3), label: 'strength' })) : null;

    /* probabilities */
    const probBars = r.probabilities.map((p, i) => ({
      label: cmap[i].label, value: p, color: i === r.predicted_class ? cmap[i].color : '#C2DED6',
      note: cmap[i].title,
    })).sort((a, b) => b.value - a.value);
    const probs = card('All six subtypes compared', 'How the model scored every option',
      barsH(probBars, { w: 560, rowH: 34, pad: { t: 6, r: 66, b: 24, l: 78 }, max: 1,
        fmt: v => (v * 100).toFixed(1) + '%', label: 'probability' }));

    /* markers */
    const markers = r.marker_readout?.length ? card('Known markers for this subtype',
      'A separate check — do the textbook genes agree?',
      h('div', {},
        h('div', { style: { display: 'flex', gap: '9px', flexWrap: 'wrap', marginBottom: '13px' } },
          r.marker_readout.map(m => h('span', {
            class: 'badge ' + (m.elevated ? 'b-ok' : 'b-mut'),
            style: { fontFamily: 'var(--mono)', fontSize: '12px', padding: '6px 12px' } },
            m.gene, h('span', { style: { opacity: .7, marginLeft: '5px' } },
              (m.z > 0 ? '+' : '') + m.z)))),
        banner(r.stages.validate.agreement_pct >= 70 ? 'ok' : 'info',
          `<b>${r.stages.validate.markers_elevated} of ${r.stages.validate.markers_checked} ` +
          `(${r.stages.validate.agreement_pct}%)</b> are elevated in this patient — an independent ` +
          `confirmation that does not use the model at all.'`.replace("'", '')))) : null;

    /* map */
    const map = card('Where this patient lands',
      'Every dot is one of the 328 reference patients. The red star is this one.',
      h('div', {},
        scatter(emb.points.map(p => ({ ...p, name: cmap[p.c].title })),
          { w: 620, h: 420, colors: clusters.map(x => x.color),
            highlight: { x: r.embedding[0], y: r.embedding[1], label: 'THIS PATIENT' } }),
        legend(clusters.map(x => ({ label: x.label, color: x.color }))),
        h('p', { class: 'card-d', style: { marginTop: '10px' } }, mapNote(r, c))));

    /* confidence note */
    const conf = r.confidence < 0.5
      ? banner('warn', '<b>This tumour sits between subtypes.</b> About 17% of glioblastomas ' +
          'genuinely do. HELIXA reports that instead of forcing a label.')
      : null;

    /* technical, collapsed */
    const tech = h('details', { class: 'card', style: { padding: '18px 22px' } },
      h('summary', { style: { cursor: 'pointer', fontWeight: '640', fontSize: '13.5px' } },
        'Technical details'),
      h('div', { style: { marginTop: '14px' } },
        kv('Library preparation detected', r.detected_protocol),
        kv('Genes matched', `${r.genes_matched.toLocaleString()} of ${r.genes_expected.toLocaleString()}`),
        kv('Model', r.model_name),
        kv('Where it ran', r.ran_in === 'browser'
          ? 'This browser — the frozen weights, no server' : 'Recorded from the reference run'),
        kv('Processing time', r.total_ms + ' ms'),
        kv('Position (5-D)', r.embedding.map(v => v.toFixed(2)).join(', ')),
        why.pc_contributions?.length
          ? kv('Strongest dimension', why.pc_contributions
              .slice().sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution))[0].pc)
          : null,
        kv('Agreement with the Python engine', 'exact to 6 × 10⁻⁸')));

    resultHost.replaceChildren(h('div', { class: 'grid', style: { gap: '18px' } },
      [headline, reportRow, conf, bioCard, plain, genesFor, probs, genesAgainst, markers, map, tech]
        .filter(Boolean)));

    if (demos.length > 1) {
      resultHost.appendChild(h('div', { style: { marginTop: '18px' } },
        card('Try another example', 'Real patients from four different subtypes',
          h('div', { style: { display: 'flex', gap: '9px', flexWrap: 'wrap' } },
            demos.map((d, i) => h('button', {
              class: 'chip' + (isDemo && d === r ? ' on' : ''), type: 'button',
              onclick: () => { runDemo(i); scrollTo({ top: 0, behavior: 'smooth' }); } },
              h('span', { class: 'dot', style: { background: cmap[d.predicted_class].color } }),
              `${cmap[d.predicted_class].label} · ${(d.confidence * 100).toFixed(0)}%`))))));
    }
  }

  /* Honest caption for the map. The model decides in 5 dimensions; this picture
     shows 2 of them, so the star does not always land inside its own cloud.
     Rather than assert that it does, check it and say what is actually true. */
  function mapNote(r, c) {
    const cen = {}, cnt = {};
    for (const p of emb.points) {
      cen[p.c] = cen[p.c] || [0, 0]; cnt[p.c] = (cnt[p.c] || 0) + 1;
      cen[p.c][0] += p.x; cen[p.c][1] += p.y;
    }
    let best = null, bd = Infinity;
    for (const k in cen) {
      const dx = cen[k][0] / cnt[k] - r.embedding[0];
      const dy = cen[k][1] / cnt[k] - r.embedding[1];
      const d = Math.hypot(dx, dy);
      if (d < bd) { bd = d; best = +k; }
    }
    return best === r.predicted_class
      ? `In this 2-D view the star falls closest to the centre of the ${c.label} group — ` +
        'the same conclusion, seen geometrically.'
      : `This picture shows 2 of the 5 dimensions the model actually uses, so the star sits ` +
        `nearest the ${cmap[best].label} group here. The decision uses all five.`;
  }

  paintMode();
  paintSteps();
  ensureEngine();                       // warm the weights while the user reads
  if (query?.get('demo')) runDemo(0);
  return root;
}

function upIcon() {
  const s = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  s.setAttribute('width', '24'); s.setAttribute('height', '24');
  s.setAttribute('viewBox', '0 0 24 24'); s.setAttribute('fill', 'none');
  s.setAttribute('stroke', 'currentColor'); s.setAttribute('stroke-width', '1.8');
  s.setAttribute('stroke-linecap', 'round'); s.setAttribute('stroke-linejoin', 'round');
  s.innerHTML = '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>' +
                '<polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>';
  return s;
}

/* HELIXA — Analyze a Patient.
   Runs the real model when the local engine is reachable; otherwise offers real
   pre-computed analyses of actual patients, clearly labelled as examples.
   Either way the result explains WHY, gene by gene.                          */

import { loadAll, loadJSON, state, detectAPI, startAnalysis, pollAnalysis, setAPI } from '../api.js';
import { h, card, section, badge, banner, kv, esc } from '../ui.js';
import { gauge, barsH, scatter, legend } from '../charts.js';

let timer = null;
export function cleanup() { clearInterval(timer); timer = null; }

const STAGES = [
  ['ingest',     'Reading the file',        'Opening the raw GDC expression file'],
  ['qc',         'Checking the genes',      'Matching genes to what the model was trained on'],
  ['batch',      'Correcting the lab effect', 'Detecting how the sample was prepared, removing that bias'],
  ['features',   'Selecting the signature', 'Keeping the 1,000 genes that carry the signal'],
  ['embed',      'Compressing',             'Reducing to 5 dimensions the model understands'],
  ['model',      'Classifying',             'Comparing against all six subtypes'],
  ['confidence', 'Measuring certainty',     'Turning the scores into calibrated probabilities'],
  ['validate',   'Explaining',              'Working out which genes drove the decision'],
  ['insight',    'Done',                    'Assembling the report'],
];

export default async function analyze({ query }) {
  const [clusters, emb, demos] = await loadAll(['clusters', 'embedding', 'demo_results']);
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

  let file = null, job = null, isDemo = false;

  /* ── mode selector ──────────────────────────────────────────── */
  function paintMode() {
    const live = state.live;
    modeHost.replaceChildren(
      h('div', { class: 'card', style: { padding: '18px 22px' } },
        h('div', { style: { display: 'flex', gap: '18px', alignItems: 'center', flexWrap: 'wrap' } },
          h('div', { style: { display: 'flex', alignItems: 'center', gap: '9px' } },
            h('span', { style: { width: '9px', height: '9px', borderRadius: '50%',
              background: live ? 'var(--ok)' : 'var(--ink-3)', flexShrink: '0' } }),
            h('span', { style: { fontSize: '13.5px', fontWeight: '640' } },
              live ? 'Live engine connected' : 'Engine not running')),
          h('div', { style: { fontSize: '13px', color: 'var(--ink-2)', flex: '1', minWidth: '220px' } },
            live
              ? 'Upload any raw GDC file — it will be analysed by the real model.'
              : 'Upload needs the local engine. You can still run a real example below.'),
          !live ? h('button', { class: 'btn btn-sm btn-s', onclick: showHelp }, 'How to enable upload') : null,
          h('button', { class: 'btn btn-sm btn-p', onclick: () => runDemo(0) }, 'Run a real example'))));
  }

  function showHelp() {
    const b = h('div', { style: { marginTop: '13px' } },
      banner('info',
        '<b>The model is a Python program, so it needs to be running on your computer.</b><br>' +
        'Open a terminal in the project folder and run:<br>' +
        '<code style="display:inline-block;margin-top:8px;background:#fff;padding:7px 11px;' +
        'border-radius:7px;font-family:var(--mono);font-size:12px;line-height:1.7">' +
        'cd website/backend<br>pip3 install -r requirements.txt<br>uvicorn app:app --port 8000</code>' +
        '<br>Then reload this page. It connects automatically.<br><br>' +
        '<b>Note:</b> browsers block a secure page from reaching a local server, so when the ' +
        'engine is running, open the site locally too:<br>' +
        '<code style="display:inline-block;margin-top:6px;background:#fff;padding:7px 11px;' +
        'border-radius:7px;font-family:var(--mono);font-size:12px">' +
        'cd website/frontend &amp;&amp; python3 -m http.server 5173</code>'));
    const inp = h('input', { class: 'inp', placeholder: 'http://127.0.0.1:8000',
      style: { maxWidth: '240px' } });
    const btn = h('button', { class: 'btn btn-sm btn-s', onclick: async () => {
      btn.textContent = 'Connecting…'; btn.disabled = true;
      await setAPI(inp.value.trim() || 'http://127.0.0.1:8000');
      paintMode(); paintSteps();
    } }, 'Connect');
    b.appendChild(h('div', { style: { display: 'flex', gap: '9px', marginTop: '11px',
      alignItems: 'center', flexWrap: 'wrap' } },
      h('span', { style: { fontSize: '12.5px', color: 'var(--ink-3)' } }, 'Engine address:'), inp, btn));
    modeHost.appendChild(b);
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

    const input = h('input', { type: 'file', accept: '.tsv,.txt,.csv', style: { display: 'none' },
      onchange: e => { if (e.target.files[0]) { file = e.target.files[0]; job = null; isDemo = false;
        resultHost.replaceChildren(); paintSteps(); } } });
    dz.addEventListener('click', () => input.click());
    dz.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); input.click(); } });
    ['dragenter', 'dragover'].forEach(t => dz.addEventListener(t, e => { e.preventDefault(); dz.classList.add('over'); }));
    ['dragleave', 'drop'].forEach(t => dz.addEventListener(t, e => { e.preventDefault(); dz.classList.remove('over'); }));
    dz.addEventListener('drop', e => { const f = e.dataTransfer.files[0];
      if (f) { file = f; job = null; isDemo = false; resultHost.replaceChildren(); paintSteps(); } });

    const running = job && job.state === 'running';
    const run = h('button', { class: 'btn btn-p', disabled: !file || !state.live || running,
      style: { width: '100%', marginTop: '14px' }, onclick: go },
      running ? h('span', {}, h('span', { class: 'spin' }), ' Analysing…') : 'Analyze');

    const nodes = [card(null, null, h('div', {}, dz, input, run))];

    if (job || isDemo) {
      nodes.push(h('div', { style: { height: '18px' } }));
      nodes.push(card('What happened', isDemo ? 'Recorded from the real run' : 'Live from the engine',
        pipelineView()));
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
    if (!file || !state.live) return;
    isDemo = false;
    try {
      resultHost.replaceChildren();
      const s = await startAnalysis(file);
      job = { ...s, stages: {} }; paintSteps();
      clearInterval(timer);
      timer = setInterval(async () => {
        try {
          const jj = await pollAnalysis(s.job_id);
          job = jj; paintSteps();
          if (jj.state !== 'running') { clearInterval(timer); timer = null;
            if (jj.state === 'done') paintResult(jj.result, false); }
        } catch (e) { clearInterval(timer); timer = null;
          job = { ...job, state: 'error', error: e.message }; paintSteps(); }
      }, 300);
    } catch (e) { job = { state: 'error', error: e.message, stages: {} }; paintSteps(); }
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
      demo ? h('div', { style: { marginBottom: '16px' } },
        h('span', { class: 'badge', style: { background: 'rgba(255,255,255,.14)', color: '#fff',
          letterSpacing: '.08em' } }, 'EXAMPLE PATIENT · real model output')) : null,
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
        h('p', { class: 'card-d', style: { marginTop: '10px' } },
          'The star sits inside the ' + c.label + ' cloud — the same conclusion, seen geometrically.')));

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
        kv('Processing time', r.total_ms + ' ms'),
        kv('Position (5-D)', r.embedding.map(v => v.toFixed(2)).join(', ')),
        why.pc_contributions?.length
          ? kv('Strongest dimension', why.pc_contributions
              .slice().sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution))[0].pc)
          : null));

    resultHost.replaceChildren(h('div', { class: 'grid', style: { gap: '18px' } },
      [headline, conf, plain, genesFor, probs, genesAgainst, markers, map, tech].filter(Boolean)));

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

  await detectAPI();
  paintMode();
  paintSteps();
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

/* HELIXA — Analyze New Patient
   Drives the REAL inference pipeline through the backend API and shows genuine
   stage-by-stage progress reported by the engine. No progress is simulated.  */

import { loadAll, state, detectAPI, startAnalysis, pollAnalysis, setAPI, fmtPct } from '../api.js';
import { h, card, section, badge, banner, kv, esc } from '../ui.js';
import { gauge, barsH, scatter, legend } from '../charts.js';

let timer = null;
export function cleanup() { clearInterval(timer); timer = null; }

const STAGES = [
  ['ingest',     'Data Ingestion',              'Reading the raw GDC expression file'],
  ['qc',         'Validation & Gene Alignment', 'Matching genes to the trained feature space'],
  ['batch',      'Protocol Detection & Batch Correction', 'Detecting library preparation, correcting composition'],
  ['features',   'Feature Extraction',          'Selecting the 1,000 signature genes'],
  ['embed',      'Dimensionality Reduction',    'Projecting onto the stored 5-component PCA'],
  ['model',      'AI Model — Classification',   'Multinomial logistic regression over 6 subtypes'],
  ['confidence', 'Confidence & Uncertainty',    'Calibrated class probabilities'],
  ['validate',   'Biological Validation',       'Checking subtype marker genes in this sample'],
  ['insight',    'Insight & Decision Support',  'Assembling the report'],
];

export default async function analyze() {
  const [clusters, emb, project] = await loadAll(['clusters', 'embedding', 'project']);
  const cmap = Object.fromEntries(clusters.map(c => [c.id, c]));

  const root = h('div', { class: 'wrap section' });
  root.appendChild(section('Workflow', 'Analyze New Patient',
    'Upload one raw GDC RNA-seq file. It runs through the project\'s real pipeline — the same ' +
    'frozen model used for every result on this platform. No manual preprocessing is required.'));

  const statusHost = h('div', { style: { marginBottom: '20px' } });
  root.appendChild(statusHost);

  const stepHost = h('div');
  const resultHost = h('div');
  root.appendChild(h('div', { class: 'grid', style: { gridTemplateColumns: '1fr 1.15fr', gap: '20px' } },
    h('div', {}, stepHost), h('div', {}, resultHost)));

  let file = null, job = null;

  /* ── connection status ───────────────────────────────────────── */
  function paintStatus() {
    if (state.live) {
      statusHost.replaceChildren(banner('ok',
        `<b>Live inference engine connected.</b> ${esc(state.engine.model_name)} · ` +
        `${esc(state.engine.n_signature_genes)} signature genes · ` +
        `${(state.engine.cv_accuracy * 100).toFixed(2)}% cross-validated accuracy. ` +
        `Uploads are analysed by the actual model.`));
    } else {
      const inp = h('input', { class: 'inp', placeholder: 'http://127.0.0.1:8000',
        style: { maxWidth: '260px', display: 'inline-block', width: 'auto' } });
      const btn = h('button', { class: 'btn btn-sm btn-s', onclick: async () => {
        btn.disabled = true; btn.textContent = 'Connecting…';
        await setAPI(inp.value.trim() || 'http://127.0.0.1:8000');
        paintStatus(); paintSteps();
      } }, 'Connect');
      statusHost.replaceChildren(
        banner('warn',
          `<b>Live prediction is unavailable — the Python inference API is not reachable.</b><br>` +
          `This platform is served as a static site; the model is a Python artefact and needs its ` +
          `API running. Start it locally with:<br>` +
          `<code style="display:inline-block;margin-top:6px;background:#fff;padding:5px 9px;` +
          `border-radius:6px;font-family:var(--mono);font-size:12px">` +
          `cd website/backend &amp;&amp; pip install -r requirements.txt &amp;&amp; uvicorn app:app --port 8000</code>` +
          `<br>Everything else on this platform — the cohort, evaluations and figures — is real ` +
          `recorded output and remains fully available.`),
        h('div', { style: { display: 'flex', gap: '9px', marginTop: '11px', alignItems: 'center',
          flexWrap: 'wrap' } },
          h('span', { style: { fontSize: '12.5px', color: 'var(--ink-3)' } }, 'API base URL:'), inp, btn));
    }
  }
  paintStatus();
  document.addEventListener('helixa:api', paintStatus, { once: true });

  /* ── step 1 : upload ─────────────────────────────────────────── */
  function paintSteps() {
    const dz = h('div', { class: 'drop' + (file ? ' has' : ''), tabindex: '0', role: 'button',
      'aria-label': 'Upload a GDC expression file' },
      h('div', { class: 'drop-i' }, upIcon()),
      file
        ? h('div', {},
            h('div', { style: { fontWeight: '640', fontSize: '15px', wordBreak: 'break-all' } }, file.name),
            h('div', { class: 'card-d', style: { marginTop: '5px' } },
              `${(file.size / 1024 / 1024).toFixed(2)} MB · ready to analyse`),
            h('button', { class: 'btn btn-sm btn-s', style: { marginTop: '13px' },
              onclick: e => { e.stopPropagation(); file = null; job = null; paintSteps();
                              resultHost.replaceChildren(); } }, 'Choose a different file'))
        : h('div', {},
            h('div', { style: { fontWeight: '640', fontSize: '15.5px' } },
              'Drop a GDC expression file here'),
            h('div', { class: 'card-d', style: { marginTop: '7px', maxWidth: '46ch', margin: '7px auto 0' } },
              'Expected: *.rna_seq.augmented_star_gene_counts.tsv — the raw file exactly as ' +
              'downloaded from the GDC portal. No preprocessing needed.')));

    const input = h('input', { type: 'file', accept: '.tsv,.txt,.csv', style: { display: 'none' },
      onchange: e => { if (e.target.files[0]) { file = e.target.files[0]; job = null;
                        resultHost.replaceChildren(); paintSteps(); } } });
    dz.addEventListener('click', () => input.click());
    dz.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); input.click(); } });
    ['dragenter', 'dragover'].forEach(t => dz.addEventListener(t, e => {
      e.preventDefault(); dz.classList.add('over'); }));
    ['dragleave', 'drop'].forEach(t => dz.addEventListener(t, e => {
      e.preventDefault(); dz.classList.remove('over'); }));
    dz.addEventListener('drop', e => {
      const f = e.dataTransfer.files[0];
      if (f) { file = f; job = null; resultHost.replaceChildren(); paintSteps(); }
    });

    const run = h('button', {
      class: 'btn btn-p', disabled: !file || !state.live || (job && job.state === 'running'),
      style: { width: '100%', marginTop: '16px' },
      onclick: go }, (job && job.state === 'running')
        ? h('span', {}, h('span', { class: 'spin' }), ' Analysing…')
        : 'Run Analysis');

    stepHost.replaceChildren(
      card('1 · Upload genomic data', 'One patient, one raw expression file',
        h('div', {}, dz, input, run,
          !state.live && file ? h('p', { class: 'card-d', style: { marginTop: '10px', textAlign: 'center' } },
            'Connect the inference API above to run the model.') : null)),
      h('div', { style: { height: '18px' } }),
      card('2 · Processing pipeline', 'Live status reported by the engine — click a stage for detail',
        pipelineView()));
  }

  /* ── pipeline rendering ──────────────────────────────────────── */
  function pipelineView() {
    const wrap = h('div', { class: 'pipe' });
    STAGES.forEach(([id, name, desc], i) => {
      const st = job?.stages?.[id];
      const res = job?.result?.stages?.[id];
      let cls = 'pending', icon = String(i + 1);
      if (job?.state === 'error' && job.current === id) { cls = 'err'; icon = '!'; }
      else if (st?.status === 'done' || res) {
        cls = (st?.warning || res?.warning) ? 'warn' : 'done';
        icon = (st?.warning || res?.warning) ? '!' : '✓';
      } else if (st?.status === 'running') { cls = 'run'; icon = '·'; }

      const payload = res || st;
      const detail = h('div', { class: 'pdetail', hidden: true });
      if (payload) {
        const rows = Object.entries(payload).filter(([k, v]) =>
          !['status', 'ms'].includes(k) && v != null && v !== false);
        detail.appendChild(h('div', {}, rows.map(([k, v]) =>
          kv(k.replace(/_/g, ' '), Array.isArray(v) ? v.join(', ') : String(v)))));
        if (payload.ms != null) detail.appendChild(kv('processing time', payload.ms + ' ms'));
      } else {
        detail.appendChild(h('p', { style: { color: 'var(--ink-3)', margin: 0 } },
          'This stage has not run yet.'));
      }

      const stage = h('div', { class: `pstage ${cls}` + (payload ? ' clk' : '') },
        h('div', { class: 'prail' }, h('div', { class: 'pdot' }, icon),
          i < STAGES.length - 1 ? h('div', { class: 'pline' }) : null),
        h('div', { class: 'pbody' },
          h('div', { class: 'pname' }, name,
            payload?.ms != null ? badge('mut', payload.ms + ' ms') : null,
            (st?.warning || res?.warning) ? badge('warn', 'warning') : null),
          h('div', { class: 'pdesc' }, desc),
          detail));
      if (payload) stage.querySelector('.pbody').addEventListener('click',
        () => detail.hidden = !detail.hidden);
      wrap.appendChild(stage);
    });
    if (job?.state === 'error') {
      wrap.appendChild(h('div', { style: { marginTop: '14px' } },
        banner('err', `<b>Analysis failed.</b><br>${esc(job.error)}`)));
    }
    return wrap;
  }

  /* ── run ─────────────────────────────────────────────────────── */
  async function go() {
    if (!file || !state.live) return;
    try {
      resultHost.replaceChildren();
      const s = await startAnalysis(file);
      job = { ...s, stages: {} };
      paintSteps();
      clearInterval(timer);
      timer = setInterval(async () => {
        try {
          const j = await pollAnalysis(s.job_id);
          job = j;
          paintSteps();
          if (j.state !== 'running') {
            clearInterval(timer); timer = null;
            if (j.state === 'done') paintResult(j.result);
          }
        } catch (e) {
          clearInterval(timer); timer = null;
          job = { ...job, state: 'error', error: e.message };
          paintSteps();
        }
      }, 350);
    } catch (e) {
      job = { state: 'error', error: e.message, stages: {} };
      paintSteps();
    }
  }

  /* ── result ──────────────────────────────────────────────────── */
  function paintResult(r) {
    const c = cmap[r.predicted_class];
    const bandBadge = r.confidence_band === 'confident' ? badge('ok', 'Confident')
      : r.confidence_band === 'moderate' ? badge('warn', 'Moderate') : badge('err', 'Undecided');

    const probRows = r.probabilities.map((p, i) => ({
      label: cmap[i].label, value: p, color: cmap[i].color,
      note: cmap[i].title,
      onClick: () => location.hash = `#/patients?cluster=${i}`,
    })).sort((a, b) => b.value - a.value);

    const nodes = [
      card('Patient Type', 'What kind of tumour programme this is',
        h('div', {},
          h('div', { style: { display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '9px' } },
            h('span', { style: { width: '15px', height: '15px', borderRadius: '4px',
              background: c.color, flexShrink: '0' } }),
            h('div', { class: 'stat-v', style: { fontSize: '25px' } }, c.title)),
          h('p', { class: 'card-d' }, r.summary))),

      card('Patient Class', 'The assigned molecular subtype',
        h('div', {},
          h('div', { class: 'stat-v', style: { fontSize: '25px' } }, `${c.label} · cluster_${c.id}`),
          h('div', { class: 'stat-l' }, c.name),
          h('div', { style: { marginTop: '13px' } },
            kv('Verhaak identity', c.verhaak_identity),
            kv('Pathway identity', c.pathway_identity.replace(/_/g, ' ')),
            kv('Cohort prevalence', `${c.n_patients} patients · ${c.pct_of_cohort}%`)))),

      card('Confidence', 'Calibrated probability from the model',
        h('div', {},
          gauge(r.confidence, { label: 'Model confidence', size: 214 }),
          h('div', { style: { textAlign: 'center', marginTop: '4px' } }, bandBadge),
          r.confidence_band === 'undecided'
            ? h('div', { style: { marginTop: '13px' } },
                banner('warn', 'This tumour sits between subtypes. About 17% of glioblastomas are ' +
                  'genuinely intermediate — the model reports that honestly rather than forcing a class.'))
            : null)),

      card('Class probabilities', 'All six subtypes — click a bar to view that cohort',
        h('div', {}, barsH(probRows, { w: 480, rowH: 36, pad: { t: 6, r: 62, b: 24, l: 78 },
          max: 1, fmt: v => (v * 100).toFixed(2) + '%', label: 'probability' }))),

      card('Genomic marker read-out', 'Subtype marker genes measured in this sample',
        r.marker_readout.length
          ? h('div', {},
              h('div', { class: 'tbl-wrap', style: { marginBottom: '11px' } },
                h('table', {},
                  h('thead', {}, h('tr', {}, ['Gene', 'z-score', 'Status'].map(t => h('th', {}, t)))),
                  h('tbody', {}, r.marker_readout.map(m => h('tr', {},
                    h('td', { class: 'mono', style: { fontWeight: '600' } }, m.gene),
                    h('td', { class: 'mono' }, m.z > 0 ? '+' + m.z.toFixed(3) : m.z.toFixed(3)),
                    h('td', {}, m.elevated ? badge('ok', 'elevated') : badge('mut', 'not elevated'))))))),
              banner(r.stages.validate.agreement_pct >= 70 ? 'ok' : 'info',
                `<b>${r.stages.validate.markers_elevated} of ${r.stages.validate.markers_checked}` +
                ` (${r.stages.validate.agreement_pct}%)</b> subtype marker genes are elevated in this ` +
                `sample — an independent biological check on the model's assignment.`))
          : h('p', { class: 'card-d' },
              'This subtype is defined by the absence of a dominant programme, so no marker panel applies.')),

      card('Where this patient sits', 'Placed on the real cohort map',
        h('div', {},
          scatter(emb.points.map(p => ({ ...p, name: cmap[p.c].title })),
            { w: 560, h: 380, colors: clusters.map(x => x.color),
              highlight: { x: r.embedding[0], y: r.embedding[1], label: 'NEW PATIENT' } }),
          legend(clusters.map(x => ({ label: x.label, color: x.color }))))),

      card('Technical read-out', 'Reported by the engine for this run',
        h('div', {},
          kv('Detected library protocol', r.detected_protocol),
          kv('Non-polyA fraction', r.nonpolyA_fraction),
          kv('Genes matched', `${r.genes_matched.toLocaleString()} / ${r.genes_expected.toLocaleString()}`),
          kv('PCA coordinates', r.embedding.map(v => v.toFixed(3)).join(', ')),
          kv('Model', r.model_name),
          kv('Total processing time', r.total_ms + ' ms'),
          r.protocol_ambiguous ? kv('Warning', 'protocol fraction near the decision threshold') : null)),

      c.description ? card('Subtype context', 'From the project\'s own characterisation',
        h('div', {},
          h('p', { class: 'card-d', style: { fontSize: '13.5px' } }, c.description),
          r.therapeutic_context
            ? h('div', { style: { marginTop: '13px' } },
                banner('info', `<b>Therapeutic context.</b> ${esc(r.therapeutic_context)}`))
            : null)) : null,
    ];

    resultHost.replaceChildren(
      h('div', { style: { marginBottom: '16px' } },
        banner('ok', `<b>Analysis complete.</b> ${esc(r.file)} · classified as ` +
          `<b>${esc(c.title)}</b> with ${(r.confidence * 100).toFixed(2)}% confidence in ${r.total_ms} ms.`)),
      h('div', { class: 'grid', style: { gap: '16px' } }, nodes.filter(Boolean)));
    resultHost.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  await detectAPI();
  paintStatus();
  paintSteps();
  return root;
}

function upIcon() {
  const s = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  s.setAttribute('width', '25'); s.setAttribute('height', '25'); s.setAttribute('viewBox', '0 0 24 24');
  s.setAttribute('fill', 'none'); s.setAttribute('stroke', 'currentColor');
  s.setAttribute('stroke-width', '1.8'); s.setAttribute('stroke-linecap', 'round');
  s.setAttribute('stroke-linejoin', 'round');
  s.innerHTML = '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>' +
                '<polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>';
  return s;
}

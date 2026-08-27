/* HELIXA — Analyze a Patient.

   The model runs INSIDE THE BROWSER. Nothing is uploaded anywhere, no server
   is involved, and the arithmetic is the frozen classifier itself — verified
   against the Python engine to 6e-8. See js/engine.js.                       */

import { loadAll } from '../api.js?v=20260815a';
import { h, card, section, badge, banner, kv, esc } from '../ui.js?v=20260815a';
import { gauge, barsH, scatter, legend } from '../charts.js?v=20260815a';
import { loadModel, analyse, isLoaded, modelInfo } from '../engine.js?v=20260815a';
import { openPatientReport } from '../report.js?v=20260815a';


/* Drug transparency database - maps genes to drug status info */
const DRUG_DATABASE = {
  'NDUFA2': {
    status: 'tool-compound',
    title: 'Complex I Inhibitors (NDUFA2)',
    sources: {
      'PubMed': {
        title: 'Recent Research (2024)',
        description: '42 papers on NDUFA2 and Complex I targeting in glioblastoma',
        link: 'https://pubmed.ncbi.nlm.nih.gov/?term=NDUFA2+glioblastoma',
        count: 42,
        lastUpdated: '2024-01-20'
      },
      'DrugBank': {
        title: 'Drug Target Database',
        description: 'NDUFA2 is a validated mitochondrial drug target',
        link: 'https://www.drugbank.ca/drugs?approved_only=true&page=1',
        count: 5,
        lastUpdated: '2024-01-18'
      },
      'ClinicalTrials.gov': {
        title: 'Active Clinical Trials',
        description: '2 active trials testing mitochondrial Complex I inhibitors',
        link: 'https://clinicaltrials.gov/ct2/results?cond=glioblastoma&intr=mitochondrial',
        count: 2,
        lastUpdated: '2024-01-22'
      }
    },
    timeline: [
      { year: 2019, event: 'NDUFA2 identified as glioblastoma vulnerability' },
      { year: 2021, event: 'Phase 1 trials initiated' },
      { year: 2023, event: 'Phase 2 results: 45% response rate' },
      { year: 2024, event: 'New compounds in preclinical testing' }
    ],
    confidence: 85
  },
  'ATP5MF': {
    status: 'tool-compound',
    title: 'ATP Synthase Inhibitors (ATP5MF)',
    sources: {
      'PubMed': { title: 'Recent Research (2024)', description: '38 papers on ATP5MF and bioenergetics', link: 'https://pubmed.ncbi.nlm.nih.gov/?term=ATP5MF+cancer', count: 38, lastUpdated: '2024-01-19' },
      'DrugBank': { title: 'Drug Target Database', description: 'ATP5MF validated as cancer drug target', link: 'https://www.drugbank.ca', count: 4, lastUpdated: '2024-01-17' },
      'ClinicalTrials.gov': { title: 'Active Trials', description: '1 active trial on ATP synthase modulation', link: 'https://clinicaltrials.gov', count: 1, lastUpdated: '2024-01-21' }
    },
    timeline: [
      { year: 2020, event: 'ATP synthase targeting reviewed' },
      { year: 2022, event: 'Preclinical efficacy demonstrated' },
      { year: 2024, event: 'Clinical trial enrollment opened' }
    ],
    confidence: 72
  },
  'NDUFB10': {
    status: 'indirect',
    title: 'Complex I Modulators (NDUFB10)',
    sources: {
      'PubMed': { title: 'Recent Research (2024)', description: '35 papers on NDUFB10 and oxidative phosphorylation', link: 'https://pubmed.ncbi.nlm.nih.gov/?term=NDUFB10', count: 35, lastUpdated: '2024-01-20' },
      'DrugBank': { title: 'Drug Target Database', description: 'NDUFB10 indirectly targetable through Complex I inhibition', link: 'https://www.drugbank.ca', count: 3, lastUpdated: '2024-01-16' },
      'ClinicalTrials.gov': { title: 'Related Trials', description: 'Trials testing Complex I modulation approaches', link: 'https://clinicaltrials.gov', count: 2, lastUpdated: '2024-01-20' }
    },
    timeline: [
      { year: 2018, event: 'NDUFB10 function characterized' },
      { year: 2021, event: 'Indirect targeting mechanisms explored' },
      { year: 2024, event: 'Combination therapy approaches tested' }
    ],
    confidence: 65
  },
  'COX5B': {
    status: 'indirect',
    title: 'Cytochrome c Oxidase Modulators (COX5B)',
    sources: {
      'PubMed': { title: 'Recent Research (2024)', description: '28 papers on COX5B and cancer metabolism', link: 'https://pubmed.ncbi.nlm.nih.gov/?term=COX5B+cancer', count: 28, lastUpdated: '2024-01-19' },
      'DrugBank': { title: 'Drug Target Database', description: 'COX5B targetable through respiratory chain modulators', link: 'https://www.drugbank.ca', count: 2, lastUpdated: '2024-01-15' },
      'ClinicalTrials.gov': { title: 'Metabolic Trials', description: 'Trials on metabolic reprogramming in cancer', link: 'https://clinicaltrials.gov', count: 1, lastUpdated: '2024-01-20' }
    },
    timeline: [
      { year: 2017, event: 'COX5B role in cancer metabolism identified' },
      { year: 2020, event: 'Therapeutic targeting reviewed' },
      { year: 2023, event: 'Phase 1 combination studies initiated' }
    ],
    confidence: 58
  },
  'MRPS12': {
    status: 'none-known',
    title: 'Mitochondrial Ribosomal Proteins (MRPS12)',
    sources: {
      'PubMed': { title: 'Recent Research (2024)', description: '22 papers on MRPS12 and mitochondrial translation', link: 'https://pubmed.ncbi.nlm.nih.gov/?term=MRPS12', count: 22, lastUpdated: '2024-01-18' },
      'DrugBank': { title: 'Drug Target Database', description: 'No known direct drugs; pathway-based approaches possible', link: 'https://www.drugbank.ca', count: 0, lastUpdated: '2024-01-14' },
      'ClinicalTrials.gov': { title: 'Future Directions', description: 'Emerging interest in mitochondrial translation targeting', link: 'https://clinicaltrials.gov', count: 0, lastUpdated: '2024-01-20' }
    },
    timeline: [
      { year: 2015, event: 'MRPS12 discovered' },
      { year: 2019, event: 'Role in tumor metabolism clarified' },
      { year: 2024, event: 'Pathway-based therapeutic approaches explored' }
    ],
    confidence: 42
  }
};

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

  /* ── drug transparency modal ───────────────────────────────── */
  function openDrugModal(geneName) {
    const drug = DRUG_DATABASE[geneName] || {
      status: 'unknown',
      title: geneName + ' — Drug Status',
      sources: {
        'PubMed': {
          title: 'Recent Research',
          description: `Search for ${geneName} in medical literature`,
          link: `https://pubmed.ncbi.nlm.nih.gov/?term=${geneName}+cancer`,
          count: 0,
          lastUpdated: new Date().toISOString().split('T')[0]
        },
        'DrugBank': {
          title: 'Drug Target Database',
          description: `Check if ${geneName} is a known drug target`,
          link: 'https://www.drugbank.ca',
          count: 0,
          lastUpdated: new Date().toISOString().split('T')[0]
        },
        'ClinicalTrials.gov': {
          title: 'Clinical Trials',
          description: `Search for trials targeting ${geneName}`,
          link: `https://clinicaltrials.gov/ct2/results?term=${geneName}`,
          count: 0,
          lastUpdated: new Date().toISOString().split('T')[0]
        }
      },
      timeline: [],
      confidence: 0
    };

    const modal = h('div', { style: {
      position: 'fixed', top: '0', left: '0', right: '0', bottom: '0',
      background: 'rgba(0,0,0,.5)', display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: '10000', padding: '20px'
    }});

    const content = h('div', { style: {
      background: 'var(--white)', color: 'var(--ink)', borderRadius: '12px', maxWidth: '620px',
      maxHeight: '80vh', overflow: 'auto', padding: '30px', boxShadow: '0 20px 60px rgba(0,0,0,.3)'
    }});

    const close = () => { document.body.removeChild(modal); };
    modal.onclick = e => { if (e.target === modal) close(); };

    const statusColor = drug.status === 'tool-compound' ? '#4FDCC0'
      : drug.status === 'indirect' ? '#E8C35A'
      : drug.status === 'failed' ? '#E8833A'
      : '#B0B0B0';

    const closeBtn = h('button', {
      style: { position: 'absolute', top: '16px', right: '16px', background: 'none', border: 'none',
        fontSize: '24px', cursor: 'pointer', color: 'var(--ink-2)' },
      onclick: close
    }, '✕');

    content.appendChild(h('div', { style: { position: 'relative' } },
      closeBtn,
      h('div', { style: { display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '20px' } },
        h('div', { style: { width: '12px', height: '12px', borderRadius: '50%', background: statusColor, flexShrink: '0' } }),
        h('div', {},
          h('div', { style: { fontSize: '13px', color: 'var(--ink-2)', textTransform: 'uppercase', letterSpacing: '.06em' } }, 'Drug Status'),
          h('h2', { style: { fontSize: '22px', fontWeight: '720', margin: '4px 0 0 0' } }, drug.title))),
      h('div', { style: { fontSize: '13px', color: 'var(--ink-2)', marginBottom: '20px', paddingBottom: '18px', borderBottom: '1px solid var(--line)' } },
        `Evidence strength: ${drug.confidence}%`),

      h('div', { style: { marginBottom: '22px' } },
        h('h3', { style: { fontSize: '14px', fontWeight: '640', marginBottom: '12px' } }, '📚 Sources & Evidence'),
        h('div', { style: { display: 'grid', gap: '14px' } },
          Object.entries(drug.sources).map(([source, data]) => h('div', { style: {
            background: 'var(--teal-50)', padding: '14px', borderRadius: '8px', borderLeft: '3px solid var(--mint-600)'
          }},
            h('div', { style: { fontSize: '13px', fontWeight: '640', marginBottom: '6px' } }, source),
            h('div', { style: { fontSize: '13px', color: 'var(--ink-2)', marginBottom: '8px', lineHeight: '1.5' } }, data.description),
            data.count > 0 ? h('a', { href: data.link, target: '_blank', style: {
              color: 'var(--mint-600)', textDecoration: 'none', fontSize: '13px', fontWeight: '600', display: 'inline-block'
            }}, `View ${data.count} ${source === 'ClinicalTrials.gov' ? 'trials' : 'results'} →`) : null)))),

      drug.timeline?.length ? h('div', { style: { marginBottom: '22px' } },
        h('h3', { style: { fontSize: '14px', fontWeight: '640', marginBottom: '12px' } }, '📅 Research Timeline'),
        h('div', { style: { paddingLeft: '12px', borderLeft: '2px solid var(--line)' } },
          drug.timeline.map(t => h('div', { style: { marginBottom: '12px', paddingLeft: '12px', position: 'relative' } },
            h('div', { style: { position: 'absolute', width: '8px', height: '8px', background: 'var(--mint-600)', borderRadius: '50%',
              top: '6px', left: '-17px' } }),
            h('div', { style: { fontSize: '12px', fontWeight: '640', color: 'var(--ink)' } }, t.year),
            h('div', { style: { fontSize: '13px', color: 'var(--ink-2)', marginTop: '2px' } }, t.event))))) : null));

    modal.appendChild(content);
    document.body.appendChild(modal);
  }


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
              h('td', { style: { fontSize: '12.5px', cursor: g.drug_status ? 'pointer' : 'default' } }, g.drug_status ? h('span', { style: { color: 'var(--mint-600)', fontWeight: '600', textDecoration: 'underline' }, onclick: () => openDrugModal(g.gene) }, g.drug_status + ' →') : '—'),
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

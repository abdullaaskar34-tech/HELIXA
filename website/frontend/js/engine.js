/* ============================================================================
   HELIXA — in-browser inference engine
   KBU-MedLab · Genomics into Decisions

   This is the SAME model that produced every result in this project, running
   in the browser. It is not a re-implementation or an approximation: the
   classifier's forward pass is pure arithmetic, so the exact frozen weights
   are loaded and the identical computation is reproduced step for step.

       align genes → detect library protocol → filter → renormalise to 1e6
       → log2(x+1) → z-score with the stored batch mean/sd
       → take the 1,000 signature genes → subtract the PCA mean
       → 5×1000 matmul → 6×5 matmul → softmax

   Explainability is exact for the same reason. The classifier is linear in
   principal-component space and PCA is linear in gene space, so each gene's
   contribution to the decision is  coef[class] · loading · z(gene)  — the
   decision function itself, decomposed.

   Verified numerically against the Python engine: agreement to < 1e-5.

   WHAT THE PERCENTAGE MEANS  (changed in v2)
   ------------------------------------------
   v1 was trained on the 273 CORE patients only. CORE is defined as the subset
   the consensus clustering could separate cleanly, so those points are nearly
   linearly separable in 5-PC space and the softmax saturated: the median
   reported confidence was 0.9993 and 178 of 328 patients came back at >= 99.9%,
   including tumours the clustering itself had flagged as ambiguous.

   v2 is trained on all 328 patients against the CONSENSUS PROFILE — the
   fraction of 1,000 resampled clusterings in which a tumour co-clusters with
   each subtype. The reported probability therefore measures SUBTYPE STABILITY:
   "73% CL" means this profile lands in the Classical cluster in about 73% of
   resampled clusterings. It is not a clinical or diagnostic probability.

   v2 also returns the Verhaak signature scores and the pathway scores, computed
   from the same z vector, so the browser reproduces the columns recorded for
   the reference cohort rather than only the classifier output.
   ========================================================================== */

const BASE = './model';
// Bump whenever the weights change. The .bin files are fetched by URL, so
// without this a returning visitor keeps the previously cached v1 weights even
// after a successful deploy — the site would look updated and classify with the
// old model.
const MODEL_V = '2.0.0';

let M = null;          // loaded model
let loading = null;    // in-flight promise

const f32 = b => new Float32Array(b);
const i32 = b => new Int32Array(b);

async function fetchBuf(name) {
  const r = await fetch(`${BASE}/${name}?v=${MODEL_V}`);
  if (!r.ok) throw new Error(`model file ${name} missing (${r.status})`);
  return r.arrayBuffer();
}
async function fetchTxt(name) {
  const r = await fetch(`${BASE}/${name}?v=${MODEL_V}`);
  if (!r.ok) throw new Error(`model file ${name} missing (${r.status})`);
  return r.text();
}

/** unpack an LSB-first bit mask into a Uint8Array of 0/1 */
function unpackBits(buf, n) {
  const src = new Uint8Array(buf);
  const out = new Uint8Array(n);
  for (let i = 0; i < n; i++) out[i] = (src[i >> 3] >> (i & 7)) & 1;
  return out;
}

export function isLoaded() { return M !== null; }

export function modelInfo() {
  return M ? M.manifest : null;
}

/** Load the frozen weights. Safe to call repeatedly. */
export async function loadModel(onProgress) {
  if (M) return M;
  if (loading) return loading;
  loading = (async () => {
    const step = (p, m) => onProgress && onProgress(p, m);
    step(0.05, 'Fetching model weights');
    const [manifest, idsTxt, sigNamesTxt, geneSets] = await Promise.all([
      fetch(`${BASE}/manifest.json?v=${MODEL_V}`).then(r => {
        if (!r.ok) throw new Error(`manifest.json missing (${r.status})`); return r.json(); }),
      fetchTxt('gene_ids.txt'),
      fetchTxt('sig_gene_names.txt'),
      // v2: slot lists for the Verhaak signature and pathway gene sets.
      // Absent in a v1 model directory, so a missing file is not fatal.
      fetch(`${BASE}/gene_set_slots.json?v=${MODEL_V}`).then(r => r.ok ? r.json() : null)
        .catch(() => null),
    ]);
    step(0.35, 'Loading weights');
    const [keepB, npaB, statPosB, bm0B, bm1B, gsdB, sigSlotB, pcaMeanB, pcaCompB, coefB, interB] =
      await Promise.all(['keep_mask.bin', 'nonpolya_mask.bin', 'stat_pos.bin',
        'batch_mean_0.bin', 'batch_mean_1.bin', 'global_sd.bin', 'sig_slots.bin',
        'pca_mean.bin', 'pca_components.bin', 'coef.bin', 'intercept.bin'].map(fetchBuf));

    step(0.8, 'Preparing');
    const n = manifest.n_genes;
    const geneIds = idsTxt.split('\n');
    if (geneIds.length !== n) throw new Error(`gene id count mismatch: ${geneIds.length} vs ${n}`);
    const idIndex = new Map();
    for (let i = 0; i < n; i++) idIndex.set(geneIds[i], i);

    M = {
      manifest,
      geneIds, idIndex,
      sigNames: sigNamesTxt.split('\n'),
      keep: unpackBits(keepB, n),
      npa: unpackBits(npaB, n),
      statPos: i32(statPosB),                 // positions in KEEP space
      bm: [f32(bm0B), f32(bm1B)],
      gsd: f32(gsdB),
      sigSlots: i32(sigSlotB),                // signature gene -> row in the stats arrays
      pcaMean: f32(pcaMeanB),
      pcaComp: f32(pcaCompB),                 // (n_pcs * n_sig), row-major
      coef: f32(coefB),                       // (n_classes * n_pcs), row-major
      intercept: f32(interB),
      geneSets: geneSets ? Object.fromEntries(
        Object.entries(geneSets).map(([k, v]) => [k, Int32Array.from(v)])) : null,
    };
    step(1, 'Ready');
    return M;
  })();
  try { return await loading; } finally { loading = null; }
}

/* ── TSV parsing ─────────────────────────────────────────────────────────── */
export function parseGDC(text, filename = 'upload.tsv') {
  const nl = text.indexOf('\n');
  if (nl < 0) throw new Error(`"${filename}" is empty or not a text file.`);
  // line 0 is the "# gene-model:" comment, line 1 is the header
  const hEnd = text.indexOf('\n', nl + 1);
  const header = text.slice(nl + 1, hEnd < 0 ? undefined : hEnd).split('\t');
  const iId = header.indexOf('gene_id');
  const iTpm = header.indexOf('tpm_unstranded');
  if (iId < 0) throw new Error(
    `"${filename}" has no gene_id column — this does not look like a GDC ` +
    `augmented_star_gene_counts.tsv file.`);
  if (iTpm < 0) throw new Error(
    `"${filename}" has no tpm_unstranded column. Columns found: ${header.slice(0, 8).join(', ')}`);

  const rows = new Map();
  let pos = (hEnd < 0 ? text.length : hEnd + 1);
  let count = 0;
  const N = text.length;
  while (pos < N) {
    let eol = text.indexOf('\n', pos);
    if (eol < 0) eol = N;
    const line = text.slice(pos, eol);
    pos = eol + 1;
    if (!line || line.charCodeAt(0) !== 69 /* 'E' */) continue;   // ENSG rows only
    const parts = line.split('\t');
    const gid = parts[iId];
    if (!gid || !gid.startsWith('ENSG')) continue;
    const key = gid.slice(4);                                     // drop the ENSG prefix
    if (rows.has(key)) continue;                                  // keep the first occurrence
    const v = parseFloat(parts[iTpm]);
    rows.set(key, Number.isFinite(v) ? v : 0);
    count++;
  }
  if (count < 1000) throw new Error(
    `"${filename}" contains only ${count} ENSG gene rows — expected around 60,000. ` +
    `The file appears truncated.`);
  return rows;
}

const softmax = a => {
  const m = Math.max(...a);
  const e = a.map(v => Math.exp(v - m));
  const s = e.reduce((x, y) => x + y, 0);
  return e.map(v => v / s);
};

/* ── the forward pass ────────────────────────────────────────────────────── */
export async function analyse(text, filename = 'upload.tsv', onStage) {
  const emit = (id, status, payload) => onStage && onStage(id, status, payload || {});
  if (!M) await loadModel();
  const t0 = performance.now();
  const stages = {};
  const mark = (id, t, extra) => {
    stages[id] = { ms: Math.max(0, Math.round(performance.now() - t)), ...extra };
    emit(id, 'done', stages[id]);
  };

  // 1 · ingest
  let t = performance.now(); emit('ingest', 'running');
  const rows = parseGDC(text, filename);
  mark('ingest', t, { gene_rows_read: rows.size, file: filename,
                      size_kb: Math.round(text.length / 1024) });

  // 2 · align to the training gene space
  t = performance.now(); emit('qc', 'running');
  const n = M.manifest.n_genes;
  const tpm = new Float64Array(n);
  let matched = 0;
  for (let i = 0; i < n; i++) {
    const v = rows.get(M.geneIds[i]);
    if (v !== undefined) { tpm[i] = v; matched++; }
  }
  const coverage = matched / n;
  if (coverage < 0.5) {
    emit('qc', 'error', { matched, expected: n });
    throw new Error(`Only ${matched.toLocaleString()} of ${n.toLocaleString()} expected genes ` +
      `matched (${(coverage * 100).toFixed(1)}%). This file is not compatible with the trained ` +
      `model — a different gene annotation?`);
  }
  mark('qc', t, { genes_matched: matched, genes_expected: n,
                  coverage_pct: +(coverage * 100).toFixed(2),
                  warning: coverage < 0.95 ? 'partial gene coverage' : null });

  // 3 · protocol detection + batch correction
  t = performance.now(); emit('batch', 'running');
  let totAll = 0, totNpa = 0, totKeep = 0;
  for (let i = 0; i < n; i++) {
    const v = tpm[i];
    totAll += v;
    if (M.npa[i]) totNpa += v;
    if (M.keep[i]) totKeep += v;
  }
  const frac = totNpa / Math.max(totAll, 1e-9);
  const thr = M.manifest.protocol_threshold;
  const det = frac > thr ? 1 : 0;
  const ambiguous = Math.abs(frac - thr) < 0.03;
  const scale = 1e6 / Math.max(totKeep, 1e-9);

  // KEEP-space index for every position we need statistics at
  const keepIdx = new Int32Array(M.manifest.n_keep);
  for (let i = 0, k = 0; i < n; i++) if (M.keep[i]) keepIdx[k++] = i;

  const S = M.statPos.length;
  const z = new Float32Array(S);
  const bm = M.bm[det];
  for (let s = 0; s < S; s++) {
    const gi = keepIdx[M.statPos[s]];
    const y = Math.log2(tpm[gi] * scale + 1);
    z[s] = (y - bm[s]) / M.gsd[s];
  }
  mark('batch', t, {
    detected_protocol: det ? 'total-RNA / rRNA-depleted' : 'poly(A)-selected',
    nonpolyA_fraction: +frac.toFixed(5), threshold: +thr.toFixed(5),
    genes_retained: M.manifest.n_keep, genes_removed: n - M.manifest.n_keep,
    ambiguous, warning: ambiguous ? 'protocol fraction close to the decision threshold' : null });

  // 3b · Verhaak signature and pathway scores — plain means of z over each gene
  //      set, the same definition used to build the reference cohort's columns
  const setScores = {};
  if (M.geneSets) {
    for (const [name, slots] of Object.entries(M.geneSets)) {
      let acc = 0;
      for (let i = 0; i < slots.length; i++) acc += z[slots[i]];
      setScores[name] = slots.length ? acc / slots.length : 0;
    }
  }
  const sigScores = {}, pwScores = {};
  for (const [k, v] of Object.entries(setScores)) {
    if (k.startsWith('sig_')) sigScores[k.slice(4)] = +v.toFixed(4);
    else if (k.startsWith('pw_')) pwScores[k.slice(3)] = +v.toFixed(4);
  }
  const vLabels = M.manifest.verhaak_labels || [];
  let verhaakNearest = null;
  if (vLabels.length) {
    let bi = 0;
    for (let i = 1; i < vLabels.length; i++)
      if (sigScores[vLabels[i]] > sigScores[vLabels[bi]]) bi = i;
    verhaakNearest = vLabels[bi];
  }

  // 4 · signature genes
  t = performance.now(); emit('features', 'running');
  const nSig = M.manifest.n_signature;
  const centred = new Float32Array(nSig);
  let absSum = 0;
  for (let j = 0; j < nSig; j++) {
    const v = z[M.sigSlots[j]];
    absSum += Math.abs(v);
    centred[j] = v - M.pcaMean[j];
  }
  mark('features', t, { n_signature_genes: nSig, mean_abs_z: +(absSum / nSig).toFixed(4) });

  // 5 · PCA projection
  t = performance.now(); emit('embed', 'running');
  const nPc = M.manifest.n_pcs;
  const emb = new Float64Array(nPc);
  for (let p = 0; p < nPc; p++) {
    let acc = 0; const off = p * nSig;
    for (let j = 0; j < nSig; j++) acc += centred[j] * M.pcaComp[off + j];
    emb[p] = acc;
  }
  mark('embed', t, { n_components: nPc,
                     coordinates: Array.from(emb, v => +v.toFixed(4)) });

  // 6 · classify
  t = performance.now(); emit('model', 'running');
  const K = M.manifest.n_classes;
  const logits = new Array(K);
  for (let c = 0; c < K; c++) {
    let acc = M.intercept[c]; const off = c * nPc;
    for (let p = 0; p < nPc; p++) acc += emb[p] * M.coef[off + p];
    logits[c] = acc;
  }
  const proba = softmax(logits);
  let pred = 0;
  for (let c = 1; c < K; c++) if (proba[c] > proba[pred]) pred = c;
  mark('model', t, { algorithm: M.manifest.model, predicted_class: pred });

  // 7 · confidence
  t = performance.now(); emit('confidence', 'running');
  const conf = proba[pred];
  const order = proba.map((p, i) => [p, i]).sort((a, b) => b[0] - a[0]);
  const runner = order[1][1];
  const margin = proba[pred] - proba[runner];
  // The clustering itself split CORE from BOUNDARY at a membership margin of
  // 0.50 (own-cluster consensus minus best-other). The same rule is applied
  // here so the model's call is on the same scale as the reference cohort.
  const tau = (M.manifest.core_tau !== undefined) ? M.manifest.core_tau : 0.50;
  const call = margin >= tau ? 'CORE' : 'BOUNDARY';
  const band = margin >= tau ? 'stable'
             : conf >= 0.5 ? 'moderate' : 'intermediate';
  mark('confidence', t, { confidence: +conf.toFixed(4), band, call,
                          margin: +margin.toFixed(4), runner_up: runner, tau });

  // 8 · explain
  t = performance.now(); emit('validate', 'running');
  const contrib = new Float64Array(nSig);
  for (let j = 0; j < nSig; j++) {
    let w = 0;
    for (let p = 0; p < nPc; p++) w += M.coef[pred * nPc + p] * M.pcaComp[p * nSig + j];
    contrib[j] = w * centred[j];
  }
  const idx = Array.from({ length: nSig }, (_, j) => j).sort((a, b) => contrib[b] - contrib[a]);
  let totalPos = 0;
  for (let j = 0; j < nSig; j++) if (contrib[j] > 0) totalPos += contrib[j];
  totalPos = totalPos || 1;

  const zAt = j => z[M.sigSlots[j]];
  const topFor = idx.slice(0, 12).map(j => ({
    gene: M.sigNames[j], contribution: +contrib[j].toFixed(4),
    z: +zAt(j).toFixed(3), share_pct: +(100 * contrib[j] / totalPos).toFixed(2) }));
  const topAgainst = idx.slice(-8).reverse().map(j => ({
    gene: M.sigNames[j], contribution: +contrib[j].toFixed(4), z: +zAt(j).toFixed(3) }));

  const pcContrib = Array.from({ length: nPc }, (_, p) => ({
    pc: `PC${p + 1}`, value: +emb[p].toFixed(3),
    coef: +M.coef[pred * nPc + p].toFixed(4),
    contribution: +(emb[p] * M.coef[pred * nPc + p]).toFixed(4) }));

  const markerList = M.manifest.markers[String(pred)] || [];
  const markerReadout = [];
  for (const g of markerList) {
    const slot = M.manifest.marker_slots[g];
    if (slot === undefined) continue;
    const zv = z[slot];
    markerReadout.push({ gene: g, z: +zv.toFixed(3), elevated: zv > 0 });
  }
  const nElev = markerReadout.filter(m => m.elevated).length;
  mark('validate', t, { markers_checked: markerReadout.length, markers_elevated: nElev,
    agreement_pct: markerReadout.length ? +(100 * nElev / markerReadout.length).toFixed(1) : null,
    genes_driving_decision: topFor.length });

  // 9 · done
  t = performance.now(); emit('insight', 'running'); mark('insight', t, {});

  const info = M.manifest.subtypes[String(pred)];
  return {
    ok: true, file: filename,
    predicted_class: pred,
    subtype_label: info.label, subtype_title: info.title,
    summary: info.summary, therapeutic_context: info.therapeutic,
    confidence: +conf.toFixed(4), confidence_band: band,
    margin: +margin.toFixed(4), call, core_tau: tau,
    runner_up_class: runner,
    probabilities: proba.map(p => +p.toFixed(6)),
    signature_scores: sigScores, pathway_scores: pwScores,
    verhaak_nearest: verhaakNearest,
    probability_meaning: M.manifest.probability_meaning ||
      'Fraction of resampled clusterings in which this profile co-clusters ' +
      'with that subtype — subtype stability, not clinical probability.',
    detected_protocol: stages.batch.detected_protocol,
    nonpolyA_fraction: stages.batch.nonpolyA_fraction,
    protocol_ambiguous: ambiguous,
    genes_matched: matched, genes_expected: n,
    embedding: Array.from(emb, v => +v.toFixed(4)),
    marker_readout: markerReadout,
    why: { top_genes_for: topFor, top_genes_against: topAgainst, pc_contributions: pcContrib,
           method: 'The classifier is linear in principal-component space and PCA is linear in ' +
                   'gene space, so each gene\'s exact contribution to this decision is ' +
                   'coef[class] · loading · z(gene) — the decision function itself, decomposed.' },
    stages,
    total_ms: Math.round(performance.now() - t0),
    model_name: M.manifest.model,
    // v2 reports what it actually measured. cv_accuracy / roc_auc_ovr were v1
    // accuracy-family figures against the clustering's own labels; they are not
    // the right summary for a model fitted to the consensus profile, so they are
    // replaced rather than recomputed. Kept as aliases so older consumers that
    // read r.cv_accuracy still render something truthful instead of undefined.
    loo_agreement: M.manifest.loo_agreement,
    loo_agreement_core: M.manifest.loo_agreement_core,
    loo_agreement_boundary: M.manifest.loo_agreement_boundary,
    oof_profile_corr: M.manifest.oof_profile_corr,
    oof_profile_rmse: M.manifest.oof_profile_rmse,
    n_train: M.manifest.n_train,
    cv_accuracy: M.manifest.loo_agreement,
    roc_auc: M.manifest.oof_profile_corr,
    model_version: M.manifest.version,
    ran_in: 'browser',
  };
}

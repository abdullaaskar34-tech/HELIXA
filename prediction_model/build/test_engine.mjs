/* Run the real browser engine (engine.js, unmodified) in Node against the
   exported v2 model and a real GDC file, then compare with the Python result.
   fetch is stubbed to read from the local model directory. */
import { readFile } from 'node:fs/promises';
import path from 'node:path';

const MODEL = process.argv[2];
const TSV = process.argv[3];
const EXPECT = process.argv[4];

globalThis.fetch = async (url) => {
  const name = String(url).replace(/^\.\/model\//, '');
  const p = path.join(MODEL, name);
  try {
    const buf = await readFile(p);
    return {
      ok: true, status: 200,
      arrayBuffer: async () => buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength),
      text: async () => buf.toString('utf8'),
      json: async () => JSON.parse(buf.toString('utf8')),
    };
  } catch {
    return { ok: false, status: 404, arrayBuffer: async () => { throw new Error('404'); },
             text: async () => { throw new Error('404'); }, json: async () => { throw new Error('404'); } };
  }
};

const { analyse } = await import('./website/frontend/js/engine.js');
const text = await readFile(TSV, 'utf8');
const r = await analyse(text, path.basename(TSV));

const exp = JSON.parse(await readFile(EXPECT, 'utf8'));
const e = Array.isArray(exp) ? exp.find(x => TSV.includes(x.sample_id)) : exp;

const SHORT = ['MTC', 'PN', 'CL', 'MES', 'INT', 'OLIGO'];
console.log('browser engine result');
console.log('  subtype        ', SHORT[r.predicted_class], `(${(r.confidence * 100).toFixed(1)}%)`);
console.log('  call           ', r.call, 'margin', r.margin);
console.log('  protocol       ', r.detected_protocol);
console.log('  verhaak nearest', r.verhaak_nearest);
console.log('  probabilities  ', r.probabilities.map((p, i) => `${SHORT[i]} ${(p * 100).toFixed(1)}%`).join('  '));
console.log('  pathway scores ', JSON.stringify(r.pathway_scores));
console.log('  signature      ', JSON.stringify(r.signature_scores));

if (e) {
  const dProb = Math.max(...SHORT.map((s, i) => Math.abs(r.probabilities[i] - e.probabilities[s])));
  const dPw = Math.max(...Object.entries(e.pathway_scores).map(([k, v]) => Math.abs(r.pathway_scores[k] - v)));
  const dSig = Math.max(...Object.entries(e.signature_scores).map(([k, v]) => Math.abs(r.signature_scores[k] - v)));
  console.log('\nagreement with the Python predictor');
  console.log('  same subtype        ', SHORT[r.predicted_class] === e.subtype ? 'yes' : 'NO');
  console.log('  same call           ', r.call === e.call ? 'yes' : 'NO');
  console.log('  same protocol       ', r.detected_protocol.includes('total') === (e.library_batch === 'totalRNA_rRNAdepleted') ? 'yes' : 'NO');
  console.log('  same verhaak        ', r.verhaak_nearest === e.verhaak_nearest ? 'yes' : 'NO');
  console.log('  max |Δ probability| ', dProb.toExponential(3));
  console.log('  max |Δ pathway|     ', dPw.toExponential(3));
  console.log('  max |Δ signature|   ', dSig.toExponential(3));
  const bad = SHORT[r.predicted_class] !== e.subtype || dProb > 1e-3 || dPw > 1e-3 || dSig > 1e-3;
  if (bad) { console.error('\nMISMATCH'); process.exit(1); }
  console.log('\nOK — the browser engine matches the Python predictor.');
}

/* Regenerate demo_results.json by running the REAL engine.js against the same
   five demo patients, so the site's examples show v2 numbers that are exactly
   what a user uploading those files would get. */
import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';

const MODEL = process.argv[2];
const TSVDIR = process.argv[3];
const OLD = process.argv[4];
const OUT = process.argv[5];
const ENGINE = process.argv[6];

globalThis.fetch = async (url) => {
  const name = String(url).replace(/^\.\/model\//, '');
  const p = path.join(MODEL, name);
  try {
    const buf = await readFile(p);
    return { ok: true, status: 200,
      arrayBuffer: async () => buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength),
      text: async () => buf.toString('utf8'),
      json: async () => JSON.parse(buf.toString('utf8')) };
  } catch {
    return { ok: false, status: 404,
      arrayBuffer: async () => { throw new Error('404'); },
      text: async () => { throw new Error('404'); },
      json: async () => { throw new Error('404'); } };
  }
};

const { analyse } = await import(ENGINE);
const old = JSON.parse(await readFile(OLD, 'utf8'));
const map = JSON.parse(await readFile(path.join(TSVDIR, '_map.json'), 'utf8'));

const out = [];
for (const o of old) {
  const full = map[o.demo_sample];
  if (!full) { console.error('no sample for', o.demo_sample); continue; }
  const text = await readFile(path.join(TSVDIR, full + '.tsv'), 'utf8');
  const r = await analyse(text, o.file);
  // carry over the demo identity fields the frontend expects
  r.demo_id = o.demo_id;
  r.demo_sample = o.demo_sample;
  r.subtype_name = o.subtype_name;
  r.file = o.file;
  out.push(r);
  console.log(`${o.demo_id}  ${o.subtype_label || ''} -> ${r.subtype_label}  ` +
    `conf ${o.confidence.toFixed(4)} -> ${r.confidence.toFixed(4)}  ` +
    `${r.call}  margin ${r.margin.toFixed(3)}  [${r.detected_protocol}]`);
}
await writeFile(OUT, JSON.stringify(out));
console.log('\nwrote', OUT);

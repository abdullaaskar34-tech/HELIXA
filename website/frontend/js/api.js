/* HELIXA — data layer
   Loads the REAL exported results that were exported from the project. Never
   invents data: if something is missing it says so. The classifier itself lives
   in js/engine.js and runs in the browser — there is no backend.               */

const DATA = './data';
const V = '20260815a';
const cache = new Map();

export async function loadJSON(name) {
  if (cache.has(name)) return cache.get(name);
  const r = await fetch(`${DATA}/${name}.json?v=${V}`);
  if (!r.ok) throw new Error(`Could not load ${name}.json (${r.status})`);
  const d = await r.json();
  cache.set(name, d);
  return d;
}

export function loadAll(names) {
  return Promise.all(names.map(loadJSON));
}

/* ── derived helpers over the real cohort ──────────────────────────────── */
export function clusterById(clusters, id) {
  return clusters.find(c => c.id === id);
}

export function filterPatients(patients, f) {
  return patients.filter(p => {
    if (f.clusters?.length && !f.clusters.includes(p.cluster)) return false;
    if (f.batch && p.library_batch !== f.batch) return false;
    if (f.verhaak && p.verhaak_nearest !== f.verhaak) return false;
    if (f.confidence === 'core' && !p.is_core) return false;
    if (f.confidence === 'boundary' && p.is_core) return false;
    if (f.minMembership != null && (p.consensus_membership ?? 0) < f.minMembership) return false;
    if (f.q) {
      const q = f.q.toLowerCase();
      if (!(p.id.toLowerCase().includes(q) ||
            p.sample_id.toLowerCase().includes(q) ||
            p.cluster_name.toLowerCase().includes(q) ||
            (p.verhaak_nearest || '').toLowerCase().includes(q))) return false;
    }
    return true;
  });
}

export const fmtPct = (v, d = 1) => (v == null || Number.isNaN(v)) ? '—' : `${(v * 100).toFixed(d)}%`;
export const fmtNum = (v, d = 3) => (v == null || Number.isNaN(v)) ? '—' : Number(v).toFixed(d);
export const fmtInt = (v) => (v == null) ? '—' : Number(v).toLocaleString('en-US');
export const fmtP = (p) => {
  if (p == null) return '—';
  if (p === 0) return '< 1e-300';
  if (p < 1e-4) return p.toExponential(1).replace('e', ' × 10^');
  return p.toFixed(4);
};

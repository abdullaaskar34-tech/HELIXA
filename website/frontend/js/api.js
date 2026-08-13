/* HELIXA — data layer
   Loads the REAL exported results, and talks to the live inference API when it
   is reachable. Never invents data: if something is missing it says so.        */

const DATA = './data';
const cache = new Map();

/* Candidate API bases, tried in order. Override with ?api=<url> */
function apiBases() {
  const q = new URLSearchParams(location.search).get('api');
  const l = localStorage.getItem('helixa_api');
  const out = [];
  if (q) out.push(q.replace(/\/$/, ''));
  if (l) out.push(l.replace(/\/$/, ''));
  out.push('http://127.0.0.1:8000', 'http://localhost:8000');
  if (location.protocol !== 'file:' && !/github\.io$/.test(location.hostname)) {
    out.push(location.origin);
  }
  return [...new Set(out)];
}

export const state = {
  api: null,          // resolved base url, or null
  engine: null,       // engine status payload
  live: false,        // is the real inference engine reachable?
  checked: false,
};

export async function loadJSON(name) {
  if (cache.has(name)) return cache.get(name);
  const r = await fetch(`${DATA}/${name}.json`, { cache: 'force-cache' });
  if (!r.ok) throw new Error(`Could not load ${name}.json (${r.status})`);
  const d = await r.json();
  cache.set(name, d);
  return d;
}

export function loadAll(names) {
  return Promise.all(names.map(loadJSON));
}

/* ── backend detection ─────────────────────────────────────────────────── */
export async function detectAPI({ timeout = 1800 } = {}) {
  if (state.checked) return state;
  state.checked = true;
  for (const base of apiBases()) {
    try {
      const c = new AbortController();
      const t = setTimeout(() => c.abort(), timeout);
      const r = await fetch(`${base}/api/health`, { signal: c.signal });
      clearTimeout(t);
      if (!r.ok) continue;
      const h = await r.json();
      if (h && h.engine) {
        state.api = base;
        state.engine = h.engine;
        state.live = !!h.engine.available;
        return state;
      }
    } catch { /* try next */ }
  }
  return state;
}

export function setAPI(url) {
  localStorage.setItem('helixa_api', url);
  state.checked = false;
  return detectAPI();
}

/* ── live analysis ─────────────────────────────────────────────────────── */
export async function startAnalysis(file) {
  if (!state.api) throw new Error('No inference API is connected.');
  const fd = new FormData();
  fd.append('file', file, file.name);
  const r = await fetch(`${state.api}/api/analyze`, { method: 'POST', body: fd });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(d.error || `Analysis request failed (${r.status})`);
  return d;
}

export async function pollAnalysis(jobId) {
  const r = await fetch(`${state.api}/api/analyze/${jobId}`);
  if (!r.ok) throw new Error(`Could not read job status (${r.status})`);
  return r.json();
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

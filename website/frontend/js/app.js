/* HELIXA — application shell & router
   KBU-MedLab · Genomics into Decisions                                      */

import { loader, errorBox } from './ui.js?v=20260827d';

/* ─────────────────────────────────────────── intro animation */
function introCanvas(cv, { density = 0.00011, tint = '18,180,143' } = {}) {
  const ctx = cv.getContext('2d');
  let w, h, dpr, nodes = [], raf, alive = true;
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;

  function size() {
    dpr = Math.min(devicePixelRatio || 1, 2);
    w = cv.clientWidth; h = cv.clientHeight;
    cv.width = w * dpr; cv.height = h * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const n = Math.max(26, Math.min(90, Math.round(w * h * density)));
    nodes = Array.from({ length: n }, () => ({
      x: Math.random() * w, y: Math.random() * h,
      vx: (Math.random() - .5) * .22, vy: (Math.random() - .5) * .22,
      r: 1.1 + Math.random() * 1.9,
    }));
  }
  function frame() {
    if (!alive) return;
    ctx.clearRect(0, 0, w, h);
    for (const p of nodes) {
      if (!reduce) { p.x += p.vx; p.y += p.vy; }
      if (p.x < 0 || p.x > w) p.vx *= -1;
      if (p.y < 0 || p.y > h) p.vy *= -1;
    }
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i], b = nodes[j];
        const d = Math.hypot(a.x - b.x, a.y - b.y);
        if (d < 128) {
          ctx.strokeStyle = `rgba(${tint},${(1 - d / 128) * .26})`;
          ctx.lineWidth = 1;
          ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
        }
      }
    }
    for (const p of nodes) {
      ctx.fillStyle = `rgba(${tint},.5)`;
      ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, 7); ctx.fill();
    }
    raf = requestAnimationFrame(frame);
  }
  size(); frame();
  const onR = () => size();
  addEventListener('resize', onR);
  return () => { alive = false; cancelAnimationFrame(raf); removeEventListener('resize', onR); };
}

function endIntro() {
  const i = document.getElementById('intro');
  if (!i || i.classList.contains('hide')) return;
  i.classList.add('hide');
  document.getElementById('nav').hidden = false;
  document.getElementById('footer').hidden = false;
  sessionStorage.setItem('helixa_intro', '1');
  setTimeout(() => { i.remove(); stopIntro?.(); }, 950);
}

let stopIntro = null;

/* ─────────────────────────────────────────── router */
const routes = {
  '/':        () => import('./views/home.js?v=20260827d'),
  '/analyze': () => import('./views/analyze.js?v=20260827d'),
};

function parseHash() {
  const raw = (location.hash || '#/').slice(1);
  const [path, qs] = raw.split('?');
  const parts = path.split('/').filter(Boolean);
  const base = '/' + (parts[0] || '');
  return { base, param: parts[1] ? decodeURIComponent(parts[1]) : null,
           query: new URLSearchParams(qs || '') };
}

let currentCleanup = null;

async function render() {
  const { base, param, query } = parseHash();
  const loadView = routes[base] || routes['/'];
  const app = document.getElementById('app');

  document.querySelectorAll('.nav-links a').forEach(a => {
    const t = (a.getAttribute('href') || '').slice(1).split('?')[0];
    a.classList.toggle('active', t === base);
  });
  document.getElementById('nav-links')?.classList.remove('open');
  document.getElementById('burger')?.setAttribute('aria-expanded', 'false');

  if (currentCleanup) { try { currentCleanup(); } catch {} currentCleanup = null; }
  app.replaceChildren(loader());

  try {
    const mod = await loadView();
    const node = await mod.default({ param, query });
    app.replaceChildren();
    if (node instanceof Node) app.appendChild(node);
    app.classList.remove('fade-in'); void app.offsetWidth; app.classList.add('fade-in');
    currentCleanup = mod.cleanup || null;
    if (!query.get('keepscroll')) scrollTo({ top: 0, behavior: 'instant' in scrollTo ? 'instant' : 'auto' });
  } catch (e) {
    console.error('[HELIXA] view error', e);
    app.replaceChildren(errorBox(e));
  }
}

/* ─────────────────────────────────────────── boot */
function boot() {
  document.getElementById('yr').textContent = new Date().getFullYear();

  const seen = sessionStorage.getItem('helixa_intro');
  if (seen) {
    document.getElementById('intro')?.remove();
    document.getElementById('nav').hidden = false;
    document.getElementById('footer').hidden = false;
  } else {
    const cv = document.getElementById('intro-canvas');
    if (cv) stopIntro = introCanvas(cv);
    document.getElementById('skip-intro')?.addEventListener('click', endIntro);
    setTimeout(endIntro, 4200);
    addEventListener('keydown', e => { if (e.key === 'Escape' || e.key === 'Enter') endIntro(); },
      { once: true });
  }

  document.getElementById('burger')?.addEventListener('click', e => {
    const l = document.getElementById('nav-links');
    const open = l.classList.toggle('open');
    e.currentTarget.setAttribute('aria-expanded', open ? 'true' : 'false');
  });

  const lb = document.getElementById('lightbox');
  const close = () => lb.classList.remove('on');
  lb.addEventListener('click', e => { if (e.target === lb || e.target.id === 'lb-img') close(); });
  document.getElementById('lb-close').addEventListener('click', close);
  addEventListener('keydown', e => { if (e.key === 'Escape') close(); });

  addEventListener('hashchange', render);
  render();

  console.info('[HELIXA] The classifier runs in this browser — no server involved.');
}

if (document.readyState === 'loading') addEventListener('DOMContentLoaded', boot);
else boot();

export { introCanvas };

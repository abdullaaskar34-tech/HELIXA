/* HELIXA — SVG chart primitives.
   Hand-built, dependency-free. Every chart carries a legend or direct labels,
   so identity is never colour-alone, and every mark exposes a hover tooltip. */

export const PALETTE = ['#0EAE8F', '#E8833A', '#2E7BC4', '#C79A2C', '#C2649B', '#5B8C2A'];
export const TEAL = { ink: '#0A2B29', ink2: '#3D5C58', ink3: '#6B8985',
                      line: '#DCEAE5', mint: '#12B48F', deep: '#0B3B39',
                      ok: '#12855F', warn: '#B57200', err: '#C0392B' };

let tipEl = null;
function tip() { return tipEl ||= document.getElementById('tip'); }

export function bindTip(el, html) {
  el.style.cursor = 'default';
  el.addEventListener('mousemove', e => {
    const t = tip(); if (!t) return;
    t.innerHTML = html;
    t.classList.add('on');
    const pad = 14, w = t.offsetWidth, h = t.offsetHeight;
    let x = e.clientX + pad, y = e.clientY - h - 8;
    if (x + w > innerWidth - 8) x = e.clientX - w - pad;
    if (y < 8) y = e.clientY + pad;
    t.style.left = x + 'px'; t.style.top = y + 'px';
  });
  el.addEventListener('mouseleave', () => tip()?.classList.remove('on'));
}

const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const SVGNS = 'http://www.w3.org/2000/svg';
function el(n, a = {}) {
  const e = document.createElementNS(SVGNS, n);
  for (const k in a) if (a[k] != null) e.setAttribute(k, a[k]);
  return e;
}
function svg(w, h, cls = '') {
  const s = el('svg', { viewBox: `0 0 ${w} ${h}`, class: cls, role: 'img' });
  s.style.width = '100%'; s.style.height = 'auto'; s.style.display = 'block';
  return s;
}
function txt(x, y, s, o = {}) {
  const t = el('text', { x, y, fill: o.fill || TEAL.ink2, 'font-size': o.size || 11,
    'text-anchor': o.anchor || 'start', 'font-weight': o.weight || 500,
    'dominant-baseline': o.baseline || 'auto', transform: o.transform });
  t.textContent = s;
  if (o.mono) t.setAttribute('font-family', 'JetBrains Mono, monospace');
  return t;
}
const nice = v => { const p = Math.pow(10, Math.floor(Math.log10(Math.abs(v) || 1)));
  return Math.ceil(v / p) * p; };

/* ───────────────────────────────────────────── horizontal bars */
export function barsH(data, opts = {}) {
  const { w = 560, rowH = 34, pad = { t: 8, r: 60, b: 26, l: 150 },
          fmt = v => v.toFixed(2), max: mx, colorKey = 'color', label = 'value' } = opts;
  const h = pad.t + data.length * rowH + pad.b;
  const s = svg(w, h);
  const maxV = mx ?? nice(Math.max(...data.map(d => d.value), 0.0001));
  const bw = w - pad.l - pad.r;
  for (let i = 0; i <= 4; i++) {
    const x = pad.l + bw * i / 4;
    s.appendChild(el('line', { x1: x, y1: pad.t, x2: x, y2: h - pad.b,
      stroke: TEAL.line, 'stroke-width': 1 }));
    s.appendChild(txt(x, h - pad.b + 15, fmt(maxV * i / 4), { anchor: 'middle', size: 10, fill: TEAL.ink3 }));
  }
  data.forEach((d, i) => {
    const y = pad.t + i * rowH, bh = Math.min(19, rowH - 12);
    const bl = Math.max(2, bw * (d.value / maxV));
    s.appendChild(txt(pad.l - 11, y + bh / 2 + 4, d.label, { anchor: 'end', size: 11.5, weight: 550, fill: TEAL.ink }));
    const g = el('g'); g.style.cursor = 'default';
    const r = el('rect', { x: pad.l, y, width: bl, height: bh, rx: 4,
      fill: d[colorKey] || PALETTE[i % PALETTE.length] });
    r.style.transition = 'opacity .18s';
    g.appendChild(r);
    g.appendChild(txt(pad.l + bl + 8, y + bh / 2 + 4, fmt(d.value), { size: 11, weight: 620, fill: TEAL.ink }));
    bindTip(g, `<b>${esc(d.label)}</b><br>${esc(label)}: ${fmt(d.value)}${d.note ? '<br>' + esc(d.note) : ''}`);
    g.addEventListener('mouseenter', () => r.style.opacity = .78);
    g.addEventListener('mouseleave', () => r.style.opacity = 1);
    if (d.onClick) { g.style.cursor = 'pointer'; g.addEventListener('click', d.onClick); }
    s.appendChild(g);
  });
  return s;
}

/* ───────────────────────────────────────────── vertical bars */
export function barsV(data, opts = {}) {
  const { w = 560, h = 260, pad = { t: 16, r: 12, b: 54, l: 46 },
          fmt = v => v.toFixed(0), yLabel = '' } = opts;
  const s = svg(w, h);
  const maxV = nice(Math.max(...data.map(d => d.value), 1));
  const iw = w - pad.l - pad.r, ih = h - pad.t - pad.b;
  const bw = iw / data.length;
  for (let i = 0; i <= 4; i++) {
    const y = pad.t + ih * (1 - i / 4);
    s.appendChild(el('line', { x1: pad.l, y1: y, x2: w - pad.r, y2: y, stroke: TEAL.line }));
    s.appendChild(txt(pad.l - 7, y + 3.5, fmt(maxV * i / 4), { anchor: 'end', size: 10, fill: TEAL.ink3 }));
  }
  if (yLabel) s.appendChild(txt(12, pad.t + ih / 2, yLabel,
    { anchor: 'middle', size: 10.5, fill: TEAL.ink3, transform: `rotate(-90 12 ${pad.t + ih / 2})` }));
  data.forEach((d, i) => {
    const bh = Math.max(1, ih * (d.value / maxV));
    const x = pad.l + i * bw + bw * .18, bwd = bw * .64;
    const g = el('g');
    const r = el('rect', { x, y: pad.t + ih - bh, width: bwd, height: bh, rx: 4,
      fill: d.color || PALETTE[i % PALETTE.length] });
    r.style.transition = 'opacity .18s'; g.appendChild(r);
    g.appendChild(txt(x + bwd / 2, pad.t + ih - bh - 6, fmt(d.value),
      { anchor: 'middle', size: 10.5, weight: 620, fill: TEAL.ink }));
    const lbl = txt(x + bwd / 2, pad.t + ih + 15, d.label, { anchor: 'middle', size: 10.5, fill: TEAL.ink2 });
    if (String(d.label).length > 9) {
      lbl.setAttribute('transform', `rotate(-32 ${x + bwd / 2} ${pad.t + ih + 15})`);
      lbl.setAttribute('text-anchor', 'end');
    }
    s.appendChild(lbl);
    bindTip(g, `<b>${esc(d.label)}</b><br>${fmt(d.value)}${d.note ? '<br>' + esc(d.note) : ''}`);
    g.addEventListener('mouseenter', () => r.style.opacity = .78);
    g.addEventListener('mouseleave', () => r.style.opacity = 1);
    if (d.onClick) { g.style.cursor = 'pointer'; g.addEventListener('click', d.onClick); }
    s.appendChild(g);
  });
  return s;
}

/* ───────────────────────────────────────────── donut */
export function donut(data, opts = {}) {
  const { size = 250, thick = 34, center } = opts;
  const s = svg(size, size);
  const total = data.reduce((a, d) => a + d.value, 0) || 1;
  const cx = size / 2, cy = size / 2, R = size / 2 - 6, r = R - thick;
  let a0 = -Math.PI / 2;
  data.forEach((d, i) => {
    const a1 = a0 + (d.value / total) * Math.PI * 2;
    const gap = data.length > 1 ? 0.016 : 0;
    const s0 = a0 + gap / 2, s1 = a1 - gap / 2;
    const large = (s1 - s0) > Math.PI ? 1 : 0;
    const p = el('path', {
      d: `M ${cx + R * Math.cos(s0)} ${cy + R * Math.sin(s0)}
          A ${R} ${R} 0 ${large} 1 ${cx + R * Math.cos(s1)} ${cy + R * Math.sin(s1)}
          L ${cx + r * Math.cos(s1)} ${cy + r * Math.sin(s1)}
          A ${r} ${r} 0 ${large} 0 ${cx + r * Math.cos(s0)} ${cy + r * Math.sin(s0)} Z`,
      fill: d.color || PALETTE[i % PALETTE.length] });
    p.style.transition = 'opacity .18s';
    bindTip(p, `<b>${esc(d.label)}</b><br>${d.value} · ${(d.value / total * 100).toFixed(1)}%`);
    p.addEventListener('mouseenter', () => p.style.opacity = .75);
    p.addEventListener('mouseleave', () => p.style.opacity = 1);
    if (d.onClick) { p.style.cursor = 'pointer'; p.addEventListener('click', d.onClick); }
    s.appendChild(p);
    a0 = a1;
  });
  if (center) {
    s.appendChild(txt(cx, cy - 2, center.value, { anchor: 'middle', size: 30, weight: 700, fill: TEAL.deep }));
    s.appendChild(txt(cx, cy + 18, center.label, { anchor: 'middle', size: 10.5, fill: TEAL.ink3, weight: 600 }));
  }
  return s;
}

/* ───────────────────────────────────────────── confidence gauge */
export function gauge(value, opts = {}) {
  const { size = 200, label = 'Confidence', color, thick = 15 } = opts;
  const s = svg(size, size * .68);
  const cx = size / 2, cy = size * .58, R = size / 2 - 14;
  const arc = (from, to, col, wdt) => {
    const a0 = Math.PI * (1 + from), a1 = Math.PI * (1 + to);
    const large = (a1 - a0) > Math.PI ? 1 : 0;
    return el('path', { d: `M ${cx + R * Math.cos(a0)} ${cy + R * Math.sin(a0)}
      A ${R} ${R} 0 ${large} 1 ${cx + R * Math.cos(a1)} ${cy + R * Math.sin(a1)}`,
      fill: 'none', stroke: col, 'stroke-width': wdt, 'stroke-linecap': 'round' });
  };
  s.appendChild(arc(0, 1, '#E4F0EC', thick));
  const v = Math.max(0, Math.min(1, value || 0));
  const col = color || (v >= .8 ? TEAL.ok : v >= .5 ? TEAL.mint : TEAL.warn);
  if (v > 0.002) s.appendChild(arc(0, v, col, thick));
  s.appendChild(txt(cx, cy - 12, (v * 100).toFixed(1) + '%',
    { anchor: 'middle', size: 27, weight: 700, fill: TEAL.deep }));
  s.appendChild(txt(cx, cy + 8, label, { anchor: 'middle', size: 10, fill: TEAL.ink3, weight: 620 }));
  s.appendChild(txt(cx - R, cy + 17, '0%', { anchor: 'middle', size: 9.5, fill: TEAL.ink3 }));
  s.appendChild(txt(cx + R, cy + 17, '100%', { anchor: 'middle', size: 9.5, fill: TEAL.ink3 }));
  return s;
}

/* ───────────────────────────────────────────── scatter (embedding map) */
export function scatter(points, opts = {}) {
  const { w = 640, h = 440, pad = 34, colors = PALETTE, highlight = null,
          xLabel = 'PC1', yLabel = 'PC2', onPick = null, dim = new Set() } = opts;
  const s = svg(w, h);
  const xs = points.map(p => p.x), ys = points.map(p => p.y);
  let x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
  if (highlight) { x0 = Math.min(x0, highlight.x); x1 = Math.max(x1, highlight.x);
                   y0 = Math.min(y0, highlight.y); y1 = Math.max(y1, highlight.y); }
  const mx = (x1 - x0) * .08 || 1, my = (y1 - y0) * .08 || 1;
  x0 -= mx; x1 += mx; y0 -= my; y1 += my;
  const X = v => pad + (v - x0) / (x1 - x0) * (w - pad * 2);
  const Y = v => h - pad - (v - y0) / (y1 - y0) * (h - pad * 2);
  for (let i = 0; i <= 4; i++) {
    s.appendChild(el('line', { x1: pad, y1: pad + (h - pad * 2) * i / 4, x2: w - pad,
      y2: pad + (h - pad * 2) * i / 4, stroke: TEAL.line, 'stroke-dasharray': '2 4' }));
    s.appendChild(el('line', { x1: pad + (w - pad * 2) * i / 4, y1: pad,
      x2: pad + (w - pad * 2) * i / 4, y2: h - pad, stroke: TEAL.line, 'stroke-dasharray': '2 4' }));
  }
  s.appendChild(txt(w / 2, h - 6, xLabel, { anchor: 'middle', size: 10.5, fill: TEAL.ink3 }));
  s.appendChild(txt(11, h / 2, yLabel, { anchor: 'middle', size: 10.5, fill: TEAL.ink3,
    transform: `rotate(-90 11 ${h / 2})` }));
  points.forEach(p => {
    const faded = dim.size && dim.has(p.c);
    const c = el('circle', { cx: X(p.x), cy: Y(p.y), r: p.core === false ? 3.2 : 4.2,
      fill: faded ? '#D8E6E2' : (colors[p.c % colors.length]),
      'fill-opacity': faded ? .45 : (p.core === false ? .42 : .82),
      stroke: p.core === false ? (faded ? '#CBDDD8' : colors[p.c % colors.length]) : 'none',
      'stroke-width': p.core === false ? 1.2 : 0 });
    c.style.transition = 'r .15s';
    bindTip(c, `<b>${esc(p.sid || '')}</b><br>${esc(p.name || 'cluster ' + p.c)}<br>` +
      `${p.core === false ? 'boundary tumour' : 'core tumour'}`);
    c.addEventListener('mouseenter', () => c.setAttribute('r', 7));
    c.addEventListener('mouseleave', () => c.setAttribute('r', p.core === false ? 3.2 : 4.2));
    if (onPick) { c.style.cursor = 'pointer'; c.addEventListener('click', () => onPick(p)); }
    s.appendChild(c);
  });
  if (highlight) {
    const g = el('g');
    g.appendChild(el('circle', { cx: X(highlight.x), cy: Y(highlight.y), r: 15,
      fill: 'none', stroke: TEAL.err, 'stroke-width': 2, opacity: .55 }));
    g.appendChild(el('circle', { cx: X(highlight.x), cy: Y(highlight.y), r: 8,
      fill: TEAL.err, stroke: '#fff', 'stroke-width': 2.5 }));
    bindTip(g, `<b>${esc(highlight.label || 'New patient')}</b>`);
    s.appendChild(g);
    s.appendChild(txt(X(highlight.x), Y(highlight.y) - 22, highlight.label || 'NEW PATIENT',
      { anchor: 'middle', size: 11, weight: 700, fill: TEAL.err }));
  }
  return s;
}

/* ───────────────────────────────────────────── heatmap */
export function heatmap(matrix, rows, cols, opts = {}) {
  const { w = 620, cell = 36, pad = { t: 66, r: 16, b: 14, l: 168 },
          fmt = v => v == null ? '' : v.toFixed(0), diverging = false,
          max: fixedMax, unit = '' } = opts;
  const cw = Math.min(cell + 18, (w - pad.l - pad.r) / cols.length);
  const h = pad.t + rows.length * cell + pad.b;
  const s = svg(Math.max(w, pad.l + cols.length * cw + pad.r), h);
  const flat = matrix.flat().filter(v => v != null && !Number.isNaN(v));
  const mx = fixedMax ?? Math.max(...flat.map(Math.abs), 1e-9);
  const mn = diverging ? -mx : 0;
  const col = v => {
    if (v == null || Number.isNaN(v)) return '#F2F7F5';
    if (diverging) {
      const t = Math.max(-1, Math.min(1, v / mx));
      return t >= 0 ? `rgba(14,174,143,${.12 + .82 * t})` : `rgba(196,110,60,${.12 + .82 * -t})`;
    }
    return `rgba(14,84,80,${.07 + .88 * Math.max(0, Math.min(1, (v - mn) / (mx - mn)))})`;
  };
  cols.forEach((c, j) => {
    const x = pad.l + j * cw + cw / 2;
    s.appendChild(txt(x, pad.t - 9, c, { anchor: 'end', size: 10.5, fill: TEAL.ink2,
      weight: 560, transform: `rotate(-42 ${x} ${pad.t - 9})` }));
  });
  rows.forEach((r, i) => {
    s.appendChild(txt(pad.l - 10, pad.t + i * cell + cell / 2 + 4, r,
      { anchor: 'end', size: 11, fill: TEAL.ink, weight: 550 }));
    cols.forEach((c, j) => {
      const v = matrix[i][j];
      const g = el('g');
      const rc = el('rect', { x: pad.l + j * cw + 1.5, y: pad.t + i * cell + 1.5,
        width: cw - 3, height: cell - 3, rx: 4, fill: col(v) });
      g.appendChild(rc);
      const strong = v != null && (diverging ? Math.abs(v) / mx > .55 : (v - mn) / (mx - mn) > .55);
      g.appendChild(txt(pad.l + j * cw + cw / 2, pad.t + i * cell + cell / 2 + 4, fmt(v),
        { anchor: 'middle', size: 10.5, weight: 640, fill: strong ? '#fff' : TEAL.ink }));
      bindTip(g, `<b>${esc(r)}</b><br>${esc(c)}<br>${fmt(v)}${unit}`);
      s.appendChild(g);
    });
  });
  return s;
}

/* ───────────────────────────────────────────── line / curve */
export function lines(series, opts = {}) {
  const { w = 600, h = 300, pad = { t: 18, r: 20, b: 46, l: 52 },
          xLabel = '', yLabel = '', xTicks, yFmt = v => v.toFixed(2),
          xFmt = v => String(v), yMin, yMax, markers = [] } = opts;
  const s = svg(w, h);
  const all = series.flatMap(sr => sr.points);
  const x0 = Math.min(...all.map(p => p[0])), x1 = Math.max(...all.map(p => p[0]));
  const y0 = yMin ?? Math.min(...all.map(p => p[1])), y1 = yMax ?? Math.max(...all.map(p => p[1]));
  const py = (y1 - y0) * .1 || .05;
  const Y0 = y0 - py, Y1 = y1 + py;
  const X = v => pad.l + (v - x0) / ((x1 - x0) || 1) * (w - pad.l - pad.r);
  const Y = v => h - pad.b - (v - Y0) / ((Y1 - Y0) || 1) * (h - pad.t - pad.b);
  for (let i = 0; i <= 4; i++) {
    const yy = pad.t + (h - pad.t - pad.b) * i / 4;
    s.appendChild(el('line', { x1: pad.l, y1: yy, x2: w - pad.r, y2: yy, stroke: TEAL.line }));
    s.appendChild(txt(pad.l - 7, yy + 3.5, yFmt(Y1 - (Y1 - Y0) * i / 4),
      { anchor: 'end', size: 10, fill: TEAL.ink3 }));
  }
  (xTicks || all.map(p => p[0]).filter((v, i, a) => a.indexOf(v) === i)).forEach(t => {
    s.appendChild(txt(X(t), h - pad.b + 15, xFmt(t), { anchor: 'middle', size: 10, fill: TEAL.ink3 }));
  });
  if (xLabel) s.appendChild(txt((pad.l + w - pad.r) / 2, h - 6, xLabel,
    { anchor: 'middle', size: 10.5, fill: TEAL.ink3 }));
  if (yLabel) s.appendChild(txt(12, (pad.t + h - pad.b) / 2, yLabel, { anchor: 'middle', size: 10.5,
    fill: TEAL.ink3, transform: `rotate(-90 12 ${(pad.t + h - pad.b) / 2})` }));
  markers.forEach(m => {
    s.appendChild(el('line', { x1: X(m.x), y1: pad.t, x2: X(m.x), y2: h - pad.b,
      stroke: m.color || TEAL.err, 'stroke-dasharray': '4 4', 'stroke-width': 1.5 }));
    if (m.label) s.appendChild(txt(X(m.x) + 5, pad.t + 12, m.label,
      { size: 10, fill: m.color || TEAL.err, weight: 620 }));
  });
  series.forEach((sr, si) => {
    const c = sr.color || PALETTE[si % PALETTE.length];
    s.appendChild(el('path', { d: sr.points.map((p, i) => `${i ? 'L' : 'M'} ${X(p[0])} ${Y(p[1])}`).join(' '),
      fill: 'none', stroke: c, 'stroke-width': 2.2, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' }));
    sr.points.forEach(p => {
      const ci = el('circle', { cx: X(p[0]), cy: Y(p[1]), r: 4, fill: c, stroke: '#fff', 'stroke-width': 1.6 });
      bindTip(ci, `<b>${esc(sr.name || '')}</b><br>${xFmt(p[0])} → ${yFmt(p[1])}`);
      ci.addEventListener('mouseenter', () => ci.setAttribute('r', 6.5));
      ci.addEventListener('mouseleave', () => ci.setAttribute('r', 4));
      s.appendChild(ci);
    });
  });
  return s;
}

/* ───────────────────────────────────────────── stacked bars */
export function stacked(rows, keys, opts = {}) {
  const { w = 560, rowH = 40, pad = { t: 8, r: 14, b: 26, l: 150 }, colors = PALETTE,
          fmt = v => v.toFixed(0) + '%' } = opts;
  const h = pad.t + rows.length * rowH + pad.b;
  const s = svg(w, h);
  const bw = w - pad.l - pad.r;
  rows.forEach((r, i) => {
    const y = pad.t + i * rowH, bh = rowH - 15;
    s.appendChild(txt(pad.l - 11, y + bh / 2 + 4, r.label, { anchor: 'end', size: 11.5, weight: 550, fill: TEAL.ink }));
    const total = keys.reduce((a, k) => a + (r.values[k] || 0), 0) || 1;
    let x = pad.l;
    keys.forEach((k, j) => {
      const v = r.values[k] || 0;
      const seg = bw * v / total;
      if (seg <= 0) return;
      const g = el('g');
      const rc = el('rect', { x: x + .8, y, width: Math.max(0, seg - 1.6), height: bh, rx: 3,
        fill: colors[j % colors.length] });
      g.appendChild(rc);
      if (seg > 34) g.appendChild(txt(x + seg / 2, y + bh / 2 + 4, fmt(v),
        { anchor: 'middle', size: 10, weight: 650, fill: '#fff' }));
      bindTip(g, `<b>${esc(r.label)}</b><br>${esc(k)}: ${fmt(v)}`);
      s.appendChild(g);
      x += seg;
    });
  });
  return s;
}

export function legend(items) {
  const d = document.createElement('div');
  d.className = 'legend';
  d.innerHTML = items.map(i =>
    `<span class="li"><span class="sw" style="background:${i.color}"></span>${esc(i.label)}</span>`).join('');
  return d;
}

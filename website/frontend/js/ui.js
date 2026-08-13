/* HELIXA — shared UI helpers */

export const h = (tag, attrs = {}, ...kids) => {
  const e = document.createElement(tag);
  for (const k in attrs) {
    const v = attrs[k];
    if (v == null || v === false) continue;
    if (k === 'class') e.className = v;
    else if (k === 'html') e.innerHTML = v;
    else if (k.startsWith('on') && typeof v === 'function') e.addEventListener(k.slice(2).toLowerCase(), v);
    else if (k === 'style' && typeof v === 'object') Object.assign(e.style, v);
    else e.setAttribute(k, v);
  }
  kids.flat().forEach(c => { if (c == null || c === false) return;
    e.appendChild(typeof c === 'string' || typeof c === 'number' ? document.createTextNode(String(c)) : c); });
  return e;
};

export const esc = s => String(s ?? '').replace(/[&<>"']/g,
  c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

export function card(title, desc, body, opts = {}) {
  const c = h('div', { class: 'card' + (opts.hover ? ' hov' : '') + (opts.dark ? ' dark' : '') +
    (opts.class ? ' ' + opts.class : '') });
  if (title) {
    const hd = h('div', { class: 'card-h' },
      h('div', {}, h('div', { class: 'card-t' }, title), desc ? h('div', { class: 'card-d' }, desc) : null),
      opts.action || null);
    c.appendChild(hd);
  }
  if (body) c.appendChild(body);
  return c;
}

export function stat(value, label, sub, opts = {}) {
  return h('div', { class: 'card' + (opts.dark ? ' dark' : '') + (opts.hover ? ' hov' : ''),
    style: opts.style || {} },
    h('div', { class: 'stat-v' }, value),
    h('div', { class: 'stat-l' }, label),
    sub ? h('div', { class: 'stat-sub' }, sub) : null);
}

export function section(eyebrow, title, sub) {
  return h('div', { style: { marginBottom: '26px' } },
    eyebrow ? h('div', { class: 'eyebrow' }, eyebrow) : null,
    h('h2', { class: 'h-sec' }, title),
    sub ? h('p', { class: 'sub' }, sub) : null);
}

export function banner(kind, html) {
  return h('div', { class: `banner ${kind}` }, h('div', { html }));
}

export function badge(kind, text) {
  return h('span', { class: `badge b-${kind}` }, text);
}

export function kv(k, v) {
  return h('div', { class: 'kv' }, h('span', { class: 'k' }, k),
    h('span', { class: 'v' }, typeof v === 'string' || typeof v === 'number' ? String(v) : v));
}

export function loader(msg = 'Loading real project data…') {
  return h('div', { class: 'wrap section', style: { textAlign: 'center', padding: '90px 20px' } },
    h('div', { class: 'spin dk', style: { margin: '0 auto 16px', width: '30px', height: '30px', borderWidth: '3px' } }),
    h('p', { class: 'sub', style: { margin: '0 auto' } }, msg));
}

export function errorBox(e) {
  return h('div', { class: 'wrap section' },
    banner('err', `<b>Could not load data.</b><br>${esc(e.message || e)}`));
}

export function lightbox(src, caption) {
  const lb = document.getElementById('lightbox');
  document.getElementById('lb-img').src = src;
  document.getElementById('lb-img').alt = caption || '';
  document.getElementById('lb-cap').textContent = caption || '';
  lb.classList.add('on');
}

export function chart(node) {
  return h('div', { style: { marginTop: '6px' } }, node);
}

export function initials(name) {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map(w => w[0]).join('').toUpperCase();
}

/* skeleton block */
export const skel = (hgt = 120) => h('div', { class: 'skel', style: { height: hgt + 'px' } });

/* small helper: build a chip row */
export function chips(items, activeSet, onToggle) {
  return h('div', { style: { display: 'flex', gap: '8px', flexWrap: 'wrap' } },
    items.map(it => h('button', {
      class: 'chip' + (activeSet.has(it.value) ? ' on' : ''),
      type: 'button',
      'aria-pressed': activeSet.has(it.value) ? 'true' : 'false',
      onclick: () => onToggle(it.value),
    }, it.color ? h('span', { class: 'dot', style: { background: it.color } }) : null, it.label)));
}

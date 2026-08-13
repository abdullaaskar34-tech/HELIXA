/* HELIXA — the project's original scientific figures */
import { loadJSON } from '../api.js';
import { h, card, section, badge, esc, lightbox } from '../ui.js';

export default async function visualizations() {
  const plots = await loadJSON('plots');
  const groups = [...new Set(plots.map(p => p.group))];
  let active = 'All';

  const root = h('div', { class: 'wrap section' });
  root.appendChild(section('Figures', 'Scientific Visualizations',
    `${plots.length} figures produced directly by the analysis scripts. These are the original ` +
    `matplotlib renders — not redrawn or decorated — so what you see here is exactly what the ` +
    `pipeline generated.`));

  const grid = h('div', { class: 'grid g3' });
  const bar = h('div', { class: 'tabs', style: { marginBottom: '22px' } },
    ['All', ...groups].map(g => h('button', {
      class: 'tab' + (g === active ? ' on' : ''), 'data-g': g, type: 'button',
      onclick: () => { active = g;
        bar.querySelectorAll('.tab').forEach(b => b.classList.toggle('on', b.dataset.g === g));
        draw(); } },
      g === 'All' ? `All (${plots.length})` : `${g} (${plots.filter(p => p.group === g).length})`)));
  root.appendChild(bar);
  root.appendChild(grid);

  function draw() {
    const list = active === 'All' ? plots : plots.filter(p => p.group === active);
    grid.replaceChildren(...list.map(p => h('div', {
      class: 'plot-card', tabindex: '0', role: 'button',
      'aria-label': `Enlarge: ${p.title}`,
      onclick: () => lightbox(`./assets/plots/${p.file}`, p.caption || p.title),
      onkeydown: e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault();
        lightbox(`./assets/plots/${p.file}`, p.caption || p.title); } },
    },
      h('img', { src: `./assets/plots/${p.file}`, alt: p.caption || p.title, loading: 'lazy' }),
      h('div', { class: 'plot-meta' },
        h('div', { style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          gap: '9px', marginBottom: '6px' } },
          h('div', { class: 'card-t', style: { fontSize: '13px' } }, p.title),
          badge('mut', p.group)),
        h('div', { class: 'card-d' }, p.caption),
        h('div', { class: 'mono', style: { fontSize: '10.5px', color: 'var(--ink-3)', marginTop: '8px' } },
          p.source + '/' + p.file)))));
  }
  draw();
  return root;
}

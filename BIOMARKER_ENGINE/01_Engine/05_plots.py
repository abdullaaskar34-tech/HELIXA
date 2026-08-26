# -*- coding: utf-8 -*-
"""
 Figures for the biomarker engine.
 Palette: the project's colour-vision-deficiency-validated categorical set.
 Run:  python3 05_plots.py
"""
import os, json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
SRC = os.environ.get('BIO_SRC', '/mnt/user-data/uploads/Desktop/TEKNOFEST_ONCOLOGY/new_start')
T = os.path.join(ROOT, '05_Tables')
OUT = os.path.join(ROOT, '04_Plots')
os.makedirs(OUT, exist_ok=True)

ACCENT = ['#0EAE8F', '#E8833A', '#2E7BC4', '#C79A2C', '#C2649B', '#5B8C2A']
NAMES = ['MTC', 'PN', 'CL', 'MES', 'INT', 'OLIGO']
CMAP = dict(zip(NAMES, ACCENT))
INK, INK2, LINE = '#0C2E2B', '#4A6663', '#DCE6E4'
RED = '#B04A3C'
plt.rcParams.update({'figure.dpi': 130, 'savefig.dpi': 170, 'font.size': 9.5,
                     'axes.edgecolor': LINE, 'axes.labelcolor': INK, 'text.color': INK,
                     'xtick.color': INK2, 'ytick.color': INK2, 'axes.titlesize': 11.5,
                     'axes.titleweight': 'bold', 'figure.facecolor': 'white',
                     'axes.spines.top': False, 'axes.spines.right': False})

fin = pd.read_csv(os.path.join(T, 'final_targets.csv'))
dep = pd.read_csv(os.path.join(T, 'dependency_side_depmap.csv'))
cand = pd.read_csv(os.path.join(T, 'candidates_all.csv'))
n = 0


def save(fig, name, title):
    global n
    n += 1
    fig.savefig(os.path.join(OUT, f'{n:02d}_{name}.png'), bbox_inches='tight')
    plt.close(fig)
    print(f'  {n:02d}  {title}')


def cap(ax, text, y=-.22):
    ax.text(0, y, text, transform=ax.transAxes, fontsize=8.5, color=INK2, va='top')


print('drawing figures…')

# ── 1 · the funnel ─────────────────────────────────────────────────────────
de = pd.read_csv(os.path.join(T, 'patient_side_differential_expression.csv.gz'))
steps = [('All measured genes', 25738),
         ('Mark a subtype\n(FDR, effect size, specificity)',
          int(de.groupby('gene').apply(lambda g: 0).shape[0]) if False else
          int(((de.fdr < .05) & (de.cohens_d > .5) & (de.specificity_margin > .15))
              .groupby(de.gene).any().sum())),
         ('...and glioblastoma\ndies without them', int(cand.gene.nunique())),
         ('...and survive the\nliterature check', int(fin[~fin.tier.str.startswith("EXCLUDED")].gene.nunique())),
         ('...and a drug exists',
          int(fin[(fin.tier.str.startswith('TIER 1'))].gene.nunique()))]
fig, ax = plt.subplots(figsize=(7.6, 4.6))
xs = np.arange(len(steps))
vals = [s[1] for s in steps]
b = ax.bar(xs, vals, color=[ACCENT[2], ACCENT[2], ACCENT[0], ACCENT[0], ACCENT[3]], width=.62)
ax.set_yscale('log')
for r, v in zip(b, vals):
    ax.text(r.get_x() + r.get_width() / 2, v * 1.18, f'{v:,}', ha='center',
            fontsize=10.5, fontweight='bold')
ax.set_xticks(xs)
ax.set_xticklabels([s[0] for s in steps], fontsize=8.5)
ax.set_ylabel('genes (log scale)')
ax.set_title('From 25,738 genes to a handful worth arguing about', loc='left')
cap(ax, 'Each bar is a gate, not a ranking. The steep drop between bars two and three is the\n'
        'therapeutic-window filter — the step the earlier attempt was missing.', -.34)
save(fig, 'funnel', 'the funnel')

# ── 2 · the pan-essential trap ─────────────────────────────────────────────
prev = pd.read_csv(os.path.join(T, 'previous_attempt_reexamined.csv'))
fig, ax = plt.subplots(figsize=(7.4, 4.4))
p = prev.sort_values('dep_mean_GBM')
y = np.arange(len(p))
ax.barh(y - .19, p.dep_mean_GBM, height=.36, color=ACCENT[0], label='glioblastoma needs it')
ax.barh(y + .19, p.dep_mean_nonCNS, height=.36, color=RED, label='normal tissue needs it too')
ax.set_yticks(y)
ax.set_yticklabels(p.gene, fontsize=9.5, fontfamily='monospace')
ax.set_xlim(0, 1.1)
ax.set_xlabel('probability the cell dies without this gene')
ax.legend(frameon=False, fontsize=8.5, loc='lower right')
ax.set_title('Why the first attempt found nothing usable', loc='left')
cap(ax, 'These are the ten genes it returned. The two bars are the same height for every one of\n'
        'them: the tumour needs them exactly as much as the rest of the body does. There is no\n'
        'window to aim at. Six are formally pan-essential.', -.28)
save(fig, 'pan_essential_trap', 'the pan-essential trap')

# ── 3 · the whole dependency landscape ─────────────────────────────────────
d = dep[dep.dep_mean_GBM.notna()]
fig, ax = plt.subplots(figsize=(6.8, 6.4))
ax.scatter(d.dep_mean_nonCNS, d.dep_mean_GBM, s=3, c='#C9D9D6', lw=0, alpha=.5)
sel = d[d.dependency_tier.str.startswith('A')]
ax.scatter(sel.dep_mean_nonCNS, sel.dep_mean_GBM, s=9, c=ACCENT[0], lw=0, alpha=.7)
pan = d[d.pan_essential]
ax.scatter(pan.dep_mean_nonCNS, pan.dep_mean_GBM, s=6, c=RED, lw=0, alpha=.55)
ax.plot([0, 1], [0, 1], ls='--', lw=1.1, color=INK2)
hi = fin[fin.tier.str.startswith('TIER 1')].drop_duplicates('gene')
for r in hi.itertuples():
    ax.annotate(r.gene, (r.dep_mean_nonCNS, r.dep_mean_GBM), fontsize=8.5,
                fontweight='bold', textcoords='offset points', xytext=(6, 3))
ax.set_xlabel('needed by cells OUTSIDE the brain')
ax.set_ylabel('needed by glioblastoma cells')
ax.set_title('Every gene in the genome, on two axes', loc='left')
ax.legend(handles=[Patch(color='#C9D9D6', label='all 17,931 genes'),
                   Patch(color=ACCENT[0], label='selective + variable (tier A)'),
                   Patch(color=RED, label='pan-essential — unusable')],
          frameon=False, fontsize=8.5, loc='upper left')
cap(ax, 'The diagonal is the line of no therapeutic window. Only genes ABOVE it are worth\n'
        'anything: the tumour needs them more than the body does. The red cloud sits in the\n'
        'top-right corner — essential to everything, target for nothing.', -.15)
save(fig, 'dependency_landscape', 'dependency landscape')

# ── 4 · candidates per subtype ─────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(7.2, 4.2))
order = NAMES
t1 = [len(fin[(fin.subtype == s) & fin.tier.str.startswith('TIER 1')]) for s in order]
t2 = [len(fin[(fin.subtype == s) & fin.tier.str.startswith('TIER 2')]) for s in order]
t3 = [len(fin[(fin.subtype == s) & fin.tier.str.startswith('TIER 3')]) for s in order]
ex = [len(fin[(fin.subtype == s) & fin.tier.str.startswith('EXCLUDED')]) for s in order]
xs = np.arange(6)
ax.bar(xs, t1, color=ACCENT[0], label='tier 1 · actionable')
ax.bar(xs, t2, bottom=t1, color=ACCENT[2], label='tier 2 · credible')
ax.bar(xs, t3, bottom=np.array(t1) + t2, color=ACCENT[3], label='tier 3 · hypothesis')
ax.bar(xs, ex, bottom=np.array(t1) + np.array(t2) + t3, color=RED,
       label='excluded · wrong direction')
ax.set_xticks(xs)
ax.set_xticklabels(order)
ax.set_ylabel('genes among the top 10 checked')
ax.legend(frameon=False, fontsize=8.5, ncol=2)
ax.set_title('What each subtype came back with', loc='left')
cap(ax, 'Ten candidates per subtype were checked against the literature. Every subtype produced\n'
        'something — including MTC, which the earlier attempt left completely empty.')
save(fig, 'per_subtype_tiers', 'candidates per subtype')

# ── 5 · the two-axis plot, per subtype ─────────────────────────────────────
fig, axes = plt.subplots(2, 3, figsize=(13.5, 8))
for k, ax in zip(range(6), axes.ravel()):
    c = fin[fin.cluster == k]
    ax.axhline(0.5, ls=':', lw=1, color=INK2)
    ax.axvline(0.15, ls=':', lw=1, color=INK2)
    for r in c.itertuples():
        col = (RED if r.tier.startswith('EXCLUDED') else CMAP[NAMES[k]])
        ax.scatter(r.specificity_margin, r.dep_mean_GBM, s=90, color=col,
                   alpha=.85, lw=0)
        ax.annotate(r.gene, (r.specificity_margin, r.dep_mean_GBM), fontsize=8,
                    textcoords='offset points', xytext=(7, -3))
    ax.set_title(f'{NAMES[k]}', loc='left', color=CMAP[NAMES[k]])
    ax.set_xlabel('how specific to this subtype (z)')
    ax.set_ylabel('how much the tumour needs it')
    ax.set_ylim(0, 1.02)
fig.suptitle('Both tests at once, for each subtype', x=.09, ha='left',
             fontsize=13, fontweight='bold')
fig.text(.09, .02, 'Top-right is where a real target lives: specific to the subtype AND '
         'required for survival. Red = excluded because the gene is a tumour suppressor.',
         fontsize=9, color=INK2)
fig.tight_layout(rect=[0, .045, 1, .96])
save(fig, 'two_axis_per_subtype', 'both tests per subtype')

# ── 6 · expression heatmap of the top targets ──────────────────────────────
Z = np.load(os.path.join(T, 'z_matrix.npy'))
gi = pd.read_csv(os.path.join(T, 'gene_index.csv'))
pat = pd.read_csv(os.path.join(T, 'patients.csv'))
gpos = {g: i for i, g in enumerate(gi.gene)}
top = (fin[~fin.tier.str.startswith('EXCLUDED')]
       .sort_values(['cluster', 'final_rank']).groupby('cluster').head(5))
rows = [gpos[g] for g in top.gene if g in gpos]
labs = [g for g in top.gene if g in gpos]
ordp = np.argsort(pat.cluster.values, kind='stable')
M = Z[np.ix_(rows, ordp)]
M = np.clip(M, -2.5, 2.5)
fig, ax = plt.subplots(figsize=(12, 8))
im = ax.imshow(M, aspect='auto', cmap='RdBu_r', vmin=-2.5, vmax=2.5,
               interpolation='nearest')
ax.set_yticks(range(len(labs)))
ax.set_yticklabels(labs, fontsize=8.5, fontfamily='monospace')
bounds = np.cumsum(pat.cluster.value_counts().sort_index().values)
for b_ in bounds[:-1]:
    ax.axvline(b_, color='white', lw=1.6)
prev_ = 0
for k, b_ in enumerate(bounds):
    ax.text((prev_ + b_) / 2, -1.6, NAMES[k], ha='center', fontsize=10,
            fontweight='bold', color=CMAP[NAMES[k]])
    prev_ = b_
# separate the gene blocks too
gb = np.cumsum(top.groupby('cluster').size().values)
for g_ in gb[:-1]:
    ax.axhline(g_ - .5, color='white', lw=1.6)
ax.set_xticks([])
ax.set_xlabel('328 patients, grouped by subtype')
fig.colorbar(im, ax=ax, shrink=.55, label='expression (z, batch-corrected)')
ax.set_title('The top five targets of each subtype, across every patient', loc='left', pad=26)
fig.text(.125, .02, 'Each block of rows is one subtype\'s targets. The diagonal pattern is the '
         'point: a target is red\nin its own subtype and blue elsewhere. Where a block is not '
         'clean, the panel is weaker — say so.',
         fontsize=9, color=INK2)
fig.tight_layout(rect=[0, .05, 1, 1])
save(fig, 'target_expression_heatmap', 'expression heatmap')

# ── 7 · per-line dependency for the headline targets ───────────────────────
cns = np.load(os.path.join(SRC, '_dep_cns.npy'))
cix = json.load(open(os.path.join(SRC, '_dep_cns_index.json')))
gpos2 = {}
for i, g in enumerate(cix['genes']):
    gpos2.setdefault(g, i)
is_gbm = np.array(cix['is_gbm'], dtype=bool)
show = [g for g in ['WWTR1', 'PTK2', 'ITGB5', 'CDK6', 'FGFR1', 'RHOA', 'FOSL1',
                    'KIF18B', 'VRK1', 'RPP25L', 'FERMT2', 'ARPC2'] if g in gpos2]
fig, ax = plt.subplots(figsize=(9.5, 5))
for i, g in enumerate(show):
    v = cns[is_gbm, gpos2[g]]
    v = v[~np.isnan(v)]
    ax.scatter(np.random.default_rng(i).normal(i, .085, len(v)), v, s=22,
               color=ACCENT[i % 6], alpha=.6, lw=0)
    ax.plot([i - .28, i + .28], [np.median(v)] * 2, color=INK, lw=2)
ax.axhline(.5, ls='--', lw=1.2, color=RED)
ax.text(len(show) - .4, .53, 'DepMap "likely dependent"', ha='right', fontsize=8.5, color=RED)
ax.set_xticks(range(len(show)))
ax.set_xticklabels(show, rotation=45, ha='right', fontsize=9, fontfamily='monospace')
ax.set_ylabel('dependency score')
ax.set_ylim(-.03, 1.03)
ax.set_title('Each dot is one glioblastoma cell line', loc='left')
cap(ax, 'The spread is the interesting part. A gene every line needs equally cannot be a subtype\n'
        'marker; a gene some lines cannot live without while others shrug is exactly the shape a\n'
        'subtype-specific vulnerability has.', -.42)
save(fig, 'per_line_dependency', 'per-line dependency')

# ── 8 · evidence verdicts ──────────────────────────────────────────────────
ev = pd.DataFrame(json.load(open(os.path.join(ROOT, '03_Evidence',
                                              'literature_evidence.json'))))
fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.2))
o = ['STRONG', 'MODERATE', 'WEAK', 'NOVEL']
v = [int((ev.verdict == x).sum()) for x in o]
b = axes[0].bar(o, v, color=[ACCENT[0], ACCENT[2], ACCENT[1], ACCENT[4]], width=.6)
for r, x in zip(b, v):
    axes[0].text(r.get_x() + r.get_width() / 2, x + .5, x, ha='center',
                 fontsize=11, fontweight='bold')
axes[0].set_ylabel('genes')
axes[0].set_title('What the literature actually says', loc='left')
ds = fin.drop_duplicates('gene').drug_status.value_counts()
axes[1].barh(range(len(ds)), ds.values, color=ACCENT[3])
axes[1].set_yticks(range(len(ds)))
axes[1].set_yticklabels(ds.index, fontsize=9)
axes[1].invert_yaxis()
axes[1].set_xlabel('genes')
axes[1].set_title('Is there a drug against it?', loc='left')
fig.text(.09, -.02, 'Sixty genes were checked one at a time against PubMed, Human Protein Atlas, '
         'Open Targets, DrugBank and ClinicalTrials.gov.\nTwelve came back with strong published '
         'glioblastoma evidence. Sixteen came back with almost nothing — reported as such.',
         fontsize=9, color=INK2)
fig.tight_layout()
save(fig, 'evidence_summary', 'evidence summary')

# ── 9 · volcano per subtype ────────────────────────────────────────────────
fig, axes = plt.subplots(2, 3, figsize=(13.5, 7.6))
for k, ax in zip(range(6), axes.ravel()):
    d_ = de[de.cluster == k]
    ax.scatter(d_.cohens_d, -np.log10(d_.p_value.clip(1e-300)), s=2,
               c='#D8E4E2', lw=0)
    sig = d_[(d_.fdr < .05) & (d_.cohens_d > .5) & (d_.specificity_margin > .15)]
    ax.scatter(sig.cohens_d, -np.log10(sig.p_value.clip(1e-300)), s=4,
               c=CMAP[NAMES[k]], lw=0, alpha=.6)
    hits = fin[(fin.cluster == k)].head(6)
    for r in hits.itertuples():
        row = d_[d_.gene == r.gene]
        if len(row):
            ax.scatter(row.cohens_d, -np.log10(row.p_value.clip(1e-300)), s=55,
                       facecolor='none', edgecolor=INK, lw=1.3)
            ax.annotate(r.gene, (row.cohens_d.iloc[0],
                                 -np.log10(max(row.p_value.iloc[0], 1e-300))),
                        fontsize=8, textcoords='offset points', xytext=(6, 2))
    ax.set_title(NAMES[k], loc='left', color=CMAP[NAMES[k]])
    ax.set_xlabel("effect size (Cohen's d)")
    ax.set_ylabel('-log10 p')
fig.suptitle('Which genes mark each subtype, and where the targets sit', x=.09,
             ha='left', fontsize=13, fontweight='bold')
fig.text(.09, .015, 'Grey = all 25,738 genes. Colour = passes the identity gate. '
         'Circled = made the final target panel.', fontsize=9, color=INK2)
fig.tight_layout(rect=[0, .04, 1, .96])
save(fig, 'volcano_per_subtype', 'volcano per subtype')

# ── 10 · the top targets, ranked ───────────────────────────────────────────
best = fin[~fin.tier.str.startswith('EXCLUDED')].sort_values('final_score',
                                                             ascending=False).head(22)
fig, ax = plt.subplots(figsize=(9, 7))
y = np.arange(len(best))[::-1]
ax.barh(y, best.final_score, color=[CMAP[s] for s in best.subtype], height=.66)
for yy, r in zip(y, best.itertuples()):
    ax.text(r.final_score + .006, yy, f'{r.subtype}', va='center', fontsize=8.5,
            color=CMAP[r.subtype], fontweight='bold')
ax.set_yticks(y)
ax.set_yticklabels(best.gene, fontsize=9.5, fontfamily='monospace')
ax.set_xlabel('final score  (data × literature × druggability)')
ax.set_title('The 22 strongest candidates across all six subtypes', loc='left')
cap(ax, 'The score is a geometric blend, so a gene has to do well on every axis to rise. A perfect\n'
        'marker with no dependency, or a perfect dependency shared by every subtype, both sink.', -.13)
save(fig, 'top_targets_ranked', 'top targets ranked')

print(f'\n{n} figures -> {OUT}')

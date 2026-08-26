# -*- coding: utf-8 -*-
"""
================================================================================
 BIOMARKER ENGINE — STEP 2 of 3 · THE SURVIVAL SIDE
================================================================================

Question answered here, on data that has nothing to do with our patients:

    Which genes does a glioblastoma cell DIE without,
    while a cell from another tissue survives?

Source
    DepMap CRISPR gene dependency (Chronos), 1,208 human cancer cell lines,
    18,531 genes. Every gene has been knocked out in every line and the score
    is the probability that the line depends on it. DepMap's own convention is
    that a score above 0.5 means "likely dependent".

    Of those 1,208 lines, 53 are glioblastoma or gliosarcoma, 90 are CNS/brain,
    and 1,118 are outside the brain entirely. That last group is the control.

WHY THIS STEP EXISTS AT ALL — the mistake it is fixing
    The earlier attempt took each subtype's marker genes and asked DepMap "is
    this gene essential?". Ten genes out of 265 passed. They were POLR2L,
    POLR2F, RPLP1, RPL28, PPA1, PCBP2 — RNA polymerase subunits and ribosomal
    proteins. Those are essential in EVERY human cell: brain, kidney, heart.
    A drug against them kills the patient before the tumour. They are not
    targets; they are the price of being alive.

    1,002 of the 18,531 genes are dependencies in more than 90% of ALL cell
    lines. Those 1,002 are the trap, and this step's job is to throw them out.

Three quantities are computed for every gene
    1  DEPENDENCY IN GLIOBLASTOMA  — mean score across the 53 GBM lines, and
       the fraction of them that cross DepMap's 0.5 line
    2  THERAPEUTIC WINDOW          — the same, measured across the 1,118
       non-brain lines. A real target is high in (1) and low in (2).
    3  HETEROGENEITY               — the spread of the score across the GBM
       lines. A gene that every GBM line needs equally cannot be a SUBTYPE
       marker. A gene some GBM lines cannot live without while others shrug is
       exactly the shape a subtype-specific vulnerability has.

Run:  python3 02_dependency_side.py
================================================================================
"""
import os, json
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
SRC = os.environ.get('BIO_SRC', '/mnt/user-data/uploads/Desktop/TEKNOFEST_ONCOLOGY/new_start')
OUT = os.path.join(ROOT, '05_Tables')
os.makedirs(OUT, exist_ok=True)

print('=' * 78)
print(' BIOMARKER ENGINE · STEP 2 — what a glioblastoma cell cannot live without')
print('=' * 78)

s = pd.read_csv(os.path.join(SRC, '_dep_stats.csv'))
s = s[s.dep_mean_GBM.notna()].copy()
n_gbm, n_other = int(s.n_GBM_lines.iloc[0]), int(s.n_other_lines.iloc[0])
print(f'\nDepMap            : {len(s):,} genes')
print(f'glioblastoma lines: {n_gbm}')
print(f'control lines     : {n_other} (everything outside the brain)')

# heterogeneity across the CNS lines, computed from the per-line matrix
cns = np.load(os.path.join(SRC, '_dep_cns.npy'))
cix = json.load(open(os.path.join(SRC, '_dep_cns_index.json')))
gbm_mask = np.array(cix['is_gbm'], dtype=bool)
gsub = cns[gbm_mask]
het = pd.DataFrame(dict(gene_col=cix['genes'],
                        gbm_line_sd=np.nanstd(gsub, 0),
                        gbm_line_range=np.nanmax(gsub, 0) - np.nanmin(gsub, 0),
                        gbm_lines_dependent=np.nansum(gsub > 0.5, 0)))
# the stats table was filtered to genes with a GBM score, so merge by name
# rather than by position
het = het.rename(columns={'gene_col': 'gene'}).groupby('gene', as_index=False).first()
s = s.merge(het[['gene', 'gbm_line_sd', 'gbm_line_range']], on='gene', how='left')
s['gbm_line_sd'] = s.gbm_line_sd.fillna(0.0)
s['gbm_line_range'] = s.gbm_line_range.fillna(0.0)

# ── the three verdicts ─────────────────────────────────────────────────────
# A gene is only judged on the lines where it was actually measured. 744 of the
# 18,531 genes were screened in fewer than half the panel; counting an unmeasured
# line as "not dependent" would make a pan-essential gene look selective. This is
# a bug that DID bite: NPM1 read as 27% dependent instead of its true 85%, and
# reached the candidate list before it was caught.
ENOUGH = s.n_lines_measured >= 100
s['too_few_lines'] = ~ENOUGH

PAN = (s.frac_all_lines_dependent > 0.90) | (s.dep_mean_nonCNS > 0.70)   # no window
s['pan_essential'] = PAN
s['tumour_dependency'] = s.frac_GBM_lines_dependent
s['therapeutic_window'] = s.dep_mean_GBM - s.dep_mean_nonCNS

DEP = ((s.frac_GBM_lines_dependent >= 0.30) | (s.dep_mean_GBM >= 0.40)) & ENOUGH
WIN = (~PAN) & (s.frac_all_lines_dependent < 0.60) & (s.dep_mean_nonCNS < 0.60)
HET = s.gbm_line_sd >= 0.15

s['passes_dependency'] = DEP
s['passes_window'] = WIN
s['passes_heterogeneity'] = HET
s['dependency_tier'] = np.where(PAN, 'PAN-ESSENTIAL (no therapeutic window)',
                        np.where(DEP & WIN & HET, 'A · selective + heterogeneous',
                        np.where(DEP & WIN, 'B · selective, uniform across GBM',
                        np.where(DEP, 'C · dependency without a clear window',
                                 'D · not a dependency'))))

print(f'\ngenes screened in <100 lines, set aside: {int((~ENOUGH).sum()):5d}')
print(f'pan-essential / no window, discarded  : {int(PAN.sum()):5d}')
for t, n in s.dependency_tier.value_counts().items():
    print(f'  {t:<40s} {n:6d}')

s.sort_values('frac_GBM_lines_dependent', ascending=False).to_csv(
    os.path.join(OUT, 'dependency_side_depmap.csv'), index=False)

top = s[s.dependency_tier.str.startswith('A')].sort_values('therapeutic_window', ascending=False)
print(f'\nTier A — selective AND variable across GBM lines: {len(top)} genes')
print(top[['gene', 'dep_mean_GBM', 'dep_mean_nonCNS', 'frac_GBM_lines_dependent',
           'frac_all_lines_dependent', 'gbm_line_sd']].head(20).to_string(index=False))

# the pan-essential trap, named explicitly for the report
trap = ['POLR2L', 'POLR2F', 'RPLP1', 'RPL28', 'PPA1', 'PCBP2', 'NSF', 'MOB4',
        'IFITM3', 'C19orf53']
tt = s[s.gene.isin(trap)][['gene', 'dep_mean_GBM', 'dep_mean_nonCNS',
                           'frac_all_lines_dependent', 'pan_essential']]
print('\nthe ten genes the earlier attempt returned, re-examined:')
print(tt.to_string(index=False))
tt.to_csv(os.path.join(OUT, 'previous_attempt_reexamined.csv'), index=False)
print(f'\nwritten -> {OUT}/dependency_side_depmap.csv')

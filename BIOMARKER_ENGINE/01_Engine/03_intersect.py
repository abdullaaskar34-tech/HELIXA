# -*- coding: utf-8 -*-
"""
================================================================================
 BIOMARKER ENGINE — STEP 3 of 3 · THE INTERSECTION
================================================================================

Step 1 asked the patients:  which genes MARK this subtype?
Step 2 asked DepMap:        which genes does a glioblastoma DIE without,
                            while other tissues survive?

Neither answer is a target on its own. A marker you can't drug is a label. A
dependency shared with every subtype is not personalised medicine. What this
step keeps is the overlap:

        a gene that IDENTIFIES the subtype in a patient
        AND that a glioblastoma cell CANNOT LIVE WITHOUT
        AND that a normal cell CAN live without

Three gates, applied in this order.

  GATE 1 · IDENTITY  (from our 328 patients)
      FDR < 0.05, Cohen's d > 0.5, and a specificity margin above 0.15 z.
      The margin is the strict one: the gene's mean in this subtype must beat
      its mean in the BEST of the other five, not merely their average.

  GATE 2 · TUMOUR DEPENDENCY  (from DepMap, independent data)
      dependency tier A or B: a real dependency in glioblastoma lines that is
      NOT a dependency of every cell in the body.

  GATE 3 · THERAPEUTIC WINDOW
      already inside tier A/B, and reported explicitly per gene so nobody has
      to take it on trust: mean dependency in glioblastoma minus mean
      dependency outside the brain.

RANKING
    Candidates are scored on both axes and ranked by the product of two
    normalised terms, so a gene has to do well at BOTH to rise. A spectacular
    marker with a feeble dependency, or a beautiful dependency that half the
    subtypes share, both sink.

        identity_score   = specificity_margin (z) capped at 1.5, scaled 0-1
        survival_score   = mean GBM dependency x therapeutic window, scaled 0-1
        combined         = sqrt(identity_score x survival_score)

    The geometric mean, not the arithmetic one, precisely because it punishes
    imbalance instead of averaging it away.

Run:  python3 03_intersect.py
================================================================================
"""
import os, json
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
T = os.path.join(ROOT, '05_Tables')

SUB = {0: 'MTC', 1: 'PN', 2: 'CL', 3: 'MES', 4: 'INT', 5: 'OLIGO'}
FDR_MAX, D_MIN, MARGIN_MIN = 0.05, 0.5, 0.15

print('=' * 78)
print(' BIOMARKER ENGINE · STEP 3 — genes that pass BOTH tests')
print('=' * 78)

de = pd.read_csv(os.path.join(T, 'patient_side_differential_expression.csv.gz'))
dep = pd.read_csv(os.path.join(T, 'dependency_side_depmap.csv'))
dep = dep.groupby('gene', as_index=False).first()

m = de.merge(dep[['gene', 'dep_mean_GBM', 'dep_mean_nonCNS', 'dep_mean_all_lines',
                  'frac_GBM_lines_dependent', 'frac_all_lines_dependent',
                  'gbm_line_sd', 'therapeutic_window', 'dependency_tier',
                  'pan_essential']], on='gene', how='left')
print(f'\ngenes with a DepMap dependency measurement: '
      f'{m.dep_mean_GBM.notna().sum() // 6:,} of {len(de)//6:,}')

g1 = (m.fdr < FDR_MAX) & (m.cohens_d > D_MIN) & (m.specificity_margin > MARGIN_MIN)
g2 = m.dependency_tier.isin(['A · selective + heterogeneous',
                             'B · selective, uniform across GBM'])
m['passes_identity'] = g1
m['passes_dependency'] = g2.fillna(False)
m['is_candidate'] = g1 & g2.fillna(False)

print(f'\ngate 1 · identity            : {int(g1.sum()):6,} (gene, subtype) pairs')
print(f'gate 2 · tumour dependency   : {int(g2.fillna(False).sum()):6,}')
print(f'both                         : {int(m.is_candidate.sum()):6,}')

# ── scoring ────────────────────────────────────────────────────────────────
ident = np.clip(m.specificity_margin, 0, 1.5) / 1.5
surv = m.dep_mean_GBM.fillna(0) * np.clip(m.therapeutic_window.fillna(0), 0, None)
surv = surv / max(surv[m.is_candidate].max(), 1e-9)
m['identity_score'] = ident
m['survival_score'] = np.clip(surv, 0, 1)
m['combined_score'] = np.sqrt(np.clip(ident, 0, 1) * np.clip(surv, 0, 1))

cand = m[m.is_candidate].copy().sort_values(['cluster', 'combined_score'],
                                            ascending=[True, False])
cand['rank_in_class'] = cand.groupby('cluster').cumcount() + 1

print('\ncandidates per subtype:')
for k in range(6):
    c = cand[cand.cluster == k]
    print(f'  {SUB[k]:<6s} {len(c):4d}')
    if len(c):
        top = c.head(6)
        for r in top.itertuples():
            print(f'        {r.gene:<10s} margin {r.specificity_margin:5.2f}z  '
                  f'GBM dep {r.dep_mean_GBM:.2f}  window {r.therapeutic_window:+.2f}  '
                  f'score {r.combined_score:.3f}')

cols = ['cluster', 'subtype', 'rank_in_class', 'gene', 'gene_id', 'gene_type',
        'combined_score', 'identity_score', 'survival_score',
        'mean_z_in_class', 'best_other_class_mean_z', 'specificity_margin',
        'cohens_d', 'p_value', 'fdr',
        'dep_mean_GBM', 'dep_mean_nonCNS', 'therapeutic_window',
        'frac_GBM_lines_dependent', 'frac_all_lines_dependent',
        'gbm_line_sd', 'dependency_tier', 'pan_essential']
cand[cols].to_csv(os.path.join(T, 'candidates_all.csv'), index=False)
m.to_csv(os.path.join(T, 'merged_full.csv.gz'), index=False, compression='gzip')

# how many would have survived WITHOUT the therapeutic-window gate?
naive = (g1 & (m.frac_all_lines_dependent > 0.5)).sum()
print(f'\nfor comparison — genes that pass identity and are simply "essential",')
print(f'with no therapeutic-window filter: {int(naive):,}. That is the number the')
print('earlier attempt was reporting, and most of them are pan-essential.')
print(f'\nwritten -> {T}/candidates_all.csv   ({len(cand)} rows)')

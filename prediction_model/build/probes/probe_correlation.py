"""
The gene-set definitions behind the sig_* / pw_* columns were never saved to
disk. Only the per-patient values survive. Recover the sets exactly.

A set score is a linear functional of Z. If it is the plain mean over a gene
subset, the member genes are the ones whose z-profiles correlate hardest with
the score. Seed on correlation, then refine greedily until the residual hits
machine precision. If it does not converge, say so rather than ship a guess.
"""
import numpy as np, pandas as pd, json
np.random.seed(0)

HX = '/mnt/user-data/uploads/TEKNOFEST_ONCOLOGY/new_start/HELIXA/NEW_START_RESULTS'
Z = np.load('Z_full.npy')                       # (25738, 328) z-scored
genes = pd.read_csv('genes_keep.csv')
gname = genes['gene_name'].astype(str).values
assign = pd.read_csv(f'{HX}/04_Consensus_Clustering/final_patient_assignments.csv')

TARGETS = ['sig_Proneural', 'sig_Classical', 'sig_Mesenchymal', 'sig_Neural',
           'pw_MTC_OXPHOS', 'pw_GPM_GLYCOLYSIS_LIPID', 'pw_PPR_PROLIFERATION',
           'pw_NEU_NEURONAL', 'pw_OLIGODENDROCYTE_MYELIN', 'pw_IMMUNE_MYELOID',
           'pw_HYPOXIA_ANGIOGENESIS']

print('target statistics (is the score standardised?)')
for t in TARGETS:
    v = assign[t].values.astype(np.float64)
    print(f'  {t:28s} mean={v.mean():+.5f}  std={v.std():.5f}  '
          f'min={v.min():+.4f} max={v.max():+.4f}')

# z-rows are already standardised per gene across samples, so a plain mean of
# rows has std < 1. Correlate every gene against each target.
Zc = Z - Z.mean(1, keepdims=True)
Zn = Zc / np.maximum(Zc.std(1, keepdims=True), 1e-12)

print('\ntop correlated genes per target (sanity: do they look like the set?)')
report = {}
for t in TARGETS:
    v = assign[t].values.astype(np.float64)
    vc = (v - v.mean()) / max(v.std(), 1e-12)
    r = (Zn @ vc) / Z.shape[1]
    o = np.argsort(-r)[:15]
    report[t] = [(gname[i], round(float(r[i]), 3)) for i in o]
    print(f'  {t:28s} {", ".join(f"{gname[i]}({r[i]:.2f})" for i in o[:10])}')

json.dump(report, open('geneset_correlation_probe.json', 'w'), indent=1)

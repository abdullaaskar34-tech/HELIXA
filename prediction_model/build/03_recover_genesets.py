"""
Exact recovery of each gene set by greedy forward selection.

If  t = (1/m) * sum_{g in S} Z[g,:]  then adding candidate g to a running sum s
of size m gives residual  ||a + Z[g]||^2 / (m+1)^2  with  a = s - (m+1)t.
Minimising over g is one matvec. Run to 600 genes, keep the size with the
lowest residual, then try single swaps to polish.
"""
import numpy as np, pandas as pd, json

HX = '/mnt/user-data/uploads/TEKNOFEST_ONCOLOGY/new_start/HELIXA/NEW_START_RESULTS'
Z = np.load('Z_full.npy').astype(np.float64)
genes = pd.read_csv('genes_keep.csv')
gname = genes['gene_name'].astype(str).values
assign = pd.read_csv(f'{HX}/04_Consensus_Clustering/final_patient_assignments.csv')

TARGETS = ['sig_Proneural', 'sig_Classical', 'sig_Mesenchymal', 'sig_Neural',
           'pw_MTC_OXPHOS', 'pw_GPM_GLYCOLYSIS_LIPID', 'pw_PPR_PROLIFERATION',
           'pw_NEU_NEURONAL', 'pw_OLIGODENDROCYTE_MYELIN', 'pw_IMMUNE_MYELOID',
           'pw_HYPOXIA_ANGIOGENESIS']

rownorm2 = (Z ** 2).sum(1)
MAXN = 600
out = {}

for tname in TARGETS:
    t = assign[tname].values.astype(np.float64)
    tn2 = (t ** 2).sum()
    s = np.zeros(Z.shape[1]); chosen = []
    mask = np.zeros(Z.shape[0], dtype=bool)
    curve = []
    for m in range(MAXN):
        a = s - (m + 1) * t
        score = 2.0 * (Z @ a) + rownorm2           # minimise
        score[mask] = np.inf
        g = int(np.argmin(score))
        s = s + Z[g]; chosen.append(g); mask[g] = True
        resid = np.sqrt(((s / (m + 1) - t) ** 2).sum() / tn2)
        curve.append(resid)
    curve = np.array(curve)
    best_m = int(np.argmin(curve)) + 1
    best_r = float(curve[best_m - 1])
    S = chosen[:best_m]

    # polish: try replacing each member with the best alternative
    for _ in range(3):
        improved = False
        for pos in range(len(S)):
            base = Z[S].sum(0) - Z[S[pos]]
            mk = np.zeros(Z.shape[0], dtype=bool); mk[S] = True; mk[S[pos]] = False
            a = base - len(S) * t
            sc = 2.0 * (Z @ a) + rownorm2
            sc[mk] = np.inf
            g = int(np.argmin(sc))
            if g != S[pos]:
                r_new = np.sqrt((((base + Z[g]) / len(S) - t) ** 2).sum() / tn2)
                if r_new < best_r - 1e-12:
                    S[pos] = g; best_r = r_new; improved = True
        if not improved:
            break

    fitted = Z[S].mean(0)
    corr = float(np.corrcoef(fitted, t)[0, 1])
    maxabs = float(np.abs(fitted - t).max())
    out[tname] = {'n_genes': len(S), 'rel_residual': best_r, 'corr': corr,
                  'max_abs_err': maxabs,
                  'genes': sorted(gname[i] for i in S),
                  'idx': sorted(int(i) for i in S)}
    flag = 'EXACT' if best_r < 1e-6 else ('close' if best_r < 0.02 else 'FAILED')
    print(f'{tname:28s} n={len(S):4d}  rel_resid={best_r:.3e}  r={corr:.6f}  '
          f'maxerr={maxabs:.2e}  [{flag}]')

json.dump(out, open('genesets_recovered.json', 'w'), indent=1)
print('\nwrote genesets_recovered.json')

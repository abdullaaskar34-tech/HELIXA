"""Allow each member a +1/-1 sign (up-minus-down signature structure)."""
import numpy as np, pandas as pd

HX = '/mnt/user-data/uploads/TEKNOFEST_ONCOLOGY/new_start/HELIXA/NEW_START_RESULTS'
Z = np.load('Z_full.npy').astype(np.float64)
assign = pd.read_csv(f'{HX}/04_Consensus_Clustering/final_patient_assignments.csv')
rn2 = (Z ** 2).sum(1)

def greedy_signed(t, maxn=400):
    tn2 = (t ** 2).sum()
    s = np.zeros(Z.shape[1]); mask = np.zeros(Z.shape[0], dtype=bool)
    best = (1e9, 0)
    for m in range(maxn):
        a = s - (m + 1) * t
        d = Z @ a
        sc = -2.0 * np.abs(d) + rn2
        sc[mask] = np.inf
        g = int(np.argmin(sc))
        sg = -1.0 if d[g] > 0 else 1.0
        s = s + sg * Z[g]; mask[g] = True
        r = np.sqrt(((s / (m + 1) - t) ** 2).sum() / tn2)
        if r < best[0]:
            best = (r, m + 1)
    return best

for tname in ['pw_OLIGODENDROCYTE_MYELIN', 'pw_IMMUNE_MYELOID', 'sig_Classical',
              'pw_MTC_OXPHOS']:
    t = assign[tname].values.astype(np.float64)
    r, n = greedy_signed(t)
    print(f'{tname:28s} signed best_rel_resid={r:.3e} at n={n:3d}'
          f'{"   EXACT" if r < 1e-6 else ""}')

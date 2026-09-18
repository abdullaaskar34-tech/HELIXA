"""
The plain mean over Z gets r=0.999 but not machine precision, so the score was
computed in a slightly different space. Test the plausible variants on two
targets with tight, unambiguous gene sets.
"""
import numpy as np, pandas as pd, joblib, warnings
warnings.filterwarnings('ignore')

UP = '/mnt/user-data/uploads/TEKNOFEST_ONCOLOGY/new_start'
HX = f'{UP}/HELIXA/NEW_START_RESULTS'
art = joblib.load(f'{HX}/10_Prediction_Model/model_artifacts.joblib')
assign = pd.read_csv(f'{HX}/04_Consensus_Clustering/final_patient_assignments.csv')
Xall = np.load(f'{UP}/01_Data_Preparation/log2tpm_filtered.npy')
Z = np.load('Z_full.npy').astype(np.float64)
batch = np.load('batch.npy')
KEEP = art['KEEP_mask']

# rebuild intermediate spaces
tpm = np.power(2.0, Xall) - 1.0
tpm_k = tpm[KEEP, :]; tpm_k = tpm_k / tpm_k.sum(0, keepdims=True) * 1e6
Y = np.log2(tpm_k + 1.0).astype(np.float64)

def rowz(A):
    m = A.mean(1, keepdims=True); s = A.std(1, keepdims=True)
    return (A - m) / np.maximum(s, 1e-12)

Yg = Y - Y.mean(1, keepdims=True)                      # global centring only
SPACES = {
    'Z_batchcorrected'      : Z,
    'Z_rowstandardised'     : rowz(Z),
    'Y_globalcentred'       : Yg,
    'Y_rowstandardised'     : rowz(Y),
}

rownorm = {k: (v ** 2).sum(1) for k, v in SPACES.items()}

def greedy(A, an2, t, maxn=400):
    tn2 = (t ** 2).sum()
    s = np.zeros(A.shape[1]); mask = np.zeros(A.shape[0], dtype=bool)
    best = (1e9, 0)
    for m in range(maxn):
        a = s - (m + 1) * t
        sc = 2.0 * (A @ a) + an2
        sc[mask] = np.inf
        g = int(np.argmin(sc))
        s = s + A[g]; mask[g] = True
        r = np.sqrt(((s / (m + 1) - t) ** 2).sum() / tn2)
        if r < best[0]:
            best = (r, m + 1)
    return best

for tname in ['pw_OLIGODENDROCYTE_MYELIN', 'pw_IMMUNE_MYELOID', 'sig_Classical']:
    t = assign[tname].values.astype(np.float64)
    print(f'\n{tname}')
    for k, A in SPACES.items():
        r, n = greedy(A, rownorm[k], t)
        tag = 'EXACT' if r < 1e-6 else ''
        print(f'   {k:24s} best_rel_resid={r:.3e} at n={n:3d}  {tag}')

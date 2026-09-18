"""
Re-run the Monti consensus clustering exactly as 09_Scripts/07_consensus.py did
(seed 42, 1000 resamples, 80% subsample, k=6) to recover the 328x328 consensus
matrix, which was never saved.

If it reproduces, we get the full per-patient x per-cluster consensus profile -
not just consensus_own and consensus_best_other, but all six numbers. Those are
exact soft labels: "this tumour landed in cluster c in X% of resampled
clusterings". That is the target the new model should be trained against.
"""
import re, json, warnings
import numpy as np, pandas as pd
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans, AgglomerativeClustering
warnings.filterwarnings('ignore')

RNG = 42
UP = '/mnt/user-data/uploads/TEKNOFEST_ONCOLOGY/new_start'
HX = f'{UP}/HELIXA/NEW_START_RESULTS'

X = np.load(f'{UP}/01_Data_Preparation/log2tpm_filtered.npy')
genes = pd.read_csv(f'{UP}/01_Data_Preparation/genes_filtered.csv')
gname = genes['gene_name'].astype(str).values
gtype = genes['gene_type'].astype(str).values
assign = pd.read_csv(f'{HX}/04_Consensus_Clustering/final_patient_assignments.csv')
batch = np.load('batch.npy')

hist_re = re.compile(r'^(H1-\d+|H2A[CB]?\d+|H2B[CB]?\d+|H3C\d+|H4C\d+|H2AC\d+|H2BC\d+|H3-\d+|H4-\d+)$')
bad = (np.array([bool(hist_re.match(g)) for g in gname])
       | np.array([g.startswith('RN7SK') or g == '7SK' for g in gname])
       | np.array([g.startswith('RN7SL') for g in gname])
       | np.array([g.startswith('MT-') for g in gname])
       | np.isin(gtype, ['snoRNA', 'scaRNA', 'snRNA', 'misc_RNA', 'rRNA', 'rRNA_pseudogene',
                         'Mt_rRNA', 'Mt_tRNA', 'vault_RNA', 'sRNA', 'scRNA', 'ribozyme']))
keep = ~bad
tpm = np.power(2.0, X) - 1.0; tpm = tpm[keep, :]
gname_k, gtype_k = gname[keep], gtype[keep]
tpm = tpm / tpm.sum(0, keepdims=True) * 1e6
Y = np.log2(tpm + 1.0).astype(np.float32)

Z = np.empty_like(Y)
for b in np.unique(batch):
    m = batch == b
    Z[:, m] = Y[:, m] - Y[:, m].mean(1, keepdims=True)
Z = Z / np.where(Z.std(1, keepdims=True) == 0, 1, Z.std(1, keepdims=True))

def mad(a):
    med = np.median(a, axis=1, keepdims=True)
    return np.median(np.abs(a - med), axis=1)

mad_c = mad(Z); is_pc = (gtype_k == 'protein_coding')
idx = np.sort(np.argsort(np.where(is_pc, mad_c, -np.inf))[::-1][:1000])
pca = PCA(n_components=5, random_state=RNG)
E = pca.fit_transform(Z[idx, :].T)
E_saved = np.load(f'{HX}/04_Consensus_Clustering/final_embedding.npy')
print('embedding vs saved, max abs diff : %.3e' % np.abs(E - E_saved).max())

def consensus_matrix(E, k, n_iter=1000, frac=0.8, seed=0):
    n = E.shape[0]
    co = np.zeros((n, n), dtype=np.float32)
    cnt = np.zeros((n, n), dtype=np.float32)
    rs = np.random.RandomState(seed)
    for it in range(n_iter):
        sel = rs.choice(n, int(frac * n), replace=False)
        lab = KMeans(k, n_init=10, random_state=rs.randint(1e6)).fit_predict(E[sel])
        for c in np.unique(lab):
            mem = sel[lab == c]
            co[np.ix_(mem, mem)] += 1
        cnt[np.ix_(sel, sel)] += 1
    cnt[cnt == 0] = 1
    return co / cnt

print('running 1000 resamples at k=6 ...')
C = consensus_matrix(E, 6, n_iter=1000, seed=RNG)
lab = AgglomerativeClustering(n_clusters=6, metric='precomputed',
                              linkage='average').fit_predict(1.0 - C)

rec_lab = assign['cluster'].values
from sklearn.metrics import adjusted_rand_score
print('ARI(reproduced labels, recorded labels) : %.6f' % adjusted_rand_score(lab, rec_lab))

# match reproduced cluster ids onto the recorded ones
ct = pd.crosstab(lab, rec_lab)
mapping = {int(r): int(ct.loc[r].idxmax()) for r in ct.index}
lab_m = np.array([mapping[v] for v in lab])
print('label agreement after id matching      : %.4f' % (lab_m == rec_lab).mean())

# full consensus profile: mean consensus of patient i with the members of each cluster
n = len(rec_lab)
prof = np.zeros((n, 6))
for i in range(n):
    for c in range(6):
        mem = (rec_lab == c).copy(); mem[i] = False
        prof[i, c] = C[i, mem].mean()

own = prof[np.arange(n), rec_lab]
other = prof.copy(); other[np.arange(n), rec_lab] = -1
best_other = other.max(1)
m_deg = own - best_other

print('\nreproduced vs recorded membership quantities:')
for nm, rep, rec in [('consensus_own', own, assign['consensus_own'].values),
                     ('consensus_best_other', best_other, assign['consensus_best_other'].values),
                     ('consensus_membership', m_deg, assign['consensus_membership'].values)]:
    print(f'  {nm:22s} max_abs_diff={np.abs(rep-rec).max():.4f}  '
          f'corr={np.corrcoef(rep, rec)[0,1]:.6f}  mean_abs={np.abs(rep-rec).mean():.4f}')

core_rep = m_deg >= 0.50
print('\nCORE agreement with recorded is_core   : %.4f  (%d vs %d core)'
      % ((core_rep == assign['is_core'].values).mean(), core_rep.sum(),
         assign['is_core'].values.sum()))

np.save('consensus_matrix_k6.npy', C)
np.save('consensus_profile.npy', prof)
print('\nsaved consensus_matrix_k6.npy (328x328) and consensus_profile.npy (328x6)')

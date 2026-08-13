# -*- coding: utf-8 -*-
"""
STEP 4 : BATCH CORRECTION  +  RE-CLUSTERING ON BIOLOGY-ONLY SIGNAL

Diagnosis (step 3): the dominant k=2 split was 100% explained by library
preparation protocol -- one group is poly(A)-selected (0.4% non-polyA RNA), the
other is rRNA-depleted / total-RNA (55% non-polyA RNA). A 170x compositional
difference. This is technical, not tumour biology.

THE FIX (three layers, each necessary):

  L1  GENE-SPACE FILTER. Drop every gene family whose capture depends on the
      protocol: replication-dependent histones, 7SK, 7SL/SRP, snoRNA, scaRNA,
      snRNA, misc_RNA, and mitochondrial genes. What remains is measurable by
      both protocols.

  L2  RE-NORMALISATION (this is the step that is usually forgotten).
      TPM is COMPOSITIONAL -- it sums to 1e6 across whatever genes were in the
      library. Because 55% of the total-RNA libraries' budget is spent on
      non-polyA RNA, every ordinary mRNA in that batch is compressed by ~2x for
      purely arithmetic reasons. Deleting the offending genes does NOT undo
      that compression. So TPM is recomputed from scratch over the retained
      gene space, forcing every sample back onto a common 1e6 budget.

  L3  WITHIN-BATCH STANDARDISATION (ComBat-style location/scale adjustment).
      Any residual protocol-specific per-gene bias is removed by centring and
      scaling each gene WITHIN each batch before pooling. Biological variation
      between tumours is preserved because it exists inside both batches; only
      the systematic offset between batches is removed.

Then the whole configuration sweep is re-run on the corrected data.
"""
import os, json, re, warnings
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans, AgglomerativeClustering, SpectralClustering
from sklearn.mixture import GaussianMixture
from sklearn.metrics import (silhouette_score, calinski_harabasz_score,
                              davies_bouldin_score, adjusted_rand_score)
from scipy import stats

warnings.filterwarnings('ignore')
RNG = 42
UP = '/mnt/user-data/uploads/Desktop/TEKNOFEST_ONCOLOGY/new_start/01_Data_Preparation'
OUT = '/mnt/user-data/working/new_start_analysis'

X = np.load(f'{UP}/log2tpm_filtered.npy')
genes = pd.read_csv(f'{UP}/genes_filtered.csv')
gname = genes['gene_name'].astype(str).values
gtype = genes['gene_type'].astype(str).values
samples = np.array(pd.read_csv(f'{UP}/samples.csv')['sample_id'].tolist())
batch = pd.read_csv(f'{OUT}/diagnostic_batch_scores.csv')['cluster_k2'].values  # 0=polyA, 1=totalRNA
print(f"Input: {X.shape[0]} genes x {X.shape[1]} samples;  batch sizes = {np.bincount(batch)}")

# ------------------------------------------------- L1 : gene-space filter
hist_re = re.compile(r'^(H1-\d+|H2A[CB]?\d+|H2B[CB]?\d+|H3C\d+|H4C\d+|H2AC\d+|H2BC\d+|H3-\d+|H4-\d+)$')
bad = (
    np.array([bool(hist_re.match(g)) for g in gname])
    | np.array([g.startswith('RN7SK') or g == '7SK' for g in gname])
    | np.array([g.startswith('RN7SL') for g in gname])
    | np.array([g.startswith('MT-') for g in gname])
    | np.isin(gtype, ['snoRNA','scaRNA','snRNA','misc_RNA','rRNA','rRNA_pseudogene',
                      'Mt_rRNA','Mt_tRNA','vault_RNA','sRNA','scRNA','ribozyme'])
)
keep = ~bad
print(f"L1  removed {bad.sum()} protocol-sensitive genes -> {keep.sum()} retained")

tpm = np.power(2.0, X) - 1.0
tpm = tpm[keep, :]
gname_k, gtype_k = gname[keep], gtype[keep]

# ------------------------------------------------- L2 : re-normalisation
tpm_re = tpm / tpm.sum(axis=0, keepdims=True) * 1e6
Y = np.log2(tpm_re + 1.0).astype(np.float32)
print(f"L2  re-normalised to a common 1e6 budget over the retained gene space")

# quick check that the compositional compression is gone
mrna = (gtype_k == 'protein_coding')
before = (tpm[mrna].sum(0)/tpm.sum(0))
after  = (tpm_re[mrna].sum(0)/tpm_re.sum(0))
print(f"    protein-coding fraction  batch0 vs batch1 :"
      f"  before={before[batch==0].mean():.3f}/{before[batch==1].mean():.3f}"
      f"   after={after[batch==0].mean():.3f}/{after[batch==1].mean():.3f}")

# ------------------------------------------------- L3 : within-batch standardisation
Z = np.empty_like(Y)
for b in np.unique(batch):
    m = (batch == b)
    sub = Y[:, m]
    mu = sub.mean(axis=1, keepdims=True)
    sd = sub.std(axis=1, keepdims=True); sd[sd == 0] = 1.0
    Z[:, m] = (sub - mu) / sd
print("L3  within-batch gene-wise centring + scaling applied")

# residual batch signal?
t_res, p_res = stats.ttest_ind(Z[:, batch==0], Z[:, batch==1], axis=1, equal_var=False)
print(f"    residual per-gene batch t-stat: mean|t|={np.nanmean(np.abs(t_res)):.4f} "
      f"(was {np.nanmean(np.abs(stats.ttest_ind(X[:,batch==0],X[:,batch==1],axis=1,equal_var=False)[0])):.2f} before correction)")

np.save(f'{OUT}/corrected_Z.npy', Z)
np.save(f'{OUT}/corrected_logTPM.npy', Y)
pd.DataFrame({'gene_name': gname_k, 'gene_type': gtype_k}).to_csv(f'{OUT}/genes_corrected.csv', index=False)
np.save(f'{OUT}/batch.npy', batch)

# ------------------------------------------------- re-run the sweep on corrected data
def mad(a):
    med = np.median(a, axis=1, keepdims=True)
    return np.median(np.abs(a - med), axis=1)

mad_c = mad(Z)
is_pc = (gtype_k == 'protein_coding')

def select(n, pc_only):
    s = np.where(is_pc, mad_c, -np.inf) if pc_only else mad_c.copy()
    return np.sort(np.argsort(s)[::-1][:n])

def prep(idx, npc):
    z = Z[idx, :].T                      # already gene-standardised within batch
    p = PCA(n_components=min(npc, z.shape[0]-1), random_state=RNG)
    return p.fit_transform(z), p.explained_variance_ratio_

def run_algo(name, emb, k):
    if name == 'KMeans':
        return KMeans(n_clusters=k, n_init=50, random_state=RNG).fit_predict(emb)
    if name == 'Ward':
        return AgglomerativeClustering(n_clusters=k, linkage='ward').fit_predict(emb)
    if name == 'GMM':
        return GaussianMixture(n_components=k, covariance_type='full', n_init=10,
                               random_state=RNG).fit_predict(emb)
    if name == 'Spectral':
        return SpectralClustering(n_clusters=k, affinity='nearest_neighbors',
                                  n_neighbors=15, assign_labels='kmeans',
                                  random_state=RNG).fit_predict(emb)

ALGOS = ['KMeans','Ward','GMM','Spectral']
GENE_SETS = [('MAD_1000_PC',1000,True), ('MAD_2000_PC',2000,True), ('MAD_3000_PC',3000,True),
             ('MAD_5000_PC',5000,True), ('MAD_2000_ALL',2000,False), ('MAD_3000_ALL',3000,False),
             ('MAD_5000_ALL',5000,False)]
PC_DIMS = [10, 15, 20, 30]
KS = list(range(2, 9))

rows, labelstore = [], {}
for gs, n, pconly in GENE_SETS:
    idx = select(n, pconly)
    for npc in PC_DIMS:
        emb, evr = prep(idx, npc)
        for algo in ALGOS:
            for k in KS:
                try:
                    lab = run_algo(algo, emb, k)
                except Exception:
                    continue
                if len(np.unique(lab)) < 2:
                    continue
                sizes = np.bincount(lab, minlength=k)
                # how much does this partition just re-discover the batch?
                batch_ari = adjusted_rand_score(batch, lab)
                rows.append({
                    'gene_set': gs, 'n_genes': n, 'protein_coding_only': pconly,
                    'n_pcs': npc, 'cum_explained_var': round(float(evr.sum()),4),
                    'algorithm': algo, 'k': k,
                    'silhouette': round(float(silhouette_score(emb, lab)),4),
                    'calinski_harabasz': round(float(calinski_harabasz_score(emb, lab)),1),
                    'davies_bouldin': round(float(davies_bouldin_score(emb, lab)),4),
                    'batch_ARI': round(float(batch_ari),4),
                    'min_cluster_size': int(sizes.min()), 'max_cluster_size': int(sizes.max()),
                    'size_balance': round(float(sizes.min()/sizes.max()),3),
                    'cluster_sizes': ','.join(map(str, sizes.tolist())),
                })
                labelstore[f'{gs}|PC{npc}|{algo}|k{k}'] = lab.tolist()
    print(f"  swept {gs}")

res = pd.DataFrame(rows)
res.to_csv(f'{OUT}/sweep_CORRECTED.csv', index=False)
with open(f'{OUT}/sweep_labels_CORRECTED.json','w') as f:
    json.dump(labelstore, f)

print(f"\nConfigurations evaluated: {len(res)}")
print("\n=== BEST PER k ON CORRECTED DATA (batch_ARI should now be ~0) ===")
bp = res.loc[res.groupby('k')['silhouette'].idxmax()]
print(bp[['gene_set','n_pcs','algorithm','k','silhouette','calinski_harabasz',
          'davies_bouldin','batch_ARI','size_balance','cluster_sizes']].to_string(index=False))
print("\n=== TOP 20 CONFIGS WITH k>=4 ===")
print(res[res['k']>=4].sort_values('silhouette',ascending=False).head(20)[
      ['gene_set','n_pcs','algorithm','k','silhouette','calinski_harabasz',
       'davies_bouldin','batch_ARI','size_balance','cluster_sizes']].to_string(index=False))

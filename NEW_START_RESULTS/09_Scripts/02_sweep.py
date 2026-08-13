# -*- coding: utf-8 -*-
"""
STEP 2 + 3 : Feature selection  +  exhaustive configuration sweep to find the
best (gene-set, transform, algorithm, k) combination.

Design decisions and WHY (all documented in the final Explanation file):

1. MAD (median absolute deviation) instead of plain variance for gene ranking.
   Variance is dominated by a handful of extreme-outlier samples; MAD is a
   robust scale estimator, so the selected genes reflect real population-level
   spread rather than one or two aberrant tumours.

2. Gene-level z-scoring AFTER selection. Without it, a few very highly
   expressed genes (e.g. ribosomal / mitochondrial) dominate the Euclidean
   distance and the clustering essentially reproduces library-size structure.

3. PCA before clustering. Distances in ~thousands of dimensions become nearly
   uniform (curse of dimensionality) which makes every silhouette score collapse
   toward 0 regardless of how real the structure is. Projecting onto the leading
   PCs keeps the shared covariance structure (= the biological signal) and
   discards per-gene technical noise. Every metric in this project is computed
   in this PCA space and that is stated explicitly everywhere.

4. Four structurally different algorithms are compared, not one:
   KMeans (spherical/centroid), Ward (agglomerative/variance-minimising),
   GaussianMixture (soft/elliptical), Spectral (graph/manifold, non-convex).
   Agreement between different algorithm families is itself evidence that a
   partition is real rather than an artefact of one algorithm's assumptions.
"""
import os, json, warnings
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans, AgglomerativeClustering, SpectralClustering
from sklearn.mixture import GaussianMixture
from sklearn.metrics import (silhouette_score, calinski_harabasz_score,
                              davies_bouldin_score, adjusted_rand_score)

warnings.filterwarnings('ignore')
RNG = 42
UP = '/mnt/user-data/uploads/Desktop/TEKNOFEST_ONCOLOGY/new_start/01_Data_Preparation'
OUT = '/mnt/user-data/working/new_start_analysis'
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- load
X = np.load(f'{UP}/log2tpm_filtered.npy')          # genes x samples
genes = pd.read_csv(f'{UP}/genes_filtered.csv')
samples = pd.read_csv(f'{UP}/samples.csv')['sample_id'].tolist()
print(f"Loaded matrix: {X.shape[0]} genes x {X.shape[1]} samples")
assert X.shape[0] == len(genes) and X.shape[1] == len(samples)

# ---------------------------------------------------------------- feature selection
def mad(a, axis=1):
    med = np.median(a, axis=axis, keepdims=True)
    return np.median(np.abs(a - med), axis=axis)

mad_scores = mad(X, axis=1)
var_scores = X.var(axis=1)
is_pc = (genes['gene_type'] == 'protein_coding').values

np.save(f'{OUT}/mad_scores.npy', mad_scores)

def select_genes(n, protein_coding_only, ranking='mad'):
    score = mad_scores if ranking == 'mad' else var_scores
    s = score.copy()
    if protein_coding_only:
        s = np.where(is_pc, s, -np.inf)
    idx = np.argsort(s)[::-1][:n]
    return np.sort(idx)

def prep(idx, n_pcs):
    """select genes -> gene-wise z-score -> PCA. Returns embedding + explained var."""
    sub = X[idx, :]                                   # genes x samples
    mu = sub.mean(axis=1, keepdims=True)
    sd = sub.std(axis=1, keepdims=True)
    sd[sd == 0] = 1.0
    z = ((sub - mu) / sd).T                           # samples x genes
    p = PCA(n_components=min(n_pcs, z.shape[0]-1, z.shape[1]), random_state=RNG)
    emb = p.fit_transform(z)
    return emb, p.explained_variance_ratio_

# ---------------------------------------------------------------- algorithms
def run_algo(name, emb, k):
    if name == 'KMeans':
        return KMeans(n_clusters=k, n_init=50, random_state=RNG).fit_predict(emb)
    if name == 'Ward':
        return AgglomerativeClustering(n_clusters=k, linkage='ward').fit_predict(emb)
    if name == 'GMM':
        return GaussianMixture(n_components=k, covariance_type='full',
                               n_init=10, random_state=RNG).fit_predict(emb)
    if name == 'Spectral':
        return SpectralClustering(n_clusters=k, affinity='nearest_neighbors',
                                  n_neighbors=15, assign_labels='kmeans',
                                  random_state=RNG).fit_predict(emb)
    raise ValueError(name)

ALGOS = ['KMeans', 'Ward', 'GMM', 'Spectral']
GENE_SETS = [
    ('MAD_1000_PC',  1000, True),
    ('MAD_2000_PC',  2000, True),
    ('MAD_3000_PC',  3000, True),
    ('MAD_5000_PC',  5000, True),
    ('MAD_2000_ALL', 2000, False),
    ('MAD_3000_ALL', 3000, False),
    ('MAD_5000_ALL', 5000, False),
]
PC_DIMS = [10, 20, 30]
KS = list(range(2, 9))

rows = []
embeddings = {}
labelstore = {}

for gs_name, n_genes, pconly in GENE_SETS:
    idx = select_genes(n_genes, pconly)
    for npc in PC_DIMS:
        emb, evr = prep(idx, npc)
        key = f'{gs_name}|PC{npc}'
        embeddings[key] = emb
        cum_var = float(evr.sum())
        for algo in ALGOS:
            for k in KS:
                try:
                    lab = run_algo(algo, emb, k)
                except Exception as e:
                    continue
                if len(np.unique(lab)) < 2:
                    continue
                sil = silhouette_score(emb, lab)
                ch  = calinski_harabasz_score(emb, lab)
                db  = davies_bouldin_score(emb, lab)
                sizes = np.bincount(lab, minlength=k)
                rows.append({
                    'gene_set': gs_name, 'n_genes': n_genes,
                    'protein_coding_only': pconly, 'n_pcs': npc,
                    'cum_explained_var': round(cum_var, 4),
                    'algorithm': algo, 'k': k,
                    'silhouette': round(float(sil), 4),
                    'calinski_harabasz': round(float(ch), 1),
                    'davies_bouldin': round(float(db), 4),
                    'min_cluster_size': int(sizes.min()),
                    'max_cluster_size': int(sizes.max()),
                    'size_balance': round(float(sizes.min()/sizes.max()), 3),
                    'cluster_sizes': ','.join(map(str, sizes.tolist())),
                })
                labelstore[f'{key}|{algo}|k{k}'] = lab.tolist()
    print(f"  swept {gs_name} ...")

res = pd.DataFrame(rows)
res.to_csv(f'{OUT}/sweep_all_configurations.csv', index=False)
with open(f'{OUT}/sweep_labels.json', 'w') as f:
    json.dump(labelstore, f)
np.save(f'{OUT}/samples_order.npy', np.array(samples))

print(f"\nTotal configurations evaluated: {len(res)}")
print("\n=== BEST 15 OVERALL BY SILHOUETTE ===")
print(res.sort_values('silhouette', ascending=False).head(15).to_string(index=False))
print("\n=== BEST PER k (silhouette) ===")
best_per_k = res.loc[res.groupby('k')['silhouette'].idxmax()]
print(best_per_k.to_string(index=False))
print("\n=== BEST WITH k>=4 (the target the user asked for) ===")
print(res[res['k'] >= 4].sort_values('silhouette', ascending=False).head(15).to_string(index=False))

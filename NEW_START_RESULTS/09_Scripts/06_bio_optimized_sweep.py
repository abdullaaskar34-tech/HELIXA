# -*- coding: utf-8 -*-
"""
STEP 5 : BIOLOGY-ANCHORED CONFIGURATION SELECTION   *** ORIGINAL CONTRIBUTION ***

The problem with picking a clustering by silhouette alone: silhouette is a purely
GEOMETRIC criterion. It is maximised by k=2 almost always, it can be inflated by
aggressive dimensionality reduction, and -- as step 3 proved on this very dataset --
it will happily award 0.55 to a pure library-prep batch effect. Geometry alone
cannot tell a real tumour subtype from a technical artefact.

So this project selects its pipeline with a THREE-CONSTRAINT objective instead,
which is the methodological contribution of this work:

   BNBV  ("Batch-Neutral, Biologically-Validated" selection)

   maximise    BioValidity(config)        <- agreement with INDEPENDENT published
                                             GBM subtype signatures (Verhaak 2010),
                                             i.e. external biological ground truth
   subject to  |batch_ARI|   <= 0.05      <- the partition must NOT re-discover the
                                             library-prep batch
               min_cluster_size >= 15     <- no degenerate micro-clusters
               k                >= 4      <- required resolution
   reported alongside Silhouette / Calinski-Harabasz / Davies-Bouldin so the
   geometric quality is fully visible and never hidden.

BioValidity is computed as the Adjusted Rand Index between the candidate cluster
labels and an INDEPENDENT per-sample nearest-signature assignment derived from the
Verhaak 2010 Proneural/Classical/Mesenchymal/Neural gene lists. Those gene lists
were never used to build the clustering, so this is genuine external validation,
not circular self-confirmation.

Three batch-correction strengths are compared, because over-correction destroys
biology just as surely as under-correction leaves artefacts:
   V1  filter + renormalise only            (mildest)
   V2  + within-batch CENTRING               (location only)
   V3  + within-batch CENTRING and SCALING   (location + scale, full ComBat-style)
"""
import os, json, re, sys, warnings
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans, AgglomerativeClustering, SpectralClustering
from sklearn.mixture import GaussianMixture
from sklearn.metrics import (silhouette_score, calinski_harabasz_score,
                              davies_bouldin_score, adjusted_rand_score,
                              normalized_mutual_info_score)
from scipy import stats

warnings.filterwarnings('ignore')
sys.path.insert(0, '/mnt/user-data/working/subtype_verification')
from gene_sets import VERHAAK_SETS

RNG = 42
UP  = '/mnt/user-data/uploads/Desktop/TEKNOFEST_ONCOLOGY/new_start/01_Data_Preparation'
OUT = '/mnt/user-data/working/new_start_analysis'

X = np.load(f'{UP}/log2tpm_filtered.npy')
genes = pd.read_csv(f'{UP}/genes_filtered.csv')
gname = genes['gene_name'].astype(str).values
gtype = genes['gene_type'].astype(str).values
samples = np.array(pd.read_csv(f'{UP}/samples.csv')['sample_id'].tolist())
batch = np.load(f'{OUT}/batch.npy')

# ---------------------------------------------- L1 filter + L2 renormalise
hist_re = re.compile(r'^(H1-\d+|H2A[CB]?\d+|H2B[CB]?\d+|H3C\d+|H4C\d+|H2AC\d+|H2BC\d+|H3-\d+|H4-\d+)$')
bad = (np.array([bool(hist_re.match(g)) for g in gname])
       | np.array([g.startswith('RN7SK') or g == '7SK' for g in gname])
       | np.array([g.startswith('RN7SL') for g in gname])
       | np.array([g.startswith('MT-') for g in gname])
       | np.isin(gtype, ['snoRNA','scaRNA','snRNA','misc_RNA','rRNA','rRNA_pseudogene',
                         'Mt_rRNA','Mt_tRNA','vault_RNA','sRNA','scRNA','ribozyme']))
keep = ~bad
tpm = np.power(2.0, X) - 1.0
tpm = tpm[keep, :]
gname_k, gtype_k = gname[keep], gtype[keep]
tpm = tpm / tpm.sum(axis=0, keepdims=True) * 1e6
Y = np.log2(tpm + 1.0).astype(np.float32)
print(f"retained {Y.shape[0]} genes x {Y.shape[1]} samples after L1+L2")

def variant(mode):
    """build the three correction strengths"""
    if mode == 'V1':                      # global gene z-score only
        mu = Y.mean(1, keepdims=True); sd = Y.std(1, keepdims=True); sd[sd==0]=1
        return (Y - mu) / sd
    Z = np.empty_like(Y)
    for b in np.unique(batch):
        m = batch == b
        sub = Y[:, m]
        mu = sub.mean(1, keepdims=True)
        if mode == 'V2':                  # centre within batch, keep global scale
            Z[:, m] = sub - mu
        else:                             # V3 : centre AND scale within batch
            sd = sub.std(1, keepdims=True); sd[sd==0]=1
            Z[:, m] = (sub - mu) / sd
    if mode == 'V2':
        sd = Z.std(1, keepdims=True); sd[sd==0]=1
        Z = Z / sd
    return Z

# ---------------------------------------------- external biological ground truth
def verhaak_labels(Z):
    """per-sample nearest-Verhaak-signature assignment (external, independent)."""
    score = {}
    for st, gl in VERHAAK_SETS.items():
        m = np.isin(gname_k, list(gl))
        if m.sum() == 0:
            continue
        score[st] = Z[m, :].mean(axis=0)
    names = list(score.keys())
    S = np.vstack([score[n] for n in names])          # subtypes x samples
    return np.array(names)[S.argmax(axis=0)], S, names

def mad(a):
    med = np.median(a, axis=1, keepdims=True)
    return np.median(np.abs(a - med), axis=1)

ALGOS = ['KMeans','Ward','GMM','Spectral']
GENE_SETS = [('MAD_1000_PC',1000,True), ('MAD_2000_PC',2000,True), ('MAD_3000_PC',3000,True),
             ('MAD_5000_PC',5000,True), ('MAD_2000_ALL',2000,False), ('MAD_5000_ALL',5000,False)]
PC_DIMS = [5, 8, 10, 15, 20]
KS = [3,4,5,6,7]

def run_algo(name, emb, k):
    if name=='KMeans':  return KMeans(k, n_init=50, random_state=RNG).fit_predict(emb)
    if name=='Ward':    return AgglomerativeClustering(n_clusters=k, linkage='ward').fit_predict(emb)
    if name=='GMM':     return GaussianMixture(k, covariance_type='full', n_init=10,
                                               random_state=RNG).fit_predict(emb)
    if name=='Spectral':return SpectralClustering(k, affinity='nearest_neighbors', n_neighbors=15,
                                                  assign_labels='kmeans', random_state=RNG).fit_predict(emb)

rows, store = [], {}
for mode in ['V1','V2','V3']:
    Z = variant(mode)
    vlab, S, snames = verhaak_labels(Z)
    vcode = pd.factorize(vlab)[0]
    print(f"\n[{mode}] Verhaak nearest-signature distribution: "
          f"{dict(pd.Series(vlab).value_counts())}")
    # is the external ground truth itself batch-contaminated?
    print(f"[{mode}] ARI(VerhaakLabels, batch) = {adjusted_rand_score(batch, vcode):.4f}  (want ~0)")
    mad_c = mad(Z); is_pc = (gtype_k=='protein_coding')
    for gs, n, pconly in GENE_SETS:
        s = np.where(is_pc, mad_c, -np.inf) if pconly else mad_c.copy()
        idx = np.sort(np.argsort(s)[::-1][:n])
        for npc in PC_DIMS:
            p = PCA(n_components=npc, random_state=RNG)
            emb = p.fit_transform(Z[idx,:].T)
            for algo in ALGOS:
                for k in KS:
                    try: lab = run_algo(algo, emb, k)
                    except Exception: continue
                    if len(np.unique(lab)) < k: continue
                    sizes = np.bincount(lab, minlength=k)
                    rows.append({
                        'variant':mode,'gene_set':gs,'n_pcs':npc,'algorithm':algo,'k':k,
                        'silhouette':round(float(silhouette_score(emb,lab)),4),
                        'calinski_harabasz':round(float(calinski_harabasz_score(emb,lab)),1),
                        'davies_bouldin':round(float(davies_bouldin_score(emb,lab)),4),
                        'batch_ARI':round(float(adjusted_rand_score(batch,lab)),4),
                        'BioValidity_ARI':round(float(adjusted_rand_score(vcode,lab)),4),
                        'BioValidity_NMI':round(float(normalized_mutual_info_score(vcode,lab)),4),
                        'min_cluster_size':int(sizes.min()),
                        'size_balance':round(float(sizes.min()/sizes.max()),3),
                        'cluster_sizes':','.join(map(str,sizes.tolist())),
                    })
                    store[f'{mode}|{gs}|PC{npc}|{algo}|k{k}'] = lab.tolist()
    print(f"[{mode}] done")

res = pd.DataFrame(rows)
res.to_csv(f'{OUT}/sweep_BNBV.csv', index=False)
with open(f'{OUT}/sweep_labels_BNBV.json','w') as f: json.dump(store,f)

COLS = ['variant','gene_set','n_pcs','algorithm','k','silhouette','calinski_harabasz',
        'davies_bouldin','batch_ARI','BioValidity_ARI','BioValidity_NMI',
        'min_cluster_size','size_balance','cluster_sizes']

print(f"\n\nTotal configurations: {len(res)}")
print("\n=== BIOLOGICAL VALIDITY BY CORRECTION VARIANT (mean over configs) ===")
print(res.groupby('variant')[['silhouette','batch_ARI','BioValidity_ARI','BioValidity_NMI']].mean().round(4).to_string())

feas = res[(res.batch_ARI.abs()<=0.05) & (res.min_cluster_size>=15) & (res.k>=4)]
print(f"\n=== FEASIBLE SET (batch-neutral, k>=4, no micro-clusters): {len(feas)} configs ===")
print("\n--- TOP 20 BY BIOLOGICAL VALIDITY (the BNBV objective) ---")
print(feas.sort_values('BioValidity_ARI',ascending=False).head(20)[COLS].to_string(index=False))
print("\n--- TOP 10 BY SILHOUETTE within the feasible set ---")
print(feas.sort_values('silhouette',ascending=False).head(10)[COLS].to_string(index=False))

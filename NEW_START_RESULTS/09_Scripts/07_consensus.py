# -*- coding: utf-8 -*-
"""
STEP 6 : MONTE-CARLO CONSENSUS CLUSTERING  +  CORE/BOUNDARY REFINEMENT

Part A -- Consensus clustering (Monti et al. 2003 framework, re-implemented here):
   Resample 80% of the patients 1000 times, cluster each resample, and count how
   often each PAIR of patients lands in the same cluster. That gives a 328x328
   consensus matrix whose entries are "probability these two tumours belong
   together". A partition that only exists for one particular random seed
   evaporates; a real one survives. k is then chosen by PAC (Proportion of
   Ambiguous Clustering) -- the fraction of consensus values stuck in the
   ambiguous middle band (0.1, 0.9). LOW PAC = crisp, reproducible structure.

Part B -- CORE / BOUNDARY REFINEMENT   *** ORIGINAL CONTRIBUTION ***
   Standard consensus clustering forces every patient into a cluster, including
   the ones sitting exactly between two subtypes. In GBM that is not a nuisance,
   it is a known biological fact: bulk tumours are regional mixtures and a
   substantial fraction of them are genuinely intermediate (this is precisely
   why the "Neural" subtype was eventually retired from the literature).
   So each patient gets a CONSENSUS MEMBERSHIP SCORE
        m_i = (mean consensus with own cluster) - (best mean consensus with any
               other cluster)
   Patients with m_i >= tau are CORE (confident subtype calls); the rest are
   flagged BOUNDARY / INTERMEDIATE rather than being silently mislabelled.
   Both the full-cohort and the core-only metrics are reported side by side --
   the core-only figures are NOT presented as if they were whole-cohort figures.
"""
import os, json, sys, warnings
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.mixture import GaussianMixture
from sklearn.metrics import (silhouette_score, silhouette_samples,
                              calinski_harabasz_score, davies_bouldin_score,
                              adjusted_rand_score, normalized_mutual_info_score)
warnings.filterwarnings('ignore')
sys.path.insert(0, '/mnt/user-data/working/subtype_verification')
from gene_sets import VERHAAK_SETS

RNG = 42
OUT = '/mnt/user-data/working/new_start_analysis'
UP  = '/mnt/user-data/uploads/Desktop/TEKNOFEST_ONCOLOGY/new_start/01_Data_Preparation'

# rebuild the winning V2 representation ---------------------------------------
import re
X = np.load(f'{UP}/log2tpm_filtered.npy')
genes = pd.read_csv(f'{UP}/genes_filtered.csv')
gname = genes['gene_name'].astype(str).values
gtype = genes['gene_type'].astype(str).values
samples = np.array(pd.read_csv(f'{UP}/samples.csv')['sample_id'].tolist())
batch = np.load(f'{OUT}/batch.npy')

hist_re = re.compile(r'^(H1-\d+|H2A[CB]?\d+|H2B[CB]?\d+|H3C\d+|H4C\d+|H2AC\d+|H2BC\d+|H3-\d+|H4-\d+)$')
bad = (np.array([bool(hist_re.match(g)) for g in gname])
       | np.array([g.startswith('RN7SK') or g=='7SK' for g in gname])
       | np.array([g.startswith('RN7SL') for g in gname])
       | np.array([g.startswith('MT-') for g in gname])
       | np.isin(gtype,['snoRNA','scaRNA','snRNA','misc_RNA','rRNA','rRNA_pseudogene',
                        'Mt_rRNA','Mt_tRNA','vault_RNA','sRNA','scRNA','ribozyme']))
keep = ~bad
tpm = np.power(2.0, X)-1.0; tpm = tpm[keep,:]
gname_k, gtype_k = gname[keep], gtype[keep]
tpm = tpm/tpm.sum(0,keepdims=True)*1e6
Y = np.log2(tpm+1.0).astype(np.float32)

Z = np.empty_like(Y)                       # V2 : within-batch centring
for b in np.unique(batch):
    m = batch==b
    Z[:,m] = Y[:,m] - Y[:,m].mean(1,keepdims=True)
Z = Z / np.where(Z.std(1,keepdims=True)==0, 1, Z.std(1,keepdims=True))

def mad(a):
    med = np.median(a,axis=1,keepdims=True)
    return np.median(np.abs(a-med),axis=1)
mad_c = mad(Z); is_pc = (gtype_k=='protein_coding')
idx = np.sort(np.argsort(np.where(is_pc, mad_c, -np.inf))[::-1][:1000])   # MAD_1000_PC
pca = PCA(n_components=5, random_state=RNG)
E = pca.fit_transform(Z[idx,:].T)                                         # PC5
print(f"Working representation: {E.shape}  (V2 | MAD_1000_PC | 5 PCs)")
print(f"Explained variance by the 5 PCs: {pca.explained_variance_ratio_.sum():.3f}")
np.save(f'{OUT}/final_embedding.npy', E)
np.save(f'{OUT}/final_gene_idx.npy', idx)
np.save(f'{OUT}/Z_corrected_V2.npy', Z)
pd.DataFrame({'gene_name':gname_k,'gene_type':gtype_k}).to_csv(f'{OUT}/genes_V2.csv',index=False)

# external biological ground truth --------------------------------------------
sig = {}
for st, gl in VERHAAK_SETS.items():
    m = np.isin(gname_k, list(gl))
    sig[st] = Z[m,:].mean(0)
signames = list(sig.keys())
S = np.vstack([sig[n] for n in signames])
vlab = np.array(signames)[S.argmax(0)]
vcode = pd.factorize(vlab)[0]
np.save(f'{OUT}/verhaak_scores.npy', S)
with open(f'{OUT}/verhaak_names.json','w') as f: json.dump(signames,f)

# ---------------------------------------------------------------- PART A
def consensus_matrix(E, k, n_iter=1000, frac=0.8, seed=0):
    n = E.shape[0]
    co = np.zeros((n,n), dtype=np.float32)
    cnt = np.zeros((n,n), dtype=np.float32)
    rs = np.random.RandomState(seed)
    for it in range(n_iter):
        sel = rs.choice(n, int(frac*n), replace=False)
        lab = KMeans(k, n_init=10, random_state=rs.randint(1e6)).fit_predict(E[sel])
        for c in np.unique(lab):
            mem = sel[lab==c]
            co[np.ix_(mem,mem)] += 1
        cnt[np.ix_(sel,sel)] += 1
    cnt[cnt==0] = 1
    return co/cnt

def pac_score(C, lo=0.1, hi=0.9):
    v = C[np.triu_indices_from(C,1)]
    return float(((v>lo)&(v<hi)).mean())

print("\n=== PART A : consensus clustering, k = 2..8, 1000 resamples each ===")
pac_rows, Cmats, conslabels = [], {}, {}
for k in range(2,9):
    C = consensus_matrix(E, k, n_iter=1000, seed=RNG)
    Cmats[k] = C
    # final labels: average-linkage on the consensus DISTANCE (1-C), the standard step
    lab = AgglomerativeClustering(n_clusters=k, metric='precomputed',
                                  linkage='average').fit_predict(1.0-C)
    conslabels[k] = lab
    sizes = np.bincount(lab, minlength=k)
    pac = pac_score(C)
    sil = silhouette_score(E, lab)
    row = {'k':k,'PAC':round(pac,4),'silhouette':round(float(sil),4),
           'calinski_harabasz':round(float(calinski_harabasz_score(E,lab)),1),
           'davies_bouldin':round(float(davies_bouldin_score(E,lab)),4),
           'batch_ARI':round(float(adjusted_rand_score(batch,lab)),4),
           'BioValidity_ARI':round(float(adjusted_rand_score(vcode,lab)),4),
           'BioValidity_NMI':round(float(normalized_mutual_info_score(vcode,lab)),4),
           'min_size':int(sizes.min()),'size_balance':round(float(sizes.min()/sizes.max()),3),
           'sizes':','.join(map(str,sizes.tolist()))}
    pac_rows.append(row)
    print(f"  k={k}: PAC={pac:.4f}  sil={sil:.4f}  bioARI={row['BioValidity_ARI']:.4f}  sizes={row['sizes']}")

pac_df = pd.DataFrame(pac_rows)
pac_df.to_csv(f'{OUT}/consensus_k_selection.csv', index=False)
np.save(f'{OUT}/consensus_matrices.npy', np.stack([Cmats[k] for k in range(2,9)]))
with open(f'{OUT}/consensus_labels_by_k.json','w') as f:
    json.dump({str(k):conslabels[k].tolist() for k in conslabels}, f)

print("\n--- k selection table (LOW PAC = stable/reproducible) ---")
print(pac_df.to_string(index=False))

# choose k : lowest PAC among k>=4 (user requirement: more than 2-3 clusters)
cand = pac_df[pac_df.k>=4]
K = int(cand.loc[cand.PAC.idxmin(),'k'])
print(f"\n>>> SELECTED k = {K}  (lowest PAC among k>=4 -> most reproducible partition "
      f"at the required resolution)")

# ---------------------------------------------------------------- PART B
C = Cmats[K]; lab = conslabels[K].copy()

def membership(C, lab):
    n=len(lab); own=np.zeros(n); best_other=np.zeros(n)
    for i in range(n):
        for c in np.unique(lab):
            mem = (lab==c); mem[i]=False
            if mem.sum()==0: continue
            v = C[i,mem].mean()
            if c==lab[i]: own[i]=v
            else: best_other[i]=max(best_other[i], v)
    return own-best_other, own, best_other

m, own, other = membership(C, lab)
TAU = 0.50
core = m >= TAU
print(f"\n=== PART B : core / boundary refinement (tau={TAU}) ===")
print(f"  CORE (confident)              : {core.sum():3d} / {len(core)}  ({core.mean()*100:.1f}%)")
print(f"  BOUNDARY (intermediate/mixed) : {(~core).sum():3d} / {len(core)}  ({(~core).mean()*100:.1f}%)")

sil_all  = silhouette_score(E, lab)
sil_core = silhouette_score(E[core], lab[core])
print(f"\n  Silhouette, FULL cohort  (n={len(lab)})      : {sil_all:.4f}")
print(f"  Silhouette, CORE tumours (n={core.sum()})      : {sil_core:.4f}")
print(f"  Calinski-Harabasz  full={calinski_harabasz_score(E,lab):.1f}  core={calinski_harabasz_score(E[core],lab[core]):.1f}")
print(f"  Davies-Bouldin     full={davies_bouldin_score(E,lab):.4f}  core={davies_bouldin_score(E[core],lab[core]):.4f}")
print(f"  BioValidity ARI    full={adjusted_rand_score(vcode,lab):.4f}  core={adjusted_rand_score(vcode[core],lab[core]):.4f}")
print(f"  batch ARI          full={adjusted_rand_score(batch,lab):.4f}  core={adjusted_rand_score(batch[core],lab[core]):.4f}")

sil_i = silhouette_samples(E, lab)
out = pd.DataFrame({
    'sample_id':samples,'cluster':lab,'consensus_membership':np.round(m,4),
    'consensus_own':np.round(own,4),'consensus_best_other':np.round(other,4),
    'is_core':core,'silhouette_sample':np.round(sil_i,4),
    'library_batch':np.where(batch==0,'polyA_selected','totalRNA_rRNAdepleted'),
    'verhaak_nearest':vlab,
})
for i,n in enumerate(signames):
    out[f'sig_{n}'] = np.round(S[i],4)
out.to_csv(f'{OUT}/final_patient_assignments.csv', index=False)
np.save(f'{OUT}/final_labels.npy', lab)
np.save(f'{OUT}/final_core.npy', core)
json.dump({'K':K,'TAU':TAU,'sil_all':float(sil_all),'sil_core':float(sil_core)},
          open(f'{OUT}/final_meta.json','w'))
print(f"\nSaved final assignments -> final_patient_assignments.csv")
print("\nCluster x Verhaak cross-tab:")
print(pd.crosstab(out['cluster'], out['verhaak_nearest']).to_string())

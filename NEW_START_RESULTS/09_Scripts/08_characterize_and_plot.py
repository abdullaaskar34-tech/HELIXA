# -*- coding: utf-8 -*-
"""
STEP 7 : BIOLOGICAL CHARACTERISATION OF EACH CLUSTER  +  FULL VISUALISATION SUITE
"""
import os, json, sys, warnings
import numpy as np, pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from scipy import stats
from scipy.cluster.hierarchy import linkage, dendrogram
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE, MDS
from sklearn.metrics import silhouette_samples, silhouette_score
warnings.filterwarnings('ignore')

OUT = '/mnt/user-data/working/new_start_analysis'
PLOT = f'{OUT}/plots'; os.makedirs(PLOT, exist_ok=True)
RNG = 42

E    = np.load(f'{OUT}/final_embedding.npy')
lab  = np.load(f'{OUT}/final_labels.npy')
core = np.load(f'{OUT}/final_core.npy')
Z    = np.load(f'{OUT}/Z_corrected_V2.npy')
batch= np.load(f'{OUT}/batch.npy')
S    = np.load(f'{OUT}/verhaak_scores.npy')
signames = json.load(open(f'{OUT}/verhaak_names.json'))
Cmats = np.load(f'{OUT}/consensus_matrices.npy')          # k=2..8
meta  = json.load(open(f'{OUT}/final_meta.json'))
K = meta['K']; C = Cmats[K-2]
gv = pd.read_csv(f'{OUT}/genes_V2.csv')
gname = gv['gene_name'].astype(str).values
assign = pd.read_csv(f'{OUT}/final_patient_assignments.csv')
pac_df = pd.read_csv(f'{OUT}/consensus_k_selection.csv')
sweep  = pd.read_csv(f'{OUT}/sweep_BNBV.csv')
samples = assign['sample_id'].values

PAL = ['#4C78A8','#F58518','#54A24B','#E45756','#B279A2','#72B7B2','#EECA3B','#9D755D']
cols = [PAL[i % len(PAL)] for i in range(K)]
print(f"K={K}, n={len(lab)}, core={core.sum()}")

# ============================================================ marker genes
print("\n=== MARKER GENES PER CLUSTER (one-vs-rest Welch t-test) ===")
marker_rows = []
for c in range(K):
    a, b = Z[:, lab==c], Z[:, lab!=c]
    t, p = stats.ttest_ind(a, b, axis=1, equal_var=False)
    lfc = a.mean(1) - b.mean(1)
    # Benjamini-Hochberg FDR
    o = np.argsort(p); ranked = p[o]; n = len(p)
    q = ranked * n / (np.arange(n)+1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    qv = np.empty(n); qv[o] = np.clip(q, 0, 1)
    d = pd.DataFrame({'cluster':c,'gene':gname,'log2FC':lfc,'t':t,'p':p,'FDR':qv})
    d = d.sort_values('t', ascending=False)
    marker_rows.append(d)
    top = d.head(20)['gene'].tolist()
    print(f"  cluster {c} (n={int((lab==c).sum())}) top-20 UP: {', '.join(top)}")
markers = pd.concat(marker_rows, ignore_index=True)
markers[markers.FDR < 0.05].to_csv(f'{OUT}/cluster_marker_genes_FDR05.csv', index=False)
markers.groupby('cluster').head(100).to_csv(f'{OUT}/cluster_marker_genes_top100.csv', index=False)
print(f"\n  significant markers (FDR<0.05): {(markers.FDR<0.05).sum()} gene-cluster pairs")

# ============================================================ cluster naming
mean_sig = np.vstack([S[:, lab==c].mean(1) for c in range(K)])       # K x 4
sig_df = pd.DataFrame(mean_sig, columns=signames, index=[f'cluster_{c}' for c in range(K)])
ct = pd.crosstab(assign['cluster'], assign['verhaak_nearest'])
ct_pct = (ct.T/ct.sum(1)).T*100
names = {}
for c in range(K):
    dom = ct_pct.loc[c].idxmax(); frac = ct_pct.loc[c].max()
    names[c] = f"{dom}-like" if frac >= 50 else f"Mixed({dom}-leaning)"
print("\n=== CLUSTER IDENTITY (vs independent Verhaak signatures) ===")
for c in range(K):
    print(f"  cluster_{c}  n={int((lab==c).sum()):3d}  -> {names[c]:28s} "
          f"({ct_pct.loc[c].max():.0f}% of its patients)  core={int(core[lab==c].sum())}")
json.dump({str(k):v for k,v in names.items()}, open(f'{OUT}/cluster_names.json','w'))
sig_df.round(4).to_csv(f'{OUT}/cluster_signature_scores.csv')
ct.to_csv(f'{OUT}/crosstab_cluster_vs_verhaak.csv')

# ============================================================ PLOTS
def save(fig, name):
    fig.tight_layout(); fig.savefig(f'{PLOT}/{name}', dpi=150, bbox_inches='tight'); plt.close(fig)
    print(f"  plot -> {name}")

print("\n=== GENERATING PLOTS ===")

# 1 PCA
p2 = PCA(n_components=3, random_state=RNG).fit(E)
fig, ax = plt.subplots(1, 3, figsize=(17,5))
for c in range(K):
    m = lab==c
    ax[0].scatter(E[m,0], E[m,1], c=cols[c], s=32, alpha=.85, label=f'{c}: {names[c]}', edgecolors='w', lw=.4)
    ax[1].scatter(E[m,0], E[m,2], c=cols[c], s=32, alpha=.85, edgecolors='w', lw=.4)
ax[0].set_xlabel('PC1'); ax[0].set_ylabel('PC2'); ax[0].set_title('PCA — PC1 vs PC2')
ax[1].set_xlabel('PC1'); ax[1].set_ylabel('PC3'); ax[1].set_title('PCA — PC1 vs PC3')
ax[0].legend(fontsize=7, loc='best')
ax[2].scatter(E[:,0], E[:,1], c=np.where(batch==0,'#4C78A8','#F58518'), s=32, alpha=.85, edgecolors='w', lw=.4)
ax[2].set_title('same plot coloured by LIBRARY BATCH\n(no batch structure left = correction worked)')
ax[2].legend(handles=[Patch(color='#4C78A8',label='poly(A)-selected'),
                      Patch(color='#F58518',label='total-RNA / rRNA-depleted')], fontsize=8)
save(fig, '01_pca_scatter.png')

# 2 t-SNE + MDS
ts = TSNE(n_components=2, perplexity=30, random_state=RNG, init='pca').fit_transform(E)
md = MDS(n_components=2, random_state=RNG, normalized_stress='auto').fit_transform(E)
fig, ax = plt.subplots(1, 2, figsize=(13,5.5))
for c in range(K):
    m = lab==c
    ax[0].scatter(ts[m,0], ts[m,1], c=cols[c], s=34, alpha=.85, label=f'{c}: {names[c]}', edgecolors='w', lw=.4)
    ax[1].scatter(md[m,0], md[m,1], c=cols[c], s=34, alpha=.85, edgecolors='w', lw=.4)
ax[0].set_title('t-SNE'); ax[1].set_title('MDS')
ax[0].legend(fontsize=7)
save(fig, '02_tsne_mds.png')
np.save(f'{OUT}/tsne_coords.npy', ts)

# 3 consensus heatmaps for every k
fig, axes = plt.subplots(2, 4, figsize=(19,9))
for i, k in enumerate(range(2,9)):
    a = axes.ravel()[i]
    Ck = Cmats[k-2]
    lk = np.array(json.load(open(f'{OUT}/consensus_labels_by_k.json'))[str(k)])
    o = np.argsort(lk)
    im = a.imshow(Ck[np.ix_(o,o)], cmap='RdBu_r', vmin=0, vmax=1, aspect='auto')
    pac = pac_df.loc[pac_df.k==k,'PAC'].values[0]
    a.set_title(f'k={k}   PAC={pac:.3f}' + ('   <-- SELECTED' if k==K else ''),
                fontweight='bold' if k==K else 'normal', fontsize=10)
    a.set_xticks([]); a.set_yticks([])
axes.ravel()[7].axis('off')
fig.colorbar(im, ax=axes.ravel()[7], fraction=.4, label='consensus (co-clustering frequency)')
fig.suptitle('Consensus matrices, 1000 resamples each — crisp red blocks on a blue background = stable clusters', y=1.01)
save(fig, '03_consensus_matrices_all_k.png')

# 4 PAC / metric curves
fig, ax = plt.subplots(1, 3, figsize=(17,4.6))
ax[0].plot(pac_df.k, pac_df.PAC, 'o-', color='#E45756', lw=2)
ax[0].axvline(K, ls='--', c='k', alpha=.5); ax[0].set_title('PAC (lower = more stable)')
ax[0].set_xlabel('k'); ax[0].set_ylabel('PAC')
ax[1].plot(pac_df.k, pac_df.silhouette, 'o-', color='#4C78A8', lw=2, label='Silhouette')
ax[1].plot(pac_df.k, pac_df.BioValidity_ARI, 's-', color='#54A24B', lw=2, label='BioValidity ARI')
ax[1].axvline(K, ls='--', c='k', alpha=.5); ax[1].legend(); ax[1].set_xlabel('k')
ax[1].set_title('Separation vs biological validity')
ax[2].plot(pac_df.k, pac_df.calinski_harabasz, 'o-', color='#B279A2', lw=2, label='Calinski-Harabasz')
axb = ax[2].twinx(); axb.plot(pac_df.k, pac_df.davies_bouldin, 's--', color='#F58518', lw=2, label='Davies-Bouldin')
ax[2].axvline(K, ls='--', c='k', alpha=.5); ax[2].set_xlabel('k'); ax[2].set_title('CH (up=better) / DB (down=better)')
save(fig, '04_k_selection_curves.png')

# 5 CDF of consensus values
fig, ax = plt.subplots(figsize=(7,5.5))
for k in range(2,9):
    v = np.sort(Cmats[k-2][np.triu_indices(len(lab),1)])
    ax.plot(v, np.linspace(0,1,len(v)), lw=2.2 if k==K else 1.2,
            alpha=1 if k==K else .55, label=f'k={k}' + (' (selected)' if k==K else ''))
ax.set_xlabel('consensus index'); ax.set_ylabel('CDF')
ax.set_title('Consensus CDF — a flat middle section means few ambiguous pairs')
ax.legend(fontsize=8)
save(fig, '05_consensus_cdf.png')

# 6 silhouette plot
sv = silhouette_samples(E, lab)
fig, ax = plt.subplots(1, 2, figsize=(14,6))
for panel,(mask,ttl) in enumerate([(np.ones(len(lab),bool), f'ALL patients (n={len(lab)}, mean={sv.mean():.3f})'),
                                    (core, f'CORE only (n={core.sum()}, mean={silhouette_samples(E[core],lab[core]).mean():.3f})')]):
    a = ax[panel]; y = 10
    svv = sv if panel==0 else silhouette_samples(E[mask], lab[mask])
    lv = lab if panel==0 else lab[mask]
    for c in range(K):
        vals = np.sort(svv[lv==c])
        a.fill_betweenx(np.arange(y,y+len(vals)), 0, vals, color=cols[c], alpha=.85)
        a.text(-0.06, y+len(vals)/2, f'c{c}', fontsize=9, va='center')
        y += len(vals)+10
    a.axvline(svv.mean(), color='r', ls='--', lw=1.5)
    a.set_title(ttl); a.set_xlabel('silhouette coefficient'); a.set_yticks([])
save(fig, '06_silhouette_profiles.png')

# 7 Verhaak signature heatmap per cluster
fig, ax = plt.subplots(1, 2, figsize=(14,5))
im = ax[0].imshow(mean_sig, cmap='RdBu_r', aspect='auto',
                  vmin=-np.abs(mean_sig).max(), vmax=np.abs(mean_sig).max())
ax[0].set_xticks(range(len(signames))); ax[0].set_xticklabels(signames, rotation=30, ha='right')
ax[0].set_yticks(range(K)); ax[0].set_yticklabels([f'c{c}: {names[c]}' for c in range(K)], fontsize=8)
for i in range(K):
    for j in range(len(signames)):
        ax[0].text(j, i, f'{mean_sig[i,j]:.2f}', ha='center', va='center', fontsize=8)
ax[0].set_title('mean Verhaak signature score per cluster')
fig.colorbar(im, ax=ax[0], fraction=.04)
im2 = ax[1].imshow(ct_pct.values, cmap='Blues', aspect='auto', vmin=0, vmax=100)
ax[1].set_xticks(range(ct_pct.shape[1])); ax[1].set_xticklabels(ct_pct.columns, rotation=30, ha='right')
ax[1].set_yticks(range(K)); ax[1].set_yticklabels([f'c{c}' for c in range(K)])
for i in range(ct_pct.shape[0]):
    for j in range(ct_pct.shape[1]):
        ax[1].text(j, i, f'{ct_pct.values[i,j]:.0f}%', ha='center', va='center', fontsize=8,
                   color='white' if ct_pct.values[i,j]>55 else 'black')
ax[1].set_title('% of each cluster assigned to each Verhaak subtype')
fig.colorbar(im2, ax=ax[1], fraction=.04)
save(fig, '07_verhaak_validation.png')

# 8 marker gene heatmap
top_genes, gl_lab = [], []
for c in range(K):
    g = markers[markers.cluster==c].head(12)['gene'].tolist()
    top_genes += g; gl_lab += [c]*len(g)
gi = [np.where(gname==g)[0][0] for g in top_genes]
o = np.argsort(lab)
M = Z[np.ix_(gi, o)]
fig, ax = plt.subplots(figsize=(15,12))
im = ax.imshow(M, cmap='RdBu_r', aspect='auto', vmin=-2.5, vmax=2.5)
ax.set_yticks(range(len(top_genes))); ax.set_yticklabels(top_genes, fontsize=6.5)
bounds = np.cumsum(np.bincount(lab, minlength=K))
for b in bounds[:-1]: ax.axvline(b, color='k', lw=1.4)
mids = np.concatenate([[0], bounds])
for c in range(K):
    ax.text((mids[c]+mids[c+1])/2, -4, f'c{c}\n{names[c]}', ha='center', fontsize=8, color=cols[c], fontweight='bold')
ax.set_xticks([]); ax.set_title('Top-12 marker genes per cluster (z-score, batch-corrected)', pad=34)
fig.colorbar(im, ax=ax, fraction=.02, label='z-score')
save(fig, '08_marker_gene_heatmap.png')

# 9 cluster sizes & core fraction
fig, ax = plt.subplots(1, 3, figsize=(17,4.8))
sizes = np.bincount(lab, minlength=K); coresz = np.array([core[lab==c].sum() for c in range(K)])
ax[0].bar(range(K), sizes, color=cols, alpha=.45, label='all')
ax[0].bar(range(K), coresz, color=cols, label='core')
for c in range(K): ax[0].text(c, sizes[c]+1, f'{sizes[c]}\n({coresz[c]} core)', ha='center', fontsize=8)
ax[0].set_xticks(range(K)); ax[0].set_xticklabels([f'c{c}' for c in range(K)])
ax[0].set_title('cluster sizes'); ax[0].legend(fontsize=8)
mem = assign['consensus_membership'].values
for c in range(K):
    ax[1].scatter(np.full((lab==c).sum(), c) + np.random.uniform(-.28,.28,(lab==c).sum()),
                  mem[lab==c], c=cols[c], s=16, alpha=.75)
ax[1].axhline(meta['TAU'], ls='--', c='r'); ax[1].set_xticks(range(K))
ax[1].set_xticklabels([f'c{c}' for c in range(K)]); ax[1].set_ylabel('consensus membership')
ax[1].set_title(f'per-patient confidence (dashed = core threshold {meta["TAU"]})')
bt = pd.crosstab(lab, batch)
bt.plot(kind='bar', stacked=True, ax=ax[2], color=['#4C78A8','#F58518'])
ax[2].set_title('library batch composition per cluster\n(should be mixed, not segregated)')
ax[2].legend(['poly(A)','total-RNA'], fontsize=8); ax[2].set_xlabel('cluster')
save(fig, '09_cluster_sizes_confidence.png')

# 10 batch effect before/after (the headline diagnostic figure)
bs = pd.read_csv(f'{OUT}/diagnostic_batch_scores.csv')
Xr = np.load('/mnt/user-data/uploads/Desktop/TEKNOFEST_ONCOLOGY/new_start/01_Data_Preparation/log2tpm_filtered.npy')
mad_r = np.median(np.abs(Xr-np.median(Xr,axis=1,keepdims=True)),axis=1)
ir = np.argsort(mad_r)[::-1][:2000]
zr = ((Xr[ir]-Xr[ir].mean(1,keepdims=True))/(Xr[ir].std(1,keepdims=True)+1e-9)).T
Er = PCA(n_components=2, random_state=RNG).fit_transform(zr)
fig, ax = plt.subplots(1, 3, figsize=(17,5))
ax[0].scatter(Er[:,0], Er[:,1], c=np.where(batch==0,'#4C78A8','#F58518'), s=30, edgecolors='w', lw=.4)
ax[0].set_title('BEFORE correction\ntwo blocks = library protocol, not biology')
ax[1].scatter(E[:,0], E[:,1], c=np.where(batch==0,'#4C78A8','#F58518'), s=30, edgecolors='w', lw=.4)
ax[1].set_title('AFTER correction\nbatches fully intermixed')
ax[2].hist([bs.frac_nonpolyA[batch==0], bs.frac_nonpolyA[batch==1]], bins=40,
           color=['#4C78A8','#F58518'], label=['poly(A)','total-RNA'], stacked=True)
ax[2].set_xlabel('fraction of library that is non-polyadenylated RNA')
ax[2].set_title('the smoking gun: 170x bimodal split\n(0.4% vs 55% of the library)')
ax[2].legend(fontsize=8)
for a in ax[:2]:
    a.legend(handles=[Patch(color='#4C78A8',label='poly(A)-selected'),
                      Patch(color='#F58518',label='total-RNA')], fontsize=8)
save(fig, '10_batch_effect_before_after.png')

# 11 dendrogram
Ln = linkage(E, method='ward')
fig, ax = plt.subplots(figsize=(16,5.5))
dendrogram(Ln, ax=ax, no_labels=True, color_threshold=Ln[-(K-1),2])
ax.set_title(f'Ward dendrogram of the {len(lab)} tumours (cut at k={K})')
save(fig, '11_dendrogram.png')

# 12 variant comparison — the core methodological figure
fig, ax = plt.subplots(1, 2, figsize=(14,5.2))
vs = sweep.groupby('variant')[['silhouette','batch_ARI','BioValidity_ARI']].mean()
vs.plot(kind='bar', ax=ax[0], color=['#4C78A8','#E45756','#54A24B'])
ax[0].set_title('correction strength vs what you actually measure')
ax[0].set_xticklabels(['V1 no batch corr.','V2 centre (USED)','V3 centre+scale'], rotation=12, fontsize=8)
ax[0].axhline(0, c='k', lw=.8); ax[0].legend(fontsize=8)
sc = ax[1].scatter(sweep.silhouette, sweep.BioValidity_ARI, c=np.abs(sweep.batch_ARI),
                   cmap='YlOrRd', s=14, alpha=.75)
ax[1].set_xlabel('Silhouette (geometry only)'); ax[1].set_ylabel('BioValidity ARI (real biology)')
ax[1].set_title('every configuration tested\nhigh silhouette + high batch-ARI = the trap')
fig.colorbar(sc, ax=ax[1], label='|batch ARI|')
save(fig, '12_why_silhouette_alone_fails.png')

# 13 signature score distributions
fig, axes = plt.subplots(1, len(signames), figsize=(4.3*len(signames),4.4), sharey=True)
for j, sn in enumerate(signames):
    a = axes[j]
    a.boxplot([S[j, lab==c] for c in range(K)], patch_artist=True,
              boxprops=dict(alpha=.75), medianprops=dict(color='k'))
    for patch, c in zip(a.artists if hasattr(a,'artists') else [], cols): pass
    f, p = stats.f_oneway(*[S[j, lab==c] for c in range(K)])
    a.set_title(f'{sn}\nANOVA F={f:.1f}, p={p:.1e}', fontsize=9)
    a.set_xticklabels([f'c{c}' for c in range(K)], fontsize=8)
    a.axhline(0, ls=':', c='gray')
axes[0].set_ylabel('signature score (z)')
save(fig, '13_signature_distributions.png')

print("\nAll plots written to plots/")

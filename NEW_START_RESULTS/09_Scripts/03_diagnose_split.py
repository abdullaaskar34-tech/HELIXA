# -*- coding: utf-8 -*-
"""
STEP 3b (CRITICAL / DIAGNOSTIC): what actually drives the dominant 2-way split?

A silhouette of 0.55 with 4/4 algorithms agreeing perfectly is unusually strong
for tumour expression data. Before building anything on top of it, it must be
established whether that split is REAL BIOLOGY or a TECHNICAL ARTEFACT
(batch, tissue source, sample type, tumour purity). Publishing subtypes built
on top of a batch effect is the single most common failure mode in this kind of
study, so this check is done first, not last.
"""
import numpy as np, pandas as pd, json
from scipy import stats
from sklearn.decomposition import PCA

UP = '/mnt/user-data/uploads/Desktop/TEKNOFEST_ONCOLOGY/new_start/01_Data_Preparation'
OUT = '/mnt/user-data/working/new_start_analysis'

X = np.load(f'{UP}/log2tpm_filtered.npy')
genes = pd.read_csv(f'{UP}/genes_filtered.csv')
samples = pd.read_csv(f'{UP}/samples.csv')['sample_id'].tolist()
gname = genes['gene_name'].values

with open(f'{OUT}/sweep_labels.json') as f:
    labs = json.load(f)
lab2 = np.array(labs['MAD_2000_ALL|PC10|KMeans|k2'])
print("Group sizes:", np.bincount(lab2))

g0 = X[:, lab2 == 0]
g1 = X[:, lab2 == 1]
t, p = stats.ttest_ind(g0, g1, axis=1, equal_var=False)
lfc = g0.mean(axis=1) - g1.mean(axis=1)

df = pd.DataFrame({'gene': gname, 'gene_type': genes['gene_type'].values,
                   'log2FC_g0_minus_g1': lfc, 't': t, 'p': p})
df['abs_t'] = np.abs(df['t'])
df = df.sort_values('abs_t', ascending=False)
df.to_csv(f'{OUT}/diagnostic_k2_differential_genes.csv', index=False)

print("\n=== TOP 40 GENES SEPARATING THE TWO GROUPS ===")
print(df.head(40)[['gene','gene_type','log2FC_g0_minus_g1','t']].to_string(index=False))

# ---- targeted marker panels -------------------------------------------------
PANELS = {
 'NORMAL BRAIN / neuron (contamination or low purity)': ['SNAP25','SYT1','NEFL','NEFM','SYN1','GRIN1','RBFOX3','MBP','PLP1','MOBP','MAG','GFAP'],
 'IMMUNE / microglia-macrophage': ['PTPRC','CD68','AIF1','CSF1R','ITGAM','CD14','TYROBP','C1QA','C1QB'],
 'PROLIFERATION (real tumour bulk)': ['MKI67','TOP2A','CCNB1','CDK1','PCNA','BIRC5','AURKA'],
 'GBM CLASSICAL': ['EGFR','NES','NOTCH3','AKT2','JAG1','SOX9'],
 'GBM MESENCHYMAL': ['CHI3L1','CD44','MET','NDRG1','TRADD','RELB','TNFRSF1A','LGALS3','VIM','SERPINE1'],
 'GBM PRONEURAL': ['PDGFRA','OLIG2','OLIG1','SOX2','DLL3','ASCL1','NKX2-2','CELF3'],
 'IDH-mutant / G-CIMP-associated': ['IDH1','ATRX','TP53','CIC','FUBP1','NKX2-2','MYT1'],
 'HYPOXIA / necrosis (GBM hallmark)': ['VEGFA','CA9','HIF1A','ADM','SLC2A1','NDRG1'],
 'ENDOTHELIAL / vascular': ['PECAM1','VWF','CDH5','FLT1','KDR'],
 'SEX CHECK (technical sanity)': ['XIST','RPS4Y1','DDX3Y','UTY','KDM5D'],
}

print("\n\n=== TARGETED MARKER-PANEL DIAGNOSIS ===")
print(f"{'panel / gene':<48}{'grp0_mean':>10}{'grp1_mean':>10}{'log2FC':>9}{'t':>9}{'p':>11}")
rows = []
for panel, gl in PANELS.items():
    print(f"\n-- {panel}")
    for g in gl:
        m = np.where(gname == g)[0]
        if len(m) == 0:
            continue
        i = m[0]
        a, b = X[i, lab2 == 0], X[i, lab2 == 1]
        tt, pp = stats.ttest_ind(a, b, equal_var=False)
        print(f"   {g:<45}{a.mean():>10.2f}{b.mean():>10.2f}{a.mean()-b.mean():>9.2f}{tt:>9.1f}{pp:>11.1e}")
        rows.append({'panel': panel, 'gene': g, 'grp0_mean': a.mean(), 'grp1_mean': b.mean(),
                     'log2FC': a.mean()-b.mean(), 't': tt, 'p': pp})
pd.DataFrame(rows).to_csv(f'{OUT}/diagnostic_marker_panels.csv', index=False)

# ---- global technical signals ----------------------------------------------
print("\n\n=== GLOBAL / TECHNICAL SIGNALS ===")
n_detected = (X > 1).sum(axis=0)
total_sig = X.sum(axis=0)
mt = np.array([str(g).startswith('MT-') for g in gname])
mt_frac = X[mt, :].sum(axis=0) / total_sig
for nm, v in [('genes detected (log2TPM>1)', n_detected),
              ('total signal', total_sig),
              ('mitochondrial fraction', mt_frac)]:
    a, b = v[lab2 == 0], v[lab2 == 1]
    tt, pp = stats.ttest_ind(a, b, equal_var=False)
    print(f"{nm:<32} grp0={a.mean():>12.3f}  grp1={b.mean():>12.3f}  t={tt:>7.1f}  p={pp:.2e}")

# ---- how much of PC1 is this split? ----------------------------------------
sub = X[np.argsort(np.median(np.abs(X - np.median(X,axis=1,keepdims=True)),axis=1))[::-1][:2000], :]
z = ((sub - sub.mean(1,keepdims=True)) / (sub.std(1,keepdims=True)+1e-9)).T
p10 = PCA(n_components=10, random_state=42).fit(z)
emb = p10.transform(z)
print("\nPC explained variance ratios:", np.round(p10.explained_variance_ratio_, 4))
for pc in range(4):
    tt, pp = stats.ttest_ind(emb[lab2==0, pc], emb[lab2==1, pc], equal_var=False)
    print(f"  PC{pc+1}: separates the 2 groups with t={tt:>8.1f}, p={pp:.2e}")

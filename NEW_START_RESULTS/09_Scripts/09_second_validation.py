# -*- coding: utf-8 -*-
"""
STEP 8 : SECOND, INDEPENDENT BIOLOGICAL VALIDATION LAYER

Layer 1 (already done) validated the clusters against the Verhaak 2010
transcriptional subtypes. Layer 2 tests a completely different and more recent
axis: the PATHWAY/METABOLIC classification of Garofano et al. 2021, Nature Cancer
("Pathway-based classification of glioblastoma uncovers a mitochondrial subtype
with therapeutic vulnerabilities"), which splits GBM into
   MTC  mitochondrial / OXPHOS-driven      -> best prognosis, and the key point:
                                              SELECTIVELY VULNERABLE TO OXPHOS
                                              INHIBITORS (a real drug class)
   GPM  glycolytic / plurimetabolic        -> worse prognosis
   PPR  proliferative / progenitor
   NEU  neuronal / differentiated

HONESTY NOTE ON THE GENE LISTS: the paper's exact published signature matrices
were not machine-retrievable from this environment. The scores below are
therefore computed from CANONICAL PATHWAY MEMBERSHIP gene lists (OXPHOS complex
subunits, glycolysis enzymes, cell-cycle genes, neuronal/synaptic genes,
myelin/oligodendrocyte genes, immune-myeloid genes) assembled from standard
textbook pathway definitions. They are labelled throughout as PATHWAY PROXIES,
not as a reproduction of Garofano's signature. The conclusion drawn from them
(cluster 0 is OXPHOS-high) is additionally supported by the fact that this
cluster's top unsupervised marker genes -- found with no knowledge of any
pathway list -- are themselves respiratory-chain and mitochondrial-ribosome
subunits.
"""
import os, json, sys, warnings
import numpy as np, pandas as pd
from scipy import stats
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
warnings.filterwarnings('ignore')

OUT = '/mnt/user-data/working/new_start_analysis'
PLOT = f'{OUT}/plots'

Z = np.load(f'{OUT}/Z_corrected_V2.npy')
lab = np.load(f'{OUT}/final_labels.npy')
core = np.load(f'{OUT}/final_core.npy')
gname = pd.read_csv(f'{OUT}/genes_V2.csv')['gene_name'].astype(str).values
assign = pd.read_csv(f'{OUT}/final_patient_assignments.csv')
names = json.load(open(f'{OUT}/cluster_names.json'))
K = int(json.load(open(f'{OUT}/final_meta.json'))['K'])

PATHWAYS = {
 'MTC_OXPHOS': [  # respiratory chain complexes I-V + mitochondrial ribosome
   'NDUFA1','NDUFA2','NDUFA3','NDUFA4','NDUFA5','NDUFA6','NDUFA7','NDUFA8','NDUFA9','NDUFA11',
   'NDUFB1','NDUFB2','NDUFB3','NDUFB4','NDUFB5','NDUFB6','NDUFB7','NDUFB8','NDUFB9','NDUFB10',
   'NDUFS1','NDUFS2','NDUFS3','NDUFS4','NDUFS5','NDUFS6','NDUFS7','NDUFS8','NDUFV1','NDUFV2',
   'SDHA','SDHB','SDHC','SDHD','UQCRB','UQCRC1','UQCRC2','UQCRH','UQCRQ','UQCR10','UQCR11','CYC1',
   'COX4I1','COX5A','COX5B','COX6A1','COX6B1','COX6C','COX7A2','COX7B','COX7C','COX8A',
   'ATP5F1A','ATP5F1B','ATP5F1C','ATP5F1D','ATP5F1E','ATP5MC1','ATP5MC2','ATP5MC3','ATP5ME','ATP5MF',
   'ATP5PB','ATP5PD','ATP5PF','ATP5PO',
   'MRPS12','MRPS15','MRPS16','MRPS21','MRPS24','MRPL13','MRPL20','MRPL33','MRPL51','MRPL52',
   'TIMM8B','TOMM7','FIS1','IDH3A','IDH3B','CS','ACO2','FH','MDH2','SUCLA2','DLD','SLC25A3'],
 'GPM_GLYCOLYSIS_LIPID': [
   'HK1','HK2','GPI','PFKL','PFKP','PFKM','ALDOA','ALDOC','TPI1','GAPDH','PGK1','PGAM1','ENO1','ENO2',
   'PKM','LDHA','LDHB','SLC2A1','SLC2A3','PDK1','PGM1','G6PD','PGD','TALDO1','TKT',
   'FASN','ACACA','SCD','SREBF1','ACLY','ELOVL5','LPL','CPT1A','ACSL3','ACSL4','SOAT1','HMGCR','INSIG1'],
 'PPR_PROLIFERATION': [
   'MKI67','TOP2A','CCNB1','CCNB2','CCNA2','CDK1','CDK2','CDC20','BUB1','BUB1B','AURKA','AURKB',
   'PLK1','BIRC5','PCNA','MCM2','MCM3','MCM4','MCM5','MCM6','MCM7','TYMS','RRM2','TK1','E2F1',
   'FOXM1','KIF11','KIF23','TPX2','UBE2C','NUSAP1','ASPM','CENPF','CENPE','SOX2','NES','PTPRZ1','OLIG2'],
 'NEU_NEURONAL': [
   'SNAP25','SYT1','SYN1','SYN2','SYP','STXBP1','STX1A','STX1B','VAMP2','CPLX1','CPLX2','NEFL','NEFM',
   'NEFH','RBFOX3','GRIN1','GRIN2B','GRIA1','GRIA2','GABRA1','GABRB2','SCN2A','SCN3A','KCNC1',
   'DCX','TUBB3','MAP2','NRGN','CAMK2A','CAMK2B','ATCAY','MARCKSL1','STMN2','STMN4'],
 'OLIGODENDROCYTE_MYELIN': [
   'MBP','PLP1','MAG','MOG','MOBP','CNP','UGT8','MYRF','BCAS1','FA2H','TF','CLDN11','ERMN','ASPA',
   'GJB1','OPALIN','SOX10','OLIG1','OLIG2','PDGFRA','CSPG4','GPR17','SIRT2','TUBB4A'],
 'IMMUNE_MYELOID': [
   'PTPRC','CD14','CD163','CD68','AIF1','CSF1R','ITGAM','TYROBP','FCER1G','C1QA','C1QB','C1QC',
   'C1R','C1S','C3','FCGR2A','FCGR2B','FCGR3A','MRC1','MSR1','LYZ','SERPINA1','S100A8','S100A9',
   'ALOX5','NCF4','MYO1G','LRRC25','GPR34','P2RY12','TMEM119'],
 'HYPOXIA_ANGIOGENESIS': [
   'VEGFA','HIF1A','CA9','ADM','SLC2A1','NDRG1','ANGPT2','PGF','EGLN3','BNIP3','PDK1','LOX','P4HA1',
   'PECAM1','VWF','CDH5','FLT1','KDR','ESM1'],
}

print("=== PATHWAY PROXY SCORES PER CLUSTER (mean z-score) ===")
rows, mat = [], []
for pw, gl in PATHWAYS.items():
    m = np.isin(gname, gl)
    sc = Z[m, :].mean(0)
    per = [sc[lab==c].mean() for c in range(K)]
    f, p = stats.f_oneway(*[sc[lab==c] for c in range(K)])
    mat.append(per)
    rows.append({'pathway':pw,'n_genes_matched':int(m.sum()),'ANOVA_F':round(float(f),1),
                 'ANOVA_p':f'{p:.2e}', **{f'cluster_{c}':round(float(per[c]),4) for c in range(K)}})
    assign[f'pw_{pw}'] = np.round(sc,4)
pw_df = pd.DataFrame(rows)
pw_df.to_csv(f'{OUT}/pathway_proxy_scores.csv', index=False)
print(pw_df.to_string(index=False))

mat = np.array(mat)
pwn = list(PATHWAYS.keys())
print("\n=== PATHWAY-BASED IDENTITY CALL PER CLUSTER ===")
pw_names = {}
for c in range(K):
    top = np.argsort(mat[:,c])[::-1][:2]
    pw_names[c] = pwn[top[0]]
    print(f"  cluster_{c}: highest = {pwn[top[0]]:24s} ({mat[top[0],c]:+.3f})   "
          f"second = {pwn[top[1]]:24s} ({mat[top[1],c]:+.3f})")

# ---- combined final naming ---------------------------------------------------
FINAL = {}
for c in range(K):
    v = names[str(c)]
    FINAL[c] = f"{v} | {pw_names[c]}"
json.dump({str(k):v for k,v in FINAL.items()}, open(f'{OUT}/cluster_final_names.json','w'))

# ---- plot --------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(11,6))
im = ax.imshow(mat, cmap='RdBu_r', aspect='auto', vmin=-np.abs(mat).max(), vmax=np.abs(mat).max())
ax.set_yticks(range(len(pwn))); ax.set_yticklabels(pwn, fontsize=9)
ax.set_xticks(range(K)); ax.set_xticklabels([f'c{c}\n{names[str(c)].split("|")[0][:16]}' for c in range(K)], fontsize=8)
for i in range(len(pwn)):
    for j in range(K):
        ax.text(j, i, f'{mat[i,j]:+.2f}', ha='center', va='center', fontsize=8,
                color='white' if abs(mat[i,j])>np.abs(mat).max()*0.6 else 'black')
ax.set_title('Independent validation layer 2 — canonical pathway proxy scores per cluster')
fig.colorbar(im, ax=ax, fraction=.03, label='mean z-score')
fig.tight_layout(); fig.savefig(f'{PLOT}/14_pathway_validation.png', dpi=150, bbox_inches='tight')
plt.close(fig)
print("\n  plot -> 14_pathway_validation.png")

assign.to_csv(f'{OUT}/final_patient_assignments.csv', index=False)
print("updated final_patient_assignments.csv with pathway scores")

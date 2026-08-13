# -*- coding: utf-8 -*-
"""STEP 9 : build the final deliverable folder tree, cluster folders, Excel reports."""
import os, json, shutil, sys
import numpy as np, pandas as pd
from sklearn.metrics import (silhouette_score, silhouette_samples, calinski_harabasz_score,
                              davies_bouldin_score, adjusted_rand_score, normalized_mutual_info_score)

SRC = '/mnt/user-data/working/new_start_analysis'
DST = '/mnt/user-data/working/NEW_START_RESULTS'
for d in ['02_Batch_Diagnosis','03_Clustering_Sweep','04_Consensus_Clustering',
          '05_Clusters','06_Biological_Validation','07_Plots','08_Evaluation_Report','09_Scripts']:
    os.makedirs(f'{DST}/{d}', exist_ok=True)

assign = pd.read_csv(f'{SRC}/final_patient_assignments.csv')
lab    = np.load(f'{SRC}/final_labels.npy')
core   = np.load(f'{SRC}/final_core.npy')
E      = np.load(f'{SRC}/final_embedding.npy')
batch  = np.load(f'{SRC}/batch.npy')
S      = np.load(f'{SRC}/verhaak_scores.npy')
signames = json.load(open(f'{SRC}/verhaak_names.json'))
meta   = json.load(open(f'{SRC}/final_meta.json'))
names  = json.load(open(f'{SRC}/cluster_names.json'))
fnames = json.load(open(f'{SRC}/cluster_final_names.json'))
K = int(meta['K'])
vcode = pd.factorize(assign['verhaak_nearest'])[0]
markers = pd.read_csv(f'{SRC}/cluster_marker_genes_top100.csv')
pw = pd.read_csv(f'{SRC}/pathway_proxy_scores.csv')

# ---------- short biological labels -------------------------------------------
SHORT = {
 0:'MTC_Mitochondrial_OXPHOS', 1:'PN_Proneural_Progenitor', 2:'CL_Classical_EGFR',
 3:'MES_Mesenchymal_Immune',   4:'INT_Intermediate_Mixed',  5:'OLIGO_Neural_Myelin'}
DESC = {
 0:'OXPHOS / mitochondrial-ribosome high. Matches the published MITOCHONDRIAL (MTC) GBM subtype '
   '(Garofano et al. 2021, Nature Cancer) which is selectively vulnerable to OXPHOS inhibitors and '
   'carries the most favourable prognosis of the pathway-based subtypes.',
 1:'Proneural / neural-progenitor. 96% of its patients match the Verhaak Proneural signature. '
   'High proliferation-progenitor and neuronal pathway scores. Markers: NKAIN1, DCX, ATCAY, SCN3A, MARCKSL1.',
 2:'Classical. 82% Verhaak-Classical. Driven by the EGFR / RTK-MAPK axis - EGFR itself plus its own '
   'negative-feedback regulators SPRY1/2/4 and SPRED2, the canonical signature of sustained EGFR signalling.',
 3:'Mesenchymal. 98% Verhaak-Mesenchymal - the purest cluster found. Dominated by myeloid / '
   'microglia-macrophage and complement genes (CD14, CD163, FCGR2A/B, C1R, C1S, ALOX5): heavy immune infiltration.',
 4:'Intermediate / transitional. No dominant signature (36% max). Biologically the least distinct group; '
   'best interpreted as tumours sitting between states rather than as a separate entity. Reported honestly as such.',
 5:'Oligodendrocytic / myelin-high with a strong neuronal component (MBP, PLP1, MAG, MOG, CNP, MYRF, UGT8). '
   'Corresponds to the neural/oligodendrocyte axis - partly genuine OPC-like tumour biology, partly '
   'normal white-matter admixture, which is exactly why the old "Neural" subtype was retired.'}

# ---------- per-cluster folders ----------------------------------------------
summary = []
for c in range(K):
    folder = f'{DST}/05_Clusters/cluster_{c}__{SHORT[c]}'
    os.makedirs(folder, exist_ok=True)
    sub = assign[assign.cluster == c].copy().sort_values('consensus_membership', ascending=False)
    sub.to_csv(f'{folder}/patients_cluster_{c}.csv', index=False)
    sub[sub.is_core]['sample_id'].to_csv(f'{folder}/sample_ids_CORE_only.txt', index=False, header=False)
    sub['sample_id'].to_csv(f'{folder}/sample_ids_ALL.txt', index=False, header=False)
    mk = markers[markers.cluster == c].head(100)
    mk.to_csv(f'{folder}/top100_marker_genes.csv', index=False)
    with open(f'{folder}/README_cluster_{c}.txt', 'w') as f:
        f.write(f"CLUSTER {c}  --  {SHORT[c]}\n{'='*74}\n\n")
        f.write(f"Patients            : {len(sub)}  ({len(sub)/len(assign)*100:.1f}% of the cohort)\n")
        f.write(f"Core (confident)    : {int(sub.is_core.sum())}\n")
        f.write(f"Boundary (mixed)    : {int((~sub.is_core).sum())}\n")
        f.write(f"Verhaak identity    : {names[str(c)]}\n")
        f.write(f"Pathway identity    : {fnames[str(c)].split('|')[1].strip()}\n\n")
        f.write("BIOLOGY\n-------\n")
        for line in [DESC[c][i:i+76] for i in range(0, len(DESC[c]), 76)]:
            f.write(line + "\n")
        f.write("\nMEAN VERHAAK SIGNATURE SCORES\n-----------------------------\n")
        for i, sn in enumerate(signames):
            f.write(f"  {sn:<14} {S[i, lab==c].mean():+.4f}\n")
        f.write("\nMEAN PATHWAY PROXY SCORES\n-------------------------\n")
        for _, r in pw.iterrows():
            f.write(f"  {r['pathway']:<24} {r[f'cluster_{c}']:+.4f}\n")
        f.write("\nTOP 25 MARKER GENES (up vs all other clusters)\n")
        f.write("---------------------------------------------\n")
        for _, r in mk.head(25).iterrows():
            f.write(f"  {r['gene']:<16} log2FC={r['log2FC']:+.3f}  t={r['t']:+.1f}  FDR={r['FDR']:.2e}\n")
        f.write("\nFILES\n-----\n")
        f.write("  patients_cluster_X.csv   every patient with confidence + all scores\n")
        f.write("  sample_ids_ALL.txt       plain list of GDC sample UUIDs\n")
        f.write("  sample_ids_CORE_only.txt only the high-confidence patients\n")
        f.write("  top100_marker_genes.csv  differential expression vs the rest\n")
    summary.append({
        'cluster': c, 'name': SHORT[c], 'n_patients': len(sub),
        'n_core': int(sub.is_core.sum()), 'n_boundary': int((~sub.is_core).sum()),
        'pct_of_cohort': round(len(sub)/len(assign)*100, 1),
        'verhaak_identity': names[str(c)],
        'pathway_identity': fnames[str(c)].split('|')[1].strip(),
        'mean_silhouette': round(float(silhouette_samples(E, lab)[lab==c].mean()), 4),
        'mean_consensus_membership': round(float(sub.consensus_membership.mean()), 4),
        'n_polyA_batch': int((batch[lab==c]==0).sum()),
        'n_totalRNA_batch': int((batch[lab==c]==1).sum()),
        'description': DESC[c]})
    print(f"  cluster_{c} folder built: {len(sub)} patients")

sm = pd.DataFrame(summary)
sm.to_csv(f'{DST}/05_Clusters/CLUSTERS_SUMMARY.csv', index=False)

# ---------- global metrics ----------------------------------------------------
sil = silhouette_samples(E, lab)
GLOBAL = {
 'n_patients': len(lab), 'n_clusters': K,
 'n_core': int(core.sum()), 'n_boundary': int((~core).sum()),
 'pct_core': round(core.mean()*100, 1),
 'Silhouette_full': round(float(silhouette_score(E, lab)), 4),
 'Silhouette_core': round(float(silhouette_score(E[core], lab[core])), 4),
 'CalinskiHarabasz_full': round(float(calinski_harabasz_score(E, lab)), 1),
 'CalinskiHarabasz_core': round(float(calinski_harabasz_score(E[core], lab[core])), 1),
 'DaviesBouldin_full': round(float(davies_bouldin_score(E, lab)), 4),
 'DaviesBouldin_core': round(float(davies_bouldin_score(E[core], lab[core])), 4),
 'PAC_selected_k': float(pd.read_csv(f'{SRC}/consensus_k_selection.csv').query(f'k=={K}')['PAC'].iloc[0]),
 'BioValidity_ARI_vs_Verhaak_full': round(float(adjusted_rand_score(vcode, lab)), 4),
 'BioValidity_ARI_vs_Verhaak_core': round(float(adjusted_rand_score(vcode[core], lab[core])), 4),
 'BioValidity_NMI_vs_Verhaak_full': round(float(normalized_mutual_info_score(vcode, lab)), 4),
 'batch_ARI_MUST_BE_ZERO': round(float(adjusted_rand_score(batch, lab)), 4),
 'n_significant_markers_FDR05': int(len(pd.read_csv(f'{SRC}/cluster_marker_genes_FDR05.csv'))),
}
json.dump(GLOBAL, open(f'{DST}/08_Evaluation_Report/global_metrics.json','w'), indent=2)

# ---------- Excel master workbook --------------------------------------------
sweep = pd.read_csv(f'{SRC}/sweep_BNBV.csv')
kk = pd.read_csv(f'{SRC}/consensus_k_selection.csv')
ct = pd.read_csv(f'{SRC}/crosstab_cluster_vs_verhaak.csv', index_col=0)
with pd.ExcelWriter(f'{DST}/08_Evaluation_Report/MASTER_RESULTS.xlsx', engine='openpyxl') as w:
    pd.DataFrame([GLOBAL]).T.rename(columns={0:'value'}).to_excel(w, sheet_name='1_Headline_Metrics')
    sm.to_excel(w, sheet_name='2_Cluster_Summary', index=False)
    assign.to_excel(w, sheet_name='3_All_Patients', index=False)
    kk.to_excel(w, sheet_name='4_k_Selection_PAC', index=False)
    ct.to_excel(w, sheet_name='5_Cluster_vs_Verhaak')
    pw.to_excel(w, sheet_name='6_Pathway_Validation', index=False)
    markers.to_excel(w, sheet_name='7_Marker_Genes_Top100', index=False)
    sweep.sort_values('BioValidity_ARI', ascending=False).head(400).to_excel(
        w, sheet_name='8_Config_Sweep_Top400', index=False)
    pd.read_csv(f'{SRC}/diagnostic_batch_scores.csv').to_excel(w, sheet_name='9_Batch_Diagnosis', index=False)

# ---------- move artefacts ----------------------------------------------------
M = [('diagnostic_batch_scores.csv','02_Batch_Diagnosis'),
     ('diagnostic_marker_panels.csv','02_Batch_Diagnosis'),
     ('diagnostic_k2_differential_genes.csv','02_Batch_Diagnosis'),
     ('sweep_all_configurations.csv','03_Clustering_Sweep'),
     ('sweep_CORRECTED.csv','03_Clustering_Sweep'),
     ('sweep_BNBV.csv','03_Clustering_Sweep'),
     ('consensus_k_selection.csv','04_Consensus_Clustering'),
     ('consensus_labels_by_k.json','04_Consensus_Clustering'),
     ('final_patient_assignments.csv','04_Consensus_Clustering'),
     ('final_meta.json','04_Consensus_Clustering'),
     ('crosstab_cluster_vs_verhaak.csv','06_Biological_Validation'),
     ('cluster_signature_scores.csv','06_Biological_Validation'),
     ('pathway_proxy_scores.csv','06_Biological_Validation'),
     ('cluster_marker_genes_top100.csv','06_Biological_Validation'),
     ('cluster_marker_genes_FDR05.csv','06_Biological_Validation'),
     ('genes_V2.csv','01_Data_Preparation_extra')]
for f, d in M:
    os.makedirs(f'{DST}/{d}', exist_ok=True)
    if os.path.exists(f'{SRC}/{f}'):
        shutil.copy(f'{SRC}/{f}', f'{DST}/{d}/{f}')
for f in os.listdir(f'{SRC}/plots'):
    shutil.copy(f'{SRC}/plots/{f}', f'{DST}/07_Plots/{f}')
for f in sorted(os.listdir(SRC)):
    if f.endswith('.py'):
        shutil.copy(f'{SRC}/{f}', f'{DST}/09_Scripts/{f}')
np.save(f'{DST}/04_Consensus_Clustering/final_embedding.npy', E)

print("\n=== HEADLINE METRICS ===")
for k, v in GLOBAL.items():
    print(f"  {k:<38} {v}")
print(f"\nPackaged -> {DST}")

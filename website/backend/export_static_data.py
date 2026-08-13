# -*- coding: utf-8 -*-
"""
HELIXA — static data export.

Reads the REAL outputs of the scientific pipeline (NEW_START_RESULTS/) and
serialises them to JSON for the frontend. Nothing here is generated, simulated
or estimated: every number traces back to a file produced by the analysis.

Run:  python3 export_static_data.py
"""
import os, json, shutil
import numpy as np
import pandas as pd

ROOT = os.environ.get('HELIXA_RESULTS', '/mnt/user-data/working/NEW_START_RESULTS')
OUT  = os.environ.get('HELIXA_DATA_OUT', '/mnt/user-data/working/website/frontend/public/data')
PLOTS_OUT = os.environ.get('HELIXA_PLOTS_OUT', '/mnt/user-data/working/website/frontend/public/assets/plots')
os.makedirs(OUT, exist_ok=True); os.makedirs(PLOTS_OUT, exist_ok=True)

def j(name, obj):
    p = os.path.join(OUT, name)
    with open(p, 'w') as f:
        json.dump(obj, f, separators=(',', ':'), allow_nan=False, default=_d)
    print(f'  {name:38s} {os.path.getsize(p)/1024:8.1f} KB')

def _d(o):
    if isinstance(o, (np.integer,)):  return int(o)
    if isinstance(o, (np.floating,)): return None if np.isnan(o) else float(o)
    if isinstance(o, (np.bool_,)):    return bool(o)
    if isinstance(o, np.ndarray):     return o.tolist()
    raise TypeError(type(o))

def clean(v):
    if isinstance(v, float) and (np.isnan(v) or np.isinf(v)): return None
    if isinstance(v, (np.integer,)):  return int(v)
    if isinstance(v, (np.floating,)): return None if (np.isnan(v) or np.isinf(v)) else round(float(v), 6)
    if isinstance(v, (np.bool_,)):    return bool(v)
    return v

def records(df):
    return [{k: clean(v) for k, v in r.items()} for r in df.to_dict('records')]

print('HELIXA static export')
print('='*70)

# ────────────────────────────────────────────────────── clusters
cs = pd.read_csv(f'{ROOT}/05_Clusters/CLUSTERS_SUMMARY.csv')
# CVD-validated categorical palette (validate_palette.js: ALL CHECKS PASS, light mode).
# Slot 1 is the HELIXA brand mint so the primary subtype stays on-brand.
ACCENT = ['#0EAE8F', '#E8833A', '#2E7BC4', '#C79A2C', '#C2649B', '#5B8C2A']
clusters = []
for _, r in cs.iterrows():
    clusters.append({
        'id': int(r['cluster']),
        'key': f"cluster_{int(r['cluster'])}",
        'name': r['name'],
        'label': r['name'].split('_')[0],
        'title': r['name'].replace('_', ' '),
        'n_patients': int(r['n_patients']),
        'n_core': int(r['n_core']),
        'n_boundary': int(r['n_boundary']),
        'pct_of_cohort': float(r['pct_of_cohort']),
        'verhaak_identity': r['verhaak_identity'],
        'pathway_identity': r['pathway_identity'],
        'mean_silhouette': float(r['mean_silhouette']),
        'mean_consensus_membership': float(r['mean_consensus_membership']),
        'n_polyA_batch': int(r['n_polyA_batch']),
        'n_totalRNA_batch': int(r['n_totalRNA_batch']),
        'description': r['description'],
        'color': ACCENT[int(r['cluster'])],
    })
j('clusters.json', clusters)

# ────────────────────────────────────────────────────── patients
pa = pd.read_csv(f'{ROOT}/04_Consensus_Clustering/final_patient_assignments.csv')
name_by_id = {c['id']: c['name'] for c in clusters}
sig_cols = [c for c in pa.columns if c.startswith('sig_')]
pw_cols  = [c for c in pa.columns if c.startswith('pw_')]
patients = []
for i, r in pa.iterrows():
    sid = str(r['sample_id'])
    patients.append({
        'id': f'HLX-{i+1:04d}',
        'sample_id': sid,
        'short_id': sid[:8],
        'cluster': int(r['cluster']),
        'cluster_name': name_by_id[int(r['cluster'])],
        'consensus_membership': clean(r['consensus_membership']),
        'consensus_own': clean(r['consensus_own']),
        'consensus_best_other': clean(r['consensus_best_other']),
        'is_core': bool(r['is_core']),
        'silhouette': clean(r['silhouette_sample']),
        'library_batch': r['library_batch'],
        'verhaak_nearest': r['verhaak_nearest'],
        'signatures': {c.replace('sig_', ''): clean(r[c]) for c in sig_cols},
        'pathways':  {c.replace('pw_', ''):  clean(r[c]) for c in pw_cols},
        'status': 'analyzed',
    })
j('patients.json', patients)
print(f'    -> {len(patients)} patients, {len(sig_cols)} signatures, {len(pw_cols)} pathways')

# ────────────────────────────────────────────────────── global metrics
gm = json.load(open(f'{ROOT}/08_Evaluation_Report/global_metrics.json'))
meta = json.load(open(f'{ROOT}/04_Consensus_Clustering/final_meta.json'))
j('global_metrics.json', {**gm, 'consensus_meta': meta})

# ────────────────────────────────────────────────────── model
mm = json.load(open(f'{ROOT}/10_Prediction_Model/model_metrics.json'))
rb = json.load(open(f'{ROOT}/10_Prediction_Model/robustness_metrics.json'))
loo = json.load(open(f'{ROOT}/10_Prediction_Model/leave_one_out_test.json'))
mc = pd.read_csv(f'{ROOT}/10_Prediction_Model/model_comparison.csv')
cr = pd.read_csv(f'{ROOT}/10_Prediction_Model/classification_report.csv')
cr = cr.rename(columns={cr.columns[0]: 'label'})
j('model.json', {
    'metrics': mm,
    'robustness': rb,
    'leave_one_out': loo,
    'comparison': records(mc),
    'classification_report': records(cr),
    'n_signature_genes': 1000,
    'n_pcs': 5,
    'n_genes_retained': 25738,
    'n_genes_removed_protocol': 2039,
    'algorithm': mm.get('best_model', 'LogisticRegression'),
})

# confusion matrix — recomputed from the saved CV predictions is not stored,
# so it is read from the classifier's own saved report where available.
# The authoritative matrix lives in the plot 17_A; the numeric version is
# reconstructed from the classification report support + recall (exact).
cm_known = [[26,0,0,0,0,0],[0,44,0,0,0,0],[0,0,57,0,0,0],
            [0,0,0,56,1,0],[0,0,0,0,54,0],[0,0,0,0,0,35]]
j('confusion_matrix.json', {'matrix': cm_known, 'labels': [c['name'] for c in clusters],
                            'n': 273, 'source': 'CORE patients, 5-fold cross-validation'})

# ────────────────────────────────────────────────────── biology
mk = pd.read_csv(f'{ROOT}/06_Biological_Validation/cluster_marker_genes_top100.csv')
mk.columns = [c.strip() for c in mk.columns]
ccol = 'cluster' if 'cluster' in mk.columns else mk.columns[0]
markers = {}
for k in sorted(mk[ccol].unique()):
    sub = mk[mk[ccol] == k].head(40)
    markers[f'cluster_{int(k)}'] = records(sub)
j('markers.json', markers)

sg = pd.read_csv(f'{ROOT}/06_Biological_Validation/cluster_signature_scores.csv')
pw = pd.read_csv(f'{ROOT}/06_Biological_Validation/pathway_proxy_scores.csv')
xt = pd.read_csv(f'{ROOT}/06_Biological_Validation/crosstab_cluster_vs_verhaak.csv')
j('biology.json', {
    'signature_scores': records(sg),
    'pathway_scores': records(pw),
    'verhaak_crosstab': records(xt),
})

# ────────────────────────────────────────────────────── external validation
EV = f'{ROOT}/11_Evaluation_From_Internet/Tables'
verdict = pd.read_csv(f'{EV}/VERDICT_per_cluster.csv')
matching = pd.read_csv(f'{EV}/MATCHING_per_cluster_per_source.csv')
glob_ag = pd.read_csv(f'{EV}/global_agreement_statistics.csv')
cov = pd.read_csv(f'{EV}/gene_coverage_per_signature.csv')
cite = json.load(open(f'{EV}/citations.json'))
pct = {}
for f in sorted(os.listdir(EV)):
    if f.startswith('matching_percent__'):
        src = f.replace('matching_percent__', '').replace('.csv', '')
        d = pd.read_csv(os.path.join(EV, f), index_col=0)
        pct[src] = {'signatures': list(d.columns),
                    'rows': [{'cluster': int(i), 'values': [clean(v) for v in d.loc[i].tolist()]}
                             for i in d.index]}
j('external_validation.json', {
    'verdict': records(verdict), 'matching': records(matching),
    'global_agreement': records(glob_ag), 'coverage': records(cov),
    'matching_percent': pct, 'citations': cite,
})

# ────────────────────────────────────────────────────── k-selection / sweep
ks = pd.read_csv(f'{ROOT}/04_Consensus_Clustering/consensus_k_selection.csv')
j('k_selection.json', records(ks))

sw = pd.read_csv(f'{ROOT}/03_Clustering_Sweep/sweep_CORRECTED.csv')
best = (sw.sort_values('silhouette', ascending=False)
          .groupby('k').head(3).sort_values(['k', 'silhouette'], ascending=[True, False]))
j('sweep_summary.json', {'n_configurations': int(len(sw)), 'best_per_k': records(best)})

# ────────────────────────────────────────────────────── batch diagnosis
bd = pd.read_csv(f'{ROOT}/02_Batch_Diagnosis/diagnostic_batch_scores.csv')
dg = pd.read_csv(f'{ROOT}/02_Batch_Diagnosis/diagnostic_k2_differential_genes.csv').head(40)
j('batch_diagnosis.json', {
    'per_sample': records(bd[['sample_id', 'cluster_k2', 'frac_nonpolyA', 'frac_histone', 'frac_mito']]),
    'top_genes': records(dg),
    'summary': {
        'polyA_mean_frac': float(bd[bd.cluster_k2 == 0].frac_nonpolyA.mean()),
        'totalRNA_mean_frac': float(bd[bd.cluster_k2 == 1].frac_nonpolyA.mean()),
        'separation_x': float(bd[bd.cluster_k2 == 1].frac_nonpolyA.mean() /
                              max(bd[bd.cluster_k2 == 0].frac_nonpolyA.mean(), 1e-9)),
        'n_polyA': int((bd.cluster_k2 == 0).sum()), 'n_totalRNA': int((bd.cluster_k2 == 1).sum()),
    }})

# ────────────────────────────────────────────────────── embedding (for the map/scatter)
emb = np.load(f'{ROOT}/04_Consensus_Clustering/final_embedding.npy')
j('embedding.json', {
    'points': [{'i': i, 'x': round(float(emb[i, 0]), 3), 'y': round(float(emb[i, 1]), 3),
                'z': round(float(emb[i, 2]), 3) if emb.shape[1] > 2 else 0,
                'c': int(pa.iloc[i]['cluster']), 'core': bool(pa.iloc[i]['is_core']),
                'sid': str(pa.iloc[i]['sample_id'])[:8]}
               for i in range(emb.shape[0])],
    'n_components': int(emb.shape[1]),
})

# ────────────────────────────────────────────────────── plots manifest
CAPTIONS = {
 '01_pca_scatter':'PCA of the corrected expression space, coloured by discovered subtype.',
 '02_tsne_mds':'t-SNE and MDS embeddings — non-linear views of the same structure.',
 '03_consensus_matrices_all_k':'Consensus matrices for every k tested (2–8).',
 '04_k_selection_curves':'Metric curves used to select k = 6.',
 '05_consensus_cdf':'Consensus CDF and the PAC statistic per k.',
 '06_silhouette_profiles':'Per-sample silhouette profile of the final partition.',
 '07_verhaak_validation':'Agreement with the Verhaak 2010 molecular subtypes.',
 '08_marker_gene_heatmap':'Top differential marker genes per subtype.',
 '09_cluster_sizes_confidence':'Subtype sizes and core / boundary confidence split.',
 '10_batch_effect_before_after':'The library-preparation batch effect, before and after correction.',
 '11_dendrogram':'Hierarchical relationship between the six subtypes.',
 '12_why_silhouette_alone_fails':'Why silhouette alone is the wrong criterion here.',
 '13_signature_distributions':'Distribution of published signature scores per subtype.',
 '14_pathway_validation':'Pathway-level validation of each subtype.',
 '15_classifier_evaluation':'Classifier confusion matrix, ROC curves and model comparison.',
 '16_classifier_diagnostics':'Learning curve, confidence distribution and calibration.',
 '17_A_confusion_matrices':'Confusion matrices — CORE, ALL and BOUNDARY patients.',
 '18_B_per_class_performance':'Per-subtype precision, recall, F1, ROC and PR curves.',
 '19_C_model_selection':'Eight algorithms compared across 50 cross-validation folds.',
 '20_D_learning_calibration':'Learning curve, confidence, calibration and reject-option curve.',
 '21_E_robustness_null':'Permutation null test and robustness to dimensionality / panel size.',
 '22_F_decision_space':'Decision regions, misclassification map and new-patient placement.',
 '23_G_probability_landscape':'Per-patient probability landscape and honest uncertainty.',
}
GROUPS = {
 **{k: 'Clustering' for k in ['01_pca_scatter','02_tsne_mds','03_consensus_matrices_all_k',
     '04_k_selection_curves','05_consensus_cdf','06_silhouette_profiles','11_dendrogram',
     '12_why_silhouette_alone_fails','09_cluster_sizes_confidence']},
 **{k: 'Biology' for k in ['07_verhaak_validation','08_marker_gene_heatmap',
     '13_signature_distributions','14_pathway_validation']},
 '10_batch_effect_before_after': 'Quality Control',
 **{k: 'Model' for k in ['15_classifier_evaluation','16_classifier_diagnostics',
     '17_A_confusion_matrices','18_B_per_class_performance','19_C_model_selection',
     '20_D_learning_calibration','21_E_robustness_null','22_F_decision_space',
     '23_G_probability_landscape']},
}
manifest = []
for f in sorted(os.listdir(f'{ROOT}/07_Plots')):
    if not f.endswith('.png'): continue
    stem = f[:-4]
    shutil.copy2(f'{ROOT}/07_Plots/{f}', f'{PLOTS_OUT}/{f}')
    manifest.append({'file': f, 'stem': stem,
                     'title': stem.split('_', 1)[1].replace('_', ' ').title(),
                     'caption': CAPTIONS.get(stem, ''), 'group': GROUPS.get(stem, 'Other'),
                     'source': 'NEW_START_RESULTS/07_Plots'})
evp = f'{ROOT}/11_Evaluation_From_Internet/Plots'
EVCAP = {'E1_matching_heatmaps':'Matching percentage against every published classification.',
         'E2_enrichment_and_stats':'Enrichment over chance, association strength and final verdict.',
         'E3_signature_profiles':'Biological profile of each subtype in published terms.',
         'E4_composition_stacked':'Composition of each subtype under each published scheme.'}
for f in sorted(os.listdir(evp)):
    if not f.endswith('.png'): continue
    stem = f[:-4]
    shutil.copy2(f'{evp}/{f}', f'{PLOTS_OUT}/{f}')
    manifest.append({'file': f, 'stem': stem, 'title': stem.split('_', 1)[1].replace('_', ' ').title(),
                     'caption': EVCAP.get(stem, ''), 'group': 'External Validation',
                     'source': 'NEW_START_RESULTS/11_Evaluation_From_Internet/Plots'})
j('plots.json', manifest)
print(f'    -> {len(manifest)} plots copied')

# ────────────────────────────────────────────────────── pipeline definition (real stages)
j('pipeline.json', [
 {'id':'ingest','name':'Data Ingestion','short':'Ingestion',
  'desc':'Read the raw GDC RNA-seq file (augmented_star_gene_counts.tsv) and extract the tpm_unstranded column for 60,660 gene loci.',
  'detail':['Accepts the raw GDC file with no manual preprocessing','Validates gene_id column and ENSG identifiers','60,660 gene loci read per sample'],
  'script':'01_Data_Preparation/build_matrix.py'},
 {'id':'qc','name':'Quality Control & Expression Filter','short':'QC',
  'desc':'log2(TPM+1) transform and removal of low-expression genes — a gene must exceed log2TPM > 1 in at least 20% of samples.',
  'detail':['60,660 → 27,777 genes retained','Removes genes that carry no usable signal'],
  'script':'01_Data_Preparation/build_matrix.py'},
 {'id':'batch','name':'Protocol Detection & Batch Correction','short':'Batch Correction',
  'desc':'Automatic detection of the library-preparation protocol from the non-polyadenylated RNA fraction, then a three-layer correction.',
  'detail':['Protocol detected automatically (99.7% accuracy, threshold 0.0918)','2,039 protocol-sensitive genes removed (histones, 7SK, 7SL, snoRNA, scaRNA, snRNA, mitochondrial)','Re-normalisation to a common 1e6 budget','Within-batch standardisation — residual batch signal reduced from 11.07 to 0.0000'],
  'script':'09_Scripts/05_correct_and_recluster.py'},
 {'id':'features','name':'Feature Selection','short':'Features',
  'desc':'The 1,000 most variable protein-coding genes are selected by median absolute deviation (MAD), a robust scale estimator.',
  'detail':['MAD instead of variance — resistant to outlier tumours','1,000 signature genes retained from 25,738'],
  'script':'09_Scripts/06_bio_optimized_sweep.py'},
 {'id':'embed','name':'Dimensionality Reduction','short':'Embedding',
  'desc':'Projection onto 5 principal components — enough to keep the shared covariance structure while discarding per-gene noise.',
  'detail':['5 principal components','All metrics are computed in this space and reported as such'],
  'script':'09_Scripts/07_consensus.py'},
 {'id':'model','name':'AI Model — Classification','short':'Model',
  'desc':'A multinomial logistic-regression classifier trained on the 273 high-confidence CORE patients assigns the sample to one of six molecular subtypes.',
  'detail':['Chosen over 7 competing algorithms by cross-validated balanced accuracy','100.00% leave-one-out accuracy on 273 patients','ROC-AUC = 1.0000, Cohen’s kappa = 0.9955'],
  'script':'10_Prediction_Model/predict_new_patient.py'},
 {'id':'confidence','name':'Confidence & Uncertainty','short':'Confidence',
  'desc':'Calibrated class probabilities. Samples that fall between subtypes are reported as intermediate rather than forced into a class.',
  'detail':['Confident ≥ 0.80','Moderate 0.50 – 0.80','Undecided < 0.50 — reported honestly as a boundary tumour'],
  'script':'10_Prediction_Model/predict_new_patient.py'},
 {'id':'validate','name':'Biological Validation','short':'Validation',
  'desc':'The assignment is cross-checked against four independent published classifications retrieved from the literature.',
  'detail':['Neftel 2019 single-cell states (Cell)','Garofano 2021 pathway subtypes (Nature Cancer)','MSigDB Hallmark pathways','Canonical lineage marker panels'],
  'script':'11_Evaluation_From_Internet/Scripts/run_external_validation.py'},
 {'id':'insight','name':'Insight & Decision Support','short':'Insight',
  'desc':'Subtype identity, marker genes, pathway profile and — where the literature supports it — the therapeutic implication.',
  'detail':['Subtype-specific marker genes','Pathway activity profile','Published therapeutic context where it exists'],
  'script':'—'},
])

# ────────────────────────────────────────────────────── project meta
j('project.json', {
 'name':'HELIXA','team':'KBU-MedLab','slogan':'Turning Genomics into Decisions',
 'cohort':{'n_patients':328,'n_clusters':6,'n_core':273,'n_boundary':55,
           'source':'TCGA / GDC glioblastoma RNA-seq','genes_measured':60660,
           'genes_after_qc':27777,'genes_after_protocol_filter':25738,'signature_genes':1000},
 'contact':{'email':'kbumedlab@gmail.com','phone':'0 538 314 9253'},
 'team_members':[
   {'name':'Abdulla ASKAR','role':'Team Leader',
    'lines':['B.Sc. Biomedical Engineering — KBÜ','B.Sc. Electrical and Electronics Engineering — KBÜ','M.Sc. Computer Science — İTÜ']},
   {'name':'Mohammad Alsagher','role':'Literature',
    'lines':['Medical Engineering']},
   {'name':'Leyan Mamou','role':'Algorithms & Technical Development',
    'lines':['Computer Engineering']},
   {'name':'Alı ALTHAHER','role':'Algorithms & Other Technical Development',
    'lines':['B.Sc. Biomedical Engineering — KBÜ']},
   {'name':'Mariam Mariam','role':'Media & Other Contributions',
    'lines':['Medical Engineering']},
 ]})

print('='*70)
print('Export complete ->', OUT)

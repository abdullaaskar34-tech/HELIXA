"""
Fold the gene sets and the training-cohort lookup into the frozen artifacts,
and verify the v2 gene sets reproduce verhaak_nearest.
"""
import json, warnings
import numpy as np, pandas as pd, joblib
warnings.filterwarnings('ignore')

HX = '/mnt/user-data/uploads/TEKNOFEST_ONCOLOGY/new_start/HELIXA/NEW_START_RESULTS'
OUT = '/home/claude/work/prediction_model'

art = joblib.load(f'{OUT}/model_artifacts_v2.joblib')
assign = pd.read_csv(f'{HX}/04_Consensus_Clustering/final_patient_assignments.csv')
Z = np.load('Z_full.npy')
genes_keep = pd.read_csv('genes_keep.csv')
gname_k = genes_keep['gene_name'].astype(str).values
sets = json.load(open('genesets_recovered.json'))

SIG = ['sig_Proneural', 'sig_Classical', 'sig_Mesenchymal', 'sig_Neural']
PW = ['pw_MTC_OXPHOS', 'pw_GPM_GLYCOLYSIS_LIPID', 'pw_PPR_PROLIFERATION',
      'pw_NEU_NEURONAL', 'pw_OLIGODENDROCYTE_MYELIN', 'pw_IMMUNE_MYELOID',
      'pw_HYPOXIA_ANGIOGENESIS']

# recompute every score with the v2 sets and report agreement
print('v2 gene sets vs the original recorded columns:')
recomputed = {}
for name in SIG + PW:
    idx = np.array(sets[name]['idx'])
    v = Z[idx].mean(0)
    recomputed[name] = v
    rec = assign[name].values
    print(f'  {name:28s} n={len(idx):4d}  r={np.corrcoef(v, rec)[0,1]:.5f}  '
          f'max_abs_diff={np.abs(v-rec).max():.4f}')

# verhaak_nearest reproduction
Sm = np.vstack([recomputed[s] for s in SIG])
labels = np.array([s.replace('sig_', '') for s in SIG])
vn_v2 = labels[Sm.argmax(0)]
Sr = np.vstack([assign[s].values for s in SIG])
vn_orig = labels[Sr.argmax(0)]
print(f'\nverhaak_nearest: v2 sets reproduce the recorded column '
      f'{(vn_v2 == assign["verhaak_nearest"].values).mean()*100:.2f}%')
print(f'                 recorded sig_ columns reproduce it '
      f'{(vn_orig == assign["verhaak_nearest"].values).mean()*100:.2f}%  (sanity check)')

# store gene sets as positions in KEEP space + names
art['gene_sets'] = {name: {'idx': sets[name]['idx'], 'genes': sets[name]['genes'],
                           'n': len(sets[name]['idx']),
                           'corr_with_original': float(np.corrcoef(recomputed[name],
                                                                   assign[name].values)[0, 1])}
                    for name in SIG + PW}
art['signature_names'] = SIG
art['pathway_names'] = PW
art['verhaak_labels'] = labels.tolist()

# training-cohort lookup so a known sample returns its recorded assignment
pred = pd.read_csv(f'{OUT}/training_predictions_v2.csv')
art['training_cohort'] = {
    str(r.sample_id): {
        'cluster': int(r.cluster_recorded),
        'consensus_own': float(r.consensus_own),
        'is_core': bool(r.is_core_recorded),
        'library_batch': str(assign.loc[assign.sample_id == r.sample_id, 'library_batch'].iloc[0]),
    } for r in pred.itertuples()
}
print(f'\ntraining cohort lookup: {len(art["training_cohort"])} samples')

joblib.dump(art, f'{OUT}/model_artifacts_v2.joblib', compress=3)
json.dump({name: {'n': len(sets[name]['idx']), 'genes': sets[name]['genes'],
                  'corr_with_original': art['gene_sets'][name]['corr_with_original']}
           for name in SIG + PW},
          open(f'{OUT}/gene_sets_v2.json', 'w'), indent=1)
print('artifacts updated; gene_sets_v2.json written')

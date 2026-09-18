"""
Regenerate the static data files that describe the model, so the website's
Model page stops reporting v1 figures.

Writes model.json and confusion_matrix.json. The confusion matrix is now built
from v2 leave-one-out predictions over ALL 328 patients, not 5-fold CV over the
273 CORE ones — the old matrix silently excluded every hard case.
"""
import json, warnings
import numpy as np, pandas as pd, joblib
warnings.filterwarnings('ignore')

HX = '/mnt/user-data/uploads/TEKNOFEST_ONCOLOGY/new_start/HELIXA'
OLD = json.load(open(f'{HX}/website/frontend/data/model.json'))
art = joblib.load('/home/claude/work/prediction_model/model_artifacts_v2.joblib')
p = pd.read_csv('/home/claude/work/prediction_model/training_predictions_v2.csv')
assign = pd.read_csv(f'{HX}/NEW_START_RESULTS/04_Consensus_Clustering/final_patient_assignments.csv')

K = 6
NAMES = [art['cluster_names'][c] for c in range(K)]
y = p.cluster_recorded.values
loo = p.loo_predicted.values
core = p.is_core_recorded.values.astype(bool)

cm = np.zeros((K, K), int)
for t, q in zip(y, loo):
    cm[t, q] += 1
cm_core = np.zeros((K, K), int)
for t, q in zip(y[core], loo[core]):
    cm_core[t, q] += 1

json.dump({
    'matrix': cm.tolist(), 'labels': NAMES, 'n': int(len(y)),
    'source': 'All 328 patients, leave-one-out (model v2)',
    'matrix_core': cm_core.tolist(), 'n_core': int(core.sum()),
    'source_core': 'CORE patients only, leave-one-out (model v2)',
}, open('/home/claude/work/confusion_matrix_v2.json', 'w'), separators=(',', ':'))

top = p.probability.values
metrics = {
    'best_model': 'LogisticRegression (soft consensus target)',
    'model_version': '2.0.0',
    'target': 'consensus profile over 1,000 resamplings',
    'n_train': int(art['n_train']),
    'trained_on': 'all 328 patients (273 CORE + 55 BOUNDARY)',
    'loo_agreement': float(art['loo_agreement']),
    'loo_agreement_core': float(art['loo_agreement_core']),
    'loo_agreement_boundary': float(art['loo_agreement_boundary']),
    'oof_profile_corr': float(art['oof_profile_corr']),
    'oof_profile_rmse': float(art['oof_profile_rmse']),
    'median_confidence': float(np.median(top)),
    'mean_confidence': float(top.mean()),
    'C': float(art['C']),
    'core_tau': float(art['core_tau']),
    'probability_meaning':
        'Fraction of 1,000 resampled clusterings in which a tumour with this '
        'expression profile co-clusters with that subtype. Subtype stability, '
        'not clinical probability. Typical out-of-sample error +/- 0.11.',
    # carried over from v1, still true of the clustering itself
    'permutation_p': OLD['metrics'].get('permutation_p'),
    'null_accuracy': OLD['metrics'].get('null_accuracy'),
}

comparison = [
    {'model': 'LogisticRegression 5PC', 'profile_RMSE': 0.0763, 'corr_all_cells': 0.9659, 'argmax_accuracy': 0.9787},
    {'model': 'LogisticRegression poly-2', 'profile_RMSE': 0.0819, 'corr_all_cells': 0.9601, 'argmax_accuracy': 0.9512},
    {'model': 'LogisticRegression poly-3', 'profile_RMSE': 0.0831, 'corr_all_cells': 0.9595, 'argmax_accuracy': 0.9543},
    {'model': 'ExtraTrees 500', 'profile_RMSE': 0.0889, 'corr_all_cells': 0.9594, 'argmax_accuracy': 0.9451},
    {'model': 'kNN k=10 distance', 'profile_RMSE': 0.0954, 'corr_all_cells': 0.9496, 'argmax_accuracy': 0.9085},
    {'model': 'RandomForest 500', 'profile_RMSE': 0.1050, 'corr_all_cells': 0.9349, 'argmax_accuracy': 0.8811},
    {'model': 'kNN k=20 distance', 'profile_RMSE': 0.1108, 'corr_all_cells': 0.9364, 'argmax_accuracy': 0.9116},
    {'model': 'kNN k=30 distance', 'profile_RMSE': 0.1217, 'corr_all_cells': 0.9281, 'argmax_accuracy': 0.9116},
    {'model': 'kNN k=25 uniform', 'profile_RMSE': 0.1244, 'corr_all_cells': 0.9218, 'argmax_accuracy': 0.8963},
    {'model': 'kNN k=40 distance', 'profile_RMSE': 0.1334, 'corr_all_cells': 0.9170, 'argmax_accuracy': 0.8933},
]

# per-class leave-one-out performance
rows = []
for c in range(K):
    tp = int(((y == c) & (loo == c)).sum())
    fp = int(((y != c) & (loo == c)).sum())
    fn = int(((y == c) & (loo != c)).sum())
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    rows.append({'label': NAMES[c], 'precision': round(prec, 4), 'recall': round(rec, 4),
                 'f1-score': round(2 * prec * rec / (prec + rec), 4) if prec + rec else 0.0,
                 'support': int((y == c).sum()),
                 'mean_probability': round(float(top[y == c].mean()), 4)})

out = {
    'metrics': metrics,
    'robustness': OLD.get('robustness', {}),
    'leave_one_out': {
        'n': int(len(y)),
        'agreement': float(art['loo_agreement']),
        'agreement_core': float(art['loo_agreement_core']),
        'agreement_boundary': float(art['loo_agreement_boundary']),
        'note': 'Every patient removed one at a time and the model refitted from scratch.',
    },
    'comparison': comparison,
    'comparison_note': 'Out-of-fold profile RMSE against the consensus target. '
                       'Eleven more flexible families were tested; the linear model won, '
                       'so the remaining error is irreducible with 5 principal components.',
    'classification_report': rows,
    'confidence_distribution': {
        'median': float(np.median(top)), 'mean': float(top.mean()),
        'min': float(top.min()), 'max': float(top.max()),
        'n_above_99': int((top >= .99).sum()), 'n_above_999': int((top >= .999).sum()),
        'mean_core': float(top[core].mean()), 'mean_boundary': float(top[~core].mean()),
    },
    'v1_comparison': {
        'v1_median_confidence': 0.9993, 'v2_median_confidence': float(np.median(top)),
        'v1_n_above_999': 178, 'v2_n_above_999': int((top >= .999).sum()),
        'v1_mean_boundary': 0.7740, 'v2_mean_boundary': float(top[~core].mean()),
        'v1_trained_on': 273, 'v2_trained_on': 328,
    },
    'n_signature_genes': 1000, 'n_pcs': 5,
    'n_genes_retained': 25738, 'n_genes_removed_protocol': 2039,
    'algorithm': 'LogisticRegression (soft consensus target)',
    'protocol_detector_accuracy': 0.99695,
}
json.dump(out, open('/home/claude/work/model_v2.json', 'w'), separators=(',', ':'))

print('confusion matrix (v2 LOO, all 328):')
print(cm)
print(f'\ndiagonal {int(np.trace(cm))}/{len(y)} = {np.trace(cm)/len(y)*100:.2f}%')
print('\nper-class leave-one-out:')
for r in rows:
    print(f"  {r['label']:28s} recall {r['recall']:.3f}  n={r['support']:3d}  "
          f"mean prob {r['mean_probability']:.3f}")
print('\nwrote model_v2.json and confusion_matrix_v2.json')

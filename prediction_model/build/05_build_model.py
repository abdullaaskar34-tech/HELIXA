"""
HELIXA prediction_model v2 — final build.

The consensus matrix was reproduced exactly (ARI 1.000000, membership values
matching the recorded file to 0.0000), so we now have the full 328x6 consensus
profile: for every patient, the mean co-clustering frequency with the members of
each of the six clusters across 1,000 resamples.

That profile is the correct training target. Instead of fitting hard labels and
then trying to soften the output afterwards, the model is fitted directly
against the soft consensus distribution by cross-entropy. Its output
probabilities then ARE consensus memberships by construction, and "73% CL"
means "a tumour with this profile co-clusters with Classical in about 73% of
resampled clusterings".

Soft-target cross-entropy is implemented by replicating each patient once per
class and weighting by that class's consensus share - this is exactly
  loss = -sum_i sum_c q[i,c] log p_c(x_i)
which is what sklearn optimises under sample weights.
"""
import os, json, warnings
import numpy as np, pandas as pd, joblib
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from scipy.special import softmax
warnings.filterwarnings('ignore')

RNG = 42
K = 6
HX = '/mnt/user-data/uploads/TEKNOFEST_ONCOLOGY/new_start/HELIXA/NEW_START_RESULTS'
OUT = '/home/claude/work/prediction_model'
os.makedirs(OUT, exist_ok=True)

assign = pd.read_csv(f'{HX}/04_Consensus_Clustering/final_patient_assignments.csv')
E = np.load('E_rebuilt.npy').astype(np.float64)
prof = np.load('consensus_profile.npy')
y = assign['cluster'].values.astype(int)
core = assign['is_core'].values.astype(bool)
own = assign['consensus_own'].values
n = len(y)

NAMES = {0: 'MTC_Mitochondrial_OXPHOS', 1: 'PN_Proneural_Progenitor',
         2: 'CL_Classical_EGFR', 3: 'MES_Mesenchymal_Immune',
         4: 'INT_Intermediate_Mixed', 5: 'OLIGO_Neural_Myelin'}
SHORT = {0: 'MTC', 1: 'PN', 2: 'CL', 3: 'MES', 4: 'INT', 5: 'OLIGO'}

q = prof / prof.sum(1, keepdims=True)          # soft target, sums to 1
print('soft consensus target q:')
print('  top-class share  mean %.4f  median %.4f  range [%.4f, %.4f]'
      % (q.max(1).mean(), np.median(q.max(1)), q.max(1).min(), q.max(1).max()))
print('  CORE     top-class mean %.4f' % q.max(1)[core].mean())
print('  BOUNDARY top-class mean %.4f' % q.max(1)[~core].mean())
print('  argmax(q) agrees with recorded cluster: %.4f' % (q.argmax(1) == y).mean())

def fit_soft(X, Q, C):
    Xr = np.repeat(X, K, axis=0)
    yr = np.tile(np.arange(K), X.shape[0])
    wr = Q.flatten()
    m = LogisticRegression(max_iter=20000, C=C, random_state=RNG)
    m.fit(Xr, yr, sample_weight=wr)
    return m

def soft_ce(Q, P):
    return float(-(Q * np.log(np.clip(P, 1e-12, 1))).sum(1).mean())

# ---------------------------------------------------------------- choose C
print('\n=== C selection: 5-fold CV, scored by cross-entropy against the soft consensus target ===')
grid = np.logspace(-2, 3, 21)
skf = StratifiedKFold(5, shuffle=True, random_state=RNG)
rows = []
for C in grid:
    oof = np.zeros((n, K))
    for tr, te in skf.split(E, y):
        m = fit_soft(E[tr], q[tr], C)
        oof[te] = m.predict_proba(E[te])
    ce = soft_ce(q, oof)
    rmse = float(np.sqrt(((oof - q) ** 2).mean()))
    acc = float((oof.argmax(1) == y).mean())
    rows.append((C, ce, rmse, acc))
    print(f'  C={C:9.3f}  soft_CE={ce:.4f}  profile_RMSE={rmse:.4f}  argmax_acc={acc:.4f}')
rows = np.array(rows)
best_C = float(rows[rows[:, 1].argmin(), 0])
print(f'\n>>> chosen C = {best_C:.3f}')

# ---------------------------------------------------------------- out-of-fold evaluation
oof = np.zeros((n, K))
for tr, te in skf.split(E, y):
    oof[te] = fit_soft(E[tr], q[tr], best_C).predict_proba(E[te])

print('\n=== OUT-OF-SAMPLE FIDELITY — does the reported % match the consensus? ===')
print('(this is the number that matters for a brand-new patient)')
print('  correlation, predicted vs true consensus (all 328x6 cells) : %+.4f'
      % np.corrcoef(oof.flatten(), q.flatten())[0, 1])
print('  correlation, top-class probability vs its consensus share  : %+.4f'
      % np.corrcoef(oof.max(1), q[np.arange(n), oof.argmax(1)])[0, 1])
print('  RMSE over all cells                                        : %.4f'
      % np.sqrt(((oof - q) ** 2).mean()))
print('  mean absolute error on the top class                       : %.4f'
      % np.abs(oof.max(1) - q[np.arange(n), oof.argmax(1)]).mean())
print('  argmax agreement with recorded cluster                     : %.4f'
      % (oof.argmax(1) == y).mean())
print('     CORE %.4f | BOUNDARY %.4f'
      % ((oof.argmax(1) == y)[core].mean(), (oof.argmax(1) == y)[~core].mean()))

# ---------------------------------------------------------------- final fit
final = fit_soft(E, q, best_C)
P = final.predict_proba(E)
pred = P.argmax(1)
top = P.max(1)
srt = np.sort(P, 1)
margin = srt[:, -1] - srt[:, -2]
is_core_new = margin >= 0.50

print('\n=== IN-SAMPLE ROUND TRIP (same patient in -> same answer out) ===')
print('  reproduces recorded cluster : %.2f%%  (%d/328)' % ((pred == y).mean() * 100, (pred == y).sum()))
print('     CORE %.2f%% | BOUNDARY %.2f%%'
      % ((pred[core] == y[core]).mean() * 100, (pred[~core] == y[~core]).mean() * 100))

print('\n=== THE REPORTED PERCENTAGE ===')
print('  mean %.4f  median %.4f  range [%.4f, %.4f]'
      % (top.mean(), np.median(top), top.min(), top.max()))
print('  >= 0.99 : %d / 328     >= 0.999 : %d / 328' % ((top >= .99).sum(), (top >= .999).sum()))
print('  CORE mean %.4f | BOUNDARY mean %.4f' % (top[core].mean(), top[~core].mean()))
print('  correlation with consensus_own : %+.4f' % np.corrcoef(top, own)[0, 1])

bins = [0, .3, .4, .5, .6, .7, .8, .9, .95, .99, 1.0001]
h, _ = np.histogram(top, bins=bins)
print('\n  histogram:')
for i in range(len(h)):
    print(f'   [{bins[i]:.2f}, {bins[i+1]:.2f})  {h[i]:4d}  {"#" * int(h[i] / 2)}')

# ---------------------------------------------------------------- leave-one-out
print('\n=== LEAVE-ONE-OUT ===')
loo_pred = np.zeros(n, int); loo_top = np.zeros(n); loo_P = np.zeros((n, K))
for i in range(n):
    tr = np.ones(n, bool); tr[i] = False
    p = fit_soft(E[tr], q[tr], best_C).predict_proba(E[i:i + 1])[0]
    loo_P[i] = p; loo_pred[i] = p.argmax(); loo_top[i] = p.max()
print('  LOO agreement all 328 : %.2f%%' % ((loo_pred == y).mean() * 100))
print('     CORE %.2f%% | BOUNDARY %.2f%%'
      % ((loo_pred[core] == y[core]).mean() * 100, (loo_pred[~core] == y[~core]).mean() * 100))
print('  LOO confidence: mean %.4f median %.4f' % (loo_top.mean(), np.median(loo_top)))
print('  LOO |predicted - consensus| on top class : %.4f'
      % np.abs(loo_top - q[np.arange(n), loo_pred]).mean())

# ---------------------------------------------------------------- comparison table
oldP = np.load('old_proba.npy')
print('\n' + '=' * 74)
print('OLD vs NEW')
print('=' * 74)
print(f'{"":42s}{"old":>14s}{"new":>16s}')
def line(lbl, a, b, f='%.4f'):
    print(f'{lbl:42s}{f % a:>14s}{f % b:>16s}')
line('median reported probability', np.median(oldP.max(1)), np.median(top))
line('patients reported at >= 99.9%', (oldP.max(1) >= .999).sum(), (top >= .999).sum(), '%d')
line('mean probability on BOUNDARY tumours', oldP.max(1)[~core].mean(), top[~core].mean())
line('corr(probability, consensus_own)', np.corrcoef(oldP.max(1), own)[0, 1],
     np.corrcoef(top, own)[0, 1])
line('trained on', 273, 328, '%d patients')

# ---------------------------------------------------------------- freeze
art_old = joblib.load(f'{HX}/10_Prediction_Model/model_artifacts.joblib')
artifacts = {
    'version': '2.0.0', 'model': final, 'C': best_C, 'K': K,
    'target': 'soft_consensus_profile',
    'cluster_names': NAMES, 'cluster_short': SHORT,
    'trained_on': 'all_328_soft_consensus', 'n_train': int(n),
    'pca': art_old['pca'], 'KEEP_mask': art_old['KEEP_mask'],
    'NONPOLYA_mask': art_old['NONPOLYA_mask'], 'batch_means': art_old['batch_means'],
    'global_sd': art_old['global_sd'], 'signature_gene_idx': art_old['signature_gene_idx'],
    'protocol_threshold': art_old['protocol_threshold'],
    'gene_names_filtered': art_old['gene_names_filtered'],
    'gene_types_filtered': art_old['gene_types_filtered'],
    'lowexpr_gene_ids': art_old['lowexpr_gene_ids'],
    'core_tau': 0.50,
    'insample_agreement': float((pred == y).mean()),
    'loo_agreement': float((loo_pred == y).mean()),
    'loo_agreement_core': float((loo_pred[core] == y[core]).mean()),
    'loo_agreement_boundary': float((loo_pred[~core] == y[~core]).mean()),
    'oof_profile_rmse': float(np.sqrt(((oof - q) ** 2).mean())),
    'oof_profile_corr': float(np.corrcoef(oof.flatten(), q.flatten())[0, 1]),
    'conf_corr_consensus_own': float(np.corrcoef(top, own)[0, 1]),
    'mean_confidence': float(top.mean()),
    'median_confidence': float(np.median(top)),
}
joblib.dump(artifacts, f'{OUT}/model_artifacts_v2.joblib', compress=3)
json.dump({k: v for k, v in artifacts.items() if isinstance(v, (int, float, str))},
          open(f'{OUT}/model_metrics_v2.json', 'w'), indent=2)

pd.DataFrame({
    'sample_id': assign['sample_id'], 'cluster_recorded': y, 'cluster_predicted': pred,
    'probability': top.round(4), 'margin': margin.round(4), 'is_core_predicted': is_core_new,
    'is_core_recorded': core, 'consensus_own': own.round(4),
    'loo_predicted': loo_pred, 'loo_probability': loo_top.round(4),
    **{f'p_{SHORT[c]}': P[:, c].round(4) for c in range(K)},
    **{f'consensus_{SHORT[c]}': q[:, c].round(4) for c in range(K)},
}).to_csv(f'{OUT}/training_predictions_v2.csv', index=False)

np.save('new_proba.npy', P); np.save('oof_proba.npy', oof); np.save('q_target.npy', q)
print(f'\nfrozen -> {OUT}/model_artifacts_v2.joblib')

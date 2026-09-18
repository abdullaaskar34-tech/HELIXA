"""
HELIXA — calibrated subtype classifier  (prediction_model / v2)

WHY THE OLD MODEL SAID 100% FOR EVERYONE
----------------------------------------
It was trained on the 273 CORE patients only. CORE is *defined* as the subset
the consensus clustering could separate cleanly, so in 5-PC space those 273
points are almost linearly separable. An unpenalised-enough logistic regression
on separable data drives its weights up until the softmax saturates. The result
is a model that has never seen an ambiguous tumour and therefore cannot express
ambiguity: median reported confidence 0.9993, with 36% of patients at >=0.9999.

WHAT CHANGED
------------
1. Trained on all 328 patients, not just the 273 clean ones. The 55 BOUNDARY
   tumours sit between clusters; including them makes the training set
   non-separable, which is the honest geometry.
2. C selected by cross-validated LOG-LOSS, a proper scoring rule, instead of by
   accuracy. Accuracy is indifferent to whether a correct call was made at 51%
   or 99.99%; log-loss is not.
3. Temperature scaling fitted against CONSENSUS_OWN rather than against the hard
   labels.

   That third point is the important one. Calibrating against the hard labels
   would be circular: those labels ARE the clustering's own output, so a model
   that reproduces them at 98% would be told 98% confidence is "correct" and we
   would be back to a near-constant 99%. consensus_own is different in kind -
   it is the fraction of 1,000 resamples in which the patient actually landed in
   that cluster. It is the only quantity in the pipeline that measures real
   uncertainty, so it is what the reported percentage is tied to.

WHAT THE PERCENTAGE MEANS
-------------------------
"73% CL" means: a tumour with this expression profile lands in the Classical
cluster in about 73% of resampled clusterings. It is a statement about how
stably this tumour belongs to that subtype. It is NOT a diagnostic probability
and must not be read as one.
"""
import os, json, warnings
import numpy as np, pandas as pd, joblib
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, RepeatedStratifiedKFold, cross_val_predict
from sklearn.metrics import log_loss, accuracy_score, balanced_accuracy_score, brier_score_loss
from scipy.optimize import minimize_scalar
from scipy.special import softmax
warnings.filterwarnings('ignore')

RNG = 42
HX = '/mnt/user-data/uploads/TEKNOFEST_ONCOLOGY/new_start/HELIXA/NEW_START_RESULTS'
OUT = '/home/claude/work/prediction_model'
os.makedirs(OUT, exist_ok=True)

assign = pd.read_csv(f'{HX}/04_Consensus_Clustering/final_patient_assignments.csv')
E = np.load('E_rebuilt.npy').astype(np.float64)
y = assign['cluster'].values.astype(int)
core = assign['is_core'].values.astype(bool)
own = assign['consensus_own'].values.astype(np.float64)
cm = assign['consensus_membership'].values.astype(np.float64)
K = 6
NAMES = {0: 'MTC_Mitochondrial_OXPHOS', 1: 'PN_Proneural_Progenitor',
         2: 'CL_Classical_EGFR', 3: 'MES_Mesenchymal_Immune',
         4: 'INT_Intermediate_Mixed', 5: 'OLIGO_Neural_Myelin'}

print('training set : all %d patients (%d CORE + %d BOUNDARY)' % (len(y), core.sum(), (~core).sum()))
w = own.copy()                       # weight by how stably each patient belongs
print('sample weights from consensus_own: [%.3f, %.3f]' % (w.min(), w.max()))

# ---------------------------------------------------------------- select C on log-loss
print('\n=== C selection by cross-validated log-loss (5-fold x 10 repeats) ===')
grid = np.logspace(-3, 2, 21)
cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=RNG)
rows = []
for C in grid:
    lls, accs = [], []
    for tr, te in cv.split(E, y):
        m = LogisticRegression(max_iter=5000, C=C, random_state=RNG)
        m.fit(E[tr], y[tr], sample_weight=w[tr])
        p = m.predict_proba(E[te])
        lls.append(log_loss(y[te], p, labels=list(range(K))))
        accs.append(accuracy_score(y[te], p.argmax(1)))
    rows.append((C, np.mean(lls), np.mean(accs)))
    print(f'  C={C:9.4f}   logloss={np.mean(lls):.4f}   accuracy={np.mean(accs):.4f}')
rows = np.array(rows)
best_C = float(rows[rows[:, 1].argmin(), 0])
print(f'\n>>> chosen C = {best_C:.4f}  (minimum cross-validated log-loss)')
print(f'    C that would maximise accuracy instead = {rows[rows[:, 2].argmax(), 0]:.4f}')

# ---------------------------------------------------------------- out-of-fold logits
skf = StratifiedKFold(5, shuffle=True, random_state=RNG)
base = LogisticRegression(max_iter=5000, C=best_C, random_state=RNG)
oof_logit = np.zeros((len(y), K))
for tr, te in skf.split(E, y):
    m = LogisticRegression(max_iter=5000, C=best_C, random_state=RNG)
    m.fit(E[tr], y[tr], sample_weight=w[tr])
    oof_logit[te] = m.decision_function(E[te])

# ---------------------------------------------------------------- temperature scaling
def top_prob(logit, T):
    return softmax(logit / T, axis=1).max(1)

def obj(logT):
    T = np.exp(logT)
    return float(((top_prob(oof_logit, T) - own) ** 2).mean())

res = minimize_scalar(obj, bounds=(np.log(0.2), np.log(200.0)), method='bounded')
T = float(np.exp(res.x))
print(f'\n=== temperature scaling ===')
print(f'fitted T = {T:.4f}   (T>1 softens; T=1 would be no change)')
print(f'RMSE(top-class prob vs consensus_own): before {np.sqrt(((top_prob(oof_logit,1.0)-own)**2).mean()):.4f}'
      f'   after {np.sqrt(obj(np.log(T))):.4f}')

# ---------------------------------------------------------------- final fit
final = LogisticRegression(max_iter=5000, C=best_C, random_state=RNG)
final.fit(E, y, sample_weight=w)
logit_full = final.decision_function(E)
P = softmax(logit_full / T, axis=1)
pred = P.argmax(1)
top = P.max(1)
srt = np.sort(P, axis=1)
margin = srt[:, -1] - srt[:, -2]

print('\n=== IN-SAMPLE BEHAVIOUR (the round-trip the user asked for) ===')
print(f'reproduces the recorded cluster : {(pred == y).mean() * 100:.2f}%  ({(pred == y).sum()}/328)')
print(f'  on CORE     : {(pred[core] == y[core]).mean() * 100:.2f}%')
print(f'  on BOUNDARY : {(pred[~core] == y[~core]).mean() * 100:.2f}%')

print('\n=== REPORTED PERCENTAGE — new model ===')
print(f'  mean {top.mean():.4f}   median {np.median(top):.4f}   range [{top.min():.4f}, {top.max():.4f}]')
print(f'  >= 0.99   : {(top >= .99).sum():3d} / 328')
print(f'  >= 0.999  : {(top >= .999).sum():3d} / 328')
print(f'  CORE     mean {top[core].mean():.4f}')
print(f'  BOUNDARY mean {top[~core].mean():.4f}')
print(f'  correlation with consensus_own        : {np.corrcoef(top, own)[0,1]:+.4f}')
print(f'  correlation with consensus_membership : {np.corrcoef(top, cm)[0,1]:+.4f}')

print('\nconfidence histogram (new model):')
bins = [0, .3, .4, .5, .6, .7, .8, .9, .95, .99, 1.0001]
h, _ = np.histogram(top, bins=bins)
for i in range(len(h)):
    print(f'  [{bins[i]:.2f}, {bins[i+1]:.2f})  {h[i]:4d}  {"#" * int(h[i] / 2)}')

# ---------------------------------------------------------------- leave-one-out
print('\n=== LEAVE-ONE-OUT (honest generalisation) ===')
loo_pred = np.zeros(len(y), int); loo_top = np.zeros(len(y))
for i in range(len(y)):
    tr = np.ones(len(y), bool); tr[i] = False
    m = LogisticRegression(max_iter=5000, C=best_C, random_state=RNG)
    m.fit(E[tr], y[tr], sample_weight=w[tr])
    p = softmax(m.decision_function(E[i:i+1]) / T, axis=1)[0]
    loo_pred[i] = p.argmax(); loo_top[i] = p.max()
print(f'LOO agreement all 328 : {(loo_pred == y).mean() * 100:.2f}%')
print(f'  CORE                : {(loo_pred[core] == y[core]).mean() * 100:.2f}%')
print(f'  BOUNDARY            : {(loo_pred[~core] == y[~core]).mean() * 100:.2f}%')

# ---------------------------------------------------------------- calibration quality
def ece(conf, correct, nbins=10):
    b = np.linspace(0, 1, nbins + 1); e = 0.0; rowsb = []
    for i in range(nbins):
        m = (conf >= b[i]) & (conf < b[i + 1] if i < nbins - 1 else conf <= 1.0)
        if m.sum() == 0:
            rowsb.append((b[i], b[i+1], 0, np.nan, np.nan)); continue
        acc = correct[m].mean(); cf = conf[m].mean()
        e += m.mean() * abs(acc - cf)
        rowsb.append((b[i], b[i+1], int(m.sum()), cf, acc))
    return e, rowsb

oldP = np.load('old_proba.npy')
old_top = oldP.max(1); old_ok = (oldP.argmax(1) == y)
new_ok = (loo_pred == y)
e_old, _ = ece(old_top, old_ok)
e_new, tbl = ece(loo_top, new_ok)
print(f'\nExpected calibration error vs recorded labels: old {e_old:.4f} -> new {e_new:.4f}')
print('\nreliability table (new model, leave-one-out):')
print('  bin              n    mean_conf   observed')
for lo, hi, n, cf, acc in tbl:
    if n:
        print(f'  [{lo:.1f},{hi:.1f})  {n:4d}     {cf:.3f}      {acc:.3f}')

# ---------------------------------------------------------------- freeze
art_old = joblib.load(f'{HX}/10_Prediction_Model/model_artifacts.joblib')
artifacts = {
    'version': '2.0.0',
    'model': final, 'temperature': T, 'C': best_C, 'K': K,
    'cluster_names': NAMES,
    'trained_on': 'all_328_consensus_weighted',
    'n_train': int(len(y)),
    'pca': art_old['pca'],
    'KEEP_mask': art_old['KEEP_mask'], 'NONPOLYA_mask': art_old['NONPOLYA_mask'],
    'batch_means': art_old['batch_means'], 'global_sd': art_old['global_sd'],
    'signature_gene_idx': art_old['signature_gene_idx'],
    'protocol_threshold': art_old['protocol_threshold'],
    'gene_names_filtered': art_old['gene_names_filtered'],
    'gene_types_filtered': art_old['gene_types_filtered'],
    'lowexpr_gene_ids': art_old['lowexpr_gene_ids'],
    'insample_agreement': float((pred == y).mean()),
    'loo_agreement': float((loo_pred == y).mean()),
    'loo_agreement_core': float((loo_pred[core] == y[core]).mean()),
    'loo_agreement_boundary': float((loo_pred[~core] == y[~core]).mean()),
    'conf_corr_consensus_own': float(np.corrcoef(top, own)[0, 1]),
    'ece': float(e_new),
    'mean_confidence': float(top.mean()),
}
joblib.dump(artifacts, f'{OUT}/model_artifacts_v2.joblib', compress=3)

metrics = {k: v for k, v in artifacts.items()
           if isinstance(v, (int, float, str))}
metrics['temperature'] = T
metrics['C'] = best_C
json.dump(metrics, open(f'{OUT}/model_metrics_v2.json', 'w'), indent=2)

pd.DataFrame({
    'sample_id': assign['sample_id'], 'cluster_recorded': y,
    'cluster_predicted': pred, 'probability': top.round(4),
    'margin': margin.round(4),
    'loo_predicted': loo_pred, 'loo_probability': loo_top.round(4),
    'consensus_own': own.round(4), 'consensus_membership': cm.round(4),
    'is_core': core,
    **{f'p_{NAMES[c][:3].rstrip("_")}': P[:, c].round(4) for c in range(K)},
}).to_csv(f'{OUT}/training_predictions_v2.csv', index=False)

np.save('new_proba.npy', P)
np.save('loo_top.npy', loo_top)
np.save('loo_pred.npy', loo_pred)
print(f'\nfrozen -> {OUT}/model_artifacts_v2.joblib')

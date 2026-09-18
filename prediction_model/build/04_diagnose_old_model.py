"""
Quantify the saturation: what does the SHIPPED model actually output?
This is the evidence for why a new model is needed.
"""
import numpy as np, pandas as pd, joblib, warnings
warnings.filterwarnings('ignore')

HX = '/mnt/user-data/uploads/TEKNOFEST_ONCOLOGY/new_start/HELIXA/NEW_START_RESULTS'
art = joblib.load(f'{HX}/10_Prediction_Model/model_artifacts.joblib')
assign = pd.read_csv(f'{HX}/04_Consensus_Clustering/final_patient_assignments.csv')
E = np.load('E_rebuilt.npy')

mdl = art['model']
lab = assign['cluster'].values
core = assign['is_core'].values.astype(bool)
cm = assign['consensus_membership'].values
own = assign['consensus_own'].values

P = mdl.predict_proba(E)
top = P.max(1)
pred = P.argmax(1)

print('=' * 74)
print('SHIPPED MODEL  (LogisticRegression, C=1.0, trained on 273 CORE only)')
print('=' * 74)
print(f'agreement with recorded cluster, all 328 : {(pred == lab).mean() * 100:.2f}%')
print(f'agreement on CORE  (n={core.sum()})            : {(pred[core] == lab[core]).mean() * 100:.2f}%')
print(f'agreement on BOUNDARY (n={(~core).sum()})         : {(pred[~core] == lab[~core]).mean() * 100:.2f}%')

print('\nTOP-CLASS PROBABILITY — the number the user sees as "the percentage"')
print(f'  mean        : {top.mean():.4f}')
print(f'  median      : {np.median(top):.4f}')
print(f'  min         : {top.min():.4f}')
for thr in (0.99, 0.999, 0.9999):
    print(f'  >= {thr:<7} : {(top >= thr).sum():3d} / 328  ({(top >= thr).mean() * 100:.1f}%)')

print('\n  on CORE     : mean %.4f   median %.4f' % (top[core].mean(), np.median(top[core])))
print('  on BOUNDARY : mean %.4f   median %.4f' % (top[~core].mean(), np.median(top[~core])))

print('\nWhat the consensus clustering actually recorded for the same patients:')
print(f'  consensus_membership  mean {cm.mean():.4f}  median {np.median(cm):.4f}'
      f'  range [{cm.min():.4f}, {cm.max():.4f}]')
print(f'  consensus_own         mean {own.mean():.4f}  median {np.median(own):.4f}'
      f'  range [{own.min():.4f}, {own.max():.4f}]')

r_cm = np.corrcoef(top, cm)[0, 1]
r_own = np.corrcoef(top, own)[0, 1]
print(f'\ncorrelation of model confidence with consensus_membership : {r_cm:+.4f}')
print(f'correlation of model confidence with consensus_own        : {r_own:+.4f}')
print('\n-> The model reports near-certainty for essentially every patient, including')
print('   the 55 the clustering itself flagged as genuinely ambiguous. Its confidence')
print('   carries almost no information about how sure the clustering actually was.')

# distribution table
print('\nconfidence histogram (shipped model):')
bins = [0, .5, .6, .7, .8, .9, .95, .99, .999, 1.0001]
h, _ = np.histogram(top, bins=bins)
for i in range(len(h)):
    print(f'  [{bins[i]:.3f}, {bins[i+1]:.3f})  {h[i]:4d}  {"#" * int(h[i] / 2)}')

np.save('old_proba.npy', P)

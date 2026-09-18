"""
Which model reproduces the consensus profile best out-of-sample?

The target is a 6-dimensional distribution per patient, so this is scored as a
probability-fitting problem, not a classification problem: RMSE and correlation
against the true consensus profile, plus how often the argmax still lands on the
recorded cluster. Everything is measured out-of-fold.
"""
import warnings
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.neighbors import KNeighborsRegressor
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
warnings.filterwarnings('ignore')

RNG, K = 42, 6
HX = '/mnt/user-data/uploads/TEKNOFEST_ONCOLOGY/new_start/HELIXA/NEW_START_RESULTS'
assign = pd.read_csv(f'{HX}/04_Consensus_Clustering/final_patient_assignments.csv')
E = np.load('E_rebuilt.npy').astype(np.float64)
q = np.load('q_target.npy')
y = assign['cluster'].values.astype(int)
core = assign['is_core'].values.astype(bool)
own = assign['consensus_own'].values
n = len(y)
skf = StratifiedKFold(5, shuffle=True, random_state=RNG)


def norm(P):
    P = np.clip(P, 1e-9, None)
    return P / P.sum(1, keepdims=True)


def oof_logreg(C, poly=1):
    P = np.zeros((n, K))
    for tr, te in skf.split(E, y):
        Xtr, Xte = E[tr], E[te]
        if poly > 1:
            pf = PolynomialFeatures(poly, include_bias=False)
            sc = StandardScaler()
            Xtr = sc.fit_transform(pf.fit_transform(Xtr))
            Xte = sc.transform(pf.transform(Xte))
        Xr = np.repeat(Xtr, K, axis=0)
        yr = np.tile(np.arange(K), Xtr.shape[0])
        wr = q[tr].flatten()
        m = LogisticRegression(max_iter=20000, C=C, random_state=RNG)
        m.fit(Xr, yr, sample_weight=wr)
        P[te] = m.predict_proba(Xte)
    return P


def oof_reg(make):
    P = np.zeros((n, K))
    for tr, te in skf.split(E, y):
        m = make()
        m.fit(E[tr], q[tr])
        P[te] = m.predict(E[te])
    return norm(P)


CANDIDATES = {
    'LogReg 5PC            C=0.32': lambda: oof_logreg(0.32),
    'LogReg 5PC            C=3.2': lambda: oof_logreg(3.2),
    'LogReg poly2          C=1': lambda: oof_logreg(1.0, poly=2),
    'LogReg poly2          C=10': lambda: oof_logreg(10.0, poly=2),
    'LogReg poly3          C=1': lambda: oof_logreg(1.0, poly=3),
    'kNN k=10  distance': lambda: oof_reg(lambda: KNeighborsRegressor(10, weights='distance')),
    'kNN k=20  distance': lambda: oof_reg(lambda: KNeighborsRegressor(20, weights='distance')),
    'kNN k=30  distance': lambda: oof_reg(lambda: KNeighborsRegressor(30, weights='distance')),
    'kNN k=40  distance': lambda: oof_reg(lambda: KNeighborsRegressor(40, weights='distance')),
    'kNN k=25  uniform': lambda: oof_reg(lambda: KNeighborsRegressor(25, weights='uniform')),
    'RandomForest 500': lambda: oof_reg(lambda: RandomForestRegressor(500, random_state=RNG, n_jobs=-1)),
    'ExtraTrees 500': lambda: oof_reg(lambda: ExtraTreesRegressor(500, random_state=RNG, n_jobs=-1)),
}

print('%-30s %8s %9s %9s %9s %8s' %
      ('model', 'RMSE', 'corr_all', 'corr_top', 'MAE_top', 'argmax'))
print('-' * 80)
results = {}
for name, fn in CANDIDATES.items():
    P = fn()
    rmse = float(np.sqrt(((P - q) ** 2).mean()))
    corr_all = float(np.corrcoef(P.flatten(), q.flatten())[0, 1])
    top = P.argmax(1)
    corr_top = float(np.corrcoef(P.max(1), q[np.arange(n), top])[0, 1])
    mae_top = float(np.abs(P.max(1) - q[np.arange(n), top]).mean())
    acc = float((top == y).mean())
    results[name] = (P, rmse, corr_all, corr_top, mae_top, acc)
    print('%-30s %8.4f %9.4f %9.4f %9.4f %8.4f' % (name, rmse, corr_all, corr_top, mae_top, acc))

best = min(results, key=lambda k: results[k][1])
print('-' * 80)
print(f'>>> lowest out-of-fold profile RMSE: {best}')
P = results[best][0]
print(f'    argmax agreement  all {(P.argmax(1)==y).mean()*100:.2f}%  '
      f'CORE {(P.argmax(1)==y)[core].mean()*100:.2f}%  '
      f'BOUNDARY {(P.argmax(1)==y)[~core].mean()*100:.2f}%')
print(f'    corr(top prob, consensus_own) = {np.corrcoef(P.max(1), own)[0,1]:+.4f}')
print(f'    confidence: mean {P.max(1).mean():.4f} median {np.median(P.max(1)):.4f} '
      f'range [{P.max(1).min():.4f}, {P.max(1).max():.4f}]')
np.save('best_oof.npy', P)
with open('best_model_name.txt', 'w') as f:
    f.write(best)

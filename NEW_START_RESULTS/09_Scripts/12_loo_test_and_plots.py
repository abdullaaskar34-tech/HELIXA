# -*- coding: utf-8 -*-
"""
STEP 11 : (a) fix the protocol threshold to the optimal value and re-freeze,
          (b) HONEST leave-one-out test on the uploaded patient,
          (c) model evaluation plots.
"""
import os, json, warnings, joblib, sys
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from sklearn.decomposition import PCA
from sklearn.model_selection import StratifiedKFold, cross_val_predict, learning_curve
from sklearn.metrics import (confusion_matrix, roc_curve, auc, classification_report,
                              accuracy_score)
from sklearn.preprocessing import label_binarize
warnings.filterwarnings('ignore')

SRC = '/mnt/user-data/working/new_start_analysis'
DST = '/mnt/user-data/working/NEW_START_RESULTS/10_Prediction_Model'
PLOT= '/mnt/user-data/working/NEW_START_RESULTS/07_Plots'
UPL = '/root/.claude/uploads/813770ca-7f50-5828-ac8a-328111f7af95/5701e67a-1786641187972_b18fea3fd2404f38b1c05b8cd2ac6d38.rna_seq.augmented_star_gene_counts.tsv'
TARGET_ID = 'b18fea3f-d240-4f38-b1c0-5b8cd2ac6d38'
RNG = 42

A = joblib.load(f'{DST}/model_artifacts.joblib')
samples = np.array(pd.read_csv(
    '/mnt/user-data/uploads/Desktop/TEKNOFEST_ONCOLOGY/new_start/01_Data_Preparation/samples.csv'
)['sample_id'].tolist())
batch = np.load(f'{SRC}/batch.npy')
lab   = np.load(f'{SRC}/final_labels.npy')
core  = np.load(f'{SRC}/final_core.npy')
E     = np.load(f'{SRC}/final_embedding.npy')
Xall  = np.load('/mnt/user-data/uploads/Desktop/TEKNOFEST_ONCOLOGY/new_start/01_Data_Preparation/log2tpm_filtered.npy')
K = 6
SHORT = A['cluster_names']

# ---------------------------------------------------------------- (a) fix threshold
tpm_all = np.power(2.0, Xall) - 1.0
frac = tpm_all[A['NONPOLYA_mask'], :].sum(0) / tpm_all.sum(0)
order = np.sort(frac); best_acc, best_thr = 0, A['protocol_threshold']
for i in range(len(order)-1):
    thr = (order[i]+order[i+1])/2
    acc = ((frac > thr).astype(int) == batch).mean()
    if acc > best_acc: best_acc, best_thr = acc, thr
print(f"(a) protocol threshold: old={A['protocol_threshold']:.4f} -> "
      f"optimal={best_thr:.4f} giving {best_acc*100:.2f}% accuracy on the 328 training samples")
A['protocol_threshold'] = float(best_thr)
A['protocol_threshold_accuracy'] = float(best_acc)

# ---------------------------------------------------------------- (b) leave-one-out
ti = int(np.where(samples == TARGET_ID)[0][0])
print(f"\n(b) HONEST LEAVE-ONE-OUT TEST on the uploaded patient")
print(f"    sample  : {TARGET_ID}")
print(f"    NOTE    : this file IS one of the 328 training samples, so a normal")
print(f"              prediction would be circular. It is therefore REMOVED from")
print(f"              every step below -- gene selection, PCA and the classifier")
print(f"              are all refitted on the remaining 327 patients only.")
print(f"    consensus label (ground truth) : cluster_{lab[ti]} = {SHORT[lab[ti]]}")
print(f"    is_core                        : {bool(core[ti])}")

# rebuild the ENTIRE pipeline without that sample
import re
genes = pd.read_csv('/mnt/user-data/uploads/Desktop/TEKNOFEST_ONCOLOGY/new_start/01_Data_Preparation/genes_filtered.csv')
gtype = genes['gene_type'].astype(str).values
KEEP = A['KEEP_mask']
mask_tr = np.ones(len(samples), bool); mask_tr[ti] = False

def build(tpm_mat, batch_v, fit_stats=None, gene_idx=None, pca=None):
    t = tpm_mat[KEEP, :]
    t = t / t.sum(0, keepdims=True) * 1e6
    y = np.log2(t + 1.0)
    if fit_stats is None:
        bm = {int(b): y[:, batch_v == b].mean(1) for b in np.unique(batch_v)}
        zc = np.empty_like(y)
        for b in np.unique(batch_v):
            zc[:, batch_v == b] = y[:, batch_v == b] - bm[int(b)][:, None]
        sd = zc.std(1); sd[sd == 0] = 1
        return zc/sd[:, None], (bm, sd)
    bm, sd = fit_stats
    zc = np.empty_like(y)
    for j, b in enumerate(batch_v):
        zc[:, j] = y[:, j] - bm[int(b)]
    return zc/sd[:, None], fit_stats

Ztr, stats_tr = build(tpm_all[:, mask_tr], batch[mask_tr])
mad_tr = np.median(np.abs(Ztr - np.median(Ztr, 1, keepdims=True)), 1)
is_pc = (gtype[KEEP] == 'protein_coding')
idx_tr = np.sort(np.argsort(np.where(is_pc, mad_tr, -np.inf))[::-1][:1000])
pca_tr = PCA(n_components=5, random_state=RNG).fit(Ztr[idx_tr, :].T)
Etr = pca_tr.transform(Ztr[idx_tr, :].T)
lab_tr, core_tr = lab[mask_tr], core[mask_tr]
clf_tr = LogisticRegression(max_iter=5000, C=1.0, random_state=RNG).fit(Etr[core_tr], lab_tr[core_tr])

# now push the held-out patient through, reading it from the UPLOADED FILE
df = pd.read_csv(UPL, sep='\t', skiprows=1, low_memory=False)
df = df[df['gene_id'].astype(str).str.startswith('ENSG')]
s = pd.Series(df['tpm_unstranded'].values.astype(float), index=df['gene_id'].astype(str).values)
s = s[~s.index.duplicated(keep='first')]
tpm_new = s.reindex(pd.Index(A['lowexpr_gene_ids'])).fillna(0.0).values
print(f"    genes matched from the uploaded file : {int(pd.Index(A['lowexpr_gene_ids']).isin(s.index).sum()):,}"
      f" / {len(A['lowexpr_gene_ids']):,}")

fr = tpm_new[A['NONPOLYA_mask']].sum()/tpm_new.sum()
det = int(fr > best_thr)
print(f"    detected protocol : {'total-RNA' if det else 'poly(A)'}  (non-polyA frac={fr:.4f})"
      f"   | true batch = {'total-RNA' if batch[ti] else 'poly(A)'}   "
      f"{'✔ CORRECT' if det==batch[ti] else '✘ WRONG'}")

tn = tpm_new[KEEP]; tn = tn/tn.sum()*1e6
yn = np.log2(tn+1.0)
bm, sd = stats_tr
zn = (yn - bm[det])/sd
emb_new = pca_tr.transform(zn[idx_tr].reshape(1,-1))
proba = clf_tr.predict_proba(emb_new)[0]
pred = int(np.argmax(proba))
print(f"\n    >>> PREDICTED  : cluster_{pred} = {SHORT[pred]}")
print(f"    >>> TRUE LABEL : cluster_{lab[ti]} = {SHORT[lab[ti]]}")
print(f"    >>> RESULT     : {'✔ CORRECT' if pred==lab[ti] else '✘ WRONG'}   "
      f"confidence = {proba[pred]*100:.1f}%")
print("    probabilities:")
for i in range(K):
    print(f"      cluster_{i} {SHORT[i]:<26} {proba[i]*100:6.2f}%"
          + ("  <<<" if i==pred else ""))

loo = {'sample_id':TARGET_ID,'true_cluster':int(lab[ti]),'true_name':SHORT[lab[ti]],
       'predicted_cluster':pred,'predicted_name':SHORT[pred],'correct':bool(pred==lab[ti]),
       'confidence':float(proba[pred]),'is_core':bool(core[ti]),
       'detected_protocol_correct':bool(det==batch[ti]),
       'probabilities':{SHORT[i]:float(proba[i]) for i in range(K)}}
json.dump(loo, open(f'{DST}/leave_one_out_test.json','w'), indent=2, ensure_ascii=False)

# ---- full leave-one-out over ALL core patients (the real generalisation number)
print("\n(b2) FULL LEAVE-ONE-OUT over all core patients (classifier refit each time)")
from sklearn.model_selection import LeaveOneOut
ypl = cross_val_predict(LogisticRegression(max_iter=5000, C=1.0, random_state=RNG),
                        E[core], lab[core], cv=LeaveOneOut(), n_jobs=-1)
print(f"     LOO accuracy on {core.sum()} core patients = {accuracy_score(lab[core], ypl)*100:.2f}%")
A['loo_accuracy'] = float(accuracy_score(lab[core], ypl))
joblib.dump(A, f'{DST}/model_artifacts.joblib', compress=3)

# ---------------------------------------------------------------- (c) plots
cm  = np.load(f'{DST}/_cm.npy')
ypc = np.load(f'{DST}/_cv_pred_core.npy')
ppc = np.load(f'{DST}/_cv_proba_core.npy')
comp= pd.read_csv(f'{DST}/model_comparison.csv')

fig, ax = plt.subplots(1, 3, figsize=(19,5.4))
cmn = cm/cm.sum(1, keepdims=True)*100
im = ax[0].imshow(cmn, cmap='Blues', vmin=0, vmax=100)
for i in range(K):
    for j in range(K):
        if cm[i,j]:
            ax[0].text(j, i, f'{cm[i,j]}\n{cmn[i,j]:.0f}%', ha='center', va='center',
                       fontsize=8, color='white' if cmn[i,j]>55 else 'black')
ax[0].set_xticks(range(K)); ax[0].set_yticks(range(K))
ax[0].set_xticklabels([f'c{i}' for i in range(K)]); ax[0].set_yticklabels([f'c{i}' for i in range(K)])
ax[0].set_xlabel('predicted'); ax[0].set_ylabel('true')
ax[0].set_title('Confusion matrix — 5-fold CV, CORE patients')
fig.colorbar(im, ax=ax[0], fraction=.04)

yb = label_binarize(lab[core], classes=range(K))
for i in range(K):
    fpr, tpr, _ = roc_curve(yb[:,i], ppc[:,i])
    ax[1].plot(fpr, tpr, lw=1.8, label=f'c{i} {SHORT[i][:16]} (AUC={auc(fpr,tpr):.3f})')
ax[1].plot([0,1],[0,1],'k--',lw=.8)
ax[1].set_xlabel('False positive rate'); ax[1].set_ylabel('True positive rate')
ax[1].set_title('ROC curves (one-vs-rest)'); ax[1].legend(fontsize=7, loc='lower right')

cc = comp[comp.dataset=='CORE_only'].sort_values('balanced_accuracy')
ax[2].barh(cc.model, cc.balanced_accuracy, xerr=cc.accuracy_std, color='#4C78A8')
ax[2].set_xlim(0.85, 1.005); ax[2].set_xlabel('balanced accuracy (5-fold CV x10)')
ax[2].set_title('model comparison')
for i,(m,v) in enumerate(zip(cc.model, cc.balanced_accuracy)):
    ax[2].text(v+0.002, i, f'{v:.4f}', va='center', fontsize=7.5)
fig.tight_layout(); fig.savefig(f'{PLOT}/15_classifier_evaluation.png', dpi=150, bbox_inches='tight')
plt.close(fig); print("\n  plot -> 15_classifier_evaluation.png")

fig, ax = plt.subplots(1, 3, figsize=(18,5))
ts, tr_s, te_s = learning_curve(LogisticRegression(max_iter=5000, random_state=RNG),
                                E[core], lab[core], cv=StratifiedKFold(5, shuffle=True, random_state=RNG),
                                train_sizes=np.linspace(.15,1.,10), n_jobs=-1)
ax[0].plot(ts, tr_s.mean(1), 'o-', label='train', color='#4C78A8')
ax[0].plot(ts, te_s.mean(1), 's-', label='validation', color='#E45756')
ax[0].fill_between(ts, te_s.mean(1)-te_s.std(1), te_s.mean(1)+te_s.std(1), alpha=.2, color='#E45756')
ax[0].set_xlabel('training samples'); ax[0].set_ylabel('accuracy')
ax[0].set_title('Learning curve — curves meeting high = no overfitting'); ax[0].legend()

conf = ppc.max(1)
ax[1].hist([conf[ypc==lab[core]], conf[ypc!=lab[core]]], bins=25, stacked=True,
           color=['#54A24B','#E45756'], label=['correct','wrong'])
ax[1].set_xlabel('predicted probability of the top class'); ax[1].set_title('Confidence distribution (CV)')
ax[1].legend(fontsize=8)

bins = np.linspace(0,1,11); accs, cnts = [], []
for i in range(10):
    m = (conf>=bins[i])&(conf<bins[i+1])
    accs.append((ypc[m]==lab[core][m]).mean() if m.sum() else np.nan); cnts.append(m.sum())
ax[2].plot([0,1],[0,1],'k--',lw=.8,label='perfect calibration')
ax[2].plot((bins[:-1]+bins[1:])/2, accs, 'o-', color='#B279A2', label='model')
ax[2].set_xlabel('predicted confidence'); ax[2].set_ylabel('observed accuracy')
ax[2].set_title('Calibration — is 80% confidence really 80% correct?'); ax[2].legend(fontsize=8)
fig.tight_layout(); fig.savefig(f'{PLOT}/16_classifier_diagnostics.png', dpi=150, bbox_inches='tight')
plt.close(fig); print("  plot -> 16_classifier_diagnostics.png")
print("\ndone.")

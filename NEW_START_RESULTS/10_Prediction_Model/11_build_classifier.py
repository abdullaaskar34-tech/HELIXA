# -*- coding: utf-8 -*-
"""
STEP 10 : SUPERVISED CLASSIFIER  -- assign a BRAND NEW patient to one of the 6 subtypes

THE HARD PART, AND WHY A NAIVE CLASSIFIER WOULD FAIL SILENTLY:
A new patient's TSV can come from EITHER library-prep protocol. If we just feed
raw TPM into a model trained on corrected data, a total-RNA sample would arrive
with every mRNA compressed ~2x and be mis-assigned with high confidence. So the
inference pipeline must reproduce, for one single sample, the exact same
correction that was applied to the training cohort:

  1. parse TSV -> tpm_unstranded
  2. DETECT THE PROTOCOL automatically from the non-polyA RNA fraction
     (step-3 diagnostics proved one threshold separates them with 100% accuracy)
  3. restrict to the 25,738 protocol-robust genes
  4. re-normalise to a 1e6 budget over THAT gene space
  5. log2(x+1)
  6. subtract the STORED training mean of the DETECTED batch, divide by the
     STORED global SD  (never re-estimated from the new sample -- a single
     sample has no batch of its own)
  7. take the 1000 signature genes, project onto the STORED 5-component PCA
  8. predict + return calibrated probabilities

Everything the pipeline needs is frozen into model_artifacts.joblib so inference
never touches the training data again.
"""
import os, json, re, warnings, joblib
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.model_selection import (StratifiedKFold, cross_val_score, cross_val_predict,
                                      RepeatedStratifiedKFold, learning_curve)
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, f1_score,
                              classification_report, confusion_matrix, roc_auc_score,
                              cohen_kappa_score, roc_curve)
from sklearn.preprocessing import label_binarize
warnings.filterwarnings('ignore')

SRC = '/mnt/user-data/working/new_start_analysis'
UP  = '/mnt/user-data/uploads/Desktop/TEKNOFEST_ONCOLOGY/new_start/01_Data_Preparation'
DST = '/mnt/user-data/working/NEW_START_RESULTS/10_Prediction_Model'
os.makedirs(DST, exist_ok=True)
RNG = 42

# ------------------------------------------------------------------ rebuild state
Xall  = np.load(f'{UP}/log2tpm_filtered.npy')
genes = pd.read_csv(f'{UP}/genes_filtered.csv')
gname_all = genes['gene_name'].astype(str).values
gtype_all = genes['gene_type'].astype(str).values
samples = np.array(pd.read_csv(f'{UP}/samples.csv')['sample_id'].tolist())
batch = np.load(f'{SRC}/batch.npy')
lab   = np.load(f'{SRC}/final_labels.npy')
core  = np.load(f'{SRC}/final_core.npy')
E     = np.load(f'{SRC}/final_embedding.npy')
gene_idx = np.load(f'{SRC}/final_gene_idx.npy')
K = 6

hist_re = re.compile(r'^(H1-\d+|H2A[CB]?\d+|H2B[CB]?\d+|H3C\d+|H4C\d+|H2AC\d+|H2BC\d+|H3-\d+|H4-\d+)$')
is_hist = np.array([bool(hist_re.match(g)) for g in gname_all])
is_7sk  = np.array([g.startswith('RN7SK') or g=='7SK' for g in gname_all])
is_7sl  = np.array([g.startswith('RN7SL') for g in gname_all])
is_mt   = np.array([g.startswith('MT-') for g in gname_all])
is_sno  = np.isin(gtype_all,['snoRNA','scaRNA','snRNA','misc_RNA','rRNA','rRNA_pseudogene',
                             'Mt_rRNA','Mt_tRNA','vault_RNA','sRNA','scRNA','ribozyme'])
BAD  = is_hist|is_7sk|is_7sl|is_mt|is_sno
KEEP = ~BAD
NONPOLYA_DETECTOR = is_hist|is_7sk|is_7sl|is_sno      # used for protocol detection

# reproduce training-space stats exactly
tpm = np.power(2.0, Xall)-1.0
tpm_k = tpm[KEEP,:]; tpm_k = tpm_k/tpm_k.sum(0,keepdims=True)*1e6
Y = np.log2(tpm_k+1.0).astype(np.float32)
batch_means = {int(b): Y[:, batch==b].mean(1) for b in np.unique(batch)}
Zc = np.empty_like(Y)
for b in np.unique(batch):
    Zc[:, batch==b] = Y[:, batch==b] - batch_means[int(b)][:,None]
global_sd = Zc.std(1); global_sd[global_sd==0] = 1.0
Z = Zc/global_sd[:,None]

from sklearn.decomposition import PCA
pca = PCA(n_components=5, random_state=RNG).fit(Z[gene_idx,:].T)
Efit = pca.transform(Z[gene_idx,:].T)
assert np.allclose(Efit, E, atol=1e-4), "PCA reconstruction mismatch"
print("Training-state reconstruction verified against saved embedding.")

# protocol-detection threshold, re-derived and reported
frac = tpm[NONPOLYA_DETECTOR,:].sum(0)/tpm.sum(0)
lo, hi = frac[batch==0].max(), frac[batch==1].min()
THRESH = float((lo+hi)/2)
print(f"Protocol detector: polyA max={lo:.4f}, totalRNA min={hi:.4f} -> threshold={THRESH:.4f} "
      f"(clean gap, {((frac>THRESH).astype(int)==batch).mean()*100:.1f}% accuracy on training data)")

# ------------------------------------------------------------------ model comparison
MODELS = {
 'LogisticRegression': LogisticRegression(max_iter=5000, C=1.0, random_state=RNG),
 'LDA'               : LinearDiscriminantAnalysis(),
 'SVM_rbf'           : SVC(kernel='rbf', C=10, gamma='scale', probability=True, random_state=RNG),
 'RandomForest'      : RandomForestClassifier(n_estimators=1000, random_state=RNG, n_jobs=-1),
 'ExtraTrees'        : ExtraTreesClassifier(n_estimators=1000, random_state=RNG, n_jobs=-1),
 'GradientBoosting'  : GradientBoostingClassifier(random_state=RNG),
 'kNN_k5'            : KNeighborsClassifier(n_neighbors=5),
 'kNN_k11'           : KNeighborsClassifier(n_neighbors=11),
}

def evaluate(Xd, yd, tag):
    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=RNG)
    rows = []
    print(f"\n=== MODEL COMPARISON on {tag} (n={len(yd)}) — 5-fold CV x 10 repeats ===")
    print(f"{'model':<20}{'accuracy':>18}{'balanced_acc':>16}{'macro_F1':>12}{'kappa':>10}")
    for nm, mdl in MODELS.items():
        acc = cross_val_score(mdl, Xd, yd, cv=cv, scoring='accuracy', n_jobs=-1)
        bal = cross_val_score(mdl, Xd, yd, cv=cv, scoring='balanced_accuracy', n_jobs=-1)
        f1  = cross_val_score(mdl, Xd, yd, cv=cv, scoring='f1_macro', n_jobs=-1)
        cv5 = StratifiedKFold(5, shuffle=True, random_state=RNG)
        kap = cohen_kappa_score(yd, cross_val_predict(mdl, Xd, yd, cv=cv5, n_jobs=-1))
        rows.append({'dataset':tag,'model':nm,'accuracy_mean':round(acc.mean(),4),
                     'accuracy_std':round(acc.std(),4),'balanced_accuracy':round(bal.mean(),4),
                     'macro_F1':round(f1.mean(),4),'cohen_kappa':round(kap,4)})
        print(f"{nm:<20}{acc.mean():>10.4f} ± {acc.std():.4f}{bal.mean():>16.4f}"
              f"{f1.mean():>12.4f}{kap:>10.4f}")
    return pd.DataFrame(rows)

res_core = evaluate(E[core], lab[core], 'CORE_only')
res_all  = evaluate(E,       lab,       'ALL_patients')
comp = pd.concat([res_core, res_all], ignore_index=True)
comp.to_csv(f'{DST}/model_comparison.csv', index=False)

best_name = res_core.sort_values('balanced_accuracy', ascending=False).iloc[0]['model']
print(f"\n>>> BEST MODEL (by balanced accuracy on CORE): {best_name}")
best = MODELS[best_name]

# ------------------------------------------------------------------ detailed eval
cv5 = StratifiedKFold(5, shuffle=True, random_state=RNG)
yp_core = cross_val_predict(best, E[core], lab[core], cv=cv5, n_jobs=-1)
pp_core = cross_val_predict(best, E[core], lab[core], cv=cv5, method='predict_proba', n_jobs=-1)
print(f"\n=== DETAILED CROSS-VALIDATED PERFORMANCE — {best_name} on CORE (n={core.sum()}) ===")
print(classification_report(lab[core], yp_core, digits=4))
cm = confusion_matrix(lab[core], yp_core)
print("Confusion matrix (rows=true, cols=predicted):")
print(cm)
auc_ovr = roc_auc_score(label_binarize(lab[core], classes=range(K)), pp_core,
                        average='macro', multi_class='ovr')
print(f"\nROC-AUC (one-vs-rest, macro) : {auc_ovr:.4f}")
print(f"Cohen's kappa                : {cohen_kappa_score(lab[core], yp_core):.4f}")

# honest generalisation test: train on CORE, predict the BOUNDARY patients
mdl_core = MODELS[best_name].__class__(**MODELS[best_name].get_params()).fit(E[core], lab[core])
yp_bound = mdl_core.predict(E[~core])
pp_bound = mdl_core.predict_proba(E[~core])
agree = (yp_bound == lab[~core]).mean()
print(f"\n=== HELD-OUT-BY-DESIGN TEST: model trained on {core.sum()} CORE, applied to the "
      f"{(~core).sum()} BOUNDARY patients ===")
print(f"  agreement with their consensus label : {agree*100:.1f}%")
print(f"  mean top-class probability            : {pp_bound.max(1).mean():.3f}  "
      f"(vs {pp_core.max(1).mean():.3f} on CORE)")
print("  -> lower confidence on boundary tumours is CORRECT behaviour, not a defect:")
print("     these are the genuinely intermediate cases and the model says so.")

# permutation / null test
from sklearn.model_selection import permutation_test_score
sc, perm, pval = permutation_test_score(best, E[core], lab[core], cv=cv5,
                                        n_permutations=200, random_state=RNG, n_jobs=-1)
print(f"\n=== NULL TEST (200 label permutations) ===")
print(f"  real accuracy = {sc:.4f} | random-label accuracy = {perm.mean():.4f} ± {perm.std():.4f} "
      f"| p = {pval:.2e}")

# ------------------------------------------------------------------ final fit + freeze
FINAL = MODELS[best_name].__class__(**MODELS[best_name].get_params()).fit(E[core], lab[core])
SHORT = {0:'MTC_Mitochondrial_OXPHOS',1:'PN_Proneural_Progenitor',2:'CL_Classical_EGFR',
         3:'MES_Mesenchymal_Immune',4:'INT_Intermediate_Mixed',5:'OLIGO_Neural_Myelin'}
artifacts = {
 'model': FINAL, 'model_name': best_name, 'pca': pca,
 'gene_names_filtered': gname_all, 'gene_types_filtered': gtype_all,
 'KEEP_mask': KEEP, 'NONPOLYA_mask': NONPOLYA_DETECTOR,
 'batch_means': batch_means, 'global_sd': global_sd,
 'signature_gene_idx': gene_idx, 'protocol_threshold': THRESH,
 'cluster_names': SHORT, 'K': K,
 'lowexpr_gene_ids': genes['gene_id'].astype(str).values,
 'train_confidence_mean': float(pp_core.max(1).mean()),
 'cv_accuracy': float(res_core[res_core.model==best_name]['accuracy_mean'].iloc[0]),
 'cv_balanced_accuracy': float(res_core[res_core.model==best_name]['balanced_accuracy'].iloc[0]),
 'cv_macro_f1': float(res_core[res_core.model==best_name]['macro_F1'].iloc[0]),
 'roc_auc_ovr': float(auc_ovr),
}
joblib.dump(artifacts, f'{DST}/model_artifacts.joblib', compress=3)
print(f"\nFrozen -> model_artifacts.joblib ({os.path.getsize(f'{DST}/model_artifacts.joblib')/1e6:.1f} MB)")

json.dump({'best_model':best_name,'cv_accuracy':artifacts['cv_accuracy'],
           'cv_balanced_accuracy':artifacts['cv_balanced_accuracy'],
           'cv_macro_f1':artifacts['cv_macro_f1'],'roc_auc_ovr':float(auc_ovr),
           'cohen_kappa':float(cohen_kappa_score(lab[core],yp_core)),
           'boundary_agreement':float(agree),'permutation_p':float(pval),
           'null_accuracy':float(perm.mean()),'n_train':int(core.sum())},
          open(f'{DST}/model_metrics.json','w'), indent=2)

np.save(f'{DST}/_cv_pred_core.npy', yp_core)
np.save(f'{DST}/_cv_proba_core.npy', pp_core)
np.save(f'{DST}/_cm.npy', cm)
comp.to_csv(f'{DST}/model_comparison.csv', index=False)
pd.DataFrame(classification_report(lab[core], yp_core, output_dict=True)).T.to_csv(
    f'{DST}/classification_report.csv')
print("done.")

# -*- coding: utf-8 -*-
"""
================================================================================
 BIOMARKER ENGINE — STEP 1 of 3 · THE PATIENT SIDE
================================================================================

Question answered here:
    For each of the six subtypes, which genes are switched ON in that subtype
    and not in the other five?

This is deliberately only half the story. A gene being high in a subtype does
NOT mean the tumour needs it — that is exactly the mistake the earlier attempt
made. Step 2 asks the survival question separately, on completely different
data, and step 3 keeps only the genes that pass both.

Method
    · start from the 328 real patients, batch-corrected the same way the
      classifier corrects a new patient (filter to the 25,738 retained genes,
      renormalise to a 1e6 budget, log2, then z-score against the stored mean
      and SD of the patient's own library protocol)
    · discovery uses the 273 CORE patients only. Boundary patients sit between
      subtypes by definition, so including them blurs precisely the contrast
      being measured. All 328 are used afterwards to confirm.
    · Welch t-test of subtype k against the other five, Benjamini-Hochberg FDR
    · Cohen's d for effect size — with 40-70 patients per group a tiny
      difference can be highly significant and still meaningless
    · SPECIFICITY MARGIN: mean z in subtype k minus the highest mean z among
      the other five subtypes. A gene high in three subtypes at once is not a
      biomarker for any of them. This is the column that does the real work.

Run:  python3 01_patient_side.py
================================================================================
"""
import os, json
import numpy as np
import pandas as pd
import joblib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
SRC = os.environ.get('BIO_SRC', '/mnt/user-data/uploads/Desktop/TEKNOFEST_ONCOLOGY/new_start')
RES = os.environ.get('HELIXA_RESULTS', '/mnt/user-data/working/NEW_START_RESULTS')
OUT = os.path.join(ROOT, '05_Tables')
os.makedirs(OUT, exist_ok=True)

SUB = {0: 'MTC', 1: 'PN', 2: 'CL', 3: 'MES', 4: 'INT', 5: 'OLIGO'}
FULL = {0: 'MTC — Mitochondrial / OXPHOS', 1: 'PN — Proneural Progenitor',
        2: 'CL — Classical EGFR', 3: 'MES — Mesenchymal Immune',
        4: 'INT — Intermediate Mixed', 5: 'OLIGO — Neural / Myelin'}

print('=' * 78)
print(' BIOMARKER ENGINE · STEP 1 — what each subtype switches on')
print('=' * 78)

# ── the cohort, corrected exactly as the classifier corrects it ────────────
A = joblib.load(os.path.join(RES, '10_Prediction_Model', 'model_artifacts.joblib'))
X = np.load(os.path.join(SRC, '01_Data_Preparation', 'log2tpm_ALL.npy')).astype(np.float64)
samples = pd.read_csv(os.path.join(SRC, '01_Data_Preparation', 'samples.csv'))['sample_id'].tolist()
asg = (pd.read_csv(os.path.join(SRC, 'NEW_START_RESULTS', '04_Consensus_Clustering',
                                'final_patient_assignments.csv'))
       .set_index('sample_id').loc[samples].reset_index())

KEEP = np.asarray(A['KEEP_mask'], dtype=bool)
names = np.asarray(A['gene_names_filtered']).astype(str)[KEEP]
gid = np.asarray(A["lowexpr_gene_ids"]).astype(str)[KEEP]
gtype = np.asarray(A['gene_types_filtered']).astype(str)[KEEP]
batch = (asg.library_batch.values == 'totalRNA_rRNAdepleted').astype(int)
cl = asg.cluster.values.astype(int)
core = asg.is_core.values.astype(bool)

# X holds all 60,660 loci; the model works on the 27,777 that survived the
# low-expression filter, then on the 25,738 of those the batch filter retains.
all_ids = pd.read_csv(os.path.join(SRC, '01_Data_Preparation', 'genes_ALL.csv')).gene_id.astype(str).values
pos = {g: i for i, g in enumerate(all_ids)}
lowexpr = np.asarray(A['lowexpr_gene_ids']).astype(str)
sel = np.array([pos[g] for g in lowexpr])
X = X[sel]                                   # 27,777 x 328, in the model's own order
print(f'aligned to the model gene space: {X.shape[0]:,} loci -> {int(KEEP.sum()):,} retained')

tpm = np.exp2(X) - 1.0                       # back to TPM
tpm = tpm[KEEP]
tpm *= 1e6 / tpm.sum(axis=0, keepdims=True)  # renormalise on the retained genes
Y = np.log2(tpm + 1.0)
Z = np.empty_like(Y)
for b in (0, 1):
    m = batch == b
    Z[:, m] = (Y[:, m] - A['batch_means'][b][:, None]) / A['global_sd'][:, None]
print(f'cohort            : {Z.shape[1]} patients x {Z.shape[0]:,} genes (batch-corrected)')
print(f'discovery set     : {core.sum()} core patients ({(~core).sum()} boundary held back)')
print(f'residual batch    : mean |t| across genes = '
      f'{np.abs((Z[:, batch==1].mean(1)-Z[:, batch==0].mean(1)) / (Z.std(1)+1e-9)).mean():.4f}')

# ── per-subtype contrast ───────────────────────────────────────────────────
def bh(p):
    p = np.asarray(p); n = len(p); o = np.argsort(p)
    q = np.empty(n); q[o] = np.minimum.accumulate((p[o] * n / np.arange(1, n + 1))[::-1])[::-1]
    return np.clip(q, 0, 1)

Zc = Z[:, core]; clc = cl[core]
means = np.stack([Zc[:, clc == k].mean(1) for k in range(6)])       # 6 x genes
rows = []
for k in range(6):
    a, b_ = Zc[:, clc == k], Zc[:, clc != k]
    na, nb = a.shape[1], b_.shape[1]
    ma, mb = a.mean(1), b_.mean(1)
    va, vb = a.var(1, ddof=1), b_.var(1, ddof=1)
    se = np.sqrt(va / na + vb / nb) + 1e-12
    t = (ma - mb) / se
    dof = (va / na + vb / nb) ** 2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1) + 1e-30)
    from scipy import stats
    p = 2 * stats.t.sf(np.abs(t), dof)
    d = (ma - mb) / (np.sqrt((va + vb) / 2) + 1e-12)
    other = np.delete(means, k, axis=0).max(axis=0)
    rows.append(pd.DataFrame(dict(
        cluster=k, subtype=SUB[k], gene=names, gene_id=gid, gene_type=gtype,
        mean_z_in_class=ma, mean_z_other_classes=mb,
        best_other_class_mean_z=other,
        specificity_margin=ma - other,
        cohens_d=d, t_stat=t, p_value=p, fdr=bh(p),
        n_in_class=na, n_other=nb)))
    q = bh(p)
    up = ((q < 0.05) & (d > 0.5)).sum()
    print(f'  {SUB[k]:<6s} n={na:3d}   genes up at FDR<0.05 & d>0.5 : {int(up):5d}')

de = pd.concat(rows, ignore_index=True)
de.to_csv(os.path.join(OUT, 'patient_side_differential_expression.csv.gz'),
          index=False, compression='gzip')

# also keep the full corrected matrix summary for later figures
np.save(os.path.join(OUT, 'class_mean_z.npy'), means)
pd.DataFrame(dict(gene=names, gene_id=gid, gene_type=gtype)).to_csv(
    os.path.join(OUT, 'gene_index.csv'), index=False)
np.save(os.path.join(OUT, 'z_matrix.npy'), Z.astype(np.float32))
asg.assign(is_core=core).to_csv(os.path.join(OUT, 'patients.csv'), index=False)

print(f'\nwritten -> {OUT}/patient_side_differential_expression.csv.gz  '
      f'({len(de):,} rows)')

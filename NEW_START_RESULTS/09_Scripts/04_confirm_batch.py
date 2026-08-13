# -*- coding: utf-8 -*-
"""
STEP 3c : CONFIRM the dominant 2-way split is a LIBRARY-PREPARATION BATCH EFFECT.

Hypothesis formed from the diagnostic gene list: the genes separating the two
groups are almost exclusively NON-POLYADENYLATED RNA species --
  7SK  (RN7SK*)      : non-polyA Pol-III transcript
  7SL  (RN7SL*)      : non-polyA SRP RNA
  snoRNA / scaRNA / snRNA : non-polyA
  replication-dependent histones (H1-*, H2A*, H2B*, H3C*, H4C*) : the only
        mRNAs in the human genome that are NOT polyadenylated (stem-loop instead)

That exact gene family is retained by rRNA-depletion / total-RNA library prep
and DEPLETED by poly(A)-selection library prep. If the split is driven by this
family, it is a protocol artefact, not tumour biology.

Test: build a single "non-polyA fraction" score per sample and check whether it
is bimodal and whether it predicts the cluster label.
"""
import numpy as np, pandas as pd, json, re
from scipy import stats

UP = '/mnt/user-data/uploads/Desktop/TEKNOFEST_ONCOLOGY/new_start/01_Data_Preparation'
OUT = '/mnt/user-data/working/new_start_analysis'

X = np.load(f'{UP}/log2tpm_filtered.npy')
genes = pd.read_csv(f'{UP}/genes_filtered.csv')
gname = genes['gene_name'].astype(str).values
gtype = genes['gene_type'].astype(str).values
samples = pd.read_csv(f'{UP}/samples.csv')['sample_id'].tolist()

with open(f'{OUT}/sweep_labels.json') as f:
    lab2 = np.array(json.load(f)['MAD_2000_ALL|PC10|KMeans|k2'])

# back to linear TPM for a compositional (fraction-of-library) calculation
tpm = np.power(2.0, X) - 1.0

hist_re = re.compile(r'^(H1-\d+|H2A[CB]?\d+|H2B[CB]?\d+|H3C\d+|H4C\d+|H2AC\d+|H2BC\d+|H3-\d+|H4-\d+)$')
is_hist = np.array([bool(hist_re.match(g)) for g in gname])
is_7sk  = np.array([g.startswith('RN7SK') or g == '7SK' for g in gname])
is_7sl  = np.array([g.startswith('RN7SL') for g in gname])
is_sno  = np.isin(gtype, ['snoRNA', 'scaRNA', 'snRNA', 'misc_RNA'])
is_mt   = np.array([g.startswith('MT-') for g in gname])

NONPOLYA = is_hist | is_7sk | is_7sl | is_sno
print(f"non-polyA-family genes flagged: {NONPOLYA.sum()}  "
      f"(histone={is_hist.sum()}, 7SK={is_7sk.sum()}, 7SL={is_7sl.sum()}, sno/sca/sn/misc={is_sno.sum()})")

total = tpm.sum(axis=0)
frac_nonpolya = tpm[NONPOLYA, :].sum(axis=0) / total
frac_hist     = tpm[is_hist, :].sum(axis=0) / total
frac_mt       = tpm[is_mt, :].sum(axis=0) / total

d = pd.DataFrame({'sample_id': samples, 'cluster_k2': lab2,
                  'frac_nonpolyA': frac_nonpolya,
                  'frac_histone': frac_hist,
                  'frac_mito': frac_mt})
d.to_csv(f'{OUT}/diagnostic_batch_scores.csv', index=False)

print("\n=== non-polyA fraction by cluster ===")
for g in [0, 1]:
    v = frac_nonpolya[lab2 == g]
    print(f"  cluster {g} (n={len(v):3d}) : mean={v.mean():.4f}  median={np.median(v):.4f}  "
          f"min={v.min():.4f}  max={v.max():.4f}")
tt, pp = stats.ttest_ind(frac_nonpolya[lab2==0], frac_nonpolya[lab2==1], equal_var=False)
print(f"  Welch t={tt:.1f}, p={pp:.3e}")

# separability: can a single threshold on this ONE number recover the clustering?
order = np.sort(frac_nonpolya)
best_acc, best_thr = 0, None
for i in range(len(order)-1):
    thr = (order[i] + order[i+1]) / 2
    pred = (frac_nonpolya > thr).astype(int)
    acc = max((pred == lab2).mean(), (1-pred == lab2).mean())
    if acc > best_acc:
        best_acc, best_thr = acc, thr
print(f"\n  >>> A SINGLE THRESHOLD on non-polyA fraction reproduces the k=2 clustering "
      f"with {best_acc*100:.1f}% accuracy (threshold={best_thr:.4f})")

# bimodality (dip-like check via 2-component GMM separation)
from sklearn.mixture import GaussianMixture
gm = GaussianMixture(n_components=2, n_init=20, random_state=0).fit(frac_nonpolya.reshape(-1,1))
mus = np.sort(gm.means_.ravel())
print(f"  bimodal GMM component means: {mus[0]:.4f}  vs  {mus[1]:.4f}   "
      f"(separation = {mus[1]/max(mus[0],1e-9):.1f}x)")

# ---- is there ALSO a global compositional distortion of mRNA? ---------------
pc_only = (gtype == 'protein_coding') & ~is_hist & ~is_mt
frac_mrna = tpm[pc_only, :].sum(axis=0) / total
print("\n=== fraction of library that is ordinary protein-coding mRNA ===")
for g in [0, 1]:
    v = frac_mrna[lab2 == g]
    print(f"  cluster {g}: mean={v.mean():.4f}")
print("  -> if these differ a lot, EVERY mRNA's TPM is compressed in one group")
print("     purely for compositional reasons, which is exactly what the marker")
print("     panels showed (one group higher in ALL panels simultaneously).")

# ---- sex check (pure technical sanity, should NOT track the split) ----------
print("\n=== SEX-GENE SANITY CHECK (should NOT align with the split) ===")
for g in ['XIST', 'RPS4Y1', 'DDX3Y', 'UTY', 'KDM5D']:
    m = np.where(gname == g)[0]
    if len(m) == 0:
        continue
    a, b = X[m[0], lab2==0], X[m[0], lab2==1]
    tt, pp = stats.ttest_ind(a, b, equal_var=False)
    print(f"  {g:<8} grp0={a.mean():6.2f}  grp1={b.mean():6.2f}  t={tt:6.1f}  p={pp:.2e}")

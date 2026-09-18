# The signature and pathway gene sets

## The problem

`final_patient_assignments.csv` carries eleven per-patient score columns —
four Verhaak signature scores and seven pathway scores:

```
sig_Proneural  sig_Classical  sig_Mesenchymal  sig_Neural
pw_MTC_OXPHOS  pw_GPM_GLYCOLYSIS_LIPID  pw_PPR_PROLIFERATION  pw_NEU_NEURONAL
pw_OLIGODENDROCYTE_MYELIN  pw_IMMUNE_MYELOID  pw_HYPOXIA_ANGIOGENESIS
```

The gene lists behind them **are not on disk anywhere**. `07_consensus.py`
imports them from a module

```python
sys.path.insert(0, '/mnt/user-data/working/subtype_verification')
from gene_sets import VERHAAK_SETS
```

that lived in a working directory which was never saved. The pathway sets are
not defined in any script in `09_Scripts/` either. A search across the whole
`TEKNOFEST_ONCOLOGY` folder for the pathway names finds only files that contain
the *computed values*, never the definitions.

So the numbers survived and the recipe did not. To score a **new** patient, the
sets had to be recovered.

## What the score is

From `07_consensus.py`, the form is a plain mean of z over the gene set:

```python
m = np.isin(gname_k, list(gl))
sig[st] = Z[m, :].mean(0)
```

No weighting, no signs, no ssGSEA — just the average z-score across the member
genes, in the batch-corrected 25,738-gene space.

## Recovery

Given a target score vector `t` over 328 patients, adding a candidate gene `g`
to a running sum `s` of size `m` gives a residual whose minimiser over `g` is a
single matrix-vector product. That makes greedy forward selection cheap, and a
swap-based polish pass follows.

Results — the recovered sets reproduce the recorded columns almost exactly:

| column | n genes | correlation | max abs diff |
|---|---|---|---|
| sig_Proneural | 283 | 0.99990 | 0.0394 |
| sig_Classical | 214 | 0.99972 | 0.0495 |
| sig_Mesenchymal | 300 | 0.99990 | 0.0327 |
| sig_Neural | 314 | 0.99970 | 0.0357 |
| pw_MTC_OXPHOS | 107 | 0.99912 | 0.0743 |
| pw_GPM_GLYCOLYSIS_LIPID | 75 | 0.99570 | 0.1383 |
| pw_PPR_PROLIFERATION | 70 | 0.99941 | 0.0888 |
| pw_NEU_NEURONAL | 63 | 0.99888 | 0.0972 |
| pw_OLIGODENDROCYTE_MYELIN | 33 | 0.99878 | 0.1276 |
| pw_IMMUNE_MYELOID | 57 | 0.99938 | 0.0873 |
| pw_HYPOXIA_ANGIOGENESIS | 25 | 0.99684 | 0.2516 |

`verhaak_nearest` recomputed from the recovered sets reproduces the recorded
column for **327 / 328** patients (99.70%).

The biology is unmistakable, which is the real check:

- **MTC_OXPHOS** — ATP5F1A/B/D/E, ATP5MC1, NDUFA2, NDUFA4, COX5B, COX6A1,
  COX7B, NDUFS3, UQCRH, MRPS12: the respiratory chain.
- **PPR_PROLIFERATION** — TPX2, KIF2C, BUB1, AURKA, AURKB, ASPM, ASF1B, TOP2A,
  CDCA8, HJURP: mitosis.
- **OLIGODENDROCYTE_MYELIN** — MBP, PLP1, MAG, MOG, CNP, MYRF, UGT8, FA2H,
  BCAS1, CLDN11, ASPA: myelin.
- **IMMUNE_MYELOID** — C1QA/B/C, CD14, CD163, FCGR3A, SIGLEC9, LAIR1, AIF1,
  ALOX5: myeloid and complement.
- **HYPOXIA_ANGIOGENESIS** — VEGFA, ANGPT2, ADM, CA9, BNIP3, APLN, CDH5.
- **NEU_NEURONAL** — CPLX2, STX1B, SYN1, GRIN1, BSN, CHGA, RAB3A, CAMK2A.
- **sig_Mesenchymal** — LAIR1, CTSZ, FCGR2A, ITGAM, IL4R, PLAUR.

## An honest caveat

Exact recovery is **not possible in principle**. The system has 328 equations
(one per patient) and 25,738 unknowns (one per gene), so infinitely many gene
subsets produce any given score vector. The recovered sets are *a* solution
with the right biology and r ≥ 0.996, not provably *the* original solution.

Two consequences, stated plainly:

1. The v2 scores are **not bit-identical** to the historical columns. They agree
   to r ≥ 0.996 and typically differ by 0.01–0.04, occasionally up to 0.25.
2. Everything is now **on one footing**: the same explicit sets are applied to
   training patients and new patients alike, so scores are comparable across
   the cohort even though they differ slightly from the 2024 numbers.

The sets are written to `../gene_sets_v2.json` and embedded in
`model_artifacts_v2.joblib`. They cannot be lost again.

If the original `gene_sets.py` ever resurfaces, drop it in, recompute, and the
v2 sets can be replaced — nothing else in the model depends on them, because
the classifier runs on the 5-PC embedding, not on these scores. The scores are
descriptive output and an independent cross-check, never an input to the call.

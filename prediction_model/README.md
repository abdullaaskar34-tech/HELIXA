# HELIXA prediction_model · v2 (calibrated)

Assigns a glioblastoma RNA-seq sample to one of the six HELIXA subtypes and
reports **how stably it belongs there**.

This replaces the v1 classifier, which reported ~100% confidence for almost
every patient (median 0.9993; 178 of 328 patients at ≥ 99.9%). v2 reports a
median of 0.7370 with exactly one patient above 99.9%, and its probabilities are
tied to the consensus clustering rather than to the circular hard labels.

---

## Quick start

```bash
python3 predict.py PATIENT.tsv                     # one sample, printed report
python3 predict.py PATIENT.tsv --json out.json     # machine-readable
python3 predict.py *.tsv --csv results.csv         # batch
```

Input is a GDC `augmented_star_gene_counts.tsv` (needs `gene_id` and
`tpm_unstranded`). Either library protocol works — it is detected from the data.

Requires `numpy`, `pandas`, `scikit-learn`, `joblib`.

Example output:

```
  SUBTYPE        PN — PN_Proneural_Progenitor
  PROBABILITY    86.1%   (runner-up OLIGO at 8.6%)
  CALL           CORE   margin 0.775

  subtype stability across resampled clusterings
    PN      86.1%  ##################################
    OLIGO    8.6%  ###
    MTC      3.4%  #
    CL       1.5%  #
    INT      0.4%
    MES      0.0%

  LIBRARY BATCH  polyA_selected   (non-polyA fraction 0.0089 vs threshold 0.0918)
  VERHAAK NEAREST  Proneural
```

## What you get back

| field | meaning |
|---|---|
| `cluster`, `subtype` | the call (0–5 / MTC, PN, CL, MES, INT, OLIGO) |
| `probability` | subtype stability for the winning subtype |
| `probabilities` | all six, summing to 1 |
| `margin`, `call` | gap to the runner-up; `CORE` if ≥ 0.50, else `BOUNDARY` |
| `library_batch` | detected protocol, with the fraction and threshold used |
| `signature_scores` | Verhaak Proneural / Classical / Mesenchymal / Neural |
| `verhaak_nearest` | highest of those four |
| `pathway_scores` | MTC-OXPHOS, GPM, PPR, NEU, OLIGO-myelin, immune-myeloid, hypoxia |
| `embedding` | position in the 5-D space |
| `coverage_pct` | fraction of the 27,777 expected genes matched |
| `recorded_*` | if the sample is one of the 328, its recorded assignment |

## What the percentage means

> **"73% CL" means this expression profile co-clusters with Classical in about
> 73% of resampled clusterings.**

It measures **subtype stability**, not clinical probability. Read it as ±0.11 —
the out-of-sample mean absolute error. It says nothing about prognosis or
treatment response. Full discussion in
[`EXPLANATION/07_WHAT_THE_PERCENTAGE_MEANS.md`](EXPLANATION/07_WHAT_THE_PERCENTAGE_MEANS.md).

## How it differs from v1

| | v1 | v2 |
|---|---|---|
| trained on | 273 CORE only | **all 328** |
| target | hard cluster labels | **soft consensus profile** |
| model selected by | accuracy | cross-entropy against that profile |
| median probability | 0.9993 | **0.7370** |
| patients at ≥ 99.9% | 178 / 328 | **1 / 328** |
| mean on BOUNDARY tumours | 0.7740 | **0.4743** |
| leave-one-out agreement | 100% (CORE only) | 97.87% all · 99.63% CORE · 89.09% BOUNDARY |
| returns pathway scores | no | yes |

v1 was trained only on the patients the clustering had already separated
cleanly, which made them nearly linearly separable and drove the softmax to
saturate. v2 trains on everybody, against the fraction of 1,000 resampled
clusterings in which each tumour co-clusters with each subtype.

## Files

```
prediction_model/
├── predict.py                     the predictor
├── model_artifacts_v2.joblib      frozen model + preprocessing + gene sets
├── model_metrics_v2.json          headline metrics
├── training_predictions_v2.csv    all 328 patients: recorded vs predicted
├── gene_sets_v2.json              the eleven gene sets, explicitly
├── export_browser_model_v2.py     regenerates the in-browser model
├── browser_model/                 the exported weights (478 KB)
├── build/                         every script used, in order
└── EXPLANATION/                   the full write-up
```

## Reproducing

```bash
cd build
python3 01_verify_state.py          # rebuild + verify the training state
python3 02_reproduce_consensus.py   # regenerate the 328x328 consensus matrix
python3 03_recover_genesets.py      # recover the signature/pathway gene sets
python3 04_diagnose_old_model.py    # quantify the v1 saturation
python3 05_build_model.py           # fit, calibrate, freeze
python3 06_model_comparison.py      # 12 model families, out-of-fold
python3 07_finalize_artifacts.py    # fold in gene sets + cohort lookup
python3 08_test_predictor.py        # end-to-end through the file path
python3 09_verify_browser_export.py # browser arithmetic vs Python
```

The scripts read from `NEW_START_RESULTS/` and `01_Data_Preparation/`; adjust the
paths at the top of each if the tree has moved.

## Evidence that it is wired correctly

- training state rebuilt from raw data: batch means and SD to **0.000e+00**,
  embedding to 3.2e-05
- consensus clustering re-run from seed: **ARI 1.000000**, membership values
  matching the recorded file to **0.0000**, CORE/BOUNDARY 273/55 exactly
- browser weights reproduce the Python model to **1.6e-05** across all 328
- unmodified `engine.js` run in Node against real GDC files: same subtype, call,
  protocol and Verhaak class on every test sample; pathway and signature scores
  identical to 0
- the linear model beat **11** more flexible alternatives out-of-fold

Details in [`EXPLANATION/04_VALIDATION_EVIDENCE.md`](EXPLANATION/04_VALIDATION_EVIDENCE.md).

## Read the limitations

No external cohort validation. No survival data. Two of six subtypes weakly
supported. Protocol detector 99.7%, not 100%. Gene sets are reconstructions
(r ≥ 0.996), because the originals were lost. Nothing has been tested in a lab.

[`EXPLANATION/07_WHAT_THE_PERCENTAGE_MEANS.md`](EXPLANATION/07_WHAT_THE_PERCENTAGE_MEANS.md)
has the full list.

---

## The explanation folder

| file | what it covers |
|---|---|
| `01_WHY_THE_OLD_MODEL_SAID_100_PERCENT.md` | the measurement, the cause, why hard-label calibration is circular |
| `02_THE_PREPROCESSING_CONTRACT.md` | the nine-step pipeline a new patient must go through, and proof it is honoured |
| `03_HOW_THE_NEW_MODEL_WORKS.md` | the consensus target, the fit, why a linear model |
| `04_VALIDATION_EVIDENCE.md` | every number, with the script that produced it |
| `05_GENE_SETS_AND_PATHWAYS.md` | how the lost gene sets were recovered, and the caveat |
| `06_INTEGRATION_WITH_HELIXA.md` | what changed in the website and how to revert |
| `07_WHAT_THE_PERCENTAGE_MEANS.md` | the honest reading, and the limitations |

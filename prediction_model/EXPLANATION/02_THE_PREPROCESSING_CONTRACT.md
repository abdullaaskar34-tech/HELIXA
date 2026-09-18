# The preprocessing contract

Any model that assigns a new patient to one of the six subtypes has to place
that patient in *exactly* the same numeric space the clustering lived in.
Getting this wrong fails silently — the sample still gets a confident answer,
just the wrong one. This file states the contract and records the verification
that the new model honours it.

## Why it is delicate

The 328-patient cohort mixes two library-preparation protocols:

| protocol | n | non-polyadenylated RNA fraction |
|---|---|---|
| poly(A)-selected | 141 | 0.42% |
| total-RNA / rRNA-depleted | 187 | 55.45% |

That is a ~170× difference, and before correction it dominated the data so
completely that clustering the raw matrix recovered the protocol, not the
biology (silhouette 0.5533 at k=2, reproducible across four algorithms — an
alarm, not a result).

A new patient's file can come from either protocol. If raw TPM is fed to a model
trained on corrected data, a total-RNA sample arrives with every mRNA
compressed roughly twofold and gets misassigned *with high confidence*. So the
inference path must reproduce, for one single sample, the same correction that
was applied to the whole training cohort.

## The nine steps

1. **Parse** the GDC `augmented_star_gene_counts.tsv`, take `tpm_unstranded`.
2. **Align** to the 27,777 genes of the training space by Ensembl id.
3. **Detect the protocol** from the non-polyadenylated fraction
   `sum(TPM[non-polyA]) / sum(TPM)`, compared against the frozen threshold
   **0.09179468**.
4. **Filter** to the 25,738 protocol-robust genes (`KEEP`), dropping histones,
   7SK, 7SL, snoRNA/snRNA/misc_RNA/rRNA families and all `MT-` genes.
5. **Renormalise** to a 1e6 budget *over that gene space* — the compositional
   step that is usually forgotten. Removing 2,039 genes changes what the
   remaining fractions mean, so the total must be re-established.
6. **log2(x + 1)**.
7. **Standardise** by subtracting the *stored* training mean of the *detected*
   batch and dividing by the *stored* global SD. Never re-estimated from the
   new sample — a single sample has no batch of its own.
8. **Project**: take the 1,000 MAD-selected protein-coding signature genes,
   subtract the stored PCA mean, project onto the frozen 5 components.
9. **Classify** in that 5-D space.

Steps 3–7 are the batch correction. Step 7 is where a naive implementation
breaks: recomputing the mean and SD from the incoming sample would centre it on
itself and destroy the comparison.

## Verification that the new model sits in the right space

The training state was rebuilt from the raw matrix and checked against the
frozen artifacts:

| check | result |
|---|---|
| `batch_means[0]` vs frozen | max abs diff **0.000e+00** |
| `batch_means[1]` vs frozen | max abs diff **0.000e+00** |
| `global_sd` vs frozen | max abs diff **0.000e+00** |
| 5-PC embedding vs `final_embedding.npy` | max abs diff **3.24e-05** (float32 rounding) |

Then the consensus clustering itself was re-run from scratch — 1,000 resamples
at 80%, seed 42, exactly as `09_Scripts/07_consensus.py` does it:

| check | result |
|---|---|
| embedding vs saved | max abs diff **0.000e+00** |
| ARI(reproduced labels, recorded labels) | **1.000000** |
| label agreement after cluster-id matching | **100.00%** |
| `consensus_own` vs recorded | max abs diff **0.0000** |
| `consensus_best_other` vs recorded | max abs diff **0.0000** |
| `consensus_membership` vs recorded | max abs diff **0.0000** |
| CORE/BOUNDARY split | **273 / 55**, identical to the record |

The whole clustering stage is reproducible from the raw data. That is what
licensed everything downstream: the new model is fitted in a space that is
provably the same space the labels came from.

## The protocol detector is 99.7%, not 100%

`11_build_classifier.py` states in its docstring that one threshold separates
the protocols with "100% accuracy" and a "clean gap". That is stale. Measured
on the actual data:

```
poly(A)      max non-polyA fraction = 0.21736
total-RNA    min non-polyA fraction = 0.10354
threshold                           = 0.09179
accuracy                            = 327/328 = 99.695%
```

The ranges **overlap**. One poly(A) sample (`a8050792-d0f5-4b8f-aea2-0a303f40b1ca`)
sits at 0.217, well inside the total-RNA range, and no threshold can separate
it. 99.695% is the ceiling for a single-threshold detector here, so the frozen
threshold is already optimal — but the claim of a clean gap is wrong and the
shipped `manifest.json` was right to record 0.99695.

This matters. For that one sample the wrong batch mean is subtracted, and the
downstream probability shifts by **0.29**. Every other sample is unaffected.
`predict.py` and the browser engine both flag a sample as
`protocol_ambiguous` when its fraction sits within 0.03 of the threshold, but
this particular sample is not near the threshold — it is a genuine outlier, and
no flag will catch it. It is an accepted, documented limitation.

## What is frozen

Everything inference needs is in `model_artifacts_v2.joblib`, so prediction
never touches the training data again:

- `KEEP_mask`, `NONPOLYA_mask` — the gene filters
- `batch_means` (per protocol), `global_sd` — the standardisation constants
- `signature_gene_idx` — the 1,000 signature gene positions
- `pca` — the frozen 5-component projection
- `protocol_threshold`
- `model` — the calibrated classifier
- `gene_sets` — the Verhaak and pathway gene sets (see `05_...`)
- `training_cohort` — the 328 recorded assignments, for round-trip lookup

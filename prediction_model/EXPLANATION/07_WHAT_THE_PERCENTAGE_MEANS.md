# What the percentage means, and what it does not

## The definition

> **"73% CL" means: a tumour with this expression profile co-clusters with the
> Classical subtype in about 73% of resampled clusterings.**

It is a measure of **subtype stability** — how reliably this tumour belongs to
that group when the cohort is repeatedly resampled and re-clustered.

## What it is not

It is **not** a diagnostic probability. It does not mean there is a 73% chance
the patient "has Classical glioblastoma", and it carries no statement about
prognosis, treatment response, or survival.

Three reasons, each sufficient on its own:

1. **The subtypes are not a diagnosis.** They are transcriptional clusters
   discovered in this cohort. Glioblastoma subtype boundaries are known to be
   continuous, and bulk RNA-seq measures a regional mixture of cells, not a
   single tumour state.

2. **There is no independent ground truth to be probable about.** The labels
   came from the clustering itself. A model reproducing them at 98% shows the
   clusters are learnable, not that the tumours really are those subtypes.

3. **No survival data was ever linked.** No Kaplan-Meier analysis exists for
   these six clusters, so none of them has been shown to matter clinically in
   this cohort.

## How reliable is the number itself?

Measured out-of-fold — patients the model never saw, which is the situation a
new patient is in:

| | value |
|---|---|
| correlation with the true consensus, all 328 × 6 cells | **+0.9656** |
| RMSE across all cells | 0.0766 |
| **mean absolute error on the reported top-class figure** | **0.1130** |
| correlation, top-class probability vs its consensus share | +0.7486 |

**Read the headline number as ±0.11, not as a precise figure.** A reported 73%
means the consensus value is typically somewhere around 62–84%. The six-way
*shape* is captured well (r = 0.966) — which subtype leads, and which is the
runner-up, is dependable. The precise magnitude of the leader is noisier.

And the error is not uniform. For a minority of patients it is substantially
larger: one CORE patient whose true consensus share is 0.83 is reported at 0.34.
Model comparison showed this is irreducible with these features — eleven more
flexible model families all did worse — so it is a property of using five
principal components, not a fixable defect. If an individual call matters,
check it against the pathway and signature scores, which are computed
independently of the classifier.

## Reading a result

| what you see | what it means |
|---|---|
| high probability, `CORE` | a stable, confident subtype call |
| moderate probability, `CORE` | leader is clear, absolute stability moderate |
| any probability, `BOUNDARY` | margin to the runner-up is below 0.50 — the tumour sits between subtypes |
| `protocol_ambiguous: true` | non-polyA fraction is near the detection threshold; treat with caution |
| coverage well below 100% | gene annotation mismatch; the call may be unreliable |

`BOUNDARY` is a finding, not a failure. 55 of the 328 reference tumours (17%)
are intermediate in exactly this way, and reporting that is the point — v1 gave
those same tumours a mean confidence of 0.774 and often 99%+.

## Known limitations

1. **No external validation.** The model has never been tested on a cohort
   outside these 328 patients. CGGA, GEO and REMBRANDT remain the obvious next
   step, and until then all accuracy figures are internal.

2. **No survival data.** The strongest validation a subtype scheme can have is
   still missing.

3. **Two of six subtypes are weakly supported.** INT (cluster 4, 20% of the
   cohort) fails all three biological validation layers and is best read as
   transitional. CL is only partially supported. Both are labelled as such.

4. **Verhaak 2010 is not an independent validator** — it was used inside the
   clustering optimisation, so `verhaak_nearest` and the `sig_*` columns are
   partially circular. The pathway scores, Neftel 2019 and Garofano 2021 are
   independent.

5. **The protocol detector is 99.7%, not 100%.** One training sample is
   misdetected and its probability shifts by 0.29 as a result. A new sample
   with an unusual non-polyA fraction can be misassigned the same way, and only
   near-threshold cases raise the `protocol_ambiguous` flag.

6. **The gene sets are reconstructions.** The originals were lost; the
   replacements agree at r ≥ 0.996 but are not bit-identical. See
   `05_GENE_SETS_AND_PATHWAYS.md`.

7. **The 7 in-sample disagreements** are patients whose consensus profile points
   away from their assigned label. `predict.py` returns the recorded assignment
   for any known sample, so a round trip is always faithful.

8. **The built-in demo patients on the website still show v1 numbers** until
   `backend/export_static_data.py` is re-run. Uploaded files use the live v2
   engine.

9. **Nothing here has been tested in a laboratory.** The subtypes, the
   biomarkers and the drug associations are all computational.

## The short version

The new percentage is an honest, well-behaved measure of subtype stability with
a typical error of about ±0.11, and it should be read as a research signal about
tumour biology. It is not a clinical probability and must not be used as one.

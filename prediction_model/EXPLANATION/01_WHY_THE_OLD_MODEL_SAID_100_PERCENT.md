# Why the old model reported ~100% for almost every patient

## The observation

Feeding patients to the shipped model and reading off the top-class probability
gives this:

| | shipped model (v1) |
|---|---|
| mean reported probability | 0.9565 |
| median | **0.9993** |
| minimum across all 328 patients | 0.4871 |
| patients at ≥ 99% | 234 / 328 (71.3%) |
| patients at ≥ 99.9% | **178 / 328 (54.3%)** |
| patients at ≥ 99.99% | 120 / 328 (36.6%) |

More than half the cohort came back at 99.9% or higher. That is the behaviour
that prompted this work.

For comparison, here is what the consensus clustering — the thing that
*created* the labels in the first place — actually recorded for the same
patients:

| | value |
|---|---|
| `consensus_own`, mean | 0.8027 |
| `consensus_own`, median | 0.8301 |
| `consensus_own`, range | 0.2796 – 0.9308 |

The clustering never claimed certainty above 0.93 for anybody. The classifier
built on top of it claimed 99.9%+ for half the cohort.

## The cause

It is not a bug in the code and it is not a display problem. The frontend was
already rendering the full six-way distribution correctly. The model genuinely
produced those numbers, for two compounding reasons.

**1. It was trained only on the patients that were easy by construction.**

`11_build_classifier.py` fits on `E[core]` — the 273 CORE patients. But CORE is
*defined* as the subset whose consensus membership margin exceeded 0.50, i.e.
precisely the patients the clustering could separate cleanly. In the 5-PC space
those 273 points are very nearly linearly separable.

A logistic regression on near-separable data has no reason to stop: pushing the
weights larger keeps reducing the training loss, so the decision function grows
until the softmax saturates. The model was never shown an ambiguous tumour, so
it never learned that ambiguity is possible. The 55 BOUNDARY patients — 17% of
the cohort, the genuinely intermediate tumours — were excluded from training
entirely.

**2. The model was selected on accuracy, which is blind to overconfidence.**

Accuracy scores a correct call at 51% and a correct call at 99.99% identically.
Nothing in the selection procedure penalised the saturation. The reported
figures (100% leave-one-out, ROC-AUC 0.99999) are all accuracy-family metrics,
so all of them were satisfied by a model that had stopped conveying any
uncertainty.

## Why the 100% figure was never as strong as it looked

The project README already flags this, and it is worth restating because it is
the heart of the matter:

> The classifier's 99–100% figures are expected, not miraculous. It learns to
> reproduce labels derived by clustering on this same cohort. [...] this
> measures "the subtype boundaries are cleanly learnable", not clinical
> diagnostic accuracy.

The labels are not independent ground truth — they are the clustering's own
output. A classifier that reproduces them at 98% has demonstrated that the
clusters are learnable, not that the tumours really are those subtypes.

This has a sharp consequence for calibration: **you cannot calibrate against
the hard labels.** Doing so is circular. The model is right about them ~98% of
the time, so a calibration routine would conclude that ~98% confidence is
correct and hand back a near-constant 98% — the original problem in a new
costume.

The only quantity in the whole pipeline that carries real, non-circular
uncertainty is the consensus membership: the fraction of 1,000 resampled
clusterings in which a patient actually landed in a given cluster. That is what
the new model is tied to, and the reasoning is in
`03_HOW_THE_NEW_MODEL_WORKS.md`.

## The one thing that was genuinely fine

The old model's confidence was not *meaningless* — it correlated +0.78 with
`consensus_own`, and it did report lower numbers on BOUNDARY tumours (mean
0.774) than on CORE ones (mean 0.993). The ordering carried signal. The problem
was the scale: everything was compressed against the ceiling, so the difference
between "solidly Classical" and "could go either way" was the difference
between 99.99% and 99.2% — invisible to anybody reading the number.

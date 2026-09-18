# Integration with HELIXA

## How HELIXA actually runs the model

Worth stating clearly, because it shapes everything below: **HELIXA does not
call a Python backend to classify a patient.** The whole forward pass runs in
the browser.

`website/backend/export_browser_model.py` writes the frozen weights out as flat
binary files into `website/frontend/model/`, and `website/frontend/js/engine.js`
loads them and reproduces the arithmetic in JavaScript. There is a Flask app
(`backend/app.py`, `backend/helixa_engine.py`), but the deployed site is static
— the model files are fetched and the classification happens client-side. That
is why the site works on GitHub Pages.

So integrating the new model means regenerating the binaries in
`frontend/model/` and updating the two JS files that consume them.

## What was already correct

`analyze.js` was **already rendering the full six-way probability
distribution** (`All six subtypes compared`, one bar per subtype). The "always
100%" the user saw was not a display bug — the model genuinely produced those
numbers and the frontend faithfully displayed them. No fix was needed there.

## What changed

### `website/frontend/model/` — regenerated

Written by `../export_browser_model_v2.py`. Same binary layout as v1 so the
engine changes stay small, with two additions:

- **`stat_pos.bin` now covers 2,294 positions instead of 1,017.** v1 only stored
  batch means and SDs at the 1,000 signature genes plus 17 marker genes. v2 adds
  every gene-set gene, so the browser can compute the Verhaak and pathway scores
  itself rather than only the classifier output.
- **`gene_set_slots.json`** — new file, the slot lists for the eleven gene sets.

Total 478 KB.

`coef.bin` and `intercept.bin` carry the new calibrated weights; everything else
(gene ids, masks, PCA, thresholds) is unchanged, because the preprocessing
contract did not change.

### `website/frontend/js/engine.js`

- loads `gene_set_slots.json`, tolerating its absence so a v1 model directory
  still works
- computes the four signature and seven pathway scores from the same `z` vector
  used for the call, and derives `verhaak_nearest`
- replaces the old confidence bands with the **margin** rule: `margin ≥ 0.50`
  → `CORE`, otherwise `BOUNDARY`, matching the τ the clustering used for its own
  core/boundary split
- returns `margin`, `call`, `core_tau`, `runner_up_class`, `signature_scores`,
  `pathway_scores`, `verhaak_nearest` and `probability_meaning`

### `website/frontend/js/views/analyze.js`

- the headline gauge is relabelled **"Subtype stability"** — it was
  "Confidence", which invited exactly the diagnostic reading the number does not
  support — and its colour now keys off the CORE/BOUNDARY call rather than fixed
  0.8/0.5 cutoffs that no longer suit the calibrated scale
- the probability card subtitle says what the percentages are: *"How often this
  profile co-clusters with each subtype across 1,000 resamplings"*
- the intermediate-tumour banner triggers on the margin rule and quotes the
  actual margin
- a **new card, "Signature and pathway scores"**, renders the eleven scores as
  diverging bars with the nearest Verhaak class, noting that they are computed
  from gene sets directly and do not use the classifier
- the technical panel gains the margin, the call and the threshold, and a plain
  statement of what the percentage means

## Verification

The unmodified `engine.js` was executed in Node against the exported v2 model
and real GDC files, with `fetch` stubbed to read the local model directory
(`test_engine.mjs`). Against the Python predictor:

- subtype, call, detected protocol and `verhaak_nearest` agreed on all 5 test
  samples, spanning both protocols and both CORE and BOUNDARY
- max probability difference **4.7e-05** (float32 rounding)
- pathway and signature differences **exactly 0**

Reading the exported binaries back in the browser's arithmetic across all 328
patients gives max probability difference **1.60e-05**.

## Reverting

The v1 artifacts are untouched at
`NEW_START_RESULTS/10_Prediction_Model/model_artifacts.joblib`. Running the
original `backend/export_browser_model.py` regenerates the v1 binaries into
`frontend/model/` and restores the old behaviour. The two JS files degrade
gracefully: with a v1 model directory `gene_set_slots.json` is absent, the
pathway card is simply not rendered, and `core_tau` falls back to 0.50.

## Not changed

- `backend/helixa_engine.py`, `backend/app.py` — the Flask path still loads the
  v1 joblib. The deployed site does not use it. If you intend to serve
  predictions from Python rather than the browser, point it at
  `prediction_model/predict.py`, which is self-contained.
- `backend/export_static_data.py` and the precomputed `frontend/data/*.json`
  (including `demo_results.json`). The demo results were generated with v1, so
  the four built-in example patients will still show v1-style confidences until
  that export is re-run. Uploaded files go through the live v2 engine and are
  unaffected.
- the biomarker engine and `biomarkers.json` — the biomarker panel is keyed on
  cluster identity, and cluster identity did not change.

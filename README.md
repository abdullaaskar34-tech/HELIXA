<div align="center">

<img src="website/frontend/assets/logos/helixa-logo.png" alt="HELIXA" height="80" />

### Turning Genomics into Decisions

**KBU-MedLab** · TEKNOFEST Oncology 3T Competition

</div>

---

## What HELIXA is

HELIXA is a biomedical AI platform for **glioblastoma molecular subtyping and biomarker
discovery**. It takes raw TCGA/GDC RNA-seq data, removes the technical artefacts that would
otherwise corrupt the result, discovers molecular subtypes, classifies new patients against
those subtypes, validates every conclusion against independent published literature — and,
for each subtype, surfaces the genes that both mark it in real patients **and** that a
glioblastoma cell cannot survive without, checked one at a time against the published
literature and tiered by how actionable they actually are.

It is a working system, not a mock-up. Every number the web interface displays is read
from a file produced by the analysis pipeline in this repository, and the "Analyze Patient"
workflow runs the actual frozen model. When a patient is classified, the site now also shows
the biomarker/drug-target panel for the predicted subtype, and a one-click, self-contained
**Patient Molecular Report** (logo, classification, biomarkers, technical appendix) that the
browser turns into a PDF with no server involved.

**Cohort:** 328 glioblastoma patients · **Subtypes discovered:** 6 · **Classifier:** 100% leave-one-out accuracy on 273 high-confidence patients · **Biomarker candidates:** 61 literature-checked genes across the 6 subtypes, 17 of them tier-1 actionable.

---

## The pipeline

```
Raw GDC RNA-seq  (60,660 gene loci)
        ↓  01  Data ingestion
Expression matrix  (log2 TPM+1)
        ↓  02  QC / low-expression filter          → 27,777 genes
        ↓  03  Protocol detection + batch correction → 25,738 genes, batch signal 11.07 → 0.0000
        ↓  04  Feature selection (MAD)             → 1,000 signature genes
        ↓  05  Dimensionality reduction (PCA)      → 5 components
        ↓  06  Consensus clustering (1,000 resamples) → k = 6, PAC = 0.2105
        ↓  07  Classification (multinomial logistic regression)
        ↓  08  Confidence & uncertainty            → core / boundary
        ↓  09  Biological validation               → 4 independent published sources
   Subtype · confidence · markers · pathway profile · therapeutic context
        ↓  10  Biomarker discovery (independent second pipeline, see below)
   Per-subtype drug-target panel · tiered by literature evidence · with sources
```

### The quality-control step that mattered most

The strongest signal in the uncorrected cohort was **not tumour biology — it was library
preparation protocol**. Two protocols were mixed: poly(A)-selected libraries contained
0.42% non-polyadenylated RNA, total-RNA libraries contained 55.45% — a **170× difference**,
and a single threshold separated them with 100% accuracy.

Left uncorrected, the pipeline would have "discovered" the sequencing protocol and
presented it as a molecular subtype. A three-layer correction (gene-space filter →
re-normalisation → within-batch standardisation) removes it to a residual ARI of
**-0.0044**.

---

## The six subtypes

| # | Subtype | n | Verhaak identity | Independent verdict |
|---|---------|---|------------------|---------------------|
| 0 | **MTC** — Mitochondrial / OXPHOS | 40 | Mixed (Neural-leaning) | Confirmed (moderate) · 2.15× |
| 1 | **PN** — Proneural / Progenitor | 49 | Proneural-like | Confirmed (strong) · 2.69× |
| 2 | **CL** — Classical / EGFR | 65 | Classical-like | Partially supported · 1.96× |
| 3 | **MES** — Mesenchymal / Immune | 63 | Mesenchymal-like | Confirmed (strong) · 2.84× |
| 4 | **INT** — Intermediate / Mixed | 67 | Mixed | Partially supported · 1.36× |
| 5 | **OLIGO** — Oligodendrocytic / Myelin | 44 | Mixed (Proneural-leaning) | Confirmed (strong) · 2.32× |

**cluster_0 (MTC)** independently matches the mitochondrial subtype published in
*Nature Cancer* 2021 at 72.5% (2.9× chance, p = 2.7 × 10⁻¹¹) — a subtype reported to
carry the most favourable prognosis and selective vulnerability to OXPHOS inhibitors.

---

## Biomarkers & drug targets

Classifying a patient answers "which subtype is this?" A second, independent pipeline —
the **HELIXA biomarker engine** — answers the question a classifier cannot: *for this
subtype, what could actually be drugged, and how sure are we?*

It is deliberately built to avoid the mistake an earlier attempt made: taking a subtype's
marker genes and asking a dependency database "is this gene essential?" without checking
essential *compared to what*. That approach returned ten genes — mostly RNA-polymerase
subunits and ribosomal proteins that every human cell needs equally — and left one subtype
(MTC) with nothing at all.

**The three gates a gene has to pass, in order:**

1. **Identity** — it marks the subtype in the 328 real patients (Welch t-test, FDR < 0.05,
   Cohen's d > 0.5, and a *specificity margin* > 0.15z — the gene's mean expression in this
   subtype must beat the **best** of the other five, not their average).
2. **Tumour dependency, with a safety window** — using DepMap CRISPR gene-dependency
   screening across 1,208 cancer cell lines (53 glioblastoma, 1,118 from outside the brain),
   the gene must be a real dependency of glioblastoma specifically — high dependency in the
   53 GBM lines, *and* low dependency in the 1,118 non-brain lines. 1,329 of the screened
   genes are dependencies of essentially every cell line in existence; those are discarded
   outright, because a drug against them would harm the patient as much as the tumour.
3. **Literature check** — every gene that survives both gates is looked up individually in
   PubMed, the Human Protein Atlas, Open Targets, DrugBank and ClinicalTrials.gov. This is
   the step that catches what arithmetic cannot: two of the genes that pass both statistical
   gates are established **tumour suppressors** — inhibiting them would help the tumour, not
   hurt it — and are kept visible, marked EXCLUDED with the reason, rather than silently
   dropped.

**Final tiers**, shown on the site and in every patient report:

| Tier | Meaning |
|------|---------|
| **Tier 1 · Actionable** | passes both data gates, published support, a drug against it already exists (possibly for another cancer) |
| **Tier 2 · Credible** | passes both data gates, published support, nothing built against it yet |
| **Tier 3 · Hypothesis** | passes both data gates, but the literature is thin — a real finding, unproven |
| **Excluded** | the gene is a tumour suppressor, or its biology otherwise points the wrong way |

**Result:** 359 genes pass both statistical gates; 61 of the strongest were checked against
the literature; 17 are tier-1 actionable, 18 tier-2 credible, 21 tier-3 hypotheses, and 5 were
excluded. Two of the tier-1 targets already have drugs approved in other cancers (FGFR1 →
pemigatinib, PTK2 → defactinib); two others already **failed** glioblastoma trials
(ITGB5 → cilengitide, phase III CENTRIC; CDK6 → palbociclib, terminated for futility) — that
failure is recorded on the same row rather than left out.

The full six-stage pipeline — patient-side differential expression, DepMap dependency
screening, intersection & scoring, literature evidence collection, evidence integration, and
the reporting figures — with every intermediate table and every literature source, lives in
[`BIOMARKER_ENGINE/`](./BIOMARKER_ENGINE) in this repository. `EXPLANATION_STEP_BY_STEP.txt`
there is the narrative walkthrough; `05_Tables/final_targets.csv` is the exact file the
website's `data/biomarkers.json` (and every biomarker table on the site) is generated from.

**On the site:** after a patient is classified, a "Biomarkers & drug targets for `<subtype>`"
panel appears automatically underneath the result, and a **Download / Print Patient Report**
button generates a self-contained report (see below) for that patient and subtype.

> **Same caveat as the classifier, stated plainly:** these are computational candidates from
> an unpublished research pipeline, not treatments. Nothing on this list has been tested in a
> laboratory by this project. The dependency evidence comes from cell lines, not patients —
> cell lines lack an immune system, a blood-brain barrier and a tumour microenvironment, which
> is a specific reason the MES (immune-infiltrated) panel may be understated.

---

## Patient Molecular Report

Every classified patient can be turned into a one-click, fully self-contained report — the
HELIXA logo, the patient/sample label, the predicted subtype and confidence, all six
probabilities, the genes that drove the decision, and the full biomarker/drug-target table
for that subtype, with a plain disclaimer that this is a research prototype and not a
diagnosis.

There is no PDF library and no server involved: **Download / Print Patient Report** opens the
report as a normal page in a new browser tab (`website/frontend/js/report.js`), built from
the exact same `result` object the on-page card already rendered and the exact same
`data/biomarkers.json` dataset, so the report can never disagree with what the page showed.
The tab's own "Print / Save as PDF" button (or the browser's native Ctrl/Cmd + P) hands the
page to the browser's print engine, which is how the patient/clinician saves it as a PDF —
the same mechanism a normal web page uses to become a PDF, with no upload and no third-party
service anywhere in the path.

---

## Model evaluation

| Metric | Value |
|--------|-------|
| Leave-one-out accuracy (273 core patients, model refit each time) | **100.00%** |
| Cross-validated accuracy (5-fold × 10 repeats) | 99.89% |
| Balanced accuracy | 99.91% |
| ROC-AUC (macro, one-vs-rest) | 1.0000 |
| Cohen's κ | 0.9955 |
| Permutation null test (300 shuffles) | real 99.63% vs 19.30% random, p = 0.005 |
| Boundary-tumour agreement (unseen hard cases) | 89.1% |

Eight algorithms were compared; multinomial logistic regression won on balanced accuracy
**and** consistency across all 50 folds.

---

## Repository layout

```
HELIXA/
├── NEW_START_RESULTS/            the clustering/classification project (unmodified)
│   ├── 01_Data_Preparation_extra/
│   ├── 02_Batch_Diagnosis/       the library-prep artefact, diagnosed
│   ├── 03_Clustering_Sweep/      726 configurations evaluated
│   ├── 04_Consensus_Clustering/  final assignments + embedding
│   ├── 05_Clusters/              one folder per subtype, with its patients
│   ├── 06_Biological_Validation/ marker genes, signature & pathway scores
│   ├── 07_Plots/                 23 original figures
│   ├── 08_Evaluation_Report/     global metrics + master workbook
│   ├── 09_Scripts/               every analysis script
│   ├── 10_Prediction_Model/      frozen model + predict_new_patient.py
│   └── 11_Evaluation_From_Internet/  independent literature validation
│
├── BIOMARKER_ENGINE/              the biomarker/drug-target discovery project
│   ├── EXPLANATION_STEP_BY_STEP.txt   narrative walkthrough, start here
│   ├── 01_Engine/                 the 5 scripts, run in order (01 → 05)
│   ├── 03_Evidence/               literature_evidence.{csv,json} — every source URL
│   ├── 04_Plots/                  the 10 official reporting figures
│   └── 05_Tables/                 candidates_all.csv, final_targets.csv (the
│                                   exact file website/frontend/data/biomarkers.json
│                                   is generated from), dependency_side_depmap.csv
│
├── website/
│   ├── backend/                  Starlette API wrapping the real model
│   │   ├── app.py
│   │   ├── helixa_engine.py      thin wrapper over the frozen artifacts
│   │   ├── export_static_data.py results (+ BIOMARKER_ENGINE) → JSON for the frontend
│   │   └── requirements.txt
│   └── frontend/                 zero-dependency SPA (no build step)
│       ├── index.html
│       ├── css/helixa.css
│       ├── js/                   router, data layer, SVG charts, views,
│       │                         report.js — the Patient Molecular Report
│       ├── data/                 17 JSON datasets, incl. biomarkers.json
│       └── assets/               logos + 27 scientific figures
│
└── .github/workflows/deploy.yml  GitHub Pages deployment
```

---

## Running locally

### Frontend only (all recorded results, no live prediction)

```bash
cd website/frontend
python3 -m http.server 5173
# open http://127.0.0.1:5173
```

No build step, no `npm install` — the frontend is native ES modules and hand-written CSS.

### With the live model (enables "Analyze Patient")

```bash
cd website/backend
pip install -r requirements.txt
uvicorn app:app --port 8000
```

Reload the site. It auto-detects the API at `127.0.0.1:8000` and the upload workflow
becomes active. Override the base URL with `?api=http://host:port` or the field on the
Analyze page.

### Classify a patient from the command line

```bash
cd NEW_START_RESULTS/10_Prediction_Model
pip install scikit-learn joblib pandas numpy
python3 predict_new_patient.py  /path/to/patient.rna_seq.augmented_star_gene_counts.tsv
```

### Re-export the web data after re-running the science

```bash
cd website/backend
HELIXA_RESULTS=../../NEW_START_RESULTS \
HELIXA_BIOMARKER_ENGINE=../../BIOMARKER_ENGINE \
python3 export_static_data.py
```

This regenerates every JSON in `website/frontend/data/`, including `biomarkers.json` from
`BIOMARKER_ENGINE/05_Tables/final_targets.csv`. If `HELIXA_BIOMARKER_ENGINE` does not point
to a real `final_targets.csv`, the script skips that one file and says so — it never
fabricates biomarker data.

---

## Architecture

```
Browser ── HELIXA frontend (static, GitHub Pages)
                │
                ├── /data/*.json ........ recorded results, always available
                │     including biomarkers.json (from BIOMARKER_ENGINE/05_Tables/final_targets.csv)
                │
                ├── /model/*.bin ........ frozen classifier weights, fetched once
                │     └── js/engine.js — the classifier's forward pass, in the browser
                │
                ├── js/report.js ........ builds the Patient Molecular Report
                │     (new tab, browser print-to-PDF — no server, no PDF library)
                │
                └── HTTP ── Starlette API (local) ── helixa_engine.py
                                                          │
                                              model_artifacts.joblib
                                              (frozen PCA + classifier +
                                               batch means + gene masks)
                                                          │
                                                   real prediction
```

The scientific pipeline is never embedded in the UI. The frontend renders; the backend
delegates to the frozen artifacts; the artifacts came from the scripts in
`NEW_START_RESULTS/09_Scripts/`.

### Live vs static mode

GitHub Pages serves static files only, so the Python model cannot run there. The frontend
detects this and says so plainly — it never fakes a prediction. All cohort data,
evaluations and figures remain fully available; only the upload workflow requires the
local API.

---

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `HELIXA_RESULTS` | `../../NEW_START_RESULTS` | Where the scientific outputs live |
| `HELIXA_CORS` | `localhost:5173,127.0.0.1:5173` | Allowed browser origins |
| `HELIXA_DATA` | `../frontend/data` | JSON dataset directory |

Copy `website/backend/.env.example` to `.env` and edit. Never commit `.env`.

---

## Known limitations

These are stated on the platform itself, not buried here.

1. **No external patient cohort has been tested.** Everything derives from the same
   328-patient TCGA/GDC cohort. Generalisation to another hospital or study is unproven.
2. **No clinical outcome has been linked.** Survival data has not been analysed, so these
   are molecular groupings — not validated prognostic classes.
3. **This is a computational classification, not a diagnosis.**
4. **The classifier's 99–100% figures are expected, not miraculous.** It learns to
   reproduce labels derived by clustering on this same cohort. The leave-one-out and
   permutation tests prove there is no leakage — but this measures "the subtype boundaries
   are cleanly learnable", not clinical diagnostic accuracy.
5. **Two subtypes (CL, INT) are only partially supported** by independent sources, and are
   labelled as such everywhere they appear.
6. **Verhaak 2010 is not an independent validator here** — it was used inside the
   clustering optimisation. Only Neftel 2019, Garofano 2021, MSigDB Hallmark and the
   lineage panels are independent.
7. **The biomarker/drug-target panel lists computational candidates, not treatments.**
   Nothing on it has been tested in a laboratory by this project.
8. **The dependency evidence comes from cell lines, not patients**, and cell lines were not
   classified into the 6 subtypes (no DepMap expression data was available to do so) — so a
   gene's dependency evidence is "selective to glioblastoma", not "selective to this exact
   subtype". Cell lines also lack an immune system, a blood-brain barrier and a tumour
   microenvironment, which may specifically understate the MES (immune-infiltrated) panel.
9. **The literature check covered the top ~10 ranked candidates per subtype (61 genes total),
   not all 359 that passed the statistical gates.** A gene ranked just below the cutoff was
   never checked, however promising the raw numbers.
10. **Two of the tier-1 targets already have drugs that failed in glioblastoma trials**
    (cilengitide/ITGB5, palbociclib/CDK6) — the target may still be biologically valid; that
    specific molecule was not effective in that trial. This is recorded on their row, not
    hidden.

**Next step that would matter most:** link these subtypes to survival data from GDC and
run a Kaplan-Meier analysis; and, for the biomarker panel, download DepMap's cell-line
expression data to classify the 53 glioblastoma lines into the 6 subtypes directly, turning
"selective to glioblastoma" into "selective to this exact subtype."

---

## References

- Neftel C. *et al.* An Integrative Model of Cellular States, Plasticity, and Genetics for Glioblastoma. **Cell** 2019;178(4):835-849.
- Garofano L. *et al.* Pathway-based classification of glioblastoma uncovers a mitochondrial subtype with therapeutic vulnerabilities. **Nature Cancer** 2021;2:141-156.
- Verhaak RGW *et al.* Integrated genomic analysis identifies clinically relevant subtypes of glioblastoma. **Cancer Cell** 2010;17(1):98-110.
- Liberzon A. *et al.* The Molecular Signatures Database Hallmark gene set collection. **Cell Systems** 2015;1(6):417-425.
- DepMap, Broad Institute. Cancer Dependency Map — genome-wide CRISPR gene-dependency screening across 1,208+ cancer cell lines. [depmap.org](https://depmap.org)
- Every gene-level claim in the biomarker panel carries its own source URL (PubMed, Human Protein Atlas, Open Targets, DrugBank, or ClinicalTrials.gov) in `BIOMARKER_ENGINE/03_Evidence/literature_evidence.json` and in every patient report.

---

## Team — KBU-MedLab

| | |
|---|---|
| **Abdulla ASKAR** — *Team Leader* | B.Sc. Biomedical Engineering — KBÜ · B.Sc. Electrical and Electronics Engineering — KBÜ · M.Sc. Computer Science — İTÜ |
| **Mohammad Alsagher** — *Literature* | Medical Engineering |
| **Leyan Mamou** — *Algorithms & Technical Development* | Computer Engineering |
| **Alı ALTHAHER** — *Algorithms & Other Technical Development* | B.Sc. Biomedical Engineering — KBÜ |
| **Mariam Mariam** — *Media & Other Contributions* | Medical Engineering |

**Contact** · [kbumedlab@gmail.com](mailto:kbumedlab@gmail.com) · [0 538 314 9253](tel:+905383149253)

---

<div align="center">

**HELIXA** — Turning Genomics into Decisions
<br />KBU-MedLab

</div>

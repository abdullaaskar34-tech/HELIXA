<div align="center">

<img src="website/frontend/assets/logos/helixa-logo.png" alt="HELIXA" height="80" />

### Turning Genomics into Decisions

**KBU-MedLab** · TEKNOFEST Oncology 3T Competition

</div>

---

## What HELIXA is

HELIXA is a biomedical AI platform for **glioblastoma molecular subtyping**. It takes raw
TCGA/GDC RNA-seq data, removes the technical artefacts that would otherwise corrupt the
result, discovers molecular subtypes, classifies new patients, and validates every
conclusion against independent published literature.

It is a working system, not a mock-up. Every number the web interface displays is read
from a file produced by the analysis pipeline in this repository, and the "Analyze Patient"
workflow runs the actual frozen model.

**Cohort:** 328 glioblastoma patients · **Subtypes discovered:** 6 · **Classifier:** 100% leave-one-out accuracy on 273 high-confidence patients.

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
├── NEW_START_RESULTS/            the scientific project (unmodified)
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
├── website/
│   ├── backend/                  Starlette API wrapping the real model
│   │   ├── app.py
│   │   ├── helixa_engine.py      thin wrapper over the frozen artifacts
│   │   ├── export_static_data.py results → JSON for the frontend
│   │   └── requirements.txt
│   └── frontend/                 zero-dependency SPA (no build step)
│       ├── index.html
│       ├── css/helixa.css
│       ├── js/                   router, data layer, SVG charts, 10 views
│       ├── data/                 16 JSON datasets exported from the results
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
HELIXA_RESULTS=../../NEW_START_RESULTS python3 export_static_data.py
```

---

## Architecture

```
Browser ── HELIXA frontend (static, GitHub Pages)
                │
                ├── /data/*.json ........ recorded results, always available
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

**Next step that would matter most:** link these subtypes to survival data from GDC and
run a Kaplan-Meier analysis.

---

## References

- Neftel C. *et al.* An Integrative Model of Cellular States, Plasticity, and Genetics for Glioblastoma. **Cell** 2019;178(4):835-849.
- Garofano L. *et al.* Pathway-based classification of glioblastoma uncovers a mitochondrial subtype with therapeutic vulnerabilities. **Nature Cancer** 2021;2:141-156.
- Verhaak RGW *et al.* Integrated genomic analysis identifies clinically relevant subtypes of glioblastoma. **Cancer Cell** 2010;17(1):98-110.
- Liberzon A. *et al.* The Molecular Signatures Database Hallmark gene set collection. **Cell Systems** 2015;1(6):417-425.

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

# The biomarker panel

## What changed

The website's biomarker card used to be built from Stage 5's `final_targets.csv`
alone — 61 genes. That looked like a filtered shortlist. It was not.

Stage 4 is a human reading literature for roughly ten genes per subtype, and
Stage 5 drops any candidate without a verdict. So the old panel showed whichever
genes somebody had time to look up, and 298 statistically-qualified candidates
were invisible. For PN it showed 10 of 176.

The panel now starts from Stage 3's `candidates_all.csv` — every gene that
passed both statistical gates — and layers the other two tables on top:

| file | stage | what it contributes | rows |
|---|---|---|---|
| `candidates_all.csv` | 3 | the statistics — **the base** | 359 |
| `literature_evidence.csv` | 4 | protein function, GBM evidence, druggability, **sources** | 62 |
| `final_targets.csv` | 5 | drug status, tier, final score, wrong-direction flags | 61 |

Stages 4, 5 and 6 are no longer run as pipeline steps. Only those two tables are
consumed, and nothing is recomputed — every number is carried through from the
CSV that produced it, so the panel cannot drift from the engine.

Built by `../build_biomarker_panel.py`, which writes
`website/frontend/data/biomarkers.json` (468 KB).

## Per subtype

| subtype | candidates | reviewed | tier 1 | tier 2 | tier 3 | excluded | not yet reviewed |
|---|---|---|---|---|---|---|---|
| MTC | 65 | 11 | 1 | 5 | 3 | 2 | 54 |
| PN | 176 | 10 | 2 | 4 | 4 | 0 | 166 |
| CL | 24 | 10 | 3 | 1 | 6 | 0 | 14 |
| MES | 22 | 10 | 7 | 1 | 2 | 0 | 12 |
| INT | 61 | 10 | 2 | 2 | 4 | 2 | 51 |
| OLIGO | 11 | 10 | 2 | 5 | 2 | 1 | 1 |

## Two kinds of gene, never mixed up

**Reviewed** — somebody read the literature. Protein function, glioblastoma
evidence, subtype link, druggability and drug status are shown, each followed by
the curated sources they came from. 281 source links across the panel.

**Not yet reviewed** — cleared both statistical gates, but nobody has read the
literature. The panel says so in a banner, shows only the numbers, and offers
*search* links rather than findings. A reviewing backlog is not a negative
result, and the panel never lets one look like the other.

## Plain language

Column names were replaced with terms that mean something to a clinician. Each
one carries its own definition and a line on how to read it, rendered under the
meter rather than hidden in a tooltip.

| was | now |
|---|---|
| `combined_score` | Overall target strength |
| `identity_score` | Specific to this subtype |
| `survival_score` | Tumour cannot survive without it |
| `dep_mean_GBM` | Glioblastoma cells need it |
| `dep_mean_nonCNS` | Healthy cells also need it |
| `therapeutic_window` | **Safety gap** |
| `gbm_line_sd` | Varies between tumours |
| `specificity_margin` | Expression lead over the next subtype |
| `cohens_d` | Effect size |
| `fdr` | Statistical confidence |

The headline picture for each gene answers one question — *can a drug hit this
without hurting the patient?* — with two bars and the gap between them:

```
Glioblastoma cells need it   ████████████████░░░░  72%
Healthy cells also need it   █████████░░░░░░░░░░░  42%
Safety gap  +30 pts          Wide — the tumour needs it much more
```

## Sources

Every curated claim links to where it came from, labelled by publisher (PubMed,
PMC, Nature, ScienceDirect, Neuro-Oncology, …) rather than shown as a raw URL.
Every gene, reviewed or not, also carries nine lookup links — PubMed, UniProt,
Human Protein Atlas, Pharos, DGIdb, DrugBank, ClinicalTrials.gov, DepMap and
Ensembl — generated from templates in the JSON rather than stored per gene.

Curated sources are filled; search links are outlined. The visual difference is
deliberate.

## Two bugs this work caught

**Numbers serialised as strings.** `pandas.itertuples()` returns plain Python
floats, not `np.float64`, so an `isinstance(v, np.floating)` check silently
stringified every metric. The JSON validated, the syntax checked, and the panel
died on `.toFixed()` in the browser. Found by rendering the page in real
Chromium, not by reading the file.

**FDR rounded to zero.** Rounding floats to 8 decimals turned every p-value
below 1e-8 into `0.0`, so the most significant genes displayed "statistical
confidence 0.0e+0". Small magnitudes are now kept at full precision; the
smallest surviving value is 1.78e-22.

**And one in the patient report:** `tierName()` fell through to `'Excluded'` for
any unrecognised tier, so every not-yet-reviewed gene would have been printed as
**Excluded** — the exact inversion of its meaning. It now reads "Not yet
reviewed", and the report caps at 30 genes with a count of the remainder, since
176 rows is not a printable document.

## Verified

The whole page was loaded in real Chromium against the real data:

- home page shows the v2 figures (97.9%, 0.966)
- demo patient classifies, subtype stability gauge renders, all six subtypes
  compared, signature and pathway scores present
- biomarker panel renders with 22 candidates for MES, all four filters, search
- expanding a gene shows the dependency picture, the numbers, the function, the
  evidence, the sources and the lookups
- no raw column names anywhere in the rendered text
- no page errors

## Fallback

`biomarkerPanel()` requires the v2 shape (`metrics` and `lookup_templates`) and
returns null otherwise, so against an old `biomarkers.json` the site falls back
to the previous inline table instead of rendering a panel with every metric
missing.

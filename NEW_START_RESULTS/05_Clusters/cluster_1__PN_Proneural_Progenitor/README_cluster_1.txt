CLUSTER 1  --  PN_Proneural_Progenitor
==========================================================================

Patients            : 49  (14.9% of the cohort)
Core (confident)    : 44
Boundary (mixed)    : 5
Verhaak identity    : Proneural-like
Pathway identity    : PPR_PROLIFERATION

BIOLOGY
-------
Proneural / neural-progenitor. 96% of its patients match the Verhaak Proneur
al signature. High proliferation-progenitor and neuronal pathway scores. Mar
kers: NKAIN1, DCX, ATCAY, SCN3A, MARCKSL1.

MEAN VERHAAK SIGNATURE SCORES
-----------------------------
  Proneural      +1.0391
  Classical      -0.3263
  Mesenchymal    -0.7494
  Neural         +0.1766

MEAN PATHWAY PROXY SCORES
-------------------------
  MTC_OXPHOS               +0.0081
  GPM_GLYCOLYSIS_LIPID     +0.0720
  PPR_PROLIFERATION        +0.6632
  NEU_NEURONAL             +0.5285
  OLIGODENDROCYTE_MYELIN   +0.4447
  IMMUNE_MYELOID           -0.7952
  HYPOXIA_ANGIOGENESIS     +0.0422

TOP 25 MARKER GENES (up vs all other clusters)
---------------------------------------------
  NKAIN1           log2FC=+1.681  t=+18.5  FDR=4.28e-30
  KLHL23           log2FC=+1.475  t=+18.1  FDR=1.58e-34
  ZDHHC22          log2FC=+1.334  t=+17.2  FDR=4.34e-35
  PLPPR1           log2FC=+1.411  t=+17.2  FDR=1.68e-32
  BCL7A            log2FC=+1.626  t=+17.1  FDR=4.39e-27
  SRSF12           log2FC=+1.563  t=+17.0  FDR=5.36e-28
  ATCAY            log2FC=+1.434  t=+16.8  FDR=1.74e-30
  MARCKSL1         log2FC=+1.407  t=+16.7  FDR=4.92e-31
  MEX3A            log2FC=+1.454  t=+16.7  FDR=1.67e-29
  PHACTR3          log2FC=+1.342  t=+16.6  FDR=2.70e-32
  SBK1             log2FC=+1.520  t=+16.5  FDR=1.66e-27
  DCX              log2FC=+1.509  t=+16.4  FDR=2.73e-27
  SLCO5A1          log2FC=+1.703  t=+16.3  FDR=8.84e-24
  FAM171A2         log2FC=+1.398  t=+16.0  FDR=2.06e-28
  SATB1            log2FC=+1.500  t=+16.0  FDR=3.89e-26
  RAB9B            log2FC=+1.513  t=+15.9  FDR=1.16e-25
  FAXC             log2FC=+1.474  t=+15.7  FDR=6.52e-26
  SCN3A            log2FC=+1.437  t=+15.7  FDR=1.34e-26
  FAM117B          log2FC=+1.667  t=+15.6  FDR=9.37e-23
  C16orf87         log2FC=+1.662  t=+15.6  FDR=9.03e-23
  TMEM169          log2FC=+1.520  t=+15.6  FDR=1.24e-24
  LINC02210        log2FC=+1.490  t=+15.5  FDR=5.48e-25
  RNF165           log2FC=+1.571  t=+15.4  FDR=2.22e-23
  CRMP1            log2FC=+1.425  t=+15.4  FDR=1.01e-25
  TOX3             log2FC=+1.590  t=+15.3  FDR=8.55e-23

FILES
-----
  patients_cluster_X.csv   every patient with confidence + all scores
  sample_ids_ALL.txt       plain list of GDC sample UUIDs
  sample_ids_CORE_only.txt only the high-confidence patients
  top100_marker_genes.csv  differential expression vs the rest

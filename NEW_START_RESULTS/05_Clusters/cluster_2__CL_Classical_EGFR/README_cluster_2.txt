CLUSTER 2  --  CL_Classical_EGFR
==========================================================================

Patients            : 65  (19.8% of the cohort)
Core (confident)    : 57
Boundary (mixed)    : 8
Verhaak identity    : Classical-like
Pathway identity    : PPR_PROLIFERATION

BIOLOGY
-------
Classical. 82% Verhaak-Classical. Driven by the EGFR / RTK-MAPK axis - EGFR 
itself plus its own negative-feedback regulators SPRY1/2/4 and SPRED2, the c
anonical signature of sustained EGFR signalling.

MEAN VERHAAK SIGNATURE SCORES
-----------------------------
  Proneural      -0.1592
  Classical      +0.6144
  Mesenchymal    -0.2741
  Neural         -0.3781

MEAN PATHWAY PROXY SCORES
-------------------------
  MTC_OXPHOS               +0.0636
  GPM_GLYCOLYSIS_LIPID     -0.0719
  PPR_PROLIFERATION        +0.2181
  NEU_NEURONAL             -0.3233
  OLIGODENDROCYTE_MYELIN   -0.6160
  IMMUNE_MYELOID           -0.5493
  HYPOXIA_ANGIOGENESIS     -0.0271

TOP 25 MARKER GENES (up vs all other clusters)
---------------------------------------------
  MEOX2            log2FC=+1.149  t=+13.8  FDR=3.33e-27
  VAV3             log2FC=+1.255  t=+12.6  FDR=2.35e-21
  SPRY2            log2FC=+1.130  t=+12.1  FDR=2.34e-21
  ETV4             log2FC=+1.280  t=+12.0  FDR=2.64e-19
  AC064875.1       log2FC=+1.137  t=+11.6  FDR=1.13e-19
  ZNF558           log2FC=+1.057  t=+11.3  FDR=1.46e-19
  EYA2             log2FC=+1.114  t=+11.3  FDR=7.72e-19
  SPRY1            log2FC=+1.186  t=+11.2  FDR=1.11e-17
  SPRY4            log2FC=+1.074  t=+10.6  FDR=3.25e-17
  SPRED2           log2FC=+1.085  t=+10.6  FDR=5.56e-17
  TRIB2            log2FC=+1.101  t=+10.6  FDR=8.10e-17
  LINC02587        log2FC=+1.027  t=+10.5  FDR=2.55e-17
  ZNF521           log2FC=+0.994  t=+10.4  FDR=2.98e-17
  TGIF2            log2FC=+1.208  t=+10.3  FDR=2.97e-15
  RHOJ             log2FC=+1.129  t=+10.3  FDR=9.31e-16
  ZNF426           log2FC=+1.069  t=+10.2  FDR=4.94e-16
  EGFR             log2FC=+1.087  t=+10.1  FDR=2.11e-15
  LHFPL6           log2FC=+1.086  t=+9.9  FDR=5.14e-15
  FKBP10           log2FC=+1.026  t=+9.9  FDR=1.97e-15
  EPHB4            log2FC=+0.985  t=+9.9  FDR=1.42e-15
  CLPX             log2FC=+0.932  t=+9.8  FDR=1.04e-15
  ZC3H14           log2FC=+0.978  t=+9.7  FDR=3.04e-15
  RAB34            log2FC=+0.831  t=+9.7  FDR=1.56e-16
  TMEM221          log2FC=+1.002  t=+9.7  FDR=5.17e-15
  PLCG1            log2FC=+1.028  t=+9.5  FDR=3.10e-14

FILES
-----
  patients_cluster_X.csv   every patient with confidence + all scores
  sample_ids_ALL.txt       plain list of GDC sample UUIDs
  sample_ids_CORE_only.txt only the high-confidence patients
  top100_marker_genes.csv  differential expression vs the rest

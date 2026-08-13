CLUSTER 0  --  MTC_Mitochondrial_OXPHOS
==========================================================================

Patients            : 40  (12.2% of the cohort)
Core (confident)    : 26
Boundary (mixed)    : 14
Verhaak identity    : Mixed(Neural-leaning)
Pathway identity    : MTC_OXPHOS

BIOLOGY
-------
OXPHOS / mitochondrial-ribosome high. Matches the published MITOCHONDRIAL (M
TC) GBM subtype (Garofano et al. 2021, Nature Cancer) which is selectively v
ulnerable to OXPHOS inhibitors and carries the most favourable prognosis of 
the pathway-based subtypes.

MEAN VERHAAK SIGNATURE SCORES
-----------------------------
  Proneural      -0.3477
  Classical      -0.1616
  Mesenchymal    -0.3032
  Neural         -0.0030

MEAN PATHWAY PROXY SCORES
-------------------------
  MTC_OXPHOS               +0.6661
  GPM_GLYCOLYSIS_LIPID     -0.2721
  PPR_PROLIFERATION        -0.0199
  NEU_NEURONAL             -0.2779
  OLIGODENDROCYTE_MYELIN   -0.1437
  IMMUNE_MYELOID           -0.0315
  HYPOXIA_ANGIOGENESIS     -0.3640

TOP 25 MARKER GENES (up vs all other clusters)
---------------------------------------------
  LAMTOR4          log2FC=+1.552  t=+12.4  FDR=7.50e-15
  POLR2I           log2FC=+1.357  t=+11.8  FDR=7.50e-15
  GET3             log2FC=+1.522  t=+11.5  FDR=1.07e-13
  LSM4             log2FC=+1.339  t=+11.4  FDR=2.27e-14
  ATP5MF           log2FC=+1.523  t=+11.4  FDR=1.40e-13
  NDUFA2           log2FC=+1.519  t=+11.4  FDR=1.52e-13
  MRPS12           log2FC=+1.396  t=+11.4  FDR=5.40e-14
  SNRNP25          log2FC=+1.334  t=+11.3  FDR=3.20e-14
  FIS1             log2FC=+1.412  t=+11.2  FDR=1.39e-13
  POP7             log2FC=+1.249  t=+11.1  FDR=2.61e-14
  DPM3             log2FC=+1.450  t=+11.1  FDR=2.12e-13
  ALKBH7           log2FC=+1.546  t=+11.1  FDR=3.96e-13
  NDUFB10          log2FC=+1.462  t=+11.1  FDR=2.41e-13
  ELOB             log2FC=+1.401  t=+11.0  FDR=1.89e-13
  SNAPIN           log2FC=+1.432  t=+11.0  FDR=2.38e-13
  NUDT16L1         log2FC=+1.469  t=+11.0  FDR=3.26e-13
  POLR2L           log2FC=+1.335  t=+10.9  FDR=1.60e-13
  NDUFB7           log2FC=+1.457  t=+10.9  FDR=4.63e-13
  COX5B            log2FC=+1.503  t=+10.8  FDR=7.20e-13
  NAXE             log2FC=+1.525  t=+10.7  FDR=1.22e-12
  UBL5             log2FC=+1.507  t=+10.7  FDR=1.11e-12
  GPX4             log2FC=+1.385  t=+10.6  FDR=6.70e-13
  ZNHIT1           log2FC=+1.479  t=+10.5  FDR=1.81e-12
  ROMO1            log2FC=+1.384  t=+10.5  FDR=1.01e-12
  ANAPC11          log2FC=+1.443  t=+10.4  FDR=1.75e-12

FILES
-----
  patients_cluster_X.csv   every patient with confidence + all scores
  sample_ids_ALL.txt       plain list of GDC sample UUIDs
  sample_ids_CORE_only.txt only the high-confidence patients
  top100_marker_genes.csv  differential expression vs the rest

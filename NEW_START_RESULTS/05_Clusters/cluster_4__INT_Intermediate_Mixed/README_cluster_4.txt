CLUSTER 4  --  INT_Intermediate_Mixed
==========================================================================

Patients            : 67  (20.4% of the cohort)
Core (confident)    : 54
Boundary (mixed)    : 13
Verhaak identity    : Mixed(Mesenchymal-leaning)
Pathway identity    : NEU_NEURONAL

BIOLOGY
-------
Intermediate / transitional. No dominant signature (36% max). Biologically t
he least distinct group; best interpreted as tumours sitting between states 
rather than as a separate entity. Reported honestly as such.

MEAN VERHAAK SIGNATURE SCORES
-----------------------------
  Proneural      +0.1053
  Classical      +0.1680
  Mesenchymal    +0.2107
  Neural         +0.1630

MEAN PATHWAY PROXY SCORES
-------------------------
  MTC_OXPHOS               -0.3670
  GPM_GLYCOLYSIS_LIPID     +0.0288
  PPR_PROLIFERATION        -0.0618
  NEU_NEURONAL             +0.1140
  OLIGODENDROCYTE_MYELIN   +0.0665
  IMMUNE_MYELOID           +0.0913
  HYPOXIA_ANGIOGENESIS     +0.0691

TOP 25 MARKER GENES (up vs all other clusters)
---------------------------------------------
  OTUD4            log2FC=+1.170  t=+12.9  FDR=1.67e-22
  MAP3K2           log2FC=+1.212  t=+12.4  FDR=2.03e-20
  LNPEP            log2FC=+1.201  t=+12.2  FDR=3.61e-20
  CPLANE1          log2FC=+1.175  t=+12.1  FDR=3.68e-20
  AFF1             log2FC=+1.151  t=+11.9  FDR=3.68e-20
  NADK2-AS1        log2FC=+1.261  t=+11.9  FDR=5.58e-19
  CMTR2            log2FC=+1.137  t=+11.9  FDR=3.87e-20
  SOS1             log2FC=+1.030  t=+11.8  FDR=6.12e-21
  RBM43            log2FC=+1.182  t=+11.8  FDR=1.98e-19
  RESF1            log2FC=+1.115  t=+11.8  FDR=3.68e-20
  CHIC1            log2FC=+1.194  t=+11.8  FDR=2.84e-19
  DMXL1            log2FC=+1.089  t=+11.7  FDR=3.61e-20
  C5orf51          log2FC=+1.074  t=+11.7  FDR=3.61e-20
  ZBTB41           log2FC=+1.042  t=+11.6  FDR=3.61e-20
  ZNF117           log2FC=+1.092  t=+11.6  FDR=1.22e-19
  ZMYM6            log2FC=+1.132  t=+11.5  FDR=5.89e-19
  MOB1B            log2FC=+1.135  t=+11.4  FDR=8.22e-19
  VPS13A           log2FC=+1.096  t=+11.4  FDR=4.80e-19
  ITSN2            log2FC=+1.125  t=+11.4  FDR=9.43e-19
  MEF2A            log2FC=+1.065  t=+11.3  FDR=2.84e-19
  TASOR            log2FC=+1.016  t=+11.3  FDR=1.24e-19
  SMC5             log2FC=+1.147  t=+11.3  FDR=3.01e-18
  AC010226.1       log2FC=+1.148  t=+11.2  FDR=5.36e-18
  ZMAT1            log2FC=+1.207  t=+11.1  FDR=2.17e-17
  DYNC2H1          log2FC=+1.144  t=+11.1  FDR=7.56e-18

FILES
-----
  patients_cluster_X.csv   every patient with confidence + all scores
  sample_ids_ALL.txt       plain list of GDC sample UUIDs
  sample_ids_CORE_only.txt only the high-confidence patients
  top100_marker_genes.csv  differential expression vs the rest

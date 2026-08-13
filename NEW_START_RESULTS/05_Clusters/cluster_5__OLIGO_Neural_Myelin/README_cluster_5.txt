CLUSTER 5  --  OLIGO_Neural_Myelin
==========================================================================

Patients            : 44  (13.4% of the cohort)
Core (confident)    : 35
Boundary (mixed)    : 9
Verhaak identity    : Mixed(Proneural-leaning)
Pathway identity    : OLIGODENDROCYTE_MYELIN

BIOLOGY
-------
Oligodendrocytic / myelin-high with a strong neuronal component (MBP, PLP1, 
MAG, MOG, CNP, MYRF, UGT8). Corresponds to the neural/oligodendrocyte axis -
 partly genuine OPC-like tumour biology, partly normal white-matter admixtur
e, which is exactly why the old "Neural" subtype was retired.

MEAN VERHAAK SIGNATURE SCORES
-----------------------------
  Proneural      +0.4060
  Classical      -0.2230
  Mesenchymal    -0.1127
  Neural         +0.5411

MEAN PATHWAY PROXY SCORES
-------------------------
  MTC_OXPHOS               +0.1556
  GPM_GLYCOLYSIS_LIPID     +0.1180
  PPR_PROLIFERATION        -0.1645
  NEU_NEURONAL             +0.8349
  OLIGODENDROCYTE_MYELIN   +0.9914
  IMMUNE_MYELOID           +0.1512
  HYPOXIA_ANGIOGENESIS     -0.1494

TOP 25 MARKER GENES (up vs all other clusters)
---------------------------------------------
  TUBB4A           log2FC=+1.481  t=+14.6  FDR=5.77e-20
  LGI3             log2FC=+1.567  t=+14.2  FDR=2.32e-18
  MAG              log2FC=+1.335  t=+13.1  FDR=3.35e-18
  FA2H             log2FC=+1.429  t=+13.0  FDR=3.55e-17
  BCAS1            log2FC=+1.260  t=+12.9  FDR=1.96e-18
  TF               log2FC=+1.292  t=+12.9  FDR=3.35e-18
  PPP1R16B         log2FC=+1.556  t=+12.6  FDR=1.48e-15
  MBP              log2FC=+1.413  t=+12.4  FDR=4.85e-16
  SRCIN1           log2FC=+1.422  t=+12.1  FDR=1.85e-15
  MOG              log2FC=+1.320  t=+12.1  FDR=4.85e-16
  UGT8             log2FC=+1.145  t=+12.1  FDR=7.94e-18
  PLP1             log2FC=+1.275  t=+12.0  FDR=3.28e-16
  VSTM2B           log2FC=+1.276  t=+11.8  FDR=8.43e-16
  CNP              log2FC=+1.482  t=+11.8  FDR=1.71e-14
  ADCY5            log2FC=+1.295  t=+11.5  FDR=5.70e-15
  TMEM151A         log2FC=+1.440  t=+11.5  FDR=4.40e-14
  RASGEF1C         log2FC=+1.181  t=+11.5  FDR=9.18e-16
  SYNDIG1          log2FC=+1.061  t=+11.4  FDR=5.22e-17
  MYRF             log2FC=+1.320  t=+11.3  FDR=1.99e-14
  STMN4            log2FC=+1.066  t=+11.1  FDR=4.85e-16
  DUSP26           log2FC=+1.100  t=+11.1  FDR=1.13e-15
  PRKCZ            log2FC=+1.417  t=+11.1  FDR=1.83e-13
  GABRA3           log2FC=+1.250  t=+11.0  FDR=3.27e-14
  OPCML            log2FC=+1.138  t=+11.0  FDR=4.99e-15
  GPR62            log2FC=+1.589  t=+11.0  FDR=8.88e-13

FILES
-----
  patients_cluster_X.csv   every patient with confidence + all scores
  sample_ids_ALL.txt       plain list of GDC sample UUIDs
  sample_ids_CORE_only.txt only the high-confidence patients
  top100_marker_genes.csv  differential expression vs the rest

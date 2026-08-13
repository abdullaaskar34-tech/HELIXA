CLUSTER 3  --  MES_Mesenchymal_Immune
==========================================================================

Patients            : 63  (19.2% of the cohort)
Core (confident)    : 57
Boundary (mixed)    : 6
Verhaak identity    : Mesenchymal-like
Pathway identity    : IMMUNE_MYELOID

BIOLOGY
-------
Mesenchymal. 98% Verhaak-Mesenchymal - the purest cluster found. Dominated b
y myeloid / microglia-macrophage and complement genes (CD14, CD163, FCGR2A/B
, C1R, C1S, ALOX5): heavy immune infiltration.

MEAN VERHAAK SIGNATURE SCORES
-----------------------------
  Proneural      -0.8186
  Classical      -0.3003
  Mesenchymal    +0.9128
  Neural         -0.2966

MEAN PATHWAY PROXY SCORES
-------------------------
  MTC_OXPHOS               -0.2132
  GPM_GLYCOLYSIS_LIPID     +0.0779
  PPR_PROLIFERATION        -0.5476
  NEU_NEURONAL             -0.6054
  OLIGODENDROCYTE_MYELIN   -0.3823
  IMMUNE_MYELOID           +1.0025
  HYPOXIA_ANGIOGENESIS     +0.2571

TOP 25 MARKER GENES (up vs all other clusters)
---------------------------------------------
  GNA15            log2FC=+1.524  t=+20.2  FDR=0.00e+00
  F13A1            log2FC=+1.536  t=+20.0  FDR=0.00e+00
  S100A11          log2FC=+1.469  t=+18.7  FDR=0.00e+00
  SERPINA1         log2FC=+1.444  t=+17.3  FDR=3.23e-35
  DPYD             log2FC=+1.440  t=+17.2  FDR=3.23e-35
  CD14             log2FC=+1.442  t=+16.9  FDR=1.45e-33
  GLIPR1           log2FC=+1.496  t=+16.9  FDR=4.94e-32
  NPC2             log2FC=+1.539  t=+16.8  FDR=1.19e-30
  CACNA2D4         log2FC=+1.535  t=+16.4  FDR=1.52e-29
  CTSB             log2FC=+1.702  t=+16.4  FDR=1.35e-26
  C1S              log2FC=+1.260  t=+16.3  FDR=1.53e-36
  ALOX5            log2FC=+1.447  t=+16.2  FDR=6.21e-31
  NCF4             log2FC=+1.483  t=+16.2  FDR=6.80e-30
  FCGR2B           log2FC=+1.466  t=+16.1  FDR=5.80e-30
  RBM47            log2FC=+1.338  t=+16.0  FDR=7.12e-33
  MYO1G            log2FC=+1.482  t=+15.9  FDR=6.19e-29
  FCGR2A           log2FC=+1.520  t=+15.9  FDR=5.07e-28
  C1R              log2FC=+1.283  t=+15.8  FDR=1.71e-33
  LRRC25           log2FC=+1.422  t=+15.7  FDR=1.25e-29
  CD163            log2FC=+1.431  t=+15.7  FDR=2.93e-29
  PLAUR            log2FC=+1.541  t=+15.6  FDR=8.01e-27
  CTSZ             log2FC=+1.486  t=+15.5  FDR=1.92e-27
  ITGB2            log2FC=+1.311  t=+15.4  FDR=3.08e-31
  HK3              log2FC=+1.541  t=+15.3  FDR=4.10e-26
  LAIR1            log2FC=+1.416  t=+15.3  FDR=3.46e-28

FILES
-----
  patients_cluster_X.csv   every patient with confidence + all scores
  sample_ids_ALL.txt       plain list of GDC sample UUIDs
  sample_ids_CORE_only.txt only the high-confidence patients
  top100_marker_genes.csv  differential expression vs the rest

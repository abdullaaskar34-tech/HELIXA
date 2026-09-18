"""
Rebuild the exact training state from raw inputs and verify it against the
frozen artifacts. Nothing may proceed until this passes: the new model has to
live in precisely the same numeric space as the clustering that produced the
labels.
"""
import warnings, joblib, json
import numpy as np, pandas as pd
warnings.filterwarnings('ignore')

UP  = '/mnt/user-data/uploads/TEKNOFEST_ONCOLOGY/new_start'
PREP = f'{UP}/01_Data_Preparation'
HX  = f'{UP}/HELIXA/NEW_START_RESULTS'

art = joblib.load(f'{HX}/10_Prediction_Model/model_artifacts.joblib')
print('artifact keys:', sorted(art.keys()))
print('model       :', art['model_name'], '|', art['model'])
print('K           :', art['K'])
print('threshold   :', art['protocol_threshold'])

Xall = np.load(f'{PREP}/log2tpm_filtered.npy')
genes = pd.read_csv(f'{PREP}/genes_filtered.csv')
samples = pd.read_csv(f'{PREP}/samples.csv')
assign = pd.read_csv(f'{HX}/04_Consensus_Clustering/final_patient_assignments.csv')
E_saved = np.load(f'{HX}/04_Consensus_Clustering/final_embedding.npy')

print('\nlog2tpm_filtered :', Xall.shape, Xall.dtype)
print('genes_filtered   :', genes.shape, list(genes.columns))
print('samples          :', samples.shape, list(samples.columns))
print('assignments      :', assign.shape)
print('assign columns   :', list(assign.columns))
print('embedding saved  :', E_saved.shape)

# order check: assignment file vs samples.csv
s_prep = samples['sample_id'].astype(str).values
s_assign = assign['sample_id'].astype(str).values
print('\nsample order identical prep vs assignments:', bool((s_prep == s_assign).all()))

KEEP = art['KEEP_mask']
NPA  = art['NONPOLYA_mask']
gidx = art['signature_gene_idx']
bmeans = art['batch_means']
gsd = art['global_sd']
pca = art['pca']
print('KEEP sum         :', int(KEEP.sum()))
print('NONPOLYA sum     :', int(NPA.sum()))
print('signature genes  :', gidx.shape)
print('batch_means keys :', sorted(bmeans.keys()), [v.shape for v in bmeans.values()])
print('global_sd        :', gsd.shape)
print('pca n_components :', pca.n_components_)

# ---- batch labels from the assignment file (library_batch column)
lb = assign['library_batch'].astype(str).values
print('\nlibrary_batch values:', sorted(set(lb)))
batch = (lb == 'totalRNA_rRNAdepleted').astype(int)
print('batch counts      : polyA=%d  totalRNA=%d' % ((batch == 0).sum(), (batch == 1).sum()))

# ---- reproduce the training space exactly (mirrors 11_build_classifier.py)
tpm = np.power(2.0, Xall) - 1.0
tpm_k = tpm[KEEP, :]
tpm_k = tpm_k / tpm_k.sum(0, keepdims=True) * 1e6
Y = np.log2(tpm_k + 1.0).astype(np.float32)

bm_rebuilt = {int(b): Y[:, batch == b].mean(1) for b in np.unique(batch)}
for b in sorted(bm_rebuilt):
    d = np.abs(bm_rebuilt[b] - bmeans[b]).max()
    print(f'batch_mean[{b}] max abs diff vs frozen : {d:.3e}')

Zc = np.empty_like(Y)
for b in np.unique(batch):
    Zc[:, batch == b] = Y[:, batch == b] - bmeans[b][:, None]
gsd_rebuilt = Zc.std(1); gsd_rebuilt[gsd_rebuilt == 0] = 1.0
print('global_sd max abs diff vs frozen      : %.3e' % np.abs(gsd_rebuilt - gsd).max())

Z = Zc / gsd[:, None]
E_rebuilt = pca.transform(Z[gidx, :].T)
print('\nembedding max abs diff vs saved       : %.3e' % np.abs(E_rebuilt - E_saved).max())

# ---- protocol detector
frac = tpm[NPA, :].sum(0) / tpm.sum(0)
thr = art['protocol_threshold']
acc = ((frac > thr).astype(int) == batch).mean()
print('protocol detector accuracy            : %.4f  (threshold %.6f)' % (acc, thr))
print('  polyA  frac max = %.5f' % frac[batch == 0].max())
print('  totalR frac min = %.5f' % frac[batch == 1].min())

np.save('Z_full.npy', Z)
np.save('E_rebuilt.npy', E_rebuilt)
np.save('batch.npy', batch)
np.save('frac.npy', frac)
genes.loc[KEEP].reset_index(drop=True).to_csv('genes_keep.csv', index=False)
print('\nsaved Z_full.npy', Z.shape, '| genes_keep.csv')

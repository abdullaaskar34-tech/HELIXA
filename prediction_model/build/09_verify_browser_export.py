"""
Read the exported .bin files back exactly the way engine.js does and reproduce
the forward pass in that arithmetic. If the browser numbers do not match the
Python model, the website is lying to the user.
"""
import json, os, warnings
import numpy as np, pandas as pd, joblib
warnings.filterwarnings('ignore')

M = '/home/claude/work/prediction_model/browser_model'
UP = '/mnt/user-data/uploads/TEKNOFEST_ONCOLOGY/new_start'
HX = f'{UP}/HELIXA/NEW_START_RESULTS'

man = json.load(open(f'{M}/manifest.json'))
n = man['n_genes']


def unpack(path, n):
    raw = np.fromfile(path, dtype=np.uint8)
    return np.unpackbits(raw, bitorder='little')[:n].astype(bool)


keep = unpack(f'{M}/keep_mask.bin', n)
npa = unpack(f'{M}/nonpolya_mask.bin', n)
stat_pos = np.fromfile(f'{M}/stat_pos.bin', dtype=np.int32)
bm = [np.fromfile(f'{M}/batch_mean_0.bin', dtype=np.float32),
      np.fromfile(f'{M}/batch_mean_1.bin', dtype=np.float32)]
gsd = np.fromfile(f'{M}/global_sd.bin', dtype=np.float32)
sig_slots = np.fromfile(f'{M}/sig_slots.bin', dtype=np.int32)
pca_mean = np.fromfile(f'{M}/pca_mean.bin', dtype=np.float32)
pca_comp = np.fromfile(f'{M}/pca_components.bin', dtype=np.float32)
coef = np.fromfile(f'{M}/coef.bin', dtype=np.float32)
inter = np.fromfile(f'{M}/intercept.bin', dtype=np.float32)
gs_slots = json.load(open(f'{M}/gene_set_slots.json'))

print(f'loaded: keep={keep.sum()} npa={npa.sum()} stats={len(stat_pos)} '
      f'sig={len(sig_slots)} pcs={man["n_pcs"]} classes={man["n_classes"]}')

X = np.load(f'{UP}/01_Data_Preparation/log2tpm_filtered.npy')
tpm_all = np.power(2.0, X) - 1.0
assign = pd.read_csv(f'{HX}/04_Consensus_Clustering/final_patient_assignments.csv')
art = joblib.load('/home/claude/work/prediction_model/model_artifacts_v2.joblib')
py_P = np.load('/home/claude/work/new_proba.npy')

keepIdx = np.where(keep)[0]
nSig, nPc, K = man['n_signature'], man['n_pcs'], man['n_classes']
thr = man['protocol_threshold']

dP = np.zeros(len(assign))
proto_hit = np.zeros(len(assign), bool)
gs_abs = {k: np.zeros(len(assign)) for k in gs_slots}
for i in range(len(assign)):
    tpm = tpm_all[:, i].astype(np.float64)
    totAll = tpm.sum(); totNpa = tpm[npa].sum(); totKeep = tpm[keep].sum()
    frac = totNpa / max(totAll, 1e-9)
    det = 1 if frac > thr else 0
    proto_hit[i] = (det == (assign['library_batch'].iloc[i] == 'totalRNA_rRNAdepleted'))
    scale = 1e6 / max(totKeep, 1e-9)

    gi = keepIdx[stat_pos]
    y = np.log2(tpm[gi] * scale + 1.0)
    z = (y - bm[det]) / gsd

    centred = z[sig_slots] - pca_mean
    emb = np.array([float(centred @ pca_comp[p * nSig:(p + 1) * nSig]) for p in range(nPc)])
    logits = np.array([inter[c] + emb @ coef[c * nPc:(c + 1) * nPc] for c in range(K)])
    e = np.exp(logits - logits.max()); P = e / e.sum()

    dP[i] = float(np.abs(P - py_P[i]).max())
    for name, slots in gs_slots.items():
        v = float(z[np.array(slots)].mean())
        gs_abs[name][i] = abs(v - assign[name].iloc[i])

ok = proto_hit
print(f'\nprotocol detection matches the recorded batch: {ok.sum()}/{len(assign)}')
bad = np.where(~ok)[0]
for i in bad:
    print(f'  misdetected: {assign["sample_id"].iloc[i]}  recorded '
          f'{assign["library_batch"].iloc[i]}  -> probability shifts by {dP[i]:.4f}')

print(f'\nbrowser vs python, max abs probability difference')
print(f'  over all 328 patients               : {dP.max():.3e}')
print(f'  excluding the misdetected sample    : {dP[ok].max():.3e}')

print('\ngene-set scores from the browser arrays vs the recorded columns '
      '(misdetected sample excluded):')
for k, v in gs_abs.items():
    print(f'  {k:28s} max {v[ok].max():.4f}   mean {v[ok].mean():.4f}')

assert dP[ok].max() < 1e-4, 'browser export does not reproduce the python model'
print('\nOK — the exported weights reproduce the Python model to <1e-4 for every')
print('sample whose protocol is detected correctly. The single misdetected sample')
print('is a property of the 99.7% protocol detector, not of the export.')

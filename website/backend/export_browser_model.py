# -*- coding: utf-8 -*-
"""
HELIXA — export the frozen model so it can run entirely in the browser.

The classifier's forward pass is pure arithmetic:

    align genes -> detect protocol -> filter -> renormalise to 1e6 -> log2(x+1)
    -> z-score with the stored batch mean/sd -> take 1,000 signature genes
    -> subtract the PCA mean -> 5x1000 matmul -> 6x5 matmul -> softmax

No ML runtime is required, so the same computation can be reproduced exactly in
JavaScript. This script writes the weights that the browser engine needs.

Only the values actually used downstream are exported: the batch means and
standard deviations are needed at the 1,000 signature positions and at the
marker-gene positions, not across all 25,738 retained genes.

Run:  python3 export_browser_model.py
"""
import os, json, struct
import numpy as np
import joblib

RESULTS = os.environ.get('HELIXA_RESULTS',
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'NEW_START_RESULTS')))
OUT = os.environ.get('HELIXA_MODEL_OUT',
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend', 'model')))
os.makedirs(OUT, exist_ok=True)

import helixa_engine as eng
A = joblib.load(os.path.join(RESULTS, '10_Prediction_Model', 'model_artifacts.joblib'))

gene_ids = [str(g) for g in A['lowexpr_gene_ids']]
KEEP = np.asarray(A['KEEP_mask'], dtype=bool)
NPA  = np.asarray(A['NONPOLYA_mask'], dtype=bool)
gnames_all = np.asarray(A['gene_names_filtered']).astype(str)
gnames_keep = gnames_all[KEEP]
sig_idx = np.asarray(A['signature_gene_idx'], dtype=np.int32)      # into KEEP space
bm0, bm1 = A['batch_means'][0], A['batch_means'][1]
gsd = A['global_sd']
pca_mean = A['pca'].mean_.astype(np.float32)
pca_comp = A['pca'].components_.astype(np.float32)
coef = A['model'].coef_.astype(np.float32)
inter = A['model'].intercept_.astype(np.float32)

print(f'genes total {len(gene_ids)} · retained {KEEP.sum()} · signature {len(sig_idx)}')

# ── which extra genes do we need for the marker read-out? ──────────────────
gpos = {}
for i, g in enumerate(gnames_keep):
    gpos.setdefault(g, i)
marker_genes = sorted({g for info in eng.SUBTYPE_INFO.values() for g in info['markers']})
marker_pos = [gpos[g] for g in marker_genes if g in gpos]
marker_names = [g for g in marker_genes if g in gpos]
print(f'marker genes resolved: {len(marker_names)}')

# positions in KEEP space we need mean/sd for
needed = np.array(sorted(set(sig_idx.tolist()) | set(marker_pos)), dtype=np.int32)
pos_of = {int(p): i for i, p in enumerate(needed)}
print(f'stats needed at {len(needed)} positions (instead of {KEEP.sum()})')

def f32(path, arr):
    a = np.ascontiguousarray(np.asarray(arr, dtype=np.float32))
    a.tofile(os.path.join(OUT, path)); return a.nbytes

def i32(path, arr):
    a = np.ascontiguousarray(np.asarray(arr, dtype=np.int32))
    a.tofile(os.path.join(OUT, path)); return a.nbytes

def bits(path, mask):
    """pack a boolean mask into bytes, LSB-first"""
    packed = np.packbits(np.asarray(mask, dtype=bool), bitorder='little')
    packed.tofile(os.path.join(OUT, path)); return packed.nbytes

total = 0
# gene identifiers, in the exact order the model expects.
# The ENSG prefix is constant, so it is stripped and re-added in the browser.
ids_txt = '\n'.join(g.replace('ENSG', '') for g in gene_ids)
with open(os.path.join(OUT, 'gene_ids.txt'), 'w') as f:
    f.write(ids_txt)
total += len(ids_txt.encode())

total += bits('keep_mask.bin', KEEP)
total += bits('nonpolya_mask.bin', NPA)
total += i32('stat_pos.bin', needed)                       # positions in KEEP space
total += f32('batch_mean_0.bin', bm0[needed])
total += f32('batch_mean_1.bin', bm1[needed])
total += f32('global_sd.bin',    gsd[needed])
total += i32('sig_slots.bin', [pos_of[int(p)] for p in sig_idx])   # sig -> stats row
total += f32('pca_mean.bin', pca_mean)
total += f32('pca_components.bin', pca_comp.ravel())
total += f32('coef.bin', coef.ravel())
total += f32('intercept.bin', inter)

with open(os.path.join(OUT, 'sig_gene_names.txt'), 'w') as f:
    txt = '\n'.join(gnames_keep[sig_idx].tolist()); f.write(txt); total += len(txt.encode())

manifest = {
    'version': '1.0.0',
    'model': A['model_name'],
    'n_genes': len(gene_ids),
    'n_keep': int(KEEP.sum()),
    'n_signature': int(len(sig_idx)),
    'n_stats': int(len(needed)),
    'n_pcs': int(pca_comp.shape[0]),
    'n_classes': int(coef.shape[0]),
    'protocol_threshold': float(A['protocol_threshold']),
    'protocol_threshold_accuracy': float(A.get('protocol_threshold_accuracy', 0.997)),
    'cv_accuracy': float(A.get('cv_accuracy', 0)),
    'roc_auc_ovr': float(A.get('roc_auc_ovr', 0)),
    'loo_accuracy': float(A.get('loo_accuracy', 0)),
    'markers': {str(k): v['markers'] for k, v in eng.SUBTYPE_INFO.items()},
    'marker_slots': {g: pos_of[gpos[g]] for g in marker_names},
    'subtypes': {str(k): {'label': v['label'], 'title': v['title'],
                          'summary': v['summary'], 'therapeutic': v['therapeutic']}
                 for k, v in eng.SUBTYPE_INFO.items()},
}
with open(os.path.join(OUT, 'manifest.json'), 'w') as f:
    json.dump(manifest, f, separators=(',', ':'))

print(f'\nwritten to {OUT}')
for fn in sorted(os.listdir(OUT)):
    print(f'  {fn:24s} {os.path.getsize(os.path.join(OUT, fn))/1024:9.1f} KB')
print(f'  {"TOTAL":24s} {sum(os.path.getsize(os.path.join(OUT,f)) for f in os.listdir(OUT))/1024:9.1f} KB')

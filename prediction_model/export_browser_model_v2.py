# -*- coding: utf-8 -*-
"""
Export the v2 calibrated model for in-browser inference.

Same binary layout as v1 so the engine changes stay small, with two additions:
  * the statistics positions now cover every gene-set gene as well as the
    signature and marker genes, so the browser can compute the Verhaak
    signature and pathway scores itself instead of only the classifier output;
  * the manifest carries the gene-set slot maps and the v2 calibration metrics.

Run:  python3 export_browser_model_v2.py [--out DIR]
"""
import os, json, argparse
import numpy as np, joblib

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument('--artifacts', default=os.path.join(HERE, 'model_artifacts_v2.joblib'))
ap.add_argument('--old-manifest', default=None,
                help='v1 manifest.json, reused for the subtype descriptions')
ap.add_argument('--out', default=os.path.join(HERE, 'browser_model'))
args = ap.parse_args()
os.makedirs(args.out, exist_ok=True)

A = joblib.load(args.artifacts)
gene_ids = [str(g) for g in A['lowexpr_gene_ids']]
KEEP = np.asarray(A['KEEP_mask'], dtype=bool)
NPA = np.asarray(A['NONPOLYA_mask'], dtype=bool)
gnames_keep = np.asarray(A['gene_names_filtered']).astype(str)[KEEP]
sig_idx = np.asarray(A['signature_gene_idx'], dtype=np.int32)
bm0, bm1 = A['batch_means'][0], A['batch_means'][1]
gsd = A['global_sd']
pca_mean = A['pca'].mean_.astype(np.float32)
pca_comp = A['pca'].components_.astype(np.float32)
coef = A['model'].coef_.astype(np.float32)
inter = A['model'].intercept_.astype(np.float32)

print(f'genes {len(gene_ids)} · retained {KEEP.sum()} · signature {len(sig_idx)}')

MARKERS = {
    0: ['NDUFA2', 'COX5B', 'ATP5MF', 'MRPS12'],
    1: ['NKAIN1', 'DCX', 'ATCAY', 'SCN3A', 'MARCKSL1'],
    2: ['EGFR', 'SPRY1', 'SPRY2', 'SPRY4', 'SPRED2', 'MEOX2'],
    3: ['CD14', 'CD163', 'FCGR2A', 'FCGR2B', 'C1R', 'C1S', 'ALOX5'],
    4: [],
    5: ['MBP', 'PLP1', 'MAG', 'MOG', 'CNP', 'MYRF', 'UGT8'],
}
gpos = {}
for i, g in enumerate(gnames_keep):
    gpos.setdefault(g, i)
marker_names = sorted({g for v in MARKERS.values() for g in v if g in gpos})
marker_pos = [gpos[g] for g in marker_names]

# every position the browser needs a mean/sd for
geneset_pos = set()
for gs in A['gene_sets'].values():
    geneset_pos |= set(int(i) for i in gs['idx'])
needed = np.array(sorted(set(sig_idx.tolist()) | set(marker_pos) | geneset_pos), dtype=np.int32)
pos_of = {int(p): i for i, p in enumerate(needed)}
print(f'stats needed at {len(needed)} positions (v1 used 1017; the extra rows carry '
      f'the Verhaak and pathway gene sets)')


def f32(p, a):
    a = np.ascontiguousarray(np.asarray(a, dtype=np.float32)); a.tofile(os.path.join(args.out, p)); return a.nbytes


def i32(p, a):
    a = np.ascontiguousarray(np.asarray(a, dtype=np.int32)); a.tofile(os.path.join(args.out, p)); return a.nbytes


def bits(p, m):
    a = np.packbits(np.asarray(m, dtype=bool), bitorder='little'); a.tofile(os.path.join(args.out, p)); return a.nbytes


ids_txt = '\n'.join(g.replace('ENSG', '') for g in gene_ids)
open(os.path.join(args.out, 'gene_ids.txt'), 'w').write(ids_txt)
bits('keep_mask.bin', KEEP)
bits('nonpolya_mask.bin', NPA)
i32('stat_pos.bin', needed)
f32('batch_mean_0.bin', bm0[needed])
f32('batch_mean_1.bin', bm1[needed])
f32('global_sd.bin', gsd[needed])
i32('sig_slots.bin', [pos_of[int(p)] for p in sig_idx])
f32('pca_mean.bin', pca_mean)
f32('pca_components.bin', pca_comp.ravel())
f32('coef.bin', coef.ravel())
f32('intercept.bin', inter)
open(os.path.join(args.out, 'sig_gene_names.txt'), 'w').write(
    '\n'.join(gnames_keep[sig_idx].tolist()))

# gene sets, as slot lists into the stats arrays
gene_set_slots = {name: [pos_of[int(i)] for i in gs['idx']]
                  for name, gs in A['gene_sets'].items()}
json.dump(gene_set_slots, open(os.path.join(args.out, 'gene_set_slots.json'), 'w'),
          separators=(',', ':'))

SUB = None
if args.old_manifest and os.path.exists(args.old_manifest):
    SUB = json.load(open(args.old_manifest)).get('subtypes')
if SUB is None:
    SUB = {str(c): {'label': A['cluster_short'][c], 'title': A['cluster_names'][c],
                    'summary': '', 'therapeutic': ''} for c in range(A['K'])}

manifest = {
    'version': '2.0.0',
    'model': 'LogisticRegression (soft consensus target)',
    'calibration': 'trained against the 1000-resample consensus profile',
    'n_genes': len(gene_ids), 'n_keep': int(KEEP.sum()),
    'n_signature': int(len(sig_idx)), 'n_stats': int(len(needed)),
    'n_pcs': int(pca_comp.shape[0]), 'n_classes': int(coef.shape[0]),
    'protocol_threshold': float(A['protocol_threshold']),
    'protocol_threshold_accuracy': 0.99695,
    'core_tau': float(A['core_tau']),
    'n_train': int(A['n_train']),
    'loo_agreement': float(A['loo_agreement']),
    'loo_agreement_core': float(A['loo_agreement_core']),
    'loo_agreement_boundary': float(A['loo_agreement_boundary']),
    'oof_profile_rmse': float(A['oof_profile_rmse']),
    'oof_profile_corr': float(A['oof_profile_corr']),
    'median_confidence': float(A['median_confidence']),
    'probability_meaning':
        'Fraction of 1,000 resampled clusterings in which a tumour with this '
        'expression profile co-clusters with that subtype. Subtype stability, '
        'not clinical probability.',
    'markers': {str(k): v for k, v in MARKERS.items()},
    'marker_slots': {g: pos_of[gpos[g]] for g in marker_names},
    'signature_names': A['signature_names'],
    'pathway_names': A['pathway_names'],
    'verhaak_labels': A['verhaak_labels'],
    'gene_set_sizes': {k: len(v) for k, v in gene_set_slots.items()},
    'subtypes': SUB,
}
json.dump(manifest, open(os.path.join(args.out, 'manifest.json'), 'w'), separators=(',', ':'))

print(f'\nwritten to {args.out}')
tot = 0
for fn in sorted(os.listdir(args.out)):
    sz = os.path.getsize(os.path.join(args.out, fn)); tot += sz
    print(f'  {fn:24s} {sz/1024:9.1f} KB')
print(f'  {"TOTAL":24s} {tot/1024:9.1f} KB')

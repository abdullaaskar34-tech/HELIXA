#!/usr/bin/env python3
"""
HELIXA subtype predictor  (prediction_model v2)
================================================

Assign a glioblastoma RNA-seq sample to one of the six HELIXA subtypes and
report how stably it belongs there.

    python3 predict.py PATIENT.tsv
    python3 predict.py PATIENT.tsv --json out.json
    python3 predict.py *.tsv --csv batch_results.csv

INPUT
  A GDC `augmented_star_gene_counts.tsv` (needs the `gene_id` and
  `tpm_unstranded` columns). Either library protocol is fine - the protocol is
  detected from the data and the matching correction is applied.

WHAT THE PERCENTAGE MEANS
  The model is trained against the consensus-clustering profile: the fraction of
  1,000 resampled clusterings in which a tumour co-clusters with each subtype.
  So "73% CL" means this expression profile lands in the Classical cluster in
  roughly 73% of resampled clusterings. It is a measure of how stably the tumour
  belongs to that subtype - NOT a diagnostic probability, and not a statement
  that the patient has a 73% chance of anything clinically.

  Probabilities below ~0.5, or a margin under 0.50 between the top two
  subtypes, mark an intermediate tumour. That is a real finding about the
  tumour, not a failure of the model: 55 of the 328 training tumours are
  intermediate in exactly this way.
"""
import argparse, json, sys, os
import numpy as np, pandas as pd, joblib

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, 'model_artifacts_v2.joblib')


def load_artifacts(path=ART):
    if not os.path.exists(path):
        sys.exit(f'model artifacts not found at {path}')
    return joblib.load(path)


def parse_gdc(path):
    """Read a GDC counts TSV into {gene_id: tpm}."""
    with open(path, 'r') as f:
        lines = f.read().splitlines()
    hdr_i = None
    for i, ln in enumerate(lines[:10]):
        if 'gene_id' in ln and '\t' in ln:
            hdr_i = i
            break
    if hdr_i is None:
        sys.exit(f'{os.path.basename(path)}: no gene_id header found — '
                 f'is this a GDC augmented_star_gene_counts.tsv?')
    hdr = lines[hdr_i].split('\t')
    if 'tpm_unstranded' not in hdr:
        sys.exit(f'{os.path.basename(path)}: no tpm_unstranded column. '
                 f'Columns: {", ".join(hdr[:8])}')
    gi, ti = hdr.index('gene_id'), hdr.index('tpm_unstranded')
    out = {}
    for ln in lines[hdr_i + 1:]:
        if not ln.startswith('ENSG'):
            continue
        p = ln.split('\t')
        if len(p) <= max(gi, ti):
            continue
        gid = p[gi]
        if gid in out:
            continue
        try:
            out[gid] = float(p[ti])
        except ValueError:
            out[gid] = 0.0
    if len(out) < 1000:
        sys.exit(f'{os.path.basename(path)}: only {len(out)} ENSG rows — file looks truncated.')
    return out


def predict_one(tpm_map, art, sample_id=None):
    gene_ids = art['lowexpr_gene_ids']
    n = len(gene_ids)

    # 1 · align to the training gene space (exact id, then version-stripped)
    tpm = np.zeros(n)
    matched = 0
    stripped = None
    for i, g in enumerate(gene_ids):
        v = tpm_map.get(g)
        if v is None:
            if stripped is None:
                stripped = {k.split('.')[0]: val for k, val in tpm_map.items()}
            v = stripped.get(g.split('.')[0])
        if v is not None:
            tpm[i] = v
            matched += 1
    coverage = matched / n
    if coverage < 0.5:
        raise ValueError(f'only {matched}/{n} genes matched ({coverage*100:.1f}%) — '
                         f'incompatible gene annotation')

    # 2 · detect the library protocol from the non-polyadenylated RNA fraction
    KEEP, NPA = art['KEEP_mask'], art['NONPOLYA_mask']
    tot = tpm.sum()
    frac = tpm[NPA].sum() / max(tot, 1e-9)
    thr = art['protocol_threshold']
    batch = int(frac > thr)
    protocol = 'totalRNA_rRNAdepleted' if batch else 'polyA_selected'
    ambiguous = abs(frac - thr) < 0.03

    # 3 · restrict to the protocol-robust genes and renormalise over THAT space
    tk = tpm[KEEP]
    tk = tk / max(tk.sum(), 1e-9) * 1e6
    Y = np.log2(tk + 1.0)

    # 4 · standardise with the STORED stats of the detected batch
    #     (never re-estimated: one sample has no batch of its own)
    z = (Y - art['batch_means'][batch]) / art['global_sd']

    # 5 · project onto the frozen 5-component PCA of the 1,000 signature genes
    emb = art['pca'].transform(z[art['signature_gene_idx']].reshape(1, -1))

    # 6 · classify
    P = art['model'].predict_proba(emb)[0]
    order = np.argsort(-P)
    top, second = int(order[0]), int(order[1])
    margin = float(P[top] - P[second])

    # 7 · signature and pathway scores, same z vector
    scores = {}
    for name, gs in art['gene_sets'].items():
        scores[name] = float(z[np.array(gs['idx'])].mean())
    vlabels = art['verhaak_labels']
    sigvals = [scores[f'sig_{l}'] for l in vlabels]
    verhaak_nearest = vlabels[int(np.argmax(sigvals))]

    SHORT = art['cluster_short']
    res = {
        'sample_id': sample_id,
        'cluster': top,
        'subtype': SHORT[top],
        'subtype_full': art['cluster_names'][top],
        'probability': round(float(P[top]), 4),
        'margin': round(margin, 4),
        'call': 'CORE' if margin >= art['core_tau'] else 'BOUNDARY',
        'runner_up': SHORT[second],
        'runner_up_probability': round(float(P[second]), 4),
        'probabilities': {SHORT[c]: round(float(P[c]), 4) for c in range(art['K'])},
        'library_batch': protocol,
        'nonpolyA_fraction': round(float(frac), 5),
        'protocol_threshold': round(float(thr), 5),
        'protocol_ambiguous': bool(ambiguous),
        'verhaak_nearest': verhaak_nearest,
        'signature_scores': {k.replace('sig_', ''): round(v, 4)
                             for k, v in scores.items() if k.startswith('sig_')},
        'pathway_scores': {k.replace('pw_', ''): round(v, 4)
                           for k, v in scores.items() if k.startswith('pw_')},
        'embedding': [round(float(v), 4) for v in emb[0]],
        'genes_matched': int(matched),
        'genes_expected': int(n),
        'coverage_pct': round(coverage * 100, 2),
    }
    if sample_id and sample_id in art.get('training_cohort', {}):
        rec = art['training_cohort'][sample_id]
        res['in_training_cohort'] = True
        res['recorded_cluster'] = rec['cluster']
        res['recorded_subtype'] = SHORT[rec['cluster']]
        res['recorded_consensus_own'] = rec['consensus_own']
        res['recorded_is_core'] = rec['is_core']
        res['recorded_library_batch'] = rec['library_batch']
        res['agrees_with_record'] = (rec['cluster'] == top)
    else:
        res['in_training_cohort'] = False
    return res


def render(r):
    L = []
    a = L.append
    a('=' * 68)
    a(f"  {r['sample_id'] or 'sample'}")
    a('=' * 68)
    a(f"  SUBTYPE        {r['subtype']} — {r['subtype_full']}")
    a(f"  PROBABILITY    {r['probability']*100:.1f}%   "
      f"(runner-up {r['runner_up']} at {r['runner_up_probability']*100:.1f}%)")
    a(f"  CALL           {r['call']}   margin {r['margin']:.3f}")
    a('')
    a('  subtype stability across resampled clusterings')
    for k, v in sorted(r['probabilities'].items(), key=lambda kv: -kv[1]):
        bar = '#' * int(round(v * 40))
        a(f'    {k:<6s} {v*100:5.1f}%  {bar}')
    a('')
    a(f"  LIBRARY BATCH  {r['library_batch']}"
      f"   (non-polyA fraction {r['nonpolyA_fraction']:.4f} vs threshold "
      f"{r['protocol_threshold']:.4f})")
    if r['protocol_ambiguous']:
        a('                 WARNING: close to the protocol decision threshold')
    a(f"  GENE COVERAGE  {r['genes_matched']}/{r['genes_expected']} ({r['coverage_pct']:.1f}%)")
    a('')
    a(f"  VERHAAK NEAREST  {r['verhaak_nearest']}")
    a('  signature scores')
    for k, v in r['signature_scores'].items():
        a(f'    {k:<14s} {v:+.4f}')
    a('  pathway scores')
    for k, v in r['pathway_scores'].items():
        a(f'    {k:<24s} {v:+.4f}')
    if r['in_training_cohort']:
        a('')
        a('  THIS SAMPLE IS IN THE TRAINING COHORT')
        a(f"    recorded subtype      {r['recorded_subtype']} (cluster {r['recorded_cluster']})")
        a(f"    recorded consensus    {r['recorded_consensus_own']:.4f}")
        a(f"    recorded call         {'CORE' if r['recorded_is_core'] else 'BOUNDARY'}")
        a(f"    recorded library      {r['recorded_library_batch']}")
        a(f"    model agrees          {'YES' if r['agrees_with_record'] else 'NO'}")
    a('')
    a('  The percentage is subtype STABILITY (how often this profile co-clusters')
    a('  with that subtype across 1,000 resamplings), not a clinical probability.')
    a('=' * 68)
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser(description='HELIXA subtype predictor v2')
    ap.add_argument('tsv', nargs='+', help='GDC augmented_star_gene_counts.tsv file(s)')
    ap.add_argument('--json', help='write results as JSON')
    ap.add_argument('--csv', help='write a flat CSV summary')
    ap.add_argument('--model', default=ART, help='path to model_artifacts_v2.joblib')
    ap.add_argument('--quiet', action='store_true')
    args = ap.parse_args()

    art = load_artifacts(args.model)
    out = []
    for p in args.tsv:
        sid = os.path.basename(p).split('.')[0]
        try:
            r = predict_one(parse_gdc(p), art, sid)
        except Exception as e:
            print(f'{p}: FAILED — {e}', file=sys.stderr)
            continue
        out.append(r)
        if not args.quiet:
            print(render(r))

    if args.json:
        json.dump(out if len(out) != 1 else out[0], open(args.json, 'w'), indent=2)
        print(f'wrote {args.json}')
    if args.csv:
        rows = []
        for r in out:
            row = {k: v for k, v in r.items()
                   if not isinstance(v, (dict, list))}
            row.update({f'p_{k}': v for k, v in r['probabilities'].items()})
            row.update({f'sig_{k}': v for k, v in r['signature_scores'].items()})
            row.update({f'pw_{k}': v for k, v in r['pathway_scores'].items()})
            rows.append(row)
        pd.DataFrame(rows).to_csv(args.csv, index=False)
        print(f'wrote {args.csv}')


if __name__ == '__main__':
    main()

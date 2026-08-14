# -*- coding: utf-8 -*-
"""
HELIXA — inference engine.

This module is a THIN WRAPPER around the project's existing prediction pipeline
(NEW_START_RESULTS/10_Prediction_Model/). It does not reimplement the science:
it loads the same frozen `model_artifacts.joblib` and reproduces the exact same
eight steps as `predict_new_patient.py`, only instrumented so the web UI can
report progress stage by stage.

Nothing is simulated. If the artifacts are missing, the engine reports itself
unavailable rather than inventing a prediction.
"""
from __future__ import annotations
import os, time, io, re
from typing import Callable, Optional
import numpy as np
import pandas as pd

RESULTS_ROOT = os.environ.get(
    'HELIXA_RESULTS',
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'NEW_START_RESULTS')))
ARTIFACTS = os.path.join(RESULTS_ROOT, '10_Prediction_Model', 'model_artifacts.joblib')

CONF_HIGH, CONF_LOW = 0.80, 0.50

SUBTYPE_INFO = {
 0: {'label':'MTC','title':'Mitochondrial / OXPHOS',
     'summary':'Oxidative-phosphorylation–driven tumour. Matches the published MITOCHONDRIAL (MTC) subtype.',
     'therapeutic':'The MTC subtype carries the most favourable prognosis of the pathway-based subtypes and is selectively vulnerable to OXPHOS inhibitors (Garofano et al., Nature Cancer 2021).',
     'markers':['NDUFA2','COX5B','ATP5MF','MRPS12']},
 1: {'label':'PN','title':'Proneural / Progenitor',
     'summary':'Neural-progenitor programme with high proliferation. 96% of this group match the Verhaak Proneural signature.',
     'therapeutic':'No subtype-specific approved therapy; proliferative programme is the dominant feature.',
     'markers':['NKAIN1','DCX','ATCAY','SCN3A','MARCKSL1']},
 2: {'label':'CL','title':'Classical / EGFR',
     'summary':'EGFR / RTK-MAPK axis. EGFR together with its own negative-feedback regulators SPRY1/2/4 and SPRED2.',
     'therapeutic':'EGFR is the canonical Classical-subtype axis; EGFR-directed strategies are the established research direction.',
     'markers':['EGFR','SPRY1','SPRY2','SPRY4','SPRED2','MEOX2']},
 3: {'label':'MES','title':'Mesenchymal / Immune',
     'summary':'Heavy myeloid and microglia-macrophage infiltration with complement activation. The purest subtype found (98% Verhaak-Mesenchymal).',
     'therapeutic':'Dense immune infiltration makes this the most immunotherapy-relevant group in the cohort.',
     'markers':['CD14','CD163','FCGR2A','FCGR2B','C1R','C1S','ALOX5']},
 4: {'label':'INT','title':'Intermediate / Mixed',
     'summary':'No dominant signature. Best interpreted as tumours sitting between states rather than a separate entity.',
     'therapeutic':'Reported honestly as transitional — no subtype-specific claim is made.',
     'markers':[]},
 5: {'label':'OLIGO','title':'Oligodendrocytic / Myelin',
     'summary':'Myelin-high with a strong neuronal component — partly OPC-like tumour biology, partly white-matter admixture.',
     'therapeutic':'Corresponds to the neural/oligodendrocyte axis; the historic "Neural" subtype was retired for this reason.',
     'markers':['MBP','PLP1','MAG','MOG','CNP','MYRF','UGT8']},
}

_A = None
_LOAD_ERROR: Optional[str] = None


def _load():
    global _A, _LOAD_ERROR
    if _A is not None or _LOAD_ERROR is not None:
        return _A
    try:
        import joblib
        if not os.path.exists(ARTIFACTS):
            _LOAD_ERROR = f'model_artifacts.joblib not found at {ARTIFACTS}'
            return None
        _A = joblib.load(ARTIFACTS)
        return _A
    except Exception as e:                                   # pragma: no cover
        _LOAD_ERROR = f'{type(e).__name__}: {e}'
        return None


def engine_status() -> dict:
    a = _load()
    if a is None:
        return {'available': False, 'error': _LOAD_ERROR, 'artifacts_path': ARTIFACTS}
    return {
        'available': True,
        'model_name': a['model_name'],
        'n_classes': int(a['K']),
        'cv_accuracy': float(a.get('cv_accuracy', 0)),
        'cv_balanced_accuracy': float(a.get('cv_balanced_accuracy', 0)),
        'roc_auc_ovr': float(a.get('roc_auc_ovr', 0)),
        'loo_accuracy': float(a.get('loo_accuracy', 0)) if 'loo_accuracy' in a else None,
        'protocol_threshold': float(a['protocol_threshold']),
        'n_genes_expected': int(len(a['lowexpr_gene_ids'])),
        'n_signature_genes': int(len(a['signature_gene_idx'])),
        'artifacts_path': ARTIFACTS,
    }


def parse_gdc_tsv(raw: bytes | str, filename: str = 'upload.tsv') -> pd.DataFrame:
    """Parse a raw GDC augmented_star_gene_counts.tsv. Raises ValueError if invalid."""
    buf = io.BytesIO(raw) if isinstance(raw, (bytes, bytearray)) else io.StringIO(raw)
    try:
        df = pd.read_csv(buf, sep='\t', skiprows=1, low_memory=False)
    except Exception as e:
        raise ValueError(f'Could not parse "{filename}" as a tab-separated GDC file: {e}')
    if 'gene_id' not in df.columns:
        raise ValueError(f'"{filename}" has no gene_id column — this does not look like a GDC '
                         f'augmented_star_gene_counts.tsv file.')
    if 'tpm_unstranded' not in df.columns:
        raise ValueError(f'"{filename}" has no tpm_unstranded column. Columns found: '
                         f'{", ".join(map(str, df.columns[:8]))}')
    df = df[df['gene_id'].astype(str).str.startswith('ENSG')].reset_index(drop=True)
    if len(df) < 1000:
        raise ValueError(f'"{filename}" contains only {len(df)} ENSG gene rows — expected ~60,000. '
                         f'The file appears truncated.')
    return df


def analyse(raw: bytes | str, filename: str = 'upload.tsv',
            on_stage: Optional[Callable[[str, str, dict], None]] = None) -> dict:
    """
    Run the REAL pipeline on one sample.

    on_stage(stage_id, status, payload) is called as each stage completes so the
    UI can show genuine progress. status is 'running' | 'done' | 'error'.
    """
    def emit(sid, status, payload=None):
        if on_stage:
            on_stage(sid, status, payload or {})

    a = _load()
    if a is None:
        raise RuntimeError(f'Inference engine unavailable — {_LOAD_ERROR}')

    t_all = time.time()
    stages: dict[str, dict] = {}

    def stage(sid):
        emit(sid, 'running')
        return time.time()

    # ── 1. ingestion ────────────────────────────────────────────────────────
    t = stage('ingest')
    df = parse_gdc_tsv(raw, filename)
    n_rows = len(df)
    stages['ingest'] = {'ms': int((time.time()-t)*1000),
                        'gene_rows_read': n_rows,
                        'file': filename,
                        'size_kb': round((len(raw) if isinstance(raw,(bytes,bytearray)) else len(raw))/1024, 1)}
    emit('ingest', 'done', stages['ingest'])

    # ── 2. QC / alignment to the training gene space ────────────────────────
    t = stage('qc')
    want = pd.Index(a['lowexpr_gene_ids'])
    s = pd.Series(df['tpm_unstranded'].values.astype(np.float64),
                  index=df['gene_id'].astype(str).values)
    s = s[~s.index.duplicated(keep='first')]
    matched = int(want.isin(s.index).sum())
    tpm = s.reindex(want).fillna(0.0).values
    coverage = matched / len(want)
    if coverage < 0.5:
        emit('qc', 'error', {'matched': matched, 'expected': len(want)})
        raise ValueError(f'Only {matched:,} of {len(want):,} expected genes matched '
                         f'({coverage*100:.1f}%). The file is not compatible with the trained model '
                         f'(different gene annotation?).')
    stages['qc'] = {'ms': int((time.time()-t)*1000), 'genes_matched': matched,
                    'genes_expected': int(len(want)), 'coverage_pct': round(coverage*100, 2),
                    'warning': 'partial gene coverage' if coverage < 0.95 else None}
    emit('qc', 'done', stages['qc'])

    # ── 3. protocol detection + batch correction ────────────────────────────
    t = stage('batch')
    frac = float(tpm[a['NONPOLYA_mask']].sum() / max(tpm.sum(), 1e-9))
    detected = int(frac > a['protocol_threshold'])
    proto = 'total-RNA / rRNA-depleted' if detected else 'poly(A)-selected'
    ambiguous = abs(frac - a['protocol_threshold']) < 0.03
    tk = tpm[a['KEEP_mask']]
    tk = tk / max(tk.sum(), 1e-9) * 1e6
    y = np.log2(tk + 1.0)
    z = (y - a['batch_means'][detected]) / a['global_sd']
    stages['batch'] = {'ms': int((time.time()-t)*1000), 'detected_protocol': proto,
                       'nonpolyA_fraction': round(frac, 5),
                       'threshold': round(float(a['protocol_threshold']), 5),
                       'genes_retained': int(a['KEEP_mask'].sum()),
                       'genes_removed': int((~a['KEEP_mask']).sum()),
                       'ambiguous': bool(ambiguous),
                       'warning': 'protocol fraction close to the decision threshold' if ambiguous else None}
    emit('batch', 'done', stages['batch'])

    # ── 4. feature selection ────────────────────────────────────────────────
    t = stage('features')
    sig = z[a['signature_gene_idx']]
    stages['features'] = {'ms': int((time.time()-t)*1000),
                          'n_signature_genes': int(len(a['signature_gene_idx'])),
                          'mean_abs_z': round(float(np.abs(sig).mean()), 4)}
    emit('features', 'done', stages['features'])

    # ── 5. embedding ────────────────────────────────────────────────────────
    t = stage('embed')
    emb = a['pca'].transform(sig.reshape(1, -1))
    stages['embed'] = {'ms': int((time.time()-t)*1000), 'n_components': int(emb.shape[1]),
                       'coordinates': [round(float(v), 4) for v in emb[0]]}
    emit('embed', 'done', stages['embed'])

    # ── 6. model ────────────────────────────────────────────────────────────
    t = stage('model')
    proba = a['model'].predict_proba(emb)[0]
    pred = int(np.argmax(proba))
    stages['model'] = {'ms': int((time.time()-t)*1000), 'algorithm': a['model_name'],
                       'predicted_class': pred}
    emit('model', 'done', stages['model'])

    # ── 7. confidence ───────────────────────────────────────────────────────
    t = stage('confidence')
    conf = float(proba[pred])
    band = 'confident' if conf >= CONF_HIGH else ('moderate' if conf >= CONF_LOW else 'undecided')
    order = np.argsort(proba)[::-1]
    runner = int(order[1])
    stages['confidence'] = {'ms': int((time.time()-t)*1000), 'confidence': round(conf, 4),
                            'band': band, 'margin': round(float(proba[pred]-proba[runner]), 4),
                            'runner_up': runner}
    emit('confidence', 'done', stages['confidence'])

    # ── 8. biological validation + EXPLAINABILITY ───────────────────────────
    t = stage('validate')
    info = SUBTYPE_INFO[pred]
    gnames = a['gene_names_filtered'][a['KEEP_mask']]
    gpos = {}
    for i, g in enumerate(gnames):
        gpos.setdefault(str(g), i)
    marker_readout = []
    for g in info['markers']:
        if g in gpos:
            marker_readout.append({'gene': g, 'z': round(float(z[gpos[g]]), 3),
                                   'elevated': bool(z[gpos[g]] > 0)})
    n_elev = sum(1 for m in marker_readout if m['elevated'])

    # WHY did the model choose this class?
    # The classifier is linear in PCA space, and PCA is linear in gene space, so
    # every gene's exact contribution to the decision can be recovered:
    #     contribution(gene) = sum_pc  coef[class][pc] * loading[pc][gene] * z[gene]
    # This is not an approximation or a saliency heuristic — it is the decision
    # function itself, decomposed.
    gi = a['signature_gene_idx']
    coef = a['model'].coef_[pred]                     # (n_pcs,)
    load = a['pca'].components_                       # (n_pcs, n_signature_genes)
    zsig = z[gi] - a['pca'].mean_                     # centred exactly as PCA does
    contrib = (coef @ load) * zsig                    # (n_signature_genes,)

    order = np.argsort(contrib)[::-1]
    top_for, top_against = [], []
    for j in order[:12]:
        top_for.append({'gene': str(gnames[gi[j]]), 'contribution': round(float(contrib[j]), 4),
                        'z': round(float(z[gi[j]]), 3)})
    for j in order[-8:][::-1]:
        top_against.append({'gene': str(gnames[gi[j]]), 'contribution': round(float(contrib[j]), 4),
                            'z': round(float(z[gi[j]]), 3)})
    total_pos = float(contrib[contrib > 0].sum()) or 1.0
    for m in top_for:
        m['share_pct'] = round(100 * m['contribution'] / total_pos, 2)

    # per-principal-component contribution
    pc_contrib = [{'pc': f'PC{i+1}', 'value': round(float(emb[0][i]), 3),
                   'coef': round(float(coef[i]), 4),
                   'contribution': round(float(coef[i] * emb[0][i]), 4)}
                  for i in range(len(coef))]

    stages['validate'] = {'ms': int((time.time()-t)*1000), 'markers_checked': len(marker_readout),
                          'markers_elevated': n_elev,
                          'agreement_pct': round(100*n_elev/len(marker_readout), 1) if marker_readout else None,
                          'genes_driving_decision': len(top_for)}
    emit('validate', 'done', stages['validate'])

    # ── 9. insight ──────────────────────────────────────────────────────────
    t = stage('insight')
    stages['insight'] = {'ms': int((time.time()-t)*1000)}
    emit('insight', 'done', stages['insight'])

    name = f"{info['label']}_{info['title'].replace(' / ', '_').replace(' ', '_')}"
    return {
        'ok': True,
        'file': filename,
        'predicted_class': pred,
        'subtype_label': info['label'],
        'subtype_title': info['title'],
        'subtype_name': name,
        'summary': info['summary'],
        'therapeutic_context': info['therapeutic'],
        'confidence': round(conf, 4),
        'confidence_band': band,
        'probabilities': [round(float(p), 6) for p in proba],
        'detected_protocol': proto,
        'nonpolyA_fraction': round(frac, 5),
        'protocol_ambiguous': bool(ambiguous),
        'genes_matched': matched,
        'genes_expected': int(len(want)),
        'embedding': [round(float(v), 4) for v in emb[0]],
        'marker_readout': marker_readout,
        'why': {
            'top_genes_for': top_for,
            'top_genes_against': top_against,
            'pc_contributions': pc_contrib,
            'method': ('The classifier is linear in principal-component space and PCA is linear in '
                       'gene space, so each gene\'s exact contribution to this decision is '
                       'coef[class] · loading · z(gene). These are the decision function itself, '
                       'decomposed — not an approximation.'),
        },
        'stages': stages,
        'total_ms': int((time.time()-t_all)*1000),
        'model_name': a['model_name'],
        'cv_accuracy': float(a.get('cv_accuracy', 0)),
        'roc_auc': float(a.get('roc_auc_ovr', 0)),
    }

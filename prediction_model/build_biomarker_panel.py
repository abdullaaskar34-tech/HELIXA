# -*- coding: utf-8 -*-
"""
HELIXA — build the biomarker panel the website reads.

WHAT CHANGED AND WHY
--------------------
The previous `biomarkers.json` was built from Stage 5's `final_targets.csv`
alone — 61 genes. But those 61 are not the 61 best candidates: Stage 4 was a
human reading literature for roughly ten genes per subtype (10 of 176 for PN,
10 of 11 for OLIGO), and Stage 5 drops any candidate without a verdict. So the
old panel showed whichever genes somebody happened to look up, and the other
298 statistically-qualified candidates were invisible.

This builder uses the three files that actually carry information:

  Stage 3  candidates_all.csv        359 genes — the statistics. THE BASE.
  Stage 4  literature_evidence.csv    62 genes — protein function, GBM evidence,
                                                 druggability, and SOURCES.
  Stage 5  final_targets.csv          61 genes — drug status, tier, final score,
                                                 wrong-direction / mismatch flags.

Stages 4, 5 and 6 are no longer run as pipeline steps; only these two tables are
consumed. Nothing is recomputed — every number is carried through from the CSV
that produced it, so the panel cannot drift from the engine.

Every gene now shows up. Genes with a literature check carry curated sources.
Genes without one are marked `literature_checked: false` and carry lookup links
instead of curated evidence, so the two are never confused.

Run:  python3 build_biomarker_panel.py --engine <path to biomerker_engine> \
                                       --out   <path to frontend/data/biomarkers.json>
"""
import os, json, ast, argparse
import pandas as pd
import numpy as np

SUB = {0: 'MTC', 1: 'PN', 2: 'CL', 3: 'MES', 4: 'INT', 5: 'OLIGO'}
FULL = {0: 'Mitochondrial / OXPHOS', 1: 'Proneural / Progenitor',
        2: 'Classical / EGFR', 3: 'Mesenchymal / Immune',
        4: 'Intermediate / Mixed', 5: 'Oligodendrocytic / Myelin'}

# ── plain-language names for every number the panel shows ──────────────────
# key: (label shown, one-line meaning, how to read it, format)
METRICS = {
    'target_strength': (
        'Overall target strength',
        'How good a target this gene is overall, combining how specific it is to '
        'this subtype with how much the tumour depends on it.',
        'Higher is better. This is the score the ranking uses.', 'pct'),
    'subtype_specificity': (
        'Specific to this subtype',
        'How much more active this gene is in this subtype than in the subtype '
        'where it is next most active.',
        'Higher means the gene points at this subtype and not at the others.', 'pct'),
    'tumour_dependence': (
        'Tumour cannot survive without it',
        'How badly glioblastoma cells need this gene to stay alive, combined with '
        'how much healthy tissue does not.',
        'Higher means knocking it out kills the tumour and spares normal cells.', 'pct'),
    'gbm_need': (
        'Glioblastoma cells need it',
        'Average dependency across 53 glioblastoma cell lines, from DepMap CRISPR '
        'knockout screens.',
        'Above 50% means a typical glioblastoma line dies without it.', 'pct'),
    'normal_need': (
        'Healthy cells also need it',
        'Average dependency across 1,118 cell lines from outside the brain.',
        'LOWER is better. High here means a drug would damage healthy tissue too.', 'pct'),
    'safety_gap': (
        'Safety gap',
        'How much more the tumour needs this gene than healthy tissue does.',
        'This is the room a drug has to work in. Bigger is safer.', 'signed'),
    'varies_between_tumours': (
        'Varies between tumours',
        'How differently glioblastoma cell lines respond to losing this gene.',
        'Higher means some tumours depend on it and others do not — the shape a '
        'subtype-specific vulnerability has.', 'raw'),
    'expression_lead': (
        'Expression lead over the next subtype',
        'How far this gene\'s activity in this subtype exceeds the next-highest '
        'subtype, in standard deviations.',
        'Above 0.15 was required to qualify.', 'z'),
    'effect_size': (
        'Effect size',
        "Cohen's d — how large the difference is relative to the spread within groups.",
        'Above 0.5 was required. Above 0.8 is a large effect.', 'raw'),
    'statistical_confidence': (
        'Statistical confidence',
        'False discovery rate after correcting for testing every gene.',
        'Smaller is stronger. Below 0.05 was required.', 'fdr'),
}

TIER_TEXT = {
    'TIER 1': ('Actionable', 'Passed both data gates, has published glioblastoma '
                             'support, and a drug against it already exists.'),
    'TIER 2': ('Credible target', 'Passed both data gates and has published support, '
                                  'but nothing has been built against it yet.'),
    'TIER 3': ('Hypothesis', 'Passed both data gates, but the literature is thin.'),
    'EXCLUDED': ('Wrong direction', 'The gene is a tumour suppressor, or its biology '
                                    'points the opposite way from what a drug would need.'),
    'UNCHECKED': ('Not yet reviewed', 'Passed both statistical gates, but nobody has '
                                      'read the literature on it yet. Absence of evidence '
                                      'here is not evidence of absence.'),
}


def clean(v):
    """
    JSON-safe value. Numbers MUST come out as numbers: pandas .itertuples() hands
    back plain Python floats, not np.float64, so an isinstance check against
    np.floating alone silently stringified every metric and the browser panel
    died on .toFixed(). Booleans are checked before ints because bool subclasses
    int in Python.
    """
    if v is None:
        return None
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, (int, np.integer)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        f = float(v)
        if np.isnan(f) or np.isinf(f):
            return None
        # Do NOT round small magnitudes. FDR values run to 1e-30; rounding to 8
        # decimals turns every one of them into 0.0 and the panel then reports
        # "statistical confidence 0.0e+0" for the most significant genes.
        return round(f, 8) if abs(f) >= 1e-6 else f
    s = str(v).strip()
    if s in ('', 'nan', 'None', 'NaN', '<NA>'):
        return None
    return s


def parse_sources(v):
    """literature_evidence stores a python list literal; final_targets a | string."""
    if not isinstance(v, str) or not v.strip():
        return []
    s = v.strip()
    if s.startswith('['):
        try:
            out = ast.literal_eval(s)
            return [str(x).strip() for x in out if str(x).strip()]
        except (ValueError, SyntaxError):
            pass
    return [p.strip() for p in s.split('|') if p.strip()]


def source_label(url):
    """A short human name for a URL, so links aren't raw addresses."""
    u = url.lower()
    for frag, name in [
        ('pubmed', 'PubMed'), ('ncbi.nlm.nih.gov/gene', 'NCBI Gene'),
        ('pmc.ncbi.nlm.nih.gov', 'PMC'), ('ncbi.nlm.nih.gov/pmc', 'PMC'),
        ('uniprot', 'UniProt'),
        ('pharos', 'Pharos'), ('proteinatlas', 'Human Protein Atlas'),
        ('drugbank', 'DrugBank'), ('dgidb', 'DGIdb'),
        ('clinicaltrials', 'ClinicalTrials.gov'), ('opentargets', 'Open Targets'),
        ('depmap', 'DepMap'), ('genecards', 'GeneCards'),
        ('ensembl', 'Ensembl'), ('cancer.sanger', 'COSMIC'),
        ('academic.oup.com/neuro-oncology', 'Neuro-Oncology'),
        ('academic.oup.com', 'Oxford Academic'), ('nature.com', 'Nature'),
        ('sciencedirect', 'ScienceDirect'), ('cell.com', 'Cell Press'),
        ('frontiersin', 'Frontiers'), ('aacrjournals', 'AACR'),
        ('wiley', 'Wiley'), ('springer', 'Springer'), ('biorxiv', 'bioRxiv'),
        ('mdpi', 'MDPI'), ('plos', 'PLOS'), ('jci.org', 'JCI'),
        ('oncotarget', 'Oncotarget'), ('nih.gov', 'NIH'),
    ]:
        if frag in u:
            return name
    try:
        host = url.split('//')[-1].split('/')[0].replace('www.', '')
        return host
    except Exception:
        return 'Source'


# Lookup links are identical in shape for every gene, so they are emitted once as
# templates and expanded in the browser. {gene} is the symbol, {ensembl} the
# un-versioned Ensembl id. These are SEARCHES, not curated evidence, and the
# frontend labels them as such so the two are never confused.
LOOKUP_TEMPLATES = [
    {'label': 'PubMed', 'what': 'Published papers mentioning this gene in glioblastoma',
     'url': 'https://pubmed.ncbi.nlm.nih.gov/?term={gene}+glioblastoma'},
    {'label': 'UniProt', 'what': 'What the protein is and what it does',
     'url': 'https://www.uniprot.org/uniprotkb?query={gene}+AND+organism_id:9606'},
    {'label': 'Human Protein Atlas', 'what': 'Where the protein is expressed in the body',
     'url': 'https://www.proteinatlas.org/search/{gene}'},
    {'label': 'Pharos', 'what': 'Whether any drug or tool compound is known',
     'url': 'https://pharos.nih.gov/targets?q={gene}'},
    {'label': 'DGIdb', 'what': 'Drug-gene interactions aggregated from ~30 databases',
     'url': 'https://dgidb.org/results?searchType=gene&searchTerms={gene}'},
    {'label': 'DrugBank', 'what': 'Known drugs against this target',
     'url': 'https://go.drugbank.com/unearth/q?searcher=bio_entities&query={gene}'},
    {'label': 'ClinicalTrials.gov', 'what': 'Trials naming this gene in glioblastoma',
     'url': 'https://clinicaltrials.gov/search?cond=Glioblastoma&term={gene}'},
    {'label': 'DepMap', 'what': 'The CRISPR dependency data behind the numbers above',
     'url': 'https://depmap.org/portal/gene/{gene}?tab=overview'},
    {'label': 'Ensembl', 'what': 'Gene record and genomic location', 'needs': 'ensembl',
     'url': 'https://www.ensembl.org/Homo_sapiens/Gene/Summary?g={ensembl}'},
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--engine', required=True, help='path to biomerker_engine/')
    ap.add_argument('--out', required=True, help='path to write biomarkers.json')
    ap.add_argument('--candidates', default=None)
    ap.add_argument('--literature', default=None)
    ap.add_argument('--targets', default=None)
    a = ap.parse_args()

    E = a.engine
    p_cand = a.candidates or f'{E}/stage_03_intersection_and_scoring/outputs/candidates_all.csv'
    p_lit = a.literature or f'{E}/stage_04_literature_evidence_collection/outputs/literature_evidence.csv'
    p_tgt = a.targets or f'{E}/stage_05_evidence_integration_and_excel_panels/outputs/final_targets.csv'
    for p in (p_cand, p_lit, p_tgt):
        if not os.path.exists(p):
            raise SystemExit(f'missing input: {p}')

    cand = pd.read_csv(p_cand)
    lit = pd.read_csv(p_lit)
    tgt = pd.read_csv(p_tgt)
    print(f'candidates  {cand.shape}   literature {lit.shape}   targets {tgt.shape}')

    lit_by = {str(r.gene_symbol): r for r in lit.itertuples()}
    tgt_by = {(int(r.cluster), str(r.gene)): r for r in tgt.itertuples()}

    # survival_score is min-max scaled within candidates_all, so it is already 0-1.
    by_class, summary = {}, {}
    n_lit_used = n_tgt_used = 0

    for k in range(6):
        c = cand[cand.cluster == k].sort_values('combined_score', ascending=False)
        genes = []
        for i, row in enumerate(c.itertuples(), start=1):
            g = str(row.gene)
            L = lit_by.get(g)
            T = tgt_by.get((k, g))
            if L is not None:
                n_lit_used += 1
            if T is not None:
                n_tgt_used += 1

            # tier: from Stage 5 where it exists, otherwise explicitly UNCHECKED
            if T is not None:
                tier_full = str(T.tier)
                tier_code = tier_full.split('·')[0].strip()
            else:
                tier_code, tier_full = 'UNCHECKED', 'UNCHECKED · not yet literature-reviewed'
            tier_name, tier_why = TIER_TEXT.get(tier_code, (tier_code, ''))

            curated = parse_sources(getattr(L, 'sources', None)) if L is not None else []
            sources = [{'label': source_label(u), 'kind': 'curated',
                        'what': 'Cited by the literature review for this gene', 'url': u}
                       for u in curated]

            genes.append({
                'gene': g,
                'gene_id': clean(row.gene_id),
                'rank': i,
                'literature_checked': L is not None,
                'tier': tier_code,
                'tier_name': tier_name,
                'tier_why': tier_why,
                'excluded': tier_code == 'EXCLUDED',

                # ── the numbers, under plain-language keys ──
                'target_strength': clean(row.combined_score),
                'subtype_specificity': clean(row.identity_score),
                'tumour_dependence': clean(row.survival_score),
                'gbm_need': clean(row.dep_mean_GBM),
                'normal_need': clean(row.dep_mean_nonCNS),
                'safety_gap': clean(row.therapeutic_window),
                'varies_between_tumours': clean(row.gbm_line_sd),
                'expression_lead': clean(row.specificity_margin),
                'effect_size': clean(row.cohens_d),
                'statistical_confidence': clean(row.fdr),
                'gbm_lines_dependent': clean(row.frac_GBM_lines_dependent),
                'all_lines_dependent': clean(row.frac_all_lines_dependent),

                # ── Stage 5, where it exists ──
                'final_score': clean(getattr(T, 'final_score', None)) if T is not None else None,
                'drug_status': clean(getattr(T, 'drug_status', None)) if T is not None else None,
                'drug_detail': clean(getattr(T, 'drug_detail', None)) if T is not None else None,
                'wrong_direction': clean(getattr(T, 'wrong_direction', None)) if T is not None else None,
                'subtype_mismatch': clean(getattr(T, 'subtype_mismatch', None)) if T is not None else None,

                # ── Stage 4, where it exists ──
                'verdict': clean(getattr(L, 'verdict', None)) if L is not None else None,
                'protein_function': clean(getattr(L, 'protein_function', None)) if L is not None else None,
                'gbm_evidence': clean(getattr(L, 'gbm_evidence', None)) if L is not None else None,
                'subtype_link': clean(getattr(L, 'subtype_link', None)) if L is not None else None,
                'druggable': clean(getattr(L, 'druggable', None)) if L is not None else None,
                'cancer_relevance': clean(getattr(L, 'cancer_relevance', None)) if L is not None else None,

                'sources': sources,
            })

        by_class[str(k)] = genes
        checked = [g for g in genes if g['literature_checked']]
        summary[str(k)] = {
            'subtype': SUB[k], 'subtype_full': FULL[k],
            'total_candidates': len(genes),
            'literature_checked': len(checked),
            'tier1_actionable': sum(1 for g in genes if g['tier'] == 'TIER 1'),
            'tier2_credible': sum(1 for g in genes if g['tier'] == 'TIER 2'),
            'tier3_hypothesis': sum(1 for g in genes if g['tier'] == 'TIER 3'),
            'excluded': sum(1 for g in genes if g['excluded']),
            'not_yet_reviewed': sum(1 for g in genes if g['tier'] == 'UNCHECKED'),
            'with_drug': sum(1 for g in genes if g.get('drug_status')
                             and g['drug_status'] not in ('NONE KNOWN',)),
        }
        s = summary[str(k)]
        print(f"  {SUB[k]:<6s} {s['total_candidates']:4d} candidates · "
              f"{s['literature_checked']:2d} reviewed · T1 {s['tier1_actionable']} "
              f"T2 {s['tier2_credible']} T3 {s['tier3_hypothesis']} "
              f"excl {s['excluded']} · {s['not_yet_reviewed']} not yet reviewed")

    out = {
        'version': '2.0.0',
        'generated_from': [
            'stage_03_intersection_and_scoring/outputs/candidates_all.csv — the statistics (359 candidates)',
            'stage_04_literature_evidence_collection/outputs/literature_evidence.csv — function, evidence, sources (62 genes)',
            'stage_05_evidence_integration_and_excel_panels/outputs/final_targets.csv — drug status and tier (61 genes)',
        ],
        'methodology':
            'For each subtype, a gene qualifies only if it does BOTH of these. (1) It marks '
            'the subtype in 328 real patients: Welch t-test at FDR<0.05, Cohen\'s d>0.5, and '
            'an expression lead of more than 0.15 standard deviations over the next-highest '
            'subtype. (2) Glioblastoma cell lines cannot survive without it while cells from '
            'outside the brain can: DepMap CRISPR dependency tier A. Genes that pass both are '
            'ranked by the geometric mean of subtype specificity and tumour dependence, so a '
            'gene has to do well at both — a superb marker with no dependency, or a strong '
            'dependency that every subtype shares, both sink.',
        'reading_the_panel':
            'Every candidate that passed the statistics is listed. Where a human has read the '
            'literature on a gene, its protein function, glioblastoma evidence and drug status '
            'are shown with the sources they came from. Where nobody has read it yet, the gene '
            'is marked "not yet reviewed" and only search links are offered. Absence of '
            'evidence on those genes means nobody has looked, not that nothing was found.',
        'metrics': {k: {'label': v[0], 'meaning': v[1], 'how_to_read': v[2], 'format': v[3]}
                    for k, v in METRICS.items()},
        'lookup_templates': LOOKUP_TEMPLATES,
        'tiers': {k: {'name': v[0], 'meaning': v[1]} for k, v in TIER_TEXT.items()},
        'disclaimer':
            'These are computational candidates from an unpublished research pipeline, not '
            'treatments. None of them has been tested in a laboratory by this project. Nothing '
            'here is a clinical recommendation.',
        'summary_by_class': summary,
        'by_class': by_class,
    }

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, 'w') as f:
        json.dump(out, f, separators=(',', ':'))
    total = sum(len(v) for v in by_class.values())
    print(f'\n{total} genes · {n_lit_used} with literature · {n_tgt_used} with a Stage-5 record')
    print(f'wrote {a.out}  ({os.path.getsize(a.out)/1024:.0f} KB)')


if __name__ == '__main__':
    main()

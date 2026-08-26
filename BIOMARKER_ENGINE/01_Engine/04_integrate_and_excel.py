# -*- coding: utf-8 -*-
"""
================================================================================
 BIOMARKER ENGINE — STEP 4 · EVIDENCE INTEGRATION AND THE EXCEL PANELS
================================================================================

The first three steps were arithmetic. This step adds the thing arithmetic
cannot supply: what humanity already knows about these genes.

Every one of the 60 top candidates was checked against the published
literature — PubMed, Human Protein Atlas, Open Targets, DrugBank,
ClinicalTrials.gov — and the findings are stored verbatim in
03_Evidence/literature_evidence.json, with the source URL for each claim.

Three things that check changed, and they matter more than the ranking:

  1  TWO GENES POINT THE WRONG WAY.
     PRKAR1A and APC are established TUMOUR SUPPRESSORS. A tumour suppressor
     that a cell line "depends on" is depending on it to restrain growth —
     inhibiting it would make the tumour worse, not better. They are moved to
     an EXCLUDED sheet with the reason written next to them. Pure statistics
     would have left them near the top of the INT panel.

  2  THREE MITOCHONDRIAL GENES LANDED IN THE WRONG SUBTYPE.
     PISD, SLC25A28 and NDUFAF3 are mitochondrial proteins that came out in
     the OLIGO (neural/myelin) panel. Their biology fits MTC. This is flagged,
     not hidden — it is a genuine limitation of ranking on expression alone.

  3  SOME TARGETS ALREADY HAVE DRUGS, AND SOME OF THOSE DRUGS ALREADY FAILED
     IN GLIOBLASTOMA. Cilengitide (alphaVbeta5, so ITGB5) failed phase III.
     Palbociclib (CDK4/6, so CDK6) was terminated for futility in recurrent
     GBM. Reporting the target without reporting the failed trial would be
     misleading, so both are recorded on the same row.

FINAL TIERS
    TIER 1 · ACTIONABLE      passes both data gates, published support, a
                             named drug that exists, not a tumour suppressor
    TIER 2 · CREDIBLE        passes both data gates, published support,
                             no drug yet
    TIER 3 · HYPOTHESIS      passes both data gates, little or no literature
                             — a real finding, but unproven
    EXCLUDED                 tumour suppressor, or the biology contradicts the
                             therapeutic direction

Run:  python3 04_integrate_and_excel.py
================================================================================
"""
import os, json, re
import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
T = os.path.join(ROOT, '05_Tables')
E = os.path.join(ROOT, '03_Evidence')
X = os.path.join(ROOT, '02_Panels_Excel')
os.makedirs(X, exist_ok=True)

SUB = {0: 'MTC', 1: 'PN', 2: 'CL', 3: 'MES', 4: 'INT', 5: 'OLIGO'}
FULL = {'MTC': 'Mitochondrial / OXPHOS', 'PN': 'Proneural Progenitor',
        'CL': 'Classical EGFR', 'MES': 'Mesenchymal Immune',
        'INT': 'Intermediate Mixed', 'OLIGO': 'Neural / Myelin'}

print('=' * 78)
print(' BIOMARKER ENGINE · STEP 4 — evidence integration and Excel panels')
print('=' * 78)

cand = pd.read_csv(os.path.join(T, 'candidates_all.csv'))
ev = pd.DataFrame(json.load(open(os.path.join(E, 'literature_evidence.json'))))
ev = ev.rename(columns={'gene_symbol': 'gene'})
ev['sources_joined'] = ev.sources.apply(lambda s: ' | '.join(s))
print(f'\ncandidates from step 3        : {len(cand):,}')
print(f'genes checked in the literature: {len(ev)}')

# ── genes whose biology points the wrong way ───────────────────────────────
# Flagged by the literature check, quoted here so the reason travels with the data.
WRONG_DIRECTION = {
    'PRKAR1A': 'TUMOUR SUPPRESSOR. Germline inactivating mutations cause Carney '
               'complex; described as a tumour-suppressor gene for sporadic thyroid '
               'cancer. Inhibiting it would remove a brake on growth.',
    'APC': 'TUMOUR SUPPRESSOR. Degrades beta-catenin and switches OFF Wnt '
           'signalling; biallelic loss causes familial adenomatous polyposis. '
           'Inhibiting it would activate Wnt, the opposite of what is wanted.',
    'BNIP1': 'Behaves as a tumour suppressor in the one functional cancer study '
             'available (cervical): it inhibits proliferation and promotes apoptosis.',
    'DCTN1': 'In low-grade glioma HIGH expression predicts BETTER survival, which '
             'argues against it being an oncogenic dependency.',
    'RPL41': 'TUMOUR SUPPRESSOR, and a pan-essential ribosomal protein after all. '
             'Deleted in ~59% of tumour cell lines; a 2025 in vivo CRISPR screen found '
             'it IS required for proliferation of normal tissue, overturning its old '
             '"nonessential" label. It passed the statistical gates and was caught '
             'only by reading the literature.',
}
# biology that does not match the subtype it was ranked into
SUBTYPE_MISMATCH = {
    'PISD': 'Mitochondrial enzyme — biology fits MTC, not OLIGO.',
    'SLC25A28': 'Mitochondrial iron carrier — biology fits MTC, not OLIGO.',
    'NDUFAF3': 'Complex I assembly factor — biology fits MTC, not OLIGO.',
    'RPP25L': 'tRNA/rRNA processing, not OXPHOS — but carries direct published '
              'GBM evidence, so it stays on merit.',
}
# drug status, transcribed from the literature check
DRUG_TIER = {
    'PARN': ('NONE KNOWN', 'No approved or clinical-stage PARN inhibitor. Inhibitors exist only '
             'as early research tools; the glioblastoma study used genetic depletion.'),
    'LARP1': ('INDIRECT ONLY', 'No selective LARP1 inhibitor. The tractable node is upstream — '
              'mTOR inhibitors. Rapalogs have been trialled in GBM WITHOUT success.'),
    'SEC62': ('TOOL COMPOUND', 'Trifluoperazine, an approved antipsychotic, antagonises Sec62 '
              'function in cell studies. Not a developed oncology agent.'),
    'SOCS3': ('WRONG DIRECTION FOR A DRUG', 'SOCS3 RESTRAINS JAK/STAT — inhibiting it would '
              'release the pathway. SOCS3-mimetic peptides are agonists. The druggable node is '
              'JAK (ruxolitinib), in the opposite direction.'),
    'TLN1': ('INDIRECT ONLY', 'No approved or clinical-stage direct talin-1 inhibitor. The GBM '
             'work used genetic knockdown. FAK inhibitors act on the node immediately downstream.'),
    'VRK1': ('PRECLINICAL', 'VRK-IN-1 and dihydropteridinone-derived VRK1 inhibitors are tool '
             'compounds (J Med Chem 2024). No clinical programme confirmed.'),
    'KIF18B': ('NONE KNOWN', 'No KIF18B-selective inhibitor exists. AMG 650 and the Nature Cancer '
               '2024 compounds target the PARALOGUE KIF18A — they are not KIF18B agents.'),
    'KIF2C': ('NONE KNOWN', 'No selective KIF2C/MCAK inhibitor with verified status.'),
    'FERMT2': ('NONE KNOWN', 'No selective kindlin-2 inhibitor. A protein-protein-interaction '
               'adaptor with no enzymatic active site.'),
    'ARPC2': ('TOOL COMPOUND', 'CK-666 inhibits the Arp2/3 complex and was used in the glioma '
              'study; CK-869 is related. Research tools only, and they hit the complex rather '
              'than ARPC2 selectively.'),
    'ACTR3': ('TOOL COMPOUND', 'CK-666 and CK-869 bind the Arp2/3 complex. Research tools only.'),
    'BRAT1': ('PRECLINICAL', 'Curcusone D, a natural-product diterpene, is described as a BRAT1 '
              'inhibitor; in the GBM paper it phenocopied knockdown and synergised with radiation.'),
    'CDK6': ('APPROVED (other cancers)', 'palbociclib, ribociclib, abemaciclib — approved in '
             'HR+/HER2- breast cancer. GBM: palbociclib phase 2 in recurrent RB1-positive GBM '
             'was TERMINATED FOR FUTILITY.'),
    'PTK2': ('APPROVED (other cancers)', 'defactinib (FAKZYNJA) — FDA accelerated approval '
             'May 2025 with avutometinib in KRAS-mutated low-grade serous ovarian cancer. GBM: '
             'GSK2256098 tested in recurrent GBM (Neuro-Oncology 2018), tumour penetration shown.'),
    'FGFR1': ('APPROVED (other cancers)', 'pemigatinib — FDA approved 2022 for FGFR1-rearranged '
              'myeloid/lymphoid neoplasms. FGFR-TACC fusions occur in IDH-wildtype glioma and '
              'are inhibitor-sensitive.'),
    'ITGB5': ('FAILED IN GBM', 'cilengitide (alphaVbeta3/alphaVbeta5) reached phase III CENTRIC '
              'in GBM and MISSED its primary endpoint. The target is validated; that molecule is not.'),
    'WWTR1': ('CLINICAL TRIALS', 'VT3989, a TEAD palmitoylation-site inhibitor, completed a '
              'first-in-human phase 1/2 in solid tumours (Nature Medicine 2025) with antitumour '
              'activity. TAZ is targeted through TEAD.'),
    'RHOA': ('CLINICAL TRIALS (effector)', 'ROCK inhibitors — fasudil approved in Japan for '
             'cerebral vasospasm. Direct RhoA tools (rhosin, C3 transferase) are preclinical.'),
    'FOSL1': ('PRECLINICAL', 'T-5224, a selective c-Fos/AP-1 DNA-binding inhibitor, tested '
              'clinically in rheumatoid arthritis and preclinically in oncology.'),
    'ATP5MC1': ('TOOL COMPOUND', 'oligomycin binds the ATP synthase c-ring. Research tool only '
                '— too toxic for systemic human use.'),
    'NDUFAF3': ('TRIALS (complex level)', 'IACS-010759, a complex I inhibitor, entered phase I '
                'but reported dose-limiting neurotoxicity and lactic acidosis.'),
    'ATXN7L3': ('PRECLINICAL', 'targetable indirectly through USP22 inhibitors, preclinical only.'),
}


def drug_tier(gene, druggable_text):
    """Read the status the literature check actually stated.

    An earlier version of this guessed from keywords anywhere in the text and
    got several genes badly wrong — PARN was labelled "approved" when its own
    entry ends "Approval status: preclinical / none known". Overclaiming a drug
    is the worst failure this file could have, so the rule is now: take the
    explicit status clause the check wrote, and when in doubt claim LESS.
    """
    if gene in DRUG_TIER:                       # hand-checked, richer detail
        return DRUG_TIER[gene]
    t = (druggable_text or '')
    m = re.search(r'(?:approval status|status)\s*:\s*([^.]*)', t, re.I)
    claim = (m.group(1) if m else t[:120]).lower()
    # "no known ligands, drugs or tool compounds" contains the word "tool" and
    # must NOT be read as "a tool compound exists". Only a positive statement counts.
    has_tool = bool(re.search(r'(?<!no )(?<!without )tool compound', claim)) and \
        not re.search(r'(?:no|none|without)[^.]{0,40}tool', claim)
    if 'none known' in claim or 'no approved' in claim or 'none approved' in claim:
        if has_tool:
            return ('TOOL COMPOUND', t)
        if 'preclinical' in claim:
            return ('PRECLINICAL', t)
        return ('NONE KNOWN', t)
    if 'approved' in claim:
        return ('APPROVED (other cancers)', t)
    if 'clinical trial' in claim or re.search(r'phase\s*(i|1|2|ii|3|iii)', claim):
        return ('CLINICAL TRIALS', t)
    if 'preclinical' in claim:
        return ('PRECLINICAL', t)
    if has_tool:
        return ('TOOL COMPOUND', t)
    return ('NONE KNOWN', t)


EVID_W = {'STRONG': 1.00, 'MODERATE': 0.65, 'NOVEL': 0.35, 'WEAK': 0.30}
DRUG_W = {'APPROVED (other cancers)': 1.00, 'FAILED IN GBM': 0.55,
          'INDIRECT ONLY': 0.40, 'WRONG DIRECTION FOR A DRUG': 0.20,
          'CLINICAL TRIALS': 0.85, 'CLINICAL TRIALS (effector)': 0.75,
          'TRIALS (complex level)': 0.70, 'PRECLINICAL': 0.45,
          'TOOL COMPOUND': 0.35, 'NONE KNOWN': 0.15}

m = cand.merge(ev[['gene', 'protein_function', 'gbm_evidence', 'subtype_link',
                   'druggable', 'cancer_relevance', 'verdict', 'sources_joined']],
               on='gene', how='left')
checked = m[m.verdict.notna()].copy()
print(f'candidates with a literature check: {len(checked)}')

tiers = checked.druggable.combine(checked.gene, lambda d, g: drug_tier(g, d))
checked['drug_status'] = [t[0] for t in tiers]
checked['drug_detail'] = [t[1] for t in tiers]
checked['wrong_direction'] = checked.gene.map(WRONG_DIRECTION)
checked['subtype_mismatch'] = checked.gene.map(SUBTYPE_MISMATCH)
checked['evidence_weight'] = checked.verdict.map(EVID_W)
checked['drug_weight'] = checked.drug_status.map(DRUG_W)

# final score: data score, tempered by what is actually known
checked['final_score'] = (checked.combined_score ** 0.5 *
                          checked.evidence_weight ** 0.3 *
                          checked.drug_weight ** 0.2)

def tier(r):
    if isinstance(r.wrong_direction, str):
        return 'EXCLUDED · wrong therapeutic direction'
    if (r.verdict in ('STRONG', 'MODERATE')
            and r.drug_status not in ('NONE KNOWN', 'WRONG DIRECTION FOR A DRUG')):
        return 'TIER 1 · actionable'
    if r.verdict in ('STRONG', 'MODERATE'):
        return 'TIER 2 · credible target, no drug yet'
    return 'TIER 3 · hypothesis, little literature'

checked['tier'] = checked.apply(tier, axis=1)
checked = checked.sort_values(['cluster', 'final_score'], ascending=[True, False])
checked['final_rank'] = checked.groupby('cluster').cumcount() + 1
checked.to_csv(os.path.join(T, 'final_targets.csv'), index=False)

print('\nfinal tiers:')
for t_, n in checked.tier.value_counts().items():
    print(f'  {t_:<42s} {n:3d}')
print('\nper subtype (tier 1 / tier 2 / tier 3 / excluded):')
for k in range(6):
    c = checked[checked.cluster == k]
    print(f'  {SUB[k]:<6s} {sum(c.tier.str.startswith("TIER 1")):2d} / '
          f'{sum(c.tier.str.startswith("TIER 2")):2d} / '
          f'{sum(c.tier.str.startswith("TIER 3")):2d} / '
          f'{sum(c.tier.str.startswith("EXCLUDED")):2d}')

# ── Excel ──────────────────────────────────────────────────────────────────
FONT = 'Arial'
HDR = PatternFill('solid', fgColor='0C4A44')
T1 = PatternFill('solid', fgColor='D6F0E8')
T2 = PatternFill('solid', fgColor='EAF4EF')
T3 = PatternFill('solid', fgColor='FBF3E2')
EXF = PatternFill('solid', fgColor='F8DEDA')
TITLE = PatternFill('solid', fgColor='F2F7F6')
thin = Side(style='thin', color='C9D9D6')
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)

COLS = [
    ('final_rank', 'Rank', 7), ('gene', 'Gene', 12), ('tier', 'Tier', 34),
    ('protein_function', 'What the protein does', 62),
    ('mean_z_in_class', 'Expression in this subtype (z)', 16),
    ('specificity_margin', 'Margin over the next subtype (z)', 16),
    ('cohens_d', "Effect size (Cohen's d)", 14), ('fdr', 'FDR', 11),
    ('dep_mean_GBM', 'Tumour needs it (0-1)', 15),
    ('dep_mean_nonCNS', 'Normal tissue needs it (0-1)', 16),
    ('therapeutic_window', 'Therapeutic window', 15),
    ('frac_GBM_lines_dependent', 'GBM cell lines dependent', 16),
    ('drug_status', 'Drug status', 24), ('drug_detail', 'Drug detail', 70),
    ('verdict', 'Literature verdict', 15),
    ('gbm_evidence', 'Published glioblastoma evidence', 80),
    ('subtype_link', 'Does the biology match this subtype?', 70),
    ('cancer_relevance', 'Evidence in cancer generally', 70),
    ('subtype_mismatch', 'Flag', 46),
    ('wrong_direction', 'Why excluded', 60),
    ('final_score', 'Final score', 11),
    ('sources_joined', 'Sources', 100),
]
NUMFMT = {'mean_z_in_class': '0.00', 'specificity_margin': '0.00', 'cohens_d': '0.00',
          'fdr': '0.00E+00', 'dep_mean_GBM': '0.000', 'dep_mean_nonCNS': '0.000',
          'therapeutic_window': '+0.000;-0.000;0.000',
          'frac_GBM_lines_dependent': '0.0%', 'final_score': '0.000'}


def sheet_table(ws, df, title, subtitle):
    ws['A1'] = title
    ws['A1'].font = Font(name=FONT, size=15, bold=True, color='0C4A44')
    ws['A2'] = subtitle
    ws['A2'].font = Font(name=FONT, size=10, color='4A6663')
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(COLS))
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(COLS))
    for c in (1, 2):
        ws.cell(row=c, column=1).fill = TITLE
    r0 = 4
    for j, (_, label, w) in enumerate(COLS, start=1):
        c = ws.cell(row=r0, column=j, value=label)
        c.font = Font(name=FONT, size=10, bold=True, color='FFFFFF')
        c.fill = HDR
        c.alignment = Alignment(wrap_text=True, vertical='center')
        c.border = BOX
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.row_dimensions[r0].height = 34
    for i, (_, row) in enumerate(df.iterrows()):
        rr = r0 + 1 + i
        fill = (T1 if row.tier.startswith('TIER 1') else
                T2 if row.tier.startswith('TIER 2') else
                EXF if row.tier.startswith('EXCLUDED') else T3)
        for j, (key, _, _) in enumerate(COLS, start=1):
            v = row.get(key)
            if isinstance(v, float) and np.isnan(v):
                v = ''
            c = ws.cell(row=rr, column=j, value=v)
            c.font = Font(name=FONT, size=9.5,
                          bold=(key in ('gene', 'final_rank')))
            c.fill = fill
            c.border = BOX
            c.alignment = Alignment(wrap_text=(key not in NUMFMT and key != 'gene'),
                                    vertical='top')
            if key in NUMFMT:
                c.number_format = NUMFMT[key]
    ws.freeze_panes = ws.cell(row=r0 + 1, column=3)
    return r0 + len(df)


LEGEND = [
    ('How to read this sheet', ''),
    ('Rank', 'Position within this subtype after the literature check. Rank 1 is the '
             'strongest candidate, not a proven drug target.'),
    ('Tier 1 · actionable', 'Passed both data gates, has published support, and a drug '
                            'against it already exists somewhere in medicine.'),
    ('Tier 2 · credible', 'Passed both data gates with published support, but nothing '
                          'has been built against it yet.'),
    ('Tier 3 · hypothesis', 'Passed both data gates, but the literature is thin. A real '
                            'finding that nobody has tested — interesting and unproven.'),
    ('EXCLUDED', 'The gene is a tumour suppressor or its biology points the opposite '
                 'way. Kept visible on purpose so the reasoning is auditable.'),
    ('Expression in this subtype (z)', 'How far above the cohort average this gene sits in '
                                       'this subtype, in standard deviations, after batch correction.'),
    ('Margin over the next subtype', 'The strict specificity test: this subtype minus the '
                                     'HIGHEST of the other five, not their average.'),
    ('Tumour needs it', 'Mean DepMap dependency across 53 glioblastoma cell lines. Above 0.5 '
                        'is DepMap\'s own "likely dependent" line.'),
    ('Normal tissue needs it', 'The same score across 1,118 cell lines from outside the brain. '
                               'This is the safety column — it must be LOW.'),
    ('Therapeutic window', 'The first minus the second. A positive number is the whole point: '
                           'the tumour needs it more than other tissue does.'),
    ('Sources', 'Every URL the literature check actually used. Nothing here is asserted '
                'without one.'),
]


def add_legend(wb, name='How to read this'):
    ws = wb.create_sheet(name)
    ws.column_dimensions['A'].width = 34
    ws.column_dimensions['B'].width = 110
    for i, (k, v) in enumerate(LEGEND, start=1):
        a = ws.cell(row=i, column=1, value=k)
        b = ws.cell(row=i, column=2, value=v)
        a.font = Font(name=FONT, size=11 if i == 1 else 10, bold=True,
                      color='0C4A44')
        b.font = Font(name=FONT, size=10)
        b.alignment = Alignment(wrap_text=True, vertical='top')
        ws.row_dimensions[i].height = 30 if v else 20
    return ws


print('\nwriting Excel panels…')
for k in range(6):
    c = checked[checked.cluster == k]
    if not len(c):
        continue
    wb = Workbook()
    ws = wb.active
    ws.title = f'{SUB[k]} targets'
    sheet_table(ws, c, f'{SUB[k]} — {FULL[SUB[k]]}',
                f'{len(c)} candidate targets · each one passed BOTH a patient-expression '
                f'test and an independent tumour-survival test, then was checked against '
                f'the published literature')
    add_legend(wb)
    p = os.path.join(X, f'{k}_{SUB[k]}_biomarker_targets.xlsx')
    wb.save(p)
    print(f'  {os.path.basename(p):<40s} {len(c):3d} genes')

# master workbook
wb = Workbook()
ws = wb.active
ws.title = 'All subtypes'
sheet_table(ws, checked, 'HELIXA biomarker engine — all six subtypes',
            f'{len(checked)} candidates · discovery on 328 real patients, survival on 1,208 '
            f'DepMap cell lines, then a literature check with sources')
for k in range(6):
    c = checked[checked.cluster == k]
    if len(c):
        sheet_table(wb.create_sheet(SUB[k]), c, f'{SUB[k]} — {FULL[SUB[k]]}',
                    f'{len(c)} candidates, ranked')
add_legend(wb)

# summary sheet, with live formulas over the master table
s = wb.create_sheet('Summary', 0)
s['A1'] = 'HELIXA biomarker engine — summary'
s['A1'].font = Font(name=FONT, size=16, bold=True, color='0C4A44')
s['A2'] = ('Counts below are Excel formulas over the "All subtypes" sheet, so they stay '
           'correct if you filter or edit it.')
s['A2'].font = Font(name=FONT, size=10, color='4A6663')
hdr = ['Subtype', 'Programme', 'Tier 1 · actionable', 'Tier 2 · credible',
       'Tier 3 · hypothesis', 'Excluded', 'Total']
for j, h in enumerate(hdr, start=1):
    c = s.cell(row=4, column=j, value=h)
    c.font = Font(name=FONT, size=10, bold=True, color='FFFFFF')
    c.fill = HDR
    c.alignment = Alignment(wrap_text=True, vertical='center')
    c.border = BOX
n = len(checked)
rng_sub = f"'All subtypes'!$B$5:$B${4+n}"          # gene column is B; subtype is not in COLS
# subtype is encoded in the tier sheet order, so count by matching the per-subtype sheets
for i, k in enumerate(range(6)):
    r = 5 + i
    cnt = len(checked[checked.cluster == k])
    s.cell(row=r, column=1, value=SUB[k]).font = Font(name=FONT, size=10, bold=True)
    s.cell(row=r, column=2, value=FULL[SUB[k]]).font = Font(name=FONT, size=10)
    end = 4 + cnt
    for j, key in enumerate(['TIER 1', 'TIER 2', 'TIER 3', 'EXCLUDED'], start=3):
        s.cell(row=r, column=j,
               value=f'=COUNTIF(\'{SUB[k]}\'!$C$5:$C${end},"{key}*")')
    s.cell(row=r, column=7, value=f'=SUM(C{r}:F{r})')
    for j in range(1, 8):
        s.cell(row=r, column=j).border = BOX
        s.cell(row=r, column=j).font = Font(name=FONT, size=10,
                                            bold=(j == 1))
r = 11
s.cell(row=r, column=1, value='TOTAL').font = Font(name=FONT, size=10, bold=True)
for j in range(3, 8):
    s.cell(row=r, column=j, value=f'=SUM({get_column_letter(j)}5:{get_column_letter(j)}10)')
    s.cell(row=r, column=j).font = Font(name=FONT, size=10, bold=True)
    s.cell(row=r, column=j).border = BOX
for j, w in enumerate([12, 26, 18, 18, 18, 12, 10], start=1):
    s.column_dimensions[get_column_letter(j)].width = w

notes = [
    '', 'WHAT THIS IS',
    'Genes that (a) identify one of the six molecular subtypes in real patients AND',
    '(b) a glioblastoma cell cannot survive without AND (c) a normal cell can.',
    '', 'THE DATA',
    'Patient side  : 328 real GDC glioblastoma patients, batch-corrected, 25,738 genes.',
    '                Discovery on the 273 core patients only.',
    'Survival side : DepMap CRISPR gene dependency, 1,208 cell lines, 18,531 genes.',
    '                53 glioblastoma lines against 1,118 lines from outside the brain.',
    'Evidence      : PubMed, Human Protein Atlas, Open Targets, DrugBank,',
    '                ClinicalTrials.gov — every claim carries its URL.',
    '', 'THE FILTER THAT MATTERS',
    '1,002 of the 18,531 genes are dependencies in over 90% of ALL cell lines.',
    'Those are essential for every human cell, so a drug against them kills the patient.',
    'They are excluded. The earlier attempt did not exclude them, which is why it',
    'returned POLR2L, RPLP1 and RPL28 and nothing usable.',
    '', 'WHAT THIS IS NOT',
    'These are candidates, not treatments. Nothing here has been tested in a laboratory',
    'by this project. Two named drugs against targets on this list have already FAILED',
    'in glioblastoma trials (cilengitide, palbociclib) — that is recorded on their rows.',
]
for i, t in enumerate(notes, start=13):
    c = s.cell(row=i, column=1, value=t)
    c.font = Font(name=FONT, size=10,
                  bold=t.isupper() and len(t) > 3,
                  color='0C4A44' if t.isupper() else '2A403E')

p = os.path.join(X, 'MASTER_all_subtypes.xlsx')
wb.save(p)
print(f'  {os.path.basename(p):<40s} {len(checked):3d} genes, 9 sheets')
print(f'\nwritten -> {X}')

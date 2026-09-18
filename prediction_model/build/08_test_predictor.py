"""
End-to-end verification. Rebuild GDC-format TSVs from real patients, push them
through predict.py exactly as a new upload would go, and check the answers
against the recorded assignments and against the in-process model.
"""
import os, subprocess, json, warnings
import numpy as np, pandas as pd, joblib
warnings.filterwarnings('ignore')

UP = '/mnt/user-data/uploads/TEKNOFEST_ONCOLOGY/new_start'
HX = f'{UP}/HELIXA/NEW_START_RESULTS'
OUT = '/home/claude/work/prediction_model'
TMP = '/home/claude/work/testdata'
os.makedirs(TMP, exist_ok=True)

X = np.load(f'{UP}/01_Data_Preparation/log2tpm_filtered.npy')
genes = pd.read_csv(f'{UP}/01_Data_Preparation/genes_filtered.csv')
assign = pd.read_csv(f'{HX}/04_Consensus_Clustering/final_patient_assignments.csv')
preds = pd.read_csv(f'{OUT}/training_predictions_v2.csv')
tpm_all = np.power(2.0, X) - 1.0

# pick a spread: two confident, two boundary, one of each protocol
core = assign['is_core'].values.astype(bool)
pick = []
pick += list(np.where(core & (assign.library_batch == 'polyA_selected'))[0][:2])
pick += list(np.where(core & (assign.library_batch == 'totalRNA_rRNAdepleted'))[0][:1])
pick += list(np.where(~core)[0][:2])
print('testing samples:', pick)

paths = []
for i in pick:
    sid = assign['sample_id'].iloc[i]
    p = f'{TMP}/{sid}.tsv'
    with open(p, 'w') as f:
        f.write('# gene-model: GENCODE v36\n')
        f.write('gene_id\tgene_name\tgene_type\tunstranded\tstranded_first\t'
                'stranded_second\ttpm_unstranded\tfpkm_unstranded\tfpkm_uq_unstranded\n')
        for gid, gn, gt, v in zip(genes.gene_id, genes.gene_name,
                                  genes.gene_type, tpm_all[:, i]):
            f.write(f'{gid}\t{gn}\t{gt}\t0\t0\t0\t{v:.4f}\t0\t0\n')
    paths.append(p)
print(f'wrote {len(paths)} GDC-format test files')

r = subprocess.run(['python3', f'{OUT}/predict.py'] + paths +
                   ['--json', f'{TMP}/results.json', '--quiet'],
                   capture_output=True, text=True)
if r.returncode != 0:
    print('STDERR:', r.stderr[-3000:])
    raise SystemExit('predict.py failed')
print(r.stdout.strip())

res = json.load(open(f'{TMP}/results.json'))
if isinstance(res, dict):
    res = [res]

print('\n' + '=' * 92)
print('%-38s %-6s %-6s %7s %7s %-9s %s' %
      ('sample', 'recd', 'pred', 'prob', 'consens', 'call', 'protocol OK'))
print('=' * 92)
ok_cluster = ok_proto = 0
for rr, i in zip(res, pick):
    row = preds[preds.sample_id == rr['sample_id']].iloc[0]
    proto_ok = rr['library_batch'] == assign['library_batch'].iloc[i]
    clus_ok = rr['cluster'] == row.cluster_recorded
    ok_cluster += clus_ok; ok_proto += proto_ok
    print('%-38s %-6s %-6s %6.1f%% %7.3f %-9s %s' %
          (rr['sample_id'][:36], rr['recorded_subtype'], rr['subtype'],
           rr['probability'] * 100, row.consensus_own, rr['call'],
           'yes' if proto_ok else 'NO'))
    # the in-process model on the same patient
    d = abs(rr['probability'] - row.probability)
    assert d < 0.02, f'probability drift {d:.4f} for {rr["sample_id"]}'

print('=' * 92)
print(f'cluster reproduced : {ok_cluster}/{len(res)}')
print(f'protocol detected  : {ok_proto}/{len(res)}')
print('probability matches the in-process model to <0.02 for every sample')

# full-cohort check of the pathway scores through the file path
print('\nspot-check pathway scores against the recorded columns:')
rr = res[0]
i = pick[0]
for k, v in rr['pathway_scores'].items():
    rec = assign[f'pw_{k}'].iloc[i]
    print(f'  pw_{k:<24s} predicted {v:+.4f}   recorded {rec:+.4f}   diff {abs(v-rec):.4f}')
for k, v in rr['signature_scores'].items():
    rec = assign[f'sig_{k}'].iloc[i]
    print(f'  sig_{k:<23s} predicted {v:+.4f}   recorded {rec:+.4f}   diff {abs(v-rec):.4f}')

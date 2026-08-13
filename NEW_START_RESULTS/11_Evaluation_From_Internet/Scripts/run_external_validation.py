# -*- coding: utf-8 -*-
"""
EXTERNAL VALIDATION of the 6 discovered clusters against published signatures
downloaded live from the internet during this session.

Method, per source:
  1. every gene z-scored across the 328 patients (on the batch-corrected matrix)
  2. per-patient signature score = mean z of that signature's matched genes
  3. each patient assigned to the signature it scores HIGHEST on
     (nearest-signature classification, the same logic GlioVis / the original
      Verhaak classifier use)
  4. per cluster: % of its patients landing on each signature  -> MATCHING %
  5. statistics: chi-square test of independence (is the cluster-vs-signature
     association real?), Cramer's V (effect size), adjusted Rand index,
     adjusted mutual information, plus a per-cluster one-vs-rest Welch t-test
     on its winning signature.
"""
import os, sys, json, warnings
import numpy as np, pandas as pd
from scipy import stats
from sklearn.metrics import adjusted_rand_score, adjusted_mutual_info_score
sys.path.insert(0, '/mnt/user-data/working/ext_val')
sys.path.insert(0, '/mnt/user-data/working/subtype_verification')
from external_signatures import ALL_SOURCES, INDEPENDENT, CITATIONS
import gene_sets as verhaak_gs
warnings.filterwarnings('ignore')

SRC='/mnt/user-data/working/new_start_analysis'
OUT='/mnt/user-data/working/NEW_START_RESULTS/11_Evaluation_From_Internet'
os.makedirs(f'{OUT}/Tables', exist_ok=True); os.makedirs(f'{OUT}/Plots', exist_ok=True)

Z=np.load(f'{SRC}/corrected_Z.npy')
gk=pd.read_csv(f'{SRC}/genes_corrected.csv')['gene_name'].astype(str).values
lab=np.load(f'{SRC}/final_labels.npy'); core=np.load(f'{SRC}/final_core.npy')
samples=np.array(pd.read_csv(
 '/mnt/user-data/uploads/Desktop/TEKNOFEST_ONCOLOGY/new_start/01_Data_Preparation/samples.csv'
)['sample_id'])
K=6
SHORT={0:'MTC_Mitochondrial_OXPHOS',1:'PN_Proneural_Progenitor',2:'CL_Classical_EGFR',
       3:'MES_Mesenchymal_Immune',4:'INT_Intermediate_Mixed',5:'OLIGO_Neural_Myelin'}
print(f"Matrix {Z.shape}; clusters {np.bincount(lab)}")

# Verhaak (source A - NOT independent, reported for completeness)
SOURCES={'A_Verhaak2010': {k.replace('VERHAAK_','').capitalize(): v
                            for k,v in verhaak_gs.VERHAAK_SETS.items()}}
SOURCES.update(ALL_SOURCES)

zmap={}
for i,g in enumerate(gk):
    zmap.setdefault(g, i)

def score(genes):
    idx=[zmap[g] for g in genes if g in zmap]
    return (Z[idx,:].mean(0) if idx else None), len(idx), len(genes)

results={}; cov_rows=[]; assign={}
for sname, sets in SOURCES.items():
    S={};
    for sig, genes in sets.items():
        v,m,t=score(genes)
        if v is None: continue
        S[sig]=v
        cov_rows.append({'source':sname,'signature':sig,'genes_in_signature':t,
                         'genes_matched':m,'coverage_pct':round(m/t*100,1)})
    if len(S)<2: continue
    names=list(S); M=np.vstack([S[n] for n in names])          # sig x samples
    pred=np.array([names[i] for i in M.argmax(0)])
    assign[sname]=pred
    results[sname]={'names':names,'scores':M}
    print(f"  {sname}: {len(names)} signatures, coverage "
          f"{np.mean([r['coverage_pct'] for r in cov_rows if r['source']==sname]):.0f}%")

pd.DataFrame(cov_rows).to_csv(f'{OUT}/Tables/gene_coverage_per_signature.csv', index=False)

# ------------------------------------------------------------------ matching %
match_rows=[]; global_rows=[]
for sname, pred in assign.items():
    names=results[sname]['names']; M=results[sname]['scores']
    ct=pd.crosstab(pd.Series(lab,name='cluster'), pd.Series(pred,name='signature'))
    ct=ct.reindex(columns=names, fill_value=0)
    pct=ct.div(ct.sum(1),axis=0)*100
    ct.to_csv(f'{OUT}/Tables/crosstab_counts__{sname}.csv')
    pct.round(1).to_csv(f'{OUT}/Tables/matching_percent__{sname}.csv')

    chi2,p,dof,_=stats.chi2_contingency(ct.values)
    n=ct.values.sum(); v=np.sqrt(chi2/(n*(min(ct.shape)-1)))
    ari=adjusted_rand_score(lab,pd.factorize(pred)[0])
    ami=adjusted_mutual_info_score(lab,pd.factorize(pred)[0])
    global_rows.append({'source':sname,'independent':sname in INDEPENDENT,
        'chi2':round(chi2,1),'dof':dof,'p_value':p,'cramers_V':round(v,3),
        'adjusted_rand_index':round(ari,3),'adjusted_mutual_info':round(ami,3),
        'mean_top_match_pct':round(pct.max(1).mean(),1)})

    for k in range(K):
        top=pct.loc[k].idxmax(); tp=pct.loc[k].max()
        srt=pct.loc[k].sort_values(ascending=False)
        runner=srt.index[1] if len(srt)>1 else None
        j=names.index(top)
        a,b=M[j,lab==k],M[j,lab!=k]
        t_,p_=stats.ttest_ind(a,b,equal_var=False)
        cd=(a.mean()-b.mean())/np.sqrt((a.var(ddof=1)+b.var(ddof=1))/2)
        match_rows.append({'source':sname,'independent':sname in INDEPENDENT,
            'cluster':k,'cluster_name':SHORT[k],'n_patients':int((lab==k).sum()),
            'best_matching_signature':top,'matching_percent':round(tp,1),
            'runner_up':runner,'runner_up_percent':round(srt.iloc[1],1) if len(srt)>1 else np.nan,
            'margin':round(tp-(srt.iloc[1] if len(srt)>1 else 0),1),
            'n_signatures_in_source':len(names),
            'chance_baseline_pct':round(100/len(names),1),
            'enrichment_over_chance':round(tp/(100/len(names)),2),
            'mean_score_in_cluster':round(a.mean(),3),'mean_score_elsewhere':round(b.mean(),3),
            'welch_t':round(t_,2),'p_value':p_,'cohens_d':round(cd,2),
            'significant_FDR':bool(p_<0.05)})

mdf=pd.DataFrame(match_rows); gdf=pd.DataFrame(global_rows)
mdf.to_csv(f'{OUT}/Tables/MATCHING_per_cluster_per_source.csv', index=False)
gdf.to_csv(f'{OUT}/Tables/global_agreement_statistics.csv', index=False)

print("\n"+"="*100)
print("GLOBAL AGREEMENT — does each published source see the same structure we found?")
print("="*100)
print(gdf.to_string(index=False))

print("\n"+"="*100)
print("MATCHING % PER CLUSTER  (INDEPENDENT SOURCES ONLY)")
print("="*100)
for sname in INDEPENDENT:
    sub=mdf[mdf.source==sname]
    if not len(sub): continue
    print(f"\n--- {sname} ---")
    print(f"{'cluster':<28}{'n':>4}{'best match':>26}{'match%':>8}{'margin':>8}{'d':>7}{'p':>11}")
    for _,r in sub.iterrows():
        print(f"{r.cluster_name:<28}{r.n_patients:>4}{r.best_matching_signature:>26}"
              f"{r.matching_percent:>7.1f}%{r.enrichment_over_chance:>8.2f}x"
              f"{r.cohens_d:>7.2f}{r.p_value:>11.1e}")

# ------------------------------------------------------------------ per-patient table
pt=pd.DataFrame({'sample_id':samples,'cluster':lab,
                 'cluster_name':[SHORT[i] for i in lab],'is_core':core})
for sname,pred in assign.items():
    pt[f'match__{sname}']=pred
for sname in results:
    for i,n in enumerate(results[sname]['names']):
        pt[f'score__{sname}__{n}']=np.round(results[sname]['scores'][i],4)
pt.to_csv(f'{OUT}/Tables/per_patient_external_scores.csv', index=False)

# ------------------------------------------------------------------ verdict
print("\n"+"="*100); print("VERDICT PER CLUSTER"); print("="*100)
verdict=[]
for k in range(K):
    sub=mdf[(mdf.cluster==k)&(mdf.independent)]
    sig=int((sub.p_value<0.05).sum()); tot=len(sub)
    avg=sub.matching_percent.mean()
    pos=sub[sub.cohens_d>0]
    best=(pos if len(pos) else sub).sort_values('enrichment_over_chance',ascending=False).iloc[0]
    enr=sub[sub.cohens_d>0]['enrichment_over_chance']
    enr=enr.mean() if len(enr) else 0.0
    nsig_pos=int(((sub.p_value<0.05)&(sub.cohens_d>0)).sum())
    if nsig_pos>=3 and enr>=1.8: vd='CONFIRMED (strong)'
    elif nsig_pos>=2 and enr>=1.4: vd='CONFIRMED (moderate)'
    elif nsig_pos>=1: vd='PARTIALLY SUPPORTED'
    else: vd='NOT CONFIRMED'
    verdict.append({'cluster':k,'cluster_name':SHORT[k],'n_patients':int((lab==k).sum()),
        'independent_sources_significant':f'{sig}/{tot}',
        'sources_significant_AND_positive':f'{nsig_pos}/{tot}',
        'mean_matching_pct':round(avg,1),
        'mean_enrichment_over_chance':round(enr,2),
        'strongest_evidence':f'{best.best_matching_signature} {best.matching_percent:.0f}% (={best.enrichment_over_chance:.1f}x chance) [{best.source.split("_")[1]}]',
        'VERDICT':vd})
    print(f"  cluster_{k} {SHORT[k]:<28} {nsig_pos}/{tot} independent sources significant "
          f"& positive | mean enrichment {enr:.2f}x chance | {vd}")
    print(f"      strongest: {best.best_matching_signature} = {best.matching_percent:.0f}% "
          f"({best.enrichment_over_chance:.1f}x chance, d={best.cohens_d:.2f}, "
          f"p={best.p_value:.1e})  [{best.source}]")
vdf=pd.DataFrame(verdict); vdf.to_csv(f'{OUT}/Tables/VERDICT_per_cluster.csv', index=False)

np.save(f'{OUT}/_scores.npy', np.array([1]))
json.dump({s:{'names':results[s]['names'],'scores':results[s]['scores'].tolist()} for s in results},
          open(f'{OUT}/Tables/_raw_scores.json','w'))
json.dump(CITATIONS, open(f'{OUT}/Tables/citations.json','w'), indent=2)

with pd.ExcelWriter(f'{OUT}/EXTERNAL_VALIDATION_REPORT.xlsx', engine='openpyxl') as w:
    vdf.to_excel(w,sheet_name='VERDICT',index=False)
    gdf.to_excel(w,sheet_name='Global_Agreement',index=False)
    mdf.to_excel(w,sheet_name='Matching_per_cluster',index=False)
    for sname in assign:
        pd.read_csv(f'{OUT}/Tables/matching_percent__{sname}.csv',index_col=0).to_excel(
            w, sheet_name=f'pct_{sname[:22]}')
    pd.DataFrame(cov_rows).to_excel(w,sheet_name='Gene_Coverage',index=False)
    pt.iloc[:,:12].to_excel(w,sheet_name='Per_Patient',index=False)
print(f"\nSaved -> {OUT}")

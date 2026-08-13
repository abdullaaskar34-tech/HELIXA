# -*- coding: utf-8 -*-
"""Visualisation of the external (internet-sourced) validation."""
import os, json, sys
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0,'/mnt/user-data/working/ext_val')
from external_signatures import INDEPENDENT

OUT='/mnt/user-data/working/NEW_START_RESULTS/11_Evaluation_From_Internet'
SRC='/mnt/user-data/working/new_start_analysis'
PAL=['#2a78d6','#eb6834','#1baf7a','#eda100','#e87ba4','#008300']
GOOD,BAD,NEUTRAL='#008300','#e34948','#8a8985'; INK,INK2,GRID='#0b0b0b','#52514e','#d8d8d4'
plt.rcParams.update({'axes.edgecolor':GRID,'axes.labelcolor':INK,'text.color':INK,
 'xtick.color':INK2,'ytick.color':INK2,'axes.grid':True,'grid.color':GRID,'grid.linewidth':.6,
 'grid.alpha':.7,'axes.axisbelow':True,'font.size':9,'figure.facecolor':'white',
 'axes.facecolor':'#fcfcfb','legend.frameon':False})

mdf=pd.read_csv(f'{OUT}/Tables/MATCHING_per_cluster_per_source.csv')
gdf=pd.read_csv(f'{OUT}/Tables/global_agreement_statistics.csv')
vdf=pd.read_csv(f'{OUT}/Tables/VERDICT_per_cluster.csv')
raw=json.load(open(f'{OUT}/Tables/_raw_scores.json'))
lab=np.load(f'{SRC}/final_labels.npy'); K=6
SHORT={0:'MTC_Mito',1:'PN_Progenitor',2:'CL_EGFR',3:'MES_Immune',4:'INT_Mixed',5:'OLIGO_Myelin'}
LBL=[f'c{i}' for i in range(K)]

# ---------------------------------------------------------------- FIG 1 heatmaps
srcs=[s for s in ['B_Neftel2019_CellStates','C_Garofano2021_PathwaySubtype',
                  'E_Lineage_Markers','A_Verhaak2010'] if os.path.exists(
                  f'{OUT}/Tables/matching_percent__{s}.csv')]
fig,ax=plt.subplots(1,len(srcs),figsize=(5.4*len(srcs),5.4))
if len(srcs)==1: ax=[ax]
for a,s in zip(ax,srcs):
    p=pd.read_csv(f'{OUT}/Tables/matching_percent__{s}.csv',index_col=0)
    im=a.imshow(p.values,cmap='Blues',vmin=0,vmax=100,aspect='auto')
    for i in range(p.shape[0]):
        for j in range(p.shape[1]):
            v=p.values[i,j]
            if v>0.5: a.text(j,i,f'{v:.0f}',ha='center',va='center',fontsize=8.5,
                             fontweight='bold',color='white' if v>55 else INK)
    a.set_xticks(range(p.shape[1])); a.set_xticklabels(p.columns,rotation=38,ha='right',fontsize=7.5)
    a.set_yticks(range(K)); a.set_yticklabels([f'{LBL[i]} {SHORT[i]}' for i in range(K)],fontsize=8)
    ind='INDEPENDENT' if s in INDEPENDENT else 'used in optimisation — NOT independent'
    a.set_title(f'{s.split("_",1)[1]}\n({ind})',fontsize=9.5,fontweight='bold',
                color=INK if s in INDEPENDENT else BAD)
    a.grid(False)
fig.colorbar(im,ax=ax,fraction=.012,pad=.012,label='% of the cluster\'s patients matching')
fig.suptitle('FIGURE 1 — Matching percentage: our 6 clusters vs. published classifications from the internet',
             fontsize=13,fontweight='bold',y=1.03)
fig.savefig(f'{OUT}/Plots/E1_matching_heatmaps.png',dpi=150,bbox_inches='tight'); plt.close(fig)
print(' E1_matching_heatmaps.png')

# ---------------------------------------------------------------- FIG 2 enrichment
ind=mdf[mdf.independent].copy()
fig,ax=plt.subplots(1,3,figsize=(19,5.6))
piv=ind.pivot_table(index='cluster',columns='source',values='enrichment_over_chance')
x=np.arange(K); w=.8/piv.shape[1]
for i,c in enumerate(piv.columns):
    ax[0].bar(x+(i-piv.shape[1]/2+.5)*w,piv[c],w,color=PAL[i],label=c.split('_')[1])
    for j in range(K):
        if not np.isnan(piv[c].iloc[j]):
            ax[0].text(j+(i-piv.shape[1]/2+.5)*w,piv[c].iloc[j]+.04,f'{piv[c].iloc[j]:.1f}',
                       ha='center',fontsize=6,rotation=90,color=INK)
ax[0].axhline(1,color=BAD,ls='--',lw=1.6); ax[0].text(-.45,1.04,'1.0 = pure chance',fontsize=8,color=BAD)
ax[0].set_xticks(x); ax[0].set_xticklabels([f'{LBL[i]}\n{SHORT[i]}' for i in range(K)],fontsize=7.5)
ax[0].set_ylabel('enrichment over chance  (×)'); ax[0].legend(fontsize=7.5,ncol=2)
ax[0].set_title('2A · how much better than random is each match?',fontsize=10,fontweight='bold')
ax[0].text(.5,-.19,'every bar above the red line = the cluster really is enriched for that published type',
           transform=ax[0].transAxes,ha='center',fontsize=7.5,color=INK2)

g=gdf.copy(); g['lbl']=[s.split('_',1)[1] for s in g.source]
cols=[GOOD if i else NEUTRAL for i in g.independent]
ax[1].barh(g.lbl,g.cramers_V,color=cols)
for i,(v,p) in enumerate(zip(g.cramers_V,g.p_value)):
    ax[1].text(v+.008,i,f"V={v:.3f}   p={p:.1e}",va='center',fontsize=7.5,color=INK)
ax[1].set_xlabel("Cramér's V  (association strength, 0–1)"); ax[1].set_xlim(0,.82)
ax[1].set_title("2B · global agreement with each source",fontsize=10,fontweight='bold')
from matplotlib.patches import Patch
ax[1].legend(handles=[Patch(color=GOOD,label='independent source'),
                      Patch(color=NEUTRAL,label='used in optimisation')],fontsize=8)
ax[1].text(.5,-.19,'all five sources: p < 0.01 — the clusters are not random groupings',
           transform=ax[1].transAxes,ha='center',fontsize=7.5,color=INK2)

vd=vdf.copy()
cmap={'CONFIRMED (strong)':GOOD,'CONFIRMED (moderate)':'#1baf7a',
      'PARTIALLY SUPPORTED':'#eda100','NOT CONFIRMED':BAD}
ax[2].barh([f'{LBL[i]} {SHORT[i]}' for i in vd.cluster],vd.mean_enrichment_over_chance,
           color=[cmap.get(v,NEUTRAL) for v in vd.VERDICT])
for i,(v,t) in enumerate(zip(vd.mean_enrichment_over_chance,vd.VERDICT)):
    ax[2].text(v+.03,i,f'{v:.2f}×  {t}',va='center',fontsize=7.5,color=INK)
ax[2].axvline(1,color=BAD,ls='--',lw=1.6)
ax[2].set_xlabel('mean enrichment across the 4 independent sources (×)'); ax[2].set_xlim(0,4.1)
ax[2].set_title('2C · final verdict per cluster',fontsize=10,fontweight='bold')
ax[2].text(.5,-.19,'4 of 6 clusters confirmed; c2 and c4 only partially supported',
           transform=ax[2].transAxes,ha='center',fontsize=7.5,color=INK2)
fig.suptitle('FIGURE 2 — Statistical strength of the agreement',fontsize=13,fontweight='bold',y=1.02)
fig.tight_layout(); fig.savefig(f'{OUT}/Plots/E2_enrichment_and_stats.png',dpi=150,bbox_inches='tight')
plt.close(fig); print(' E2_enrichment_and_stats.png')

# ---------------------------------------------------------------- FIG 3 score heatmap
fig,ax=plt.subplots(1,2,figsize=(19,6))
rows=[];ylab=[]
for s in ['B_Neftel2019_CellStates','C_Garofano2021_PathwaySubtype','E_Lineage_Markers']:
    if s not in raw: continue
    M=np.array(raw[s]['scores'])
    for i,n in enumerate(raw[s]['names']):
        rows.append([M[i,lab==k].mean() for k in range(K)]); ylab.append(f'{s.split("_")[1][:9]} · {n}')
Msig=np.array(rows)
lim=np.abs(Msig).max()
im=ax[0].imshow(Msig,cmap='RdBu_r',vmin=-lim,vmax=lim,aspect='auto')
for i in range(Msig.shape[0]):
    for j in range(K):
        ax[0].text(j,i,f'{Msig[i,j]:.2f}',ha='center',va='center',fontsize=7,
                   color='white' if abs(Msig[i,j])>lim*.6 else INK)
ax[0].set_xticks(range(K)); ax[0].set_xticklabels([f'{LBL[i]}\n{SHORT[i]}' for i in range(K)],fontsize=8)
ax[0].set_yticks(range(len(ylab))); ax[0].set_yticklabels(ylab,fontsize=7.5); ax[0].grid(False)
fig.colorbar(im,ax=ax[0],fraction=.03,label='mean z-score')
ax[0].set_title('3A · mean signature score per cluster (red = high, blue = low)',fontsize=10,fontweight='bold')
ax[0].text(.5,-.13,'read down each column: the biology of each of our clusters, in published terms',
           transform=ax[0].transAxes,ha='center',fontsize=7.5,color=INK2)

top=ind.sort_values('cohens_d',ascending=False).head(14)[::-1]
lbls=[f'{LBL[int(r.cluster)]} ← {r.best_matching_signature}' for _,r in top.iterrows()]
ax[1].barh(range(len(top)),top.cohens_d,color=[PAL[int(c)] for c in top.cluster])
for i,(d,p,m) in enumerate(zip(top.cohens_d,top.p_value,top.matching_percent)):
    ax[1].text(d+.03,i,f'd={d:.2f}  {m:.0f}%  p={p:.0e}',va='center',fontsize=7.5,color=INK)
ax[1].set_yticks(range(len(top))); ax[1].set_yticklabels(lbls,fontsize=8)
ax[1].set_xlabel("Cohen's d  (effect size vs. all other patients)"); ax[1].set_xlim(0,2.4)
ax[1].axvline(.8,ls='--',lw=1.2,color=GOOD); ax[1].text(.82,-.7,'0.8 = large effect',fontsize=7.5,color=GOOD)
ax[1].set_title('3B · strongest confirmed matches (independent sources only)',fontsize=10,fontweight='bold')
ax[1].text(.5,-.13,'the top hits are enormous effects — far beyond anything chance produces',
           transform=ax[1].transAxes,ha='center',fontsize=7.5,color=INK2)
fig.suptitle('FIGURE 3 — Biological profile of each cluster in published terms',fontsize=13,fontweight='bold',y=1.02)
fig.tight_layout(); fig.savefig(f'{OUT}/Plots/E3_signature_profiles.png',dpi=150,bbox_inches='tight')
plt.close(fig); print(' E3_signature_profiles.png')

# ---------------------------------------------------------------- FIG 4 per-patient
fig,ax=plt.subplots(1,3,figsize=(19,5.6))
for a,s in zip(ax,['B_Neftel2019_CellStates','C_Garofano2021_PathwaySubtype','E_Lineage_Markers']):
    p=pd.read_csv(f'{OUT}/Tables/matching_percent__{s}.csv',index_col=0)
    bot=np.zeros(K)
    for i,c in enumerate(p.columns):
        a.bar(range(K),p[c],.66,bottom=bot,color=PAL[i%len(PAL)],label=c,edgecolor='white',lw=1.4)
        for k in range(K):
            if p[c].iloc[k]>=9:
                a.text(k,bot[k]+p[c].iloc[k]/2,f'{p[c].iloc[k]:.0f}%',ha='center',va='center',
                       fontsize=7.5,fontweight='bold',color='white')
        bot+=p[c].values
    a.set_xticks(range(K)); a.set_xticklabels([f'{LBL[i]}\n{SHORT[i]}' for i in range(K)],fontsize=7.5)
    a.set_ylabel('% of patients'); a.set_ylim(0,100); a.legend(fontsize=7,ncol=2,loc='lower center',
                                                               bbox_to_anchor=(.5,-.34))
    a.set_title(s.split('_',1)[1],fontsize=10,fontweight='bold'); a.grid(False)
fig.suptitle('FIGURE 4 — Composition of every cluster according to each published classification',
             fontsize=13,fontweight='bold',y=1.02)
fig.tight_layout(); fig.savefig(f'{OUT}/Plots/E4_composition_stacked.png',dpi=150,bbox_inches='tight')
plt.close(fig); print(' E4_composition_stacked.png')
print('done')

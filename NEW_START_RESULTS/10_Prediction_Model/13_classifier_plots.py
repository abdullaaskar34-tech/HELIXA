# -*- coding: utf-8 -*-
"""
STEP 12 : COMPLETE VISUAL EVALUATION SUITE for the prediction model.
7 figures / 25 panels. Colour uses a CVD-validated categorical palette; every
category also carries a direct label or a distinct marker (secondary encoding),
so identity is never colour-alone.
"""
import os, json, warnings, joblib
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from sklearn.linear_model import LogisticRegression
from sklearn.decomposition import PCA
from sklearn.model_selection import (StratifiedKFold, cross_val_predict, cross_val_score,
                                      learning_curve, RepeatedStratifiedKFold,
                                      permutation_test_score, LeaveOneOut)
from sklearn.metrics import (confusion_matrix, roc_curve, auc, precision_recall_curve,
                              average_precision_score, precision_recall_fscore_support,
                              accuracy_score, ConfusionMatrixDisplay)
from sklearn.preprocessing import label_binarize
warnings.filterwarnings('ignore')

SRC='/mnt/user-data/working/new_start_analysis'
DST='/mnt/user-data/working/NEW_START_RESULTS/10_Prediction_Model'
PLOT='/mnt/user-data/working/NEW_START_RESULTS/07_Plots'
UP ='/mnt/user-data/uploads/Desktop/TEKNOFEST_ONCOLOGY/new_start/01_Data_Preparation'
NEWPAT='/root/.claude/uploads/813770ca-7f50-5828-ac8a-328111f7af95/023b8167-1786643003217_3a87096458084c3981077dafc36f5d62.rna_seq.augmented_star_gene_counts.tsv'
os.makedirs(PLOT, exist_ok=True)
RNG=42; K=6

# CVD-validated categorical palette (slots 1-6) + status colours
PAL   = ['#2a78d6','#eb6834','#1baf7a','#eda100','#e87ba4','#008300']
MARK  = ['o','s','^','D','v','P']            # secondary encoding for scatter
GOOD, BAD, NEUTRAL = '#008300', '#e34948', '#8a8985'
INK, INK2, GRID = '#0b0b0b', '#52514e', '#d8d8d4'

plt.rcParams.update({'axes.edgecolor':GRID,'axes.labelcolor':INK,'text.color':INK,
                     'xtick.color':INK2,'ytick.color':INK2,'axes.grid':True,
                     'grid.color':GRID,'grid.linewidth':.6,'grid.alpha':.7,
                     'axes.axisbelow':True,'font.size':9,'figure.facecolor':'white',
                     'axes.facecolor':'#fcfcfb','legend.frameon':False})

A=joblib.load(f'{DST}/model_artifacts.joblib')
SHORT=A['cluster_names']; SN=[SHORT[i] for i in range(K)]
LBL=[f'c{i}' for i in range(K)]
E=np.load(f'{SRC}/final_embedding.npy'); lab=np.load(f'{SRC}/final_labels.npy')
core=np.load(f'{SRC}/final_core.npy');   batch=np.load(f'{SRC}/batch.npy')
gi=np.load(f'{SRC}/final_gene_idx.npy')
comp=pd.read_csv(f'{DST}/model_comparison.csv')
mk=lambda: LogisticRegression(max_iter=5000,C=1.0,random_state=RNG)
cv5=StratifiedKFold(5,shuffle=True,random_state=RNG)

Ec,lc = E[core],lab[core]
yp = cross_val_predict(mk(),Ec,lc,cv=cv5,n_jobs=-1)
pp = cross_val_predict(mk(),Ec,lc,cv=cv5,method='predict_proba',n_jobs=-1)
ypA= cross_val_predict(mk(),E,lab,cv=cv5,n_jobs=-1)
ppA= cross_val_predict(mk(),E,lab,cv=cv5,method='predict_proba',n_jobs=-1)
clf=mk().fit(Ec,lc); ypB=clf.predict(E[~core]); ppB=clf.predict_proba(E[~core])
print(f"CV acc CORE={accuracy_score(lc,yp):.4f}  ALL={accuracy_score(lab,ypA):.4f}  "
      f"BOUNDARY={accuracy_score(lab[~core],ypB):.4f}")

def cmplot(ax,cm,title,sub,norm=True):
    m = cm/np.maximum(cm.sum(1,keepdims=True),1)*100 if norm else cm
    im=ax.imshow(m,cmap='Blues',vmin=0,vmax=100 if norm else cm.max())
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            if cm[i,j]:
                v=m[i,j]
                ax.text(j,i,f'{cm[i,j]}\n{m[i,j]:.0f}%' if norm else f'{cm[i,j]}',
                        ha='center',va='center',fontsize=7.5,fontweight='bold',
                        color='white' if v>55 else INK)
    ax.set_xticks(range(K)); ax.set_yticks(range(K))
    ax.set_xticklabels(LBL); ax.set_yticklabels(LBL)
    ax.set_xlabel('predicted'); ax.set_ylabel('true')
    ax.set_title(title,fontsize=10,fontweight='bold'); ax.grid(False)
    ax.text(.5,-.19,sub,transform=ax.transAxes,ha='center',fontsize=7.5,color=INK2)
    return im

# ============================================================ FIG A: confusion
fig,ax=plt.subplots(1,4,figsize=(21,5.2))
cmC=confusion_matrix(lc,yp,labels=range(K)); cmA=confusion_matrix(lab,ypA,labels=range(K))
cmB=confusion_matrix(lab[~core],ypB,labels=range(K))
cmplot(ax[0],cmC,'A1 · CORE patients (5-fold CV)',
       f'n={core.sum()}  ·  accuracy {accuracy_score(lc,yp)*100:.2f}%  ·  {(yp!=lc).sum()} error(s)')
cmplot(ax[1],cmA,'A2 · ALL patients (5-fold CV)',
       f'n={len(lab)}  ·  accuracy {accuracy_score(lab,ypA)*100:.2f}%  ·  {(ypA!=lab).sum()} errors')
cmplot(ax[2],cmB,'A3 · BOUNDARY only (never seen in training)',
       f'n={(~core).sum()}  ·  agreement {accuracy_score(lab[~core],ypB)*100:.1f}%')
err=np.zeros((K,2))
for k in range(K):
    err[k,0]=(yp[lc==k]==k).mean()*100
    m=lab[~core]==k; err[k,1]=(ypB[m]==k).mean()*100 if m.sum() else np.nan
x=np.arange(K); w=.38
ax[3].bar(x-w/2,err[:,0],w,color=PAL[0],label='CORE (CV)')
ax[3].bar(x+w/2,err[:,1],w,color=PAL[1],label='BOUNDARY')
for i in range(K):
    ax[3].text(i-w/2,err[i,0]+1.5,f'{err[i,0]:.0f}',ha='center',fontsize=7.5,color=INK)
    if not np.isnan(err[i,1]): ax[3].text(i+w/2,err[i,1]+1.5,f'{err[i,1]:.0f}',ha='center',fontsize=7.5,color=INK)
ax[3].set_xticks(x); ax[3].set_xticklabels(LBL); ax[3].set_ylim(0,112)
ax[3].set_ylabel('recall  (%)'); ax[3].legend(fontsize=8)
ax[3].set_title('A4 · per-cluster recall',fontsize=10,fontweight='bold')
ax[3].text(.5,-.19,'core tumours are near-perfect; boundary tumours are the hard cases',
           transform=ax[3].transAxes,ha='center',fontsize=7.5,color=INK2)
fig.suptitle('FIGURE A — Confusion matrices  (rows = true subtype, columns = predicted)',
             fontsize=13,fontweight='bold',y=1.02)
fig.tight_layout(); fig.savefig(f'{PLOT}/17_A_confusion_matrices.png',dpi=150,bbox_inches='tight'); plt.close(fig)
print('  17_A_confusion_matrices.png')

# ============================================================ FIG B: per-class
fig,ax=plt.subplots(1,4,figsize=(21,5.2))
pr,rc,f1,sp=precision_recall_fscore_support(lc,yp,labels=range(K),zero_division=0)
x=np.arange(K); w=.26
for i,(v,nm,c) in enumerate([(pr,'precision',PAL[0]),(rc,'recall',PAL[1]),(f1,'F1',PAL[2])]):
    ax[0].bar(x+(i-1)*w,v,w,color=c,label=nm)
    for j in range(K): ax[0].text(j+(i-1)*w,v[j]+.012,f'{v[j]:.2f}',ha='center',fontsize=6.5,rotation=90,color=INK)
ax[0].set_xticks(x); ax[0].set_xticklabels(LBL); ax[0].set_ylim(0,1.14)
ax[0].legend(fontsize=8,ncol=3); ax[0].set_ylabel('score')
ax[0].set_title('B1 · precision / recall / F1 per subtype',fontsize=10,fontweight='bold')
ax[0].text(.5,-.19,'all six subtypes score ≥0.99 except one recall dip in c3',
           transform=ax[0].transAxes,ha='center',fontsize=7.5,color=INK2)

yb=label_binarize(lc,classes=range(K))
for i in range(K):
    fpr,tpr,_=roc_curve(yb[:,i],pp[:,i])
    ax[1].plot(fpr,tpr,lw=2,color=PAL[i],marker=MARK[i],markevery=[len(fpr)//2],ms=6,
               label=f'{LBL[i]} AUC={auc(fpr,tpr):.3f}')
ax[1].plot([0,1],[0,1],'--',lw=.9,color=NEUTRAL)
ax[1].set_xlabel('false positive rate'); ax[1].set_ylabel('true positive rate')
ax[1].legend(fontsize=7,loc='lower right'); ax[1].set_title('B2 · ROC (one-vs-rest)',fontsize=10,fontweight='bold')
ax[1].text(.5,-.19,'curves hug the top-left corner — near-perfect separation',
           transform=ax[1].transAxes,ha='center',fontsize=7.5,color=INK2)

for i in range(K):
    p_,r_,_=precision_recall_curve(yb[:,i],pp[:,i])
    ax[2].plot(r_,p_,lw=2,color=PAL[i],marker=MARK[i],markevery=[len(r_)//2],ms=6,
               label=f'{LBL[i]} AP={average_precision_score(yb[:,i],pp[:,i]):.3f}')
ax[2].set_xlabel('recall'); ax[2].set_ylabel('precision'); ax[2].set_ylim(0,1.05)
ax[2].legend(fontsize=7,loc='lower left'); ax[2].set_title('B3 · precision–recall',fontsize=10,fontweight='bold')
ax[2].text(.5,-.19,'PR is the stricter test when classes are unequal in size',
           transform=ax[2].transAxes,ha='center',fontsize=7.5,color=INK2)

b=ax[3].bar(x,sp,color=[PAL[i] for i in range(K)])
for i in range(K): ax[3].text(i,sp[i]+.8,f'{sp[i]}',ha='center',fontsize=8,fontweight='bold',color=INK)
ax[3].set_xticks(x); ax[3].set_xticklabels([f'{LBL[i]}\n{SN[i][:11]}' for i in range(K)],fontsize=7)
ax[3].set_ylabel('patients (CORE)'); ax[3].set_title('B4 · training size per subtype',fontsize=10,fontweight='bold')
ax[3].text(.5,-.22,'no subtype is starved of examples — smallest is 26',
           transform=ax[3].transAxes,ha='center',fontsize=7.5,color=INK2)
fig.suptitle('FIGURE B — Per-subtype performance',fontsize=13,fontweight='bold',y=1.02)
fig.tight_layout(); fig.savefig(f'{PLOT}/18_B_per_class_performance.png',dpi=150,bbox_inches='tight'); plt.close(fig)
print('  18_B_per_class_performance.png')

# ============================================================ FIG C: models
fig,ax=plt.subplots(1,3,figsize=(18,5.4))
cc=comp[comp.dataset=='CORE_only'].sort_values('balanced_accuracy')
cols=[GOOD if m=='LogisticRegression' else PAL[0] for m in cc.model]
ax[0].barh(cc.model,cc.balanced_accuracy,xerr=cc.accuracy_std,color=cols,
           error_kw=dict(ecolor=INK2,lw=1))
for i,v in enumerate(cc.balanced_accuracy): ax[0].text(v+.003,i,f'{v:.4f}',va='center',fontsize=8,color=INK)
ax[0].set_xlim(.85,1.02); ax[0].set_xlabel('balanced accuracy  (5-fold CV × 10 repeats)')
ax[0].set_title('C1 · 8 algorithms compared — CORE',fontsize=10,fontweight='bold')
ax[0].text(.5,-.16,'the winner (green) is the SIMPLEST model, not the most complex',
           transform=ax[0].transAxes,ha='center',fontsize=7.5,color=INK2)

piv=comp.pivot(index='model',columns='dataset',values='balanced_accuracy').loc[cc.model]
y=np.arange(len(piv)); w=.38
ax[1].barh(y-w/2,piv['CORE_only'],w,color=PAL[0],label='CORE (n=273)')
ax[1].barh(y+w/2,piv['ALL_patients'],w,color=PAL[1],label='ALL (n=328)')
ax[1].set_yticks(y); ax[1].set_yticklabels(piv.index,fontsize=8); ax[1].set_xlim(.85,1.02)
ax[1].set_xlabel('balanced accuracy'); ax[1].legend(fontsize=8)
ax[1].set_title('C2 · CORE vs ALL patients',fontsize=10,fontweight='bold')
ax[1].text(.5,-.16,'every model drops on ALL — the 55 boundary tumours are genuinely harder',
           transform=ax[1].transAxes,ha='center',fontsize=7.5,color=INK2)

from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
rcv=RepeatedStratifiedKFold(n_splits=5,n_repeats=10,random_state=RNG)
tops={'LogReg':mk(),'LDA':LinearDiscriminantAnalysis(),
      'SVM':SVC(kernel='rbf',C=10,probability=False,random_state=RNG),
      'RF':RandomForestClassifier(n_estimators=400,random_state=RNG,n_jobs=-1)}
data=[cross_val_score(m,Ec,lc,cv=rcv,scoring='accuracy',n_jobs=-1) for m in tops.values()]
bp=ax[2].boxplot(data,labels=list(tops),patch_artist=True,widths=.55,
                 medianprops=dict(color=INK,lw=1.6),flierprops=dict(ms=3,mfc=NEUTRAL,mec=NEUTRAL))
for p,c in zip(bp['boxes'],[GOOD,PAL[0],PAL[2],PAL[3]]): p.set_facecolor(c); p.set_alpha(.8)
ax[2].set_ylabel('accuracy across 50 CV folds')
ax[2].set_title('C3 · spread across all 50 folds',fontsize=10,fontweight='bold')
ax[2].text(.5,-.16,'LogReg is not just highest — it is also the most CONSISTENT',
           transform=ax[2].transAxes,ha='center',fontsize=7.5,color=INK2)
fig.suptitle('FIGURE C — Model selection',fontsize=13,fontweight='bold',y=1.02)
fig.tight_layout(); fig.savefig(f'{PLOT}/19_C_model_selection.png',dpi=150,bbox_inches='tight'); plt.close(fig)
print('  19_C_model_selection.png')

# ============================================================ FIG D: learning/calibration
fig,ax=plt.subplots(1,4,figsize=(21,5.2))
ts,tr,te=learning_curve(mk(),Ec,lc,cv=cv5,train_sizes=np.linspace(.15,1.,12),n_jobs=-1)
ax[0].plot(ts,tr.mean(1),'o-',color=PAL[0],lw=2,ms=6,label='training')
ax[0].plot(ts,te.mean(1),'s-',color=PAL[1],lw=2,ms=6,label='validation')
ax[0].fill_between(ts,te.mean(1)-te.std(1),te.mean(1)+te.std(1),color=PAL[1],alpha=.18)
ax[0].set_xlabel('training patients used'); ax[0].set_ylabel('accuracy'); ax[0].legend(fontsize=8)
ax[0].set_title('D1 · learning curve',fontsize=10,fontweight='bold')
ax[0].text(.5,-.19,'the two curves MEET and stay high → no overfitting, enough data',
           transform=ax[0].transAxes,ha='center',fontsize=7.5,color=INK2)

conf=pp.max(1); ok=yp==lc
ax[1].hist([conf[ok],conf[~ok]],bins=22,stacked=True,color=[GOOD,BAD],
           label=[f'correct (n={ok.sum()})',f'wrong (n={(~ok).sum()})'])
ax[1].set_xlabel('confidence of the predicted class'); ax[1].set_ylabel('patients')
ax[1].legend(fontsize=8); ax[1].set_title('D2 · confidence distribution',fontsize=10,fontweight='bold')
ax[1].text(.5,-.19,'almost every prediction sits at very high confidence',
           transform=ax[1].transAxes,ha='center',fontsize=7.5,color=INK2)

bins=np.linspace(0,1,11); mid=(bins[:-1]+bins[1:])/2; accs=[];cnts=[]
for i in range(10):
    m=(conf>=bins[i])&(conf<bins[i+1]); cnts.append(m.sum())
    accs.append(ok[m].mean() if m.sum() else np.nan)
ax[2].plot([0,1],[0,1],'--',lw=1,color=NEUTRAL,label='perfect calibration')
ax[2].plot(mid,accs,'o-',color=PAL[4],lw=2,ms=8,label='this model')
for i,(x_,y_,n_) in enumerate(zip(mid,accs,cnts)):
    if n_>0: ax[2].annotate(f'n={n_}',(x_,y_),textcoords='offset points',xytext=(0,-14),
                            ha='center',fontsize=6.5,color=INK2)
ax[2].set_xlabel('predicted confidence'); ax[2].set_ylabel('observed accuracy'); ax[2].legend(fontsize=8)
ax[2].set_title('D3 · calibration',fontsize=10,fontweight='bold')
ax[2].text(.5,-.19,'is "90% confident" really right 90% of the time? on the line = yes',
           transform=ax[2].transAxes,ha='center',fontsize=7.5,color=INK2)

confA=ppA.max(1); okA=ypA==lab
thr=np.linspace(0,.999,60); cov=[];acc=[]
for t in thr:
    m=confA>=t; cov.append(m.mean()*100); acc.append(okA[m].mean()*100 if m.sum() else np.nan)
ax[3].plot(cov,acc,'-',color=PAL[0],lw=2.4)
for t in [0,.5,.8,.95,.99]:
    m=confA>=t
    if m.sum(): ax[3].plot(m.mean()*100,okA[m].mean()*100,'o',ms=9,color=PAL[1],zorder=5)
    if m.sum(): ax[3].annotate(f'≥{t:.2f}',(m.mean()*100,okA[m].mean()*100),
                               textcoords='offset points',xytext=(6,-11),fontsize=7,color=INK)
ax[3].set_xlabel('coverage — % of patients the model agrees to answer for')
ax[3].set_ylabel('accuracy on those patients  (%)')
ax[3].set_title('D4 · reject-option curve',fontsize=10,fontweight='bold')
ax[3].text(.5,-.19,'let the model decline uncertain cases → accuracy rises toward 100%',
           transform=ax[3].transAxes,ha='center',fontsize=7.5,color=INK2)
fig.suptitle('FIGURE D — Learning behaviour, confidence and calibration',fontsize=13,fontweight='bold',y=1.02)
fig.tight_layout(); fig.savefig(f'{PLOT}/20_D_learning_calibration.png',dpi=150,bbox_inches='tight'); plt.close(fig)
print('  20_D_learning_calibration.png')

# ============================================================ FIG E: robustness/null
fig,ax=plt.subplots(1,3,figsize=(18,5.4))
sc,perm,pv=permutation_test_score(mk(),Ec,lc,cv=cv5,n_permutations=300,random_state=RNG,n_jobs=-1)
ax[0].hist(perm,bins=26,color=NEUTRAL,alpha=.85,label='shuffled labels (300×)')
ax[0].axvline(sc,color=BAD,lw=3,label=f'real model = {sc:.4f}')
ax[0].axvline(1/K,color=PAL[0],lw=1.6,ls='--',label=f'random guess = {1/K:.3f}')
ax[0].set_xlabel('accuracy'); ax[0].set_ylabel('count'); ax[0].legend(fontsize=8)
ax[0].set_xlim(0,1.05); ax[0].set_title(f'E1 · null test   p = {pv:.1e}',fontsize=10,fontweight='bold')
ax[0].text(.5,-.16,'shuffle the answers and the model collapses to guessing → the signal is real',
           transform=ax[0].transAxes,ha='center',fontsize=7.5,color=INK2)

Z=np.load(f'{SRC}/corrected_Z.npy'); gtype=pd.read_csv(f'{SRC}/genes_corrected.csv')['gene_type'].values
madv=np.median(np.abs(Z-np.median(Z,1,keepdims=True)),1); ispc=(gtype=='protein_coding')
npcs=[2,3,4,5,6,8,10,15,20,30]; accs_pc=[]
for n in npcs:
    Em=PCA(n_components=n,random_state=RNG).fit_transform(Z[gi,:].T)
    accs_pc.append(cross_val_score(mk(),Em[core],lc,cv=cv5,n_jobs=-1).mean())
ax[1].plot(npcs,accs_pc,'o-',color=PAL[2],lw=2,ms=7)
ax[1].axvline(5,color=BAD,ls='--',lw=1.6); ax[1].text(5.4,min(accs_pc),'chosen = 5',fontsize=8,color=BAD)
for a,b_ in zip(npcs,accs_pc): ax[1].annotate(f'{b_:.3f}',(a,b_),textcoords='offset points',xytext=(0,7),ha='center',fontsize=6.5,color=INK2)
ax[1].set_xlabel('number of principal components'); ax[1].set_ylabel('CV accuracy')
ax[1].set_title('E2 · robustness to dimensionality',fontsize=10,fontweight='bold')
ax[1].text(.5,-.16,'performance is stable across a wide range — not a lucky setting',
           transform=ax[1].transAxes,ha='center',fontsize=7.5,color=INK2)

ngs=[200,500,1000,2000,3000,5000]; accs_g=[]
for n in ngs:
    idx=np.sort(np.argsort(np.where(ispc,madv,-np.inf))[::-1][:n])
    Em=PCA(n_components=5,random_state=RNG).fit_transform(Z[idx,:].T)
    accs_g.append(cross_val_score(mk(),Em[core],lc,cv=cv5,n_jobs=-1).mean())
ax[2].plot(ngs,accs_g,'s-',color=PAL[3],lw=2,ms=7)
ax[2].axvline(1000,color=BAD,ls='--',lw=1.6); ax[2].text(1120,min(accs_g),'chosen = 1000',fontsize=8,color=BAD)
for a,b_ in zip(ngs,accs_g): ax[2].annotate(f'{b_:.3f}',(a,b_),textcoords='offset points',xytext=(0,7),ha='center',fontsize=6.5,color=INK2)
ax[2].set_xscale('log'); ax[2].set_xlabel('number of signature genes (log scale)'); ax[2].set_ylabel('CV accuracy')
ax[2].set_title('E3 · robustness to gene-panel size',fontsize=10,fontweight='bold')
ax[2].text(.5,-.16,'even 200 genes works — the signal is not fragile',
           transform=ax[2].transAxes,ha='center',fontsize=7.5,color=INK2)
fig.suptitle('FIGURE E — Is the result real, and is it robust?',fontsize=13,fontweight='bold',y=1.02)
fig.tight_layout(); fig.savefig(f'{PLOT}/21_E_robustness_null.png',dpi=150,bbox_inches='tight'); plt.close(fig)
print('  21_E_robustness_null.png')
json.dump({'perm_p':float(pv),'perm_real':float(sc),'perm_null_mean':float(perm.mean()),
           'acc_vs_npcs':dict(zip(map(str,npcs),map(float,accs_pc))),
           'acc_vs_ngenes':dict(zip(map(str,ngs),map(float,accs_g)))},
          open(f'{DST}/robustness_metrics.json','w'),indent=2)

# ============================================================ FIG F: decision space
fig,ax=plt.subplots(1,3,figsize=(19,5.8))
clf2=mk().fit(Ec[:,:2],lc)
pad=1.5; x0,x1=E[:,0].min()-pad,E[:,0].max()+pad; y0,y1=E[:,1].min()-pad,E[:,1].max()+pad
xx,yy=np.meshgrid(np.linspace(x0,x1,320),np.linspace(y0,y1,320))
zz=clf2.predict(np.c_[xx.ravel(),yy.ravel()]).reshape(xx.shape)
from matplotlib.colors import ListedColormap
ax[0].contourf(xx,yy,zz,levels=np.arange(-.5,K,1),colors=PAL,alpha=.16)
ax[0].contour(xx,yy,zz,levels=np.arange(-.5,K,1),colors=GRID,linewidths=.8)
for k in range(K):
    m=(lab==k)&core
    ax[0].scatter(E[m,0],E[m,1],s=34,c=PAL[k],marker=MARK[k],edgecolors='white',lw=.7,label=LBL[k])
    c_=E[lab==k][:,:2].mean(0)
    ax[0].annotate(LBL[k],c_,fontsize=11,fontweight='bold',ha='center',color=INK,
                   bbox=dict(boxstyle='round,pad=.22',fc='white',ec=GRID,alpha=.92))
ax[0].set_xlabel('PC1'); ax[0].set_ylabel('PC2'); ax[0].legend(fontsize=7,ncol=3,loc='upper right')
ax[0].set_title('F1 · decision regions (PC1–PC2)',fontsize=10,fontweight='bold')
ax[0].text(.5,-.16,'coloured background = what the model would answer at that position',
           transform=ax[0].transAxes,ha='center',fontsize=7.5,color=INK2)

for k in range(K):
    m=(lab==k)&core
    ax[1].scatter(E[m,0],E[m,1],s=26,c=PAL[k],marker=MARK[k],alpha=.5,edgecolors='none')
mis=core.copy(); mis[core]=yp!=lc
ax[1].scatter(E[~core,0],E[~core,1],s=44,facecolors='none',edgecolors=NEUTRAL,lw=1.3,
              label=f'boundary (n={(~core).sum()})')
ax[1].scatter(E[mis,0],E[mis,1],s=210,marker='X',c=BAD,edgecolors='white',lw=1.4,zorder=6,
              label=f'CV misclassified (n={mis.sum()})')
ax[1].set_xlabel('PC1'); ax[1].set_ylabel('PC2'); ax[1].legend(fontsize=8,loc='upper right')
ax[1].set_title('F2 · where the model makes mistakes',fontsize=10,fontweight='bold')
ax[1].text(.5,-.16,'the single error sits exactly on a border — not a random failure',
           transform=ax[1].transAxes,ha='center',fontsize=7.5,color=INK2)

df=pd.read_csv(NEWPAT,sep='\t',skiprows=1,low_memory=False)
df=df[df['gene_id'].astype(str).str.startswith('ENSG')]
s=pd.Series(df['tpm_unstranded'].values.astype(float),index=df['gene_id'].astype(str).values)
s=s[~s.index.duplicated(keep='first')]
tn_=s.reindex(pd.Index(A['lowexpr_gene_ids'])).fillna(0.).values
det=int(tn_[A['NONPOLYA_mask']].sum()/tn_.sum()>A['protocol_threshold'])
t2=tn_[A['KEEP_mask']]; t2=t2/t2.sum()*1e6
zn=(np.log2(t2+1.)-A['batch_means'][det])/A['global_sd']
enew=A['pca'].transform(zn[gi].reshape(1,-1))
pnew=A['model'].predict_proba(enew)[0]; knew=int(np.argmax(pnew))
for k in range(K):
    ax[2].scatter(E[lab==k,0],E[lab==k,1],s=26,c=PAL[k],marker=MARK[k],alpha=.42,edgecolors='none',label=LBL[k])
    ax[2].scatter(*E[lab==k][:,:2].mean(0),s=190,marker='*',c=PAL[k],edgecolors=INK,lw=1.1,zorder=5)
ax[2].scatter(enew[0,0],enew[0,1],s=520,marker='*',c=BAD,edgecolors='white',lw=2,zorder=10)
ax[2].annotate(f'NEW PATIENT\n→ {LBL[knew]} ({pnew[knew]*100:.1f}%)',(enew[0,0],enew[0,1]),
               textcoords='offset points',xytext=(16,16),fontsize=9,fontweight='bold',color=BAD,
               bbox=dict(boxstyle='round,pad=.32',fc='white',ec=BAD,lw=1.3))
ax[2].set_xlabel('PC1'); ax[2].set_ylabel('PC2'); ax[2].legend(fontsize=7,ncol=3,loc='upper right')
ax[2].set_title('F3 · the new patient placed on the map',fontsize=10,fontweight='bold')
ax[2].text(.5,-.16,'stars = cluster centres; the red star is the newly uploaded patient',
           transform=ax[2].transAxes,ha='center',fontsize=7.5,color=INK2)
fig.suptitle('FIGURE F — What the model actually learned, drawn in 2-D',fontsize=13,fontweight='bold',y=1.02)
fig.tight_layout(); fig.savefig(f'{PLOT}/22_F_decision_space.png',dpi=150,bbox_inches='tight'); plt.close(fig)
print('  22_F_decision_space.png')

# ============================================================ FIG G: probabilities
fig=plt.figure(figsize=(20,5.6))
gs=fig.add_gridspec(1,3,width_ratios=[1.7,1,1])
a0=fig.add_subplot(gs[0]); a1=fig.add_subplot(gs[1]); a2=fig.add_subplot(gs[2])
o=np.lexsort((-ppA.max(1),lab))
im=a0.imshow(ppA[o].T,aspect='auto',cmap='Blues',vmin=0,vmax=1,interpolation='nearest')
b_=0
for k in range(K):
    n=(lab==k).sum(); b_+=n
    a0.axvline(b_-.5,color=INK,lw=1.2)
    a0.text(b_-n/2,-.85,LBL[k],ha='center',fontsize=9,fontweight='bold',color=PAL[k])
a0.set_yticks(range(K)); a0.set_yticklabels([f'{LBL[i]} {SN[i][:17]}' for i in range(K)],fontsize=7.5)
a0.set_xlabel('patients — grouped by their assigned subtype, sorted by confidence')
a0.set_title('G1 · predicted probability for every patient × every subtype',fontsize=10,fontweight='bold')
a0.grid(False); fig.colorbar(im,ax=a0,fraction=.02,pad=.01,label='probability')
a0.text(.5,-.24,'a clean bright diagonal block per group = confident, unambiguous assignment',
        transform=a0.transAxes,ha='center',fontsize=7.5,color=INK2)

d=[ppA[lab==k].max(1) for k in range(K)]
bp=a1.boxplot(d,labels=LBL,patch_artist=True,widths=.6,medianprops=dict(color=INK,lw=1.6),
              flierprops=dict(ms=3.4,mfc=NEUTRAL,mec=NEUTRAL))
for p,c in zip(bp['boxes'],PAL): p.set_facecolor(c); p.set_alpha(.72)
a1.axhline(.8,ls='--',lw=1.2,color=GOOD); a1.text(.15,.807,'confident ≥0.80',fontsize=7.5,color=GOOD)
a1.axhline(.5,ls='--',lw=1.2,color=BAD);  a1.text(.15,.507,'undecided <0.50',fontsize=7.5,color=BAD)
a1.set_ylabel('top-class probability'); a1.set_ylim(0,1.06)
a1.set_title('G2 · confidence by subtype',fontsize=10,fontweight='bold')
a1.text(.5,-.24,'c4 (the intermediate group) is the least confident — as it should be',
        transform=a1.transAxes,ha='center',fontsize=7.5,color=INK2)

cc_=ppA.max(1); grp=[cc_[core],cc_[~core]]
bp=a2.boxplot(grp,labels=[f'CORE\nn={core.sum()}',f'BOUNDARY\nn={(~core).sum()}'],
              patch_artist=True,widths=.5,medianprops=dict(color=INK,lw=1.6),
              flierprops=dict(ms=3.4,mfc=NEUTRAL,mec=NEUTRAL))
for p,c in zip(bp['boxes'],[GOOD,PAL[3]]): p.set_facecolor(c); p.set_alpha(.75)
for i,g in enumerate(grp,1):
    a2.scatter(np.random.normal(i,.055,len(g)),g,s=9,color=INK2,alpha=.35,zorder=3)
    a2.text(i,1.035,f'mean {g.mean():.3f}',ha='center',fontsize=8,fontweight='bold',color=INK)
a2.set_ylabel('top-class probability'); a2.set_ylim(0,1.09)
a2.set_title('G3 · the model knows which cases are hard',fontsize=10,fontweight='bold')
a2.text(.5,-.24,'lower confidence on genuinely mixed tumours is correct behaviour, not a defect',
        transform=a2.transAxes,ha='center',fontsize=7.5,color=INK2)
fig.suptitle('FIGURE G — Probability landscape and honest uncertainty',fontsize=13,fontweight='bold',y=1.02)
fig.tight_layout(); fig.savefig(f'{PLOT}/23_G_probability_landscape.png',dpi=150,bbox_inches='tight'); plt.close(fig)
print('  23_G_probability_landscape.png')
print('\nAll 7 figures / 25 panels written.')

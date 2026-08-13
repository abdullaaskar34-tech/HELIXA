#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
GBM SUBTYPE PREDICTOR  —  تصنيف مريض جديد إلى أحد الأنماط الفرعية الستة
================================================================================

الاستخدام / USAGE:

    python3 predict_new_patient.py  <patient_file.tsv>
    python3 predict_new_patient.py  <folder_with_many_tsv_files>/
    python3 predict_new_patient.py  file1.tsv file2.tsv file3.tsv

الملف المُدخل يجب أن يكون بنفس صيغة ملفات GDC الخام:
    *.rna_seq.augmented_star_gene_counts.tsv
(نفس الملفات الموجودة في rawdata/ — لا حاجة لأي معالجة مسبقة إطلاقاً)

المخرجات:
    • طباعة على الشاشة: النمط المتوقّع + درجة الثقة + احتمال كل نمط
    • ملف prediction_results.csv فيه كل النتائج

المتطلبات:  numpy, pandas, scikit-learn, joblib
================================================================================
"""
import sys, os, glob, json
import numpy as np
import pandas as pd
import joblib

HERE = os.path.dirname(os.path.abspath(__file__))
ART  = os.path.join(HERE, 'model_artifacts.joblib')

CONF_HIGH = 0.80     # فوقها: تصنيف واثق
CONF_LOW  = 0.50     # تحتها: ورم بينيّ/غير محسوم

DESC = {
 0: 'ميتوكوندري / OXPHOS — يطابق نمط MTC المنشور (Nature Cancer 2021).\n'
    '     ★ أفضل إنذار، وحسّاس انتقائياً لمثبّطات OXPHOS (فئة دوائية موجودة فعلاً).',
 1: 'Proneural / سلائف عصبية — 96% من مرضى هذه المجموعة يطابقون توقيع Verhaak Proneural.\n'
    '     جينات مميزة: NKAIN1, DCX, ATCAY, SCN3A.',
 2: 'Classical — محور EGFR / RTK-MAPK. جينات مميزة: EGFR, SPRY1/2/4, SPRED2, MEOX2.',
 3: 'Mesenchymal — 98% نقاء، ارتشاح مناعي كثيف (بلاعم/ميكروغليا).\n'
    '     جينات مميزة: CD14, CD163, FCGR2A/B, C1R, C1S.',
 4: 'انتقالي / مختلط — لا يوجد توقيع مسيطر. يُفسَّر كحالة بينية وليس نمطاً مستقلاً.',
 5: 'قليل التغصّن / مايلين مرتفع مع مكوّن عصبي.\n'
    '     جينات مميزة: MBP, PLP1, MAG, MOG, CNP, MYRF.',
}


def load_tsv(path):
    """قراءة ملف GDC خام واستخراج عمود tpm_unstranded مرتّباً حسب gene_id."""
    df = pd.read_csv(path, sep='\t', skiprows=1, low_memory=False)
    df = df[df['gene_id'].astype(str).str.startswith('ENSG')].reset_index(drop=True)
    if 'tpm_unstranded' not in df.columns:
        raise ValueError(f"{path}: العمود tpm_unstranded غير موجود — هل هذا ملف GDC صحيح؟")
    return df


def predict_one(path, A):
    df = load_tsv(path)

    # --- محاذاة الجينات مع فضاء التدريب (بالـ gene_id، وليس بالاسم) -----------
    want = pd.Index(A['lowexpr_gene_ids'])
    have = pd.Index(df['gene_id'].astype(str).values)
    s = pd.Series(df['tpm_unstranded'].values.astype(np.float64), index=have)
    s = s[~s.index.duplicated(keep='first')]
    tpm = s.reindex(want).fillna(0.0).values
    matched = int(want.isin(have).sum())

    # --- 1) كشف بروتوكول تحضير المكتبة تلقائياً -------------------------------
    frac_nonpolya = tpm[A['NONPOLYA_mask']].sum() / max(tpm.sum(), 1e-9)
    detected = int(frac_nonpolya > A['protocol_threshold'])
    proto = 'total-RNA / rRNA-depleted' if detected else 'poly(A)-selected'
    ambiguous = abs(frac_nonpolya - A['protocol_threshold']) < 0.03

    # --- 2..5) الفلترة + إعادة التطبيع + اللوغاريتم ---------------------------
    t = tpm[A['KEEP_mask']]
    t = t / max(t.sum(), 1e-9) * 1e6
    y = np.log2(t + 1.0)

    # --- 6) التصحيح بإحصاءات التدريب المجمّدة (لا تُعاد تقديرها أبداً) --------
    z = (y - A['batch_means'][detected]) / A['global_sd']

    # --- 7) الجينات التوقيعية + الإسقاط على PCA المحفوظ -----------------------
    emb = A['pca'].transform(z[A['signature_gene_idx']].reshape(1, -1))

    # --- 8) التنبؤ -------------------------------------------------------------
    proba = A['model'].predict_proba(emb)[0]
    pred = int(np.argmax(proba))
    conf = float(proba[pred])
    flag = ('واثق' if conf >= CONF_HIGH else
            'متوسط' if conf >= CONF_LOW else 'غير محسوم — ورم بينيّ')

    return {
        'file': os.path.basename(path),
        'predicted_cluster': pred,
        'predicted_name': A['cluster_names'][pred],
        'confidence': round(conf, 4),
        'confidence_flag': flag,
        'detected_protocol': proto,
        'nonpolyA_fraction': round(float(frac_nonpolya), 5),
        'protocol_ambiguous': ambiguous,
        'genes_matched': matched,
        'genes_expected': len(want),
        **{f'prob_cluster_{i}': round(float(proba[i]), 4) for i in range(A['K'])},
    }


def main(argv):
    if not os.path.exists(ART):
        sys.exit(f"خطأ: ملف النموذج غير موجود:\n  {ART}")
    A = joblib.load(ART)

    if len(argv) < 2:
        sys.exit(__doc__)

    files = []
    for a in argv[1:]:
        if os.path.isdir(a):
            files += sorted(glob.glob(os.path.join(a, '*.tsv')))
        else:
            files.append(a)
    if not files:
        sys.exit("لم يتم العثور على أي ملف .tsv")

    print("=" * 78)
    print("GBM SUBTYPE PREDICTOR")
    print(f"النموذج: {A['model_name']}   |   دقة التحقق المتقاطع: "
          f"{A['cv_accuracy']*100:.2f}%   |   ROC-AUC: {A['roc_auc_ovr']:.4f}")
    print("=" * 78)

    out = []
    for f in files:
        try:
            r = predict_one(f, A)
        except Exception as e:
            print(f"\n[فشل] {os.path.basename(f)}: {e}")
            continue
        out.append(r)
        print(f"\nالملف: {r['file']}")
        print(f"  الجينات المطابقة    : {r['genes_matched']:,} / {r['genes_expected']:,}")
        print(f"  البروتوكول المكتشف  : {r['detected_protocol']} "
              f"(نسبة non-polyA = {r['nonpolyA_fraction']:.4f})"
              + ("   ⚠️ قريب من الحد الفاصل" if r['protocol_ambiguous'] else ""))
        print(f"\n  >>> النمط المتوقّع : cluster_{r['predicted_cluster']} — {r['predicted_name']}")
        print(f"  >>> الثقة          : {r['confidence']*100:.1f} %  ({r['confidence_flag']})")
        print(f"\n  {DESC[r['predicted_cluster']]}")
        print("\n  احتمالات كل الأنماط:")
        for i in range(A['K']):
            p = r[f'prob_cluster_{i}']
            bar = '█' * int(round(p * 40))
            mark = ' <<<' if i == r['predicted_cluster'] else ''
            print(f"    cluster_{i} {A['cluster_names'][i]:<26} {p*100:5.1f}%  {bar}{mark}")
        if r['confidence'] < CONF_LOW:
            print("\n  ⚠️ ثقة منخفضة: هذا الورم يقع بين نمطين. هذا ليس خطأً في النموذج —")
            print("     نحو 17% من أورام GBM بينيّة فعلاً، والنموذج يُبلّغ عن ذلك بصدق")
            print("     بدل إعطاء تصنيف واثق زائف.")
        print("-" * 78)

    if out:
        d = pd.DataFrame(out)
        dest = os.path.join(os.getcwd(), 'prediction_results.csv')
        d.to_csv(dest, index=False)
        print(f"\nتم حفظ النتائج -> {dest}")
        if len(out) > 1:
            print("\nملخّص التوزيع:")
            print(d['predicted_name'].value_counts().to_string())


if __name__ == '__main__':
    main(sys.argv)

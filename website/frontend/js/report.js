/* HELIXA — printable Patient Molecular Report
   KBU-MedLab · Genomics into Decisions

   Builds a fully self-contained report document (classification result +
   the biomarker/drug-target panel for the predicted subtype) and opens it
   in a new browser tab. No server, no PDF library: the user prints it or
   saves it as a PDF with the browser's own print dialog (Ctrl/Cmd+P →
   "Save as PDF"), which is opened automatically.

   Every figure in the report is read directly from the same `result` object
   `js/engine.js` produced and the same `data/biomarkers.json` dataset the
   on-page biomarker card reads — nothing here is computed independently, so
   the report can never disagree with what the page already showed.        */

const esc = s => String(s ?? '').replace(/[&<>"']/g,
  c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const fmtPct = (v, d = 1) => (v == null || Number.isNaN(v)) ? '—' : (v * 100).toFixed(d) + '%';
const fmtNum = (v, d = 3) => (v == null || Number.isNaN(v)) ? '—' : Number(v).toFixed(d);

function tierClass(t) {
  if (!t) return 'tx';
  if (t.startsWith('TIER 1')) return 't1';
  if (t.startsWith('TIER 2')) return 't2';
  if (t.startsWith('TIER 3')) return 't3';
  return 'tx';
}
function tierName(t) {
  if (!t) return 'Excluded';
  if (t.startsWith('TIER 1')) return 'Tier 1 · Actionable';
  if (t.startsWith('TIER 2')) return 'Tier 2 · Credible';
  if (t.startsWith('TIER 3')) return 'Tier 3 · Hypothesis';
  return 'Excluded';
}

/**
 * @param {object} result   the object returned by engine.js `analyse()`
 * @param {object} cmap     cluster id -> cluster record (from data/clusters.json)
 * @param {object} bio      the parsed data/biomarkers.json dataset
 * @param {object} meta     { patientLabel, fileName, isDemo }
 */
export function openPatientReport(result, cmap, bio, meta = {}) {
  const c = cmap[result.predicted_class];
  const classKey = String(result.predicted_class);
  const genes = (bio?.by_class?.[classKey] || []).slice();
  const summary = bio?.summary_by_class?.[classKey] || {};
  const active = genes.filter(g => !g.excluded);
  const excluded = genes.filter(g => g.excluded);

  const now = new Date();
  const reportId = 'HLX-' + now.toISOString().replace(/[-:.]/g, '').replace('T', '-').slice(0, 15);
  const generatedAt = now.toLocaleString(undefined, {
    year: 'numeric', month: 'short', day: '2-digit',
    hour: '2-digit', minute: '2-digit' });

  const base = location.href.split('#')[0];

  const probRows = result.probabilities
    .map((p, i) => ({ i, p }))
    .sort((a, b) => b.p - a.p)
    .map(({ i, p }) => `
      <tr class="${i === result.predicted_class ? 'hi' : ''}">
        <td>${esc(cmap[i].label)}</td>
        <td>${esc(cmap[i].title)}</td>
        <td class="num">${fmtPct(p, 1)}</td>
        <td><div class="bar"><span style="width:${(p * 100).toFixed(1)}%;background:${cmap[i].color}"></span></div></td>
      </tr>`).join('');

  const topFor = (result.why?.top_genes_for || []).slice(0, 6).map(g => `
    <li><b class="mono">${esc(g.gene)}</b> — ${fmtPct(g.share_pct / 100, 1)} of the decision evidence
        (z = ${g.z > 0 ? '+' : ''}${g.z})</li>`).join('');

  const markerLine = result.marker_readout?.length
    ? `<p><b>${result.stages?.validate?.markers_elevated ?? '—'} of
        ${result.stages?.validate?.markers_checked ?? '—'}</b>
        (${result.stages?.validate?.agreement_pct ?? '—'}%) textbook marker genes for this subtype
        are elevated in this patient — an independent check that does not use the model at all.</p>`
    : '';

  const geneRow = g => `
    <tr class="${g.excluded ? 'excl' : ''}">
      <td class="num">${g.rank}</td>
      <td class="mono"><b>${esc(g.gene)}</b></td>
      <td><span class="tag ${tierClass(g.tier)}">${esc(tierName(g.tier))}</span></td>
      <td class="fn">${esc(g.protein_function || '—')}</td>
      <td>${esc(g.drug_status || '—')}</td>
      <td class="num">${g.final_score != null ? fmtNum(g.final_score, 3) : '—'}</td>
    </tr>
    ${g.excluded ? `<tr class="excl-reason"><td></td><td colspan="5"><i>Excluded — ${esc(g.wrong_direction || g.subtype_mismatch || 'biology contradicts the therapeutic direction')}</i></td></tr>` : ''}
  `;

  const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<base href="${esc(base)}">
<title>HELIXA Patient Report — ${esc(reportId)}</title>
<style>
  :root{
    --ink:#14201E; --ink-2:#4A6663; --line:#DCE6E4; --line-2:#C9D9D6;
    --teal-950:#062725; --teal-900:#0B3B39; --mint-500:#12B48F;
    --ok:#12855F; --warn:#B57200; --err:#C0392B; --surface-2:#F2F7F6;
  }
  *{box-sizing:border-box}
  body{font-family:-apple-system,'Inter',Segoe UI,Arial,sans-serif;color:var(--ink);
       margin:0;padding:0;background:#fff;-webkit-print-color-adjust:exact;print-color-adjust:exact}
  .page{max-width:880px;margin:0 auto;padding:34px 40px 60px}
  .hd{display:flex;align-items:center;justify-content:space-between;gap:16px;
      border-bottom:2px solid var(--teal-900);padding-bottom:16px;margin-bottom:22px}
  .hd img.logo{height:38px}
  .hd img.tek{height:30px;opacity:.9}
  .hd .meta{text-align:right;font-size:11.5px;color:var(--ink-2);line-height:1.55}
  h1{font-size:20px;margin:0 0 2px;letter-spacing:-.01em}
  .sub{font-size:12.5px;color:var(--ink-2);margin:0 0 22px}
  .disclaimer{background:#FDF1DC;border:1px solid #EBD6A8;color:#7A5300;
      border-radius:8px;padding:10px 14px;font-size:12px;line-height:1.55;margin-bottom:22px}
  .patient-box{display:grid;grid-template-columns:1fr 1fr;gap:0 24px;
      border:1px solid var(--line);border-radius:10px;padding:14px 18px;margin-bottom:24px;
      background:var(--surface-2)}
  .patient-box .kv{display:flex;justify-content:space-between;gap:10px;padding:5px 0;
      border-bottom:1px dashed var(--line-2);font-size:12.5px}
  .patient-box .kv:last-child,.patient-box .kv:nth-last-child(2){border-bottom:none}
  .patient-box .k{color:var(--ink-2)}
  .patient-box .v{font-weight:600;text-align:right}
  h2{font-size:14.5px;letter-spacing:.02em;margin:30px 0 4px;padding-top:14px;
     border-top:1px solid var(--line);color:var(--teal-900)}
  h2:first-of-type{border-top:none;padding-top:0;margin-top:0}
  .h-sub{font-size:11.5px;color:var(--ink-2);margin:0 0 12px}
  .headline{display:flex;align-items:center;gap:16px;background:var(--teal-950);color:#fff;
      border-radius:10px;padding:18px 22px;margin-bottom:8px}
  .headline .dot{width:14px;height:14px;border-radius:4px;flex-shrink:0}
  .headline .cls{font-size:24px;font-weight:750;letter-spacing:-.02em}
  .headline .sm{font-size:11.5px;color:rgba(255,255,255,.68);margin-top:3px}
  .headline .conf{margin-left:auto;text-align:right}
  .headline .conf b{font-size:26px;display:block}
  .headline .conf span{font-size:10.5px;color:rgba(255,255,255,.68);text-transform:uppercase;letter-spacing:.08em}
  table{width:100%;border-collapse:collapse;font-size:11.8px;margin-top:6px}
  thead th{background:var(--surface-2);text-align:left;padding:7px 9px;font-size:10px;
      text-transform:uppercase;letter-spacing:.04em;color:var(--ink-2);border-bottom:1.5px solid var(--line-2)}
  tbody td{padding:6.5px 9px;border-bottom:1px solid var(--line);vertical-align:top}
  tbody tr.hi{background:#E3F6EE;font-weight:650}
  tbody tr.excl td{color:var(--ink-2)}
  tbody tr.excl-reason td{padding-top:0;padding-bottom:8px;font-size:11px;color:var(--err)}
  td.num{text-align:right;font-variant-numeric:tabular-nums}
  td.fn{max-width:230px}
  .mono{font-family:'JetBrains Mono',ui-monospace,monospace}
  .bar{width:80px;height:7px;background:var(--line);border-radius:99px;overflow:hidden}
  .bar span{display:block;height:100%}
  .tag{display:inline-block;padding:2px 8px;border-radius:99px;font-size:10px;font-weight:650;white-space:nowrap}
  .tag.t1{background:#E3F6EE;color:var(--ok)}
  .tag.t2{background:#E2F2F0;color:#1E8C82}
  .tag.t3{background:#FDF1DC;color:var(--warn)}
  .tag.tx{background:#FBE9E7;color:var(--err)}
  .summary-strip{display:flex;gap:10px;margin:8px 0 14px;flex-wrap:wrap}
  .summary-strip .s{flex:1;min-width:110px;border:1px solid var(--line);border-radius:8px;
      padding:9px 12px;text-align:center}
  .summary-strip .s b{display:block;font-size:19px}
  .summary-strip .s span{font-size:10px;color:var(--ink-2);text-transform:uppercase;letter-spacing:.04em}
  .method{font-size:11.5px;color:var(--ink-2);line-height:1.65;background:var(--surface-2);
      border-radius:8px;padding:12px 14px;margin-bottom:10px}
  ul.evid{margin:6px 0 0;padding-left:18px;font-size:12px;line-height:1.7}
  .appendix{font-size:11.5px}
  .appendix .kv{display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px dashed var(--line)}
  .ft{margin-top:34px;padding-top:14px;border-top:1px solid var(--line);
      font-size:10.5px;color:var(--ink-2);display:flex;justify-content:space-between;gap:10px}
  .print-bar{position:sticky;top:0;background:#fff;border-bottom:1px solid var(--line);
      padding:10px 40px;display:flex;justify-content:flex-end;gap:8px;z-index:10}
  .print-bar button{background:var(--mint-500);color:#fff;border:none;border-radius:8px;
      padding:8px 16px;font-size:12.5px;font-weight:650;cursor:pointer}
  @media print{ .print-bar{display:none} .page{padding:0 6px} h2{break-inside:avoid} tr{break-inside:avoid} }
</style>
</head>
<body>
<div class="print-bar"><button onclick="window.print()">Print / Save as PDF</button></div>
<div class="page">

  <div class="hd">
    <img class="logo" src="./assets/logos/helixa-logo.png" alt="HELIXA">
    <div class="meta">
      Report ID ${esc(reportId)}<br>
      Generated ${esc(generatedAt)}
    </div>
  </div>

  <h1>Patient Molecular Report</h1>
  <p class="sub">Subtype classification and biomarker / drug-target panel · computed in the patient's browser, no data transmitted</p>

  <div class="disclaimer">
    <b>Research prototype — not a clinical diagnosis.</b> This report is generated by an
    unpublished, TEKNOFEST-competition research pipeline (KBU-MedLab). No external patient
    cohort has been tested, no clinical outcome has been linked to these subtypes, and the
    biomarker candidates listed below have not been validated in a laboratory. This document
    must not be used, alone or in part, to make a treatment decision.
  </div>

  <div class="patient-box">
    <div class="kv"><span class="k">Patient / sample label</span><span class="v">${esc(meta.patientLabel || '(not provided)')}</span></div>
    <div class="kv"><span class="k">Source file</span><span class="v">${esc(meta.fileName || (meta.isDemo ? 'recorded example run' : '—'))}</span></div>
    <div class="kv"><span class="k">Report ID</span><span class="v mono">${esc(reportId)}</span></div>
    <div class="kv"><span class="k">Generated</span><span class="v">${esc(generatedAt)}</span></div>
  </div>

  <h2>Classification result</h2>
  <div class="headline">
    <span class="dot" style="background:${c.color}"></span>
    <div>
      <div class="cls">${esc(c.title.replace(c.label + ' ', ''))}</div>
      <div class="sm">Subtype ${esc(c.label)} · ${esc(String(c.n_patients))} of 328 reference-cohort patients share it</div>
    </div>
    <div class="conf"><b>${fmtPct(result.confidence, 1)}</b><span>Subtype stability · ${esc(result.call || result.confidence_band)}</span></div>
  </div>
  <p style="font-size:12.5px;line-height:1.7;color:var(--ink-2)">${esc(result.summary)}</p>

  <table>
    <thead><tr><th>Subtype</th><th>Description</th><th>Probability</th><th></th></tr></thead>
    <tbody>${probRows}</tbody>
  </table>

  <h2>Why this subtype</h2>
  <p class="h-sub">The strongest genic evidence behind the classifier's decision — the model is linear, so each gene's exact contribution can be calculated directly, not estimated.</p>
  <ul class="evid">${topFor}</ul>
  ${markerLine}

  <h2>Biomarkers &amp; drug targets for ${esc(c.label)} — ${esc(c.title.replace(c.label + ' ', ''))}</h2>
  <p class="h-sub">From the HELIXA biomarker engine: genes that mark this subtype in real patients <i>and</i> that a glioblastoma cell line cannot survive without while normal tissue can, checked one at a time against the published literature.</p>
  <div class="summary-strip">
    <div class="s"><b>${summary.tier1_actionable ?? 0}</b><span>Tier 1 · Actionable</span></div>
    <div class="s"><b>${summary.tier2_credible ?? 0}</b><span>Tier 2 · Credible</span></div>
    <div class="s"><b>${summary.tier3_hypothesis ?? 0}</b><span>Tier 3 · Hypothesis</span></div>
    <div class="s"><b>${summary.excluded ?? 0}</b><span>Excluded</span></div>
  </div>
  ${genes.length ? `
  <table>
    <thead><tr><th>#</th><th>Gene</th><th>Tier</th><th>Function</th><th>Drug status</th><th>Score</th></tr></thead>
    <tbody>${genes.map(geneRow).join('')}</tbody>
  </table>
  <p style="font-size:10.5px;color:var(--ink-2);margin-top:8px">
    Candidates, not treatments. Two named drugs against targets that can appear on this list —
    cilengitide (ITGB5) and palbociclib (CDK6) — have already failed glioblastoma trials; that
    is recorded on their row when applicable.
  </p>` : `<p style="font-size:12.5px;color:var(--ink-2)">No literature-checked candidates are recorded for this subtype yet.</p>`}

  <h2>Technical appendix</h2>
  <div class="appendix">
    <div class="kv"><span>Library preparation detected</span><span><b>${esc(result.detected_protocol)}</b></span></div>
    <div class="kv"><span>Genes matched</span><span><b>${(result.genes_matched||0).toLocaleString()} of ${(result.genes_expected||0).toLocaleString()}</b></span></div>
    <div class="kv"><span>Model</span><span><b>${esc(result.model_name)}</b>${result.model_version ? ' · v' + esc(result.model_version) : ''} · trained on ${esc(String(result.n_train ?? 328))} patients</span></div>
    <div class="kv"><span>Leave-one-out agreement</span><span>${fmtPct(result.loo_agreement,2)} overall · ${fmtPct(result.loo_agreement_core,2)} core · ${fmtPct(result.loo_agreement_boundary,2)} boundary</span></div>
    <div class="kv"><span>Agreement with the consensus profile</span><span>r = ${fmtNum(result.oof_profile_corr,4)} out-of-sample</span></div>
    <div class="kv"><span>Margin to runner-up</span><span><b>${fmtNum(result.margin,4)}</b> · call ${esc(result.call || '—')} (threshold ${fmtNum(result.core_tau ?? 0.5,2)})</span></div>
    <div class="kv"><span>What the percentage means</span><span>${esc(result.probability_meaning || 'Subtype stability across resampled clusterings, not a clinical probability.')}</span></div>
    <div class="kv"><span>Position in 5-D embedding</span><span class="mono">${(result.embedding||[]).map(v=>v.toFixed(2)).join(', ')}</span></div>
    <div class="kv"><span>Where it ran</span><span>${result.ran_in === 'browser' ? 'This browser — frozen weights, no server' : 'Recorded from the reference run'}</span></div>
    <div class="kv"><span>Processing time</span><span>${esc(String(result.total_ms))} ms</span></div>
  </div>

  <div class="ft">
    <div>HELIXA — Genomics into Decisions · KBU-MedLab · TEKNOFEST Oncology 3T</div>
    <div>kbumedlab@gmail.com</div>
  </div>

</div>
</body>
</html>`;

  const w = window.open('', '_blank');
  if (!w) { alert('Please allow pop-ups for this site to view the patient report.'); return; }
  w.document.open();
  w.document.write(html);
  w.document.close();
}

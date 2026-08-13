#!/usr/bin/env bash
# ============================================================================
#  HELIXA — verify the deployed site
#  KBU-MedLab · Turning Genomics into Decisions
#
#      cd ~/Desktop/TEKNOFEST_ONCOLOGY/new_start/HELIXA
#      bash verify_deployment.sh
#
#  Checks every asset the live site needs and reports exactly what is broken.
# ============================================================================
set -uo pipefail

BASE="https://abdullaaskar34-tech.github.io/HELIXA"
c_g=$'\033[32m'; c_r=$'\033[31m'; c_y=$'\033[33m'; c_b=$'\033[1m'; c_0=$'\033[0m'
pass=0; fail=0

chk(){ # url, label
  local code
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 25 -L "$1")
  if [ "$code" = "200" ]; then
    printf "  ${c_g}✓${c_0} %-46s %s\n" "$2" "$code"; pass=$((pass+1))
  else
    printf "  ${c_r}✗${c_0} %-46s ${c_r}%s${c_0}\n" "$2" "$code"; fail=$((fail+1))
  fi
}

printf "\n${c_b}HELIXA — deployment verification${c_0}\n"
printf "%s\n" "$BASE"
printf "════════════════════════════════════════════════════════════\n"

printf "\n${c_b}1 · Core files${c_0}\n"
chk "$BASE/"                        "index.html"
chk "$BASE/css/helixa.css"          "stylesheet"
chk "$BASE/js/app.js"               "app router"
chk "$BASE/js/api.js"               "data layer"
chk "$BASE/js/charts.js"            "chart engine"
chk "$BASE/js/ui.js"                "ui helpers"

printf "\n${c_b}2 · Views (10)${c_0}\n"
for v in landing dashboard analyze patients patient pipeline analytics evaluation visualizations about; do
  chk "$BASE/js/views/$v.js" "view: $v"
done

printf "\n${c_b}3 · Branding${c_0}\n"
chk "$BASE/assets/logos/helixa-logo.png"        "HELIXA logo"
chk "$BASE/assets/logos/helixa-logo-white.png"  "HELIXA logo (white)"
chk "$BASE/assets/logos/teknofest-logo.png"     "TEKNOFEST logo"
chk "$BASE/assets/logos/favicon.png"            "favicon"

printf "\n${c_b}4 · Scientific data (15 datasets)${c_0}\n"
for d in project clusters patients global_metrics model confusion_matrix markers \
         biology external_validation k_selection sweep_summary batch_diagnosis \
         embedding plots pipeline; do
  chk "$BASE/data/$d.json" "data: $d.json"
done

printf "\n${c_b}5 · Figures (spot check)${c_0}\n"
for p in 01_pca_scatter 08_marker_gene_heatmap 17_A_confusion_matrices \
         21_E_robustness_null 22_F_decision_space E1_matching_heatmaps; do
  chk "$BASE/assets/plots/$p.png" "figure: $p.png"
done

printf "\n${c_b}6 · Content sanity${c_0}\n"
html=$(curl -s --max-time 25 -L "$BASE/")
for needle in "HELIXA" "Turning Genomics into Decisions" "KBU-MedLab" \
              "helixa-logo.png" "teknofest-logo.png" "kbumedlab@gmail.com"; do
  if printf '%s' "$html" | grep -qF "$needle"; then
    printf "  ${c_g}✓${c_0} %-46s present\n" "\"$needle\""; pass=$((pass+1))
  else
    printf "  ${c_r}✗${c_0} %-46s ${c_r}MISSING${c_0}\n" "\"$needle\""; fail=$((fail+1))
  fi
done

n=$(curl -s --max-time 25 -L "$BASE/data/clusters.json" | grep -o '"id"' | wc -l | tr -d ' ')
if [ "$n" = "6" ]; then
  printf "  ${c_g}✓${c_0} %-46s %s subtypes\n" "clusters.json parses" "$n"; pass=$((pass+1))
else
  printf "  ${c_r}✗${c_0} %-46s got %s, expected 6\n" "clusters.json parses" "$n"; fail=$((fail+1))
fi

np=$(curl -s --max-time 25 -L "$BASE/data/patients.json" | grep -o '"sample_id"' | wc -l | tr -d ' ')
if [ "$np" = "328" ]; then
  printf "  ${c_g}✓${c_0} %-46s %s patients\n" "patients.json parses" "$np"; pass=$((pass+1))
else
  printf "  ${c_r}✗${c_0} %-46s got %s, expected 328\n" "patients.json parses" "$np"; fail=$((fail+1))
fi

printf "\n════════════════════════════════════════════════════════════\n"
if [ "$fail" -eq 0 ]; then
  printf "${c_g}${c_b}  ALL %s CHECKS PASSED — the deployment is healthy.${c_0}\n\n" "$pass"
  printf "  Open it:  ${c_b}%s/${c_0}\n\n" "$BASE"
else
  printf "${c_r}${c_b}  %s passed, %s FAILED.${c_0}\n\n" "$pass" "$fail"
  printf "  If most things 404: the Pages build may still be running.\n"
  printf "  Check  https://github.com/abdullaaskar34-tech/HELIXA/actions\n"
  printf "  and re-run this script once the run is green.\n\n"
fi

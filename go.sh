#!/usr/bin/env bash
# ============================================================================
#  HELIXA — ship the in-browser model to GitHub Pages
#
#      bash go.sh
#
#  The classifier now runs inside the visitor's browser. There is no Python to
#  install and no server to start: the frozen weights (468 KB) are downloaded
#  once and the forward pass is reproduced in JavaScript, exactly.
# ============================================================================
set -uo pipefail

USER_NAME="abdullaaskar34-tech"
REPO="HELIXA"
g=$'\033[32m'; r=$'\033[31m'; y=$'\033[33m'; b=$'\033[1m'; z=$'\033[0m'

cd "$(dirname "$0")" || exit 1
printf "\n${b}HELIXA — deploy the in-browser model${z}\n"
printf "════════════════════════════════════════════════════════\n"
[ -d .git ] || { printf "${r}✗ This is not the HELIXA git folder.${z}\n"; exit 1; }

F=website/frontend
ok=1
for f in "$F/js/engine.js" "$F/model/manifest.json" "$F/js/views/analyze.js" \
         "$F/js/views/home.js" "$F/index.html"; do
  if [ -f "$f" ]; then printf "  ${g}✓${z} %s\n" "$f"
  else printf "  ${r}✗ missing %s${z}\n" "$f"; ok=0; fi
done
nbin=$(ls "$F"/model/*.bin 2>/dev/null | wc -l | tr -d ' ')
printf "  ${g}✓${z} %s weight files (%s)\n" "$nbin" "$(du -sh "$F/model" 2>/dev/null | cut -f1)"
[ "${nbin:-0}" -ge 10 ] || { printf "${r}✗ the model weights did not unzip properly${z}\n"; ok=0; }
[ "$ok" = 1 ] || { printf "\n${r}Stopping — unzip the update again.${z}\n\n"; exit 1; }

git add -A
if git diff --cached --quiet 2>/dev/null; then
  printf "  ${g}✓${z} already committed\n"
else
  git commit -q -m "Run the classifier in the browser — no Python, no server

The frozen model's forward pass is pure arithmetic, so the exact weights are
exported (468 KB) and the identical computation is reproduced in JavaScript.
Verified against the Python engine on four real patients: subtype,
probabilities, embedding, per-gene contributions and marker z-scores agree to
6e-8, with the 1,000-gene ranking in the identical order.

The analyze page now runs uploads locally, so the deployed site no longer asks
the visitor to install anything."
  printf "  ${g}✓${z} committed\n"
fi

printf "\n${b}Paste your GitHub token and press Enter${z}\n(the text stays hidden)\n> "
if [ -r /dev/tty ]; then IFS= read -rs TOKEN < /dev/tty; else IFS= read -rs TOKEN; fi
echo; echo
[ -n "${TOKEN:-}" ] || { printf "${r}✗ no token entered${z}\n"; exit 1; }

printf "  pushing…\n"
git remote set-url origin "https://${TOKEN}@github.com/$USER_NAME/$REPO.git"
if ! git push -q origin main 2>/tmp/hx.log; then
  git remote set-url origin "https://github.com/$USER_NAME/$REPO.git"
  T="$TOKEN"; unset TOKEN
  printf "${r}✗ push failed:${z}\n"; sed "s|$T|***|g" /tmp/hx.log | sed 's/^/    /' | head -8
  printf "\n  ${y}Most likely the token expired. Make a new one with\n"
  printf "  Contents: Read and write  +  Workflows: Read and write.${z}\n\n"
  rm -f /tmp/hx.log; exit 1
fi
git remote set-url origin "https://github.com/$USER_NAME/$REPO.git"
printf "  ${g}✓${z} pushed — the token is not stored anywhere\n"

API="https://api.github.com"
auth=(-H "Authorization: Bearer ${TOKEN}" -H "Accept: application/vnd.github+json")
printf "\n  watching the build"
concl=""
for i in $(seq 1 40); do
  sleep 15; printf "."
  j=$(curl -s "${auth[@]}" "$API/repos/$USER_NAME/$REPO/actions/runs?per_page=1")
  st=$(printf '%s' "$j" | sed -n 's/.*"status"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
  concl=$(printf '%s' "$j" | sed -n 's/.*"conclusion"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
  [ "$st" = "completed" ] && break
done
echo
unset TOKEN
if [ "$concl" = "success" ]; then printf "  ${g}✓ build succeeded${z}\n"
else printf "  ${y}! build finished as: %s — log: https://github.com/$USER_NAME/$REPO/actions${z}\n" "${concl:-unknown}"; fi

URL="https://$USER_NAME.github.io/$REPO"
printf "\n  checking that the model is being served"
for i in 1 2 3 4 5 6 7 8; do
  sleep 12; printf "."
  if curl -s --max-time 20 "$URL/model/manifest.json?probe=$RANDOM" | grep -q "n_signature"; then
    echo; printf "  ${g}✓ the model is live — the site classifies with no server${z}\n"
    printf "\n════════════════════════════════════════════════════════\n"
    printf "  ${b}%s/${z}\n" "$URL"
    printf "════════════════════════════════════════════════════════\n"
    printf "\n  Open it with Cmd+Shift+R the first time, go to\n"
    printf "  \"Analyze a Patient\", and drop any .augmented_star_gene_counts.tsv.\n\n"
    rm -f /tmp/hx.log; exit 0
  fi
done
echo
printf "  ${y}! not served yet — wait a minute, then reload %s/ with Cmd+Shift+R${z}\n\n" "$URL"
rm -f /tmp/hx.log

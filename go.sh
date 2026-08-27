#!/usr/bin/env bash
# ============================================================================
#  HELIXA — push the in-browser model to GitHub Pages
#      bash go.sh
#  Everything is already committed. This only pushes and then verifies that
#  the model is genuinely being served. It never touches the git index.
# ============================================================================
set -uo pipefail
USER_NAME="abdullaaskar34-tech"; REPO="HELIXA"
g=$'\033[32m'; r=$'\033[31m'; y=$'\033[33m'; b=$'\033[1m'; z=$'\033[0m'
cd "$(dirname "$0")" || exit 1

printf "\n${b}HELIXA — deploy the in-browser model${z}\n"
printf "════════════════════════════════════════════════════════\n"

rm -f .git/index.lock 2>/dev/null

n=$(git log --oneline origin/main..HEAD 2>/dev/null | wc -l | tr -d ' ')
if [ "${n:-0}" -eq 0 ]; then
  printf "  ${y}! nothing new to push — origin already has this commit${z}\n"
else
  printf "  ${g}✓${z} %s commit(s) to push:\n" "$n"
  git log --oneline origin/main..HEAD | sed 's/^/      /'
fi
printf "  ${g}✓${z} model payload: %s files, %s\n" \
  "$(ls website/frontend/model | wc -l | tr -d ' ')" \
  "$(du -sh website/frontend/model | cut -f1)"

printf "\n${b}Paste your GitHub token and press Enter${z}\n(the text stays hidden)\n> "
if [ -r /dev/tty ]; then IFS= read -rs TOKEN < /dev/tty; else IFS= read -rs TOKEN; fi
echo; echo
[ -n "${TOKEN:-}" ] || { printf "${r}✗ no token entered${z}\n\n"; exit 1; }

printf "  pushing…\n"
git remote set-url origin "https://${TOKEN}@github.com/$USER_NAME/$REPO.git"
if ! git push origin main 2>/tmp/hx.log; then
  git remote set-url origin "https://github.com/$USER_NAME/$REPO.git"
  T="$TOKEN"; unset TOKEN
  printf "${r}✗ push failed:${z}\n"; sed "s|$T|***|g" /tmp/hx.log | sed 's/^/    /' | head -10
  printf "\n  ${y}Most likely the token expired. Create a new one with\n"
  printf "  Contents: Read and write  +  Workflows: Read and write.${z}\n\n"
  rm -f /tmp/hx.log; exit 1
fi
git remote set-url origin "https://github.com/$USER_NAME/$REPO.git"
printf "  ${g}✓${z} pushed — the token is not stored anywhere\n"

API="https://api.github.com"
printf "\n  watching the build"
concl=""
for i in $(seq 1 40); do
  sleep 15; printf "."
  j=$(curl -s -H "Authorization: Bearer ${TOKEN}" -H "Accept: application/vnd.github+json" \
      "$API/repos/$USER_NAME/$REPO/actions/runs?per_page=1")
  st=$(printf '%s' "$j" | sed -n 's/.*"status"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
  concl=$(printf '%s' "$j" | sed -n 's/.*"conclusion"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
  [ "$st" = "completed" ] && break
done
echo; unset TOKEN
if [ "$concl" = "success" ]; then printf "  ${g}✓ build succeeded${z}\n"
else printf "  ${y}! build finished as: %s${z}\n    log: https://github.com/$USER_NAME/$REPO/actions\n" "${concl:-unknown}"; fi

URL="https://$USER_NAME.github.io/$REPO"
printf "\n  checking that the model is really being served"
for i in 1 2 3 4 5 6 7 8 9 10; do
  sleep 12; printf "."
  if curl -s --max-time 20 "$URL/model/manifest.json?probe=$RANDOM" | grep -q "n_signature"; then
    echo; printf "  ${g}✓ the model is live — the site classifies with no server${z}\n"
    printf "\n════════════════════════════════════════════════════════\n"
    printf "  ${b}%s/${z}\n" "$URL"
    printf "════════════════════════════════════════════════════════\n"
    printf "\n  Open it with Cmd+Shift+R, go to \"Analyze a Patient\",\n"
    printf "  and drop any .augmented_star_gene_counts.tsv file.\n\n"
    rm -f /tmp/hx.log; exit 0
  fi
done
echo
printf "  ${y}! not served yet — wait a minute, then reload %s/ with Cmd+Shift+R${z}\n\n" "$URL"
rm -f /tmp/hx.log

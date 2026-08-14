#!/usr/bin/env bash
# ============================================================================
#  HELIXA — push the current commit to GitHub
#      bash push.sh
# ============================================================================
set -uo pipefail

USER_NAME="abdullaaskar34-tech"
REPO="HELIXA"
g=$'\033[32m'; r=$'\033[31m'; y=$'\033[33m'; b=$'\033[1m'; z=$'\033[0m'

cd "$(dirname "$0")" || exit 1

printf "\n${b}HELIXA — push to GitHub${z}\n"
printf "════════════════════════════════════════════════════════\n"

[ -d .git ] || { printf "${r}✗ No git repository here.${z}\n"; exit 1; }

# restore anything accidentally deleted from the working tree
git checkout -- . 2>/dev/null || true

nv=$(ls website/frontend/js/views/ 2>/dev/null | wc -l | tr -d ' ')
nd=$(ls website/frontend/data/*.json 2>/dev/null | wc -l | tr -d ' ')
printf "  ${g}✓${z} %s view files, %s data files\n" "$nv" "$nd"
[ "$nv" -ge 2 ] || { printf "${r}✗ Views are missing — stopping.${z}\n"; exit 1; }

# commit anything still uncommitted
git add -A
if git diff --cached --quiet 2>/dev/null; then
  printf "  ${g}✓${z} nothing new to commit\n"
else
  git commit -q -m "Update HELIXA site"
  printf "  ${g}✓${z} committed pending changes\n"
fi

ahead=$(git log --oneline origin/main..HEAD 2>/dev/null | wc -l | tr -d ' ')
printf "  ${g}✓${z} %s commit(s) ready to push\n\n" "${ahead:-?}"

# ── ask for the token, reading straight from the terminal ───────────────────
printf "${b}Paste your GitHub token and press Enter${z}\n"
printf "(the text stays hidden while you type)\n"
printf "> "
if [ -r /dev/tty ]; then
  IFS= read -rs TOKEN < /dev/tty
else
  IFS= read -rs TOKEN
fi
echo; echo
[ -n "${TOKEN:-}" ] || { printf "${r}✗ No token entered.${z}\n"; exit 1; }

printf "  pushing…\n"
git remote set-url origin "https://${TOKEN}@github.com/$USER_NAME/$REPO.git"
if git push origin main 2>/tmp/hx_push.log; then
  git remote set-url origin "https://github.com/$USER_NAME/$REPO.git"
  unset TOKEN
  printf "\n  ${g}✓ pushed${z}\n"
  printf "  ${g}✓ token removed from git config${z}\n"
  printf "\n════════════════════════════════════════════════════════\n"
  printf "  Build   :  https://github.com/$USER_NAME/$REPO/actions\n"
  printf "  ${b}Site    :  https://$USER_NAME.github.io/$REPO/${z}\n"
  printf "════════════════════════════════════════════════════════\n"
  printf "\n  Give it 1–2 minutes, then open the site.\n\n"
else
  git remote set-url origin "https://github.com/$USER_NAME/$REPO.git"
  T="$TOKEN"; unset TOKEN
  printf "\n${r}✗ Push failed:${z}\n"
  sed "s|$T|***|g" /tmp/hx_push.log | sed 's/^/    /' | head -10
  printf "\n  ${y}Most likely: the token is expired, or missing\n"
  printf "  'Contents: Read and write' / 'Workflows: Read and write'.${z}\n\n"
  rm -f /tmp/hx_push.log
  exit 1
fi
rm -f /tmp/hx_push.log

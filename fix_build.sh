#!/usr/bin/env bash
# ============================================================================
#  HELIXA — repair the Pages workflow and redeploy
#
#      bash fix_build.sh
#
#  The previous workflow hard-coded the names of the ten original view files.
#  After the site was slimmed to two views that check could never pass, so the
#  build failed and the old site stayed live. This replaces it with a generic
#  check that does not care how many pages exist.
# ============================================================================
set -uo pipefail

USER_NAME="abdullaaskar34-tech"
REPO="HELIXA"
g=$'\033[32m'; r=$'\033[31m'; y=$'\033[33m'; b=$'\033[1m'; z=$'\033[0m'

cd "$(dirname "$0")" || exit 1
printf "\n${b}HELIXA — repair the build${z}\n"
printf "════════════════════════════════════════════════════════\n"
[ -d .git ] || { printf "${r}✗ no git repository here${z}\n"; exit 1; }

git checkout -- . 2>/dev/null || true

# ── write a workflow that adapts to whatever the site actually contains ─────
mkdir -p .github/workflows
cat > .github/workflows/deploy.yml <<'YAML'
name: Deploy HELIXA to GitHub Pages

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Verify the site payload
        run: |
          cd website/frontend
          missing=0
          echo "-- core files --"
          for f in index.html css/helixa.css js/app.js js/api.js js/charts.js js/ui.js; do
            if [ -f "$f" ]; then echo "  ok   $f"; else echo "  MISS $f"; missing=1; fi
          done
          echo "-- branding --"
          for f in assets/logos/helixa-logo.png assets/logos/teknofest-logo.png; do
            if [ -f "$f" ]; then echo "  ok   $f"; else echo "  MISS $f"; missing=1; fi
          done
          echo "-- pages --"
          nviews=$(ls js/views/*.js 2>/dev/null | wc -l)
          echo "  $nviews page module(s):"
          ls js/views/*.js 2>/dev/null | sed 's|^|    |'
          if [ "$nviews" -lt 1 ]; then echo "  no page modules found"; missing=1; fi
          echo "-- data --"
          ndata=$(ls data/*.json 2>/dev/null | wc -l)
          echo "  $ndata JSON dataset(s)"
          if [ "$ndata" -lt 1 ]; then echo "  no datasets found"; missing=1; fi
          if [ "$missing" -ne 0 ]; then echo "STOP: required files are missing."; exit 1; fi
          echo "Payload OK."

      - name: Setup Pages
        uses: actions/configure-pages@v5

      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: website/frontend

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
YAML
printf "  ${g}✓${z} workflow rewritten — no hard-coded page names\n"

nv=$(ls website/frontend/js/views/*.js 2>/dev/null | wc -l | tr -d ' ')
printf "  ${g}✓${z} site currently has %s page module(s): %s\n" "$nv" \
  "$(ls website/frontend/js/views/ 2>/dev/null | tr '\n' ' ')"

git add -A
if git diff --cached --quiet 2>/dev/null; then
  git commit -q --allow-empty -m "Re-trigger Pages build"
  printf "  ${g}✓${z} nothing changed — re-triggering the build\n"
else
  git commit -q -m "Fix Pages build: make the payload check independent of page names

The verify step listed the ten original view files by name. After the site was
reduced to two pages that check could never pass, so every build failed and the
previous site stayed deployed. It now checks the core files and simply requires
at least one page module and one dataset."
  printf "  ${g}✓${z} committed\n"
fi

printf "\n${b}Paste your GitHub token and press Enter${z}\n(the text stays hidden)\n> "
if [ -r /dev/tty ]; then IFS= read -rs TOKEN < /dev/tty; else IFS= read -rs TOKEN; fi
echo; echo
[ -n "${TOKEN:-}" ] || { printf "${r}✗ no token entered${z}\n"; exit 1; }

git remote set-url origin "https://${TOKEN}@github.com/$USER_NAME/$REPO.git"
if ! git push -q origin main 2>/tmp/hx.log; then
  git remote set-url origin "https://github.com/$USER_NAME/$REPO.git"
  T="$TOKEN"; unset TOKEN
  printf "${r}✗ push failed:${z}\n"; sed "s|$T|***|g" /tmp/hx.log | sed 's/^/    /' | head -8
  rm -f /tmp/hx.log; exit 1
fi
git remote set-url origin "https://github.com/$USER_NAME/$REPO.git"
printf "  ${g}✓${z} pushed\n"

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
if [ "$concl" = "success" ]; then
  printf "  ${g}✓ build succeeded${z}\n"
else
  printf "  ${y}! build finished as: %s${z}\n" "${concl:-unknown}"
  printf "    log: https://github.com/$USER_NAME/$REPO/actions\n"
fi

printf "\n  checking the live page"
URL="https://$USER_NAME.github.io/$REPO"
for i in 1 2 3 4 5 6 7 8; do
  sleep 12; printf "."
  if curl -s --max-time 20 "$URL/js/views/home.js?probe=$RANDOM" | head -c 60 | grep -q "HELIXA"; then
    echo; printf "  ${g}✓ the NEW site is live${z}\n"
    printf "\n════════════════════════════════════════════════════════\n"
    printf "  ${b}%s/${z}\n" "$URL"
    printf "════════════════════════════════════════════════════════\n"
    printf "\n  Open it with Cmd+Shift+R the first time.\n\n"
    rm -f /tmp/hx.log; exit 0
  fi
done
echo
printf "  ${y}! home.js is not being served yet — give it another minute,\n"
printf "    then reload %s/ with Cmd+Shift+R${z}\n\n" "$URL"
rm -f /tmp/hx.log

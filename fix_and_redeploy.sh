#!/usr/bin/env bash
# ============================================================================
#  HELIXA — fix the Pages workflow and redeploy
#
#      cd ~/Desktop/TEKNOFEST_ONCOLOGY/new_start/HELIXA
#      bash fix_and_redeploy.sh
# ============================================================================
set -uo pipefail

USER_NAME="abdullaaskar34-tech"
REPO="HELIXA"
c_g=$'\033[32m'; c_r=$'\033[31m'; c_y=$'\033[33m'; c_b=$'\033[1m'; c_0=$'\033[0m'
ok(){ printf "  ${c_g}✓${c_0} %s\n" "$1"; }
warn(){ printf "  ${c_y}!${c_0} %s\n" "$1"; }
die(){ printf "  ${c_r}✗ %s${c_0}\n" "$1"; exit 1; }
step(){ printf "\n${c_b}%s${c_0}\n" "$1"; }

printf "\n${c_b}HELIXA — fix workflow & redeploy${c_0}\n"
printf "════════════════════════════════════════════════════════════\n"

[ -d website/frontend ] || die "Run this from inside the HELIXA folder."
[ -d .git ] || die "No git repository here — run deploy_to_github.sh first."

step "1 · GitHub token"
printf "  Paste your token (hidden), then Enter:\n  > "
read -rs TOKEN; echo
[ -n "${TOKEN:-}" ] || die "No token entered."
API="https://api.github.com"
auth=(-H "Authorization: Bearer ${TOKEN}" -H "Accept: application/vnd.github+json" \
      -H "X-GitHub-Api-Version: 2022-11-28")

step "2 · Setting Pages source to GitHub Actions"
code=$(curl -s -o /tmp/hx_p.json -w '%{http_code}' -X POST "${auth[@]}" \
  "$API/repos/$USER_NAME/$REPO/pages" -d '{"build_type":"workflow"}')
if [ "$code" = "409" ]; then
  code=$(curl -s -o /tmp/hx_p.json -w '%{http_code}' -X PUT "${auth[@]}" \
    "$API/repos/$USER_NAME/$REPO/pages" -d '{"build_type":"workflow"}')
fi
case "$code" in
  200|201|204) ok "Pages source = GitHub Actions" ;;
  *) warn "Pages API returned HTTP $code"
     sed 's/^/    /' /tmp/hx_p.json 2>/dev/null | head -4
     warn "Set it by hand: Settings → Pages → Source = GitHub Actions" ;;
esac

step "3 · Writing the corrected workflow"
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
          echo "-- required files --"
          missing=0
          for f in index.html css/helixa.css js/app.js js/api.js js/charts.js js/ui.js \
                   assets/logos/helixa-logo.png assets/logos/teknofest-logo.png; do
            if [ -f "$f" ]; then echo "  ok   $f"; else echo "  MISS $f"; missing=1; fi
          done
          for v in landing dashboard analyze patients patient pipeline analytics \
                   evaluation visualizations about; do
            if [ -f "js/views/$v.js" ]; then echo "  ok   js/views/$v.js"; else echo "  MISS js/views/$v.js"; missing=1; fi
          done
          echo "-- payloads --"
          echo "  $(ls data/*.json 2>/dev/null | wc -l) JSON datasets"
          echo "  $(ls assets/plots/*.png 2>/dev/null | wc -l) scientific figures"
          if [ "$missing" -ne 0 ]; then echo "Required files are missing."; exit 1; fi
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
ok "workflow rewritten (build + deploy split, fragile syntax check removed)"

step "3b · Pushing"
git add -A
if git diff --cached --quiet 2>/dev/null; then
  ok "no file changes — will just re-trigger the build"
  git commit -q --allow-empty -m "Re-trigger Pages deployment"
else
  git commit -q -m "Fix GitHub Pages workflow: split build/deploy jobs, drop fragile syntax check

The previous verify step stripped whole 'export default ...' lines before
parsing, which made every view look like a syntax error and failed the build."
  ok "committed the fix"
fi

git remote set-url origin "https://${TOKEN}@github.com/$USER_NAME/$REPO.git"
if git push -q origin main 2>/tmp/hx_push.log; then
  ok "pushed"
else
  grep -v "$TOKEN" /tmp/hx_push.log | sed 's/^/    /' | head -6
  git remote set-url origin "https://github.com/$USER_NAME/$REPO.git"
  die "Push failed — check the token has Contents + Workflows write access."
fi
git remote set-url origin "https://github.com/$USER_NAME/$REPO.git"
ok "token removed from git config"

step "4 · Watching the build"
printf "  waiting for the Actions run"
URL="https://$USER_NAME.github.io/$REPO/"
for i in $(seq 1 40); do
  sleep 15; printf "."
  st=$(curl -s "${auth[@]}" "$API/repos/$USER_NAME/$REPO/actions/runs?per_page=1" \
       | sed -n 's/.*"status"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
  cc=$(curl -s "${auth[@]}" "$API/repos/$USER_NAME/$REPO/actions/runs?per_page=1" \
       | sed -n 's/.*"conclusion"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
  if [ "$st" = "completed" ]; then
    echo
    if [ "$cc" = "success" ]; then ok "build succeeded"; else
      printf "  ${c_r}✗ build concluded: %s${c_0}\n" "$cc"
      printf "  Open the log: https://github.com/$USER_NAME/$REPO/actions\n"
    fi
    break
  fi
done
echo

step "5 · Testing the live URL"
for i in 1 2 3 4 5 6; do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 -L "$URL")
  if [ "$code" = "200" ]; then ok "site is live (HTTP 200)"; break; fi
  printf "  HTTP %s — waiting for propagation…\n" "$code"; sleep 20
done

printf "\n════════════════════════════════════════════════════════════\n"
printf "  Live URL   :  ${c_b}%s${c_0}\n" "$URL"
printf "  Actions    :  https://github.com/%s/%s/actions\n" "$USER_NAME" "$REPO"
printf "════════════════════════════════════════════════════════════\n\n"
printf "  Next: bash verify_deployment.sh\n\n"

unset TOKEN
rm -f /tmp/hx_p.json /tmp/hx_push.log 2>/dev/null || true

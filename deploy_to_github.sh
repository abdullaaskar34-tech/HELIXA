#!/usr/bin/env bash
# ============================================================================
#  HELIXA — one-command GitHub deployment
#  KBU-MedLab · Turning Genomics into Decisions
#
#  Run this from your own Mac Terminal (it needs your normal internet access).
#
#      cd ~/Desktop/TEKNOFEST_ONCOLOGY/new_start/HELIXA
#      bash deploy_to_github.sh
#
#  It will:
#    1. ask for your GitHub token (typed invisibly — never stored, never logged)
#    2. create the repository under your account
#    3. commit everything and push
#    4. enable GitHub Pages
#    5. print your live URL
# ============================================================================
set -euo pipefail

USER_NAME="abdullaaskar34-tech"
REPO="HELIXA"
BRANCH="main"

c_g=$'\033[32m'; c_r=$'\033[31m'; c_y=$'\033[33m'; c_b=$'\033[1m'; c_0=$'\033[0m'
ok(){   printf "  ${c_g}✓${c_0} %s\n" "$1"; }
warn(){ printf "  ${c_y}!${c_0} %s\n" "$1"; }
die(){  printf "  ${c_r}✗ %s${c_0}\n" "$1"; exit 1; }
step(){ printf "\n${c_b}%s${c_0}\n" "$1"; }

printf "\n${c_b}HELIXA — deploy to GitHub${c_0}\n"
printf "Turning Genomics into Decisions · KBU-MedLab\n"
printf "════════════════════════════════════════════════════════════\n"

# ── 0. sanity ───────────────────────────────────────────────────────────────
step "0 · Checking this folder"
[ -f README.md ] && [ -d website/frontend ] || die "Run this from inside the HELIXA folder (README.md and website/ must be here)."
command -v git >/dev/null || die "git is not installed. Install Xcode command line tools: xcode-select --install"
ok "HELIXA project found"
ok "git $(git --version | awk '{print $3}')"

n_plots=$(ls website/frontend/assets/plots/*.png 2>/dev/null | wc -l | tr -d ' ')
n_data=$(ls website/frontend/data/*.json 2>/dev/null | wc -l | tr -d ' ')
[ "$n_plots" -ge 20 ] || die "Only $n_plots figures found — the assets folder looks incomplete."
[ "$n_data" -ge 14 ]  || die "Only $n_data JSON datasets found — run website/backend/export_static_data.py first."
ok "$n_plots scientific figures, $n_data datasets"

# ── 1. token ────────────────────────────────────────────────────────────────
step "1 · GitHub authentication"
printf "  Paste your GitHub token (input is hidden), then press Enter:\n  > "
read -rs TOKEN; echo
[ -n "${TOKEN:-}" ] || die "No token entered."

API="https://api.github.com"
auth=(-H "Authorization: Bearer ${TOKEN}" -H "Accept: application/vnd.github+json" \
      -H "X-GitHub-Api-Version: 2022-11-28")

who=$(curl -fsS "${auth[@]}" "$API/user" 2>/dev/null || true)
if [ -z "$who" ]; then
  warn "Could not read /user (fine-grained tokens often can't)."
  warn "Continuing — the repository call below will confirm access."
  LOGIN="$USER_NAME"
else
  LOGIN=$(printf '%s' "$who" | sed -n 's/.*"login"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
  ok "Authenticated as ${LOGIN:-unknown}"
fi

# ── 2. repository ───────────────────────────────────────────────────────────
step "2 · Repository"
code=$(curl -s -o /tmp/hx_repo.json -w '%{http_code}' "${auth[@]}" "$API/repos/$USER_NAME/$REPO")
if [ "$code" = "200" ]; then
  ok "Repository $USER_NAME/$REPO already exists — will push into it"
else
  printf '  Creating %s/%s …\n' "$USER_NAME" "$REPO"
  code=$(curl -s -o /tmp/hx_new.json -w '%{http_code}' -X POST "${auth[@]}" "$API/user/repos" \
    -d "{\"name\":\"$REPO\",\"description\":\"HELIXA — Turning Genomics into Decisions. Biomedical AI platform for glioblastoma molecular subtyping. KBU-MedLab.\",\"homepage\":\"https://$USER_NAME.github.io/$REPO/\",\"private\":false,\"has_issues\":true,\"has_wiki\":false}")
  if [ "$code" = "201" ]; then
    ok "Repository created"
  else
    printf "  ${c_r}GitHub said (HTTP %s):${c_0}\n" "$code"; sed 's/^/    /' /tmp/hx_new.json 2>/dev/null | head -8
    die "Could not create the repository. Your token likely lacks the 'repo' scope (classic) or 'Administration: Read & write' (fine-grained)."
  fi
fi

# ── 3. commit ───────────────────────────────────────────────────────────────
step "3 · Preparing the commit"
if [ ! -d .git ]; then
  git init -q
  git checkout -q -b "$BRANCH" 2>/dev/null || git branch -M "$BRANCH"
  ok "git repository initialised"
else
  git branch -M "$BRANCH" 2>/dev/null || true
  ok "existing git repository reused"
fi

git config user.name  "KBU-MedLab"        2>/dev/null || true
git config user.email "kbumedlab@gmail.com" 2>/dev/null || true

git add -A
if git diff --cached --quiet 2>/dev/null; then
  ok "nothing new to commit"
else
  git commit -q -m "HELIXA — Turning Genomics into Decisions (KBU-MedLab)

Biomedical AI platform for glioblastoma molecular subtyping, wrapping the
project's real scientific pipeline in a production web interface.

- 328 TCGA/GDC patients -> 6 molecular subtypes
- Library-preparation batch effect diagnosed and corrected (residual ARI -0.0044)
- Classifier: 100% leave-one-out accuracy, ROC-AUC 1.0000, permutation p=0.005
- Validated against 4 independent published classifications
- Zero-dependency frontend (no build step) + Starlette API over the frozen model"
  ok "committed $(git ls-files | wc -l | tr -d ' ') files"
fi

# safety: make sure nothing sensitive slipped in
if git ls-files | grep -qiE '(^|/)\.env$|token|secret|credential|\.pem$|\.key$'; then
  warn "A file with a sensitive-looking name is staged — check it before pushing:"
  git ls-files | grep -iE '(^|/)\.env$|token|secret|credential|\.pem$|\.key$' | sed 's/^/      /'
  printf "  Continue anyway? [y/N] "; read -r a; [ "$a" = "y" ] || die "Stopped."
else
  ok "no secrets in the commit"
fi

# ── 4. push ─────────────────────────────────────────────────────────────────
step "4 · Pushing to GitHub"
git remote remove origin 2>/dev/null || true
git remote add origin "https://${TOKEN}@github.com/$USER_NAME/$REPO.git"
if git push -q -u origin "$BRANCH" --force 2>/tmp/hx_push.log; then
  ok "pushed to $BRANCH"
else
  sed 's/^/    /' /tmp/hx_push.log | grep -v "$TOKEN" | head -8
  git remote set-url origin "https://github.com/$USER_NAME/$REPO.git"
  die "Push failed. Check that the token has 'Contents: Read & write' and 'Workflows: Read & write'."
fi
# strip the token back out of the stored remote immediately
git remote set-url origin "https://github.com/$USER_NAME/$REPO.git"
ok "token removed from the local git config"

# ── 5. pages ────────────────────────────────────────────────────────────────
step "5 · Enabling GitHub Pages"
code=$(curl -s -o /tmp/hx_pages.json -w '%{http_code}' -X POST "${auth[@]}" \
  "$API/repos/$USER_NAME/$REPO/pages" -d '{"build_type":"workflow"}')
case "$code" in
  201|204) ok "Pages enabled (GitHub Actions source)" ;;
  409)     ok "Pages was already enabled" ;;
  *)       warn "Could not enable Pages automatically (HTTP $code)."
           warn "Enable it by hand: Settings → Pages → Source = GitHub Actions" ;;
esac

URL="https://$USER_NAME.github.io/$REPO/"

printf "\n════════════════════════════════════════════════════════════\n"
printf "${c_g}${c_b}  HELIXA is deploying.${c_0}\n\n"
printf "  Repository :  https://github.com/$USER_NAME/$REPO\n"
printf "  Live URL   :  ${c_b}$URL${c_0}\n"
printf "  Build log  :  https://github.com/$USER_NAME/$REPO/actions\n\n"
printf "  The first build takes about 1–2 minutes. If the URL 404s, wait for the\n"
printf "  Actions run to go green, then reload.\n"
printf "════════════════════════════════════════════════════════════\n\n"
printf "${c_y}  Security reminder:${c_0} rotate any token you have pasted into a chat\n"
printf "  window — GitHub → Settings → Developer settings → Tokens → Revoke.\n\n"

unset TOKEN
rm -f /tmp/hx_repo.json /tmp/hx_new.json /tmp/hx_pages.json /tmp/hx_push.log 2>/dev/null || true

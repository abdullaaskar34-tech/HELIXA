#!/usr/bin/env bash
# ============================================================================
#  HELIXA — commit the v2 model and deploy it
#      bash push_v2.sh
#
#  This folder lives in iCloud Drive, so most files are placeholders that git
#  cannot read ("not a git repository"). Step 1 pulls them back down. Then it
#  commits everything and hands over to go.sh, which does the push and watches
#  the build.
# ============================================================================
set -uo pipefail
g=$'\033[32m'; r=$'\033[31m'; y=$'\033[33m'; b=$'\033[1m'; z=$'\033[0m'
cd "$(dirname "$0")" || exit 1

printf "\n${b}HELIXA — deploy the calibrated model (v2)${z}\n"
printf "════════════════════════════════════════════════════════\n\n"

# ── 1 · bring the folder back from iCloud ───────────────────────────────────
printf "  1. downloading from iCloud (about 20 MB)…\n"
if command -v brctl >/dev/null 2>&1; then
  brctl download . >/dev/null 2>&1
fi
find . -type f -exec cat {} + >/dev/null 2>&1
printf "     ${g}done${z}\n\n"

# ── 2 · is git alive again? ─────────────────────────────────────────────────
printf "  2. checking the repository…\n"
if ! git rev-parse --git-dir >/dev/null 2>&1; then
  printf "     ${r}git still cannot read this folder.${z}\n"
  printf "     Open Finder, right-click the HELIXA folder and choose\n"
  printf "     \"Download Now\", wait for the cloud icons to disappear,\n"
  printf "     then run this script again.\n\n"
  exit 1
fi
branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
printf "     ${g}ok${z} — on branch %s\n\n" "$branch"

# ── 3 · stage and show what changed ─────────────────────────────────────────
printf "  3. staging changes…\n"
rm -f .git/index.lock 2>/dev/null
git add -A
n=$(git diff --cached --name-only | wc -l | tr -d ' ')
if [ "${n:-0}" -eq 0 ]; then
  printf "     ${y}nothing new to commit — going straight to the push${z}\n\n"
else
  printf "     ${g}%s file(s) staged${z}\n" "$n"
  git diff --cached --stat | tail -12 | sed 's/^/       /'
  printf "\n"

  printf "  4. committing…\n"
  git commit -q -F - <<'MSG'
Replace the subtype classifier with a calibrated model (v2)

v1 was trained on the 273 CORE patients only, which are near-separable in
5-PC space, so the softmax saturated: median confidence 0.9993, with 178 of
328 patients reported at >=99.9%. v2 trains on all 328 patients against the
consensus profile -- the fraction of 1,000 resampled clusterings in which a
tumour co-clusters with each subtype. Median confidence is now 0.7370, with
one patient above 99.9%.

The reported percentage now means subtype stability, not diagnostic
probability. Leave-one-out agreement 97.87% (99.63% core, 89.09% boundary);
out-of-sample match to the consensus profile r=0.9656. Twelve model families
were compared out-of-fold and the linear model won, so the residual error is
irreducible with five principal components.

Also in this change:
- regenerated the five demo patients, which were all confident cases reading
  ~100% (1.0000, 1.0000, 0.9999, 1.0000, 0.9924); DEMO-5's source sample was
  missing and is replaced with an intermediate tumour
- rebuilt the confusion matrix over all 328 patients by leave-one-out rather
  than 5-fold CV over the 273 core, which had excluded every hard case
- corrected the hardcoded "100% leave-one-out accuracy" claims in the
  homepage and README
- the browser engine now returns Verhaak signature and pathway scores
- bumped the asset cache-busting versions so returning visitors do not keep
  the cached v1 JavaScript, data files and model weights

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_012XBrR7PQiSq1pthboXoAtu
MSG
  printf "     ${g}committed${z}\n\n"
fi

# ── 4 · hand over to the existing deploy script ─────────────────────────────
printf "════════════════════════════════════════════════════════\n"
printf "  handing over to go.sh — it will ask for your token\n"
printf "════════════════════════════════════════════════════════\n"
exec bash go.sh

#!/usr/bin/env bash
# ============================================================================
#  HELIXA — commit whatever has changed and deploy it
#
#      bash push_v2.sh                  # uses the built-in message below
#      bash push_v2.sh "your message"   # uses your own message
#
#  This folder lives in iCloud Drive, so most files are placeholders that git
#  cannot read ("not a git repository"). Step 1 pulls them back down. Then it
#  commits and hands over to go.sh, which does the push and watches the build.
# ============================================================================
set -uo pipefail
g=$'\033[32m'; r=$'\033[31m'; y=$'\033[33m'; b=$'\033[1m'; z=$'\033[0m'
cd "$(dirname "$0")" || exit 1

MSG="${1:-}"

printf "\n${b}HELIXA — commit and deploy${z}\n"
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
printf "     ${g}ok${z} — on branch %s\n\n" "$(git rev-parse --abbrev-ref HEAD 2>/dev/null)"

# ── 3 · stage and show what changed ─────────────────────────────────────────
printf "  3. staging changes…\n"
rm -f .git/index.lock 2>/dev/null
git add -A
n=$(git diff --cached --name-only | wc -l | tr -d ' ')
if [ "${n:-0}" -eq 0 ]; then
  printf "     ${y}nothing new to commit — going straight to the push${z}\n\n"
else
  printf "     ${g}%s file(s) staged${z}\n" "$n"
  git diff --cached --stat | tail -14 | sed 's/^/       /'
  printf "\n  4. committing…\n"

  if [ -n "$MSG" ]; then
    git commit -q -m "$MSG" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>" \
      -m "Claude-Session: https://claude.ai/code/session_012XBrR7PQiSq1pthboXoAtu"
  else
    git commit -q -F - <<'COMMITMSG'
Rebuild the biomarker panel on the Stage-3 candidate list

The panel was built from Stage 5's final_targets.csv alone — 61 genes — which
read as a filtered shortlist but was not one. Stage 4 is a human reading
literature for roughly ten genes per subtype, and Stage 5 drops any candidate
without a verdict, so the panel showed whichever genes somebody had time to look
up and hid 298 statistically-qualified candidates. For PN it showed 10 of 176.

It now starts from Stage 3's candidates_all.csv — every gene that passed both
statistical gates — and layers the other two tables on top:

  candidates_all.csv      Stage 3   the statistics, the base       359 genes
  literature_evidence.csv Stage 4   function, evidence, sources     62 genes
  final_targets.csv       Stage 5   drug status and tier            61 genes

Stages 4, 5 and 6 are no longer run as pipeline steps; only those two tables are
consumed, and nothing is recomputed, so the panel cannot drift from the engine.

Genes nobody has reviewed are labelled "Not yet reviewed" with a banner, and
carry search links rather than findings — a reviewing backlog is not a negative
result and the panel never lets one look like the other.

Column names were replaced with terms a clinician can read, each carrying its own
definition: survival_score became "tumour cannot survive without it",
therapeutic_window became "safety gap", dep_mean_nonCNS became "healthy cells
also need it". Each gene leads with a picture answering one question — can a drug
hit this without hurting the patient — as two bars and the gap between them.
281 curated source links, labelled by publisher, plus nine lookup links per gene.

Three bugs found while testing the page in a real browser:
- pandas .itertuples() returns plain floats, not np.float64, so an isinstance
  check against np.floating stringified every metric; the JSON validated and the
  panel died on .toFixed()
- rounding floats to 8 decimals turned every FDR below 1e-8 into 0.0, so the most
  significant genes displayed "statistical confidence 0.0e+0"
- report.js tierName() fell through to "Excluded" for any unrecognised tier, so
  every not-yet-reviewed gene would have printed as Excluded — the inverse of its
  meaning. The report also now caps at 30 genes; 176 rows is not a document.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_012XBrR7PQiSq1pthboXoAtu
COMMITMSG
  fi
  printf "     ${g}committed${z}\n\n"
fi

# ── 4 · hand over to the existing deploy script ─────────────────────────────
printf "════════════════════════════════════════════════════════\n"
printf "  handing over to go.sh — it will ask for your token\n"
printf "════════════════════════════════════════════════════════\n"
exec bash go.sh

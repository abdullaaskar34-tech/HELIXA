#!/usr/bin/env bash
# ============================================================================
#  HELIXA — pull the folder down from iCloud, fast.
#
#      bash hydrate.sh
#
#  push_v2.sh step 1 reads all 821 files one at a time; each file that iCloud
#  has evicted is its own round trip, so it crawls and looks frozen. This does
#  the same job with 12 downloads running at once, retries whatever did not
#  make it, and prints how many are left after every pass so you can see it
#  moving.
#
#  Run this first, then push_v2.sh sails through its step 1 in seconds.
# ============================================================================
set -uo pipefail
g=$'\033[32m'; r=$'\033[31m'; y=$'\033[33m'; b=$'\033[1m'; z=$'\033[0m'
cd "$(dirname "$0")" || exit 1

PAR=12          # how many files to fetch at once
MAX_PASSES=25   # give up after this many rounds

printf "\n${b}HELIXA — pulling the folder down from iCloud${z}\n"
printf "════════════════════════════════════════════════════════\n\n"

total=$(find . -type f 2>/dev/null | wc -l | tr -d ' ')
printf "  %s files in this folder\n\n" "$total"

# ── nudge iCloud first; harmless if brctl is unavailable ────────────────────
if command -v brctl >/dev/null 2>&1; then
  printf "  asking iCloud to send everything…\n"
  brctl download . >/dev/null 2>&1
  printf "     ${g}requested${z}\n\n"
fi

# ── which files can we not read yet? ────────────────────────────────────────
remaining() {
  find . -type f -print0 2>/dev/null \
    | xargs -0 -P "$PAR" -n 1 sh -c 'head -c 1 "$0" >/dev/null 2>&1 || printf "%s\n" "$0"' 2>/dev/null
}

pass=0
while : ; do
  pass=$((pass + 1))
  left=$(remaining)
  n=$(printf "%s" "$left" | grep -c . || true)

  if [ "${n:-0}" -eq 0 ]; then
    printf "  ${g}all %s files are down${z}\n\n" "$total"
    break
  fi

  if [ "$pass" -gt "$MAX_PASSES" ]; then
    printf "\n  ${r}%s file(s) would not come down after %s passes:${z}\n" "$n" "$MAX_PASSES"
    printf "%s\n" "$left" | head -20 | sed 's/^/       /'
    printf "\n  Open Finder, right-click the HELIXA folder, choose \"Download Now\",\n"
    printf "  wait for the cloud icons to clear, then run this again.\n\n"
    exit 1
  fi

  printf "  pass %-2s · %4s still to come down — fetching %s at a time…\n" "$pass" "$n" "$PAR"

  # reading a file is what tells iCloud to send it; do many at once
  printf "%s\n" "$left" | tr '\n' '\0' \
    | xargs -0 -P "$PAR" -n 1 sh -c 'cat "$0" >/dev/null 2>&1' 2>/dev/null

  sleep 1
done

# ── is git alive now? that is the whole point ───────────────────────────────
printf "  checking git…\n"
if git rev-parse --git-dir >/dev/null 2>&1; then
  printf "     ${g}ok${z} — on branch %s\n\n" "$(git rev-parse --abbrev-ref HEAD 2>/dev/null)"
  printf "════════════════════════════════════════════════════════\n"
  printf "  ready. now run:\n\n"
  printf "    ${b}bash push_v2.sh \"Remove the research-prototype disclaimer from the patient report\"${z}\n\n"
  printf "════════════════════════════════════════════════════════\n"
else
  printf "     ${y}git still cannot read the folder.${z}\n"
  printf "     %s\n\n" "$(git rev-parse --git-dir 2>&1 | head -1)"
  exit 1
fi

#!/usr/bin/env bash
# status_all.sh — aggregate git status across every repo in ~/GitHub/.
#
# Usage:
#   status_all.sh                 # all repos
#   status_all.sh --dirty-only    # only dirty repos
#   status_all.sh --perimeter quantos-core
#
# Compatible with macOS /bin/bash 3.2 (no mapfile).

set -u

GH="${HOME}/GitHub"
HUB="${GH}/.claude"
REGISTRY="${HUB}/registry/repos.yaml"

DIRTY_ONLY=0
PERIMETER=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dirty-only) DIRTY_ONLY=1; shift ;;
    --perimeter)  PERIMETER="$2"; shift 2 ;;
    -h|--help)
      sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

# Repo list — directories with a .git/ inside ~/GitHub/.
REPO_LIST=""
for d in "$GH"/*/; do
  d="${d%/}"
  name="$(basename "$d")"
  case "$name" in
    .*|__pycache__) continue ;;
  esac
  if [ -d "$d/.git" ]; then
    REPO_LIST="${REPO_LIST}${d}
"
  fi
done

# Optional perimeter filter: extract members from repos.yaml block-list
# (`quantos-core: [Shared, BacktestLab, ...]`).
if [ -n "$PERIMETER" ] && [ -f "$REGISTRY" ]; then
  MEMBERS_RAW="$(
    awk -v p="${PERIMETER}:" '
      $1 == p {
        line = $0
        sub(/^[^[]*\[/, "", line)
        sub(/\].*$/, "", line)
        gsub(/,/, " ", line)
        print line
        exit
      }
    ' "$REGISTRY"
  )"
  FILTERED=""
  for repo in $REPO_LIST; do
    name="$(basename "$repo")"
    for m in $MEMBERS_RAW; do
      if [ "$m" = "$name" ]; then
        FILTERED="${FILTERED}${repo}
"
      fi
    done
  done
  REPO_LIST="$FILTERED"
fi

TOTAL=0
DIRTY=0
AHEAD_TOTAL=0
BEHIND_TOTAL=0

printf "%-22s  %-12s  %-14s  %s\n" "REPO" "BRANCH" "STATE" "LAST COMMIT"
printf "%-22s  %-12s  %-14s  %s\n" "----" "------" "-----" "-----------"

for repo in $REPO_LIST; do
  TOTAL=$((TOTAL + 1))
  name="$(basename "$repo")"
  branch="$(git -C "$repo" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"
  porcelain="$(git -C "$repo" status --porcelain 2>/dev/null)"
  last="$(git -C "$repo" log -1 --format='%cs %s' 2>/dev/null | cut -c1-60)"

  state="clean"
  if [ -n "$porcelain" ]; then
    state="dirty"
    DIRTY=$((DIRTY + 1))
  fi

  ab="$(git -C "$repo" rev-list --left-right --count "@{u}...HEAD" 2>/dev/null || true)"
  if [ -n "$ab" ]; then
    behind="$(printf '%s' "$ab" | awk '{print $1}')"
    ahead="$(printf '%s' "$ab" | awk '{print $2}')"
    if [ "${ahead:-0}" -gt 0 ] 2>/dev/null; then
      state="${state}/+${ahead}"
      AHEAD_TOTAL=$((AHEAD_TOTAL + ahead))
    fi
    if [ "${behind:-0}" -gt 0 ] 2>/dev/null; then
      state="${state}/-${behind}"
      BEHIND_TOTAL=$((BEHIND_TOTAL + behind))
    fi
  fi

  if [ "$DIRTY_ONLY" -eq 1 ] && [ "$state" = "clean" ]; then
    continue
  fi

  printf "%-22s  %-12s  %-14s  %s\n" "$name" "$branch" "$state" "$last"
done

echo
echo "Summary: ${TOTAL} repos | ${DIRTY} dirty | ${AHEAD_TOTAL} ahead | ${BEHIND_TOTAL} behind"

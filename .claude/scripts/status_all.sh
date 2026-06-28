#!/usr/bin/env bash
# status_all.sh — aggregate git status across every repo in ~/GitHub/.
#
# Usage:
#   status_all.sh                 # all repos (human table)
#   status_all.sh --dirty-only    # only dirty repos
#   status_all.sh --perimeter quantos-core
#   status_all.sh --json          # machine-readable matrix (additive)
#
# Flags compose: --json --dirty-only --perimeter all work together.
# Compatible with macOS /bin/bash 3.2 (no mapfile). No jq dependency.

set -u

GH="${HOME}/GitHub"
HUB="${GH}/.claude"
REGISTRY="${HUB}/registry/repos.yaml"

DIRTY_ONLY=0
PERIMETER=""
JSON=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dirty-only) DIRTY_ONLY=1; shift ;;
    --perimeter)  PERIMETER="$2"; shift 2 ;;
    --json)       JSON=1; shift ;;
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

# Minimal JSON string escaper — backslash + double-quote are the only
# characters that can appear in our field set (git ref names forbid the
# rest; paths under ~/GitHub never carry control chars). No jq needed.
json_escape() {
  printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'
}

TOTAL=0
DIRTY=0
AHEAD_TOTAL=0
BEHIND_TOTAL=0

if [ "$JSON" -eq 1 ]; then
  printf '{\n'
  printf '  "generated_by": "status_all.sh",\n'
  printf '  "github_root": "%s",\n' "$(json_escape "$GH")"
  printf '  "filter": {"dirty_only": %s, "perimeter": %s},\n' \
    "$([ "$DIRTY_ONLY" -eq 1 ] && echo true || echo false)" \
    "$([ -n "$PERIMETER" ] && printf '"%s"' "$(json_escape "$PERIMETER")" || echo null)"
  printf '  "repos": [\n'
else
  printf "%-22s  %-12s  %-14s  %s\n" "REPO" "BRANCH" "STATE" "LAST COMMIT"
  printf "%-22s  %-12s  %-14s  %s\n" "----" "------" "-----" "-----------"
fi

FIRST=1

for repo in $REPO_LIST; do
  TOTAL=$((TOTAL + 1))
  name="$(basename "$repo")"
  branch="$(git -C "$repo" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"
  porcelain="$(git -C "$repo" status --porcelain 2>/dev/null)"
  last="$(git -C "$repo" log -1 --format='%cs %s' 2>/dev/null | cut -c1-60)"
  upstream="$(git -C "$repo" rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)"

  untracked=0
  dirty_bool=false
  state="clean"
  if [ -n "$porcelain" ]; then
    state="dirty"
    dirty_bool=true
    DIRTY=$((DIRTY + 1))
    untracked="$(printf '%s\n' "$porcelain" | grep -c '^??' 2>/dev/null || true)"
    untracked="${untracked:-0}"
  fi

  ahead=0
  behind=0
  ab="$(git -C "$repo" rev-list --left-right --count "@{u}...HEAD" 2>/dev/null || true)"
  if [ -n "$ab" ]; then
    behind="$(printf '%s' "$ab" | awk '{print $1}')"
    ahead="$(printf '%s' "$ab" | awk '{print $2}')"
    behind="${behind:-0}"
    ahead="${ahead:-0}"
    if [ "$ahead" -gt 0 ] 2>/dev/null; then
      state="${state}/+${ahead}"
      AHEAD_TOTAL=$((AHEAD_TOTAL + ahead))
    fi
    if [ "$behind" -gt 0 ] 2>/dev/null; then
      state="${state}/-${behind}"
      BEHIND_TOTAL=$((BEHIND_TOTAL + behind))
    fi
  fi

  if [ "$DIRTY_ONLY" -eq 1 ] && [ "$dirty_bool" = "false" ]; then
    continue
  fi

  if [ "$JSON" -eq 1 ]; then
    if [ -n "$upstream" ]; then
      upstream_json="\"$(json_escape "$upstream")\""
    else
      upstream_json="null"
    fi
    if [ "$FIRST" -eq 0 ]; then
      printf ',\n'
    fi
    FIRST=0
    printf '    {"name": "%s", "path": "%s", "branch": "%s", "upstream": %s, "dirty": %s, "untracked": %s, "ahead": %s, "behind": %s}' \
      "$(json_escape "$name")" \
      "$(json_escape "$repo")" \
      "$(json_escape "$branch")" \
      "$upstream_json" \
      "$dirty_bool" \
      "${untracked:-0}" \
      "${ahead:-0}" \
      "${behind:-0}"
  else
    printf "%-22s  %-12s  %-14s  %s\n" "$name" "$branch" "$state" "$last"
  fi
done

if [ "$JSON" -eq 1 ]; then
  if [ "$FIRST" -eq 0 ]; then
    printf '\n'
  fi
  printf '  ],\n'
  printf '  "summary": {"repos": %s, "dirty": %s, "ahead": %s, "behind": %s}\n' \
    "$TOTAL" "$DIRTY" "$AHEAD_TOTAL" "$BEHIND_TOTAL"
  printf '}\n'
else
  echo
  echo "Summary: ${TOTAL} repos | ${DIRTY} dirty | ${AHEAD_TOTAL} ahead | ${BEHIND_TOTAL} behind"
fi

#!/usr/bin/env bash
# grep_all.sh — ripgrep across every repo in ~/GitHub/ with sensible
# excludes and optional perimeter / repo filters.
#
# Usage:
#   grep_all.sh "<pattern>"
#   grep_all.sh "<pattern>" --perimeter quantos-core
#   grep_all.sh "<pattern>" --repo Shared --repo BacktestLab
#
# Compatible with macOS /bin/bash 3.2 (no mapfile).

set -u

if ! command -v rg >/dev/null 2>&1; then
  echo "ripgrep (rg) is required. brew install ripgrep" >&2
  exit 2
fi

GH="${HOME}/GitHub"
REGISTRY="${GH}/.claude/registry/repos.yaml"

PATTERN=""
PERIMETER=""
REPOS_FILTER=""
RG_EXTRA=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --perimeter) PERIMETER="$2"; shift 2 ;;
    --repo)      REPOS_FILTER="${REPOS_FILTER} $2"; shift 2 ;;
    --rg)        shift; RG_EXTRA="$*"; break ;;
    -h|--help)
      sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      if [ -z "$PATTERN" ]; then PATTERN="$1"; shift
      else RG_EXTRA="${RG_EXTRA} $1"; shift
      fi
      ;;
  esac
done

if [ -z "$PATTERN" ]; then
  echo "usage: grep_all.sh <pattern> [--perimeter <p>] [--repo <name> ...]" >&2
  exit 2
fi

# Enumerate repos with .git/.
REPO_LIST=""
for d in "$GH"/*/; do
  d="${d%/}"
  name="$(basename "$d")"
  case "$name" in .*) continue ;; esac
  if [ -d "$d/.git" ]; then
    REPO_LIST="${REPO_LIST}${d}
"
  fi
done

# Perimeter filter.
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

# --repo overrides perimeter.
if [ -n "$REPOS_FILTER" ]; then
  FILTERED=""
  for repo in $REPO_LIST; do
    name="$(basename "$repo")"
    for m in $REPOS_FILTER; do
      if [ "$m" = "$name" ]; then
        FILTERED="${FILTERED}${repo}
"
      fi
    done
  done
  REPO_LIST="$FILTERED"
fi

if [ -z "$REPO_LIST" ]; then
  echo "no matching repos." >&2
  exit 1
fi

# Standard excludes.
EXCLUDE_ARGS="--glob !**/.venv/** --glob !**/node_modules/** \
--glob !**/.mypy_cache/** --glob !**/.pytest_cache/** \
--glob !**/.import_linter_cache/** --glob !**/.ruff_cache/** \
--glob !**/.hypothesis/** --glob !**/outputs/** \
--glob !**/dist/** --glob !**/build/** \
--glob !**/.playwright-mcp/** --glob !**/.pyop2_cache/**"

TOTAL_HITS=0
N_REPOS=0
for repo in $REPO_LIST; do
  N_REPOS=$((N_REPOS + 1))
  name="$(basename "$repo")"
  # shellcheck disable=SC2086
  results="$(rg --no-heading --line-number --color never --max-count 50 \
              $EXCLUDE_ARGS $RG_EXTRA \
              -- "$PATTERN" "$repo" 2>/dev/null || true)"
  if [ -n "$results" ]; then
    count="$(printf '%s\n' "$results" | wc -l | tr -d ' ')"
    echo "── $name ($count hits) ──"
    printf '%s\n' "$results" | sed "s|^${repo}/||"
    echo
    TOTAL_HITS=$((TOTAL_HITS + count))
  fi
done

echo "Total: ${TOTAL_HITS} hits across ${N_REPOS} repos for /${PATTERN}/."

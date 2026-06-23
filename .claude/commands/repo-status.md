---
name: repo-status
description: Aggregate git status (branch, dirty/clean, ahead/behind, last commit) across every repo in the constellation. Accepts --dirty-only and --perimeter filters.
---

# /repo-status

Compact constellation-wide git status.

## Pipeline

1. Invoke the `multi-repo-status` skill.
2. The skill calls `scripts/status_all.sh` with any filters parsed from
   the arguments.

## Arguments

- `--dirty-only` — only show repos with uncommitted changes.
- `--perimeter <p>` — restrict to a perimeter (`quantos-core`,
  `quantos-info`, …).

## Aliases

`/status-all`, `/git-status-all`.

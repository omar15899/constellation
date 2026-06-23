---
name: find-in-repos
description: Search a pattern across every repo with optional perimeter / stack / repo filters. Backed by ripgrep, with the standard constellation excludes.
---

# /find-in-repos

Cross-repo ripgrep with ranked, perimeter-aware output.

## Usage

```
/find-in-repos <pattern> [--perimeter <p>] [--repo <name> ...] [--type <ext>]
```

## Pipeline

1. Invoke the `cross-repo-grep` skill.
2. The skill calls `scripts/grep_all.sh` with the supplied filters.

## Output

Grouped by repo, capped at ~200 lines unless `--full` is passed.

## Aliases

`/grep-all`, `/search-repos`.

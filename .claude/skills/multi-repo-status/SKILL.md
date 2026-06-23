---
name: multi-repo-status
description: Aggregate git status, current branch, ahead/behind, dirty tree, and last commit across every repo in the constellation. Trigger when the user says "status of all repos", "what's dirty", "constellation status", "estado de todos los repos", or invokes /repo-status.
---

# multi-repo-status

The fastest possible view onto "what's the state of all my work?".

## Output

Per-repo block:

```
Shared              [main, clean]       last: 2026-05-13 "wire substrate preflight"
BacktestLab         [main, 2 ahead]     last: 2026-05-12 "engine: rename KnownAt"
MonteCarloLab       [main, dirty]       last: 2026-05-12 "mc paths integrator"
                                        modified: 3, untracked: 1
...
```

End with a one-line summary: `16 repos | 1 dirty | 2 ahead | 0 behind`.

## Operating procedure

1. Read `registry/repos.yaml` to know the active repo set.
2. For each repo, in parallel:
   - `git -C <path> rev-parse --abbrev-ref HEAD`
   - `git -C <path> status --porcelain`
   - `git -C <path> rev-list --left-right --count @{u}...HEAD` (if upstream)
   - `git -C <path> log -1 --format='%cs %s'`
3. Render the table above. Sort by perimeter (`quantos-core` first,
   then `quantos-info`, `quantos-alloc`, `quantos-prod`, `quantos-ui`,
   `adjacent`).
4. Emit the summary.

## Bundled script

`scripts/status_all.sh`:

```bash
bash ~/GitHub/.claude/scripts/status_all.sh
```

Supports `--perimeter <p>` and `--dirty-only` filters.

## Invariants

- Never mutates a repo. Pure git read commands.
- Times out per-repo at 5 seconds; reports `timeout` instead of
  blocking.
- Output sized for terminal: capped at one line per repo plus a
  modified/untracked counter when dirty.

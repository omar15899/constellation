---
name: cross-repo-grep
description: Search across every repository under ~/GitHub/ with optional perimeter / stack / repo filters and ranked output. Use when the user says "find X across repos", "grep all labs for Y", "busca Z en todos los repos", "where is X defined", or invokes /find-in-repos.
---

# cross-repo-grep

Wraps `agents/cross-repo-search.md` as a user-invocable skill.

## When to fire

- "Find <symbol> across repos."
- "Which lab defines <symbol>?"
- "Grep all labs for <string>."
- `/find-in-repos <query>`.

## Operating procedure

1. Parse the query and optional filters (`--perimeter`, `--stack`,
   `--repo`).
2. Compute the target set from `registry/repos.yaml`.
3. Shell out to:

   ```bash
   bash ~/GitHub/.claude/scripts/grep_all.sh "<query>" [--perimeter <p>] [--repo <name> ...]
   ```

4. The script runs `rg` in parallel with the standard exclude globs
   (`.venv`, `node_modules`, `outputs`, caches, `dist`, `build`).
5. Rank hits using the rules in
   [`agents/cross-repo-search.md`](../../agents/cross-repo-search.md):
   tier-proximity → canonical-files weight → recency.
6. Cap output at ~200 lines unless `--full` is passed.

## Output format

```
Query: "BLAKE3"
Filter: quantos-core (5 repos)

Shared/packages/quant_observability/audit.py:22:  HASH_ALGO = "BLAKE3"
BacktestLab/packages/quant_backtest/identity.py:48:  return blake3(...)
...

Hits: 14 across 6 files in 3 repos.
```

## Invariants

- Never reads inside excluded paths.
- Never reads `.env*` or files matching common secret patterns.
- Sorted, deduplicated, capped output.

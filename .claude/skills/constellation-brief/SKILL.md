---
name: constellation-brief
description: Generate a 1-page brief of the current state of ~/GitHub/ — every repo's perimeter, tier, status, last commit, dirty-or-clean, and any active drift. Trigger when the user says "constellation brief", "give me the state of GitHub", "snapshot of all repos", "resumen del constellation", or invokes /constellation.
---

# constellation-brief

The fast onboarding view. Designed to be readable in 30 seconds at the
start of any session.

## When to fire

- New session at `~/GitHub/`.
- "Give me the state of GitHub."
- `/constellation`.

## What it produces

A single markdown block with four sections:

```markdown
# Constellation Brief — 2026-05-15

## Counts
- 16 repos | 12 QuantOS | 3 adjacent | 1 UI
- 1 dirty | 2 ahead | 0 behind | 0 missing

## QuantOS state
| Tier | Repo            | Branch | State        | Last commit |
| ---- | --------------- | ------ | ------------ | ----------- |
| 0    | Shared          | main   | clean        | 2026-05-13  |
| 1    | BacktestLab     | main   | 2 ahead      | 2026-05-12  |
| 1    | MonteCarloLab   | main   | dirty (3,1)  | 2026-05-12  |
...

## Adjacent state
| Repo               | Branch | State | Last commit |
| ------------------ | ------ | ----- | ----------- |
| Scilux             | main   | clean | 2026-04-15  |
...

## Drift
- (none)  OR  - see docs/drift_report.md
```

## Operating procedure

1. Run `repo-discovery` (auto-refresh registry).
2. Run `multi-repo-status` (aggregate git state).
3. Run `perimeter-keeper` in summary mode (existence-of-drift only).
4. Render the four sections.
5. Cache the result for the session — second invocations within the
   same session reuse the cache unless explicitly refreshed.

## Invariants

- Pure read. No writes outside the cache file in
  `~/GitHub/.claude/.cache/` (gitignored anyway — this hub isn't a repo).
- Idempotent within a session.
- Falls back gracefully if any sub-skill fails — partial output is
  preferable to no output.

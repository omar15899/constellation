---
name: repos
description: Print the constellation repo index (the human-readable mirror of registry/repos.yaml). Refreshes the registry first if drift is detected.
---

# /repos

Show every repo under `~/GitHub/`, grouped by perimeter, with stack,
tier, status, and last commit.

## Pipeline

1. Run `repo-discovery` skill (refreshes registry if drift detected).
2. Render `REPOS.md` content to the user.
3. If drift was detected, append a short note pointing to
   `docs/drift_report.md` (if applicable).

## Aliases

`/constellation/repos`, `/labs`.

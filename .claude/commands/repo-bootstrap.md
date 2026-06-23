---
name: repo-bootstrap
description: Apply the standard constellation layout to an under-equipped repo. Dry-run by default; pass --apply to write.
---

# /repo-bootstrap

Bring a new or legacy repo up to the standard layout — `.claude/`,
CLAUDE.md template, peers.yaml seeded from the master registry, and
(for QuantOS variant) `.importlinter` + CI workflow.

## Usage

```
/repo-bootstrap <repo_path> [--variant quantos|adjacent] [--apply]
```

## Pipeline

1. Invoke the `repo-bootstrap` skill.
2. The skill calls `scripts/bootstrap_repo.sh`.
3. Without `--apply`: prints the planned actions and exits.
4. With `--apply`: creates missing directories, copies template files
   (never overwrites), seeds `peers.yaml`.

## Variants

- `adjacent` (default) — minimal `.claude/` layout, no QuantOS tier
  enforcement.
- `quantos` — full `.claude/` layout plus `.importlinter` and CI
  workflow.

## Invariants

- Never overwrites an existing file.
- Idempotent: a second run produces zero new actions if the first
  succeeded.
- Never commits inside the target repo.

## Aliases

`/bootstrap-repo`, `/wire-repo`.

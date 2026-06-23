---
name: repo-discovery
description: Scan ~/GitHub/ for new, removed, or renamed repositories and refresh registry/repos.yaml + REPOS.md. Trigger when the user says "rescan repos", "discover new repos", "refresh the constellation index", "actualiza el índice de repos", or after a fresh clone has landed in ~/GitHub/.
---

# repo-discovery

A focused skill that materialises the cartographer's pipeline as a
one-shot user-invocable operation.

## When to fire

- "Rescan ~/GitHub/", "refresh the constellation", "what's new on disk".
- After a `git clone` into `~/GitHub/`.
- Before invoking `multi-repo-orchestrator` on a session that has been
  idle for >24h.
- Implicitly fired as the first step of `/repos` and `/constellation`.

## Operating procedure

1. List `~/GitHub/` and identify git repos (directories containing
   `.git/`). Skip caches and `.claude/`.
2. Load `registry/repos.yaml`.
3. Compute three sets:
   - `added` (on disk, not in registry).
   - `removed` (in registry, missing on disk).
   - `renamed` (matched by `.git/config` remote URL despite path change).
4. For each `added`: dispatch the `repo-classifier` logic to draft a
   proposed YAML row.
5. Write the new registry atomically (preserve comments).
6. Render `REPOS.md` from the registry.
7. Report a short summary back to the user.

## Bundled script

`scripts/discover_repos.py` implements the full pipeline. The skill
shells out to it via:

```bash
python3 ~/GitHub/.claude/scripts/discover_repos.py --apply
```

Use `--dry-run` to preview the diff without writing.

## Invariants

- Never deletes a registry entry whose on-disk path is missing —
  marks it `missing` and asks.
- Never auto-assigns a QuantOS tier to an unknown repo. Adjacent by
  default; user confirms promotion.
- Idempotent: no on-disk changes ⇒ no registry writes.

---
name: repo-bootstrap
description: Apply the standard QuantOS (or adjacent) repo layout to an under-equipped repository — .claude/ scaffolding, CLAUDE.md template, .importlinter contract, CI workflows, hooks, peers.yaml. Trigger when the user says "bootstrap this repo", "give it the standard layout", "wire X into the constellation", "monta el setup AI en este repo", or invokes /repo-bootstrap.
---

# repo-bootstrap

The skill that brings a new (or legacy) repo up to the standard
constellation layout.

## When to fire

- A repo has just been classified (`adjacent` or `quantos-*`) and lacks
  a `.claude/` directory.
- A repo's `.claude/` is partial — missing hooks, peers, or registry.
- The user explicitly says "wire this repo into the constellation".

## Two variants

| Variant      | Target perimeter           | What it installs                                                                                                  |
| ------------ | -------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `quantos`    | any `quantos-*` perimeter  | Full layout: `.claude/{agents,commands,hooks,registry,skills,tests}`, `.importlinter`, CI workflows, peers.yaml.   |
| `adjacent`   | `adjacent` perimeter       | Minimal layout: `.claude/{agents,commands,hooks,registry}`, no import-linter, no QuantOS tier contracts.           |

The variant is chosen from `registry/repos.yaml`. If the repo is not
yet in the registry, the skill calls `repo-classifier` first.

## Operating procedure

1. Confirm the perimeter (read `repos.yaml` or classify).
2. Confirm the variant.
3. **Dry-run**: list every file that would be created. Show the user.
   Never overwrite an existing file silently.
4. On user confirmation, copy from `templates/`:
   - `templates/CLAUDE.md.template` → `<repo>/CLAUDE.md` (only if absent).
   - `templates/new_repo_layout.md` informs the structure.
   - For `quantos`: also copy the standard `.importlinter` template
     and the standard `.github/workflows/lint.yml`.
   - For `adjacent`: skip Python-specific bits.
5. Run `bash ~/GitHub/.claude/templates/claude_subagent_link.sh <repo>` to
   wire shared agents/skills into the new `.claude/`.
6. Update `registry/repos.yaml`:
   - Flip `claude_dir` to `.claude`.
   - Update `status` if appropriate.
7. Drop a `peers.yaml` derived from the master registry.

## Invariants

- **Never overwrites** an existing file. Always dry-run first.
- Never commits inside the target repo. The user commits.
- Never installs hooks into a repo unless the user explicitly authorises
  the hook in question.
- Idempotent: a second run on the same repo emits zero diffs.

## Bundled script

`scripts/bootstrap_repo.sh` is the underlying engine. Usage:

```bash
bash ~/GitHub/.claude/scripts/bootstrap_repo.sh <repo_path> [--variant quantos|adjacent] [--apply]
```

Without `--apply`, the script prints the planned actions.

---
name: repo-bootstrap
description: Scaffold a requested repository with the constellation Claude layout, preserving existing files. Use for bootstrap this repo or install the standard setup; choose minimal adjacent or QuantOS templates from its actual contracts.
---

# Bootstrap a repository

Read the target's existing AGENTS.md and CLAUDE.md, resolve its identity and
registry classification, and choose `quantos` or `adjacent` from that evidence.
Use `repo-discovery` for unresolved classification. Do not impose QuantOS on
an independent project. A bootstrap request authorizes the requested scaffolding.

Preview before applying, from the hub:

```bash
bash .claude/scripts/bootstrap_repo.sh <repo_path> --variant adjacent
bash .claude/scripts/bootstrap_repo.sh <repo_path> --variant adjacent --apply
```

Use `quantos` only for a QuantOS target. Inspect the plan; existing files must
be preserved. The helper creates missing Claude directories, the root contract
and a `peers.yaml.snapshot`; QuantOS adds import-linter and CI templates.
These are starter templates, not proof of configured checks or native hooks.

Resolve placeholders and adapt package paths, tier constraints and checks to
the actual repo before declaring setup complete. Validate syntax, references,
relevant checks and the final diff; report incomplete integration explicitly.
Only wire shared surfaces or generate Codex when the request covers them. Never
modify global trust or assume another repo's approval. No commits are implied.

---
name: repo-discovery
description: Discover new or missing repositories, classify an unknown project, or audit and repair registry metadata. Use for rescan repos, classify this repo, refresh the index or perimeter metadata drift.
---

# Discover and classify repositories

Read the [registry](../../registry/repos.yaml) and relevant
[perimeters](../../policies/perimeter_doctrine.md). Use
`constellation-cartographer` for classification or metadata work with a separate
context; follow its [procedure](../../agents/constellation-cartographer.md)
directly for a small inspection.

From the hub, run the read-only comparison:

```bash
python3 .claude/scripts/discover_repos.py --json
python3 .claude/scripts/discover_repos.py --state
```

There is no `--dry-run` flag. The reserved `--apply` does not update anything.
A classification request produces an evidence-backed proposal; an update request
authorizes unambiguous registry and index corrections. Do not ask again for
routine edits already covered by that request.

Resolve linked worktree identity with Git instead of counting every `.git` file
as a new repo. Never derive a QuantOS tier solely from an import or `.importlinter`
presence. Keep language stack values separate from tooling profiles. Unknown
ownership or architecture remains a proposal, not a silently chosen fact.

For updates, preserve unrelated work and keep `repos:`, perimeter memberships
and [REPOS.md](../../REPOS.md) consistent. Missing roots are findings, not an
instruction to delete rows. Run `python3 .claude/scripts/validate_repos.py` and
review the diff; that validator is not a complete schema/architecture audit.
No blanket peer sync, neighbor writes or recurring scans are implied.

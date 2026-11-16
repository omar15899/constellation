---
name: repo-discovery
description: Discover new or missing repositories, classify an unknown project, or audit and repair registry metadata. Use for rescan repos, classify this repo, refresh the index or perimeter metadata drift.
---

# Discover and classify repositories

Read the [project registry](../../../profiles/projects.json) and relevant
[perimeters](../../../README.md). Use
`ecosystem_researcher` for classification or metadata work with a separate
context; follow its [procedure](../../../README.md)
directly for a small inspection.

Compare direct child directories against the central registry. Confirm each Git
owner using `git -C PATH rev-parse --show-toplevel --git-common-dir`; count a
linked worktree as a checkout of its owner rather than inventing a new project.
A classification request produces an evidence-backed proposal; an update request
authorizes unambiguous registry and index corrections. Do not ask again for
routine edits already covered by that request.

Resolve linked worktree identity with Git instead of counting every `.git` file
as a new repo. Never derive a QuantOS tier solely from an import or `.importlinter`
presence. Keep language stack values separate from tooling profiles. Unknown
ownership or architecture remains a proposal, not a silently chosen fact.

For updates, preserve unrelated work and keep project records, perimeter memberships
and [project profiles](../../../profiles/projects.json) consistent. Missing roots are findings, not an
instruction to delete rows. Validate changed JSON, referenced roots and profiles, then review the diff;
syntax validation is not a complete architecture audit.
No blanket peer sync, neighbor writes or recurring scans are implied.

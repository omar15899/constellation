---
name: repo-status
description: Inspect repository git state or produce a constellation brief with inventory, perimeters and tiers. Use for what is dirty, status of all repos, repo index or a current constellation snapshot; never updates the registry.
---

# Repository status and constellation brief

Read the [project registry](../../../profiles/projects.json) for identity, tier and perimeter.
For filesystem drift, compare the selected registered roots with direct child
Git markers. Confirm owner/worktree identity with Git. Unknown directories are
findings, not implied enrollment. Include the hub separately when requested.

For selected roots, obtain branch, dirty/untracked state and upstream directly
with `git -C <path> status --short --branch` and the last commit with
`git -C <path> log -1`. Quote each path and batch independent reads. Use
`git rev-list --left-right --count '@{u}...HEAD'` for exact ahead/behind counts.
Filter dirty results after reading state, not by assuming a registry status.
For a deeper profile, inspect the referenced project profile and domain tests. A failed command is unknown, not clean.

Report upstream absence separately from zero ahead/behind; counts are relative
to local tracking refs and do not establish remote freshness. Do not fetch,
stash, checkout or clean as part of status.

For an inventory/brief, combine registry facts with current status and, when
filesystem drift matters, a read-only comparison of Git owners against the registry.
Compute the requested totals and summarize material drift; do not recycle cached
counts or automatically update metadata. Route requested repairs through
`repo-discovery`. A brief does not imply an import-graph audit. Include last
commit, branch and caveats only to the level useful for the question.

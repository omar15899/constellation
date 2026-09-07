---
name: repo-status
description: Inspect repository git state or produce a constellation brief with inventory, perimeters and tiers. Use for what is dirty, status of all repos, repo index or a current constellation snapshot; never updates the registry.
---

# Repository status and constellation brief

Read the [registry](../../registry/repos.yaml) for identity, tier and perimeter.
For a filesystem comparison and brief state snapshot, run from the hub:

```bash
python3 .claude/scripts/discover_repos.py --json --state
```

The helper enumerates visible child Git markers; its worktree labels are
heuristics to confirm with Git. Its counts are not a registry census: it omits
the hub and may include unknown or external roots. Select the requested roots
and perimeter from the registry; exclude external projects from governance.
Include the hub separately when requested.

For selected roots, obtain branch, dirty/untracked state and upstream directly
with `git -C <path> status --short --branch` and the last commit with
`git -C <path> log -1`. Quote each path and batch independent reads. Use
`git rev-list --left-right --count '@{u}...HEAD'` for exact ahead/behind counts.
Filter dirty results after reading state, not by assuming a registry status.
For a deeper repo profile use `repo-doctor`. A failed command is unknown, not clean.

Report upstream absence separately from zero ahead/behind; counts are relative
to local tracking refs and do not establish remote freshness. Do not fetch,
stash, checkout or clean as part of status.

For an inventory/brief, combine registry facts with current status and, when
filesystem drift matters, `python3 .claude/scripts/discover_repos.py --json`.
Compute the requested totals and summarize material drift; do not recycle cached
counts or automatically update metadata. Route requested repairs through
`repo-discovery`. A brief does not imply an import-graph audit. Include last
commit, branch and caveats only to the level useful for the question.

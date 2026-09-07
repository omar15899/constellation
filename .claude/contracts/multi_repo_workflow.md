# Multi-repository workflow

A multi-repository change affects separate git histories. Identify each affected
root, read its local contracts and inspect existing changes. State why each root
must change, then coordinate implementation through
[multi-repo-orchestrator](../agents/multi-repo-orchestrator.md). Providers precede
consumers; include fractional tiers and Tier 4 where applicable.

Run checks for the changed behavior in each repository and at affected boundaries.
Repair failures without bypassing gates. A dirty tree is not by itself a failed
result, and implementation does not imply authorization to commit or publish.

When commits are in scope, follow [commit policy](commit_policy.md),
[cross-repo rules](../policies/cross_repo_commits.md) and the target's
[policy entry](../registry/repo_commit_policy.yaml). Use
[commit-research](../commands/commit-research.md) with explicit repository and
scope selection. One commit belongs to one repository and logical change.
Push only under established authority and its branch/policy checks.

Report per-repository changes, executed validation and limitations. Include commit
hashes and push outcomes only when those actions were performed. Preserve task
state needed to resume interrupted work without copying transcripts or private logs.
No required ledger entry or fixed report matrix applies to every ordinary edit.

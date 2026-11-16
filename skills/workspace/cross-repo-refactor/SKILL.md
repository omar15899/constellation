---
name: cross-repo-refactor
description: Propagate a symbol, API or schema change across independent repositories in dependency order with per-repository validation. Use when a change has multiple repository consumers, not for a rename contained in one repo.
---

# Cross-repository refactor

Use [ecosystem_coder](../../../README.md) for the
cross-repository implementation. Preserve user-selected behavior and scope;
resolve routine implementation choices from source evidence.

1. Locate the provider and consumers with `find-in-repos`. Inspect tests,
   serialized schemas, examples and dynamic references when relevant. Do not
   confuse truncated search results with complete consumer coverage.
2. Read affected repository contracts and initial diffs. State compatibility
   expectations and coordinate file ownership without overwriting others' work.
3. Implement providers before consumers using actual dependency relationships.
   Numeric tiers include fractional values and Tier 4; UI/adjacent use their
   actual contracts. Do not create compatibility shims unless required.
4. Verify changed behavior in each affected repo and the cross-repository
   boundary. Use `tier-check` if dependencies or import contracts change.
   Repair in-scope failures; report missing coverage without calling it a pass.
5. Inspect the combined diff and remaining references. Report each repo's change,
   tests and any migration limitations. A dirty tree is not inherently failure;
   unrelated changes stay intact.

Commits and publication follow established authority and
[commit policy](../../../README.md). No automatic commit,
clean-tree requirement, repeated approval ritual or unrelated whole-stack audit.

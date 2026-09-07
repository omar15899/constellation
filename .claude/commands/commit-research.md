---
name: commit-research
description: Plan or create policy-driven commits for explicitly selected repositories and scopes, preserving unrelated and pre-staged work. Use for committing or pushing the current task; dry-run does not imply authority to apply or publish.
---

# Scoped commits

Read [commit policy](../contracts/commit_policy.md) and the relevant
[repository policy](../registry/repo_commit_policy.yaml). Inspect the current
index and diff, identify this task's files and check existing commit/push authority.
Do not infer that every dirty repo or every file in a scope belongs to this task.

Preview with an explicit repository, exact task files and optional scope filter:

```bash
python3 .claude/scripts/research_committer.py --repo <repo-id-or-path> --path <relative-file> --scope <scope> --task <task-id>
```

Repeat `--path` for the exact files owned by this task; it is literal, not a glob
or directory selector, and requires one explicit `--repo`. Process multiple
repositories separately. Paths intersect the selected scopes and policy; inspect
every planned path, check and exclusion. Do not move files or expand policy merely
to include them.

The default refuses existing staged work. With reviewed exact paths,
`--include-prestaged` allows selected whole-file changes while leaving unrelated
index entries intact. It rejects a selected file whose staged content differs
from its working content. Never use it to absorb unknown hunks; isolate mixed
ownership through the repository's supported workflow or report the exact overlap.
After a commit, only its paths are synchronized in the index. A failed index
synchronization requires reconciliation before continuing or pushing; report the
existing commit rather than retrying blindly.

Apply the reviewed plan only under established commit authority by adding
`--apply`. Add `--push` only under established push authority; the target's
`auto_push` and expected-branch gates still apply. A blocked plan is not a commit.
Do not use branch bypass flags to defeat a refusal. Read actual help before
using optional arguments; the writer is [research_committer.py](../scripts/research_committer.py).

Use [verify-loop](verify-loop.md) for relevant final verification. For a research
lever, supply its ID and use [gate-check](gate-check.md) to assess or record its
verdict when requested. Do not equate committer schema/check success with proof
of statistical validity.

Inspect resulting commits and report exact paths/scopes, hashes, checks and push
outcomes. No additional loop-ledger entry is required unless the task needs one.
Never bundle git roots, bypass hooks, stage private archives or add AI attribution.

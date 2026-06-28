---
name: commit-research
description: Policy-driven, scope-granular, auditable commits across the constellation's independent git repos — one commit per repo per scope, verbose traceable messages (Context/Changes/Evidence/Risk/Rollback + trailers), per-repo checks, pre-staged protection, and push controlled by registry/repo_commit_policy.yaml. Dry-run first; apply/push only on explicit request.
---

# /commit-research [--task <id>] [--apply] [--push]

Git is part of the research ledger. This command lands the current work as
**one atomic commit per repo per scope**, each message reconstructing what
changed, why, with what evidence, which checks passed, and which artifacts back
it. Backed by [`scripts/research_committer.py`](../scripts/research_committer.py)
and governed by [`registry/repo_commit_policy.yaml`](../registry/repo_commit_policy.yaml).
The full doctrine is [`docs/git_as_research_ledger.md`](../docs/git_as_research_ledger.md).

## Procedure

1. **Inspect.** Run a **dry-run first** (the default — never mutates the index,
   never commits, never pushes):

   ```bash
   python3 ~/GitHub/.claude/scripts/research_committer.py --task <task-id>
   ```

   Read the table: per repo, the scopes it would commit, the checks it would run,
   the files left out as `unknown`, and any `ABORTED`/`BLOCKED` reason.

2. **Protect pre-staged work.** If a repo reports `ABORTED` for pre-staged files
   not owned by this task, **do not** blindly fold them in. Either commit them
   separately first, unstage them, or — only if they genuinely belong to this
   task — re-run with `--include-prestaged`.

3. **Classify honestly.** Files reported as `unknown` are left out by design.
   Move them into a real scope (path) or commit them deliberately; never force
   them in.

4. **Apply** only when the plan is clean. Per-repo `auto_push` in the policy plus
   the `--push` flag plus a branch matching `expected_branch` are ALL required to
   push:

   ```bash
   python3 ~/GitHub/.claude/scripts/research_committer.py --task <task-id> --apply           # commit, no push
   python3 ~/GitHub/.claude/scripts/research_committer.py --task <task-id> --apply --push     # commit + push
   ```

   Run `--apply --push` **only** when the user asked to commit/push, or when the
   policy authorises auto-push for the targeted repo and the user's request
   covers it. Conservative / `dry_run_only` repos never apply without being named
   explicitly with `--repo`.

5. **Record.** Append a one-paragraph entry to
   [`loop_ledger.md`](../loop_ledger.md): which repos, which scopes, which commit
   hashes, what was pushed.

6. **Research levers.** If the change advances or settles a research lever, pass
   `--lever <id>` so the trailer ties the commit to the registry, and update
   `levers.yaml` / `research_ledger.md` via [`/gate-check`](gate-check.md). A
   report claiming promotion without a gate artifact is **hard-blocked** by the
   `promotion_gate_if_metrics_changed` check.

## What the committer guarantees (hard)

- One repo per commit, one scope per commit — never bundled.
- Pathspec staging only — never `git add .` / `git add -A` from a parent.
- Dry-run never touches the real index (throwaway `GIT_INDEX_FILE`).
- A staged secret / `.env` / key / token aborts that commit.
- A failed check aborts that scope — success is never declared past a failure.
- Push refused when `HEAD != expected_branch` unless `--allow-branch-mismatch`.
- Unclassifiable files are left out and reported, never committed.

## Useful flags

`--repo <id|path>` (repeatable) · `--scope <scope>` (repeatable) ·
`--run-class <control-plane|diagnostic|research|deployable|production>` ·
`--message-subject "..."` · `--context "..."` · `--lever <id>` ·
`--include-prestaged` · `--allow-branch-mismatch` · `--json`.

Run [`/ship-loop`](ship-loop.md) before applying on a serious change — the gate
verifies evidence before anything lands.

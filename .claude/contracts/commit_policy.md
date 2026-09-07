# Commit-Policy Contract

*Constellation plane. A thin summary of how a commit is made safe, granular, and
auditable across the constellation's independent git surfaces. This document
invents nothing — it points at the real enforcement. The authority is the code
and the policy file; this is the map.*

Authoritative implementations:

- [`../registry/repo_commit_policy.yaml`](../registry/repo_commit_policy.yaml) — per-repo machine-readable policy.
- [`../scripts/research_committer.py`](../scripts/research_committer.py) — the policy-driven committer (`/commit-research`).
- [`../scripts/constellation_commit.py`](../scripts/constellation_commit.py) — legacy implementation, retained for direct callers; no longer a discoverable command. Use the scoped `commit-research` workflow for new tasks.
- [`../hooks/commit_guard.py`](../hooks/commit_guard.py) — standalone commit/push validator.
- [`../docs/git_as_research_ledger.md`](../docs/git_as_research_ledger.md) — the doctrine this contract abridges.

## 1. Never cross roots

A multi-repo change is **not** a multi-repo commit. Each repository is its own git
surface and gets its own commit; the committer never mixes two repos in one commit
(one `git -C <repo>` surface per commit) and never `git add .`/`-A` from a parent.
Full rule set in [`../policies/cross_repo_commits.md`](../policies/cross_repo_commits.md)
and the workflow in [`multi_repo_workflow.md`](multi_repo_workflow.md).

## 2. One repo, one scope — granular

Within a repo, changes are grouped into one commit **per scope**, classified by
path:

`contracts · registry · hooks · scripts · commands · tests · research-code ·
config · docs · reports · artifacts · unknown`

Use one explicit repository and repeat `--path` for exact task files. File selection
intersects scopes and policy; it never widens the allowed set. `--include-prestaged`
requires exact paths and rejects selected partial staging. After each commit,
only its paths are synchronized in the real index; unrelated entries survive.

Commits land in a stable scope order (contracts/registry first, reports/artifacts
last). Files that do not classify land in `unknown` and are **left out and
reported** — never force-committed. The per-repo `include`/`exclude` pathspec
prefixes and `allow_artifacts` (`true | false | selective`) / `allow_reports`
fields in [`../registry/repo_commit_policy.yaml`](../registry/repo_commit_policy.yaml)
bound what may be staged.

## 3. Verbose, traceable message format

Every commit carries a human imperative subject plus a structured body and
trailers, so `git log` is a queryable research ledger:

```
<verb> <object> <purpose>

Context:   - why this change exists
Changes:   - the files in this scope
Evidence:  - checks run and passed
Risk:      - blast radius and what could break
Rollback:  - how to undo (git revert <hash>)

Task: <task-id>
Scope: <scope> [<shortstat>]
Run-Class: <control-plane|diagnostic|research|deployable|production>
Checks: <checks that passed>
Artifacts: <artifact paths or none>
Lever: <lever id or none>
Session: <session id or ->
```

[`../hooks/commit_guard.py`](../hooks/commit_guard.py) hard-blocks a message
missing the required trailers (`Task:`, `Scope:`, `Run-Class:`, `Checks:`).

## 4. Branch-gated, fail-closed auto-push

Push happens only when **all** hold:

1. `--push` was passed;
2. the repo's `auto_push: true` in the policy file;
3. `HEAD == expected_branch` (else blocked unless `--allow-branch-mismatch`);
4. the repo is not `dry_run_only`.

Conservative / unknown repos never push and never apply without being named with
`--repo`. There is never a `--force` and never a `--no-verify`. The committer is
dry-run by default — nothing is staged, committed, or pushed unless asked.
The validator [`../hooks/commit_guard.py`](../hooks/commit_guard.py) fails **closed**
(exits 2 on internal error) so a crash can never greenlight a commit.

## 5. The commit ledger = git trailers

Because the trailers are plain `Key: value` lines, the research trail is
reconstructed with `git log --grep` / `git interpret-trailers` and no extra
tooling — by `Task:`, `Lever:`, `Run-Class:`, or `Session:`. See the query recipes
in [`../docs/git_as_research_ledger.md`](../docs/git_as_research_ledger.md). The git
history is one of four composing ledgers (lever registry, research ledger, loop
ledger, git history); none replaces another.

## Determinism boundary

Hard-block signals (objective, dangerous — always enforced) vs advisory
methodology signals (warn; block only under `*_STRICT=1`) are listed in
[`../docs/git_as_research_ledger.md`](../docs/git_as_research_ledger.md). The strict
postures are summarised in [`research_modes.md`](research_modes.md). Reports that
claim promotion are checked against the gate — see
[`promotion_gate.md`](promotion_gate.md).

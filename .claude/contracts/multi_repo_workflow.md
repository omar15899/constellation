# Multi-Repo Workflow Contract

*Constellation plane. The fixed sequence for any change that touches more than one
git root under `~/GitHub/`. This **extends, it does not replace**, the hard rules in
[`../policies/cross_repo_commits.md`](../policies/cross_repo_commits.md) and the
orchestration pipeline in
[`../agents/multi-repo-orchestrator.md`](../agents/multi-repo-orchestrator.md). When
this contract is silent, those two are authoritative.*

A multi-repo change is **not** a multi-repo commit. Each repository is its own git
surface and is committed and pushed independently.

## The sequence

1. **Identify each git root.** Enumerate every distinct repository the change
   touches (the constellation root `constellation` is itself one git surface,
   beside — not above — the sub-repos). Re-read
   [`../registry/repos.yaml`](../registry/repos.yaml) and
   [`../registry/repo_commit_policy.yaml`](../registry/repo_commit_policy.yaml) so
   the target set and per-repo policy are canonical.

2. **Declare why each is touched.** For every root, write one line: the per-repo
   unit of work and why it must change. This becomes that repo's commit subject —
   it describes *that repo's* change, never the global intent (the global intent
   lives in the PR description and, canonically, a vault-side ADR).

3. **Run repo-local checks.** Each repo's own checks run as configured in the
   policy file (`py_compile_changed`, `secret_scan`, `evidence_audit_if_reports_changed`,
   `promotion_gate_if_metrics_changed`, …) and that repo's own pre-commit gate
   stays authoritative. No `--no-verify`. A failed check aborts that scope's
   commit — never declare success past a failure.

4. **One commit per repo (per scope).** Commit each root separately, in tier order
   (Tier 0 `Shared` first, then 1, 1.5, 2, 2.5, 3, UI) so no consumer sees a broken
   intermediate `main`. Use the verbose trailer message defined in
   [`commit_policy.md`](commit_policy.md). Never stage across roots.

5. **Push each separately.** Push per repo, only when policy + branch gate allow
   (`auto_push: true`, `HEAD == expected_branch`); branch gate is fail-closed.
   Cross-repo PRs: one PR per repo, mutually cross-referenced, CI green per repo
   independently (the consumer's CI is expected to be red until `Shared` lands).
   Never `--force` to `main`.

6. **Final matrix.** Report a per-repo matrix: repo · unit · scope(s) · commit hash
   · pushed? · checks. The orchestrator emits exactly this (one section per repo
   plus the cross-repo invariants checked) and records resumable state for an
   interrupted pipeline — see
   [`../agents/multi-repo-orchestrator.md`](../agents/multi-repo-orchestrator.md).

## Tooling

- `/commit-research` → [`../scripts/research_committer.py`](../scripts/research_committer.py)
  — policy-driven, scope-granular, dry-run by default. Governed research/implementation work.
- `/commit-constellation` → [`../scripts/constellation_commit.py`](../scripts/constellation_commit.py)
  — lighter tier-ordered per-repo committer for quick control-plane commits.

Both are atomic per repo and never bundle repos.

## What never crosses a root

- A single commit containing files from more than one repo.
- `.claude/` (the `constellation` control plane) bundled with a lab's code edits.
- Vault-side (`~/OmarOS/`) updates bundled with `~/GitHub/` work — vault commits
  live in OmarOS's own history.

These are restated from [`../policies/cross_repo_commits.md`](../policies/cross_repo_commits.md),
which remains the binding rule set.

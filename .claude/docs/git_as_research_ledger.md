# Git as the research ledger

Git is not just version control here — it is the **durable, queryable record of
what we did, why, with what evidence, which checks passed, and which artifacts
back it**. The lever registry holds the *verdict*; the loop ledger holds the
*session narrative*; the commit history holds the *trail of edits* that produced
both. This document is the doctrine for that layer.

Implemented by [`../scripts/research_committer.py`](../scripts/research_committer.py)
(committer), [`../registry/repo_commit_policy.yaml`](../registry/repo_commit_policy.yaml)
(per-repo policy), [`../commands/commit-research.md`](../commands/commit-research.md)
(command), and [`../hooks/commit_guard.py`](../hooks/commit_guard.py) (validator).

## Why Git is part of the ledger

A research program is only reproducible if you can answer, for any past number:
*which code produced it, against which data, having passed which checks?* Prose
reports rot and overstate. The commit graph does not: it is content-addressed,
append-only, and survives across sessions and machines. By forcing every commit
to carry structured trailers, `git log` becomes a database you can query by task,
by lever, and by run-class.

## The four ledgers and how they differ

| Ledger | Granularity | Answers | Lifetime |
|---|---|---|---|
| `registry/levers.yaml` | one row per falsifiable hypothesis | "what is the VERDICT of this research question?" | across all sessions |
| `research_ledger.md` | human mirror of the above | "what did we learn, readable?" | across all sessions |
| `loop_ledger.md` | one entry per serious session | "HOW did this session execute (plan→verify)?" | per session, appended |
| **Git history** | one commit per repo per scope | "WHICH edits, with what evidence/checks, produced the above?" | permanent, per repo |

They compose: a lever verdict (`levers.yaml`) is justified by a session narrative
(`loop_ledger.md`) which points at the commits (Git) that carry the diffs, checks,
and artifacts. None replaces another.

## What a traceable commit must contain

The committer writes this message shape (subject is human, imperative, specific —
never "update files"):

```
<verb> <object> <purpose>

Context:
- why this change exists
Changes:
- the files in this scope
Evidence:
- checks run and passed
Risk:
- blast radius and what could break
Rollback:
- how to undo (git revert <hash>)

Task: <task-id>
Scope: <scope> [<shortstat>]
Run-Class: <control-plane|diagnostic|research|deployable|production>
Checks: <checks that passed>
Artifacts: <artifact paths or none>
Lever: <lever id or none>
Session: <session id or ->
```

Subject examples: *add the Bash run ledger and wire it into PostToolUse* ·
*cross-check evidence claims against the Bash run ledger* ·
*make the committer tier-ordered and dry-run index-safe*.

## How changes are grouped

One commit per **repo** and per **scope**. A repo is its own git surface; scopes
are classified by path:

`contracts · registry · hooks · scripts · commands · tests · research-code ·
config · docs · reports · artifacts · unknown`

Files that do not classify land in `unknown` and are **left out and reported** —
never force-committed. Commits land in a stable scope order (contracts/registry
first, reports/artifacts last) so a reviewer reads structure before output.

## When auto-push is allowed

Push happens only when **all** hold:

1. `--push` was passed;
2. the repo's `auto_push: true` in `repo_commit_policy.yaml`;
3. `HEAD == expected_branch` (else blocked unless `--allow-branch-mismatch`);
4. the repo is not `dry_run_only`.

Conservative / unknown repos never push and never apply without being named with
`--repo`. There is never a `--force` and never a `--no-verify`.

## The determinism boundary

```
Hard-block (objective, dangerous — always enforced):
  - secrets / .env / keys / tokens staged
  - invalid Python touched (py_compile)
  - invalid settings.json
  - a report referencing a missing artifact
  - failed relevant tests / checks
  - pre-staged files not owned by the task (unless --include-prestaged)
  - push to the wrong branch (unless --allow-branch-mismatch)
  - a commit message missing required trailers
  - large artifacts outside the allowlist
  - a report claiming promotion with no gate artifact

Advisory (methodology — warns; blocks only under *_STRICT=1):
  - re-running a dead lever (DEAD_LEVER_STRICT)
  - a seedless stochastic script (METRIC_PROVENANCE_STRICT / COMMIT_GUARD_STRICT)
  - broad claims (robust / confirmed / production-ready) (LOOP_GUARD_STRICT)
  - incomplete but non-critical ledger entries
```

This mirrors the constellation's standing posture: hooks block only hard,
objective signals; methodology is advisory and opt-in strict.

## Reconstructing a session from `git log`

```bash
# everything one task landed, across all repos and scopes
git log --all --grep 'Task: research-git-ledger' --oneline

# every commit advancing a research lever
git log --all --grep 'Lever: multisleeve-hrp-book'

# only the production-class changes
git log --all --grep 'Run-Class: production'

# one session's full footprint
git log --all --grep 'Session: <id>'

# full body (Context/Changes/Evidence/Risk/Rollback) of a commit
git show -s --format=%B <hash>
```

Because the trailers are plain `Key: value` lines, `git interpret-trailers` and
any `--grep` reconstruct the research trail without extra tooling.

## Relationship to the simpler committer

[`constellation_commit.py`](../scripts/constellation_commit.py) is the lighter
tier-ordered committer (quick per-repo commits with provenance trailers).
`research_committer.py` is the policy-driven superset: per-scope grouping,
per-repo checks, pre-staged protection, run-class, and the verbose message above.
Use `/commit-research` for governed research/implementation work;
`commit-research` is the shared entry point, including control-plane work.
Always select the authorized repositories and scopes explicitly. The older
`constellation_commit.py` remains for direct callers, without a discoverable skill.

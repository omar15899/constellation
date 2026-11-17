# Cross-Repo Commits

A multi-repo change is *not* a multi-repo commit. This policy
prescribes how a change that spans repos is committed, reviewed,
landed, and recorded.

## Hard rules

1. **One commit per repo.** Each repository is its own Git owner and
   Constellation task. Use the common `commit` and `push` entry points.
   Never invoke `git commit` across repos in a single call. Each commit
   is atomic within its repo.
2. **Tier order for landings.** Land Tier 0 first, then 1, 1.5, 2,
   2.5, 3, UI. The opposite order produces a broken intermediate state
   on `main` for every consumer.
3. **Branch per logical change.** The same branch name across repos
   for one cross-repo feature (e.g. `rename-known-at-to-with-time`).
   The branch name is the canonical identifier of the cross-repo unit.
4. **One PR per repo, mutually cross-referenced.** Each PR's
   description starts with:

   ```
   Part of cross-repo change: <branch-name>
   Companion PRs:
     - https://github.com/<org>/Shared/pull/123
     - https://github.com/<org>/BacktestLab/pull/456
     ...
   ```

5. **CI must pass per repo independently.** No "merge once everyone is
   green" tricks — the consumer's CI will be red until Shared lands,
   that is expected. Merge in tier order.
6. **No `--no-verify`.** The pre-commit gate of each lab is
   authoritative for that lab.
7. **No `--force` to `main`.** Constellation hub does not authorise
   force-pushes to any main branch.

## Commit message style

Inherits from `~/GitHub/Constellation/instructions/AGENTS.md`:

- Present tense, plain English.
- No AI attribution.
- No `Co-authored-by`.
- One imperative sentence summarising the change in that repo.

A cross-repo change produces commits like:

```
Shared:        rename KnownAt to WithTime
BacktestLab:   update consumers for WithTime rename
MonteCarloLab: update consumers for WithTime rename
PricingLab:    update consumers for WithTime rename
```

Note that each message describes *that repo's* change, not the global
intent. The global intent lives in the PR description and (canonically)
in a vault-side ADR.

## The vault-side ADR

For any cross-repo refactor, open a corresponding ADR under
`~/OmarOS/05_Projects/QuantOS/Decisions/` *before* the first commit
lands. The ADR:

- Describes the motivation in one paragraph.
- Lists the affected repos.
- Records the agreed naming / signature / schema.
- Links each PR once it is open.

The active coordinator proposes the ADR follow-up and records it only
within the authorized vault scope. Each owner has a separate task.

## Idempotence + retry

If the active coordinator is interrupted:

- Per-repo commits that landed remain (no rollback).
- Per-repo branches that were created remain (no cleanup unless asked).
- The coordinator records a curated checkpoint in the private Constellation
  task ledger. Resume with `constellation.py status` and `recover` for the
  specific owner; do not create a second orchestration state file.

## What never gets committed across repos

- A single commit containing files from more than one repo (impossible
  in practice, but worth stating).
- Hub control-plane updates bundled with a lab's code edits. The hub is its
  own `constellation` repository and receives its own scoped commit when
  authorized.
- Vault-side updates bundled with `~/GitHub/` work. Vault commits are
  recorded inside `~/OmarOS/`'s git history, never in a lab.

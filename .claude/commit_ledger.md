# Commit ledger

There is no separate commit-ledger file to maintain. **The durable commit ledger
is the git history itself** — the structured trailers every constellation commit
carries make `git log` a queryable database of what landed, why, with what
evidence, and against which task and lever. The doctrine lives in
[`docs/git_as_research_ledger.md`](docs/git_as_research_ledger.md); the writer is
[`scripts/research_committer.py`](scripts/research_committer.py) (via
[`/commit-research`](commands/commit-research.md)).

This file exists only to point at that history and, optionally, to host a hand-
appended index of notable landings. It is **not** a system of record — if it ever
disagrees with `git log`, the commit graph wins.

## The trailers every commit carries

```
Task: <task-id>
Scope: <scope> [<shortstat>]
Run-Class: <control-plane|diagnostic|research|deployable|production>
Checks: <checks that passed>
Artifacts: <artifact paths or none>
Lever: <lever id or none>
Session: <session id or ->
```

Because trailers are plain `Key: value` lines, no tooling beyond `git log
--grep` / `git interpret-trailers` is needed to reconstruct any trail.

## Querying the ledger

```bash
# everything one task landed, across every repo and scope
git log --all --grep 'Task: <task-id>' --oneline

# every commit that advanced or settled a research lever
git log --all --grep 'Lever: <lever-id>' --oneline

# only the production-class (committed-result) changes
git log --all --grep 'Run-Class: production' --oneline

# one session's full footprint
git log --all --grep 'Session: <id>' --oneline

# the full body (Context/Changes/Evidence/Risk/Rollback) of one commit
git show -s --format=%B <hash>
```

## Where this sits among the ledgers

| Ledger | Answers | System of record? |
|---|---|---|
| `registry/levers.yaml` | what is the VERDICT of a hypothesis? | yes (machine) |
| `research_ledger.md` | what did we learn, readable? | mirror of the above |
| `loop_ledger.md` | HOW did a session execute (plan→verify)? | yes (per session) |
| **Git history** | WHICH edits, with what evidence/checks, produced the above? | **yes (permanent)** |
| `commit_ledger.md` (this file) | a pointer + optional hand index | no — convenience only |

## Optional appendable matrix

A reviewer may append a one-line row per notable landing below. This is a
courtesy index for fast scanning, never authoritative — the trailers above are.
Leave it empty until there is something worth surfacing.

| date | task | repos | run-class | lever | head commits |
|------|------|-------|-----------|-------|--------------|

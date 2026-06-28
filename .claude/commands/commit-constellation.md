---
name: commit-constellation
description: Granular, per-repo, traceable commits across every dirty git surface under ~/GitHub/ (root constellation repo + each sub-repo), with verbose git-trailer provenance and automatic push. Atomic per repo; never bundles repos; never force-pushes.
---

# /commit-constellation [--push] [--dry-run]

The constellation is many independent git surfaces. This command lands the
current work as **one atomic commit per repo**, with verbose, machine-greppable
trailers so the whole research/implementation history is reconstructable from
`git log` alone. Backed by
[`scripts/constellation_commit.py`](../scripts/constellation_commit.py).

## Procedure

1. **Survey.** `python3 ~/GitHub/.claude/scripts/constellation_commit.py --dry-run --intent "x"`
   (or `~/GitHub/.claude/scripts/status_all.sh --dirty-only`) to list every
   dirty surface — the root `constellation` repo and each sub-repo.

2. **Inspect each dirty repo's diff** (`git -C <repo> diff`). Group changes into
   **logical units**. Granularity is the *model's* call; atomicity per repo is
   the *script's* guarantee. If a repo holds two unrelated changes, write two
   commit entries for it with disjoint `paths`.

3. **Write a spec** to the scratchpad, e.g. `commit_spec.json`:

   ```json
   {
     "session": "<short session id or task slug>",
     "commits": [
       {
         "repo": "ResearchLab",
         "subject": "charge realistic borrow cost on the short leg",
         "body": "Why: the long/short edge was scored with a free short leg...",
         "paths": ["research/ltr/costs.py", "research/ltr/backtest.py"],
         "lever": "short-leg-cost",
         "task": "short-leg-cost"
       },
       {
         "repo": ".",
         "subject": "record short-leg-cost verdict in lever registry",
         "paths": [".claude/registry/levers.yaml"],
         "lever": "short-leg-cost"
       }
     ]
   }
   ```

   - `repo: "."` is the root `constellation` repo (the control plane).
   - `subject` describes **that repo's** change, imperative, plain English, no
     AI attribution (per `~/CLAUDE.md`).
   - `lever` / `task` tie the commit to research state — set `lever` to the
     `registry/levers.yaml` entry the work advances when applicable.
   - Omit `paths` to stage the repo's whole working tree.

4. **Run it:**

   ```bash
   python3 ~/GitHub/.claude/scripts/constellation_commit.py --spec commit_spec.json --push
   ```

   For a quick uniform pass (one subject, every dirty repo, stage-all):

   ```bash
   python3 ~/GitHub/.claude/scripts/constellation_commit.py --intent "subject" --push
   ```

5. **Read the JSON report.** Each repo returns `committed [<hash>]` + `pushed`,
   or a clear `skip` / `ABORTED` / `BLOCKED` reason. A non-zero exit means at
   least one repo was aborted (staged secret) or blocked (its own pre-commit
   hook). Fix and re-run only the offending repo.

## Guarantees the script enforces

- **Atomic per repo** — `git -C <repo>` only; one repo's tree never leaks into
  another's commit (constellation git policy).
- **Secret abort** — a staged `.env` / key / token unstages and skips that repo.
- **No `--force`, no `--no-verify`** — per-repo pre-commit hooks stay
  authoritative; a blocked commit is reported, not bypassed.
- **Auto-push** sets upstream on first push, never force-pushes, never pushes a
  detached HEAD; one repo's push failure does not abort the others.
- **Traceability trailers** on every commit:
  `Changed-files`, `Repo`, `Branch`, `Lever`, `Task`, `Session` — query later
  with `git log --grep 'Lever: short-leg-cost'`.

Run `/ship-loop` first when the work is a serious change — the gate verifies
evidence before anything lands.

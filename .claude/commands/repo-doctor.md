---
name: repo-doctor
description: Read-only health check for the ~/GitHub/.claude hub. Composes the existing validators (levers/settings/repos) and adds settings.json integrity, referenced-hook existence, commands//contracts/ presence, and hub git state. With --repo it profiles a target repo (branch/upstream/dirty/untracked/merge-conflict, project type, available checks, raw-data hygiene, oversized staged blobs). Never mutates.
---

# /repo-doctor [--repo <path>] [--json]

One command to answer "is the constellation control plane healthy, and is this
repo in a sane state to work in?" — without touching anything. Backed by
[`scripts/doctor.py`](../scripts/doctor.py).

## Invoke

```bash
python3 ~/GitHub/.claude/scripts/doctor.py                       # hub health
python3 ~/GitHub/.claude/scripts/doctor.py --repo ~/GitHub/MarketDataLab
python3 ~/GitHub/.claude/scripts/doctor.py --json                # machine-readable
```

Read the verdict line: `CONSTELLATION DOCTOR: PASS | WARN | FAIL`. Exit code is
`0` for PASS/WARN and `1` for FAIL (a hard, actionable problem).

## What it checks

- **validators** — runs `validate_levers.py`, `validate_settings.py`,
  `validate_repos.py` as subprocesses. A missing validator is `not-run`, never a
  crash; a nonzero validator is `FAIL`.
- **hub structure** — `settings.json` parses; every hook it references exists;
  `commands/` and `contracts/` are present.
- **hub git** — branch, upstream tracking, ahead/behind, dirty/clean.
- **repo (with `--repo`)** — branch/upstream, dirty, untracked, merge conflicts
  (`FAIL`), project type, available checks (`pytest|ruff|mypy|npm|make`), raw
  research data wrongly tracked in git, and staged blobs `>=5 MiB`.

## Guarantees

- **Never mutates.** No index writes, no commits, no file edits — pure read.
- Safe to run at session start, before a commit, or when onboarding a repo.

## Note on hooks

The doctor reports hook *existence and wiring* in `settings.json`. Newly added
or edited hooks only go live after a Claude session restart — the running
session keeps the hook set it started with. If a hook was just added, restart
the session before trusting that it fires; the doctor confirms it is referenced
and present, not that the live session already loaded it.

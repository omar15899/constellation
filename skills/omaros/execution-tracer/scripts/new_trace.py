#!/usr/bin/env python3
"""Scaffold an execution trace under 11_Documents_and_Reports/Execution_Traces/<date>/<task_id>.md.

Pre-populates: frontmatter, section skeleton, and the Git actions table using
`git log` over the provided commit range. All other sections start empty with
"n/a (reason: input not available)" placeholders that the caller replaces.

Usage:
    echo '{...}' | python3 new_trace.py

Required fields:
    task_id    string (slug)
    title      string
    status     completed | blocked | aborted
    risk       low | medium | high

Optional:
    worktree   path or null                       (default: null)
    project    project slug                       (default: null)
    since      commit hash or ISO date            (default: HEAD~10)
    until      commit hash or ISO date            (default: HEAD)

Exit codes:
    0  scaffold written
    1  filesystem error
    2  bad payload
"""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path


VAULT_ROOT = Path(os.environ.get("OMAROS_ROOT", Path("/Users/omarkhalil/OmarOS")))
TRACES_DIR = VAULT_ROOT / "11_Documents_and_Reports" / "Execution_Traces"

REQUIRED = {"task_id", "title", "status", "risk"}
VALID_STATUS = {"completed", "blocked", "aborted"}
VALID_RISK = {"low", "medium", "high"}


def validate(payload: dict) -> None:
    missing = REQUIRED - payload.keys()
    if missing:
        sys.stderr.write(f"error: missing fields: {sorted(missing)}\n")
        sys.exit(2)
    if payload["status"] not in VALID_STATUS:
        sys.stderr.write(f"error: status must be one of {sorted(VALID_STATUS)}\n")
        sys.exit(2)
    if payload["risk"] not in VALID_RISK:
        sys.stderr.write(f"error: risk must be one of {sorted(VALID_RISK)}\n")
        sys.exit(2)


def git_commits(since: str, until: str) -> list[tuple[str, str]]:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(VAULT_ROOT),
                "log",
                "--format=%h|%s",
                f"{since}..{until}",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []
    if result.returncode != 0:
        return []
    out = []
    for line in result.stdout.strip().splitlines():
        if "|" in line:
            h, msg = line.split("|", 1)
            out.append((h, msg))
    return out


def render(payload: dict, now: dt.datetime, commits: list[tuple[str, str]]) -> str:
    project = payload.get("project") or "null"
    worktree = payload.get("worktree") or "null"

    git_rows = (
        "\n".join(f"| `{h}` | {msg} | ? |" for h, msg in commits)
        or "| n/a | (no commits in range) | n/a |"
    )

    return f"""---
task_id: {payload['task_id']}
title: "{payload['title']}"
status: {payload['status']}
worktree: {worktree}
created: {now.isoformat()}
completed: {now.isoformat()}
risk: {payload['risk']}
note_type: execution_trace
project: {project}
related_task: null
invariants_passed: []
invariants_waived: []
tags: [execution_trace]
author: Omar
ai_generated: true
---

# {payload['title']}

## 1. Objective

n/a (reason: input not available)

## 2. Plan

n/a (reason: input not available)

## 3. Actions executed

n/a (reason: input not available)

## 4. Files changed

n/a (reason: input not available)

## 5. Tests run

n/a (reason: input not available)

## 6. Documentation updated

n/a (reason: input not available)

## 7. Git actions

| Hash | Message | Pushed |
|------|---------|:------:|
{git_rows}

## 8. Logs

n/a (reason: input not available)

## 9. Invariants

| Invariant | Status | Evidence / Reason |
|-----------|:------:|-------------------|
| n/a       | n/a    | n/a               |

## 10. Pending risks

n/a (reason: input not available)

## 11. Recovery actions

n/a (reason: not applicable)
"""


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"error: invalid JSON: {exc}\n")
        sys.exit(2)

    validate(payload)

    now = dt.datetime.now()
    since = payload.get("since", "HEAD~10")
    until = payload.get("until", "HEAD")
    commits = git_commits(since, until)

    target_dir = TRACES_DIR / now.date().isoformat()
    target = target_dir / f"{payload['task_id']}.md"

    target_dir.mkdir(parents=True, exist_ok=True)
    target.write_text(render(payload, now, commits), encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()

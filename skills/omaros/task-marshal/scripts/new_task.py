#!/usr/bin/env python3
"""Scaffold a new task file under 02_Tasks_and_Execution/Backlog/ from a JSON payload.

Reads a JSON object from stdin; writes the canonical task skeleton with
frontmatter + the four-section body. Also appends a history bullet.

Usage:
    echo '{...}' | python3 new_task.py

Required fields:
    title     string
    slug      string (ASCII snake_case)

Optional fields:
    priority  P0 | P1 | P2 | P3         (default: P2)
    project   slug of parent project    (default: null)
    owner     name                      (default: Omar)
    due       YYYY-MM-DD                (default: null)
    tags      list                      (default: ["task"])

Exit codes:
    0  scaffold written
    1  target already exists
    2  bad payload
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path


VAULT_ROOT = Path(os.environ.get("OMAROS_ROOT", Path("/Users/omarkhalil/OmarOS")))
BACKLOG_DIR = VAULT_ROOT / "02_Tasks_and_Execution" / "Backlog"

PRIORITIES = {"P0", "P1", "P2", "P3"}


def validate(payload: dict) -> None:
    for f in ("title", "slug"):
        if f not in payload or not payload[f]:
            sys.stderr.write(f"error: missing required field '{f}'\n")
            sys.exit(2)
    pri = payload.get("priority", "P2")
    if pri not in PRIORITIES:
        sys.stderr.write(f"error: priority must be one of {sorted(PRIORITIES)}\n")
        sys.exit(2)


def render(payload: dict, date: dt.date) -> str:
    tags = payload.get("tags", ["task"])
    fm_tags = ", ".join(tags)
    project = payload.get("project") or "null"
    due = payload.get("due") or "null"
    owner = payload.get("owner", "Omar")
    priority = payload.get("priority", "P2")

    return f"""---
title: "{payload['title']}"
note_type: task
status: draft
priority: {priority}
project: {project}
owner: {owner}
due: {due}
created: {date.isoformat()}
updated: {date.isoformat()}
closed_at: null
blocker: null
tags: [{fm_tags}]
author: Omar
ai_generated: true
---

# {payload['title']}

## Context

## Definition of done

- [ ]

## Notes

## History

- {date.isoformat()} — Created (priority {priority}).
"""


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"error: invalid JSON: {exc}\n")
        sys.exit(2)

    validate(payload)
    date = dt.date.today()
    target = BACKLOG_DIR / f"{date.isoformat()}_{payload['slug']}.md"

    if target.exists():
        sys.stderr.write(f"error: target exists: {target}\n")
        sys.exit(1)

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(payload, date), encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()

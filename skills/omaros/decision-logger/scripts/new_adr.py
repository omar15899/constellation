#!/usr/bin/env python3
"""Scaffold a new ADR file under 20_System_Governance/Decisions/ from a JSON payload.

Reads a JSON object from stdin with the required fields; writes a canonical ADR
skeleton with frontmatter + empty section headings. Does NOT fill substantive
content — that is the caller's job. Exits without modification if target exists
(idempotent); the caller may overwrite explicitly.

Usage:
    echo '{...}' | python3 new_adr.py

Required input fields:
    title          string
    slug           string (ASCII snake_case)
    reversibility  one of: reversible | hard_to_reverse | irreversible
    affects        list of strings

Optional:
    supersedes     list of prior ADR paths (defaults to [])
    date           YYYY-MM-DD (defaults to today)
    tags           list (defaults to ["decision"])

Output:
    prints the absolute target path to stdout.

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
DECISIONS_DIR = VAULT_ROOT / "20_System_Governance" / "Decisions"

REQUIRED = {"title", "slug", "reversibility", "affects"}
REVERSIBILITY = {"reversible", "hard_to_reverse", "irreversible"}


def validate(payload: dict) -> None:
    missing = REQUIRED - payload.keys()
    if missing:
        sys.stderr.write(f"error: missing fields: {sorted(missing)}\n")
        sys.exit(2)
    if payload["reversibility"] not in REVERSIBILITY:
        sys.stderr.write(
            f"error: reversibility must be one of {sorted(REVERSIBILITY)}\n"
        )
        sys.exit(2)
    if not isinstance(payload["affects"], list) or not payload["affects"]:
        sys.stderr.write("error: affects must be a non-empty list\n")
        sys.exit(2)


def render(payload: dict, date: dt.date) -> str:
    fm_affects = "\n".join(f"  - {a}" for a in payload["affects"])
    fm_supersedes = json.dumps(payload.get("supersedes", []))
    tags = payload.get("tags", ["decision"])
    fm_tags = ", ".join(tags)

    return f"""---
title: "{payload['title']}"
note_type: decision_log
status: active
reversibility: {payload['reversibility']}
decided_at: {date.isoformat()}
decided_by: Omar
affects:
{fm_affects}
supersedes: {fm_supersedes}
superseded_by: null
tags: [{fm_tags}]
created: {date.isoformat()}
updated: {date.isoformat()}
author: Omar
ai_generated: true
ai_reviewed: false
---

# {payload['title']}

## Context

## Options considered

### Option A

**Pros:**
**Cons:**

### Option B

**Pros:**
**Cons:**

## Decision

## Rationale

## Reversibility

## Consequences

## References
"""


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"error: invalid JSON on stdin: {exc}\n")
        sys.exit(2)

    validate(payload)
    date = dt.date.fromisoformat(payload["date"]) if "date" in payload else dt.date.today()
    target = DECISIONS_DIR / f"{date.isoformat()}_{payload['slug']}.md"

    if target.exists():
        sys.stderr.write(f"error: target exists: {target}\n")
        sys.exit(1)

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(payload, date), encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Scaffold an incident note under 11_Documents_and_Reports/Incidents/ from a payload.

Reads the caller's structured failure payload on stdin (per the failure-reporter
skill input contract) and writes a canonical incident note. Idempotent per day+
slug: existing target for the same day+slug is overwritten (same incident
re-reported).

Usage:
    echo '{...}' | python3 new_incident.py

Required fields (from skill input contract):
    agent, phase, error_class, error_message, failed_at

Optional fields:
    source_id, command, started_at, context (dict), severity (defaults to P2)

Exit codes:
    0  scaffold written
    2  bad payload
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path


VAULT_ROOT = Path(os.environ.get("OMAROS_ROOT", Path("/Users/omarkhalil/OmarOS")))
INCIDENTS_DIR = VAULT_ROOT / "11_Documents_and_Reports" / "Incidents"

REQUIRED = {"agent", "phase", "error_class", "error_message", "failed_at"}
VALID_PHASE = {"probe", "extract", "transform", "route", "write", "commit"}
VALID_CLASS = {"unreachable", "auth", "schema", "timeout", "partial_write", "unknown"}
VALID_SEVERITY = {"P0", "P1", "P2", "P3"}


def validate(payload: dict) -> None:
    missing = REQUIRED - payload.keys()
    if missing:
        sys.stderr.write(f"error: missing fields: {sorted(missing)}\n")
        sys.exit(2)
    if payload["phase"] not in VALID_PHASE:
        sys.stderr.write(f"error: phase must be one of {sorted(VALID_PHASE)}\n")
        sys.exit(2)
    if payload["error_class"] not in VALID_CLASS:
        sys.stderr.write(f"error: error_class must be one of {sorted(VALID_CLASS)}\n")
        sys.exit(2)


def compute_slug(payload: dict) -> str:
    sid = payload.get("source_id") or payload["agent"]
    return f"{sid}_{payload['error_class']}"


def render(payload: dict, date: dt.date, slug: str) -> str:
    ctx = payload.get("context", {}) or {}
    adapter = ctx.get("adapter", "not reported")
    endpoint = ctx.get("endpoint", "not reported")
    retry_count = ctx.get("retry_count", "not reported")
    prev_success = ctx.get("previous_success", "none known")
    severity = payload.get("severity", "P2")
    if severity not in VALID_SEVERITY:
        severity = "P2"
    source_id = payload.get("source_id") or "null"
    command = payload.get("command", "not reported")
    started_at = payload.get("started_at", "not reported")
    error_msg = payload["error_message"]

    return f"""---
title: "{source_id} — {payload['error_class']}"
note_type: incident_report
source_id: {source_id}
agent: {payload['agent']}
command: {command}
phase: {payload['phase']}
error_class: {payload['error_class']}
severity: {severity}
status: open
started_at: {started_at}
failed_at: {payload['failed_at']}
resolved_at: null
created: {date.isoformat()}
updated: {date.isoformat()}
tags: [incident, refresh, {source_id}, {payload['error_class']}]
author: Omar
ai_generated: true
---

# {source_id} — {payload['error_class']}

## 1. Summary

_Caller to replace: one paragraph on what was attempted, what failed, current state._

## 2. Timeline

- **Started:** {started_at}
- **Failed:** {payload['failed_at']}
- **Previous successful run:** {prev_success}

## 3. Error (verbatim)

```
{error_msg}
```

## 4. Context

- **Adapter:** {adapter}
- **Endpoint:** {endpoint}
- **Retry count:** {retry_count}
- **Phase:** {payload['phase']}

## 5. Reproduction

_Caller to replace: concrete command + args._

## 6. Likely cause (hypothesis)

_No hypothesis available at write time._

## 7. Next actions

_Caller to fill: owner per step, ≤5._

## 8. Related

_Caller to fill: master refresh report, prior incidents._
"""


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"error: invalid JSON: {exc}\n")
        sys.exit(2)

    validate(payload)
    date = dt.date.today()
    slug = compute_slug(payload)
    target = INCIDENTS_DIR / f"{date.isoformat()}_{slug}.md"

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(payload, date, slug), encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()

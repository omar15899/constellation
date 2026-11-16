#!/usr/bin/env python3
"""Create today's (or a given day's) daily note from the canonical template.

Idempotent: if the target file already exists, exits 0 without modification.
Prints the absolute path of the daily note to stdout (either newly-created or
pre-existing), so the caller can route the next action to the right file.

Usage:
    python3 new_daily.py [YYYY-MM-DD]

Argument:
    YYYY-MM-DD  Target date. Defaults to today (local timezone).

Exit codes:
    0  success (file created or already existed)
    1  template missing or filesystem error
    2  bad argument
"""
from __future__ import annotations

import datetime as dt
import os
import sys
from pathlib import Path


VAULT_ROOT = Path(os.environ.get("OMAROS_ROOT", Path("/Users/omarkhalil/OmarOS")))
DAILY_DIR = VAULT_ROOT / "01_Daily_Life" / "Journal" / "Daily"
TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "daily_template.md"


def iso_week(date: dt.date) -> str:
    year, week, _ = date.isocalendar()
    return f"{year}-W{week:02d}"


def parse_date(arg: str | None) -> dt.date:
    if not arg:
        return dt.date.today()
    try:
        return dt.date.fromisoformat(arg)
    except ValueError:
        sys.stderr.write(f"error: invalid date '{arg}'; expected YYYY-MM-DD\n")
        sys.exit(2)


def main() -> None:
    date = parse_date(sys.argv[1] if len(sys.argv) > 1 else None)
    target = DAILY_DIR / f"{date.isoformat()}.md"

    if target.exists():
        print(target)
        return

    if not TEMPLATE.exists():
        sys.stderr.write(f"error: template not found at {TEMPLATE}\n")
        sys.exit(1)

    body = TEMPLATE.read_text(encoding="utf-8")
    body = body.replace("{{date}}", date.isoformat())
    body = body.replace("{{weekly}}", iso_week(date))

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()

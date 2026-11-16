#!/usr/bin/env python3
"""Compute a structured per-repo diff summary for the repo-reporter skill.

Runs `git log` and `git diff --stat` against the given clone, classifies
commits by theme from their subjects, groups files by top-level directory,
and emits a JSON blob on stdout that the skill body formats into the report.

Read-only on the clone. Never commits, never pushes, never fetches.

Usage:
    python3 compute_diff.py <clone_path> <since_ref> [<until_ref>]

Args:
    clone_path  absolute path to the local clone
    since_ref   commit hash, ISO date, or "N.days.ago"
    until_ref   defaults to HEAD

Output:
    JSON with keys: head, branch, commits (list), themes (dict),
                    files_by_dir (dict), todos (list), counts.

Exit codes:
    0  ok
    1  git failure
    2  bad args
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path


THEME_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^\s*(feat|feature|add)\b", re.I), "feature"),
    (re.compile(r"^\s*(fix|bug|hotfix)\b", re.I), "bug_fix"),
    (re.compile(r"^\s*(refactor|cleanup)\b", re.I), "refactor"),
    (re.compile(r"^\s*(docs?|readme)\b", re.I), "docs"),
    (re.compile(r"^\s*(test|spec)\b", re.I), "tests"),
    (re.compile(r"^\s*(arch|architecture|redesign)\b", re.I), "architecture"),
    (re.compile(r"^\s*(release|version|bump)\b", re.I), "release"),
]

TODO_RE = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b")


def git(clone: Path, *args: str, timeout: int = 30) -> tuple[int, str, str]:
    result = subprocess.run(
        ["git", "-C", str(clone), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def classify_theme(subject: str) -> str:
    for pattern, theme in THEME_RULES:
        if pattern.search(subject):
            return theme
    return "chore"


def top_level_dir(path: str) -> str:
    parts = Path(path).parts
    return parts[0] if parts else "root"


def main() -> None:
    if len(sys.argv) < 3:
        sys.stderr.write("usage: compute_diff.py <clone_path> <since_ref> [<until_ref>]\n")
        sys.exit(2)

    clone = Path(sys.argv[1])
    since = sys.argv[2]
    until = sys.argv[3] if len(sys.argv) > 3 else "HEAD"

    if not (clone / ".git").exists() and not (clone / "HEAD").exists():
        sys.stderr.write(f"error: not a git repo: {clone}\n")
        sys.exit(1)

    code, head, err = git(clone, "rev-parse", until)
    if code != 0:
        sys.stderr.write(f"git rev-parse failed: {err}\n")
        sys.exit(1)

    code, branch, _ = git(clone, "rev-parse", "--abbrev-ref", until)

    code, log_out, err = git(
        clone,
        "log",
        "--format=%h|%an|%ad|%s",
        "--date=iso-strict",
        f"{since}..{until}",
    )
    if code != 0:
        sys.stderr.write(f"git log failed: {err}\n")
        sys.exit(1)

    commits: list[dict] = []
    themes: Counter = Counter()
    for line in log_out.splitlines():
        if not line.strip():
            continue
        parts = line.split("|", 3)
        if len(parts) != 4:
            continue
        h, author, when, subject = parts
        theme = classify_theme(subject)
        themes[theme] += 1
        commits.append(
            {"hash": h, "author": author, "date": when, "subject": subject, "theme": theme}
        )

    code, files_out, _ = git(clone, "diff", "--name-only", f"{since}..{until}")
    files = [p for p in files_out.splitlines() if p.strip()] if code == 0 else []
    files_by_dir: dict[str, int] = defaultdict(int)
    for p in files:
        files_by_dir[top_level_dir(p)] += 1

    code, diff_out, _ = git(clone, "diff", f"{since}..{until}")
    todos: list[dict] = []
    if code == 0:
        current_file = None
        current_line = 0
        for line in diff_out.splitlines():
            if line.startswith("+++ b/"):
                current_file = line[6:]
                current_line = 0
                continue
            if line.startswith("@@"):
                match = re.search(r"\+(\d+)", line)
                if match:
                    current_line = int(match.group(1)) - 1
                continue
            if line.startswith("+") and not line.startswith("+++"):
                current_line += 1
                if TODO_RE.search(line):
                    todos.append({"file": current_file, "line": current_line, "text": line[1:].strip()})
            elif not line.startswith("-"):
                current_line += 1

    out = {
        "clone": str(clone),
        "head": head,
        "branch": branch,
        "since": since,
        "until": until,
        "commits": commits,
        "themes": dict(themes),
        "files_by_dir": dict(files_by_dir),
        "todos": todos,
        "counts": {
            "commits": len(commits),
            "files_changed": len(files),
            "todos": len(todos),
        },
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()

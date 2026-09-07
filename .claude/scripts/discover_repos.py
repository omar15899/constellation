#!/usr/bin/env python3
"""discover_repos.py — inspect filesystem drift against the registry.

Walks ~/GitHub/, identifies every git repository, diffs against the
current registry, and prints proposals. It never updates the registry.

This script is intentionally dependency-free: only the standard
library and the system `git` binary are used. YAML is hand-parsed in
the minimal sense needed to preserve comments — for any real edit, the
canonical pattern is "rewrite the `repos:` block, keep everything else
verbatim".

Usage:
    python3 ~/GitHub/.claude/scripts/discover_repos.py            # dry-run
    python3 ~/GitHub/.claude/scripts/discover_repos.py --state    # git summary
    python3 ~/GitHub/.claude/scripts/discover_repos.py --json     # machine
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

GITHUB_ROOT = Path.home() / "GitHub"
HUB = GITHUB_ROOT / ".claude"
REGISTRY = HUB / "registry" / "repos.yaml"
SKIP = {".claude", ".scripts", ".venv", ".pytest_cache", "__pycache__"}


@dataclass
class RepoOnDisk:
    name: str
    path: str
    is_worktree: bool
    has_claude: bool
    has_pyproject: bool
    has_package_json: bool
    has_importlinter: bool


def discover() -> list[RepoOnDisk]:
    out: list[RepoOnDisk] = []
    for child in sorted(GITHUB_ROOT.iterdir()):
        if child.name in SKIP or child.name.startswith("."):
            continue
        if not child.is_dir():
            continue
        git_marker = child / ".git"
        if not git_marker.exists():
            continue
        out.append(
            RepoOnDisk(
                name=child.name,
                path=str(child),
                # A linked worktree has `.git` as a file (a gitdir pointer),
                # not a directory. See policies/worktree_lifecycle.md.
                is_worktree=git_marker.is_file(),
                has_claude=(child / ".claude").exists(),
                has_pyproject=(child / "pyproject.toml").exists(),
                has_package_json=(child / "package.json").exists(),
                has_importlinter=(child / ".importlinter").exists(),
            )
        )
    return out


def load_registry_names() -> set[str]:
    if not REGISTRY.exists():
        return set()
    names: set[str] = set()
    inside_repos = False
    for line in REGISTRY.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("repos:"):
            inside_repos = True
            continue
        if inside_repos:
            if stripped.startswith("future_repos:") or (
                stripped and not line.startswith((" ", "-", "#"))
            ):
                inside_repos = False
            elif stripped.startswith("- name:"):
                names.add(stripped.split(":", 1)[1].strip())
    return names


def diff(on_disk: list[RepoOnDisk], registered: set[str]) -> dict[str, list[str]]:
    # Worktrees are checkouts of registered repos, not repos in their own
    # right — they never count as added/removed drift.
    repo_names = {r.name for r in on_disk if not r.is_worktree}
    return {
        "added": sorted(repo_names - registered),
        "removed": sorted(registered - repo_names),
        "present": sorted(repo_names & registered),
    }


def git_state(path: str) -> dict[str, str]:
    def run(args: list[str]) -> str | None:
        try:
            r = subprocess.run(
                ["git", "-C", path] + args,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            return r.stdout.strip() if r.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            return None

    branch = run(["rev-parse", "--abbrev-ref", "HEAD"]) or "?"
    last = run(["log", "-1", "--format=%cs %s"]) or "?"
    porcelain = run(["status", "--porcelain"])
    dirty = "unknown" if porcelain is None else "dirty" if porcelain else "clean"
    return {"branch": branch, "last": last, "state": dirty}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="(reserved) apply changes")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--state", action="store_true", help="include git state per repo")
    args = parser.parse_args()

    on_disk = discover()
    repos = [r for r in on_disk if not r.is_worktree]
    worktrees = [r for r in on_disk if r.is_worktree]
    registered = load_registry_names()
    d = diff(on_disk, registered)

    report: dict[str, object] = {
        "github_root": str(GITHUB_ROOT),
        "registry": str(REGISTRY),
        "counts": {
            "on_disk": len(repos),
            "worktrees": len(worktrees),
            "registered": len(registered),
            "added": len(d["added"]),
            "removed": len(d["removed"]),
        },
        "diff": d,
        "worktrees": [r.name for r in worktrees],
        "on_disk": [asdict(r) for r in on_disk],
    }

    if args.state:
        report["state"] = {r.name: git_state(r.path) for r in on_disk}

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"~/GitHub/  →  {len(repos)} repos on disk  (+{len(worktrees)} worktrees)")
        print(f"registry  →  {len(registered)} registered")
        if worktrees:
            print("\n[~] git worktrees (checkouts of registered repos, not drift):")
            for r in worktrees:
                print(f"    {r.name}")
        if d["added"]:
            print("\n[+] not in registry (would propose classification):")
            for n in d["added"]:
                print(f"    {n}")
        if d["removed"]:
            print("\n[-] in registry but missing on disk:")
            for n in d["removed"]:
                print(f"    {n}")
        if not d["added"] and not d["removed"]:
            print("\nregistry is in sync with disk.")
        if args.state:
            print()
            for r in on_disk:
                s = report["state"][r.name]  # type: ignore[index]
                tag = " (worktree)" if r.is_worktree else ""
                print(f"  {r.name:<26}  [{s['branch']}, {s['state']}]   {s['last']}{tag}")

    if args.apply:
        print(
            "\n--apply is reserved: write-back requires constellation-cartographer "
            "to merge proposed classifications into repos.yaml.",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""validate_repos.py — integrity validator for registry/repos.yaml.

Stdlib-only, hand-parsed YAML (no PyYAML), in the hooks/_levers.py style. Reuses
_levers._parse_list_block to read the `repos:` list rather than re-implementing a
parser, and a tiny local reader for the `perimeters:` membership map. Verifies that
every registered repo actually exists on disk as a git root, that names and paths are
unique, and that each repo's declared perimeter agrees with the `perimeters:` map.
Backs constellation health checks the way validate_levers.py backs the lever registry.

Checks (HARD = nonzero exit / FAIL; WARN = advisory):
  HARD  name present and unique
  HARD  path present and unique
  HARD  path exists on disk
  HARD  path is a git root (.git present)
  WARN  declared perimeter is a known perimeter key
  WARN  repo is listed under its declared perimeter in the `perimeters:` map
  WARN  every name in the `perimeters:` map has a `repos:` entry
  WARN  (--cross-check) on-disk git roots not present in the registry

Usage:
    python3 .claude/scripts/validate_repos.py             # validate the real registry
    python3 .claude/scripts/validate_repos.py --path X    # validate a copy (tests)
    python3 .claude/scripts/validate_repos.py --cross-check
    python3 .claude/scripts/validate_repos.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_HUB = _HERE.parent
sys.path.insert(0, str(_HUB / "hooks"))
sys.path.insert(0, str(_HERE))
import _levers  # noqa: E402

REGISTRY = _HUB / "registry" / "repos.yaml"


def _parse_perimeters(lines: list[str]) -> dict[str, list[str]]:
    """Parse the top-level `perimeters:` block (mapping of name -> inline [list])."""
    out: dict[str, list[str]] = {}
    in_block = False
    for line in lines:
        stripped = line.strip()
        if not in_block:
            if stripped == "perimeters:":
                in_block = True
            continue
        if stripped == "" or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent == 0:
            break  # next top-level key — block done
        if ":" in stripped:
            key, _, rest = stripped.partition(":")
            rest = rest.strip()
            members: list[str] = []
            if rest.startswith("[") and rest.endswith("]"):
                inner = rest[1:-1].strip()
                if inner:
                    members = [m.strip() for m in inner.split(",") if m.strip()]
            out[key.strip()] = members
    return out


def validate(path: Path | None = None, cross_check: bool = False) -> dict:
    reg = path or REGISTRY
    lines = reg.read_text(errors="ignore").splitlines()
    repos = _levers._parse_list_block(lines, "repos")
    perimeters = _parse_perimeters(lines)

    errors: list[str] = []
    warnings: list[str] = []
    seen_names: set[str] = set()
    seen_paths: set[str] = set()
    repo_names = {r.get("name", "") for r in repos}
    members_in_map: set[str] = set()
    for ms in perimeters.values():
        members_in_map.update(ms)

    for repo in repos:
        name = repo.get("name", "")
        tag = name or "<no-name>"
        if not name:
            errors.append(f"{tag}: missing name")
        elif name in seen_names:
            errors.append(f"{name}: duplicate name")
        seen_names.add(name)

        raw_path = repo.get("path", "")
        if not raw_path:
            errors.append(f"{tag}: missing path")
        else:
            norm = str(Path(raw_path))
            if norm in seen_paths:
                errors.append(f"{tag}: duplicate path {raw_path}")
            seen_paths.add(norm)
            p = Path(raw_path)
            if not p.exists():
                errors.append(f"{tag}: path does not exist: {raw_path}")
            elif not (p / ".git").exists():
                errors.append(f"{tag}: not a git root (no .git): {raw_path}")

        perim = repo.get("perimeter", "")
        if perim and perimeters:
            if perim not in perimeters:
                warnings.append(f"{tag}: unknown perimeter {perim!r}")
            elif name and name not in perimeters[perim]:
                warnings.append(f"{tag}: not listed under perimeter {perim!r} in the perimeters map")

    for member in sorted(members_in_map - repo_names):
        warnings.append(f"{member}: in perimeters map but has no repos: entry")

    discovered: list[str] = []
    if cross_check:
        try:
            import discover_repos  # noqa: E402

            discovered = [r.name for r in discover_repos.discover() if not r.is_worktree]
        except Exception as exc:  # pragma: no cover - discovery is best-effort
            warnings.append(f"cross-check skipped: {exc}")
        for nm in sorted(set(discovered) - repo_names):
            warnings.append(f"{nm}: git root on disk but not in registry")

    histogram: dict[str, int] = {}
    for repo in repos:
        per = repo.get("perimeter", "?") or "?"
        histogram[per] = histogram.get(per, 0) + 1

    return {
        "ok": not errors,
        "repos": len(repos),
        "histogram": dict(sorted(histogram.items())),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--path", default=None, help="Validate a specific repos.yaml (default: the registry).")
    ap.add_argument("--cross-check", action="store_true", help="Diff the registry against git roots discovered on disk.")
    ap.add_argument("--json", action="store_true", help="Emit JSON.")
    args = ap.parse_args()
    result = validate(Path(args.path) if args.path else None, cross_check=args.cross_check)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        status = "PASS" if result["ok"] else "FAIL"
        if result["ok"] and result["warnings"]:
            status = "WARN"
        print(f"REPOS: {status}")
        print(f"repos: {result['repos']}")
        for perim, count in result["histogram"].items():
            print(f"  {perim}: {count}")
        for err in result["errors"]:
            print(f"ERROR: {err}")
        for warn in result["warnings"]:
            print(f"warning: {warn}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

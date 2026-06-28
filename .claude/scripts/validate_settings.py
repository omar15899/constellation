#!/usr/bin/env python3
"""validate_settings.py — integrity check for .claude/settings.json hook wiring.

Stdlib-only. Parses settings.json (json), walks every hook command, and for each
referenced script file:

  - resolves $CLAUDE_PROJECT_DIR (and ~ / other env vars) to a real path
  - HARD  the script file exists
  - HARD  .py hooks py_compile cleanly
  - HARD  .sh hooks pass `bash -n`
  - WARN  .sh hooks carry the exec bit (advisory: the command invokes them as
          `bash script.sh`, so the bit is not load-bearing, but a hook meant to
          run standalone should keep it)

A settings.json that wires a hook to a missing or broken script silently breaks
the harness — the hook just fails to fire. This is the pre-flight that catches it.

Usage:
    python3 .claude/scripts/validate_settings.py                  # validate the real settings
    python3 .claude/scripts/validate_settings.py --settings X     # validate a copy (tests)
    python3 .claude/scripts/validate_settings.py --project-dir D  # override $CLAUDE_PROJECT_DIR
    python3 .claude/scripts/validate_settings.py --json
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

_HUB = Path(__file__).resolve().parents[1]
_SETTINGS = _HUB / "settings.json"

_INTERPRETERS = {"python", "python3", "bash", "sh", "zsh", "node"}


def _default_project_dir(settings_path: Path) -> Path:
    """$CLAUDE_PROJECT_DIR is the dir holding the .claude/ that owns settings.json."""
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env)
    parent = settings_path.resolve().parent  # .../.claude
    if parent.name == ".claude":
        return parent.parent
    return parent


def _expand(token: str, project_dir: Path) -> str:
    token = token.replace("${CLAUDE_PROJECT_DIR}", str(project_dir))
    token = token.replace("$CLAUDE_PROJECT_DIR", str(project_dir))
    token = os.path.expandvars(token)
    token = os.path.expanduser(token)
    return token


def _extract_script(command: str, project_dir: Path) -> str | None:
    """Pull the script path out of a hook command (first token ending in .py/.sh)."""
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()
    for tok in tokens:
        base = os.path.basename(tok).lower()
        if base in _INTERPRETERS or tok.startswith("-"):
            continue
        if tok.endswith(".py") or tok.endswith(".sh"):
            return _expand(tok, project_dir)
    return None


def _py_compiles(path: Path) -> tuple[bool, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "py_compile", str(path)],
        capture_output=True, text=True,
    )
    return proc.returncode == 0, (proc.stderr or proc.stdout).strip()


def _bash_ok(path: Path) -> tuple[bool, str]:
    proc = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
    return proc.returncode == 0, (proc.stderr or proc.stdout).strip()


def _iter_commands(settings: dict):
    """Yield (event, matcher, command) for every command hook in settings.json."""
    hooks = settings.get("hooks", {})
    if not isinstance(hooks, dict):
        return
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict):
                continue
            matcher = group.get("matcher", "*")
            for hook in group.get("hooks", []) or []:
                if not isinstance(hook, dict):
                    continue
                if hook.get("type") != "command":
                    continue
                cmd = hook.get("command")
                if isinstance(cmd, str) and cmd.strip():
                    yield event, matcher, cmd


def validate(settings_path: Path, project_dir: Path | None = None) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    results: list[dict] = []

    if not settings_path.exists():
        return {
            "ok": False, "settings": str(settings_path), "project_dir": None,
            "hooks": [], "errors": [f"settings file not found: {settings_path}"],
            "warnings": [], "counts": {},
        }

    try:
        settings = json.loads(settings_path.read_text())
    except json.JSONDecodeError as exc:
        return {
            "ok": False, "settings": str(settings_path), "project_dir": None,
            "hooks": [], "errors": [f"settings.json is not valid JSON: {exc}"],
            "warnings": [], "counts": {},
        }

    pdir = project_dir or _default_project_dir(settings_path)

    for event, matcher, cmd in _iter_commands(settings):
        tag = f"{event}/{matcher}"
        script = _extract_script(cmd, pdir)
        entry = {
            "event": event, "matcher": matcher, "command": cmd,
            "script": script, "status": "OK", "detail": "",
        }

        if script is None:
            entry["status"] = "NO_SCRIPT"
            entry["detail"] = "no .py/.sh path found in command"
            warnings.append(f"{tag}: no script path detected in command (not validated)")
            results.append(entry)
            continue

        path = Path(script)
        if not path.exists():
            entry["status"] = "MISSING"
            entry["detail"] = f"file not found: {script}"
            errors.append(f"{tag}: missing script {script}")
            results.append(entry)
            continue

        if script.endswith(".py"):
            ok, detail = _py_compiles(path)
            if not ok:
                entry["status"] = "COMPILE_FAIL"
                entry["detail"] = detail
                errors.append(f"{tag}: py_compile failed for {script}")
        elif script.endswith(".sh"):
            ok, detail = _bash_ok(path)
            if not ok:
                entry["status"] = "SYNTAX_FAIL"
                entry["detail"] = detail
                errors.append(f"{tag}: bash -n failed for {script}")
            elif not os.access(path, os.X_OK):
                entry["status"] = "NOT_EXECUTABLE"
                entry["detail"] = "missing exec bit"
                warnings.append(f"{tag}: {script} is not executable (exec bit unset)")

        results.append(entry)

    counts = {
        "total": len(results),
        "ok": sum(1 for r in results if r["status"] == "OK"),
        "missing": sum(1 for r in results if r["status"] == "MISSING"),
        "uncompilable": sum(1 for r in results if r["status"] in ("COMPILE_FAIL", "SYNTAX_FAIL")),
        "non_executable": sum(1 for r in results if r["status"] == "NOT_EXECUTABLE"),
    }

    return {
        "ok": not errors,
        "settings": str(settings_path),
        "project_dir": str(pdir),
        "hooks": results,
        "errors": errors,
        "warnings": warnings,
        "counts": counts,
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--settings", default=None, help="Path to settings.json (default: the hub's).")
    ap.add_argument("--project-dir", dest="project_dir", default=None,
                    help="Override $CLAUDE_PROJECT_DIR (default: inferred from settings location).")
    ap.add_argument("--json", action="store_true", help="Emit JSON.")
    args = ap.parse_args()

    settings_path = Path(args.settings) if args.settings else _SETTINGS
    pdir = Path(args.project_dir) if args.project_dir else None
    result = validate(settings_path, pdir)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        status = "PASS" if result["ok"] else "FAIL"
        if result["ok"] and result["warnings"]:
            status = "WARN"
        print(f"SETTINGS: {status}")
        print(f"file: {result['settings']}")
        if result.get("project_dir"):
            print(f"project_dir: {result['project_dir']}")
        c = result.get("counts") or {}
        if c:
            print(f"hooks: {c['total']} (ok {c['ok']}, missing {c['missing']}, "
                  f"uncompilable {c['uncompilable']}, non-executable {c['non_executable']})")
        for r in result["hooks"]:
            line = f"  [{r['status']}] {r['event']}/{r['matcher']}: {r['script'] or r['command']}"
            if r["detail"] and r["status"] != "OK":
                line += f" — {r['detail'].splitlines()[0] if r['detail'] else ''}"
            print(line)
        for err in result["errors"]:
            print(f"ERROR: {err}")
        for warn in result["warnings"]:
            print(f"warning: {warn}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

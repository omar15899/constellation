#!/usr/bin/env python3
"""Stable, installer-owned entry point for Constellation's native hooks.

Only standard-library code runs before the installed receipt and complete release
are verified. A shared installation lock pins that release until the hook exits.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import signal
import stat
import sys

sys.dont_write_bytecode = True
EVENTS = frozenset({"UserPromptSubmit", "PreToolUse", "SubagentStart", "SubagentStop", "Stop"})
PLUGIN_DIRECTORY = "plugins/constellation"
CATALOG_MANIFEST = ".agents/plugins/marketplace.json"
CHECK_SECONDS = 1.0


# BEGIN CONSTELLATION CURRENT INVENTORY
# Generated from build.allowed_files; do not maintain a second inventory.
_CURRENT_COMMON_FILES = frozenset((
    ".claude-plugin/plugin.json",
    ".codex-plugin/plugin.json",
    "agents/researcher.md",
    "agents/reviewer.md",
    "agents/security-reviewer.md",
    "agents/verifier.md",
    "ecosystem/README.md",
    "ecosystem/__init__.py",
    "ecosystem/agents/researcher.toml",
    "ecosystem/agents/reviewer.toml",
    "ecosystem/agents/security-reviewer.toml",
    "ecosystem/agents/verifier.toml",
    "ecosystem/build.py",
    "ecosystem/claude-hooks.json",
    "ecosystem/claude.py",
    "ecosystem/claude_hooks.py",
    "ecosystem/cli.py",
    "ecosystem/core.py",
    "ecosystem/docs/architecture.md",
    "ecosystem/docs/compatibility.md",
    "ecosystem/docs/evaluation.md",
    "ecosystem/docs/migrations.md",
    "ecosystem/docs/progress.md",
    "ecosystem/docs/windows.md",
    "ecosystem/evals/cases.json",
    "ecosystem/evals/rubric.json",
    "ecosystem/hook_entry.py",
    "ecosystem/hooks.json",
    "ecosystem/hooks.py",
    "ecosystem/install.py",
    "ecosystem/native.py",
    "ecosystem/platform_support.py",
    "ecosystem/references/protocol.md",
    "ecosystem/requirements-dev.txt",
    "ecosystem/runtime/__init__.py",
    "ecosystem/runtime/agent_policy.py",
    "ecosystem/runtime/dispatch.py",
    "ecosystem/runtime/progress.py",
    "ecosystem/runtime/review-policy.json",
    "ecosystem/runtime/review_gate.py",
    "ecosystem/runtime/workflow.py",
    "ecosystem/runtime/workspace.py",
    "ecosystem/storage.py",
    "ecosystem/tests/helpers.py",
    "ecosystem/tests/native_claude_probe.py",
    "ecosystem/tests/test_capabilities.py",
    "ecosystem/tests/test_claude_hooks.py",
    "ecosystem/tests/test_claude_install.py",
    "ecosystem/tests/test_claude_package.py",
    "ecosystem/tests/test_core.py",
    "ecosystem/tests/test_hook_entry.py",
    "ecosystem/tests/test_hooks.py",
    "ecosystem/tests/test_package.py",
    "ecosystem/tests/test_platform_support.py",
    "ecosystem/tests/test_progress.py",
    "ecosystem/tests/test_progress_core.py",
    "ecosystem/tests/test_validation.py",
    "ecosystem/tests/test_windows_claude.py",
    "ecosystem/tests/windows_acceptance.py",
    "ecosystem/validate.py",
))
_CURRENT_MODULE_FILES = {
    "coding": frozenset((
        "agents/coder.md",
        "ecosystem/agents/coder.toml",
        "skills/coding/SKILL.md",
        "skills/coding/agents/openai.yaml",
        "skills/coding/references/workflow.md",
    )),
    "mathematics": frozenset((
        "agents/counterexample.md",
        "agents/mathematician.md",
        "ecosystem/agents/counterexample.toml",
        "ecosystem/agents/mathematician.toml",
        "ecosystem/references/ontology-examples.md",
        "ecosystem/references/ontology.md",
        "skills/mathematics/SKILL.md",
        "skills/mathematics/agents/openai.yaml",
        "skills/mathematics/references/workflow.md",
    )),
    "quant-research": frozenset((
        "agents/coder.md",
        "agents/counterexample.md",
        "agents/mathematician.md",
        "ecosystem/agents/coder.toml",
        "ecosystem/agents/counterexample.toml",
        "ecosystem/agents/mathematician.toml",
        "skills/quant-research/SKILL.md",
        "skills/quant-research/agents/openai.yaml",
        "skills/quant-research/references/workflow.md",
    )),
    "writter": frozenset((
        "agents/coder.md",
        "agents/editor.md",
        "agents/mathematician.md",
        "ecosystem/agents/coder.toml",
        "ecosystem/agents/editor.toml",
        "ecosystem/agents/mathematician.toml",
        "ecosystem/references/ontology-examples.md",
        "ecosystem/references/ontology.md",
        "skills/writter/SKILL.md",
        "skills/writter/agents/openai.yaml",
        "skills/writter/references/workflow.md",
    )),
}


def _current_files(modules):
    """Return the active trusted inventory without importing package code."""
    if (not isinstance(modules, (list, tuple)) or not modules
            or not all(isinstance(module, str) for module in modules)
            or len(set(modules)) != len(modules)
            or not set(modules) <= set(_CURRENT_MODULE_FILES)):
        raise ValueError("Invalid current package modules")
    return set(_CURRENT_COMMON_FILES).union(
        *(_CURRENT_MODULE_FILES[module] for module in modules))
# END CONSTELLATION CURRENT INVENTORY


class EntryError(ValueError):
    """The installed release cannot safely be selected."""


def _relative(relative: str) -> Path:
    parts = Path(relative)
    if (not relative or parts.is_absolute() or parts.as_posix() != relative
            or any(part in (".", "..") for part in parts.parts)):
        raise EntryError("invalid installed path")
    return parts


def _path(root: Path, relative: str) -> Path:
    parts = _relative(relative)
    current = root
    for part in parts.parts:
        current /= part
        if current.is_symlink():
            raise EntryError("linked installation path")
    return current


def _record(path: Path) -> dict:
    mode = path.stat().st_mode
    if not stat.S_ISREG(mode):
        raise EntryError("installation file is not regular")
    return {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "mode": stat.S_IMODE(mode)}


def _records(value: object) -> dict:
    if not isinstance(value, dict) or not value:
        raise EntryError("invalid installed inventory")
    for relative, record in value.items():
        if (not isinstance(relative, str) or not isinstance(record, dict)
                or set(record) != {"sha256", "mode"}
                or not isinstance(record["sha256"], str)
                or not re.fullmatch(r"[0-9a-f]{64}", record["sha256"])
                or type(record["mode"]) is not int or record["mode"] not in (0o644, 0o755)):
            raise EntryError("invalid installed record")
        _relative(relative)
    return value


def _object(path: Path) -> dict:
    if not stat.S_ISREG(path.stat().st_mode):
        raise EntryError("installation metadata is not regular")

    def unique(pairs: list[tuple[str, object]]) -> dict:
        result = {}
        for key, value in pairs:
            if key in result:
                raise EntryError("duplicate installation metadata")
            result[key] = value
        return result

    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)
    if not isinstance(value, dict):
        raise EntryError("invalid installation metadata")
    return value


def _inventory(root: Path) -> dict:
    if root.is_symlink() or not root.is_dir():
        raise EntryError("installation directory is missing or linked")
    result = {}
    for directory, subdirs, names in os.walk(root, followlinks=False):
        for name in subdirs + names:
            if (Path(directory) / name).is_symlink():
                raise EntryError("linked installed resource")
        for name in names:
            path = Path(directory) / name
            result[path.relative_to(root).as_posix()] = _record(path)
    return result


def _verified_hook(home: Path, entry: Path) -> Path:
    receipt = _object(_path(home, "constellation/receipt.json"))
    if (set(receipt) != {"schema", "modules", "version", "catalog", "cache", "agents", "hook"}
            or type(receipt["schema"]) is not int or receipt["schema"] != 3):
        raise EntryError("installation requires a stable-entry receipt")
    modules = receipt["modules"]
    if (not isinstance(modules, list) or not modules
            or not all(isinstance(module, str) for module in modules)
            or len(set(modules)) != len(modules)
            or not set(modules) <= set(_CURRENT_MODULE_FILES)):
        raise EntryError("invalid installed modules")
    version = receipt["version"]
    if not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", version):
        raise EntryError("invalid installed version")
    catalog_records = _records(receipt["catalog"])
    cache_records = _records(receipt["cache"])
    if set(cache_records) != _current_files(modules) | {"bundle.json"}:
        raise EntryError("installed inventory differs from the active layout")
    expected_agents = {
        "constellation-" + Path(relative).name: {
            "sha256": cache_records[relative]["sha256"], "mode": 0o644}
        for relative in sorted(_current_files(modules))
        if relative.startswith("ecosystem/agents/")
    }
    # Validate names before even interpreting receipt-supplied agent paths.
    # Native profiles normalize source permissions while retaining source bytes.
    if (not isinstance(receipt["agents"], dict)
            or set(receipt["agents"]) != set(expected_agents)):
        raise EntryError("native agent receipt differs from the current projection")
    agent_records = _records(receipt["agents"])
    if agent_records != expected_agents:
        raise EntryError("native agent receipt differs from the current projection")
    _records({"hook.py": receipt["hook"]})
    if receipt["hook"] != _record(entry) or receipt["hook"]["mode"] != 0o644:
        raise EntryError("stable entry differs from its receipt")
    source_record = cache_records.get("ecosystem/hook_entry.py", {})
    if receipt["hook"]["sha256"] != source_record.get("sha256"):
        raise EntryError("stable entry differs from its release")
    expected_catalog = {f"{PLUGIN_DIRECTORY}/{name}": record for name, record in cache_records.items()}
    expected_catalog[CATALOG_MANIFEST] = catalog_records.get(CATALOG_MANIFEST)
    if catalog_records != expected_catalog:
        raise EntryError("catalog and cache receipts differ")
    catalog = _path(home, "constellation/catalog")
    cache = _path(home, f"plugins/cache/constellation/constellation/{version}")
    if _inventory(catalog) != catalog_records or _inventory(cache) != cache_records:
        raise EntryError("installed release is incomplete or modified")
    root = catalog / PLUGIN_DIRECTORY
    manifest = _object(root / "bundle.json")
    if (set(manifest) != {"schema", "modules", "files"}
            or type(manifest["schema"]) is not int or manifest["schema"] != 1
            or manifest["modules"] != modules
            or manifest["files"] != {name: record for name, record in cache_records.items()
                                     if name != "bundle.json"}):
        raise EntryError("bundle and receipt differ")
    plugin = _object(root / ".codex-plugin/plugin.json")
    if plugin.get("name") != "constellation" or plugin.get("version") != version:
        raise EntryError("plugin and receipt differ")
    for name, expected in expected_agents.items():
        try:
            if _record(_path(home, "agents/" + name)) != expected:
                raise EntryError("owned native agent projection was modified")
        except OSError as exc:
            raise EntryError("owned native agent projection is missing or unsafe") from exc
    hook = _path(root, "ecosystem/hooks.py")
    if "ecosystem/hooks.py" not in cache_records:
        raise EntryError("installed hook is unrecorded")
    return hook


def _failure(event: str, reason: str) -> dict:
    message = f"Constellation INCOMPLETE: {reason}. No task closure was approved; inspect the installation."
    if event == "PreToolUse":
        return {"hookSpecificOutput": {"hookEventName": event, "permissionDecision": "deny",
                                       "permissionDecisionReason": message}}
    # Installation failures have no validated task state with which to bound a
    # Stop retry. Report incompleteness without creating an endless stop loop.
    return {"systemMessage": message}


def _deadline(_signum: int, _frame: object) -> None:
    raise EntryError("installation verification exceeded its internal deadline")


def main() -> int:
    event = sys.argv[1] if len(sys.argv) > 1 else ""
    descriptor = None
    previous_handler = None
    try:
        if event not in EVENTS:
            raise EntryError("invalid hook event")
        if sys.version_info < (3, 11):
            raise EntryError("Python 3.11 or newer is required")
        # The existing hooks.py arms its own eight-second budget on entering main;
        # verification and module loading have a separate one-second maximum.
        previous_handler = signal.signal(signal.SIGALRM, _deadline)
        signal.setitimer(signal.ITIMER_REAL, CHECK_SECONDS)
        entry = Path(__file__).absolute()
        home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").absolute()
        if home.is_symlink() or entry != _path(home, "constellation/hook.py"):
            raise EntryError("stable entry is outside the installation")
        lock = _path(home, "constellation/.install.lock")
        descriptor = os.open(lock, os.O_RDONLY | os.O_NOFOLLOW)
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise EntryError("installation lock is not regular")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise EntryError("installation update is in progress; retry after it finishes") from exc
        hook = _verified_hook(home, entry)
        # No receipt-supplied paths, payload fields, cwd or PYTHONPATH select code.
        # Retain LOCK_SH through all lazy runtime imports and event evaluation.
        sys.argv[0] = str(hook)
        runpy.run_path(str(hook), run_name="__main__")
        return 0
    except EntryError as exc:
        result = _failure(event, str(exc))
    except Exception:
        result = _failure(event, "installation could not be verified")
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        if previous_handler is not None:
            signal.signal(signal.SIGALRM, previous_handler)
        if descriptor is not None:
            os.close(descriptor)
    print(json.dumps(result, ensure_ascii=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Translate native Claude events to the existing Constellation evidence engine.

The CLI validates the complete release using only the standard library before
importing package code. Native events contribute structural metadata only; no
prompt, transcript, message or edited content crosses the adapter.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack, contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import signal
import stat
import sys
from typing import Any, Iterator

sys.dont_write_bytecode = True

# The builder replaces this fixed-sibling source import with the complete
# standard-library helper body. Distributed bootstraps import no package code
# before their release and ownership metadata have been checked.
# BEGIN CONSTELLATION PLATFORM SUPPORT
if __package__:
    from .platform_support import (
        IS_WINDOWS, PlatformError, _ps_guard_parents, file_lock, is_reparse,
        logical_mode, open_regular, validate_windows_relative, verify_access,
    )
else:
    _source_directory = str(Path(__file__).resolve().parent)
    sys.path.insert(0, _source_directory)
    try:
        from platform_support import (
            IS_WINDOWS, PlatformError, _ps_guard_parents, file_lock, is_reparse,
            logical_mode, open_regular, validate_windows_relative, verify_access,
        )
    finally:
        sys.path.remove(_source_directory)
# END CONSTELLATION PLATFORM SUPPORT
EVENTS = frozenset({"SessionStart", "UserPromptSubmit", "PreToolUse", "SubagentStart", "SubagentStop", "Stop"})
FILE_TOOLS = {"Write": "file_path", "Edit": "file_path", "MultiEdit": "file_path", "NotebookEdit": "notebook_path"}
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,120}\Z")
MARKER = ".constellation-install.json"
MAX_METADATA_BYTES = 1024 * 1024
PYTHON_REQUIREMENT = (
    "Constellation INCOMPLETE: Python 3.11 or newer is required. "
    "Set PATH for Claude so its hook's Python executable selects a supported interpreter, then restart Claude."
)


class AdapterError(ValueError):
    """A fixed diagnostic, never an event or source-code excerpt."""


def _object(path: Path) -> dict[str, Any]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise AdapterError("Duplicate release metadata.")
            value[key] = item
        return value

    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1 or metadata.st_size > MAX_METADATA_BYTES:
        raise AdapterError("Release metadata is unavailable or unsafe.")
    _release_access(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise AdapterError("Release metadata is invalid.") from exc
    if not isinstance(value, dict):
        raise AdapterError("Release metadata must be an object.")
    return value


def _windows_lookup(value: str) -> None:
    """Reject Windows aliases before any lookup can normalize them away."""
    if not IS_WINDOWS:
        return
    from pathlib import PureWindowsPath

    candidate = PureWindowsPath(value)
    if (candidate.anchor.startswith(("\\\\", "//"))
            or (candidate.drive and not candidate.is_absolute())
            or (candidate.root and not candidate.drive)):
        raise AdapterError("Native path has an ambiguous Windows anchor.")
    parts = candidate.parts[1:] if candidate.is_absolute() else candidate.parts
    if not parts:
        if candidate.is_absolute():
            return
        raise AdapterError("Native path has no Windows file component.")
    try:
        validate_windows_relative("/".join(parts))
    except (PlatformError, ValueError) as exc:
        raise AdapterError("Native path has an unsafe Windows component.") from exc


def _unlinked_lookup(path: Path) -> None:
    """Inspect the original absolute Windows lookup before resolving aliases."""
    if not IS_WINDOWS:
        return
    if path.parts:
        _windows_lookup(str(path))
    # absolute() anchors a relative lookup at its original cwd without resolving
    # reparse points. Skipping this step would drop its first path component.
    path = path.absolute()
    _windows_lookup(str(path))
    current = Path(path.anchor)
    if is_reparse(current):
        raise AdapterError("Native lookup traverses a reparse point.")
    for component in path.parts[1:]:
        current /= component
        if is_reparse(current):
            raise AdapterError("Native lookup traverses a reparse point.")


def _release_access(path: Path, *, private: bool = False) -> None:
    """Reject foreign mutation rights before using a release lookup."""
    try:
        verify_access(path, private=private)
    except PlatformError as exc:
        raise AdapterError("Release filesystem permissions are unsafe.") from exc


def _release_mode(path: Path, expected: int, *, private: bool = False) -> int:
    """Bind package modes to real permissions on each supported filesystem."""
    _release_access(path, private=private)
    try:
        return logical_mode(path, expected=expected)
    except PlatformError as exc:
        raise AdapterError("Release filesystem permissions are unsafe.") from exc


def _resource(root: Path, relative: str) -> Path:
    if IS_WINDOWS:
        try:
            validate_windows_relative(relative)
        except (PlatformError, ValueError) as exc:
            raise AdapterError("Release contains an unsafe Windows path.") from exc
    path = Path(relative)
    if (not relative or path.is_absolute() or path.as_posix() != relative
            or any(part in {".", ".."} for part in path.parts)):
        raise AdapterError("Release contains an unsafe path.")
    current = root
    for part in path.parts:
        current /= part
        if is_reparse(current):
            raise AdapterError("Release contains a symbolic link or reparse point.")
    return current


def _verify_release(root: Path, *, installed: bool) -> dict[str, Any]:
    """Bind all executable resources before the first package import."""
    _unlinked_lookup(root)
    if is_reparse(root) or not root.is_dir():
        raise AdapterError("Release directory is missing or linked.")
    _release_access(root)
    manifest = _object(_resource(root, "bundle.json"))
    if (set(manifest) != {"schema", "modules", "files"} or type(manifest["schema"]) is not int
            or manifest["schema"] != 1 or not isinstance(manifest["modules"], list)
            or not manifest["modules"] or not all(isinstance(item, str) for item in manifest["modules"])
            or len(set(manifest["modules"])) != len(manifest["modules"])
            or not set(manifest["modules"]) <= {"coding", "mathematics", "quant-research", "writter"}
            or not isinstance(manifest["files"], dict) or not manifest["files"]):
        raise AdapterError("Release manifest is invalid.")
    for relative, record in manifest["files"].items():
        if (not isinstance(relative, str) or not isinstance(record, dict)
                or set(record) != {"sha256", "mode"}
                or not isinstance(record["sha256"], str)
                or not re.fullmatch(r"[0-9a-f]{64}", record["sha256"])
                or type(record["mode"]) is not int or record["mode"] not in {0o644, 0o755}):
            raise AdapterError("Release inventory is invalid.")
        path = _resource(root, relative)
        metadata = path.lstat()
        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1
                or _release_mode(path, record["mode"]) != record["mode"]
                or hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]):
            raise AdapterError("Release resources are incomplete or modified.")
    actual: set[str] = set()
    for directory, subdirs, names in os.walk(root, followlinks=False):
        _release_access(Path(directory))
        for name in subdirs + names:
            if is_reparse(Path(directory) / name):
                raise AdapterError("Release contains a symbolic link or reparse point.")
        actual.update((Path(directory) / name).relative_to(root).as_posix() for name in names)
    expected = set(manifest["files"]) | {"bundle.json"}
    if installed:
        expected.add(MARKER)
    if actual != expected or "ecosystem/claude_hooks.py" not in manifest["files"]:
        raise AdapterError("Release has unexpected or missing resources.")
    native = _object(_resource(root, ".claude-plugin/plugin.json"))
    codex = _object(_resource(root, ".codex-plugin/plugin.json"))
    version = native.get("version")
    if (native.get("name") != "constellation" or codex.get("name") != "constellation"
            or not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", version)
            or version != codex.get("version")):
        raise AdapterError("Native release identities disagree.")
    if installed:
        marker_path = _resource(root, MARKER)
        receipt = _object(marker_path)
        if (set(receipt) != {"schema", "owner", "plugin_id", "version", "modules", "bundle_sha256"}
                or type(receipt["schema"]) is not int or receipt["schema"] != 1
                or receipt["owner"] != "constellation-claude-skills-dir"
                or receipt["plugin_id"] != "constellation@skills-dir"
                or receipt["version"] != native.get("version") or receipt["modules"] != manifest["modules"]
                or _release_mode(marker_path, 0o600, private=True) != 0o600
                or receipt["bundle_sha256"] != hashlib.sha256((root / "bundle.json").read_bytes()).hexdigest()):
            raise AdapterError("Installed release ownership is invalid.")
    return manifest


def _is_managed_root(root: Path) -> bool:
    """Classify managed names using the host filesystem's case semantics."""
    name, parent = root.name, root.parent.name
    if IS_WINDOWS:
        name, parent = name.casefold(), parent.casefold()
    return name == "constellation" and parent == "skills"


@contextmanager
def verified_release(root: Path) -> Iterator[dict[str, Any]]:
    """Hold a real shared installation lock through verification and dispatch."""
    _unlinked_lookup(root)
    if is_reparse(root):
        raise AdapterError("Release directory is linked.")
    root = root.resolve(strict=True)
    installed = _is_managed_root(root)
    with ExitStack() as held:
        if IS_WINDOWS:
            # Keep every original lookup directory, including the release root,
            # pinned against rename until verified dispatch has completed.
            held.enter_context(_ps_guard_parents(root / "bundle.json"))
        if installed:
            home = root.parent.parent
            # A foreign writer on a parent could replace a verified child tree
            # without changing the child's current hashes or file ACLs.
            _release_access(home)
            _release_access(root.parent)
            _release_access(home / "constellation", private=True)
            lock = _resource(home, "constellation/.install.lock")
            metadata = lock.lstat()
            if (not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1
                    or _release_mode(lock, 0o600, private=True) != 0o600):
                raise AdapterError("Installation lock is unsafe.")
            try:
                descriptor = open_regular(lock, os.O_RDONLY, mode=0o600, private=True)
            except PlatformError as exc:
                raise AdapterError("Installation lock is unsafe.") from exc
            held.callback(os.close, descriptor)
            opened = os.fstat(descriptor)
            if (opened.st_dev, opened.st_ino) != (metadata.st_dev, metadata.st_ino):
                raise AdapterError("Installation lock changed.")
            held.enter_context(file_lock(descriptor, exclusive=False, blocking=False))
        elif IS_WINDOWS:
            # DELETE_CHILD and ADD_SUBDIRECTORY on the parent can replace an
            # otherwise protected explicit --plugin-dir release. Parent pinning
            # and its access policy are complementary guarantees.
            _release_access(root.parent)
        yield _verify_release(root, installed=installed)


def _identity(value: Any) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise AdapterError("Native identity is missing or invalid.")
    return value


def _context(event: str, message: str) -> dict[str, Any]:
    return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": message}}


def _command_line(arguments: list[str]) -> str:
    """Format guidance for the native shell without interpolating path contents."""
    if IS_WINDOWS:
        return "& " + " ".join("'" + value.replace("'", "''") + "'" for value in arguments)
    return shlex.join(arguments)


def _command_argument(value: str) -> str:
    return "'" + value.replace("'", "''") + "'" if IS_WINDOWS else shlex.quote(value)


def _bootstrap(event: str, native: str, session: str, root: Path, *,
               include_method_guidance: bool = True) -> str:
    from ecosystem.hooks import METHOD_GUIDANCE

    command = _command_line([sys.executable, "-I", str(root / "ecosystem/cli.py")])
    method = METHOD_GUIDANCE + " " if include_method_guidance else ""
    return (
        f"Constellation shared research environment. Your lifecycle identity is {session!r}; "
        f"your actual native author/reviewer identity is {native!r}. Shared CLI: {command}. "
        f"For Git use {command} git --root PROJECT --session {_command_argument(session)} OPERATION; "
        "for non-Git research use the same CLI's portable protocol with explicit session_id. "
        f"Read {str(root / 'ecosystem/references/protocol.md')!r} for that protocol. "
        "Use a project's existing workflow and policies when supplied; do not create duplicate contracts. "
        "Brief questions need no persistent task. Substantial research declares requirements, hypotheses, "
        "sources and acceptance checks; keep proof, calculation and empirical evidence distinct. "
        "Use native agents with exclusive scopes and real identities; inherit session model, effort and "
        "permissions and respect the effective client capacity. Findings, stale evidence and failed checks "
        "remain open until independently verified. Shared gates, not Stop alone, determine completion. "
        "Hooks do not start tasks, fetch, install, publish or confine arbitrary shell/MCP writes. "
        + method + "In Claude, invoke the native Skill tool for the relevant available entry; "
        "if that entry cannot be invoked, read its SKILL.md with an available tool."
    )


def handle_event(payload: Any, state_dir: Path | None = None,
                 expected_event: str | None = None, *, package_root: Path | None = None) -> dict[str, Any]:
    """Adapt structural Claude fields; the existing engine retains all authority."""
    owner = os.environ.get("CONSTELLATION_HOOK_OWNER", "shared")
    if owner == "project":
        return {}
    if owner != "shared":
        raise AdapterError("Hook owner must be shared or project.")
    if not isinstance(payload, dict):
        raise AdapterError("Expected a native JSON event object.")
    event = payload.get("hook_event_name")
    if (not isinstance(event, str) or event not in EVENTS
            or (expected_event is not None and event != expected_event)):
        raise AdapterError("Native event does not match its registered handler.")
    native = _identity(payload.get("session_id"))
    session = "claude-" + native
    raw_cwd = payload.get("cwd")
    if (not isinstance(raw_cwd, str) or not raw_cwd or len(raw_cwd) > 4096
            or any(ord(char) < 32 for char in raw_cwd) or not Path(raw_cwd).is_absolute()):
        raise AdapterError("Expected an absolute native working directory.")
    _unlinked_lookup(Path(raw_cwd))
    cwd = Path(raw_cwd).resolve(strict=True)
    if not cwd.is_dir():
        raise AdapterError("Native working directory is unavailable.")
    root = package_root if package_root is not None else Path(__file__).resolve().parent.parent
    if event == "SessionStart":
        return _context(event, _bootstrap(event, native, session, root))
    clean: dict[str, Any] = {"hook_event_name": event, "session_id": session,
                             "cwd": str(cwd), "turn_id": "claude-native"}
    if event == "PreToolUse":
        tool = payload.get("tool_name")
        if not isinstance(tool, str) or tool not in FILE_TOOLS:
            raise AdapterError("Expected a registered native file-editing tool.")
        inputs = payload.get("tool_input")
        name = inputs.get(FILE_TOOLS[tool]) if isinstance(inputs, dict) else None
        if (not isinstance(name, str) or not name or name != name.strip()
                or any(ord(char) < 32 for char in name) or ".." in Path(name).parts):
            raise AdapterError("Native file-tool path is invalid.")
        _windows_lookup(name)
        target = Path(name) if Path(name).is_absolute() else cwd / name
        clean.update(tool_name="apply_patch", tool_input=(
            f"*** Begin Patch\n*** Update File: {target}\n*** End Patch"))
    elif event in {"SubagentStart", "SubagentStop"}:
        clean["agent_id"] = _identity(payload.get("agent_id"))
    if event == "Stop":
        active = payload.get("stop_hook_active", False)
        if not isinstance(active, bool):
            raise AdapterError("Native stop continuation flag is invalid.")
        clean["stop_hook_active"] = active
    from ecosystem import hooks
    result = hooks.handle_event(clean, state_dir, event)
    if event == "UserPromptSubmit":
        details = result.get("hookSpecificOutput")
        if not result:
            return _context(event, _bootstrap(event, native, session, root))
        if isinstance(details, dict) and details.get("hookEventName") == event:
            details["additionalContext"] = str(details.get("additionalContext", "")) + " " + _bootstrap(
                event, native, session, root, include_method_guidance=False)
    return result


def _failure(event: str, message: str | None = None) -> dict[str, Any]:
    message = message or "Constellation INCOMPLETE: the Claude hook or verified release is unavailable. Inspect installation and task state."
    if event == "PreToolUse":
        return {"hookSpecificOutput": {"hookEventName": event, "permissionDecision": "deny", "permissionDecisionReason": message}}
    return {"systemMessage": message}


def _timed_out(_signum: int, _frame: Any) -> None:
    raise AdapterError("Hook evaluation exceeded its deadline.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("event", choices=sorted(EVENTS))
    parser.add_argument("--state-dir", type=Path, help="Explicit isolated portable state location")
    args = parser.parse_args(argv)
    # A project-owned adapter must not load or compete with this lifecycle.
    if os.environ.get("CONSTELLATION_HOOK_OWNER") == "project":
        print("{}")
        return 0
    if sys.version_info < (3, 11):
        if args.event == "UserPromptSubmit":
            print(PYTHON_REQUIREMENT, file=sys.stderr)
            return 2
        print(json.dumps(_failure(args.event, PYTHON_REQUIREMENT), ensure_ascii=True, separators=(",", ":")))
        return 0
    timer_supported = hasattr(signal, "SIGALRM") and hasattr(signal, "setitimer")
    previous_handler = None
    timer_armed = False
    try:
        if timer_supported:
            previous_handler = signal.signal(signal.SIGALRM, _timed_out)
            signal.setitimer(signal.ITIMER_REAL, 8.0)
            timer_armed = True
        root = Path(__file__).absolute().parent.parent
        with verified_release(root):
            # Only a verified sibling directory enters sys.path, never event cwd.
            sys.path.insert(0, str(root))
            from ecosystem import hooks
            result = handle_event(hooks.read_payload(sys.stdin.buffer), args.state_dir, args.event,
                                  package_root=root)
    except Exception:
        if args.event == "UserPromptSubmit":
            print("Constellation: Claude prompt hook validation failed; task remains incomplete.", file=sys.stderr)
            return 2
        result = _failure(args.event)
    finally:
        if timer_armed:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous_handler)
    print(json.dumps(result, ensure_ascii=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

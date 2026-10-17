#!/usr/bin/env python3
"""Narrow, advisory Codex lifecycle adapter for explicitly registered tasks.

The command loads only its installed sibling engine. Event data selects registered
state and never executable code. Neither prompt nor transcript fields are used.
Tool coverage is limited to apply_patch; this is not a sandbox for shell or MCP.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import signal
import stat
import sys
from typing import Any, BinaryIO

# The manifest invokes Python in isolated mode. Reintroduce only our fixed code
# directory, never the event cwd or a directory supplied through the payload.
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

MAX_INPUT_BYTES = 1024 * 1024
MAX_PATCH_PATHS = 4096
EVENTS = frozenset({"UserPromptSubmit", "PreToolUse", "SubagentStart", "SubagentStop", "Stop"})
PATCH_TOOL = re.compile(r"^(?:[A-Za-z0-9_]+[.:])*(?:apply_patch|Edit|Write)$")
IDENTIFIER = re.compile(r"^[A-Za-z0-9_.:-]{1,200}$")
LIMITS = (
    "Constellation only checks registered task metadata and apply_patch paths. "
    "Shell, MCP and other tool paths remain outside this guard; client permissions "
    "and independent review still apply. Tool events do not identify the agent; "
    "path scope is shared by the active tasks in this session."
)


class HookError(Exception):
    """An adapter failure with a fixed, payload-free diagnostic."""


def _identifier(value: Any) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise HookError("invalid event identifier")
    return value


def _cwd(value: Any) -> Path:
    if not isinstance(value, str) or not value or len(value) > 4096:
        raise HookError("invalid event working directory")
    if any(ord(char) < 32 for char in value) or not Path(value).is_absolute():
        raise HookError("invalid event working directory")
    root = Path(value).resolve(strict=True)
    if not root.is_dir():
        raise HookError("event working directory is not a directory")
    return root


def _warning(reason: str) -> dict[str, Any]:
    return {"systemMessage": f"Constellation INCOMPLETE: {reason}. No task closure was approved. {LIMITS}"}


def _context(event: str, message: str) -> dict[str, Any]:
    return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": message}}


def _deny(reason: str) -> dict[str, Any]:
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "deny",
        "permissionDecisionReason": f"Constellation: {reason}. Declare the intended exact paths before editing.",
    }}


def _request_id(payload: dict[str, Any], task: dict[str, Any]) -> str:
    # Include only documented metadata; never fingerprint a prompt or transcript.
    fields = [payload["hook_event_name"], _identifier(payload.get("turn_id")),
              task["session_id"], task["task_id"]]
    if payload["hook_event_name"] in {"SubagentStart", "SubagentStop"}:
        fields.append(_identifier(payload.get("agent_id")))
    if payload["hook_event_name"] == "Stop":
        active = payload.get("stop_hook_active", False)
        if not isinstance(active, bool):
            raise HookError("invalid stop continuation metadata")
        fields.append(active)
    digest = hashlib.sha256(json.dumps(fields, separators=(",", ":")).encode()).hexdigest()
    return "hook-" + digest


def patch_paths(command: Any) -> list[str]:
    """Extract every edit and rename endpoint, rejecting ambiguous envelopes."""
    if not isinstance(command, str) or not command or "\x00" in command:
        raise HookError("patch input is missing or malformed")
    lines = command.strip().split("\n")
    lines = [line.removesuffix("\r") for line in lines]
    if len(lines) < 3 or lines[0] != "*** Begin Patch" or lines[-1] != "*** End Patch":
        raise HookError("patch envelope is not supported")
    paths: list[str] = []
    operation: str | None = None
    move_allowed = False
    for line in lines[1:-1]:
        matched = False
        for prefix, kind in (("*** Add File: ", "add"), ("*** Update File: ", "update"),
                             ("*** Delete File: ", "delete"), ("*** Move to: ", "move")):
            if line.startswith(prefix):
                if kind == "move" and not move_allowed:
                    raise HookError("patch rename is not attached to an update")
                name = line[len(prefix):]
                if not name or name != name.strip() or any(ord(char) < 32 for char in name):
                    raise HookError("patch contains an ambiguous path")
                paths.append(name)
                if len(paths) > MAX_PATCH_PATHS:
                    raise HookError("patch exceeds the path limit")
                move_allowed = kind == "update"
                if kind != "move":
                    operation = kind
                matched = True
                break
        if matched:
            continue
        if operation is None or (line.startswith("*** ") and line != "*** End of File"):
            raise HookError("patch structure is not supported")
        move_allowed = False
    if not paths:
        raise HookError("patch declares no file operations")
    return paths


def _original_patch_target(cwd: Path, name: str) -> Path:
    """Validate original lookup components before cancelling any parent steps.

    In a/../file, a must be an existing real directory. Cancelling that pair
    lexically first would hide symlinks and could authorize a different file.
    Starting at the filesystem anchor also checks every physical cwd ancestor.
    """
    lookup = cwd / name
    if not lookup.is_absolute() or lookup.anchor.startswith(("//", "\\\\")):
        raise HookError("patch path has an ambiguous filesystem anchor")
    current = Path(lookup.anchor)
    components = lookup.parts[1:]
    for index, component in enumerate(components):
        if component == "..":
            current = current.parent
            continue
        current = current / component
        remaining = components[index + 1:]
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            # Add operations may create parents. A parent step through a missing
            # directory is not an equivalent lookup and must not be simplified.
            if ".." in remaining:
                raise HookError("patch parent traversal crosses a missing directory") from None
            return current.joinpath(*remaining)
        if stat.S_ISLNK(metadata.st_mode):
            raise HookError("patch path traverses a symbolic link")
        if remaining and not stat.S_ISDIR(metadata.st_mode):
            raise HookError("patch path traverses a non-directory")
    return current


def _guard_patch(payload: dict[str, Any], tasks: list[dict[str, Any]], cwd: Path,
                 state_dir: Path, engine_type: Any) -> dict[str, Any]:
    if not isinstance(payload.get("tool_name"), str) or not PATCH_TOOL.fullmatch(payload["tool_name"]):
        return {}
    tool_input = payload.get("tool_input")
    try:
        if not isinstance(tool_input, dict):
            raise HookError("patch input is not an object")
        paths = patch_paths(tool_input.get("command"))
        scopes: dict[Path, set[str]] = {}
        for task in tasks:
            root = Path(task["root"]).resolve(strict=True)
            scopes.setdefault(root, set()).update(task["paths"])
        for name in paths:
            candidate = _original_patch_target(cwd, name)
            permitted = False
            for root, allowed in scopes.items():
                try:
                    relative = candidate.relative_to(root).as_posix()
                except ValueError:
                    continue
                if relative not in allowed:
                    continue
                engine_type(root, state_dir).validate_path(relative)
                permitted = True
                break
            if not permitted:
                return _deny("patch touches a path outside the registered scope")
        return {}
    except Exception:
        # Inputs and engine exception text may contain private material. Do not
        # echo them into the client or persist the patch body.
        return _deny("the registered patch scope could not be verified")


def handle_event(payload: dict[str, Any], state_dir: Path | None = None,
                 expected_event: str | None = None) -> dict[str, Any]:
    """Handle a documented event without assuming a role absent from its schema."""
    if not isinstance(payload, dict):
        raise HookError("hook input must be a JSON object")
    event = payload.get("hook_event_name")
    if not isinstance(event, str) or event not in EVENTS:
        return _warning("unsupported hook event; no state changed")
    if expected_event is not None and event != expected_event:
        raise HookError("hook event does not match its registered handler")
    session = _identifier(payload.get("session_id"))
    cwd = _cwd(payload.get("cwd"))
    from ecosystem.core import Engine, default_state_dir, discover_active
    state_dir = state_dir if state_dir is not None else default_state_dir()
    discovered = discover_active(state_dir, session, cwd)
    # An explicit complete/partial close ends the hook scope. Later unrelated
    # work must not inherit it; reopening a task is an explicit CLI operation.
    tasks = [task for task in discovered["tasks"] if task["status"] == "active"]
    if not tasks:
        return {}
    if event == "PreToolUse":
        return _guard_patch(payload, tasks, cwd, state_dir, Engine)
    if event == "UserPromptSubmit":
        return _context(event,
            "Constellation has registered tasks for this session and directory. "
            "Use the explicit skill/CLI protocol to inspect or revise their obligations. "
            "This hook does not infer a profile or scope from the prompt. " + LIMITS)
    if event in {"SubagentStart", "SubagentStop"}:
        if len(tasks) != 1:
            return _warning("subagent event is ambiguous across registered tasks; no attribution recorded")
        task = tasks[0]
        agent = _identifier(payload.get("agent_id"))
        request = {"session_id": session, "task_id": task["task_id"],
                   "expected_revision": task["revision"], "request_id": _request_id(payload, task),
                   "observed_agent_id": agent, "event": "start" if event == "SubagentStart" else "stop"}
        Engine(Path(task["root"]), state_dir).execute("observe-agent", request)
        if event == "SubagentStart":
            return _context(event,
                "Constellation observed this native subagent for one registered task. "
                "Observation grants no role or file ownership: the coordinator must explicitly "
                "register your native ID and assign paths. Preserve other agents' work, "
                "return evidence, and leave publication to the coordinator. " + LIMITS)
        return {}
    if len(tasks) != 1:
        return _warning("Stop is ambiguous across registered tasks; inspect and close each task explicitly")
    task = tasks[0]
    outcome = Engine(Path(task["root"]), state_dir).execute("hook-stop", {
        "session_id": session, "task_id": task["task_id"],
        "expected_revision": task["revision"], "request_id": _request_id(payload, task),
    })
    if outcome.get("decision") == "complete":
        return {}
    if outcome.get("decision") == "continue" and not outcome.get("replayed", False):
        return {"decision": "block", "reason":
                "Constellation has unfinished registered obligations. Inspect task status, "
                "complete the remaining authorized work and its independent verification, "
                "then close the task through the explicit CLI. If completion is unavailable, "
                "report the pending obligations and close as partial. This hook starts no agents, "
                "checks or commits; it requests at most two continuations per task."}
    return _warning("registered obligations remain pending or this Stop event was already handled; "
                    "report the pending work explicitly and use the CLI for partial closure")


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise HookError("hook input contains duplicate JSON keys")
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    raise HookError("hook input contains a nonfinite JSON number")


def read_payload(stream: BinaryIO) -> dict[str, Any]:
    raw = stream.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise HookError("hook input exceeds the byte limit")
    try:
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_object,
                             parse_constant=_reject_constant)
    except (ValueError, UnicodeError, RecursionError):
        raise HookError("hook input is not strict UTF-8 JSON") from None
    if not isinstance(payload, dict):
        raise HookError("hook input must be a JSON object")
    return payload


def _timed_out(_signum: int, _frame: Any) -> None:
    raise HookError("hook evaluation exceeded its internal deadline")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("event", choices=sorted(EVENTS))
    parser.add_argument("--state-dir", type=Path, help="Explicit state location for isolated checks")
    args = parser.parse_args(argv)
    if sys.version_info < (3, 11):
        print(json.dumps(_warning("Python 3.11 or newer is required")))
        return 0
    timer_supported = hasattr(signal, "SIGALRM") and hasattr(signal, "setitimer")
    previous_handler = None
    timer_armed = False
    try:
        if timer_supported:
            previous_handler = signal.signal(signal.SIGALRM, _timed_out)
            signal.setitimer(signal.ITIMER_REAL, 8.0)
            timer_armed = True
        result = handle_event(read_payload(sys.stdin.buffer), args.state_dir, args.event)
    except HookError as exc:
        result = _warning(str(exc))
    except Exception:
        result = _warning("hook evaluation failed; inspect task state explicitly")
    finally:
        if timer_armed:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous_handler)
    print(json.dumps(result, ensure_ascii=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

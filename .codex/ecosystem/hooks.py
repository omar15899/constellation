#!/usr/bin/env python3
"""One Codex lifecycle adapter for explicitly registered Git or portable tasks.

The command loads only its installed sibling engine. Event data selects registered
state and never executable code. Neither prompt nor transcript fields are used.
Discovery never starts a contract, fetches Git or loads code from a project.
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


def _failure(event: str, reason: str) -> dict[str, Any]:
    # A broken discovery path cannot silently turn a registered edit guard off.
    return _deny(reason) if event == "PreToolUse" else _warning(reason)


def _patch_command(payload: dict[str, Any]) -> str:
    inputs = payload.get("tool_input")
    if isinstance(inputs, str):
        return inputs
    if not isinstance(inputs, dict):
        raise HookError("patch input is not an object or string")
    values = [inputs[key] for key in ("input", "patch", "command") if key in inputs]
    if not values or not all(isinstance(value, str) for value in values):
        raise HookError("patch input is missing or malformed")
    if any(value != values[0] for value in values):
        raise HookError("patch input has conflicting representations")
    return values[0]


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


def _original_patch_target(cwd: Path, name: str, *, deleting: bool = False) -> Path:
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
            if deleting and not remaining:
                return current
            raise HookError("patch path traverses a symbolic link")
        if remaining and not stat.S_ISDIR(metadata.st_mode):
            raise HookError("patch path traverses a non-directory")
    return current


def _guard_patch(payload: dict[str, Any], tasks: list[dict[str, Any]], cwd: Path,
                 state_dir: Path, engine_type: Any) -> dict[str, Any]:
    if not isinstance(payload.get("tool_name"), str) or not PATCH_TOOL.fullmatch(payload["tool_name"]):
        return {}
    try:
        paths = patch_paths(_patch_command(payload))
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
    except HookError as exc:
        return _deny(str(exc))
    except Exception:
        # Inputs and engine exception text may contain private material. Do not
        # echo them into the client or persist the patch body.
        return _deny("the registered patch scope could not be verified")


def _git_state(path: Path) -> dict[str, Any] | None:
    """Read bounded lifecycle metadata, without following an alternate state file."""
    if not path.exists() and not path.is_symlink():
        return None
    if path.parent.is_symlink() or not path.parent.is_dir() or path.is_symlink() or not path.is_file():
        raise HookError("Git lifecycle state is not a regular local file")
    with path.open("rb") as stream:
        state = read_payload(stream)
    return state


def _git_contracts(cwd: Path, session: str) -> list[dict[str, Any]]:
    """Discover existing owners and containing workspace tasks without creating state.

    The only project input used here is data. The Git implementation comes from
    the installed package, and no project Python module is imported or executed.
    A workspace and its per-repository contracts are one lifecycle, not rivals.
    """
    roots = [root for root in (cwd, *cwd.parents)
             if (root / ".git").exists() or (root / ".git").is_symlink()]
    if not roots:
        return []
    from ecosystem.runtime.workflow import Workflow

    owner = roots[0]
    workflows: dict[Path, dict[str, Any]] = {}
    workspaces: list[dict[str, Any]] = []
    for root in roots:
        if (root / ".git").is_symlink():
            raise HookError("Git metadata must not be a symbolic link")
        flow = Workflow(root, session, create_state=False)
        manifest = flow.home / f"workspace-{flow.key}.json"
        state = _git_state(manifest)
        if state is not None and not state.get("finished"):
            members = state.get("roots")
            if state.get("schema_version") != 1 or not isinstance(members, list) or not members:
                raise HookError("workspace lifecycle metadata is malformed")
            boundaries: list[Path] = []
            for member in members:
                if not isinstance(member, str) or not member or Path(member).is_absolute() or ".." in Path(member).parts:
                    raise HookError("workspace ownership metadata is malformed")
                target = root / member
                if target.resolve() != target or not target.is_dir():
                    raise HookError("workspace ownership boundary is unavailable")
                boundaries.append(target)
            # The coordinator may operate from the workspace root even if the
            # hub itself is not a participant. An unrelated child is excluded.
            if owner == root or owner in boundaries:
                workspaces.append({"kind": "workspace", "root": root,
                                   "members": boundaries, "state": state})
        state = _git_state(flow.path)
        if state is not None:
            if not isinstance(state.get("requirements"), list) or not all(
                    isinstance(item, str) for item in state["requirements"]):
                raise HookError("Git lifecycle requirements are malformed")
            if root == owner and state["requirements"] and not state.get("finished"):
                workflows[root] = {"kind": "repository", "root": root, "state": state}
    covered = {member for workspace in workspaces for member in workspace["members"]}
    return workspaces + [flow for root, flow in workflows.items() if root not in covered]


def _legacy_contract(root: Path, session: str) -> dict[str, Any] | None:
    """Read the isolated OmarOS migration contract as data, never project code.

    This compatibility reader authorizes only exact patch paths. Domain checks,
    review and publication remain with the recipient's existing lifecycle.
    """
    from ecosystem.runtime.workflow import Workflow

    flow = Workflow(root, session, create_state=False)
    path = flow.home.parent / "omaros" / f"{flow.key}.json"
    state = _git_state(path)
    if state is None or state.get("finished"):
        return None
    requirements = state.get("requirements")
    if not isinstance(requirements, list) or not all(isinstance(item, str) and item.strip() for item in requirements):
        raise HookError("legacy recipient requirements are malformed")
    if not requirements:
        return None
    return {"kind": "legacy-omaros", "root": root, "state": state}


def _guard_legacy(contract: dict[str, Any], actions: list[tuple[str, Path]]) -> None:
    from ecosystem.runtime.workflow import publication_target, safe_path

    root, state = contract["root"], contract["state"]
    paths, deletions = state.get("paths"), state.get("deletions", [])
    if (not isinstance(paths, list) or not all(isinstance(name, str) for name in paths)
            or len(set(paths)) != len(paths) or not isinstance(deletions, list)
            or not all(isinstance(name, str) for name in deletions) or not set(deletions) <= set(paths)
            or state.get("sync_error") or not isinstance(state.get("sync"), dict)):
        raise HookError("legacy recipient needs an exact plan and successful upstream check")
    if state.get("target") != publication_target(root):
        raise HookError("legacy recipient publication target changed")
    sync = state["sync"]
    if (not isinstance(sync.get("checked_at"), str) or not sync["checked_at"]
            or not isinstance(sync.get("head"), str) or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", sync["head"])
            or type(sync.get("behind")) is not int or sync["behind"] != 0
            or any(sync.get(key) != value for key, value in state["target"].items())):
        raise HookError("legacy recipient upstream evidence is incomplete or inconsistent")
    for action, target in actions:
        name = target.relative_to(root).as_posix()
        # These private export boundaries are retained by the legacy vault.
        # No knowledge content or baseline-private inventory is consulted.
        private = name.lower()
        if (private.startswith((".claude/logs/", "09_data_sources/email_exports/by_message/",
                                "09_data_sources/email_exports/snapshots/", "09_data_sources/email_exports/backfill/",
                                "11_documents_and_reports/email/"))
                or private == "09_data_sources/email_exports/index.json"):
            raise HookError("legacy recipient path is private")
        if name not in paths or (name in deletions and action != "Delete File"):
            raise HookError("legacy recipient path is outside its declared scope")
        # OmarOS does not allow symlink artifacts, including deletion targets.
        safe_path(root, name)


def _guard_git(payload: dict[str, Any], contract: dict[str, Any], cwd: Path,
               session: str, state_dir: Path) -> dict[str, Any]:
    from ecosystem.core import discover_active
    from ecosystem.runtime.workflow import Workflow, owner_root

    if not isinstance(payload.get("tool_name"), str) or not PATCH_TOOL.fullmatch(payload["tool_name"]):
        return {}
    try:
        command = _patch_command(payload)
        patch_paths(command)
        groups: dict[tuple[str, Path], tuple[dict[str, Any], list[tuple[str, Path]]]] = {}
        for action, name in re.findall(r"^\*\*\* (Add File|Update File|Delete File|Move to): (.+)$", command, re.M):
            target = _original_patch_target(cwd, name.removesuffix("\r"), deleting=action == "Delete File")
            recipient = contract
            if not target.is_relative_to(contract["root"]):
                owner = owner_root(target.parent)
                candidates = _git_contracts(owner, session)
                legacy = _legacy_contract(owner, session)
                if legacy is not None:
                    candidates.append(legacy)
                if len(candidates) != 1 or discover_active(state_dir, session, owner)["tasks"]:
                    raise HookError("external patch owner has no unambiguous active Git contract")
                recipient = candidates[0]
            key = (recipient["kind"], recipient["root"])
            groups.setdefault(key, (recipient, []))[1].append((action, target))
        for recipient, actions in groups.values():
            if recipient["kind"] == "legacy-omaros":
                _guard_legacy(recipient, actions)
                continue
            reduced = {"tool_input": "*** Begin Patch\n" + "\n".join(
                f"*** {action}: {target}" for action, target in actions) + "\n*** End Patch"}
            if recipient["kind"] == "workspace":
                from ecosystem.runtime.workspace import Workspace
                Workspace(recipient["root"], session).guard_patch(reduced, cwd, active_only=True)
            else:
                flow = Workflow(recipient["root"], session, create_state=False)
                with flow.lock():
                    flow.guard_patch(reduced, cwd, active_only=True)
        return {}
    except HookError as exc:
        return _deny(str(exc))
    except Exception:
        return _deny("the registered Git patch scope could not be verified")


def _handle_git(payload: dict[str, Any], contract: dict[str, Any], cwd: Path,
                session: str, state_dir: Path) -> dict[str, Any]:
    from ecosystem.runtime.workflow import Workflow, subagent_context

    event = payload["hook_event_name"]
    if event == "UserPromptSubmit":
        return _context(event,
            f"Constellation has an active Git {contract['kind']} contract. Use --session {session!r}. "
            "Inspect its existing requirements and incorporate corrections explicitly. "
            "This prompt does not start, reset, synchronize or publish a task. " + LIMITS)
    if event == "SubagentStart":
        _identifier(payload.get("agent_id"))
        return subagent_context(session, payload)
    if event == "SubagentStop":
        _identifier(payload.get("agent_id"))
        return {}
    if event == "PreToolUse":
        return _guard_git(payload, contract, cwd, session, state_dir)
    if contract["kind"] == "workspace":
        from ecosystem.runtime.workspace import Workspace
        return Workspace(contract["root"], session).stop(request_id=_request_id(payload, {
            "session_id": session, "task_id": str(contract["root"]),
        }), active_only=True)
    flow = Workflow(contract["root"], session, create_state=False)
    with flow.lock():
        return flow.stop(request_id=_request_id(payload, {
            "session_id": session, "task_id": str(contract["root"]),
        }), active_only=True)


def handle_event(payload: dict[str, Any], state_dir: Path | None = None,
                 expected_event: str | None = None) -> dict[str, Any]:
    """Handle a documented event without assuming a role absent from its schema."""
    if not isinstance(payload, dict):
        raise HookError("hook input must be a JSON object")
    event = payload.get("hook_event_name")
    if expected_event is not None and event != expected_event:
        raise HookError("hook event does not match its registered handler")
    if not isinstance(event, str) or event not in EVENTS:
        return _warning("unsupported hook event; no state changed")
    session = _identifier(payload.get("session_id"))
    cwd = _cwd(payload.get("cwd"))
    from ecosystem.core import Engine, default_state_dir, discover_active
    state_dir = state_dir if state_dir is not None else default_state_dir()
    discovered = discover_active(state_dir, session, cwd)
    # An explicit complete/partial close ends the hook scope. Later unrelated
    # work must not inherit it; reopening a task is an explicit CLI operation.
    tasks = [task for task in discovered["tasks"] if task["status"] == "active"]
    git_contracts = _git_contracts(cwd, session)
    if len(git_contracts) > 1 or (git_contracts and tasks):
        return _failure(event, "multiple independent lifecycle contracts match this session and directory; "
                        "inspect and reconcile them explicitly; no lifecycle was selected")
    if git_contracts:
        return _handle_git(payload, git_contracts[0], cwd, session, state_dir)
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
        print(json.dumps(_failure(args.event, "Python 3.11 or newer is required")))
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
        result = _failure(args.event, str(exc))
    except Exception:
        result = _failure(args.event, "hook evaluation failed; inspect task state explicitly")
    finally:
        if timer_armed:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous_handler)
    print(json.dumps(result, ensure_ascii=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

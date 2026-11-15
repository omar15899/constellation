#!/usr/bin/env python3
"""Connect native Copilot CLI hooks to the existing Constellation engine.

The adapter stores no prompts, transcripts, tool arguments or second task ledger.
Its command line selects trusted installation paths; event payloads never select
Python modules. Hook decisions supplement the client's permissions and are not
a sandbox: shell writes, disabled hooks and native timeout rules remain outside
the path check implemented here.
"""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
import re
import stat
import sys
from types import ModuleType
from typing import Any, BinaryIO

sys.dont_write_bytecode = True

MAX_INPUT_BYTES = 1024 * 1024
EVENTS = ("sessionStart", "subagentStart", "preToolUse", "agentStop")
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
GUIDANCE = (
    "Use the installed Constellation coding instructions. Before implementation, "
    "create or resume one shared-engine task with explicit scope, requirements "
    "and focused checks. Register actual native contributor and reviewer IDs; "
    "never fabricate independent reviews. Write simple English code, English "
    "class names and Google-style Python docstrings explaining contracts and "
    "decisions. Preserve unrelated changes. Run existing checks and add only "
    "the smallest tests needed for a concrete uncovered risk. Delegate three "
    "independent reviewers in parallel for correctness, readability and robustness, "
    "with each reviewer covering the whole change. Resolve findings, rerun "
    "affected checks and close through the shared engine. Hooks do not dispatch "
    "agents, run project checks, certify readability or authorize publication."
)


class AdapterError(ValueError):
    """The adapter cannot safely interpret a request or select a task."""


def identifier(value: Any) -> str:
    """Validate structural identities without retaining other event contents."""
    if not isinstance(value, str) or IDENTIFIER.fullmatch(value) is None:
        raise AdapterError("A valid native session or agent identifier is required.")
    return value


def absolute_path(value: Any) -> Path:
    """Require an explicit local path without interpreting event shell syntax."""
    if (not isinstance(value, str) or not value or len(value) > 4096
            or any(ord(character) < 32 for character in value)):
        raise AdapterError("An absolute filesystem path is required.")
    path = Path(value)
    if not path.is_absolute():
        raise AdapterError("An absolute filesystem path is required.")
    return path


def read_object(stream: BinaryIO) -> dict[str, Any]:
    """Read one bounded strict UTF-8 JSON object from the client's input stream.

    Args:
        stream: Binary stream containing one JSON object.

    Returns:
        The decoded object without logging any fields.

    Raises:
        AdapterError: Input is oversized, malformed, ambiguous or not an object.
    """
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise AdapterError("Duplicate JSON keys are not supported.")
            result[key] = value
        return result

    def reject_constant(_value: str) -> None:
        raise AdapterError("Nonfinite JSON numbers are not supported.")

    raw = stream.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise AdapterError("Input exceeds the adapter's byte limit.")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                           parse_constant=reject_constant)
    except (ValueError, UnicodeError, RecursionError):
        raise AdapterError("Input must be one strict UTF-8 JSON object.") from None
    if not isinstance(value, dict):
        raise AdapterError("Input must be one strict UTF-8 JSON object.")
    return value


def load_bundle(bundle: Path) -> ModuleType:
    """Verify the selected installation and load its existing portable engine.

    The installed hook pins this path in its exec arguments. Verification checks
    inventory and integrity against the local manifest, not publisher identity.
    The installer and its selected source must already be trusted.

    Args:
        bundle: Absolute bundle directory pinned by the installation.

    Returns:
        The verified installation's shared engine module.

    Raises:
        AdapterError: A linked lookup or different loaded engine is found.
        ValueError: The existing builder rejects the bundle inventory.
    """
    for component in (*reversed(bundle.parents), bundle):
        info = component.lstat()
        if (stat.S_ISLNK(info.st_mode)
                or getattr(info, "st_file_attributes", 0)
                & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)):
            raise AdapterError("The engine installation must not traverse links or reparse points.")
    for name, module in tuple(sys.modules.items()):
        if name == "ecosystem" or name.startswith("ecosystem."):
            origin = getattr(module, "__file__", None)
            if origin is None or not Path(origin).resolve().is_relative_to(bundle.resolve()):
                raise AdapterError("Another engine installation is already loaded in this process.")
    sys.path.insert(0, str(bundle))
    builder = importlib.import_module("ecosystem.build")
    builder.verify_bundle(bundle)
    return importlib.import_module("ecosystem.core")


def validate_directory(core: ModuleType, root: Path) -> None:
    """Reject missing or linked native working directories before discovery."""
    for component in (*reversed(root.parents), root):
        if core.platform.is_reparse(component):
            raise AdapterError("Project lookup must not traverse links or reparse points.")
    if not root.is_dir():
        raise AdapterError("The project directory does not exist.")


def validate_location(core: ModuleType, state_dir: Path, root: Path) -> None:
    """Keep operational state outside an explicitly selected project root."""
    validate_directory(core, root)
    if state_dir.resolve().is_relative_to(root.resolve()):
        raise AdapterError("Coordination state must remain outside the project.")


def matching_tasks(core: ModuleType, state_dir: Path, session: str,
                   cwd: Path) -> list[dict[str, Any]]:
    """Find existing tasks, including closures that need fresh verification.

    Discovery is read-only. Completed tasks remain relevant in the same native
    session so that editing an artifact cannot silently reuse an old approval.
    Explicit partial closure permits handoff without certifying completion.
    Creation sequence comes from the existing task row, whose identity is
    preserved by the store's update-in-place save operation.

    Args:
        core: Verified shared engine module.
        state_dir: Existing private coordination store, outside the project.
        session: Native parent session identifier.
        cwd: Native working directory used only to select containing roots.

    Returns:
        Summaries of active and closed tasks relevant to this session and root.
    """
    tasks = []
    with core.Store(state_dir).connection() as database:
        if database is None:
            return tasks
        for row in database.execute(
                "SELECT rowid AS sequence,root,session,task,state FROM tasks WHERE session=? ORDER BY rowid",
                (session,)):
            state = core.decode(row["state"])
            if cwd.resolve().is_relative_to(Path(row["root"])):
                tasks.append({"root": row["root"], "session_id": row["session"],
                              "task_id": row["task"], "author": state["author"],
                              "status": state["status"], "revision": state["revision"],
                              "sequence": row["sequence"]})
    return tasks


def deny(reason: str) -> dict[str, str]:
    """Deny one native tool call without granting permissions to other calls."""
    return {"permissionDecision": "deny", "permissionDecisionReason": reason}


def guard_edit(core: ModuleType, state_dir: Path, cwd: Path,
               payload: dict[str, Any], tasks: list[dict[str, Any]]) -> dict[str, str]:
    """Require an unambiguous declared file for native create and edit tools.

    Args:
        core: Verified shared engine module.
        state_dir: Explicit private coordination store.
        cwd: Native working directory for relative file arguments.
        payload: Native tool event; only the file argument is interpreted.
        tasks: Existing containing task summaries for the native parent session.

    Returns:
        A denial on ambiguity or unsafe scope; otherwise an empty decision that
        retains the client's normal permission checks.
    """
    active = [task for task in tasks if task["status"] == "active"]
    if len(active) != 1:
        return deny("Create or resume exactly one Constellation task before editing files.")
    arguments = payload.get("toolArgs")
    if isinstance(arguments, str):
        import io
        arguments = read_object(io.BytesIO(arguments.encode("utf-8")))
    if not isinstance(arguments, dict):
        return deny("The file tool must expose object arguments containing its path.")
    name = arguments.get("path")
    if (not isinstance(name, str) or not name or len(name) > 4096
            or any(ord(character) < 32 for character in name)):
        return deny("The file tool must expose a nonempty path.")
    task = active[0]
    root = Path(task["root"])
    engine = core.Engine(root, state_dir)
    validate_location(core, state_dir, root)
    candidate = Path(name) if Path(name).is_absolute() else cwd / name
    try:
        relative = candidate.relative_to(root).as_posix()
        engine.validate_path(relative)
    except (ValueError, core.Error):
        return deny("The requested file is outside the task's safe project paths.")
    status = engine.execute("status", {"session_id": task["session_id"],
                                      "task_id": task["task_id"], "agent_id": task["author"]})
    declared = {entry["path"] for entry in status["contract"]["deliverables"]}
    if relative not in declared:
        return deny("Add this exact file to the current task plan before editing it.")
    # An empty decision leaves the client's normal permission checks in effect.
    return {}


def handle_event(core: ModuleType, state_dir: Path, event: str,
                 payload: dict[str, Any]) -> dict[str, Any]:
    """Translate a native camelCase event into shared-engine evidence decisions.

    Args:
        core: Verified installation's existing ``ecosystem.core`` module.
        state_dir: Explicit absolute private coordination store.
        event: Event pinned by the installed hook configuration.
        payload: Native event object. Prompt and transcript fields are ignored.

    Returns:
        Only the documented native context or decision fields.

    Raises:
        AdapterError: Structural metadata cannot be interpreted safely.
    """
    if event not in EVENTS or not isinstance(payload, dict):
        raise AdapterError("Unsupported event or invalid event object.")
    session = identifier(payload.get("sessionId"))
    cwd = absolute_path(payload.get("cwd"))
    # A native cwd can be the user's home, which legitimately contains the
    # private store. Only an actual selected task root defines deliverables.
    validate_directory(core, cwd)
    if event in {"sessionStart", "subagentStart"}:
        return {"additionalContext": f"Native parent session_id: {session}. " + GUIDANCE}
    if event == "preToolUse":
        tool = payload.get("toolName")
        if not isinstance(tool, str) or not tool:
            raise AdapterError("The native tool name is missing.")
        if tool not in {"create", "edit"}:
            return {}
        tasks = matching_tasks(core, state_dir, session, cwd)
        return guard_edit(core, state_dir, cwd, payload, tasks)
    # A whole-project closure belongs to the parent; a child cannot close the
    # coordinator's task before the parent integrates and checks its result.
    if payload.get("agentId") is not None:
        identifier(payload["agentId"])
        return {}
    if "stop_hook_active" in payload and type(payload["stop_hook_active"]) is not bool:
        raise AdapterError("The native stop continuation flag must be boolean.")
    statuses = []
    for task in matching_tasks(core, state_dir, session, cwd):
        root = Path(task["root"])
        validate_location(core, state_dir, root)
        status = core.Engine(root, state_dir).execute("status", {
            "session_id": session, "task_id": task["task_id"], "agent_id": task["author"]})
        statuses.append((task, status))
    current_completions = [
        (task, {entry["path"] for entry in status["contract"]["deliverables"]})
        for task, status in statuses
        if status["status"] == "complete" and status["closure_current"]
    ]
    for task, status in statuses:
        if status["status"] == "partial":
            continue
        if status["status"] == "complete" and status["closure_current"]:
            continue
        # A later outcome may legitimately replace earlier artifacts in the
        # same chat. Only a current complete successor covering every earlier
        # deliverable supersedes that historical closure. Active work and
        # partial, overlapping or unrelated outcomes never grant that approval.
        paths = {entry["path"] for entry in status["contract"]["deliverables"]}
        superseded = status["status"] == "complete" and any(
            newer["root"] == task["root"] and newer["sequence"] > task["sequence"]
            and paths <= newer_paths for newer, newer_paths in current_completions)
        if not superseded:
            return {"decision": "block", "reason":
                    "Constellation has unfinished or stale obligations. Inspect the task's "
                    "status, run its focused checks, obtain current independent reviews, "
                    "and close complete. If completion is unavailable, report the exact "
                    "pending work and explicitly close partial. Repeated native blocks "
                    "are bounded by Copilot and do not certify eventual completion."}
    return {}


def main(argv: list[str] | None = None) -> int:
    """Run native hooks or forward one unchanged portable-engine request.

    Args:
        argv: Explicit command arguments, or the process arguments when omitted.

    Returns:
        Zero for a native decision, including a denial or stop block. Returns
        two for malformed manual operations or unavailable context injection.
        Error text is fixed and never includes private event contents.
    """
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if callable(getattr(stream, "reconfigure", None)):
            stream.reconfigure(encoding="utf-8", errors="strict")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, type=absolute_path)
    parser.add_argument("--state-dir", required=True, type=absolute_path)
    parser.add_argument("--root", type=absolute_path)
    commands = parser.add_subparsers(dest="mode", required=True)
    hooks = commands.add_parser("hook")
    hooks.add_argument("--event", required=True, choices=EVENTS)
    run = commands.add_parser("run")
    run.add_argument("operation")
    args = parser.parse_args(argv)
    try:
        core = load_bundle(args.bundle)
        payload = read_object(sys.stdin.buffer)
        if args.mode == "hook":
            result = handle_event(core, args.state_dir, args.event, payload)
        else:
            if args.root is None:
                raise AdapterError("Manual engine operations require --root.")
            validate_location(core, args.state_dir, args.root)
            result = core.Engine(args.root, args.state_dir).execute(args.operation, payload)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0
    except Exception:
        # Never echo the exception: third-party filesystem errors may embed
        # private event contents or source paths. The engine's status command
        # remains the explicit interface for pending task details.
        if args.mode == "hook":
            result = (deny("Constellation could not validate this file operation.")
                      if args.event == "preToolUse" else
                      {"decision": "block", "reason": "Constellation could not validate task evidence."}
                      if args.event == "agentStop" else {})
            print(json.dumps(result))
            print("Constellation adapter could not validate the request.", file=sys.stderr)
            return 0 if args.event in {"preToolUse", "agentStop"} else 2
        print(json.dumps({"error": "Constellation rejected the request; inspect its schema and current task status."}),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

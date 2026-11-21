"""Two native hooks: declared edit scope and bounded unfinished-work notices.

These are cooperative guards, not a shell sandbox. Arbitrary programs can write
without a structured edit payload; exact Git publication checks are separate.
Hook payloads and command output are never stored by this module.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Mapping, TextIO

from .git import GitError, _text
from .platform_support import IS_WINDOWS, is_reparse, validate_windows_lookup
from .state import ENGIE_ROUTE, EngieLearningStore, Store, engie_learning_path, validate_engie_scope


class HookError(ValueError):
    """A structured edit cannot be attributed to a declared scope."""


def _deny(reason: str) -> dict[str, Any]:
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
            "permissionDecision": "deny", "permissionDecisionReason":
            f"Constellation: {reason}"}}


def _tool(payload: Mapping[str, Any]) -> str:
    name = payload.get("tool_name", "")
    if not isinstance(name, str):
        raise HookError("Tool name is malformed")
    return re.split(r"[./]|__", name)[-1].casefold()


def patch_paths(patch: str) -> list[str]:
    """Extract all patch targets, including both endpoints of every move.

    Args:
        patch: A native apply_patch envelope, never shell source.

    Returns:
        Exact path strings in the patch. Content lines are not interpreted.

    Raises:
        HookError: The envelope or a path declaration is ambiguous.
    """
    lines = patch.strip().splitlines()
    if (len(lines) < 3 or lines[0] != "*** Begin Patch"
            or lines[-1] != "*** End Patch" or "\x00" in patch):
        raise HookError("Unsupported patch envelope")
    paths: list[str] = []
    move_allowed = False
    for line in lines[1:-1]:
        match = re.fullmatch(r"\*\*\* (Add File|Update File|Delete File|Move to): (.+)", line)
        if match:
            operation, name = match.groups()
            if operation == "Move to" and not move_allowed:
                raise HookError("Move has no preceding update")
            if name.strip() != name or any(ord(char) < 32 for char in name):
                raise HookError("Ambiguous edit path")
            paths.append(name)
            move_allowed = operation == "Update File"
        elif line.startswith("*** ") and line != "*** End of File":
            raise HookError("Unknown patch directive")
        elif line:
            move_allowed = False
    if not paths:
        raise HookError("Patch contains no file operations")
    return paths


def _edit_paths(payload: Mapping[str, Any], tool: str) -> list[str]:
    value = payload.get("tool_input")
    if tool == "apply_patch":
        if isinstance(value, str):
            return patch_paths(value)
        if not isinstance(value, dict):
            raise HookError("Missing patch input")
        texts = [value[key] for key in ("input", "patch", "command") if key in value]
        if (not texts or not all(isinstance(item, str) for item in texts)
                or any(item != texts[0] for item in texts)):
            raise HookError("Missing or conflicting patch input")
        return patch_paths(texts[0])
    # Claude's NotebookEdit has a distinct target field; it is still a write
    # subject to the same exact-path ownership as Write and Edit.
    field = "notebook_path" if tool == "notebookedit" else "file_path"
    if not isinstance(value, dict) or not isinstance(value.get(field), str):
        raise HookError("Missing structured edit target")
    return [value[field]]


def destructive_command_reason(command: str) -> str | None:
    """Retain Omar's existing direct-command deny rules across shell aliases.

    This detects common direct forms, not all equivalent programs. The native
    client's own permissions and exact Git gates remain independent boundaries.
    """
    direct = (r"(?:^|[;&|\n])\s*(?:(?:sudo|command)\s+)*"
              r"(?:env(?:\s+[A-Za-z_][A-Za-z0-9_]*=\S+)*\s+)?"
              r"(?:[^\s]*?/)?(?:rm|rmdir|curl|wget)(?:\s|$)")
    if re.search(direct, command, re.IGNORECASE):
        return "Direct rm/rmdir/curl/wget is forbidden; use a recoverable operation or reviewed network tool."
    if IS_WINDOWS:
        windows_direct = (
            r"(?:^|[;&|\n])\s*(?:&\s+)?"
            r"(?:Microsoft\.PowerShell\.(?:Management|Utility)\\)?"
            r"(?:Remove-Item|del|erase|rd|ri|rmdir|Invoke-WebRequest|Invoke-RestMethod|"
            r"iwr|irm|curl(?:\.exe)?|wget(?:\.exe)?)(?:\s|$)"
        )
        if re.search(windows_direct, command, re.IGNORECASE):
            return "Use a recoverable operation or reviewed network tool for this Windows command."
    git_prefix = r"\bgit(?:\.exe)?(?:\s+-C\s+(?:'[^']*'|\"[^\"]*\"|\S+))?\s+"
    rules = (
        (r"reset\s+[^\n;&|]*--hard\b", "Hard reset discards local work."),
        (r"push\b[^\n;&|]*(?:--force(?:-with-lease)?|-f)(?:\s|$)", "Force push rewrites remote history."),
        (r"clean(?:\s|$)", "Git clean removes untracked work."),
        (r"filter-branch(?:\s|$)", "Filter-branch rewrites history."),
        (r"checkout\s+--(?:\s|$)", "Checkout can discard local edits."),
    )
    for pattern, reason in rules:
        if re.search(git_prefix + pattern, command, re.IGNORECASE):
            return reason
    return None


def _identity(payload: Mapping[str, Any]) -> tuple[str, str]:
    session = payload.get("session_id")
    actor = payload.get("agent_id") or session
    if not isinstance(session, str) or not session or not isinstance(actor, str) or not actor:
        raise HookError("An edit requires native session and agent identity")
    return session, actor


def _routing_diagnostic(session: str, actor: str) -> str:
    """Expose only bounded routing identifiers, never tool input or prompts."""
    def safe(value: str) -> str:
        return value if re.fullmatch(r"[A-Za-z0-9_./:-]{1,128}", value) else "<invalid-id>"
    return f"session={safe(session)} actor={safe(actor)}"


def _target(cwd: Path, name: str) -> tuple[Path, str]:
    """Resolve one path without following links or crossing a nested Git owner."""
    given = Path(name)
    if (not name or any(part.casefold() in {"..", ".git"} for part in given.parts)
            or any(ord(character) < 32 for character in name)):
        raise HookError("Edit path contains an unsafe component")
    if IS_WINDOWS:
        if given.anchor and not given.is_absolute():
            raise HookError("Edit path uses an ambiguous Windows drive or root")
    elif "\\" in name:
        raise HookError("Edit path contains an unsafe component")
    path = Path(os.path.abspath(cwd / given))
    if IS_WINDOWS:
        validate_windows_lookup(path)
        if path.exists() and path.lstat().st_nlink != 1 and path.is_file():
            raise HookError("Edit target has multiple Windows file names")
    elif any(is_reparse(ancestor) for ancestor in (path, *path.parents)):
        raise HookError("Edit traverses a symbolic link")
    existing = path.parent
    while not existing.exists():
        if existing == existing.parent:
            raise HookError("Edit has no existing parent")
        existing = existing.parent
    try:
        root = Path(_text(existing, "rev-parse", "--show-toplevel", timeout=10)).resolve()
    except GitError as error:
        raise HookError("Edit has no declared Git owner") from error
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError as exc:
        raise HookError("Edit leaves its Git owner") from exc
    if relative == ".":
        raise HookError("Edit must name a file")
    return root, relative


def _participates(task: Mapping[str, Any], session: str, actor: str | None) -> bool:
    # A native child may get its own session ID. Its declared author ID still
    # associates it with this task; this does not authenticate identities.
    return (task.get("session_id", task.get("coordinator")) == session
            or actor == task.get("coordinator")
            or actor in task.get("assignments", {}).values())


def _actor(task: Mapping[str, Any], session: str, observed: str) -> str | None:
    """Resolve task-local native routing UUIDs to their declared agent labels.

    Codex may return a canonical agent label when spawning but use a session
    UUID in hook events. For a subagent, the native event carries the owning
    parent session_id separately from the child's agent_id. This association is
    runtime routing evidence, not identity authentication. Old records without
    a mapping keep their behavior. Historical aliases never grant edit access.
    """
    mapping = task.get("actor_sessions", {})
    if (not isinstance(mapping, dict)
            or any(not isinstance(name, str) or not isinstance(value, str)
                   or not name or not value for name, value in mapping.items())
            or len(set(mapping.values())) != len(mapping)):
        raise HookError("Task has an ambiguous actor-to-session association")
    parent_session = task.get("session_id", task.get("coordinator"))
    if observed in mapping:
        return observed if session in {mapping[observed], parent_session} else None
    for name, value in mapping.items():
        if value == observed:
            return name if session in {value, parent_session} else None
    return observed


def _allows(task: Mapping[str, Any], root: Path, relative: str,
            session: str, observed: str) -> bool:
    if Path(task["root"]).resolve() != root or relative not in task.get("assignments", {}):
        return False
    actor = _actor(task, session, observed)
    return (actor is not None and _participates(task, session, actor)
            and (actor == task.get("coordinator") or actor == task["assignments"][relative]))


def _active(store: Store | None, *, engie_roots: set[Path] | None = None) -> list[dict[str, Any]]:
    """Read both applicable ledgers through their atomic, nonmutating views."""
    # Publication holds the ledger lock while talking to Git. Native hooks must
    # use atomic record snapshots: waiting for that lock can exceed the native
    # hook timeout and turn a scope decision into a transport failure.
    if store is not None:
        tasks = store.list_tasks()
    else:
        tasks = Store(read_only=True).list_tasks()
        private = EngieLearningStore.existing(engie_roots)
        if private is not None:
            tasks += private.list_tasks()
    return [task for task in tasks if task.get("status") != "closed"]


def pre_tool(payload: Mapping[str, Any], store: Store | None = None) -> dict[str, Any]:
    """Check recognized edits and retained destructive shell rules.

    Read-only and unrecognized tools require no task. Structured writes require
    an active task that assigns every exact path to this native actor, or to the
    task coordinator. Errors on recognized writes return an explicit denial.
    """
    try:
        tool = _tool(payload)
        if tool in {"bash", "exec_command", "powershell", "shell", "shell_command"}:
            inputs = payload.get("tool_input")
            command = inputs.get("command", inputs.get("cmd", "")) if isinstance(inputs, dict) else ""
            reason = destructive_command_reason(command) if isinstance(command, str) else None
            return _deny(reason) if reason else {}
        if tool not in {"apply_patch", "write", "edit", "multiedit", "notebookedit"}:
            return {}
        session, actor = _identity(payload)
        cwd_value = payload.get("cwd")
        if not isinstance(cwd_value, str) or not Path(cwd_value).is_absolute():
            raise HookError("A structured edit requires an absolute working directory")
        targets = [_target(Path(cwd_value), name) for name in _edit_paths(payload, tool)]
        tasks = _active(store, engie_roots={root for root, relative in targets
                                           if engie_learning_path(relative)})
        private_edits: dict[Path, list[str]] = {}
        for root, relative in targets:
            matching = [task for task in tasks if _allows(task, root, relative, session, actor)]
            if not matching:
                raise HookError("Edit is outside this actor's declared exact paths; open or extend the task first "
                                f"({_routing_diagnostic(session, actor)})")
            if any(task.get("ledger") == ENGIE_ROUTE for task in matching):
                private_edits.setdefault(root, []).append(relative)
        for root, paths in private_edits.items():
            validate_engie_scope(root, paths)
        return {}
    except HookError as error:
        return _deny(str(error))
    except (ValueError, OSError, KeyError, TypeError):
        # Detailed file names and command bodies are unnecessary in a denial.
        return _deny("Structured edit scope cannot be verified; check the task, actor and exact paths.")


def stop(payload: Mapping[str, Any], store: Store | None = None) -> dict[str, Any]:
    """Report pending work once, retaining all state for later recovery.

    A continuation cannot claim completion or loop indefinitely: when the client
    sends stop_hook_active=true, return an advisory and leave the task open.
    """
    try:
        session, actor = _identity(payload)
        tasks = [task for task in _active(store)
                 if _participates(task, session, _actor(task, session, actor))]
        if not tasks:
            return {}
        ids = ", ".join(str(task["id"]) for task in tasks[:8])
        reason = (f"Constellation has pending local tasks: {ids}. Inspect status, record evidence, "
                  "and finish or report the remaining obligations. A successful push needs the exact remote SHA.")
        if payload.get("stop_hook_active") is True:
            return {"systemMessage": reason + " Tasks remain open; this continuation is not blocked again."}
        return {"decision": "block", "reason": reason}
    except (ValueError, OSError, KeyError, TypeError):
        reason = "Constellation cannot inspect local pending work; no task completion is certified."
        return ({"systemMessage": reason} if payload.get("stop_hook_active") is True
                else {"decision": "block", "reason": reason})


def main(event: str, stdin: TextIO | None = None) -> int:
    """Read one native hook object and emit one decision without storing input."""
    if event not in {"pre-tool", "stop"}:
        raise ValueError("Unsupported hook event")
    try:
        payload = json.load(stdin or sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError("Hook input must be an object")
    except (ValueError, OSError):
        output = (_deny("Malformed hook payload") if event == "pre-tool" else
                  {"systemMessage": "Constellation could not inspect pending tasks: malformed hook payload."})
    else:
        output = pre_tool(payload) if event == "pre-tool" else stop(payload)
    print(json.dumps(output))
    # JSON decisions need successful hook transport; exit 2 is reserved by
    # clients for hook errors and can hide the structured denial.
    return 0

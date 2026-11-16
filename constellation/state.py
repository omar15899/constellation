"""Small, private task ledger; Codex remains the agent and session runtime.

Identities are native IDs supplied by the coordinator, not authenticated users.
The ledger checks independence and freshness; it cannot certify review quality.
Only curated requirements, evidence and milestones belong here, never prompts,
transcripts, secrets or captured command output.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import tempfile
from typing import Any, Iterator, Mapping, Sequence
import uuid


class StateError(ValueError):
    """A task would violate scope, evidence or publication invariants."""


def now() -> str:
    """Return an unambiguous UTC timestamp for curated evidence."""
    return datetime.now(timezone.utc).isoformat()


def digest(value: Any) -> str:
    """Hash deterministic JSON, preserving exact Unicode string values."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode()).hexdigest()


def git(root: Path, *args: str) -> str:
    """Run bounded, read-only Git plumbing without persisting process output."""
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                            text=True, timeout=30, check=False)
    if result.returncode:
        raise StateError("Git metadata could not be read")
    return result.stdout.strip()


def validate_paths(root: Path, assignments: Mapping[str, str]) -> dict[str, str]:
    """Validate exact file ownership and reject aliases and nested Git owners.

    Args:
        root: Canonical Git worktree root.
        assignments: Exact relative file paths mapped to native author IDs.

    Returns:
        A sorted copy of the validated assignment map.

    Raises:
        StateError: A path is ambiguous, traverses a link, or leaves this owner.
    """
    if not assignments:
        raise StateError("A change requires at least one exact file path")
    folded: set[str] = set()
    for value, author in assignments.items():
        path = PurePosixPath(value)
        if (not isinstance(author, str) or not author.strip() or not value
                or path.is_absolute() or str(path) != value or "\\" in value
                or any(part in {"..", ".", ".git"} for part in path.parts)
                or any(ord(character) < 32 for character in value)):
            raise StateError("Assignments require literal relative file paths and author IDs")
        if value.casefold() in folded:
            raise StateError("Case aliases cannot have separate owners")
        folded.add(value.casefold())
        current = root
        for part in path.parts:
            current /= part
            if current.is_symlink():
                raise StateError("Scope cannot traverse symbolic links")
        if current.is_dir():
            raise StateError("Scope contains a directory; enumerate exact files")
        if current.exists() and not stat.S_ISREG(current.stat().st_mode):
            raise StateError("Scope supports regular files and deletions only")
        parent = current.parent
        while not parent.exists():
            parent = parent.parent
        if Path(git(parent, "rev-parse", "--show-toplevel")).resolve() != root:
            raise StateError("Scope crosses a different Git owner")
    names = sorted(assignments)
    if any(second.startswith(first + "/") for first in names for second in names):
        raise StateError("A file and its descendants cannot share scope")
    return {name: assignments[name] for name in names}


def effective_policy(root: str | Path, supplied: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Add current central restrictions and bind the relevant owner instructions.

    Explicit policy may strengthen restrictions. It cannot remove the project's
    private patterns or preserved Git validators. Re-reading this policy for
    each candidate makes a later profile edit invalidate earlier evidence.
    """
    root = Path(root).resolve()
    policy = dict(supplied or {})
    source = Path(__file__).resolve().parents[1]
    registry = source / "profiles/projects.json"
    selected = None
    if registry.exists():
        for project in json.loads(registry.read_text())["projects"]:
            if Path(project["root"]).expanduser().resolve() == root:
                selected = project
                break
    policy["private_patterns"] = sorted(set(policy.get("private_patterns", []))
        | set((selected or {}).get("private_patterns", [])))
    chain = policy.get("preserve_git_hook_chain") or []
    chain = [chain] if isinstance(chain, str) else list(chain)
    configured = (selected or {}).get("preserve_git_hook_chain") or []
    configured = [configured] if isinstance(configured, str) else list(configured)
    policy["preserve_git_hook_chain"] = sorted(set(chain + configured))
    instructions = [root / "AGENTS.md"]
    if selected and selected.get("profile"):
        instructions.append(source / selected["profile"])
    policy["_profile_sha256"] = digest({"project": selected,
        "instructions": {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in instructions if path.is_file()}})
    return policy


def artifact_fingerprint(task: Mapping[str, Any], candidate_value: Any = None) -> str:
    """Bind checks to the candidate Git tree, target, policy and task contract.

    Candidate calculation uses an isolated Git index, so unrelated staged work
    is neither included nor changed. Every call rechecks current file bytes.
    """
    root = Path(task["root"])
    validate_paths(root, task["assignments"])
    instructions: dict[str, str | None] = {}
    for name in task["paths"]:
        parent = (root / name).parent
        while parent.is_relative_to(root):
            instruction = parent / "AGENTS.md"
            if instruction.is_symlink() or (instruction.exists() and not instruction.is_file()):
                raise StateError("Applicable instructions must be regular files")
            instructions[str(instruction.relative_to(root))] = (
                hashlib.sha256(instruction.read_bytes()).hexdigest() if instruction.exists() else None)
            if parent == root:
                break
            parent = parent.parent
    if task.get("mode", "publish") == "local":
        files = {}
        for name in task["paths"]:
            path = root / name
            files[name] = ({"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                            "mode": stat.S_IMODE(path.stat().st_mode)}
                           if path.exists() else None)
        candidate_digest = digest({"root": str(root), "files": files, "mode": "local",
                                   "policy": effective_policy(root, task.get("policy"))})
    else:
        from .git import candidate

        current = candidate_value or candidate(task["root"], task["paths"], task["target"], task.get("policy"))
        candidate_digest = current["fingerprint"]
    return digest({"candidate": candidate_digest,
                   "instructions": instructions,
                   "requirement": task["requirement"],
                   "assignments": task["assignments"],
                   "authors": task.get("authors", {path: [author]
                       for path, author in task["assignments"].items()}),
                   "assignment_history": task.get("assignment_history", []),
                   "actor_sessions": task.get("actor_sessions", {}),
                   "actor_session_history": task.get("actor_session_history", {}),
                   "coordinator": task["coordinator"],
                   "owner_session_id": task.get("session_id", task["coordinator"]),
                   "required_checks": task["required_checks"]})


def fingerprint(task: Mapping[str, Any], candidate_value: Any = None) -> str:
    """Bind reviews to both the current artifact and latest check evidence.

    Replacing a check command, or rerunning it after review, requires a fresh
    review. Artifact checks use a separate digest to avoid a circular binding.
    """
    return digest({"artifact": artifact_fingerprint(task, candidate_value),
                   "checks": task["checks"]})


def authors(task: Mapping[str, Any]) -> set[str]:
    """Return recorded authors and their current or historical event aliases."""
    return set(task["assignments"].values()) | {
        author for identities in task.get("authors", {}).values() for author in identities} | {
        session for sessions in task.get("actor_session_history", {}).values() for session in sessions
    } | set(task.get("actor_sessions", {}).values())


def _record_actor_sessions(task: dict[str, Any], updates: Mapping[str, str], *,
                           normalize_legacy_uuid: bool = False) -> list[dict[str, str]]:
    """Join explicitly identified native actors to unique hook-event sessions.

    Previous aliases remain reserved to their actor and ineligible for review.
    The owning task session is a routing selector, not inferred actor evidence.
    Only explicit reassignment may normalize an inactive historical raw UUID;
    its caller records the reason and returned corrections in assignment history.
    """
    if not isinstance(updates, Mapping):
        raise StateError("Actor sessions must map native identities to event sessions")
    active = set(task["assignments"].values()) | {task["coordinator"]}
    known = active | {
        author for identities in task.get("authors", {}).values() for author in identities}
    current = dict(task.get("actor_sessions", {}))
    history = {actor: list(sessions) for actor, sessions
               in task.get("actor_session_history", {}).items()}
    previous_aliases = {actor: set(sessions) for actor, sessions in history.items()}
    for actor, session in current.items():
        history.setdefault(actor, []).append(session)
    for actor, session in updates.items():
        if (not isinstance(actor, str) or actor not in known or not isinstance(session, str)
                or not session.strip() or session != session.strip()):
            raise StateError("Session aliases require declared native actors and exact nonempty IDs")
        current[actor] = session
        history.setdefault(actor, []).append(session)
    owners: dict[str, str] = {}
    corrections: dict[str, str] = {}
    for actor, sessions in history.items():
        for session in sessions:
            if session in owners and owners[session] != actor:
                raise StateError("An event session cannot identify distinct native actors")
            if session in known and session != actor:
                legacy_uuid = re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", session)
                established = session in previous_aliases.get(actor, set())
                explicit = normalize_legacy_uuid and updates.get(actor) == session
                if session in active or not legacy_uuid or not (established or explicit):
                    raise StateError("An event session cannot identify distinct native actors")
                if not established:
                    corrections[session] = actor
            owners[session] = actor
    task["actor_sessions"] = current
    task["actor_session_history"] = {actor: sorted(set(sessions))
                                      for actor, sessions in history.items()}
    return [{"legacy_actor": legacy, "native_actor": actor}
            for legacy, actor in sorted(corrections.items())]


def ready(task: Mapping[str, Any]) -> str:
    """Require current successful checks and independent approval.

    Returns:
        The current fingerprint, suitable for a publication journal.

    Raises:
        StateError: Evidence is missing, failed, stale or not independent.
    """
    artifact = artifact_fingerprint(task)
    current = digest({"artifact": artifact, "checks": task["checks"]})
    for check_id in task["required_checks"]:
        check = task["checks"].get(check_id, {})
        if (check.get("status") != "passed" or check.get("returncode") != 0
                or check.get("fingerprint") != artifact):
            raise StateError("Required check is missing, failed or stale: " + check_id)
    author_ids = authors(task)
    # The latest report from each reviewer governs; an old approval cannot hide
    # a later rejection, while a corrected re-review remains possible.
    reports = {report["reviewer"]: report for report in task["reviews"]
               if report["fingerprint"] == current}
    independent = [report for reviewer, report in reports.items()
                   if reviewer not in author_ids and reviewer != task["coordinator"]]
    if any(report["verdict"] == "reject" for report in independent):
        raise StateError("A current independent review rejects this candidate")
    if not any(report["verdict"] == "approve" for report in independent):
        raise StateError("Current independent approval is missing")
    return current


def _require_mutable_evidence(task: Mapping[str, Any]) -> None:
    """Freeze evidence for a committed candidate until a verified local follow-up.

    Git owns remote verification and records the explicit pending-local status.
    Requiring its matching verified journal also covers interrupted commits
    whose task record has not yet received the publication receipt.
    """
    from .git import _journal_path

    publication = task.get("publication", {})
    journal_path = _journal_path(task["root"], task["id"])
    if not publication and not journal_path.exists():
        return
    if publication.get("status") == "verified_local_changes" and journal_path.is_file():
        journal = json.loads(journal_path.read_text())
        if (publication.get("commit") and journal.get("phase") == "verified"
                and journal.get("commit") == publication["commit"]):
            return
    raise StateError("Evidence is frozen by publication; recover the pending commit or push first")


class Store:
    """A private, atomic JSON ledger with one lock covering ownership changes.

    Args:
        state_dir: Private state root, defaulting to CONSTELLATION_STATE_DIR or
            ~/.local/state/constellation. Different sessions must share it.
    """

    def __init__(self, state_dir: str | Path | None = None):
        self.root = Path(state_dir or os.environ.get("CONSTELLATION_STATE_DIR")
                         or Path.home() / ".local/state/constellation").expanduser().resolve()
        self.tasks = self.root / "tasks"
        self.tasks.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.root.chmod(0o700)
        self.tasks.chmod(0o700)

    def _path(self, task_id: str) -> Path:
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}", task_id):
            raise StateError("Task ID must be a simple local identifier")
        return self.tasks / (task_id + ".json")

    @contextmanager
    def _lock(self) -> Iterator[None]:
        with (self.root / ".lock").open("a", encoding="utf-8") as handle:
            os.chmod(handle.name, 0o600)
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _read(self, task_id: str) -> dict[str, Any]:
        try:
            task = json.loads(self._path(task_id).read_text())
        except (FileNotFoundError, json.JSONDecodeError) as error:
            raise StateError("Task is absent or unreadable: " + task_id) from error
        if task.get("schema") != 1 or task.get("id") != task_id:
            raise StateError("Unsupported or mismatched task record")
        return task

    def save_locked(self, task: dict[str, Any]) -> None:
        """Durably save while holding locked(); supports publication checkpoints."""
        destination = self._path(task["id"])
        descriptor, temporary = tempfile.mkstemp(prefix=".task-", dir=self.tasks)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(task, handle, ensure_ascii=False, sort_keys=True, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
            directory = os.open(self.tasks, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    @contextmanager
    def locked(self, task_id: str) -> Iterator[dict[str, Any]]:
        """Yield the current mutable task and save only on successful completion."""
        with self._lock():
            task = self._read(task_id)
            yield task
            self.save_locked(task)

    def get(self, task_id: str) -> dict[str, Any]:
        """Read one task without changing its lifecycle."""
        with self._lock():
            return self._read(task_id)

    def active(self, root: str | Path | None = None) -> list[dict[str, Any]]:
        """Return unfinished assignments, optionally for one exact Git owner."""
        selected = str(Path(root).resolve()) if root is not None else None
        with self._lock():
            return [task for path in sorted(self.tasks.glob("*.json"))
                    if (task := self._read(path.stem))["status"] != "closed"
                    and (selected is None or task["root"] == selected)]

    def list_tasks(self) -> list[dict[str, Any]]:
        """Read atomic task snapshots without acquiring the publication lock.

        Git hooks may run while their parent holds locked(). Each record is
        atomic, but this intentionally does not promise a global snapshot.
        """
        return [self._read(path.stem) for path in sorted(self.tasks.glob("*.json"))]

    def begin(self, task_id: str, root: str | Path, requirement: str,
              assignments: Mapping[str, str], *, coordinator: str,
              session_id: str | None = None,
              actor_sessions: Mapping[str, str] | None = None,
              mode: str = "publish",
              remote: str = "origin", branch: str | None = None,
              ref: str | None = None, required_checks: Sequence[str] = ("default",),
              policy: dict[str, Any] | None = None) -> dict[str, Any]:
        """Freeze scope and publication target before changing files.

        Existing task IDs and overlapping unfinished scopes fail closed. A query
        needs no task; every change records at least one required behavior check.
        """
        root = Path(root).expanduser().resolve()
        if mode not in {"publish", "local"}:
            raise StateError("Task mode must be publish or local")
        if not requirement.strip() or not coordinator.strip():
            raise StateError("A change needs a requirement and coordinator ID")
        if Path(git(root, "rev-parse", "--show-toplevel")).resolve() != root:
            raise StateError("Root must be the exact Git owner")
        owners = validate_paths(root, assignments)
        from .git import target as publication_target
        checks = list(required_checks)
        if not checks or len(set(checks)) != len(checks) or not all(checks):
            raise StateError("Declare unique required checks")
        target = publication_target(root, remote, branch, ref) if mode == "publish" else None
        policy = effective_policy(root, policy)
        task = {"schema": 1, "id": task_id, "root": str(root),
                "requirement": requirement, "assignments": owners, "paths": list(owners),
                "authors": {path: [author] for path, author in owners.items()},
                "assignment_history": [],
                "coordinator": coordinator, "session_id": session_id or coordinator,
                "target": target, "mode": mode,
                "base_head": git(root, "rev-parse", "HEAD"), "policy": policy,
                "required_checks": checks, "checks": {}, "reviews": [],
                "milestones": [], "publication": {}, "created": now(), "status": "open"}
        _record_actor_sessions(task, actor_sessions if actor_sessions is not None else {})
        with self._lock():
            if self._path(task_id).exists():
                raise StateError("Task already exists; resume it instead")
            for path in self.tasks.glob("*.json"):
                other = self._read(path.stem)
                if other["status"] == "closed" or other["root"] != str(root):
                    continue
                incoming = {name.casefold() for name in owners}
                occupied = {name.casefold() for name in other["paths"]}
                if any(a == b or a.startswith(b + "/") or b.startswith(a + "/")
                       for a in incoming for b in occupied):
                    raise StateError("Another unfinished task owns part of this scope: " + other["id"])
            self.save_locked(task)
        return task

    def checkpoint(self, task_id: str, summary: str) -> dict[str, Any]:
        """Append a curated milestone; callers must exclude private raw material."""
        if not summary.strip():
            raise StateError("A checkpoint needs a meaningful summary")
        with self.locked(task_id) as task:
            task["milestones"].append({"at": now(), "summary": summary})
        return task

    def assign(self, task_id: str, path: str, author: str, reason: str,
               session_id: str | None = None, owner_session_id: str | None = None) -> dict[str, Any]:
        """Transfer an existing exact path without forgetting previous authors.

        Args:
            task_id: Existing open task, before any publication intent.
            path: Exact path already belonging to this task.
            author: Native agent ID returned by the spawning tool. Environment
                variables may be inherited and do not establish actor identity.
            reason: Curated reason for correcting or transferring ownership.
            session_id: Optional event-session alias explicitly associated with
                this native actor. This is separate from the task's owning session.
                An inactive historical raw UUID may be explicitly normalized;
                it remains an author and cannot already identify another actor.
            owner_session_id: Optional parent session used to group native hook
                events. Corrects routing or resumes this task in another session
                without inferring or changing the actor's identity.

        Returns:
            Updated task; its previous checks and reviews remain as stale history.
        """
        if (not isinstance(path, str) or not isinstance(author, str) or not author.strip()
                or not isinstance(reason, str) or not reason.strip()):
            raise StateError("Reassignment needs a native author ID and a reason")
        if owner_session_id is not None and (not isinstance(owner_session_id, str)
                or not owner_session_id.strip() or owner_session_id != owner_session_id.strip()):
            raise StateError("The owning session requires an exact nonempty native ID")
        with self.locked(task_id) as task:
            from .git import _journal_path

            if (task["status"] != "open" or task["publication"]
                    or _journal_path(task["root"], task_id).exists()):
                raise StateError("Cannot reassign a closed task or a publication in progress")
            if path not in task["assignments"]:
                raise StateError("Reassignment cannot extend the task's declared scope")
            previous = task["assignments"][path]
            previous_owner_session = task.get("session_id", task["coordinator"])
            if author == previous and (session_id is None
                    or task.get("actor_sessions", {}).get(author) == session_id) and (
                    owner_session_id is None or owner_session_id == previous_owner_session):
                raise StateError("This native author already owns the path")
            history = task.setdefault("authors", {name: [owner]
                for name, owner in task["assignments"].items()})
            history[path] = sorted(set(history.get(path, [])) | {previous, author})
            task["assignments"][path] = author
            corrections = _record_actor_sessions(task,
                {author: session_id} if session_id is not None else {},
                normalize_legacy_uuid=session_id is not None)
            if owner_session_id is not None:
                task["session_id"] = owner_session_id
            task.setdefault("assignment_history", []).append({"at": now(), "path": path,
                "previous": previous, "author": author, "reason": reason, "session_id": session_id,
                "previous_owner_session_id": previous_owner_session,
                "owner_session_id": task.get("session_id", task["coordinator"]),
                "identity_corrections": corrections})
        return task

    def check(self, task_id: str, check_id: str, argv: Sequence[str], *,
              timeout: float = 300) -> dict[str, Any]:
        """Run a bounded check outside the lock and retain its current attempt.

        Raw command/output is not stored. A failed, timed-out, superseded or
        mutating check cannot reuse older successful evidence.
        """
        if isinstance(argv, str) or not argv or not all(isinstance(item, str) and item for item in argv):
            raise StateError("Checks require a nonempty argv, not a shell string")
        if not 0 < timeout <= 3600:
            raise StateError("Check timeout must be within (0, 3600] seconds")
        with self.locked(task_id) as task:
            if check_id not in task["required_checks"] or task["status"] != "open":
                raise StateError("Check is not declared on an open task")
            _require_mutable_evidence(task)
            version = artifact_fingerprint(task)
            attempt = uuid.uuid4().hex
            task["checks"][check_id] = {"attempt": attempt, "status": "running",
                "fingerprint": version, "argv_sha256": digest(list(argv)), "started": now()}
            root = task["root"]
        try:
            result = subprocess.run(list(argv), cwd=root, capture_output=True,
                                    timeout=timeout, check=False)
            code, output = result.returncode, result.stdout + result.stderr
            status = "passed" if code == 0 else "failed"
        except (OSError, subprocess.TimeoutExpired):
            code, output, status = None, b"", "failed"
        with self.locked(task_id) as task:
            record = task["checks"][check_id]
            if record["attempt"] != attempt:
                raise StateError("A newer check attempt superseded this result")
            try:
                changed = artifact_fingerprint(task) != version
            except (ValueError, RuntimeError):
                changed = True
            record.update(returncode=code, status="stale" if changed else status,
                          output_sha256=hashlib.sha256(output).hexdigest(), finished=now())
        return record

    def review(self, task_id: str, reviewer: str, evidence: str,
               verdict: str = "approve", *, expected_fingerprint: str) -> dict[str, Any]:
        """Record an independent assessment of an explicitly observed candidate.

        The reviewer must supply the fingerprint obtained before review. This
        prevents a changed artifact being silently relabelled as reviewed.
        """
        if not reviewer.strip() or not evidence.strip() or verdict not in {"approve", "reject"}:
            raise StateError("Review needs an identity, evidence and a supported verdict")
        with self.locked(task_id) as task:
            _require_mutable_evidence(task)
            if reviewer in authors(task) or reviewer == task["coordinator"]:
                raise StateError("Authors and coordinator cannot approve their own change")
            current = fingerprint(task)
            if task["status"] != "open" or expected_fingerprint != current:
                raise StateError("Review candidate changed or task is no longer open")
            report = {"reviewer": reviewer, "evidence": evidence, "verdict": verdict,
                      "fingerprint": current, "at": now()}
            task["reviews"].append(report)
        return report

    def status(self, task_id: str) -> dict[str, Any]:
        """Return task state and independently recomputed readiness."""
        task = self.get(task_id)
        current = None
        try:
            current = fingerprint(task)
            ready(task)
            gate = {"ready": True, "fingerprint": current}
        except (ValueError, RuntimeError) as error:
            gate = {"ready": False, "fingerprint": current, "reason": str(error)}
        return {**task, "gate": gate}

    def finish(self, task_id: str) -> dict[str, Any]:
        """Close reviewed local work without making any Git publication claim."""
        with self.locked(task_id) as task:
            if task.get("mode") != "local" or task["status"] != "open":
                raise StateError("Local finish requires an open local task")
            version = ready(task)
            task["status"] = "closed"
            task["closed"] = {"at": now(), "fingerprint": version, "kind": "local"}
        return task

    def cancel(self, task_id: str, reason: str) -> dict[str, Any]:
        """Cancel an unassessed assignment without claiming completion or editing files.

        A task with checks, reviews or publication intent must be resolved in its
        existing lifecycle; cancellation cannot hide adverse evidence.
        """
        if not reason.strip():
            raise StateError("Cancellation requires an explicit reason")
        with self.locked(task_id) as task:
            if (task["status"] != "open" or task["checks"] or task["reviews"]
                    or task["publication"]):
                raise StateError("Only an open unassessed assignment can be cancelled")
            task["status"] = "closed"
            task["closed"] = {"at": now(), "kind": "cancelled", "reason": reason}
        return task

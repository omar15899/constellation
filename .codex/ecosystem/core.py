"""Revision-bound coordination without Git, daemons or stored command output."""
from __future__ import annotations

import copy
import hashlib
import math
import os
from pathlib import Path
import re
import sqlite3
import stat
import subprocess
import sys
import time
from typing import Any
import uuid

from . import platform_support as platform
from .build import MODULE_AGENTS
from .runtime import DEFAULT_POLICY
from .runtime import review_gate as gate
from .runtime import progress as journal
from .storage import Error, Store, decode, encode

_SOURCE = Path(__file__).resolve().parent
_BASE = _SOURCE.parent
_POLICY = DEFAULT_POLICY
_ENVELOPE = {"session_id", "task_id", "agent_id", "expected_revision", "request_id"}
_PROFILES = set(MODULE_AGENTS)
_ACCEPTANCE = {"behavior", "proof", "calculation", "editorial"}
_KINDS = {"behavior", "numeric", "formal", "editorial"}
_FIELDS = {
    "plan": {"requirements", "deliverables", "checks", "inputs", "depends_on", "risk", "agents"},
    "status": set(), "review-context": set(), "review-start": {"quick_code_reason", "continuation"},
    "review-budget": {"expected_budget_revision", "deadline_at", "reason"},
    "register-agent": {"registered_agent_id", "role"}, "author": {"author", "paths"},
    "check": {"id", "argv", "timeout"}, "recover-check": {"id", "attempt_id"},
    "review-report": {"token", "reviewer", "role", "focus", "paths", "summary", "evidence", "findings", "assessments"},
    "review-resolve": {"token", "id", "verifier", "disposition", "evidence"},
    "discover": {"requirement"}, "close": {"mode"}, "stop": set(),
    "hook-stop": set(), "observe-agent": {"observed_agent_id", "event"},
    "progress-show": set(), "progress-update": {"task_uid", "checkpoint", "source_alias"},
    "progress-export": {"task_uid", "policy_path"},
    "progress-ack": {"task_uid", "receipt", "policy_path"},
}


class RevisionConflict(Error):
    """A stale optimistic revision; callers may retry only safe operations."""


def digest(value: Any) -> str:
    """Canonical JSON digest, also used for check definitions."""
    return hashlib.sha256(encode(value).encode()).hexdigest()


def _request_digest(operation: str, payload: dict[str, Any]) -> str:
    # A retry can refresh its optimistic revision without changing its meaning.
    return digest({"operation": operation, "payload": {k: v for k, v in payload.items() if k != "expected_revision"}})


def default_state_dir() -> Path:
    override = os.environ.get("CONSTELLATION_STATE_DIR")
    if override:
        return Path(override)
    return Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "constellation" / "state"


def _text(value: Any, label: str, limit: int = 12000) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip() or len(value) > limit:
        raise Error(f"{label} must be nonempty text without surrounding whitespace.")
    return value


def _identifier(value: Any, label: str) -> str:
    text = _text(value, label, 128)
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]*", text) is None:
        raise Error(f"Invalid {label}.")
    return text


def _sha(value: Any) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise Error("SHA-256 must be 64 lowercase hexadecimal characters.")
    return value


def _object(value: Any, required: set[str], optional: set[str] = frozenset()) -> dict[str, Any]:
    if not isinstance(value, dict) or not required <= value.keys() or value.keys() - required - optional:
        raise Error("Object has missing or unknown fields.")
    return value


def _list(value: Any, label: str, *, nonempty: bool = False) -> list[Any]:
    if not isinstance(value, list) or (nonempty and not value):
        raise Error(f"{label} must be a list{' with entries' if nonempty else ''}.")
    return value


def _strings(value: Any, label: str, *, nonempty: bool = False) -> list[str]:
    result = [_text(item, label, 1000) for item in _list(value, label, nonempty=nonempty)]
    if len(result) != len(set(result)):
        raise Error(f"{label} cannot contain duplicates.")
    return result


def _summary(root: str, session: str, task: str, state: dict[str, Any]) -> dict[str, Any]:
    return {"root": root, "session_id": session, "task_id": task, "revision": state["revision"],
            "author": state["author"], "agents": state["agents"],
            "paths": [item["path"] for item in state["contract"]["deliverables"]],
            "status": state["status"]}


def discover_active(state_dir: Path, session_id: str, cwd: Path) -> dict[str, Any]:
    """Find existing containing roots without deriving executable code from cwd."""
    session = _identifier(session_id, "session_id")
    current = Path(cwd).resolve(strict=True)
    tasks = []
    with Store(state_dir).connection() as db:
        if db is not None:
            for row in db.execute("SELECT root,session,task,state FROM tasks WHERE session=? ORDER BY root,task", (session,)):
                root = Path(row["root"])
                if current.is_relative_to(root):
                    state = decode(row["state"])
                    if state["status"] == "active":
                        tasks.append(_summary(row["root"], row["session"], row["task"], state))
    return {"tasks": tasks}


class Engine:
    def __init__(self, root: Path, state_dir: Path):
        if sys.version_info < (3, 11):
            raise Error("The portable engine requires Python 3.11 or newer.")
        supplied_root = Path(root)
        if platform.IS_WINDOWS:
            # Never erase the original junction lookup before validating it.
            original_lookup = supplied_root.absolute()
            for component in (*reversed(original_lookup.parents), original_lookup):
                if platform.is_reparse(component):
                    raise Error("Project root must not traverse symbolic links or reparse points.")
            try:
                supplied_root = platform.validate_lookup(supplied_root)
            except platform.PlatformError as exc:
                raise Error("Windows project root contains an unsafe filesystem lookup.") from exc
        self.root = supplied_root.resolve(strict=True)
        if not self.root.is_dir():
            raise Error("Root must be an existing directory.")
        self.store = Store(state_dir)

    def validate_path(self, name: str) -> Path:
        _text(name, "path", 1000)
        try:
            target = gate._path(self.root, name)
        except gate.ReviewError as exc:
            raise Error(str(exc)) from None
        if target.is_symlink() or target.resolve().is_relative_to(self.store.directory.resolve()):
            raise Error("Artifacts and inputs cannot include symbolic links or engine state.")
        return target

    def _input_record(self, path: Path) -> dict[str, Any] | None:
        """Bind input bytes and, on Windows, its effective access descriptor."""
        if not path.is_file():
            return None
        if not platform.IS_WINDOWS:
            return {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "mode": stat.S_IMODE(path.stat().st_mode)}
        try:
            descriptor = platform.open_regular(path, os.O_RDONLY, private=False)
            with os.fdopen(descriptor, "rb") as stream:
                return {"sha256": hashlib.sha256(stream.read()).hexdigest(),
                        "mode": stat.S_IMODE(os.fstat(stream.fileno()).st_mode),
                        "access": platform.access_fingerprint(path)}
        except platform.PlatformError as exc:
            raise Error("Declared input has an unsafe or changed Windows access policy.") from exc

    def _resources(self, contract: dict[str, Any]) -> dict[str, str]:
        paths = [_SOURCE / "runtime/__init__.py", _SOURCE / "runtime/review_gate.py",
                 _POLICY, _SOURCE / "core.py", _SOURCE / "storage.py",
                 _SOURCE / "platform_support.py",
                 _SOURCE / "cli.py", _SOURCE / "hooks.py", _SOURCE / "hook_entry.py",
                 _SOURCE / "build.py", _SOURCE / "references/protocol.md"]
        manifest = _SOURCE / "manifests" / "codex-plugin.json"
        paths.append(manifest if manifest.exists() else _BASE / ".codex-plugin/plugin.json")
        paths.extend(_SOURCE / "agents" / (name + ".toml") for name in ("researcher", "reviewer", "security-reviewer", "verifier"))
        profiles = {p for item in contract["deliverables"] for p in item["profiles"]}
        if profiles & {"mathematics", "writter"}:
            paths.extend(_SOURCE / "references" / name for name in ("ontology.md", "ontology-examples.md"))
        for profile in sorted(profiles):
            directory = _BASE / "skills" / profile
            paths.extend(directory / name for name in ("SKILL.md", "agents/openai.yaml", "references/workflow.md"))
            paths.extend(_SOURCE / "agents" / (name + ".toml") for name in MODULE_AGENTS[profile])
        result = {}
        for path in paths:
            relative = path.relative_to(_BASE)
            if any((_BASE / parent).is_symlink() for parent in relative.parents) or path.is_symlink() or not path.is_file():
                raise Error(f"Required installed resource is missing or unsafe: {path.relative_to(_BASE)}")
            result[path.relative_to(_BASE).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        return result

    def _requirement(self, value: Any) -> dict[str, Any]:
        row = _object(value, {"id", "text", "deliverables", "checks", "acceptance"}, {"accepted_verdicts"})
        result = {"id": _identifier(row["id"], "requirement id"), "text": _text(row["text"], "requirement text"),
                  "deliverables": _strings(row["deliverables"], "requirement deliverables", nonempty=True),
                  "checks": _strings(row["checks"], "requirement checks"), "acceptance": row["acceptance"]}
        if result["acceptance"] not in _ACCEPTANCE:
            raise Error("Unsupported requirement acceptance.")
        if result["acceptance"] in {"behavior", "calculation"} and not result["checks"]:
            raise Error("Behavior and calculation requirements need executable checks.")
        verdicts = _strings(row.get("accepted_verdicts", ["proved"] if result["acceptance"] == "proof" else ["satisfied"]),
                            "accepted verdicts", nonempty=True)
        if set(verdicts) - {"satisfied", "proved", "refuted"}:
            raise Error("Unsupported accepted verdict.")
        if result["acceptance"] == "proof" and "satisfied" in verdicts:
            raise Error("Proof obligations must name their epistemic verdict explicitly.")
        result["accepted_verdicts"] = sorted(verdicts)
        return result

    def _contract(self, payload: dict[str, Any]) -> dict[str, Any]:
        names = {"requirements", "deliverables", "checks", "inputs", "depends_on", "risk"}
        if not names <= payload.keys():
            raise Error("Plan is missing required contract fields.")
        contract = {"requirements": [self._requirement(row) for row in _list(payload["requirements"], "requirements", nonempty=True)]}
        artifacts = []
        for row in _list(payload["deliverables"], "deliverables", nonempty=True):
            _object(row, {"path", "profiles"})
            self.validate_path(row["path"])
            profiles = _strings(row["profiles"], "profiles", nonempty=True)
            if set(profiles) - _PROFILES:
                raise Error("Unknown deliverable profile.")
            artifacts.append({"path": row["path"], "profiles": sorted(profiles)})
        checks = []
        for row in _list(payload["checks"], "checks"):
            _object(row, {"id", "kind", "definition_sha256"})
            if row["kind"] not in _KINDS:
                raise Error("Unsupported check kind.")
            checks.append({"id": _identifier(row["id"], "check id"), "kind": row["kind"],
                           "definition_sha256": _sha(row["definition_sha256"])})
        inputs = []
        for row in _list(payload["inputs"], "inputs"):
            _object(row, {"path", "sha256"})
            path = self.validate_path(row["path"])
            current = self._input_record(path)
            if current is None or current["sha256"] != _sha(row["sha256"]):
                raise Error("Declared input hash differs from its local regular file.")
            inputs.append(dict(row))
        dependencies = []
        for row in _list(payload["depends_on"], "depends_on"):
            _object(row, {"session_id", "task_id", "version"})
            dependencies.append({"session_id": _identifier(row["session_id"], "dependency session"),
                                 "task_id": _identifier(row["task_id"], "dependency task"), "version": _sha(row["version"])})
        if payload["risk"] not in gate.MODES:
            raise Error("Risk must be quick, standard or deep.")
        contract.update(deliverables=artifacts, checks=checks, inputs=inputs, depends_on=dependencies, risk=payload["risk"])
        for collection, field in ((contract["requirements"], "id"), (artifacts, "path"), (checks, "id"), (inputs, "path")):
            if len(collection) != len({row[field] for row in collection}):
                raise Error("Duplicate contract identifier or path.")
        if len(dependencies) != len({(row["session_id"], row["task_id"]) for row in dependencies}):
            raise Error("Duplicate dependency.")
        paths, ids = {item["path"] for item in artifacts}, {item["id"] for item in checks}
        if paths & {item["path"] for item in inputs}:
            raise Error("Inputs and deliverables must be disjoint.")
        try:
            platform.ensure_distinct_paths(
                self.root, [item["path"] for item in (*artifacts, *inputs)])
        except platform.PlatformError as exc:
            raise Error("Contract paths must identify distinct artifacts and inputs.") from exc
        covered = set()
        for requirement in contract["requirements"]:
            if not set(requirement["deliverables"]) <= paths or not set(requirement["checks"]) <= ids:
                raise Error("Requirement references an undeclared deliverable or check.")
            covered.update(requirement["deliverables"])
        if covered != paths:
            raise Error("Every deliverable needs an observable requirement.")
        self._resources(contract)
        return contract

    def _snapshot(self, db: sqlite3.Connection, key: tuple[str, str, str], state: dict[str, Any], seen: frozenset = frozenset()) -> dict[str, Any]:
        if key in seen:
            raise Error("Dependency cycle.")
        contract = state["contract"]
        paths = [item["path"] for item in contract["deliverables"]]
        for name in paths:
            self.validate_path(name)
        artifacts = gate._artifacts(self.root, paths, [])
        inputs = {}
        for row in contract["inputs"]:
            path = self.validate_path(row["path"])
            inputs[row["path"]] = self._input_record(path)
        dependencies = []
        for row in contract["depends_on"]:
            dependency_key = (str(self.root), row["session_id"], row["task_id"])
            provider = self.store.load(db, dependency_key)
            if provider is None:
                raise Error("Dependency is not registered in this root and state store.")
            provider_snapshot = self._snapshot(db, dependency_key, provider, seen | {key})
            self._sync_gate(provider, provider_snapshot)
            closure = provider.get("closure")
            valid = bool(closure and provider["status"] == "complete" and closure["version"] == row["version"])
            if valid:
                current_token = gate.prepare(self.root, provider["gate"], policy_path=_POLICY)["token"]
                valid = closure["token"] == current_token and not self._mechanical(provider, provider_snapshot)
            if valid:
                try:
                    gate.validate(self.root, provider["gate"], policy_path=_POLICY)
                except gate.ReviewError:
                    valid = False
            dependencies.append({**row, "current": closure["version"] if closure else None, "valid": valid})
        return {"contract": digest(contract), "artifacts": artifacts, "inputs": inputs,
                "resources": self._resources(contract), "dependencies": dependencies}

    def _sync_gate(self, state: dict[str, Any], snapshot: dict[str, Any]) -> None:
        contract = state["contract"]
        context = digest({"snapshot": snapshot, "checks": state["checks"]})
        state["gate"].update(author=state["author"], started=state["started"], initial_head=None,
                             requirements=[row["id"] + ": " + row["text"] for row in contract["requirements"]],
                             paths=[row["path"] for row in contract["deliverables"]],
                             review_risk=contract["risk"], review_context_sha256=context)

    def _mechanical(self, state: dict[str, Any], snapshot: dict[str, Any]) -> list[str]:
        pending = []
        for name, artifact in snapshot["artifacts"].items():
            if artifact is None:
                pending.append("missing deliverable: " + name)
        for row in state["contract"]["inputs"]:
            current = snapshot["inputs"].get(row["path"])
            if current is None or current["sha256"] != row["sha256"]:
                pending.append("changed input: " + row["path"])
        for row in snapshot["dependencies"]:
            if not row["valid"]:
                pending.append("stale dependency: " + row["session_id"] + "/" + row["task_id"])
        for definition in state["contract"]["checks"]:
            check = state["checks"].get(definition["id"])
            if not check or check["status"] != "passed" or check.get("snapshot_sha256") != digest(snapshot):
                pending.append("missing, failed or stale check: " + definition["id"])
        authors = state["gate"].get("review_authors", {})
        for name in snapshot["artifacts"]:
            if not any(name in entries for entries in authors.values()):
                pending.append("unregistered authorship: " + name)
        return pending

    def _assessments_pending(self, state: dict[str, Any], token: str) -> list[str]:
        reviews = state.get("assessments", {}).get(token, {})
        pending = []
        for requirement in state["contract"]["requirements"]:
            assessments = [row for rows in reviews.values() for row in rows if row["requirement_id"] == requirement["id"]]
            accepted = set(requirement["accepted_verdicts"])
            support = {"proof_review", "formal"} if requirement["acceptance"] == "proof" else {
                "behavior": {"behavior", "formal"}, "calculation": {"experimental", "formal", "proof_review"},
                "editorial": {"editorial"}}[requirement["acceptance"]]
            if (not assessments or len({row["verdict"] for row in assessments}) > 1
                    or any(row["verdict"] not in accepted or row["support"] not in support for row in assessments)):
                pending.append("unmet substantive requirement: " + requirement["id"])
        return pending

    def _pending(self, state: dict[str, Any], snapshot: dict[str, Any]) -> list[str]:
        pending = self._mechanical(state, snapshot)
        context = gate.prepare(self.root, state["gate"], policy_path=_POLICY)
        try:
            gate.validate(self.root, state["gate"], policy_path=_POLICY)
        except gate.ReviewError as exc:
            pending.append(str(exc))
        pending.extend(self._assessments_pending(state, context["token"]))
        return pending

    def _coordinator(self, state: dict[str, Any], actor: str) -> None:
        if actor != state["author"]:
            raise Error("This mutation requires the frozen coordinator identity.")

    def _request(self, db: sqlite3.Connection, key: tuple[str, str, str], operation: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        request_id = payload.get("request_id")
        if request_id is None:
            return None
        _identifier(request_id, "request_id")
        row = db.execute("SELECT digest,response FROM requests WHERE root=? AND session=? AND task=? AND request=?", (*key, request_id)).fetchone()
        if row is None:
            return None
        if row["digest"] != _request_digest(operation, payload):
            raise Error("request_id was already used for different input.")
        return {**decode(row["response"]), "replayed": True}

    def _save(self, db: sqlite3.Connection, key: tuple[str, str, str], state: dict[str, Any], operation: str, payload: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        state["revision"] += 1
        self.store.save(db, key, state)
        response = {**result, "revision": state["revision"], "replayed": False}
        if "request_id" in payload:
            db.execute("INSERT INTO requests VALUES (?,?,?,?,?,?)", (*key, payload["request_id"], _request_digest(operation, payload), encode(response)))
        return response

    def execute(self, operation: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            if not isinstance(payload, dict):
                raise Error("Expected a request object.")
            if operation == "progress-ack" and "request_id" in payload:
                # A successful historical replay performs no new export or
                # receipt mutation, even if its former policy is unavailable.
                required = {"session_id", "task_id", "agent_id", "expected_revision"}
                _object(payload, required, (_ENVELOPE | _FIELDS[operation]) - required)
                _identifier(payload["agent_id"], "agent_id")
                if type(payload["expected_revision"]) is not int or payload["expected_revision"] < 0:
                    raise Error("expected_revision must be a nonnegative integer.")
                key = (str(self.root), _identifier(payload["session_id"], "session_id"),
                       _identifier(payload["task_id"], "task_id"))
                with self.store.connection() as db:
                    replay = self._request(db, key, operation, payload) if db is not None else None
                if replay is not None:
                    return replay
            policy_path = Path(payload.get("policy_path", Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "progress-journal.json")) if operation in {"progress-export", "progress-ack"} else None
            progress_policy = decode(policy_path.read_text()) if operation == "progress-ack" else None
            result = self._execute(operation, payload, progress_policy=progress_policy)
            if operation == "progress-export":
                policy = decode(policy_path.read_text())
                return {"envelope": journal.export_envelope(result["task_progress"], source_root=self.root, policy=policy,
                                                            workflow_finished=result["workflow_finished"]),
                        "revision": result["revision"]}
            return result
        except journal.ProgressError as exc:
            raise Error(str(exc)) from None
        except gate.ReviewError as exc:
            raise Error(str(exc)) from None
        except (OSError, UnicodeError) as exc:
            raise Error(f"Local resource unavailable ({type(exc).__name__}).") from None
        except (TypeError, KeyError, IndexError):
            raise Error("Invalid request shape or corrupted task state.") from None

    def _execute(self, operation: str, payload: dict[str, Any], *, progress_policy: dict[str, Any] | None = None) -> dict[str, Any]:
        if operation == "active-tasks":
            _object(payload, {"session_id"})
            result = discover_active(self.store.directory, payload["session_id"], self.root)
            return {"tasks": [row for row in result["tasks"] if row["root"] == str(self.root)]}
        if operation not in _FIELDS:
            raise Error("Unknown operation.")
        hook = operation in {"hook-stop", "observe-agent"}
        read = operation in {"status", "review-context", "progress-show", "progress-export"}
        required = {"session_id", "task_id"} | (set() if hook else {"agent_id"})
        if not read:
            required.add("expected_revision")
        if hook or operation == "stop":
            required.add("request_id")
        _object(payload, required, (_ENVELOPE | _FIELDS[operation]) - required)
        key = (str(self.root), _identifier(payload["session_id"], "session_id"), _identifier(payload["task_id"], "task_id"))
        actor = _identifier(payload["agent_id"], "agent_id") if not hook else None
        if not read and (type(payload["expected_revision"]) is not int or payload["expected_revision"] < 0):
            raise Error("expected_revision must be a nonnegative integer.")
        with self.store.connection(write=not read) as db:
            if db is None:
                raise Error("Task does not exist.")
            if not read:
                replay = self._request(db, key, operation, payload)
                if replay is not None:
                    return replay
            state = self.store.load(db, key)
            if state is None:
                if operation != "plan" or payload["expected_revision"] != 0:
                    raise Error("Task does not exist; create it with plan at revision zero.")
                state = {"revision": 0, "author": actor, "started": str(uuid.uuid4()), "agents": {actor: "coordinator"},
                         "gate": {}, "checks": {}, "assessments": {}, "status": "active", "closure": None,
                         "stop_attempts": 0, "observed_agents": {}, "discovered": {}}
            elif not hook and actor not in state["agents"]:
                raise Error("Agent is not registered for this task.")
            if not read and state["revision"] != payload["expected_revision"]:
                raise RevisionConflict("Revision conflict; read status and retry explicitly.")
            if operation == "plan":
                self._coordinator(state, actor)
                contract = self._contract(payload)
                previous = state.get("contract")
                if previous:
                    for field, identity in (("requirements", "id"), ("deliverables", "path"), ("checks", "id"), ("inputs", "path")):
                        if not {row[identity] for row in previous[field]} <= {row[identity] for row in contract[field]}:
                            raise Error("Replanning cannot remove existing obligations, deliverables or checks.")
                    previous_requirements = {row["id"]: row for row in previous["requirements"]}
                    for row in contract["requirements"]:
                        old = previous_requirements.get(row["id"])
                        if old and (row["acceptance"] != old["acceptance"]
                                    or row["accepted_verdicts"] != old["accepted_verdicts"]
                                    or not set(old["deliverables"]) <= set(row["deliverables"])
                                    or not set(old["checks"]) <= set(row["checks"])):
                            raise Error("Replanning cannot weaken an existing requirement's acceptance or coverage.")
                        if row["id"] in state["discovered"] and row != state["discovered"][row["id"]]:
                            raise Error("A discovered obligation cannot be reassigned by replanning.")
                    old_profiles = {row["path"]: set(row["profiles"]) for row in previous["deliverables"]}
                    if any(not old_profiles.get(row["path"], set()) <= set(row["profiles"]) for row in contract["deliverables"]):
                        raise Error("Replanning cannot remove a deliverable profile.")
                    if not {(r["session_id"], r["task_id"]) for r in previous["depends_on"]} <= {(r["session_id"], r["task_id"]) for r in contract["depends_on"]}:
                        raise Error("Replanning cannot remove dependencies.")
                    contract["risk"] = max((contract["risk"], previous["risk"]), key=gate.MODES.index)
                for item in _list(payload.get("agents", []), "agents"):
                    _object(item, {"agent_id", "role"})
                    self._register(state, item["agent_id"], item["role"])
                state["contract"] = contract
                state.update(status="active", closure=None)
                snapshot = self._snapshot(db, key, state)
                self._sync_gate(state, snapshot)
                return self._save(db, key, state, operation, payload, {"planned": True})
            if operation.startswith("progress-"):
                current = state.get("task_progress")
                if operation == "progress-show":
                    return {"task_progress": journal.validate_progress(current) if current else None,
                            "revision": state["revision"]}
                self._coordinator(state, actor)
                if current is None:
                    if operation != "progress-update" or payload.get("task_uid") is not None:
                        raise Error("Task needs a first progress-update without task_uid.")
                    current = journal.create_progress(
                        payload["checkpoint"]["snapshot"]["objectives"][0],
                        source_alias=payload.get("source_alias", re.sub(r"[^a-z0-9-]+", "-", self.root.name.lower()).strip("-")[:64].rstrip("-") or "project"))
                elif payload.get("task_uid") != current["task_uid"]:
                    raise Error("Progress task_uid does not match the current task.")
                elif "source_alias" in payload:
                    raise Error("The progress source_alias is immutable after its first checkpoint.")
                if operation == "progress-export":
                    # The persisted checkpoint is copied before releasing SQLite;
                    # authorization and the export run without a transaction.
                    return {"task_progress": copy.deepcopy(current), "revision": state["revision"],
                            "workflow_finished": self._progress_finished(db, key, state)}
                if operation == "progress-update":
                    updated = journal.checkpoint(current, payload["checkpoint"])
                else:
                    envelope = journal.export_envelope(current, source_root=self.root, policy=progress_policy,
                                                       workflow_finished=self._progress_finished(db, key, state))
                    updated = journal.acknowledge(current, envelope=envelope, receipt=payload["receipt"])
                state["task_progress"] = updated
                return self._save(db, key, state, operation, payload, {"task_progress": updated})
            snapshot = self._snapshot(db, key, state)
            self._sync_gate(state, snapshot)
            if operation == "status":
                pending = self._pending(state, snapshot)
                context = gate.prepare(self.root, state["gate"], policy_path=_POLICY)
                return {**_summary(*key, state), "contract": state["contract"], "checks": state["checks"],
                        "gate": state["gate"], "closure": state["closure"], "pending": pending,
                        "budget": context["budget"],
                        "task_progress": state.get("task_progress"),
                        "closure_current": bool(state["status"] == "complete" and state["closure"]
                                                and state["closure"]["token"] == context["token"] and not pending),
                        "stop_attempts": state["stop_attempts"], "observed_agents": state["observed_agents"]}
            if operation == "review-context":
                context = gate.prepare(self.root, state["gate"], policy_path=_POLICY)
                return {**context, "revision": state["revision"],
                        "closure_current": bool(state["status"] == "complete" and state["closure"]
                                                and state["closure"]["token"] == context["token"] and not self._pending(state, snapshot)),
                        "pending": self._mechanical(state, snapshot)}
            if state["status"] != "active" and operation not in {"close", "stop", "hook-stop", "review-budget"}:
                raise Error("Task is closed; replan explicitly before continuing work.")
            if operation == "check":
                reservation = self._reserve_check(db, key, state, snapshot, payload)
                response = self._save(db, key, state, operation, payload, reservation)
            else:
                result = self._mutate(operation, payload, state, snapshot)
                if operation == "recover-check":
                    check = state["checks"][payload["id"]]
                    db.execute("UPDATE attempts SET data=? WHERE root=? AND session=? AND task=? AND attempt=?",
                               (encode(check), *key, check["attempt_id"]))
                return self._save(db, key, state, operation, payload, result)
        # No database transaction survives into user-supplied executable work.
        return self._run_check(key, payload, reservation, response)

    def _progress_finished(self, db: sqlite3.Connection, key: tuple[str, str, str], state: dict[str, Any]) -> bool:
        """A narrative cannot create or renew a current completion certificate."""
        if state["status"] != "complete" or not state.get("closure"):
            return False
        candidate = copy.deepcopy(state)
        try:
            snapshot = self._snapshot(db, key, candidate)
            self._sync_gate(candidate, snapshot)
            context = gate.prepare(self.root, candidate["gate"], policy_path=_POLICY)
            return candidate["closure"]["token"] == context["token"] and not self._pending(candidate, snapshot)
        except (Error, gate.ReviewError, OSError):
            return False

    def _register(self, state: dict[str, Any], identity: str, role: str) -> None:
        _identifier(identity, "registered agent")
        if role not in {"worker", "reviewer"}:
            raise Error("Registered agent role must be worker or reviewer.")
        old = state["agents"].get(identity)
        if old is not None and old != role:
            raise Error("A registered role cannot be changed.")
        state["agents"][identity] = role

    def _mutate(self, operation: str, payload: dict[str, Any], state: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
        actor = payload.get("agent_id")
        fields = {name: value for name, value in payload.items() if name in _FIELDS[operation]}
        if operation == "register-agent":
            _object(fields, {"registered_agent_id", "role"})
            self._coordinator(state, actor)
            self._register(state, fields["registered_agent_id"], fields["role"])
            return {"registered": fields["registered_agent_id"]}
        if operation == "observe-agent":
            _object(fields, {"observed_agent_id", "event"})
            identity = _identifier(fields["observed_agent_id"], "observed_agent_id")
            if fields["event"] not in {"start", "stop"}:
                raise Error("Observed event must be start or stop.")
            state["observed_agents"][identity] = fields["event"]
            return {"observed": identity, "registered": identity in state["agents"]}
        if operation == "author":
            _object(fields, {"author", "paths"})
            self._coordinator(state, actor)
            if fields["author"] not in state["agents"]:
                raise Error("Contributing author must be a registered agent.")
            state.update(status="active", closure=None)
            return gate.author(self.root, state["gate"], fields, policy_path=_POLICY)
        if operation == "review-budget":
            _object(fields, _FIELDS[operation])
            self._coordinator(state, actor)
            return gate.budget(self.root, state["gate"], fields, policy_path=_POLICY)
        if operation == "review-start":
            self._coordinator(state, actor)
            pending = self._mechanical(state, snapshot)
            if pending:
                raise Error("Review cannot start: " + "; ".join(pending))
            state.update(status="active", closure=None)
            return gate.start(self.root, state["gate"], policy_path=_POLICY,
                              quick_code_reason=fields.get("quick_code_reason"),
                              continuation=fields.get("continuation"))
        if operation == "review-report":
            _object(fields, _FIELDS[operation])
            if fields["reviewer"] != actor:
                raise Error("Report reviewer must equal the registered acting agent.")
            assessments = self._validate_assessments(state, fields)
            report = {name: value for name, value in fields.items() if name != "assessments"}
            result = gate.report(self.root, state["gate"], report, policy_path=_POLICY)
            reports = state["assessments"].setdefault(fields["token"], {})
            if actor in reports and reports[actor] != assessments:
                raise Error("A reviewer cannot replace their substantive assessment for this revision.")
            reports[actor] = assessments
            state.update(status="active", closure=None)
            return result
        if operation == "review-resolve":
            _object(fields, _FIELDS[operation])
            if fields["verifier"] != actor:
                raise Error("Resolution verifier must equal the registered acting agent.")
            state.update(status="active", closure=None)
            return gate.resolve(self.root, state["gate"], fields, policy_path=_POLICY)
        if operation == "discover":
            _object(fields, {"requirement"})
            requirement = self._requirement(fields["requirement"])
            old = next((row for row in state["contract"]["requirements"] if row["id"] == requirement["id"]), None)
            if old is not None:
                if old != requirement:
                    raise Error("A discovered obligation ID cannot be reassigned.")
                return {"discovered": requirement["id"], "unchanged": True}
            proposal = copy.deepcopy(state["contract"])
            proposal["requirements"].append(requirement)
            state["contract"] = self._contract(proposal)
            state["discovered"][requirement["id"]] = requirement
            state.update(status="active", closure=None)
            return {"discovered": requirement["id"], "unchanged": False}
        if operation == "recover-check":
            _object(fields, {"id", "attempt_id"})
            self._coordinator(state, actor)
            check = state["checks"].get(fields["id"])
            if not check or check["attempt_id"] != fields["attempt_id"] or check["status"] != "running":
                raise Error("Recovery requires the exact current running attempt.")
            check.update(status="abandoned", completed=time.time())
            state.update(status="active", closure=None)
            return {"recovered": fields["attempt_id"], "status": "abandoned"}
        if operation == "close":
            _object(fields, {"mode"})
            self._coordinator(state, actor)
            if fields["mode"] not in {"complete", "partial"}:
                raise Error("Close mode must be complete or partial.")
            pending = self._pending(state, snapshot)
            if fields["mode"] == "partial":
                state.update(status="partial", closure=None)
                return {"status": "partial", "pending": pending}
            if pending:
                raise Error("Cannot close complete: " + "; ".join(pending))
            token = gate.prepare(self.root, state["gate"], policy_path=_POLICY)["token"]
            closure = {"token": token, "version": digest({"token": token, "assessments": state["assessments"].get(token),
                                                          "gate": state["gate"]["review_gate"]})}
            state.update(status="complete", closure=closure)
            return {"status": "complete", **closure, "pending": []}
        if operation in {"stop", "hook-stop"}:
            pending = self._pending(state, snapshot)
            context = gate.prepare(self.root, state["gate"], policy_path=_POLICY)
            if not pending and state["status"] == "complete" and state["closure"]["token"] == context["token"]:
                return {"decision": "complete", "attempts": state["stop_attempts"], "pending": []}
            if not pending:
                pending = ["explicit complete closure is pending"]
            attempts = state["stop_attempts"]
            if attempts < 2:
                state["stop_attempts"] += 1
                decision = "continue"
            else:
                decision = "incomplete"
            return {"decision": decision, "attempts": state["stop_attempts"], "pending": pending}
        raise Error("Unsupported mutation.")

    def _validate_assessments(self, state: dict[str, Any], fields: dict[str, Any]) -> list[dict[str, Any]]:
        result = []
        requirements = {row["id"]: row for row in state["contract"]["requirements"]}
        for row in _list(fields["assessments"], "assessments"):
            _object(row, {"requirement_id", "verdict", "support", "evidence"})
            requirement = requirements.get(row["requirement_id"])
            if requirement is None:
                raise Error("Assessment references an unknown requirement.")
            if "correctness" not in fields["focus"] or not set(requirement["deliverables"]) <= set(fields["paths"]):
                raise Error("Substantive assessment needs correctness review covering its deliverables.")
            if row["verdict"] not in {"satisfied", "proved", "conditional", "conjecture", "refuted"}:
                raise Error("Unsupported assessment verdict.")
            if row["support"] not in {"behavior", "proof_review", "formal", "experimental", "editorial"}:
                raise Error("Unsupported assessment support.")
            if row["support"] == "formal" and not any(check["kind"] == "formal" and check["id"] in requirement["checks"]
                                                       for check in state["contract"]["checks"]):
                raise Error("Formal support requires an assigned formal check.")
            if (row["verdict"] == "proved" or (row["verdict"] == "refuted" and requirement["acceptance"] == "proof")) and row["support"] not in {"proof_review", "formal"}:
                raise Error("A proof claim requires proof review or formal support, never numeric evidence alone.")
            result.append({**row, "evidence": _text(row["evidence"], "assessment evidence")})
        if len(result) != len({row["requirement_id"] for row in result}):
            raise Error("Duplicate substantive assessment.")
        return result

    def _reserve_check(self, db: sqlite3.Connection, key: tuple[str, str, str], state: dict[str, Any], snapshot: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        if not {"id", "argv"} <= payload.keys():
            raise Error("Check needs id and argv.")
        identifier = _identifier(payload["id"], "check id")
        argv = _list(payload["argv"], "argv", nonempty=True)
        if any(not isinstance(arg, str) or "\x00" in arg for arg in argv) or not argv[0]:
            raise Error("argv must contain strings without null bytes and a nonempty executable.")
        timeout = payload.get("timeout", 300)
        if type(timeout) not in {int, float} or not math.isfinite(timeout) or not 0 < timeout <= 3600:
            raise Error("Check timeout must be positive and at most 3600 seconds.")
        definition = next((row for row in state["contract"]["checks"] if row["id"] == identifier), None)
        if definition is None or definition["definition_sha256"] != digest(argv):
            raise Error("Check argv does not match its declared definition hash.")
        old = state["checks"].get(identifier)
        if old and old["status"] == "running":
            raise Error("This check already has a running attempt; recover it explicitly if abandoned.")
        if any(not row["valid"] for row in snapshot["dependencies"]):
            raise Error("Checks require currently closed dependency versions.")
        attempt = {"attempt_id": str(uuid.uuid4()), "id": identifier,
                   "generation": old["generation"] + 1 if old else 1, "status": "running",
                   "command_sha256": digest(argv), "snapshot_sha256": digest(snapshot),
                   "started": time.time(), "timeout": timeout}
        state["checks"][identifier] = attempt
        state.update(status="active", closure=None)
        db.execute("INSERT INTO attempts VALUES (?,?,?,?,?)", (*key, attempt["attempt_id"], encode(attempt)))
        return dict(attempt)

    def _run_check(self, key: tuple[str, str, str], payload: dict[str, Any], reservation: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
        started = time.monotonic()
        status, returncode = "failed", None
        try:
            process = subprocess.run(payload["argv"], cwd=self.root, shell=False, stdin=subprocess.DEVNULL,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                     timeout=reservation["timeout"], check=False)
            returncode = process.returncode
            status = "passed" if returncode == 0 else "failed"
        except subprocess.TimeoutExpired:
            status = "timeout"
        except OSError:
            status = "launch_failed"
        result = {**reservation, "status": status, "returncode": returncode,
                  "completed": time.time(), "duration_seconds": time.monotonic() - started}
        with self.store.connection(write=True) as db:
            state = self.store.load(db, key)
            if state is None:
                raise Error("Task disappeared during check execution.")
            current = state["checks"].get(reservation["id"])
            if not current or current["attempt_id"] != reservation["attempt_id"] or current["status"] != "running":
                result["status"] = "superseded"
            else:
                try:
                    snapshot = self._snapshot(db, key, state)
                    if digest(snapshot) != reservation["snapshot_sha256"]:
                        result["status"] = "stale"
                except (Error, gate.ReviewError, OSError):
                    result["status"] = "stale"
                state["checks"][reservation["id"]] = dict(result)
            db.execute("UPDATE attempts SET data=? WHERE root=? AND session=? AND task=? AND attempt=?", (encode(result), *key, reservation["attempt_id"]))
            state["revision"] += 1
            self.store.save(db, key, state)
            response = {**result, "revision": state["revision"], "replayed": False}
            if "request_id" in payload:
                db.execute("UPDATE requests SET response=? WHERE root=? AND session=? AND task=? AND request=?", (encode(response), *key, payload["request_id"]))
            return response

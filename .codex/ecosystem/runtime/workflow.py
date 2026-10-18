#!/usr/bin/env python3
"""Constellation lifecycle: explicit scope, evidence, safe Git, and bounded closure.

Operational state lives in Git's private directory. No prompt or transcript is
stored. Hooks enforce observable conditions, not the truth of a semantic review.
"""
from __future__ import annotations

import argparse
import copy
from contextlib import contextmanager, nullcontext
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Iterator

from . import progress as journal


class Blocked(RuntimeError):
    """A condition requiring correction before publication or completion."""


def review_engine():
    """Use the one packaged review engine, never executable code from cwd."""
    from . import review_gate
    return review_gate


def run(root: Path, *args: str, timeout: int = 25, extra_env: dict[str, str] | None = None) -> str:
    operation = f"git {args[1]}" if args[0] == "git" and len(args) > 1 else "command"
    try:
        result = subprocess.run(args, cwd=root, capture_output=True, text=True,
                                timeout=timeout, env={**os.environ, **(extra_env or {}), "GIT_TERMINAL_PROMPT": "0"})
    except subprocess.TimeoutExpired:
        raise Blocked(f"{operation} timed out after {timeout}s.") from None
    if result.returncode:
        output_hash = digest((result.stdout + result.stderr).encode())
        raise Blocked(f"{operation} failed ({result.returncode}); output SHA256 {output_hash}. Retry the operation directly for diagnostics.")
    return result.stdout.rstrip("\n")


def git(root: Path, *args: str, extra_env: dict[str, str] | None = None) -> str:
    return run(root, "git", *args, extra_env=extra_env)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def stop_replay(state: dict[str, Any], request_id: str | None) -> dict[str, Any] | None:
    """Do not spend another continuation on a replayed native lifecycle event."""
    if request_id is None:
        return None
    if not isinstance(request_id, str) or not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", request_id):
        raise Blocked("Stop request_id must be a bounded event identifier.")
    previous = state.get("last_stop_request", {})
    if previous.get("id") != request_id:
        return None
    if not previous.get("incomplete"):
        return {}
    return {"continue": False, "systemMessage": "Constellation: INCOMPLETE. Replayed Stop event; inspect the existing task status."}


def record_stop(state: dict[str, Any], request_id: str | None, result: dict[str, Any]) -> dict[str, Any]:
    if request_id is not None:
        state["last_stop_request"] = {"id": request_id, "incomplete": bool(result)}
    return result


def private_path(path: str) -> bool:
    """Reject private runtime data even when it was accidentally tracked before."""
    p = path.lower()
    parts = Path(p).parts
    return (any(part in {".git", ".ssh", "secrets",
                         "turn_states", ".sync_state", ".codex_notuse",
                         "conversations", "archived_sessions", "rollouts"} for part in parts)
            or "_conversations/" in p or "conversation_archive" in p
            or "_daemon." in p or p.startswith("docs/sk_runs/")
            or p.startswith((".claude/cache/", ".claude/run/", ".codex/cache/",
                             ".codex/sessions/", ".codex/log/", ".codex/state/"))
            or Path(p).name.startswith("rollout-")
            or Path(p).name in {"auth.json", "credentials.json", "secrets.json", ".netrc",
                                  "id_rsa", "id_ed25519", ".ds_store"}
            or any(part == ".env" or part.startswith(".env.") for part in parts)
            or p.endswith((".pem", ".key", ".p12", ".pfx", ".jsonl")))


def owner_root(path: Path) -> Path:
    """Find the owning repository, including for a file not created yet."""
    directory = path if path.is_dir() else path.parent
    while not directory.is_dir():
        if directory.parent == directory:
            raise Blocked("No existing directory for the requested artifact.")
        directory = directory.parent
    return Path(git(directory, "rev-parse", "--show-toplevel")).resolve()


def safe_path(root: Path, name: str, *, deletion: bool = False) -> str:
    path = Path(name)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise Blocked(f"Expected a repository-relative file: {name}")
    target = root / path
    resolved = target.parent.resolve() if deletion and target.is_symlink() else target.resolve()
    if private_path(name) or not resolved.is_relative_to(root.resolve()):
        raise Blocked(f"Private or external path: {name}")
    components = path.parents if deletion else (path, *path.parents)
    if (target.is_dir() and not (deletion and target.is_symlink())) or any((root / part).is_symlink() for part in components):
        raise Blocked(f"Declare individual regular files: {name}")
    if owner_root(target.parent) != root.resolve():
        raise Blocked(f"Path belongs to a nested repository: {name}. Route it to its owning repository.")
    return path.as_posix()


def changed(root: Path) -> set[str]:
    tracked = git(root, "diff", "HEAD", "--name-only", "-z").split("\0")
    untracked = git(root, "ls-files", "--others", "--exclude-standard", "-z").split("\0")
    return set(tracked + untracked) - {""}


def snapshot(root: Path, paths: list[str], deletions: list[str] = ()) -> dict[str, str | None]:
    result = {}
    for p in sorted(paths):
        safe_path(root, p, deletion=p in deletions)
        target = root / p
        if target.is_symlink():
            result[p] = "symlink:" + digest(os.readlink(target).encode())
        else:
            mode = "100755:" if target.is_file() and target.stat().st_mode & 0o100 else "100644:"
            result[p] = mode + digest(target.read_bytes()) if target.is_file() else None
    return result


def publication_target(root: Path) -> dict[str, str]:
    """Identify one upstream destination without retaining potentially secret URLs."""
    branch = git(root, "symbolic-ref", "--short", "HEAD")
    remote = git(root, "config", "--get", f"branch.{branch}.remote")
    ref = git(root, "config", "--get", f"branch.{branch}.merge")
    if remote == "." or not ref.startswith("refs/heads/"):
        raise Blocked("An external upstream branch is required; configure it explicitly.")
    fetch_urls = git(root, "remote", "get-url", "--all", remote).splitlines()
    push_urls = git(root, "remote", "get-url", "--push", "--all", remote).splitlines()
    if len(fetch_urls) != 1 or len(push_urls) != 1 or fetch_urls != push_urls:
        raise Blocked("The upstream must have one identical fetch and push URL; distinct or multiple pushurl destinations require an explicit separate workflow.")
    return {"branch": branch, "remote": remote, "ref": ref,
            "url_sha256": digest(fetch_urls[0].encode())}


def sync(root: Path) -> dict[str, Any]:
    target = publication_target(root)
    git(root, "fetch", "--prune", target["remote"])
    ahead, behind = map(int, git(root, "rev-list", "--left-right", "--count", "HEAD...@{upstream}").split())
    if behind:
        if ahead:
            raise Blocked("Local and remote histories diverged. Reconcile explicitly; no automatic rebase.")
        if changed(root):
            raise Blocked("Remote has new commits and the working tree is dirty. Preserve local work before pulling.")
        git(root, "merge", "--ff-only", "@{upstream}")
    if publication_target(root) != target:
        raise Blocked("The upstream destination changed during synchronization. Restore the task destination before continuing.")
    return {"checked_at": now(), **target,
            "head": git(root, "rev-parse", "HEAD"), "ahead": ahead, "behind": 0}


def validate_blob(root: Path, path: str, blob: bytes) -> list[str]:
    """Repository code has no vault metadata schema; privacy still applies."""
    return [f"Private path cannot be committed or pushed: {path}"] if private_path(path) else []


def staged_paths(root: Path) -> set[str]:
    return set(filter(None, git(root, "diff", "--cached", "--no-renames", "--name-only", "-z").split("\0")))


def index_fingerprint(root: Path, excluded: list[str]) -> str:
    """Compare index entries and flags without reading unrelated blob content."""
    entries = git(root, "ls-files", "--stage", "-v", "-z").split("\0")
    selected = set(excluded)
    return digest("\0".join(entry for entry in entries
                            if entry and entry.split("\t", 1)[1] not in selected).encode())


def staged_gate(root: Path, paths: list[str] | None = None) -> None:
    scope = ("--", *paths) if paths is not None else ()
    git(root, "--literal-pathspecs", "diff", "--cached", "--check", *scope)
    errors: list[str] = []
    staged = git(root, "--literal-pathspecs", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z", *scope).split("\0")
    for p in filter(None, staged):
        # The native profile validates paths, not repository-specific content.
        # Never read a private blob just to refuse its publication.
        errors.extend(validate_blob(root, p, b""))
    if errors:
        raise Blocked("\n".join(errors))


def stored_snapshot(root: Path, paths: list[str], revision: str | None = None) -> dict[str, str | None]:
    """Hash the selected Git blobs, independently of their working-tree copies."""
    command = ("ls-tree", "-z", revision) if revision is not None else ("ls-files", "--stage", "-z")
    entries = git(root, "--literal-pathspecs", *command, "--", *paths)
    result: dict[str, str | None] = dict.fromkeys(paths)
    for entry in filter(None, entries.split("\0")):
        metadata, name = entry.split("\t", 1)
        mode, middle, last = metadata.split()
        if revision is None:
            if last != "0":
                raise Blocked("The selected index contains unresolved merge stages.")
            object_id = middle
        else:
            if middle != "blob":
                raise Blocked("A reviewed artifact was replaced by a non-file Git object.")
            object_id = last
        blob = subprocess.run(["git", "cat-file", "blob", object_id], cwd=root,
                              capture_output=True, timeout=25)
        if blob.returncode:
            raise Blocked("Could not verify a selected Git blob against the review.")
        result[name] = ("symlink:" if mode == "120000" else mode + ":") + digest(blob.stdout)
    return result


def outgoing_gate(root: Path, local: str, remote_sha: str) -> None:
    if set(local) == {"0"}:
        return
    # A different remote knowing an object does not authorize its transmission
    # to this destination. A new branch needs its reachable history checked.
    revision = [local] if set(remote_sha) == {"0"} else [f"{remote_sha}..{local}"]
    commits = git(root, "rev-list", *revision).splitlines()
    errors = []
    for commit in commits:
        paths = git(root, "diff-tree", "--root", "-m", "--no-commit-id", "--name-only",
                    "-r", "--diff-filter=ACMR", "-z", commit).split("\0")
        for p in set(filter(None, paths)):
            if private_path(p):
                errors.append(f"{commit[:10]} includes private data: {p}")
    if errors:
        raise Blocked("\n".join(errors[:30]))


class Workflow:
    def __init__(self, root: Path, session: str, *, create_state: bool = True):
        self.root = root.resolve()
        self.session = session
        self.home = Path(git(root, "rev-parse", "--path-format=absolute", "--git-path", "constellation"))
        if create_state:
            self.home.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.key = digest(session.encode())[:24]
        self.path = self.home / f"{self.key}.json"

    @contextmanager
    def lock(self) -> Iterator[None]:
        self.home.mkdir(parents=True, exist_ok=True, mode=0o700)
        with (self.home / "workflow.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield

    def log(self, event: str, **fields: Any) -> None:
        with (self.home / "events.jsonl").open("a") as stream:
            stream.write(json.dumps({"at": now(), "session": self.key, "event": event, **fields}) + "\n")

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            raise Blocked("No active task contract. Run workflow.py begin, then plan.")
        return json.loads(self.path.read_text())

    def save(self, state: dict[str, Any]) -> None:
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")
        temp.replace(self.path)

    def begin(self, turn: str) -> dict[str, Any]:
        if self.path.exists():
            history = self.home / "history"
            history.mkdir(exist_ok=True, mode=0o700)
            old = self.path.read_bytes()
            (history / f"{self.key}-{digest(old)[:16]}.json").write_bytes(old)
        state: dict[str, Any] = {"turn": turn, "started": now(), "initial_head": git(self.root, "rev-parse", "HEAD"),
                                 "baseline_dirty": sorted(changed(self.root)), "requirements": [],
                                 "paths": [], "checks": [], "commits": [], "stop_attempts": 0,
                                 "author": self.session}
        try:
            state["target"] = publication_target(self.root)
            synchronized = sync(self.root)
            self.ensure_target(state)
            # Accepted upstream history precedes this task's recovery scope.
            state.update(sync=synchronized, initial_head=synchronized["head"])
        except (Blocked, subprocess.TimeoutExpired) as exc:
            state["sync_error"] = str(exc)
        self.save(state)
        self.log("begin", turn=turn, sync_ok="sync" in state)
        return state

    def ensure_target(self, state: dict[str, Any]) -> dict[str, str]:
        target = publication_target(self.root)
        if not state.get("target"):
            raise Blocked("The task has no frozen upstream destination. Run plan again before continuing.")
        if target != state["target"]:
            raise Blocked("The branch or upstream destination changed since the task began. Restore it or begin an explicitly separate task.")
        return target

    def sync_upstream(self, state: dict[str, Any]) -> dict[str, Any]:
        self.ensure_target(state)
        info = sync(self.root)
        self.ensure_target(state)
        return info

    def plan(self, spec: dict[str, Any]) -> dict[str, Any]:
        state = self.load()
        self.identify_author(state)
        requirements = spec.get("requirements")
        if not isinstance(requirements, list) or not requirements or not all(isinstance(r, str) and r.strip() for r in requirements):
            raise Blocked("Plan requires a nonempty list of observable requirements.")
        deletions = spec.get("deletions", [])
        if not isinstance(deletions, list) or not all(isinstance(p, str) for p in deletions):
            raise Blocked("Deletions must list exact tracked file paths.")
        paths = [safe_path(self.root, p, deletion=p in deletions) for p in spec.get("paths", [])]
        if not set(deletions) <= set(paths) or len(set(deletions)) != len(deletions):
            raise Blocked("Deletions must be a unique subset of declared paths.")
        previous_deletions = state.get("deletions", [])
        for p in deletions:
            if p not in previous_deletions:
                git(self.root, "--literal-pathspecs", "ls-files", "--error-unmatch", "--", p)
        if paths or not state.get("sync_error"):
            # Renewing a plan pins contracts made before destination freezing,
            # while preserving their original ownership baseline and evidence.
            if not state.get("target"):
                target = publication_target(self.root)
                previous = state.get("sync", {})
                if (previous or state.get("requirements")) and any(
                        previous.get(k) != value for k, value in target.items()
                        if k != "url_sha256" or k in previous):
                    raise Blocked("The upstream changed since begin; restore the original destination.")
                state["target"] = target
            self.ensure_target(state)
            if state.get("sync_error"):
                try:
                    first_sync = not state.get("sync")
                    state["sync"] = self.sync_upstream(state)
                    if first_sync:
                        state["initial_head"] = state["sync"]["head"]
                    state.pop("sync_error", None)
                except (Blocked, subprocess.TimeoutExpired) as exc:
                    state["sync_error"] = str(exc)
                    self.save(state)
                    raise
        existing = set(paths) & set(state["baseline_dirty"])
        adoption = spec.get("adopt_existing", {})
        if any(not isinstance(adoption.get(p), str) or not adoption[p].strip() for p in existing):
            raise Blocked("Some files were already modified. Inspect ownership and supply an adopt_existing justification per file.")
        if len(set(requirements)) != len(requirements) or len(set(paths)) != len(paths):
            raise Blocked("Requirements and paths must be unique.")
        state.update(requirements=requirements, paths=paths, deletions=deletions, review=None, finished=None,
                     adoption={p: adoption[p] for p in existing},
                     unrelated=spec.get("unrelated", {}))
        self.save(state)
        self.log("plan", requirements=len(requirements), paths=paths)
        return state

    def progress_operation(self, operation: str, payload: dict[str, Any] | None = None,
                           *, policy: dict[str, Any] | None = None) -> dict[str, Any]:
        """Curate the existing task store; callers retain its normal Git lock."""
        if operation not in {"show", "update", "export", "ack"}:
            raise Blocked("Unknown progress operation.")
        payload = {} if payload is None else payload
        fields = {"show": set(), "update": {"task_uid", "expected_task_start", "expected_revision", "checkpoint", "source_alias"},
                  "export": {"task_uid"}, "ack": {"task_uid", "expected_revision", "receipt"}}
        if not isinstance(payload, dict) or payload.keys() - fields[operation]:
            raise Blocked("Unknown progress request fields.")
        state = self.load()
        current = state.get("task_progress")
        if operation == "show":
            return {"task_progress": journal.validate_progress(current) if current else None,
                    "expected_task_start": state["started"],
                    "revision": len(current["milestones"]) if current else 0}
        if state.get("author") not in {None, self.key, self.session}:
            raise Blocked("Progress requires the frozen coordinator identity.")
        if owner_root(self.root) != self.root:
            raise Blocked("Repository ownership changed since the task began.")
        if state.get("target"):
            self.ensure_target(state)
        if current is None:
            if (operation != "update" or payload.get("task_uid") is not None
                    or payload.get("expected_task_start") != state["started"]):
                raise Blocked("First progress-update requires the current expected_task_start and no task_uid.")
            if not state.get("requirements"):
                raise Blocked("Declare the task objectives with plan before recording progress.")
            try:
                current = journal.create_progress(payload["checkpoint"]["snapshot"]["objectives"][0],
                    source_alias=payload.get("source_alias", re.sub(r"[^a-z0-9-]+", "-", self.root.name.lower()).strip("-")[:64].rstrip("-") or "project"))
            except (journal.ProgressError, KeyError, IndexError, TypeError) as exc:
                raise Blocked("The first checkpoint requires valid curated objectives.") from exc
        elif payload.get("task_uid") != current["task_uid"]:
            # A lost response to the first checkpoint leaves the caller without
            # its UUID. Only the exact initial request may replay in that case.
            if (operation == "update" and payload.get("task_uid") is None
                    and payload.get("expected_task_start") == state["started"]
                    and payload.get("source_alias", current["source_alias"]) == current["source_alias"]
                    and type(payload.get("expected_revision")) is int and payload["expected_revision"] == 0):
                try:
                    replay = journal.checkpoint(current, payload["checkpoint"])
                except (journal.ProgressError, KeyError) as exc:
                    raise Blocked(str(exc)) from None
                if replay == current:
                    return {"task_progress": current, "revision": len(current["milestones"])}
            raise Blocked("Progress task_uid does not match the current task.")
        elif "source_alias" in payload:
            raise Blocked("The progress source_alias is immutable after its first checkpoint.")
        try:
            if operation == "export":
                # The caller exports this copy only after releasing source locks.
                return {"task_progress": copy.deepcopy(current), "workflow_finished": self._progress_finished(state)}
            revision = payload.get("expected_revision")
            if type(revision) is not int or revision < 0:
                raise Blocked("Progress expected_revision must be a nonnegative integer.")
            if operation == "update":
                updated = journal.checkpoint(current, payload["checkpoint"])
                if updated != current and revision != len(current["milestones"]):
                    raise Blocked("Progress revision conflict; read progress-show and retry explicitly.")
            else:
                if revision != len(current["milestones"]):
                    raise Blocked("Progress revision conflict; read progress-show and retry explicitly.")
                envelope = journal.export_envelope(current, source_root=self.root, policy=policy,
                                                   workflow_finished=self._progress_finished(state))
                updated = journal.acknowledge(current, envelope=envelope, receipt=payload["receipt"])
        except (journal.ProgressError, KeyError) as exc:
            raise Blocked(str(exc)) from None
        if updated != state.get("task_progress"):
            state["task_progress"] = updated
            self.save(state)
        return {"task_progress": updated, "revision": len(updated["milestones"])}

    @staticmethod
    def progress_policy(policy_path: Path | None = None) -> dict[str, Any]:
        """Read explicit local policy before entering a source transaction."""
        policy_path = policy_path or Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "progress-journal.json"
        return json.loads(policy_path.read_text())

    def _progress_finished(self, state: dict[str, Any]) -> bool:
        if not state.get("finished"):
            return False
        try:
            self.reviewed(state)
            self.checked_scope(state)
            return git(self.root, "rev-parse", "HEAD") == state["finished"]["head"]
        except (Blocked, KeyError, OSError):
            return False

    def export_progress(self, prepared: dict[str, Any], policy_path: Path | None = None) -> dict[str, Any]:
        """Export a durable checkpoint without holding a source or vault lock."""
        try:
            policy = self.progress_policy(policy_path)
            envelope = journal.export_envelope(prepared["task_progress"], source_root=self.root, policy=policy,
                                               workflow_finished=prepared["workflow_finished"])
        except journal.ProgressError as exc:
            raise Blocked(str(exc)) from None
        return {"envelope": envelope}

    def check(self, command: list[str], *, timeout: int = 300) -> dict[str, Any]:
        state = self.load()
        if not command:
            raise Blocked("check needs a command after --.")
        if type(timeout) is not int or not 1 <= timeout <= 3600:
            raise Blocked("Check timeout must be an integer between 1 and 3600 seconds.")
        before = snapshot(self.root, state["paths"], state.get("deletions", []))
        record = {"command_sha256": digest(json.dumps(command).encode()), "exit_code": -1, "at": now(),
                  "timeout_seconds": timeout, "snapshot": before, "changed_during_check": False,
                  "output_sha256": digest(b""), "completed": False}
        # Persist a failing attempt before execution. Interruption or failure to
        # inspect a mutated artifact can never revive an earlier successful run.
        state["checks"].append(record)
        state["review"] = None
        state["finished"] = None
        self.save(state)
        try:
            result = subprocess.run(command, cwd=self.root, capture_output=True, timeout=timeout)
        except (OSError, subprocess.TimeoutExpired) as exc:
            # An unlaunchable or timed-out check must supersede its old success.
            result = subprocess.CompletedProcess(command, -1, b"", type(exc).__name__.encode())
        try:
            after = snapshot(self.root, state["paths"], state.get("deletions", []))
        except (Blocked, OSError):
            after = None
        record.update(exit_code=result.returncode, changed_during_check=before != after,
                      output_sha256=digest(result.stdout + result.stderr), completed=True)
        self.save(state)
        print(result.stdout.decode("utf-8", errors="replace"), end="")
        print(result.stderr.decode("utf-8", errors="replace"), end="", file=sys.stderr)
        if result.returncode or before != after:
            raise Blocked("Check failed or modified a declared artifact; correct and rerun it.")
        return record

    def review_operation(self, operation: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if operation not in {"prepare", "start", "report", "resolve", "author", "budget"}:
            raise Blocked("Unknown independent review operation.")
        if payload is not None and not isinstance(payload, dict):
            raise Blocked("Expected an independent review request object.")
        state = self.load()
        self.identify_author(state)
        self.ensure_target(state)
        if operation == "budget" and state.get("author") != self.session:
            raise Blocked("Review budget requires the frozen coordinator identity.")
        engine = review_engine()
        try:
            if operation == "start" and payload and payload.get("risk"):
                levels = ("quick", "standard", "deep")
                risk = payload["risk"]
                if risk not in levels:
                    raise Blocked("Risk must be quick, standard or deep.")
                previous = state.get("review_risk", "quick")
                if levels.index(risk) < levels.index(previous):
                    raise Blocked("The risk floor cannot be lowered during an active task.")
                state["review_risk"] = risk
            function = getattr(engine, operation)
            if operation == "start":
                result = function(self.root, state, quick_code_reason=(payload or {}).get("quick_code_reason"),
                                  continuation=(payload or {}).get("continuation"))
            else:
                result = function(self.root, state, payload) if operation in {"report", "resolve", "author", "budget"} else function(self.root, state)
        except engine.ReviewError as exc:
            raise Blocked(str(exc)) from exc
        if operation != "prepare":
            self.save(state)
            self.log("independent_review_" + operation)
        return result

    def identify_author(self, state: dict[str, Any]) -> None:
        # Session IDs and reviewer IDs use the same declared representation.
        # Upgrade earlier, not-yet-reviewed contracts without touching a ledger.
        if not state.get("review_gate") and not state.get("review_budget") and state.get("author") in {None, self.key}:
            state["author"] = self.session

    def independent_reviewed(self, state: dict[str, Any]) -> None:
        engine = review_engine()
        try:
            engine.validate(self.root, state)
        except engine.ReviewError as exc:
            raise Blocked(str(exc)) from exc

    def review(self, evidence: dict[str, Any]) -> dict[str, Any]:
        state = self.load()
        if not state["requirements"] or set(evidence) != set(state["requirements"]):
            raise Blocked("Supply evidence for every requirement, using the exact requirement as the key.")
        if not all(isinstance(v, str) and v.strip() for v in evidence.values()):
            raise Blocked("Review evidence must be nonempty text, not a boolean assertion.")
        current = snapshot(self.root, state["paths"], state.get("deletions", []))
        for p, sha in current.items():
            if p in state.get("deletions", []):
                if sha is not None:
                    raise Blocked(f"Declared deletion still exists: {p}")
                continue
            if sha is None:
                raise Blocked(f"Declared artifact missing: {p}")
            errors = self.validate_blob(p, (self.root / p).read_bytes())
            if errors:
                raise Blocked("\n".join(errors))
        # Each command's latest result supersedes its older success, including
        # a failure on identical bytes. A changed artifact requires a fresh run.
        latest = {c["command_sha256"]: c for c in state["checks"]}
        required = [p for p in state["paths"] if not p.endswith((".md", ".rst", ".txt"))]
        passing = [c for c in latest.values() if c["exit_code"] == 0 and not c["changed_during_check"]
                   and all(c["snapshot"].get(p) == current[p] for p in required)]
        if any(c["exit_code"] != 0 or c["changed_during_check"] for c in latest.values()):
            raise Blocked("A check is still failing; rerun that check successfully before review.")
        if required and not passing:
            raise Blocked("Code changes need a passing check recorded against the current artifacts.")
        self.independent_reviewed(state)
        state["review"] = {"at": now(), "evidence": evidence, "snapshot": current,
                           "kind": "model_semantic_review_with_mechanical_validation"}
        state["finished"] = None
        self.save(state)
        self.log("review", paths=state["paths"])
        return {"reviewed": True, "requirements": len(evidence)}

    def reviewed(self, state: dict[str, Any]) -> None:
        if not state.get("review") or state["review"]["snapshot"] != snapshot(self.root, state["paths"], state.get("deletions", [])):
            raise Blocked("Missing or stale review. Compare the actual result with every requirement.")
        self.independent_reviewed(state)

    def guard_patch(self, payload: dict[str, Any], cwd: Path, *, active_only: bool = False) -> None:
        state = self.load()
        if active_only and state.get("finished"):
            return
        if state.get("sync_error") or not state["requirements"]:
            raise Blocked(state.get("sync_error") or "Declare the task requirements and paths before editing.")
        self.ensure_target(state)
        inputs = payload.get("tool_input", {})
        if not isinstance(inputs, (str, dict)):
            raise Blocked("Unrecognized patch payload; expected a patch string or object.")
        patch = inputs if isinstance(inputs, str) else inputs.get("input", inputs.get("patch", inputs.get("command", "")))
        if not isinstance(patch, str):
            raise Blocked("Unrecognized patch payload; expected a patch string.")
        paths = re.findall(r"^\*\*\* (Add File|Update File|Delete File|Move to): (.+)$", patch, re.M)
        if not paths:
            raise Blocked("Unrecognized patch payload; no edit was authorized by this guard.")
        # Normalize the working directory (macOS exposes /var via /private/var),
        # but leave patch components unresolved so safe_path can reject aliases.
        cwd = cwd.resolve()
        for action, name in paths:
            target = Path(name) if Path(name).is_absolute() else cwd / name
            name_in_root = os.path.relpath(target, self.root)
            deletion = name_in_root in state.get("deletions", [])
            if deletion and action != "Delete File":
                raise Blocked(f"Declared deletion only authorizes Delete File: {name_in_root}")
            relative = safe_path(self.root, name_in_root, deletion=deletion)
            if relative not in state["paths"]:
                raise Blocked(f"Undeclared patch path: {relative}")

    def checked_scope(self, state: dict[str, Any]) -> set[str]:
        dirty = changed(self.root)
        pending = set(state["paths"]) & dirty
        if pending:
            raise Blocked(f"Uncommitted task files: {', '.join(sorted(pending))}")
        unexpected = dirty - set(state["baseline_dirty"]) - set(state["paths"])
        unknown = {p for p in unexpected if not private_path(p) and not state.get("unrelated", {}).get(p)}
        if unknown:
            raise Blocked(f"New undeclared files need scope review: {', '.join(sorted(unknown))}. Declare task paths or explain unrelated paths in plan.")
        return unexpected

    def validate_blob(self, path: str, blob: bytes) -> list[str]:
        """Domain adapters may add artifact validation without another lifecycle."""
        return validate_blob(self.root, path, blob)

    def staged_gate(self, paths: list[str] | None = None) -> None:
        staged_gate(self.root, paths)

    def outgoing_gate(self, local: str, remote_sha: str) -> None:
        outgoing_gate(self.root, local, remote_sha)

    def publish(self) -> dict[str, Any]:
        state = self.load()
        if state.get("publication_blocker"):
            raise Blocked(state["publication_blocker"])
        info = self.sync_upstream(state)
        local = git(self.root, "rev-parse", "HEAD")
        remote_sha = git(self.root, "rev-parse", "@{upstream}")
        self.outgoing_gate(local, remote_sha)
        self.ensure_target(state)
        if info["ahead"]:
            git(self.root, "push", info["remote"], f"{local}:{info['ref']}")
        actual = git(self.root, "ls-remote", "--exit-code", info["remote"], info["ref"]).split()[0]
        self.ensure_target(state)
        if actual != local or git(self.root, "rev-parse", "HEAD") != local:
            raise Blocked("Remote verification failed: the upstream does not match local HEAD.")
        self.log("remote_verified", commit=local)
        return {"head": local, "remote": info["remote"], "ref": info["ref"], "verified_at": now()}

    def commit(self, paths: list[str], message: str, *, preserve_index: bool = False) -> dict[str, Any]:
        state = self.load()
        if state.get("publication_blocker"):
            raise Blocked(state["publication_blocker"])
        state.update(finished=None, publication=None)
        self.save(state)
        self.reviewed(state)
        if not paths or not set(paths) <= set(state["paths"]):
            raise Blocked("Commit paths must be a nonempty subset of the declared artifacts.")
        initial_staged = staged_paths(self.root)
        if initial_staged and not preserve_index:
            raise Blocked("Index already contains staged work. Preserve it and resolve ownership explicitly.")
        if preserve_index and initial_staged & set(paths):
            raise Blocked("Selected paths overlap existing staged work; preserve-index requires disjoint ownership.")
        preserved = index_fingerprint(self.root, paths) if preserve_index else None
        self.sync_upstream(state)
        self.reviewed(state)
        parent = git(self.root, "rev-parse", "HEAD")
        git(self.root, "--literal-pathspecs", "add", "--", *paths)
        self.staged_gate(paths if preserve_index else None)
        staged = staged_paths(self.root)
        if preserve_index and index_fingerprint(self.root, paths) != preserved:
            raise Blocked("Unrelated index entries changed concurrently. They were not committed by this workflow.")
        if not preserve_index and not staged <= set(paths):
            raise Blocked("The index changed concurrently and contains unselected work. It was preserved.")
        expected = {path: state["review"]["snapshot"][path] for path in paths}
        if stored_snapshot(self.root, paths) != expected:
            raise Blocked("Staged content differs from the reviewed artifacts. Preserve and review the changes before committing.")
        self.reviewed(state)
        # Hooks and other Git clients do not share our lifecycle lock. Inspect
        # the durable commit before it can leave this machine, including retry
        # after a crash or failed event write immediately following Git's commit.
        state["publication_blocker"] = ("A local commit failed verification against the reviewed scope. "
                                        "It was preserved without publication; reconcile it explicitly before publishing.")
        self.save(state)
        try:
            commit_env = {"CONSTELLATION_COMMIT_OWNER": "native"}
            if preserve_index:
                git(self.root, "--literal-pathspecs", "commit", "--only", "-m", message, "--", *paths,
                    extra_env=commit_env)
            else:
                git(self.root, "commit", "-m", message, extra_env=commit_env)
        except Blocked:
            if git(self.root, "rev-parse", "HEAD") == parent:
                state.pop("publication_blocker")
                self.save(state)
            raise
        commit = git(self.root, "rev-parse", "HEAD")
        state["commits"].append(commit)
        self.save(state)
        self.log("commit", commit=commit, paths=paths)
        if preserve_index and index_fingerprint(self.root, paths) != preserved:
            raise Blocked("Unrelated index entries changed during commit. The local commit was retained without publication.")
        actual_paths = set(filter(None, git(self.root, "diff-tree", "--no-commit-id", "--no-renames", "--name-only", "-r", "-z", parent, commit).split("\0")))
        if git(self.root, "rev-parse", f"{commit}^") != parent or not actual_paths <= set(paths):
            raise Blocked(state["publication_blocker"])
        if stored_snapshot(self.root, paths, commit) != expected:
            raise Blocked(state["publication_blocker"])
        self.reviewed(state)
        state.pop("publication_blocker")
        self.save(state)
        published = self.publish()
        state["publication"] = published
        self.save(state)
        return published

    def recover(self, expected_head: str) -> dict[str, Any]:
        """Audit an externally repaired commit without modifying Git or publishing."""
        state = self.load()
        if not state.get("publication_blocker"):
            raise Blocked("There is no blocked publication to recover.")
        if not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", expected_head):
            raise Blocked("Recovery requires the exact full commit SHA authorized for verification.")
        if git(self.root, "rev-parse", "HEAD") != expected_head:
            raise Blocked("HEAD does not match the expected recovery commit.")
        self.ensure_target(state)
        self.reviewed(state)
        expected = state["review"]["snapshot"]
        if stored_snapshot(self.root, state["paths"], expected_head) != expected:
            raise Blocked("The recovery commit does not contain the reviewed artifacts.")
        initial = state["initial_head"]
        try:
            git(self.root, "merge-base", "--is-ancestor", initial, expected_head)
        except Blocked:
            raise Blocked("Recovery must descend from the task's initial commit.") from None
        commits = git(self.root, "rev-list", "--reverse", f"{initial}..{expected_head}").splitlines()
        for commit in commits:
            paths = set(filter(None, git(self.root, "diff-tree", "--root", "-m", "--no-commit-id",
                                         "--no-renames", "--name-only", "-r", "-z", commit).split("\0")))
            if not paths <= set(state["paths"]) or any(private_path(path) for path in paths):
                raise Blocked("Recovery history contains private or undeclared paths; preserve the blocker and reconcile the history explicitly.")
        self.ensure_target(state)
        self.reviewed(state)
        if git(self.root, "rev-parse", "HEAD") != expected_head:
            raise Blocked("HEAD changed during recovery verification.")
        record = {"head": expected_head, "initial_head": initial, "commits": commits, "at": now()}
        self.log("recovery_verified", **record)
        state.setdefault("recoveries", []).append(record)
        state.update(commits=commits, publication=None, finished=None, stop_attempts=0)
        state.pop("publication_blocker")
        self.save(state)
        return {"recovered": True, "head": expected_head, "audited_commits": len(commits),
                "publication_verified": False}

    def finish(self) -> dict[str, Any]:
        state = self.load()
        state.update(finished=None, publication=None)
        self.save(state)
        self.reviewed(state)
        self.checked_scope(state)
        publication = self.publish()
        # Synchronization can fast-forward a clean tree after the first review.
        self.reviewed(state)
        unexpected = self.checked_scope(state)
        state.update(publication=publication, finished={"at": now(), "head": publication["head"]},
                     unrelated_new_paths=sorted(unexpected))
        self.save(state)
        self.log("finish", commit=publication["head"])
        return {"completed": True, "publication": publication, "unrelated_new_paths": sorted(unexpected)}

    def stop(self, request_id: str | None = None, *, active_only: bool = False) -> dict[str, Any]:
        state = self.load()
        if active_only and state.get("finished"):
            return {}
        replay = stop_replay(state, request_id)
        if replay is not None:
            return replay
        try:
            self.ensure_target(state)
            self.reviewed(state)
            if not state.get("finished") or state["finished"]["head"] != git(self.root, "rev-parse", "HEAD"):
                raise Blocked("Run workflow.py finish to verify commits and the remote branch.")
            self.checked_scope(state)
            result = record_stop(state, request_id, {})
            if request_id is not None:
                self.save(state)
            return result
        except Blocked as exc:
            state["stop_attempts"] += 1
            self.log("stop_incomplete", reason=str(exc))
            if state["stop_attempts"] > 2:
                result = {"continue": False, "stopReason": f"Constellation task incomplete: {exc}",
                        "systemMessage": f"Constellation: INCOMPLETE. {exc}"}
            else:
                result = {"decision": "block", "reason": f"[CONSTELLATION-CONTINUE:{self.key}] {exc} Follow .codex/README.md. Report any real blocker; never claim completion without evidence."}
            record_stop(state, request_id, result)
            self.save(state)
            return result


def subagent_context(session: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Return worker instructions without creating or consulting lifecycle state."""
    context = (f"Constellation worker {payload.get('agent_id', 'unknown')!r}; parent session is {session!r}. "
               f"Use --session {session!r} when referring to the coordinator's contract. "
               "Read the root AGENTS.md, .codex/WORKSPACE.md and the assigned repositories' AGENTS.md, "
               ".codex/PROJECT.md and applicable directory instructions. For research read .codex/RESEARCH.md. "
               "Work only on your assigned exact files; preserve other agents' changes. "
               "Do not begin, reset or replace the parent's contract. Do not commit or push; the coordinator publishes. "
               "Report your actual native agent ID, edited paths, results and verification evidence to the coordinator "
               "for review-author registration before independent review. Do not fabricate agent identities or reports. "
               "Do not inspect or manage worktree counts. Never persist prompts or transcripts in reports or artifacts.")
    return {"hookSpecificOutput": {"hookEventName": "SubagentStart", "additionalContext": context}}


def main(argv: list[str] | None = None, *, workflow_factory: type[Workflow] = Workflow) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--session", default=os.environ.get("CODEX_THREAD_ID", "manual"))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("begin").add_argument("--turn", default="manual")
    sub.add_parser("plan")
    sub.add_parser("review")
    for name in ("review-context", "review-start", "review-report", "review-resolve", "review-author", "review-budget"):
        command = sub.add_parser(name)
        if name == "review-start":
            command.add_argument("--risk", choices=("quick", "standard", "deep"))
            command.add_argument("--quick-code-reason", help="Justify a trivial ordinary code change before its first review round.")
            command.add_argument("--continuation-reason", help="Explain why another review iteration is useful.")
            command.add_argument("--continuation-next-action", help="Describe the concrete next review action.")
    sub.add_parser("status")
    for name in ("progress-show", "progress-update"):
        sub.add_parser(name)
    sub.add_parser("progress-ack").add_argument("--policy", type=Path)
    progress_export = sub.add_parser("progress-export")
    progress_export.add_argument("--task-uid", required=True)
    progress_export.add_argument("--policy", type=Path)
    sub.add_parser("finish")
    sub.add_parser("recover").add_argument("expected_head")
    check = sub.add_parser("check")
    check.add_argument("--timeout", type=int, default=300)
    check.add_argument("argv", nargs=argparse.REMAINDER)
    commit = sub.add_parser("commit")
    commit.add_argument("-m", "--message", required=True)
    commit.add_argument("--preserve-index", action="store_true")
    commit.add_argument("paths", nargs="+")
    sub.add_parser("hook").add_argument("event", choices=["prompt", "pre-tool", "stop", "subagent-start"])
    sub.add_parser("git-hook").add_argument("event", choices=["pre-commit", "post-commit", "pre-push"])
    args = parser.parse_args(argv)
    if args.command == "review-start" and ((args.continuation_reason is None) != (args.continuation_next_action is None)):
        parser.error("--continuation-reason and --continuation-next-action must be supplied together.")
    if args.command == "hook":
        # Existing trusted definitions remain live in open clients after a
        # plugin update. Route them through the fixed package gateway too.
        from ..hooks import main as hooks_main
        events = {"prompt": "UserPromptSubmit", "pre-tool": "PreToolUse",
                  "stop": "Stop", "subagent-start": "SubagentStart"}
        return hooks_main([events[args.event]])
    payload = json.load(sys.stdin) if args.command in {"plan", "review", "review-report", "review-resolve", "review-author", "review-budget", "progress-update", "progress-ack"} else {}
    if not isinstance(payload, dict):
        raise Blocked("Expected a JSON request object.")
    cwd = Path(payload.get("cwd", args.root)).absolute()
    root = Path(git(cwd, "rev-parse", "--show-toplevel"))
    workflow = workflow_factory(root, payload.get("session_id", args.session))
    progress_policy = workflow.progress_policy(args.policy) if args.command == "progress-ack" else None
    # Git runs its hooks synchronously inside commit/push; reacquiring the parent
    # workflow lock here would deadlock. JSONL append is one write per event.
    with (nullcontext() if args.command == "git-hook" else workflow.lock()):
        if args.command == "begin":
            result = workflow.begin(args.turn)
        elif args.command == "plan":
            result = workflow.plan(payload)
        elif args.command == "review":
            result = workflow.review(payload)
        elif args.command.startswith("review-"):
            operation = args.command.removeprefix("review-")
            if operation == "start":
                payload = {"risk": args.risk, "quick_code_reason": args.quick_code_reason}
                if args.continuation_reason is not None:
                    payload["continuation"] = {"reason": args.continuation_reason,
                                               "next_action": args.continuation_next_action}
            result = workflow.review_operation("prepare" if operation == "context" else operation, payload)
        elif args.command == "status":
            result = workflow.load()
        elif args.command.startswith("progress-"):
            operation = args.command.removeprefix("progress-")
            if operation == "export":
                payload = {"task_uid": args.task_uid}
            result = workflow.progress_operation(operation, payload, policy=progress_policy)
        elif args.command == "check":
            result = workflow.check(args.argv[1:] if args.argv[:1] == ["--"] else args.argv, timeout=args.timeout)
        elif args.command == "commit":
            result = workflow.commit(args.paths, args.message, preserve_index=args.preserve_index)
        elif args.command == "finish":
            result = workflow.finish()
        elif args.command == "recover":
            result = workflow.recover(args.expected_head)
        elif args.command == "git-hook":
            if args.event == "pre-commit":
                workflow.staged_gate()
                workflow.log("git_commit_preflight")
            elif args.event == "post-commit":
                workflow.log("git_committed", commit=git(root, "rev-parse", "HEAD"))
            else:
                for line in sys.stdin:
                    _, local, _, remote_sha = line.split()
                    workflow.outgoing_gate(local, remote_sha)
                workflow.log("git_push_preflight")
            result = {}
    if args.command == "progress-export":
        result = workflow.export_progress(result, args.policy)
    print(json.dumps(result, ensure_ascii=False))
    return 2 if args.command == "begin" and result.get("sync_error") else 0


def entrypoint(argv: list[str] | None = None, **options: Any) -> int:
    try:
        return main(argv, **options)
    except (Blocked, subprocess.TimeoutExpired, OSError, ValueError) as exc:
        print(f"Constellation: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.modules[__package__ + ".workflow"] = sys.modules[__name__]
    raise SystemExit(entrypoint())

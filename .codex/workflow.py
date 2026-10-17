#!/usr/bin/env python3
"""Constellation lifecycle: explicit scope, evidence, safe Git, and bounded closure.

Operational state lives in Git's private directory. No prompt or transcript is
stored. Hooks enforce observable conditions, not the truth of a semantic review.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager, nullcontext
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Iterator



class Blocked(RuntimeError):
    """A condition requiring correction before publication or completion."""


def review_engine():
    """Load the sibling engine also when this module is loaded by file path."""
    name = "constellation_review_gate"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name("review_gate.py"))
        if spec is None or spec.loader is None:
            raise Blocked("Independent review engine is unavailable.")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            sys.modules.pop(name, None)
            raise
    return sys.modules[name]


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
    def __init__(self, root: Path, session: str):
        self.root = root.resolve()
        self.session = session
        self.home = Path(git(root, "rev-parse", "--path-format=absolute", "--git-path", "constellation"))
        self.home.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.key = digest(session.encode())[:24]
        self.path = self.home / f"{self.key}.json"

    @contextmanager
    def lock(self) -> Iterator[None]:
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
            state["sync"] = sync(self.root)
            self.ensure_target(state)
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
                    state["sync"] = self.sync_upstream(state)
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
        if operation not in {"prepare", "start", "report", "resolve"}:
            raise Blocked("Unknown independent review operation.")
        state = self.load()
        self.identify_author(state)
        self.ensure_target(state)
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
            result = function(self.root, state, payload) if operation in {"report", "resolve"} else function(self.root, state)
        except engine.ReviewError as exc:
            raise Blocked(str(exc)) from exc
        if operation != "prepare":
            state.update(review=None, finished=None)
            self.save(state)
            self.log("independent_review_" + operation)
        return result

    def identify_author(self, state: dict[str, Any]) -> None:
        # Session IDs and reviewer IDs use the same declared representation.
        # Upgrade earlier, not-yet-reviewed contracts without touching a ledger.
        if not state.get("review_gate") and state.get("author") in {None, self.key}:
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
            errors = validate_blob(self.root, p, (self.root / p).read_bytes())
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

    def guard_patch(self, payload: dict[str, Any], cwd: Path) -> None:
        state = self.load()
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

    def publish(self) -> dict[str, Any]:
        state = self.load()
        if state.get("publication_blocker"):
            raise Blocked(state["publication_blocker"])
        info = self.sync_upstream(state)
        local = git(self.root, "rev-parse", "HEAD")
        remote_sha = git(self.root, "rev-parse", "@{upstream}")
        outgoing_gate(self.root, local, remote_sha)
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
        staged_gate(self.root, paths if preserve_index else None)
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

    def stop(self) -> dict[str, Any]:
        state = self.load()
        try:
            self.ensure_target(state)
            self.reviewed(state)
            if not state.get("finished") or state["finished"]["head"] != git(self.root, "rev-parse", "HEAD"):
                raise Blocked("Run workflow.py finish to verify commits and the remote branch.")
            self.checked_scope(state)
            return {}
        except Blocked as exc:
            state["stop_attempts"] += 1
            self.save(state)
            self.log("stop_incomplete", reason=str(exc))
            if state["stop_attempts"] > 2:
                return {"continue": False, "stopReason": f"Constellation task incomplete: {exc}",
                        "systemMessage": f"Constellation: INCOMPLETE. {exc}"}
            return {"decision": "block", "reason": f"[CONSTELLATION-CONTINUE:{self.key}] {exc} Follow .codex/README.md. Report any real blocker; never claim completion without evidence."}


def workspace_hook(workflow: Workflow, event: str, payload: dict[str, Any], cwd: Path) -> dict[str, Any] | None:
    """Dispatch before taking a repository lock; the coordinator owns lock order."""
    manifest = workflow.home / f"workspace-{workflow.key}.json"
    if not manifest.exists() and not manifest.is_symlink():
        return None
    if manifest.is_symlink() or not manifest.is_file():
        raise Blocked("Workspace lifecycle manifest must be a regular local file.")
    from workspace import Workspace

    workspace = Workspace(workflow.root, payload.get("session_id", "manual"))
    if event == "pre-tool":
        workspace.guard_patch(payload, cwd)
        return {}
    if event == "stop":
        return workspace.stop()
    with workspace.lock():
        state = workspace.load()
        continuation = str(payload.get("prompt", "")).startswith(f"[CONSTELLATION-CONTINUE:{workflow.key}]")
        if state.get("finished") and not continuation:
            # A new task may select different repositories. Preserve the prior
            # workspace contract, then let the ordinary prompt lifecycle begin.
            history = workflow.home / "history"
            history.mkdir(exist_ok=True, mode=0o700)
            old = manifest.read_bytes()
            (history / f"workspace-{workflow.key}-{digest(old)[:16]}.json").write_bytes(old)
            manifest.unlink()
            return None
        context = (f"Constellation workspace lifecycle active. Use --session {workspace.session!r}. "
                   "Read .codex/WORKSPACE.md. The unfinished workspace contract and its repository ownership were preserved. "
                   "Incorporate corrections with workspace.py plan; use its check, review, commit and finish commands for all participating repositories. "
                   "No new hub task or upstream synchronization was started by this prompt. "
                   "Do not inspect or manage worktree counts. Prompt/transcript content is never logged.")
        return {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": context}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--session", default=os.environ.get("CODEX_THREAD_ID", "manual"))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("begin").add_argument("--turn", default="manual")
    sub.add_parser("plan")
    sub.add_parser("review")
    for name in ("review-context", "review-start", "review-report", "review-resolve"):
        command = sub.add_parser(name)
        if name == "review-start":
            command.add_argument("--risk", choices=("quick", "standard", "deep"))
    sub.add_parser("status")
    sub.add_parser("finish")
    sub.add_parser("recover").add_argument("expected_head")
    check = sub.add_parser("check")
    check.add_argument("--timeout", type=int, default=300)
    check.add_argument("argv", nargs=argparse.REMAINDER)
    commit = sub.add_parser("commit")
    commit.add_argument("-m", "--message", required=True)
    commit.add_argument("--preserve-index", action="store_true")
    commit.add_argument("paths", nargs="+")
    sub.add_parser("hook").add_argument("event", choices=["prompt", "pre-tool", "stop"])
    sub.add_parser("git-hook").add_argument("event", choices=["pre-commit", "post-commit", "pre-push"])
    args = parser.parse_args()
    payload = json.load(sys.stdin) if args.command in {"plan", "review", "hook", "review-report", "review-resolve"} else {}
    cwd = Path(payload.get("cwd", args.root)).absolute()
    root = Path(git(cwd, "rev-parse", "--show-toplevel"))
    if args.command == "hook":
        # Parent configuration can be inherited by an independent child repo.
        # Only this script's own repository may receive its lifecycle actions.
        if root.resolve() != Path(__file__).resolve().parents[1]:
            print("{}")
            return 0
        marker = root / ".codex/profile.json"
        if marker.is_symlink() or not marker.is_file():
            raise Blocked("Native profile marker must be a regular local file.")
        profile = json.loads(marker.read_text())
        if not isinstance(profile, dict) or profile.get("mode") != "native":
            raise Blocked("Native profile marker must declare mode native.")
    workflow = Workflow(root, payload.get("session_id", args.session))
    if args.command == "hook":
        result = workspace_hook(workflow, args.event, {**payload, "session_id": payload.get("session_id", args.session)}, cwd)
        if result is not None:
            print(json.dumps(result, ensure_ascii=False))
            return 0
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
                payload = {"risk": args.risk}
            result = workflow.review_operation("prepare" if operation == "context" else operation, payload)
        elif args.command == "status":
            result = workflow.load()
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
                staged_gate(root)
                workflow.log("git_commit_preflight")
            elif args.event == "post-commit":
                workflow.log("git_committed", commit=git(root, "rev-parse", "HEAD"))
            else:
                for line in sys.stdin:
                    _, local, _, remote_sha = line.split()
                    outgoing_gate(root, local, remote_sha)
                workflow.log("git_push_preflight")
            result = {}
        elif args.event == "prompt":
            marker = f"[CONSTELLATION-CONTINUE:{workflow.key}]"
            if str(payload.get("prompt", "")).startswith(marker) and workflow.path.exists():
                state = workflow.load()
            elif workflow.path.exists() and workflow.load().get("requirements") and not workflow.load().get("finished"):
                # A status question or steered requirement must not silently
                # erase the unfinished objective and its evidence.
                state = workflow.load()
                state.update(turn=str(payload.get("turn_id", "unknown")), review=None, finished=None)
                try:
                    state["sync"] = workflow.sync_upstream(state)
                    state.pop("sync_error", None)
                except (Blocked, subprocess.TimeoutExpired) as exc:
                    state["sync_error"] = str(exc)
                workflow.save(state)
                workflow.log("steered_prompt", turn=state["turn"])
            else:
                state = workflow.begin(str(payload.get("turn_id", "unknown")))
            context = (f"Constellation lifecycle active. Use --session {payload.get('session_id', args.session)!r}. "
                       "Read .codex/README.md; declare requirements with plan, execute, review each requirement, commit only declared files and finish (push + remote verification). "
                       "Do not inspect or manage worktree counts. Prompt/transcript content is never logged. ")
            if state["requirements"]:
                context += "An unfinished contract was preserved; incorporate the new message. Use begin only if the user explicitly replaces or cancels that objective. "
            context += f"SYNC BLOCKER: {state['sync_error']} Read-only work may continue." if state.get("sync_error") else "Upstream checked."
            result = {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": context}}
        elif args.event == "stop":
            result = workflow.stop() if workflow.path.exists() else {
                "continue": False, "systemMessage": "Constellation: INCOMPLETE. No task contract; check that UserPromptSubmit is trusted."}
        else:
            workflow.guard_patch(payload, cwd)
            result = {}
    print(json.dumps(result, ensure_ascii=False))
    return 2 if args.command == "begin" and result.get("sync_error") else 0


if __name__ == "__main__":
    # workspace imports this runtime; keep one Blocked class when this file is
    # launched as a script so coordinator rejections reach the normal handler.
    sys.modules["workflow"] = sys.modules[__name__]
    try:
        raise SystemExit(main())
    except (Blocked, subprocess.TimeoutExpired, OSError, ValueError) as exc:
        print(f"Constellation: {exc}", file=sys.stderr)
        raise SystemExit(2)

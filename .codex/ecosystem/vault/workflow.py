#!/usr/bin/env python3
"""OmarOS lifecycle: explicit scope, evidence, safe Git, and bounded closure.

Operational state lives in Git's private directory. No prompt or transcript is
stored. Hooks enforce observable conditions, not the truth of a semantic review.
"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None

from . import progress_journal, review_gate
from ..runtime import progress
from .. import platform_support as ps
from ..runtime.workflow import (Blocked, Workflow as GitWorkflow, digest, now,
                                prepare_stop, incomplete_stop, _read_private_text, _write_private,
                                frozen_transport, publish_frozen, remote_tip, verify_outgoing_commits, validate_changed_scope)


def review_engine():
    return review_gate


def progress_engine():
    return progress


def journal_engine():
    return progress_journal


def run(root: Path, *args: str, timeout: int = 25, extra_env: dict[str, str] | None = None) -> str:
    operation = "command"
    if args and args[0] == "git":
        operation = "git command"
        position = 1
        while position < len(args) and args[position] in {"--no-replace-objects", "--literal-pathspecs"}:
            position += 1
        # Only fixed command names may enter diagnostics; option values, paths,
        # messages and captured Git output can contain private information.
        if position < len(args) and args[position] in {
                "add", "cat-file", "check-ignore", "commit", "config", "diff", "diff-tree", "fetch",
                "ls-files", "ls-remote", "ls-tree", "merge", "merge-base", "push", "remote",
                "rev-list", "rev-parse", "status", "symbolic-ref"}:
            operation = f"git {args[position]}"
    try:
        result = subprocess.run(args, cwd=root, capture_output=True, text=True,
                                timeout=timeout, env={**os.environ, **(extra_env or {}), "GIT_TERMINAL_PROMPT": "0"})
    except subprocess.TimeoutExpired:
        raise Blocked(f"{operation} timed out after {timeout}s.") from None
    if result.returncode:
        output_hash = digest((result.stdout + result.stderr).encode())
        raise Blocked(f"{operation} failed ({result.returncode}); output SHA256 {output_hash}. Retry the operation directly for diagnostics.")
    return result.stdout.rstrip("\n")


def git(root: Path, *args: str, timeout: int = 25, extra_env: dict[str, str] | None = None,
        config: tuple[str, ...] = ()) -> str:
    options = [item for entry in config for item in ("-c", entry)]
    return run(root, "git", "--no-replace-objects", *options, *args, timeout=timeout, extra_env=extra_env)


def private_path(path: str) -> bool:
    """Reject private runtime data even when it was accidentally tracked before."""
    p = path.lower()
    parts = Path(p).parts
    # Imported Markdown can document a daemon; its runtime logs remain private.
    managed_daemon_document = (
        len(parts) >= 5 and parts[1] == "research_repositories"
        and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", parts[2]) is not None
        and parts[3] == "files"
        and not any("_daemon." in part for part in parts[:-1])
        and ((parts[0] == "11_documents_and_reports" and parts[-1].endswith("_daemon.md"))
             or (parts[0] == "90_attachments" and parts[-1].endswith("_daemon.md.source")))
    )
    return (any(part in {".git", ".ssh", "secrets",
                         "turn_states", ".sync_state", ".codex_notuse",
                         "conversations", "archived_sessions", "rollouts"} for part in parts)
            or p == "06_knowledge_base/mathematics/finance/engie/private"
            or p.startswith("06_knowledge_base/mathematics/finance/engie/private/")
            or "_conversations/" in p or "conversation_archive" in p
            or ("_daemon." in p and not managed_daemon_document) or p.startswith("docs/sk_runs/")
            or p.startswith((".claude/cache/", ".claude/run/", ".claude/logs/", ".codex/cache/",
                             ".codex/sessions/", ".codex/log/", ".codex/state/"))
            or p.startswith(("09_data_sources/email_exports/by_message/",
                             "09_data_sources/email_exports/snapshots/", "09_data_sources/email_exports/backfill/",
                             "11_documents_and_reports/email/"))
            or p == "09_data_sources/email_exports/index.json"
            or Path(p).name.startswith("rollout-")
            or Path(p).name in {"auth.json", "credentials.json", "secrets.json", ".netrc",
                                  "id_rsa", "id_ed25519", ".ds_store"}
            or any(part == ".env" or part.startswith(".env.") for part in parts)
            or p.endswith((".pem", ".key", ".p12", ".pfx", ".jsonl")))


def safe_path(root: Path, name: str) -> str:
    if not isinstance(name, str):
        raise Blocked("Artifact paths must be text.")
    path = Path(name)
    if path.as_posix() != name or path.is_absolute() or ".." in path.parts or not path.parts:
        raise Blocked(f"Expected a repository-relative file: {name}")
    if private_path(name) or not (root / path).resolve().is_relative_to(root.resolve()):
        raise Blocked(f"Private or external path: {name}")
    if (root / path).is_dir() or any((root / part).is_symlink() for part in (path, *path.parents)):
        raise Blocked(f"Declare individual regular files: {name}")
    if git_owner(root / path) != root.resolve():
        raise Blocked(f"Path belongs to a nested repository: {name}")
    return path.as_posix()


def changed(root: Path) -> set[str]:
    tracked = git(root, "diff", "HEAD", "--name-only", "-z").split("\0")
    untracked = git(root, "ls-files", "--others", "--exclude-standard", "-z").split("\0")
    return set(tracked + untracked) - {""}


def snapshot(root: Path, paths: list[str]) -> dict[str, str | None]:
    result = {}
    for p in sorted(paths):
        safe_path(root, p)
        result[p] = digest((root / p).read_bytes()) if (root / p).is_file() else None
    return result


def snapshot_modes(root: Path, paths: list[str]) -> dict[str, str | None]:
    result = {}
    for name in sorted(paths):
        safe_path(root, name)
        target = root / name
        result[name] = ("100755" if target.stat().st_mode & 0o100 else "100644") if target.is_file() else None
    return result


def artifact_snapshot(root: Path, paths: list[str]) -> dict[str, str | None]:
    content, modes = snapshot(root, paths), snapshot_modes(root, paths)
    return {name: modes[name] + ":" + value if value is not None else None for name, value in content.items()}


def rename_hashes(root: Path, state: dict[str, Any], paths: list[str],
                  renames: Any) -> dict[str, str]:
    """Pin archival renames to regular source blobs present when the task began."""
    if not isinstance(renames, dict) or not all(
            isinstance(old, str) and isinstance(new, str) for old, new in renames.items()):
        raise Blocked("Renames must map exact source paths to exact destination paths.")
    if (len(set(renames.values())) != len(renames)
            or set(renames) & set(renames.values())):
        raise Blocked("Rename endpoints must be distinct; chains and cycles are not supported.")
    result = {}
    for old, new in renames.items():
        safe_path(root, old)
        safe_path(root, new)
        if not {old, new} <= set(paths):
            raise Blocked("Declare both endpoints of every rename in paths.")
        if {old, new} & set(state.get("baseline_dirty", [])):
            raise Blocked("Archival rename endpoints had pre-existing changes; preserve and resolve them explicitly.")
        if git(root, "--literal-pathspecs", "ls-tree", "-z", state["initial_head"], "--", new):
            raise Blocked(f"Archival rename destination already existed when the task began: {new}")
        ignored = subprocess.run(["git", "check-ignore", "--no-index", "--quiet", "--", new],
                                 cwd=root, capture_output=True)
        if ignored.returncode == 0:
            raise Blocked(f"Archival rename destination is ignored: {new}")
        if ignored.returncode != 1:
            raise Blocked("Cannot verify ignore rules for the archival destination.")
        records = [item for item in git(root, "--literal-pathspecs", "ls-tree", "-z",
                   state["initial_head"], "--", old).split("\0") if item]
        if len(records) != 1:
            raise Blocked(f"Rename source was not tracked when the task began: {old}")
        metadata, name = records[0].split("\t", 1)
        mode, kind, oid = metadata.split()
        if name != old or kind != "blob" or mode not in {"100644", "100755"}:
            raise Blocked(f"Rename source must be a tracked regular file: {old}")
        result[old] = digest(subprocess.check_output(["git", "--no-replace-objects", "cat-file", "blob", oid], cwd=root))
        if (root / old).is_file() and digest((root / old).read_bytes()) != result[old]:
            raise Blocked(f"Archival rename source changed since the task began: {old}")
    return result


def validate_renames(root: Path, state: dict[str, Any], current: dict[str, str | None]) -> None:
    """A reviewed absence is valid only with its byte-identical declared destination."""
    for old, new in state.get("renames", {}).items():
        expected = state.get("rename_hashes", {}).get(old)
        if os.path.lexists(root / old) or current.get(old) is not None:
            raise Blocked(f"Declared rename source must be absent: {old}")
        if expected is None or current.get(new) != expected:
            raise Blocked(f"Declared rename destination must preserve source bytes: {old} -> {new}")


def deletion_paths(root: Path, state: dict[str, Any], paths: list[str],
                   deletions: Any, renames: dict[str, str]) -> list[str]:
    """Authorize exact deletions against the task's original tracked files."""
    if (not isinstance(deletions, list) or not all(isinstance(p, str) for p in deletions)
            or len(set(deletions)) != len(deletions)):
        raise Blocked("Deletions must be a unique list of exact file paths.")
    if not set(deletions) <= set(paths):
        raise Blocked("Declare every deletion in paths.")
    if set(deletions) & set(renames.values()):
        raise Blocked("A rename destination cannot also be a declared deletion.")
    for name in deletions:
        safe_path(root, name)
        records = [item for item in git(root, "--literal-pathspecs", "ls-tree", "-z",
                   state["initial_head"], "--", name).split("\0") if item]
        if len(records) != 1:
            raise Blocked(f"Deletion source was not tracked when the task began: {name}")
        metadata, tracked_name = records[0].split("\t", 1)
        mode, kind, _ = metadata.split()
        if tracked_name != name or kind != "blob" or mode not in {"100644", "100755"}:
            raise Blocked(f"Deletion source must be a tracked regular file: {name}")
    return sorted(set(deletions) | set(renames))


def validate_deletions(root: Path, state: dict[str, Any], current: dict[str, str | None]) -> None:
    for name in set(state.get("deletions", [])) | set(state.get("renames", {})):
        if os.path.lexists(root / name) or current.get(name) is not None:
            raise Blocked(f"Declared deletion must be absent: {name}")


def git_owner(target: Path) -> Path:
    """Resolve a file's actual repository, including files not created yet."""
    parent = target.parent
    while not parent.is_dir():
        if parent.parent == parent:
            raise Blocked("No existing directory for the delegated file.")
        parent = parent.parent
    return Path(git(parent, "rev-parse", "--show-toplevel")).resolve()


def delegate_target(root: Path) -> dict[str, str]:
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


def delegate_state(parent: Path, entry: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    """Read an explicitly declared lifecycle contract; never execute foreign code."""
    if not isinstance(entry, dict) or set(entry) != {"root", "namespace", "session"}:
        raise Blocked("Delegates require exactly root, namespace and session.")
    if not all(isinstance(entry[key], str) and entry[key].strip() for key in entry):
        raise Blocked("Delegate root, namespace and session must be nonempty strings.")
    root = Path(entry["root"])
    if (not root.is_absolute() or root.resolve() != root or root == parent
            or root.is_relative_to(parent) or parent.is_relative_to(root)):
        raise Blocked("Delegate must name a canonical, independent Git root.")
    if Path(git(root, "rev-parse", "--show-toplevel")).resolve() != root:
        raise Blocked("Delegate must name the actual Git root.")
    if entry["namespace"] not in {"constellation", "omaros"}:
        raise Blocked("Unsupported delegate lifecycle namespace.")
    if not isinstance(entry["session"], str) or not entry["session"].strip():
        raise Blocked("Delegate requires an explicit session.")
    directory = Path(git(root, "rev-parse", "--path-format=absolute", "--git-path", entry["namespace"]))
    path = directory / (digest(entry["session"].encode())[:24] + ".json")
    if directory.resolve() != directory or path.is_symlink() or not path.is_file():
        raise Blocked("Delegate has no regular lifecycle state; begin and plan there first.")
    state = json.loads(path.read_text())
    if (not isinstance(state, dict) or not isinstance(state.get("requirements"), list)
            or not state["requirements"]
            or not all(isinstance(item, str) and item.strip() for item in state["requirements"])
            or state.get("sync_error")):
        raise Blocked("Delegate needs a valid plan and successful upstream check.")
    paths, deletions = state.get("paths"), state.get("deletions", [])
    if (not isinstance(paths, list) or not all(isinstance(item, str) for item in paths)
            or len(set(paths)) != len(paths) or not isinstance(deletions, list)
            or not all(isinstance(item, str) for item in deletions)
            or not set(deletions) <= set(paths)):
        raise Blocked("Delegate must declare exact file paths and deletions.")
    current = delegate_target(root)
    previous = state.get("target") or state.get("sync") or {}
    if not isinstance(previous, dict) or any(previous.get(key) != value for key, value in current.items()
                                            if key != "url_sha256" or key in previous):
        raise Blocked("Delegate publication target changed; destination changed since its upstream check.")
    return root, state


def check_delegate_target(root: Path, targets: dict[str, Any]) -> None:
    if targets.get(str(root)) != delegate_target(root):
        raise Blocked("Delegate publication target changed or was not pinned; renew the parent plan explicitly.")


def delegated_path(root: Path, state: dict[str, Any], name: str, action: str) -> Path:
    path = Path(name)
    if path.is_absolute() or ".." in path.parts or not path.parts or private_path(name):
        raise Blocked("Invalid or private delegated path.")
    if name not in state.get("paths", []):
        raise Blocked(f"Undeclared delegated patch path: {name}")
    target = root / path
    deletion = name in state.get("deletions", [])
    if deletion and action != "Delete File":
        raise Blocked(f"Declared deletion only authorizes Delete File: {name}")
    parts = path.parents if deletion else (path, *path.parents)
    if any((root / part).is_symlink() for part in parts):
        raise Blocked("Delegated paths cannot traverse symlinks.")
    if (target.is_dir() and not (deletion and target.is_symlink())) or git_owner(target) != root:
        raise Blocked("Delegated path belongs to another repository or is not a file.")
    return target


def delegate_artifact_claim(value: Any) -> tuple[str | None, str | None]:
    """Decode recorded bytes and only the permissions actually claimed by review."""
    if value is None:
        return None, None
    match = re.fullmatch(r"(?:(100644|100755|symlink):)?([0-9a-f]{64})", value) if isinstance(value, str) else None
    if match is None:
        raise Blocked("Delegate review has an invalid artifact fingerprint.")
    prefix, sha = match.groups()
    return sha, "120000" if prefix == "symlink" else prefix


def validate_delegate_artifacts(root: Path, state: dict[str, Any], head: str,
                                current: dict[str, str | None], modes: dict[str, str | None]) -> None:
    """Validate both live files and pinned Git objects without importing child code.

    OmarOS records raw SHA plus an optional modes map; current Constellation
    embeds mode in each SHA. Older byte-only records retain their byte-only
    guarantee. Neither namespace gains permission evidence that it never stored.
    """
    review = state.get("review")
    expected = review.get("snapshot") if isinstance(review, dict) else None
    paths = state["paths"]
    if not isinstance(expected, dict) or set(expected) != set(paths):
        raise Blocked(f"Delegate review is stale: {root}")
    claimed_modes = review.get("modes")
    if "modes" in review and (not isinstance(claimed_modes, dict) or set(claimed_modes) != set(paths)):
        raise Blocked(f"Delegate review has invalid permission evidence: {root}")
    durable = stored_snapshot(root, paths, head) if paths else {}
    deletions = set(state.get("deletions", [])) | set(state.get("renames", {}))
    for name in paths:
        if name in deletions and expected[name] is not None:
            raise Blocked(f"Delegate review has an incomplete declared deletion: {root}")
        expected_sha, embedded_mode = delegate_artifact_claim(expected[name])
        claimed_mode = claimed_modes[name] if claimed_modes is not None else embedded_mode
        if (claimed_mode is not None and not isinstance(claimed_mode, str)):
            raise Blocked(f"Delegate review has invalid permission evidence: {root}")
        if (claimed_mode not in {None, "100644", "100755", "120000"}
                or embedded_mode is not None and claimed_mode != embedded_mode
                or expected_sha is None and claimed_mode is not None
                or claimed_modes is not None and expected_sha is not None and claimed_mode is None):
            raise Blocked(f"Delegate review has conflicting permission evidence: {root}")
        current_sha, _ = delegate_artifact_claim(current[name])
        regular = expected_sha is not None and embedded_mode != "120000" and claimed_mode != "120000"
        if (expected_sha != current_sha or claimed_mode is not None and claimed_mode != modes[name]
                or regular and modes[name] not in {"100644", "100755"}):
            raise Blocked(f"Delegate review is stale: {root}")
        durable_sha, durable_mode = delegate_artifact_claim(durable[name])
        if (expected_sha != durable_sha or claimed_mode is not None and claimed_mode != durable_mode
                or regular and durable_mode not in {"100644", "100755"}):
            raise Blocked(f"Delegate durable HEAD differs from its reviewed artifacts or permissions: {root}")
    validate_deletions(root, state, current)


def completed_delegates(parent: Path, entries: list[dict[str, Any]], *, remote: bool = False,
                        targets: dict[str, Any] | None = None) -> dict[str, str]:
    """Require each independent contract's reviewed, committed, published version."""
    result = {}
    for entry in entries:
        root, state = delegate_state(parent, entry)
        check_delegate_target(root, targets or {})
        head = git(root, "rev-parse", "HEAD")
        publication = state.get("publication") or {}
        if (not isinstance(state.get("finished"), dict) or not isinstance(publication, dict)
                or state["finished"].get("local_only") is True
                or state["finished"].get("head") != head or publication.get("head") != head):
            raise Blocked(f"Delegate must finish its own lifecycle: {root}")
        current = {}
        for name in state.get("paths", []):
            action = "Delete File" if name in state.get("deletions", []) else "Update File"
            target = delegated_path(root, state, name, action)
            current[name] = ("symlink:" + digest(os.readlink(target).encode()) if target.is_symlink()
                             else digest(target.read_bytes()) if target.is_file() else None)
        child_modes = {name: ("120000" if (root / name).is_symlink() else
                             "100755" if (root / name).is_file() and (root / name).stat().st_mode & 0o100 else
                             "100644" if (root / name).is_file() else None) for name in state["paths"]}
        validate_delegate_artifacts(root, state, head, current, child_modes)
        dirty = changed(root)
        if set(state.get("paths", [])) & dirty:
            raise Blocked(f"Delegate has uncommitted task files: {root}")
        unexpected = dirty - set(state.get("baseline_dirty", [])) - set(state["paths"])
        unknown = {name for name in unexpected if not private_path(name) and not state.get("unrelated", {}).get(name)}
        if unknown:
            raise Blocked(f"Delegate has new undeclared files requiring scope review: {root}")
        branch = git(root, "symbolic-ref", "--short", "HEAD")
        for key, config_key in (("remote", "remote"), ("ref", "merge")):
            if publication.get(key) != git(root, "config", "--get", f"branch.{branch}.{config_key}"):
                raise Blocked(f"Delegate publication target changed: {root}")
        if remote:
            approved = (targets or {}).get(str(root))
            if not approved:
                raise Blocked("Remote delegate verification requires its parent's frozen target.")
            with frozen_transport(root, approved, git) as transport:
                actual = remote_tip(transport, approved)
            if actual != head:
                raise Blocked(f"Delegate remote no longer matches: {root}")
        if git(root, "rev-parse", "HEAD") != head:
            raise Blocked(f"Delegate HEAD changed during completion validation: {root}")
        check_delegate_target(root, targets or {})
        result[str(root)] = digest(json.dumps({"head": head, "paths": current, "publication": publication}, sort_keys=True).encode())
    return result


def sync(root: Path, expected: dict[str, str] | None = None) -> dict[str, Any]:
    target = delegate_target(root)
    if expected is not None and expected != target:
        raise Blocked("The upstream destination changed before synchronization.")
    with frozen_transport(root, target, git) as transport:
        transport("fetch", "--upload-pack=git-upload-pack", "--prune", "--no-recurse-submodules", "--", target["remote"])
    ahead, behind = map(int, git(root, "rev-list", "--left-right", "--count", "HEAD...@{upstream}").split())
    if behind:
        if ahead:
            raise Blocked("Local and remote histories diverged. Reconcile explicitly; no automatic rebase.")
        if changed(root):
            raise Blocked("Remote has new commits and the working tree is dirty. Preserve local work before pulling.")
        git(root, "merge", "--ff-only", "@{upstream}")
    if delegate_target(root) != target:
        raise Blocked("The upstream destination changed during synchronization. Restore the task destination before continuing.")
    return {"checked_at": now(), **target,
            "head": git(root, "rev-parse", "HEAD"), "ahead": ahead, "behind": 0}


def validate_blob(root: Path, path: str, blob: bytes) -> list[str]:
    errors = []
    if private_path(path):
        return [f"Private path cannot be committed or pushed: {path}"]
    if path.startswith("90_Attachments/") and len(blob) > 10 * 1024 * 1024:
        errors.append(f"Attachment exceeds 10 MiB: {path}")
    if not re.match(r"^\d\d_[^/]+/.*\.md$", path):
        return errors
    if yaml is None:
        raise Blocked("OmarOS note validation requires PyYAML in the Constellation interpreter.")
    try:
        text = blob.decode("utf-8")
        if not text.startswith("---\n"):
            raise ValueError("missing frontmatter")
        closing = re.search(r"(?m)^---[ \t]*\r?$", text[4:])
        if closing is None:
            raise ValueError("missing frontmatter closing delimiter")
        fm = yaml.safe_load(text[4:4 + closing.start()])
        if not isinstance(fm, dict):
            raise ValueError("frontmatter is not a mapping")
        for key in ("title", "note_type", "domain", "status", "created", "updated", "author"):
            if not fm.get(key):
                errors.append(f"{path}: missing {key}")
        enums_path = root / "19_Metadata_and_Schema/Status_Enums/enums.json"
        if enums_path.exists():
            enums = json.loads(enums_path.read_text())
            for key in ("status", "priority", "confidence"):
                if key in fm and fm[key] not in enums[key]:
                    errors.append(f"{path}: invalid {key}")
        types_path = root / "19_Metadata_and_Schema/Note_Types/note_types.json"
        if types_path.exists() and fm.get("note_type") not in json.loads(types_path.read_text())["note_types"]:
            errors.append(f"{path}: invalid note_type")
        for key in ("created", "updated"):
            if key in fm and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(fm[key])):
                errors.append(f"{path}: {key} must be an ISO date")
        if fm.get("domain") != path.split("/")[0]:
            errors.append(f"{path}: domain does not match placement")
        if path.startswith("06_Knowledge_Base/"):
            components = Path(path).parts
            subdomain_moc = (
                len(components) == 3 and fm.get("note_type") == "moc"
                and fm.get("domain") == "06_Knowledge_Base"
                and fm.get("subdomain") == components[1]
            )
            if len(components) < 4 and not subdomain_moc:
                errors.append(f"{path}: knowledge needs subdomain/area/file")
        if path.startswith(("04_Research/", "06_Knowledge_Base/")) and not isinstance(fm.get("latex_pending"), bool):
            errors.append(f"{path}: latex_pending must be boolean")
    except (ValueError, UnicodeError, yaml.YAMLError) as exc:
        errors.append(f"{path}: {exc}")
    return errors


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
    staged = list(filter(None, git(root, "--literal-pathspecs", "diff", "--cached", "--no-renames",
                                  "--name-only", "--diff-filter=ACMRT", "-z", *scope).split("\0")))
    private = [name for name in staged if private_path(name)]
    if private:
        raise Blocked("\n".join(f"Private path cannot be committed or pushed: {name}" for name in private))
    git(root, "--literal-pathspecs", "diff", "--cached", "--check", *scope)
    errors: list[str] = []
    for name in staged:
        entries = list(filter(None, git(root, "--literal-pathspecs", "ls-files", "--stage", "-z", "--", name).split("\0")))
        if len(entries) != 1:
            raise Blocked("The selected index must contain one resolved file entry per path.")
        metadata, actual_name = entries[0].split("\t", 1)
        _, object_id, stage = metadata.split()
        if actual_name != name or stage != "0":
            raise Blocked("The selected index contains an ambiguous path or unresolved merge stages.")
        # Revision syntax such as :0:.env is not a literal index filename.
        # Resolve the exact path to its OID before opening a blob.
        blob = subprocess.check_output(["git", "--no-replace-objects", "cat-file", "blob", object_id], cwd=root)
        errors.extend(validate_blob(root, name, blob))
    if errors:
        raise Blocked("\n".join(errors))


def notes_monitor_index_gate(root: Path) -> None:
    """Check the real index while ``commit --only`` holds its native lock.

    The monitor keeps its own exclusive lock throughout this callback. Git's
    hook index is temporary; inspecting it would miss staged work in the real
    index that ``--only`` is about to replace for the monitor's three paths.
    """
    snapshot_id = os.environ.get("OMAROS_MONITOR_SNAPSHOT")
    if snapshot_id is None:
        return
    if re.fullmatch(r"[0-9a-f]{64}", snapshot_id) is None:
        raise Blocked("Invalid Notes/Reminders snapshot marker.")
    paths = ("00_Inbox/Apple_Notes_Monitor/notes_history.json",
             "02_Tasks_and_Execution/Monitor/reminders_history.json",
             "17_Dashboards/Tasks/notes_reminders_monitor.md")
    git_directory = Path(git(root, "rev-parse", "--absolute-git-dir"))
    storage = git_directory / "notes-reminders-monitor"
    receipt_path = storage / "commit_attempt.json"

    def regular(path: Path) -> os.stat_result:
        if any(part.is_symlink() for part in (path, *path.parents)):
            raise Blocked("Notes/Reminders Git state cannot traverse symlinks.")
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode):
            raise Blocked("Notes/Reminders Git state requires regular files.")
        return metadata

    def identity(metadata: os.stat_result) -> tuple[int, ...]:
        return (metadata.st_dev, metadata.st_ino, metadata.st_mode, metadata.st_size,
                metadata.st_mtime_ns, metadata.st_ctime_ns)

    def read_receipt() -> tuple[bytes, tuple[int, ...]]:
        metadata = regular(receipt_path)
        if metadata.st_mode & 0o077 or metadata.st_size > 1024 * 1024:
            raise Blocked("Notes/Reminders commit receipt is not private or bounded.")
        descriptor = os.open(receipt_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as stream:
            if identity(os.fstat(stream.fileno())) != identity(metadata):
                raise Blocked("Notes/Reminders commit receipt changed while opening it.")
            payload = stream.read(1024 * 1024 + 1)
            if (len(payload) > 1024 * 1024
                    or identity(os.fstat(stream.fileno())) != identity(metadata)
                    or identity(regular(receipt_path)) != identity(metadata)):
                raise Blocked("Notes/Reminders commit receipt changed while reading it.")
        return payload, identity(metadata)

    try:
        if not storage.is_dir() or storage.stat().st_mode & 0o077:
            raise Blocked("Notes/Reminders commit state requires a private directory.")
        original, original_identity = read_receipt()
        receipt = json.loads(original)
        if (not isinstance(receipt, dict) or type(receipt.get("schema_version")) is not int
                or receipt["schema_version"] != 1 or receipt.get("snapshot_id") != snapshot_id
                or not isinstance(receipt.get("parent"), str)
                or re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", receipt["parent"]) is None
                or not isinstance(receipt.get("branch"), str)
                or not receipt["branch"].startswith("refs/heads/")
                or not isinstance(receipt.get("own_index_sha256"), str)
                or re.fullmatch(r"[0-9a-f]{64}", receipt["own_index_sha256"]) is None
                or ("guarded_snapshot" in receipt and receipt["guarded_snapshot"] != snapshot_id)):
            raise Blocked("Invalid Notes/Reminders commit receipt.")
        if (git(root, "rev-parse", "HEAD") != receipt["parent"]
                or git(root, "symbolic-ref", "--quiet", "HEAD") != receipt["branch"]):
            raise Blocked("Notes/Reminders HEAD or branch changed before commit.")
        real_index = git_directory / "index"
        reservation = git_directory / "index.lock"
        reserved = {path: identity(regular(path)) for path in (real_index, reservation)}
        entries = git(root, "--literal-pathspecs", "ls-files", "--stage", "-v", "-z", "--", *paths,
                      extra_env={"GIT_INDEX_FILE": str(real_index)})
        if digest(entries.encode()) != receipt["own_index_sha256"]:
            raise Blocked("Notes/Reminders paths have concurrent staged work or index flags.")
        if (any(identity(regular(path)) != metadata for path, metadata in reserved.items())
                or git(root, "rev-parse", "HEAD") != receipt["parent"]
                or git(root, "symbolic-ref", "--quiet", "HEAD") != receipt["branch"]):
            raise Blocked("Notes/Reminders Git reservation or HEAD changed during commit guard.")
        if read_receipt() != (original, original_identity):
            raise Blocked("Notes/Reminders commit receipt changed during validation.")
        if receipt.get("guarded_snapshot") != snapshot_id:
            receipt["guarded_snapshot"] = snapshot_id
            journal_engine()._write(receipt_path, (json.dumps(receipt, ensure_ascii=False,
                                                           sort_keys=True, indent=2) + "\n").encode(), 0o600)
    except (OSError, ValueError, UnicodeError) as exc:
        raise Blocked("Invalid or unsafe Notes/Reminders commit state.") from exc


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
        if private_path(name):
            raise Blocked(f"Private path cannot be verified for publication: {name}")
        blob = subprocess.run(["git", "--no-replace-objects", "cat-file", "blob", object_id], cwd=root,
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
                    "-r", "--no-renames", "--diff-filter=ACMRT", "-z", commit).split("\0")
        for p in set(filter(None, paths)):
            if private_path(p):
                errors.append(f"{commit[:10]} includes private data: {p}")
    if errors:
        raise Blocked("\n".join(errors[:30]))


class Workflow(GitWorkflow):
    """Git workflow specialized for vault records, metadata and delegated owners.

    Use the shared Git engine's durable store and locks with the vault's existing
    state namespace, so outstanding contracts remain available after upgrades.
    """
    def __init__(self, root: Path, session: str):
        self.root = root.resolve()
        self.session = session
        self.home = Path(git(root, "rev-parse", "--path-format=absolute", "--git-path", "omaros"))
        ps.secure_mkdir(self.home, parents=True, exist_ok=True, mode=0o700)
        self.key = digest(session.encode())[:24]
        self.path = self.home / f"{self.key}.json"

    def save(self, state: dict[str, Any]) -> None:
        # Upgrade older local records without retaining argument text in newly
        # written operational state. Their byte-only checks stay stale.
        for check in state.get("checks", []):
            if "command" in check:
                check.setdefault("command_sha256", digest(json.dumps(check.pop("command")).encode()))
        super().save(state)

    def progress_show(self) -> dict[str, Any]:
        state = self.load()
        progress = state.get("task_progress")
        if progress is not None:
            progress_engine().validate_progress(progress)
        return {"expected_task_start": state["started"], "task_progress": progress,
                "revision": len(progress["milestones"]) if progress else 0}

    def progress_update(self, payload: dict[str, Any]) -> dict[str, Any]:
        if (not isinstance(payload, dict) or set(payload) - {
                "expected_task_start", "task_uid", "expected_revision", "checkpoint", "source_alias"}):
            raise Blocked("Unsupported progress update fields.")
        state = self.load()
        engine = progress_engine()
        current = state.get("task_progress")
        if not state.get("requirements"):
            raise Blocked("Declare the objective before recording progress.")
        if current is None:
            if (payload.get("expected_task_start") != state["started"]
                    or payload.get("task_uid") is not None
                    or type(payload.get("expected_revision")) is not int
                    or payload["expected_revision"] != 0):
                raise Blocked("Initial progress requires the current task start and expected_revision 0.")
            checkpoint = payload.get("checkpoint")
            snapshot = checkpoint.get("snapshot") if isinstance(checkpoint, dict) else None
            objectives = snapshot.get("objectives") if isinstance(snapshot, dict) else None
            if not isinstance(objectives, list) or not objectives:
                raise Blocked("Initial progress requires explicit curated objectives.")
            default_alias = re.sub(r"[^a-z0-9]+", "-", self.root.name.lower()).strip("-")[:64].rstrip("-") or "project"
            current = engine.create_progress(objectives[0], source_alias=payload.get("source_alias", default_alias))
        else:
            engine.validate_progress(current)
            # An interrupted first response leaves the caller without the UUID.
            # Only the exact first checkpoint and original start can be replayed.
            default_alias = re.sub(r"[^a-z0-9]+", "-", self.root.name.lower()).strip("-")[:64].rstrip("-") or "project"
            initial_replay = (payload.get("task_uid") is None
                              and payload.get("expected_task_start") == state["started"]
                              and type(payload.get("expected_revision")) is int
                              and payload["expected_revision"] == 0
                              and payload.get("source_alias", default_alias) == current["source_alias"]
                              and isinstance(payload.get("checkpoint"), dict)
                              and bool(current["milestones"])
                              and payload["checkpoint"].get("id") == current["milestones"][0]["id"])
            if initial_replay and engine.checkpoint(current, payload["checkpoint"]) == current:
                return {"expected_task_start": state["started"], "task_progress": current,
                        "revision": len(current["milestones"])}
            if (payload.get("task_uid") != current["task_uid"] or "source_alias" in payload
                    or type(payload.get("expected_revision")) is not int
                    or not 0 <= payload["expected_revision"] <= len(current["milestones"])):
                raise Blocked("Progress identity or revision is stale; inspect progress-show before retrying.")
            repeated = engine.checkpoint(current, payload.get("checkpoint"))
            if repeated == current:
                return {"expected_task_start": state["started"], "task_progress": current,
                        "revision": len(current["milestones"])}
            if payload["expected_revision"] != len(current["milestones"]):
                raise Blocked("Progress identity or revision is stale; inspect progress-show before retrying.")
        updated = repeated if state.get("task_progress") is not None else engine.checkpoint(current, payload.get("checkpoint"))
        if updated != state.get("task_progress"):
            state["task_progress"] = updated
            self.save(state)
        return {"expected_task_start": state["started"], "task_progress": updated,
                "revision": len(updated["milestones"])}

    def progress_export(self, task_uid: str, policy_path: Path) -> dict[str, Any]:
        state = self.load()
        current = state.get("task_progress")
        if not current or current.get("task_uid") != task_uid:
            raise Blocked("Progress export requires the current task identity.")
        finished = state.get("finished")
        workflow_finished = False
        if finished and finished.get("head") == git(self.root, "rev-parse", "HEAD"):
            try:
                query = not state["paths"] and not state.get("delegates")
                remote_query = query and finished.get("readonly") is True and finished.get("local_only") is False
                if not query or remote_query:
                    self.ensure_target(state)
                self.reviewed(state)
                if query and finished.get("local_only") is not True:
                    publication = state.get("publication") or {}
                    target = state.get("target") or {}
                    if (not remote_query or publication.get("head") != finished["head"]
                            or any(publication.get(key) != target.get(key) for key in ("remote", "ref"))):
                        raise Blocked("Progress cannot attest an unverified query closure.")
                self.checked_scope(state)
                self.durable_reviewed(state)
                workflow_finished = True
            except (Blocked, ValueError):
                pass
        return progress_engine().export_envelope(
            current, source_root=self.root, policy=journal_engine().read_policy(policy_path),
            workflow_finished=workflow_finished)

    def progress_ack(self, payload: dict[str, Any], policy_path: Path) -> dict[str, Any]:
        state = self.load()
        current = state.get("task_progress")
        if (not isinstance(payload, dict) or set(payload) != {"task_uid", "expected_revision", "receipt"}
                or not current or payload.get("task_uid") != current.get("task_uid")
                or type(payload.get("expected_revision")) is not int
                or payload["expected_revision"] != len(current["milestones"])):
            raise Blocked("Progress acknowledgment requires the current task identity and revision.")
        envelope = self.progress_export(payload["task_uid"], policy_path)
        updated = progress_engine().acknowledge(current, envelope=envelope, receipt=payload.get("receipt"))
        if updated != current:
            state["task_progress"] = updated
            self.save(state)
        return updated

    def journal_import(self, payload: dict[str, Any], source_root: Path, policy_path: Path) -> dict[str, Any]:
        return journal_engine().receive(
            self, payload, source_root=source_root, policy=journal_engine().read_policy(policy_path),
            progress=progress_engine(), validate_path=safe_path, validate_blob=validate_blob)

    def begin(self, turn: str, *, prior_hook_turns: list[str] | None = None) -> dict[str, Any]:
        if self.path.exists():
            if self.load().get("publication_deferred"):
                raise Blocked("Publication is deferred; explicitly resume it with publish --resume-deferred before replacing this contract.")
            history = self.home / "history"
            ps.secure_mkdir(history, exist_ok=True, mode=0o700)
            old = _read_private_text(self.path).encode("utf-8")
            _write_private(history / f"{self.key}-{digest(old)[:16]}.json", old)
        state: dict[str, Any] = {"turn": turn, "started": now(), "initial_head": git(self.root, "rev-parse", "HEAD"),
                                 "baseline_dirty": sorted(changed(self.root)), "requirements": [],
                                 "paths": [], "checks": [], "commits": [], "stop_attempts": 0,
                                 "author": self.session}
        if prior_hook_turns is not None:
            state["hook_turn_hashes"] = prior_hook_turns
        try:
            state["target"] = delegate_target(self.root)
            state["sync"] = self.sync_upstream(state)
        except (Blocked, subprocess.TimeoutExpired) as exc:
            state["sync_error"] = str(exc)
        self.save(state)
        self.log("begin", turn=turn, sync_ok="sync" in state)
        return state

    def ensure_target(self, state: dict[str, Any]) -> dict[str, str]:
        target = delegate_target(self.root)
        if not state.get("target"):
            raise Blocked("The task has no frozen upstream destination. Run plan again before continuing.")
        if target != state["target"]:
            raise Blocked("The branch or upstream destination changed since the task began. Restore it or begin an explicitly separate task.")
        return target

    def sync_upstream(self, state: dict[str, Any]) -> dict[str, Any]:
        self.ensure_target(state)
        info = sync(self.root, state["target"])
        self.ensure_target(state)
        if not state.get("sync"):
            # Freeze the first usable tree and its receipt together, regardless
            # of which lifecycle entry point recovers the initial connection.
            state.update(initial_head=info["head"], sync=info)
            self.save(state)
        return info

    def plan(self, spec: dict[str, Any]) -> dict[str, Any]:
        state = self.load()
        self.identify_author(state)
        requirements = spec.get("requirements")
        if not isinstance(requirements, list) or not requirements or not all(isinstance(r, str) and r.strip() for r in requirements):
            raise Blocked("Plan requires a nonempty list of observable requirements.")
        raw_paths = spec.get("paths", [])
        if not isinstance(raw_paths, list) or not all(isinstance(p, str) for p in raw_paths):
            raise Blocked("Paths must list exact repository-relative files.")
        paths = [safe_path(self.root, p) for p in raw_paths]
        if paths or not state.get("sync_error"):
            # Renewing a plan pins contracts made before destination freezing,
            # while preserving their original ownership baseline and evidence.
            if not state.get("target"):
                target = delegate_target(self.root)
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
                    # Freeze successful recovery even if scope validation fails.
                    self.save(state)
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
        renames = spec.get("renames", state.get("renames", {}))
        preserved = rename_hashes(self.root, state, paths, renames)
        deletions = deletion_paths(self.root, state, paths, spec.get("deletions", []), renames)
        delegates = spec.get("delegates", state.get("delegates", []))
        if not isinstance(delegates, list):
            raise Blocked("Delegates must be an explicit list of lifecycle contracts.")
        roots = [str(delegate_state(self.root, entry)[0]) for entry in delegates]
        if len(set(roots)) != len(roots):
            raise Blocked("Declare each delegated repository only once.")
        targets = {root: delegate_target(Path(root)) for root in roots}
        for root, target in state.get("delegate_targets", {}).items():
            if root in targets and target != targets[root]:
                raise Blocked("A delegate destination changed; restore it before renewing this task.")
        state.update(requirements=requirements, paths=paths, deletions=deletions, review=None, finished=None,
                     adoption={p: adoption[p] for p in existing},
                     unrelated=spec.get("unrelated", {}), delegates=delegates, delegate_targets=targets,
                     renames=renames, rename_hashes=preserved)
        self.save(state)
        self.log("plan", requirements=len(requirements), paths=paths)
        return state

    def validate_checks(self, state: dict[str, Any]) -> None:
        latest = {c.get("command_sha256", digest(json.dumps(c.get("command", [])).encode())): index
                  for index, c in enumerate(state["checks"])}
        resolved = self.resolved_checks(state)
        if any(index not in resolved and (state["checks"][index]["exit_code"] != 0
                   or state["checks"][index]["changed_during_check"]) for index in latest.values()):
            raise Blocked("A check is still failing; rerun that check successfully before review.")
        required = [p for p in state["paths"] if p.endswith((".py", ".sh", ".js", ".ts", ".json", ".toml", ".yaml", ".yml"))
                    or p.startswith(".codex/git-hooks/")]
        version = artifact_snapshot(self.root, state["paths"])
        passing = [c for index in latest.values() for c in [state["checks"][index]]
                   if c["exit_code"] == 0 and not c["changed_during_check"]
                   and all(p in c["snapshot"] and c["snapshot"][p] == version[p] for p in required)]
        if required and not passing:
            raise Blocked("Code changes need a passing check recorded against the current artifacts.")

    def check_snapshot(self, state: dict[str, Any]) -> dict[str, str | None]:
        # Vault receipts predate the generic Git representation.
        return artifact_snapshot(self.root, state["paths"])

    def review_module(self):
        return review_engine()

    def checked_scope(self, state: dict[str, Any]) -> set[str]:
        return validate_changed_scope(state, changed(self.root), private_path)

    def identify_author(self, state: dict[str, Any]) -> None:
        # Session IDs and reviewer IDs use the same declared representation.
        # Upgrade earlier, not-yet-reviewed contracts without touching a ledger.
        if not state.get("review_gate") and state.get("author") in {None, self.key}:
            state["author"] = self.session
        super().identify_author(state)

    def review_context(self, state: dict[str, Any]) -> dict[str, Any]:
        # Older contracts may only declare rename sources. Keep those derived
        # absences alongside explicit deletions without discarding either.
        state["deletions"] = sorted(set(state.get("deletions", [])) | set(state.get("renames", {})))
        delegated = {}
        for entry in state.get("delegates", []):
            root, child = delegate_state(self.root, entry)
            check_delegate_target(root, state.get("delegate_targets", {}))
            child_paths = child["paths"]
            delegated[str(root)] = {
                "contract": {key: child.get(key) for key in (
                    "requirements", "paths", "deletions", "renames", "rename_hashes", "checks", "check_resolutions",
                    "review", "review_gate", "review_authors", "target", "publication", "finished")},
                "head": git(root, "rev-parse", "HEAD"),
                "artifacts": {name: (
                    "symlink:" + digest(os.readlink(delegated_path(root, child, name, "Delete File")).encode())
                    if (root / name).is_symlink() else
                    artifact_snapshot(root, [name])[name]) for name in child_paths}}
        state["review_context_sha256"] = digest(json.dumps({
            "checks": state.get("checks", []), "deletions": state["deletions"],
            "renames": state.get("renames", {}),
            "rename_hashes": state.get("rename_hashes", {}), "delegates": state.get("delegates", []),
            "delegate_targets": state.get("delegate_targets", {}), "delegated": delegated,
            "target": state.get("target")}, sort_keys=True).encode())
        return state

    def review(self, evidence: dict[str, Any]) -> dict[str, Any]:
        state = self.load()
        if not state["requirements"] or set(evidence) != set(state["requirements"]):
            raise Blocked("Supply evidence for every requirement, using the exact requirement as the key.")
        if not all(isinstance(v, str) and v.strip() for v in evidence.values()):
            raise Blocked("Review evidence must be nonempty text, not a boolean assertion.")
        current = snapshot(self.root, state["paths"])
        validate_renames(self.root, state, current)
        validate_deletions(self.root, state, current)
        for p, sha in current.items():
            if sha is None:
                if p in state.get("deletions", []) or p in state.get("renames", {}):
                    continue
                raise Blocked(f"Declared artifact missing: {p}")
            errors = validate_blob(self.root, p, (self.root / p).read_bytes())
            if errors:
                raise Blocked("\n".join(errors))
        self.validate_checks(state)
        self.independent_reviewed(state)
        state["review"] = {"at": now(), "evidence": evidence, "snapshot": current,
                           "check_resolutions_sha256": digest(json.dumps(state.get("check_resolutions", []), sort_keys=True).encode()),
                           "context_sha256": digest(json.dumps({"requirements": state["requirements"],
                               "review_context_sha256": state["review_context_sha256"]}, sort_keys=True).encode()),
                           "modes": snapshot_modes(self.root, state["paths"]),
                           "delegates": completed_delegates(self.root, state.get("delegates", []), targets=state.get("delegate_targets")),
                           "kind": "model_semantic_review_with_mechanical_validation"}
        state["finished"] = None
        self.save(state)
        self.log("review", paths=state["paths"])
        return {"reviewed": True, "requirements": len(evidence)}

    def reviewed(self, state: dict[str, Any]) -> None:
        if not state.get("review") or state["review"]["snapshot"] != snapshot(self.root, state["paths"]):
            raise Blocked("Missing or stale review. Compare the actual result with every requirement.")
        if state["review"].get("modes") != snapshot_modes(self.root, state["paths"]):
            raise Blocked("Missing or stale review: artifact permissions changed.")
        if state["review"].get("delegates", {}) != completed_delegates(self.root, state.get("delegates", []), targets=state.get("delegate_targets")):
            raise Blocked("Delegated results changed after review.")
        self.independent_reviewed(state)
        self.validate_checks(state)
        context_hash = digest(json.dumps({"requirements": state["requirements"],
            "review_context_sha256": state["review_context_sha256"]}, sort_keys=True).encode())
        if state["review"].get("context_sha256") != context_hash:
            raise Blocked("Missing or stale review: task or check context changed.")
        if state["review"].get("check_resolutions_sha256", digest(b"[]")) != digest(
                json.dumps(state.get("check_resolutions", []), sort_keys=True).encode()):
            raise Blocked("Missing or stale review: check resolutions changed.")
        validate_renames(self.root, state, state["review"]["snapshot"])
        validate_deletions(self.root, state, state["review"]["snapshot"])

    def dispatch(self, capacity: int) -> dict[str, Any]:
        from .dispatch import build

        return build(self, capacity)

    def guard_patch(self, payload: dict[str, Any], cwd: Path) -> None:
        state = self.load()
        if state.get("sync_error") or not state["requirements"]:
            raise Blocked(state.get("sync_error") or "Declare the task requirements and paths before editing.")
        self.ensure_target(state)
        inputs = payload.get("tool_input")
        if isinstance(inputs, str):
            patch = inputs
        elif isinstance(inputs, dict):
            # Native Codex wraps freeform apply_patch text in `command`.
            # This is patch data, never a shell command to execute.
            candidates = [inputs[key] for key in ("input", "patch", "command") if key in inputs]
            if (not candidates or any(not isinstance(value, str) for value in candidates)
                    or any(value != candidates[0] for value in candidates)):
                raise Blocked("Unrecognized or conflicting patch payload; no edit was authorized.")
            patch = candidates[0]
        else:
            raise Blocked("Unrecognized patch payload; no edit was authorized by this guard.")
        lines = patch.strip().splitlines()
        if not lines or lines[0] != "*** Begin Patch" or lines[-1] != "*** End Patch":
            raise Blocked("Expected a complete apply_patch document; no edit was authorized.")
        paths = re.findall(r"^\*\*\* (Add File|Update File|Delete File|Move to): (.+)$", patch, re.M)
        if not paths:
            raise Blocked("Unrecognized patch payload; no edit was authorized by this guard.")
        # Normalize the working directory (macOS exposes /var via /private/var),
        # but leave patch components unresolved so safe_path can reject aliases.
        cwd = cwd.resolve()
        delegated_entries = {entry["root"]: entry for entry in state.get("delegates", [])}
        validated_delegates: dict[str, tuple[Path, dict[str, Any]]] = {}
        for action, name in paths:
            raw = Path(name)
            if ".." in raw.parts:
                raise Blocked("Patch paths must not traverse parent directories.")
            target = cwd / raw
            # Validate the lookup chain before asking Git for a foreign owner.
            # The final link is handled by the recipient's exact deletion policy.
            if any(ps.is_reparse(parent) for parent in reversed(target.parents)):
                raise Blocked("Patch paths cannot traverse symlinks or reparse points.")
            if not target.is_relative_to(self.root):
                owner = git_owner(target)
                key = str(owner)
                if key not in delegated_entries:
                    raise Blocked(f"Undeclared external repository: {owner}")
                if key not in validated_delegates:
                    root, delegated = delegate_state(self.root, delegated_entries[key])
                    check_delegate_target(root, state.get("delegate_targets", {}))
                    validated_delegates[key] = (root, delegated)
                root, delegated = validated_delegates[key]
                delegated_path(root, delegated, target.relative_to(root).as_posix(), action)
                continue
            relative = safe_path(self.root, target.relative_to(self.root).as_posix())
            if relative not in state["paths"]:
                raise Blocked(f"Undeclared patch path: {relative}")
            deletions = set(state.get("deletions", [])) | set(state.get("renames", {}))
            if action == "Delete File" and relative not in deletions:
                raise Blocked(f"Undeclared deletion: {relative}")
            if relative in deletions and relative not in state.get("renames", {}) and action != "Delete File":
                raise Blocked(f"Declared deletion only authorizes Delete File: {relative}")

    def durable_reviewed(self, state: dict[str, Any], paths: list[str] | None = None,
                         revision: str = "HEAD") -> None:
        """Require reviewed bytes and modes in Git, independent of status flags."""
        selected = state["paths"] if paths is None else paths
        if not set(selected) <= set(state["paths"]):
            raise Blocked("Publication validation must stay inside the reviewed task scope.")
        if not selected:
            return
        review = state.get("review") or {}
        expected = {name: (None if review["snapshot"][name] is None else
                           review["modes"][name] + ":" + review["snapshot"][name]) for name in selected}
        if stored_snapshot(self.root, selected, revision) != expected:
            raise Blocked("Committed HEAD differs from the reviewed artifacts or permissions. Commit the reviewed version before publication or closure.")

    def publish(self, paths: list[str] | None = None, *, resume_deferred: bool = False,
                whole_head: bool = False) -> dict[str, Any]:
        state = self.load()
        if type(resume_deferred) is not bool:
            raise Blocked("resume-deferred must be an explicit boolean option.")
        if state.get("publication_deferred") and not resume_deferred:
            raise Blocked("Publication is deferred; use publish --resume-deferred only after authorizing the entire outgoing history.")
        if resume_deferred and not state.get("publication_deferred"):
            raise Blocked("There is no deferred publication to resume.")
        if paths is not None and (not paths or set(paths) != set(state.get("committed_paths", []))):
            raise Blocked("Partial publication requires the cumulative paths of verified workflow commits.")
        if state.get("publication_blocker"):
            raise Blocked(state["publication_blocker"])
        info = self.sync_upstream(state)
        self.reviewed(state)
        local = git(self.root, "rev-parse", "HEAD")
        self.durable_reviewed(state, paths, local)
        if whole_head and (state["paths"] or state.get("delegates")):
            raise Blocked("Whole-HEAD publication requires an explicit provider with no task paths.")
        target = self.ensure_target(state)
        publish_frozen(self.root, target, local, state["commits"],
                       lambda head, base: outgoing_gate(self.root, head, base), git, whole_head=whole_head)
        self.ensure_target(state)
        self.reviewed(state)
        self.durable_reviewed(state, paths, local)
        self.log("remote_verified", commit=local)
        publication = {"head": local, "remote": info["remote"], "ref": info["ref"], "verified_at": now()}
        if resume_deferred:
            state["publication"] = publication
            state.pop("publication_deferred")
            self.save(state)
        return publication

    def commit(self, paths: list[str], message: str, *, preserve_index: bool = False,
               local_only: bool = False) -> dict[str, Any]:
        state = self.load()
        if type(local_only) is not bool:
            raise Blocked("local-only must be an explicit boolean option.")
        if state.get("publication_deferred") and not local_only:
            raise Blocked("Publication is deferred; use commit --local-only or explicitly resume with publish --resume-deferred.")
        if state.get("publication_blocker"):
            raise Blocked(state["publication_blocker"])
        state.update(finished=None, publication=None)
        self.save(state)
        self.reviewed(state)
        if not paths or not set(paths) <= set(state["paths"]):
            raise Blocked("Commit paths must be a nonempty subset of the declared artifacts.")
        for old, new in state.get("renames", {}).items():
            if (old in paths) != (new in paths):
                raise Blocked("Commit both endpoints of a declared rename together.")
        initial_staged = staged_paths(self.root)
        if initial_staged and not preserve_index:
            raise Blocked("Index already contains staged work. Preserve it and resolve ownership explicitly.")
        if preserve_index and initial_staged & set(paths):
            raise Blocked("Selected paths overlap existing staged work; preserve-index requires disjoint ownership.")
        preserved = index_fingerprint(self.root, paths) if preserve_index else None
        self.sync_upstream(state)
        self.reviewed(state)
        parent = git(self.root, "rev-parse", "HEAD")
        if not local_only:
            with frozen_transport(self.root, state["target"], git) as transport:
                verify_outgoing_commits(self.root, remote_tip(transport, state["target"]), parent, state["commits"])
        git(self.root, "--literal-pathspecs", "add", "--", *paths, timeout=300)
        staged_gate(self.root, paths if preserve_index else None)
        staged = staged_paths(self.root)
        if preserve_index and index_fingerprint(self.root, paths) != preserved:
            raise Blocked("Unrelated index entries changed concurrently. They were not committed by this workflow.")
        if not preserve_index and not staged <= set(paths):
            raise Blocked("The index changed concurrently and contains unselected work. It was preserved.")
        expected = artifact_snapshot(self.root, paths)
        if stored_snapshot(self.root, paths) != expected:
            raise Blocked("Staged content differs from the reviewed artifacts. Preserve and review the changes before committing.")
        self.reviewed(state)
        # Hooks and other Git clients do not share our lifecycle lock. Inspect
        # the durable commit before it can leave this machine, including retry
        # after a crash or failed event write immediately following Git's commit.
        if local_only:
            # Persist the no-publication intent before Git can create history,
            # so recovery after a crash cannot silently enable an implicit push.
            state["publication_deferred"] = True
        state["publication_blocker"] = ("A local commit failed verification against the reviewed scope. "
                                        "It was preserved without publication; reconcile it explicitly before publishing.")
        self.save(state)
        try:
            commit_env = {"CONSTELLATION_COMMIT_OWNER": "native"}
            if preserve_index:
                git(self.root, "--literal-pathspecs", "commit", "--only", "-m", message, "--", *paths,
                    timeout=1200, extra_env=commit_env)
            else:
                git(self.root, "commit", "-m", message, timeout=1200, extra_env=commit_env)
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
        parents = git(self.root, "rev-list", "--parents", "-n", "1", commit).split()
        if parents != [commit, parent] or not actual_paths <= set(paths):
            raise Blocked(state["publication_blocker"])
        if stored_snapshot(self.root, paths, commit) != expected:
            raise Blocked(state["publication_blocker"])
        self.reviewed(state)
        state["committed_paths"] = sorted(set(state.get("committed_paths", [])) | set(paths))
        state.pop("publication_blocker")
        self.save(state)
        if local_only:
            self.log("commit_publication_deferred", commit=commit)
            return {"head": commit, "local_only": True, "publication_deferred": True,
                    "publication": None, "completed": False}
        published = self.publish(state["committed_paths"])
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
        expected = artifact_snapshot(self.root, state["paths"])
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
        state.update(commits=commits, committed_paths=list(state["paths"]),
                     publication=None, finished=None, stop_attempts=0)
        state.pop("publication_blocker")
        self.save(state)
        return {"recovered": True, "head": expected_head, "audited_commits": len(commits),
                "publication_verified": False}

    def finish(self, *, publish_readonly: bool = False) -> dict[str, Any]:
        state = self.load()
        if state.get("publication_deferred"):
            raise Blocked("Publication is deferred; explicitly resume with publish --resume-deferred before finishing.")
        query = not state["paths"] and not state.get("delegates")
        if type(publish_readonly) is not bool or publish_readonly and not query:
            raise Blocked("publish-readonly is only valid for a query with no paths or delegates.")
        state.update(finished=None, publication=None)
        self.save(state)
        self.reviewed(state)
        if query and not publish_readonly:
            unexpected = self.checked_scope(state)
            state.update(finished={"at": now(), "head": git(self.root, "rev-parse", "HEAD"),
                                   "readonly": True, "local_only": True},
                         unrelated_new_paths=sorted(unexpected))
            self.save(state)
            self.log("finish_readonly")
            return {"completed": True, "readonly": True, "local_only": True,
                    "publication": None, "unrelated_new_paths": sorted(unexpected)}
        completed_delegates(self.root, state.get("delegates", []), remote=True, targets=state.get("delegate_targets"))
        self.checked_scope(state)
        self.durable_reviewed(state)
        publication = self.publish(whole_head=publish_readonly)
        state = self.load()
        # Synchronization can fast-forward a clean tree after the first review.
        self.reviewed(state)
        completed_delegates(self.root, state.get("delegates", []), remote=True, targets=state.get("delegate_targets"))
        unexpected = self.checked_scope(state)
        self.durable_reviewed(state)
        finished = {"at": now(), "head": publication["head"]}
        if query:
            finished.update(readonly=True, local_only=False)
        state.update(publication=publication, finished=finished, unrelated_new_paths=sorted(unexpected))
        state.pop("sync_error", None)
        self.save(state)
        self.log("finish", commit=publication["head"])
        result = {"completed": True, "publication": publication, "unrelated_new_paths": sorted(unexpected)}
        if query:
            result.update(readonly=True, local_only=False)
        return result

    def stop(self, *, request_id: str | None = None) -> dict[str, Any]:
        state = self.load()
        key, migrated = prepare_stop(state, request_id)
        try:
            query = not state["paths"] and not state.get("delegates")
            finished = state.get("finished") or {}
            remote_query = query and finished.get("readonly") is True and finished.get("local_only") is False
            if not query or remote_query:
                self.ensure_target(state)
            self.reviewed(state)
            if not state.get("finished") or state["finished"]["head"] != git(self.root, "rev-parse", "HEAD"):
                raise Blocked("Run workflow.py finish to verify commits and the remote branch.")
            if query and finished.get("local_only") is not True:
                publication = state.get("publication") or {}
                target = state.get("target") or {}
                if (not remote_query or publication.get("head") != finished["head"]
                        or any(publication.get(key) != target.get(key) for key in ("remote", "ref"))):
                    raise Blocked("Run workflow.py finish for local closure, or finish --publish-readonly for a published query provider.")
            self.checked_scope(state)
            self.durable_reviewed(state)
        except Blocked as exc:
            reason = str(exc)
            result, charged = incomplete_stop(state, key, reason, label="OmarOS",
                continuation=f"[OMAROS-CONTINUE:{self.key}] {reason} Follow .codex/README.md. Report any real blocker; never claim completion without evidence.")
            if charged:
                self.log("stop_incomplete", reason=reason)
            if charged or migrated:
                self.save(state)
            return result
        if migrated:
            self.save(state)
        return {}


def coordination_context(session: str) -> str:
    """Keep prompt guidance aligned with the explicit native coordinator API."""
    return (f"For parallel work, run python3 .codex/workflow.py --session {session!r} dispatch --capacity N "
            "with N bounded by available session capacity, then assign its deterministic tasks to real native subagents. "
            "Read .codex/RESEARCH.md for research. Before independent review, register every contributing author "
            "with review-author using {author, paths} and actual native agent IDs. "
            "The coordinator alone integrates and publishes through check, review, commit and finish for each Git owner. ")


def subagent_context(session: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Return worker instructions without creating or consulting lifecycle state."""
    context = (f"OmarOS worker {payload.get('agent_id', 'unknown')!r}; parent session is {session!r}. "
               f"Use --session {session!r} when referring to the coordinator's contract. "
               "Read the vault AGENTS.md, .codex/README.md and the assigned repositories' AGENTS.md, "
               ".codex/PROJECT.md and applicable directory instructions. For research read .codex/RESEARCH.md. "
               "Work only on your assigned exact files; preserve other agents' changes. "
               "Do not begin, reset or replace the parent's contract. Do not commit or push; the coordinator publishes. "
               "Report your actual native agent ID, edited paths, results and verification evidence to the coordinator "
               "for review-author registration before independent review. Do not fabricate agent identities or reports. "
               "Do not inspect or manage worktree counts. Never persist prompts or transcripts in reports or artifacts.")
    return {"hookSpecificOutput": {"hookEventName": "SubagentStart", "additionalContext": context}}


def _git_root(directory: Path) -> Path:
    return Path(git(directory, "rev-parse", "--show-toplevel")).resolve()


def _hook_identifier(value: Any, field: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,200}", value):
        raise Blocked(f"Invalid vault hook {field}.")
    return value


def _prompt(flow: Workflow, turn: str) -> dict[str, Any]:
    previous = flow.load() if flow.path.exists() else None
    # Keep only native identifier hashes, including across completed tasks in this
    # session. A delayed delivery must not reopen an earlier task or discard a
    # later review. A pre-profile record has at most its latest known turn.
    key = digest(turn.encode("ascii"))
    history = list(previous.get("hook_turn_hashes", [])) if previous else []
    previous_turn = previous.get("turn") if previous else None
    if isinstance(previous_turn, str) and re.fullmatch(r"[A-Za-z0-9_.:-]{1,200}", previous_turn):
        previous_key = digest(previous_turn.encode("ascii"))
        if previous_key not in history:
            history.append(previous_key)
    if previous is not None and key in history:
        state = previous
    elif previous is not None and previous.get("requirements") and not previous.get("finished"):
        # A follow-up steers the open contract. Only the trusted lifecycle
        # decides when to replace it; the prompt content is never consulted.
        state = previous
        state.update(turn=turn, review=None, finished=None, hook_turn_hashes=history + [key])
        try:
            state["sync"] = flow.sync_upstream(state)
            state.pop("sync_error", None)
        except (Blocked, subprocess.TimeoutExpired) as exc:
            state["sync_error"] = str(exc)
        flow.save(state)
        flow.log("steered_prompt", turn=turn)
    else:
        state = flow.begin(turn, prior_hook_turns=history + [key])
    context = (f"OmarOS lifecycle active. Use --session {flow.session!r}. "
               "Read .codex/README.md; declare requirements with plan, execute, review each requirement, "
               "commit only declared files and finish (push + remote verification). "
               + coordination_context(flow.session)
               + "Do not inspect or manage worktree counts. Prompt/transcript content is never logged. ")
    if state["requirements"] and not state.get("finished"):
        context += "An unfinished contract was preserved; incorporate the current request. "
    context += ("SYNC BLOCKER: " + state["sync_error"] + " Read-only work may continue."
                if state.get("sync_error") else "Upstream checked.")
    return {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": context}}


def handle_hook_event(payload: dict[str, Any], *, project_root: Path) -> dict[str, Any]:
    """Dispatch native metadata to one registered vault under its existing lock.

    The caller independently authenticates its installed package and selects the
    vault root. An event in a sibling or nested Git owner cannot create vault
    state. Only the necessary identifiers and patch input are inspected.
    """
    return _handle_hook(payload, project_root=project_root, legacy_cli=False)


def _handle_hook(payload: dict[str, Any], *, project_root: Path, legacy_cli: bool) -> dict[str, Any]:
    event = payload.get("hook_event_name")
    if event not in {"UserPromptSubmit", "PreToolUse", "Stop", "SubagentStart"}:
        return {}
    raw_cwd = payload.get("cwd")
    if not isinstance(raw_cwd, str) or not Path(raw_cwd).is_absolute():
        raise Blocked("Vault hook requires an absolute working directory.")
    root = project_root.resolve(strict=True)
    cwd = Path(raw_cwd).resolve(strict=True)
    if not cwd.is_relative_to(root) or _git_root(cwd) != root:
        return {}
    session = _hook_identifier(payload.get("session_id"), "session_id")
    if event == "SubagentStart":
        agent_id = _hook_identifier(payload.get("agent_id"), "agent_id")
        return subagent_context(session, {"agent_id": agent_id})
    if event == "PreToolUse":
        # The general plugin matcher also handles Edit and Write. Those native
        # operations are intentionally refused by the vault patch-only contract.
        name = payload.get("tool_name")
        if name is not None and not isinstance(name, str):
            raise Blocked("Invalid vault hook tool name.")
        if name is not None and not re.fullmatch(r"(?:[A-Za-z0-9_]+[.:])*(apply_patch|Edit|Write)", name):
            return {}
        if name is not None and not name.endswith("apply_patch"):
            raise Blocked("Vault edits require a declared apply_patch document.")
    with review_gate.selected_project(root):
        flow = Workflow(root, session)
        with flow.lock():
            if event == "UserPromptSubmit":
                return _prompt(flow, _hook_identifier(payload.get("turn_id"), "turn_id"))
            if event == "Stop":
                turn = payload.get("turn_id")
                if not legacy_cli or turn is not None:
                    turn = _hook_identifier(turn, "turn_id")
                continuation = payload.get("stop_hook_active", False)
                if not isinstance(continuation, bool):
                    raise Blocked("Invalid vault stop continuation metadata.")
                # Claude's project CLI predates native turn identifiers. Without
                # one, distinct Stop events have no provable replay identity.
                request_id = digest(json.dumps([session, turn, continuation]).encode()) if turn is not None else None
                return flow.stop(request_id=request_id) if flow.path.exists() else {
                    "continue": False, "systemMessage": "OmarOS: INCOMPLETE. No task contract; check that UserPromptSubmit is trusted."}
            flow.guard_patch({"tool_input": payload.get("tool_input")}, cwd)
            return {}


def entrypoint(argv: list[str] | None = None, *, project_root: Path) -> int:
    """Run one command for the trusted root selected by the verified launcher."""
    try:
        with review_gate.selected_project(project_root):
            return main(argv, project_root=project_root)
    except (Blocked, subprocess.TimeoutExpired, OSError, ValueError) as exc:
        print(f"OmarOS: {exc}", file=sys.stderr)
        return 2


def main(argv: list[str] | None = None, *, project_root: Path | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=project_root or Path.cwd())
    parser.add_argument("--session", default=os.environ.get("CODEX_THREAD_ID", "manual"))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("begin").add_argument("--turn", default="manual")
    sub.add_parser("plan")
    sub.add_parser("review")
    sub.add_parser("check-resolve")
    for name in ("review-context", "review-start", "review-report", "review-resolve", "review-author", "review-budget"):
        command = sub.add_parser(name)
        if name == "review-start":
            command.add_argument("--risk", choices=("quick", "standard", "deep"))
            command.add_argument("--continuation-reason")
            command.add_argument("--continuation-next-action")
    sub.add_parser("dispatch").add_argument("--capacity", type=int, required=True)
    sub.add_parser("recover").add_argument("expected_head")
    sub.add_parser("status")
    sub.add_parser("guard-status")
    sub.add_parser("progress-show")
    sub.add_parser("progress-update")
    ack = sub.add_parser("progress-ack")
    ack.add_argument("--policy", type=Path, default=journal_engine().POLICY_PATH)
    export = sub.add_parser("progress-export")
    export.add_argument("--task-uid", required=True)
    export.add_argument("--policy", type=Path, default=journal_engine().POLICY_PATH)
    for command in ("journal-paths", "journal-import"):
        journal = sub.add_parser(command)
        journal.add_argument("--source-root", type=Path, required=True)
        journal.add_argument("--policy", type=Path, default=journal_engine().POLICY_PATH)
    sub.add_parser("finish").add_argument("--publish-readonly", action="store_true")
    check = sub.add_parser("check")
    check.add_argument("--timeout", type=int, default=300)
    check.add_argument("argv", nargs=argparse.REMAINDER)
    commit = sub.add_parser("commit")
    commit.add_argument("-m", "--message", required=True)
    commit.add_argument("--preserve-index", action="store_true")
    commit.add_argument("--local-only", action="store_true")
    commit.add_argument("paths", nargs="+")
    sub.add_parser("publish").add_argument("--resume-deferred", action="store_true")
    sub.add_parser("hook").add_argument("event", choices=["prompt", "pre-tool", "stop", "subagent-start"])
    sub.add_parser("git-hook").add_argument("event", choices=["pre-commit", "post-commit", "pre-push"])
    args = parser.parse_args(argv)
    payload = json.load(sys.stdin) if args.command in {"plan", "review", "check-resolve", "hook", "review-report", "review-resolve", "review-author", "review-budget", "progress-update", "progress-ack", "journal-import", "journal-paths"} else {}
    root = _git_root(args.root)
    if project_root is not None and root != project_root.resolve(strict=True):
        raise Blocked("This vault launcher is bound to a different Git owner.")
    if args.command == "guard-status":
        from .install import verify_guard

        home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
        print(json.dumps(verify_guard(root, home), ensure_ascii=False))
        return 0
    if args.command == "hook":
        events = {"prompt": "UserPromptSubmit", "pre-tool": "PreToolUse",
                  "stop": "Stop", "subagent-start": "SubagentStart"}
        data = {**payload, "hook_event_name": events[args.event]}
        data.setdefault("cwd", str(args.root))
        data.setdefault("session_id", args.session)
        print(json.dumps(_handle_hook(data, project_root=root, legacy_cli=True), ensure_ascii=False))
        return 0
    workflow = Workflow(root, args.session)
    # Git runs its hooks synchronously inside commit/push; reacquiring the parent
    # lock would deadlock. Status reads an atomically replaced JSON snapshot and
    # must also remain observable from a check while its writer holds the lock.
    with (nullcontext() if args.command in {"git-hook", "status"} else workflow.lock()):
        if args.command == "begin":
            result = workflow.begin(args.turn)
        elif args.command == "plan":
            result = workflow.plan(payload)
        elif args.command == "review":
            result = workflow.review(payload)
        elif args.command == "check-resolve":
            result = workflow.check_resolve(payload)
        elif args.command.startswith("review-"):
            operation = args.command[len("review-"):]
            if operation == "start":
                payload = {"risk": args.risk}
                if args.continuation_reason is not None or args.continuation_next_action is not None:
                    payload["continuation"] = {"reason": args.continuation_reason,
                                               "next_action": args.continuation_next_action}
            result = workflow.review_operation("prepare" if operation == "context" else operation, payload)
        elif args.command == "dispatch":
            result = workflow.dispatch(args.capacity)
        elif args.command == "recover":
            result = workflow.recover(args.expected_head)
        elif args.command == "status":
            result = workflow.load()
        elif args.command == "progress-show":
            result = workflow.progress_show()
        elif args.command == "progress-update":
            result = workflow.progress_update(payload)
        elif args.command == "progress-export":
            result = workflow.progress_export(args.task_uid, args.policy)
        elif args.command == "progress-ack":
            result = workflow.progress_ack(payload, args.policy)
        elif args.command == "journal-paths":
            envelope, paths = journal_engine().authorized_paths(
                payload, source_root=args.source_root, policy=journal_engine().read_policy(args.policy),
                progress=progress_engine(), target_root=workflow.root)
            result = {"task_uid": envelope["task_uid"], "paths": paths}
        elif args.command == "journal-import":
            result = workflow.journal_import(payload, args.source_root, args.policy)
        elif args.command == "check":
            result = workflow.check(args.argv[1:] if args.argv[:1] == ["--"] else args.argv, timeout=args.timeout)
        elif args.command == "commit":
            result = workflow.commit(args.paths, args.message, preserve_index=args.preserve_index,
                                     local_only=args.local_only)
        elif args.command == "publish":
            result = workflow.publish(resume_deferred=args.resume_deferred)
        elif args.command == "finish":
            result = workflow.finish(publish_readonly=args.publish_readonly)
        elif args.command == "git-hook":
            if args.event == "pre-commit":
                staged_gate(root)
                notes_monitor_index_gate(root)
                workflow.log("git_commit_preflight")
            elif args.event == "post-commit":
                workflow.log("git_committed", commit=git(root, "rev-parse", "HEAD"))
            else:
                for line in sys.stdin:
                    _, local, _, remote_sha = line.split()
                    outgoing_gate(root, local, remote_sha)
                workflow.log("git_push_preflight")
            result = {}
    print(json.dumps(result, ensure_ascii=False))
    return 0

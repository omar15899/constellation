"""Adaptive, revision-specific independent review of declared artifacts.

Reviewer identities are attestations, not cryptographic proof of independence.
Only publishable engineering evidence belongs in reports: never conversation,
prompt, command or captured-output text. This module does not spawn agents,
grant human approval, or replace a repository's CI and deployment controls.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
from typing import Any, Callable

from . import DEFAULT_POLICY


class ReviewError(ValueError):
    """A review contract is invalid, incomplete or no longer current."""


MODES = ("quick", "standard", "deep")
FOCUS = {"correctness", "security"}
SEVERITIES = {"critical", "high", "medium", "low"}


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode()).hexdigest()


def _text(value: Any, label: str, limit: int = 12000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ReviewError(f"{label} must be nonempty text of at most {limit} characters.")
    return value.strip()


def _integer(value: Any, label: str, low: int = 1, high: int = 64) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ReviewError(f"{label} must be an integer from {low} to {high}.")
    return value


def _strings(value: Any, label: str, *, empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not empty):
        raise ReviewError(f"{label} must be a list{' (which may be empty)' if empty else ' with entries'}.")
    for item in value:
        _text(item, label, 1000)
    # A path's whitespace is part of its identity. Validation must never redirect
    # evidence to another file by normalizing an otherwise legal filename.
    result = list(value)
    if len(result) != len(set(result)):
        raise ReviewError(f"{label} cannot contain duplicates.")
    return result


def _object(value: Any, label: str, required: set[str], optional: set[str] = frozenset()) -> dict[str, Any]:
    if not isinstance(value, dict) or not required <= value.keys() or value.keys() - required - optional:
        raise ReviewError(f"{label} has missing or unknown fields.")
    return value


def _read_json(path: Path, label: str) -> Any:
    if path.is_symlink() or not path.is_file():
        raise ReviewError(f"{label} must exist as a regular local file: {path}")
    try:
        return json.loads(path.read_text())
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReviewError(f"Cannot read {label}: {type(exc).__name__}.") from None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _deadline(value: Any) -> datetime:
    text = _text(value, "Review budget deadline", 64)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)", text) is None:
        raise ReviewError("Review budget deadline must be an explicit UTC ISO 8601 timestamp.")
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        raise ReviewError("Review budget deadline must be a valid UTC timestamp.") from None


def _budget_context(state: dict[str, Any]) -> dict[str, Any]:
    record = state.get("review_budget")
    if record is None:
        return {"revision": 0, "deadline_at": None, "status": "unknown"}
    _object(record, "Stored review budget", {"revision", "deadline_at", "author", "history"})
    revision = _integer(record["revision"], "Review budget revision", high=2**63 - 1)
    deadline = _deadline(record["deadline_at"])
    if record["author"] != _author(state):
        raise ReviewError("Task author identity changed during review budgeting.")
    if not isinstance(record["history"], list) or len(record["history"]) != revision:
        raise ReviewError("Review budget history must retain every revision.")
    for number, entry in enumerate(record["history"], 1):
        _object(entry, "Review budget history entry", {"revision", "deadline_at", "reason", "author", "recorded_at"})
        if type(entry["revision"]) is not int or entry["revision"] != number or entry["author"] != record["author"]:
            raise ReviewError("Review budget history or frozen author is inconsistent.")
        _deadline(entry["deadline_at"])
        _deadline(entry["recorded_at"])
        _text(entry["reason"], "Review budget reason", 1000)
    if record["history"][-1]["deadline_at"] != record["deadline_at"]:
        raise ReviewError("Review budget deadline does not match its history.")
    return {"revision": revision, "deadline_at": record["deadline_at"],
            "status": "exhausted" if _utc_now() >= deadline else "available"}


def budget(root: Path, state: dict[str, Any], payload: dict[str, Any], *, policy_path: Path | None = None,
           path_validator: Callable[[Path, str], Any] | None = None) -> dict[str, Any]:
    """Persist an explicit wall-clock deadline without altering review evidence."""
    _object(payload, "Review budget", {"expected_budget_revision", "deadline_at", "reason"})
    expected = _integer(payload["expected_budget_revision"], "Expected budget revision", low=0, high=2**63 - 2)
    deadline = _deadline(payload["deadline_at"]).isoformat().replace("+00:00", "Z")
    reason = _text(payload["reason"], "Review budget reason", 1000)
    context = prepare(root, state, policy_path=policy_path, path_validator=path_validator)
    if not context["enabled"]:
        raise ReviewError("Review budget requires an enabled independent review policy.")
    previous = context["budget"]
    if expected != previous["revision"]:
        record = state.get("review_budget")
        if record and expected == previous["revision"] - 1:
            latest = record["history"][-1]
            if latest["deadline_at"] == deadline and latest["reason"] == reason:
                return {"budget": previous, "unchanged": True}
        raise ReviewError("Review budget revision is stale; read the current budget before changing it.")
    frozen_author = _author(state)
    if state.get("review_gate") is not None:
        ledger = _ledger(state, context, allow_policy_change=True)
        if ledger["author"] != frozen_author:
            raise ReviewError("Task author identity changed during independent review.")
    history = deepcopy(state.get("review_budget", {}).get("history", []))
    revision = expected + 1
    history.append({"revision": revision, "deadline_at": deadline, "reason": reason,
                    "author": frozen_author, "recorded_at": _utc_now().isoformat().replace("+00:00", "Z")})
    state["review_budget"] = {"revision": revision, "deadline_at": deadline,
                              "author": frozen_author, "history": history}
    return {"budget": _budget_context(state), "unchanged": False}


def _validated_policy(value: Any) -> dict[str, Any]:
    _object(value, "Review policy", {"schema_version", "modes",
                                    "documentation_extensions", "documentation_names", "deep_patterns"},
            {"allow_quick_code", "max_rounds"})
    if "allow_quick_code" in value and type(value["allow_quick_code"]) is not bool:
        raise ReviewError("allow_quick_code must be a boolean.")
    if type(value["schema_version"]) is not int or value["schema_version"] not in {1, 2}:
        raise ReviewError("Unsupported review policy schema_version.")
    if value["schema_version"] == 1:
        _integer(value.get("max_rounds"), "Legacy maximum review rounds", high=10)
    elif "max_rounds" in value:
        raise ReviewError("Schema 2 review policy does not accept max_rounds.")
    _object(value["modes"], "Review modes", set(MODES))
    previous_count = 0
    previous_focus: dict[str, int] = {}
    for mode in MODES:
        config = _object(value["modes"][mode], f"Mode {mode}", {"reviewers", "focus"})
        count = _integer(config["reviewers"], f"{mode} reviewers")
        focuses = config["focus"]
        if not isinstance(focuses, dict) or not focuses or focuses.keys() - FOCUS or "correctness" not in focuses:
            raise ReviewError(f"Mode {mode} requires correctness focus and only supported focus names.")
        for name, required in focuses.items():
            _integer(required, f"{mode}/{name} reviewers", high=count)
        if count < previous_count or any(focuses.get(name, 0) < required for name, required in previous_focus.items()):
            raise ReviewError("Higher risk modes cannot reduce reviewer requirements.")
        previous_count, previous_focus = count, focuses
    if "security" not in value["modes"]["deep"]["focus"]:
        raise ReviewError("Deep review requires security focus.")
    for key in ("documentation_extensions", "documentation_names", "deep_patterns"):
        _strings(value[key], key, empty=key != "deep_patterns")
    if any(not extension.startswith(".") or "/" in extension for extension in value["documentation_extensions"]):
        raise ReviewError("Documentation extensions must be filename suffixes beginning with a dot.")
    # Normalize legacy policy and ledger floors before hashing. The obsolete
    # round cap is not a safety minimum; every other floor remains binding.
    return {**{key: deepcopy(item) for key, item in value.items() if key != "max_rounds"},
            "schema_version": 2}


def _policy_floor(policy: dict[str, Any], previous: dict[str, Any] | None) -> dict[str, Any]:
    """Configuration changes may strengthen an active task, never weaken it."""
    policy = _validated_policy(policy)
    if previous is None:
        return {**policy, **{name: sorted(policy[name]) for name in
                            ("documentation_extensions", "documentation_names", "deep_patterns")}}
    previous = _validated_policy(previous)
    result = {**policy, "modes": {}}
    if "allow_quick_code" in policy or "allow_quick_code" in previous:
        result["allow_quick_code"] = policy.get("allow_quick_code", False) and previous.get("allow_quick_code", False)
    for mode in MODES:
        current, old = policy["modes"][mode], previous["modes"][mode]
        result["modes"][mode] = {"reviewers": max(current["reviewers"], old["reviewers"]),
                                 "focus": {focus: max(current["focus"].get(focus, 0), old["focus"].get(focus, 0))
                                           for focus in current["focus"].keys() | old["focus"].keys()}}
    for name in ("documentation_extensions", "documentation_names"):
        result[name] = sorted(set(policy[name]) & set(previous[name]))
    result["deep_patterns"] = sorted(set(policy["deep_patterns"]) | set(previous["deep_patterns"]))
    return _validated_policy(result)


def policy_for(root: Path, *, policy_path: Path | None = None) -> dict[str, Any] | None:
    """Apply shared minimums to every exact native ownership registration.

    A nested registry cannot withdraw an enclosing workspace's native contract.
    External and unregistered owners retain their own rules when no workspace
    registers them as native. Standalone and native projects may tighten the
    packaged policy locally without creating a project registry; registering
    workspaces may add their own restrictions.
    Explicit injection remains a separate contract for embedding and tests.
    """
    root = root.resolve()
    if policy_path is not None:
        return _validated_policy(_read_json(Path(policy_path), "review policy"))
    workspaces = []
    registered_native = []
    # CLI routing chooses the nearest workspace. Review instead retains every
    # applicable native contract, so nearer project data cannot turn it off.
    for hub in (root, *root.parents):
        registry_path = hub / ".codex/repositories.json"
        if not (registry_path.exists() or registry_path.is_symlink()):
            continue
        workspaces.append(hub)
        registry = _read_json(registry_path, "repository registry")
        if not isinstance(registry, dict) or not isinstance(registry.get("repositories"), list):
            raise ReviewError("Invalid repository registry.")
        name = root.relative_to(hub).as_posix()
        matching = [entry for entry in registry["repositories"]
                    if isinstance(entry, dict) and entry.get("path") == name]
        if not matching:
            continue
        if len(matching) != 1 or matching[0].get("management") not in {"native", "external"}:
            raise ReviewError("Invalid or duplicate repository registration.")
        if matching[0]["management"] == "native":
            registered_native.append(hub)
    if workspaces and not registered_native:
        return None
    if registered_native:
        try:
            actual = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=root,
                                    capture_output=True, text=True, timeout=25, check=True)
        except (OSError, subprocess.SubprocessError):
            raise ReviewError("Cannot verify the registered native repository owner.") from None
        if Path(actual.stdout.strip()).resolve() != root:
            raise ReviewError("The registered native path is not its actual Git repository root.")
    policy = _validated_policy(_read_json(DEFAULT_POLICY, "review policy"))
    for owner in dict.fromkeys([root, *registered_native]):
        local_policy = owner / ".codex/review-policy.json"
        if local_policy.exists() or local_policy.is_symlink():
            policy = _policy_floor(_validated_policy(_read_json(local_policy, "review policy")), policy)
    return policy


def _path(root: Path, name: str) -> Path:
    path = Path(name)
    parts = path.parts
    lower = name.lower()
    lowered_parts = Path(lower).parts
    # Imported Markdown can document a daemon; its runtime logs remain private.
    managed_daemon_document = (
        len(lowered_parts) >= 5 and lowered_parts[1] == "research_repositories"
        and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", lowered_parts[2]) is not None
        and lowered_parts[3] == "files"
        and not any("_daemon." in part for part in lowered_parts[:-1])
        and ((lowered_parts[0] == "11_documents_and_reports" and lowered_parts[-1].endswith("_daemon.md"))
             or (lowered_parts[0] == "90_attachments" and lowered_parts[-1].endswith("_daemon.md.source")))
    )
    if (not parts or path.is_absolute() or ".." in parts or path.as_posix() != name
            or any(part.lower() in {".git", ".ssh", "secrets", "conversations", "rollouts",
                                   "archived_sessions", "turn_states", ".sync_state", ".codex_notuse"}
                   for part in parts)
            or any(part.lower() == ".env" or part.lower().startswith(".env.") for part in parts)
            or "conversation_archive" in lower or "_conversations/" in lower
            or ("_daemon." in lower and not managed_daemon_document)
            or lower.startswith((".codex/sessions/", ".codex/log/", ".codex/state/", ".codex/cache/",
                                 ".claude/cache/", ".claude/run/", "docs/sk_runs/"))
            or path.name.lower().startswith("rollout-")
            or path.name.lower() in {"auth.json", "credentials.json", "secrets.json", ".netrc", "id_rsa", "id_ed25519"}
            or lower.endswith((".pem", ".key", ".p12", ".pfx", ".jsonl"))):
        raise ReviewError(f"Invalid or private review path: {name}")
    target = root / path
    if any((root / parent).is_symlink() for parent in path.parents) or not target.parent.resolve().is_relative_to(root):
        raise ReviewError(f"Review path traverses a symlink or escapes its repository: {name}")
    return target


def _artifacts(root: Path, paths: list[str], deletions: list[str]) -> dict[str, Any]:
    result = {}
    for name in sorted(paths):
        target = _path(root, name)
        try:
            info = target.lstat()
        except FileNotFoundError:
            result[name] = None
            continue
        if stat.S_ISLNK(info.st_mode):
            if name not in deletions:
                raise ReviewError(f"Review artifact is a symlink: {name}")
            result[name] = {"sha256": hashlib.sha256(os.readlink(target).encode()).hexdigest(), "mode": "120000"}
        elif stat.S_ISREG(info.st_mode):
            result[name] = {"sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                            "mode": "100755" if info.st_mode & 0o100 else "100644"}
        else:
            raise ReviewError(f"Review artifact must be a regular file: {name}")
    return result


def prepare(root: Path, state: dict[str, Any], *, policy_path: Path | None = None,
            path_validator: Callable[[Path, str], Any] | None = None,
            _quick_code_reason: str | None = None) -> dict[str, Any]:
    """Return the exact context required for the next independent review."""
    policy = policy_for(root, policy_path=policy_path)
    if policy is None:
        if state.get("review_gate"):
            raise ReviewError("An active review cannot be disabled by changing repository registration.")
        return {"enabled": False}
    ledger = state.get("review_gate")
    policy_hash = _hash(policy)
    if policy_path is not None and (_quick_code_reason is not None or
            isinstance(ledger, dict) and ledger.get("quick_code_declaration") is not None):
        # Embedders retain their explicit ordinary-review contract. The optional
        # relaxation additionally requires the receiver's current consent, on
        # every preparation and validation, including after the first report.
        receiver_policy = policy_for(root)
        policy_hash = _hash({"explicit_policy": policy, "receiver_policy": receiver_policy})
        policy = (_policy_floor(policy, receiver_policy) if receiver_policy is not None
                  else {**policy, "allow_quick_code": False})
    policy = _policy_floor(policy, ledger.get("policy_floor") if isinstance(ledger, dict) else None)
    root = root.resolve()
    requirements = _strings(state.get("requirements"), "Requirements")
    paths = _strings(state.get("paths"), "Review paths", empty=True)
    deletions = _strings(state.get("deletions", []), "Review deletions", empty=True)
    if not set(deletions) <= set(paths):
        raise ReviewError("Review deletions must be a subset of review paths.")
    if not paths:
        if ledger:
            raise ReviewError("An active review cannot become read-only by withdrawing its entire scope.")
        return {"enabled": False, "reason": "read-only scope"}
    # Domain restrictions run before the shared engine reads any artifact.
    # Their return value cannot redirect the canonical, validated path.
    if path_validator is not None:
        for name in paths:
            path_validator(root, name)
    artifacts = _artifacts(root, paths, deletions)
    deep = any(fnmatch.fnmatchcase(path.lower(), pattern.lower())
               for path in paths for pattern in policy["deep_patterns"])
    docs_only = all(Path(path).suffix.lower() in policy["documentation_extensions"]
                    or Path(path).name in policy["documentation_names"] for path in paths)
    mode = "deep" if deep else "quick" if docs_only else "standard"
    risk_floor = state.get("review_risk", "quick")
    previous_mode = ledger.get("mode_floor", "quick") if isinstance(ledger, dict) else "quick"
    if risk_floor not in MODES or previous_mode not in MODES:
        raise ReviewError("Review risk must be quick, standard or deep.")
    mode = max((mode, risk_floor, previous_mode), key=MODES.index)
    authors = _authors(root, state)
    token_material = {"repository": str(root), "author": state.get("author"),
                   "review_authors": authors,
                   "task_started": state.get("started"), "initial_head": state.get("initial_head"),
                   "policy": policy_hash, "policy_floor": _hash(policy), "mode": mode,
                   "requirements": requirements, "paths": sorted(paths),
                   "deletions": sorted(deletions), "artifacts": artifacts}
    extra_context = {}
    if "review_context_sha256" in state:
        digest = state["review_context_sha256"]
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ReviewError("Review context SHA-256 must be 64 lowercase hexadecimal characters.")
        extra_context["review_context_sha256"] = digest
        token_material.update(extra_context)
    declaration = ledger.get("quick_code_declaration") if isinstance(ledger, dict) else None
    if _quick_code_reason is not None:
        reason = _text(_quick_code_reason, "Quick code reason", 1000)
        if ledger is None:
            if not policy.get("allow_quick_code", False):
                raise ReviewError("The effective review policy does not permit Quick code declarations.")
            if docs_only or mode != "standard":
                raise ReviewError("Quick code declarations apply only to ordinary non-sensitive code; existing risk floors remain binding.")
            # The pure preparation binds the premise to the ordinary Standard
            # snapshot. Only start persists it after all admission checks pass.
            declaration = {"reason": reason, "snapshot_sha256": _hash(token_material)}
    if declaration is not None:
        _object(declaration, "Quick code declaration", {"reason", "snapshot_sha256"})
        reason = _text(declaration["reason"], "Quick code reason", 1000)
        if not isinstance(declaration["snapshot_sha256"], str) or re.fullmatch(r"[0-9a-f]{64}", declaration["snapshot_sha256"]) is None:
            raise ReviewError("Quick code declaration snapshot must be a SHA-256 digest.")
        current = declaration["snapshot_sha256"] == _hash(token_material)
        if current and policy.get("allow_quick_code", False) and not deep and not docs_only:
            mode = max(("quick", risk_floor, previous_mode), key=MODES.index)
        elif not current:
            # A changed scope must not regain Quick by becoming documentation;
            # the coordinator's original premise no longer describes this work.
            mode = max((mode, "standard"), key=MODES.index)
        extra_context.update(quick_code_reason=reason, quick_code_current=current,
                             quick_code_declaration=declaration)
        token_material.update(mode=mode, quick_code_declaration=declaration)
    token = _hash(token_material)
    adaptation = _adaptation(ledger, artifacts, token)
    return {"enabled": True, "token": token, **extra_context, "mode": mode, "policy_sha256": policy_hash,
            "policy_floor": policy,
            "required_reviewers": policy["modes"][mode]["reviewers"],
            "required_focus": policy["modes"][mode]["focus"],
            "budget": _budget_context(state), "adaptation": adaptation,
            "requirements": requirements, "author": _author(state), "review_authors": authors,
            "paths": paths, "deletions": deletions, "artifacts": artifacts,
            "identity_assurance": "declared identities; not cryptographically authenticated"}


def _ledger(state: dict[str, Any], context: dict[str, Any], *, allow_policy_change: bool = False) -> dict[str, Any]:
    ledger = state.get("review_gate")
    if not isinstance(ledger, dict) or ledger.get("schema_version") not in {1, 2} or not isinstance(ledger.get("rounds"), list) or not isinstance(ledger.get("findings"), dict):
        raise ReviewError("Start an independent review before submitting evidence or publishing.")
    if not allow_policy_change and ledger.get("policy_sha256") != context["policy_sha256"]:
        raise ReviewError("Review policy changed during this task; start a fresh round under its retained policy floor.")
    return ledger


def _current(state: dict[str, Any], context: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    ledger = _ledger(state, context)
    if not ledger["rounds"] or ledger["rounds"][-1]["token"] != context["token"]:
        raise ReviewError("Independent review is missing or stale; start a round for the current artifacts.")
    return ledger, ledger["rounds"][-1]


def _independent_basis(ledger: dict[str, Any] | None) -> str:
    """Fingerprint recorded observations, not token churn or a quality score."""
    observations = set()
    for revision in (ledger or {}).get("rounds", []):
        for report in revision["reports"].values():
            observations.add(_hash({"artifact_fingerprint": revision.get("artifact_fingerprint"),
                                    "report": {key: value for key, value in report.items() if key != "token"}}))
    for identifier, finding in (ledger or {}).get("findings", {}).items():
        for resolution in finding.get("resolutions", []):
            observations.add(_hash({"finding": identifier, "path": finding["path"],
                                    "resolution": {key: value for key, value in resolution.items()
                                                   if key not in {"token", "round", "review_context_sha256"}}}))
    return _hash(sorted(observations))


def _adaptation(ledger: dict[str, Any] | None, artifacts: dict[str, Any], token: str) -> dict[str, Any]:
    fingerprint = _hash(artifacts)
    rounds = (ledger or {}).get("rounds", [])
    basis = _independent_basis(ledger)
    matches = [revision for revision in rounds if revision.get("artifact_fingerprint") == fingerprint]
    unchanged = bool(rounds and rounds[-1]["token"] == token)
    repeat = matches[-1] if matches else None
    no_progress = repeat is not None and repeat.get("independent_basis") == basis
    findings = (ledger or {}).get("findings", {})
    cycle = _hash({"artifacts": fingerprint, "findings": sorted(findings)})
    recurring = []
    if rounds:
        observed = {item["id"] for report in rounds[-1]["reports"].values() for item in report["findings"]}
        recurring = sorted(identifier for identifier in observed if any(
            resolution["round"] < rounds[-1]["number"] for resolution in findings[identifier].get("resolutions", [])))
    return {"artifact_fingerprint": fingerprint, "independent_basis": basis,
            "signal": "unchanged" if unchanged else "repeated_without_new_observation" if no_progress
                      else "new_independent_observation" if repeat
                      else "legacy_baseline" if rounds and not any("artifact_fingerprint" in item for item in rounds)
                      else "new_artifacts" if rounds else "initial",
            "continuation_required": bool(no_progress and not unchanged),
            "cycle_key": cycle, "repeated_round": repeat["number"] if repeat else None,
            "recurring_findings": recurring, "observations_round": rounds[-1]["number"] if rounds else None,
            "history_complete": all("artifact_fingerprint" in item for item in rounds),
            "limits": "Exact artifact and recorded-observation comparison; not semantic progress or native resource telemetry."}


def _author(state: dict[str, Any]) -> str:
    return _text(state.get("author"), "Task author identity", 128)


def _authors(root: Path, state: dict[str, Any]) -> dict[str, list[str]]:
    """Preserve attribution even when a later plan withdraws an artifact."""
    authors = state.get("review_authors", {})
    if not isinstance(authors, dict):
        raise ReviewError("Contributing authors must map identities to artifact paths.")
    normalized = {}
    for identity, paths in authors.items():
        if _text(identity, "Contributing author identity", 128) != identity:
            raise ReviewError("Contributing author identities cannot have surrounding whitespace.")
        entries = _strings(paths, "Contributing author paths")
        for name in entries:
            _path(root, name)
        normalized[identity] = sorted(entries)
    return dict(sorted(normalized.items()))


def author(root: Path, state: dict[str, Any], payload: dict[str, Any], *, policy_path: Path | None = None,
           path_validator: Callable[[Path, str], Any] | None = None) -> dict[str, Any]:
    """Register cumulative, declared authorship before assigning independent review."""
    context = prepare(root, state, policy_path=policy_path, path_validator=path_validator)
    if not context["enabled"]:
        raise ReviewError("Independent review policy is not enabled for this repository.")
    _object(payload, "Contributing author", {"author", "paths"})
    identity = _text(payload["author"], "Contributing author identity", 128)
    paths = _strings(payload["paths"], "Contributing author paths")
    if not set(paths) <= set(context["paths"]):
        raise ReviewError("Contributing author paths must belong to the declared review scope.")
    authors = context["review_authors"]
    combined = sorted(set(authors.get(identity, [])) | set(paths))
    if combined == authors.get(identity):
        return {"registered": identity, "paths": combined, "unchanged": True}
    state["review_authors"] = dict(sorted({**authors, identity: combined}.items()))
    state["review"] = None
    state["finished"] = None
    return {"registered": identity, "paths": combined, "unchanged": False}


def start(root: Path, state: dict[str, Any], *, policy_path: Path | None = None,
          path_validator: Callable[[Path, str], Any] | None = None,
          quick_code_reason: str | None = None, continuation: dict[str, Any] | None = None) -> dict[str, Any]:
    if continuation is not None:
        _object(continuation, "Review continuation", {"reason", "next_action"})
        continuation = {key: _text(continuation[key], f"Continuation {key}", 1000)
                        for key in ("reason", "next_action")}
    context = prepare(root, state, policy_path=policy_path, path_validator=path_validator,
                      _quick_code_reason=quick_code_reason)
    if not context["enabled"]:
        if quick_code_reason is not None or continuation is not None:
            raise ReviewError("Review declarations require an enabled independent review policy.")
        return context
    ledger = state.get("review_gate")
    declaration = None
    if quick_code_reason is not None:
        reason = _text(quick_code_reason, "Quick code reason", 1000)
        if ledger is not None:
            previous = ledger.get("quick_code_declaration")
            if previous is None:
                raise ReviewError("Declare Quick code before the first review round; an active task cannot be downgraded.")
            if (reason != previous["reason"] or not context.get("quick_code_current")
                    or not ledger.get("rounds") or ledger["rounds"][0]["token"] != context["token"]):
                raise ReviewError("Quick code declaration cannot be changed or replayed for a different review snapshot.")
        else:
            declaration = context["quick_code_declaration"]
    author = _author(state)
    for path, artifact in context["artifacts"].items():
        if (path in context["deletions"]) != (artifact is None):
            raise ReviewError(f"Complete the declared artifact or deletion before review: {path}")
    if ledger is None:
        ledger = {"schema_version": 2, "policy_sha256": context["policy_sha256"],
                  "policy_floor": context["policy_floor"], "mode_floor": context["mode"],
                  "author": author, "rounds": [], "findings": {}}
        if declaration is not None:
            ledger["quick_code_declaration"] = declaration
    else:
        ledger = _ledger(state, context, allow_policy_change=True)
    if ledger["author"] != author:
        raise ReviewError("Task author identity changed during independent review.")
    if ledger["rounds"] and ledger["rounds"][-1]["token"] == context["token"]:
        return {**context, "round": ledger["rounds"][-1]["number"], "unchanged": True}
    if context["budget"]["status"] == "exhausted":
        raise ReviewError("Declared review budget deadline is exhausted; record an explicit budget decision before a new round.")
    adaptation = context["adaptation"]
    if adaptation["continuation_required"] and continuation is None:
        raise ReviewError("Repeated review artifacts without a new independent observation require continuation reason and next_action.")
    decision = None
    if continuation is not None:
        decision = {**continuation, "cycle_key": adaptation["cycle_key"],
                    "basis_key": adaptation["independent_basis"]}
        if any(revision.get("continuation") == decision for revision in ledger["rounds"]):
            raise ReviewError("Review continuation replay: this exact cycle, independent basis and declaration were already used.")
    # Admission is transactional, including invalidated resolution statuses.
    ledger = deepcopy(ledger)
    stale_resolutions = []
    for finding in ledger["findings"].values():
        if finding["status"] != "open":
            resolution = finding["resolution"]
            if (resolution["artifact"] != context["artifacts"].get(finding["path"])
                    or finding["path"] in context["review_authors"].get(resolution["verifier"], [])
                    or resolution.get("review_context_sha256") != context.get("review_context_sha256")):
                finding["status"] = "open"
                stale_resolutions.append(finding["id"])
    number = len(ledger["rounds"]) + 1
    ledger.update(schema_version=2, policy_sha256=context["policy_sha256"], policy_floor=context["policy_floor"], mode_floor=context["mode"])
    revision = {"number": number, "token": context["token"], "mode": context["mode"], "reports": {},
                "artifact_fingerprint": adaptation["artifact_fingerprint"],
                "independent_basis": adaptation["independent_basis"],
                "stale_resolutions": sorted(stale_resolutions)}
    if decision is not None:
        revision["continuation"] = decision
    ledger["rounds"].append(revision)
    state["review_gate"] = ledger
    state["review"] = None
    state["finished"] = None
    return {**context, "round": number, "unchanged": False}


def _finding(value: Any, paths: list[str]) -> dict[str, Any]:
    required = {"id", "path", "line", "severity", "origin", "scenario", "consequence", "evidence"}
    _object(value, "Finding", required)
    finding = {key: _text(value[key], f"Finding {key}", 96 if key == "id" else 12000)
               for key in required - {"line", "path"}}
    _text(value["path"], "Finding path", 1000)
    finding["path"] = value["path"]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]*", finding["id"]):
        raise ReviewError("Finding ID must be a stable identifier containing letters, numbers, dots, colons, underscores or dashes.")
    finding["line"] = _integer(value["line"], "Finding line", high=10000000)
    if finding["path"] not in paths:
        raise ReviewError("Finding path must be a declared review artifact.")
    if finding["severity"] not in SEVERITIES:
        raise ReviewError("Finding severity must describe an actionable bug; style and nit findings are excluded.")
    if finding["origin"] not in {"introduced", "preexisting"}:
        raise ReviewError("Finding origin must be introduced or preexisting.")
    return finding


def report(root: Path, state: dict[str, Any], payload: dict[str, Any], *, policy_path: Path | None = None,
           path_validator: Callable[[Path, str], Any] | None = None) -> dict[str, Any]:
    context = prepare(root, state, policy_path=policy_path, path_validator=path_validator)
    if not context["enabled"]:
        raise ReviewError("Independent review policy is not enabled for this repository.")
    ledger, current = _current(state, context)
    _object(payload, "Review report", {"token", "reviewer", "role", "focus", "paths", "summary", "evidence", "findings"})
    reviewer = _text(payload["reviewer"], "Reviewer identity", 128)
    if reviewer == _author(state) or ledger["author"] != _author(state):
        raise ReviewError("Independent reviewer must differ from the frozen task author.")
    if payload["token"] != context["token"]:
        raise ReviewError("Report revision token is stale.")
    if payload["role"] != "reviewer":
        raise ReviewError("Review report role must be reviewer.")
    focus = _strings(payload["focus"], "Review focus")
    if set(focus) - FOCUS:
        raise ReviewError("Unsupported review focus.")
    paths = _strings(payload["paths"], "Reviewed paths", empty=not context["paths"])
    if not set(paths) <= set(context["paths"]):
        raise ReviewError("Reviewed paths must belong to this review's declared scope.")
    if set(paths) & set(context["review_authors"].get(reviewer, [])):
        raise ReviewError("An independent reviewer cannot review artifacts they contributed to.")
    if not isinstance(payload["findings"], list):
        raise ReviewError("Report findings must be a list.")
    findings = [_finding(value, paths) for value in payload["findings"]]
    if len({finding["id"] for finding in findings}) != len(findings):
        raise ReviewError("A report cannot duplicate finding IDs.")
    normalized = {"token": context["token"], "reviewer": reviewer, "role": "reviewer",
                  "focus": sorted(focus), "paths": sorted(paths),
                  "summary": _text(payload["summary"], "Review summary"),
                  "evidence": _text(payload["evidence"], "Review evidence"), "findings": findings}
    existing_report = current["reports"].get(reviewer)
    if existing_report is not None:
        if existing_report != normalized:
            raise ReviewError("A reviewer already submitted a different report for this revision.")
        return {"accepted": True, "unchanged": True, "round": current["number"]}
    for finding in findings:
        existing = ledger["findings"].get(finding["id"])
        if existing and (existing["path"] != finding["path"] or existing["origin"] != finding["origin"]):
            raise ReviewError("A stable finding ID cannot be reassigned to another path or origin.")
        if existing and existing["status"] != "open":
            raise ReviewError("Do not repeat a resolved finding; use a new ID for a distinct regression.")
        if existing and any(existing[key] != value for key, value in finding.items() if key != "line"):
            raise ReviewError("A stable finding ID cannot have conflicting semantic content.")
        if (existing and existing["line"] != finding["line"]
                and existing.get("last_token", existing["first_token"]) == context["token"]):
            raise ReviewError("A stable finding's line can move only in a new review revision.")
    # Validate the entire payload before changing state: malformed reports cannot
    # leave partial findings or consume a reviewer slot.
    for finding in findings:
        existing = ledger["findings"].get(finding["id"])
        if existing:
            existing["discoverers"] = sorted(set(existing["discoverers"]) | {reviewer})
            # Relocations across revisions preserve the issue identity; within a
            # revision, every discoverer must agree on its canonical definition.
            existing.update(line=finding["line"], last_token=context["token"])
        else:
            ledger["findings"][finding["id"]] = {**finding, "discoverers": [reviewer],
                                                     "status": "open", "first_token": context["token"],
                                                     "last_token": context["token"],
                                                     "resolution": None, "resolutions": []}
    current["reports"][reviewer] = normalized
    state["review"] = None
    state["finished"] = None
    return {"accepted": True, "unchanged": False, "round": current["number"], "findings": len(findings)}


def resolve(root: Path, state: dict[str, Any], payload: dict[str, Any], *, policy_path: Path | None = None,
           path_validator: Callable[[Path, str], Any] | None = None) -> dict[str, Any]:
    context = prepare(root, state, policy_path=policy_path, path_validator=path_validator)
    if not context["enabled"]:
        raise ReviewError("Independent review policy is not enabled for this repository.")
    ledger, current = _current(state, context)
    _object(payload, "Finding resolution", {"token", "id", "verifier", "disposition", "evidence"})
    if payload["token"] != context["token"]:
        raise ReviewError("Resolution revision token is stale.")
    identifier = _text(payload["id"], "Finding ID", 96)
    finding = ledger["findings"].get(identifier)
    if finding is None:
        raise ReviewError("Cannot resolve an unknown finding.")
    verifier = _text(payload["verifier"], "Verifier identity", 128)
    if verifier in finding["discoverers"] or verifier == _author(state) or ledger["author"] != _author(state):
        raise ReviewError("Resolution needs a verifier distinct from the author and every finding discoverer.")
    if finding["path"] in context["review_authors"].get(verifier, []):
        raise ReviewError("A contributing author cannot independently resolve a finding on their artifact.")
    if payload["disposition"] not in {"fixed", "dismissed"}:
        raise ReviewError("Resolution disposition must be fixed or dismissed.")
    evidence = _text(payload["evidence"], "Resolution evidence")
    resolution = {"token": context["token"], "verifier": verifier, "disposition": payload["disposition"],
                  "evidence": evidence, "artifact": context["artifacts"].get(finding["path"]), "round": current["number"]}
    if "review_context_sha256" in context:
        resolution["review_context_sha256"] = context["review_context_sha256"]
    if finding["status"] != "open":
        if finding["resolution"] == resolution:
            return {"resolved": identifier, "unchanged": True}
        raise ReviewError("Finding already has a different resolution.")
    finding["status"] = payload["disposition"]
    finding["resolution"] = resolution
    finding["resolutions"].append(resolution)
    state["review"] = None
    state["finished"] = None
    return {"resolved": identifier, "unchanged": False}


def validate(root: Path, state: dict[str, Any], *, policy_path: Path | None = None,
          path_validator: Callable[[Path, str], Any] | None = None) -> None:
    context = prepare(root, state, policy_path=policy_path, path_validator=path_validator)
    if not context["enabled"]:
        return
    ledger, current = _current(state, context)
    if ledger["author"] != _author(state):
        raise ReviewError("Task author identity changed during independent review.")
    reports = current["reports"]
    if len(reports) < context["required_reviewers"]:
        raise ReviewError(f"Independent {context['mode']} review needs {context['required_reviewers']} distinct reviewers.")
    for focus, required in context["required_focus"].items():
        if sum(focus in item["focus"] for item in reports.values()) < required:
            raise ReviewError(f"Independent review needs {required} distinct reviewers with {focus} focus.")
        covered_focus = {path for item in reports.values() if focus in item["focus"] for path in item["paths"]}
        if covered_focus != set(context["paths"]):
            raise ReviewError(f"Independent {focus} reports do not cover every declared review artifact.")
        insufficient = sorted(path for path in context["paths"]
                              if sum(focus in item["focus"] and path in item["paths"]
                                     for item in reports.values()) < required)
        if insufficient:
            raise ReviewError(f"Independent {focus} review needs {required} distinct reviewers per artifact: {', '.join(insufficient)}")
    covered = {path for item in reports.values() for path in item["paths"]}
    if covered != set(context["paths"]):
        raise ReviewError("Independent reports do not cover every declared review artifact.")
    insufficient = sorted(path for path in context["paths"]
                          if sum(path in item["paths"] for item in reports.values()) < context["required_reviewers"])
    if insufficient:
        raise ReviewError(f"Independent {context['mode']} review needs {context['required_reviewers']} distinct reviewers per artifact: {', '.join(insufficient)}")
    opened = sorted(identifier for identifier, finding in ledger["findings"].items() if finding["status"] == "open")
    if opened:
        raise ReviewError(f"Unresolved independent review findings: {', '.join(opened)}")

"""Select the installed review policy for an explicitly bound vault.

The Git owner remains a caller-selected project. Ownership is never derived from
the installation directory, the event payload, or executable project files.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from pathlib import Path
import subprocess
from typing import Any, Iterator

from ..runtime import review_gate as _SHARED

DEFAULT_POLICY = Path(__file__).with_name("review-policy.json")
_PROJECT_ROOT: ContextVar[Path | None] = ContextVar("vault_project_root", default=None)


@contextmanager
def selected_project(root: Path) -> Iterator[None]:
    """Apply vault rules only to this owner for the lifetime of one invocation."""
    token = _PROJECT_ROOT.set(root.resolve(strict=True))
    try:
        yield
    finally:
        _PROJECT_ROOT.reset(token)


ReviewError = _SHARED.ReviewError
MODES, FOCUS, SEVERITIES = _SHARED.MODES, _SHARED.FOCUS, _SHARED.SEVERITIES
_read_json, _validated_policy = _SHARED._read_json, _SHARED._validated_policy


def policy_for(root: Path, *, policy_path: Path | None = None) -> dict[str, Any] | None:
    """Apply this local engine only to its owning vault; tests may inject policy.

    Independent repositories retain their own controls. Removing or corrupting
    the installed policy fails closed, without a registry or hub dependency.
    """
    root = root.resolve()
    if policy_path is not None:
        return _validated_policy(_read_json(Path(policy_path), "review policy"))
    installed = _PROJECT_ROOT.get()
    if root != installed:
        return None
    try:
        actual = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=root,
                                capture_output=True, text=True, timeout=25, check=True)
    except (OSError, subprocess.SubprocessError):
        raise ReviewError("Cannot verify the native vault owner.") from None
    if Path(actual.stdout.strip()).resolve() != root:
        raise ReviewError("The native vault path is not its actual Git repository root.")
    return _validated_policy(_read_json(DEFAULT_POLICY, "review policy"))


def _path(root: Path, name: str) -> Path:
    from .workflow import private_path

    if private_path(name):
        raise ReviewError(f"Invalid or private review path: {name}")
    return _SHARED._path(root, name)


def _current_ledger(state: dict[str, Any]) -> dict[str, Any]:
    """Translate the old vault *record*, leaving the original intact on failure.

    Old rounds, findings, authors and all effective coverage minima survive
    migration. The retired round cap governed admission only. Current configuration
    must always pass the installed schema-2 policy validator.
    """
    ledger = state.get("review_gate")
    if not isinstance(ledger, dict) or type(ledger.get("schema_version")) is not int or ledger["schema_version"] != 1:
        return state
    floor = ledger.get("policy_floor")
    if (not isinstance(floor, dict) or type(floor.get("schema_version")) is not int
            or floor["schema_version"] != 1 or type(floor.get("max_rounds")) is not int
            or not 1 <= floor["max_rounds"] <= 10 or ledger.get("mode_floor") not in MODES
            or ledger.get("author") != state.get("author") or not isinstance(ledger.get("rounds"), list)
            or not isinstance(ledger.get("findings"), dict)):
        raise ReviewError("Unrecognized historical vault ledger; preserve the record for explicit recovery.")
    converted_floor = {key: value for key, value in floor.items() if key != "max_rounds"}
    converted_floor["schema_version"] = 2
    current = {**deepcopy(ledger), "schema_version": 2,
               "policy_floor": _validated_policy(converted_floor)}
    return {**state, "review_gate": current}


def _invoke(operation: str, root: Path, state: dict[str, Any], *args: Any,
            policy_path: Path | None = None, **kwargs: Any) -> Any:
    if policy_for(root, policy_path=policy_path) is None:
        if state.get("review_gate"):
            raise ReviewError("An active review cannot be disabled by changing repository registration.")
        if operation in {"prepare", "start"}:
            return {"enabled": False}
        if operation == "validate":
            return None
        raise ReviewError("Independent review policy is not enabled for this repository.")
    selected = Path(policy_path) if policy_path is not None else DEFAULT_POLICY
    # Validate vault-specific privacy rules before the shared engine observes any artifacts.
    current_names = list(state["paths"]) if isinstance(state.get("paths"), list) else []
    deletions = state["deletions"] if isinstance(state.get("deletions"), list) else []
    names = list(current_names)
    if isinstance(state.get("review_authors"), dict):
        for entries in state["review_authors"].values():
            if isinstance(entries, list):
                names.extend(entries)
    for name in names:
        if isinstance(name, str):
            target = _path(root.resolve(), name)
            if target.is_symlink() and name in current_names and name not in deletions:
                raise ReviewError(f"Review artifact must be a regular file: {name}")
    function = getattr(_SHARED, operation)
    working = _current_ledger(state)
    result = function(root, working, *args, policy_path=selected, path_validator=_path, **kwargs)
    if working is not state and operation not in {"prepare", "validate"}:
        state.update(working)
    return result


def prepare(root: Path, state: dict[str, Any], *, policy_path: Path | None = None) -> dict[str, Any]:
    return _invoke("prepare", root, state, policy_path=policy_path)


def author(root: Path, state: dict[str, Any], payload: dict[str, Any], *, policy_path: Path | None = None) -> dict[str, Any]:
    return _invoke("author", root, state, payload, policy_path=policy_path)


def start(root: Path, state: dict[str, Any], *, policy_path: Path | None = None,
          continuation: dict[str, Any] | None = None,
          quick_code_reason: str | None = None) -> dict[str, Any]:
    if quick_code_reason is not None:
        raise ReviewError("The vault profile does not permit reducing review for code.")
    return _invoke("start", root, state, policy_path=policy_path, continuation=continuation)


def budget(root: Path, state: dict[str, Any], payload: dict[str, Any], *,
           policy_path: Path | None = None) -> dict[str, Any]:
    return _invoke("budget", root, state, payload, policy_path=policy_path)


def report(root: Path, state: dict[str, Any], payload: dict[str, Any], *, policy_path: Path | None = None) -> dict[str, Any]:
    return _invoke("report", root, state, payload, policy_path=policy_path)


def resolve(root: Path, state: dict[str, Any], payload: dict[str, Any], *, policy_path: Path | None = None) -> dict[str, Any]:
    return _invoke("resolve", root, state, payload, policy_path=policy_path)


def validate(root: Path, state: dict[str, Any], *, policy_path: Path | None = None) -> None:
    _invoke("validate", root, state, policy_path=policy_path)

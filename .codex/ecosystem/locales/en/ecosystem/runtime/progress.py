"""Curated progress values shared by task adapters and the local journal receiver.

Adapters own persistence, locks, source-root identity and permissions. This module
never reads source contents or writes a vault. Narrative evidence and a local
receipt grant no authority to checks, reviews, publication or task completion.
Text validation constrains the document format; it is not a universal secret
scanner. Callers must curate information within the authorised trust domain.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any
from urllib.parse import unquote, urlsplit
import uuid


class ProgressError(ValueError):
    """A malformed, conflicting or unauthorised progress operation."""


DASHBOARD_PATH = "17_Dashboards/Constellation.md"
_LIST_FIELDS = ("objectives", "completed", "decisions", "findings", "verification",
                "unresolved", "next_steps")
_VISIBILITY = {"unknown", "personal", "restricted"}
_MAX_MILESTONES = 256
_HASH = re.compile(r"[a-f0-9]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}\Z")
_ALIAS = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?\Z")


def _keys(value: Any, required: set[str], optional: set[str] = frozenset()) -> None:
    if not isinstance(value, dict) or set(value) - required - optional or required - set(value):
        raise ProgressError("Progress fields do not match the supported schema.")


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _timestamp(value: str | None = None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
    if not isinstance(value, str):
        raise ProgressError("Progress timestamps must be timezone-aware ISO dates.")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ProgressError("Invalid progress timestamp.") from error
    if result.tzinfo is None or result.utcoffset() is None:
        raise ProgressError("Progress timestamps must include a timezone.")
    try:
        return result.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
    except (OverflowError, ValueError) as error:
        raise ProgressError("Progress timestamp is outside the supported UTC date range.") from error


def _identifier(value: Any, *, task: bool = False) -> str:
    if task:
        try:
            valid = isinstance(value, str) and str(uuid.UUID(value)) == value
        except (ValueError, AttributeError):
            valid = False
    else:
        valid = isinstance(value, str) and _ID.fullmatch(value) is not None
    if not valid:
        raise ProgressError("Invalid stable progress identifier.")
    return value


def _stored_timestamp(value: Any) -> str:
    if not isinstance(value, str):
        raise ProgressError("Stored progress timestamps must be explicit strings.")
    return _timestamp(value)


def _alias(value: Any) -> str:
    if not isinstance(value, str) or not _ALIAS.fullmatch(value):
        raise ProgressError("Source alias must be a lowercase ASCII slug.")
    return value


def _text(value: Any, *, limit: int = 1200) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ProgressError("Curated progress text must be nonempty and bounded.")
    if (any(ord(character) < 32 or ord(character) == 127 for character in value)
            or any(marker in value for marker in ("<", ">", "[[", "]]", "```", "~~~"))
            or re.search(r"(?:[a-z][a-z0-9+.-]*://|javascript:|data:)", value, re.I)):
        raise ProgressError("Use single-line plain text and typed references, not embedded markup or URLs.")
    return value


def _reference(value: Any) -> dict[str, str]:
    _keys(value, {"kind", "label", "value"})
    kind = value["kind"]
    if not isinstance(kind, str) or kind not in {"repository", "commit", "experiment", "documentation"}:
        raise ProgressError("Unknown curated reference type.")
    label = _text(value["label"], limit=160)
    target = value["value"]
    if not isinstance(target, str) or not target or len(target) > 1000:
        raise ProgressError("Invalid curated reference value.")
    if any(ord(character) < 33 or ord(character) > 126 for character in target):
        raise ProgressError("References must use printable ASCII without whitespace.")
    if any(character in target for character in "<>[]`\\\"'"):
        raise ProgressError("Unsafe reference syntax.")
    if kind == "commit":
        if not re.fullmatch(r"[a-fA-F0-9]{7,64}", target):
            raise ProgressError("Commit references require a hexadecimal object ID.")
    elif ":" in target:
        try:
            parsed = urlsplit(target)
            host = parsed.hostname
            port = parsed.port
        except ValueError as error:
            raise ProgressError("Invalid reference URL.") from error
        decoded = unquote(target)
        if (parsed.scheme != "https" or not host or parsed.username is not None
                or parsed.password is not None or parsed.query or parsed.fragment
                or port not in (None, 443) or not re.fullmatch(r"[a-zA-Z0-9.-]+", host)
                or any(character in decoded for character in "<>[]`\\\"'?#@")
                or any(ord(character) < 33 or ord(character) == 127 for character in decoded)
                or "%" in decoded
                or re.search(r"(?:token|secret|password|api[-_]?key|sk-)[=/:-]", decoded, re.I)):
            raise ProgressError("Reference URLs must be HTTPS without credentials, queries or fragments.")
    else:
        path = PurePosixPath(target)
        if (path.is_absolute() or ".." in path.parts or target.startswith("~")
                or any(part in {".git", "sessions", "logs", "archives", "auth.json", "credentials.json", ".env"}
                       for part in path.parts)
                or (".codex" in path.parts and any(part in {"memories", "learning"} for part in path.parts))
                or any(character in target for character in "?#@:%")):
            raise ProgressError("Reference paths must be safe relative identifiers.")
    return {"kind": kind, "label": label, "value": target}


def _snapshot(value: Any) -> dict[str, Any]:
    _keys(value, set(_LIST_FIELDS) | {"current", "references"})
    result: dict[str, Any] = {"current": _text(value["current"])}
    for name in _LIST_FIELDS:
        items = value[name]
        if not isinstance(items, list) or len(items) > 32 or (name == "objectives" and not items):
            raise ProgressError("Progress sections must be bounded lists; objectives cannot be empty.")
        result[name] = [_text(item) for item in items]
    refs = value["references"]
    if not isinstance(refs, list) or len(refs) > 32:
        raise ProgressError("Progress references must be a bounded list.")
    result["references"] = [_reference(item) for item in refs]
    return result


def _payload(value: Any) -> dict[str, Any]:
    _keys(value, {"id", "summary", "snapshot"}, {"visibility"})
    visibility = value.get("visibility", "unknown")
    if not isinstance(visibility, str) or visibility not in _VISIBILITY:
        raise ProgressError("Unknown progress visibility.")
    return {"id": _identifier(value["id"]), "summary": _text(value["summary"]),
            "visibility": visibility, "snapshot": _snapshot(value["snapshot"])}


def create_progress(objective: str, *, source_alias: str, created_at: str | None = None,
                    task_uid: str | None = None) -> dict[str, Any]:
    """Initialise once; the caller persists the UUID independently of a session ID."""
    return {"schema_version": 1, "task_uid": _identifier(task_uid if task_uid is not None else str(uuid.uuid4()), task=True),
            "source_alias": _alias(source_alias), "created_at": _timestamp(created_at),
            "objective": _text(objective), "milestones": [], "receipt": None}


def validate_progress(progress: Any) -> dict[str, Any]:
    """Validate loaded state without consulting a vault, model or session."""
    _keys(progress, {"schema_version", "task_uid", "source_alias", "created_at", "objective",
                     "milestones", "receipt"})
    if type(progress["schema_version"]) is not int or progress["schema_version"] != 1:
        raise ProgressError("Unsupported progress schema.")
    result = create_progress(progress["objective"], source_alias=progress["source_alias"],
                             created_at=_stored_timestamp(progress["created_at"]),
                             task_uid=_identifier(progress["task_uid"], task=True))
    milestones = progress["milestones"]
    if not isinstance(milestones, list) or len(milestones) > _MAX_MILESTONES:
        raise ProgressError("Progress history is not a bounded milestone list.")
    seen: set[str] = set()
    previous = result["created_at"]
    for milestone in milestones:
        _keys(milestone, {"id", "summary", "visibility", "snapshot", "at", "content_hash"})
        item = _payload({key: milestone[key] for key in ("id", "summary", "visibility", "snapshot")})
        at = _stored_timestamp(milestone["at"])
        if item["id"] in seen or at < previous or milestone["content_hash"] != _hash(item):
            raise ProgressError("Milestone identity, chronology or content hash is invalid.")
        result["milestones"].append({**item, "at": at, "content_hash": _hash(item)})
        seen.add(item["id"])
        previous = at
    receipt = progress["receipt"]
    if receipt is not None:
        _keys(receipt, {"status", "task_uid", "content_hash", "target_root_hash", "note_path", "at"})
        if receipt["status"] != "RECEIVED_LOCAL" or not isinstance(receipt["content_hash"], str) \
                or not _HASH.fullmatch(receipt["content_hash"]) \
                or receipt["task_uid"] != result["task_uid"] \
                or not isinstance(receipt["target_root_hash"], str) \
                or not _HASH.fullmatch(receipt["target_root_hash"]) \
                or receipt["note_path"] != _note_path(result["created_at"], result["source_alias"], result["task_uid"]):
            raise ProgressError("Progress receipts attest local reception only.")
        result["receipt"] = {**receipt, "at": _stored_timestamp(receipt["at"])}
        if result["receipt"]["at"] < result["created_at"]:
            raise ProgressError("Stored reception cannot precede task creation.")
    return result


def checkpoint(progress: dict[str, Any], payload: dict[str, Any], *,
               at: str | None = None) -> dict[str, Any]:
    """Append one full curated snapshot; a repeated ID never rewinds later work."""
    result = validate_progress(progress)
    item = _payload(payload)
    content_hash = _hash(item)
    for previous in result["milestones"]:
        if previous["id"] == item["id"]:
            if previous["content_hash"] != content_hash:
                raise ProgressError("Milestone ID already has different content; add a correction milestone.")
            return result
    if len(result["milestones"]) >= _MAX_MILESTONES:
        raise ProgressError("Milestone limit reached; curate a follow-up task rather than collecting execution logs.")
    when = _timestamp(at)
    previous_at = result["milestones"][-1]["at"] if result["milestones"] else result["created_at"]
    if when < previous_at:
        raise ProgressError("Milestones must be chronological.")
    result["milestones"].append({**item, "at": when, "content_hash": content_hash})
    return result


def target_root_hash(root: Path) -> str:
    """Bind a local destination without exposing its absolute path in a note."""
    path = Path(root)
    if not path.is_absolute() or path != path.resolve():
        raise ProgressError("Journal target must be a canonical absolute path without symlinks.")
    return _hash({"root": str(path)})


def validate_policy(policy: Any, *, source_root: Path, source_alias: str) -> None:
    """Require exact, separate local authorisation; project registration is irrelevant.

    The adapter supplies the real source root. Resolving metadata here reads no
    source contents. Matching a parent root never authorises a nested project.
    """
    _keys(policy, {"schema_version", "sources", "target"})
    if type(policy["schema_version"]) is not int or policy["schema_version"] != 1:
        raise ProgressError("Unsupported local export policy schema.")
    alias = _alias(source_alias)
    _keys(policy["target"], {"root"})
    if not isinstance(policy["target"]["root"], str):
        raise ProgressError("Journal target root must be an absolute path string.")
    target_root_hash(Path(policy["target"]["root"]))
    root = Path(source_root)
    if not root.is_absolute() or not root.is_dir() or root != root.resolve():
        raise ProgressError("The trusted source root must be an existing canonical absolute directory.")
    sources = policy["sources"]
    if not isinstance(sources, list) or len(sources) > 256:
        raise ProgressError("Local export policy must contain a bounded source list.")
    authorised = False
    roots: set[str] = set()
    aliases: set[str] = set()
    for entry in sources:
        _keys(entry, {"root", "alias", "visibility"})
        if (not isinstance(entry["root"], str) or not Path(entry["root"]).is_absolute()
                or str(Path(entry["root"])) != entry["root"]):
            raise ProgressError("Export policy roots must be exact absolute paths.")
        item_alias = _alias(entry["alias"])
        if not isinstance(entry["visibility"], str) or entry["visibility"] not in _VISIBILITY:
            raise ProgressError("Invalid source-policy visibility.")
        if entry["root"] in roots or item_alias in aliases:
            raise ProgressError("Export policy roots and aliases must be unique.")
        roots.add(entry["root"])
        aliases.add(item_alias)
        if entry["root"] == str(root) and item_alias == alias and entry["visibility"] == "personal":
            authorised = True
    if not authorised:
        raise ProgressError("Source root has no exact personal export authorisation in local policy.")


def _note_path(created_at: str, alias: str, task_uid: str) -> str:
    return (f"11_Documents_and_Reports/Execution_Traces/{created_at[:10]}/"
            f"constellation_{alias}_{task_uid}.md")


def _envelope(progress: dict[str, Any], *, target_hash: str, workflow_finished: bool) -> dict[str, Any]:
    milestones = progress["milestones"]
    if not milestones or milestones[-1]["visibility"] != "personal":
        raise ProgressError("The latest checkpoint must explicitly be personal before export.")
    if type(workflow_finished) is not bool:
        raise ProgressError("Workflow closure must be a trusted adapter-derived boolean.")
    result = {"schema_version": 1, "task_uid": progress["task_uid"],
              "source_alias": progress["source_alias"], "created_at": progress["created_at"],
              "target_root_hash": target_hash, "workflow_finished": workflow_finished,
              "note_path": _note_path(progress["created_at"], progress["source_alias"], progress["task_uid"]),
              "snapshot": deepcopy(milestones[-1]["snapshot"]),
              "milestones": [{key: deepcopy(item[key]) for key in ("id", "at", "summary", "content_hash")}
                             for item in milestones if item["visibility"] == "personal"]}
    result["content_hash"] = _hash(result)
    return result


def export_envelope(progress: dict[str, Any], *, source_root: Path,
                    policy: dict[str, Any], workflow_finished: bool = False) -> dict[str, Any]:
    """Return a deterministic curated envelope, without writing any destination."""
    state = validate_progress(progress)
    validate_policy(policy, source_root=source_root, source_alias=state["source_alias"])
    return _envelope(state, target_hash=target_root_hash(Path(policy["target"]["root"])),
                     workflow_finished=workflow_finished)


def validate_envelope(envelope: Any) -> dict[str, Any]:
    _keys(envelope, {"schema_version", "task_uid", "source_alias", "created_at", "note_path",
                     "snapshot", "milestones", "content_hash", "target_root_hash", "workflow_finished"})
    if type(envelope["schema_version"]) is not int or envelope["schema_version"] != 1:
        raise ProgressError("Unsupported journal envelope schema.")
    uid = _identifier(envelope["task_uid"], task=True)
    alias = _alias(envelope["source_alias"])
    created = _stored_timestamp(envelope["created_at"])
    if not isinstance(envelope["target_root_hash"], str) or not _HASH.fullmatch(envelope["target_root_hash"]) \
            or type(envelope["workflow_finished"]) is not bool:
        raise ProgressError("Invalid target binding or workflow closure indicator.")
    if envelope["note_path"] != _note_path(created, alias, uid):
        raise ProgressError("Journal note path must be anchored to task identity and creation day.")
    result = {"schema_version": 1, "task_uid": uid, "source_alias": alias, "created_at": created,
              "target_root_hash": envelope["target_root_hash"], "workflow_finished": envelope["workflow_finished"],
              "note_path": envelope["note_path"], "snapshot": _snapshot(envelope["snapshot"]), "milestones": []}
    if not isinstance(envelope["milestones"], list) or not 1 <= len(envelope["milestones"]) <= _MAX_MILESTONES:
        raise ProgressError("Journal envelope requires bounded personal milestones.")
    seen: set[str] = set()
    previous = created
    for item in envelope["milestones"]:
        _keys(item, {"id", "at", "summary", "content_hash"})
        identifier = _identifier(item["id"])
        at = _stored_timestamp(item["at"])
        if identifier in seen or at < previous or not isinstance(item["content_hash"], str) \
                or not _HASH.fullmatch(item["content_hash"]):
            raise ProgressError("Invalid exported milestone identity, chronology or hash.")
        result["milestones"].append({"id": identifier, "at": at, "summary": _text(item["summary"]),
                                     "content_hash": item["content_hash"]})
        previous = at
        seen.add(identifier)
    if envelope["content_hash"] != _hash(result):
        raise ProgressError("Journal envelope content hash does not match.")
    return {**result, "content_hash": envelope["content_hash"]}


def acknowledge(progress: dict[str, Any], *, envelope: dict[str, Any],
                receipt: dict[str, Any]) -> dict[str, Any]:
    """Record only local reception of this exact task's current curated snapshot."""
    result = validate_progress(progress)
    current = validate_envelope(envelope)
    expected = _envelope(result, target_hash=current["target_root_hash"],
                         workflow_finished=current["workflow_finished"])
    _keys(receipt, {"status", "task_uid", "content_hash", "target_root_hash", "note_path", "at"})
    bindings = ("task_uid", "content_hash", "target_root_hash", "note_path")
    if current != expected or receipt["status"] != "RECEIVED_LOCAL" \
            or any(receipt[key] != expected[key] for key in bindings):
        raise ProgressError("Receipt does not match the task's current curated envelope.")
    when = _stored_timestamp(receipt["at"])
    if when < result["milestones"][-1]["at"]:
        raise ProgressError("Reception cannot precede the acknowledged checkpoint.")
    if result["receipt"] is not None and result["receipt"]["content_hash"] == current["content_hash"]:
        return result
    result["receipt"] = {**receipt, "at": when}
    return result


def _escape(value: str) -> str:
    return re.sub(r"([\\`*_{}\[\]()#+.!|~-])", r"\\\1", value)


def _managed(body: str, identity: str, existing: str | None) -> str:
    """Keep a single generated prefix and preserve the unmanaged tail verbatim."""
    digest = hashlib.sha256(body.encode()).hexdigest()
    header_end = body.index("\n---\n", 4) + len("\n---\n")
    header, managed = body[:header_end], body[header_end:]
    prefix = header + f"<!-- constellation-progress:{identity}:sha256={digest} -->\n"
    end = f"<!-- /constellation-progress:{identity} -->"
    generated = prefix + managed + end
    tail = "\n\n## Personal notes\n"
    if existing is not None:
        pattern = (rf"\A(---\n(?:(?!\n---\n).)*\n---\n)"
                   rf"<!-- constellation-progress:{re.escape(identity)}:sha256=([a-f0-9]{{64}}) -->\n")
        match = re.match(pattern, existing, re.S)
        if not match or existing.count(end) != 1 or existing.count("<!-- constellation-progress:") != 1:
            raise ProgressError("Existing note is foreign or has ambiguous managed markers.")
        stop = existing.index(end, match.end())
        prior_body = match.group(1) + existing[match.end():stop]
        if hashlib.sha256(prior_body.encode()).hexdigest() != match.group(2):
            raise ProgressError("Managed journal content was edited; reconcile it before synchronising.")
        tail = existing[stop + len(end):]
    return generated + tail


def _frontmatter(title: str, note_type: str, domain: str, created: str, updated: str,
                 *, task_uid: str | None = None, workflow_finished: bool = False) -> str:
    fields: dict[str, Any] = {"title": title, "note_type": note_type, "domain": domain,
              "subdomain": "Constellation" if note_type == "dashboard" else "Execution_Traces",
              "tags": ["constellation", "progress"],
              "status": "active" if note_type == "dashboard" else ("completed" if workflow_finished else "in_progress"),
              "created": created[:10], "updated": updated[:10], "author": "Omar"}
    if task_uid:
        fields["task_id"] = task_uid
    return "---\n" + "\n".join(f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in fields.items()) + "\n---\n\n"


def render_note(envelope: dict[str, Any], existing: str | None = None) -> str:
    """Render curated text; a receipt deliberately makes no publication claim."""
    item = validate_envelope(envelope)
    snap = item["snapshot"]
    title = f"Constellation — {item['source_alias']}"
    body = _frontmatter(title, "execution_trace", "11_Documents_and_Reports", item["created_at"],
                        item["milestones"][-1]["at"], task_uid=item["task_uid"],
                        workflow_finished=item["workflow_finished"])
    body += f"# {_escape(title)}\n\n"
    body += "Local receipt of curated progress; receipt does not establish publication or workflow completion.\n\n"
    if item["workflow_finished"]:
        body += "The source adapter attests to its workflow closure; this does not by itself prove scientific conclusions.\n\n"
    body += f"Task: {item['task_uid']}\n\nAuthorized source: {_escape(item['source_alias'])}\n\n"
    headings = {"objectives": "Objectives", "current": "Current state", "completed": "Completed work",
                "decisions": "Decisions", "findings": "Findings", "verification": "Declared evidence",
                "unresolved": "Unresolved issues", "next_steps": "Next steps"}
    for name, title in headings.items():
        body += f"## {title}\n\n"
        values = [snap[name]] if name == "current" else snap[name]
        body += "\n".join(f"- {_escape(value)}" for value in values) if values else "No entries."
        body += "\n\n"
    body += "## References\n\n"
    body += "\n".join(f"- {_escape(ref['label'])} ({ref['kind']}): {_escape(ref['value'])}"
                       for ref in snap["references"]) or "No references."
    body += "\n\n## Milestones\n\n"
    body += "\n".join(f"- {entry['at']} · {_escape(entry['id'])}: {_escape(entry['summary'])}"
                       for entry in item["milestones"])
    body += "\n\n"
    return _managed(body, item["task_uid"], existing)


def dashboard_entry(envelope: dict[str, Any]) -> dict[str, Any]:
    """Keep only display metadata in the receiver index, not a second task store."""
    item = validate_envelope(envelope)
    return {key: item[key] for key in ("task_uid", "source_alias", "note_path", "created_at",
                                       "target_root_hash", "workflow_finished", "content_hash")} | {
        "updated_at": item["milestones"][-1]["at"], "current": item["snapshot"]["current"]}


def _dashboard_entry(entry: Any) -> dict[str, Any]:
    _keys(entry, {"task_uid", "source_alias", "note_path", "created_at", "updated_at", "current",
                 "target_root_hash", "workflow_finished", "content_hash"})
    uid = _identifier(entry["task_uid"], task=True)
    alias = _alias(entry["source_alias"])
    created = _stored_timestamp(entry["created_at"])
    updated = _stored_timestamp(entry["updated_at"])
    if entry["note_path"] != _note_path(created, alias, uid) or updated < created \
            or type(entry["workflow_finished"]) is not bool:
        raise ProgressError("Dashboard entry has invalid identity, chronology or workflow state.")
    for field in ("target_root_hash", "content_hash"):
        if not isinstance(entry[field], str) or not _HASH.fullmatch(entry[field]):
            raise ProgressError("Dashboard entry has an invalid hash.")
    return {**entry, "created_at": created, "updated_at": updated, "current": _text(entry["current"])}


def render_dashboard(entries: list[dict[str, Any]], existing: str | None = None) -> str:
    """Render the receiver's bounded task index; it is not operational task state."""
    if not isinstance(entries, list) or len(entries) > 1000:
        raise ProgressError("Dashboard entries must be a bounded list.")
    items = sorted((_dashboard_entry(entry) for entry in entries),
                   key=lambda item: (item["updated_at"], item["task_uid"]), reverse=True)
    if len({item["task_uid"] for item in items}) != len(items):
        raise ProgressError("Dashboard task identities must be unique.")
    if len({item["target_root_hash"] for item in items}) > 1:
        raise ProgressError("Dashboard entries must belong to one authorised destination.")
    created = min((item["created_at"] for item in items), default="1970-01-01")
    updated = max((item["updated_at"] for item in items), default=created)
    body = _frontmatter("Constellation", "dashboard", "17_Dashboards", created, updated)
    body += "# Constellation\n\nProgress received locally; sources retain operational state and publication responsibility.\n\n"
    for item in items:
        relative = "../" + item["note_path"]
        status = "workflow closed" if item["workflow_finished"] else "in progress"
        body += f"- [{item['source_alias']} · {item['task_uid']}]({relative}) ({status}): {_escape(item['current'])}\n"
    body += "\n"
    return _managed(body, "dashboard", existing)

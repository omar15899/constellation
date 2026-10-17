#!/usr/bin/env python3
"""Check and apply an explicit concurrency policy to native Codex profiles.

Only the bounded concurrency assignment is managed. The writer never renders
the rest of a TOML document, changes user model/permission settings, or creates
a clone. Writes require the existing workspace lifecycle's declared scope.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any, Iterator

from workflow import Blocked, now
from workspace import Workspace, relative

KEY = "max_concurrent_threads_per_session"
BEGIN = "# BEGIN constellation managed agent policy"
END = "# END constellation managed agent policy"
CONFIG = ".codex/config.toml"


def _unique_object(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            raise Blocked(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Blocked(f"Cannot read valid JSON from {path.name}: {type(exc).__name__}") from None


def _settings(value: Any, label: str) -> int:
    if not isinstance(value, dict) or set(value) != {KEY}:
        raise Blocked(f"{label} must contain only {KEY}.")
    count = value[KEY]
    if type(count) is not int or not 1 <= count <= 2147483647:
        raise Blocked(f"{label}.{KEY} must be a positive 32-bit integer, excluding booleans.")
    return count


def load_policy(workspace: Workspace) -> dict[str, Any]:
    path = workspace._target(".codex/agent-policy.json")
    if not path.is_file():
        raise Blocked("A regular .codex/agent-policy.json is required.")
    data = _json(path)
    if (not isinstance(data, dict) or set(data) != {"schema_version", "defaults", "repositories"}
            or type(data["schema_version"]) is not int or data["schema_version"] != 1):
        raise Blocked("agent-policy.json requires schema_version 1, defaults and repositories only.")
    _settings(data["defaults"], "defaults")
    overrides = data["repositories"]
    if not isinstance(overrides, dict):
        raise Blocked("repositories must map registered native repository paths to settings.")
    for name, settings in overrides.items():
        if relative(name, root=True) != name or workspace.repositories.get(name) != "native":
            raise Blocked(f"Policy overrides require an exact registered native repository: {name}")
        _settings(settings, f"repositories[{name}]")
    return data


def effective_limit(policy: dict[str, Any], repository: str) -> int:
    return policy["repositories"].get(repository, policy["defaults"])[KEY]


def _statements(source: str) -> Iterator[tuple[int, int, str]]:
    """Read TOML statement boundaries without altering strings or comments.

    This is a conservative structural reader, not a general TOML parser. It
    keeps multiline string/array contents from impersonating keys or tables.
    On Python 3.11+ tomllib additionally validates the complete document.
    """
    start = 0
    index = 0
    quote = ""
    multiline = False
    depth: list[str] = []
    cleaned = list(source)
    while index < len(source):
        char = source[index]
        if quote:
            if quote == '"' and char == "\\":
                index += 2
                continue
            if char == quote:
                if multiline:
                    run = len(source[index:]) - len(source[index:].lstrip(quote))
                    if run >= 3:
                        if run > 5:
                            raise Blocked("Ambiguous TOML quote sequence; repair config before applying policy.")
                        quote = ""
                        index += run
                        continue
                else:
                    quote = ""
            elif char == "\n" and not multiline:
                raise Blocked("Invalid multiline TOML string; repair config before applying policy.")
        elif char in "\"'":
            quote = char
            multiline = source.startswith(char * 3, index)
            if multiline:
                index += 3
                continue
        elif char == "#":
            end = source.find("\n", index)
            end = len(source) if end == -1 else end
            cleaned[index:end] = " " * (end - index)
            index = end
            continue
        elif char in "[{":
            depth.append(char)
        elif char in "]}":
            if not depth or depth.pop() != {"}": "{", "]": "["}[char]:
                raise Blocked("Unbalanced TOML delimiters; repair config before applying policy.")
        if char == "\n" and not quote and not depth:
            yield start, index + 1, "".join(cleaned[start:index + 1]).strip()
            start = index + 1
        index += 1
    if quote or depth:
        raise Blocked("Unterminated TOML value; repair config before applying policy.")
    if start < len(source):
        yield start, len(source), "".join(cleaned[start:]).strip()


def _key_parts(source: str) -> tuple[str, ...]:
    # Escaped quoted keys are uncommon and easy to misinterpret without a full
    # parser on Python 3.9. Reject them instead of risking a hidden duplicate.
    pattern = r'''\s*(?:([A-Za-z0-9_-]+)|"([^"\\\r\n]*)"|'([^'\r\n]*)')\s*'''
    parts = []
    offset = 0
    while True:
        match = re.match(pattern, source[offset:])
        if not match:
            raise Blocked("Unsupported TOML key spelling; use unescaped keys before applying policy.")
        parts.append(next(value for value in match.groups() if value is not None))
        offset += match.end()
        if offset == len(source):
            return tuple(parts)
        if source[offset] != ".":
            raise Blocked("Invalid TOML key; repair config before applying policy.")
        offset += 1


def _assignment(source: str) -> tuple[tuple[str, ...], str]:
    quote = ""
    for index, char in enumerate(source):
        if quote:
            if char == quote:
                quote = ""
        elif char in "\"'":
            quote = char
        elif char == "=":
            return _key_parts(source[:index]), source[index + 1:].strip()
    raise Blocked("Expected a TOML assignment; repair config before applying policy.")


def _validate_toml(source: str) -> None:
    try:
        import tomllib
    except ImportError:
        return
    try:
        tomllib.loads(source)
    except tomllib.TOMLDecodeError:
        raise Blocked("Invalid TOML config; repair it before applying policy.") from None


def render_config(source: str, limit: int) -> str:
    """Insert/update a bounded assignment while preserving all other text."""
    _settings({KEY: limit}, "limit")
    _validate_toml(source)
    statements = list(_statements(source))
    markers = []
    for start, end, clean in statements:
        raw = source[start:end].strip()
        if not clean and raw in {BEGIN, END}:
            markers.append((raw, start, end))
    if markers:
        if len(markers) != 2 or [item[0] for item in markers] != [BEGIN, END]:
            raise Blocked("Managed policy markers are duplicated or incomplete.")
        begin, end = markers
        active_table = ()
        for start, _, clean in statements:
            if start >= begin[1]:
                break
            if clean.startswith("["):
                if clean.startswith("[["):
                    active_table = _key_parts(clean[2:-2].strip()) + ("[]",)
                else:
                    active_table = _key_parts(clean[1:-1].strip())
        if active_table != ("agents",):
            raise Blocked("Managed policy block must belong to the ordinary [agents] table.")
        inside = source[begin[2]:end[1]]
        if not re.fullmatch(r"\s*" + KEY + r"\s*=\s*[1-9][0-9]*\s*", inside):
            raise Blocked("Managed policy block contains unexpected content; preserve and reconcile it manually.")
        # Keep the table header outside the block: later user additions below
        # the marker must retain their original table when the block changes.
        source = source[:begin[1]] + source[end[2]:]
        statements = list(_statements(source))

    table: tuple[str, ...] = ()
    agent_table_end = None
    dotted_agents = False
    seen_tables: set[tuple[str, ...]] = set()
    for start, end, clean in statements:
        if not clean:
            continue
        if clean.startswith("["):
            array = clean.startswith("[[")
            width = 2 if array else 1
            if not clean.endswith("]" * width):
                raise Blocked("Unsupported TOML table declaration.")
            table = _key_parts(clean[width:-width].strip())
            if table[:2] in {("agents", KEY), ("agents", "max_threads")}:
                raise Blocked("Agent concurrency must be a scalar, not an unmanaged TOML table.")
            if table == ("agents",):
                if array or table in seen_tables:
                    raise Blocked("The agents setting must be one ordinary TOML table.")
                agent_table_end = end
            seen_tables.add(table)
            continue
        key, _ = _assignment(clean)
        full = table + key
        if full[:1] == ("agents",):
            if full[:2] in {("agents", KEY), ("agents", "max_threads")}:
                raise Blocked("Unmanaged agent concurrency setting exists (including legacy max_threads); reconcile it explicitly.")
            if full == ("agents",):
                raise Blocked("Inline agents tables are not edited automatically; use a regular [agents] table.")
            if not table:
                dotted_agents = True

    newline = "\r\n" if "\r\n" in source else "\n"
    if agent_table_end is not None:
        offset = agent_table_end
        key = KEY
        prefix = "" if source[:offset].endswith(("\n", "\r")) else newline
    elif dotted_agents:
        # A dotted-key-created table cannot be redeclared as [agents].
        raise Blocked("Dotted agents settings require a regular [agents] table before policy management.")
    else:
        offset = len(source)
        prefix = ("" if not source or source.endswith("\n") else newline)
        if source and not source.endswith(newline * 2):
            prefix += newline
        prefix += "[agents]" + newline
        key = KEY
    block = newline.join((BEGIN, f"{key} = {limit}", END, ""))
    result = source[:offset] + prefix + block + source[offset:]
    _validate_toml(result)
    return result


class AgentPolicy:
    def __init__(self, root: Path, session: str):
        self.workspace = Workspace(root, session)
        self.policy = load_policy(self.workspace)

    def select(self, names: list[str] | None, *, applying: bool = False) -> tuple[list[str], list[str]]:
        if applying and not names:
            raise Blocked("apply requires explicit --repo selections; no repository is selected implicitly.")
        selected = names if names is not None else [name for name, management in self.workspace.repositories.items()
                                                   if management == "native"]
        if not selected or len(set(selected)) != len(selected):
            raise Blocked("Select a nonempty list of unique repositories.")
        present, missing = [], []
        for name in selected:
            if relative(name, root=True) != name or self.workspace.repositories.get(name) != "native":
                raise Blocked(f"Only exact registered native repositories may be selected: {name}")
            root = self.workspace._target(name)
            if not root.exists():
                if names is not None:
                    raise Blocked(f"Selected repository is not cloned: {name}")
                missing.append(name)
                continue
            if not root.is_dir() or self.workspace.route_one(name)["repository"] != name:
                raise Blocked(f"Registered repository does not own its Git root: {name}")
            prefix = "" if name == "." else name + "/"
            profile = self.workspace._target(prefix + ".codex/profile.json")
            data = _json(profile)
            if not isinstance(data, dict) or data.get("mode") != "native":
                raise Blocked(f"Native profile marker missing for {name}.")
            present.append(name)
        return present, missing

    def _candidate(self, name: str) -> tuple[Path, bytes | None, bytes]:
        prefix = "" if name == "." else name + "/"
        route = self.workspace.route_one(prefix + CONFIG, file=True)
        if route["repository"] != name:
            raise Blocked(f"Config Git ownership changed for {name}.")
        path = self.workspace._target(prefix + CONFIG)
        if not path.parent.is_dir():
            raise Blocked(f"Native profile directory missing for {name}.")
        original = path.read_bytes() if path.exists() else None
        try:
            source = original.decode("utf-8") if original is not None else ""
        except UnicodeError:
            raise Blocked(f"Config must use UTF-8: {name}") from None
        rendered = render_config(source, effective_limit(self.policy, name)).encode("utf-8")
        return path, original, rendered

    def inspect(self, names: list[str] | None = None) -> dict[str, Any]:
        selected, missing = self.select(names)
        repositories = []
        for name in selected:
            path, original, rendered = self._candidate(name)
            repositories.append({"repository": name, "config": path.relative_to(self.workspace.root).as_posix(),
                                 KEY: effective_limit(self.policy, name), "matches": original == rendered})
        return {"schema_version": 1, "primary_agent_included": False, "repositories": repositories,
                "skipped_missing": missing, "matches": all(item["matches"] for item in repositories)}

    def apply(self, names: list[str] | None) -> dict[str, Any]:
        selected, _ = self.select(names, applying=True)
        workspace = self.workspace
        with workspace.lock():
            state = workspace.load()
            with workspace.flows(state["roots"]) as flows:
                workspace.validate(state, flows)
                candidates = []
                # No target is changed until every config and contract passes.
                for name in selected:
                    if name not in flows:
                        raise Blocked(f"Repository is outside the workspace plan: {name}")
                    path, original, rendered = self._candidate(name)
                    action = "Add File" if original is None else "Update File"
                    flows[name].guard_patch({"tool_input": f"*** {action}: {CONFIG}\n"}, flows[name].root)
                    candidates.append((name, path, original, rendered))
                changed = []
                for name, path, original, rendered in candidates:
                    if original == rendered:
                        continue
                    # Recheck symlinks/ownership and bytes immediately before
                    # replacement. Repository locks coordinate native writers.
                    current_path, current, current_rendered = self._candidate(name)
                    if current_path != path or current != original or current_rendered != rendered:
                        raise Blocked(f"Config changed during policy application: {name}; rerun after reconciling it.")
                    mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
                    temporary = None
                    try:
                        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".agent-policy-", delete=False) as stream:
                            temporary = Path(stream.name)
                            stream.write(rendered)
                            stream.flush()
                            os.fsync(stream.fileno())
                        temporary.chmod(mode)
                        temporary.replace(path)
                    finally:
                        if temporary is not None:
                            temporary.unlink(missing_ok=True)
                    changed.append(name)
                state["finished"] = None
                workspace.save(state)
        return {"applied": changed, "unchanged": [name for name in selected if name not in changed],
                "reload_required": bool(changed), "at": now()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--session", default=os.environ.get("CODEX_THREAD_ID", "manual"))
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("show", "check", "apply"):
        command = sub.add_parser(name)
        command.add_argument("--repo", action="append", help="exact repository path from repositories.json; repeat to select several")
    args = parser.parse_args()
    try:
        policy = AgentPolicy(args.root, args.session)
        result = policy.apply(args.repo) if args.command == "apply" else policy.inspect(args.repo)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 1 if args.command == "check" and not result["matches"] else 0
    except (Blocked, OSError, ValueError) as exc:
        print(f"Blocked: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

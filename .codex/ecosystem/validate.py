#!/usr/bin/env python3
"""Structural checks for this portable package, using Python 3.11+ only.

SKILL.md frontmatter is deliberately restricted to two JSON-quoted strings:
name and description. UI metadata accepts a JSON object or a two-space-indented
YAML mapping with JSON-quoted strings and booleans. This is not a general YAML
parser and does not certify semantic quality, safe arbitrary code, or discovery
by a particular Codex client. Use skill-creator's official checker separately.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
from typing import Iterable
from urllib.parse import unquote, urlsplit

try:
    import tomllib
except ModuleNotFoundError:  # Give older system Python an actionable diagnostic.
    tomllib = None  # type: ignore[assignment]


# The candidate selected by --root is data. Load layout code only from the
# trusted package containing this validator, without consulting sys.path.
_LAYOUT_SPEC = importlib.util.spec_from_file_location(
    "constellation_validator_layout", Path(__file__).resolve().with_name("build.py")
)
if _LAYOUT_SPEC is None or _LAYOUT_SPEC.loader is None:
    raise RuntimeError("The trusted package layout could not be loaded")
_LAYOUT = importlib.util.module_from_spec(_LAYOUT_SPEC)
# Validation must not add bytecode files to the package it is checking. Keep
# this loader read-only without changing the caller's policy for later imports.
_ORIGINAL_BYTECODE_POLICY = sys.dont_write_bytecode
try:
    sys.dont_write_bytecode = True
    _LAYOUT_SPEC.loader.exec_module(_LAYOUT)
finally:
    sys.dont_write_bytecode = _ORIGINAL_BYTECODE_POLICY
MODULES = _LAYOUT.MODULES
MODULE_AGENTS = _LAYOUT.MODULE_AGENTS
COMMON_FILES = _LAYOUT.COMMON_FILES
HOOK_EVENTS = ("UserPromptSubmit", "PreToolUse", "SubagentStart", "SubagentStop", "Stop")
PRE_TOOL_MATCHER = r"^(?:[A-Za-z0-9_]+[.:])*(?:apply_patch|Edit|Write)$"
CLAUDE_EVENTS = ("SessionStart", *HOOK_EVENTS)
_PRIVATE_NAMES = {
    ".git", ".env", "auth.json", "credentials.json", "secrets.json", "id_rsa",
    "id_ed25519", "sessions", "transcripts", "conversations", "archives", "logs",
    "rollout", "rollouts", "sync-state.json", "sync_state.json",
}


def _object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate mapping key")
        result[key] = value
    return result


def _json(text: str) -> object:
    return json.loads(text, object_pairs_hook=_object)


def _mapping(text: str) -> dict[str, object]:
    """Read the package's small documented metadata format, not arbitrary YAML."""
    if text.lstrip().startswith("{"):
        value = _json(text)
        if not isinstance(value, dict):
            raise ValueError("expected mapping")
        return value
    root: dict[str, object] = {}
    stack: list[tuple[int, dict[str, object]]] = [(-2, root)]
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(r"( *)([a-z][a-z_]*):(?: (.*))?", line)
        if not match or len(match[1]) % 2:
            raise ValueError("expected two-space mappings with quoted string or boolean values")
        indent, key, raw = len(match[1]), match[2], match[3]
        while stack[-1][0] >= indent:
            stack.pop()
        if indent != stack[-1][0] + 2:
            raise ValueError("invalid mapping indentation")
        parent = stack[-1][1]
        if key in parent:
            raise ValueError("duplicate mapping key")
        if raw is None:
            child: dict[str, object] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            value = _json(raw)
            if not isinstance(value, (str, bool)):
                raise ValueError("metadata scalars must be quoted strings or booleans")
            parent[key] = value
    return root


def _private(path: Path) -> bool:
    return any(
        part.lower() in _PRIVATE_NAMES
        or part.lower().startswith((".env.", "rollout-", "transcript-", "conversation-"))
        or part.lower().endswith((".jsonl", ".log", ".pem", ".key", ".p12"))
        for part in path.parts
    )


def _required_files(modules: Iterable[str], manifest: str) -> list[str]:
    required = _LAYOUT.allowed_files(modules)
    if manifest != _LAYOUT.PLUGIN_MANIFEST:
        required = {_LAYOUT.source_path(relative) for relative in required}
    return sorted(required)


class _Validator:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.errors: list[str] = []

    def error(self, path: str | Path, message: str) -> None:
        self.errors.append(f"{path}: {message}")

    def path(self, relative: str | Path, *, directory_ok: bool = False) -> Path | None:
        """Check containment and links before opening any package resource."""
        rel = Path(relative)
        if rel.is_absolute() or _private(rel):
            self.error(relative, "external or private resource is forbidden")
            return None
        current = self.root
        for part in rel.parts:
            if not current.is_dir():
                self.error(relative, "resource parent must be an existing directory")
                return None
            if part == "..":
                if current == self.root:
                    self.error(relative, "resource escapes the package root")
                    return None
                current = current.parent
            else:
                current = current / part
            if _LAYOUT._PLATFORM.is_reparse(current):
                self.error(relative, "symlinks and reparse points are forbidden")
                return None
        resolved = current.resolve()
        if not resolved.is_relative_to(self.root):
            self.error(relative, "resource escapes the package root")
            return None
        if _LAYOUT._PLATFORM.IS_WINDOWS:
            try:
                _LAYOUT._PLATFORM.validate_windows_relative(resolved.relative_to(self.root).as_posix())
            except _LAYOUT._PLATFORM.PlatformError:
                self.error(relative, "Windows resource has an ambiguous or reserved path")
                return None
        if directory_ok and resolved.is_dir():
            return resolved
        if not resolved.is_file():
            self.error(relative, "required regular file is missing")
            return None
        if not stat.S_ISREG(resolved.stat().st_mode):
            self.error(relative, "resource must be a regular file")
            return None
        return resolved

    def read(self, relative: str | Path) -> str | None:
        path = self.path(relative)
        if path is None:
            return None
        try:
            if path.stat().st_size > 2_000_000:
                self.error(relative, "text resource exceeds the package size limit")
                return None
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            self.error(relative, "resource is unreadable UTF-8")
            return None

    def json(self, relative: str | Path) -> dict[str, object] | None:
        text = self.read(relative)
        if text is None:
            return None
        try:
            data = _json(text)
            if not isinstance(data, dict):
                raise ValueError("expected mapping")
            return data
        except (ValueError, RecursionError):
            self.error(relative, "invalid JSON object or duplicate keys")
            return None

    def scan(self, relative: str | Path) -> None:
        """Inspect names without opening private data or following directory links."""
        base = self.root / relative
        if _LAYOUT._PLATFORM.is_reparse(base):
            self.error(relative, "symlinks are forbidden")
            return
        for parent, directories, files in os.walk(base, followlinks=False):
            try:
                _LAYOUT._PLATFORM.verify_access(Path(parent), private=False)
            except _LAYOUT._PLATFORM.PlatformError:
                self.error(Path(parent).relative_to(self.root), "directory access permits untrusted replacement")
            for name in directories[:] + files:
                path = Path(parent) / name
                rel = path.relative_to(self.root)
                if _LAYOUT._PLATFORM.is_reparse(path) or _private(rel):
                    self.error(rel, "symlink or private resource is forbidden")
                    if name in directories:
                        directories.remove(name)

    def links(self, relative: str, text: str) -> None:
        # This package uses inline Markdown links and reference definitions.
        # Ignore code examples so illustrative paths are not treated as resources.
        prose = re.sub(r"(?ms)^\s*(`{3,}|~{3,}).*?^\s*\1\s*$", "", text)
        targets = re.findall(r"\[[^\]\n]*\]\(([^)\n]+)\)", prose)
        targets += re.findall(r"(?m)^ {0,3}\[[^\]\n]+\]:\s*(\S+)", prose)
        for target in targets:
            target = target.strip()
            if target.startswith("<") and ">" in target:
                target = target[1:target.index(">")]
            else:
                target = target.split(' "', 1)[0].split(" '", 1)[0]
            url = urlsplit(target)
            if url.scheme in {"https", "http", "mailto"}:
                continue
            if url.scheme or url.netloc:
                self.error(relative, "unsupported or external local-link scheme")
                continue
            if not url.path:
                continue
            decoded = unquote(url.path)
            if decoded.startswith(("/", "~")) or "\\" in decoded or "\x00" in decoded:
                self.error(relative, "local links must use relative package paths")
                continue
            self.path(Path(relative).parent / decoded, directory_ok=True)

    def skill(self, module: str) -> None:
        relative = f"skills/{module}/SKILL.md"
        content = self.read(relative)
        if content is not None:
            match = re.fullmatch(r"---\n(.*?)\n---(?:\n|$)(.*)", content, re.DOTALL)
            if match is None:
                self.error(relative, "missing or malformed frontmatter")
            else:
                try:
                    data = _mapping(match[1])
                    if set(data) != {"name", "description"}:
                        raise ValueError("frontmatter must contain only name and description")
                    name, description = data["name"], data["description"]
                    if name != module:
                        self.error(relative, "name must exactly match its module directory")
                    if not isinstance(description, str) or not description.strip():
                        self.error(relative, "description must be a non-empty string")
                    elif len(description) > 1024 or "<" in description or ">" in description:
                        self.error(relative, "description exceeds supported length or contains angle brackets")
                    if not match[2].strip():
                        self.error(relative, "instruction body must not be empty")
                except (ValueError, RecursionError):
                    self.error(relative, "frontmatter requires only JSON-quoted name and description strings")
                self.links(relative, match[2])
        ui_path = f"skills/{module}/agents/openai.yaml"
        ui_text = self.read(ui_path)
        if ui_text is None:
            return
        try:
            ui = _mapping(ui_text)
        except (ValueError, RecursionError):
            self.error(ui_path, "unsupported metadata format; use quoted-string mappings or JSON")
            return
        if not set(ui) <= {"interface", "policy"}:
            self.error(ui_path, "unsupported metadata fields for this package")
        interface = ui.get("interface")
        if not isinstance(interface, dict):
            self.error(ui_path, "interface must be a mapping")
            return
        fields = {"display_name", "short_description", "default_prompt", "icon_small", "icon_large", "brand_color"}
        if not set(interface) <= fields:
            self.error(ui_path, "unsupported interface field")
        for field in ("display_name", "short_description", "default_prompt"):
            if not isinstance(interface.get(field), str) or not interface[field].strip():
                self.error(ui_path, f"{field} must be a non-empty string")
        short = interface.get("short_description")
        if isinstance(short, str) and not 25 <= len(short) <= 64:
            self.error(ui_path, "short_description must have 25 to 64 characters")
        prompt = interface.get("default_prompt")
        if isinstance(prompt, str) and not re.search(r"\$(?:constellation:)?" + re.escape(module) + r"(?![\w:-])", prompt):
            self.error(ui_path, "default_prompt must mention this skill by its exact $name")
        color = interface.get("brand_color")
        if color is not None and (not isinstance(color, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", color)):
            self.error(ui_path, "brand_color must be a six-digit hex color")
        for field in ("icon_small", "icon_large"):
            if field in interface:
                icon = interface[field]
                if not isinstance(icon, str) or not icon.startswith("./assets/"):
                    self.error(ui_path, f"{field} must refer to a local ./assets/ file")
                else:
                    self.path(Path(f"skills/{module}") / icon)
        if "policy" in ui:
            policy = ui["policy"]
            if not isinstance(policy, dict) or set(policy) != {"allow_implicit_invocation"} or type(policy["allow_implicit_invocation"]) is not bool:
                self.error(ui_path, "policy must contain a boolean allow_implicit_invocation")

    def agent(self, name: str) -> None:
        relative = f"ecosystem/agents/{name}.toml"
        content = self.read(relative)
        if content is None:
            return
        try:
            data = tomllib.loads(content)
        except (ValueError, RecursionError):
            self.error(relative, "invalid TOML")
            return
        if set(data) != {"name", "description", "developer_instructions"}:
            self.error(relative, "only name, description and developer_instructions are permitted; model, effort and permissions must be inherited")
        for field in ("name", "description", "developer_instructions"):
            if not isinstance(data.get(field), str) or not data[field].strip():
                self.error(relative, f"{field} must be a non-empty string")
        if data.get("name") != "ecosystem_" + name.replace("-", "_"):
            self.error(relative, "agent name must match its ecosystem role")

    def manifest(self, relative: str) -> None:
        data = self.json(relative)
        if data is None:
            return
        if set(data) != {"name", "version", "description", "skills", "hooks"}:
            self.error(relative, "unsupported plugin manifest schema")
        expected = {"name": "constellation", "skills": "./skills/", "hooks": "./ecosystem/hooks.json"}
        for field, value in expected.items():
            if data.get(field) != value:
                self.error(relative, f"{field} must equal the package's declared portable value")
        version = data.get("version")
        if not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", version):
            self.error(relative, "version must be a safe non-empty release identifier")
        elif version in {"1.3.0", "1.3.1"}:
            self.error(relative, f"version {version} is reserved for the historical owned layout")
        if "description" in data and (not isinstance(data["description"], str) or not data["description"].strip()):
            self.error(relative, "description must be a non-empty string")

    def claude(self, *, bundled: bool, modules: Iterable[str]) -> None:
        relative = (_LAYOUT.CLAUDE_PLUGIN_MANIFEST if bundled
                    else _LAYOUT.source_path(_LAYOUT.CLAUDE_PLUGIN_MANIFEST))
        metadata = self.json(relative)
        if metadata is not None:
            try:
                _LAYOUT._check_claude_plugin(metadata)
            except ValueError:
                self.error(relative, "invalid native Claude plugin manifest")
            codex = self.json(_LAYOUT.PLUGIN_MANIFEST if bundled else _LAYOUT.source_path(_LAYOUT.PLUGIN_MANIFEST))
            if codex is not None and metadata.get("version") != codex.get("version"):
                self.error(relative, "native plugin versions must agree")
        for resource in sorted(_LAYOUT.allowed_files(modules)):
            if not resource.startswith("agents/") or not resource.endswith(".md"):
                continue
            canonical = self.path(_LAYOUT.source_path(resource))
            if canonical is None:
                continue
            try:
                expected = _LAYOUT.render_claude_agent(canonical.read_bytes())
                if bundled:
                    actual = self.path(resource)
                    if actual is not None and actual.read_bytes() != expected:
                        self.error(resource, "Claude agent must match its canonical role and inherit runtime choices")
            except ValueError:
                self.error(_LAYOUT.source_path(resource), "canonical role cannot produce a native Claude agent")
        relative = "ecosystem/claude-hooks.json" if bundled else _LAYOUT.source_path("ecosystem/claude-hooks.json")
        data = self.json(relative)
        events = data.get("hooks") if data is not None else None
        if not isinstance(events, dict) or set(events) != set(CLAUDE_EVENTS):
            self.error(relative, "Claude hooks require exactly the supported native events")
            return
        try:
            _LAYOUT.claude_hook_target(data)
        except _LAYOUT.BundleError as exc:
            self.error(relative, str(exc))

    def hooks(self, *, bundled: bool) -> None:
        relative = "ecosystem/hooks.json" if bundled else _LAYOUT.source_path("ecosystem/hooks.json")
        data = self.json(relative)
        if data is None:
            return
        events = data.get("hooks")
        if not {"hooks"} <= set(data) <= {"hooks", "description"} or not isinstance(events, dict) or set(events) != set(HOOK_EVENTS):
            self.error(relative, "hook manifest must contain exactly the supported lifecycle events")
            return
        if "description" in data and (not isinstance(data["description"], str) or not data["description"].strip()):
            self.error(relative, "hook description must be a non-empty string")
        for event in HOOK_EVENTS:
            groups = events[event]
            keys = {"hooks", "matcher"} if event == "PreToolUse" else {"hooks"}
            if not isinstance(groups, list) or len(groups) != 1 or not isinstance(groups[0], dict) or set(groups[0]) != keys:
                self.error(relative, f"{event} has an invalid matcher group")
                continue
            group = groups[0]
            if event == "PreToolUse" and group["matcher"] != PRE_TOOL_MATCHER:
                self.error(relative, "PreToolUse matcher differs from the declared package contract")
            hooks = group["hooks"]
            command = f'python3 -I "${{CODEX_HOME:-$HOME/.codex}}/constellation/hook.py" {event}'
            if not isinstance(hooks, list) or len(hooks) != 1 or not isinstance(hooks[0], dict):
                self.error(relative, f"{event} requires exactly one command hook")
            elif hooks[0] != {"type": "command", "command": command, "timeout": 10} or type(hooks[0].get("timeout")) is not int:
                self.error(relative, f"{event} requires the declared isolated Python command and timeout")


def validate(root: Path | str, modules: Iterable[str] | None = None) -> list[str]:
    """Return structural errors; an empty list is success. Never run candidate code."""
    if tomllib is None:
        return ["Python 3.11 or newer is required (stdlib tomllib)"]
    root = Path(root).expanduser()
    if _LAYOUT._PLATFORM.IS_WINDOWS:
        try:
            root = _LAYOUT._PLATFORM.validate_lookup(root)
        except _LAYOUT._PLATFORM.PlatformError:
            return ["package root must use an unambiguous local path without reparse points"]
    root = root.absolute()
    if _LAYOUT._PLATFORM.is_reparse(root) or not root.is_dir():
        return ["package root must be an existing directory, not a symlink"]
    root = root.resolve()
    validator = _Validator(root)
    if isinstance(modules, str):
        return ["modules must be an iterable of module names, not a single string"]
    try:
        selected = list(modules) if modules is not None else [name for name in MODULES if (root / "skills" / name).exists()]
    except TypeError:
        return ["modules must be an iterable of module names"]
    if not selected or any(name not in MODULES for name in selected) or len(selected) != len(set(selected)):
        return ["modules must be a non-empty unique selection of: " + ", ".join(MODULES)]
    bundled = (root / ".codex-plugin").exists()
    manifest = _LAYOUT.PLUGIN_MANIFEST if bundled else _LAYOUT.source_path(_LAYOUT.PLUGIN_MANIFEST)
    required = _required_files(selected, manifest)
    agents = [Path(path).stem for path in required if path.startswith("ecosystem/agents/") and path.endswith(".toml")]
    try:
        if bundled:
            validator.scan(".")
        else:
            for module in selected:
                validator.scan(f"skills/{module}")
            for directory in ("ecosystem/agents", "ecosystem/references", "ecosystem/evals", "ecosystem/tests", "ecosystem/runtime", "ecosystem/manifests", "ecosystem/docs"):
                validator.scan(directory)
        for relative in required:
            validator.path(relative)
        validator.manifest(manifest)
        validator.claude(bundled=bundled, modules=selected)
        validator.hooks(bundled=bundled)
        for module in selected:
            validator.skill(module)
        for name in agents:
            validator.agent(name)
        for relative in required:
            if relative.endswith(".md") and not relative.endswith("SKILL.md"):
                content = validator.read(relative)
                if content is not None:
                    if not content.strip():
                        validator.error(relative, "document must not be empty")
                    validator.links(relative, content)
        if bundled:
            inventory = validator.json("bundle.json")
            if inventory is not None:
                if set(inventory) != {"schema", "modules", "files"} or type(inventory.get("schema")) is not int or inventory["schema"] != 1:
                    validator.error("bundle.json", "unsupported inventory schema")
                inventory_modules = inventory.get("modules")
                valid_modules = isinstance(inventory_modules, list) and bool(inventory_modules) and all(isinstance(name, str) and name in MODULES for name in inventory_modules)
                valid_modules = valid_modules and len(inventory_modules) == len(set(inventory_modules)) and set(selected) <= set(inventory_modules)
                if not valid_modules:
                    validator.error("bundle.json", "inventory modules do not cover the selected modules")
                files = inventory.get("files")
                if not isinstance(files, dict):
                    validator.error("bundle.json", "files must be an object")
                else:
                    if not set(required) <= set(files):
                        validator.error("bundle.json", "inventory omits required package resources")
                    permitted = set(_required_files(inventory_modules, manifest)) if valid_modules else set(required)
                    if valid_modules and set(files) != permitted:
                        validator.error("bundle.json", "inventory differs from the declared package resources")
                    actual = {
                        (Path(parent) / name).relative_to(root).as_posix()
                        for parent, _, names in os.walk(root, followlinks=False) for name in names
                    }
                    if actual != set(files) | {"bundle.json"}:
                        validator.error("bundle.json", "package files differ from the inventory")
                    for relative, record in files.items():
                        if not isinstance(relative, str) or str(PurePosixPath(relative)) != relative or ".." in PurePosixPath(relative).parts:
                            validator.error("bundle.json", "inventory paths must be normalized relative paths")
                            continue
                        if relative not in permitted:
                            validator.error("bundle.json", "inventory contains a resource outside the package allowlist")
                            continue
                        path = validator.path(relative)
                        if not isinstance(record, dict) or set(record) != {"sha256", "mode"}:
                            validator.error("bundle.json", "invalid resource record")
                        elif path is not None:
                            if hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
                                validator.error(relative, "inventory digest mismatch")
                            if record["mode"] not in (0o644, 0o755):
                                validator.error(relative, "inventory permission mode must be 0644 or 0755")
                            else:
                                try:
                                    if _LAYOUT._PLATFORM.logical_mode(path, expected=record["mode"]) != record["mode"]:
                                        validator.error(relative, "inventory permission mode mismatch")
                                except _LAYOUT._PLATFORM.PlatformError:
                                    validator.error(relative, "inventory access permissions are unsafe")
            bootstrap_path = validator.path("ecosystem/claude_hooks.py")
            support_path = validator.path("ecosystem/platform_support.py")
            if bootstrap_path is not None and support_path is not None:
                try:
                    bootstrap = bootstrap_path.read_bytes()
                    if _LAYOUT.render_claude_bootstrap(bootstrap, support_path.read_bytes()) != bootstrap:
                        validator.error("ecosystem/claude_hooks.py", "bootstrap differs from canonical platform support")
                except _LAYOUT.BundleError as exc:
                    validator.error("ecosystem/claude_hooks.py", str(exc))
    except (OSError, ValueError, RecursionError) as exc:
        validator.error("package", f"validation could not complete ({type(exc).__name__})")
    return list(dict.fromkeys(validator.errors))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1], help="source .codex directory or built package root")
    parser.add_argument("--modules", nargs="+", choices=MODULES, help="validate selected available modules (default: all present)")
    args = parser.parse_args(argv)
    errors = validate(args.root, args.modules)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("Package structure is valid; semantic quality and native discovery require separate evidence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

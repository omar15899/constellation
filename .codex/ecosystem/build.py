#!/usr/bin/env python3
"""Build a deterministic, explicitly allowlisted Constellation bundle."""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
from itertools import combinations
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import tomllib
from typing import Iterable
import zipfile
from types import ModuleType


def _load_platform() -> ModuleType:
    """Load only this trusted builder's sibling, never a candidate-root module."""
    if __package__:
        from . import platform_support
        return platform_support
    spec = importlib.util.spec_from_file_location(
        "constellation_build_platform", Path(__file__).resolve().with_name("platform_support.py"))
    if spec is None or spec.loader is None:
        raise RuntimeError("The trusted platform support module is unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    bytecode = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = bytecode
    return module


_PLATFORM = _load_platform()
TARGETS = ("posix", "windows-claude")

MODULES = ("coding", "mathematics", "quant-research", "writter")
BUNDLE_MANIFEST = "bundle.json"
PLUGIN_MANIFEST = ".codex-plugin/plugin.json"
CLAUDE_PLUGIN_MANIFEST = ".claude-plugin/plugin.json"
INSTALL_RECEIPT = ".constellation-install.json"
CLAUDE_FILES = (
    "ecosystem/claude.py", "ecosystem/claude_hooks.py", "ecosystem/claude-hooks.json",
    "ecosystem/tests/test_claude_install.py", "ecosystem/tests/test_claude_hooks.py",
    "ecosystem/tests/test_claude_package.py",
    "ecosystem/tests/native_claude_probe.py",
)
COMMON_FILES = (
    *CLAUDE_FILES,
    "ecosystem/platform_support.py", "ecosystem/docs/windows.md",
    "ecosystem/tests/test_platform_support.py", "ecosystem/tests/test_windows_claude.py",
    "ecosystem/tests/windows_acceptance.py",
    *(f"ecosystem/runtime/{name}.py" for name in
      ("__init__", "workflow", "workspace", "dispatch", "review_gate", "agent_policy", "progress")),
    "ecosystem/runtime/review-policy.json",
    *(f"ecosystem/{name}.py" for name in
      ("__init__", "core", "storage", "cli", "hooks", "hook_entry", "build", "install", "native", "validate")),
    "ecosystem/hooks.json", "ecosystem/README.md", "ecosystem/docs/compatibility.md",
    "ecosystem/docs/architecture.md", "ecosystem/docs/migrations.md", "ecosystem/docs/progress.md",
    "ecosystem/requirements-dev.txt", "ecosystem/references/protocol.md",
    "ecosystem/docs/evaluation.md",
    "ecosystem/evals/cases.json", "ecosystem/evals/rubric.json",
    *(f"ecosystem/tests/{name}.py" for name in
      ("helpers", "test_core", "test_hooks", "test_hook_entry", "test_package", "test_validation", "test_capabilities",
       "test_progress", "test_progress_core")),
    *(f"ecosystem/agents/{name}.toml" for name in
      ("researcher", "reviewer", "security-reviewer", "verifier")),
)
MODULE_AGENTS = {
    "coding": ("coder",),
    "mathematics": ("mathematician", "counterexample"),
    "quant-research": ("coder", "mathematician", "counterexample"),
    "writter": ("editor", "mathematician", "coder"),
}


class BundleError(ValueError):
    """A source or bundle violates its explicit packaging contract."""


def select_modules(modules: Iterable[str] | None = None) -> tuple[str, ...]:
    values = list(MODULES if modules is None else modules)
    if not values or any(value not in MODULES for value in values):
        raise BundleError("Select one or more of: " + ", ".join(MODULES))
    if len(values) != len(set(values)):
        raise BundleError("Module selection contains duplicates")
    return tuple(module for module in MODULES if module in values)


def allowed_files(modules: Iterable[str]) -> set[str]:
    selected = select_modules(modules)
    paths = set(COMMON_FILES) | {PLUGIN_MANIFEST, CLAUDE_PLUGIN_MANIFEST}
    for module in selected:
        paths.update(f"skills/{module}/{name}" for name in
                     ("SKILL.md", "agents/openai.yaml", "references/workflow.md"))
        paths.update(f"ecosystem/agents/{name}.toml" for name in MODULE_AGENTS[module])
    if "mathematics" in selected or "writter" in selected:
        paths.update(("ecosystem/references/ontology.md",
                      "ecosystem/references/ontology-examples.md"))
    paths.update(f"agents/{Path(path).stem}.md" for path in tuple(paths)
                 if path.startswith("ecosystem/agents/") and path.endswith(".toml"))
    return paths


_INVENTORY_BEGIN = "# BEGIN CONSTELLATION CURRENT INVENTORY"
_INVENTORY_END = "# END CONSTELLATION CURRENT INVENTORY"


def current_inventory_block() -> str:
    """Project the one current allowlist into self-contained native entries."""
    singles = {module: allowed_files((module,)) for module in MODULES}
    common = set.intersection(*singles.values())
    extras = {module: singles[module] - common for module in MODULES}
    for count in range(1, len(MODULES) + 1):
        for group in combinations(MODULES, count):
            projected = common.union(*(extras[module] for module in group))
            if projected != allowed_files(group):
                raise BundleError("Native inventory projection does not match the current layout")
    lines = [_INVENTORY_BEGIN, "# Generated from build.allowed_files; do not maintain a second inventory.",
             "_CURRENT_COMMON_FILES = frozenset(("]
    lines.extend("    " + json.dumps(path) + "," for path in sorted(common))
    lines.append("))")
    lines.append("_CURRENT_MODULE_FILES = {")
    for module in MODULES:
        lines.append("    " + json.dumps(module) + ": frozenset((")
        lines.extend("        " + json.dumps(path) + "," for path in sorted(extras[module]))
        lines.append("    )),")
    lines.extend(["}", "", "",
                  "def _current_files(modules):",
                  '    """Return the active trusted inventory without importing package code."""',
                  "    if (not isinstance(modules, (list, tuple)) or not modules",
                  "            or not all(isinstance(module, str) for module in modules)",
                  "            or len(set(modules)) != len(modules)",
                  "            or not set(modules) <= set(_CURRENT_MODULE_FILES)):",
                  '        raise ValueError("Invalid current package modules")',
                  "    return set(_CURRENT_COMMON_FILES).union(",
                  "        *(_CURRENT_MODULE_FILES[module] for module in modules))",
                  _INVENTORY_END])
    return "\n".join(lines)


def render_current_inventory(content: bytes) -> bytes:
    """Regenerate only the exact native inventory block; never execute it."""
    try:
        text = content.decode("utf-8")
    except UnicodeError as exc:
        raise BundleError("Native bootstrap must be UTF-8") from exc
    if text.count(_INVENTORY_BEGIN) != 1 or text.count(_INVENTORY_END) != 1:
        raise BundleError("Native bootstrap must contain one current inventory block")
    before, remainder = text.split(_INVENTORY_BEGIN, 1)
    _, after = remainder.split(_INVENTORY_END, 1)
    return (before + current_inventory_block() + after).encode("utf-8")


def translation_files() -> set[str]:
    """Return the complete source-only English inventory, including all modules."""
    paths = {source_path(path) for path in allowed_files(MODULES)
             if Path(path).suffix in {".md", ".toml", ".yaml"}}
    return paths | {"ecosystem/evals/cases.json", "ecosystem/evals/rubric.json",
                    "ecosystem/runtime/progress.py"}


_PROGRESS_TRANSLATABLE = frozenset({
    "Recepción local de progreso curado; la recepción no acredita publicación ni finalización del workflow.\n\n",
    "El adaptador de origen acredita el cierre de su workflow; esto no demuestra por sí solo conclusiones científicas.\n\n",
    "Tarea: ", "\n\nOrigen autorizado: ", "Objetivos", "Estado actual", "Trabajo realizado",
    "Decisiones", "Hallazgos", "Evidencia declarada", "Cuestiones pendientes", "Próximos pasos",
    "Sin entradas.", "## Referencias\n\n", "Sin referencias.", "\n\n## Hitos\n\n",
    "# Constellation\n\nProgreso recibido localmente; las fuentes conservan el estado operativo y la publicación.\n\n",
    "workflow cerrado", "en curso", "\n\n## Notas personales\n",
})


def _check_progress_translation(canonical: bytes, translated: bytes) -> None:
    """Allow only display-string replacements; never execute translated Python."""
    try:
        original = ast.parse(canonical)
        candidate = ast.parse(translated)
    except (SyntaxError, UnicodeError) as exc:
        raise BundleError("Invalid progress renderer translation") from exc
    original_nodes, candidate_nodes = list(ast.walk(original)), list(ast.walk(candidate))
    if len(original_nodes) != len(candidate_nodes):
        raise BundleError("Progress translation changes executable structure")
    for left, right in zip(original_nodes, candidate_nodes):
        if (isinstance(left, ast.Constant) and isinstance(right, ast.Constant)
                and left.value != right.value):
            if (not isinstance(left.value, str) or left.value not in _PROGRESS_TRANSLATABLE
                    or not isinstance(right.value, str) or not right.value.strip()):
                raise BundleError("Progress translation changes a non-display constant")
            right.value = left.value
    if ast.dump(original) != ast.dump(candidate):
        raise BundleError("Progress translation changes executable structure")


def _english_resources(source: Path) -> dict[str, bytes]:
    """Load one fixed, complete translation tree; reject links and extra files."""
    expected = translation_files()
    prefix = "ecosystem/locales/en/"
    # regular_file checks every component, including the locale root, before read.
    resources = {relative: regular_file(source, prefix + relative).read_bytes()
                 for relative in sorted(expected)}
    actual = set()
    for directory, subdirs, files in os.walk(source / "ecosystem/locales/en", followlinks=False):
        for name in subdirs + files:
            if _PLATFORM.is_reparse(Path(directory) / name):
                raise BundleError("English translation contains a symlink or reparse point")
        actual.update((Path(directory) / name).relative_to(source / "ecosystem/locales/en").as_posix()
                      for name in files)
    if actual != expected:
        raise BundleError("English translation inventory differs from the allowlist")
    for relative, content in resources.items():
        try:
            if not content.decode("utf-8").strip():
                raise ValueError("empty translation")
        except (UnicodeError, ValueError) as exc:
            raise BundleError(f"Invalid English text: {relative}") from exc
    progress = "ecosystem/runtime/progress.py"
    _check_progress_translation(regular_file(source, progress).read_bytes(), resources[progress])
    return resources


def source_path(relative: str) -> str:
    """Map a distributed resource to its canonical source, without loading code."""
    if relative == PLUGIN_MANIFEST:
        return "ecosystem/manifests/codex-plugin.json"
    if relative == CLAUDE_PLUGIN_MANIFEST:
        return "ecosystem/manifests/claude-plugin.json"
    if relative == "ecosystem/hooks.json":
        return "ecosystem/manifests/codex-hooks.json"
    if relative == "ecosystem/claude-hooks.json":
        return "ecosystem/manifests/claude-hooks.json"
    path = Path(relative)
    if len(path.parts) == 2 and path.parts[0] == "agents" and path.suffix == ".md":
        return f"ecosystem/agents/{path.stem}.toml"
    return relative


def render_claude_agent(content: bytes) -> bytes:
    """Project native metadata while retaining one canonical instruction body."""
    try:
        agent = tomllib.loads(content.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise BundleError("Invalid canonical agent metadata") from exc
    if (set(agent) != {"name", "description", "developer_instructions"}
            or not all(isinstance(agent.get(key), str) and agent[key].strip() for key in agent)
            or not re.fullmatch(r"ecosystem_[a-z_]+", agent["name"])):
        raise BundleError("Canonical agent must inherit runtime choices and declare its instructions")
    name = agent["name"].replace("_", "-")
    return ("---\nname: " + json.dumps(name) + "\ndescription: "
            + json.dumps(agent["description"], ensure_ascii=False)
            + '\nmodel: "inherit"\n---\n\n' + agent["developer_instructions"].strip()
            + "\n").encode("utf-8")


_PLATFORM_BEGIN = "# BEGIN CONSTELLATION PLATFORM SUPPORT"
_PLATFORM_END = "# END CONSTELLATION PLATFORM SUPPORT"


def render_claude_bootstrap(content: bytes, support: bytes) -> bytes:
    """Embed the one canonical stdlib helper before any package verification.

    The built native entry is self-contained: it cannot import an unverified
    helper from its bundle. Keeping the markers makes rendering idempotent for
    source fixtures reconstructed from a previously built package.
    """
    try:
        text, helper = content.decode("utf-8"), support.decode("utf-8")
    except UnicodeError as exc:
        raise BundleError("Bootstrap and platform support must be UTF-8") from exc
    if text.count(_PLATFORM_BEGIN) != 1 or text.count(_PLATFORM_END) != 1:
        raise BundleError("Claude bootstrap must have one canonical platform block")
    before, remainder = text.split(_PLATFORM_BEGIN, 1)
    _, after = remainder.split(_PLATFORM_END, 1)
    helper = re.sub(r"^from __future__ import annotations\r?\n", "", helper, flags=re.MULTILINE)
    rendered = before + _PLATFORM_BEGIN + "\n" + helper.rstrip() + "\n" + _PLATFORM_END + after
    try:
        tree = ast.parse(rendered)
    except SyntaxError as exc:
        raise BundleError("Rendered Claude bootstrap is invalid Python") from exc
    for node in ast.walk(tree):
        imported = ([node.module or ""] if isinstance(node, ast.ImportFrom) else
                    [alias.name for alias in node.names] if isinstance(node, ast.Import) else [])
        if any(name.rsplit(".", 1)[-1] == "platform_support" for name in imported):
            raise BundleError("Rendered Claude bootstrap may not import an unverified platform helper")
    return rendered.encode("utf-8")


def claude_hook_target(data: dict) -> str:
    """Validate all fixed native exec handlers and return their shared target."""
    events = ("SessionStart", "UserPromptSubmit", "PreToolUse",
              "SubagentStart", "SubagentStop", "Stop")
    if (not isinstance(data, dict) or not {"hooks"} <= set(data) <= {"hooks", "description"}
            or not isinstance(data.get("hooks"), dict) or set(data["hooks"]) != set(events)):
        raise BundleError("Claude hooks require the complete supported event set")
    if "description" in data and (not isinstance(data["description"], str) or not data["description"].strip()):
        raise BundleError("Claude hook description must be nonempty text")
    commands = set()
    for event in events:
        groups = data["hooks"][event]
        keys = {"hooks", "matcher"} if event == "PreToolUse" else {"hooks"}
        if (not isinstance(groups, list) or len(groups) != 1 or not isinstance(groups[0], dict)
                or set(groups[0]) != keys):
            raise BundleError("Claude hooks require exactly one fixed native group")
        group = groups[0]
        if event == "PreToolUse" and group["matcher"] != "^(Write|Edit|MultiEdit|NotebookEdit)$":
            raise BundleError("Claude hook matcher differs from the supported contract")
        hooks = group["hooks"]
        if not isinstance(hooks, list) or len(hooks) != 1 or not isinstance(hooks[0], dict):
            raise BundleError("Claude hooks require exactly one native handler")
        hook = hooks[0]
        command, timeout = hook.get("command"), hook.get("timeout")
        if not isinstance(command, str) or command not in {"python3", "python"}:
            raise BundleError("Claude hook interpreter is not a supported executable")
        native_path = "$" + "{CLAUDE_PLUGIN_ROOT}/ecosystem/claude_hooks.py"
        expected = {"type": "command", "command": command, "timeout": timeout,
                    "args": ["-I", native_path, event]}
        if event in {"UserPromptSubmit", "PreToolUse"}:
            expected["onFailure"] = "block"
        if hook != expected or type(timeout) is not int or not 1 <= timeout <= 60:
            raise BundleError("Claude hooks require isolated native command and declared failure policy")
        commands.add(command)
    if commands == {"python3"}:
        return "posix"
    if commands == {"python"}:
        return "windows-claude"
    raise BundleError("Claude hooks mix incompatible interpreter targets")


def _claude_target_manifest(content: bytes, target: str) -> bytes:
    """Select a fixed exec-form interpreter without introducing shell syntax."""
    data = _decode_object(content)
    if claude_hook_target(data) == target:
        return content
    command = "python" if target == "windows-claude" else "python3"
    for groups in data.get("hooks", {}).values():
        for group in groups:
            for hook in group.get("hooks", []):
                hook["command"] = command
    return (json.dumps(data, sort_keys=True, indent=2) + "\n").encode("utf-8")


def bundle_target(root: Path) -> str:
    """Return the target after validating every native Claude command handler."""
    return claude_hook_target(_json(regular_file(root, "ecosystem/claude-hooks.json")))


def source_resource(root: Path, relative: str) -> tuple[bytes, int]:
    """Read or render a resource identically for build, validation and comparison."""
    root = Path(root)
    portable = (root / BUNDLE_MANIFEST).is_file()
    origin = regular_file(root, relative if portable else source_path(relative))
    content = origin.read_bytes()
    if not portable and relative.startswith("agents/") and relative.endswith(".md"):
        return render_claude_agent(content), 0o644
    if not portable and relative in {"ecosystem/claude_hooks.py", "ecosystem/hook_entry.py"}:
        projected = render_current_inventory(content)
        if projected != content:
            raise BundleError("Source bootstrap inventory is stale; regenerate it from the current builder")
        content = projected
    if not portable and relative == "ecosystem/claude_hooks.py":
        support = regular_file(root, "ecosystem/platform_support.py").read_bytes()
        content = render_claude_bootstrap(content, support)
    if portable and _PLATFORM.IS_WINDOWS:
        inventory = _json(regular_file(root, BUNDLE_MANIFEST))
        try:
            expected_mode = inventory["files"][relative]["mode"]
        except (KeyError, TypeError) as exc:
            raise BundleError("Portable resource mode is missing from its inventory") from exc
        mode = _PLATFORM.logical_mode(origin, expected=expected_mode)
    else:
        mode = _PLATFORM.logical_mode(origin)
    return content, 0o755 if mode & stat.S_IXUSR else 0o644


def regular_file(root: Path, relative: str) -> Path:
    """Check every component before opening an allowlisted file."""
    path = Path(relative)
    if path.is_absolute() or not path.parts or any(p in (".", "..") for p in path.parts):
        raise BundleError("Invalid relative bundle path")
    if _PLATFORM.IS_WINDOWS:
        try:
            _PLATFORM.validate_windows_relative(relative)
        except _PLATFORM.PlatformError as exc:
            raise BundleError("Invalid Windows bundle path") from exc
    current = root
    if _PLATFORM.IS_WINDOWS:
        for ancestor in (*reversed(root.parents), root):
            if _PLATFORM.is_reparse(ancestor):
                raise BundleError("Bundle root traverses a reparse point")
    if _PLATFORM.is_reparse(current):
        raise BundleError("Bundle root cannot be a symlink or reparse point")
    for part in path.parts:
        current /= part
        if _PLATFORM.is_reparse(current):
            raise BundleError(f"Symlink or reparse point is forbidden: {relative}")
    try:
        metadata = current.stat()
    except FileNotFoundError as exc:
        raise BundleError(f"Required file is missing: {relative}") from exc
    if not stat.S_ISREG(metadata.st_mode):
        raise BundleError(f"Not a regular file: {relative}")
    if metadata.st_nlink != 1:
        raise BundleError(f"Package resource has multiple hard links: {relative}")
    return current


def file_record(path: Path, *, expected_mode: int | None = None) -> dict[str, object]:
    """Hash bytes and validate physical POSIX or effective Windows permissions."""
    try:
        mode = _PLATFORM.logical_mode(path, expected=expected_mode)
    except _PLATFORM.PlatformError as exc:
        raise BundleError("Resource access permissions are unsafe") from exc
    if _PLATFORM.IS_WINDOWS:
        try:
            descriptor = _PLATFORM.open_regular(path, os.O_RDONLY, mode=mode)
            with os.fdopen(descriptor, "rb") as stream:
                digest = hashlib.sha256(stream.read()).hexdigest()
        except _PLATFORM.PlatformError as exc:
            raise BundleError("Resource changed or is not a safe regular file") from exc
    else:
        # Existing POSIX callers also record already-owned destinations before
        # atomically replacing their inode, preserving independently held links.
        # Package resources reject hard links in regular_file, before recording.
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"sha256": digest, "mode": mode}


def _decode_object(content: str | bytes) -> dict:
    """Give builders, installers and native loaders one unambiguous JSON meaning."""
    def unique(pairs: list[tuple[str, object]]) -> dict:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate mapping key")
            result[key] = value
        return result

    value = json.loads(content, object_pairs_hook=unique)
    if not isinstance(value, dict):
        raise ValueError("expected a JSON object")
    return value


def _json(path: Path) -> dict:
    try:
        return _decode_object(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BundleError(f"Invalid JSON: {path.name}") from exc


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    _PLATFORM.set_access(path, 0o644)


def _check_plugin(value: dict) -> None:
    if (not isinstance(value, dict) or set(value) != {"name", "version", "description", "skills", "hooks"}
            or value.get("name") != "constellation" or not isinstance(value.get("version"), str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", value["version"])
            or not isinstance(value.get("description"), str) or not value["description"].strip()
            or value.get("skills") != "./skills/"
            or value.get("hooks") != "./ecosystem/hooks.json"):
        raise BundleError("Plugin manifest does not match the Constellation contract")


def _check_claude_plugin(value: dict) -> None:
    if (not isinstance(value, dict) or set(value) != {"name", "version", "description", "author", "skills", "hooks"}
            or value.get("name") != "constellation" or not isinstance(value.get("version"), str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", value["version"])
            or not isinstance(value.get("description"), str) or not value["description"].strip()
            or value.get("author") != {"name": "Constellation"}
            or value.get("skills") != "./skills/"
            or value.get("hooks") != "./ecosystem/claude-hooks.json"):
        raise BundleError("Claude plugin manifest does not match the Constellation contract")


def verify_bundle(root: Path, *, installation: bool = False) -> dict:
    """Verify the one active package layout without executing candidate code.

    Incoming distributions and existing installations use this same inventory,
    projection and access contract. Release identifiers do not select readers.
    """
    root = Path(root)
    if _PLATFORM.IS_WINDOWS:
        root = _PLATFORM.validate_lookup(root)
    if _PLATFORM.is_reparse(root) or not root.is_dir():
        raise BundleError("Bundle must be a real directory")
    root = root.resolve()
    try:
        _PLATFORM.verify_access(root, private=False)
    except _PLATFORM.PlatformError as exc:
        raise BundleError("Bundle directory access permits untrusted replacement") from exc
    manifest = _json(regular_file(root, BUNDLE_MANIFEST))
    if (set(manifest) != {"schema", "modules", "files"}
            or type(manifest.get("schema")) is not int or manifest["schema"] != 1):
        raise BundleError("Unsupported bundle schema")
    if not isinstance(manifest.get("modules"), list):
        raise BundleError("Bundle modules must be an explicit list")
    selected = select_modules(manifest["modules"])
    expected = allowed_files(selected)
    if not isinstance(manifest.get("files"), dict) or set(manifest["files"]) != expected:
        raise BundleError("Bundle file list differs from the allowlist")
    actual = set()
    for directory, subdirs, files in os.walk(root, followlinks=False):
        try:
            _PLATFORM.verify_access(Path(directory), private=False)
        except _PLATFORM.PlatformError as exc:
            raise BundleError("Bundle directory access permits untrusted replacement") from exc
        for name in subdirs + files:
            path = Path(directory) / name
            if _PLATFORM.is_reparse(path):
                raise BundleError("Bundle contains a symlink or reparse point")
        for name in files:
            actual.add((Path(directory) / name).relative_to(root).as_posix())
    metadata = {INSTALL_RECEIPT} if installation else set()
    if actual != expected | {BUNDLE_MANIFEST} | metadata:
        raise BundleError("Bundle contains missing or non-allowlisted files")
    if installation:
        receipt = regular_file(root, INSTALL_RECEIPT)
        try:
            if _PLATFORM.logical_mode(receipt, expected=0o600) != 0o600:
                raise _PLATFORM.PlatformError("Private receipt access is required")
        except _PLATFORM.PlatformError as exc:
            raise BundleError("Installation receipt must have mode 0600 or verified private Windows access") from exc
    for relative in sorted(expected):
        claimed = manifest["files"][relative]
        if (not isinstance(claimed, dict) or set(claimed) != {"sha256", "mode"}
                or type(claimed["mode"]) is not int or claimed["mode"] not in (0o644, 0o755)):
            raise BundleError(f"Bundle integrity mismatch: {relative}")
        record = file_record(regular_file(root, relative), expected_mode=claimed["mode"])
        if record != claimed:
            raise BundleError(f"Bundle integrity mismatch: {relative}")
    codex = _json(regular_file(root, PLUGIN_MANIFEST))
    claude = _json(regular_file(root, CLAUDE_PLUGIN_MANIFEST))
    _check_plugin(codex)
    _check_claude_plugin(claude)
    if codex["version"] != claude["version"]:
        raise BundleError("Native plugin versions differ")
    bundle_target(root)
    for relative in ("ecosystem/claude_hooks.py", "ecosystem/hook_entry.py"):
        entry = regular_file(root, relative).read_bytes()
        if render_current_inventory(entry) != entry:
            raise BundleError(f"Native bootstrap inventory differs from the current layout: {relative}")
    bootstrap = regular_file(root, "ecosystem/claude_hooks.py").read_bytes()
    support = regular_file(root, "ecosystem/platform_support.py").read_bytes()
    if render_claude_bootstrap(bootstrap, support) != bootstrap:
        raise BundleError("Claude bootstrap differs from canonical platform support")
    for relative in sorted(expected):
        if relative.startswith("agents/") and relative.endswith(".md"):
            canonical = regular_file(root, source_path(relative))
            if (root / relative).read_bytes() != render_claude_agent(canonical.read_bytes()):
                raise BundleError(f"Claude agent differs from its canonical source: {relative}")
    return manifest


def build_bundle(output: Path, modules: Iterable[str] | None = None,
                 source_root: Path | None = None, *, language: str = "es",
                 target: str = "posix") -> dict:
    """Build a self-contained bundle in a new directory outside its source.

    Args:
        output: New destination; existing directories and overlapping paths fail.
        modules: Canonical module IDs to include, or all available modules.
        source_root: Canonical .codex source tree or a verified portable bundle.
        language: "es" keeps source bytes; "en" selects the complete checked-in
            English overlays. For portable inputs the default preserves their
            existing language; explicit "en" is rejected because overlays are
            source-only and rebuilding does not perform language conversion.
        target: "posix" keeps canonical commands. "windows-claude" emits the
            fixed native Python exec-form hooks. Portable inputs preserve their
            current target with the default; explicit conversion is rejected.

    Returns:
        The unchanged schema-1 inventory with content hashes and file modes.

    Raises:
        BundleError: Invalid language, incomplete/unsafe translations, invalid
            input bundle, unavailable modules, or an unsafe destination.
    """
    source = Path(source_root) if source_root is not None else Path(__file__).resolve().parent.parent
    if _PLATFORM.IS_WINDOWS:
        source = _PLATFORM.validate_lookup(source)
    if _PLATFORM.is_reparse(source) or not source.is_dir():
        raise BundleError("Source must be a real directory")
    source = source.resolve()
    portable = (source / BUNDLE_MANIFEST).exists()
    if language not in {"es", "en"}:
        raise BundleError("Language must be es or en")
    if portable and language != "es":
        raise BundleError("Portable bundles preserve their language; select English from canonical sources")
    if target not in TARGETS:
        raise BundleError("Target must be posix or windows-claude")
    if portable and target != "posix":
        raise BundleError("Portable bundles preserve their target; select Windows from canonical sources")
    translations = _english_resources(source) if language == "en" else {}
    available = verify_bundle(source)["modules"] if portable else MODULES
    selected = select_modules(available if modules is None else modules)
    if not set(selected) <= set(available):
        raise BundleError("Requested module is not present in the source bundle")
    output = Path(output)
    if _PLATFORM.IS_WINDOWS:
        output = _PLATFORM.validate_lookup(output)
    if _PLATFORM.is_reparse(output):
        raise BundleError("Output cannot be a symlink")
    output = output.absolute().resolve()
    if output == source or source in output.parents or output in source.parents:
        raise BundleError("Output and source must not overlap")
    if output.exists():
        raise BundleError("Output already exists; choose a new directory")
    sources: dict[str, tuple[bytes, int]] = {}
    for relative in sorted(allowed_files(selected)):
        content, mode = source_resource(source, relative)
        origin = source_path(relative)
        if origin in translations:
            content = translations[origin]
            if relative.startswith("agents/") and relative.endswith(".md"):
                content = render_claude_agent(content)
        if not portable and relative == "ecosystem/claude-hooks.json":
            content = _claude_target_manifest(content, target)
        sources[relative] = content, mode
    try:
        codex = _decode_object(sources[PLUGIN_MANIFEST][0])
        claude = _decode_object(sources[CLAUDE_PLUGIN_MANIFEST][0])
    except (UnicodeError, ValueError) as exc:
        raise BundleError("Invalid native plugin metadata") from exc
    _check_plugin(codex)
    _check_claude_plugin(claude)
    if codex["version"] != claude["version"]:
        raise BundleError("Native plugin versions differ")
    if _PLATFORM.IS_WINDOWS:
        # A public package may be readable by others; its construction boundary
        # must never allow untrusted ADD_FILE/DELETE_CHILD before hashes exist.
        _PLATFORM.secure_mkdir(output.parent, mode=0o755, parents=True, exist_ok=True)
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".constellation-build-", dir=output.parent) as temporary:
        staging = Path(temporary) / "bundle"
        if _PLATFORM.IS_WINDOWS:
            _PLATFORM.secure_mkdir(staging, mode=0o700)
        else:
            staging.mkdir(mode=0o755)
        for relative, (content, mode) in sources.items():
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            _PLATFORM.set_access(target, mode)
        manifest = {"schema": 1, "modules": list(selected),
                    "files": {p: file_record(staging / p) for p in sorted(sources)}}
        _write_json(staging / BUNDLE_MANIFEST, manifest)
        for directory, _, _ in os.walk(staging):
            _PLATFORM.set_access(Path(directory), 0o755)
        verify_bundle(staging)
        # Platform promotion preserves exclusive ownership on both OS families.
        try:
            _PLATFORM.promote_directory(staging, output)
        except FileExistsError as exc:
            raise BundleError("Output appeared while building") from exc
    return manifest


def write_archive(bundle: Path, output: Path) -> None:
    """Write a byte-reproducible ZIP with normalized timestamps and permissions."""
    bundle = Path(bundle)
    if _PLATFORM.IS_WINDOWS:
        bundle = _PLATFORM.validate_lookup(bundle)
    bundle = bundle.resolve()
    manifest = verify_bundle(bundle)
    output = Path(output)
    if _PLATFORM.IS_WINDOWS:
        output = _PLATFORM.validate_lookup(output)
    output = output.absolute()
    if output.is_symlink() or output.exists() or bundle == output or bundle in output.resolve().parents:
        raise BundleError("Archive must be new and outside the bundle")
    output.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
            created = True
            for relative in sorted([BUNDLE_MANIFEST, *manifest["files"]]):
                source = regular_file(bundle, relative)
                entry = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
                entry.create_system = 3
                mode = 0o644 if relative == BUNDLE_MANIFEST else manifest["files"][relative]["mode"]
                entry.external_attr = (stat.S_IFREG | mode) << 16
                entry.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(entry, source.read_bytes())
    except Exception:
        if created and output.is_file():
            output.unlink()
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--modules", nargs="+", choices=MODULES)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--language", choices=("es", "en"), default="es",
                        help="Source language edition; portable inputs preserve their existing language")
    parser.add_argument("--target", choices=TARGETS, default="posix",
                        help="Native source target; portable inputs preserve their existing target")
    args = parser.parse_args(argv)
    if sys.version_info < (3, 11):
        parser.error("Python 3.11 or newer is required")
    try:
        result = build_bundle(args.output, args.modules, args.source_root, language=args.language, target=args.target)
        if args.archive:
            write_archive(args.output, args.archive)
        print(json.dumps({"output": str(args.output.resolve()), "modules": result["modules"],
                          "files": len(result["files"])}, sort_keys=True))
        return 0
    except (BundleError, OSError) as exc:
        parser.exit(1, f"Build rejected: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build a deterministic, explicitly allowlisted Constellation bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
from typing import Iterable
import zipfile

MODULES = ("coding", "mathematics", "writter")
BUNDLE_MANIFEST = "bundle.json"
PLUGIN_MANIFEST = ".codex-plugin/plugin.json"
COMMON_FILES = (
    *(f"ecosystem/runtime/{name}.py" for name in
      ("__init__", "workflow", "workspace", "dispatch", "review_gate", "agent_policy", "progress")),
    "ecosystem/runtime/review-policy.json",
    *(f"ecosystem/{name}.py" for name in
      ("__init__", "core", "storage", "cli", "hooks", "hook_entry", "build", "install", "native", "validate")),
    "ecosystem/hooks.json", "ecosystem/README.md", "ecosystem/COMPATIBILITY.md",
    "ecosystem/ARCHITECTURE.md", "ecosystem/MIGRATION.md", "ecosystem/PROGRESS.md",
    "ecosystem/requirements-dev.txt", "ecosystem/references/protocol.md",
    "ecosystem/EVALUATION.md", "ecosystem/evaluation.json",
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
    paths = set(COMMON_FILES) | {PLUGIN_MANIFEST}
    for module in selected:
        paths.update(f"skills/{module}/{name}" for name in
                     ("SKILL.md", "agents/openai.yaml", "references/workflow.md"))
        paths.update(f"ecosystem/agents/{name}.toml" for name in MODULE_AGENTS[module])
    if "mathematics" in selected or "writter" in selected:
        paths.update(("ecosystem/references/ontology.md",
                      "ecosystem/references/ontology-examples.md"))
    return paths


def regular_file(root: Path, relative: str) -> Path:
    """Check every component before opening an allowlisted file."""
    path = Path(relative)
    if path.is_absolute() or not path.parts or any(p in (".", "..") for p in path.parts):
        raise BundleError("Invalid relative bundle path")
    current = root
    for part in path.parts:
        current /= part
        if current.is_symlink():
            raise BundleError(f"Symlink is forbidden: {relative}")
    try:
        mode = current.stat().st_mode
    except FileNotFoundError as exc:
        raise BundleError(f"Required file is missing: {relative}") from exc
    if not stat.S_ISREG(mode):
        raise BundleError(f"Not a regular file: {relative}")
    return current


def file_record(path: Path) -> dict[str, object]:
    return {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "mode": stat.S_IMODE(path.stat().st_mode)}


def _json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BundleError(f"Invalid JSON: {path.name}") from exc
    if not isinstance(value, dict):
        raise BundleError(f"Expected a JSON object: {path.name}")
    return value


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o644)


def _check_plugin(value: dict) -> None:
    if (set(value) != {"name", "version", "description", "skills", "hooks"}
            or value.get("name") != "constellation" or not isinstance(value.get("version"), str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", value["version"])
            or not isinstance(value.get("description"), str) or not value["description"].strip()
            or value.get("skills") != "./skills/"
            or value.get("hooks") != "./ecosystem/hooks.json"):
        raise BundleError("Plugin manifest does not match the Constellation contract")


def verify_bundle(root: Path) -> dict:
    """Verify exact file membership, hashes, modes and the compat manifest."""
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise BundleError("Bundle must be a real directory")
    root = root.resolve()
    manifest = _json(regular_file(root, BUNDLE_MANIFEST))
    if manifest.get("schema") != 1:
        raise BundleError("Unsupported bundle schema")
    if not isinstance(manifest.get("modules"), list):
        raise BundleError("Bundle modules must be an explicit list")
    selected = select_modules(manifest["modules"])
    expected = allowed_files(selected)
    if not isinstance(manifest.get("files"), dict) or set(manifest["files"]) != expected:
        raise BundleError("Bundle file list differs from the allowlist")
    actual = set()
    for directory, subdirs, files in os.walk(root, followlinks=False):
        for name in subdirs + files:
            path = Path(directory) / name
            if path.is_symlink():
                raise BundleError("Bundle contains a symlink")
        for name in files:
            actual.add((Path(directory) / name).relative_to(root).as_posix())
    if actual != expected | {BUNDLE_MANIFEST}:
        raise BundleError("Bundle contains missing or non-allowlisted files")
    for relative in sorted(expected):
        record = file_record(regular_file(root, relative))
        if record["mode"] not in (0o644, 0o755) or record != manifest["files"][relative]:
            raise BundleError(f"Bundle integrity mismatch: {relative}")
    _check_plugin(_json(regular_file(root, PLUGIN_MANIFEST)))
    return manifest


def build_bundle(output: Path, modules: Iterable[str] | None = None,
                 source_root: Path | None = None) -> dict:
    """Build outside the source tree, without Git or a writable checkout."""
    source = Path(source_root) if source_root is not None else Path(__file__).resolve().parent.parent
    if source.is_symlink() or not source.is_dir():
        raise BundleError("Source must be a real directory")
    source = source.resolve()
    portable = (source / BUNDLE_MANIFEST).exists()
    available = verify_bundle(source)["modules"] if portable else MODULES
    selected = select_modules(available if modules is None else modules)
    if not set(selected) <= set(available):
        raise BundleError("Requested module is not present in the source bundle")
    output = Path(output)
    if output.is_symlink():
        raise BundleError("Output cannot be a symlink")
    output = output.absolute().resolve()
    if output == source or source in output.parents or output in source.parents:
        raise BundleError("Output and source must not overlap")
    if output.exists():
        raise BundleError("Output already exists; choose a new directory")
    sources: dict[str, Path] = {}
    for relative in sorted(allowed_files(selected)):
        origin = relative if relative != PLUGIN_MANIFEST or portable else "ecosystem/plugin.json"
        sources[relative] = regular_file(source, origin)
    _check_plugin(_json(sources[PLUGIN_MANIFEST]))
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".constellation-build-", dir=output.parent) as temporary:
        staging = Path(temporary) / "bundle"
        staging.mkdir(mode=0o755)
        for relative, origin in sources.items():
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(origin.read_bytes())
            target.chmod(0o755 if origin.stat().st_mode & stat.S_IXUSR else 0o644)
        manifest = {"schema": 1, "modules": list(selected),
                    "files": {p: file_record(staging / p) for p in sorted(sources)}}
        _write_json(staging / BUNDLE_MANIFEST, manifest)
        for directory, _, _ in os.walk(staging):
            Path(directory).chmod(0o755)
        verify_bundle(staging)
        # Claim the destination exclusively before the atomic directory replacement.
        try:
            output.mkdir(mode=0o755)
        except FileExistsError as exc:
            raise BundleError("Output appeared while building") from exc
        try:
            staging.rename(output)
        except OSError:
            try:
                output.rmdir()
            except OSError:
                pass
            raise
    return manifest


def write_archive(bundle: Path, output: Path) -> None:
    """Write a byte-reproducible ZIP with normalized timestamps and permissions."""
    bundle = Path(bundle).resolve()
    manifest = verify_bundle(bundle)
    output = Path(output).absolute()
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
                entry.external_attr = (stat.S_IFREG | stat.S_IMODE(source.stat().st_mode)) << 16
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
    args = parser.parse_args(argv)
    if sys.version_info < (3, 11):
        parser.error("Python 3.11 or newer is required")
    try:
        result = build_bundle(args.output, args.modules, args.source_root)
        if args.archive:
            write_archive(args.output, args.archive)
        print(json.dumps({"output": str(args.output.resolve()), "modules": result["modules"],
                          "files": len(result["files"])}, sort_keys=True))
        return 0
    except (BundleError, OSError) as exc:
        parser.exit(1, f"Build rejected: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())

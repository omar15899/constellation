#!/usr/bin/env python3
"""Install or export the English, coding-focused Copilot CLI profile.

Examples:
    python -B install.py --check
    python -B install.py --apply
    python -B install.py --export copilot-windows.zip --include-docs PATH

Installation never replaces an existing different file. Export freezes the
committed Constellation core, so unrelated working-tree edits stay on the source
machine. The Copilot adapter uses that core directly; no Claude client is needed.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import tempfile
from types import ModuleType
from typing import Iterator
import zipfile

sys.dont_write_bytecode = True

PROFILE_FILES = (
    "README.md", "copilot-instructions.md", "docs.md", "runtime.py",
    "agents/implementer.agent.md", "agents/correctness-reviewer.agent.md",
    "agents/readability-reviewer.agent.md", "agents/robustness-reviewer.agent.md",
    "skills/human-coding/SKILL.md",
)
HOOK_EVENTS = ("sessionStart", "subagentStart", "preToolUse", "agentStop")
PACKAGE_MANIFEST = "package.json"
MAX_FILE_BYTES = 32 * 1024 * 1024


class InstallError(ValueError):
    """The package or destination cannot satisfy the installation contract."""


def _json_bytes(value: object) -> bytes:
    """Serialize stable UTF-8 metadata for hashes and reproducible exports."""
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _safe_path(path: Path) -> Path:
    """Reject linked ancestors before using an absolute filesystem lookup."""
    supplied = Path(path).expanduser().absolute()
    for component in (*reversed(supplied.parents), supplied):
        try:
            info = component.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise InstallError("Managed paths must not traverse links or reparse points.")
        if component != supplied and not stat.S_ISDIR(info.st_mode):
            raise InstallError("A managed path has a non-directory ancestor.")
    return supplied


def _read(path: Path) -> bytes:
    """Read a bounded, singly linked regular file without following links."""
    path = _safe_path(path)
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > MAX_FILE_BYTES:
        raise InstallError("Package files must be bounded, singly linked regular files.")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        data = stream.read(MAX_FILE_BYTES + 1)
    after = path.lstat()
    identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
    if identity(before) != identity(opened) or identity(before) != identity(after) or len(data) > MAX_FILE_BYTES:
        raise InstallError("A package file changed while being read.")
    return data


def _load(path: Path, name: str) -> ModuleType:
    """Load a fixed local module after its containing package is checked."""
    _read(path)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise InstallError("A required local Python module is unavailable.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _git(repo: Path, *arguments: str) -> bytes:
    """Read committed source without changing branches, the index or files."""
    result = subprocess.run(["git", "--no-replace-objects", "-C", str(repo), *arguments],
                            capture_output=True, timeout=60, check=False)
    if result.returncode:
        raise InstallError("Cannot read the committed Constellation core from Git.")
    return result.stdout


def _head_core(profile: Path, temporary: Path) -> tuple[Path, str, ModuleType]:
    """Build only explicitly selected committed resources in a temporary tree."""
    temporary = temporary.resolve(strict=True)
    repo = profile.parents[2]
    commit = _git(repo, "rev-parse", "HEAD").decode("ascii").strip()
    source = temporary / "source"
    for relative in ("ecosystem/build.py", "ecosystem/platform_support.py"):
        destination = source / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(_git(repo, "show", f"{commit}:.codex/{relative}"))
    builder = _load(source / "ecosystem/build.py", "copilot_committed_builder")
    selected = {builder.source_path(name) for name in builder.allowed_files(("coding",))}
    selected.update("ecosystem/locales/en/" + name for name in builder.translation_files())
    selected.add("ecosystem/runtime/progress.py")
    tree = _git(repo, "ls-tree", "-r", "-z", commit, "--", ".codex")
    modes = {}
    for record in tree.split(b"\0"):
        if record:
            metadata, name = record.split(b"\t", 1)
            modes[name.decode("utf-8")] = metadata.split()[0]
    for relative in sorted(selected):
        tracked = ".codex/" + relative
        mode = modes.get(tracked)
        if mode not in (b"100644", b"100755"):
            raise InstallError("A selected committed core resource is missing or linked.")
        destination = source / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(_git(repo, "show", f"{commit}:{tracked}"))
        destination.chmod(0o755 if mode == b"100755" else 0o644)
    bundle = temporary / "bundle"
    builder.build_bundle(bundle, ("coding",), source, language="en", target="windows-claude")
    return bundle, commit, builder


def _relative(name: str) -> str:
    """Accept only literal package-relative POSIX paths."""
    path = PurePosixPath(name)
    if (not isinstance(name, str) or not name or path.is_absolute() or "\\" in name
            or any(part in ("", ".", "..") or ":" in part for part in name.split("/"))):
        raise InstallError("Package inventory contains an unsafe relative path.")
    return path.as_posix()


def _verify_package(profile: Path) -> dict:
    """Check exported bytes before importing their bundled core modules."""
    manifest = json.loads(_read(profile / PACKAGE_MANIFEST))
    if (set(manifest) != {"schema", "core_source_commit", "files"} or manifest["schema"] != 1
            or not isinstance(manifest["files"], dict)):
        raise InstallError("Unsupported Copilot profile package manifest.")
    expected = {_relative(name) for name in manifest["files"]}
    required = {"install.py", "official_docs.py", "bundle/bundle.json", *PROFILE_FILES}
    if not required <= expected:
        raise InstallError("The Copilot profile package is incomplete.")
    actual = set()
    for directory, directories, files in os.walk(profile, followlinks=False):
        for name in directories + files:
            _safe_path(Path(directory) / name)
        actual.update((Path(directory) / name).relative_to(profile).as_posix() for name in files)
    if actual != expected | {PACKAGE_MANIFEST}:
        raise InstallError("Exported profile inventory differs from its manifest.")
    for name in sorted(expected):
        data = _read(profile / name)
        if manifest["files"][name] != hashlib.sha256(data).hexdigest():
            raise InstallError("Exported profile integrity check failed.")
    return manifest


@contextmanager
def payload(profile: Path) -> Iterator[tuple[dict[str, bytes], str, ModuleType]]:
    """Yield the explicit portable payload and its committed-core provenance."""
    profile = _safe_path(profile)
    exported = (profile / PACKAGE_MANIFEST).exists()
    with tempfile.TemporaryDirectory(prefix="copilot-profile-") as directory:
        if exported:
            manifest = _verify_package(profile)
            bundle = profile / "bundle"
            commit = manifest["core_source_commit"]
            builder = _load(bundle / "ecosystem/build.py", "copilot_exported_builder")
            docs_tool = profile / "official_docs.py"
        else:
            bundle, commit, builder = _head_core(profile, Path(directory))
            docs_tool = profile.parent / "official_docs.py"
        core = builder.verify_bundle(bundle)
        files = {name: _read(profile / name) for name in PROFILE_FILES}
        files["install.py"] = _read(profile / "install.py")
        files["official_docs.py"] = _read(docs_tool)
        for name in sorted({"bundle.json", *core["files"]}):
            files["bundle/" + name] = _read(bundle / name)
        if exported:
            for name in manifest["files"]:
                if name.startswith("docs/official/"):
                    files[name] = _read(profile / name)
        yield files, commit, builder


def _snapshot(root: Path, docs_tool: bytes, temporary: Path) -> dict[str, bytes]:
    """Include only the verified public Copilot documentation selection."""
    tool = temporary.resolve(strict=True) / "official_docs.py"
    tool.write_bytes(docs_tool)
    module = _load(tool, "copilot_export_docs")
    root = _safe_path(root)
    module.inspect_snapshot(root, "copilot")
    return {"docs/official/" + name: _read(root / name)
            for name in (*module.sources("copilot"), "manifest.json", "INDEX.md")}


def export_profile(profile: Path, output: Path, docs_root: Path | None = None) -> dict:
    """Write a reproducible, new ZIP containing only portable public resources.

    Args:
        profile: Canonical profile source or a verified previously exported tree.
        output: New ZIP path; an existing object is always rejected.
        docs_root: Optional verified Copilot official-document snapshot directory.

    Returns:
        Archive path, SHA-256 and committed-core provenance.
    """
    output = _safe_path(output)
    if output.exists():
        raise InstallError("The export archive must not already exist.")
    with payload(profile) as (files, commit, _):
        files = dict(files)
        if docs_root is not None:
            with tempfile.TemporaryDirectory(prefix="copilot-public-docs-") as directory:
                files.update(_snapshot(docs_root, files["official_docs.py"], Path(directory)))
        files[PACKAGE_MANIFEST] = _json_bytes({"schema": 1, "core_source_commit": commit,
            "files": {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())}})
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in sorted(files.items()):
                entry = zipfile.ZipInfo("copilot-profile/" + name, date_time=(1980, 1, 1, 0, 0, 0))
                entry.create_system = 3
                entry.external_attr = (stat.S_IFREG | 0o644) << 16
                entry.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(entry, data)
    return {"archive": str(output), "sha256": hashlib.sha256(_read(output)).hexdigest(),
            "core_source_commit": commit}


def _installation_files(files: dict[str, bytes], home: Path, commit: str) -> dict[str, bytes]:
    """Render native hooks at their destination without changing client permissions."""
    copilot = home / ".copilot"
    installed = {name: files[name] for name in PROFILE_FILES
                 if name.startswith(("agents/", "skills/")) or name == "copilot-instructions.md"}
    readme = files["README.md"].decode("utf-8").replace(
        "(skills/human-coding/SKILL.md)", "(../../skills/human-coding/SKILL.md)").replace(
        "(docs.md)", "(../../docs/README.md)").encode("utf-8")
    installed.update({"docs/README.md": files["docs.md"], "constellation/profile/README.md": readme,
                      "tools/official_docs.py": files["official_docs.py"],
                      "constellation/profile/runtime.py": files["runtime.py"]})
    installed.update({"constellation/" + name: data for name, data in files.items() if name.startswith("bundle/")})
    installed.update({name: data for name, data in files.items() if name.startswith("docs/official/")})
    runtime = copilot / "constellation/profile/runtime.py"
    args = ["-I", "-B", str(runtime), "--bundle", str(copilot / "constellation/bundle"),
            "--state-dir", str(copilot / "constellation/state"), "hook", "--event"]
    installed["hooks/constellation.json"] = _json_bytes({"version": 1, "hooks": {
        event: [{"type": "command", "exec": str(Path(sys.executable).absolute()),
                 "args": [*args, event], "timeoutSec": 30}] for event in HOOK_EVENTS}})
    receipt = {"schema": 1, "core_source_commit": commit,
               "files": {name: hashlib.sha256(data).hexdigest() for name, data in sorted(installed.items())}}
    installed["constellation/profile-receipt.json"] = _json_bytes(receipt)
    return installed


def install_profile(profile: Path, home: Path, *, apply: bool = False) -> dict:
    """Check the full destination, then create only absent managed files.

    Args:
        profile: Canonical profile source or exported package root.
        home: User home containing the native .copilot directory.
        apply: Create missing resources when true; otherwise inspect only.

    Returns:
        Counts of unchanged and missing resources and the installation mode.

    Raises:
        InstallError: Any conflict, link, unsafe access or invalid package.
    """
    home = _safe_path(home)
    with payload(profile) as (files, commit, builder):
        platform = builder._PLATFORM
        installed = _installation_files(files, home, commit)
        root = home / ".copilot"
        bundle_manifest = json.loads(files["bundle/bundle.json"])
        modes = {"constellation/bundle/" + name: record["mode"]
                 for name, record in bundle_manifest["files"].items()}
        modes["constellation/bundle/bundle.json"] = 0o644
        state = _safe_path(root / "constellation/state")
        if state.exists():
            if not state.is_dir():
                raise InstallError("The private state path must be a directory.")
            platform.verify_access(state, private=True)
        docs_lock = root / "docs/.official.lock" if "docs/official/manifest.json" in installed else None
        if docs_lock is not None:
            _safe_path(docs_lock)
            if docs_lock.exists():
                _read(docs_lock)
                platform.verify_access(docs_lock, private=False)
        missing = []
        for name, data in sorted(installed.items()):
            target = _safe_path(root / name)
            if target.exists():
                if _read(target) != data:
                    raise InstallError("Existing managed file differs; preserve it and resolve the conflict before installation: " + name)
                platform.verify_access(target, private=False)
                if name in modes and platform.logical_mode(target, expected=modes[name]) != modes[name]:
                    raise InstallError("Existing core resource has different permissions: " + name)
            else:
                missing.append(name)
        if apply:
            # Directory creation and exclusive file creation preserve anything an
            # editor or another installer creates after the complete preflight.
            for name in missing:
                target = root / name
                platform.secure_mkdir(target.parent, mode=0o700, parents=True, exist_ok=True)
                mode = modes.get(name, 0o600)
                descriptor = platform.open_regular(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                                                   mode=mode, private=mode == 0o600)
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(installed[name])
                    stream.flush()
                    os.fsync(stream.fileno())
            if docs_lock is not None and not docs_lock.exists():
                # The lock is local runtime state, never an exported resource or
                # receipt entry. Existing lock bytes and open handles are retained.
                descriptor = platform.open_regular(docs_lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                                                   mode=0o600, private=True)
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(b"\0")
            platform.secure_mkdir(root / "constellation/state", mode=0o700, parents=True, exist_ok=True)
            builder.verify_bundle(root / "constellation/bundle")
        return {"mode": "apply" if apply else "check", "home": str(root),
                "unchanged": len(installed) - len(missing), "missing": len(missing),
                "core_source_commit": commit, "native_windows_acceptance": "pending"}


def main() -> int:
    """Expose read-only checking, explicit installation and portable export."""
    if sys.version_info < (3, 11):
        print("Copilot profile requires Python 3.11 or newer.", file=sys.stderr)
        return 2
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--home", type=Path, default=Path.home())
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--check", action="store_true", help="Inspect only; the default")
    action.add_argument("--apply", action="store_true", help="Create missing profile resources")
    action.add_argument("--export", type=Path, metavar="NEW_ZIP", help="Export a new portable ZIP")
    parser.add_argument("--include-docs", type=Path, help="Verified public Copilot docs/official snapshot; export only")
    args = parser.parse_args()
    if args.include_docs is not None and args.export is None:
        parser.error("--include-docs requires --export")
    try:
        profile = Path(__file__).absolute().parent
        result = (export_profile(profile, args.export, args.include_docs) if args.export is not None
                  else install_profile(profile, args.home, apply=args.apply))
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (InstallError, OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        print("Copilot profile: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

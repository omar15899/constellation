#!/usr/bin/env python3
"""Small native Codex adapter; never starts a thread or stores protocol traffic."""
from __future__ import annotations

import argparse
from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import queue
import re
import stat
import subprocess
import sys
import threading
import time
import tomllib
from types import ModuleType
from typing import Any, BinaryIO, Iterable, Iterator

sys.dont_write_bytecode = True

PLUGIN_ID = "constellation@constellation"


class NativeError(RuntimeError):
    """The native client did not confirm an operation."""


def _regular(root: Path, relative: str) -> Path:
    path = root
    for part in Path(relative).parts:
        path /= part
        if path.is_symlink():
            raise NativeError("Source exclusion requires regular files without symlinks")
    try:
        if not stat.S_ISREG(path.stat().st_mode):
            raise NativeError("Source exclusion requires regular files")
    except OSError as exc:
        raise NativeError("A required source or installed skill file is unavailable") from exc
    return path


def _running_inventory() -> ModuleType:
    """Read the canonical inventory from this running package, never the target."""
    path = _regular(Path(__file__).resolve().parent, "build.py")
    specification = importlib.util.spec_from_file_location("constellation_native_inventory", path)
    if specification is None or specification.loader is None:
        raise NativeError("The running package inventory is unavailable")
    inventory = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(inventory)
    return inventory


def _source_overrides(directory: Path, names_by_path: dict[str, str]) -> dict[str, bool]:
    """Read exact selected path and name settings without changing unrelated preferences."""
    selected_paths = names_by_path.keys()
    config = directory / "config.toml"
    if not selected_paths or (not config.exists() and not config.is_symlink()):
        return {}
    try:
        with _regular(directory, "config.toml").open("rb") as stream:
            entries = tomllib.load(stream).get("skills", {}).get("config", [])
        if not isinstance(entries, list):
            raise ValueError("invalid skill config")
        exact: dict[str, bool] = {}
        effective: dict[str, bool] = {}
        by_name: dict[str, list[str]] = {}
        for path, name in names_by_path.items():
            by_name.setdefault(name, []).append(path)
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError("invalid skill entry")
            name = entry.get("name")
            path = entry.get("path")
            named_paths = by_name.get(name, []) if isinstance(name, str) else []
            if isinstance(path, str) and path not in selected_paths and os.path.normpath(path) in selected_paths:
                raise ValueError("ambiguous selected path alias")
            if not named_paths and (not isinstance(path, str) or path not in selected_paths):
                continue
            if (path is not None and name is not None) or type(entry.get("enabled")) is not bool:
                raise ValueError("ambiguous selected skill override")
            enabled = entry["enabled"]
            if named_paths:
                for matched in named_paths:
                    effective[matched] = enabled
            else:
                if path in exact:
                    raise ValueError("duplicate exact source path override")
                exact[path] = effective[path] = enabled
    except (ValueError, AttributeError, OSError) as exc:
        raise NativeError("Cannot confirm explicit skill path overrides in " + str(config)) from exc
    # Codex selects the last matching rule. Preserve any explicit path enable
    # even if shadowed, as writing that path would replace the user's choice.
    result = {path: True for path, enabled in effective.items() if enabled}
    for path, enabled in exact.items():
        result[path] = result.get(path, False) or enabled
    return result


def _configured_exclusions(home: Path, source: Path, paths: set[str], *,
                           names_by_path: dict[str, str] | None = None) -> set[str]:
    """Resolve exact rules in each layer, using native names for legacy path aliases."""
    if names_by_path is None:
        names_by_path = {path: Path(path).parent.name for path in paths}
    if set(names_by_path) != paths or any(not isinstance(name, str) or not name for name in names_by_path.values()):
        raise NativeError("Missing or ambiguous native names for the selected source paths")
    excluded: set[str] = set()
    for origin, directory in (("user", home), ("project", source)):
        for path, enabled in _source_overrides(directory, names_by_path).items():
            if enabled:
                raise NativeError(f"Explicit {origin} preference enables source skill {path}; resolve the setting before exclusion")
            excluded.add(path)
    return excluded


def _canonical_source_root(source_root: Path, home: Path) -> Path:
    """Recognize the source layout before reading any project skill preference."""
    source = Path(source_root)
    if source.is_symlink() or not source.is_dir():
        raise NativeError("Source root must be a real source directory")
    source = source.resolve()
    cache_parent = home / "plugins" / "cache"
    if ((source / "bundle.json").exists() or (source / "bundle.json").is_symlink()
            or source == cache_parent or cache_parent in source.parents):
        raise NativeError("Source exclusion does not accept a bundle or plugin cache")
    try:
        manifest = json.loads(_regular(source, "ecosystem/manifests/codex-plugin.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise NativeError("The source plugin manifest is invalid") from exc
    if (not isinstance(manifest, dict) or manifest.get("name") != "constellation"
            or manifest.get("skills") != "./skills/" or manifest.get("hooks") != "./ecosystem/hooks.json"):
        raise NativeError("The directory is not a Constellation source layout")
    return source


def _source_skill_files(source: Path, skills: Iterable[str], layout: ModuleType) -> dict[str, str]:
    """List present native entrypoints, distinguishing missing paths from unsafe aliases."""
    present = {}
    for name in skills:
        path = source
        for component in ("skills", name, "SKILL.md"):
            path = path / component
            try:
                if layout._PLATFORM.is_reparse(path):
                    raise NativeError("Source skill paths must not traverse links or reparse points")
                mode = path.lstat().st_mode
            except FileNotFoundError:
                break
            except OSError as exc:
                raise NativeError("Cannot determine the exact source skill path") from exc
            if component == "SKILL.md":
                if not stat.S_ISREG(mode):
                    raise NativeError("Source skill entry must be a regular file")
                present[name] = str(path)
            elif not stat.S_ISDIR(mode):
                raise NativeError("Source skill parent must be a real directory")
    return present


def _protected_names(requested: Iterable[str], selected: Iterable[str]) -> set[str]:
    """Only canonical, selected skill names can identify earlier exclusions."""
    if isinstance(requested, str):
        raise NativeError("Protected exclusions must be individual selected skill names")
    names = list(requested)
    if any(not isinstance(name, str) or name not in selected for name in names):
        raise NativeError("Protected exclusion does not name a selected skill")
    return set(names)


def _require_protection(protected: dict[str, str], configured: set[str], snapshot: dict | None = None) -> None:
    for path, name in protected.items():
        if path not in configured:
            raise NativeError(f"Previously excluded source {path} no longer has an explicit disable; review the source preference")
        if snapshot is not None and snapshot.get(path) != {"name": name, "enabled": False}:
            raise NativeError(f"Previously excluded source {path} is not disabled in native discovery; review the source preference")


def _require_source_identity(layout: ModuleType, source: Path, modules: list[str], manifest: dict) -> None:
    """Authorize new exclusions only for the same executable resources and modes."""
    for relative in sorted(layout.allowed_files(modules)):
        installed_record = manifest["files"][relative]
        try:
            source_bytes, source_mode = layout.source_resource(source, relative)
        except (OSError, ValueError) as exc:
            raise NativeError("Cannot read source resources for comparison") from exc
        if (hashlib.sha256(source_bytes).hexdigest() != installed_record["sha256"]
                or source_mode != installed_record["mode"]):
            raise NativeError(f"Source and installed resource differ: {relative}; no exclusions were written")


def _skill_snapshot(rpc: _Rpc, cwd: Path) -> dict[str, dict]:
    result = rpc.call("skills/list", {"cwds": [str(cwd)], "forceReload": True})
    row = _discovery_row(result, str(cwd))
    if row.get("errors"):
        raise NativeError("Native skill discovery could not be verified")
    skills = row.get("skills")
    if not isinstance(skills, list):
        raise NativeError("Native skill discovery returned invalid metadata")
    snapshot = {}
    for skill in skills:
        if (not isinstance(skill, dict) or not isinstance(skill.get("path"), str)
                or not isinstance(skill.get("name"), str) or not isinstance(skill.get("enabled"), bool)):
            raise NativeError("Native skill discovery returned invalid metadata")
        path = str(Path(skill["path"]).resolve())
        if path in snapshot:
            raise NativeError("Native skill discovery contains an ambiguous path")
        snapshot[path] = {"name": skill["name"], "enabled": skill["enabled"]}
    return snapshot


def _metadata_rows(value: Any, key: str) -> list[dict]:
    rows = value.get(key) if isinstance(value, dict) else None
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise NativeError("Native discovery returned invalid metadata")
    return rows


def _discovery_row(value: dict, location: str) -> dict:
    rows = _metadata_rows(value, "data")
    if len(rows) != 1 or rows[0].get("cwd") != location:
        raise NativeError("Native discovery did not confirm the requested directory")
    return rows[0]


def _issues(row: dict) -> tuple[list[dict], list[dict]]:
    """Do not echo parser messages, which can include source/configuration text."""
    errors = _metadata_rows(row, "errors")
    warnings = row.get("warnings", [])
    if not isinstance(warnings, list) or any(not isinstance(item, str) for item in warnings):
        raise NativeError("Native discovery returned invalid warning metadata")
    return ([{"kind": "native_discovery_error",
              "path": item.get("path") if isinstance(item.get("path"), str) else None}
             for item in errors],
            [{"kind": "native_discovery_warning",
              "message": "Native discovery reported a warning; message content is omitted."}
             for _ in warnings])


def _skill_metadata(row: dict) -> dict:
    if (not isinstance(row.get("name"), str) or not isinstance(row.get("path"), str)
            or not isinstance(row.get("enabled"), bool)):
        raise NativeError("Native discovery returned invalid skill metadata")
    return {**{key: row.get(key) for key in
               ("name", "description", "path", "scope", "enabled", "pluginId")
               if row.get(key) is None or isinstance(row.get(key), (str, bool))},
            "discovered": True}


def _hook_metadata(row: dict) -> dict:
    if (not isinstance(row.get("eventName"), str)
            or not isinstance(row.get("enabled"), bool)):
        raise NativeError("Native discovery returned invalid hook metadata")
    return {**{key: row.get(key) for key in
               ("key", "eventName", "source", "sourcePath", "pluginId", "enabled", "trustStatus")
               if row.get(key) is None or isinstance(row.get(key), (str, bool))},
            "discovered": True}


class _Rpc:
    def __init__(self, client: NativeClient, *, mutating: bool = False):
        self.timeout = client.timeout
        self.counter = 0
        self.messages: queue.Queue[dict | None] = queue.Queue()
        inherit = client._lock_inheritance(mutating)
        if mutating and not inherit:
            raise NativeError("A managed preference writer requires the device installation lock")
        try:
            self.process = subprocess.Popen(
                [client.executable, "app-server", "--stdio"], cwd=client.cwd,
                env=client.environment(), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=True, bufsize=1, **inherit,
            )
        except OSError as exc:
            raise NativeError("Cannot start the native Codex app-server") from exc
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()
        try:
            self.call("initialize", {"clientInfo": {"name": "constellation-installer", "version": "1.0.0"},
                                     "capabilities": {"experimentalApi": True}})
            self._send({"method": "initialized"})
        except Exception:
            self.close()
            raise

    def _read(self) -> None:
        assert self.process.stdout is not None
        try:
            for line in self.process.stdout:
                try:
                    value = json.loads(line)
                    # Notifications are discarded, never exposed or persisted.
                    if isinstance(value, dict) and "id" in value:
                        self.messages.put(value)
                except ValueError:
                    continue
        finally:
            self.messages.put(None)

    def _send(self, value: dict) -> None:
        assert self.process.stdin is not None
        try:
            self.process.stdin.write(json.dumps(value) + "\n")
            self.process.stdin.flush()
        except (OSError, ValueError) as exc:
            raise NativeError("Native app-server closed its input") from exc

    def call(self, method: str, params: dict) -> dict:
        self.counter += 1
        self._send({"id": self.counter, "method": method, "params": params})
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            try:
                response = self.messages.get(timeout=max(0.01, deadline - time.monotonic()))
            except queue.Empty as exc:
                raise NativeError(f"Native request timed out: {method}") from exc
            if response is None:
                raise NativeError("Native app-server exited before responding")
            if response.get("id") != self.counter:
                continue
            if "error" in response:
                raise NativeError(f"Native request failed: {method}")
            result = response.get("result")
            if not isinstance(result, dict):
                raise NativeError(f"Invalid native response: {method}")
            return result
        raise NativeError(f"Native request timed out: {method}")

    def close(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self.reader.join(timeout=1)
        for stream in (self.process.stdin, self.process.stdout):
            if stream is not None:
                stream.close()


class NativeClient:
    """Native plugin operations with an explicit home and bounded execution."""

    def __init__(self, codex_home: Path, executable: str = "codex",
                 cwd: Path | None = None, timeout: float = 30):
        self.codex_home = Path(codex_home).resolve()
        self.executable = executable
        self.cwd = Path(cwd).resolve() if cwd is not None else self.codex_home
        self.timeout = timeout
        self._install_lock: ContextVar[BinaryIO | None] = ContextVar("constellation_native_install_lock", default=None)

    @contextmanager
    def inherit_install_lock(self, descriptor: int) -> Iterator[None]:
        """Keep orphaned native mutations on the installer's POSIX flock.

        The caller holds the exclusive lock for installation, or the shared
        lock for source exclusion. An inherited duplicate refers to the same
        open file description and outlives a parent killed during a write.
        """
        if os.name != "posix":
            raise NativeError("Native Codex installation requires POSIX descriptor inheritance")
        expected = _regular(self.codex_home, "constellation/.install.lock")
        try:
            if not os.path.samestat(os.fstat(descriptor), expected.stat()):
                raise NativeError("The installation lock does not belong to this native client")
            held = os.fdopen(os.dup(descriptor), "rb")
        except (OSError, ValueError) as exc:
            raise NativeError("Invalid native installation lock descriptor") from exc
        with held:
            token = self._install_lock.set(held)
            try:
                yield
            finally:
                self._install_lock.reset(token)

    def environment(self) -> dict[str, str]:
        env = dict(os.environ)
        env["CODEX_HOME"] = str(self.codex_home)
        env.pop("CODEX_THREAD_ID", None)
        return env

    def _lock_inheritance(self, mutating: bool) -> dict[str, tuple[int, ...]]:
        held = self._install_lock.get() if mutating else None
        if held is not None and held.closed:
            raise NativeError("The native installation lock scope has ended")
        return {"pass_fds": (held.fileno(),)} if held is not None else {}

    def _run_json(self, *args: str, mutating: bool = False) -> Any:
        try:
            result = subprocess.run([self.executable, *args, "--json"], cwd=self.cwd,
                                    env=self.environment(), stdout=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL, text=True, timeout=self.timeout, **self._lock_inheritance(mutating))
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise NativeError("Native Codex command could not complete") from exc
        if result.returncode:
            raise NativeError(f"Native Codex command failed (exit {result.returncode})")
        try:
            value = json.loads(result.stdout)
        except ValueError as exc:
            raise NativeError("Native Codex returned invalid JSON") from exc
        return value

    def _run(self, *args: str, mutating: bool = False) -> dict:
        value = self._run_json(*args, mutating=mutating)
        if not isinstance(value, dict):
            raise NativeError("Native Codex returned an unexpected result")
        return value

    def marketplaces(self) -> list[dict]:
        value = self._run("plugin", "marketplace", "list")
        rows = value.get("marketplaces")
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise NativeError("Invalid native marketplace list")
        return rows

    def plugins(self, marketplace: str | None = None) -> list[dict]:
        if marketplace is not None and (not isinstance(marketplace, str)
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", marketplace)):
            raise NativeError("Invalid native marketplace filter")
        arguments = ("plugin", "list")
        if marketplace is not None:
            arguments += ("--marketplace", marketplace)
        value = self._run(*arguments)
        if set(value) != {"installed", "available"}:
            raise NativeError("Ambiguous or unsupported native plugin list")
        rows, available = value["installed"], value["available"]
        if not isinstance(available, list) or any(not isinstance(row, dict) for row in available):
            raise NativeError("Invalid native available plugin metadata")
        if (not isinstance(rows, list) or any(not isinstance(row, dict)
                or not isinstance(row.get("pluginId"), str) or not row["pluginId"].strip()
                or type(row.get("enabled")) is not bool
                or ("installed" in row and row["installed"] is not True) for row in rows)):
            raise NativeError("Invalid native plugin list")
        return rows

    def add_marketplace(self, path: Path) -> dict:
        return self._run("plugin", "marketplace", "add", str(path.resolve()), mutating=True)

    def add_plugin(self) -> dict:
        return self._run("plugin", "add", PLUGIN_ID, mutating=True)

    def remove_plugin(self) -> dict:
        return self._run("plugin", "remove", PLUGIN_ID, mutating=True)

    def remove_marketplace(self) -> dict:
        return self._run("plugin", "marketplace", "remove", "constellation", mutating=True)

    def capabilities(self) -> dict[str, Any]:
        """Discover fresh CLI metadata without loading skills or invoking capabilities.

        Each native surface may fail independently. Only explicitly allowed fields
        leave this adapter: no MCP transport, hook command, raw config or messages.
        """
        location = str(self.cwd)
        result: dict[str, Any] = {
            "surface": "fresh_codex_cli", "cwd": location,
            "skills": [], "hooks": [], "plugins": [], "mcp_servers": [],
            "agents": {"configured_max_concurrent_threads_per_session": None,
                       "effective_session_limit": None},
            "checks": {}, "errors": [], "warnings": [],
            "unverified": ["current_session_availability", "authorized", "compatible",
                           "executable", "skill_instructions_loaded", "executed"],
            "limits": [
                "Discovery describes a fresh CLI process, not the current client or its subagents.",
                "Plugin installation and enabled settings do not prove callable capabilities.",
                "MCP entries are configuration metadata; no server handshake or tool call is made.",
                "Configured agent capacity is not a verified limit of the current session.",
            ],
        }

        def failed(name: str, source: str) -> None:
            result["checks"][name] = {"source": source, "status": "failed"}
            result["errors"].append({"source": source, "kind": "metadata_unavailable",
                                     "message": "Native metadata is unavailable or malformed."})

        def checked(name: str, source: str) -> None:
            result["checks"][name] = {"source": source, "status": "ok"}

        try:
            plugins = self.plugins()
            metadata = []
            for row in plugins:
                if (not isinstance(row.get("pluginId"), str)
                        or not isinstance(row.get("enabled"), bool)):
                    raise NativeError("Invalid native plugin metadata")
                metadata.append({"pluginId": row["pluginId"], "enabled": row["enabled"],
                                 "installed": True, "discovered": True,
                                 "version": row.get("version") if isinstance(row.get("version"), str) else None})
            result["plugins"] = metadata
            checked("plugins", "codex plugin list --json")
        except NativeError:
            failed("plugins", "codex plugin list --json")

        try:
            servers = self._run_json("mcp", "list")
            if not isinstance(servers, list):
                raise NativeError("Invalid native MCP metadata")
            metadata = []
            for row in servers:
                if (not isinstance(row, dict) or not isinstance(row.get("name"), str)
                        or not isinstance(row.get("enabled"), bool)):
                    raise NativeError("Invalid native MCP metadata")
                metadata.append({"name": row["name"], "enabled": row["enabled"],
                                 "configured": True,
                                 "auth_status": row.get("auth_status")
                                 if isinstance(row.get("auth_status"), str) else None})
            result["mcp_servers"] = metadata
            checked("mcp", "codex mcp list --json")
        except NativeError:
            failed("mcp", "codex mcp list --json")

        try:
            rpc = _Rpc(self)
        except NativeError:
            for name, source in (("skills", "skills/list"), ("hooks", "hooks/list"),
                                 ("agents", "config/read")):
                failed(name, source)
        else:
            try:
                for name, source, params, convert in (
                    ("skills", "skills/list", {"cwds": [location], "forceReload": True}, _skill_metadata),
                    ("hooks", "hooks/list", {"cwds": [location]}, _hook_metadata),
                ):
                    try:
                        row = _discovery_row(rpc.call(source, params), location)
                        errors, warnings = _issues(row)
                        result[name] = [convert(item) for item in _metadata_rows(row, name)]
                        result["errors"].extend({"source": source, **item} for item in errors)
                        result["warnings"].extend({"source": source, **item} for item in warnings)
                        checked(name, source)
                        if errors or warnings:
                            result["checks"][name]["status"] = "partial"
                    except NativeError:
                        failed(name, source)
                try:
                    config = rpc.call("config/read", {"cwd": location, "includeLayers": False}).get("config")
                    if not isinstance(config, dict):
                        raise NativeError("Invalid native configuration metadata")
                    agents = config.get("agents", {})
                    if not isinstance(agents, dict):
                        raise NativeError("Invalid native agent configuration")
                    capacity = agents.get("max_concurrent_threads_per_session")
                    if capacity is not None and (type(capacity) is not int or capacity < 1):
                        raise NativeError("Invalid native configured agent capacity")
                    result["agents"]["configured_max_concurrent_threads_per_session"] = capacity
                    checked("agents", "config/read")
                except NativeError:
                    failed("agents", "config/read")
            finally:
                rpc.close()
        result["status"] = "partial" if result["errors"] or result["warnings"] else "complete"
        return result

    def exclude_source_skills(self, source_root: Path, modules: Iterable[str] | None = None, *,
                              expected_bundle_sha256: str | None = None,
                              protect_exclusions: Iterable[str] = ()) -> dict[str, Any]:
        """Confirm existing exclusions or disable equivalent installed source skills.

        Every new path override requires resource identity. An existing explicit
        override is stable across releases and can be confirmed without rewriting
        it. A failed write or final verification reports partial progress.
        """
        if expected_bundle_sha256 is not None and (
                not isinstance(expected_bundle_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_bundle_sha256)):
            raise NativeError("Expected bundle digest must be a lowercase SHA-256")
        layout = _running_inventory()
        with ExitStack() as held:
            try:
                lock = _regular(self.codex_home, "constellation/.install.lock")
                descriptor = layout._PLATFORM.open_regular(lock, os.O_RDONLY, private=True)
                held.callback(os.close, descriptor)
                held.enter_context(layout._PLATFORM.file_lock(descriptor, exclusive=False, blocking=False))
                held.enter_context(self.inherit_install_lock(descriptor))
            except BlockingIOError as exc:
                raise NativeError("Installation is in progress; retry source exclusion after promotion") from exc
            except OSError as exc:
                raise NativeError("Cannot pin the installed Constellation release for source exclusion") from exc
            return self._exclude_verified_source(source_root, modules, layout, expected_bundle_sha256, protect_exclusions)

    def check_protected_sources(self, source_root: Path, modules: Iterable[str] | None,
                                protect_exclusions: Iterable[str]) -> dict[str, Any]:
        """Read explicit settings using this candidate before installing or contacting Codex."""
        layout = _running_inventory()
        source = _canonical_source_root(source_root, self.codex_home)
        running_root = Path(__file__).resolve().parents[1]
        try:
            available = (layout.verify_bundle(running_root)["modules"] if (running_root / "bundle.json").exists()
                         else layout.AVAILABLE_MODULES)
            selected = layout.select_modules(available if modules is None else modules)
        except (ValueError, OSError) as exc:
            raise NativeError("Cannot verify the candidate module inventory or selection") from exc
        if not set(selected) <= set(available):
            raise NativeError("Select modules present in the candidate release")
        skills = layout.skill_names(selected)
        protected_names = _protected_names(protect_exclusions, skills)
        present = _source_skill_files(source, sorted(protected_names), layout)
        protected = {path: name for name, path in present.items()}
        configured = _configured_exclusions(self.codex_home, source, set(protected))
        _require_protection(protected, configured)
        return {"status": "protected", "source_root": str(source), "present": sorted(protected.values()),
                "absent": sorted(set(protected_names) - set(protected.values()))}


    def _read_source_snapshot(self, cwd: Path) -> dict[str, dict]:
        rpc = _Rpc(self)
        try:
            return _skill_snapshot(rpc, cwd)
        finally:
            rpc.close()

    def _exclude_verified_source(self, source_root: Path, modules: Iterable[str] | None,
                                 layout: ModuleType, expected_bundle_sha256: str | None,
                                 protect_exclusions: Iterable[str]) -> dict[str, Any]:
        """Compare and exclude source paths while the installation lock is held."""
        source = _canonical_source_root(source_root, self.codex_home)
        plugins = [item for item in self.plugins(marketplace="constellation") if item.get("pluginId") == PLUGIN_ID]
        if (len(plugins) != 1 or plugins[0].get("enabled") is not True
                or plugins[0].get("installed", True) is not True):
            raise NativeError("Source exclusion requires the installed, enabled Constellation plugin")
        version = plugins[0].get("version")
        if not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", version):
            raise NativeError("The installed plugin version is invalid")
        cache_relative = f"plugins/cache/constellation/constellation/{version}"
        # Only this installation's verified manifest can select modules. A module
        # may supply several native skills; directory names alone are not evidence
        # that all resources required to substitute the source have been installed.
        try:
            marker = _regular(self.codex_home, f"{cache_relative}/bundle.json")
            verified_manifest = layout.verify_bundle(marker.parent)
            bundle_sha256 = hashlib.sha256(marker.read_bytes()).hexdigest()
            installed_modules = verified_manifest["modules"]
            selected = list(layout.select_modules(installed_modules if modules is None else modules))
        except (ValueError, OSError) as exc:
            raise NativeError("Cannot verify the installed module inventory or selection") from exc
        if expected_bundle_sha256 is not None and expected_bundle_sha256 != bundle_sha256:
            raise NativeError("Installed bundle no longer matches the expected digest; no exclusions were written")
        if not set(selected) <= set(installed_modules):
            raise NativeError("Select unique modules present in the installed plugin")
        skills = layout.skill_names(selected)
        installed = {name: str(_regular(self.codex_home, f"{cache_relative}/skills/{name}/SKILL.md"))
                     for name in skills}
        sources = _source_skill_files(source, skills, layout)
        absent = {name: str(source / "skills" / name / "SKILL.md") for name in skills if name not in sources}
        protected_names = _protected_names(protect_exclusions, skills)
        protected = {path: name for name, path in sources.items() if name in protected_names}
        persisted = _configured_exclusions(self.codex_home, source, set(sources.values()))
        before = self._read_source_snapshot(source.parent)
        _require_protection(protected, persisted, before)
        paths = []
        for name in skills:
            loaded = before.get(installed[name])
            if loaded != {"name": "constellation:" + name, "enabled": True}:
                raise NativeError("The selected installed skill is not enabled in native discovery")
            if name in absent:
                if absent[name] in before:
                    raise NativeError("Native discovery disagrees with the missing source path")
                continue
            original = before.get(sources[name])
            if original is None or original["name"] != name:
                raise NativeError("The selected source skill is absent or ambiguous in native discovery")
            if sources[name] in persisted and original["enabled"]:
                raise NativeError(f"Configured exclusion is not effective for {sources[name]}; resolve conflicting native settings")
            paths.append({"path": sources[name], "name": name, "enabled": None,
                          "verified": False, "write_attempted": False, "write_confirmed": False})
        changes = [item for item in paths if item["path"] not in persisted]
        if changes:
            # A completely absent module cannot shadow the installed one.
            # Every represented module, including shared helpers, must match.
            represented = [mod for mod in selected if any(name in sources for name in layout.skill_names([mod]))]
            if "omaros" in represented:
                # A specialist depends on the four general methods even when
                # the caller is excluding only its project source paths.
                represented = [*layout.MODULES, "omaros"]
            _require_source_identity(layout, source, represented, verified_manifest)
        operation = "apply" if changes else ("already_confirmed" if paths else "no_source_paths")
        result: dict[str, Any] = {"status": "partial", "source_root": str(source),
            "modules": selected, "paths": paths, "bundle_sha256": bundle_sha256,
            "source_identity_checked": bool(changes),
            "operation": operation, "absent_sources": sorted(absent), "protected_exclusions": sorted(protected.values()),
            "methods": {"write": "skills/config/write", "verify": "skills/list"}}
        if changes:
            rpc = _Rpc(self, mutating=True)
            try:
                for item in changes:
                    try:
                        # Native preference writes are per path. Re-read explicit
                        # choices so a concurrent edit stops the remaining writes.
                        recently_excluded = _configured_exclusions(self.codex_home, source, set(sources.values()))
                        if protected:
                            _require_protection(protected, recently_excluded, _skill_snapshot(rpc, source.parent))
                        if item["path"] in recently_excluded:
                            continue
                        item["write_attempted"] = True
                        response = rpc.call("skills/config/write", {"path": item["path"], "enabled": False})
                        item["write_confirmed"] = response.get("effectiveEnabled") is False
                        if not item["write_confirmed"]:
                            result["error"] = "Native source exclusion was not confirmed; inspect effective skill settings"
                            break
                    except NativeError as exc:
                        result["error"] = str(exc)
                        break
            finally:
                rpc.close()
        # A fresh server checks persisted discovery, independent of the writer's cache.
        try:
            after = self._read_source_snapshot(source.parent)
            if _source_skill_files(source, skills, layout) != sources or any(path in after for path in absent.values()):
                result["error"] = "Source skill presence changed during exclusion; inspect native discovery"
            excluded = {item["path"] for item in paths}
            persisted = _configured_exclusions(self.codex_home, source, excluded)
            _require_protection(protected, persisted, after)
            for item in paths:
                found = after.get(item["path"])
                item["enabled"] = found["enabled"] if found else None
                item["verified"] = item["path"] in persisted and found == {"name": item["name"], "enabled": False}
            if ({path: value for path, value in before.items() if path not in excluded}
                    != {path: value for path, value in after.items() if path not in excluded}):
                result["error"] = "Other skill discovery changed during exclusion; inspect native skill settings"
            if all(item["verified"] for item in paths) and "error" not in result:
                result["status"] = "excluded"
            elif "error" not in result:
                result["error"] = "Native discovery did not verify every source skill as disabled"
        except NativeError as exc:
            result["error"] = str(exc)
        return result

    def inspect(self, cwd: Path | None = None, marketplace_path: Path | None = None) -> dict[str, Any]:
        """Return only relevant skill/hook/plugin metadata; never raw responses."""
        location = str(Path(cwd).resolve() if cwd is not None else self.cwd)
        rpc = _Rpc(self)
        try:
            skills = rpc.call("skills/list", {"cwds": [location], "forceReload": True})
            hooks = rpc.call("hooks/list", {"cwds": [location]})
            result: dict[str, Any] = {"skills": [], "hooks": [], "errors": 0, "warnings": 0}
            for row in skills.get("data", []):
                result["errors"] += len(row.get("errors", []))
                for skill in row.get("skills", []):
                    if str(skill.get("name", "")).startswith("constellation:"):
                        result["skills"].append({key: skill.get(key) for key in
                                                ("name", "path", "enabled")})
            for row in hooks.get("data", []):
                result["errors"] += len(row.get("errors", []))
                result["warnings"] += len(row.get("warnings", []))
                for hook in row.get("hooks", []):
                    if hook.get("pluginId") == PLUGIN_ID:
                        result["hooks"].append({key: hook.get(key) for key in
                            ("key", "eventName", "sourcePath", "enabled", "trustStatus")})
            if marketplace_path is not None:
                plugin = rpc.call("plugin/read", {"pluginName": "constellation",
                    "marketplacePath": str(Path(marketplace_path).resolve())}).get("plugin", {})
                summary = plugin.get("summary", {})
                result["plugin"] = {key: summary.get(key) for key in
                                    ("id", "installed", "enabled", "localVersion")}
            return result
        finally:
            rpc.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-home", type=Path, required=True)
    parser.add_argument("--cwd", type=Path)
    parser.add_argument("--codex", default="codex")
    parser.add_argument("--marketplace-path", type=Path)
    operation = parser.add_mutually_exclusive_group()
    operation.add_argument("--exclude-source-root", type=Path)
    operation.add_argument("--capabilities", action="store_true",
                           help="Read fresh CLI capability metadata without executing skills or tools")
    parser.add_argument("--modules", nargs="+", help="Select module IDs in the verified installed bundle")
    parser.add_argument("--expected-bundle-sha256", help="Require this installed bundle digest for exclusion")
    parser.add_argument("--protect-exclusion", action="append", default=[], metavar="NAME",
                        help="Preserve a previously confirmed exclusion if the source is still present")
    parser.add_argument("--check-protected-only", action="store_true",
                        help="Preflight explicit preferences without installing a release or contacting Codex")
    args = parser.parse_args(argv)
    if (args.check_protected_only or args.protect_exclusion) and args.exclude_source_root is None:
        parser.error("Protecting source exclusions requires --exclude-source-root")
    if args.check_protected_only and args.expected_bundle_sha256:
        parser.error("--check-protected-only does not inspect the installed bundle")
    if args.expected_bundle_sha256 is not None and args.exclude_source_root is None:
        parser.error("--expected-bundle-sha256 requires --exclude-source-root")
    if args.modules and args.exclude_source_root is None:
        parser.error("--modules requires --exclude-source-root")
    if args.capabilities and args.marketplace_path is not None:
        parser.error("--marketplace-path does not apply to --capabilities")
    try:
        client = NativeClient(args.codex_home, args.codex, args.cwd)
        if args.capabilities:
            result = client.capabilities()
            print(json.dumps(result, sort_keys=True))
            return 0 if result["status"] == "complete" else 1
        if args.check_protected_only:
            result = client.check_protected_sources(args.exclude_source_root, args.modules, args.protect_exclusion)
            print(json.dumps(result, sort_keys=True))
            return 0
        if args.exclude_source_root is not None:
            result = client.exclude_source_skills(args.exclude_source_root, args.modules,
                                                 expected_bundle_sha256=args.expected_bundle_sha256,
                                                 protect_exclusions=args.protect_exclusion)
            print(json.dumps(result, sort_keys=True))
            return 0 if result["status"] == "excluded" else 1
        print(json.dumps(client.inspect(marketplace_path=args.marketplace_path), sort_keys=True))
        return 0
    except NativeError as exc:
        parser.exit(1, f"Native discovery failed: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())

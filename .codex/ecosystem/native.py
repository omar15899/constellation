#!/usr/bin/env python3
"""Small native Codex adapter; never starts a thread or stores protocol traffic."""
from __future__ import annotations

import argparse
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
from typing import Any, Iterable

sys.dont_write_bytecode = True

PLUGIN_ID = "constellation@constellation"
MODULES = ("coding", "mathematics", "writter")


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


def _comparison_resources(modules: list[str]) -> tuple[str, set[str]]:
    """Read the canonical inventory from this running package, never the target."""
    path = _regular(Path(__file__).resolve().parent, "build.py")
    specification = importlib.util.spec_from_file_location("constellation_native_inventory", path)
    if specification is None or specification.loader is None:
        raise NativeError("The running package inventory is unavailable")
    inventory = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(inventory)
    return inventory.PLUGIN_MANIFEST, inventory.allowed_files(modules)


def _skill_snapshot(rpc: _Rpc, cwd: Path) -> dict[str, dict]:
    result = rpc.call("skills/list", {"cwds": [str(cwd)], "forceReload": True})
    rows = result.get("data")
    if (not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict)
            or rows[0].get("errors")):
        raise NativeError("Native skill discovery could not be verified")
    skills = rows[0].get("skills")
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
    def __init__(self, client: NativeClient):
        self.timeout = client.timeout
        self.counter = 0
        self.messages: queue.Queue[dict | None] = queue.Queue()
        try:
            self.process = subprocess.Popen(
                [client.executable, "app-server", "--stdio"], cwd=client.cwd,
                env=client.environment(), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=True, bufsize=1,
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

    def environment(self) -> dict[str, str]:
        env = dict(os.environ)
        env["CODEX_HOME"] = str(self.codex_home)
        env.pop("CODEX_THREAD_ID", None)
        return env

    def _run_json(self, *args: str) -> Any:
        try:
            result = subprocess.run([self.executable, *args, "--json"], cwd=self.cwd,
                                    env=self.environment(), stdout=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL, text=True, timeout=self.timeout)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise NativeError("Native Codex command could not complete") from exc
        if result.returncode:
            raise NativeError(f"Native Codex command failed (exit {result.returncode})")
        try:
            value = json.loads(result.stdout)
        except ValueError as exc:
            raise NativeError("Native Codex returned invalid JSON") from exc
        return value

    def _run(self, *args: str) -> dict:
        value = self._run_json(*args)
        if not isinstance(value, dict):
            raise NativeError("Native Codex returned an unexpected result")
        return value

    def marketplaces(self) -> list[dict]:
        value = self._run("plugin", "marketplace", "list")
        rows = value.get("marketplaces")
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise NativeError("Invalid native marketplace list")
        return rows

    def plugins(self) -> list[dict]:
        value = self._run("plugin", "list")
        rows = value.get("installed")
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise NativeError("Invalid native plugin list")
        return rows

    def add_marketplace(self, path: Path) -> dict:
        return self._run("plugin", "marketplace", "add", str(path.resolve()))

    def add_plugin(self) -> dict:
        return self._run("plugin", "add", PLUGIN_ID)

    def remove_plugin(self) -> dict:
        return self._run("plugin", "remove", PLUGIN_ID)

    def remove_marketplace(self) -> dict:
        return self._run("plugin", "marketplace", "remove", "constellation")

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

    def exclude_source_skills(self, source_root: Path,
                              modules: Iterable[str] | None = None) -> dict[str, Any]:
        """Opt in to native path exclusions for identical installed source skills.

        All checks precede writes. A write or verification failure returns explicit
        partial metadata; already-written flags are retained, never silently undone.
        """
        source = Path(source_root)
        if source.is_symlink() or not source.is_dir():
            raise NativeError("Source root must be a real source directory")
        source = source.resolve()
        cache_parent = self.codex_home / "plugins" / "cache"
        if ((source / "bundle.json").exists() or (source / "bundle.json").is_symlink()
                or source == cache_parent or cache_parent in source.parents):
            raise NativeError("Source exclusion does not accept a bundle or plugin cache")
        try:
            manifest = json.loads(_regular(source, "ecosystem/plugin.json").read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise NativeError("The source plugin manifest is invalid") from exc
        if (not isinstance(manifest, dict) or manifest.get("name") != "constellation"
                or manifest.get("skills") != "./skills/" or manifest.get("hooks") != "./ecosystem/hooks.json"):
            raise NativeError("The directory is not a Constellation source layout")
        plugins = [item for item in self.plugins() if item.get("pluginId") == PLUGIN_ID]
        if (len(plugins) != 1 or plugins[0].get("enabled") is not True
                or plugins[0].get("installed", True) is not True):
            raise NativeError("Source exclusion requires the installed, enabled Constellation plugin")
        version = plugins[0].get("version")
        if not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", version):
            raise NativeError("The installed plugin version is invalid")
        cache_relative = f"plugins/cache/constellation/constellation/{version}"
        installed = {module: str(_regular(self.codex_home, f"{cache_relative}/skills/{module}/SKILL.md"))
                     for module in MODULES
                     if (self.codex_home / cache_relative / "skills" / module / "SKILL.md").exists()}
        selected = list(installed) if modules is None else list(modules)
        if (not selected or any(not isinstance(module, str) for module in selected)
                or len(set(selected)) != len(selected)
                or any(module not in installed for module in selected)):
            raise NativeError("Select unique modules present in the installed plugin")
        selected = [module for module in MODULES if module in selected]
        plugin_manifest, resources = _comparison_resources(selected)
        for relative in sorted(resources):
            source_relative = "ecosystem/plugin.json" if relative == plugin_manifest else relative
            origin = _regular(source, source_relative)
            destination = _regular(self.codex_home, f"{cache_relative}/{relative}")
            try:
                source_hash = hashlib.sha256(origin.read_bytes()).digest()
                installed_hash = hashlib.sha256(destination.read_bytes()).digest()
            except OSError as exc:
                raise NativeError("Cannot read source and installed resources for comparison") from exc
            if source_hash != installed_hash:
                raise NativeError(f"Source and installed resource differ: {source_relative}; no exclusions were written")
        sources = {module: str(source / "skills" / module / "SKILL.md") for module in selected}
        rpc = _Rpc(self)
        try:
            before = _skill_snapshot(rpc, source.parent)
            paths = []
            for module in selected:
                loaded = before.get(installed[module])
                original = before.get(sources[module])
                if loaded != {"name": "constellation:" + module, "enabled": True}:
                    raise NativeError("The selected installed skill is not enabled in native discovery")
                if original is None or original["name"] != module:
                    raise NativeError("The selected source skill is absent or ambiguous in native discovery")
                paths.append({"path": sources[module], "name": module, "enabled": None,
                              "verified": False, "write_attempted": False, "write_confirmed": False})
            result: dict[str, Any] = {"status": "partial", "source_root": str(source),
                "modules": selected, "paths": paths,
                "methods": {"write": "skills/config/write", "verify": "skills/list"}}
            for item in paths:
                if before[item["path"]]["enabled"] is False:
                    continue
                item["write_attempted"] = True
                try:
                    response = rpc.call("skills/config/write", {"path": item["path"], "enabled": False})
                    item["write_confirmed"] = response.get("effectiveEnabled") is False
                    if not item["write_confirmed"]:
                        result["error"] = "Native source exclusion was not confirmed; inspect effective skill settings"
                        break
                except NativeError:
                    result["error"] = "Native source exclusion failed; earlier path flags may have been written"
                    break
        finally:
            rpc.close()
        # A fresh server checks persisted discovery, independent of the writer's cache.
        try:
            verifier = _Rpc(self)
            try:
                after = _skill_snapshot(verifier, source.parent)
            finally:
                verifier.close()
            excluded = {item["path"] for item in paths}
            for item in paths:
                found = after.get(item["path"])
                item["enabled"] = found["enabled"] if found else None
                item["verified"] = found == {"name": item["name"], "enabled": False}
            if ({path: value for path, value in before.items() if path not in excluded}
                    != {path: value for path, value in after.items() if path not in excluded}):
                result["error"] = "Other skill discovery changed during exclusion; inspect native skill settings"
            if all(item["verified"] for item in paths) and "error" not in result:
                result["status"] = "excluded"
            elif "error" not in result:
                result["error"] = "Native discovery did not verify every source skill as disabled"
        except NativeError:
            result["error"] = "Exclusion flags may have been written; native discovery verification failed"
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
    parser.add_argument("--modules", nargs="+", choices=MODULES)
    args = parser.parse_args(argv)
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
        if args.exclude_source_root is not None:
            result = client.exclude_source_skills(args.exclude_source_root, args.modules)
            print(json.dumps(result, sort_keys=True))
            return 0 if result["status"] == "excluded" else 1
        print(json.dumps(client.inspect(marketplace_path=args.marketplace_path), sort_keys=True))
        return 0
    except NativeError as exc:
        parser.exit(1, f"Native discovery failed: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())

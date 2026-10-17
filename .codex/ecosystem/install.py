#!/usr/bin/env python3
"""Install a portable bundle through Codex, preserving independently owned files."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile
import tomllib
from typing import Iterable, Iterator

sys.dont_write_bytecode = True
if __package__:
    from .build import (BUNDLE_MANIFEST, MODULES, PLUGIN_MANIFEST, BundleError, allowed_files,
                        build_bundle, file_record, regular_file, select_modules, verify_bundle)
    from .native import NativeClient, NativeError, PLUGIN_ID
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from build import (BUNDLE_MANIFEST, MODULES, PLUGIN_MANIFEST, BundleError, allowed_files,
                       build_bundle, file_record, regular_file, select_modules, verify_bundle)
    from native import NativeClient, NativeError, PLUGIN_ID

CATALOG_MANIFEST = ".agents/plugins/marketplace.json"
PLUGIN_DIRECTORY = "plugins/constellation"


class InstallError(ValueError):
    """Installation is unsafe, conflicted or could not be verified."""


def _safe_anchor(path: Path) -> Path:
    if path.is_symlink():
        raise InstallError(f"Managed path is a symlink: {path.name}")
    return path.resolve()


def _no_links(root: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise InstallError("Invalid managed path")
    current = root
    for part in path.parts:
        current /= part
        if current.is_symlink():
            raise InstallError(f"Managed path is a symlink: {relative}")
    return current


def _inventory(root: Path) -> dict:
    if root.is_symlink() or not root.is_dir():
        raise InstallError("Managed directory is missing or linked")
    files = {}
    for directory, subdirs, names in os.walk(root, followlinks=False):
        for name in subdirs + names:
            if (Path(directory) / name).is_symlink():
                raise InstallError("Managed directory contains a symlink")
        for name in names:
            path = Path(directory) / name
            if not stat.S_ISREG(path.stat().st_mode):
                raise InstallError("Managed directory contains a non-regular file")
            files[path.relative_to(root).as_posix()] = file_record(path)
    return dict(sorted(files.items()))


def _load_receipt(path: Path) -> dict | None:
    if path.is_symlink():
        raise InstallError("Installation receipt cannot be a symlink")
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or value.get("schema") != 1:
            raise ValueError("schema")
        modules = select_modules(value["modules"])
        expected = {f"{PLUGIN_DIRECTORY}/{p}" for p in allowed_files(modules) | {BUNDLE_MANIFEST}}
        expected.add(CATALOG_MANIFEST)
        if set(value["catalog"]) != expected:
            raise ValueError("catalog")
        expected_agents = {"constellation-" + Path(p).name for p in allowed_files(modules)
                           if p.startswith("ecosystem/agents/")}
        if set(value["agents"]) != expected_agents:
            raise ValueError("agents")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", value["version"]):
            raise ValueError("version")
        if set(value["cache"]) != allowed_files(modules) | {BUNDLE_MANIFEST}:
            raise ValueError("cache")
        return value
    except (KeyError, TypeError, ValueError, OSError) as exc:
        raise InstallError("Invalid installation receipt; no files were changed") from exc


def _cache_root(home: Path, version: str) -> Path:
    if not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", version):
        raise InstallError("Native plugin has an invalid version")
    return _no_links(home, f"plugins/cache/constellation/constellation/{version}")


def _disabled_in_config(home: Path) -> bool:
    path = _no_links(home, "config.toml")
    if not path.exists():
        return False
    try:
        with path.open("rb") as stream:
            config = tomllib.load(stream)
        plugin = config.get("plugins", {}).get(PLUGIN_ID, {})
        return plugin.get("enabled") is False
    except (OSError, ValueError, AttributeError) as exc:
        raise InstallError("Cannot safely read the native plugin enablement setting") from exc


def _registered(client: NativeClient, catalog: Path) -> tuple[bool, dict | None]:
    markets = [row for row in client.marketplaces() if row.get("name") == "constellation"]
    if len(markets) > 1:
        raise InstallError("Native marketplace registration is ambiguous")
    if markets:
        origin = markets[0].get("marketplaceSource", {})
        if (origin.get("sourceType") != "local" or not isinstance(origin.get("source"), str)
                or Path(origin["source"]).resolve() != catalog):
            raise InstallError("Marketplace constellation belongs to another source")
    plugins = [row for row in client.plugins() if row.get("pluginId") == PLUGIN_ID]
    if len(plugins) > 1:
        raise InstallError("Native plugin registration is ambiguous")
    plugin = plugins[0] if plugins else None
    if plugin is not None and plugin.get("enabled") is not True:
        raise InstallError("The plugin is disabled; preserve that decision and enable it explicitly in Codex")
    return bool(markets), plugin


def _preflight(home: Path, selected: tuple[str, ...], client: NativeClient,
               *, query_native: bool = True) -> tuple[dict | None, bool, dict | None]:
    managed = _no_links(home, "constellation")
    catalog = _no_links(home, "constellation/catalog")
    receipt = _load_receipt(_no_links(home, "constellation/receipt.json"))
    if managed.exists():
        if not managed.is_dir():
            raise InstallError("Installation directory is not a directory")
        # The runtime owns state independently; installation never traverses it.
        if any(p.name not in {"catalog", "receipt.json", ".install.lock", "state"}
               for p in managed.iterdir()):
            raise InstallError("Installation directory contains independently owned files")
    if _disabled_in_config(home):
        raise InstallError("The plugin is disabled; preserve that decision and enable it explicitly in Codex")
    cache_parent = _no_links(home, "plugins/cache/constellation/constellation")
    if cache_parent.exists():
        if not cache_parent.is_dir():
            raise InstallError("Native cache destination is not a directory")
        expected_versions = {receipt["version"]} if receipt else set()
        if {p.name for p in cache_parent.iterdir()} != expected_versions:
            raise InstallError("Native cache contains files outside the installation receipt")
    registered, plugin = _registered(client, catalog) if query_native else (False, None)
    if receipt is None:
        if catalog.exists() or registered or plugin is not None:
            raise InstallError("Existing installation has no ownership receipt")
    else:
        if not registered or plugin is None or plugin.get("version") != receipt["version"]:
            raise InstallError("Native registration differs from the installation receipt")
        if _inventory(catalog) != receipt["catalog"]:
            raise InstallError("Catalog was modified; preserve its files before updating")
        if _inventory(_cache_root(home, receipt["version"])) != receipt["cache"]:
            raise InstallError("Native cache was modified; preserve its files before updating")
        for name, record in receipt["agents"].items():
            path = _no_links(home, "agents/" + name)
            if not path.is_file() or file_record(path) != record:
                raise InstallError(f"Installed agent was modified: {name}")
    existing_agents = set(receipt["agents"]) if receipt else set()
    agents_dir = _no_links(home, "agents")
    if agents_dir.exists() and not agents_dir.is_dir():
        raise InstallError("Agent destination is not a directory")
    for relative in allowed_files(selected):
        if relative.startswith("ecosystem/agents/"):
            name = "constellation-" + Path(relative).name
            target = _no_links(home, "agents/" + name)
            if target.exists() and name not in existing_agents:
                raise InstallError(f"Agent destination belongs to another owner: {name}")
    return receipt, registered, plugin


@contextmanager
def _lock(home: Path) -> Iterator[None]:
    managed = _no_links(home, "constellation")
    managed.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = _no_links(home, "constellation/.install.lock")
    if path.exists() and not path.is_file():
        raise InstallError("Installation lock is not a regular file")
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise InstallError("Another Constellation installation is running") from exc
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _replace_bytes(path: Path, content: bytes, mode: int) -> None:
    """Replace one owned directory entry without writing its previous inode."""
    descriptor, name = tempfile.mkstemp(dir=path.parent, prefix=".constellation-")
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            os.fchmod(stream.fileno(), mode)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _write_json(path: Path, value: dict) -> None:
    content = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8")
    _replace_bytes(path, content, 0o600)


def install_bundle(bundle: Path, codex_home: Path, modules: Iterable[str] | None = None,
                   check: bool = False, client: NativeClient | None = None) -> dict:
    """Install or update one plugin; compensate failures through native commands.

    ``check`` performs validation and conflict detection without staging files.
    The injected client permits filesystem-realistic tests without Codex.
    Native caches and trust settings are never written directly.
    """
    bundle = Path(bundle)
    manifest = verify_bundle(bundle)
    bundle = bundle.resolve()
    selected = select_modules(manifest["modules"] if modules is None else modules)
    if not set(selected) <= set(manifest["modules"]):
        raise InstallError("Requested modules are absent from this bundle")
    home = _safe_anchor(Path(codex_home))
    managed = home / "constellation"
    if bundle == managed or managed in bundle.parents or bundle in managed.parents:
        raise InstallError("Bundle and installation directory must not overlap")
    backend = client or NativeClient(home, cwd=home if home.exists() else bundle)
    # A disabled plugin is rejected before taking the lock or running a mutating CLI.
    receipt, registered, old_plugin = _preflight(home, selected, backend,
                                               query_native=home.exists())
    if check:
        return {"status": "checked", "modules": list(selected), "update": receipt is not None,
                "catalog": str(managed / "catalog")}
    with _lock(home):
        receipt, registered, old_plugin = _preflight(home, selected, backend)
        with tempfile.TemporaryDirectory(prefix="constellation-install-") as temporary:
            work = Path(temporary)
            payload = work / "payload"
            build_bundle(payload, selected, bundle)
            catalog_stage = work / "catalog"
            destination = catalog_stage / PLUGIN_DIRECTORY
            destination.parent.mkdir(parents=True)
            shutil.copytree(payload, destination)
            market_file = catalog_stage / CATALOG_MANIFEST
            market_file.parent.mkdir(parents=True)
            market_file.write_text(json.dumps({"name": "constellation", "plugins": [{
                "name": "constellation", "source": {"source": "local", "path": "./plugins/constellation"},
                "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                "category": "Productivity"}]}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            market_file.chmod(0o644)
            catalog = managed / "catalog"
            backup = work / "previous-catalog"
            if receipt:
                shutil.copytree(catalog, backup)
            agent_sources = {"constellation-" + Path(p).name: payload / p for p in allowed_files(selected)
                             if p.startswith("ecosystem/agents/")}
            previous_agents = {name: ((home / "agents" / name).read_bytes(),
                                     stat.S_IMODE((home / "agents" / name).stat().st_mode))
                               for name in (receipt["agents"] if receipt else ())}
            attempted_marketplace = False
            attempted_plugin = False
            changed_agents = False
            # Recheck immediately before replacing files after building the payload.
            _preflight(home, selected, backend)
            try:
                if catalog.exists():
                    shutil.rmtree(catalog)
                shutil.copytree(catalog_stage, catalog)
                attempted_marketplace = not registered
                if not registered:
                    backend.add_marketplace(catalog)
                attempted_plugin = True
                backend.add_plugin()
                _, installed = _registered(backend, catalog)
                version = json.loads((payload / PLUGIN_MANIFEST).read_text(encoding="utf-8"))["version"]
                if installed is None or installed.get("version") != version:
                    raise InstallError("Native installation did not confirm the expected version")
                cache = _cache_root(home, version)
                if _inventory(cache) != _inventory(payload):
                    raise InstallError("Native cache differs from the verified bundle")
                agents_dir = _no_links(home, "agents")
                agents_dir.mkdir(mode=0o755, parents=True, exist_ok=True)
                changed_agents = True
                for name, source in agent_sources.items():
                    target = _no_links(home, "agents/" + name)
                    _replace_bytes(target, source.read_bytes(), 0o644)
                for name in set(previous_agents) - set(agent_sources):
                    (agents_dir / name).unlink()
                result = {"schema": 1, "modules": list(selected), "version": version,
                          "catalog": _inventory(catalog), "cache": _inventory(cache),
                          "agents": {name: file_record(agents_dir / name) for name in sorted(agent_sources)}}
                _write_json(managed / "receipt.json", result)
                return {"status": "updated" if receipt else "installed", "modules": list(selected),
                        "version": version, "agents": sorted(agent_sources), "catalog": str(catalog),
                        "hooks": "Review and trust the plugin hooks in Codex; trust was not changed."}
            except Exception as failure:
                rollback_errors = []
                try:
                    if receipt:
                        if catalog.exists():
                            shutil.rmtree(catalog)
                        shutil.copytree(backup, catalog)
                    if changed_agents:
                        for name in set(agent_sources) - set(previous_agents):
                            (home / "agents" / name).unlink(missing_ok=True)
                        for name, (content, mode) in previous_agents.items():
                            target = _no_links(home, "agents/" + name)
                            _replace_bytes(target, content, mode)
                except (OSError, InstallError):
                    rollback_errors.append("owned files")
                if attempted_plugin:
                    try:
                        if old_plugin is not None:
                            if rollback_errors:
                                raise InstallError("Previous catalog could not be restored")
                            backend.add_plugin()
                        elif any(p.get("pluginId") == PLUGIN_ID for p in backend.plugins()):
                            backend.remove_plugin()
                    except Exception:
                        rollback_errors.append("native plugin")
                if attempted_marketplace and not rollback_errors:
                    try:
                        if any(p.get("name") == "constellation" for p in backend.marketplaces()):
                            backend.remove_marketplace()
                    except Exception:
                        rollback_errors.append("native marketplace")
                # Native remove/list still needs a readable local marketplace.
                if receipt is None and not rollback_errors:
                    try:
                        if catalog.exists():
                            shutil.rmtree(catalog)
                    except OSError:
                        rollback_errors.append("new catalog")
                if not rollback_errors:
                    try:
                        if receipt:
                            _preflight(home, select_modules(receipt["modules"]), backend)
                        elif any(p.get("pluginId") == PLUGIN_ID for p in backend.plugins()):
                            raise InstallError("Plugin registration remains after rollback")
                    except Exception:
                        rollback_errors.append("restoration verification")
                if rollback_errors:
                    raise InstallError("Installation failed; rollback needs attention for "
                                       + ", ".join(rollback_errors)) from failure
                raise InstallError("Installation failed; previous owned files and registration restored") from failure


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--codex-home", type=Path, required=True)
    parser.add_argument("--modules", nargs="+", choices=MODULES)
    parser.add_argument("--check", "--dry-run", action="store_true")
    parser.add_argument("--codex", default="codex")
    args = parser.parse_args(argv)
    try:
        home = args.codex_home.resolve()
        client = NativeClient(home, args.codex, cwd=home if home.exists() else args.bundle.resolve())
        result = install_bundle(args.bundle, args.codex_home, args.modules, args.check, client)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (InstallError, BundleError, NativeError, OSError) as exc:
        parser.exit(1, f"Installation rejected: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())

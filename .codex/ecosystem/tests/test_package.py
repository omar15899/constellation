"""Filesystem-real package tests; synthetic native behavior is explicitly marked.

The synthetic backend is not evidence of Codex discovery. Real native discovery
has a separate test using only a temporary CODEX_HOME and no conversation/thread.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
import tomllib
import unittest
from unittest.mock import patch
from urllib.parse import unquote, urlsplit
import zipfile

sys.dont_write_bytecode = True
SOURCE_DIR = Path(__file__).resolve().parents[1]
CODEX_DIR = SOURCE_DIR.parent
sys.path.insert(0, str(SOURCE_DIR))

from build import BundleError, build_bundle, verify_bundle, write_archive
from install import InstallError, install_bundle
import install as installer
from native import NativeClient, NativeError
import native as native_adapter


ALL_MODULES = ("coding", "mathematics", "writter")
IS_DISTRIBUTED = (CODEX_DIR / "bundle.json").is_file()
MODULES = (tuple(json.loads((CODEX_DIR / "bundle.json").read_text())["modules"])
           if IS_DISTRIBUTED else ALL_MODULES)
PLUGIN_ID = "constellation@constellation"
PLUGIN_MANIFEST = ".codex-plugin/plugin.json"
CORE_FILES = {
    "review_gate.py", "review-policy.json", "ecosystem/core.py",
    "ecosystem/storage.py", "ecosystem/cli.py", "ecosystem/build.py",
    "ecosystem/install.py", "ecosystem/native.py", "ecosystem/validate.py",
    "ecosystem/hooks.py", "ecosystem/hooks.json", "ecosystem/references/protocol.md",
    "ecosystem/agents/researcher.toml", "ecosystem/agents/reviewer.toml",
    "ecosystem/agents/security-reviewer.toml", "ecosystem/agents/verifier.toml",
}


def snapshot(root: Path) -> dict[str, tuple[str, bytes | str, int]]:
    """Compare bytes, link destinations and permissions, without following links."""
    result: dict[str, tuple[str, bytes | str, int]] = {}
    if not root.exists():
        return result
    for directory, subdirs, files in os.walk(root, followlinks=False):
        for name in sorted(subdirs + files):
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                result[relative] = ("link", os.readlink(path), 0)
            elif path.is_file():
                result[relative] = ("file", path.read_bytes(), stat.S_IMODE(path.stat().st_mode))
    return result


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


class SyntheticNativeClient:
    """A deliberately destructive fake; all registries and caches are real files.

    Adding replaces a cache and enables the plugin, including an explicit false
    in config. Marketplace registration replaces an existing same-name source.
    Failures happen *after* effects, so rollback cannot assume an atomic CLI.
    This does not invoke or claim to reproduce the complete native Codex client.
    """

    def __init__(self, home: Path):
        self.home = home
        self.mutations: list[str] = []
        self.fail_once: str | None = None
        self.fail_before_once: str | None = None
        self.corrupt_cache_once = False
        self.fail_rollback = False

    def _rows(self, name: str) -> list[dict]:
        path = self.home / "synthetic-native" / (name + ".json")
        return json.loads(path.read_text()) if path.exists() else []

    def _save(self, name: str, rows: list[dict]) -> None:
        path = self.home / "synthetic-native" / (name + ".json")
        if rows:
            write_json(path, rows)
        else:
            path.unlink(missing_ok=True)

    def _failure(self, operation: str) -> None:
        if self.fail_once == operation:
            self.fail_once = None
            raise NativeError("Synthetic failure after " + operation)

    def _before(self, operation: str) -> None:
        if self.fail_before_once == operation:
            self.fail_before_once = None
            raise NativeError("Synthetic failure before " + operation)

    def marketplaces(self) -> list[dict]:
        return self._rows("marketplaces")

    def plugins(self) -> list[dict]:
        return self._rows("plugins")

    def add_marketplace(self, path: Path) -> dict:
        self.mutations.append("add_marketplace")
        self._before("add_marketplace")
        catalog = json.loads((path / ".agents/plugins/marketplace.json").read_text())
        assert catalog["name"] == "constellation"
        rows = [row for row in self.marketplaces() if row["name"] != "constellation"]
        rows.append({"name": "constellation", "marketplaceSource": {
            "sourceType": "local", "source": str(path.resolve())}})
        self._save("marketplaces", rows)
        self._failure("add_marketplace")
        return {"name": "constellation"}

    def _enable(self, enabled: bool | None) -> None:
        config = self.home / "config.toml"
        text = config.read_text() if config.exists() else ""
        pattern = r'(?m)^\[plugins\."constellation@constellation"\]\n(?:[^\[].*\n|\n)*'
        text = re.sub(pattern, "", text)
        if enabled is not None:
            text += '[plugins."constellation@constellation"]\nenabled = ' + str(enabled).lower() + "\n"
        if text:
            config.write_text(text)
        else:
            config.unlink(missing_ok=True)

    def add_plugin(self) -> dict:
        self.mutations.append("add_plugin")
        self._before("add_plugin")
        market = next(row for row in self.marketplaces() if row["name"] == "constellation")
        source = Path(market["marketplaceSource"]["source"]) / "plugins/constellation"
        metadata = json.loads((source / PLUGIN_MANIFEST).read_text())
        version = metadata["version"]
        cache = self.home / "plugins/cache/constellation/constellation" / version
        # Native add replaces the entire version directory, not just this version.
        if cache.parent.exists():
            shutil.rmtree(cache.parent)
        cache.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, cache)
        self._enable(True)
        rows = [row for row in self.plugins() if row["pluginId"] != PLUGIN_ID]
        rows.append({"pluginId": PLUGIN_ID, "version": version, "enabled": True})
        self._save("plugins", rows)
        if self.corrupt_cache_once:
            self.corrupt_cache_once = False
            (cache / "review-policy.json").write_text("{}\n")
        self._failure("add_plugin")
        return {"pluginId": PLUGIN_ID, "version": version}

    def remove_plugin(self) -> dict:
        self.mutations.append("remove_plugin")
        if self.fail_rollback:
            raise NativeError("Synthetic rollback failure")
        cache = self.home / "plugins/cache/constellation/constellation"
        if cache.exists():
            shutil.rmtree(cache)
        self._save("plugins", [row for row in self.plugins() if row["pluginId"] != PLUGIN_ID])
        self._enable(None)
        return {}

    def remove_marketplace(self) -> dict:
        self.mutations.append("remove_marketplace")
        self._save("marketplaces", [row for row in self.marketplaces() if row["name"] != "constellation"])
        return {}


class BundleCase(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="constellation-package-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.module = MODULES[0]
        self.bundle = self.root / "bundle"
        self.manifest = build_bundle(self.bundle, source_root=CODEX_DIR)

    def source_copy(self, name: str = "source") -> Path:
        source = self.root / name
        shutil.copytree(self.bundle, source)
        (source / "bundle.json").unlink()
        (source / PLUGIN_MANIFEST).replace(source / "ecosystem/plugin.json")
        (source / ".codex-plugin").rmdir()
        return source

    def changed_bundle(self, version: str = "1.0.1", *, change_agent: bool = False) -> Path:
        source = self.source_copy("update-source")
        metadata = json.loads((source / "ecosystem/plugin.json").read_text())
        metadata["version"] = version
        write_json(source / "ecosystem/plugin.json", metadata)
        workflow = source / f"skills/{self.module}/references/workflow.md"
        workflow.write_text(workflow.read_text() + "\nUpdated synthetic release.\n")
        if change_agent:
            agent = source / "ecosystem/agents/reviewer.toml"
            agent.write_text(agent.read_text() + "\n# Updated synthetic reviewer release.\n")
        result = self.root / "updated-bundle"
        build_bundle(result, MODULES, source_root=source)
        return result

    def engine_request(self, home: Path, code_root: Path, operation: str, payload: dict) -> dict:
        """Exercise the shipped CLI with its real default state location."""
        project = self.root / "state-project"
        project.mkdir(exist_ok=True)
        environment = dict(os.environ)
        environment["CODEX_HOME"] = str(home)
        environment.pop("CODEX_THREAD_ID", None)
        environment.pop("PYTHONPATH", None)
        result = subprocess.run(
            [sys.executable, "-I", "-B", str(code_root / "ecosystem/cli.py"),
             "--root", str(project), operation], input=json.dumps(payload), cwd=project,
            env=environment, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        value = json.loads(result.stdout)
        self.assertTrue(value["ok"])
        return value

    def create_default_state(self, home: Path, code_root: Path) -> tuple[Path, dict, int]:
        project = self.root / "state-project"
        project.mkdir(exist_ok=True)
        (project / "result.md").write_text("state fixture\n")
        argv = [sys.executable, "-I", "-c",
                "from pathlib import Path; assert Path('result.md').read_text() == 'state fixture\\n'"]
        check_hash = hashlib.sha256(json.dumps(argv, separators=(",", ":")).encode()).hexdigest()
        identity = {"session_id": "fixture-state-session", "task_id": "fixture-state-task",
                    "agent_id": "fixture-state-coordinator"}
        plan = {**identity, "expected_revision": 0,
                "requirements": [{"id": "r1", "text": "The state fixture remains available.",
                                  "deliverables": ["result.md"], "checks": ["c1"],
                                  "acceptance": "editorial"}],
                "deliverables": [{"path": "result.md", "profiles": [self.module]}],
                "checks": [{"id": "c1", "kind": "editorial", "definition_sha256": check_hash}],
                "inputs": [], "depends_on": [], "risk": "standard"}
        result = self.engine_request(home, code_root, "plan", plan)
        state = home / "constellation/state"
        self.assertTrue(state.is_dir())
        self.assertTrue(snapshot(state))
        return state, identity, result["revision"]


class BuildTests(BundleCase):
    def test_reproducible_bytes_hashes_modes_and_archive(self) -> None:
        rebuilt = self.root / "rebuilt"
        source = self.source_copy()
        for path in source.rglob("*"):
            if path.is_file():
                os.utime(path, (1000000000, 1000000000))
        manifest = build_bundle(rebuilt, MODULES, source_root=source)
        self.assertEqual(self.manifest, manifest)
        self.assertEqual(snapshot(self.bundle), snapshot(rebuilt))
        for relative, record in manifest["files"].items():
            self.assertEqual(record["sha256"], hashlib.sha256((rebuilt / relative).read_bytes()).hexdigest())
        first, second = self.root / "first.zip", self.root / "second.zip"
        write_archive(self.bundle, first)
        write_archive(rebuilt, second)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        with zipfile.ZipFile(first) as archive:
            self.assertEqual(archive.namelist(), sorted(["bundle.json", *manifest["files"]]))
            self.assertTrue(all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in archive.infolist()))
            unpacked = self.root / "unpacked"
            archive.extractall(unpacked)
            for info in archive.infolist():
                (unpacked / info.filename).chmod((info.external_attr >> 16) & 0o777)
        self.assertEqual(verify_bundle(unpacked), manifest)

    def test_each_module_is_independent_and_keeps_the_common_engine(self) -> None:
        for module in MODULES:
            with self.subTest(module=module):
                target = self.root / module
                manifest = build_bundle(target, [module], source_root=self.bundle)
                self.assertEqual(manifest["modules"], [module])
                self.assertTrue(CORE_FILES <= set(manifest["files"]))
                self.assertEqual(sorted(path.name for path in (target / "skills").iterdir()), [module])
                self.assertTrue((target / f"skills/{module}/references/workflow.md").is_file())
                self.assertEqual(verify_bundle(target), manifest)

    def test_common_gate_and_policy_are_source_bytes_and_manifest_has_one_native_location(self) -> None:
        for relative in ("review_gate.py", "review-policy.json"):
            self.assertEqual((self.bundle / relative).read_bytes(), (CODEX_DIR / relative).read_bytes())
        origin = CODEX_DIR / PLUGIN_MANIFEST if IS_DISTRIBUTED else SOURCE_DIR / "plugin.json"
        self.assertEqual((self.bundle / PLUGIN_MANIFEST).read_bytes(), origin.read_bytes())
        self.assertFalse((self.bundle / "plugin.json").exists())
        self.assertFalse((self.bundle / "ecosystem/plugin.json").exists())
        metadata = json.loads((self.bundle / PLUGIN_MANIFEST).read_text())
        self.assertEqual(metadata["skills"], "./skills/")
        self.assertEqual(metadata["hooks"], "./ecosystem/hooks.json")
        for path in self.bundle.rglob("*"):
            if path.is_file():
                self.assertNotIn(str(CODEX_DIR.parent).encode(), path.read_bytes())

    def test_installed_markdown_resources_close_inside_every_subset(self) -> None:
        for module in MODULES:
            target = self.root / ("links-" + module)
            build_bundle(target, [module], source_root=self.bundle)
            docs = list((target / "skills").rglob("*.md")) + list((target / "ecosystem/references").glob("*.md"))
            for path in docs:
                text = path.read_text()
                self.assertNotIn(str(CODEX_DIR.parent), text)
                for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
                    url = urlsplit(link.strip("<>"))
                    if url.scheme or not url.path:
                        continue
                    resolved = (path.parent / unquote(url.path)).resolve()
                    with self.subTest(module=module, file=path.name, link=link):
                        self.assertTrue(resolved.is_relative_to(target))
                        self.assertTrue(resolved.exists(), f"Broken installed resource: {path}: {link}")

    def test_private_and_unlisted_source_data_are_not_packaged(self) -> None:
        source = self.source_copy()
        marker = ("Synthetic private fixture " + self.root.name).encode()
        for relative in ("auth.json", "sessions/example.jsonl", "logs/daemon.log", ".env",
                         f"skills/{self.module}/private.md", "ecosystem/extra.py"):
            path = source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(marker)
        target = self.root / "filtered"
        build_bundle(target, MODULES, source_root=source)
        self.assertEqual(snapshot(self.bundle), snapshot(target))
        self.assertFalse(any(marker in value[1] for value in snapshot(target).values()))

    def test_missing_required_resource_rejects_without_creating_output(self) -> None:
        source = self.source_copy()
        (source / f"skills/{self.module}/references/workflow.md").unlink()
        output = self.root / "rejected"
        with self.assertRaises(BundleError):
            build_bundle(output, [self.module], source_root=source)
        self.assertFalse(output.exists())

    def test_source_file_and_directory_symlinks_are_rejected(self) -> None:
        source = self.source_copy()
        for relative in ("review_gate.py", f"skills/{self.module}/references"):
            path = source / relative
            held = self.root / ("held-" + path.name)
            path.rename(held)
            path.symlink_to(held, target_is_directory=held.is_dir())
            with self.subTest(relative=relative), self.assertRaises(BundleError):
                build_bundle(self.root / "rejected", [self.module], source_root=source)
            path.unlink()
            held.rename(path)
        linked = self.root / "linked-source"
        linked.symlink_to(source, target_is_directory=True)
        with self.assertRaises(BundleError):
            build_bundle(self.root / "rejected", MODULES, source_root=linked)

    def test_output_collisions_overlaps_and_symlinks_preserve_existing_files(self) -> None:
        before = snapshot(self.bundle)
        for output in (self.bundle, self.bundle / "nested", self.root):
            with self.subTest(output=output), self.assertRaises(BundleError):
                build_bundle(output, source_root=self.bundle)
        linked = self.root / "linked-output"
        linked.symlink_to(self.bundle, target_is_directory=True)
        with self.assertRaises(BundleError):
            build_bundle(linked, source_root=CODEX_DIR)
        self.assertEqual(snapshot(self.bundle), before)

    def test_bundle_integrity_rejects_changed_missing_extra_private_and_symlink_files(self) -> None:
        for mutation in ("changed", "missing", "extra", "private", "symlink", "mode"):
            target = self.root / mutation
            shutil.copytree(self.bundle, target)
            path = target / "review-policy.json"
            if mutation == "changed":
                path.write_text("{}\n")
            elif mutation == "missing":
                path.unlink()
            elif mutation == "extra":
                (target / "unexpected.txt").write_text("unexpected\n")
            elif mutation == "private":
                (target / "auth.json").write_text('{"synthetic":true}\n')
            elif mutation == "symlink":
                path.unlink()
                path.symlink_to(self.bundle / "review-policy.json")
            else:
                path.chmod(0o600)
            with self.subTest(mutation=mutation), self.assertRaises(BundleError):
                verify_bundle(target)

    def test_manifest_path_escape_and_invalid_module_selections_are_rejected(self) -> None:
        manifest_path = self.bundle / "bundle.json"
        original = manifest_path.read_bytes()
        for escape in ("../outside", "/tmp/outside", "skills/coding/../../outside"):
            value = json.loads(original)
            value["files"][escape] = {"sha256": "0" * 64, "mode": 0o644}
            write_json(manifest_path, value)
            with self.subTest(path=escape), self.assertRaises(BundleError):
                verify_bundle(self.bundle)
        manifest_path.write_bytes(original)
        for modules in ([], ["unknown"], [self.module, self.module]):
            with self.subTest(modules=modules), self.assertRaises(BundleError):
                build_bundle(self.root / "bad-modules", modules, source_root=self.bundle)
        subset = self.root / "one-module-only"
        build_bundle(subset, [self.module], source_root=self.bundle)
        absent = next(module for module in ALL_MODULES if module != self.module)
        with self.assertRaises(BundleError):
            build_bundle(self.root / "absent-module", [absent], source_root=subset)

    def test_native_manifest_paths_and_version_cannot_escape_the_package(self) -> None:
        source = self.source_copy()
        path = source / "ecosystem/plugin.json"
        original = json.loads(path.read_text())
        for field, value in (("skills", "../private"), ("hooks", "/tmp/unowned-hooks.json"),
                             ("version", "../escape"), ("version", "/tmp/escape")):
            write_json(path, {**original, field: value})
            with self.subTest(field=field, value=value), self.assertRaises(BundleError):
                build_bundle(self.root / "rejected-metadata", MODULES, source_root=source)
            self.assertFalse((self.root / "rejected-metadata").exists())

    def test_archive_rejects_existing_and_in_bundle_outputs(self) -> None:
        existing = self.root / "existing.zip"
        existing.write_bytes(b"independent archive")
        for path in (existing, self.bundle / "export.zip"):
            with self.subTest(path=path), self.assertRaises(BundleError):
                write_archive(self.bundle, path)
        self.assertEqual(existing.read_bytes(), b"independent archive")
        self.assertEqual(verify_bundle(self.bundle), self.manifest)


class SyntheticInstallationTests(BundleCase):
    def setUp(self) -> None:
        super().setUp()
        self.home = self.root / "receiver-home"
        self.home.mkdir()
        self.backend = SyntheticNativeClient(self.home)
        self.config = ('# Independent user formatting must survive.\nmodel = "synthetic-model"\n\n'
                       '[plugins."unrelated@example"]\nenabled = false\n')
        (self.home / "config.toml").write_text(self.config)
        for relative in ("AGENTS.md", "agents/user-agent.toml", "skills/user-skill/SKILL.md",
                         "plugins/cache/example/unrelated/1.0.0/resource.txt"):
            path = self.home / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("Independent fixture: " + relative + "\n")
        self.backend._save("marketplaces", [{"name": "example", "marketplaceSource": {
            "sourceType": "local", "source": str(self.root / "unrelated-marketplace")}}])
        self.backend._save("plugins", [{"pluginId": "unrelated@example", "version": "1.0.0", "enabled": False}])
        self.unrelated = {name: record for name, record in snapshot(self.home).items()
                          if name not in {"config.toml", "synthetic-native/plugins.json", "synthetic-native/marketplaces.json"}}

    def install(self, bundle: Path | None = None, modules: list[str] | None = None, check: bool = False) -> dict:
        return install_bundle(bundle or self.bundle, self.home, modules, check, self.backend)

    def assert_unrelated_preserved(self) -> None:
        after = snapshot(self.home)
        self.assertEqual({name: after.get(name) for name in self.unrelated}, self.unrelated)
        config = (self.home / "config.toml").read_text()
        self.assertTrue(config.startswith(self.config))
        self.assertFalse(tomllib.loads(config)["plugins"]["unrelated@example"]["enabled"])
        self.assertEqual([row for row in self.backend.plugins() if row["pluginId"] == "unrelated@example"],
                         [{"pluginId": "unrelated@example", "version": "1.0.0", "enabled": False}])
        self.assertEqual(len([row for row in self.backend.marketplaces() if row["name"] == "example"]), 1)

    def receipt(self) -> dict:
        return json.loads((self.home / "constellation/receipt.json").read_text())

    def cache(self, version: str | None = None) -> Path:
        version = version or self.receipt()["version"]
        return self.home / "plugins/cache/constellation/constellation" / version

    def test_install_repeat_and_update_use_native_registration_and_preserve_unrelated_files(self) -> None:
        first = self.install()
        self.assertEqual(first["status"], "installed")
        before = snapshot(self.home)
        repeated = self.install()
        self.assertIn(repeated["status"], {"updated", "unchanged"})
        self.assertEqual(snapshot(self.home), before)
        self.assertEqual(self.backend.mutations.count("add_marketplace"), 1)
        self.assertEqual(len([row for row in self.backend.plugins() if row["pluginId"] == PLUGIN_ID]), 1)
        updated = self.install(self.changed_bundle())
        self.assertEqual(updated["version"], "1.0.1")
        self.assertEqual(self.receipt()["version"], "1.0.1")
        self.assertIn("Updated synthetic release.", (self.cache() / f"skills/{self.module}/references/workflow.md").read_text())
        self.assert_unrelated_preserved()

    def test_receipt_hashes_actual_owned_files_and_has_no_duplicate_global_skills(self) -> None:
        self.install()
        receipt = self.receipt()
        self.assertEqual(receipt["modules"], list(MODULES))
        for group, base in (("catalog", self.home / "constellation/catalog"),
                            ("cache", self.cache()), ("agents", self.home / "agents")):
            for relative, record in receipt[group].items():
                path = base / relative
                self.assertEqual(record["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
                self.assertEqual(record["mode"], stat.S_IMODE(path.stat().st_mode))
        self.assertEqual(sorted(path.name for path in (self.home / "skills").iterdir()), ["user-skill"])
        self.assertEqual(sorted(path.name for path in (self.cache() / "skills").iterdir()), list(MODULES))
        self.assert_unrelated_preserved()

    def test_each_module_installs_alone_then_update_replaces_owned_subset(self) -> None:
        for module in MODULES:
            with self.subTest(module=module):
                self.install(modules=[module])
                self.assertEqual(self.receipt()["modules"], [module])
                self.assertEqual(sorted(path.name for path in (self.cache() / "skills").iterdir()), [module])
                self.assertTrue(CORE_FILES <= set(verify_bundle(self.cache())["files"]))
                actual_agents = {path.name for path in (self.home / "agents").glob("constellation-*")}
                self.assertEqual(actual_agents, set(self.receipt()["agents"]))
                self.assert_unrelated_preserved()

    def test_check_is_read_only_before_and_after_installation(self) -> None:
        for installed in (False, True):
            if installed:
                self.install()
            before, mutations = snapshot(self.home), list(self.backend.mutations)
            result = self.install(check=True)
            self.assertEqual(result["status"], "checked")
            self.assertEqual(snapshot(self.home), before)
            self.assertEqual(self.backend.mutations, mutations)

    def test_default_engine_state_survives_check_reinstall_and_update(self) -> None:
        self.install()
        state, identity, revision = self.create_default_state(self.home, self.cache())
        before = snapshot(state)
        self.assertEqual(self.install(check=True)["status"], "checked")
        self.assertEqual(snapshot(state), before)
        self.install()
        self.assertEqual(snapshot(state), before)
        self.install(self.changed_bundle())
        self.assertEqual(snapshot(state), before)
        self.assertEqual(self.engine_request(self.home, self.cache(), "status", identity)["revision"], revision)
        self.assertEqual(snapshot(state), before)
        self.assert_unrelated_preserved()

    def test_default_engine_state_created_before_first_install_is_preserved(self) -> None:
        state, identity, revision = self.create_default_state(self.home, self.bundle)
        before = snapshot(state)
        self.assertEqual(self.install(check=True)["status"], "checked")
        self.assertEqual(snapshot(state), before)
        self.assertEqual(self.install()["status"], "installed")
        self.assertEqual(snapshot(state), before)
        self.assertEqual(self.engine_request(self.home, self.cache(), "status", identity)["revision"], revision)
        self.assertEqual(snapshot(state), before)
        self.assert_unrelated_preserved()

    def test_hardlinked_owned_agent_update_preserves_external_inode(self) -> None:
        self.install()
        managed = self.home / "agents/constellation-reviewer.toml"
        external = self.root / "external-agent.toml"
        os.link(managed, external)
        self.assertTrue(os.path.samefile(managed, external))
        content, mode = external.read_bytes(), stat.S_IMODE(external.stat().st_mode)
        self.install(self.changed_bundle(change_agent=True))
        self.assertEqual(external.read_bytes(), content)
        self.assertEqual(stat.S_IMODE(external.stat().st_mode), mode)
        self.assertFalse(os.path.samefile(managed, external))
        self.assertIn(b"Updated synthetic reviewer release.", managed.read_bytes())
        self.assert_unrelated_preserved()

    def test_hardlink_created_after_update_is_not_overwritten_by_rollback(self) -> None:
        self.install()
        before = snapshot(self.home)
        managed = self.home / "agents/constellation-reviewer.toml"
        external = self.root / "external-updated-agent.toml"
        updated = self.changed_bundle(change_agent=True)
        updated_content = (updated / "ecosystem/agents/reviewer.toml").read_bytes()

        def fail_receipt(_path: Path, _value: dict) -> None:
            self.assertEqual(managed.read_bytes(), updated_content)
            os.link(managed, external)
            raise OSError("Synthetic receipt failure after agent replacement")

        with patch.object(installer, "_write_json", side_effect=fail_receipt):
            with self.assertRaisesRegex(InstallError, "restored"):
                self.install(updated)
        self.assertTrue(external.is_file())
        self.assertEqual(external.read_bytes(), updated_content)
        self.assertFalse(os.path.samefile(managed, external))
        self.assertEqual(snapshot(self.home), before)
        self.assert_unrelated_preserved()

    def test_disabled_configuration_is_preserved_before_any_native_mutation(self) -> None:
        self.install()
        self.backend._enable(False)
        before, mutations = snapshot(self.home), list(self.backend.mutations)
        with self.assertRaises(InstallError):
            self.install()
        self.assertEqual(snapshot(self.home), before)
        self.assertEqual(self.backend.mutations, mutations)
        self.assertFalse(tomllib.loads((self.home / "config.toml").read_text())["plugins"][PLUGIN_ID]["enabled"])

    def test_disabled_native_registration_is_preserved_even_without_config_flag(self) -> None:
        self.install()
        rows = self.backend.plugins()
        next(row for row in rows if row["pluginId"] == PLUGIN_ID)["enabled"] = False
        self.backend._save("plugins", rows)
        before, mutations = snapshot(self.home), list(self.backend.mutations)
        with self.assertRaises(InstallError):
            self.install()
        self.assertEqual(snapshot(self.home), before)
        self.assertEqual(self.backend.mutations, mutations)

    def test_same_name_marketplace_from_another_source_is_not_replaced(self) -> None:
        rows = self.backend.marketplaces()
        rows.append({"name": "constellation", "marketplaceSource": {
            "sourceType": "local", "source": str(self.root / "independent-catalog")}})
        self.backend._save("marketplaces", rows)
        before = snapshot(self.home)
        with self.assertRaises(InstallError):
            self.install()
        self.assertEqual(snapshot(self.home), before)
        self.assertEqual(self.backend.mutations, [])

    def test_preexisting_agent_destination_is_not_adopted(self) -> None:
        (self.home / "agents/constellation-reviewer.toml").write_text("independently owned\n")
        before = snapshot(self.home)
        with self.assertRaises(InstallError):
            self.install()
        self.assertEqual(snapshot(self.home), before)
        self.assertEqual(self.backend.mutations, [])

    def test_modified_catalog_cache_or_agent_prevents_update_without_mutation(self) -> None:
        self.install()
        targets = (self.home / "constellation/catalog/plugins/constellation/review-policy.json",
                   self.cache() / f"skills/{self.module}/SKILL.md", self.home / "agents/constellation-reviewer.toml")
        for target in targets:
            original = target.read_bytes()
            target.write_bytes(original + b"\nIndependent local edit.\n")
            before, mutations = snapshot(self.home), list(self.backend.mutations)
            with self.subTest(target=target), self.assertRaises(InstallError):
                self.install()
            self.assertEqual(snapshot(self.home), before)
            self.assertEqual(self.backend.mutations, mutations)
            target.write_bytes(original)

    def test_extra_native_version_is_preserved_before_destructive_native_add(self) -> None:
        self.install()
        foreign = self.cache().parent / "independent-version" / "sentinel"
        foreign.parent.mkdir()
        foreign.write_text("Independently retained native cache.\n")
        before, mutations = snapshot(self.home), list(self.backend.mutations)
        with self.assertRaises(InstallError):
            self.install()
        self.assertEqual(snapshot(self.home), before)
        self.assertEqual(self.backend.mutations, mutations)

    def test_check_missing_home_does_not_create_it_and_bundle_overlap_is_rejected(self) -> None:
        absent = self.root / "absent-home"
        client = SyntheticNativeClient(absent)
        result = install_bundle(self.bundle, absent, check=True, client=client)
        self.assertEqual(result["status"], "checked")
        self.assertFalse(absent.exists())
        before = snapshot(self.bundle)
        with self.assertRaises(InstallError):
            install_bundle(self.bundle, self.bundle, client=SyntheticNativeClient(self.bundle))
        self.assertEqual(snapshot(self.bundle), before)

    def test_symlinked_managed_destination_is_rejected_without_touching_target(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "sentinel").write_text("unrelated\n")
        (self.home / "constellation").symlink_to(outside, target_is_directory=True)
        before, external = snapshot(self.home), snapshot(outside)
        with self.assertRaises(InstallError):
            self.install()
        self.assertEqual(snapshot(self.home), before)
        self.assertEqual(snapshot(outside), external)
        self.assertEqual(self.backend.mutations, [])

    def test_invalid_or_missing_receipt_never_adopts_an_existing_installation(self) -> None:
        self.install()
        receipt = self.home / "constellation/receipt.json"
        for value in (None, {"schema": 1}, {"schema": 999}):
            if value is None:
                receipt.unlink()
            else:
                write_json(receipt, value)
            before, mutations = snapshot(self.home), list(self.backend.mutations)
            with self.subTest(receipt=value), self.assertRaises(InstallError):
                self.install()
            self.assertEqual(snapshot(self.home), before)
            self.assertEqual(self.backend.mutations, mutations)

    def test_first_install_partial_native_failures_roll_back_and_do_not_write_receipt(self) -> None:
        for when in ("before", "after"):
            for operation in ("add_marketplace", "add_plugin"):
                if when == "before":
                    self.backend.fail_before_once = operation
                else:
                    self.backend.fail_once = operation
                before = snapshot(self.home)
                with self.subTest(operation=operation, when=when), self.assertRaises(InstallError):
                    self.install()
                after = snapshot(self.home)
                after.pop("constellation/.install.lock", None)
                before.pop("constellation/.install.lock", None)
                self.assertEqual(after, before)
                self.assertFalse((self.home / "constellation/receipt.json").exists())
                self.assert_unrelated_preserved()

    def test_failed_update_restores_prior_receipt_catalog_agents_and_native_state(self) -> None:
        self.install()
        updated = self.changed_bundle()
        before = snapshot(self.home)
        self.backend.fail_once = "add_plugin"
        with self.assertRaises(InstallError):
            self.install(updated)
        self.assertEqual(snapshot(self.home), before)
        self.assertEqual(self.receipt()["version"], "1.0.0")
        self.assert_unrelated_preserved()

    def test_native_cache_mismatch_is_rejected_and_compensated(self) -> None:
        before = snapshot(self.home)
        self.backend.corrupt_cache_once = True
        with self.assertRaises(InstallError):
            self.install()
        after = snapshot(self.home)
        after.pop("constellation/.install.lock", None)
        self.assertEqual(after, before)
        self.assertFalse((self.home / "constellation/receipt.json").exists())

    def test_failed_compensation_is_reported_as_incomplete_not_success(self) -> None:
        self.backend.fail_once = "add_plugin"
        self.backend.fail_rollback = True
        with self.assertRaisesRegex(InstallError, "rollback.*attention"):
            self.install()
        self.assertFalse((self.home / "constellation/receipt.json").exists())
        self.assertTrue((self.home / "constellation/catalog/.agents/plugins/marketplace.json").is_file())
        self.assertTrue(any(row["name"] == "constellation" for row in self.backend.marketplaces()))
        self.assert_unrelated_preserved()

    def test_receiver_can_run_and_rebuild_without_original_source_or_git(self) -> None:
        source = self.source_copy()
        carried = self.root / "carried"
        build_bundle(carried, [self.module], source_root=source)
        self.install(carried)
        shutil.rmtree(source)
        shutil.rmtree(carried)
        receiver = self.root / "receiver-project"
        receiver.mkdir()
        env = dict(os.environ)
        env["CODEX_HOME"] = str(self.home)
        env.pop("PYTHONPATH", None)
        env.pop("CODEX_THREAD_ID", None)
        self.assertFalse((receiver / ".git").exists())
        # Deny Python reads of the original checkout as well as deleting the
        # transported source. This is an audit-based regression guard, not an OS
        # sandbox claim; installed imports must be sufficient on their own.
        isolated_runner = textwrap.dedent('''\
            import json, os, pathlib, runpy, sys
            forbidden = tuple(pathlib.Path(p).resolve() for p in json.loads(sys.argv[1]))
            def deny_source(event, args):
                if event not in {"open", "os.listdir", "os.scandir"} or not args:
                    return
                value = args[0]
                if not isinstance(value, (str, bytes, os.PathLike)):
                    return
                path = pathlib.Path(os.fsdecode(value)).resolve()
                if any(path == root or root in path.parents for root in forbidden):
                    raise RuntimeError("Original source is unavailable in this receiver test")
            sys.addaudithook(deny_source)
            sys.argv = sys.argv[2:]
            runpy.run_path(sys.argv[0], run_name="__main__")
            ''')
        runner = [sys.executable, "-I", "-B", "-c", isolated_runner,
                  json.dumps([str(CODEX_DIR.parent), str(source), str(carried)])]
        (receiver / "result.py").write_text("answer = 42\n")
        argv = [sys.executable, "-I", "-c",
                "from pathlib import Path; assert Path('result.py').read_text() == 'answer = 42\\n'"]
        check_hash = hashlib.sha256(json.dumps(argv, sort_keys=True, separators=(",", ":"),
                                                ensure_ascii=False).encode()).hexdigest()
        request = {
            "session_id": "fixture-receiver-session", "task_id": "fixture-receiver-task",
            "agent_id": "fixture-receiver-coordinator", "expected_revision": 0,
            "requirements": [{"id": "r1", "text": "The receiver contains the expected answer.",
                              "deliverables": ["result.py"], "checks": ["c1"], "acceptance": "behavior"}],
            "deliverables": [{"path": "result.py", "profiles": [self.module]}],
            "checks": [{"id": "c1", "kind": "behavior", "definition_sha256": check_hash}],
            "inputs": [], "depends_on": [], "risk": "standard",
        }
        cli_args = [str(self.cache() / "ecosystem/cli.py"), "--root", str(receiver),
                    "--state-dir", str(self.root / "receiver-state")]
        cli = subprocess.run([*runner, *cli_args, "plan"], input=json.dumps(request),
                             cwd=receiver, env=env, capture_output=True, text=True, timeout=20)
        self.assertEqual(cli.returncode, 0, cli.stderr + cli.stdout)
        planned = json.loads(cli.stdout)
        self.assertTrue(planned["ok"])
        status_request = {key: request[key] for key in ("session_id", "task_id", "agent_id")}
        status = subprocess.run([*runner, *cli_args, "status"], input=json.dumps(status_request),
                                cwd=receiver, env=env, capture_output=True, text=True, timeout=20)
        self.assertEqual(status.returncode, 0, status.stderr + status.stdout)
        self.assertEqual(json.loads(status.stdout)["revision"], planned["revision"])
        rebuilt = self.root / "receiver-built"
        built = subprocess.run([*runner, str(self.cache() / "ecosystem/build.py"),
                                "--output", str(rebuilt)], cwd=receiver, env=env,
                               capture_output=True, text=True, timeout=20)
        self.assertEqual(built.returncode, 0, built.stderr)
        self.assertEqual(verify_bundle(rebuilt)["modules"], [self.module])
        self.assertEqual(snapshot(rebuilt), snapshot(self.cache()))
        self.assertFalse((receiver / ".git").exists())


class NativeAdapterSubprocessTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="constellation-native-adapter-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.home = self.root / "home"
        self.home.mkdir()
        self.executable = self.root / "synthetic-codex"
        self.executable.write_text("#!" + sys.executable + "\n" + textwrap.dedent('''\
            import json, os, pathlib, sys
            home = pathlib.Path(os.environ["CODEX_HOME"])
            arguments = sys.argv[1:]
            with (home / "synthetic-calls.jsonl").open("a") as stream:
                stream.write(json.dumps({"args": arguments, "cwd": os.getcwd(),
                    "home": str(home), "thread_present": "CODEX_THREAD_ID" in os.environ}) + "\\n")
            if (home / "fail").exists():
                print("synthetic private stdout must not leak")
                raise SystemExit(7)
            if (home / "bad-json").exists():
                print("not JSON")
            elif arguments[:3] == ["plugin", "marketplace", "list"]:
                print(json.dumps({"marketplaces": []}))
            elif arguments[:2] == ["plugin", "list"]:
                print(json.dumps({"installed": []}))
            else:
                print("{}")
            '''))
        self.executable.chmod(0o755)
        self.client = NativeClient(self.home, str(self.executable), self.root, timeout=5)

    def test_native_adapter_uses_explicit_home_cwd_and_real_cli_subprocesses(self) -> None:
        self.assertEqual(self.client.marketplaces(), [])
        self.assertEqual(self.client.plugins(), [])
        self.client.add_marketplace(self.root / "catalog")
        self.client.add_plugin()
        self.client.remove_plugin()
        self.client.remove_marketplace()
        calls = [json.loads(line) for line in (self.home / "synthetic-calls.jsonl").read_text().splitlines()]
        self.assertEqual([row["args"] for row in calls], [
            ["plugin", "marketplace", "list", "--json"], ["plugin", "list", "--json"],
            ["plugin", "marketplace", "add", str(self.root / "catalog"), "--json"],
            ["plugin", "add", PLUGIN_ID, "--json"], ["plugin", "remove", PLUGIN_ID, "--json"],
            ["plugin", "marketplace", "remove", "constellation", "--json"],
        ])
        self.assertTrue(all(row["home"] == str(self.home) and row["cwd"] == str(self.root) for row in calls))
        self.assertTrue(all(row["thread_present"] is False for row in calls))

    def test_cli_failure_and_invalid_json_are_rejected_without_echoing_output(self) -> None:
        for flag in ("fail", "bad-json"):
            (self.home / flag).touch()
            with self.subTest(flag=flag), self.assertRaises(NativeError) as raised:
                self.client.plugins()
            self.assertNotIn("synthetic private", str(raised.exception))
            (self.home / flag).unlink()


@unittest.skipUnless(shutil.which("codex"), "Native Codex executable is unavailable; synthetic tests are separate")
class RealNativeInstallationTests(BundleCase):
    def test_real_native_install_discovery_repeat_and_read_only_check(self) -> None:
        home = self.root / "native-home"
        home.mkdir()
        receiver = self.root / "native-receiver"
        receiver.mkdir()
        client = NativeClient(home, shutil.which("codex") or "codex", receiver, timeout=45)
        installed = install_bundle(self.bundle, home, client=client)
        self.assertEqual(installed["status"], "installed")
        discovery = client.inspect(receiver, Path(installed["catalog"]) / ".agents/plugins/marketplace.json")
        self.assertEqual(discovery["errors"], 0)
        skills = discovery["skills"]
        self.assertEqual(sorted(skill["name"] for skill in skills), ["constellation:" + module for module in MODULES])
        self.assertTrue(all(skill["enabled"] for skill in skills))
        self.assertTrue(all(Path(skill["path"]).is_relative_to(home / "plugins/cache") for skill in skills))
        self.assertEqual(discovery["plugin"]["id"], PLUGIN_ID)
        self.assertTrue(discovery["plugin"]["installed"])
        self.assertTrue(discovery["plugin"]["enabled"])
        self.assertEqual({hook["eventName"] for hook in discovery["hooks"]},
                         {"userPromptSubmit", "preToolUse", "subagentStart", "subagentStop", "stop"})
        self.assertTrue(all(hook["trustStatus"] == "untrusted" for hook in discovery["hooks"]))
        state, identity, revision = self.create_default_state(
            home, home / "plugins/cache/constellation/constellation" / installed["version"])
        state_before = snapshot(state)
        install_bundle(self.bundle, home, client=client)
        self.assertEqual(snapshot(state), state_before)
        self.assertEqual(len([row for row in client.marketplaces() if row["name"] == "constellation"]), 1)
        self.assertEqual(len([row for row in client.plugins() if row["pluginId"] == PLUGIN_ID]), 1)
        before = snapshot(home)
        self.assertEqual(install_bundle(self.bundle, home, check=True, client=client)["status"], "checked")
        self.assertEqual(snapshot(home), before)
        updated = install_bundle(self.changed_bundle(), home, client=client)
        self.assertEqual(snapshot(state), state_before)
        cache = home / "plugins/cache/constellation/constellation" / updated["version"]
        self.assertEqual(self.engine_request(home, cache, "status", identity)["revision"], revision)
        self.assertEqual(snapshot(state), state_before)
        self.assertTrue(all(not (home / "skills" / module).exists() for module in MODULES))
        self.assertFalse((receiver / ".git").exists())


@unittest.skipUnless(shutil.which("codex"), "Native Codex executable is unavailable; source exclusion requires real RPC")
class RealNativeSourceExclusionTests(BundleCase):
    def preference_snapshot(self, home: Path) -> dict[str, tuple[str, bytes | str, int]]:
        """Track settings and installed content, excluding native housekeeping.

        App-server reads may create its own logs and temporary repositories. This
        test neither reads those files nor treats their lifecycle as a skill edit.
        """
        result = {}
        for name in ("config.toml", "agents", "skills", "plugins", "constellation"):
            path = home / name
            if path.is_file():
                result[name] = ("file", path.read_bytes(), stat.S_IMODE(path.stat().st_mode))
            elif path.is_dir():
                result.update({name + "/" + relative: record for relative, record in snapshot(path).items()})
        return result

    def rpc(self, client: NativeClient, method: str, parameters: dict) -> dict:
        connection = native_adapter._Rpc(client)
        try:
            return connection.call(method, parameters)
        finally:
            connection.close()

    def prepare_source(self, *, install: bool = True,
                       modules: list[str] | None = None) -> tuple[Path, Path, NativeClient, Path]:
        source = self.source_copy("source-project/.codex")
        home = self.root / "source-exclusion-home"
        home.mkdir()
        (home / "config.toml").write_text(
            '# Independent fixture preferences.\nmodel = "fixture-local-model"\n'
            'model_reasoning_effort = "high"\n')
        foreign = home / "skills/fixture-independent/SKILL.md"
        foreign.parent.mkdir(parents=True)
        foreign.write_text('---\nname: fixture-independent\n'
                           'description: "Independent source exclusion fixture."\n---\n'
                           'This fixture is independently owned.\n')
        client = NativeClient(home, shutil.which("codex") or "codex", source.parent, timeout=45)
        if install:
            install_bundle(self.bundle, home, modules, client=client)
        self.rpc(client, "skills/config/write", {"path": str(foreign), "enabled": False})
        return source, home, client, foreign

    def skill_rows(self, client: NativeClient, project: Path) -> dict[Path, dict]:
        response = self.rpc(client, "skills/list", {"cwds": [str(project)], "forceReload": True})
        result = {}
        for row in response.get("data", []):
            self.assertEqual(row.get("errors", []), [])
            for skill in row.get("skills", []):
                path = Path(skill["path"]).resolve()
                if path.is_relative_to(self.root):
                    self.assertNotIn(path, result)
                    result[path] = skill
        return result

    def test_native_exclusion_disables_only_source_preserves_foreign_preferences_and_repeats(self) -> None:
        source, home, client, foreign = self.prepare_source()
        source_paths = {source / "skills" / module / "SKILL.md" for module in MODULES}
        before_rows = self.skill_rows(client, source.parent)
        self.assertTrue(all(before_rows[path]["enabled"] is True for path in source_paths))
        self.assertFalse(before_rows[foreign]["enabled"])
        plugin_paths = {path for path, row in before_rows.items()
                        if row["name"] in {"constellation:" + module for module in MODULES}}
        self.assertEqual(len(plugin_paths), len(MODULES))
        self.assertTrue(all(before_rows[path]["enabled"] is True for path in plugin_paths))
        source_before, cache_before = snapshot(source), snapshot(home / "plugins/cache")
        agents_before = snapshot(home / "agents")
        configuration_before = tomllib.loads((home / "config.toml").read_text())

        result = client.exclude_source_skills(source)
        self.assertEqual(result["status"], "excluded", result)
        self.assertEqual(result["modules"], list(MODULES))
        self.assertEqual({Path(row["path"]) for row in result["paths"]}, source_paths)
        self.assertTrue(all(row["enabled"] is False and row["verified"] for row in result["paths"]))
        self.assertTrue(all(row["write_attempted"] and row["write_confirmed"] for row in result["paths"]))
        after_rows = self.skill_rows(client, source.parent)
        self.assertTrue(all(after_rows[path]["enabled"] is False for path in source_paths))
        self.assertTrue(all(after_rows[path]["enabled"] is True for path in plugin_paths))
        self.assertFalse(after_rows[foreign]["enabled"])
        self.assertEqual(snapshot(source), source_before)
        self.assertEqual(snapshot(home / "plugins/cache"), cache_before)
        self.assertEqual(snapshot(home / "agents"), agents_before)
        configuration_after = tomllib.loads((home / "config.toml").read_text())
        excluded_rules = [row for row in configuration_after["skills"]["config"]
                          if Path(row["path"]) in source_paths]
        self.assertEqual(len(excluded_rules), len(MODULES))
        self.assertTrue(all(row["enabled"] is False for row in excluded_rules))
        configuration_after["skills"]["config"] = [row for row in configuration_after["skills"]["config"]
                                                    if Path(row["path"]) not in source_paths]
        self.assertEqual(configuration_after, configuration_before)
        self.assertTrue((home / "config.toml").read_text().startswith("# Independent fixture preferences.\n"))

        before_repeat = self.preference_snapshot(home)
        repeated = client.exclude_source_skills(source)
        self.assertEqual(repeated["status"], "excluded", repeated)
        self.assertTrue(all(not row["write_attempted"] for row in repeated["paths"]))
        self.assertEqual(self.preference_snapshot(home), before_repeat)
        cli = subprocess.run(
            [sys.executable, "-I", "-B", str(SOURCE_DIR / "native.py"),
             "--codex-home", str(home), "--cwd", str(source.parent),
             "--codex", shutil.which("codex") or "codex", "--exclude-source-root", str(source)],
            cwd=source.parent, capture_output=True, text=True, timeout=45)
        self.assertEqual(cli.returncode, 0, cli.stdout + cli.stderr)
        cli_result = json.loads(cli.stdout)
        self.assertEqual(cli_result["status"], "excluded")
        self.assertTrue(all(not row["write_attempted"] for row in cli_result["paths"]))
        self.assertEqual(self.preference_snapshot(home), before_repeat)

    def test_exclusion_selects_only_modules_present_in_the_enabled_installation(self) -> None:
        source, home, client, foreign = self.prepare_source(modules=[self.module])
        absent = next(module for module in ALL_MODULES if module != self.module)
        before = self.preference_snapshot(home)
        with self.assertRaises(NativeError):
            client.exclude_source_skills(source, modules=[absent])
        self.assertEqual(self.preference_snapshot(home), before)
        result = client.exclude_source_skills(source)
        self.assertEqual(result["status"], "excluded", result)
        self.assertEqual(result["modules"], [self.module])
        self.assertEqual([Path(row["path"]) for row in result["paths"]],
                         [source / "skills" / self.module / "SKILL.md"])
        rows = self.skill_rows(client, source.parent)
        for module in MODULES:
            self.assertIs(rows[source / "skills" / module / "SKILL.md"]["enabled"], module != self.module)
        self.assertFalse(rows[foreign]["enabled"])
        plugin_rows = [row for row in rows.values() if row["name"].startswith("constellation:")]
        self.assertEqual([row["name"] for row in plugin_rows], ["constellation:" + self.module])
        self.assertTrue(plugin_rows[0]["enabled"])

    def test_lost_native_write_acknowledgement_reports_partial_and_verifies_persisted_flags(self) -> None:
        source, home, client, foreign = self.prepare_source()
        original_call = native_adapter._Rpc.call
        injected = False

        def lose_first_write_acknowledgement(connection: object, method: str, parameters: dict) -> dict:
            nonlocal injected
            response = original_call(connection, method, parameters)
            if method == "skills/config/write" and not injected:
                injected = True
                raise NativeError("Synthetic lost acknowledgement after the real native write")
            return response

        with patch.object(native_adapter._Rpc, "call", new=lose_first_write_acknowledgement):
            result = client.exclude_source_skills(source)
        self.assertTrue(injected)
        self.assertEqual(result["status"], "partial", result)
        self.assertIn("error", result)
        self.assertTrue(result["paths"][0]["write_attempted"])
        self.assertFalse(result["paths"][0]["write_confirmed"])
        self.assertTrue(result["paths"][0]["verified"])
        self.assertTrue(all(not row["write_attempted"] for row in result["paths"][1:]))
        rows = self.skill_rows(client, source.parent)
        self.assertFalse(rows[source / "skills" / MODULES[0] / "SKILL.md"]["enabled"])
        self.assertTrue(all(rows[source / "skills" / module / "SKILL.md"]["enabled"] is True
                            for module in MODULES[1:]))
        self.assertTrue(all(row["enabled"] is True for row in rows.values()
                            if row["name"].startswith("constellation:")))
        self.assertFalse(rows[foreign]["enabled"])

    def test_source_mismatch_unsafe_paths_and_bundle_are_rejected_before_configuration_changes(self) -> None:
        source, home, client, _foreign = self.prepare_source()
        skill = source / "skills" / self.module / "SKILL.md"
        original = skill.read_bytes()
        skill.write_bytes(original + b"\nIndependently modified source skill.\n")
        before = self.preference_snapshot(home)
        with self.assertRaises(NativeError):
            client.exclude_source_skills(source)
        self.assertEqual(self.preference_snapshot(home), before)
        skill.write_bytes(original)

        outside = self.root / "independent-source-skill.md"
        outside.write_bytes(original)
        skill.unlink()
        skill.symlink_to(outside)
        before, outside_before = self.preference_snapshot(home), outside.read_bytes()
        with self.assertRaises(NativeError):
            client.exclude_source_skills(source)
        self.assertEqual(self.preference_snapshot(home), before)
        self.assertEqual(outside.read_bytes(), outside_before)
        skill.unlink()
        skill.write_bytes(original)

        source_alias = self.root / "source-alias"
        source_alias.symlink_to(source, target_is_directory=True)
        cache_root = home / "plugins/cache/constellation/constellation/1.0.0"
        for unsafe in (source_alias, self.bundle, cache_root, self.root):
            with self.subTest(source=unsafe):
                before = self.preference_snapshot(home)
                with self.assertRaises(NativeError):
                    client.exclude_source_skills(unsafe)
                self.assertEqual(self.preference_snapshot(home), before)

        manifest = source / "ecosystem/plugin.json"
        original_manifest = manifest.read_bytes()
        value = json.loads(original_manifest)
        value["name"] = "independent-plugin"
        write_json(manifest, value)
        before = self.preference_snapshot(home)
        with self.assertRaises(NativeError):
            client.exclude_source_skills(source)
        self.assertEqual(self.preference_snapshot(home), before)
        manifest.write_bytes(original_manifest)

    def test_missing_or_disabled_installed_plugin_cannot_disable_source_skills(self) -> None:
        source, home, client, _foreign = self.prepare_source(install=False)
        before = self.preference_snapshot(home)
        with self.assertRaises(NativeError):
            client.exclude_source_skills(source)
        self.assertEqual(self.preference_snapshot(home), before)

        install_bundle(self.bundle, home, client=client)
        configuration = home / "config.toml"
        text = configuration.read_text()
        table = '[plugins."constellation@constellation"]\nenabled = true'
        self.assertIn(table, text)
        configuration.write_text(text.replace(table, table.replace("true", "false"), 1))
        self.assertFalse(next(row for row in client.plugins() if row["pluginId"] == PLUGIN_ID)["enabled"])
        before = self.preference_snapshot(home)
        with self.assertRaises(NativeError):
            client.exclude_source_skills(source)
        self.assertEqual(self.preference_snapshot(home), before)
        rows = self.skill_rows(client, source.parent)
        self.assertTrue(all(rows[source / "skills" / module / "SKILL.md"]["enabled"] is True
                            for module in MODULES))

    def assert_resource_divergence_is_rejected(self, relative: str) -> None:
        source, home, client, _foreign = self.prepare_source()
        path = source / relative
        original = path.read_bytes()
        source_skill = source / "skills" / self.module / "SKILL.md"
        version = json.loads((self.bundle / PLUGIN_MANIFEST).read_text())["version"]
        installed_skill = (home / "plugins/cache/constellation/constellation" / version
                           / "skills" / self.module / "SKILL.md")
        self.assertEqual(source_skill.read_bytes(), installed_skill.read_bytes())
        before = self.preference_snapshot(home)
        path.write_bytes(original + b"\n# Independently changed source resource.\n")
        try:
            with self.assertRaises(NativeError):
                client.exclude_source_skills(source)
            self.assertEqual(self.preference_snapshot(home), before)
            rows = self.skill_rows(client, source.parent)
            self.assertTrue(all(rows[source / "skills" / module / "SKILL.md"]["enabled"] is True
                                for module in MODULES))
        finally:
            path.write_bytes(original)
        self.assertEqual(client.exclude_source_skills(source)["status"], "excluded")

    def test_changed_workflow_with_identical_skill_metadata_cannot_be_excluded(self) -> None:
        self.assert_resource_divergence_is_rejected(f"skills/{self.module}/references/workflow.md")

    def test_changed_shared_protocol_with_identical_skill_metadata_cannot_be_excluded(self) -> None:
        self.assert_resource_divergence_is_rejected("ecosystem/references/protocol.md")

    def test_changed_shared_runtime_with_identical_skill_metadata_cannot_be_excluded(self) -> None:
        self.assert_resource_divergence_is_rejected("ecosystem/core.py")

    def test_changed_shared_reviewer_with_identical_skill_metadata_cannot_be_excluded(self) -> None:
        self.assert_resource_divergence_is_rejected("ecosystem/agents/reviewer.toml")

    def test_changed_selected_module_agent_with_identical_skill_metadata_cannot_be_excluded(self) -> None:
        role = {"coding": "coder", "mathematics": "mathematician", "writter": "editor"}[self.module]
        self.assert_resource_divergence_is_rejected(f"ecosystem/agents/{role}.toml")

    def test_source_build_inventory_is_compared_as_data_and_never_executed(self) -> None:
        source, home, client, _foreign = self.prepare_source()
        path = source / "ecosystem/build.py"
        original = path.read_bytes()
        marker = self.root / "untrusted-inventory-was-executed"
        before = self.preference_snapshot(home)
        path.write_text(f"from pathlib import Path\nPath({str(marker)!r}).write_text('unexpected execution')\n")
        try:
            with self.assertRaises(NativeError):
                client.exclude_source_skills(source)
            self.assertFalse(marker.exists())
            self.assertEqual(self.preference_snapshot(home), before)
        finally:
            path.write_bytes(original)
        self.assertEqual(client.exclude_source_skills(source)["status"], "excluded")

    @unittest.skipUnless(set(MODULES) & {"mathematics", "writter"},
                         "Ontology closure requires mathematics or writter in this distribution")
    def test_changed_shared_ontology_with_identical_skill_metadata_cannot_be_excluded(self) -> None:
        self.assert_resource_divergence_is_rejected("ecosystem/references/ontology.md")

    @unittest.skipUnless(len(MODULES) > 1,
                         "An unselected source module requires at least two distributed modules")
    def test_changed_unselected_module_does_not_prevent_excluding_the_installed_subset(self) -> None:
        source, home, client, _foreign = self.prepare_source(modules=[self.module])
        unselected = next(module for module in MODULES if module != self.module)
        path = source / "skills" / unselected / "references/workflow.md"
        path.write_bytes(path.read_bytes() + b"\nUnselected source workflow change.\n")
        result = client.exclude_source_skills(source)
        self.assertEqual(result["status"], "excluded", result)
        self.assertEqual(result["modules"], [self.module])
        rows = self.skill_rows(client, source.parent)
        self.assertFalse(rows[source / "skills" / self.module / "SKILL.md"]["enabled"])
        self.assertTrue(rows[source / "skills" / unselected / "SKILL.md"]["enabled"])


@unittest.skipIf(IS_DISTRIBUTED, "Source-only distribution harness; nested execution would recurse")
class DistributedSuiteTests(unittest.TestCase):
    def test_full_and_each_module_run_their_shipped_suites_without_mutating_bundle(self) -> None:
        with tempfile.TemporaryDirectory(prefix="constellation-distributed-suite-") as temporary:
            root = Path(temporary).resolve()
            selections = [("full", ALL_MODULES), *((module, (module,)) for module in ALL_MODULES)]
            for name, modules in selections:
                with self.subTest(distribution=name):
                    bundle = root / name
                    manifest = build_bundle(bundle, modules, source_root=CODEX_DIR)
                    before = snapshot(bundle)
                    receiver = root / (name + "-receiver")
                    receiver.mkdir()
                    environment = dict(os.environ)
                    environment["CODEX_HOME"] = str(root / (name + "-home"))
                    environment["PYTHONDONTWRITEBYTECODE"] = "1"
                    environment.pop("CODEX_THREAD_ID", None)
                    environment.pop("PYTHONPATH", None)
                    result = subprocess.run(
                        [sys.executable, "-I", "-B", "-m", "unittest", "discover", "-s",
                         str(bundle / "ecosystem/tests"), "-v"], cwd=receiver, env=environment,
                        capture_output=True, text=True, timeout=180)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    summary = re.search(r"^Ran (\d+) tests? in ([\d.]+)s$", result.stderr, re.MULTILINE)
                    self.assertIsNotNone(summary, result.stderr)
                    assert summary is not None
                    self.assertGreater(int(summary[1]), 0)
                    skips = re.search(r"OK \(skipped=(\d+)\)", result.stderr)
                    print(f"Distributed {name}: {summary[1]} tests in {summary[2]}s; "
                          f"{skips[1] if skips else '0'} explicit skips.")
                    self.assertEqual(verify_bundle(bundle), manifest)
                    self.assertEqual(snapshot(bundle), before)
                    self.assertFalse((receiver / ".git").exists())


if __name__ == "__main__":
    unittest.main()

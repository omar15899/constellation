"""Filesystem-real package tests; synthetic native behavior is explicitly marked.

The synthetic backend is not evidence of Codex discovery. Real native discovery
has a separate test using only a temporary CODEX_HOME and no conversation/thread.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
from itertools import combinations
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
import time
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
import build as builder
from install import InstallError, install_bundle
import install as installer
from native import NativeClient, NativeError
import native as native_adapter


ALL_MODULES = ("coding", "mathematics", "quant-research", "writter")
IS_DISTRIBUTED = (CODEX_DIR / "bundle.json").is_file()
MODULES = (tuple(json.loads((CODEX_DIR / "bundle.json").read_text())["modules"])
           if IS_DISTRIBUTED else ALL_MODULES)
HISTORICAL_MODULES = tuple(module for module in MODULES
                           if module in ("coding", "mathematics", "writter"))
PLUGIN_ID = "constellation@constellation"
PLUGIN_MANIFEST = ".codex-plugin/plugin.json"
CLAUDE_PLUGIN_MANIFEST = ".claude-plugin/plugin.json"
CORE_FILES = {
    "ecosystem/runtime/review_gate.py", "ecosystem/runtime/review-policy.json", "ecosystem/core.py",
    "ecosystem/runtime/__init__.py", "ecosystem/runtime/workflow.py",
    "ecosystem/runtime/workspace.py", "ecosystem/runtime/dispatch.py",
    "ecosystem/runtime/agent_policy.py", "ecosystem/runtime/progress.py",
    "ecosystem/storage.py", "ecosystem/cli.py", "ecosystem/build.py",
    "ecosystem/install.py", "ecosystem/native.py", "ecosystem/validate.py",
    "ecosystem/hooks.py", "ecosystem/hook_entry.py", "ecosystem/hooks.json", "ecosystem/references/protocol.md", "ecosystem/docs/progress.md",
    "ecosystem/agents/researcher.toml", "ecosystem/agents/reviewer.toml",
    "ecosystem/agents/security-reviewer.toml", "ecosystem/agents/verifier.toml",
    "ecosystem/tests/test_progress.py", "ecosystem/tests/test_progress_core.py",
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
        self.plugin_queries: list[str | None] = []

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

    def plugins(self, marketplace: str | None = None) -> list[dict]:
        self.plugin_queries.append(marketplace)
        rows = self._rows("plugins")
        if marketplace is not None:
            rows = [row for row in rows if isinstance(row.get("pluginId"), str)
                    and row["pluginId"].endswith("@" + marketplace)]
        return rows

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
        rows = [row for row in self._rows("plugins") if row["pluginId"] != PLUGIN_ID]
        rows.append({"pluginId": PLUGIN_ID, "version": version, "enabled": True})
        self._save("plugins", rows)
        if self.corrupt_cache_once:
            self.corrupt_cache_once = False
            (cache / "ecosystem/runtime/review-policy.json").write_text("{}\n")
        self._failure("add_plugin")
        return {"pluginId": PLUGIN_ID, "version": version}

    def remove_plugin(self) -> dict:
        self.mutations.append("remove_plugin")
        if self.fail_rollback:
            raise NativeError("Synthetic rollback failure")
        cache = self.home / "plugins/cache/constellation/constellation"
        if cache.exists():
            shutil.rmtree(cache)
        self._save("plugins", [row for row in self._rows("plugins") if row["pluginId"] != PLUGIN_ID])
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
        self.current_version = json.loads((self.bundle / PLUGIN_MANIFEST).read_text())["version"]

    def source_copy(self, name: str = "source") -> Path:
        source = self.root / name
        shutil.copytree(self.bundle, source)
        (source / "bundle.json").unlink()
        (source / "ecosystem/manifests").mkdir(exist_ok=True)
        (source / PLUGIN_MANIFEST).replace(source / "ecosystem/manifests/codex-plugin.json")
        (source / ".codex-plugin").rmdir()
        (source / CLAUDE_PLUGIN_MANIFEST).replace(source / "ecosystem/manifests/claude-plugin.json")
        (source / ".claude-plugin").rmdir()
        for origin, target in (("hooks.json", "codex-hooks.json"), ("claude-hooks.json", "claude-hooks.json")):
            (source / "ecosystem" / origin).replace(source / "ecosystem/manifests" / target)
        shutil.rmtree(source / "agents")
        return source

    def changed_bundle(self, version: str = "1.1.1", *, change_agent: bool = False,
                       change_entry: bool = False) -> Path:
        source = self.source_copy("update-source")
        metadata = json.loads((source / "ecosystem/manifests/codex-plugin.json").read_text())
        metadata["version"] = version
        write_json(source / "ecosystem/manifests/codex-plugin.json", metadata)
        claude = json.loads((source / "ecosystem/manifests/claude-plugin.json").read_text())
        write_json(source / "ecosystem/manifests/claude-plugin.json", {**claude, "version": version})
        workflow = source / f"skills/{self.module}/references/workflow.md"
        workflow.write_text(workflow.read_text() + "\nUpdated synthetic release.\n")
        if change_agent:
            agent = source / "ecosystem/agents/reviewer.toml"
            agent.write_text(agent.read_text() + "\n# Updated synthetic reviewer release.\n")
        if change_entry:
            entry = source / "ecosystem/hook_entry.py"
            entry.write_text(entry.read_text() + "\n# Updated synthetic stable entry release.\n")
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


class RuntimeStatusTests(BundleCase):
    def setUp(self) -> None:
        super().setUp()
        self.receiver = self.root / "status-receiver"
        self.receiver.mkdir()
        self.environment = dict(os.environ)
        self.environment.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull,
                                GIT_CONFIG_NOSYSTEM="1", CODEX_HOME=str(self.root / "status-home"))
        self.environment.pop("CODEX_THREAD_ID", None)
        self.environment.pop("PYTHONPATH", None)
        for args in (("init", "-b", "main", str(self.receiver)),
                     ("-C", str(self.receiver), "config", "user.name", "Status Fixture"),
                     ("-C", str(self.receiver), "config", "user.email", "status@example.invalid"),
                     ("-C", str(self.receiver), "config", "core.hooksPath", str(self.root / "no-hooks"))):
            subprocess.run(["git", *args], env=self.environment, capture_output=True,
                           text=True, check=True, timeout=10)
        (self.receiver / "README.md").write_text("Status fixture.\n")
        for args in (("add", "README.md"), ("commit", "-m", "Create status fixture")):
            subprocess.run(["git", *args], cwd=self.receiver, env=self.environment,
                           capture_output=True, text=True, check=True, timeout=10)
        self.session = "synthetic-status-reader"
        self.command = [sys.executable, "-I", "-B", str(self.bundle / "ecosystem/cli.py"),
                        "git", "--root", str(self.receiver), "--session", self.session]
        begun = self.invoke("begin")
        self.assertEqual(begun.returncode, 2, begun.stderr)
        self.assertIn("sync_error", json.loads(begun.stdout))
        planned = self.invoke("plan", payload={"requirements": ["Inspect the pending fixture."], "paths": []})
        self.assertEqual(planned.returncode, 0, planned.stderr)
        self.home = self.receiver / ".git/constellation"
        self.state = self.home / (hashlib.sha256(self.session.encode()).hexdigest()[:24] + ".json")

    def invoke(self, *arguments: str, payload: dict | None = None,
               timeout: int = 5) -> subprocess.CompletedProcess:
        return subprocess.run([*self.command, *arguments], cwd=self.receiver, env=self.environment,
                              input=json.dumps(payload) if payload is not None else None,
                              capture_output=True, text=True, timeout=timeout)

    def test_checked_command_can_read_its_own_pending_status(self) -> None:
        result = self.invoke("check", "--timeout", "3", "--", *self.command, "status", timeout=6)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        pending, completed = [json.loads(line) for line in result.stdout.splitlines() if line]
        self.assertFalse(pending["checks"][-1]["completed"])
        self.assertIsNone(pending.get("finished"))
        self.assertTrue(completed["completed"])
        self.assertEqual(completed["exit_code"], 0)
        self.assertEqual(json.loads(self.state.read_text())["checks"][-1], completed)

    def test_status_reads_one_unchanged_incomplete_snapshot_while_writer_holds_lock(self) -> None:
        before = snapshot(self.home)
        with (self.home / "workflow.lock").open("a") as writer, builder._PLATFORM.file_lock(writer.fileno()):
            result = self.invoke("status", timeout=3)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), json.loads(self.state.read_text()))
            self.assertIsNone(json.loads(result.stdout).get("finished"))
            self.assertEqual(snapshot(self.home), before)
            with (self.home / "workflow.lock").open("a") as contender:
                with self.assertRaises(BlockingIOError):
                    with builder._PLATFORM.file_lock(contender.fileno(), blocking=False):
                        pass

    def test_mutation_still_waits_for_writer_lock_and_does_not_release_it(self) -> None:
        marker = self.root / "mutator-entered-lock"
        runner = textwrap.dedent('''\
            from contextlib import contextmanager
            from pathlib import Path
            import sys
            sys.path.insert(0, sys.argv[1])
            from ecosystem.runtime.workflow import Workflow, entrypoint
            class ObservedWorkflow(Workflow):
                @contextmanager
                def lock(self):
                    Path(sys.argv[2]).write_text("entered")
                    with super().lock():
                        yield
            raise SystemExit(entrypoint(sys.argv[3:], workflow_factory=ObservedWorkflow))
            ''')
        process = None
        before = self.state.read_bytes()
        try:
            with (self.home / "workflow.lock").open("a") as writer, builder._PLATFORM.file_lock(writer.fileno()):
                process = subprocess.Popen(
                    [sys.executable, "-I", "-B", "-c", runner, str(self.bundle), str(marker),
                     "--root", str(self.receiver), "--session", self.session, "plan"],
                    cwd=self.receiver, env=self.environment, stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                assert process.stdin is not None
                process.stdin.write(json.dumps({"requirements": ["Queued fixture update."], "paths": []}))
                process.stdin.close()
                process.stdin = None
                deadline = time.monotonic() + 5
                while not marker.exists() and process.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertTrue(marker.exists(), "Mutator did not reach the real workflow lock")
                self.assertIsNone(process.poll())
                self.assertEqual(self.state.read_bytes(), before)
                with (self.home / "workflow.lock").open("a") as contender:
                    with self.assertRaises(BlockingIOError):
                        with builder._PLATFORM.file_lock(contender.fileno(), blocking=False):
                            pass
            output, error = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 0, error)
            self.assertEqual(json.loads(output)["requirements"], ["Queued fixture update."])
            self.assertEqual(json.loads(self.state.read_text())["requirements"], ["Queued fixture update."])
        finally:
            if process is not None and process.poll() is None:
                process.kill()
                process.communicate(timeout=5)


class BuildTests(BundleCase):
    def test_exported_git_runtime_reviews_and_publishes_without_hub_or_project_scaffolding(self) -> None:
        receiver = self.root / "standalone-git"
        receiver.mkdir()
        remote = self.root / "standalone.git"
        environment = dict(os.environ)
        environment.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull,
                           GIT_CONFIG_NOSYSTEM="1", GIT_ALLOW_PROTOCOL="file")
        environment.pop("PYTHONPATH", None)
        environment.pop("CODEX_THREAD_ID", None)
        for args in (("init", "--bare", str(remote)), ("init", "-b", "main", str(receiver)),
                     ("-C", str(receiver), "config", "user.name", "Synthetic Fixture"),
                     ("-C", str(receiver), "config", "user.email", "fixture@example.invalid"),
                     ("-C", str(receiver), "config", "core.hooksPath", str(self.root / "no-hooks"))):
            subprocess.run(["git", *args], env=environment, capture_output=True, text=True,
                           check=True, timeout=15)
        (receiver / "README.md").write_text("Initial fixture.\n")
        for args in (("add", "README.md"), ("commit", "-m", "Create fixture"),
                     ("remote", "add", "origin", str(remote)), ("push", "-u", "origin", "main")):
            subprocess.run(["git", *args], cwd=receiver, env=environment, capture_output=True,
                           text=True, check=True, timeout=15)
        runner = textwrap.dedent('''\
            import os, pathlib, runpy, sys
            original = pathlib.Path(sys.argv[1])
            def deny_source(event, args):
                if event in {"open", "os.listdir", "os.scandir"} and args and isinstance(args[0], (str, bytes, os.PathLike)):
                    path = pathlib.Path(os.fsdecode(args[0])).resolve()
                    if path == original or original in path.parents:
                        raise RuntimeError("The original package is unavailable")
            sys.addaudithook(deny_source)
            sys.argv = sys.argv[2:]
            runpy.run_path(sys.argv[0], run_name="__main__")
            ''')
        command = [sys.executable, "-I", "-B", "-c", runner, str(CODEX_DIR),
                   str(self.bundle / "ecosystem/cli.py"), "git", "--root", str(receiver),
                   "--session", "synthetic-standalone-author"]

        def invoke(*args: str, payload: dict | None = None, rejected: bool = False) -> dict:
            result = subprocess.run([*command, *args], input=json.dumps(payload or {}),
                                    cwd=receiver, env=environment, capture_output=True, text=True, timeout=30)
            if rejected:
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                return {}
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return json.loads(result.stdout)

        self.assertNotIn("sync_error", invoke("begin"))
        requirement = "Document the verified fixture result."
        invoke("plan", payload={"requirements": [requirement], "paths": ["README.md"]})
        artifact = receiver / "README.md"
        artifact.write_text("Verified fixture.\n")
        invoke("review", payload={requirement: "Fixture checked."}, rejected=True)

        def report() -> None:
            context = invoke("review-start")
            invoke("review-report", payload={
                "token": context["token"], "reviewer": "synthetic-independent-reviewer",
                "role": "reviewer", "focus": ["correctness"], "paths": ["README.md"],
                "summary": "Synthetic fixture review.",
                "evidence": "Inspected the expected fixture bytes.", "findings": [],
            })

        report()
        artifact.write_text("Updated verified fixture.\n")
        invoke("review", payload={requirement: "Fixture checked."}, rejected=True)
        report()
        invoke("check", "--", sys.executable, "-I", "-B", "-c",
               "from pathlib import Path; assert 'Updated' in Path('README.md').read_text()")
        # The final review binds the definitive check set as well as artifact bytes.
        report()
        invoke("review", payload={requirement: "Checked the updated fixture and independent review."})
        invoke("commit", "-m", "Update fixture", "README.md")
        self.assertTrue(invoke("finish")["completed"])
        self.assertFalse((receiver / ".codex").exists())
        self.assertFalse((receiver / "AGENTS.md").exists())

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
        for relative in ("ecosystem/runtime/review_gate.py", "ecosystem/runtime/review-policy.json"):
            self.assertEqual((self.bundle / relative).read_bytes(), (CODEX_DIR / relative).read_bytes())
        origin = CODEX_DIR / PLUGIN_MANIFEST if IS_DISTRIBUTED else SOURCE_DIR / "manifests/codex-plugin.json"
        self.assertEqual((self.bundle / PLUGIN_MANIFEST).read_bytes(), origin.read_bytes())
        self.assertFalse((self.bundle / "plugin.json").exists())
        self.assertFalse((self.bundle / "ecosystem/manifests/codex-plugin.json").exists())
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
        for relative in ("ecosystem/runtime/review_gate.py", f"skills/{self.module}/references"):
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
            path = target / "ecosystem/runtime/review-policy.json"
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
                path.symlink_to(self.bundle / "ecosystem/runtime/review-policy.json")
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
        path = source / "ecosystem/manifests/codex-plugin.json"
        original = json.loads(path.read_text())
        for field, value in (("skills", "../private"), ("hooks", "/tmp/unowned-hooks.json"),
                             ("version", "../escape"), ("version", "/tmp/escape")):
            write_json(path, {**original, field: value})
            with self.subTest(field=field, value=value), self.assertRaises(BundleError):
                build_bundle(self.root / "rejected-metadata", MODULES, source_root=source)
            self.assertFalse((self.root / "rejected-metadata").exists())

    def test_current_layout_cannot_claim_historical_130_identity(self) -> None:
        import claude as claude_installer

        source = self.source_copy()
        for relative in (PLUGIN_MANIFEST, CLAUDE_PLUGIN_MANIFEST):
            path = source / builder.source_path(relative)
            metadata = json.loads(path.read_text())
            write_json(path, {**metadata, "version": "1.3.0"})
        before_source = snapshot(source)
        output = self.root / "historical-label-output"
        with self.assertRaisesRegex(BundleError, "reserved for the historical"):
            build_bundle(output, MODULES, source_root=source)
        self.assertFalse(output.exists())
        self.assertEqual(snapshot(source), before_source)

        # This is a structurally current package with correct hashes, not a
        # corrupt file or a genuine historical release. Both inputs must fail
        # before either installer can create an ownership receipt or register it.
        manifest = json.loads((self.bundle / "bundle.json").read_text())
        for relative in (PLUGIN_MANIFEST, CLAUDE_PLUGIN_MANIFEST):
            path = self.bundle / relative
            metadata = json.loads(path.read_text())
            write_json(path, {**metadata, "version": "1.3.0"})
            manifest["files"][relative] = builder.file_record(path)
        write_json(self.bundle / "bundle.json", manifest)
        before_bundle = snapshot(self.bundle)
        with self.assertRaisesRegex(BundleError, "reserved for the historical"):
            verify_bundle(self.bundle)
        with self.assertRaises(BundleError):
            builder.verify_owned_bundle(self.bundle)
        codex_home = self.root / "rejected-codex-home"
        claude_home = self.root / "rejected-claude-home"
        backend = SyntheticNativeClient(codex_home)
        for check in (True, False):
            with self.subTest(client="codex", check=check):
                with self.assertRaisesRegex(BundleError, "reserved for the historical"):
                    install_bundle(self.bundle, codex_home, check=check, client=backend)
                self.assertFalse(codex_home.exists())
                self.assertEqual(backend.mutations, [])
            with self.subTest(client="claude", check=check):
                with self.assertRaisesRegex(BundleError, "reserved for the historical"):
                    claude_installer.install_bundle(self.bundle, claude_home, check=check)
                self.assertFalse(claude_home.exists())
        self.assertEqual(snapshot(self.bundle), before_bundle)

    def test_bundle_modules_require_an_explicit_list_before_rebuild(self) -> None:
        path = self.bundle / "bundle.json"
        original = json.loads(path.read_text())
        for modules in (None, True, 1, "coding", {name: True for name in MODULES}):
            with self.subTest(modules=modules):
                write_json(path, {**original, "modules": modules})
                with self.assertRaises(BundleError):
                    verify_bundle(self.bundle)
                with self.assertRaises(BundleError):
                    build_bundle(self.root / "rejected-modules", source_root=self.bundle)
                self.assertFalse((self.root / "rejected-modules").exists())

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

    def seed_legacy_installation(self, modules: list[str] | None = None,
                                 *, executable_agent: bool = False) -> None:
        """Create the historical ownership layout with synthetic release bytes.

        Only the inventory is historical; this fixture never executes 1.0 code
        and is not a substitute for testing the user's actual prior release.
        """
        modules = list(HISTORICAL_MODULES) if modules is None else modules
        if not modules:
            self.skipTest("This distribution contains no historical modules")
        self.assertTrue(set(modules) <= set(HISTORICAL_MODULES))
        self.install(modules=modules)
        receipt = self.receipt()
        catalog = self.home / "constellation/catalog"
        payload = catalog / "plugins/constellation"
        for current, old in (("compatibility", "COMPATIBILITY"), ("architecture", "ARCHITECTURE"),
                             ("migrations", "MIGRATION"), ("progress", "PROGRESS"), ("evaluation", "EVALUATION")):
            (payload / f"ecosystem/docs/{current}.md").replace(payload / f"ecosystem/{old}.md")
        write_json(payload / "ecosystem/evaluation.json", {"historical_fixture": True})
        for name in ("review_gate.py", "review-policy.json"):
            (payload / "ecosystem/runtime" / name).replace(payload / name)
        shutil.rmtree(payload / "ecosystem/runtime")
        for name in ("ARCHITECTURE.md", "MIGRATION.md", "PROGRESS.md", "tests/test_capabilities.py",
                     "tests/test_progress.py", "tests/test_progress_core.py", "hook_entry.py",
                     "tests/test_hook_entry.py"):
            (payload / "ecosystem" / name).unlink()
        historical = installer._legacy_receipt_files(tuple(modules))
        for relative in set(installer._inventory(payload)) - historical - {"bundle.json"}:
            (payload / relative).unlink()
        metadata = json.loads((payload / PLUGIN_MANIFEST).read_text())
        write_json(payload / PLUGIN_MANIFEST, {**metadata, "version": "1.0.0"})
        if executable_agent:
            (payload / "ecosystem/agents/reviewer.toml").chmod(0o755)
        records = installer._inventory(payload)
        records.pop("bundle.json")
        write_json(payload / "bundle.json", {"schema": 1, "modules": receipt["modules"], "files": records})
        self.backend.add_plugin()
        receipt.pop("hook")
        (self.home / "constellation/hook.py").unlink()
        write_json(self.home / "constellation/receipt.json", {
            **receipt, "schema": 1, "version": "1.0.0",
            "catalog": installer._inventory(catalog),
            "cache": installer._inventory(self.cache("1.0.0")),
        })
        self.backend.mutations.clear()

    def seed_prior_shared_installation(self, modules: list[str] | None = None) -> None:
        """Model an owned schema-2 release before the progress resources existed."""
        modules = list(HISTORICAL_MODULES) if modules is None else modules
        if not modules:
            self.skipTest("This distribution contains no historical modules")
        self.assertTrue(set(modules) <= set(HISTORICAL_MODULES))
        self.install(modules=modules)
        self.rewrite_owned_shared_resources(remove=(
            "ecosystem/runtime/progress.py", "ecosystem/tests/test_progress.py",
            "ecosystem/tests/test_progress_core.py", "ecosystem/docs/progress.md",
            "ecosystem/hook_entry.py", "ecosystem/tests/test_hook_entry.py",
            *builder.CLAUDE_FILES, CLAUDE_PLUGIN_MANIFEST,
            *(relative for relative in builder.allowed_files(modules) if relative.startswith("agents/")),
        ))
        receipt = self.receipt()
        receipt.pop("hook")
        receipt["schema"] = 2
        (self.home / "constellation/hook.py").unlink()
        write_json(self.home / "constellation/receipt.json", receipt)

    def seed_dual_130_installation(self, modules: list[str] | None = None) -> None:
        """Use real files with the independently specified previous layout.

        This tests migration semantics with synthetic payload bytes. A release
        smoke test can additionally seed the published 1.3.0 artifact.
        """
        self.install(modules=modules)
        receipt = self.receipt()
        catalog = self.home / "constellation/catalog"
        payload = catalog / "plugins/constellation"
        for current, old in (("compatibility", "COMPATIBILITY"), ("architecture", "ARCHITECTURE"),
                             ("migrations", "MIGRATION"), ("progress", "PROGRESS"), ("evaluation", "EVALUATION")):
            (payload / f"ecosystem/docs/{current}.md").replace(payload / f"ecosystem/{old}.md")
        for relative in set(installer._inventory(payload)) - builder.legacy_files_130(receipt["modules"]) - {"bundle.json"}:
            (payload / relative).unlink()
        (payload / "ecosystem/docs").rmdir()
        write_json(payload / "ecosystem/evaluation.json", {"historical_fixture": True})
        for relative in (PLUGIN_MANIFEST, CLAUDE_PLUGIN_MANIFEST):
            metadata = json.loads((payload / relative).read_text())
            write_json(payload / relative, {**metadata, "version": "1.3.0"})
        records = installer._inventory(payload)
        records.pop("bundle.json")
        write_json(payload / "bundle.json", {"schema": 1, "modules": receipt["modules"], "files": records})
        self.backend.add_plugin()
        write_json(self.home / "constellation/receipt.json", {
            **receipt, "version": "1.3.0", "catalog": installer._inventory(catalog),
            "cache": installer._inventory(self.cache("1.3.0")),
        })
        self.backend.mutations.clear()

    def test_dual_130_upgrade_reorganizes_each_subset_and_preserves_unrelated_state(self) -> None:
        for modules in [*([module] for module in MODULES), list(MODULES)]:
            with self.subTest(modules=modules):
                self.seed_dual_130_installation(modules)
                previous = snapshot(self.home)
                self.assertEqual(self.install(modules=modules, check=True)["status"], "checked")
                self.assertEqual(snapshot(self.home), previous)
                self.assertEqual(self.backend.mutations, [])
                result = self.install(modules=modules)
                self.assertEqual(result["version"], self.current_version)
                self.assertEqual(verify_bundle(self.cache())["modules"], modules)
                self.assertTrue((self.cache() / "ecosystem/docs/architecture.md").is_file())
                self.assertFalse((self.cache() / "ecosystem/ARCHITECTURE.md").exists())
                self.assertFalse((self.cache() / "ecosystem/evaluation.json").exists())
                self.assert_unrelated_preserved()

    def test_dual_130_upgrade_failure_restores_exact_previous_files(self) -> None:
        self.seed_dual_130_installation()
        before = snapshot(self.home)
        self.backend.fail_once = "add_plugin"
        with self.assertRaisesRegex(InstallError, "previous owned files and registration restored"):
            self.install()
        self.assertEqual(snapshot(self.home), before)
        self.assertEqual(self.receipt()["version"], "1.3.0")
        self.assertEqual(self.install()["version"], self.current_version)

    def test_dual_130_receipt_rejects_mixed_missing_and_unknown_inventory(self) -> None:
        for change in ({"add": ("ecosystem/docs/architecture.md",)},
                       {"add": ("ecosystem/unknown.py",)},
                       {"remove": ("ecosystem/evaluation.json",)}):
            with self.subTest(change=change):
                self.seed_dual_130_installation()
                original = snapshot(self.home)
                self.rewrite_owned_shared_resources(**change)
                before = snapshot(self.home)
                with self.assertRaisesRegex(InstallError, "Invalid installation receipt"):
                    self.install()
                self.assertEqual(snapshot(self.home), before)
                self.assertEqual(self.backend.mutations, [])
                shutil.rmtree(self.home)
                self.home.mkdir()
                for relative, (kind, content, mode) in original.items():
                    self.assertEqual(kind, "file")
                    path = self.home / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(content)
                    path.chmod(mode)
                # File snapshots deliberately omit directories; restore this private boundary too.
                builder._PLATFORM.set_access(self.home / "constellation", 0o700)

    def test_dual_130_previous_package_is_read_as_data(self) -> None:
        self.seed_dual_130_installation()
        payload = self.home / "constellation/catalog/plugins/constellation"
        marker = self.root / "previous-release-was-executed"
        (payload / "ecosystem/build.py").write_text(
            f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\n")
        self.rewrite_owned_shared_resources()
        self.assertEqual(self.install()["version"], self.current_version)
        self.assertFalse(marker.exists())

    def rewrite_owned_shared_resources(self, *, remove: tuple[str, ...] = (),
                                       add: tuple[str, ...] = ()) -> None:
        receipt = self.receipt()
        catalog = self.home / "constellation/catalog"
        payload = catalog / "plugins/constellation"
        for relative in remove:
            (payload / relative).unlink()
        for relative in add:
            path = payload / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("Synthetic independently named resource.\n")
        records = installer._inventory(payload)
        records.pop("bundle.json")
        write_json(payload / "bundle.json", {
            "schema": 1, "modules": receipt["modules"], "files": records,
        })
        self.backend.add_plugin()
        write_json(self.home / "constellation/receipt.json", {
            **receipt, "catalog": installer._inventory(catalog),
            "cache": installer._inventory(self.cache()),
        })
        self.backend.mutations.clear()

    @unittest.skipUnless(HISTORICAL_MODULES, "This distribution contains no historical modules")
    def test_prior_shared_release_accepts_added_resources_for_every_module_selection(self) -> None:
        for count in range(1, len(HISTORICAL_MODULES) + 1):
            for selected in combinations(HISTORICAL_MODULES, count):
                modules = list(selected)
                with self.subTest(modules=modules):
                    self.seed_prior_shared_installation(modules)
                    self.assertFalse((self.cache() / "ecosystem/runtime/progress.py").exists())
                    before = snapshot(self.home)
                    self.assertEqual(self.install(modules=modules, check=True)["status"], "checked")
                    self.assertEqual(snapshot(self.home), before)
                    self.assertEqual(self.backend.mutations, [])
                    self.assertEqual(self.install(modules=modules)["status"], "updated")
                    self.assertTrue((self.cache() / "ecosystem/runtime/progress.py").is_file())
                    self.assertEqual(verify_bundle(self.cache())["modules"], modules)
                    self.assert_unrelated_preserved()

    def test_failed_shared_resource_expansion_restores_prior_release_and_can_retry(self) -> None:
        self.seed_prior_shared_installation()
        state = self.home / "constellation/state/progress.json"
        state.parent.mkdir(parents=True)
        state.write_text('{"synthetic": "recoverable state"}\n')
        before = snapshot(self.home)
        self.backend.fail_once = "add_plugin"
        with self.assertRaisesRegex(InstallError, "previous owned files and registration restored"):
            self.install()
        self.assertEqual(snapshot(self.home), before)
        self.assertEqual(self.install(check=True)["status"], "checked")
        self.assertEqual(self.install()["status"], "updated")
        self.assertEqual(state.read_text(), '{"synthetic": "recoverable state"}\n')
        self.assert_unrelated_preserved()

    def test_prior_shared_package_code_is_never_executed_during_upgrade(self) -> None:
        self.seed_prior_shared_installation()
        marker = self.root / "old-builder-executed"
        payload = self.home / "constellation/catalog/plugins/constellation"
        (payload / "ecosystem/build.py").write_text(
            f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\n"
            "raise RuntimeError('The previous release must only be read as data')\n"
        )
        self.rewrite_owned_shared_resources()
        self.assertEqual(self.install()["status"], "updated")
        self.assertFalse(marker.exists())

    @unittest.skipUnless(HISTORICAL_MODULES, "This distribution contains no historical modules")
    def test_prior_shared_release_cannot_claim_foreign_files_or_omit_module_identity(self) -> None:
        for change in ({"add": ("ecosystem/foreign.py",)},
                       {"add": ("agents/foreign.toml",)},
                       {"add": ("ecosystem/agents/foreign.toml",)},
                       {"remove": (f"skills/{HISTORICAL_MODULES[0]}/SKILL.md",)},
                       {"remove": ("ecosystem/agents/reviewer.toml",)}):
            with self.subTest(change=change):
                self.seed_prior_shared_installation()
                before_change = snapshot(self.home)
                self.rewrite_owned_shared_resources(**change)
                before = snapshot(self.home)
                with self.assertRaises(InstallError):
                    self.install()
                self.assertEqual(snapshot(self.home), before)
                self.assertEqual(self.backend.mutations, [])
                # Restore this fixture through exact bytes, never production state.
                shutil.rmtree(self.home)
                self.home.mkdir()
                for relative, (kind, contents, mode) in before_change.items():
                    self.assertEqual(kind, "file")
                    path = self.home / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(contents)
                    path.chmod(mode)
                builder._PLATFORM.set_access(self.home / "constellation", 0o700)

    @unittest.skipUnless(HISTORICAL_MODULES, "This distribution contains no historical modules")
    def test_legacy_release_updates_to_shared_runtime_for_every_module_selection(self) -> None:
        selections = [list(group) for count in range(1, len(HISTORICAL_MODULES) + 1)
                      for group in combinations(HISTORICAL_MODULES, count)]
        for modules in selections:
            with self.subTest(modules=modules):
                self.seed_legacy_installation(modules)
                self.assertEqual(self.install(modules=modules, check=True)["status"], "checked")
                self.assertEqual(self.backend.mutations, [])
                result = self.install(modules=modules)
                self.assertEqual(result["status"], "updated")
                self.assertEqual(result["version"], self.current_version)
                self.assertEqual(self.receipt()["schema"], 3)
                self.assertFalse((self.cache() / "review_gate.py").exists())
                self.assertTrue((self.cache() / "ecosystem/runtime/workflow.py").is_file())
                self.assertEqual(self.install(modules=modules, check=True)["status"], "checked")
                self.assert_unrelated_preserved()

    def test_failed_legacy_upgrade_restores_old_inventory_and_can_retry(self) -> None:
        self.seed_legacy_installation()
        before = snapshot(self.home)
        self.backend.fail_once = "add_plugin"
        with self.assertRaisesRegex(InstallError, "previous owned files and registration restored"):
            self.install()
        self.assertEqual(snapshot(self.home), before)
        self.assertEqual(self.receipt()["schema"], 1)
        self.assertEqual(self.install(check=True)["status"], "checked")
        self.assertEqual(self.install()["version"], self.current_version)

    def test_executable_packaged_agent_keeps_normalized_projection_across_updates(self) -> None:
        source = self.source_copy()
        (source / "ecosystem/agents/reviewer.toml").chmod(0o755)
        bundle = self.root / "executable-agent-bundle"
        build_bundle(bundle, MODULES, source_root=source)
        self.install(bundle)
        receipt = self.receipt()
        self.assertEqual(receipt["cache"]["ecosystem/agents/reviewer.toml"]["mode"], 0o755)
        self.assertEqual(receipt["agents"]["constellation-reviewer.toml"]["mode"], 0o644)
        self.assertEqual(self.install(bundle, check=True)["status"], "checked")
        self.assertEqual(self.install(bundle)["status"], "updated")

    def test_executable_legacy_agent_keeps_normalized_projection_across_upgrade(self) -> None:
        self.seed_legacy_installation(executable_agent=True)
        self.assertEqual(self.install(check=True)["status"], "checked")
        self.assertEqual(self.install()["status"], "updated")

    def test_legacy_upgrade_preserves_and_rejects_unrecorded_catalog_files(self) -> None:
        self.seed_legacy_installation()
        payload = self.home / "constellation/catalog/plugins/constellation"
        module = self.receipt()["modules"][0]
        for name in (".DS_Store", "skills/.DS_Store", f"skills/{module}/.DS_Store"):
            path = payload / name
            path.write_bytes(b"independently owned fixture bytes")
        before = snapshot(self.home)
        with self.assertRaisesRegex(InstallError, "Catalog was modified"):
            self.install()
        self.assertEqual(snapshot(self.home), before)
        self.assertEqual(self.backend.mutations, [])

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
        self.assertEqual(updated["version"], "1.1.1")
        self.assertEqual(self.receipt()["version"], "1.1.1")
        self.assertIn("Updated synthetic release.", (self.cache() / f"skills/{self.module}/references/workflow.md").read_text())
        self.assert_unrelated_preserved()

    def test_receipt_hashes_actual_owned_files_and_has_no_duplicate_global_skills(self) -> None:
        self.install()
        receipt = self.receipt()
        self.assertEqual(receipt["schema"], 3)
        entry = self.home / "constellation/hook.py"
        self.assertEqual(receipt["hook"], installer.file_record(entry))
        self.assertEqual(receipt["hook"]["mode"], 0o644)
        self.assertEqual(entry.read_bytes(), (self.cache() / "ecosystem/hook_entry.py").read_bytes())
        self.assertEqual(receipt["modules"], list(MODULES))
        for group, base in (("catalog", self.home / "constellation/catalog"),
                            ("cache", self.cache()), ("agents", self.home / "agents")):
            for relative, record in receipt[group].items():
                path = base / relative
                self.assertEqual(record["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
                self.assertEqual(record["mode"], stat.S_IMODE(path.stat().st_mode))
        self.assertEqual(sorted(path.name for path in (self.home / "skills").iterdir()), ["user-skill"])
        self.assertEqual(sorted(path.name for path in (self.cache() / "skills").iterdir()), list(MODULES))

    def test_stable_entry_foreign_files_and_links_are_never_adopted(self) -> None:
        managed = self.home / "constellation"
        managed.mkdir()
        entry = managed / "hook.py"
        for kind in ("file", "symlink", "directory"):
            with self.subTest(kind=kind):
                if kind == "file":
                    entry.write_text("Independently owned entry.\n")
                elif kind == "symlink":
                    entry.symlink_to(self.home / "AGENTS.md")
                else:
                    entry.mkdir()
                before = snapshot(self.home)
                with self.assertRaises(InstallError):
                    self.install()
                self.assertEqual(snapshot(self.home), before)
                self.assertEqual(self.backend.mutations, [])
                if kind == "directory":
                    entry.rmdir()
                else:
                    entry.unlink()

    def test_stable_entry_changed_hash_mode_missing_or_link_blocks_update(self) -> None:
        self.install()
        entry = self.home / "constellation/hook.py"
        content = entry.read_bytes()
        for damage in ("content", "mode", "missing", "symlink"):
            with self.subTest(damage=damage):
                if damage == "content":
                    entry.write_text("Changed entry.\n")
                elif damage == "mode":
                    entry.chmod(0o755)
                else:
                    entry.unlink()
                    if damage == "symlink":
                        entry.symlink_to(self.home / "AGENTS.md")
                before, mutations = snapshot(self.home), list(self.backend.mutations)
                with self.assertRaises(InstallError):
                    self.install()
                self.assertEqual(snapshot(self.home), before)
                self.assertEqual(self.backend.mutations, mutations)
                entry.unlink(missing_ok=True)
                entry.write_bytes(content)
                entry.chmod(0o644)

    def test_receipt_failure_after_atomic_write_restores_entry_and_previous_receipt(self) -> None:
        self.install()
        before = snapshot(self.home)
        update = self.changed_bundle(change_entry=True)
        original_write = installer._write_json

        def write_then_fail(path: Path, value: dict) -> None:
            original_write(path, value)
            self.assertIn(b"Updated synthetic stable entry release", (path.parent / "hook.py").read_bytes())
            raise OSError("Synthetic lost acknowledgement after receipt replacement")

        with patch.object(installer, "_write_json", side_effect=write_then_fail):
            with self.assertRaisesRegex(InstallError, "previous owned files.*restored"):
                self.install(update)
        self.assertEqual(snapshot(self.home), before)

    def test_first_install_receipt_failure_removes_new_stable_entry(self) -> None:
        original_write = installer._write_json

        def write_then_fail(path: Path, value: dict) -> None:
            original_write(path, value)
            raise OSError("Synthetic failure after receipt replacement")

        with patch.object(installer, "_write_json", side_effect=write_then_fail):
            with self.assertRaisesRegex(InstallError, "previous owned files.*restored"):
                self.install()
        self.assertFalse((self.home / "constellation/hook.py").exists())
        self.assertFalse((self.home / "constellation/receipt.json").exists())
        self.assertFalse((self.home / "constellation/catalog").exists())
        self.assert_unrelated_preserved()

    def test_stable_entry_atomic_replacement_preserves_external_hardlink(self) -> None:
        self.install()
        entry = self.home / "constellation/hook.py"
        external = self.root / "independently-held-entry.py"
        os.link(entry, external)
        before, inode = external.read_bytes(), external.stat().st_ino
        self.install(self.changed_bundle(change_entry=True))
        self.assertEqual(external.read_bytes(), before)
        self.assertEqual(external.stat().st_ino, inode)
        self.assertNotEqual(entry.stat().st_ino, inode)
        self.assertNotEqual(entry.read_bytes(), before)
        self.assert_unrelated_preserved()

    def test_selected_modules_install_check_and_upgrade_preserve_owned_subset(self) -> None:
        updated = self.changed_bundle(version="1.2.1")
        for modules in [*([module] for module in MODULES), list(MODULES)]:
            with self.subTest(modules=modules):
                self.install(modules=modules)
                self.assertEqual(self.receipt()["modules"], modules)
                self.assertEqual(sorted(path.name for path in (self.cache() / "skills").iterdir()), modules)
                self.assertTrue(CORE_FILES <= set(verify_bundle(self.cache())["files"]))
                actual_agents = {path.name for path in (self.home / "agents").glob("constellation-*")}
                self.assertEqual(actual_agents, set(self.receipt()["agents"]))
                before, mutations = snapshot(self.home), list(self.backend.mutations)
                self.assertEqual(self.install(modules=modules, check=True)["status"], "checked")
                self.assertEqual(snapshot(self.home), before)
                self.assertEqual(self.backend.mutations, mutations)
                self.assertEqual(self.install(updated, modules=modules)["status"], "updated")
                self.assertEqual(self.receipt()["schema"], 3)
                self.assertEqual(verify_bundle(self.cache())["modules"], modules)
                self.assertEqual(self.install(updated, modules=modules, check=True)["status"], "checked")
                self.assert_unrelated_preserved()

    @unittest.skipUnless("quant-research" in MODULES, "This distribution omits quant-research")
    def test_installed_quant_research_profile_runs_the_shared_engine(self) -> None:
        self.install(modules=["quant-research"])
        self.module = "quant-research"
        _state, _identity, revision = self.create_default_state(self.home, self.cache())
        self.assertGreater(revision, 0)

    @unittest.skipUnless("quant-research" in MODULES, "This distribution omits quant-research")
    def test_historical_receipts_cannot_claim_a_later_module(self) -> None:
        self.install(modules=["quant-research"])
        path = self.home / "constellation/receipt.json"
        original = self.receipt()
        for schema in (1, 2):
            with self.subTest(schema=schema):
                invalid = {**original, "schema": schema}
                invalid.pop("hook")
                if schema == 1:
                    invalid["version"] = "1.0.0"
                write_json(path, invalid)
                before, mutations = snapshot(self.home), list(self.backend.mutations)
                with self.assertRaisesRegex(InstallError, "Invalid installation receipt"):
                    self.install(modules=["quant-research"])
                self.assertEqual(snapshot(self.home), before)
                self.assertEqual(self.backend.mutations, mutations)
        write_json(path, original)

    @unittest.skipUnless("quant-research" in MODULES, "This distribution omits quant-research")
    def test_current_receipt_requires_every_quant_research_identity(self) -> None:
        paths = [*(f"skills/quant-research/{name}" for name in
                   ("SKILL.md", "agents/openai.yaml", "references/workflow.md")),
                 *(f"ecosystem/agents/{role}.toml" for role in
                   ("coder", "mathematician", "counterexample"))]
        for relative in paths:
            with self.subTest(identity=relative):
                self.install(modules=["quant-research"])
                self.rewrite_owned_shared_resources(remove=(relative,))
                before, mutations = snapshot(self.home), list(self.backend.mutations)
                with self.assertRaisesRegex(InstallError, "Invalid installation receipt"):
                    self.install(modules=["quant-research"])
                self.assertEqual(snapshot(self.home), before)
                self.assertEqual(self.backend.mutations, mutations)
                # Restore the fixture's complete release for the next corrupt
                # inventory; production installation is intentionally rejected.
                payload = self.home / "constellation/catalog/plugins/constellation"
                shutil.copy2(self.bundle / relative, payload / relative)
                self.rewrite_owned_shared_resources()

    def test_current_receipt_accepts_a_later_optional_agent_resource(self) -> None:
        self.install()
        source = self.source_copy("future-agent-source")
        relative = "ecosystem/agents/future-analyst.toml"
        (source / relative).write_text(
            'name = "ecosystem_future_analyst"\n'
            'description = "Synthetic future release profile."\n'
            'developer_instructions = "Use the assigned evidence."\n'
        )
        metadata = json.loads((source / "ecosystem/manifests/codex-plugin.json").read_text())
        write_json(source / "ecosystem/manifests/codex-plugin.json", {**metadata, "version": "1.2.1"})
        metadata = json.loads((source / "ecosystem/manifests/claude-plugin.json").read_text())
        write_json(source / "ecosystem/manifests/claude-plugin.json", {**metadata, "version": "1.2.1"})
        with patch.object(builder, "COMMON_FILES", (*builder.COMMON_FILES, relative)):
            updated = self.root / "future-agent-bundle"
            build_bundle(updated, MODULES, source_root=source)
            before, mutations = snapshot(self.home), list(self.backend.mutations)
            self.assertEqual(self.install(updated, check=True)["status"], "checked")
            self.assertEqual(snapshot(self.home), before)
            self.assertEqual(self.backend.mutations, mutations)
            self.assertEqual(self.install(updated)["status"], "updated")
            self.assertIn(relative, self.receipt()["cache"])
            self.assertEqual(self.install(updated, check=True)["status"], "checked")

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
        targets = (self.home / "constellation/catalog/plugins/constellation/ecosystem/runtime/review-policy.json",
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

    def test_corrupt_receipt_types_records_paths_and_duplicates_are_rejected_before_mutation(self) -> None:
        self.install()
        path = self.home / "constellation/receipt.json"
        original = self.receipt()
        variants = [{**original, "schema": True}, {**original, "schema": 1},
                    {**original, "extra": "unknown"}, {**original, "modules": None},
                    {**original, "modules": {self.module: True}},
                    *({**original, group: list(original[group])} for group in ("cache", "catalog", "agents"))]
        for record in ({"sha256": "x" * 64, "mode": 0o644},
                       {"sha256": "0" * 64, "mode": True},
                       {"sha256": "0" * 64, "mode": 0o600},
                       {"sha256": "0" * 64, "mode": 0o644, "extra": True}):
            value = json.loads(json.dumps(original))
            value["cache"]["bundle.json"] = record
            variants.append(value)
        for extra in ("../outside", "/tmp/outside", "ecosystem/../../outside", ".DS_Store"):
            value = json.loads(json.dumps(original))
            value["cache"][extra] = {"sha256": "0" * 64, "mode": 0o644}
            variants.append(value)
        texts = [json.dumps(value) for value in variants]
        texts.append('{"schema": 999,' + json.dumps(original)[1:])
        for text in texts:
            with self.subTest(receipt=text[:100]):
                path.write_text(text)
                before, mutations = snapshot(self.home), list(self.backend.mutations)
                with self.assertRaises(InstallError):
                    self.install()
                self.assertEqual(snapshot(self.home), before)
                self.assertEqual(self.backend.mutations, mutations)

    def test_receipt_must_be_a_regular_file_before_reading(self) -> None:
        path = self.root / "unreadable-receipt"
        for kind in ("directory", "fifo", "symlink"):
            with self.subTest(kind=kind):
                if kind == "directory":
                    path.mkdir()
                elif kind == "fifo":
                    os.mkfifo(path)
                else:
                    path.symlink_to(self.bundle / "bundle.json")
                with self.assertRaises(InstallError):
                    installer._load_receipt(path)
                path.rmdir() if kind == "directory" else path.unlink()

    def test_legacy_manifest_inconsistency_is_rejected_even_with_updated_receipt_hashes(self) -> None:
        self.seed_legacy_installation()
        for metadata_path in ("bundle.json", PLUGIN_MANIFEST):
            with self.subTest(path=metadata_path):
                receipt = self.receipt()
                catalog = self.home / "constellation/catalog"
                payload = catalog / "plugins/constellation"
                path = payload / metadata_path
                original = path.read_bytes()
                data = json.loads(original)
                data["modules" if metadata_path == "bundle.json" else "version"] = [] if metadata_path == "bundle.json" else "9.9.9"
                write_json(path, data)
                shutil.copyfile(path, self.cache() / metadata_path)
                write_json(self.home / "constellation/receipt.json", {
                    **receipt, "catalog": installer._inventory(catalog), "cache": installer._inventory(self.cache()),
                })
                before = snapshot(self.home)
                with self.assertRaisesRegex(InstallError, "metadata differs"):
                    self.install()
                self.assertEqual(snapshot(self.home), before)
                self.assertEqual(self.backend.mutations, [])
                path.write_bytes(original)
                shutil.copyfile(path, self.cache() / metadata_path)
                write_json(self.home / "constellation/receipt.json", receipt)

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

    def test_installation_and_rollback_query_only_the_managed_marketplace(self) -> None:
        self.backend.fail_once = "add_plugin"
        with self.assertRaises(InstallError):
            self.install()
        self.assertTrue(self.backend.plugin_queries)
        self.assertEqual(set(self.backend.plugin_queries), {"constellation"})
        self.backend.plugin_queries.clear()
        self.install()
        self.assertTrue(self.backend.plugin_queries)
        self.assertEqual(set(self.backend.plugin_queries), {"constellation"})
        self.assert_unrelated_preserved()

    def test_failed_update_restores_prior_receipt_catalog_agents_and_native_state(self) -> None:
        self.install()
        updated = self.changed_bundle()
        before = snapshot(self.home)
        self.backend.fail_once = "add_plugin"
        with self.assertRaises(InstallError):
            self.install(updated)
        self.assertEqual(snapshot(self.home), before)
        self.assertEqual(self.receipt()["version"], self.current_version)
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

    def test_native_retaining_an_old_cache_cannot_report_a_successful_update(self) -> None:
        self.install()
        updated = self.changed_bundle()
        before = snapshot(self.home)
        old_cache = self.cache()
        previous = self.root / "previous-cache"
        shutil.copytree(old_cache, previous)
        native_add = self.backend.add_plugin
        first_attempt = True

        def retain_previous_once() -> dict:
            nonlocal first_attempt
            result = native_add()
            if first_attempt:
                first_attempt = False
                shutil.copytree(previous, old_cache)
            return result

        with patch.object(self.backend, "add_plugin", side_effect=retain_previous_once):
            with self.assertRaisesRegex(InstallError, "previous owned files and registration restored"):
                self.install(updated)
        self.assertEqual(snapshot(self.home), before)
        self.assertEqual(self.install(check=True)["status"], "checked")

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


@unittest.skipIf(os.name == "nt", "Codex native Windows is outside this Claude-only candidate")
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
                response = home / "plugin-response.json"
                print(response.read_text() if response.exists()
                      else json.dumps({"installed": [], "available": []}))
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

    def test_marketplace_filter_is_one_structured_native_cli_argument(self) -> None:
        self.assertEqual(self.client.plugins(marketplace="constellation"), [])
        calls = [json.loads(line) for line in (self.home / "synthetic-calls.jsonl").read_text().splitlines()]
        self.assertEqual([row["args"] for row in calls],
                         [["plugin", "list", "--marketplace", "constellation", "--json"]])

    def test_installed_rows_normalize_legacy_and_current_cli_envelopes(self) -> None:
        row = {"pluginId": PLUGIN_ID, "enabled": True, "version": "1.3.0"}
        available = {"pluginId": "candidate@constellation", "enabled": True}
        for response in ({"plugins": [row]}, {"installed": [row]},
                         {"installed": [row], "available": [available]}):
            with self.subTest(envelope=list(response)):
                write_json(self.home / "plugin-response.json", response)
                self.assertEqual(self.client.plugins(marketplace="constellation"), [row])

    def test_available_rows_never_establish_installation(self) -> None:
        row = {"pluginId": PLUGIN_ID, "enabled": True, "version": "1.3.0"}
        write_json(self.home / "plugin-response.json", {"installed": [], "available": [row]})
        self.assertEqual(self.client.plugins(marketplace="constellation"), [])
        self.assertEqual(installer._registered(self.client, self.root / "catalog"), (False, None))

    def test_ambiguous_and_malformed_plugin_envelopes_are_rejected(self) -> None:
        row = {"pluginId": PLUGIN_ID, "enabled": True}
        responses = ([], {}, {"plugins": None}, {"plugins": [None]},
                     {"installed": [], "plugins": []}, {"installed": [], "available": {}},
                     {"available": [row]}, {"installed": [row], "available": [None]},
                     {"installed": [row], "unknown": []},
                     {"installed": [{**row, "installed": False}]},
                     {"plugins": [{**row, "enabled": 1}]}, {"installed": [{}]})
        for response in responses:
            with self.subTest(response=response):
                write_json(self.home / "plugin-response.json", response)
                with self.assertRaises(NativeError):
                    self.client.plugins(marketplace="constellation")

    def test_general_diagnostics_keep_the_unscoped_plugin_query(self) -> None:
        with patch.object(self.client, "plugins", wraps=self.client.plugins) as queried, \
                patch.object(native_adapter, "_Rpc", side_effect=NativeError("Synthetic unavailable RPC")):
            result = self.client.capabilities()
        queried.assert_called_once_with()
        self.assertEqual(result["checks"]["plugins"]["status"], "ok")
        calls = [json.loads(line) for line in (self.home / "synthetic-calls.jsonl").read_text().splitlines()]
        self.assertEqual(calls[0]["args"], ["plugin", "list", "--json"])


@unittest.skipUnless(shutil.which("codex"), "Native Codex executable is unavailable; synthetic tests are separate")
@unittest.skipIf(os.name == "nt", "Codex native Windows is outside this Claude-only candidate")
class RealNativeInstallationTests(BundleCase):
    def test_real_native_same_version_update_refreshes_runtime_bytes(self) -> None:
        home = self.root / "same-version-home"
        home.mkdir()
        receiver = self.root / "same-version-receiver"
        receiver.mkdir()
        client = NativeClient(home, shutil.which("codex") or "codex", receiver, timeout=45)
        installed = install_bundle(self.bundle, home, client=client)
        source = self.source_copy("same-version-source")
        runtime = source / "ecosystem/runtime/workflow.py"
        runtime.write_bytes(runtime.read_bytes() + b"\n# Synthetic same-version payload refresh.\n")
        update = self.root / "same-version-bundle"
        build_bundle(update, MODULES, source_root=source)
        result = install_bundle(update, home, client=client)
        self.assertEqual(result["version"], installed["version"])
        cache = home / "plugins/cache/constellation/constellation" / installed["version"]
        self.assertEqual((cache / "ecosystem/runtime/workflow.py").read_bytes(), runtime.read_bytes())
        self.assertNotEqual((cache / "ecosystem/runtime/workflow.py").read_bytes(),
                            (self.bundle / "ecosystem/runtime/workflow.py").read_bytes())

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
@unittest.skipIf(os.name == "nt", "Codex native Windows is outside this Claude-only candidate")
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

        with patch.object(client, "plugins", wraps=client.plugins) as queried:
            result = client.exclude_source_skills(source)
        queried.assert_called_once_with(marketplace="constellation")
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
        version = json.loads((self.bundle / PLUGIN_MANIFEST).read_text())["version"]
        cache_root = home / "plugins/cache/constellation/constellation" / version
        for unsafe in (source_alias, self.bundle, cache_root, self.root):
            with self.subTest(source=unsafe):
                before = self.preference_snapshot(home)
                with self.assertRaises(NativeError):
                    client.exclude_source_skills(unsafe)
                self.assertEqual(self.preference_snapshot(home), before)

        manifest = source / "ecosystem/manifests/codex-plugin.json"
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
        role = {"coding": "coder", "mathematics": "mathematician",
                "quant-research": "coder", "writter": "editor"}[self.module]
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
@unittest.skipIf(os.name == "nt", "POSIX export harness; run windows_acceptance.py for native Windows")
class DistributedSuiteTests(unittest.TestCase):
    def test_full_and_each_module_run_their_shipped_suites_without_mutating_bundle(self) -> None:
        with tempfile.TemporaryDirectory(prefix="constellation-distributed-suite-") as temporary:
            root = Path(temporary).resolve()
            selections = [("full", ALL_MODULES), *((module, (module,)) for module in ALL_MODULES)]
            cases = []
            for name, modules in selections:
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
                environment.pop("CONSTELLATION_STATE_DIR", None)
                cases.append((name, bundle, manifest, before, receiver, environment))

            # Each child has its own receiver, native home and default state.
            # Run bounded independent processes; inspect every result in order.
            with ThreadPoolExecutor(max_workers=2) as executor:
                pending = [executor.submit(
                    subprocess.run,
                    [sys.executable, "-I", "-B", "-m", "unittest", "discover", "-s",
                     str(bundle / "ecosystem/tests"), "-q"], cwd=receiver, env=environment,
                    capture_output=True, text=True, timeout=300,
                ) for _, bundle, _, _, receiver, environment in cases]
                for (name, bundle, manifest, before, receiver, _), future in zip(cases, pending):
                    with self.subTest(distribution=name):
                        result = future.result()
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

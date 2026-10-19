"""Exercise the installed hook command against real, isolated filesystem state.

Native registration is synthetic, as in test_package. These tests establish the
bootstrap's behavior, not Codex hook trust or native event delivery.
"""
from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import textwrap
import time
from typing import Any

from test_package import (
    BundleCase, MODULES, SOURCE_DIR, SyntheticNativeClient,
    build_bundle, install_bundle, snapshot, write_json,
)
from install import InstallError


class HookEntryTests(BundleCase):
    def runtime_bundle(self, label: str, *, hold: bool = False) -> Path:
        """Ship a visible runtime through the normal bundle and receipt checks."""
        source = self.source_copy("source-" + label)
        metadata = json.loads((source / "ecosystem/plugin.json").read_text())
        metadata["version"] = "8.0." + label
        write_json(source / "ecosystem/plugin.json", metadata)
        runtime = textwrap.dedent(f"""\
            import json
            import os
            from pathlib import Path
            import signal
            import sys

            Path(os.environ["CONSTELLATION_TEST_MARKER"]).write_text({label!r})

            def main(argv=None):
                if {hold!r}:
                    signal.setitimer(signal.ITIMER_REAL, 0)
                    Path(os.environ["CONSTELLATION_TEST_READY"]).write_text("ready")
                    sys.stdin.readline()
                print(json.dumps({{"systemMessage": {label!r}}}))
                return 0

            if __name__ == "__main__":
                raise SystemExit(main())
            """)
        (source / "ecosystem/hooks.py").write_text(runtime)
        bundle = self.root / ("bundle-" + label)
        build_bundle(bundle, MODULES, source_root=source)
        return bundle

    def installed(self, bundle: Path | None = None, *, home: Path | None = None
                  ) -> tuple[Path, SyntheticNativeClient]:
        home = home or self.root / "codex home with spaces"
        backend = SyntheticNativeClient(home)
        install_bundle(bundle or self.bundle, home, client=backend)
        return home, backend

    def command(self, home: Path, event: str = "PreToolUse") -> str:
        receipt = json.loads((home / "constellation/receipt.json").read_text())
        cache = home / "plugins/cache/constellation/constellation" / receipt["version"]
        manifest = json.loads((cache / "ecosystem/hooks.json").read_text())
        return manifest["hooks"][event][0]["hooks"][0]["command"]

    def environment(self, home: Path) -> dict[str, str]:
        environment = dict(os.environ)
        environment.pop("CODEX_THREAD_ID", None)
        environment.pop("PYTHONPATH", None)
        environment["CODEX_HOME"] = str(home)
        environment["CONSTELLATION_TEST_MARKER"] = str(self.root / "runtime-imported")
        environment["CONSTELLATION_TEST_READY"] = str(self.root / "runtime-ready")
        return environment

    def invoke(self, home: Path, *, event: str = "PreToolUse", command: str | None = None,
               environment: dict[str, str] | None = None, payload: dict[str, Any] | None = None,
               cwd: Path | None = None) -> dict[str, Any]:
        result = subprocess.run(
            ["/bin/sh", "-c", command or self.command(home, event)],
            input=json.dumps(payload or {}), env=environment or self.environment(home),
            cwd=cwd or self.root, capture_output=True, text=True, timeout=5,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr, "")
        value = json.loads(result.stdout)
        self.assertIsInstance(value, dict)
        return value

    def assert_failure(self, value: dict[str, Any], event: str = "PreToolUse") -> None:
        if event == "PreToolUse":
            self.assertEqual(value["hookSpecificOutput"]["permissionDecision"], "deny")
            self.assertEqual(value["hookSpecificOutput"]["hookEventName"], event)
        elif event in {"Stop", "SubagentStop"}:
            self.assertNotIn("decision", value)
            self.assertIn("INCOMPLETE", value["systemMessage"])
            self.assertIn("No task closure was approved", value["systemMessage"])
        else:
            self.assertTrue(value["systemMessage"])

    def wait_for_file(self, path: Path, process: subprocess.Popen[str]) -> None:
        deadline = time.monotonic() + 5
        while not path.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.01)
        if not path.exists():
            process.kill()
            output, error = process.communicate(timeout=5)
            self.fail("Fixture did not reach its barrier: " + output + error)

    def test_captured_manifest_command_survives_upgrade_and_deleted_old_cache(self) -> None:
        release_a = self.runtime_bundle("a")
        release_b = self.runtime_bundle("b")
        home, backend = self.installed(release_a)
        command_a = self.command(home)
        self.assertEqual(self.invoke(home, command=command_a), {"systemMessage": "a"})
        cache_a = home / "plugins/cache/constellation/constellation/8.0.a"
        self.assertTrue(cache_a.is_dir())

        install_bundle(release_b, home, client=backend)

        self.assertFalse(cache_a.exists())
        self.assertEqual(command_a, self.command(home))
        self.assertEqual(self.invoke(home, command=command_a), {"systemMessage": "b"})
        self.assertEqual((self.root / "runtime-imported").read_text(), "b")

    def test_every_distributed_module_bootstraps_independently(self) -> None:
        bundle = self.runtime_bundle("modules")
        for module in MODULES:
            with self.subTest(module=module):
                home = self.root / (module + "-home")
                install_bundle(bundle, home, modules=[module], client=SyntheticNativeClient(home))
                self.assertEqual(self.invoke(home), {"systemMessage": "modules"})

    def test_invalid_module_receipts_reject_before_runtime_import(self) -> None:
        home, _ = self.installed(self.runtime_bundle("invalidmodules"))
        command = self.command(home)
        path = home / "constellation/receipt.json"
        original = json.loads(path.read_text())
        for modules in ([], "quant-research", ["unknown"], ["quant-research-extra"],
                        [self.module, self.module], [1]):
            with self.subTest(modules=modules):
                write_json(path, {**original, "modules": modules})
                before = snapshot(home)

                self.assert_failure(self.invoke(home, command=command))

                self.assertFalse((self.root / "runtime-imported").exists())
                self.assertEqual(snapshot(home), before)

    def test_manifest_resolves_codex_home_with_spaces_and_home_fallback(self) -> None:
        bundle = self.runtime_bundle("paths")
        user_home = self.root / "user home with spaces"
        home, _ = self.installed(bundle, home=user_home / ".codex")
        command = self.command(home)
        self.assertEqual(self.invoke(home, command=command), {"systemMessage": "paths"})
        environment = self.environment(home)
        environment["HOME"] = str(user_home)
        for value in (None, ""):
            with self.subTest(codex_home=value):
                if value is None:
                    environment.pop("CODEX_HOME", None)
                else:
                    environment["CODEX_HOME"] = value
                self.assertEqual(self.invoke(home, command=command, environment=environment),
                                 {"systemMessage": "paths"})

    def test_isolated_interpreter_ignores_pythonpath_and_working_directory_modules(self) -> None:
        home, _ = self.installed(self.runtime_bundle("isolated"))
        untrusted = self.root / "untrusted working directory"
        untrusted.mkdir()
        marker = self.root / "untrusted-code-executed"
        attack = f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\n"
        for name in ("sitecustomize.py", "json.py", "hashlib.py", "hooks.py", "install.py"):
            (untrusted / name).write_text(attack)
        environment = self.environment(home)
        environment["PYTHONPATH"] = str(untrusted)
        before = snapshot(untrusted)

        value = self.invoke(home, cwd=untrusted, environment=environment)

        self.assertEqual(value, {"systemMessage": "isolated"})
        self.assertFalse(marker.exists())
        self.assertEqual(snapshot(untrusted), before)

    def test_payload_paths_do_not_select_executable_code(self) -> None:
        home, _ = self.installed()
        untrusted = self.root / "payload selected code"
        untrusted.mkdir()
        marker = self.root / "payload-code-executed"
        attack = f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\n"
        for name in ("hooks.py", "core.py", "install.py", "sitecustomize.py"):
            (untrusted / name).write_text(attack)
        payload = {"hook_event_name": "PreToolUse", "session_id": "entry-fixture-session",
                   "turn_id": "entry-fixture-turn", "cwd": str(untrusted),
                   "tool_name": "apply_patch", "tool_input": {"input":
                       "*** Begin Patch\n*** Add File: result.txt\n+fixture\n*** End Patch"},
                   "plugin_root": str(untrusted), "code_root": str(untrusted),
                   "runtime_path": str(untrusted / "hooks.py"),
                   "state_dir": str(untrusted), "CODEX_HOME": str(untrusted)}

        self.assertEqual(self.invoke(home, payload=payload, cwd=untrusted), {})
        self.assertFalse(marker.exists())

    def test_exclusive_installer_lock_returns_immediate_event_specific_failure(self) -> None:
        home, _ = self.installed(self.runtime_bundle("locked"))
        state = home / "constellation/state"
        state.mkdir()
        (state / "sentinel.json").write_text('{"revision":7}\n')
        before = snapshot(home)
        with (home / "constellation/.install.lock").open("rb") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            for event in ("PreToolUse", "Stop", "SubagentStop", "UserPromptSubmit", "SubagentStart"):
                with self.subTest(event=event):
                    started = time.monotonic()
                    value = self.invoke(home, event=event)
                    self.assertLess(time.monotonic() - started, 2)
                    self.assert_failure(value, event)
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        self.assertFalse((self.root / "runtime-imported").exists())
        self.assertEqual(snapshot(home), before)

    def test_repeated_stop_failures_warn_without_requesting_another_continuation(self) -> None:
        bundle = self.runtime_bundle("repeatedstop")
        for condition in ("locked", "corrupt-receipt"):
            with self.subTest(condition=condition):
                home, _ = self.installed(bundle, home=self.root / ("home-" + condition))
                commands = {event: self.command(home, event) for event in ("Stop", "SubagentStop")}
                state = home / "constellation/state"
                state.mkdir()
                (state / "sentinel.json").write_text('{"revision":7}\n')
                if condition == "corrupt-receipt":
                    (home / "constellation/receipt.json").write_text('{"schema":')
                before = snapshot(home)
                with (home / "constellation/.install.lock").open("rb") as stream:
                    if condition == "locked":
                        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    for event, command in commands.items():
                        for repeat, active in enumerate((False, True, True)):
                            with self.subTest(event=event, repeat=repeat, stop_hook_active=active):
                                payload = {"hook_event_name": event,
                                           "session_id": "repeated-stop-fixture-session",
                                           "turn_id": "repeated-stop-fixture-turn",
                                           "agent_id": "repeated-stop-fixture-agent",
                                           "cwd": str(self.root), "stop_hook_active": active}

                                value = self.invoke(home, event=event, command=command, payload=payload)

                                self.assert_failure(value, event)
                                self.assertFalse((self.root / "runtime-imported").exists())
                                self.assertEqual(snapshot(home), before)
                    if condition == "locked":
                        fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

    def test_shared_lock_is_held_through_runtime_and_prevents_installer_mutation(self) -> None:
        bundle = self.runtime_bundle("holding", hold=True)
        home, backend = self.installed(bundle)
        process = subprocess.Popen(
            ["/bin/sh", "-c", "exec " + self.command(home)], cwd=self.root,
            env=self.environment(home), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True,
        )
        try:
            self.wait_for_file(self.root / "runtime-ready", process)
            before = snapshot(home)
            mutations = list(backend.mutations)
            with (home / "constellation/.install.lock").open("rb") as stream:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(InstallError):
                install_bundle(bundle, home, client=backend)
            self.assertEqual(backend.mutations, mutations)
            self.assertEqual(snapshot(home), before)
            output, error = process.communicate("release\n", timeout=5)
            self.assertEqual(process.returncode, 0, output + error)
            self.assertEqual(error, "")
            self.assertEqual(json.loads(output), {"systemMessage": "holding"})
            with (home / "constellation/.install.lock").open("rb") as stream:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        finally:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=5)

    def test_incomplete_or_modified_installation_rejects_before_runtime_import(self) -> None:
        home, _ = self.installed(self.runtime_bundle("integrity"))
        command = self.command(home)
        pristine = self.root / "pristine-home"
        shutil.copytree(home, pristine)
        relative_targets = {
            "catalog": "constellation/catalog/plugins/constellation/ecosystem/hooks.py",
            "cache": "plugins/cache/constellation/constellation/8.0.integrity/ecosystem/hooks.py",
            "receipt": "constellation/receipt.json",
            "entry": "constellation/hook.py",
            "lock": "constellation/.install.lock",
        }
        cases = [(group, action) for group in ("catalog", "cache")
                 for action in ("missing", "hash", "mode", "symlink")]
        cases += [("receipt", action) for action in
                  ("missing", "json", "schema", "hook-hash", "hook-mode", "symlink")]
        cases += [("entry", action) for action in ("hash", "mode", "symlink")]
        cases += [("lock", "symlink")]
        for index, (group, action) in enumerate(cases):
            with self.subTest(group=group, action=action):
                shutil.rmtree(home)
                shutil.copytree(pristine, home)
                target = home / relative_targets[group]
                if action == "missing":
                    target.unlink()
                elif action == "hash":
                    target.write_text(target.read_text() + "\n# unrecorded modification\n")
                elif action == "mode":
                    target.chmod(0o600)
                elif action == "symlink":
                    outside = self.root / ("external-target-" + str(index))
                    target.replace(outside)
                    target.symlink_to(outside)
                elif action == "json":
                    target.write_text('{"schema":')
                else:
                    receipt = json.loads(target.read_text())
                    if action == "schema":
                        receipt["schema"] = 2
                        receipt.pop("hook", None)
                    elif action == "hook-hash":
                        receipt["hook"]["sha256"] = "0" * 64
                    elif action == "hook-mode":
                        receipt["hook"]["mode"] = 0o755
                    write_json(target, receipt)
                before = snapshot(home)

                value = self.invoke(home, command=command)

                self.assert_failure(value)
                self.assertFalse((self.root / "runtime-imported").exists())
                self.assertEqual(snapshot(home), before)

    def test_catalog_and_cache_cannot_be_redirected_through_parent_symlinks(self) -> None:
        bundle = self.runtime_bundle("parents")
        for index, relative in enumerate(("constellation/catalog", "plugins/cache")):
            with self.subTest(path=relative):
                home, _ = self.installed(bundle, home=self.root / ("home-" + str(index)))
                command = self.command(home)
                target = home / relative
                external = self.root / ("external-directory-" + str(index))
                target.replace(external)
                target.symlink_to(external, target_is_directory=True)
                before = snapshot(home)

                self.assert_failure(self.invoke(home, command=command))

                self.assertFalse((self.root / "runtime-imported").exists())
                self.assertEqual(snapshot(home), before)

    def test_sigkill_during_install_leaves_controlled_failure_after_lock_release(self) -> None:
        home, _ = self.installed(self.runtime_bundle("beforekill"))
        command = self.command(home)
        update = self.runtime_bundle("afterkill")
        ready = self.root / "installer-ready"
        script = textwrap.dedent("""\
            import pathlib
            import sys
            import tempfile
            sys.path.insert(0, sys.argv[1])
            sys.path.insert(0, sys.argv[2])
            from test_package import SyntheticNativeClient
            from install import install_bundle

            class PausingNativeClient(SyntheticNativeClient):
                def add_plugin(self):
                    result = super().add_plugin()
                    pathlib.Path(sys.argv[5]).write_text("ready")
                    sys.stdin.readline()
                    return result

            home = pathlib.Path(sys.argv[4])
            # SIGKILL bypasses TemporaryDirectory cleanup; retain all fixture
            # files below the owning test's temporary root.
            tempfile.tempdir = str(pathlib.Path(sys.argv[5]).parent)
            install_bundle(pathlib.Path(sys.argv[3]), home, client=PausingNativeClient(home))
            """)
        process = subprocess.Popen(
            [sys.executable, "-I", "-B", "-c", script, str(SOURCE_DIR),
             str(SOURCE_DIR / "tests"), str(update), str(home), str(ready)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        try:
            self.wait_for_file(ready, process)
            self.assert_failure(self.invoke(home, command=command))
            process.kill()
            process.communicate(timeout=5)
            self.assertEqual(process.returncode, -signal.SIGKILL)
            self.assertFalse((home / "plugins/cache/constellation/constellation/8.0.beforekill").exists())
            self.assertTrue((home / "plugins/cache/constellation/constellation/8.0.afterkill").is_dir())
            self.assertEqual(json.loads((home / "constellation/receipt.json").read_text())["version"],
                             "8.0.beforekill")
            before = snapshot(home)

            self.assert_failure(self.invoke(home, command=command))

            self.assertFalse((self.root / "runtime-imported").exists())
            self.assertEqual(snapshot(home), before)
        finally:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=5)

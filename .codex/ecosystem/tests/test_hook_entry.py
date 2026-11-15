"""Exercise the installed hook command against real, isolated filesystem state.

Native registration is synthetic, as in test_package. These tests establish the
bootstrap's behavior, not Codex hook trust or native event delivery.
"""
from __future__ import annotations

try:
    import fcntl
except ImportError:  # Native Codex bootstrap is outside the Windows Claude target.
    fcntl = None
import json
import importlib.util
import hashlib
import os
from pathlib import Path
import shutil
import shlex
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from unittest import mock
from typing import Any

from test_package import (
    BundleCase, BundleError, METHODS, MODULES, SOURCE_DIR, SyntheticNativeClient,
    build_bundle, install_bundle, snapshot, write_json,
)
from install import InstallError


@unittest.skipIf(os.name == "nt", "POSIX Codex bootstrap; Windows candidate targets Claude only")
class HookEntryTests(BundleCase):
    def runtime_bundle(self, label: str, *, hold: bool = False) -> Path:
        """Ship a visible runtime through the normal bundle and receipt checks."""
        source = self.source_copy("source-" + label)
        metadata = json.loads((source / "ecosystem/manifests/codex-plugin.json").read_text())
        metadata["version"] = "8.0." + label
        write_json(source / "ecosystem/manifests/codex-plugin.json", metadata)
        claude = json.loads((source / "ecosystem/manifests/claude-plugin.json").read_text())
        write_json(source / "ecosystem/manifests/claude-plugin.json", {**claude, "version": metadata["version"]})
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

    @unittest.skipUnless((SOURCE_DIR / "vault/workflow.py").is_file(), "optional vault profile")
    def test_one_installed_release_routes_vault_commands_and_real_event_payloads(self) -> None:
        """Exercise the native wire format under the same verified entry as the CLI."""
        from build import AVAILABLE_MODULES

        personal = self.root / "personal-bundle"
        build_bundle(personal, AVAILABLE_MODULES, source_root=SOURCE_DIR.parent)
        home, _ = self.installed(personal)
        project = self.root / "vault"
        project.mkdir()
        env = self.environment(home)
        env["HOME"] = str(self.root / "user")
        env.pop("CODEX_THREAD_ID", None)
        def git(*args: str, cwd: Path = project) -> None:
            subprocess.run(["git", *args], cwd=cwd, env=env, check=True, capture_output=True)

        git("init", "-q", "-b", "main")
        git("config", "user.name", "Synthetic profile test")
        git("config", "user.email", "fixture@example.invalid")
        git("config", "core.hooksPath", str(project / ".git/hooks"))
        git("config", "commit.gpgsign", "false")
        git("commit", "-qm", "Start fixture", "--allow-empty")
        bare = self.root / "remote.git"
        git("init", "--bare", "-q", str(bare))
        git("remote", "add", "origin", str(bare))
        git("push", "-qu", "origin", "main")

        entry = home / "constellation/run"
        def command(*args: str, data: dict | None = None, expected: int = 0, environment=None) -> dict:
            process = subprocess.run([str(entry), *args], cwd=project, env=environment or env,
                                     input=json.dumps(data or {}), text=True, capture_output=True, timeout=20)
            self.assertEqual(process.returncode, expected, process.stdout + process.stderr)
            return json.loads(process.stdout) if process.stdout else {}

        session = "fixture-vault-session"
        fake_git = project / "git"
        marker = self.root / "project-git-must-not-run"
        fake_git.write_text("#!/bin/sh\n: > " + shlex.quote(str(marker)) + "\nexit 1\n")
        fake_git.chmod(0o755)
        event_env = {**env, "PATH": str(project) + os.pathsep + env["PATH"],
                     "GIT_DIR": str(self.root / "false-owner")}
        def event(name: str, **fields: object) -> dict:
            return command(name, environment=event_env, data={"hook_event_name": name, "turn_id": "fixture-turn",
                                      "session_id": session, "cwd": str(project), **fields})

        options = ("--project-root", str(project))
        command("install-vault", *options, "--expected-bundle-sha256", "0" * 64, expected=2)
        self.assertFalse((home / "constellation-vault.json").exists())
        self.assertEqual(command("register-vault", *options)["root"], str(project))
        binding = home / "constellation-vault.json"
        original = binding.read_bytes()
        command("register-vault", *options)
        self.assertEqual(binding.read_bytes(), original)
        self.assertEqual(binding.stat().st_nlink, 1)

        # A disk identity change requires an explicit inspected hash; normal
        # registration remains fail-closed until the operator renews it.
        stale = json.loads(original)
        stale["owner"][0] += 1
        stale["git_dir"][0] += 1
        binding.write_text(json.dumps(stale))
        stale_bytes = binding.read_bytes()
        inspected = command("renew-vault", *options)
        self.assertEqual(inspected["status"], "renewal_required")
        command("register-vault", *options, expected=2)
        renewed = command("renew-vault", *options, "--expected-registration-sha256",
                          inspected["expected_registration_sha256"])
        self.assertEqual(renewed["status"], "renewed")
        self.assertEqual(Path(renewed["recovery"]).read_bytes(), stale_bytes)
        self.assertEqual(command("renew-vault", *options)["status"], "current")
        original = binding.read_bytes()

        prompt = event("UserPromptSubmit", prompt="synthetic-secret-never-read")
        self.assertIn("OmarOS", prompt["hookSpecificOutput"]["additionalContext"])
        command("vault", *options, "--session", session, "plan",
                data={"requirements": ["Synthetic scoped artifact."], "paths": ["result.md"]})
        tool = {"tool_name": "functions.apply_patch", "tool_input": {"command":
            "*** Begin Patch\n*** Add File: result.md\n+result\n*** End Patch"}}
        self.assertEqual(event("PreToolUse", **tool), {})
        tool["tool_input"] = {"command": "*** Begin Patch\n*** Delete File: result.md\n*** End Patch"}
        self.assertEqual(event("PreToolUse", **tool)["hookSpecificOutput"]["permissionDecision"], "deny")
        first = event("Stop", stop_hook_active=False)
        self.assertEqual(first["decision"], "block")
        self.assertTrue(first["reason"])
        replay = event("Stop", stop_hook_active=False)
        self.assertIs(replay.get("continue"), False)
        self.assertNotIn("decision", replay)
        status = command("vault", *options, "--session", session, "status")
        self.assertEqual(status["stop_attempts"], 1)
        self.assertIsNone(status["finished"])
        self.assertNotIn("synthetic-secret-never-read", json.dumps(status))
        nested = project / "nested"
        nested.mkdir()
        git("init", "-q", cwd=nested)
        outside = self.root / "sibling"
        outside.mkdir()
        escaping = {"tool_name": "functions.apply_patch", "tool_input": {"command":
            f"*** Begin Patch\n*** Add File: {project}/result.md\n+x\n*** End Patch"}}
        self.assertEqual(event("PreToolUse", cwd=str(outside), **escaping)
                         ["hookSpecificOutput"]["permissionDecision"], "deny")
        other = event("UserPromptSubmit", cwd=str(nested))
        self.assertNotIn("OmarOS lifecycle active", other["hookSpecificOutput"]["additionalContext"])
        self.assertFalse((nested / ".git/omaros").exists())

        project.rename(self.root / "original-owner")
        project.mkdir()
        git("init", "-q")
        self.assertEqual(event("PreToolUse", **tool)["hookSpecificOutput"]["permissionDecision"], "deny")
        command("register-vault", *options, expected=2)
        self.assertEqual(binding.read_bytes(), original)
        self.assertFalse((project / ".git/omaros").exists())
        self.assertFalse(marker.exists())

    @unittest.skipUnless((SOURCE_DIR / "vault/workflow.py").is_file(), "optional vault profile")
    def test_enrollment_writer_retains_the_exclusive_device_lock_after_dispatch(self) -> None:
        """A child which can still mutate settings prevents a conflicting update."""
        import contextlib
        import io
        from build import AVAILABLE_MODULES
        with mock.patch.object(sys, "path", [str(SOURCE_DIR.parent), *sys.path]):
            from ecosystem.vault import install as vault_install
        import hook_entry

        personal = self.root / "writer-bundle"
        build_bundle(personal, AVAILABLE_MODULES, source_root=SOURCE_DIR.parent)
        home, _ = self.installed(personal)
        repo = self.root / "writer-project"
        repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True, capture_output=True)
        lock = home / "constellation/.install.lock"
        child = None

        def write_settings(root, codex_home, *, codex, expected_binding, install_lock_fd):
            nonlocal child
            self.assertEqual(root, repo)
            self.assertEqual(codex_home, home)
            self.assertTrue(os.path.samestat(lock.stat(), os.fstat(install_lock_fd)))
            self.assertFalse(os.get_inheritable(install_lock_fd))
            child = subprocess.Popen([sys.executable, "-I", "-c", "import sys; sys.stdin.read()"],
                                     stdin=subprocess.PIPE, pass_fds=(install_lock_fd,))
            return 0

        try:
            with mock.patch.object(vault_install, "entrypoint", side_effect=write_settings), \
                    mock.patch.object(sys, "path", list(sys.path)), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(hook_entry.dispatch_installed(
                    home, "install-vault", ["--project-root", str(repo)]), 0)
            with lock.open("rb") as contender:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(contender.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
                child.communicate(input=b"done", timeout=5)
                fcntl.flock(contender.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            if child is not None and child.poll() is None:
                child.kill()
                child.communicate(timeout=5)


    def test_updates_receive_immutable_programs_after_the_device_lock_is_released(self) -> None:
        source = self.source_copy("scheduled-source")
        (source / "ecosystem/updates.py").write_text(textwrap.dedent("""\
            import fcntl, hashlib, json
            def run(args, *, home, sync_source, verifier_source):
                with (home / 'constellation/.install.lock').open('rb') as lock:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    print(json.dumps([hashlib.sha256(data).hexdigest()
                                      for data in (sync_source, verifier_source)]))
                return 0
            """))
        candidate = self.root / "scheduled-bundle"
        build_bundle(candidate, MODULES, source_root=source)
        home, _ = self.installed(candidate)
        receipt = json.loads((home / "constellation/receipt.json").read_text())
        result = subprocess.run([str(home / "constellation/run"), "updates", "fixture"],
                                env=self.environment(home), cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = [receipt["cache"]["ecosystem/" + name]["sha256"] for name in ("sync.py", "hook_entry.py")]
        self.assertEqual(json.loads(result.stdout), expected)

        # A non-cooperating replacement after the initial inventory check cannot
        # turn changed bytes into an executable snapshot.
        import hook_entry
        package = home / "constellation/catalog/plugins/constellation"
        (package / "ecosystem/sync.py").write_text("raise AssertionError('substituted program')")
        with self.assertRaisesRegex(hook_entry.EntryError, "differs from its receipt"):
            hook_entry._standalone_snapshot(package, receipt["cache"], "sync.py")


    def test_native_launcher_uses_the_installer_python_without_path_discovery(self) -> None:
        home = self.root / "device's selected home"
        home, _ = self.installed(self.runtime_bundle("boundpython"), home=home)
        env = {**self.environment(home), "PATH": str(self.root / "empty-path")}
        self.assertIsNone(shutil.which("python3", path=env["PATH"]))
        self.assertEqual(self.invoke(home, environment=env), {"systemMessage": "boundpython"})
        # Explicit invocation remains bound to the same home even if the ambient
        # computer or caller selects a different Codex installation.
        env["CODEX_HOME"] = str(self.root / "different-home")
        cmd = shlex.quote(str(home / "constellation/run")) + " Stop"
        self.assertEqual(self.invoke(home, command=cmd, environment=env, event="Stop"),
                         {"systemMessage": "boundpython"})

    def test_unavailable_python_denies_native_edits_and_fails_operator_commands(self) -> None:
        from hook_entry import launcher_bytes
        launcher = self.root / "run"
        missing = str(self.root / "removed interpreter")
        launcher.write_bytes(launcher_bytes(missing, self.root, missing, "0" * 64))
        launcher.chmod(0o700)
        for event in ("PreToolUse", "Stop"):
            result = subprocess.run([str(launcher), event], text=True, capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 0)
            self.assert_failure(json.loads(result.stdout), event)
        command = subprocess.run([str(launcher), "cli", "git", "--help"], capture_output=True, timeout=5)
        self.assertNotEqual(command.returncode, 0)

    def test_tampered_bootstrap_cannot_execute_before_native_verification(self) -> None:
        home, _ = self.installed()
        entry = home / "constellation/hook.py"
        marker = self.root / "tampered-entry-was-executed"
        entry.write_text(f"from pathlib import Path\nPath({str(marker)!r}).touch()\nprint('{{}}')\n")
        for event in ("PreToolUse", "Stop"):
            self.assert_failure(self.invoke(home, event=event), event)
        cli = subprocess.run([str(home / "constellation/run"), "cli", "git", "--help"], capture_output=True)
        self.assertNotEqual(cli.returncode, 0)
        self.assertFalse(marker.exists())

    def test_verified_bootstrap_executes_the_bytes_captured_before_path_replacement(self) -> None:
        from hook_entry import _VERIFY_ENTRY
        entry = self.root / "entry.py"
        entry.write_text("captured_code_ran = True\n")
        entry.chmod(0o644)
        expected = hashlib.sha256(entry.read_bytes()).hexdigest()
        digest_function = hashlib.sha256
        def swap_after_read(data: bytes):
            entry.rename(self.root / "original.py")
            entry.write_text("raise AssertionError('substituted code ran')\n")
            return digest_function(data)
        proof = {}
        with mock.patch.object(sys, "argv", ["-c", str(entry), expected]), \
                mock.patch.object(hashlib, "sha256", side_effect=swap_after_read):
            exec(_VERIFY_ENTRY, proof)
        self.assertTrue(proof["namespace"]["captured_code_ran"])

    def test_redirected_venv_alias_cannot_execute_project_code(self) -> None:
        from hook_entry import launcher_bytes
        marker = self.root / "foreign-python-ran"
        foreign = self.root / "project-python"
        foreign.write_text("#!/bin/sh\n: > " + shlex.quote(str(marker)) + "\nprintf '{}\\n'\n")
        foreign.chmod(0o755)
        alias = self.root / "venv-python"
        alias.symlink_to(foreign)
        target = str(Path(sys.executable).resolve(strict=True))
        run = self.root / "bound-run"
        run.write_bytes(launcher_bytes(str(alias), self.root, target, "0" * 64))
        run.chmod(0o700)
        result = subprocess.run([str(run), "PreToolUse"], text=True, capture_output=True)
        self.assert_failure(json.loads(result.stdout))
        self.assertFalse(marker.exists())

    def test_cli_mode_rejects_a_damaged_release_with_nonzero_exit(self) -> None:
        home, _ = self.installed()
        entry = home / "constellation/hook.py"
        args = [sys.executable, "-I", str(entry), "cli", "git", "--help"]
        env = self.environment(home)
        ok = subprocess.run(args, cwd=self.root, env=env, text=True, capture_output=True)
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        metadata = home / "constellation/receipt.json"
        metadata.write_text("{}")
        failed = subprocess.run(args, cwd=self.root, env=env, text=True, capture_output=True)
        self.assertNotEqual(failed.returncode, 0)
        self.assertEqual(failed.stdout, "")

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
                modules = [*METHODS, module] if module == "omaros" else [module]
                install_bundle(bundle, home, modules=modules, client=SyntheticNativeClient(home))
                self.assertEqual(self.invoke(home), {"systemMessage": "modules"})
        if "omaros" in MODULES:
            for partial in (["omaros"], [self.module, "omaros"]):
                with self.subTest(incomplete_personal_profile=partial):
                    home = self.root / ("incomplete-personal-" + str(len(partial)))
                    with self.assertRaisesRegex(BundleError, "all four general methods"):
                        install_bundle(bundle, home, modules=partial, client=SyntheticNativeClient(home))
                    self.assertFalse(home.exists())

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


    def test_reduced_current_receipt_inventory_rejects_before_runtime_import(self) -> None:
        home, _ = self.installed(self.runtime_bundle("currentinventory"))
        receipt_path = home / "constellation/receipt.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        payload = home / "constellation/catalog/plugins/constellation"
        cache = home / "plugins/cache/constellation/constellation" / receipt["version"]
        relative = "ecosystem/docs/windows.md"
        for root in (payload, cache):
            manifest_path = root / "bundle.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            (root / relative).unlink()
            manifest["files"].pop(relative)
            write_json(manifest_path, manifest)
        receipt["cache"].pop(relative)
        receipt["catalog"].pop("plugins/constellation/" + relative)
        record = {"sha256": hashlib.sha256((cache / "bundle.json").read_bytes()).hexdigest(), "mode": 0o644}
        receipt["cache"]["bundle.json"] = record
        receipt["catalog"]["plugins/constellation/bundle.json"] = record
        write_json(receipt_path, receipt)
        before = snapshot(home)
        spec = importlib.util.spec_from_file_location(
            "synthetic_current_source_entry", SOURCE_DIR / "hook_entry.py")
        assert spec is not None and spec.loader is not None
        source_entry = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(source_entry)
        with self.assertRaisesRegex(source_entry.EntryError, "active layout"):
            source_entry._verified_hook(home, home / "constellation/hook.py")
        self.assert_failure(self.invoke(home))
        self.assertFalse((self.root / "runtime-imported").exists())
        self.assertEqual(snapshot(home), before)


    @staticmethod
    def source_entry():
        spec = importlib.util.spec_from_file_location(
            "synthetic_current_agent_source_entry", SOURCE_DIR / "hook_entry.py")
        assert spec is not None and spec.loader is not None
        subject = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(subject)
        return subject

    def test_agent_receipt_projection_rejects_incomplete_or_mismatched_records_before_reads(self) -> None:
        home, _ = self.installed(self.runtime_bundle("agentrecords"))
        receipt_path = home / "constellation/receipt.json"
        original = json.loads(receipt_path.read_text(encoding="utf-8"))
        owned = sorted(original["agents"])[0]
        foreign = home / "agents/foreign-agent.toml"
        foreign.write_bytes(b"Synthetic independently owned profile.\n")
        subject = self.source_entry()
        original_path, original_relative = subject._path, subject._relative
        looked_up, interpreted = [], []

        def traced_relative(relative):
            interpreted.append(relative)
            return original_relative(relative)

        def traced_path(root, relative):
            looked_up.append(relative)
            return original_path(root, relative)

        subject._path, subject._relative = traced_path, traced_relative
        try:
            for mutation in ("missing", "extra", "hash", "mode"):
                candidate = json.loads(json.dumps(original))
                if mutation == "missing":
                    candidate["agents"].pop(owned)
                elif mutation == "extra":
                    candidate["agents"]["foreign-agent.toml"] = dict(original["agents"][owned])
                elif mutation == "hash":
                    candidate["agents"][owned]["sha256"] = "0" * 64
                else:
                    candidate["agents"][owned]["mode"] = 0o755
                write_json(receipt_path, candidate)
                before = snapshot(home)
                looked_up.clear()
                interpreted.clear()
                with self.subTest(mutation=mutation):
                    with self.assertRaisesRegex(subject.EntryError, "agent receipt"):
                        subject._verified_hook(home, home / "constellation/hook.py")
                    self.assertFalse(any(name.startswith("agents/") for name in looked_up))
                    if mutation in {"missing", "extra"}:
                        self.assertFalse(set(interpreted) & (set(original["agents"]) | {"foreign-agent.toml"}))
                    self.assert_failure(self.invoke(home))
                    self.assertFalse((self.root / "runtime-imported").exists())
                    self.assertEqual(snapshot(home), before)
        finally:
            subject._path, subject._relative = original_path, original_relative
            write_json(receipt_path, original)
        self.assertEqual(self.invoke(home), {"systemMessage": "agentrecords"})
        self.assertEqual(foreign.read_bytes(), b"Synthetic independently owned profile.\n")

    def test_owned_agent_projection_damage_rejects_before_runtime_import(self) -> None:
        home, _ = self.installed(self.runtime_bundle("agentfiles"))
        receipt = json.loads((home / "constellation/receipt.json").read_text(encoding="utf-8"))
        profile = home / "agents" / sorted(receipt["agents"])[0]
        content, mode = profile.read_bytes(), profile.stat().st_mode & 0o777
        external = self.root / "independently-held-agent.toml"
        external.write_bytes(content)
        subject = self.source_entry()
        for mutation in ("missing", "bytes", "mode", "symlink"):
            if mutation == "missing":
                profile.unlink()
            elif mutation == "bytes":
                profile.write_bytes(content + b"\n# Synthetic edit.\n")
            elif mutation == "mode":
                profile.chmod(0o755)
            else:
                profile.unlink()
                profile.symlink_to(external)
            before = snapshot(home)
            try:
                with self.subTest(mutation=mutation):
                    with self.assertRaises(subject.EntryError):
                        subject._verified_hook(home, home / "constellation/hook.py")
                    self.assert_failure(self.invoke(home))
                    self.assertFalse((self.root / "runtime-imported").exists())
                    self.assertEqual(snapshot(home), before)
                    self.assertEqual(external.read_bytes(), content)
            finally:
                profile.unlink(missing_ok=True)
                profile.write_bytes(content)
                profile.chmod(mode)
        self.assertEqual(self.invoke(home), {"systemMessage": "agentfiles"})

    def test_current_agent_projection_normalizes_mode_and_preserves_foreign_profiles(self) -> None:
        bundle = self.runtime_bundle("agentprojection")
        source = bundle / "ecosystem/agents/reviewer.toml"
        source.chmod(0o755)
        manifest = json.loads((bundle / "bundle.json").read_text(encoding="utf-8"))
        manifest["files"]["ecosystem/agents/reviewer.toml"]["mode"] = 0o755
        write_json(bundle / "bundle.json", manifest)
        home, _ = self.installed(bundle)
        receipt = json.loads((home / "constellation/receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["cache"]["ecosystem/agents/reviewer.toml"]["mode"], 0o755)
        self.assertEqual(receipt["agents"]["constellation-reviewer.toml"]["mode"], 0o644)
        foreign = home / "agents/unrelated-profile.toml"
        foreign.write_bytes(b"Synthetic unrelated profile, preserved verbatim.\n")
        held = self.root / "held-native-profile.toml"
        os.link(home / "agents/constellation-reviewer.toml", held)
        before = snapshot(home)
        subject = self.source_entry()
        self.assertEqual(subject._verified_hook(home, home / "constellation/hook.py").name, "hooks.py")
        self.assertEqual(self.invoke(home), {"systemMessage": "agentprojection"})
        self.assertEqual(snapshot(home), before)
        self.assertEqual(foreign.read_bytes(), b"Synthetic unrelated profile, preserved verbatim.\n")
        self.assertEqual(held.read_bytes(), source.read_bytes())

    def test_sync_launcher_runs_authenticated_snapshot_after_releasing_install_lock(self):
        source = self.source_copy("sync-launcher-source")
        (source / "ecosystem/sync.py").write_text(textwrap.dedent("""\
            import fcntl, json, os
            from pathlib import Path
            def main(args):
                home = Path(args[-1])
                assert args[-2] == '--codex-home'
                with (home / 'constellation/.install.lock').open('rb') as lock:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    Path(os.environ['CONSTELLATION_TEST_MARKER']).write_text('sync')
                    print(json.dumps({'args': args, 'home': str(home)}))
                return 0
            """))
        bundle = self.root / "sync-launcher-bundle"
        build_bundle(bundle, MODULES, source_root=source)
        home, _ = self.installed(bundle)
        environment = self.environment(home)
        launcher = home / "constellation/run"
        result = subprocess.run([str(launcher), "sync", "--restore", "fixture-recovery"],
                                env=environment, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {
            "args": ["--restore", "fixture-recovery", "--codex-home", str(home)], "home": str(home)})
        marker = Path(environment["CONSTELLATION_TEST_MARKER"])
        marker.unlink()
        result = subprocess.run([str(launcher), "sync", "--codex-home", str(self.root / "other")],
                                env=environment, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 2)
        self.assertIn("cannot override", result.stderr)
        self.assertFalse(marker.exists())


@unittest.skipIf(os.name == "nt", "Codex renewal uses POSIX atomic file exchange")
class VaultRegistrationRecoveryTests(unittest.TestCase):
    def setUp(self):
        from helpers import CODEX_DIR
        with mock.patch.object(sys, "path", [str(CODEX_DIR), *sys.path]):
            from ecosystem import hooks
        self.hooks = hooks
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.home = self.root / "home"
        self.home.mkdir(mode=0o700)
        self.vault = self.root / "vault"
        self.vault.mkdir()
        subprocess.run(["git", "init", "-q", str(self.vault)], check=True, capture_output=True)
        self.binding = hooks._vault_binding(self.vault)
        stale = json.loads(json.dumps(self.binding))
        stale["owner"][0] += 1
        stale["git_dir"][0] += 1
        self.record = self.home / "constellation-vault.json"
        self.original = (json.dumps(stale) + "\n").encode()
        self.record.write_bytes(self.original)
        self.record.chmod(0o600)
        self.digest = hashlib.sha256(self.original).hexdigest()

    def test_inspection_is_read_only_and_renewal_retains_actual_private_original(self):
        old_inode = self.record.stat().st_ino
        inspected = self.hooks.renew_vault_registration(self.home, str(self.vault))
        self.assertEqual(inspected["status"], "renewal_required")
        self.assertEqual(inspected["expected_registration_sha256"], self.digest)
        self.assertEqual(list(self.home.iterdir()), [self.record])
        renewed = self.hooks.renew_vault_registration(self.home, str(self.vault), expected_sha256=self.digest)
        recovery = Path(renewed["recovery"])
        self.assertEqual(renewed["status"], "renewed")
        self.assertEqual(recovery.read_bytes(), self.original)
        self.assertEqual(recovery.stat().st_ino, old_inode)
        self.assertEqual(recovery.stat().st_mode & 0o777, 0o600)
        self.assertEqual(recovery.parent.stat().st_mode & 0o777, 0o700)
        self.assertEqual(json.loads(self.record.read_bytes()), self.binding)
        self.assertEqual(self.hooks.check_vault_registration(self.home, str(self.vault), require_bound=True), self.binding)
        current = self.hooks.renew_vault_registration(self.home, str(self.vault),
                                                     expected_sha256=renewed["expected_registration_sha256"])
        self.assertEqual(current["status"], "current")
        self.assertIsNone(current["recovery"])

    def test_wrong_root_or_stale_hash_cannot_change_registration(self):
        other = self.root / "other"
        other.mkdir()
        subprocess.run(["git", "init", "-q", str(other)], check=True, capture_output=True)
        with self.assertRaisesRegex(ValueError, "cannot change"):
            self.hooks.renew_vault_registration(self.home, str(other), expected_sha256=self.digest)
        for digest in ("0" * 64, "bad-digest"):
            with self.subTest(digest=digest), self.assertRaises(ValueError):
                self.hooks.renew_vault_registration(self.home, str(self.vault), expected_sha256=digest)
        self.assertEqual(self.record.read_bytes(), self.original)
        self.assertEqual(list(self.home.iterdir()), [self.record])

    def test_replacing_vault_after_inspection_cannot_enroll_substitute(self):
        inspected = self.hooks.renew_vault_registration(self.home, str(self.vault))
        self.vault.rename(self.root / "original-vault")
        self.vault.mkdir()
        subprocess.run(["git", "init", "-q", str(self.vault)], check=True, capture_output=True)
        with self.assertRaisesRegex(ValueError, "preserves.*inodes"):
            self.hooks.renew_vault_registration(
                self.home, str(self.vault), expected_sha256=inspected["expected_registration_sha256"])
        self.assertEqual(self.record.read_bytes(), self.original)
        self.assertEqual(list(self.home.iterdir()), [self.record])

    def test_exchange_or_postpublication_failure_preserves_or_restores_original(self):
        with mock.patch.object(self.hooks, "exchange_files", side_effect=OSError("fixture exchange failure")):
            with self.assertRaisesRegex(ValueError, "retained recovery"):
                self.hooks.renew_vault_registration(self.home, str(self.vault), expected_sha256=self.digest)
        self.assertEqual(self.record.read_bytes(), self.original)
        with mock.patch.object(self.hooks, "sync_directory", side_effect=[
            None, None, None, OSError("fixture sync failure"), None, None
        ]):
            with self.assertRaisesRegex(ValueError, "retained recovery"):
                self.hooks.renew_vault_registration(self.home, str(self.vault), expected_sha256=self.digest)
        self.assertEqual(self.record.read_bytes(), self.original)
        self.assertEqual(self.hooks.renew_vault_registration(self.home, str(self.vault))["status"], "renewal_required")

    def test_registration_change_at_exchange_is_preserved_and_rejected(self):
        exchange = self.hooks.exchange_files
        newer = self.original + b" "
        calls = 0

        def competing_writer(stage, target):
            nonlocal calls
            calls += 1
            if calls == 1:
                target.write_bytes(newer)
            exchange(stage, target)

        with mock.patch.object(self.hooks, "exchange_files", side_effect=competing_writer):
            with self.assertRaisesRegex(ValueError, "retained recovery"):
                self.hooks.renew_vault_registration(self.home, str(self.vault), expected_sha256=self.digest)
        self.assertEqual(self.record.read_bytes(), newer)
        recovery = tuple((self.home / "constellation-vault-recovery").glob("*/registration.json"))
        self.assertEqual(len(recovery), 1)
        self.assertEqual(json.loads(recovery[0].read_bytes()), self.binding)

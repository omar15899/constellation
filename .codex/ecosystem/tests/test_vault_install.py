"""Real Git enrollment tests with independent temporary repository and Codex home."""
from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

# Discovery with python -I starts outside the package directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ecosystem.vault import install


class VaultEnrollmentTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name).resolve()
        self.root = base / "vault with spaces"
        self.home = base / "Codex Home"
        self.root.mkdir()
        self.home.mkdir()
        launcher = self.home / "constellation/run"
        launcher.parent.mkdir()
        self.lock = (launcher.parent / ".install.lock").open("w+b")
        fcntl.flock(self.lock.fileno(), fcntl.LOCK_EX)
        self.addCleanup(self.lock.close)
        # Fixture for the machine-certified launcher. Approval and stdin still
        # pass through an actual Git hook and an independent Python process.
        launcher.write_text(f'#!/bin/sh\nexec {shlex.quote(sys.executable)} -I -B '
                            '"$CODEX_HOME/constellation/hook.py" "$@"\n')
        launcher.chmod(0o700)
        environment = patch.dict(os.environ, {
            "GIT_CONFIG_GLOBAL": str(base / "isolated.gitconfig"), "GIT_CONFIG_NOSYSTEM": "1",
        })
        environment.start()
        self.addCleanup(environment.stop)
        self.git("init", "-q")

    def git(self, *args: str) -> str:
        return subprocess.check_output(["git", *args], text=True, cwd=self.root).strip()

    def enroll(self) -> Path:
        self.assertEqual(install.entrypoint(self.root, self.home, install_lock_fd=self.lock.fileno()), 0)
        return Path(self.git("rev-parse", "--path-format=absolute", "--git-path", "hooks"))

    def test_real_git_invokes_bound_entry_with_exact_root_and_stream_and_retry_is_idempotent(self) -> None:
        entry = self.home / "constellation/hook.py"
        entry.write_text("import json,os,sys\nfrom pathlib import Path\n"
                         "Path(__file__).with_name('seen').write_text(json.dumps("
                         "[sys.argv[1:],os.environ['CODEX_HOME'],sys.stdin.read()]))\nprint('{}')\n")
        generation = self.enroll()
        before = {p.name: p.stat().st_ino for p in generation.iterdir()}
        self.assertEqual(set(before), {*install.EVENTS, "guard.config"})
        self.assertEqual(self.enroll(), generation)
        self.assertEqual({p.name: p.stat().st_ino for p in generation.iterdir()}, before)
        subprocess.run(["git", "hook", "run", "pre-commit"], cwd=self.root, check=True)
        import json
        self.assertEqual(json.loads(entry.with_name("seen").read_text()),
                         [["vault", "--project-root", str(self.root), "git-hook", "pre-commit"],
                          str(self.home), ""])
        subprocess.run([str(generation / "pre-push"), "origin", "unused-url"], cwd=self.root,
                       input="ref sha ref sha\n", text=True, check=True)
        self.assertEqual(json.loads(entry.with_name("seen").read_text()),
                         [["vault", "--project-root", str(self.root), "git-hook", "pre-push"],
                          str(self.home), "ref sha ref sha\n"])

    def test_older_bootstrap_returning_successful_hook_diagnostic_cannot_approve_git(self) -> None:
        entry = self.home / "constellation/hook.py"
        for output in ('{"systemMessage":"unknown event"}', '', '{}'):
            entry.write_text("print(" + repr(output) + ")\n")
            hook = self.enroll() / "pre-commit"
            result = subprocess.run([str(hook)], cwd=self.root, capture_output=True)
            self.assertEqual(result.returncode, 0 if output == '{}' else 2)
        entry.write_text("print('{}')\nraise SystemExit(3)\n")
        self.assertEqual(subprocess.run([str(hook)], cwd=self.root).returncode, 3)

    def _commit(self, root: Path, message: str) -> None:
        subprocess.run(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.test",
                        "-c", "commit.gpgSign=false", "commit", "-q", "--allow-empty", "-m", message],
                       cwd=root, check=True, capture_output=True, timeout=10)

    def _linked_checkout_enrollment(self, *, enroll_linked: bool) -> None:
        main = self.root
        linked = main.with_name("linked checkout")
        self._commit(main, "Seed both checkouts")
        self.git("config", "--local", "core.hooksPath", ".codex/git-hooks")
        self.git("worktree", "add", "--detach", "-q", str(linked), "HEAD")

        target, sibling = (linked, main) if enroll_linked else (main, linked)
        self.root = target
        # The sibling already relies on its own implementation of the
        # relative legacy hook. The selected target has no legacy executable.
        sibling_hook = sibling / ".codex/git-hooks/pre-commit"
        sibling_hook.parent.mkdir(parents=True)
        sibling_hook.write_text("#!/bin/sh\necho sibling-hook >> sibling-receipt\n")
        sibling_hook.chmod(0o755)
        entry = self.home / "constellation/hook.py"
        entry.write_text("from pathlib import Path\nimport sys\n"
                         "with Path(__file__).with_name('seen').open('a') as out: "
                         "out.write(sys.argv[-1] + '\\n')\nprint('{}')\n")

        generation = self.enroll()
        effective = subprocess.check_output(["git", "rev-parse", "--path-format=absolute",
                                             "--git-path", "hooks"], cwd=sibling, text=True).strip()
        self.assertEqual(Path(effective), sibling_hook.parent)
        self.assertEqual(self.git("config", "--local", "--no-includes", "--get", "core.hooksPath"),
                         ".codex/git-hooks")
        self.assertNotEqual(generation, sibling_hook.parent)
        self._commit(target, "Run selected vault guard")
        self._commit(sibling, "Run original sibling guard")
        self.assertEqual(entry.with_name("seen").read_text().splitlines(), ["pre-commit", "post-commit"])
        self.assertEqual((sibling / "sibling-receipt").read_text(), "sibling-hook\n")
        self.assertFalse((target / "sibling-receipt").exists())

    def test_main_checkout_guard_preserves_linked_checkout_hook_and_commit(self) -> None:
        self._linked_checkout_enrollment(enroll_linked=False)

    def test_linked_checkout_guard_preserves_main_checkout_hook_and_commit(self) -> None:
        self._linked_checkout_enrollment(enroll_linked=True)

    def test_trailing_include_after_core_setting_never_partially_activates_guard(self) -> None:
        included = self.root.parent / "local include with spaces"
        included.write_text('[core]\n\thooksPath = .codex/git-hooks\n'
                            '[scientific]\n\tmodel = "value from include"\n')
        include_before = included.read_bytes()
        self.git("config", "--local", "core.hooksPath", ".codex/git-hooks")
        self.git("config", "--local", "--add", "include.path", str(included))
        config = self.root / ".git/config"
        original = config.read_bytes()
        self.assertLess(original.index(b"hooksPath"), original.index(b"[include]"))
        try:
            generation = self.enroll()
        except install.EnrollmentError:
            self.assertEqual(config.read_bytes(), original)
            self.assertEqual(self.git("config", "--includes", "--get", "core.hooksPath"), ".codex/git-hooks")
        else:
            self.assertEqual(Path(self.git("config", "--includes", "--get", "core.hooksPath")), generation)
            self.assertNotEqual(generation, self.root / ".codex/git-hooks")
            self.assertTrue((generation / "pre-commit").is_file())
            self.assertIn(original, config.read_bytes())
        self.assertEqual(included.read_bytes(), include_before)
        self.assertEqual(self.git("config", "--includes", "--get", "scientific.model"), "value from include")

    def test_gitdir_metacharacter_is_literal_or_rejected_before_configuration_changes(self) -> None:
        literal = self.root.with_name("vault[ab]?*literal")
        self.root.rename(literal)
        self.root = literal
        config = self.root / ".git/config"
        original = config.read_bytes()
        try:
            selected = self.enroll()
        except install.EnrollmentError:
            self.assertEqual(config.read_bytes(), original)
            self.assertFalse((self.home / "constellation-vault-guards").exists())
        else:
            self.assertEqual(Path(self.git("config", "--includes", "--get", "core.hooksPath")), selected)
            self.assertTrue((selected / "pre-commit").is_file())
            # Give a differently named Git owner the same include directives.
            # A glob matching the literal directory and this lookalike would
            # also redirect the second owner's hooks.
            other = literal.with_name("vault[ab]XYliteral")
            other.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=other, check=True)
            subprocess.run(["git", "config", "--local", "include.path", str(config)],
                           cwd=other, check=True)
            other_hooks = subprocess.check_output(["git", "rev-parse", "--path-format=absolute",
                                                  "--git-path", "hooks"], cwd=other, text=True).strip()
            self.assertEqual(Path(other_hooks), other / ".git/hooks")

    def test_foreign_hooks_and_modified_legacy_hooks_survive(self) -> None:
        default = self.root / ".git/hooks/pre-commit"
        default.write_text("external")
        with self.assertRaisesRegex(install.EnrollmentError, "would be replaced"):
            self.enroll()
        self.assertEqual(default.read_text(), "external")
        default.unlink()
        original = self.root / ".codex/git-hooks/pre-push"
        original.parent.mkdir(parents=True)
        original.write_text("custom")
        original.chmod(0o755)
        self.git("config", "--local", "core.hooksPath", ".codex/git-hooks")
        with self.assertRaisesRegex(install.EnrollmentError, "Modified"):
            self.enroll()
        self.assertEqual(self.git("config", "--get", "core.hooksPath"), ".codex/git-hooks")
        self.assertEqual(original.read_text(), "custom")

    def test_removed_legacy_bytes_still_present_in_user_index_block_migration(self) -> None:
        hook = self.root / ".codex/git-hooks/pre-commit"
        hook.parent.mkdir(parents=True)
        hook.write_text("user staging")
        hook.chmod(0o755)
        self.git("add", ".codex/git-hooks/pre-commit")
        hook.unlink()
        self.git("config", "--local", "core.hooksPath", ".codex/git-hooks")
        with self.assertRaisesRegex(install.EnrollmentError, "index"):
            self.enroll()
        self.assertEqual(self.git("show", ":.codex/git-hooks/pre-commit"), "user staging")

    def test_higher_precedence_hook_configuration_never_changes_local_config(self) -> None:
        with patch.dict(os.environ, {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.hooksPath",
                                     "GIT_CONFIG_VALUE_0": ".codex/git-hooks"}):
            with self.assertRaisesRegex(install.EnrollmentError, "higher-precedence"):
                self.enroll()
        result = subprocess.run(["git", "config", "--local", "--get", "core.hooksPath"], cwd=self.root)
        self.assertEqual(result.returncode, 1)

    def _competing_hook_choice(self, *, legacy: bool) -> None:
        legacy_path = ".codex/git-hooks"
        if legacy:
            self.git("config", "--local", "core.hooksPath", legacy_path)
        config_file = self.root / ".git/config"
        committed = []
        def select_during_preparation(*args):
            if legacy:
                self.git("config", "--local", "--unset", "core.hooksPath")
            else:
                self.git("config", "--local", "core.hooksPath", legacy_path)
            committed.append(config_file.read_bytes())
            return 0

        # Both user selections would be acceptable in a *new* enrollment.
        # This one started from the opposite state and may not replace them.
        with patch.object(install, "exclude_local_skills", side_effect=select_during_preparation):
            with self.assertRaises(install.EnrollmentError):
                self.enroll()
        self.assertEqual(committed, [config_file.read_bytes()])
        self.assertFalse(config_file.with_name("config.lock").exists())

    def test_external_include_edit_under_common_lock_is_preserved_before_skill_settings(self) -> None:
        included = self.root.parent / "external config"
        self.git("config", "--local", "include.path", str(included))
        included.write_text("[core]\n\thooksPath = .codex/git-hooks\n")
        original = (self.root / ".git/config").read_bytes()
        update = install._updated_config
        def external_edit(*args):
            # The outside configuration has its own lock and the common local
            # hooksPath stays absent. The change must still invalidate selection.
            self.assertTrue((self.root / ".git/config.lock").is_file())
            self.git("config", "--file", str(included), "--unset", "core.hooksPath")
            return update(*args)
        with patch.object(install, "_updated_config", side_effect=external_edit), \
                patch.object(install, "exclude_local_skills", side_effect=AssertionError("premature enrollment")):
            with self.assertRaisesRegex(install.EnrollmentError, "change preserved"):
                self.enroll()
        self.assertEqual((self.root / ".git/config").read_bytes(), original)
        self.assertNotIn(b"hooksPath", included.read_bytes())

    def test_user_can_select_legacy_hooks_during_first_enrollment(self) -> None:
        self._competing_hook_choice(legacy=False)

    def test_user_can_remove_legacy_selection_during_migration(self) -> None:
        self._competing_hook_choice(legacy=True)

    def test_git_writer_observes_config_lock_during_activation_and_can_retry(self) -> None:
        compute = install._updated_config
        attempted = []
        def competing_write(original: bytes, destination: Path, git_dir: Path) -> bytes:
            lock = self.root / ".git/config.lock"
            self.assertTrue(lock.is_file())
            writer = subprocess.run(["git", "config", "--local", "core.hooksPath", "my-hooks"],
                                    cwd=self.root, capture_output=True, timeout=10)
            attempted.append(writer.returncode)
            return compute(original, destination, git_dir)

        with patch.object(install, "_updated_config", side_effect=competing_write):
            selected = self.enroll()
        self.assertTrue(attempted)
        self.assertTrue(all(code != 0 for code in attempted))
        self.assertEqual(Path(self.git("rev-parse", "--path-format=absolute", "--git-path", "hooks")), selected)
        self.git("config", "--local", "core.hooksPath", "my-hooks")
        self.assertEqual(self.git("config", "--local", "--no-includes", "--get", "core.hooksPath"), "my-hooks")

    def test_preserves_other_git_values_committed_during_preparation(self) -> None:
        def write_unrelated(*args):
            self.git("config", "--local", "--add", "scientific.inputs", "first sample")
            self.git("config", "--local", "--add", "scientific.inputs", "second sample")
            return 0
        with patch.object(install, "exclude_local_skills", side_effect=write_unrelated):
            self.enroll()
        self.assertEqual(self.git("config", "--local", "--get-all", "scientific.inputs").splitlines(),
                         ["first sample", "second sample"])

    def test_root_exchanged_under_lock_cannot_change_either_repository_config(self) -> None:
        from ecosystem.hooks import check_vault_registration
        binding = check_vault_registration(self.home, str(self.root), require_bound=False)
        moved = self.root.with_name("original repository")
        original_config = (self.root / ".git/config").read_bytes()
        compute = install._updated_config
        replacement_config = []
        def exchange(original: bytes, destination: Path, git_dir: Path) -> bytes:
            self.root.rename(moved)
            self.root.mkdir()
            self.git("init", "-q")
            self.git("config", "--local", "project.identity", "replacement")
            replacement_config.append((self.root / ".git/config").read_bytes())
            return compute(original, destination, git_dir)

        with patch.object(install, "_updated_config", side_effect=exchange):
            with self.assertRaises(ValueError):
                install.entrypoint(self.root, self.home, expected_binding=binding, install_lock_fd=self.lock.fileno())
        self.assertEqual((moved / ".git/config").read_bytes(), original_config)
        self.assertEqual(replacement_config, [(self.root / ".git/config").read_bytes()])
        self.assertFalse((moved / ".git/config.lock").exists())
        self.assertFalse((self.root / ".git/config.lock").exists())

    def test_existing_git_lock_is_never_removed_and_retry_works_after_release(self) -> None:
        config = self.root / ".git/config"
        original = config.read_bytes()
        lock = config.with_name("config.lock")
        lock.write_bytes(b"another writer owns these bytes")
        inode = lock.stat().st_ino
        with self.assertRaises(install.EnrollmentError):
            self.enroll()
        self.assertEqual(lock.stat().st_ino, inode)
        self.assertEqual(lock.read_bytes(), b"another writer owns these bytes")
        self.assertEqual(config.read_bytes(), original)
        lock.unlink()
        self.enroll()

    def test_ambiguous_existing_local_hooks_setting_is_preserved(self) -> None:
        for value in (".codex/git-hooks", ".codex/git-hooks"):
            self.git("config", "--local", "--add", "core.hooksPath", value)
        with self.assertRaisesRegex(install.EnrollmentError, "Conflicting"):
            self.enroll()
        self.assertEqual(self.git("config", "--local", "--get-all", "core.hooksPath").splitlines(),
                         [".codex/git-hooks", ".codex/git-hooks"])

    def test_corrupt_generation_and_explicit_disabled_git_setting_block_enrollment(self) -> None:
        self.git("config", "core.hooksPath", str(self.home / "empty"))
        with self.assertRaisesRegex(install.EnrollmentError, "would be replaced"):
            self.enroll()
        self.git("config", "--unset", "core.hooksPath")
        generation = self.enroll()
        (generation / "post-commit").write_text("tampered")
        with self.assertRaisesRegex(install.EnrollmentError, "modified"):
            self.enroll()
        self.assertEqual((generation / "post-commit").read_text(), "tampered")

    def test_user_and_project_enables_are_checked_for_every_alias_before_first_native_write(self):
        for folder in ("a", "b"):
            skill = self.root / ".agents/skills" / folder / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text("---\nname: duplicate\n---\n")
        self.git("add", ".agents")
        paths = sorted(str(p) for p in self.root.glob(".agents/skills/*/SKILL.md"))
        row = {"cwd": str(self.root), "errors": [], "skills": [
            {"name": "duplicate", "enabled": False, "path": path} for path in paths]}
        project = self.root / ".codex"
        project.mkdir()

        class Reader:
            def __init__(self, client, *, mutating=False):
                if mutating or client._lock_inheritance(False):
                    raise AssertionError("Explicit conflict must precede all lock-bearing writers")
            def call(self, method, payload):
                if method == "skills/list":
                    return {"data": [row]}
                if method == "config/read":
                    return {"config": {"skills": {"config": []}}}
                raise AssertionError("Unexpected mutation")
            def close(self):
                pass

        with patch.object(install, "_Rpc", Reader):
            for directory in (self.home, project):
                for selector in (f"path = {json.dumps(paths[0])}", 'name = "duplicate"'):
                    with self.subTest(scope=directory.name, selector=selector):
                        target = directory / "config.toml"
                        initial = ("[[skills.config]]\n" + selector + "\nenabled = true\n").encode()
                        target.write_bytes(initial)
                        with self.assertRaises(install.EnrollmentError):
                            self.enroll()
                        self.assertEqual(target.read_bytes(), initial)
                        target.unlink()
        self.assertEqual(subprocess.run(["git", "config", "--get", "core.hooksPath"], cwd=self.root).returncode, 1)

    def test_partial_native_exclusion_can_retry_and_user_overrides_are_preserved(self) -> None:
        skill = self.root / ".agents/skills/legacy/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("test fixture")
        self.git("add", ".agents/skills/legacy/SKILL.md")
        flag = {"name": "legacy", "enabled": True}
        overrides = [{"path": str(skill), "enabled": True}]
        calls = []
        class Rpc:
            def __init__(self, client, *, mutating=False):
                self.mutating = mutating
                inheritance = client._lock_inheritance(mutating)
                if mutating:
                    fd, = inheritance["pass_fds"]
                    self_test.assertTrue(os.path.samestat(os.fstat(self_test.lock.fileno()), os.fstat(fd)))
                else:
                    self_test.assertEqual(inheritance, {})
            def close(self):
                pass
            def call(self, method, payload):
                if method == "skills/list":
                    return {"data": [{"cwd": payload["cwds"][0], "errors": [],
                                      "skills": [{"path": str(skill), **flag}]}]}
                if method == "config/read":
                    return {"config": {"skills": {"config": overrides}}}
                self_test.assertTrue(self.mutating)
                self_test.assertEqual(payload, {"path": str(skill), "enabled": False})
                (self_test.home / "config.toml").write_text(
                    "[[skills.config]]\npath = " + json.dumps(str(skill)) + "\nenabled = false\n")
                flag["enabled"] = False
                calls.append(method)
                return {"effectiveEnabled": len(calls) == 1}
        self_test = self
        with patch.object(install, "_Rpc", Rpc):
            # Both calls inside _skill_snapshot and a fresh verification use our
            # synthetic server; Git and generation installation are real.
            with self.assertRaisesRegex(install.EnrollmentError, "Explicit user"):
                self.enroll()
            self.assertFalse(calls)
            overrides.clear()
            with self.assertRaisesRegex(install.EnrollmentError, "not confirmed"):
                self.enroll()
            self.assertEqual(calls, ["skills/config/write"])
            self.assertEqual(subprocess.run(["git", "config", "--get", "core.hooksPath"],
                                            cwd=self.root).returncode, 1)
            self.enroll()
            self.assertEqual(calls, ["skills/config/write"])

    @unittest.skipUnless(os.name == "posix", "POSIX vault enrollment uses flock and SIGKILL")
    def test_interrupted_enrollment_pins_only_the_orphaned_native_writer(self) -> None:
        import select
        import signal
        import textwrap
        from contextlib import ExitStack

        skill = self.root / ".agents/skills/legacy/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("fixture skill")
        self.git("add", ".agents/skills/legacy/SKILL.md")
        proxy = self.home / "fixture-codex"
        proxy.write_text("#!" + sys.executable + "\n" + textwrap.dedent(r'''
            import json, os, select, signal, sys
            from pathlib import Path

            signal.alarm(20)  # Also bounds FIFO open if the test runner exits.
            home = Path(os.environ["CODEX_HOME"])
            skill = Path.cwd() / ".agents/skills/legacy/SKILL.md"
            lock = (home / "constellation/.install.lock").stat()
            inherited = False
            for name in os.listdir("/dev/fd"):
                try:
                    inherited |= os.path.samestat(lock, os.fstat(int(name)))
                except (OSError, ValueError):
                    pass

            for line in sys.stdin:
                request = json.loads(line)
                if "id" not in request:
                    continue
                method = request["method"]
                result = {}
                if method in {"skills/list", "skills/config/write"}:
                    with (home / "rpc-events").open("a") as stream:
                        stream.write(json.dumps([method, inherited]) + "\n")
                if method == "skills/list":
                    result = {"data": [{"cwd": str(Path.cwd()), "errors": [], "skills": [
                        {"name": "legacy", "enabled": not (home / "config.toml").exists(),
                         "path": str(skill)}]}]}
                elif method == "config/read":
                    result = {"config": {}}
                elif method == "skills/config/write":
                    if request["params"] != {"path": str(skill), "enabled": False}:
                        os._exit(3)
                    (home / "writer-ready").write_bytes(b"R")
                    with (home / "writer-release").open("rb", buffering=0) as release:
                        if not select.select([release], [], [], 15)[0] or release.read(1) != b"X":
                            os._exit(2)
                    (home / "config.toml").write_text("[[skills.config]]\npath = "
                                                      + json.dumps(str(skill)) + "\nenabled = false\n")
                    os._exit(0)
                print(json.dumps({"id": request["id"], "result": result}), flush=True)
            '''))
        proxy.chmod(0o700)
        worker = textwrap.dedent('''
            import fcntl, sys
            from pathlib import Path
            sys.path.insert(0, sys.argv[1])
            from ecosystem.vault.install import exclude_local_skills
            root, home = map(Path, sys.argv[2:4])
            with (home / "constellation/.install.lock").open("rb") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                assert exclude_local_skills(root, home, sys.argv[4], lock.fileno()) == 1
            ''')
        command = [sys.executable, "-IB", "-c", worker, str(Path(__file__).resolve().parents[2]),
                   str(self.root), str(self.home), str(proxy)]
        # The enrollment subprocess must be the sole owner of the device lock
        # before its writer inherits a duplicate of the same open description.
        self.lock.close()
        with ExitStack() as stack:
            fds = []
            for name in ("writer-ready", "writer-release"):
                path = self.home / name
                os.mkfifo(path, 0o600)
                descriptor = os.open(path, os.O_RDWR | os.O_NONBLOCK)
                stack.callback(os.close, descriptor)
                fds.append(descriptor)
            ready, release = fds
            child = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                self.assertTrue(select.select([ready], [], [], 10)[0], "native writer did not reach its write")
                self.assertEqual(os.read(ready, 1), b"R")
                child.kill()
                self.assertEqual(child.wait(timeout=10), -signal.SIGKILL)
                with (self.home / "constellation/.install.lock").open("rb") as contender:
                    with self.assertRaises(BlockingIOError):
                        fcntl.flock(contender, fcntl.LOCK_EX | fcntl.LOCK_NB)
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=10)
                os.write(release, b"X")
            # The retry acquires the actual device lock after the orphan exits.
            # Its initial and verification probes both observe the persisted flag.
            replay = subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True, timeout=10)
            self.assertEqual(replay.returncode, 0, replay.stderr)
        events = [json.loads(line) for line in (self.home / "rpc-events").read_text().splitlines()]
        self.assertEqual(events, [["skills/list", False], ["skills/config/write", True],
                                  ["skills/list", False], ["skills/list", False]])

    def _register_guard_fixture(self) -> Path:
        from ecosystem.hooks import check_vault_registration, save_vault_registration
        generation = self.enroll()
        binding = check_vault_registration(self.home, str(self.root), require_bound=False)
        save_vault_registration(self.home, binding)
        return generation

    def test_verify_guard_accepts_actual_registered_generation_without_writes(self) -> None:
        generation = self._register_guard_fixture()
        paths = [self.root / ".git/config", self.home / "constellation-vault.json", *generation.iterdir()]
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns, p.stat().st_ino, p.stat().st_mode) for p in paths}
        self.assertEqual(install.verify_guard(self.root, self.home),
                         {"verified": True, "root": str(self.root), "hooks": str(generation)})
        after = {p: (p.read_bytes(), p.stat().st_mtime_ns, p.stat().st_ino, p.stat().st_mode) for p in paths}
        self.assertEqual(before, after)

    def test_verify_guard_rejects_unregistered_root_and_wrong_owner(self) -> None:
        self.enroll()
        with self.assertRaises(ValueError):
            install.verify_guard(self.root, self.home)
        self._register_guard_fixture()
        other = self.root.parent / "another owner"
        other.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=other, check=True)
        with self.assertRaises(ValueError):
            install.verify_guard(other, self.home)

    def test_verify_guard_rejects_self_consistent_generation_for_other_root(self) -> None:
        self._register_guard_fixture()
        other = self.root.parent / "another owner"
        other.mkdir()
        unrelated = install.prepare_guards(self.home / "constellation-vault-guards", other, self.home)
        install.verify_generation(unrelated)
        with (self.root / ".git/config").open("a") as config:
            config.write("\n[core]\n\thooksPath = " + install._git_quote(str(unrelated)) + "\n")
        with self.assertRaisesRegex(install.EnrollmentError, "canonical"):
            install.verify_guard(self.root, self.home)

    def test_verify_guard_rejects_altered_generation(self) -> None:
        generation = self._register_guard_fixture()
        (generation / "pre-commit").write_text("altered fixture")
        with self.assertRaisesRegex(install.EnrollmentError, "modified"):
            install.verify_guard(self.root, self.home)

    def test_verify_guard_rechecks_owner_and_effective_selection(self) -> None:
        self._register_guard_fixture()
        verify = install.verify_generation

        def change_selection(target):
            verify(target)
            with (self.root / ".git/config").open("a") as config:
                config.write("\n[core]\n\thooksPath = another-choice\n")

        with patch.object(install, "verify_generation", side_effect=change_selection):
            with self.assertRaisesRegex(install.EnrollmentError, "changed during"):
                install.verify_guard(self.root, self.home)

    def test_verify_guard_rejects_owner_exchanged_during_verification(self) -> None:
        generation = self._register_guard_fixture()
        original = self.root / ".git/config"
        before = original.read_bytes()
        old = self.root.parent / "original owner"
        verify = install.verify_generation

        def exchange(target):
            verify(target)
            self.root.rename(old)
            self.root.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)

        with patch.object(install, "verify_generation", side_effect=exchange):
            with self.assertRaises(ValueError):
                install.verify_guard(self.root, self.home)
        self.assertEqual((old / ".git/config").read_bytes(), before)
        self.assertEqual((generation / "pre-commit").read_bytes(), install._redirector(self.root, self.home))

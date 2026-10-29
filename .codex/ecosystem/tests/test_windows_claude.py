"""Claude's native Windows installer contract and portable regression cases.

The Windows cases exercise the real filesystem, ACLs and process locks. They
are explicitly skipped on other operating systems; passing portable cases does
not establish native Windows acceptance or Claude's live hook dispatch.
"""
from __future__ import annotations

import ctypes
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
ECOSYSTEM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ECOSYSTEM.parent))
sys.path.insert(0, str(ECOSYSTEM))

import claude as installer
import platform_support as platform
from build import BUNDLE_MANIFEST, build_bundle, bundle_target, file_record
from install import InstallError, _replace_bytes

storage = importlib.import_module("ecosystem.storage")
core = importlib.import_module("ecosystem.core")
from test_core import FixtureCase
from helpers import DEFAULT_PROFILE, Scenario


def _snapshot(root: Path) -> dict[str, tuple]:
    """Capture bytes and physical modes, excluding timestamps and ACL text."""
    result = {}
    if root.exists():
        for path in root.rglob("*"):
            name = path.relative_to(root).as_posix()
            if platform.is_reparse(path):
                result[name] = ("reparse",)
            elif path.is_file():
                result[name] = ("file", hashlib.sha256(path.read_bytes()).hexdigest(),
                                path.stat().st_mode)
            else:
                result[name] = ("directory", path.stat().st_mode)
    return result


class PublicUtf8BoundaryTests(unittest.TestCase):
    """Exercise the public CLI under an explicitly emulated Windows code page."""

    CP1252_RUNNER = (
        "import io,json,runpy,sys\n"
        "for name in ('stdin','stdout','stderr'):\n"
        " stream=getattr(sys,name); raw=stream.detach()\n"
        " setattr(sys,name,io.TextIOWrapper(raw,encoding='cp1252',errors='strict'))\n"
        "script,root,state,session,task,actor=sys.argv[1:7]\n"
        "entry=runpy.run_path(script,run_name='fixture_public_cli')['main']\n"
        "code=entry(['--root',root,'--state-dir',state,'plan'])\n"
        "if code: raise SystemExit(code)\n"
        "sys.stdin=io.StringIO(json.dumps(dict(session_id=session,task_id=task,agent_id=actor)))\n"
        "raise SystemExit(entry(['--root',root,'--state-dir',state,'status']))\n"
    )

    def run_plan(self, *, ensure_ascii: bool) -> tuple[Scenario, dict]:
        temporary = tempfile.TemporaryDirectory(prefix="public-cli-codepage-")
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name).resolve()
        scenario = Scenario(root=base / "Résumé Ω", state_dir=base / "private state Ω")
        self.addCleanup(scenario.cleanup)
        text = "Résumé Ω must survive the public JSON boundary exactly."
        scenario.contract["requirements"][0]["text"] = text
        payload = scenario.payload(**scenario.contract)
        result = subprocess.run(
            [sys.executable, "-I", "-B", "-c", self.CP1252_RUNNER,
             str(ECOSYSTEM / "cli.py"), str(scenario.root), str(scenario.state_dir),
             scenario.session, scenario.task, "fixture-coordinator"],
            input=json.dumps(payload, ensure_ascii=ensure_ascii).encode("utf-8"),
            capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
        # Decoding is deliberately strict: mojibake and a cp1252 response are
        # failures even if the JSON's ASCII structural characters still parse.
        responses = [json.loads(line) for line in result.stdout.decode("utf-8").splitlines()]
        self.assertEqual(len(responses), 2)
        self.assertTrue(all(response["ok"] for response in responses), responses)
        response = responses[-1]
        self.assertEqual(response["root"], str(scenario.root))
        return scenario, response

    def test_ascii_escaped_input_still_emits_utf8_json_from_cp1252_streams(self) -> None:
        scenario, response = self.run_plan(ensure_ascii=True)
        self.assertEqual(response["revision"], 1)
        stored = core.Engine(scenario.root, scenario.state_dir).execute(
            "status", {"session_id": scenario.session, "task_id": scenario.task,
                       "agent_id": "fixture-coordinator"})
        self.assertEqual(stored["contract"]["requirements"][0]["text"],
                         scenario.contract["requirements"][0]["text"])

    def test_literal_utf8_input_is_stored_exactly_under_cp1252_stream_emulation(self) -> None:
        scenario, _ = self.run_plan(ensure_ascii=False)
        # A new engine reads persisted state. An output-only encoding repair
        # cannot conceal a requirement that was decoded incorrectly on stdin.
        stored = core.Engine(scenario.root, scenario.state_dir).execute(
            "status", {"session_id": scenario.session, "task_id": scenario.task,
                       "agent_id": "fixture-coordinator"})
        self.assertEqual(stored["contract"]["requirements"][0]["text"],
                         "Résumé Ω must survive the public JSON boundary exactly.")


    def test_invalid_utf8_is_json_failure_without_echo_stderr_or_state_creation(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="public-cli-invalid-utf8-")
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name).resolve()
        root, state = base / "Résumé Ω", base / "must-not-be-created"
        root.mkdir()
        untrusted = b'{"session_id":"UNTRUSTED-RAW-PAYLOAD-\xff","task_id":"fixture-task","agent_id":"fixture-coordinator"}'
        result = subprocess.run(
            [sys.executable, "-I", "-B", str(ECOSYSTEM / "cli.py"),
             "--root", str(root), "--state-dir", str(state), "status"],
            input=untrusted, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stderr, b"")
        self.assertEqual(json.loads(result.stdout.decode("utf-8")), {
            "ok": False, "error": "Portable CLI text must be valid UTF-8."})
        self.assertNotIn(b"UNTRUSTED-RAW-PAYLOAD", result.stdout)
        self.assertNotIn(b"\xff", result.stdout)
        self.assertFalse(state.exists())
        self.assertEqual(list(root.iterdir()), [])


class InterpreterPreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="claude-python-preflight-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.bundle = self.root / "bundle"
        (self.bundle / "ecosystem").mkdir(parents=True)
        self.executable = self.root / "python.exe"
        self.executable.write_bytes(b"Synthetic executable identity; never executed")
        self.hooks("python")

    def hooks(self, command: str) -> None:
        (self.bundle / "ecosystem/claude-hooks.json").write_text(
            json.dumps({"hooks": {"Stop": [{"hooks": [{"command": command}]}]}}),
            encoding="utf-8")

    def check(self, *, identity: object = None, code: int = 0) -> None:
        result = subprocess.CompletedProcess(
            [], code, json.dumps(["nt", [3, 12]] if identity is None else identity).encode(), b"")
        with patch.object(platform, "IS_WINDOWS", True), \
                patch.object(installer.shutil, "which", return_value=str(self.executable)), \
                patch.object(installer.subprocess, "run", return_value=result) as launch:
            installer._runtime_preflight(self.bundle)
        launch.assert_called_once()
        arguments = launch.call_args.args[0]
        self.assertEqual(arguments[:4], [str(self.executable), "-I", "-B", "-c"])
        self.assertNotIn("shell", launch.call_args.kwargs)

    def test_native_interpreter_is_verified_without_mutating_inputs(self) -> None:
        before = _snapshot(self.root)
        self.check()
        self.assertEqual(_snapshot(self.root), before)

    def test_wrong_target_or_missing_real_executable_is_rejected(self) -> None:
        with patch.object(platform, "IS_WINDOWS", True):
            self.hooks("python3")
            with self.assertRaisesRegex(InstallError, "windows-claude"):
                installer._runtime_preflight(self.bundle)
            self.hooks("python")
            for executable in (None, str(self.root / "python.cmd")):
                with self.subTest(executable=executable), \
                        patch.object(installer.shutil, "which", return_value=executable):
                    with self.assertRaisesRegex(InstallError, "real Python"):
                        installer._runtime_preflight(self.bundle)
        with patch.object(platform, "IS_WINDOWS", False):
            with self.assertRaisesRegex(InstallError, "native Windows"):
                installer._runtime_preflight(self.bundle)

    def test_managed_root_classification_respects_windows_case_without_changing_posix(self) -> None:
        for selected in (False, True):
            with self.subTest(windows=selected), patch.object(platform, "IS_WINDOWS", selected):
                self.assertTrue(installer._is_managed_root(Path("skills/constellation")))
                self.assertEqual(installer._is_managed_root(Path("Skills/Constellation")), selected)
                self.assertFalse(installer._is_managed_root(Path("other/constellation")))

    def test_old_foreign_failed_or_malformed_interpreters_fail_closed(self) -> None:
        for identity, code in ((["nt", [3, 9]], 0), (["posix", [3, 12]], 0),
                               (["nt", ["3", 12]], 0), ({"not": "identity"}, 0),
                               (["nt", [3, 12]], 1)):
            with self.subTest(identity=identity, code=code), self.assertRaises(InstallError):
                self.check(identity=identity, code=code)


class ReplacementPrimitiveTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="claude-replacement-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()

    def test_replacement_preserves_a_previous_hardlink_and_creates_private_inode(self) -> None:
        outside = self.root / "independently-owned.txt"
        outside.write_bytes(b"old independently owned data")
        target = self.root / "receipt.json"
        os.link(outside, target)
        _replace_bytes(target, b"new owned receipt", 0o600)
        self.assertEqual(outside.read_bytes(), b"old independently owned data")
        self.assertEqual(target.read_bytes(), b"new owned receipt")
        self.assertEqual(target.stat().st_nlink, 1)
        platform.verify_access(target, private=True)
        self.assertEqual(platform.logical_mode(target, expected=0o600), 0o600)

    def test_failed_flush_preserves_previous_bytes_and_cleans_only_own_temporary(self) -> None:
        target = self.root / "receipt.json"
        target.write_bytes(b"preserved")
        before = _snapshot(self.root)
        with patch.object(platform, "sync_file", side_effect=OSError("synthetic flush failure")):
            with self.assertRaises(OSError):
                _replace_bytes(target, b"must not replace", 0o600)
        self.assertEqual(_snapshot(self.root), before)

    def test_body_io_contention_is_not_misreported_as_lock_acquisition(self) -> None:
        home = self.root / "managed home"
        with self.assertRaisesRegex(BlockingIOError, "synthetic body I/O"):
            with installer.installation_lock(home, exclusive=True, create=True):
                raise BlockingIOError("synthetic body I/O")
        # The original exception still releases the lock and its handle.
        with installer.installation_lock(home, exclusive=True):
            pass

    @unittest.skipIf(os.name == "nt", "POSIX symlink analogue; native junction rejection is tested below")
    def test_windows_state_validation_checks_original_ancestor_before_resolve(self) -> None:
        actual = self.root / "actual"
        actual.mkdir()
        alias = self.root / "alias"
        alias.symlink_to(actual, target_is_directory=True)
        with patch.object(storage.platform, "IS_WINDOWS", True):
            with self.assertRaisesRegex(storage.Error, "reparse"):
                storage.Store(alias / "private-state")
        self.assertFalse((actual / "private-state").exists())
        with patch.object(core.platform, "IS_WINDOWS", True):
            with self.assertRaisesRegex(storage.Error, "reparse"):
                core.Engine(alias, self.root / "state-outside-alias")
        self.assertFalse((self.root / "state-outside-alias").exists())


class PortableEvidenceBoundaryTests(FixtureCase):
    def test_platform_runtime_bytes_are_pinned_after_checks_and_closure(self) -> None:
        scenario = self.scenario()
        runtime, subject = self.isolated_runtime(scenario)
        scenario.plan()
        scenario.approve()
        scenario.close()
        support = runtime / "ecosystem/platform_support.py"
        support.write_bytes(support.read_bytes() + b"\n# Synthetic runtime freshness delta.\n")
        self.assertTrue(scenario.call("status")["pending"])
        with self.assertRaises(subject.Error):
            scenario.close()

    def test_windows_input_record_binds_acl_even_when_bytes_and_mode_are_identical(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="input-access-snapshot-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name).resolve()
        artifact = root / "input.md"
        artifact.write_bytes(b"same bytes")
        engine = core.Engine(root, root / "state")
        opened = lambda path, flags, **options: os.open(path, flags)
        with patch.object(core.platform, "IS_WINDOWS", True), \
                patch.object(core.platform, "open_regular", side_effect=opened) as guard, \
                patch.object(core.platform, "access_fingerprint", side_effect=("acl-before", "acl-after")):
            before = engine._input_record(artifact)
            after = engine._input_record(artifact)
        self.assertEqual(before["sha256"], after["sha256"])
        self.assertEqual(before["mode"], after["mode"])
        self.assertNotEqual(before["access"], after["access"])
        self.assertEqual(guard.call_count, 2)
        self.assertTrue(all(call.kwargs == {"private": False} for call in guard.call_args_list))

    def test_physical_aliases_are_rejected_and_distinct_case_files_remain_valid(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="contract-identity-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name).resolve()
        first, second = root / "Report.md", root / "report.md"
        first.write_bytes(b"first")
        engine = core.Engine(root, root / "state")

        def payload(deliverables: list[str], inputs: list[dict] | None = None) -> dict:
            return {
                "requirements": [{"id": "r", "text": "Each output has an independent identity.",
                    "deliverables": deliverables, "checks": [], "acceptance": "editorial"}],
                "deliverables": [{"path": name, "profiles": [DEFAULT_PROFILE]} for name in deliverables],
                "checks": [], "inputs": inputs or [], "depends_on": [], "risk": "quick"}

        if second.exists() and os.path.samefile(first, second):
            with self.assertRaises(storage.Error):
                engine._contract(payload(["Report.md", "report.md"]))
            with self.assertRaises(storage.Error):
                engine._contract(payload(["Report.md"], [{
                    "path": "report.md", "sha256": hashlib.sha256(second.read_bytes()).hexdigest()}]))
        else:
            second.write_bytes(b"distinct")
            self.assertFalse(os.path.samefile(first, second))
            contract = engine._contract(payload(["Report.md", "report.md"]))
            self.assertEqual(len(contract["deliverables"]), 2)
        alias = root / "hardlink.md"
        os.link(first, alias)
        with self.assertRaises(storage.Error):
            engine._contract(payload(["Report.md"], [{
                "path": "hardlink.md", "sha256": hashlib.sha256(first.read_bytes()).hexdigest()}]))

    @unittest.skipIf(os.name == "nt", "Portable casefold branch simulation; real Windows has the same contract test")
    def test_prospective_windows_case_aliases_are_rejected_before_files_exist(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="prospective-case-identity-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name).resolve()
        engine = core.Engine(root, root / "state")
        payload = {
            "requirements": [{"id": "r", "text": "Outputs are independent.",
                "deliverables": ["Report.md", "report.md"], "checks": [], "acceptance": "editorial"}],
            "deliverables": [{"path": name, "profiles": [DEFAULT_PROFILE]}
                             for name in ("Report.md", "report.md")],
            "checks": [], "inputs": [], "depends_on": [], "risk": "quick"}
        # The native path/ACL backend is covered separately. Here only namespace
        # identity is selected as Windows while using a real POSIX temporary root.
        with patch.object(core.platform, "IS_WINDOWS", True), \
                patch.object(core.platform, "validate_lookup", side_effect=lambda path: Path(path).absolute()), \
                patch.object(core.platform, "_ps_check_components"), \
                patch.object(engine, "validate_path", side_effect=lambda name: root / name), \
                patch.object(engine, "_resources", return_value={}):
            with self.assertRaisesRegex(storage.Error, "distinct"):
                engine._contract(payload)


@unittest.skipUnless(os.name == "nt", "Requires native Windows: ACLs, locks, junctions and rename semantics")
class NativeWindowsClaudeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.shared = tempfile.TemporaryDirectory(prefix="claude-windows-release-")
        cls.source = ECOSYSTEM.parent
        cls.bundle = Path(cls.shared.name).resolve() / "English package with spaces"
        options = {} if (cls.source / BUNDLE_MANIFEST).exists() else {
            "language": "en", "target": "windows-claude"}
        build_bundle(cls.bundle, source_root=cls.source, **options)
        if bundle_target(cls.bundle) != "windows-claude":
            cls.shared.cleanup()
            raise unittest.SkipTest("Native Windows acceptance requires a windows-claude package")
        cls.previous_path = os.environ.get("PATH", "")
        os.environ["PATH"] = str(Path(sys.executable).parent) + os.pathsep + cls.previous_path

    @classmethod
    def tearDownClass(cls) -> None:
        os.environ["PATH"] = cls.previous_path
        cls.shared.cleanup()

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="claude-native-windows-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.home = self.root / "native home with spaces é"
        self.target = self.home / "skills/constellation"

    def changed_bundle(self) -> Path:
        destination = self.root / "same-version update"
        shutil.copytree(self.bundle, destination)
        manifest = json.loads((destination / BUNDLE_MANIFEST).read_text(encoding="utf-8"))
        resource = "ecosystem/README.md"
        path = destination / resource
        path.write_bytes(path.read_bytes() + b"\nSynthetic same-version update.\n")
        manifest["files"][resource] = file_record(path)
        (destination / BUNDLE_MANIFEST).write_text(
            json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        return destination

    def test_fresh_repeat_update_and_preflight_preserve_foreign_configuration(self) -> None:
        self.home.mkdir()
        settings = self.home / "settings.json"
        settings.write_text('{"model":"synthetic-existing-user-choice"}\n', encoding="utf-8")
        foreign = self.home / "independently-owned.txt"
        foreign.write_bytes(b"preserve")
        before = _snapshot(self.home)
        self.assertEqual(installer.install_bundle(self.bundle, self.home, check=True)["status"], "checked")
        self.assertEqual(_snapshot(self.home), before)
        result = installer.install_bundle(self.bundle, self.home)
        self.assertEqual(result["status"], "installed")
        self.assertIn(result["directory_sync"], {"supported", "unsupported"})
        before = _snapshot(self.home)
        self.assertEqual(installer.install_bundle(self.bundle, self.home)["status"], "unchanged")
        self.assertEqual(_snapshot(self.home), before)
        self.assertEqual(installer.install_bundle(self.changed_bundle(), self.home)["status"], "updated")
        self.assertEqual(settings.read_text(encoding="utf-8"),
                         '{"model":"synthetic-existing-user-choice"}\n')
        self.assertEqual(foreign.read_bytes(), b"preserve")
        installer.verify_installation(self.target)
        platform.verify_access(self.home / installer.LOCK_PATH, private=True)
        platform.verify_access(self.target / ".constellation-install.json", private=True)

    def test_real_shared_readers_exclude_an_installer_process(self) -> None:
        installer.install_bundle(self.bundle, self.home)
        before = _snapshot(self.home)
        code = (
            "import sys;sys.path.insert(0,sys.argv[1]);import claude;"
            "from pathlib import Path\n"
            "try:\n"
            " claude.install_bundle(Path(sys.argv[2]),Path(sys.argv[3]))\n"
            "except claude.InstallError:\n"
            " print('installer excluded');raise SystemExit(23)\n"
            "raise SystemExit(42)\n")
        reader = (
            "import sys;sys.path.insert(0,sys.argv[1]);import claude;"
            "from pathlib import Path\n"
            "with claude.verified_installation(Path(sys.argv[2])):\n"
            " print('shared reader acquired')\n")
        with installer.verified_installation(self.target):
            result = subprocess.run([sys.executable, "-I", "-B", "-c", reader,
                                     str(self.target / "ecosystem"), str(self.target)],
                                    capture_output=True, text=True, encoding="utf-8", timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("shared reader acquired", result.stdout)
            result = subprocess.run([sys.executable, "-I", "-B", "-c", code,
                                     str(self.target / "ecosystem"), str(self.bundle), str(self.home)],
                                    capture_output=True, text=True, encoding="utf-8", timeout=20)
            self.assertEqual(result.returncode, 23, result.stderr)
        self.assertEqual(_snapshot(self.home), before)

    def test_failed_promotion_restores_previous_payload(self) -> None:
        installer.install_bundle(self.bundle, self.home)
        before = _snapshot(self.home)
        replacement = self.changed_bundle()
        original = platform.promote_directory

        def fail_stage(source: Path, destination: Path) -> None:
            if source.name == installer.STAGING_NAME:
                raise OSError("synthetic promotion failure after backup")
            original(source, destination)

        with patch.object(platform, "promote_directory", side_effect=fail_stage):
            with self.assertRaisesRegex(InstallError, "previous owned payload was restored"):
                installer.install_bundle(replacement, self.home)
        self.assertEqual(_snapshot(self.home), before)
        installer.verify_installation(self.target)

    def test_private_receipt_acl_and_hardlinked_lock_are_rejected(self) -> None:
        installer.install_bundle(self.bundle, self.home)
        marker = self.target / ".constellation-install.json"
        platform.set_access(marker, 0o644)
        with self.assertRaisesRegex(InstallError, "permissions"):
            installer.verify_installation(self.target)
        platform.set_access(marker, 0o600)
        lock = self.home / installer.LOCK_PATH
        os.link(lock, self.root / "foreign-lock-alias")
        before = _snapshot(self.home)
        with self.assertRaisesRegex(InstallError, "singly linked"):
            installer.install_bundle(self.bundle, self.home)
        self.assertEqual(_snapshot(self.home), before)

    def test_interrupted_stage_and_backup_are_preserved_for_explicit_recovery(self) -> None:
        installer.install_bundle(self.bundle, self.home)
        for name in (installer.STAGING_NAME, installer.BACKUP_NAME):
            with self.subTest(name=name):
                pending = self.target.parent / name
                pending.mkdir()
                (pending / "retained.txt").write_bytes(b"recover")
                before = _snapshot(self.home)
                with self.assertRaisesRegex(InstallError, "pending staging or backup"):
                    installer.install_bundle(self.bundle, self.home)
                self.assertEqual(_snapshot(self.home), before)
                shutil.rmtree(pending)

    def test_junction_in_original_home_or_state_path_is_rejected(self) -> None:
        actual = self.root / "actual private parent"
        actual.mkdir()
        junction = self.root / "junction alias"
        if any(character in str(self.root) for character in '%!"'):
            self.skipTest("Host temporary path cannot be safely passed to the junction fixture")
        buffer = ctypes.create_unicode_buffer(32768)
        length = ctypes.windll.kernel32.GetSystemDirectoryW(buffer, len(buffer))
        self.assertGreater(length, 0)
        command = Path(buffer.value) / "cmd.exe"
        result = subprocess.run([str(command), "/d", "/c",
                                 'mklink /J "' + str(junction) + '" "' + str(actual) + '"'],
                                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        try:
            self.assertTrue(platform.is_reparse(junction))
            with self.assertRaisesRegex(InstallError, "reparse"):
                installer.install_bundle(self.bundle, junction / "claude home")
            with self.assertRaisesRegex(storage.Error, "reparse"):
                storage.Store(junction / "private-state")
            with self.assertRaisesRegex(storage.Error, "reparse"):
                core.Engine(junction, self.root / "state-outside-alias")
            self.assertEqual(list(actual.iterdir()), [])
            self.assertFalse((self.root / "state-outside-alias").exists())
        finally:
            junction.rmdir()

    def test_managed_case_variant_cannot_escape_receipt_or_installation_lock(self) -> None:
        installer.install_bundle(self.bundle, self.home)
        variant = self.home / "Skills/Constellation"
        self.assertTrue(variant.exists(), "Acceptance requires ordinary case-insensitive Windows lookup")
        self.assertTrue(os.path.samefile(self.target, variant))
        with installer.verified_installation(variant) as manifest:
            self.assertEqual(manifest["modules"],
                             installer.verify_installation(self.target)["manifest"]["modules"])
        with installer.installation_lock(self.home, exclusive=True):
            with self.assertRaisesRegex(InstallError, "running"):
                with installer.verified_installation(variant):
                    pass
        marker = variant / ".constellation-install.json"
        marker.unlink()
        with self.assertRaises(InstallError):
            with installer.verified_installation(variant):
                pass
        # With neither marker nor lock present, the old case-sensitive branch
        # would mistake this for an explicit uninstalled bundle and accept it.
        (self.home / installer.LOCK_PATH).unlink()
        with self.assertRaisesRegex(InstallError, "lock is missing"):
            with installer.verified_installation(variant):
                pass

    def test_verified_read_api_rejects_mutable_parent_dacl_without_rewriting_it(self) -> None:
        installer.install_bundle(self.bundle, self.home)
        skills = self.target.parent
        kernel, security = platform._ps_windows_api()
        current = platform._ps_current_sid()
        sddl = "O:" + current + "D:P(A;OICI;FA;;;" + current + ")(A;OICI;FA;;;WD)"
        descriptor = ctypes.c_void_p()
        self.assertTrue(security.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            sddl, 1, ctypes.byref(descriptor), None))
        try:
            present, defaulted, dacl = ctypes.c_int(), ctypes.c_int(), ctypes.c_void_p()
            self.assertTrue(security.GetSecurityDescriptorDacl(
                descriptor, ctypes.byref(present), ctypes.byref(dacl), ctypes.byref(defaulted)))
            self.assertEqual(security.SetNamedSecurityInfoW(
                platform._ps_native_name(skills), 1, 0x80000004, None, None, dacl, None), 0)
        finally:
            kernel.LocalFree(descriptor)
        before = platform.access_fingerprint(skills)
        with self.assertRaisesRegex(InstallError, "directory permissions"):
            with installer.verified_installation(self.target):
                pass
        self.assertEqual(platform.access_fingerprint(skills), before)
        platform.set_access(skills, 0o755)
        with installer.verified_installation(self.target):
            pass

    def test_prospective_case_aliases_cannot_be_independent_deliverables(self) -> None:
        project = self.root / "prospective research project"
        project.mkdir()
        engine = core.Engine(project, self.root / "prospective state")
        payload = {
            "requirements": [{"id": "r", "text": "Outputs are independent.",
                "deliverables": ["Report.md", "report.md"], "checks": [], "acceptance": "editorial"}],
            "deliverables": [{"path": name, "profiles": [DEFAULT_PROFILE]}
                             for name in ("Report.md", "report.md")],
            "checks": [], "inputs": [], "depends_on": [], "risk": "quick"}
        with self.assertRaisesRegex(storage.Error, "distinct"):
            engine._contract(payload)
        self.assertEqual(list(project.iterdir()), [])

    def test_input_acl_change_invalidates_passed_checks_and_complete_closure(self) -> None:
        scenario = Scenario(root=self.root / "research project",
                            state_dir=self.root / "research state")
        self.addCleanup(scenario.cleanup)
        source = scenario.root / "input.md"
        source.write_bytes(b"same input content")
        platform.set_access(source, 0o600)
        scenario.contract["inputs"] = [{
            "path": "input.md", "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}]
        scenario.plan()
        scenario.approve()
        scenario.close()
        original_bytes, original_mode = source.read_bytes(), source.stat().st_mode
        platform.set_access(source, 0o644)
        self.assertEqual(source.read_bytes(), original_bytes)
        self.assertEqual(source.stat().st_mode, original_mode)
        self.assertTrue(scenario.call("status")["pending"])
        with self.assertRaises(storage.Error):
            scenario.close()

    def test_crashed_sqlite_writer_retains_private_journal_and_recovers(self) -> None:
        directory = self.root / "private SQLite state"
        store = storage.Store(directory)
        with store.connection(write=True):
            pass
        code = (
            "import os,sqlite3,sys;"
            "db=sqlite3.connect(sys.argv[1]);"
            "db.execute('PRAGMA cache_size=1');"
            "db.execute('BEGIN IMMEDIATE');"
            "db.execute('UPDATE metadata SET version=2');"
            "db.execute('CREATE TABLE crash_fixture (payload TEXT)');"
            "db.executemany('INSERT INTO crash_fixture VALUES (?)', [('x'*4000,)]*40);"
            "os._exit(17)")
        result = subprocess.run([sys.executable, "-I", "-B", "-c", code, str(store.path)],
                                capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 17, result.stderr.decode("utf-8", errors="replace"))
        self.assertTrue(Path(str(store.path) + "-journal").exists())
        # Recovery is an explicit write operation; a read-only status must not
        # mutate a crashed transaction's journal behind the caller's back.
        with store.connection(write=True) as connection:
            self.assertEqual(connection.execute("SELECT version FROM metadata").fetchall()[0][0], 1)
            self.assertIsNone(connection.execute(
                "SELECT name FROM sqlite_master WHERE name='crash_fixture'").fetchone())
        platform.verify_access(directory, private=True)
        platform.verify_access(store.path, private=True)


if __name__ == "__main__":
    unittest.main()

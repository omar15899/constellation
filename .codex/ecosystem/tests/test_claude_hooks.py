"""Synthetic native payloads exercise real shared Git and portable evidence gates.

These checks do not establish interactive Claude trust, model behaviour or native
event dispatch. All state, repositories, remotes and event content are fixtures.
"""
from __future__ import annotations

from contextlib import chdir, contextmanager, redirect_stderr, redirect_stdout
import ctypes
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from types import FunctionType
from unittest import mock

SOURCE = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(SOURCE.parent))
from ecosystem import claude_hooks as adapter, hooks, platform_support
from ecosystem.build import source_resource
from ecosystem.platform_support import file_lock, set_access
from helpers import Scenario


NATIVE = "fixture-claude-session"
SESSION = "claude-" + NATIVE
PRIVATE = "SYNTHETIC-PRIVATE-CLAUDE-EVENT-4f538"


class ClaudeAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="claude-native-adapter-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / "project with spaces"
        self.root.mkdir()
        self.state = self.base / "isolated-state"
        self.environment = mock.patch.dict(os.environ, {"CONSTELLATION_HOOK_OWNER": "shared"})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def payload(self, event: str, **changes: object) -> dict:
        value = {"hook_event_name": event, "session_id": NATIVE, "cwd": str(self.root),
                 "prompt": PRIVATE, "transcript_path": PRIVATE, "last_assistant_message": PRIVATE,
                 "agent_transcript_path": PRIVATE, "tool_input": {"file_path": "result.md", "content": PRIVATE},
                 "tool_name": "Write", "agent_id": "fixture-native-worker", "stop_hook_active": False}
        value.update(changes)
        return value

    def handle(self, event: str, **changes: object) -> dict:
        return adapter.handle_event(self.payload(event, **changes), self.state, event)

    def denied(self, result: dict) -> None:
        self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")

    def scenario(self) -> Scenario:
        scenario = Scenario(root=self.root, state_dir=self.state, session=SESSION)
        self.addCleanup(scenario.cleanup)
        scenario.plan()
        return scenario

    def test_bootstrap_is_relocatable_and_does_not_create_a_task(self) -> None:
        relocated = self.base / "a different laptop" / "research centre"
        result = adapter.handle_event(self.payload("SessionStart"), self.state, "SessionStart",
                                      package_root=relocated)
        context = result["hookSpecificOutput"]["additionalContext"]
        self.assertIn(str(relocated / "ecosystem/cli.py"), context)
        self.assertIn("--session " + SESSION, context)
        self.assertIn("actual native author/reviewer identity", context)
        self.assertNotIn(PRIVATE, json.dumps(result))
        self.assertFalse(self.state.exists())
        self.assertFalse((self.root / ".codex").exists())

    def test_unregistered_events_remain_proportional_and_do_not_create_state(self) -> None:
        for event in sorted(adapter.EVENTS):
            with self.subTest(event=event):
                result = self.handle(event)
                if event in {"SessionStart", "UserPromptSubmit"}:
                    self.assertEqual(result["hookSpecificOutput"]["hookEventName"], event)
                else:
                    self.assertEqual(result, {})
        self.assertFalse(self.state.exists())

    def test_shared_method_guidance_does_not_infer_scope_from_private_prompt(self) -> None:
        class StructuralOnly(dict):
            def get(self, key, default=None):
                if key in {"prompt", "transcript_path", "last_assistant_message"}:
                    raise AssertionError("Private content must not select methods")
                return super().get(key, default)

        for event in ("SessionStart", "UserPromptSubmit"):
            result = adapter.handle_event(StructuralOnly(self.payload(event)), self.state, event)
            context = result["hookSpecificOutput"]["additionalContext"]
            self.assertEqual(context.count(hooks.METHOD_GUIDANCE), 1)
            self.assertIn("native Skill tool", context)
            self.assertNotIn(PRIVATE, context)
        self.assertFalse(self.state.exists())
        scenario = self.scenario()
        before = scenario.call("status")
        context = self.handle("UserPromptSubmit")["hookSpecificOutput"]["additionalContext"]
        self.assertEqual(context.count(hooks.METHOD_GUIDANCE), 1)
        self.assertEqual(scenario.call("status"), before)
        self.denied(self.handle("PreToolUse", tool_input={"file_path": "undeclared.md"}))

    def test_only_structural_fields_reach_shared_dispatch(self) -> None:
        for tool, field in adapter.FILE_TOOLS.items():
            with self.subTest(tool=tool), mock.patch.object(hooks, "handle_event", return_value={}) as dispatch:
                result = self.handle("PreToolUse", tool_name=tool,
                                     tool_input={field: "result.md", "content": PRIVATE, "edits": PRIVATE})
                self.assertEqual(result, {})
                clean = dispatch.call_args.args[0]
                self.assertEqual(set(clean), {"hook_event_name", "session_id", "cwd", "turn_id", "tool_name", "tool_input"})
                self.assertEqual(clean["session_id"], SESSION)
                self.assertEqual(clean["turn_id"], "claude-native")
                self.assertEqual(clean["tool_name"], "apply_patch")
                self.assertNotIn(PRIVATE, json.dumps(clean))
                self.assertIn(str(self.root / "result.md"), clean["tool_input"])

    def test_portable_file_guards_cover_all_native_editors(self) -> None:
        self.scenario()
        for tool, field in adapter.FILE_TOOLS.items():
            with self.subTest(tool=tool):
                self.assertEqual(self.handle("PreToolUse", tool_name=tool, tool_input={field: "result.md"}), {})
                self.denied(self.handle("PreToolUse", tool_name=tool, tool_input={field: "undeclared.md"}))
                self.denied(self.handle("PreToolUse", tool_name=tool,
                                        tool_input={field: str(self.base / "outside.md")}))

    def test_traversal_controls_and_symlink_components_are_rejected(self) -> None:
        self.scenario()
        for name in ("../result.md", "nested/../result.md", "result.md\n*** Update File: other.md", "\x00bad", " result.md"):
            with self.subTest(name=name), self.assertRaises(adapter.AdapterError):
                self.handle("PreToolUse", tool_input={"file_path": name})
        try:
            (self.root / "alias").symlink_to(self.base, target_is_directory=True)
        except OSError as exc:
            if os.name == "nt" and getattr(exc, "winerror", None) == 1314:
                self.skipTest("Directory symlink fixture requires Windows Developer Mode")
            raise
        self.denied(self.handle("PreToolUse", tool_input={"file_path": "alias/result.md"}))

    def test_native_agent_observation_preserves_real_identity_and_private_content(self) -> None:
        scenario = self.scenario()
        self.handle("SubagentStart")
        state = scenario.call("status")
        self.assertEqual(state["observed_agents"], {"fixture-native-worker": "start"})
        self.handle("SubagentStop")
        state = scenario.call("status")
        self.assertEqual(state["observed_agents"], {"fixture-native-worker": "stop"})
        for path in self.state.iterdir():
            if path.is_file():
                self.assertNotIn(PRIVATE.encode(), path.read_bytes())

    def test_other_native_sessions_do_not_inherit_registered_paths(self) -> None:
        scenario = self.scenario()
        before = scenario.call("status")
        self.assertEqual(self.handle("PreToolUse", session_id="unregistered-native-session",
                                     tool_input={"file_path": "other.md"}), {})
        self.assertEqual(scenario.call("status"), before)

    def test_stop_replay_is_bounded_and_completed_task_stays_closed(self) -> None:
        scenario = self.scenario()
        self.assertEqual(self.handle("Stop")["decision"], "block")
        self.assertNotEqual(self.handle("Stop").get("decision"), "block")
        scenario.call("status")
        scenario.approve()
        scenario.close()
        self.assertEqual(self.handle("Stop"), {})
        self.assertEqual(scenario.call("status")["status"], "complete")

    def test_project_owner_bypasses_shared_import_and_malformed_payload(self) -> None:
        with mock.patch.dict(os.environ, {"CONSTELLATION_HOOK_OWNER": "project"}), mock.patch.object(hooks, "handle_event") as dispatch:
            self.assertEqual(adapter.handle_event(None, self.state), {})
            dispatch.assert_not_called()
        self.assertFalse(self.state.exists())

    def test_malformed_native_metadata_is_rejected(self) -> None:
        invalid = ({"session_id": "../outside"}, {"session_id": "x" * 122}, {"cwd": "relative"},
                   {"hook_event_name": "Stop"}, {"session_id": None})
        for changes in invalid:
            with self.subTest(changes=changes), self.assertRaises(adapter.AdapterError):
                self.handle("PreToolUse", **changes)
        with self.assertRaises(adapter.AdapterError):
            self.handle("Stop", stop_hook_active="yes")

    def git_plan(self):
        from ecosystem.runtime.workflow import Workflow
        remote = self.base / "remote.git"
        def git(*args: str) -> None:
            subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)
        git("init", "--bare", "-q", str(remote))
        git("init", "-q", "-b", "main")
        git("config", "user.name", "Synthetic Claude fixture")
        git("config", "user.email", "fixture@example.invalid")
        git("config", "core.hooksPath", str(self.root / ".git/hooks"))
        git("config", "commit.gpgsign", "false")
        (self.root / "result.md").write_text("fixture\n")
        git("add", "result.md")
        git("commit", "-qm", "Create synthetic fixture")
        git("remote", "add", "origin", str(remote))
        git("push", "-qu", "origin", "main")
        flow = Workflow(self.root, SESSION)
        flow.begin("synthetic-setup")
        flow.plan({"requirements": ["Synthetic result is checked"], "paths": ["result.md"]})
        return flow

    def test_real_git_contract_is_shared_without_project_code_import(self) -> None:
        flow = self.git_plan()
        self.assertEqual(self.handle("PreToolUse"), {})
        self.denied(self.handle("PreToolUse", tool_input={"file_path": "undeclared.md"}))
        self.assertIn(SESSION, self.handle("UserPromptSubmit")["hookSpecificOutput"]["additionalContext"])
        self.assertEqual(self.handle("Stop")["decision"], "block")
        self.assertFalse(flow.load().get("finished"))
        self.assertFalse(self.state.exists())


class ClaudeLoaderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="claude-verified-loader-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()

    def release(self, *, installed: bool = False,
                managed_names: tuple[str, str] = ("skills", "constellation")) -> Path:
        root = (self.base / "home" / managed_names[0] / managed_names[1]
                if installed else self.base / "bundle")
        resources = {
            "ecosystem/claude_hooks.py": source_resource(SOURCE.parent, "ecosystem/claude_hooks.py")[0],
            ".claude-plugin/plugin.json": json.dumps({"name": "constellation", "version": "1.3.0"}).encode(),
            ".codex-plugin/plugin.json": json.dumps({"name": "constellation", "version": "1.3.0"}).encode(),
            "ecosystem/hooks.py": b"raise RuntimeError('synthetic unimported package')\n",
        }
        records = {}
        for relative, content in resources.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            set_access(path, 0o644)
            records[relative] = {"sha256": hashlib.sha256(content).hexdigest(), "mode": 0o644}
        manifest = {"schema": 1, "modules": ["coding"], "files": records}
        (root / "bundle.json").write_text(json.dumps(manifest))
        set_access(root / "bundle.json", 0o644)
        if installed:
            receipt = {"schema": 1, "owner": "constellation-claude-skills-dir", "plugin_id": "constellation@skills-dir",
                       "version": "1.3.0", "modules": ["coding"],
                       "bundle_sha256": hashlib.sha256((root / "bundle.json").read_bytes()).hexdigest()}
            (root / adapter.MARKER).write_text(json.dumps(receipt))
            set_access(root / adapter.MARKER, 0o600)
            lock = root.parent.parent / "constellation/.install.lock"
            lock.parent.mkdir()
            set_access(lock.parent, 0o700)
            lock.write_bytes(b"")
            set_access(lock, 0o600)
        return root

    def test_managed_root_classification_preserves_platform_case_rules(self) -> None:
        for windows in (False, True):
            classifier = FunctionType(
                adapter._is_managed_root.__code__,
                {**adapter._is_managed_root.__globals__, "IS_WINDOWS": windows},
            )
            for root, expected in (
                    (Path("home/skills/constellation"), True),
                    (Path("home/Skills/Constellation"), windows),
                    (Path("home/SKILLS/CONSTELLATION"), windows),
                    (Path("home/skill/constellation"), False),
                    (Path("home/skills/unrelated"), False)):
                with self.subTest(windows=windows, root=str(root)):
                    self.assertEqual(classifier(root), expected)

    def _case_variant_managed_ownership_contract(self) -> None:
        root = self.release(installed=True, managed_names=("Skills", "Constellation"))
        marker = root / adapter.MARKER
        content = marker.read_bytes()
        marker.unlink()
        # This rejection fails with the former case-sensitive classification:
        # that path was treated as an explicit uninstalled bundle.
        with self.assertRaises(adapter.AdapterError):
            with adapter.verified_release(root):
                self.fail("case-variant managed root skipped its ownership receipt")
        marker.write_bytes(content)
        set_access(marker, 0o600)
        with adapter.verified_release(root) as manifest:
            self.assertEqual(manifest["modules"], ["coding"])
        lock = root.parent.parent / "constellation/.install.lock"
        with lock.open("rb") as stream:
            with file_lock(stream.fileno(), exclusive=True, blocking=False):
                with self.assertRaises(BlockingIOError):
                    with adapter.verified_release(root):
                        self.fail("case-variant managed root skipped the installer lock")
        lock.unlink()
        with self.assertRaises((adapter.AdapterError, OSError)):
            with adapter.verified_release(root):
                self.fail("case-variant managed root accepted a missing install lock")

    def test_windows_case_classification_keeps_receipt_and_lock_required(self) -> None:
        # Clone the actual classifier code, changing only its policy flag.
        # In an exported bootstrap helpers share the adapter's globals: changing
        # module IS_WINDOWS would incorrectly switch host filesystem primitives.
        classifier = FunctionType(
            adapter._is_managed_root.__code__,
            {**adapter._is_managed_root.__globals__, "IS_WINDOWS": True},
        )
        with mock.patch.object(adapter, "_is_managed_root", classifier):
            self._case_variant_managed_ownership_contract()

    @unittest.skipUnless(os.name == "nt", "Managed path case behavior requires native Windows")
    def test_native_windows_case_variant_installation_keeps_ownership_checks(self) -> None:
        self._case_variant_managed_ownership_contract()

    def test_stdlib_verifier_accepts_relocated_bundle_and_installed_receipt(self) -> None:
        root = self.release()
        moved = self.base / "relocated laptop" / "bundle"
        moved.parent.mkdir()
        shutil.move(str(root), str(moved))
        with adapter.verified_release(moved) as manifest:
            self.assertEqual(manifest["modules"], ["coding"])
        installed = self.release(installed=True)
        with adapter.verified_release(installed) as manifest:
            self.assertEqual(manifest["modules"], ["coding"])

    def _relative_release_alias(self) -> tuple[Path, Path]:
        root = self.release()
        alias = self.base / "junction"
        try:
            alias.symlink_to(self.base, target_is_directory=True)
        except OSError as exc:
            if os.name == "nt" and getattr(exc, "winerror", None) == 1314:
                self.skipTest("Directory symlink fixture requires Windows Developer Mode")
            raise
        return root, alias

    def test_relative_release_first_component_is_checked_before_resolution(self) -> None:
        _root, alias = self._relative_release_alias()
        with chdir(self.base), \
                mock.patch.object(adapter, "IS_WINDOWS", True), \
                mock.patch.object(adapter, "_windows_lookup", return_value=None), \
                mock.patch.object(adapter, "is_reparse", wraps=adapter.is_reparse) as inspect:
            with self.assertRaisesRegex(adapter.AdapterError, "reparse"):
                with adapter.verified_release(Path("junction/bundle")):
                    self.fail("relative release skipped its first redirected component")
        self.assertIn(mock.call(alias), inspect.call_args_list)

    def test_relative_release_checks_the_original_working_directory_ancestors(self) -> None:
        _root, alias = self._relative_release_alias()
        # Simulate a native cwd whose original name still includes a junction.
        # resolve() must not erase that ancestor before the guard inspects it.
        with chdir(self.base), \
                mock.patch.object(adapter, "IS_WINDOWS", True), \
                mock.patch.object(adapter, "_windows_lookup", return_value=None), \
                mock.patch.object(adapter.os, "getcwd", return_value=str(alias)), \
                mock.patch.object(adapter, "is_reparse", wraps=adapter.is_reparse) as inspect:
            with self.assertRaisesRegex(adapter.AdapterError, "reparse"):
                adapter._unlinked_lookup(Path("bundle"))
                self.fail("relative release skipped a redirected cwd ancestor")
        self.assertIn(mock.call(alias), inspect.call_args_list)

    def test_existing_relative_release_and_current_directory_remain_valid(self) -> None:
        root = self.release()
        with chdir(self.base):
            with adapter.verified_release(Path("bundle")) as manifest:
                self.assertEqual(manifest["modules"], ["coding"])
        with chdir(root):
            with adapter.verified_release(Path(".")) as manifest:
                self.assertEqual(manifest["modules"], ["coding"])

    @unittest.skipUnless(os.name == "nt", "Relative reparse behavior requires native Windows")
    def test_native_windows_relative_release_rejects_first_reparse_component(self) -> None:
        _root, _alias = self._relative_release_alias()
        with chdir(self.base):
            with self.assertRaisesRegex(adapter.AdapterError, "reparse"):
                with adapter.verified_release(Path("junction/bundle")):
                    self.fail("native relative release skipped a reparse component")

    def test_tamper_unexpected_files_links_and_missing_receipt_are_rejected(self) -> None:
        root = self.release(installed=True)
        module = root / "ecosystem/hooks.py"
        original = module.read_bytes()
        module.write_bytes(original + b"# altered\n")
        with self.assertRaises(adapter.AdapterError):
            with adapter.verified_release(root):
                self.fail("tampered package accepted")
        module.write_bytes(original)
        extra = root / "unexpected.py"
        extra.write_text("fixture\n")
        with self.assertRaises(adapter.AdapterError):
            with adapter.verified_release(root):
                self.fail("unexpected resource accepted")
        extra.unlink()
        outside = self.base / "outside.py"
        outside.write_bytes(original)
        module.unlink()
        if os.name == "nt":
            # A hardlink needs no symlink privilege and must be refused by the
            # same installed-resource ownership check.
            os.link(outside, module)
        else:
            module.symlink_to(outside)
        with self.assertRaises(adapter.AdapterError):
            with adapter.verified_release(root):
                self.fail("linked resource accepted")
        module.unlink()
        module.write_bytes(original)
        (root / adapter.MARKER).unlink()
        with self.assertRaises(adapter.AdapterError):
            with adapter.verified_release(root):
                self.fail("unowned installation accepted")

    @unittest.skipIf(os.name == "nt", "POSIX permission mutation; Windows ACL primitives have native tests")
    def test_writable_package_directories_are_rejected_before_import(self) -> None:
        root = self.release()
        for directory in (root, root / "ecosystem"):
            before = directory.stat().st_mode & 0o777
            try:
                directory.chmod(0o777)
                with self.subTest(directory=directory.name), self.assertRaises(adapter.AdapterError):
                    with adapter.verified_release(root):
                        self.fail("foreign-writable release directory accepted")
            finally:
                directory.chmod(before)
        with adapter.verified_release(root):
            pass

    @unittest.skipIf(os.name == "nt", "POSIX permission mutation; Windows ACL primitives have native tests")
    def test_writable_installed_parent_boundaries_are_rejected(self) -> None:
        root = self.release(installed=True)
        home = root.parent.parent
        for directory in (home, root.parent, home / "constellation"):
            before = directory.stat().st_mode & 0o777
            try:
                directory.chmod(0o777)
                with self.subTest(directory=directory.name), self.assertRaises(adapter.AdapterError):
                    with adapter.verified_release(root):
                        self.fail("foreign-writable managed parent accepted")
            finally:
                directory.chmod(before)
        with adapter.verified_release(root):
            pass

    def test_unmanaged_windows_policy_checks_parent_access_and_keeps_pins_through_yield(self) -> None:
        root = self.release()
        events = []

        @contextmanager
        def pin_lookup(path):
            events.append(("enter", path))
            try:
                yield
            finally:
                events.append(("exit", path))

        generator = adapter.verified_release.__wrapped__
        verify_windows_policy = contextmanager(FunctionType(
            generator.__code__,
            {**generator.__globals__, "IS_WINDOWS": True, "_ps_guard_parents": pin_lookup},
        ))
        with verify_windows_policy(root) as manifest:
            self.assertEqual(manifest["modules"], ["coding"])
            self.assertEqual(events, [("enter", root / "bundle.json")])
        self.assertEqual(events[-1], ("exit", root / "bundle.json"))
        events.clear()
        with self.assertRaisesRegex(RuntimeError, "synthetic consumer"):
            with verify_windows_policy(root):
                self.assertEqual(events, [("enter", root / "bundle.json")])
                raise RuntimeError("synthetic consumer")
        self.assertEqual(events[-1], ("exit", root / "bundle.json"))
        if os.name != "nt":
            # Windows chmod does not change DACLs. Its native ACL rejection is
            # exercised separately; the pin-lifetime positives above run there.
            before = self.base.stat().st_mode & 0o7777
            try:
                self.base.chmod(0o777)
                with self.assertRaises(adapter.AdapterError):
                    with verify_windows_policy(root):
                        self.fail("unmanaged Windows policy accepted a foreign-writable parent")
                self.assertEqual(events[-1], ("exit", root / "bundle.json"))
            finally:
                self.base.chmod(before)
        with verify_windows_policy(root):
            pass

    @unittest.skipIf(os.name == "nt", "POSIX sticky-directory semantics")
    def test_posix_sticky_parent_keeps_an_owned_explicit_bundle_usable(self) -> None:
        root = self.release()
        before = self.base.stat().st_mode & 0o7777
        try:
            self.base.chmod(0o1777)
            with adapter.verified_release(root) as manifest:
                self.assertEqual(manifest["modules"], ["coding"])
        finally:
            self.base.chmod(before)

    @unittest.skipUnless(os.name == "nt", "Directory handle lifetime requires native Windows")
    def test_native_windows_unmanaged_lookup_stays_pinned_and_releases_after_errors(self) -> None:
        root = self.release()
        moved = self.base / "moved-bundle"
        with adapter.verified_release(root):
            with self.assertRaises(OSError):
                root.rename(moved)
            self.assertTrue(root.is_dir())
        root.rename(moved)
        moved.rename(root)
        with self.assertRaisesRegex(RuntimeError, "synthetic consumer"):
            with adapter.verified_release(root):
                raise RuntimeError("synthetic consumer")
        root.rename(moved)
        moved.rename(root)
        inventory = root / "bundle.json"
        content = inventory.read_bytes()
        inventory.write_bytes(b"{invalid")
        with self.assertRaises(adapter.AdapterError):
            with adapter.verified_release(root):
                self.fail("invalid inventory reached dispatch")
        inventory.write_bytes(content)
        root.rename(moved)

    @unittest.skipUnless(os.name == "nt", "Parent replacement DACL requires native Windows")
    def test_native_windows_unmanaged_parent_replacement_rights_are_rejected(self) -> None:
        root = self.release()
        set_access(root, 0o700)
        set_access(self.base, 0o700)
        module = root / "ecosystem/claude_hooks.py"
        before = (platform_support.access_fingerprint(root),
                  platform_support.access_fingerprint(module))
        kernel, security = platform_support._ps_windows_api()
        current = platform_support._ps_current_sid()
        descriptor, dacl = ctypes.c_void_p(), ctypes.c_void_p()
        sddl = ("O:" + current + "D:P(A;;FA;;;" + current
                + ")(A;;FA;;;SY)(A;;FA;;;BA)(A;;0x00000044;;;WD)")
        try:
            self.assertTrue(security.ConvertStringSecurityDescriptorToSecurityDescriptorW(
                sddl, 1, ctypes.byref(descriptor), None))
            present, defaulted = ctypes.c_int(), ctypes.c_int()
            self.assertTrue(security.GetSecurityDescriptorDacl(
                descriptor, ctypes.byref(present), ctypes.byref(dacl), ctypes.byref(defaulted)))
            self.assertEqual(security.SetNamedSecurityInfoW(
                platform_support._ps_native_name(self.base), 1, 0x80000004,
                None, None, dacl, None), 0)
            self.assertEqual(before, (platform_support.access_fingerprint(root),
                                     platform_support.access_fingerprint(module)))
            adapter._verify_release(root, installed=False)
            with self.assertRaises(adapter.AdapterError):
                with adapter.verified_release(root):
                    self.fail("this-folder-only parent replacement rights reached dispatch")
        finally:
            try:
                set_access(self.base, 0o700)
            finally:
                if descriptor.value:
                    kernel.LocalFree(descriptor)
        with adapter.verified_release(root):
            pass

    def test_exclusive_installer_lock_blocks_hook_without_importing_package(self) -> None:
        root = self.release(installed=True)
        with (root.parent.parent / "constellation/.install.lock").open("rb") as stream:
            with file_lock(stream.fileno(), exclusive=True, blocking=False):
                with self.assertRaises(BlockingIOError):
                    with adapter.verified_release(root):
                        self.fail("installer race accepted")

    def test_malformed_native_release_identity_is_rejected(self) -> None:
        root = self.release()
        manifest = json.loads((root / "bundle.json").read_text())
        for relative in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json"):
            path = root / relative
            path.write_text(json.dumps({"name": "constellation"}))
            manifest["files"][relative]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        (root / "bundle.json").write_text(json.dumps(manifest))
        with self.assertRaises(adapter.AdapterError):
            with adapter.verified_release(root):
                self.fail("missing native versions accepted")

    def invoke(self, root: Path, event: str, *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
        environment = dict(os.environ)
        environment.pop("CONSTELLATION_HOOK_OWNER", None)
        if env:
            environment.update(env)
        return subprocess.run([sys.executable, "-I", str(root / "ecosystem/claude_hooks.py"), event],
                              input=json.dumps({"hook_event_name": event, "session_id": NATIVE,
                                                "cwd": str(self.base), "prompt": PRIVATE}),
                              text=True, capture_output=True, env=environment, timeout=15)

    def test_operational_failure_denies_tools_and_blocks_prompt_with_no_private_output(self) -> None:
        root = self.release()
        # Package code would raise if imported; a corrupt hash must reject it first.
        marker = self.base / "unverified-package-imported"
        (root / "ecosystem/hooks.py").write_text(
            "from pathlib import Path\n"
            f"Path({str(marker)!r}).write_text('synthetic import ran')\n"
            "raise RuntimeError('LEAK-IMPORT-SENTINEL')\n")
        tool = self.invoke(root, "PreToolUse")
        self.assertEqual(tool.returncode, 0)
        self.assertEqual(json.loads(tool.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")
        prompt = self.invoke(root, "UserPromptSubmit")
        self.assertEqual(prompt.returncode, 2)
        self.assertNotIn("LEAK-IMPORT-SENTINEL", tool.stdout + tool.stderr + prompt.stdout + prompt.stderr)
        self.assertNotIn(PRIVATE, tool.stdout + tool.stderr + prompt.stdout + prompt.stderr)
        self.assertFalse(marker.exists())

    def test_unsupported_python_rejects_without_loading_runtime_or_reading_event(self) -> None:
        for event in sorted(adapter.EVENTS):
            output, errors = io.StringIO(), io.StringIO()
            private_input = mock.Mock()
            private_input.buffer.read.side_effect = AssertionError("Private input must remain unread")
            with self.subTest(event=event), \
                    mock.patch.dict(os.environ, {"CONSTELLATION_HOOK_OWNER": "shared"}), \
                    mock.patch.object(adapter.sys, "version_info", (3, 9, 6)), \
                    mock.patch.object(adapter.sys, "stdin", private_input), \
                    mock.patch.object(adapter, "verified_release") as verify, \
                    mock.patch.object(adapter, "handle_event") as dispatch, \
                    redirect_stdout(output), redirect_stderr(errors):
                code = adapter.main([event])
            verify.assert_not_called()
            dispatch.assert_not_called()
            private_input.buffer.read.assert_not_called()
            combined = output.getvalue() + errors.getvalue()
            self.assertIn("Python 3.11", combined)
            self.assertIn("PATH", combined)
            self.assertNotIn(PRIVATE, combined)
            if event == "UserPromptSubmit":
                self.assertEqual(code, 2)
                self.assertEqual(output.getvalue(), "")
            else:
                self.assertEqual(code, 0)
                response = json.loads(output.getvalue())
                if event == "PreToolUse":
                    self.assertEqual(response["hookSpecificOutput"]["permissionDecision"], "deny")
                else:
                    self.assertEqual(set(response), {"systemMessage"})
                self.assertNotIn("additionalContext", combined)

    def test_distributed_bootstrap_does_not_import_an_unverified_helper(self) -> None:
        root = self.release()
        rendered = (root / "ecosystem/claude_hooks.py").read_text(encoding="utf-8")
        self.assertNotIn("from platform_support import", rendered)
        self.assertNotIn("from .platform_support import", rendered)
        marker = self.base / "unverified-helper-imported"
        (root / "ecosystem/platform_support.py").write_text(
            "from pathlib import Path\n"
            f"Path({str(marker)!r}).write_text('must not run')\n"
            "raise RuntimeError('SYNTHETIC-HELPER-LEAK')\n", encoding="utf-8")
        result = self.invoke(root, "PreToolUse")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertFalse(marker.exists())
        self.assertNotIn("SYNTHETIC-HELPER-LEAK", result.stdout + result.stderr)

    def test_windows_native_names_reject_aliases_without_filesystem_lookup(self) -> None:
        invalid = (
            "C:relative.md", "\\\\server\\share\\result.md", "\\root-relative.md",
            "\\\\?\\C:\\project\\result.md", "result.md:stream", "NUL.txt",
            "aux", "folder./result.md", "folder /result.md", "folder/../result.md",
        )
        with mock.patch.object(adapter, "IS_WINDOWS", True):
            for value in invalid:
                with self.subTest(value=value), self.assertRaises(adapter.AdapterError):
                    adapter._windows_lookup(value)
            for value in ("folder/result.md", "C:\\Projects\\O'Neil\\result.md"):
                with self.subTest(value=value):
                    adapter._windows_lookup(value)

    @unittest.skipUnless(os.name == "nt", "PowerShell argument execution requires native Windows")
    def test_powershell_guidance_round_trips_literal_arguments(self) -> None:
        executable = shutil.which("powershell.exe") or shutil.which("pwsh.exe")
        if executable is None:
            self.skipTest("Native PowerShell executable is unavailable")
        values = ["space name", "O'Neil", "$literal", "'; throw 'SYNTHETIC-INJECTION", "Unicode-λ"]
        command = adapter._command_line([
            sys.executable, "-I", "-c",
            "import json,sys;print(json.dumps(sys.argv[1:],ensure_ascii=True))", *values,
        ])
        result = subprocess.run(
            [executable, "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True, text=True, encoding="utf-8", timeout=15, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout.strip()), values)

    def test_project_owned_cli_needs_no_package_import_or_manifest(self) -> None:
        root = self.release()
        (root / "bundle.json").unlink()
        result = self.invoke(root, "SessionStart", env={"CONSTELLATION_HOOK_OWNER": "project"})
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout), {})


if __name__ == "__main__":
    unittest.main()

"""Cross-platform filesystem contracts; Windows cases require actual Windows.

No test accesses a personal installation, account, model or network. Skipped
native Windows cases are reported as unexecuted, never treated as acceptance.
"""
from __future__ import annotations

from contextlib import contextmanager
import ctypes
import importlib.util
import os
from pathlib import Path, PurePosixPath
import queue
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock

sys.dont_write_bytecode = True
SOURCE = Path(__file__).resolve().parents[1] / "platform_support.py"
_SPEC = importlib.util.spec_from_file_location("constellation_platform_tested", SOURCE)
assert _SPEC is not None and _SPEC.loader is not None
subject = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(subject)

_CHILD = r"""
import importlib.util,os,sys
from pathlib import Path, PurePosixPath
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location("platform_child",sys.argv[1])
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
fd=module.open_regular(Path(sys.argv[2]),os.O_RDWR,private=True)
try:
    try:
        with module.file_lock(fd,exclusive=sys.argv[3]=="exclusive",blocking=False):
            print("acquired",flush=True)
            if len(sys.argv)>4:
                sys.stdin.readline()
    except BlockingIOError:
        print("blocked",flush=True)
        raise SystemExit(73)
finally:
    os.close(fd)
"""


class PathContractTests(unittest.TestCase):
    def test_windows_protocol_paths_preserve_valid_unicode_and_spaces(self) -> None:
        for value in ("notes/result.md", "folder with spaces/énergie.txt", ".codex/config.json"):
            self.assertEqual(subject.validate_windows_relative(value), value)

    def test_windows_aliases_devices_streams_and_ambiguous_paths_are_rejected(self) -> None:
        invalid = ("", ".", "..", "/root", "//server/share", "C:relative", "C:/absolute",
                   "a\\b", "a/../b", "a/./b", "a//b", "a/", "CON", "con.txt", "AUX",
                   "NUL.log", "PRN", "COM1.ext", "LPT9", "com¹.txt", "LPT²",
                   "CONIN$", "CONOUT$", "CLOCK$", "CON .txt", "NUL .txt", "COM1 .x",
                   "LPT1 .x", "folder/CON .txt", "COM¹ .txt", "LPT² .log", "name.", "name ", "a:b", "a?b",
                   "a*b", "a<b", 'a"b', "a|b", "a\x00b", "a\nb", "a/.. ")
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(subject.PlatformError):
                subject.validate_windows_relative(value)


class _FilesystemFixture:
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="constellation platform ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.private = self.root / "private"
        subject.secure_mkdir(self.private)
        self.path = self.private / "lock file.txt"
        fd = subject.open_regular(self.path, os.O_CREAT | os.O_EXCL | os.O_RDWR, private=True)
        os.write(fd, b"original content")
        subject.sync_file(fd)
        os.close(fd)

    def child(self, kind: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "-I", "-B", "-c", _CHILD, str(SOURCE),
                               str(self.path), kind], capture_output=True, text=True,
                              timeout=15, cwd=self.root)



class FilesystemContractTests(_FilesystemFixture, unittest.TestCase):
    def test_private_creation_mode_identity_and_flush(self) -> None:
        subject.verify_access(self.private, private=True)
        subject.verify_access(self.path, private=True)
        self.assertEqual(subject.logical_mode(self.path, expected=0o600), 0o600)
        fd = subject.open_regular(self.path, os.O_RDONLY, private=True)
        try:
            self.assertFalse(os.get_inheritable(fd))
            self.assertEqual(os.read(fd, 100), b"original content")
        finally:
            os.close(fd)
        self.assertIsInstance(subject.sync_directory(self.private), bool)

    def test_existing_foreign_destination_is_never_replaced(self) -> None:
        stage, target = self.root / "stage", self.root / "target"
        subject.secure_mkdir(stage, 0o755)
        subject.secure_mkdir(target, 0o755)
        (target / "user.txt").write_text("preserve", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            subject.promote_directory(stage, target)
        self.assertEqual((target / "user.txt").read_text(encoding="utf-8"), "preserve")
        self.assertTrue(stage.is_dir())

    def test_new_directory_promotion_preserves_payload(self) -> None:
        stage, target = self.root / "staging", self.root / "installed"
        subject.secure_mkdir(stage, 0o755)
        (stage / "payload.txt").write_bytes(b"payload")
        subject.promote_directory(stage, target)
        self.assertFalse(stage.exists())
        self.assertEqual((target / "payload.txt").read_bytes(), b"payload")

    @unittest.skipIf(subject.IS_WINDOWS, "POSIX native rename fault; Windows uses MoveFileEx")
    def test_failed_posix_exclusive_rename_preserves_source_and_absence(self) -> None:
        stage, target = self.root / "staging", self.root / "installed"
        subject.secure_mkdir(stage, 0o755)
        with mock.patch.object(subject, "_ps_posix_rename_exclusive",
                               side_effect=OSError("synthetic failure")):
            with self.assertRaises(OSError):
                subject.promote_directory(stage, target)
        self.assertTrue(stage.is_dir())
        self.assertFalse(target.exists())

    @unittest.skipIf(subject.IS_WINDOWS, "POSIX native rename interleaving; Windows uses MoveFileEx")
    def test_concurrent_empty_target_is_preserved_by_atomic_posix_promotion(self) -> None:
        stage, target = self.root / "staging", self.root / "installed"
        subject.secure_mkdir(stage, 0o755)
        (stage / "payload.txt").write_bytes(b"preserve source")
        native = subject._ps_posix_rename_exclusive
        foreign_identity = []
        def create_foreign_then_rename(source, destination):
            target.mkdir()
            info = target.stat()
            foreign_identity.append((info.st_dev, info.st_ino))
            native(source, destination)
        with mock.patch.object(subject, "_ps_posix_rename_exclusive",
                               side_effect=create_foreign_then_rename):
            with self.assertRaises(FileExistsError):
                subject.promote_directory(stage, target)
        current = target.stat()
        self.assertEqual((current.st_dev, current.st_ino), foreign_identity[0])
        self.assertEqual((stage / "payload.txt").read_bytes(), b"preserve source")
        self.assertEqual(list(target.iterdir()), [])

    @unittest.skipIf(subject.IS_WINDOWS, "POSIX identity-swap contract; Windows denies delete-sharing")
    def test_identity_swap_is_rejected_before_truncation(self) -> None:
        previous = self.private / "previous.txt"
        real_open = os.open
        def swap_after_open(path, flags, mode=0o777):
            descriptor = real_open(path, flags, mode)
            self.path.rename(previous)
            self.path.write_bytes(b"replacement")
            os.chmod(self.path, 0o600)
            return descriptor
        with mock.patch.object(subject.os, "open", swap_after_open):
            with self.assertRaises(subject.PlatformError):
                subject.open_regular(self.path, os.O_WRONLY | os.O_TRUNC, private=True)
        self.assertEqual(previous.read_bytes(), b"original content")
        self.assertEqual(self.path.read_bytes(), b"replacement")

    def test_shared_readers_and_exclusive_writer_are_distinguished_between_processes(self) -> None:
        fd = subject.open_regular(self.path, os.O_RDWR, private=True)
        try:
            with subject.file_lock(fd, exclusive=False):
                reader, writer = self.child("shared"), self.child("exclusive")
                self.assertEqual(reader.returncode, 0, reader.stderr)
                self.assertEqual(writer.returncode, 73, writer.stderr)
            with subject.file_lock(fd, exclusive=True):
                for kind in ("shared", "exclusive"):
                    result = self.child(kind)
                    self.assertEqual(result.returncode, 73, result.stderr)
            self.assertEqual(self.child("exclusive").returncode, 0)
        finally:
            os.close(fd)

    def test_exception_releases_lock_for_another_process(self) -> None:
        fd = subject.open_regular(self.path, os.O_RDWR, private=True)
        try:
            with self.assertRaisesRegex(ValueError, "body failure"):
                with subject.file_lock(fd):
                    raise ValueError("body failure")
            self.assertEqual(self.child("exclusive").returncode, 0)
        finally:
            os.close(fd)

    def test_hardlink_is_rejected_before_truncation_or_permission_change(self) -> None:
        alias = self.private / "hardlink"
        try:
            os.link(self.path, alias)
        except OSError as exc:
            self.skipTest("Filesystem cannot create the required hardlink: " + type(exc).__name__)
        before = self.path.read_bytes(), stat.S_IMODE(self.path.stat().st_mode)
        with self.assertRaises(subject.PlatformError):
            subject.open_regular(alias, os.O_WRONLY | os.O_TRUNC, private=True)
        with self.assertRaises(subject.PlatformError):
            subject.set_access(alias, 0o644)
        self.assertEqual((self.path.read_bytes(), stat.S_IMODE(self.path.stat().st_mode)), before)

    def test_symbolic_link_and_linked_parent_are_rejected(self) -> None:
        link = self.root / "linked"
        try:
            link.symlink_to(self.private, target_is_directory=True)
        except OSError as exc:
            self.skipTest("Creating symbolic links is not permitted: " + type(exc).__name__)
        self.assertTrue(subject.is_reparse(link))
        with self.assertRaises(subject.PlatformError):
            subject.open_regular(link / self.path.name, os.O_RDWR, private=True)
        with self.assertRaises(subject.PlatformError):
            subject.secure_mkdir(link / "child")
        self.assertFalse((self.private / "child").exists())

    def test_private_final_directory_is_validated_without_automatic_adoption(self) -> None:
        subject.set_access(self.private, 0o755)
        before = subject.access_fingerprint(self.private)
        with self.assertRaises(subject.PlatformError):
            subject.secure_mkdir(self.private, exist_ok=True)
        self.assertEqual(subject.access_fingerprint(self.private), before)

    def test_permission_fingerprint_is_stable_and_changes_with_policy(self) -> None:
        first = subject.access_fingerprint(self.path)
        self.assertRegex(first, r"^[0-9a-f]{64}$")
        self.assertEqual(first, subject.access_fingerprint(self.path))
        subject.set_access(self.path, 0o644)
        self.assertNotEqual(first, subject.access_fingerprint(self.path))

    def test_inherited_sidecar_requires_its_direct_private_parent(self) -> None:
        sidecar = self.private / "state.sqlite-journal"
        sidecar.write_bytes(b"synthetic journal")
        if not subject.IS_WINDOWS:
            os.chmod(sidecar, 0o600)
        subject.verify_access(sidecar, private=True, inherited_from=self.private)
        with self.assertRaises(subject.PlatformError):
            subject.verify_access(sidecar, private=True, inherited_from=self.root)
        subject.set_access(sidecar, 0o644)
        with self.assertRaises(subject.PlatformError):
            subject.verify_access(sidecar, private=True, inherited_from=self.private)
        subject.set_access(sidecar, 0o600)
        subject.set_access(self.private, 0o755)
        with self.assertRaises(subject.PlatformError):
            subject.verify_access(sidecar, private=True, inherited_from=self.private)


class ArtifactIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="constellation artifact identity ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()

    def test_exact_and_existing_hardlink_aliases_are_detected(self) -> None:
        path = self.root / "artifact.txt"
        path.write_bytes(b"same file")
        alias = self.root / "alias.txt"
        os.link(path, alias)
        self.assertTrue(subject.same_artifact(self.root, "artifact.txt", "artifact.txt"))
        self.assertTrue(subject.same_artifact(self.root, "artifact.txt", "alias.txt"))
        with self.assertRaises(subject.PlatformError):
            subject.ensure_distinct_paths(self.root, ["artifact.txt", "alias.txt"])

    def test_distinct_names_remain_distinct_when_the_filesystem_distinguishes_them(self) -> None:
        first, second = self.root / "Name.txt", self.root / "name.txt"
        first.write_bytes(b"first")
        second.write_bytes(b"second")
        if first.stat().st_ino == second.stat().st_ino or subject.IS_WINDOWS:
            self.assertTrue(subject.same_artifact(self.root, "Name.txt", "name.txt"))
            with self.assertRaises(subject.PlatformError):
                subject.ensure_distinct_paths(self.root, ["Name.txt", "name.txt"])
        else:
            self.assertFalse(subject.same_artifact(self.root, "Name.txt", "name.txt"))
            subject.ensure_distinct_paths(self.root, ["Name.txt", "name.txt"])

    @unittest.skipIf(subject.IS_WINDOWS, "These names are valid only on POSIX")
    def test_posix_colon_and_backslash_names_keep_their_existing_meaning(self) -> None:
        names = ["C:notes.md", "back" + chr(92) + "slash.txt"]
        for name in names:
            (self.root / name).write_bytes(b"legitimate POSIX name")
            self.assertTrue(subject.same_artifact(self.root, name, name))
        subject.ensure_distinct_paths(self.root, names)

    def test_windows_prospective_case_aliases_are_rejected_before_creation(self) -> None:
        # Only lexical Windows policy is simulated; no Windows API call is claimed.
        with mock.patch.object(subject, "IS_WINDOWS", True), \
                mock.patch.object(subject, "validate_lookup", return_value=self.root), \
                mock.patch.object(subject, "_ps_check_components"):
            self.assertTrue(subject.same_artifact(self.root, "Future.txt", "future.txt"))
            with self.assertRaises(subject.PlatformError):
                subject.ensure_distinct_paths(self.root, ["Future.txt", "future.txt"])

    def test_symlink_identity_is_rejected_without_following(self) -> None:
        original, alias = self.root / "original.txt", self.root / "alias.txt"
        original.write_bytes(b"original")
        try:
            alias.symlink_to(original)
        except OSError as exc:
            self.skipTest("Symbolic link creation unavailable: " + type(exc).__name__)
        with self.assertRaises(subject.PlatformError):
            subject.same_artifact(self.root, "original.txt", "alias.txt")


@unittest.skipUnless(sys.platform.startswith("linux"), "Actual Linux renameat2 acceptance requires Linux")
class NativeLinuxPromotionTests(_FilesystemFixture, unittest.TestCase):
    def test_native_linux_exclusive_promotion_and_collision(self) -> None:
        stage, target = self.root / "stage", self.root / "target"
        subject.secure_mkdir(stage, 0o755)
        subject.promote_directory(stage, target)
        self.assertFalse(stage.exists())
        self.assertTrue(target.is_dir())
        stage.mkdir()
        before = target.stat()
        with self.assertRaises(FileExistsError):
            subject.promote_directory(stage, target)
        self.assertEqual((target.stat().st_dev, target.stat().st_ino),
                         (before.st_dev, before.st_ino))
        self.assertTrue(stage.is_dir())


class PosixRenameSelectionTests(unittest.TestCase):
    def tearDown(self) -> None:
        subject._ps_posix_rename_api.cache_clear()

    def test_linux_binding_uses_noreplace_flag_and_absolute_fd_arguments(self) -> None:
        function = mock.Mock(return_value=0)
        library = mock.Mock()
        library.renameat2 = function
        subject._ps_posix_rename_api.cache_clear()
        with (mock.patch.object(subject.sys, "platform", "linux"),
              mock.patch.object(subject.ctypes, "CDLL", return_value=library)):
            subject._ps_posix_rename_exclusive(PurePosixPath("/fixed/source"), PurePosixPath("/fixed/target"))
        function.assert_called_once_with(-100, b"/fixed/source", -100, b"/fixed/target", 1)

    def test_unavailable_native_entry_fails_without_a_rename_fallback(self) -> None:
        class NoRenameEntries:
            pass
        subject._ps_posix_rename_api.cache_clear()
        with (mock.patch.object(subject.sys, "platform", "linux"),
              mock.patch.object(subject.ctypes, "CDLL", return_value=NoRenameEntries()),
              mock.patch.object(Path, "rename") as fallback):
            with self.assertRaises(subject.PlatformError):
                subject._ps_posix_rename_exclusive(PurePosixPath("/fixed/source"), PurePosixPath("/fixed/target"))
        fallback.assert_not_called()

    def test_filesystem_rejection_is_not_retried_without_exclusive_flag(self) -> None:
        def unsupported(*_arguments):
            ctypes.set_errno(subject.errno.ENOTSUP)
            return -1
        function = mock.Mock(side_effect=unsupported)
        library = mock.Mock()
        library.renamex_np = function
        subject._ps_posix_rename_api.cache_clear()
        with (mock.patch.object(subject.sys, "platform", "darwin"),
              mock.patch.object(subject.ctypes, "CDLL", return_value=library),
              mock.patch.object(Path, "rename") as fallback):
            with self.assertRaisesRegex(subject.PlatformError, "unsupported"):
                subject._ps_posix_rename_exclusive(PurePosixPath("/fixed/source"), PurePosixPath("/fixed/target"))
        function.assert_called_once_with(b"/fixed/source", b"/fixed/target", 4)
        fallback.assert_not_called()


class SimulatedWindowsAclTests(unittest.TestCase):
    def check_acl(self, inherited_sid: str, *, direct_flags: int = 0) -> None:
        # Exercise the actual ctypes ACE parser with native-layout buffers, while
        # substituting only OS calls; this does not claim a Windows execution.
        class Ace(ctypes.Structure):
            _fields_ = [("header", subject._ps_ACE_HEADER), ("mask", ctypes.c_uint32),
                        ("sid_start", ctypes.c_uint32)]
        first = Ace(subject._ps_ACE_HEADER(0, direct_flags, 12), 0x001F01FF, 0)
        second = Ace(subject._ps_ACE_HEADER(0, 0x0B, 12), 0x001F01FF, 0)
        header = subject._ps_ACL_HEADER(2, 0, 32, 2, 0)
        current = "S-1-5-21-100-200-300-1000"
        def named(_path, _type, _flags, owner, _group, dacl, _sacl, descriptor):
            ctypes.cast(owner, ctypes.POINTER(ctypes.c_void_p))[0] = 1
            ctypes.cast(dacl, ctypes.POINTER(ctypes.c_void_p))[0] = ctypes.addressof(header)
            ctypes.cast(descriptor, ctypes.POINTER(ctypes.c_void_p))[0] = 42
            return 0
        def control(_descriptor, value, revision):
            ctypes.cast(value, ctypes.POINTER(subject._ps_WORD))[0] = 0x1000
            ctypes.cast(revision, ctypes.POINTER(subject._ps_DWORD))[0] = 1
            return 1
        def get_ace(_dacl, index, value):
            ctypes.cast(value, ctypes.POINTER(ctypes.c_void_p))[0] = ctypes.addressof((first, second)[index])
            return 1
        mapping = {1: current, ctypes.addressof(first) + 8: current,
                   ctypes.addressof(second) + 8: inherited_sid}
        security, kernel = mock.Mock(), mock.Mock()
        security.GetNamedSecurityInfoW.side_effect = named
        security.GetSecurityDescriptorControl.side_effect = control
        security.GetAce.side_effect = get_ace
        def sid_text(value):
            address = value if isinstance(value, int) else value.value
            return mapping[address]
        with tempfile.TemporaryDirectory(prefix="constellation ACL parser ") as temporary:
            root = Path(temporary).resolve()
            with (mock.patch.object(subject, "IS_WINDOWS", True),
                  mock.patch.object(subject, "_ps_windows_api", return_value=(kernel, security)),
                  mock.patch.object(subject, "_ps_current_sid", return_value=current),
                  mock.patch.object(subject, "_ps_absolute", side_effect=lambda path: Path(path).absolute()),
                  mock.patch.object(subject, "_ps_check_components"),
                  mock.patch.object(subject, "_ps_sid_text", side_effect=sid_text)):
                owner, protected, entries = subject._ps_acl(root)
                self.assertEqual(owner, current)
                self.assertTrue(protected)
                self.assertEqual(len(entries), 2)
                self.assertEqual(entries[1][3], 0x0B)
                subject.verify_access(root, private=True)

    def test_inherit_only_everyone_grant_is_rejected_for_private_directory(self) -> None:
        with self.assertRaises(subject.PlatformError):
            self.check_acl("S-1-1-0")

    def test_inherit_only_trusted_grant_remains_allowed(self) -> None:
        self.check_acl("S-1-5-18")

    def test_inherit_only_owner_grant_does_not_count_as_direct_access(self) -> None:
        with self.assertRaises(subject.PlatformError):
            self.check_acl("S-1-5-18", direct_flags=0x0B)


class SimulatedWindowsFailureTests(unittest.TestCase):
    def test_directory_flush_does_not_disguise_access_denial_as_unsupported(self) -> None:
        kernel = mock.Mock()
        kernel.CreateFileW.return_value = ctypes.c_void_p(-1).value
        root = Path(tempfile.gettempdir())
        for code in (1, 50, 5, 6, 87):
            with self.subTest(code=code), mock.patch.object(subject, "IS_WINDOWS", True), \
                    mock.patch.object(subject, "_ps_windows_api", return_value=(kernel, None)), \
                    mock.patch.object(subject, "_ps_absolute", return_value=root), \
                    mock.patch.object(subject, "_ps_check_components"), \
                    mock.patch.object(subject, "_ps_native_name", return_value="fixed"), \
                    mock.patch.object(ctypes, "get_last_error", return_value=code, create=True):
                if code in (1, 50):
                    self.assertFalse(subject.sync_directory(root))
                else:
                    with self.assertRaises(subject.PlatformError):
                        subject.sync_directory(root)


@unittest.skipUnless(subject.IS_WINDOWS, "Native Windows acceptance requires a Windows host")
class NativeWindowsContractTests(_FilesystemFixture, unittest.TestCase):
    def test_private_directory_rejects_everyone_inherit_only_full_control(self) -> None:
        kernel, security = subject._ps_windows_api()
        current = subject._ps_current_sid()
        descriptor, dacl = ctypes.c_void_p(), ctypes.c_void_p()
        sddl = "O:" + current + "D:P(A;OICI;FA;;;" + current + ")(A;OICIIO;FA;;;WD)"
        self.assertTrue(security.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            sddl, 1, ctypes.byref(descriptor), None))
        try:
            present, defaulted = ctypes.c_int(), ctypes.c_int()
            self.assertTrue(security.GetSecurityDescriptorDacl(descriptor,
                ctypes.byref(present), ctypes.byref(dacl), ctypes.byref(defaulted)))
            self.assertEqual(security.SetNamedSecurityInfoW(subject._ps_native_name(self.private),
                1, 0x80000004, None, None, dacl, None), 0)
            with self.assertRaises(subject.PlatformError):
                subject.verify_access(self.private, private=True)
            sidecar = self.private / "must-not-create-journal"
            self.assertFalse(sidecar.exists())
        finally:
            kernel.LocalFree(descriptor)

    def test_native_lookup_rejects_reserved_device_space_aliases(self) -> None:
        for name in ("CON .txt", "NUL .txt", "COM1 .x", "LPT1 .x", "COM¹ .txt"):
            with self.subTest(name=name), self.assertRaises(subject.PlatformError):
                subject.open_regular(self.private / name, os.O_CREAT | os.O_RDWR, private=True)

    def test_open_handle_prevents_renaming_until_closed(self) -> None:
        fd = subject.open_regular(self.path, os.O_RDWR, private=True)
        moved = self.private / "moved.txt"
        try:
            with self.assertRaises(PermissionError):
                self.path.rename(moved)
        finally:
            os.close(fd)
        self.path.rename(moved)
        self.assertEqual(moved.read_bytes(), b"original content")

    def test_private_acl_is_protected_and_public_acl_is_not_accepted_as_private(self) -> None:
        subject.verify_access(self.path, private=True)
        _, protected, entries = subject._ps_acl(self.path)
        self.assertTrue(protected)
        self.assertTrue(entries)
        self.assertTrue(all(kind != 0 or sid in subject._ps_trusted_sids()
                            for kind, mask, sid, flags in entries))
        subject.set_access(self.path, 0o644)
        with self.assertRaises(subject.PlatformError):
            subject.verify_access(self.path, private=True)
        self.assertEqual(subject.logical_mode(self.path, expected=0o644), 0o644)

    def test_inherited_sqlite_sidecar_is_not_treated_as_an_explicit_private_receipt(self) -> None:
        sidecar = self.private / "state.sqlite-wal"
        sidecar.write_bytes(b"synthetic WAL")
        with self.assertRaises(subject.PlatformError):
            subject.verify_access(sidecar, private=True)
        subject.verify_access(sidecar, private=True, inherited_from=self.private)

    def test_junction_parent_is_rejected_without_following_it(self) -> None:
        link = self.root / "junction"
        command = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/cmd.exe"
        result = subprocess.run([str(command), "/d", "/c",
            'mklink /J "' + str(link) + '" "' + str(self.private) + '"'],
            capture_output=True, text=True, timeout=10,
            env={"SystemRoot": str(command.parents[1])}, cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.addCleanup(lambda: link.rmdir() if link.exists() else None)
        self.assertTrue(subject.is_reparse(link))
        with self.assertRaises(subject.PlatformError):
            subject.open_regular(link / self.path.name, os.O_RDWR, private=True)

    def test_process_exit_releases_a_native_lock(self) -> None:
        process = subprocess.Popen([sys.executable, "-I", "-B", "-c", _CHILD, str(SOURCE),
                                   str(self.path), "exclusive", "hold"],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, cwd=self.root)
        ready = queue.Queue()
        reader = threading.Thread(target=lambda: ready.put(process.stdout.readline()), daemon=True)
        reader.start()
        try:
            self.assertEqual(ready.get(timeout=10).strip(), "acquired")
            self.assertEqual(self.child("shared").returncode, 73)
        finally:
            process.terminate()
            process.communicate(timeout=10)
        self.assertEqual(self.child("exclusive").returncode, 0)


if __name__ == "__main__":
    unittest.main()

"""Platform-specific paths, private filesystem access and ledger locking."""

from __future__ import annotations

from contextlib import contextmanager
import ctypes
import errno
from functools import lru_cache
import hashlib
import os
from pathlib import Path, PureWindowsPath
import re
import stat
import time
from typing import Iterator

IS_WINDOWS = os.name == "nt"
DWORD = ctypes.c_uint32
HANDLE = ctypes.c_void_p
FILE_ATTRIBUTE_REPARSE_POINT = 0x400
FILE_SHARE_READ_WRITE = 0x3
FILE_SHARE_DELETE = 0x4
OPEN_EXISTING = 3
FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
SE_DACL_PROTECTED = 0x1000
INVALID_HANDLE = ctypes.c_void_p(-1).value


def default_state_dir(home: Path | None = None) -> Path:
    """Return the local state location for the current or selected home.

    Windows uses the current profile's Local AppData, or the conventional
    AppData/Local directory when planning against an alternate home. The Unix
    location is retained for compatibility with existing ledgers.
    """
    user_home = Path.home()
    home = home or user_home
    if IS_WINDOWS:
        local_app_data = os.environ.get("LOCALAPPDATA") if home == user_home else None
        return (Path(local_app_data) if local_app_data else home / "AppData/Local") / "Constellation"
    return home / ".local/state/constellation"


def validate_windows_relative(value: str) -> None:
    """Reject noncanonical relative Windows paths and reserved file names.

    Args:
        value: A relative pathname using forward slash separators.

    Raises:
        ValueError: The path could select a drive, alternate stream, device or
            differently named filesystem entry.
    """
    native = PureWindowsPath(value)
    if not value or "\\" in value or native.drive or native.root:
        raise ValueError("Expected a canonical Windows-relative file path")
    for part in value.split("/"):
        if (not part or part in {".", ".."} or part[-1] in " ."
                or re.search(r'[<>:"|?*\x00-\x1f]', part)
                or re.fullmatch(
                    r"(?:CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|CLOCK\$|COM[1-9¹²³]|LPT[1-9¹²³])",
                    part.split(".", 1)[0].rstrip(" ."), re.IGNORECASE)):
            raise ValueError("Path contains a reserved or ambiguous Windows component")


def is_reparse(path: Path) -> bool:
    """Return whether an existing path is a symlink or other reparse point."""
    if IS_WINDOWS:
        return bool((_windows_attributes(path) or 0) & FILE_ATTRIBUTE_REPARSE_POINT)
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(info.st_mode)


class _Overlapped(ctypes.Structure):
    _fields_ = [("internal", ctypes.c_size_t), ("internal_high", ctypes.c_size_t),
                ("offset", DWORD), ("offset_high", DWORD), ("event", HANDLE)]


class _SecurityAttributes(ctypes.Structure):
    _fields_ = [("size", DWORD), ("descriptor", ctypes.c_void_p), ("inherit_handle", ctypes.c_int)]


class _SidAndAttributes(ctypes.Structure):
    _fields_ = [("sid", ctypes.c_void_p), ("attributes", DWORD)]


class _AclHeader(ctypes.Structure):
    _fields_ = [("revision", ctypes.c_ubyte), ("reserved", ctypes.c_ubyte),
                ("size", ctypes.c_uint16), ("count", ctypes.c_uint16),
                ("reserved2", ctypes.c_uint16)]


@lru_cache(maxsize=1)
def _windows_api():
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    security = ctypes.WinDLL("advapi32", use_last_error=True)
    pointer = ctypes.POINTER(ctypes.c_void_p)
    attributes = ctypes.POINTER(_SecurityAttributes)
    bindings = [
        (kernel, "GetCurrentProcess", [], HANDLE),
        (kernel, "CloseHandle", [HANDLE], ctypes.c_int),
        (kernel, "LocalFree", [ctypes.c_void_p], ctypes.c_void_p),
        (kernel, "GetLongPathNameW", [ctypes.c_wchar_p, ctypes.c_wchar_p, DWORD], DWORD),
        (kernel, "CreateFileW", [ctypes.c_wchar_p, DWORD, DWORD, attributes, DWORD, DWORD, HANDLE], HANDLE),
        (kernel, "CreateDirectoryW", [ctypes.c_wchar_p, attributes], ctypes.c_int),
        (kernel, "GetFileAttributesW", [ctypes.c_wchar_p], DWORD),
        (kernel, "LockFileEx", [HANDLE, DWORD, DWORD, DWORD, DWORD,
                               ctypes.POINTER(_Overlapped)], ctypes.c_int),
        (kernel, "UnlockFileEx", [HANDLE, DWORD, DWORD, DWORD,
                                 ctypes.POINTER(_Overlapped)], ctypes.c_int),
        (kernel, "MoveFileExW", [ctypes.c_wchar_p, ctypes.c_wchar_p, DWORD], ctypes.c_int),
        (security, "OpenProcessToken", [HANDLE, DWORD, ctypes.POINTER(HANDLE)], ctypes.c_int),
        (security, "GetTokenInformation", [HANDLE, ctypes.c_int, ctypes.c_void_p, DWORD,
                                           ctypes.POINTER(DWORD)], ctypes.c_int),
        (security, "ConvertSidToStringSidW", [ctypes.c_void_p, pointer], ctypes.c_int),
        (security, "ConvertStringSecurityDescriptorToSecurityDescriptorW",
         [ctypes.c_wchar_p, DWORD, pointer, ctypes.POINTER(DWORD)], ctypes.c_int),
        (security, "GetNamedSecurityInfoW", [ctypes.c_wchar_p, ctypes.c_int, DWORD, pointer,
                                             pointer, pointer, pointer, pointer], DWORD),
        (security, "GetSecurityDescriptorControl", [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint16),
                                                     ctypes.POINTER(DWORD)], ctypes.c_int),
        (security, "SetNamedSecurityInfoW", [ctypes.c_wchar_p, ctypes.c_int, DWORD, ctypes.c_void_p,
                                             ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p], DWORD),
        (security, "GetAce", [ctypes.c_void_p, DWORD, pointer], ctypes.c_int),
    ]
    for library, name, arguments, result in bindings:
        function = getattr(library, name)
        function.argtypes = arguments
        function.restype = result
    return kernel, security


def _windows_error(operation: str, code: int | None = None) -> OSError:
    code = ctypes.get_last_error() if code is None else code
    error = OSError(errno.EACCES, f"{operation} failed (Windows error {code})")
    error.winerror = code
    return error


def _sid_text(pointer: ctypes.c_void_p) -> str:
    kernel, security = _windows_api()
    text = ctypes.c_void_p()
    if not pointer or not security.ConvertSidToStringSidW(pointer, ctypes.byref(text)):
        raise _windows_error("Security identifier validation")
    try:
        return ctypes.wstring_at(text.value)
    finally:
        kernel.LocalFree(text)


@lru_cache(maxsize=1)
def _current_sid() -> str:
    kernel, security = _windows_api()
    token = HANDLE()
    if not security.OpenProcessToken(kernel.GetCurrentProcess(), 0x8, ctypes.byref(token)):
        raise _windows_error("Current-user token lookup")
    try:
        size = DWORD()
        security.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))
        if not size.value:
            raise _windows_error("Current-user token sizing")
        data = ctypes.create_string_buffer(size.value)
        if not security.GetTokenInformation(token, 1, data, size, ctypes.byref(size)):
            raise _windows_error("Current-user token lookup")
        return _sid_text(ctypes.cast(data, ctypes.POINTER(_SidAndAttributes)).contents.sid)
    finally:
        kernel.CloseHandle(token)


def _native_name(path: Path) -> str:
    return "\\\\?\\" + str(path)


def _windows_attributes(path: Path) -> int | None:
    kernel, _ = _windows_api()
    native = _native_name(path) if re.fullmatch(r"[A-Za-z]:", path.drive) and path.is_absolute() else str(path)
    attributes = kernel.GetFileAttributesW(native)
    if attributes != 0xFFFFFFFF:
        return attributes
    code = ctypes.get_last_error()
    if code in {2, 3}:
        return None
    raise _windows_error("Windows file attribute lookup", code)


def validate_windows_lookup(path: Path, *, allow_leaf_symlink: bool = False) -> Path:
    """Check a Windows path before resolution can hide aliases or traversal.

    Accepts local drive paths with optional missing descendants. It rejects
    junctions, other reparse points, and aliases generated by short file names.
    A Git operation can separately authorize a symbolic link at the exact leaf.
    """
    if not re.fullmatch(r"[A-Za-z]:", path.drive) or not path.is_absolute():
        raise ValueError("Managed Windows paths require an absolute local drive path")
    if path.parts[1:]:
        validate_windows_relative("/".join(path.parts[1:]))
    kernel, _ = _windows_api()
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        attributes = _windows_attributes(current)
        if attributes is None:
            break
        if attributes & FILE_ATTRIBUTE_REPARSE_POINT:
            if current != path or not allow_leaf_symlink or not current.is_symlink():
                raise ValueError(f"Managed path traverses a reparse point: {current}")
        name = _native_name(current)
        size = kernel.GetLongPathNameW(name, None, 0)
        if not size:
            raise _windows_error("Windows path name validation")
        actual = ctypes.create_unicode_buffer(size)
        written = kernel.GetLongPathNameW(name, actual, size)
        if not written or written >= size:
            raise _windows_error("Windows path name validation")
        if Path(actual.value).name.casefold() != part.casefold():
            raise ValueError(f"Managed path uses a Windows short-name alias: {current}")
    return path


def windows_executable(command: str, *, project: Path | None = None) -> str:
    """Resolve a Windows program without using the subprocess search order.

    Absolute .exe paths are explicit. A relative path with a separator is
    interpreted against the named project. Bare names resolve only through
    absolute PATH directories outside the current directory and project.
    """
    requested = Path(command)
    if requested.suffix and requested.suffix.casefold() != ".exe":
        raise ValueError("Use an explicit .exe interpreter for Windows checks and commands")
    if requested.is_absolute() or any(separator in command for separator in ("/", "\\")):
        if not requested.is_absolute():
            if project is None or requested.anchor:
                raise ValueError("Use an absolute local Windows executable path")
            requested = project / requested
        if requested.suffix.casefold() != ".exe":
            raise ValueError("Use a full .exe path for an explicit Windows command")
        validate_windows_lookup(requested)
        if not requested.is_file():
            raise FileNotFoundError(f"Windows executable is unavailable: {requested}")
        return str(requested)
    if requested.anchor:
        raise ValueError("A Windows executable name cannot select a drive")
    name = requested.name
    name = name if requested.suffix else name + ".exe"
    validate_windows_relative(name)
    current = Path.cwd().resolve()
    for entry in os.get_exec_path():
        directory = Path(entry.strip().removeprefix('"').removesuffix('"'))
        if (not directory.is_absolute() or directory == current
                or project is not None and directory.is_relative_to(project)):
            continue
        candidate = directory / name
        try:
            validate_windows_lookup(candidate)
            if candidate.is_file():
                return str(candidate)
        except (OSError, ValueError):
            continue
    raise FileNotFoundError(
        f"Windows executable {name} is unavailable in absolute PATH directories; use a trusted .exe path")


def git_executable(*, project: Path | None = None) -> str:
    """Select Git without consulting the Windows current-directory search."""
    if not IS_WINDOWS:
        return "git"
    configured = os.environ.get("CONSTELLATION_GIT")
    if configured:
        path = Path(configured)
        if not path.is_absolute() or path.name.casefold() != "git.exe":
            raise ValueError("CONSTELLATION_GIT must be the absolute local path to git.exe")
        return windows_executable(configured)
    return windows_executable("git.exe", project=project)


@contextmanager
def _directory_security() -> Iterator[_SecurityAttributes]:
    kernel, security = _windows_api()
    user_sid = _current_sid()
    entries = "".join(f"(A;OICI;FA;;;{sid})" for sid in (user_sid, "SY", "BA"))
    descriptor = ctypes.c_void_p()
    if not security.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            f"O:{user_sid}D:P{entries}", 1, ctypes.byref(descriptor), None):
        raise _windows_error("Private directory access descriptor")
    try:
        yield _SecurityAttributes(ctypes.sizeof(_SecurityAttributes), descriptor.value, 0)
    finally:
        kernel.LocalFree(descriptor)


@contextmanager
def _windows_dacl(path: Path) -> Iterator[tuple[str, bool, ctypes.c_void_p]]:
    kernel, security = _windows_api()
    owner, dacl, descriptor = ctypes.c_void_p(), ctypes.c_void_p(), ctypes.c_void_p()
    code = security.GetNamedSecurityInfoW(_native_name(path), 1, 0x5, ctypes.byref(owner),
        None, ctypes.byref(dacl), None, ctypes.byref(descriptor))
    if code:
        raise _windows_error("Access-control lookup", code)
    try:
        control, revision = ctypes.c_uint16(), DWORD()
        if not owner.value or not dacl.value:
            raise OSError(f"Managed path has no explicit owner or discretionary ACL: {path}")
        if not security.GetSecurityDescriptorControl(descriptor, ctypes.byref(control),
                                                       ctypes.byref(revision)):
            raise _windows_error("Access-control metadata lookup")
        yield _sid_text(owner), bool(control.value & SE_DACL_PROTECTED), dacl
    finally:
        kernel.LocalFree(descriptor)


def _verify_windows_private(path: Path, *, directory: bool) -> None:
    _, security = _windows_api()
    user_sid = _current_sid()
    trusted = {user_sid, "S-1-5-18", "S-1-5-32-544"}
    owner_mask = 0
    with _windows_dacl(path) as (owner, protected, dacl):
        if owner not in trusted or (directory and not protected):
            raise OSError(f"Managed path has an unsafe Windows owner or access policy: {path}")
        count = ctypes.cast(dacl, ctypes.POINTER(_AclHeader)).contents.count
        for index in range(count):
            entry = ctypes.c_void_p()
            if not security.GetAce(dacl, index, ctypes.byref(entry)):
                raise _windows_error("Access-control entry lookup")
            kind = ctypes.c_ubyte.from_address(entry.value).value
            flags = ctypes.c_ubyte.from_address(entry.value + 1).value
            size = ctypes.c_uint16.from_address(entry.value + 2).value
            if kind not in {0, 1} or size < 12:
                raise OSError(f"Managed path has an unsupported access-control entry: {path}")
            mask = DWORD.from_address(entry.value + 4).value
            sid = _sid_text(ctypes.c_void_p(entry.value + 8))
            applies = not flags & 0x8
            if kind == 0 and mask and sid not in trusted and (applies or directory and flags & 0x3):
                raise OSError(f"Managed path grants Windows access to another principal: {path}")
            if applies and sid == user_sid:
                if kind == 1 and mask:
                    raise OSError(f"Managed Windows path denies its owner access: {path}")
                if kind == 0:
                    owner_mask |= mask
    if not (owner_mask & 0x10000000 or owner_mask & 0x001F01FF == 0x001F01FF):
        raise OSError(f"Managed Windows path does not give its owner full control: {path}")


def secure_mkdir(path: Path) -> None:
    """Create private state directories, including missing parents.

    On Windows create each missing directory with its private DACL already
    assigned. Verify the target directory's DACL and leave existing ancestors
    alone. On Unix retain 0700 and the existing behavior for managed paths.
    """
    if not IS_WINDOWS:
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        if path.is_symlink():
            raise OSError(f"Private state requires a regular directory: {path}")
        path.chmod(0o700)
        return

    validate_windows_lookup(path)
    if not path.parent.exists():
        secure_mkdir(path.parent)
    kernel, _ = _windows_api()
    with _directory_security() as attributes:
        if not kernel.CreateDirectoryW(_native_name(path), ctypes.byref(attributes)):
            code = ctypes.get_last_error()
            if code != 183:
                raise _windows_error("Private directory creation", code)
    if not path.is_dir() or is_reparse(path):
        raise OSError(f"Private state requires a regular directory: {path}")
    _verify_windows_private(path, directory=True)


def verify_windows_private_entry(path: Path) -> None:
    """Check that a native Windows entry is safe to retain in private state.

    Existing entries may inherit their ACL. Only the current user, System
    and Administrators may have access. Directory descendants need their own
    checks before being moved into a private receipt.
    """
    validate_windows_lookup(path)
    metadata = path.lstat()
    if not (stat.S_ISDIR(metadata.st_mode)
            or (stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1)):
        raise OSError(f"Private retention requires a regular directory or singly linked file: {path}")
    _verify_windows_private(path, directory=False)


def windows_copy_dacl(source: Path, destination: Path) -> None:
    """Apply a native Windows file's DACL to a replacement in the same location.

    Use after promotion to the original directory so any inherited entries
    derive from the correct parent. The original file remains the recovery copy.
    """
    validate_windows_lookup(source)
    validate_windows_lookup(destination)
    _, security = _windows_api()
    with _windows_dacl(source) as (owner, protected, dacl), _windows_dacl(destination) as (new_owner, _, _):
        if owner != new_owner:
            raise OSError(f"Replacement would change the Windows file owner: {destination}")
        flags = 0x80000000 if protected else 0x20000000
        code = security.SetNamedSecurityInfoW(_native_name(destination), 1, flags | 0x4,
                                              None, None, dacl, None)
        if code:
            raise _windows_error("Native replacement access assignment", code)


def windows_dacl_fingerprint(path: Path) -> str:
    """Hash the owner, DACL protection and ordered access entries."""
    validate_windows_lookup(path)
    _, security = _windows_api()
    with _windows_dacl(path) as (owner, protected, dacl):
        digest = hashlib.sha256(f"{owner}:{protected}".encode("ascii"))
        count = ctypes.cast(dacl, ctypes.POINTER(_AclHeader)).contents.count
        for index in range(count):
            entry = ctypes.c_void_p()
            if not security.GetAce(dacl, index, ctypes.byref(entry)):
                raise _windows_error("Access-control entry lookup")
            size = ctypes.c_uint16.from_address(entry.value + 2).value
            digest.update(ctypes.string_at(entry.value, size))
        return digest.hexdigest()


@contextmanager
def ledger_lock(path: Path) -> Iterator[None]:
    """Hold the platform's ledger lock for the duration of a task update."""
    if not IS_WINDOWS:
        import fcntl

        with path.open("a", encoding="utf-8") as handle:
            os.chmod(path, 0o600)
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return

    import msvcrt

    validate_windows_lookup(path)
    with path.open("a+b") as stream:
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1 or is_reparse(path):
            raise OSError(f"Ledger lock must be a regular file: {path}")
        _verify_windows_private(path, directory=False)
        kernel, _ = _windows_api()
        handle, offset = msvcrt.get_osfhandle(stream.fileno()), _Overlapped()
        # Lock byte zero even on a new empty file. No content is stored there.
        while not kernel.LockFileEx(handle, 0x3, 0, 1, 0, ctypes.byref(offset)):
            code = ctypes.get_last_error()
            if code not in {32, 33}:
                raise _windows_error("Ledger lock acquisition", code)
            time.sleep(0.01)
        try:
            yield
        finally:
            if not kernel.UnlockFileEx(handle, 0, 1, 0, ctypes.byref(offset)):
                raise _windows_error("Ledger lock release")


def read_ledger_record(path: Path) -> str:
    """Read an atomic snapshot, allowing a Windows writer to replace the name."""
    if not IS_WINDOWS:
        return path.read_text(encoding="utf-8")

    import msvcrt

    validate_windows_lookup(path)
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise OSError(f"Ledger record must be a regular file: {path}")
    _verify_windows_private(path, directory=False)
    kernel, _ = _windows_api()
    handle = kernel.CreateFileW(_native_name(path), 0x80000000,
        FILE_SHARE_READ_WRITE | FILE_SHARE_DELETE, None, OPEN_EXISTING, FILE_FLAG_OPEN_REPARSE_POINT, None)
    if handle == INVALID_HANDLE:
        code = ctypes.get_last_error()
        if code in {2, 3}:
            raise FileNotFoundError(path)
        raise _windows_error("Ledger record open", code)
    try:
        descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
    except BaseException:
        kernel.CloseHandle(handle)
        raise
    with os.fdopen(descriptor, "r", encoding="utf-8") as stream:
        return stream.read()


def replace_ledger_record(temporary: Path, destination: Path) -> None:
    """Publish an already flushed record using an atomic same-directory rename.

    A Windows process may hold a destination without delete sharing. Retry
    transient sharing conflicts briefly, retaining the previous record on failure.
    Windows requests write-through on the rename. Unix fsyncs the parent.
    """
    if not IS_WINDOWS:
        os.replace(temporary, destination)
        directory = os.open(destination.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        return

    validate_windows_lookup(destination)
    if destination.exists():
        metadata = destination.lstat()
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise OSError(f"Ledger record must be a regular file: {destination}")
        _verify_windows_private(destination, directory=False)
    kernel, _ = _windows_api()
    deadline = time.monotonic() + 2.0
    while not kernel.MoveFileExW(_native_name(temporary), _native_name(destination), 0x9):
        code = ctypes.get_last_error()
        if code not in {5, 32, 33} or time.monotonic() >= deadline:
            raise _windows_error("Ledger record replacement", code)
        time.sleep(0.02)

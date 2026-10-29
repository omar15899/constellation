"""Filesystem primitives shared by the runtime and the standalone hook bootstrap.

POSIX keeps its native file modes and flock semantics. Windows uses handle locks
and protected DACLs; Unix mode values are package metadata there, never an ACL.
The module has no package imports and initializes Win32 bindings only when used,
so the builder may embed these exact definitions in the verification bootstrap.
"""
from __future__ import annotations

from contextlib import contextmanager
import ctypes
import errno
from functools import lru_cache
import hashlib
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import stat
import sys
import time
from typing import Iterable, Iterator

IS_WINDOWS = os.name == "nt"


class PlatformError(OSError):
    """A required filesystem guarantee could not be established."""


_ps_DWORD = ctypes.c_uint32
_ps_WORD = ctypes.c_uint16
_ps_BYTE = ctypes.c_ubyte
_ps_HANDLE = ctypes.c_void_p


class _ps_OVERLAPPED(ctypes.Structure):
    _fields_ = [("Internal", ctypes.c_size_t), ("InternalHigh", ctypes.c_size_t),
                ("Offset", _ps_DWORD), ("OffsetHigh", _ps_DWORD), ("hEvent", _ps_HANDLE)]


class _ps_SECURITY_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("nLength", _ps_DWORD), ("lpSecurityDescriptor", ctypes.c_void_p),
                ("bInheritHandle", ctypes.c_int)]


class _ps_FILETIME(ctypes.Structure):
    _fields_ = [("low", _ps_DWORD), ("high", _ps_DWORD)]


class _ps_FILE_INFORMATION(ctypes.Structure):
    _fields_ = [("attributes", _ps_DWORD), ("created", _ps_FILETIME),
                ("accessed", _ps_FILETIME), ("written", _ps_FILETIME),
                ("volume", _ps_DWORD), ("size_high", _ps_DWORD),
                ("size_low", _ps_DWORD), ("links", _ps_DWORD),
                ("index_high", _ps_DWORD), ("index_low", _ps_DWORD)]


class _ps_ACL_HEADER(ctypes.Structure):
    _fields_ = [("revision", _ps_BYTE), ("reserved", _ps_BYTE),
                ("size", _ps_WORD), ("count", _ps_WORD), ("reserved2", _ps_WORD)]


class _ps_ACE_HEADER(ctypes.Structure):
    _fields_ = [("type", _ps_BYTE), ("flags", _ps_BYTE), ("size", _ps_WORD)]


class _ps_SID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("sid", ctypes.c_void_p), ("attributes", _ps_DWORD)]


@lru_cache(maxsize=1)
def _ps_windows_api():
    if not IS_WINDOWS:
        raise PlatformError("Win32 filesystem operations require native Windows.")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    security = ctypes.WinDLL("advapi32", use_last_error=True)
    pvoid = ctypes.POINTER(ctypes.c_void_p)
    bindings = [
        (kernel, "GetCurrentProcess", [], _ps_HANDLE),
        (kernel, "CloseHandle", [_ps_HANDLE], ctypes.c_int),
        (kernel, "LocalFree", [ctypes.c_void_p], ctypes.c_void_p),
        (kernel, "CreateFileW", [ctypes.c_wchar_p, _ps_DWORD, _ps_DWORD,
            ctypes.POINTER(_ps_SECURITY_ATTRIBUTES), _ps_DWORD, _ps_DWORD, _ps_HANDLE], _ps_HANDLE),
        (kernel, "CreateDirectoryW", [ctypes.c_wchar_p,
            ctypes.POINTER(_ps_SECURITY_ATTRIBUTES)], ctypes.c_int),
        (kernel, "GetFileInformationByHandle", [_ps_HANDLE,
            ctypes.POINTER(_ps_FILE_INFORMATION)], ctypes.c_int),
        (kernel, "LockFileEx", [_ps_HANDLE, _ps_DWORD, _ps_DWORD, _ps_DWORD,
            _ps_DWORD, ctypes.POINTER(_ps_OVERLAPPED)], ctypes.c_int),
        (kernel, "UnlockFileEx", [_ps_HANDLE, _ps_DWORD, _ps_DWORD,
            _ps_DWORD, ctypes.POINTER(_ps_OVERLAPPED)], ctypes.c_int),
        (kernel, "FlushFileBuffers", [_ps_HANDLE], ctypes.c_int),
        (kernel, "MoveFileExW", [ctypes.c_wchar_p, ctypes.c_wchar_p, _ps_DWORD], ctypes.c_int),
        (security, "OpenProcessToken", [_ps_HANDLE, _ps_DWORD,
            ctypes.POINTER(_ps_HANDLE)], ctypes.c_int),
        (security, "GetTokenInformation", [_ps_HANDLE, ctypes.c_int, ctypes.c_void_p,
            _ps_DWORD, ctypes.POINTER(_ps_DWORD)], ctypes.c_int),
        (security, "ConvertSidToStringSidW", [ctypes.c_void_p, pvoid], ctypes.c_int),
        (security, "ConvertStringSecurityDescriptorToSecurityDescriptorW",
            [ctypes.c_wchar_p, _ps_DWORD, pvoid, ctypes.POINTER(_ps_DWORD)], ctypes.c_int),
        (security, "ConvertSecurityDescriptorToStringSecurityDescriptorW",
            [ctypes.c_void_p, _ps_DWORD, _ps_DWORD, pvoid, ctypes.POINTER(_ps_DWORD)], ctypes.c_int),
        (security, "GetSecurityDescriptorDacl", [ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_int), pvoid, ctypes.POINTER(ctypes.c_int)], ctypes.c_int),
        (security, "GetSecurityDescriptorControl", [ctypes.c_void_p,
            ctypes.POINTER(_ps_WORD), ctypes.POINTER(_ps_DWORD)], ctypes.c_int),
        (security, "GetNamedSecurityInfoW", [ctypes.c_wchar_p, ctypes.c_int, _ps_DWORD,
            pvoid, pvoid, pvoid, pvoid, pvoid], _ps_DWORD),
        (security, "SetNamedSecurityInfoW", [ctypes.c_wchar_p, ctypes.c_int, _ps_DWORD,
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p], _ps_DWORD),
        (security, "GetAce", [ctypes.c_void_p, _ps_DWORD, pvoid], ctypes.c_int),
    ]
    for library, name, arguments, result in bindings:
        function = getattr(library, name)
        function.argtypes = arguments
        function.restype = result
    return kernel, security


def _ps_raise_windows(operation: str, code: int | None = None) -> None:
    code = ctypes.get_last_error() if code is None else code
    error = PlatformError(errno.EACCES, operation + " failed (Windows error " + str(code) + ").")
    error.winerror = code
    raise error


def _ps_sid_text(pointer: ctypes.c_void_p) -> str:
    kernel, security = _ps_windows_api()
    text_pointer = ctypes.c_void_p()
    if not pointer or not security.ConvertSidToStringSidW(pointer, ctypes.byref(text_pointer)):
        _ps_raise_windows("Security identifier validation")
    try:
        return ctypes.wstring_at(text_pointer.value)
    finally:
        kernel.LocalFree(text_pointer)


@lru_cache(maxsize=1)
def _ps_current_sid() -> str:
    kernel, security = _ps_windows_api()
    token = _ps_HANDLE()
    if not security.OpenProcessToken(kernel.GetCurrentProcess(), 0x0008, ctypes.byref(token)):
        _ps_raise_windows("Current-user token lookup")
    try:
        size = _ps_DWORD()
        security.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))
        if not size.value:
            _ps_raise_windows("Current-user token sizing")
        buffer = ctypes.create_string_buffer(size.value)
        if not security.GetTokenInformation(token, 1, buffer, size, ctypes.byref(size)):
            _ps_raise_windows("Current-user token lookup")
        return _ps_sid_text(ctypes.cast(buffer, ctypes.POINTER(_ps_SID_AND_ATTRIBUTES)).contents.sid)
    finally:
        kernel.CloseHandle(token)


def _ps_trusted_sids() -> frozenset[str]:
    return frozenset({_ps_current_sid(), "S-1-5-18", "S-1-5-32-544"})


def validate_windows_relative(value: str) -> str:
    """Validate a canonical relative protocol path against Windows aliases.

    Args:
        value: A nonempty forward-slash relative path, without dot components.

    Returns:
        The unchanged value. This function is platform independent for tests.

    Raises:
        PlatformError: Drive/UNC/device syntax, ADS, reserved names, forbidden
            characters, backslashes, or trailing dot/space aliases are present.
    """
    if not isinstance(value, str) or not value or "\\" in value:
        raise PlatformError("Expected a canonical Windows-safe relative path.")
    path = PurePosixPath(value)
    win = PureWindowsPath(value)
    if (path.is_absolute() or win.drive or win.root or path.as_posix() != value
            or any(part in {"", ".", ".."} for part in value.split("/"))):
        raise PlatformError("Expected a canonical Windows-safe relative path.")
    for part in path.parts:
        if (part[-1:] in {".", " "} or re.search(r'[<>:"|?*\x00-\x1f]', part)
                or re.fullmatch(r"(?:CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|CLOCK\$|COM[1-9¹²³]|LPT[1-9¹²³])",
                                part.split(".", 1)[0].rstrip(" ."), re.IGNORECASE)):
            raise PlatformError("Path contains a reserved or ambiguous Windows component.")
    return value


def is_reparse(path: Path) -> bool:
    """Return whether an existing path is a symlink or any Windows reparse point."""
    try:
        info = Path(path).lstat()
    except FileNotFoundError:
        return False
    return (stat.S_ISLNK(info.st_mode)
            or bool(getattr(info, "st_file_attributes", 0) & 0x00000400))


def _ps_absolute(path: Path) -> Path:
    original = Path(path)
    if IS_WINDOWS:
        lookup = PureWindowsPath(str(path))
        if ((lookup.drive and not lookup.root) or (lookup.root and not lookup.drive)
                or lookup.drive.startswith("\\\\")):
            raise PlatformError("Managed Windows lookup contains an ambiguous drive or namespace.")
    supplied = original.absolute()
    if ".." in original.parts or ".." in supplied.parts:
        raise PlatformError("Managed paths cannot contain parent traversal.")
    if IS_WINDOWS:
        if not re.fullmatch(r"[A-Za-z]:", supplied.drive) or not supplied.is_absolute():
            raise PlatformError("Managed Windows paths require a local absolute drive path.")
        if supplied.parts[1:]:
            validate_windows_relative("/".join(supplied.parts[1:]))
    return supplied


def _ps_native_name(path: Path) -> str:
    return "\\\\?\\" + str(_ps_absolute(path))


def _ps_check_components(path: Path) -> None:
    supplied = _ps_absolute(path)
    current = Path(supplied.anchor)
    for part in supplied.parts[1:]:
        current /= part
        if is_reparse(current):
            raise PlatformError("Managed path contains a symbolic link or reparse point.")


def validate_lookup(path: Path) -> Path:
    """Validate an original filesystem lookup before resolving any aliases.

    This checks path syntax and all existing components for symlinks/reparse
    points. It does not impose a private or package ACL on a project directory.
    Missing final components are permitted for a subsequent exclusive creation.
    """
    supplied = _ps_absolute(path)
    _ps_check_components(supplied)
    return supplied


def _ps_artifact_path(root: Path, value: str) -> Path:
    if (not isinstance(value, str) or not value
            or PurePosixPath(value).is_absolute()
            or PurePosixPath(value).as_posix() != value
            or any(part in {"", ".", ".."} for part in value.split("/"))):
        raise PlatformError("Artifact identity requires a canonical relative path.")
    if IS_WINDOWS:
        validate_windows_relative(value)
    path = root / value
    _ps_check_components(path)
    return path


def _ps_artifact_identity(path: Path) -> tuple[int, int] | None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    if is_reparse(path):
        raise PlatformError("Artifact identity cannot follow a reparse point.")
    return (info.st_dev, info.st_ino) if stat.S_ISREG(info.st_mode) else None


def same_artifact(root: Path, left: str, right: str) -> bool:
    """Compare protocol names and existing physical regular-file identities.

    Windows names also compare case-insensitively before a file exists. On other
    platforms only actual file identity detects case aliases, preserving distinct
    case-sensitive files. Hardlinks share identity; links/reparse points are
    rejected rather than followed. The lookup root is checked before resolving.
    """
    root = validate_lookup(root)
    a, b = _ps_artifact_path(root, left), _ps_artifact_path(root, right)
    if left == right or IS_WINDOWS and left.casefold() == right.casefold():
        return True
    identity = _ps_artifact_identity(a)
    return identity is not None and identity == _ps_artifact_identity(b)


def ensure_distinct_paths(root: Path, paths: Iterable[str]) -> None:
    """Reject name/case/physical aliases within one declared artifact set."""
    if isinstance(paths, (str, bytes)):
        raise PlatformError("Artifact paths must be an iterable of distinct names.")
    root = validate_lookup(root)
    names, identities = set(), set()
    for value in paths:
        path = _ps_artifact_path(root, value)
        name = value.casefold() if IS_WINDOWS else value
        identity = _ps_artifact_identity(path)
        if name in names or identity is not None and identity in identities:
            raise PlatformError("Artifact set contains duplicate or physically aliased paths.")
        names.add(name)
        if identity is not None:
            identities.add(identity)


def _ps_handle_info(handle: int) -> _ps_FILE_INFORMATION:
    kernel, _ = _ps_windows_api()
    info = _ps_FILE_INFORMATION()
    if not kernel.GetFileInformationByHandle(handle, ctypes.byref(info)):
        _ps_raise_windows("File-handle identity lookup")
    if info.attributes & 0x00000400:
        raise PlatformError("An opened resource is a reparse point.")
    return info


@contextmanager
def _ps_guard_parents(path: Path) -> Iterator[None]:
    """Hold no-delete directory handles while a final Windows component opens."""
    kernel, _ = _ps_windows_api()
    handles = []
    supplied = _ps_absolute(path)
    current = Path(supplied.anchor)
    try:
        for part in (None, *supplied.parts[1:-1]):
            if part is not None:
                current /= part
            handle = kernel.CreateFileW(_ps_native_name(current), 0x00020080, 0x3,
                                       None, 3, 0x02200000, None)
            if handle == ctypes.c_void_p(-1).value:
                _ps_raise_windows("Parent directory pinning")
            handles.append(handle)
            info = _ps_handle_info(handle)
            if not info.attributes & 0x10:
                raise PlatformError("Managed parent is not a directory.")
        yield
    finally:
        for handle in reversed(handles):
            kernel.CloseHandle(handle)


def _ps_acl(path: Path) -> tuple[str, bool, list[tuple[int, int, str, int]]]:
    kernel, security = _ps_windows_api()
    owner, dacl, descriptor = ctypes.c_void_p(), ctypes.c_void_p(), ctypes.c_void_p()
    result = security.GetNamedSecurityInfoW(_ps_native_name(path), 1, 0x5,
        ctypes.byref(owner), None, ctypes.byref(dacl), None, ctypes.byref(descriptor))
    if result:
        _ps_raise_windows("Access-control lookup", result)
    try:
        if not owner.value or not dacl.value:
            raise PlatformError("Resource has no explicit owner or discretionary ACL.")
        control, revision = _ps_WORD(), _ps_DWORD()
        if not security.GetSecurityDescriptorControl(descriptor, ctypes.byref(control),
                                                       ctypes.byref(revision)):
            _ps_raise_windows("Access-control metadata validation")
        entries = []
        header = ctypes.cast(dacl, ctypes.POINTER(_ps_ACL_HEADER)).contents
        for number in range(header.count):
            ace = ctypes.c_void_p()
            if not security.GetAce(dacl, number, ctypes.byref(ace)):
                _ps_raise_windows("Access-control entry lookup")
            entry = ctypes.cast(ace, ctypes.POINTER(_ps_ACE_HEADER)).contents
            if entry.type not in {0, 1} or entry.size < 12:
                raise PlatformError("Resource has an unsupported access-control entry.")
            mask = ctypes.c_uint32.from_address(ace.value + 4).value
            sid = _ps_sid_text(ctypes.c_void_p(ace.value + 8))
            entries.append((entry.type, mask, sid, entry.flags))
        return _ps_sid_text(owner), bool(control.value & 0x1000), entries
    finally:
        kernel.LocalFree(descriptor)


def verify_access(path: Path, *, private: bool = False,
                  inherited_from: Path | None = None) -> None:
    """Reject unsafe access, links and multiply linked regular resources.

    Private Windows objects must have a protected DACL granting access only to
    the current user, SYSTEM or Administrators. Public package objects may grant
    read/execute to others, but may not grant them mutation or ownership rights.
    Unsupported ACL forms fail closed. Stronger private ACLs are valid for a
    public package. A SQLite sidecar may opt into inherited protection only as a
    direct child of an explicitly verified protected private parent; its own ACL
    must still grant access solely to trusted principals. POSIX private modes
    are exactly 0600 for files, 0700 for dirs.
    """
    path = _ps_absolute(path)
    if inherited_from is not None:
        parent = _ps_absolute(inherited_from)
        if not private or path.parent != parent:
            raise PlatformError("Inherited protection requires a direct private parent.")
        verify_access(parent, private=True)
    _ps_check_components(path)
    info = path.lstat()
    if is_reparse(path) or not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
        raise PlatformError("Resource must be a regular file or directory without reparse points.")
    if stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
        raise PlatformError("Managed files must have exactly one hard link.")
    if not IS_WINDOWS:
        mode = stat.S_IMODE(info.st_mode)
        expected = 0o700 if stat.S_ISDIR(info.st_mode) else 0o600
        if (private and mode != expected) or (not private and mode & 0o022):
            raise PlatformError("Resource permissions do not meet the access policy.")
        return
    owner, protected, entries = _ps_acl(path)
    trusted = _ps_trusted_sids()
    if owner not in trusted or (private and not protected and inherited_from is None):
        raise PlatformError("Resource owner or protected access policy is unsafe.")
    mutation = 0x500D0156  # GENERIC_ALL/WRITE, DELETE, WRITE_DAC/OWNER, file/dir writes.
    current_allowed = 0
    for kind, mask, sid, flags in entries:
        applies_here = not bool(flags & 0x08)
        propagates = stat.S_ISDIR(info.st_mode) and bool(flags & 0x03)
        if not applies_here and not propagates:
            continue
        if kind == 1:
            if private and applies_here and sid == _ps_current_sid() and mask:
                raise PlatformError("Private access denies its current owner.")
            continue
        if applies_here and sid == _ps_current_sid():
            current_allowed |= mask
        if sid not in trusted and (private and mask or mask & mutation):
            raise PlatformError("Resource grants unsafe access to another principal or its future children.")
    if private and not (current_allowed & 0x10000000 or current_allowed & 0x001F01FF == 0x001F01FF):
        raise PlatformError("Private access does not explicitly grant the current user full control.")


def access_fingerprint(path: Path) -> str:
    """Hash stable permission metadata without exposing account identifiers.

    Windows binds the owner and complete DACL SDDL, including protection,
    inheritance flags and ACE order. POSIX binds the actual mode bits.
    """
    path = _ps_absolute(path)
    _ps_check_components(path)
    if not IS_WINDOWS:
        return hashlib.sha256(str(stat.S_IMODE(path.lstat().st_mode)).encode("ascii")).hexdigest()
    kernel, security = _ps_windows_api()
    descriptor, text_pointer = ctypes.c_void_p(), ctypes.c_void_p()
    result = security.GetNamedSecurityInfoW(_ps_native_name(path), 1, 0x5,
                                           None, None, None, None, ctypes.byref(descriptor))
    if result:
        _ps_raise_windows("Access fingerprint lookup", result)
    try:
        if not security.ConvertSecurityDescriptorToStringSecurityDescriptorW(
                descriptor, 1, 0x5, ctypes.byref(text_pointer), None):
            _ps_raise_windows("Access fingerprint conversion")
        attributes = getattr(path.lstat(), "st_file_attributes", 0) & 0x00000411
        policy = ctypes.wstring_at(text_pointer.value) + "|attributes=" + str(attributes)
        return hashlib.sha256(policy.encode("utf-8")).hexdigest()
    finally:
        if text_pointer.value:
            kernel.LocalFree(text_pointer)
        kernel.LocalFree(descriptor)


@contextmanager
def _ps_security(mode: int, *, directory: bool) -> Iterator[_ps_SECURITY_ATTRIBUTES]:
    kernel, security = _ps_windows_api()
    sid = _ps_current_sid()
    inheritance = "OICI" if directory else ""
    aces = "".join("(A;" + inheritance + ";FA;;;" + principal + ")"
                   for principal in (sid, "SY", "BA"))
    if mode & 0o077:
        aces += "(A;" + inheritance + ";" + ("FRFX" if mode & 0o111 else "FR") + ";;;WD)"
    sddl = "O:" + sid + "D:P" + aces
    descriptor = ctypes.c_void_p()
    if not security.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            sddl, 1, ctypes.byref(descriptor), None):
        _ps_raise_windows("Private access descriptor construction")
    try:
        attributes = _ps_SECURITY_ATTRIBUTES(ctypes.sizeof(_ps_SECURITY_ATTRIBUTES),
                                              descriptor.value, 0)
        yield attributes
    finally:
        kernel.LocalFree(descriptor)


def set_access(path: Path, mode: int) -> None:
    """Set owned-object permissions using POSIX modes or a protected Windows ACL."""
    if mode not in {0o600, 0o700, 0o644, 0o755}:
        raise PlatformError("Unsupported managed permission mode.")
    path = _ps_absolute(path)
    _ps_check_components(path)
    info = path.lstat()
    if (is_reparse(path) or not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode))
            or stat.S_ISREG(info.st_mode) and info.st_nlink != 1):
        raise PlatformError("Cannot assign access to a linked or special resource.")
    if not IS_WINDOWS:
        os.chmod(path, mode)
    else:
        _, security = _ps_windows_api()
        with _ps_security(mode, directory=stat.S_ISDIR(info.st_mode)) as attributes:
            present, defaulted, dacl = ctypes.c_int(), ctypes.c_int(), ctypes.c_void_p()
            if not security.GetSecurityDescriptorDacl(attributes.lpSecurityDescriptor,
                    ctypes.byref(present), ctypes.byref(dacl), ctypes.byref(defaulted)) or not present.value or not dacl.value:
                _ps_raise_windows("Access descriptor extraction")
            result = security.SetNamedSecurityInfoW(_ps_native_name(path), 1, 0x80000004,
                                                     None, None, dacl, None)
            if result:
                _ps_raise_windows("Protected access assignment", result)
    verify_access(path, private=not bool(mode & 0o077))


def logical_mode(path: Path, expected: int | None = None) -> int:
    """Return POSIX permissions, or verified logical package permissions on Windows.

    Windows cannot infer a Unix executable bit from stat(). With an expected
    manifest mode it validates the corresponding ACL and returns that logical
    mode; without one, canonical sources use 0644 for files and 0755 for dirs.
    """
    if expected is not None and expected not in {0o600, 0o700, 0o644, 0o755}:
        raise PlatformError("Invalid logical permission mode.")
    if not IS_WINDOWS:
        return stat.S_IMODE(Path(path).lstat().st_mode)
    mode = expected if expected is not None else (0o755 if Path(path).is_dir() else 0o644)
    verify_access(path, private=not bool(mode & 0o077))
    return mode


def secure_mkdir(path: Path, mode: int = 0o700, *, parents: bool = False,
                 exist_ok: bool = False) -> None:
    """Create directories with private ACLs atomically on Windows.

    Existing ancestors are checked for reparse points without changing their
    permissions. An existing final directory is validated, never silently fixed.
    """
    if mode not in {0o700, 0o755}:
        raise PlatformError("Managed directories require mode 0700 or 0755.")
    path = _ps_absolute(path)
    _ps_check_components(path)
    if parents and not path.parent.exists():
        secure_mkdir(path.parent, mode, parents=True, exist_ok=True)
    if not IS_WINDOWS:
        path.mkdir(mode=mode, exist_ok=exist_ok)
    else:
        kernel, _ = _ps_windows_api()
        with _ps_guard_parents(path), _ps_security(mode, directory=True) as attributes:
            if not kernel.CreateDirectoryW(_ps_native_name(path), ctypes.byref(attributes)):
                code = ctypes.get_last_error()
                if code != 183 or not exist_ok:
                    if code == 183:
                        raise FileExistsError(errno.EEXIST, "Destination already exists.", str(path))
                    _ps_raise_windows("Secure directory creation", code)
    if not path.is_dir() or is_reparse(path):
        raise PlatformError("Managed directory is linked or invalid.")
    verify_access(path, private=mode == 0o700)


def open_regular(path: Path, flags: int, mode: int = 0o600, *, private: bool = False) -> int:
    """Open a singly linked file without following a final link or reparse point.

    Windows pins each parent directory until the no-follow final handle is open,
    denies delete-sharing and creates new files with their DACL already applied.
    Destructive truncation happens only after handle/path identity validation.
    The returned non-inheritable descriptor belongs to the caller.
    """
    path = _ps_absolute(path)
    _ps_check_components(path)
    if mode not in {0o600, 0o644, 0o755}:
        raise PlatformError("Invalid regular-file permission mode.")
    try:
        before = path.lstat()
    except FileNotFoundError:
        before = None
    if before is not None and (is_reparse(path) or not stat.S_ISREG(before.st_mode)
                               or before.st_nlink != 1):
        raise PlatformError("Managed resource is linked or not a regular file.")
    descriptor = None
    try:
        if not IS_WINDOWS:
            safe_flags = (flags & ~os.O_TRUNC) | getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(path, safe_flags, mode)
        else:
            import msvcrt
            kernel, _ = _ps_windows_api()
            access_bits = flags & (os.O_WRONLY | os.O_RDWR)
            desired = (0x80000000 if access_bits != os.O_WRONLY else 0)
            desired |= 0x40000000 if access_bits else 0
            desired |= 0x00020000  # READ_CONTROL for private access validation.
            disposition = 1 if flags & os.O_CREAT and flags & os.O_EXCL else (4 if flags & os.O_CREAT else 3)
            with _ps_guard_parents(path), _ps_security(mode, directory=False) as attributes:
                handle = kernel.CreateFileW(_ps_native_name(path), desired, 0x3,
                    ctypes.byref(attributes), disposition, 0x00200080, None)
                if handle == ctypes.c_void_p(-1).value:
                    code = ctypes.get_last_error()
                    if code in {80, 183}:
                        raise FileExistsError(errno.EEXIST, "Destination already exists.", str(path))
                    if code in {2, 3}:
                        raise FileNotFoundError(errno.ENOENT, "Resource does not exist.", str(path))
                    _ps_raise_windows("Secure file open", code)
                try:
                    _ps_handle_info(handle)
                    descriptor = msvcrt.open_osfhandle(handle, (flags & (os.O_APPEND | os.O_WRONLY | os.O_RDWR)) | os.O_BINARY)
                except BaseException:
                    kernel.CloseHandle(handle)
                    raise
        os.set_inheritable(descriptor, False)
        opened, current = os.fstat(descriptor), path.lstat()
        if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
                or (opened.st_dev, opened.st_ino) != (current.st_dev, current.st_ino)
                or (before is not None and (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino))):
            raise PlatformError("Managed file identity changed while opening.")
        verify_access(path, private=private)
        if flags & os.O_TRUNC:
            os.ftruncate(descriptor, 0)
        result, descriptor = descriptor, None
        return result
    finally:
        if descriptor is not None:
            os.close(descriptor)


@contextmanager
def file_lock(descriptor: int, *, exclusive: bool = True,
              blocking: bool = True) -> Iterator[None]:
    """Hold a real whole-protocol lock until exit, including across exceptions.

    Every participant locks byte zero. Windows uses shared/exclusive LockFileEx
    handle locks; POSIX uses flock. A nonblocking conflict raises BlockingIOError.
    Blocking acquisition retries only contention; operational errors fail closed.
    """
    if not IS_WINDOWS:
        import fcntl
        operation = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
        fcntl.flock(descriptor, operation | (0 if blocking else fcntl.LOCK_NB))
        try:
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        return
    import msvcrt
    kernel, _ = _ps_windows_api()
    handle = msvcrt.get_osfhandle(descriptor)
    overlapped = _ps_OVERLAPPED()
    flags = 0x1 | (0x2 if exclusive else 0)
    while not kernel.LockFileEx(handle, flags, 0, 1, 0, ctypes.byref(overlapped)):
        code = ctypes.get_last_error()
        if code not in {32, 33}:
            _ps_raise_windows("File-lock acquisition", code)
        if not blocking:
            raise BlockingIOError(errno.EWOULDBLOCK, "Managed file lock is held.")
        time.sleep(0.01)
    try:
        yield
    finally:
        if not kernel.UnlockFileEx(handle, 0, 1, 0, ctypes.byref(overlapped)):
            _ps_raise_windows("File-lock release")


@lru_cache(maxsize=2)
def _ps_posix_rename_api(system: str):
    """Bind an atomic no-replace primitive, never a check-then-rename fallback."""
    if system != "darwin" and not system.startswith("linux"):
        raise PlatformError(errno.ENOTSUP, "Atomic exclusive directory rename is unavailable on this platform.")
    library = ctypes.CDLL(None, use_errno=True)
    try:
        if system == "darwin":
            function = library.renamex_np
            function.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        else:
            function = library.renameat2
            function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
                                 ctypes.c_char_p, ctypes.c_uint]
    except AttributeError as exc:
        raise PlatformError(errno.ENOTSUP, "Atomic exclusive directory rename is unavailable in libc.") from exc
    function.restype = ctypes.c_int
    return function


def _ps_posix_rename_exclusive(stage: Path, target: Path) -> None:
    function = _ps_posix_rename_api(sys.platform)
    ctypes.set_errno(0)
    source, destination = os.fsencode(stage), os.fsencode(target)
    if sys.platform == "darwin":
        result = function(source, destination, 0x4)  # RENAME_EXCL
    else:
        result = function(-100, source, -100, destination, 0x1)  # AT_FDCWD, RENAME_NOREPLACE
    if result == 0:
        return
    code = ctypes.get_errno() or errno.EIO
    if code in {errno.EEXIST, errno.ENOTEMPTY}:
        raise FileExistsError(errno.EEXIST, "Destination already exists.", str(target))
    if code in {errno.ENOSYS, errno.ENOTSUP, errno.EOPNOTSUPP, errno.EINVAL}:
        raise PlatformError(code, "Atomic exclusive directory rename is unsupported or rejected by this filesystem.")
    raise PlatformError(code, "Atomic exclusive directory rename failed.")


def promote_directory(stage: Path, target: Path) -> None:
    """Atomically rename a directory only when the destination does not exist.

    macOS uses renamex_np(RENAME_EXCL), Linux uses renameat2(RENAME_NOREPLACE),
    and Windows uses MoveFileEx without replacement and with write-through.
    There is no target precreation, check-then-rename or replacement fallback.
    Unsupported operating systems, libc entries or filesystems fail closed.
    """
    stage, target = _ps_absolute(stage), _ps_absolute(target)
    _ps_check_components(stage)
    _ps_check_components(target)
    if not stage.is_dir() or is_reparse(stage):
        raise PlatformError("Staged directory is missing or linked.")
    if IS_WINDOWS:
        kernel, _ = _ps_windows_api()
        if not kernel.MoveFileExW(_ps_native_name(stage), _ps_native_name(target), 0x8):
            code = ctypes.get_last_error()
            if code in {80, 183} or target.exists():
                raise FileExistsError(errno.EEXIST, "Destination already exists.", str(target))
            _ps_raise_windows("Exclusive directory promotion", code)
        return
    _ps_posix_rename_exclusive(stage, target)


def sync_file(descriptor: int) -> None:
    """Flush file content through the operating system or raise on failure."""
    if not IS_WINDOWS:
        os.fsync(descriptor)
        return
    import msvcrt
    kernel, _ = _ps_windows_api()
    if not kernel.FlushFileBuffers(msvcrt.get_osfhandle(descriptor)):
        _ps_raise_windows("File flush")


def sync_directory(path: Path) -> bool:
    """Attempt a directory-metadata flush and report actual support.

    POSIX returns True only after fsync. Windows returns False solely when the
    filesystem/API explicitly does not support flushing a directory handle;
    other failures raise. Directory promotion separately requests write-through.
    False never establishes power-loss durability and must be reported as such.
    """
    path = _ps_absolute(path)
    _ps_check_components(path)
    if not IS_WINDOWS:
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
            return True
        finally:
            os.close(descriptor)
    kernel, _ = _ps_windows_api()
    handle = kernel.CreateFileW(_ps_native_name(path), 0xC0000000, 0x7,
                               None, 3, 0x02200000, None)
    if handle == ctypes.c_void_p(-1).value:
        code = ctypes.get_last_error()
        if code in {1, 50}:
            return False
        _ps_raise_windows("Directory flush open", code)
    try:
        _ps_handle_info(handle)
        if kernel.FlushFileBuffers(handle):
            return True
        code = ctypes.get_last_error()
        if code in {1, 50}:
            return False
        _ps_raise_windows("Directory flush", code)
    finally:
        kernel.CloseHandle(handle)

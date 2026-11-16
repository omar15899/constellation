"""POSIX locking and exclusive publication needed by the course production skill."""
from __future__ import annotations

from contextlib import contextmanager
import ctypes
import errno
import os
import stat
import sys
from typing import Iterator


@contextmanager
def file_lock(descriptor: int, *, exclusive: bool = True, blocking: bool = True) -> Iterator[None]:
    """Hold a flock until exit; operational errors and contention are not hidden."""
    import fcntl
    mode = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
    fcntl.flock(descriptor, mode | (0 if blocking else fcntl.LOCK_NB))
    try:
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)


def promote_directory_at(source_fd: int, source_name: str, destination_fd: int,
                         destination_name: str) -> None:
    """Atomically publish a directory without replacing any existing entry.

    Args:
        source_fd: Open directory containing the completed staging directory.
        source_name: One filename under source_fd.
        destination_fd: Open destination parent.
        destination_name: One vacant filename under destination_fd.

    Raises:
        OSError: Unsupported platform, invalid input, collision or rename failure.
    """
    for fd, name in ((source_fd, source_name), (destination_fd, destination_name)):
        if (type(fd) is not int or fd < 0 or not stat.S_ISDIR(os.fstat(fd).st_mode)
                or not isinstance(name, str) or not name or name in {".", ".."}
                or "/" in name or "\0" in name):
            raise ValueError("Directory publication requires open parents and single names")
    if not stat.S_ISDIR(os.stat(source_name, dir_fd=source_fd, follow_symlinks=False).st_mode):
        raise ValueError("The staged entry is not a real directory")
    if sys.platform != "darwin" and not sys.platform.startswith("linux"):
        raise OSError(errno.ENOTSUP, "Exclusive directory publication requires macOS or Linux")
    libc = ctypes.CDLL(None, use_errno=True)
    function = libc.renameatx_np if sys.platform == "darwin" else libc.renameat2
    function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    function.restype = ctypes.c_int
    flag = 4 if sys.platform == "darwin" else 1
    if function(source_fd, os.fsencode(source_name), destination_fd, os.fsencode(destination_name), flag):
        code = ctypes.get_errno() or errno.EIO
        raise OSError(code, os.strerror(code), destination_name)

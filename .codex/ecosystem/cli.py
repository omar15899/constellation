#!/usr/bin/env python3
"""Keep the workspace's historical CLI on the verified device installation.

The engine and development source live under the user's Codex home. This
adapter only supplies the workspace root; it never imports a local engine.
"""
from __future__ import annotations

import os
import sys

if __name__ == "__main__" and not sys.flags.isolated:
    os.execv(sys.executable, [sys.executable, "-I", "-B", __file__, *sys.argv[1:]])

from pathlib import Path
import fcntl
import hashlib
import json
import stat
import subprocess


def _record(path: Path) -> dict:
    """Read a regular transport file's bytes and permission record."""
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
        raise ValueError("Transport requires regular installation files")
    return {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "mode": stat.S_IMODE(path.stat().st_mode)}


def _handoff(home: Path, arguments: list[str]) -> int:
    """Execute receipt-checked launcher bytes under the installation lock.

    The receipt and transport checks preserve the historical source entry's
    rejection of incomplete, replaced or nonregular device installations.
    The launcher verifies the installed package before dispatching operations.
    """
    transport = home / "constellation"
    launcher = transport / "run"
    receipt_path = transport / "receipt.json"
    if (not home.is_absolute()
            or any(path.is_symlink() for path in (*transport.parents, transport, receipt_path))
            or not receipt_path.is_file() or not launcher.is_file()):
        raise ValueError("the verified device launcher is unavailable")
    descriptor = os.open(transport / ".install.lock", os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as handle:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError("the installation lock is not regular")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("Constellation is updating; retry after installation") from exc
        receipt = json.loads(receipt_path.read_bytes())
        if (not isinstance(receipt, dict) or receipt.get("schema") != 4
                or not isinstance(receipt.get("python"), str)
                or not Path(receipt["python"]).is_absolute()
                or not isinstance(receipt.get("cache"), dict)):
            raise ValueError("the installation receipt is incompatible")
        launch_record = _record(launcher)
        hook_record = _record(transport / "hook.py")
        if (launch_record["mode"] != 0o700 or launch_record != receipt.get("launcher")
                or hook_record["mode"] != 0o644 or hook_record != receipt.get("hook")
                or hook_record != receipt["cache"].get("ecosystem/hook_entry.py")):
            raise ValueError("the installed transport does not match its receipt")
        code = launcher.read_bytes()
        if hashlib.sha256(code).hexdigest() != launch_record["sha256"]:
            raise ValueError("the launcher changed during verification")
        return subprocess.run(["/bin/sh", "-c", code.decode("utf-8"), str(launcher),
                               "cli", *arguments]).returncode


def main(argv: list[str] | None = None) -> int:
    """Forward arguments and the caller's directory to the installed launcher.

    ``workspace`` and ``agent-policy`` default to this adapter's GitHub root.
    An explicit later ``--root`` keeps precedence. Other commands, including
    ``git``, receive their original arguments and working directory unchanged.

    Args:
        argv: CLI arguments without the program name; defaults to ``sys.argv``.

    Returns:
        Two if the launcher is unavailable or development mode was requested.
        Otherwise the installed launcher's exit status, without changing cwd.
    """
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments[:1] == ["--source"]:
        print("Constellation source moved to ~/.codex/.codex/ecosystem/cli.py; "
              "run development commands there with --source.", file=sys.stderr)
        return 2
    root = Path(__file__).resolve().parents[2]
    home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    if arguments[:1] in (["workspace"], ["agent-policy"]):
        arguments = [arguments[0], "--root", str(root), *arguments[1:]]
    try:
        return _handoff(home, arguments)
    except (OSError, ValueError) as exc:
        print(f"Constellation: {exc}. Repair or update the verified device installation.",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

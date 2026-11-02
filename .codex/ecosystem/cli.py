#!/usr/bin/env python3
"""Constellation entry point for portable evidence and native Git workflows."""
import os
import sys

if __name__ == "__main__" and not sys.flags.isolated:
    os.execv(sys.executable, [sys.executable, "-I", "-B", __file__, *sys.argv[1:]])

import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
import subprocess
from typing import Optional

sys.dont_write_bytecode = True


def _source_checkout() -> Optional[Path]:
    """Identify the source by its own Git owner and versioned distribution manifest.

    Relocated packages can also live under a directory named .codex. The
    caller's working directory and local profile cannot select the engine.
    """
    package = Path(__file__).resolve().parent.parent
    root = package.parent
    if package.name.casefold() != ".codex" or not (root / ".git").exists():
        return None
    result = subprocess.run(
        ["git", "--no-replace-objects", "--git-dir", str(root / ".git"),
         "ls-tree", "HEAD", "--", ".codex/ecosystem/manifests/codex-plugin.json"],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode:
        raise ValueError("Cannot establish ownership of the Constellation source checkout.")
    return root if result.stdout.strip() else None


def _record(path: Path) -> dict:
    """Record the contents and mode of a regular installed transport file."""
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
        raise ValueError("Constellation transport requires regular installation files.")
    return {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "mode": stat.S_IMODE(path.stat().st_mode)}


def _handoff(root: Optional[Path], arguments: list[str]) -> int:
    """Execute the recorded launcher under the device installation lock.

    A source checkout supplies its hub root. For a deliberately extracted
    bundle named .codex, the manifest must match the installed release. In both
    cases only the device code executes, independent of the caller's Python.
    """
    import fcntl  # Codex device installations are supported on POSIX.
    home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    transport = home / "constellation"
    launcher = transport / "run"
    receipt_path = transport / "receipt.json"
    error = "Install or update the Constellation release with the verified CLI for this device."
    if (not home.is_absolute() or any(p.is_symlink() for p in (*transport.parents, transport, receipt_path))
            or not receipt_path.is_file() or not launcher.is_file()):
        raise ValueError(error)
    lock = transport / ".install.lock"
    descriptor = os.open(lock, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as handle:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError(error)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("Constellation is updating; retry after installation.") from exc
        receipt = json.loads(receipt_path.read_bytes())
        if (not isinstance(receipt, dict) or receipt.get("schema") != 4
                or not isinstance(receipt.get("python"), str) or not Path(receipt["python"]).is_absolute()
                or not isinstance(receipt.get("cache"), dict)):
            raise ValueError(error)
        launch_record = _record(launcher)
        hook_record = _record(transport / "hook.py")
        if (launch_record["mode"] != 0o700 or launch_record != receipt.get("launcher")
                or hook_record["mode"] != 0o644 or hook_record != receipt.get("hook")
                or hook_record != receipt["cache"].get("ecosystem/hook_entry.py")):
            raise ValueError(error)
        # Execute these checked launcher bytes; replacing the on-disk path
        # cannot select another shell program after this read.
        launch_code = launcher.read_bytes()
        if hashlib.sha256(launch_code).hexdigest() != launch_record["sha256"]:
            raise ValueError(error)
        if root is None:
            marker = Path(__file__).resolve().parent.parent / "bundle.json"
            if _record(marker) != receipt["cache"].get("bundle.json"):
                raise ValueError("This .codex directory does not identify the installed Constellation bundle.")
        elif arguments[:1] in (["workspace"], ["agent-policy"]):
            # An explicit --root later on the same command line retains precedence.
            arguments = [arguments[0], "--root", str(root), *arguments[1:]]
        return subprocess.run(["/bin/sh", "-c", launch_code.decode("utf-8"), str(launcher),
                               "cli", *arguments]).returncode


def _select_runtime() -> None:
    """Reserve .codex for an identified source or the corresponding device bundle."""
    package = Path(__file__).resolve().parent.parent
    root = _source_checkout()
    if sys.argv[1:2] == ["--source"]:
        if root is None:
            raise ValueError("--source requires a versioned Constellation development checkout.")
        del sys.argv[1]
    elif root is not None:
        raise SystemExit(_handoff(root, sys.argv[1:]))
    elif package.name.casefold() == ".codex":
        if not (package / "bundle.json").is_file():
            raise ValueError("Unidentified .codex checkout; use the installed Constellation CLI.")
        raise SystemExit(_handoff(None, sys.argv[1:]))


if __name__ == "__main__":
    try:
        _select_runtime()
    except (ImportError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print("Constellation: " + str(exc), file=sys.stderr)
        raise SystemExit(2) from None

if sys.version_info < (3, 11):
    sys.exit("Constellation development and portable execution require Python 3.11 or newer.")

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from ecosystem.core import Engine, Error, default_state_dir
    from ecosystem.storage import decode, encode
else:
    from .core import Engine, Error, default_state_dir
    from .storage import decode, encode


def _skill_read(arguments: list[str]) -> int:
    """Read an exact skill from this bundle while the installed launcher holds its lock."""
    if len(arguments) != 1 or not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", arguments[0]):
        print("skill-read requires one exact installed skill name.", file=sys.stderr)
        return 2
    root = Path(__file__).resolve().parent.parent
    relative = f"skills/{arguments[0]}/SKILL.md"
    try:
        # A developer checkout or an omitted optional module cannot supply an
        # arbitrary file by name. Only an owned, inventoried package member wins.
        from ecosystem.build import verify_bundle
        manifest = verify_bundle(root)
        if relative not in manifest["files"]:
            raise ValueError
        path = root / relative
        result = {"path": str(path), "content": path.read_text(encoding="utf-8")}
    except (KeyError, OSError, TypeError, ValueError, RuntimeError):
        print("The selected skill is unavailable in this verified release.", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


def _configure_utf8_streams() -> None:
    """Keep JSON and command output independent of the Windows code page."""
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="strict")


def main(argv: Optional[list[str]] = None, *, installation_home: Optional[Path] = None) -> int:
    _configure_utf8_streams()
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments[:1] == ["skill-run"]:
        if installation_home is None:
            print("skill-run requires the verified device launcher.", file=sys.stderr)
            return 2
        try:
            from ecosystem.vault.skill_run import entrypoint
        except ModuleNotFoundError as error:
            if error.name not in {"ecosystem.vault", "ecosystem.vault.skill_run"}:
                raise
            print("Install the omaros module to use its skill helpers.", file=sys.stderr)
            return 2
        return entrypoint(installation_home, arguments[1:])
    if arguments[:1] == ["native"]:
        from ecosystem.native import main as native_main
        return native_main(arguments[1:])
    if arguments[:1] == ["skill-read"]:
        return _skill_read(arguments[1:])
    if arguments[:1] == ["git"]:
        from ecosystem.runtime.workflow import entrypoint
        return entrypoint(arguments[1:])
    if arguments[:1] in (["workspace"], ["agent-policy"]):
        package_parent = Path(__file__).resolve().parent.parent
        # Source aliases retain one owner even on case-insensitive filesystems.
        # Only a complete verified bundle can opt out of that checkout default.
        default_root = None
        if package_parent.name.casefold() == ".codex":
            default_root = package_parent.parent
            marker = package_parent / "bundle.json"
            if marker.exists() or marker.is_symlink():
                from ecosystem.build import verify_bundle
                try:
                    verify_bundle(package_parent)
                except (OSError, ValueError):
                    pass
                else:
                    default_root = None
        if arguments[0] == "workspace":
            from ecosystem.runtime.workspace import entrypoint
        else:
            from ecosystem.runtime.agent_policy import entrypoint
        return entrypoint(arguments[1:], default_root=default_root)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--state-dir", type=Path, default=default_state_dir())
    parser.add_argument("operation")
    options = parser.parse_args(arguments)
    try:
        payload = decode(sys.stdin.read())
        result = Engine(options.root, options.state_dir).execute(options.operation, payload)
    except UnicodeError:
        print(encode({"ok": False, "error": "Portable CLI text must be valid UTF-8."}))
        return 2
    except (Error, OSError) as exc:
        print(encode({"ok": False, "error": str(exc)}))
        return 2
    check_failed = options.operation == "check" and result.get("status") != "passed"
    print(encode({"ok": not check_failed, **result}))
    return 2 if check_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

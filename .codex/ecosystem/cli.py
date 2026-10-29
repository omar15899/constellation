#!/usr/bin/env python3
"""Constellation entry point for portable evidence and native Git workflows."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.dont_write_bytecode = True

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from ecosystem.core import Engine, Error, default_state_dir
    from ecosystem.storage import decode, encode
else:
    from .core import Engine, Error, default_state_dir
    from .storage import decode, encode


def _configure_utf8_streams() -> None:
    """Keep JSON and command output independent of the Windows code page."""
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="strict")


def main(argv: list[str] | None = None) -> int:
    _configure_utf8_streams()
    arguments = list(sys.argv[1:] if argv is None else argv)
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

#!/usr/bin/env python3
"""Strict JSON CLI for the portable local coordination engine."""
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--state-dir", type=Path, default=default_state_dir())
    parser.add_argument("operation")
    options = parser.parse_args(argv)
    try:
        payload = decode(sys.stdin.read())
        result = Engine(options.root, options.state_dir).execute(options.operation, payload)
    except (Error, OSError) as exc:
        print(encode({"ok": False, "error": str(exc)}))
        return 2
    check_failed = options.operation == "check" and result.get("status") != "passed"
    print(encode({"ok": not check_failed, **result}))
    return 2 if check_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

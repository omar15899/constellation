#!/usr/bin/env python3
"""_levers.py — dependency-free reader for registry/levers.yaml.

The constellation convention is stdlib-only, hand-parsed YAML (see
scripts/discover_repos.py, hooks/_common.py) — PyYAML is NOT installed. This
module hand-parses the regular subset of YAML that levers.yaml uses: a top-level
`levers:` list of mappings whose scalar fields are `key: value` (optionally
single/double quoted). It does not implement general YAML; it implements exactly
the shape levers.yaml is written in.

Public API:
    levers_path()            -> Path of registry/levers.yaml
    load_levers()            -> list[dict] (one dict per lever)
    load_strategies()        -> list[dict] (one dict per strategy)
    by_verdict(levers)       -> dict[str, list[dict]]
    is_truthy(value)         -> bool   (yaml-ish boolean coercion)
"""
from __future__ import annotations

from pathlib import Path

HUB = Path.home() / "GitHub" / ".claude"


def levers_path() -> Path:
    return HUB / "registry" / "levers.yaml"


def _strip_scalar(raw: str) -> str:
    v = raw.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
        v = v[1:-1]
    return v


def _parse_list_block(lines: list[str], block_key: str) -> list[dict]:
    """Parse a top-level `block_key:` whose value is a list of mappings.

    Items begin at indent 2 with `- `; their fields are at indent 4 as
    `key: value`. The block ends at the next top-level (indent 0, non-blank,
    non-comment) line.
    """
    records: list[dict] = []
    in_block = False
    current: dict | None = None
    for line in lines:
        stripped = line.strip()
        if not in_block:
            if stripped == f"{block_key}:":
                in_block = True
            continue
        # inside the block
        if stripped == "" or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent == 0:
            break  # next top-level key — block done
        if stripped.startswith("- "):
            if current is not None:
                records.append(current)
            current = {}
            rest = stripped[2:]
            if ":" in rest:
                k, _, v = rest.partition(":")
                current[k.strip()] = _strip_scalar(v)
        elif current is not None and ":" in stripped:
            k, _, v = stripped.partition(":")
            current[k.strip()] = _strip_scalar(v)
    if current is not None:
        records.append(current)
    return records


def _read_lines() -> list[str]:
    p = levers_path()
    if not p.exists():
        return []
    return p.read_text(errors="ignore").splitlines()


def load_levers() -> list[dict]:
    return _parse_list_block(_read_lines(), "levers")


def load_strategies() -> list[dict]:
    return _parse_list_block(_read_lines(), "strategies")


def by_verdict(levers: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for lev in levers:
        out.setdefault(lev.get("verdict", "OPEN"), []).append(lev)
    return out


def is_truthy(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")


if __name__ == "__main__":
    levs = load_levers()
    strats = load_strategies()
    print(f"levers={len(levs)} strategies={len(strats)}")
    bv = by_verdict(levs)
    for verdict in sorted(bv):
        print(f"  {verdict}: {len(bv[verdict])}  -> {[l['id'] for l in bv[verdict]]}")

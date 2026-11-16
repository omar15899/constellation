#!/usr/bin/env python3
"""Extract adaptation markers from a generic scaffold.

Input can be one of:
  - a 6-section `isomorph-synth` markdown artefact
  - a materialized scaffold directory (after `materialize_scaffold.py` ran)

Emits a JSON array of marker records, one per marker occurrence:

    [
        {
            "marker": "USER-INTEGRATION REQUIRED",
            "file": "src/pkg/infrastructure/adapters/market_data_adapter.py",
            "symbol": "MarketDataAdapter.fetch_observations",
            "line": 14,
            "contract_hint": "bind to the firm's real vendor client; return DataFrame matching ..."
        },
        ...
    ]

The output is the skeleton for Section 3 of the reintegration map (and indirectly,
the cross-check that `validate_rebind_map.py` runs to ensure every marker is
accounted for).

Usage:
    python3 extract_adaptation_points.py <artefact.md>       # parses the Section-3 file blocks
    python3 extract_adaptation_points.py <scaffold-dir>      # walks the live tree, greps source

Safety:
  - Read-only everywhere; never writes into the target.
  - Skips credential-looking files in a scaffold directory (.env*, *.pem, *.key).
  - Skips binary files via a null-byte sniff.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

MARKERS = (
    "USER-INTEGRATION REQUIRED",
    "ADAPTATION POINT",
    "PROJECT-SPECIFIC IMPLEMENTATION GOES HERE",
)
MARKER_RE = re.compile("|".join(re.escape(m) for m in MARKERS))

# For Python / TS symbol context — take the nearest preceding def/class line.
PY_SYMBOL_RE = re.compile(r"^\s*(?:async\s+)?(?:def|class)\s+(\w+)")
TS_SYMBOL_RE = re.compile(
    r"^\s*(?:export\s+)?(?:async\s+)?(?:function|class|const|let|var)\s+(\w+)"
)

SECRET_PATTERNS = [
    re.compile(r"(^|/)\.env(\..*)?$"),
    re.compile(r"\.pem$"),
    re.compile(r"\.key$"),
    re.compile(r"(^|/)credentials(\..*)?$", re.IGNORECASE),
    re.compile(r"(^|/)secrets\.ya?ml$", re.IGNORECASE),
]

IGNORE_DIRS = {
    "node_modules", ".git", ".venv", "venv", "__pycache__", ".cache",
    "dist", "build", "site-packages", ".idea", ".vscode", "target",
}

_FENCE_OPEN_RE = re.compile(r"^```[A-Za-z0-9_+\-.]*\s*$")
_FENCE_CLOSE_RE = re.compile(r"^```\s*$")
_H2_FILE_RE = re.compile(r"^##\s+(\S.*?)\s*$")
_H1_RE = re.compile(r"^#\s+.+$")


def _is_secret_path(rel: str) -> bool:
    return any(p.search(rel) for p in SECRET_PATTERNS)


def _is_binary(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            return b"\x00" in f.read(2048)
    except OSError:
        return True


def _nearest_symbol(lines: list[str], idx: int, lang: str) -> str:
    rx = PY_SYMBOL_RE if lang == "python" else TS_SYMBOL_RE
    for i in range(idx, -1, -1):
        m = rx.match(lines[i])
        if m:
            return m.group(1)
    return ""


def _contract_hint(lines: list[str], idx: int, span: int = 4) -> str:
    """Return a short excerpt around the marker, stripped of comment markers."""
    lo = max(0, idx - 1)
    hi = min(len(lines), idx + span)
    buf = []
    for ln in lines[lo:hi]:
        cleaned = re.sub(r"^\s*(#|//|/\*|\*|\"\"\"|''')\s?", "", ln).rstrip()
        if cleaned:
            buf.append(cleaned)
    hint = " ".join(buf)
    return hint[:280]


def _scan_file(rel: str, content: str, lang: str | None) -> list[dict]:
    out = []
    lines = content.splitlines()
    for i, ln in enumerate(lines):
        for m in MARKER_RE.finditer(ln):
            sym = _nearest_symbol(lines, i, lang) if lang in {"python", "typescript", "javascript"} else ""
            out.append({
                "marker": m.group(0),
                "file": rel,
                "symbol": sym,
                "line": i + 1,
                "contract_hint": _contract_hint(lines, i),
            })
    return out


def _lang_for(path: Path) -> str | None:
    ext = path.suffix.lower()
    if ext in (".py", ".pyi"):
        return "python"
    if ext in (".ts", ".tsx"):
        return "typescript"
    if ext in (".js", ".jsx", ".mjs", ".cjs"):
        return "javascript"
    if ext in (".go",):
        return "go"
    if ext in (".rs",):
        return "rust"
    if ext in (".md", ".markdown"):
        return "markdown"
    return None


def scan_directory(root: Path) -> list[dict]:
    root = root.resolve()
    results: list[dict] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS and not d.startswith(".")]
        for fname in filenames:
            fpath = Path(dirpath) / fname
            rel = str(fpath.relative_to(root))
            if _is_secret_path(rel):
                continue
            if _is_binary(fpath):
                continue
            try:
                content = fpath.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            lang = _lang_for(fpath)
            results.extend(_scan_file(rel, content, lang))
    return results


def scan_artefact(artefact: Path) -> list[dict]:
    """Walk Section 3 of a 6-section synth artefact and scan each fenced file."""
    text = artefact.read_text(encoding="utf-8")
    lines = text.splitlines()
    # Locate Section 3.
    try:
        s3_start = next(i for i, ln in enumerate(lines) if ln.strip() == "# 3. File contents")
    except StopIteration:
        # Not a synth artefact — fall back to scanning the whole document as markdown.
        return _scan_file(str(artefact), text, "markdown")
    s3_end = len(lines)
    for j in range(s3_start + 1, len(lines)):
        if lines[j].startswith("# ") and lines[j].strip() != "# 3. File contents":
            s3_end = j
            break

    results: list[dict] = []
    i = s3_start + 1
    current_file: str | None = None
    while i < s3_end:
        ln = lines[i]
        m = _H2_FILE_RE.match(ln)
        if m:
            current_file = m.group(1).strip().strip("`")
            i += 1
            continue
        if _FENCE_OPEN_RE.match(ln) and current_file is not None:
            i += 1
            buf = []
            while i < s3_end and not _FENCE_CLOSE_RE.match(lines[i]):
                buf.append(lines[i])
                i += 1
            # skip closing fence
            if i < s3_end:
                i += 1
            lang = _lang_for(Path(current_file))
            results.extend(_scan_file(current_file, "\n".join(buf), lang))
            current_file = None
            continue
        i += 1
    return results


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="path to a synth artefact (.md) OR a scaffold directory")
    ap.add_argument("--pretty", action="store_true", help="pretty-print JSON")
    args = ap.parse_args()

    p = Path(args.target).expanduser()
    if not p.exists():
        sys.stderr.write(f"error: target does not exist: {p}\n")
        sys.exit(2)

    if p.is_dir():
        results = scan_directory(p)
    else:
        results = scan_artefact(p)

    payload = {
        "target": str(p),
        "marker_count": len(results),
        "by_marker": {m: sum(1 for r in results if r["marker"] == m) for m in MARKERS},
        "markers": results,
    }
    if args.pretty:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()

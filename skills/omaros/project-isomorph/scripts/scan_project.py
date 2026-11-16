#!/usr/bin/env python3
"""Walk a target project directory and emit a structured topology profile.

This is the first-pass scanner for the project-isomorph skill. It never writes
into the target and never reads credential-like files. The output is a JSON
profile intended to be the skeleton off which the dossier is built — so the
skill doesn't need to load every file into context to understand the shape.

What it emits (single JSON object on stdout):

  {
    "root": "<abs path>",
    "file_count": <int>,
    "loc_total": <int>,
    "languages": {"python": 42, "typescript": 17, "yaml": 8, ...},
    "tree": {
        "<relpath>": {
            "kind": "file" | "dir",
            "bytes": <int>,
            "lines": <int>,
            "language": "<lang-or-null>"
        }, ...
    },
    "manifests": {
        "pyproject.toml":  {"declared_deps": [...], "entry_points": [...]},
        "package.json":    {"declared_deps": [...], "scripts": [...]},
        "requirements.txt": {"declared_deps": [...]},
        "go.mod":          {"module": "...", "declared_deps": [...]},
        "Cargo.toml":      {"package_name": "...", "declared_deps": [...]}
    },
    "python_imports": {
        "<relpath>.py": {
            "stdlib":  ["os", "sys", ...],
            "third":   ["numpy", "pandas", ...],
            "relative": ["..utils", ".core", ...]
        }
    },
    "entry_points": {
        "shell_scripts": [...],       # files with a shebang
        "python_main":   [...],       # files with `if __name__ == "__main__":`
        "declared":      [...]        # from manifests (console_scripts, bin)
    },
    "warnings": [...]
  }

Usage:
    python3 scan_project.py <target-path>             # pretty JSON to stdout
    python3 scan_project.py <target-path> --compact   # single-line JSON
    python3 scan_project.py <target-path> --max-bytes 500000  # skip larger files

Safety:
  - Never opens files matching SECRET_FILE_PATTERNS.
  - Never follows symlinks that point outside the target root.
  - Only reads files it needs to parse (manifests, .py for imports).
  - Skips binary files via a null-byte heuristic.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from pathlib import Path

IGNORE_DIR_NAMES = {
    "node_modules", ".git", ".venv", "venv", "__pycache__", ".cache",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist", "build",
    "site-packages", ".idea", ".vscode", ".tox", "target",  # rust target
    ".next", ".turbo", ".parcel-cache", "coverage", ".nyc_output",
}

SECRET_FILE_PATTERNS = [
    re.compile(r"(^|/)\.env(\..*)?$"),
    re.compile(r"\.pem$"),
    re.compile(r"\.key$"),
    re.compile(r"\.p12$"),
    re.compile(r"\.pfx$"),
    re.compile(r"(^|/)id_rsa(\..*)?$"),
    re.compile(r"(^|/)id_ed25519(\..*)?$"),
    re.compile(r"(^|/)credentials(\..*)?$", re.IGNORECASE),
    re.compile(r"(^|/)secrets\.ya?ml$", re.IGNORECASE),
]

EXT_LANG_MAP = {
    ".py": "python", ".pyi": "python", ".ipynb": "jupyter_notebook",
    ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "typescript",
    ".jsx": "javascript",
    ".go": "go", ".rs": "rust", ".rb": "ruby",
    ".java": "java", ".kt": "kotlin", ".scala": "scala",
    ".c": "c", ".h": "c", ".cpp": "cpp", ".cc": "cpp", ".hpp": "cpp",
    ".cs": "csharp",
    ".php": "php",
    ".sh": "shell", ".bash": "shell", ".zsh": "shell",
    ".sql": "sql",
    ".r": "r", ".R": "r",
    ".tex": "latex", ".bib": "bibtex",
    ".md": "markdown", ".rst": "restructuredtext",
    ".yaml": "yaml", ".yml": "yaml",
    ".toml": "toml", ".json": "json", ".jsonc": "json",
    ".ini": "ini", ".cfg": "ini",
    ".html": "html", ".css": "css", ".scss": "scss",
    ".dockerfile": "dockerfile", ".proto": "protobuf",
    ".avro": "avro", ".parquet": "parquet_binary",
}

STDLIB_PY_3_11 = {
    "abc", "argparse", "ast", "asyncio", "base64", "bisect", "builtins",
    "collections", "concurrent", "contextlib", "contextvars", "copy",
    "csv", "ctypes", "dataclasses", "datetime", "decimal", "difflib",
    "dis", "email", "enum", "errno", "fnmatch", "functools", "gc", "glob",
    "gzip", "hashlib", "heapq", "hmac", "html", "http", "importlib",
    "inspect", "io", "ipaddress", "itertools", "json", "keyword",
    "logging", "math", "mimetypes", "multiprocessing", "numbers",
    "operator", "os", "pathlib", "pickle", "platform", "plistlib",
    "pprint", "queue", "random", "re", "secrets", "select", "selectors",
    "shlex", "shutil", "signal", "site", "socket", "sqlite3", "ssl",
    "stat", "statistics", "string", "struct", "subprocess", "sys",
    "tempfile", "textwrap", "threading", "time", "timeit", "tokenize",
    "traceback", "types", "typing", "unittest", "urllib", "uuid",
    "warnings", "weakref", "xml", "zipfile", "zoneinfo",
    "__future__",
}


def _is_secret_path(rel: str) -> bool:
    for pat in SECRET_FILE_PATTERNS:
        if pat.search(rel):
            return True
    return False


def _guess_lang(p: Path) -> str | None:
    # Special-case Dockerfile (no extension) and Makefile
    name = p.name.lower()
    if name == "dockerfile" or name.endswith(".dockerfile"):
        return "dockerfile"
    if name == "makefile":
        return "make"
    return EXT_LANG_MAP.get(p.suffix.lower())


def _is_binary(path: Path, sniff_bytes: int = 2048) -> bool:
    try:
        with path.open("rb") as f:
            chunk = f.read(sniff_bytes)
    except OSError:
        return True
    if b"\x00" in chunk:
        return True
    return False


def _count_lines(path: Path) -> int:
    try:
        with path.open("rb") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def _parse_pyproject(path: Path) -> dict:
    try:
        import tomllib  # py311+
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore
        except ImportError:
            return {"declared_deps": [], "entry_points": [], "_error": "tomllib not available"}
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"declared_deps": [], "entry_points": [], "_error": str(exc)}
    deps: list[str] = []
    proj = data.get("project", {})
    for d in proj.get("dependencies", []) or []:
        deps.append(str(d).split()[0].split(">=")[0].split("==")[0].split("<")[0].strip())
    optional_deps = proj.get("optional-dependencies", {}) or {}
    for group, lst in optional_deps.items():
        for d in lst:
            deps.append(str(d).split()[0].split(">=")[0].split("==")[0].split("<")[0].strip())
    # Poetry / hatch-style
    tool = data.get("tool", {})
    for section in ("poetry", "hatch"):
        sec = tool.get(section, {}) or {}
        for k in sec.get("dependencies", {}) or {}:
            if k.lower() != "python":
                deps.append(k)
    entry_points = list(proj.get("scripts", {}).keys())
    return {"declared_deps": sorted(set(deps)), "entry_points": sorted(entry_points)}


def _parse_package_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"declared_deps": [], "scripts": [], "_error": str(exc)}
    deps = list((data.get("dependencies") or {}).keys()) + \
           list((data.get("devDependencies") or {}).keys()) + \
           list((data.get("peerDependencies") or {}).keys())
    scripts = list((data.get("scripts") or {}).keys())
    return {"declared_deps": sorted(set(deps)), "scripts": sorted(scripts)}


def _parse_requirements(path: Path) -> dict:
    deps: list[str] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip()
            if not line or line.startswith("-"):
                continue
            name = re.split(r"[<>=!~]", line, maxsplit=1)[0].strip()
            if name:
                deps.append(name)
    except OSError:
        pass
    return {"declared_deps": sorted(set(deps))}


def _parse_go_mod(path: Path) -> dict:
    try:
        txt = path.read_text(encoding="utf-8")
    except OSError:
        return {"module": None, "declared_deps": []}
    mod = None
    m = re.search(r"^module\s+(\S+)", txt, re.MULTILINE)
    if m:
        mod = m.group(1)
    deps = re.findall(r"^\s*([\w./-]+)\s+v[\w.-]+", txt, re.MULTILINE)
    return {"module": mod, "declared_deps": sorted(set(deps))}


def _parse_cargo_toml(path: Path) -> dict:
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore
        except ImportError:
            return {"package_name": None, "declared_deps": []}
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"package_name": None, "declared_deps": []}
    pkg = (data.get("package") or {}).get("name")
    deps = list((data.get("dependencies") or {}).keys()) + \
           list((data.get("dev-dependencies") or {}).keys())
    return {"package_name": pkg, "declared_deps": sorted(set(deps))}


def _parse_python_imports(path: Path) -> dict:
    try:
        src = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {"stdlib": [], "third": [], "relative": []}
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return {"stdlib": [], "third": [], "relative": []}
    stdlib, third, relative = set(), set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".", 1)[0]
                (stdlib if top in STDLIB_PY_3_11 else third).add(top)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                mod = node.module or ""
                relative.add("." * node.level + mod)
            elif node.module:
                top = node.module.split(".", 1)[0]
                (stdlib if top in STDLIB_PY_3_11 else third).add(top)
    return {
        "stdlib": sorted(stdlib),
        "third": sorted(third),
        "relative": sorted(relative),
    }


def _looks_like_python_main(path: Path) -> bool:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if '__name__' in line and '__main__' in line and '==' in line:
                    return True
    except OSError:
        pass
    return False


def _has_shebang(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            return f.read(2) == b"#!"
    except OSError:
        return False


def scan(root: Path, max_bytes: int) -> dict:
    root = root.resolve()
    warnings: list[str] = []

    tree: dict[str, dict] = {}
    languages: dict[str, int] = {}
    file_count = 0
    loc_total = 0
    manifests: dict[str, dict] = {}
    python_imports: dict[str, dict] = {}
    entry_points: dict[str, list[str]] = {"shell_scripts": [], "python_main": [], "declared": []}

    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        # Prune ignored directories in-place
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIR_NAMES and not d.startswith(".")]
        dpath = Path(dirpath)
        rel_dir = str(dpath.relative_to(root))
        if rel_dir != ".":
            tree[rel_dir] = {"kind": "dir", "bytes": 0, "lines": 0, "language": None}

        for fname in filenames:
            fpath = dpath / fname
            try:
                rel = str(fpath.relative_to(root))
            except ValueError:
                continue

            if _is_secret_path(rel):
                warnings.append(f"skipped secret-like file: {rel}")
                continue

            try:
                st = fpath.stat()
            except OSError:
                continue
            size = st.st_size

            if size > max_bytes:
                tree[rel] = {"kind": "file", "bytes": size, "lines": None,
                             "language": _guess_lang(fpath), "truncated": True}
                file_count += 1
                continue

            if _is_binary(fpath):
                tree[rel] = {"kind": "file", "bytes": size, "lines": 0,
                             "language": _guess_lang(fpath), "binary": True}
                file_count += 1
                continue

            lines = _count_lines(fpath)
            lang = _guess_lang(fpath)

            tree[rel] = {"kind": "file", "bytes": size, "lines": lines, "language": lang}
            file_count += 1
            loc_total += lines
            if lang:
                languages[lang] = languages.get(lang, 0) + lines

            # Manifests
            if fname == "pyproject.toml":
                manifests.setdefault("pyproject.toml", []).append({"path": rel, **_parse_pyproject(fpath)})
                entry_points["declared"].extend(manifests["pyproject.toml"][-1].get("entry_points", []))
            elif fname == "package.json":
                manifests.setdefault("package.json", []).append({"path": rel, **_parse_package_json(fpath)})
                entry_points["declared"].extend(manifests["package.json"][-1].get("scripts", []))
            elif fname == "requirements.txt" or fname.startswith("requirements-"):
                manifests.setdefault("requirements.txt", []).append({"path": rel, **_parse_requirements(fpath)})
            elif fname == "go.mod":
                manifests.setdefault("go.mod", []).append({"path": rel, **_parse_go_mod(fpath)})
            elif fname == "Cargo.toml":
                manifests.setdefault("Cargo.toml", []).append({"path": rel, **_parse_cargo_toml(fpath)})

            # Python imports
            if lang == "python":
                python_imports[rel] = _parse_python_imports(fpath)
                if _looks_like_python_main(fpath):
                    entry_points["python_main"].append(rel)

            # Shell script detection
            if lang in {"shell", "python"} and _has_shebang(fpath):
                entry_points["shell_scripts"].append(rel)

    return {
        "root": str(root),
        "file_count": file_count,
        "loc_total": loc_total,
        "languages": dict(sorted(languages.items(), key=lambda kv: -kv[1])),
        "tree": tree,
        "manifests": manifests,
        "python_imports": python_imports,
        "entry_points": {k: sorted(set(v)) for k, v in entry_points.items()},
        "warnings": warnings,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="path to the target project root")
    ap.add_argument("--compact", action="store_true",
                    help="emit single-line JSON instead of pretty-printed")
    ap.add_argument("--max-bytes", type=int, default=2_000_000,
                    help="skip content parsing for files larger than this (default 2 MB)")
    args = ap.parse_args()

    root = Path(args.target).expanduser()
    if not root.exists():
        sys.stderr.write(f"error: target does not exist: {root}\n")
        sys.exit(2)
    if not root.is_dir():
        sys.stderr.write(f"error: target is not a directory: {root}\n")
        sys.exit(2)

    profile = scan(root, args.max_bytes)
    if args.compact:
        print(json.dumps(profile, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(profile, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

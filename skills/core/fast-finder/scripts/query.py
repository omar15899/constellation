#!/usr/bin/env python3
"""Exact queries over Fast Finder's privacy-filtered vault inventory."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, time, timedelta, timezone
from fnmatch import fnmatchcase
from functools import lru_cache
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time as clock

# Importing the installed sibling must not modify the verified package.
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("fast_finder_search", Path(__file__).with_name("search.py"))
if spec is None or spec.loader is None:
    raise ImportError("The installed Fast Finder search module is missing.")
search = importlib.util.module_from_spec(spec)
spec.loader.exec_module(search)

MAX_CONTENT_SIZE = 2 * 1024 * 1024
MAX_HITS = 200


def glob_matches(path: Path, pattern: str) -> bool:
    parts = pattern.split("/")
    if not pattern or not all(parts) or ".." in parts:
        raise ValueError("Globs must be non-empty vault-relative patterns.")
    if len(parts) == 1:
        return fnmatchcase(path.name, pattern)

    @lru_cache(maxsize=None)
    def matches(i: int, j: int) -> bool:
        if j == len(parts):
            return i == len(path.parts)
        if parts[j] == "**":
            return matches(i, j + 1) or i < len(path.parts) and matches(i + 1, j)
        return i < len(path.parts) and fnmatchcase(path.parts[i], parts[j]) and matches(i + 1, j + 1)

    return matches(0, 0)


def content(inventory: search.Inventory, paths: list[Path], args: argparse.Namespace) -> dict:
    if not args.pattern:
        raise ValueError("Select a non-empty search pattern.")
    eligible = [path for path in paths if inventory[path].size <= MAX_CONTENT_SIZE]
    options = []
    if not args.regex:
        options.append("--fixed-strings")
    if args.ignore_case:
        options.append("--ignore-case")
    options.extend(["-e", args.pattern])
    # Validate the expression even when no files are eligible.
    result = subprocess.run(["rg", "--no-config", *options, "--", "-"], input=b"",
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
    if result.returncode not in (0, 1):
        raise ValueError("ripgrep rejected the search pattern.")
    results: list[dict] = []
    occurrences = matching_lines = 0
    files: set[Path] = set()
    deadline = clock.monotonic() + 30 * (1 + len(eligible) // search.FD_BATCH)
    for path, hit in search.rg_hits(inventory, eligible, options, deadline):
        count = sum(match["end"] > match["start"] for match in hit["submatches"])
        if not count:
            continue
        if len(results) < args.limit:
            if args.show == "paths" and path not in files:
                results.append({"path": path.as_posix()})
            elif args.show == "hits":
                results.append({"path": path.as_posix(), "line": hit["line_number"],
                                "excerpt": search.rg_text(hit["lines"]).rstrip("\r\n")[:320],
                                "matches": count})
        matching_lines += 1
        files.add(path)
        occurrences += count
    total = {"count": occurrences, "hits": matching_lines, "paths": len(files)}[args.show]
    return {"total_items": total, "matched_files": len(files), "occurrences": occurrences,
            "max_file_bytes": MAX_CONTENT_SIZE, "excluded_large_files": len(paths) - len(eligible),
            "partial": False, "results": results}


def timestamp(raw: str, *, upper: bool, now: datetime) -> float:
    value = raw.casefold()
    relative = re.fullmatch(r"(\d+)\.(hour|day|week)s?\.ago", value)
    if relative:
        offset = timedelta(**{relative[2] + "s": int(relative[1])})
        return (now - offset).timestamp()
    if value == "now":
        return now.timestamp()
    if value in {"today", "yesterday"}:
        day = now.date() - timedelta(days=int(value == "yesterday"))
    else:
        day = datetime.strptime(raw, "%Y-%m-%d").date()
    return datetime.combine(day, time.max if upper else time.min, tzinfo=timezone.utc).timestamp()


def paths_by_stat(inventory: search.Inventory, paths: list[Path], args: argparse.Namespace) -> dict:
    now = datetime.now(timezone.utc)
    since = timestamp(args.since, upper=False, now=now) if args.since else float("-inf")
    until = timestamp(args.until, upper=True, now=now) if args.until else float("inf")
    if since > until or args.min_size < 0 or args.max_size is not None and args.max_size < args.min_size:
        raise ValueError("Invalid date or size bounds.")
    rows = []
    for opened in inventory.batches(paths):
        for path, fd in opened.items():
            info = os.fstat(fd)
            if since <= info.st_mtime <= until and info.st_size >= args.min_size and (
                    args.max_size is None or info.st_size <= args.max_size):
                rows.append({"path": path.as_posix(), "size": info.st_size,
                             "mtime": datetime.fromtimestamp(info.st_mtime, timezone.utc).isoformat(timespec="microseconds")})
    # The inventory is path-sorted, which breaks ties deterministically.
    rows.sort(key=lambda row: row[args.sort], reverse=args.descending)
    return {"total_items": len(rows), "partial": False, "results": rows[:args.limit]}


def values(value) -> list[str]:
    items = value if isinstance(value, list) else [value]
    return [str(item) for item in items if item is not None and item != ""]


def pair(raw: str) -> tuple[str, str]:
    key, separator, value = raw.partition("=")
    if not key or not separator:
        raise ValueError("Field predicates require key=value.")
    return key, value


def notes(inventory: search.Inventory, paths: list[Path], args: argparse.Namespace) -> dict:
    summaries = args.operation == "summary"
    expected = [] if summaries else [pair(raw) for raw in args.field]
    rejected = [] if summaries else [pair(raw) for raw in args.not_field]
    substrings = [] if summaries else [pair(raw) for raw in args.contains]
    if summaries:
        requested = list(args.files)
        if args.stdin:
            requested.extend(line.rstrip("\r\n") for line in sys.stdin if line.rstrip("\r\n"))
        if requested:
            selected = {Path(name) for name in requested}
            if not selected.issubset(paths):
                raise ValueError("A summary target is missing, excluded, or outside the selected inventory.")
            paths = [path for path in paths if path in selected]
        elif args.stdin:
            paths = []
        else:
            raise ValueError("Specify summary FILE paths or pass --stdin.")
    results = []
    groups: Counter[str] = Counter()
    missing_group = 0
    total = 0
    if not summaries:
        paths = [path for path in paths if path.suffix.casefold() == ".md"]
    for opened in inventory.batches(paths):
        for path, fd in opened.items():
            fields, _, body = search.read_note(fd, path, strict=True)
            if not summaries:
                if (any(v not in values(fields.get(k)) for k, v in expected)
                        or any(v in values(fields.get(k)) for k, v in rejected)
                        or any(not values(fields.get(k)) for k in args.exists)
                        or any(values(fields.get(k)) for k in args.missing)
                        or any(not any(v.casefold() in val.casefold() for val in values(fields.get(k))) for k, v in substrings)):
                    continue
                if args.group_by:
                    labels = set(values(fields.get(args.group_by)))
                    if labels:
                        groups.update(labels)
                    else:
                        missing_group += 1
            total += 1
            if len(results) < args.limit:
                row = {"path": path.as_posix(), **{key: fields.get(key) for key in ("title", "status", "tags", "note_type", "updated")}}
                if summaries:
                    row["excerpt"] = next((line.strip()[:200] for line in body.splitlines()
                                           if line.strip() and not line.lstrip().startswith("#")), "")
                results.append(row)
    output = {"total_items": total, "partial": False, "results": results}
    if not summaries and args.group_by:
        output["groups"] = dict(sorted(groups.items()))
        output["missing_group"] = missing_group
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--path", action="append", default=[])
    for name in ("config", "include-raw", "include-archive"):
        parser.add_argument("--" + name, action="store_true")
    modes = parser.add_subparsers(dest="operation", required=True)
    matcher = modes.add_parser("content")
    matcher.add_argument("pattern")
    matcher.add_argument("--regex", action="store_true")
    matcher.add_argument("--ignore-case", action="store_true")
    matcher.add_argument("--show", choices=("count", "paths", "hits"), default="count")
    attrs = modes.add_parser("paths")
    attrs.add_argument("--since")
    attrs.add_argument("--until")
    attrs.add_argument("--min-size", type=int, default=0)
    attrs.add_argument("--max-size", type=int)
    attrs.add_argument("--sort", choices=("path", "mtime", "size"), default="path")
    attrs.add_argument("--descending", action="store_true")
    summaries = modes.add_parser("summary")
    summaries.add_argument("files", nargs="*")
    summaries.add_argument("--stdin", action="store_true")
    filters = modes.add_parser("metadata")
    for name in ("field", "not-field", "exists", "missing", "contains"):
        filters.add_argument("--" + name, action="append", default=[])
    filters.add_argument("--group-by")
    for mode in (matcher, attrs, summaries, filters):
        mode.add_argument("--glob", action="append", default=[])
        mode.add_argument("--exclude", action="append", default=[])
        mode.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    try:
        if not 0 <= args.limit <= MAX_HITS:
            raise ValueError(f"--limit must be between 0 and {MAX_HITS}.")
        root = search.project_root(args.root)
        names_only = args.operation == "paths"
        available = search.allowed_inventory(root, args.path, args.config, args.include_archive,
                                      args.include_raw, names_only=names_only)
        selected = [p for p in available if (not args.glob or any(glob_matches(p, g) for g in args.glob))
                    and not any(glob_matches(p, g) for g in args.exclude)]
        if args.operation == "content":
            output = content(available, selected, args)
        elif names_only:
            output = paths_by_stat(available, selected, args)
        else:
            output = notes(available, selected, args)
        print(json.dumps(output, default=str, allow_nan=False))
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        parser.exit(2, f"Fast Finder: {error}\n")


if __name__ == "__main__":
    main()

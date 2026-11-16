#!/usr/bin/env python3
"""Bounded live retrieval: ripgrep discovery, deterministic ranking, real excerpts."""
from __future__ import annotations

import argparse
from contextlib import ExitStack, closing, contextmanager
import json
import os
from pathlib import Path
import re
import base64
import stat
import subprocess
import time
import threading
import unicodedata
from typing import Any, Iterator, NamedTuple

import yaml

VAULT_MARKER = Path("05_Projects/OmarOS/Architecture/OmarOS_Architecture.md")
RESTRICTED = Path("06_Knowledge_Base/Mathematics/Finance/ENGIE/Private")

SKIP = {".git", ".obsidian", "node_modules", ".codex_notuse", "__pycache__"}
PRIVATE = ("13_Health", "16_Relationships_and_People")
PRIVATE_FOLDED = {name.casefold() for name in PRIVATE}
STOP_WORDS = {"busca", "buscar", "encuentra", "donde", "estan", "esta", "mis", "notas", "sobre", "de", "la", "el", "los", "las", "en", "y", "que", "find", "search", "my", "notes", "about", "the", "on", "of", "and"}


def project_root(explicit_root: Path | None = None) -> Path:
    """Resolve the receiving vault independently of the installed plugin."""
    directory = explicit_root if explicit_root is not None else Path.cwd()
    if directory.is_symlink():
        raise ValueError("The requested project root must not be a symlink.")
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    result = subprocess.run(["git", "-C", str(directory), "rev-parse", "--show-toplevel"],
                            capture_output=True, text=True, env=environment, timeout=15)
    if result.returncode:
        raise ValueError("Select the OmarOS Git checkout with --root.")
    owner = Path(result.stdout.strip()).resolve()
    if explicit_root is not None and explicit_root.resolve() != owner:
        raise ValueError("--root must select the owning Git root.")
    marker = owner / VAULT_MARKER
    if marker.resolve() != marker or not marker.is_file():
        raise ValueError("Fast Finder requires an OmarOS checkout with its architecture map.")
    return owner


def normalize(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(c))


def terms_for(query: str) -> list[str]:
    words = re.findall(r"[\w+-]+", normalize(query))
    cleaned = list(dict.fromkeys(w for w in words if w not in STOP_WORDS))
    return cleaned or words


def term_pattern(term: str) -> str:
    accents = {"a": "[aáàâäã]", "e": "[eéèêë]", "i": "[iíìîï]", "o": "[oóòôöõ]", "u": "[uúùûü]", "n": "[nñ]"}
    return "".join(accents.get(c, re.escape(c)) for c in term)


def read_note(fd: int, name: Path, *, strict: bool = False) -> tuple[dict[str, Any], str, str]:
    """Read a bounded prefix; a frontmatter delimiter must occupy its own line."""
    prefix = os.pread(fd, 16384, 0).decode("utf-8", errors="replace").replace("\r\n", "\n")
    if not prefix.startswith("---\n"):
        return {}, prefix, prefix
    fence = re.search(r"(?m)^---[ \t]*$", prefix[4:])
    if fence:
        try:
            parsed = yaml.safe_load(prefix[4:4 + fence.start()])
            if isinstance(parsed, dict):
                return parsed, prefix, prefix[4 + fence.end():]
        except yaml.YAMLError:
            pass
    if strict:
        raise ValueError(f"Invalid or incomplete frontmatter within the first 16 KiB: {name.name}")
    return {}, prefix, prefix


def visible(relative: Path, scopes: list[str], config: bool, archive: bool, raw: bool) -> bool:
    """Apply exclusions to spellings returned by rg, including case aliases."""
    parts = tuple(p.casefold() for p in relative.parts)
    if not parts:  # The explicit "." scope denotes the vault.
        return True
    pattern = "/" + "/".join(parts) + "/"
    excluded = (
        f"/{RESTRICTED.as_posix().casefold()}/", "/docs/sk_runs/", "/.codex/sessions/",
        "/.codex/log/", "/.codex/logs/", "/.codex/cache/", "/.codex/state/", "/.claude/cache/",
        "/.claude/run/", "/.claude/logs/", "/09_data_sources/email_exports/by_message/",
        "/09_data_sources/email_exports/snapshots/", "/09_data_sources/email_exports/backfill/",
        "/11_documents_and_reports/email/", "/09_data_sources/email_exports/index.json/",
    )
    if any(x in pattern for x in excluded) or any(x in pattern for x in ("_conversations/", "conversation_archive", "_daemon.")):
        return False
    if set(parts) & (SKIP | {
        "conversations", "archived_sessions", "rollouts", "turn_states", ".sync_state",
        "secrets", ".ssh", "logs", "auth.json", "credentials.json", "secrets.json",
        ".ds_store", ".netrc", "id_rsa", "id_ed25519",
    }) or any(name.startswith((".env", "rollout-")) for name in parts):
        return False
    if parts[0] in PRIVATE_FOLDED and not any(
            Path(s).parts and Path(s).parts[0].casefold() == parts[0] for s in scopes):
        return False
    if parts[0] == "99_archive" and not archive or parts[0] == "09_data_sources" and not raw:
        return False
    if any(re.match(r"^id_(?:rsa|ed25519|dsa|ecdsa)(?:$|[._-])", item) for item in parts):
        return False
    sensitive = {"auth", "credential", "credentials", "secret", "secrets", "password", "passwords", "passwd",
                 "token", "tokens", "pem", "key", "p12", "pfx", "netrc", "jsonl", "log", "keytab", "keys", "keychain", "keystore", "jks", "kdbx", "p8", "pkcs8", "pkcs12"}
    if any(sensitive.intersection(re.split(r"[^a-z0-9]+", item)) for item in parts):
        return False
    return config or not any(part.startswith(".") for part in parts)


TEXT_TYPES = {".md", ".txt", ".tex", ".yaml", ".yml", ".toml", ".py", ".json"}
METADATA_TYPES = TEXT_TYPES | {".pdf", ".docx", ".odt", ".pptx", ".xlsx", ".csv", ".tsv", ".epub",
                              ".png", ".jpg", ".jpeg", ".svg", ".gif", ".webp", ".mp3", ".mp4", ".wav"}
MAX_BYTES = 2 * 1024 * 1024
FD_BATCH = 64


class Identity(NamedTuple):
    device: int
    inode: int
    mode: int
    links: int
    size: int
    mtime_ns: int
    ctime_ns: int

    @classmethod
    def from_stat(cls, info: os.stat_result) -> Identity:
        return cls(info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size,
                   info.st_mtime_ns, info.st_ctime_ns)


def git_inventory(root: Path, args: list[str], *, stdin: bytes = b"", ignore: bool = False,
                  timeout: float = 12) -> set[Path]:
    command = ["git", *([] if ignore else ["--literal-pathspecs"]), "-C", str(root), *args]
    result = subprocess.run(command, input=stdin, capture_output=True, timeout=timeout,
                            env={k: v for k, v in os.environ.items() if not k.startswith("GIT_")})
    if result.returncode not in ((0, 1) if ignore else (0,)):
        raise ValueError("Could not verify the Git ownership and exclusions of the scope.")
    return {Path(os.fsdecode(value)) for value in result.stdout.split(b"\0") if value}


def ignored(root: Path, paths, timeout: float = 12) -> set[Path]:
    if not paths or not (root / ".git").exists():
        return set()
    names = b"".join(b"./" + os.fsencode(p) + b"\0" for p in paths)
    return git_inventory(root, ["check-ignore", "--no-index", "-z", "--stdin"], stdin=names,
                         ignore=True, timeout=timeout)


def foreign_root(directory: Path | int) -> bool:
    """Test ownership boundaries by marker presence without reading another owner's files."""
    def present(name: str) -> bool:
        try:
            if isinstance(directory, int):
                os.stat(name, dir_fd=directory, follow_symlinks=False)
            else:
                (directory / name).lstat()
        except FileNotFoundError:
            return False
        return True

    # .git files cover linked worktrees and submodules. Bare repositories and
    # Git administrative dirs have no .git child; their HEAD and refs/object
    # store (or commondir) mark a boundary even under an ordinary folder name.
    return present(".git") or present("HEAD") and any(present(p) for p in ("objects", "refs", "commondir", "packed-refs"))


def nested(parent: Path, root: Path, cache: dict[Path, bool]) -> bool:
    if parent not in cache:
        cache[parent] = (parent != root and (nested(parent.parent, root, cache)
                         or parent.is_symlink() or foreign_root(parent)))
    return cache[parent]


class Inventory(dict[Path, Identity]):
    """Stable file identities, with authorization checked again around every read."""
    def __init__(self, root: Path):
        super().__init__()
        self.root = root
        info = root.lstat()
        if not stat.S_ISDIR(info.st_mode):
            raise ValueError("Expected a real vault directory.")
        self.root_identity = (info.st_dev, info.st_ino)
        self.git_identity = self.git_marker()

    def git_marker(self):
        try:
            marker = (self.root / ".git").lstat()
        except FileNotFoundError:
            return None
        if not (stat.S_ISDIR(marker.st_mode) or stat.S_ISREG(marker.st_mode)):
            raise ValueError("Invalid Git ownership marker.")
        return (marker.st_dev, marker.st_ino,
                marker.st_ctime_ns if not stat.S_ISDIR(marker.st_mode) else None)

    def open_file(self, relative: Path) -> int:
        flags = os.O_RDONLY | os.O_NOFOLLOW
        directory = os.open(self.root, flags | os.O_DIRECTORY)
        try:
            info = os.fstat(directory)
            if (info.st_dev, info.st_ino) != self.root_identity:
                raise ValueError("The vault root changed during the query.")
            for part in relative.parts[:-1]:
                child = os.open(part, flags | os.O_DIRECTORY, dir_fd=directory)
                os.close(directory)
                directory = child
                if foreign_root(directory):
                    raise ValueError("A candidate now has another Git owner.")
            fd = os.open(relative.name, flags | os.O_NONBLOCK, dir_fd=directory)
            try:
                if Identity.from_stat(os.fstat(fd)) != self[relative]:
                    raise ValueError("An inventoried file changed before it could be read.")
            except BaseException:
                os.close(fd)
                raise
            return fd
        finally:
            os.close(directory)

    @contextmanager
    def open_batch(self, paths: list[Path]):
        if self.git_marker() != self.git_identity or ignored(self.root, paths):
            raise ValueError("Git ownership or ignore rules changed during the query.")
        with ExitStack() as stack:
            opened = {}
            for path in paths:
                fd = self.open_file(path)
                stack.callback(os.close, fd)
                opened[path] = fd
            try:
                yield opened
            finally:
                # Verify the same ancestry/owner and single-linked inode still
                # name the bytes we actually read before returning any results.
                for path in paths:
                    os.close(self.open_file(path))
                if self.git_marker() != self.git_identity or ignored(self.root, paths):
                    raise ValueError("Git ownership or ignore rules changed during the query.")

    def batches(self, paths):
        ordered = list(paths)
        for start in range(0, len(ordered), FD_BATCH):
            with self.open_batch(ordered[start:start + FD_BATCH]) as opened:
                yield opened


def allowed_inventory(root: Path, scopes: list[str], config: bool, archive: bool, raw: bool,
                      timeout: float = 12, *, names_only: bool = False) -> Inventory:
    """Intersect Git and rg discovery, checking ignored tracked descendants as well."""
    if (os.name != "posix" or not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "pread")
            or not Path("/dev/fd").is_dir() or os.open not in os.supports_dir_fd):
        raise RuntimeError("Fast Finder requires POSIX no-follow file descriptors and /dev/fd.")
    inventory = Inventory(root)
    owners = {root: False}
    for scope in scopes:
        relative = Path(scope)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Scopes must stay inside the vault.")
        target = root / relative
        if not visible(relative, scopes, config, archive, raw) or (
                target != root and nested(target.parent, root, owners)):
            raise ValueError("Scope is private, excluded, or belongs to a different Git owner.")
        try:
            mode = target.lstat().st_mode
        except FileNotFoundError:
            raise ValueError(f"Scope does not exist: {scope}") from None
        if stat.S_ISLNK(mode) or stat.S_ISDIR(mode) and nested(target, root, owners):
            raise ValueError("Scope crosses a symlink or another Git owner.")
    if ignored(root, scopes, timeout):
        raise ValueError("An explicit scope is excluded by the vault's Git ignore rules.")
    roots = scopes or ["."]
    command = ["rg", "--no-config", "--hidden", "--files", "--null"]
    # Positive rg globs override ignore files. Filter allowed types only after
    # discovery. Git reports untracked nested checkouts as directory entries;
    # omit their contents and avoid entering registered submodules as well.
    owned = None
    if (root / ".git").exists():
        owned = git_inventory(root, ["ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", *roots],
                              timeout=timeout)
        for path in owned:
            full = root / path
            if not visible(path, scopes, config, archive, raw) or nested(full.parent, root, owners):
                continue
            try:
                is_dir = stat.S_ISDIR(full.lstat().st_mode)
            except FileNotFoundError:
                continue
            if is_dir:
                nested(full, root, owners)
        for directory, foreign in owners.items():
            if foreign and not owners.get(directory.parent):
                escaped = re.sub(r"([*?{}\[\]\\])", r"\\\1", directory.relative_to(root).as_posix())
                command.extend(["--glob", f"!/{escaped}/**"])
    blocked = [".git", ".obsidian", "node_modules", ".codex_NOTUSE", "__pycache__", ".sync_state", "turn_states"]
    if not config:
        blocked.extend([".codex", ".agents", ".claude"])
    if not raw:
        blocked.append("09_Data_Sources")
    if not archive:
        blocked.append("99_Archive")
    if not any(Path(s).parts and Path(s).parts[0].casefold() in PRIVATE_FOLDED for s in scopes):
        blocked.extend(PRIVATE)
    blocked.extend(["secrets", ".ssh", "conversations", "archived_sessions", "rollouts", "logs"])
    for part in blocked:
        command.extend(["--iglob", f"!**/{part}/**"])
    command.extend(["--iglob", f"!**/{RESTRICTED.as_posix()}/**"])
    result = subprocess.run([*command, "--", *roots], cwd=root, capture_output=True, timeout=timeout)
    if result.returncode not in (0, 1):
        raise ValueError("Could not enumerate the requested scope with ripgrep.")
    names = {Path(os.fsdecode(name)) for name in result.stdout.split(b"\0") if name}
    if owned is not None:
        names.intersection_update(owned)
    names = {path for path in names if visible(path, scopes, config, archive, raw)
             and not nested((root / path).parent, root, owners)}
    names.difference_update(ignored(root, names, timeout))
    formats = METADATA_TYPES if names_only else TEXT_TYPES
    for path in sorted(names):
        if path.suffix.casefold() not in formats:
            continue
        try:
            info = (root / path).lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
            inventory[path] = Identity.from_stat(info)
    if inventory.git_marker() != inventory.git_identity:
        raise ValueError("Git ownership changed during discovery.")
    return inventory


def rg_text(data: dict) -> str:
    return data["text"] if "text" in data else base64.b64decode(data["bytes"]).decode("utf-8", "replace")


def rg_hits(inventory: Inventory, paths, arguments: list[str], deadline: float):
    """Search already-open eligible inodes; rg never reopens names from the vault."""
    with closing(inventory.batches(paths)) as batches:
        for opened in batches:
            mapping = {f"/dev/fd/{fd}": p for p, fd in opened.items()}
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Content scan timed out.")
            with subprocess.Popen(["rg", "--no-config", "--json", "--threads", "1", *arguments, "--", *mapping],
                                  pass_fds=tuple(opened.values()), stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL) as process:
                expired = threading.Event()

                def expire() -> None:
                    expired.set()
                    process.kill()

                timer = threading.Timer(remaining, expire)
                timer.start()
                try:
                    assert process.stdout is not None
                    for line in process.stdout:
                        event = json.loads(line)
                        if event["type"] == "match":
                            hit = event["data"]
                            yield mapping[rg_text(hit["path"])], hit
                    status = process.wait()
                    if expired.is_set():
                        raise TimeoutError("Content scan timed out.")
                    if status not in (0, 1):
                        raise RuntimeError("ripgrep did not complete its scan.")
                finally:
                    timer.cancel()
                    timer.join()
                    if process.poll() is None:
                        process.kill()


def search(root: Path, query: str, *, scopes: list[str] | None = None, limit: int = 10,
           fields: dict[str, str] | None = None, config: bool = False,
           archive: bool = False, raw: bool = False, max_candidates: int = 600,
           timeout: float = 12) -> dict[str, Any]:
    start = time.monotonic()
    root = root.resolve()
    scopes = scopes or []
    terms = terms_for(query)
    if not terms and not fields:
        raise ValueError("Provide search terms or a metadata filter.")
    paths = allowed_inventory(root, scopes, config, archive, raw, timeout)
    roots = scopes or ["."]
    candidates: dict[str, list[tuple[int, str]]] = {}
    partial = False
    for path in paths:
        if not terms or any(term in normalize(str(path)) for term in terms):
            if len(candidates) >= max_candidates:
                partial = True
                break
            candidates[str(path)] = []
    command = ["--ignore-case", "--max-count", "6"]
    for term in terms:
        command.extend(["-e", term_pattern(term)])
    eligible = [p for p, identity in paths.items() if identity.size <= MAX_BYTES]
    try:
        with closing(rg_hits(paths, eligible if terms else [], command, start + timeout)) as scan:
            for path, hit in scan:
                name = str(path)
                if name not in candidates and len(candidates) >= max_candidates:
                    partial = True
                    break
                candidates.setdefault(name, []).append((hit["line_number"], rg_text(hit["lines"]).strip()))
    except TimeoutError:
        partial = True

    def rank(path: Path, fd: int) -> dict[str, Any] | None:
        name = str(path)
        hits = candidates[name]
        fm, prefix, _ = read_note(fd, path)
        for field, value in (fields or {}).items():
            actual = fm.get(field)
            values = actual if isinstance(actual, list) else [actual]
            if normalize(value) not in [normalize(str(v)) for v in values]:
                return None
        title = str(fm.get("title", Path(name).stem))
        headings = " ".join(l for l in prefix.splitlines() if l.startswith("#"))
        pieces = {"title": normalize(title), "path": normalize(name), "headings": normalize(headings),
                  "body": normalize(" ".join(text for _, text in hits))}
        matched = [t for t in terms if any(t in v for v in pieces.values())]
        score = 30 * len(matched) / max(1, len(terms))
        score += sum(weight for t in terms for part, weight in (("title", 8), ("path", 5), ("headings", 3), ("body", 1)) if t in pieces[part])
        status = str(fm.get("status", ""))
        score += {"canonical": 4, "foundational": 4, "active": 2, "draft": 0, "archived": -4}.get(status, 0)
        hits.sort(key=lambda h: (-sum(t in normalize(h[1]) for t in terms), h[0]))
        if hits:
            line, excerpt = hits[0]
        else:
            numbered = list(enumerate(prefix.splitlines(), 1))
            line, excerpt = next(((n, t) for n, t in numbered if t.startswith("#")),
                                 numbered[0] if numbered else (None, ""))
        return {"path": str(root / name), "title": title, "status": status,
                "updated": str(fm.get("updated", "")), "line": line, "excerpt": excerpt[:320],
                "score": round(score, 3), "matched_terms": matched}

    ranked = []
    for opened in paths.batches([Path(name) for name in candidates]):
        for path, fd in opened.items():
            row = rank(path, fd)
            if row is not None:
                ranked.append(row)
    ranked.sort(key=lambda r: r["path"])
    ranked.sort(key=lambda r: (r["score"], r["updated"]), reverse=True)
    return {"query": query, "scope": roots, "total_candidates": len(candidates),
            "matching_candidates": len(ranked), "partial": partial, "max_file_bytes": 2097152,
            "elapsed_ms": round((time.monotonic() - start) * 1000, 1), "results": ranked[:limit]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?", default="")
    parser.add_argument("--root", type=Path, help="Exact OmarOS checkout; default: discover the Git owner of the working directory.")
    parser.add_argument("--path", action="append", default=[])
    parser.add_argument("--field", action="append", default=[], help="key=value; repeat for AND")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--config", action="store_true")
    parser.add_argument("--include-archive", action="store_true")
    parser.add_argument("--include-raw", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.limit <= 200:
        parser.error("limit must be 1–200")
    try:
        fields = dict(item.split("=", 1) for item in args.field)
        result = search(project_root(args.root), args.query, scopes=args.path, limit=args.limit, fields=fields,
                        config=args.config, archive=args.include_archive, raw=args.include_raw)
        print(json.dumps(result, ensure_ascii=False))
    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
        parser.exit(2, f"Fast Finder: {exc}\n")


if __name__ == "__main__":
    main()

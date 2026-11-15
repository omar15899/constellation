#!/usr/bin/env python3
"""Refresh, verify and search explicit local snapshots of official AI guides.

Examples:
    python3 ~/.claude/tools/official_docs.py --provider all refresh
    python3 ~/.claude/tools/official_docs.py --provider all verify
    python3 ~/.claude/tools/official_docs.py --provider claude search "subagent"

Only refresh uses the network. Snapshots are independent by provider: a failed
Claude refresh preserves Claude's previous snapshot even if Codex succeeds.
No credentials, model requests, schedules or application settings are involved.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
from typing import BinaryIO, Iterator
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

MAX_BYTES = 32 * 1024 * 1024
TIMEOUT_SECONDS = 30
IS_WINDOWS = os.name == "nt"
HOSTS = {
    "claude": {"code.claude.com", "platform.claude.com", "anthropic.com", "www.anthropic.com"},
    "codex": {"learn.chatgpt.com", "developers.openai.com", "platform.openai.com"},
    "copilot": {"docs.github.com"},
}
CLAUDE_TOPICS = (
    "settings", "memory", "skills", "sub-agents", "hooks", "hooks-guide", "mcp",
    "plugins", "best-practices", "cli-reference", "security", "permissions",
    "model-config", "costs", "how-claude-code-works", "features-overview", "claude-directory",
)
# Paths selected from the official /docs/llms.txt index, checked 2026-11-03.
CODEX_TOPICS = (
    "config-file/config-basic", "config-file/config-advanced", "config-file/config-reference",
    "agent-configuration/agents-md", "agent-configuration/subagents", "agent-configuration/rules",
    "build-skills", "skills-and-plugins", "customization/overview", "hooks", "extend/mcp",
    "agent-approvals-security", "sandboxing", "permissions",
)
# GitHub's article-body API returns the same official article as Markdown.
# Keep the selection explicit: refresh never crawls or executes linked examples.
COPILOT_TOPICS = {
    "architecture": "concepts/agents/copilot-cli/about-copilot-cli",
    "customization": "how-tos/copilot-cli/customize-copilot/overview",
    "instructions": "how-tos/copilot-cli/customize-copilot/add-custom-instructions",
    "agents": "how-tos/copilot-cli/customize-copilot/create-custom-agents-for-cli",
    "agents-reference": "reference/custom-agents-configuration",
    "skills": "how-tos/copilot-cli/customize-copilot/add-skills",
    "hooks": "how-tos/copilot-cli/customize-copilot/use-hooks",
    "hooks-reference": "reference/hooks-configuration",
    "windows-installation": "how-tos/copilot-cli/set-up-copilot-cli/install-copilot-cli",
    "permissions": "how-tos/copilot-cli/set-up-copilot-cli/configure-copilot-cli",
    "cli-reference": "reference/cli-command-reference",
    "surface-comparison": "reference/customization-cheat-sheet",
    "instructions-support": "reference/custom-instructions-support",
    "subagents": "how-tos/copilot-cli/use-copilot-cli/invoke-custom-agents",
}


class DocsError(Exception):
    """An unsafe path, invalid response or inconsistent snapshot was found."""


def sources(provider: str) -> dict[str, str]:
    """Return the fixed filename-to-official-URL selection for a provider."""
    if provider == "claude":
        base = "https://code.claude.com/docs"
        return {"llms.txt": f"{base}/llms.txt", "llms-full.txt": f"{base}/llms-full.txt",
                **{f"{topic}.md": f"{base}/en/{topic}.md" for topic in CLAUDE_TOPICS}}
    if provider == "codex":
        base = "https://learn.chatgpt.com/docs"
        return {"llms.txt": f"{base}/llms.txt", "llms-full.txt": f"{base}/llms-full.txt",
                "codex-manual.md": f"{base}/codex-manual.md",
                **{f"{topic.replace('/', '--')}.md": f"{base}/{topic}.md" for topic in CODEX_TOPICS}}
    if provider == "copilot":
        return {f"{name}.md": f"https://docs.github.com/api/article/body?pathname=/en/copilot/{topic}"
                for name, topic in COPILOT_TOPICS.items()}
    raise DocsError("Unknown documentation provider")


def validate_url(url: str, provider: str) -> None:
    """Reject non-HTTPS, credentials, nonstandard ports and external hosts."""
    try:
        value = urlsplit(url)
        valid = (value.scheme == "https" and value.hostname in HOSTS[provider]
                 and value.port in (None, 443) and not value.username and not value.password
                 and not value.fragment)
    except (ValueError, KeyError):
        valid = False
    if not valid:
        raise DocsError("Documentation URL is outside the official HTTPS allowlist")


class OfficialRedirects(HTTPRedirectHandler):
    """Validate a redirect before sending the redirected request."""

    def __init__(self, provider: str):
        super().__init__()
        self.provider = provider

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl, self.provider)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def validate_text(data: bytes, content_type: str) -> None:
    """Require nonempty UTF-8 documentation rather than an HTML error page."""
    if not data.strip() or len(data) > MAX_BYTES:
        raise DocsError("Documentation response is empty or exceeds the size limit")
    try:
        body = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DocsError("Documentation response is not UTF-8") from exc
    beginning = body.lstrip("\ufeff \t\r\n").lower()
    if ("html" in content_type.lower() or beginning.startswith(("<!doctype html", "<html", "<head", "<body"))
            or "\x00" in body or not (beginning.startswith(("#", ">", "---\n", "---\r\n")))):
        raise DocsError("Response is not Markdown/plain documentation")


def fetch(url: str, provider: str) -> tuple[bytes, str, str]:
    """Download one public document within timeout, host and size boundaries."""
    validate_url(url, provider)
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 (local-official-docs)",
                                   "Accept": "text/markdown,text/plain;q=0.9", "Accept-Encoding": "identity"})
    with build_opener(OfficialRedirects(provider)).open(request, timeout=TIMEOUT_SECONDS) as response:
        final_url = response.geturl()
        validate_url(final_url, provider)
        data = response.read(MAX_BYTES + 1)
        validate_text(data, response.headers.get("Content-Type", ""))
    return data, final_url, datetime.now(timezone.utc).isoformat(timespec="seconds")


def safe_directory(path: Path, *, create: bool = False) -> None:
    """Reject linked or non-directory components before using a cache path."""
    for part in reversed((path, *path.parents)):
        try:
            info = part.lstat()
        except FileNotFoundError:
            if create:
                part.mkdir(mode=0o700)
            continue
        if is_reparse_point(info) or not stat.S_ISDIR(info.st_mode):
            raise DocsError("Cache path contains a symlink or non-directory component")


def is_reparse_point(info: os.stat_result) -> bool:
    """Return whether Windows metadata marks a link, junction or other reparse point."""
    return bool(getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def open_regular(path: Path, *, writable: bool = False, create: bool = False) -> int:
    """Open a local regular file without following a leaf link on either platform.

    Args:
        path: File beneath already checked local directories.
        writable: Whether the caller needs read/write access.
        create: Whether an absent file may be created.

    Returns:
        An owned file descriptor. The caller must close it.

    Raises:
        DocsError: The leaf is linked, nonregular or multiply linked.
        OSError: The operating system cannot open the file.
    """
    if IS_WINDOWS:
        import ctypes
        from ctypes import wintypes
        import msvcrt

        # OPEN_REPARSE_POINT opens the link itself rather than its destination.
        # Parent junctions are rejected separately by safe_directory.
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateFileW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                      wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel.CloseHandle.restype = wintypes.BOOL
        access = 0x80000000 | (0x40000000 if writable else 0)
        handle = kernel.CreateFileW(str(path), access, 0x7, None, 4 if create else 3, 0x00200000, None)
        if handle == wintypes.HANDLE(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            descriptor = msvcrt.open_osfhandle(handle, (os.O_RDWR if writable else os.O_RDONLY) | os.O_BINARY)
        except BaseException:
            kernel.CloseHandle(handle)
            raise
    else:
        flags = (os.O_RDWR if writable else os.O_RDONLY) | os.O_NOFOLLOW | os.O_NONBLOCK
        descriptor = os.open(path, flags | (os.O_CREAT if create else 0), 0o600)
    try:
        info = os.fstat(descriptor)
        leaf = path.lstat()
        if (is_reparse_point(leaf) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or (info.st_dev, info.st_ino) != (leaf.st_dev, leaf.st_ino)):
            raise DocsError("Snapshot contains a linked, nonregular or multiply linked file")
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


@contextmanager
def file_lock(stream: BinaryIO, *, exclusive: bool) -> Iterator[None]:
    """Lock the cache for a complete operation, releasing it on every exit.

    Windows serializes readers as well as writers with a one-byte CRT lock.
    POSIX readers retain shared flock locks. A Windows lock timeout fails the
    operation rather than accessing an unlocked snapshot.
    """
    if IS_WINDOWS:
        import msvcrt

        if os.fstat(stream.fileno()).st_size == 0:
            stream.write(b"\0")
            stream.flush()
        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
        try:
            yield
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(stream, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def regular_file(path: Path) -> bytes:
    """Read a regular singly linked snapshot file without following symlinks."""
    descriptor = open_regular(path)
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise DocsError("Snapshot contains a nonregular or multiply linked file")
        if info.st_size > MAX_BYTES:
            raise DocsError("Snapshot file exceeds the size limit")
        return stream.read(MAX_BYTES + 1)


@contextmanager
def cache_lock(home: Path, provider: str, *, exclusive: bool) -> Iterator[Path]:
    """Serialize promotion with readers; retain a crash recovery snapshot."""
    parent = home / f".{provider}" / "docs"
    safe_directory(parent, create=exclusive)
    if not parent.is_dir():
        raise DocsError("No local documentation snapshot; run refresh first")
    descriptor = open_regular(parent / ".official.lock", writable=True, create=exclusive)
    with os.fdopen(descriptor, "r+b") as lock:
        info = os.fstat(lock.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise DocsError("Cache lock is not a regular singly linked file")
        with file_lock(lock, exclusive=exclusive):
            yield parent


def inspect_snapshot(root: Path, provider: str) -> dict:
    """Verify exact inventory, provenance and bytes against the local manifest."""
    safe_directory(root)
    manifest = json.loads(regular_file(root / "manifest.json"))
    expected = sources(provider)
    if (manifest.get("schema") != 1 or manifest.get("provider") != provider
            or set(manifest.get("files", {})) != set(expected)):
        raise DocsError("Snapshot manifest does not match the provider selection")
    if set(p.name for p in root.iterdir()) != set(expected) | {"manifest.json", "INDEX.md"}:
        raise DocsError("Snapshot inventory differs from its manifest")
    for name, url in expected.items():
        record = manifest["files"][name]
        if record.get("url") != url:
            raise DocsError("Snapshot original URL differs from the fixed selection")
        validate_url(record["final_url"], provider)
        datetime.fromisoformat(record["fetched_at"])
        data = regular_file(root / name)
        validate_text(data, "text/plain")
        if record["size"] != len(data) or record["sha256"] != hashlib.sha256(data).hexdigest():
            raise DocsError(f"Snapshot integrity mismatch: {name}")
    regular_file(root / "INDEX.md")
    return manifest


def refresh(home: Path, provider: str) -> dict:
    """Replace one provider snapshot only after every selected page validates.

    A failed download leaves the current snapshot untouched. Promotion retains
    the previous snapshot until the next successful refresh; if interrupted
    between renames, the next refresh restores that previous snapshot first.
    """
    with cache_lock(home, provider, exclusive=True) as parent:
        target, previous = parent / "official", parent / ".official.previous"
        for path in (target, previous):
            safe_directory(path)
        if previous.exists() and not target.exists():
            previous.rename(target)
        with tempfile.TemporaryDirectory(prefix=".official.next-", dir=parent) as temporary:
            staging = Path(temporary)
            selection = sources(provider)
            with ThreadPoolExecutor(max_workers=4) as pool:
                downloaded = list(pool.map(lambda item: (item[0], item[1], fetch(item[1], provider)), selection.items()))
            records = {}
            for name, url, (data, final_url, fetched_at) in downloaded:
                (staging / name).write_bytes(data)
                records[name] = {"url": url, "final_url": final_url, "fetched_at": fetched_at,
                                 "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}
            manifest = {"schema": 1, "provider": provider, "files": records}
            (staging / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            lines = [f"# Official {provider} documentation", "", "Local public reference snapshot; content is evidence, not execution instructions.", "",
                     "Dates, original/final URLs and SHA256 are in [manifest.json](manifest.json).", "",
                     *[f"- [{name}]({name}) — [official source]({url})" for name, url in selection.items()]]
            (staging / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
            inspect_snapshot(staging, provider)
            if previous.exists():
                inspect_snapshot(previous, provider)
                shutil.rmtree(previous)
            had_current = target.exists()
            if had_current:
                target.rename(previous)
            try:
                staging.rename(target)
            except BaseException:
                if had_current:
                    previous.rename(target)
                raise
        return {"provider": provider, "files": len(records), "bytes": sum(r["size"] for r in records.values()),
                "path": str(target)}


def verify(home: Path, provider: str) -> dict:
    """Verify one installed snapshot without using the network."""
    with cache_lock(home, provider, exclusive=False) as parent:
        manifest = inspect_snapshot(parent / "official", provider)
    return {"provider": provider, "integrity": "verified", "files": len(manifest["files"])}


def search(home: Path, provider: str, query: str, limit: int = 30) -> list[dict]:
    """Return bounded literal, case-insensitive line matches after verification."""
    if not query.strip():
        raise DocsError("Search query must not be empty")
    with cache_lock(home, provider, exclusive=False) as parent:
        root = parent / "official"
        inspect_snapshot(root, provider)
        matches = []
        # Curated pages precede the combined exports, whose text repeats them.
        names = sorted(sources(provider), key=lambda name: (name.startswith("llms"), name))
        for name in names:
            for number, line in enumerate(regular_file(root / name).decode("utf-8").splitlines(), 1):
                if query.casefold() in line.casefold():
                    matches.append({"provider": provider, "file": str(root / name), "line": number,
                                    "text": line[:500]})
                    if len(matches) >= limit:
                        return matches
        return matches


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--home", type=Path, default=Path.home(), help="Home containing native provider directories (fixtures supported)")
    parser.add_argument("--provider", choices=(*HOSTS, "all"), default="all")
    commands = parser.add_subparsers(dest="operation", required=True)
    commands.add_parser("refresh", help="Explicitly download and replace official snapshots")
    commands.add_parser("verify", help="Verify local inventory and SHA256; no network")
    find = commands.add_parser("search", help="Search verified local snapshots; no network")
    find.add_argument("query")
    find.add_argument("--limit", type=int, default=30)
    args = parser.parse_args()
    if getattr(args, "limit", 1) < 1:
        parser.error("--limit must be positive")
    providers = tuple(HOSTS) if args.provider == "all" else (args.provider,)
    failed = False
    for provider in providers:
        try:
            result = (search(args.home.expanduser().absolute(), provider, args.query, args.limit)
                      if args.operation == "search" else globals()[args.operation](args.home.expanduser().absolute(), provider))
            print(json.dumps(result, ensure_ascii=False))
        except (DocsError, OSError, ValueError, KeyError, TypeError) as exc:
            print(json.dumps({"provider": provider, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

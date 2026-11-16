#!/usr/bin/env bash
# secret_scan.sh — constellation secret gate (Pre/PostToolUse + manual).
#
# PreToolUse(Write|Edit|MultiEdit): scans the PENDING content/new_string and,
#   on exit 2, the write is DENIED — the secret never reaches disk.
# PostToolUse(Write|Edit|MultiEdit): scans the written file_path.
# Either context also scans the changed index blobs, not the working copy.
# Protected filenames are refused before opening them. Exit 0 = clean;
# exit 2 = blocked or unable to verify. Diagnostics never quote source text.
#
# Pattern matching runs in embedded python3 (portable on macOS BSD grep, which
# lacks -P/PCRE). Detection is tuned for LOW false positives: it does NOT do
# generic high-entropy scanning, because this constellation is full of
# content-addressed SHA roots that such a detector would flag constantly.
set -uo pipefail

# Keep the event on stdin, never in process arguments or a temporary file.
exec python3 /dev/fd/3 3<<'PY'
import sys, os, re, json, subprocess
from pathlib import Path

TAG = "[constellation:secret_scan]"
MAX_BYTES = 5_000_000
payload = sys.stdin.read() if not sys.stdin.isatty() else ""

def emit(m): sys.stderr.write(f"{TAG} {m}\n")

fail = False

def protected(path):
    parts = tuple(part.lower() for part in Path(path).parts)
    b = parts[-1] if parts else ""
    private_tree = ("_conversations" in parts
                    or any(pair in {(".codex", "sessions"), (".codex", "archived_sessions"),
                                    (".claude", "run")} for pair in zip(parts, parts[1:])))
    return (b.startswith(".env") or b.endswith((".pem", ".key"))
            or b == "credentials.json" or (b.startswith("rollout") and b.endswith(".jsonl"))
            or private_tree)

def refuse_path(path, *, follow_links=False):
    global fail
    if protected(path) or (follow_links and protected(str(Path(path).resolve()))):
        emit(f"BLOCKED: protected private/secrets path {path!r}; contents were not read.")
        fail = True
        return True
    return False

def git(*args, check=True):
    result = subprocess.run(["git", *args], capture_output=True, timeout=5,
                            env=dict(os.environ, LC_ALL="C"))
    if check and result.returncode:
        raise RuntimeError("git inspection failed")
    return result

KEY_BLOCK = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
PREFIX = re.compile(
    r"((?:AKIA|ASIA)[0-9A-Z]{12,}|ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}"
    r"|github_pat_[A-Za-z0-9_]{20,}|sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,}"
    r"|xox[baprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_\-]{30,})")
CRED = (r"api[_-]?key|secret(?:[_-]?key)?|client[_-]?secret|access[_-]?key"
        r"|secret[_-]?access[_-]?key|auth[_-]?token|access[_-]?token|token"
        r"|password|passwd|pwd|credential|private[_-]?key|t212[_-]?key"
        r"|broker[_-]?(?:key|secret|token)")
# code: a credential name = a QUOTED literal (full span, spaces ok), len>=8
ASSIGN_QUOTED = re.compile(rf"""(?i)\b({CRED})\b["']?\s*[:=]\s*["']([^"'\n]{{8,}})["']""")
# config/dotenv: KEY = value or KEY: value, quoted or not
ASSIGN_BARE = re.compile(rf"""(?i)^\s*(?:export\s+)?([A-Za-z0-9_.\-]*?(?:{CRED})[A-Za-z0-9_.\-]*)\s*[:=]\s*["']?([^\s"'#]{{8,}})["']?\s*$""")
PLACEHOLDER = re.compile(
    r"(?i)^(your[_-]?\w*|examples?|changeme|placeholder|dummy|redacted|sample"
    r"|none|null|true|false|test|secret|password|passwd|token|apikey|api[_-]?key|key"
    r"|<.*>|\$\{.*\}|\$[a-z_]+|x{3,}|\*{3,}|\.{3,}|0+|\d+)$")

CODE_EXT = {".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs", ".java", ".go",
            ".rb", ".rs", ".c", ".h", ".cpp", ".cc", ".php", ".scala", ".kt",
            ".swift", ".sh", ".bash", ".zsh"}
DOC_EXT = {".md", ".rst", ".adoc"}

def is_placeholder(v):
    return bool(PLACEHOLDER.match(v.strip())) or len(set(v)) <= 3

def secretish(v):
    # config values: ignore URLs/paths and short descriptive tokens.
    if re.match(r"^(https?://|ftp://|[./~]|[A-Za-z]:\\)", v):
        return False
    if len(v) >= 20:
        return True
    if len(v) >= 12 and re.search(r"[A-Za-z]", v) and re.search(r"\d", v):
        return True
    return bool(PREFIX.search(v))

def kind(path):
    b = os.path.basename(path)
    if b == ".env" or b.startswith(".env."):
        return "config"
    _, ext = os.path.splitext(b)
    ext = ext.lower()
    if ext in CODE_EXT:
        return "code"
    if ext in DOC_EXT:
        return "doc"
    return "config"  # .yaml/.json/.ini/.cfg/.toml/.txt/no-ext → treat as config

def scan(path, text):
    global fail
    k = kind(path)
    for i, line in enumerate(text.splitlines(), 1):
        if KEY_BLOCK.search(line):
            emit(f"BLOCKED: private key material in {path!r}:{i}"); fail = True
        m = PREFIX.search(line)
        if m:
            emit(f"BLOCKED: credential-prefixed token in {path!r}:{i}")
            fail = True
        if k == "doc":
            continue  # docs: only hard tokens/keys, to avoid flagging tutorials
        for am in ASSIGN_QUOTED.finditer(line):
            if not is_placeholder(am.group(2)):
                emit(f"BLOCKED: secret-like assignment in {path!r}:{i}")
                fail = True
        if k == "config":
            bm = ASSIGN_BARE.match(line)
            if bm and not is_placeholder(bm.group(2)) and secretish(bm.group(2)):
                emit(f"BLOCKED: secret-like config entry in {path!r}:{i}")
                fail = True

def scan_bounded(path, content):
    if len(content) > MAX_BYTES:
        raise RuntimeError("content exceeds scan limit")
    text = content.decode("utf-8", errors="replace") if isinstance(content, bytes) else content
    scan(path, text)

def main():
    global fail
    data = json.loads(payload) if payload.strip() else {}
    if not isinstance(data, dict):
        raise ValueError("invalid event")
    if data.get("cwd"):
        os.chdir(data["cwd"])
    ti = data.get("tool_input") or {}
    fp = ti.get("file_path")
    pending = []
    for name in ("content", "new_string"):
        if isinstance(ti.get(name), str):
            pending.append(ti[name])
    for edit in ti.get("edits") or []:
        if isinstance(edit, dict) and isinstance(edit.get("new_string"), str):
            pending.append(edit["new_string"])
    if not (fp and refuse_path(fp, follow_links=True)):
        # PostToolUse must inspect the complete result, including context that
        # could combine with an inserted fragment to form a credential.
        if fp and data.get("hook_event_name") == "PostToolUse":
            path = Path(fp)
            if path.is_file():
                with path.open("rb") as source:
                    scan_bounded(fp, source.read(MAX_BYTES + 1))
        elif pending:
            scan_bounded(fp or "<pending>", "\n".join(pending))
        elif fp and Path(fp).is_file():
            with open(fp, "rb") as source:
                scan_bounded(fp, source.read(MAX_BYTES + 1))

    repo = git("rev-parse", "--show-toplevel", check=False)
    if repo.returncode:
        if b"not a git repository" in repo.stderr:
            return
        raise RuntimeError("cannot determine git context")
    os.chdir(os.fsdecode(repo.stdout.rstrip(b"\n")))
    changed = set(git("diff", "--cached", "--name-only", "-z", "--diff-filter=ACMRTUXB").stdout.split(b"\0"))
    changed.discard(b"")
    # Read metadata first so protected names never reach cat-file. NUL records
    # preserve spaces, tabs and newlines in Git paths.
    entries = git("ls-files", "--stage", "-z").stdout.split(b"\0")
    for entry in entries:
        if not entry:
            continue
        metadata, raw_path = entry.split(b"\t", 1)
        if raw_path not in changed:
            continue
        mode, oid, stage = metadata.split()
        path = os.fsdecode(raw_path)
        if refuse_path(path):
            continue
        if stage != b"0":
            raise RuntimeError("unmerged index")
        if mode == b"160000":
            continue  # A gitlink is a commit reference, not file contents.
        object_id = oid.decode("ascii")
        if int(git("cat-file", "-s", object_id).stdout) > MAX_BYTES:
            raise RuntimeError("staged content exceeds scan limit")
        scan_bounded(f"index:{path}", git("cat-file", "blob", object_id).stdout)

try:
    main()
except Exception as exc:
    # Error strings and tracebacks can contain event data or source lines.
    emit(f"BLOCKED: secret verification could not finish ({type(exc).__name__}); inspect hook inputs, file size and Git state locally.")
    fail = True

if fail:
    emit("Remove the secret; use an env var or secrets manager; then re-run.")
    sys.exit(2)
sys.exit(0)
PY

#!/usr/bin/env bash
# secret_scan.sh — constellation secret gate (Pre/PostToolUse + manual).
#
# PreToolUse(Write|Edit|MultiEdit): scans the PENDING content/new_string and,
#   on exit 2, the write is DENIED — the secret never reaches disk.
# PostToolUse(Write|Edit|MultiEdit): scans the written file_path.
# Either context, and when run inside a git work tree, also scans the staged
# diff. Exit 0 = clean, exit 2 = block (Claude Code feeds stderr back).
#
# Pattern matching runs in embedded python3 (portable on macOS BSD grep, which
# lacks -P/PCRE). Detection is tuned for LOW false positives: it does NOT do
# generic high-entropy scanning, because this constellation is full of
# content-addressed SHA roots that such a detector would flag constantly.
set -uo pipefail

payload=""
if [ ! -t 0 ]; then payload="$(cat 2>/dev/null || true)"; fi

python3 - "$payload" <<'PY'
import sys, os, re, json, subprocess

TAG = "[constellation:secret_scan]"
MAX_BYTES = 5_000_000
payload = sys.argv[1] if len(sys.argv) > 1 else ""

def emit(m): sys.stderr.write(f"{TAG} {m}\n")

# (path, text-or-None). text!=None means scan that text (pending content);
# text==None means read path from disk.
targets, staged = [], []

if payload.strip():
    try:
        d = json.loads(payload)
        ti = d.get("tool_input") or {}
        fp = ti.get("file_path")
        pending = []
        if isinstance(ti.get("content"), str):
            pending.append(ti["content"])
        if isinstance(ti.get("new_string"), str):
            pending.append(ti["new_string"])
        for e in (ti.get("edits") or []):
            if isinstance(e, dict) and isinstance(e.get("new_string"), str):
                pending.append(e["new_string"])
        if pending:
            targets.append((fp or "<pending>", "\n".join(pending)))
        elif fp and os.path.isfile(fp):
            targets.append((fp, None))
    except Exception:
        pass

in_git = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"],
                        capture_output=True).returncode == 0
if in_git:
    out = subprocess.run(["git", "diff", "--cached", "--name-only"],
                         capture_output=True, text=True)
    staged = [l.strip() for l in out.stdout.splitlines() if l.strip()]
    for f in staged:
        if os.path.isfile(f):
            targets.append((f, None))

fail = False

# .env by filename (written or staged)
for f in [t[0] for t in targets] + staged:
    b = os.path.basename(f)
    if b == ".env" or b.startswith(".env."):
        emit(f"BLOCKED: '{f}' is an environment secrets file — never stage/commit it.")
        fail = True

KEY_BLOCK = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
PREFIX = re.compile(
    r"(AKIA[0-9A-Z]{12,}|ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}"
    r"|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9]{20,}"
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
            emit(f"BLOCKED: private key material in {path}:{i}"); fail = True
        m = PREFIX.search(line)
        if m:
            emit(f"BLOCKED: credential-prefixed token in {path}:{i} (starts {m.group(0)[:6]}…)")
            fail = True
        if k == "doc":
            continue  # docs: only hard tokens/keys, to avoid flagging tutorials
        for am in ASSIGN_QUOTED.finditer(line):
            if not is_placeholder(am.group(2)):
                emit(f"BLOCKED: secret-like assignment in {path}:{i} — {am.group(1)} = <{len(am.group(2))} chars, quoted>")
                fail = True
        if k == "config":
            bm = ASSIGN_BARE.match(line)
            if bm and not is_placeholder(bm.group(2)) and secretish(bm.group(2)):
                emit(f"BLOCKED: secret-like config entry in {path}:{i} — {bm.group(1)}=<{len(bm.group(2))} chars>")
                fail = True

for path, text in targets:
    if text is None:
        try:
            if os.path.getsize(path) > MAX_BYTES:
                continue
            with open(path, "r", errors="ignore") as fh:
                text = fh.read()
        except Exception:
            continue
    else:
        text = text[:MAX_BYTES]
    if "\x00" in text[:2048]:
        continue
    scan(path, text)

if fail:
    emit("Remove the secret; use an env var or secrets manager; then re-run.")
    sys.exit(2)
sys.exit(0)
PY

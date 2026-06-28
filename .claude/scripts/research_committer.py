#!/usr/bin/env python3
"""research_committer.py — policy-driven, scope-granular, auditable committer.

Git is part of the research ledger: every commit must reconstruct WHAT changed,
WHY, with WHAT evidence, WHICH checks passed, and WHICH artifacts back it. This
committer enforces that across the constellation's independent git surfaces.

It is the policy-driven evolution of constellation_commit.py: it reads
registry/repo_commit_policy.yaml, groups a repo's changes into scopes, runs
per-repo checks before each commit, writes a verbose traceable message, and
pushes only to the expected branch when policy + flags allow. Dry-run is the
default; nothing is applied or pushed unless asked.

Usage:
    research_committer.py [--apply] [--push] [--repo ID|PATH ...]
                          [--task ID] [--run-class CLASS]
                          [--message-subject "..."] [--scope SCOPE ...]
                          [--include-prestaged] [--allow-branch-mismatch]
                          [--lever ID] [--session ID]

Defaults: dry-run (no staging mutation, no commit, no push), all dirty repos.

Hard rules (enforced, not advisory):
  - dry-run never mutates the real index (operates on a throwaway GIT_INDEX_FILE);
  - never `git add .` / `git add -A` from a parent — staging is by explicit pathspec;
  - never mixes two repos in one commit (one `git -C <repo>` surface per commit);
  - never mixes two scopes in one commit (one commit per scope);
  - pre-staged files not produced by this run ABORT the repo unless --include-prestaged;
  - a staged secret / .env / key / token ABORTS the commit;
  - a failed check ABORTS that scope's commit (never declares success);
  - push refused when HEAD != expected_branch (unless --allow-branch-mismatch);
  - dry_run_only repos are never applied;
  - unclassifiable files are left out and reported, never committed;
  - no `--force`, no `--no-verify`.

Stdlib only. On internal error, reports and exits non-zero — never commits past
a failure.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TAG = "[constellation:research_committer]"
GITHUB_ROOT = Path.home() / "GitHub"
POLICY_FILE = GITHUB_ROOT / ".claude" / "registry" / "repo_commit_policy.yaml"
RUN_CLASSES = {"control-plane", "diagnostic", "research", "deployable", "production"}

KEY_BLOCK = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
TOKEN = re.compile(
    r"(AKIA[0-9A-Z]{12,}|ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}"
    r"|sk-[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"
    r"|xox[baprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_\-]{30,})"
)
SENSITIVE_NAME = re.compile(r"(?i)(^|/)(\.env(\.|$)|.*\.(pem|key|p12|pfx|keystore)$|"
                            r"id_rsa|id_ed25519|credentials(\.json)?$|secrets?\.(ya?ml|json|toml))")
ARTIFACT_SUFFIX = re.compile(r"(?i)\.(csv|parquet|npy|npz|feather|pkl|pickle|h5|hdf5|joblib|png|jpg|jpeg|pdf|zip|gz|bin)$")
# selective allow_artifacts permits only light figures/tables, never heavy blobs.
ARTIFACT_ALLOWLIST = re.compile(r"(?i)\.(png|jpg|jpeg|svg|csv|json|md)$")
TODO_MARK = re.compile(r"(?<![A-Za-z])(TODO|FIXME|XXX|TKTK)[:(]")
# Byte-level secret patterns — scanned over raw staged blob bytes (NOT the
# textual diff), so binary / .gitattributes -diff files cannot hide a secret.
KEY_BLOCK_B = re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----")
TOKEN_B = re.compile(
    rb"(AKIA[0-9A-Z]{12,}|ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}"
    rb"|sk-[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"
    rb"|xox[baprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_\-]{30,})"
)


def artifact_allowed(rel: str, pol: dict) -> bool:
    aa = pol.get("allow_artifacts")
    if aa is True:
        return True
    if aa == "selective":
        return bool(ARTIFACT_ALLOWLIST.search(rel))
    return False


def emit(m: str) -> None:
    sys.stderr.write(f"{TAG} {m}\n")


# --------------------------------------------------------------------------- git
def git(repo: Path, *args: str, index_file: str | None = None,
        binary: bool = False) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    # Literal pathspecs: a filename containing * ? [ must never glob-expand and
    # sweep in unrelated files (otherwise `git add -- 'a*'` over-matches).
    env["GIT_LITERAL_PATHSPECS"] = "1"
    if index_file:
        env["GIT_INDEX_FILE"] = index_file
    if binary:
        return subprocess.run(["git", "-C", str(repo), *args],
                              capture_output=True, env=env)
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True, env=env)


def is_git_repo(p: Path) -> bool:
    return p.exists() and git(p, "rev-parse", "--is-inside-work-tree").returncode == 0


def toplevel(p: Path) -> Path | None:
    r = git(p, "rev-parse", "--show-toplevel")
    return Path(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else None


def branch_of(repo: Path) -> str:
    return git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def temp_index_for(repo: Path) -> str | None:
    """A throwaway index seeded from HEAD (NOT from the real index), so staging,
    checks, and the commit itself see exactly HEAD + this scope's paths — the
    real index (and any pre-staged content in it) is never read or mutated."""
    try:
        fd, tmp = tempfile.mkstemp(prefix="rc_idx_")
        os.close(fd)
        os.unlink(tmp)  # let git create it fresh
        # seed from HEAD if there is one; on an unborn branch leave it empty
        if git(repo, "rev-parse", "--verify", "-q", "HEAD").returncode == 0:
            git(repo, "read-tree", "HEAD", index_file=tmp)
        return tmp
    except Exception:
        return None


# ------------------------------------------------------------------ yaml parser
def _coerce(v: str):
    s = v.strip()
    if s.startswith("[") and s.endswith("]"):       # inline flow list [a, b, c]
        inner = s[1:-1].strip()
        return [_coerce(x) for x in inner.split(",")] if inner else []
    s = s.strip('"').strip("'")
    if s in ("true", "True"):
        return True
    if s in ("false", "False"):
        return False
    if s in ("null", "~", ""):
        return None
    return s


def parse_yaml(text: str):
    """Minimal recursive-descent parser for the YAML subset used by the policy
    file: nested maps, `- ` scalar lists, and scalars. Stdlib only — same spirit
    as hooks/_levers.py. NOT a general YAML implementation."""
    def strip_comment(s: str) -> str:
        # strip an inline '#'/' #' comment, but not one inside quotes
        out, q = [], None
        i = 0
        while i < len(s):
            c = s[i]
            if q:
                out.append(c)
                if c == q:
                    q = None
            elif c in ("'", '"'):
                q = c
                out.append(c)
            elif c == "#" and (i == 0 or s[i - 1] == " "):
                break
            else:
                out.append(c)
            i += 1
        return "".join(out)

    lines: list[tuple[int, str]] = []
    for raw in text.splitlines():
        raw = raw.replace("\t", "    ")  # tabs -> 4 spaces (never silently drop)
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        line = strip_comment(raw).rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        lines.append((indent, line.strip()))

    pos = 0

    def block(bi: int):
        nonlocal pos
        if lines[pos][1].startswith("- "):
            result: list = []
            while pos < len(lines) and lines[pos][0] == bi and lines[pos][1].startswith("- "):
                result.append(_coerce(lines[pos][1][2:]))
                pos += 1
            return result
        result_d: dict = {}
        while pos < len(lines) and lines[pos][0] == bi and not lines[pos][1].startswith("- "):
            content = lines[pos][1]
            key, _, val = content.partition(":")
            key, val = key.strip(), val.strip()
            pos += 1
            if val == "":
                # a value block follows: a flush-or-deeper '- ' list, or a
                # deeper nested map. Otherwise the value is null.
                if pos < len(lines):
                    ni, nl = lines[pos][0], lines[pos][1]
                    if nl.startswith("- ") and ni >= bi:
                        result_d[key] = block(ni)
                    elif ni > bi:
                        result_d[key] = block(ni)
                    else:
                        result_d[key] = None
                else:
                    result_d[key] = None
            else:
                result_d[key] = _coerce(val)
        return result_d

    return block(lines[0][0]) if lines else {}


def load_policy() -> dict:
    pf = os.environ.get("RC_POLICY_FILE")
    global POLICY_FILE
    if pf:
        POLICY_FILE = Path(os.path.expanduser(pf))
    if not POLICY_FILE.exists():
        return {"default": {"conservative": True, "auto_push": False,
                            "dry_run_only": False, "checks": ["secret_scan"]},
                "repos": {}}
    text = POLICY_FILE.read_text()
    pol = parse_yaml(text)
    # Fail loud on a half-parsed policy: if the file declares repos but parsing
    # produced none, governance would silently fall to defaults — refuse.
    if re.search(r"(?m)^repos:\s*$", text) and not (isinstance(pol.get("repos"), dict) and pol["repos"]):
        raise SystemExit(f"{TAG} policy parse error: 'repos:' present but no repos parsed "
                         f"from {POLICY_FILE} — refusing to run on a half-parsed policy.")
    return pol


# Lists in the policy may parse as dict {} when empty; normalise.
def _as_list(v):
    if isinstance(v, list):
        return v
    if isinstance(v, dict):
        return list(v.keys())
    if v is None:
        return []
    return [v]


def policy_for(repo: Path, policy: dict) -> dict:
    default = dict(policy.get("default", {}) or {})
    repos = policy.get("repos", {}) or {}
    top = toplevel(repo)
    match = None
    for rid, cfg in repos.items():
        if not isinstance(cfg, dict):
            continue
        p = cfg.get("path", "")
        rp = Path(os.path.expanduser(p)) if p else None
        rt = toplevel(rp) if rp and rp.exists() else None
        # Identity is by git toplevel / path ONLY — never by basename. A scratch
        # dir merely NAMED like a registered repo must not inherit its auto_push.
        if (rt and top and rt == top) or (rp and top and rp == top):
            match = (rid, cfg)
            break
    merged = dict(default)
    if match:
        merged.update({k: v for k, v in match[1].items() if v is not None})
        merged["id"] = match[0]
        merged["conservative"] = bool(match[1].get("conservative", False))
    else:
        merged["id"] = repo.name
        merged["conservative"] = True
        merged["dry_run_only"] = merged.get("dry_run_only", False)
        merged["auto_push"] = False
    merged["checks"] = _as_list(merged.get("checks", ["secret_scan"]))
    # Non-negotiable floor: secret scanning can never be disabled by an empty or
    # malformed policy field. It always runs, first.
    if "secret_scan" not in merged["checks"]:
        merged["checks"] = ["secret_scan", *merged["checks"]]
    merged["include"] = _as_list(merged.get("include", []))
    merged["exclude"] = _as_list(merged.get("exclude", []))
    return merged


# --------------------------------------------------------------- scope mapping
SCOPE_RULES = [
    ("hooks", re.compile(r"(^|/)\.claude/hooks/")),
    ("commands", re.compile(r"(^|/)\.claude/commands/")),
    ("contracts", re.compile(r"(^|/)\.claude/contracts/")),
    ("registry", re.compile(r"(^|/)\.claude/registry/|(^|/)registry/")),
    ("scripts", re.compile(r"(^|/)\.claude/scripts/|(^|/)scripts/")),
    ("docs", re.compile(r"(^|/)\.claude/docs/|(^|/)docs/")),
    ("tests", re.compile(r"(^|/)tests?/|(^|/)test_[^/]+\.py$|_test\.py$|\.test\.[tj]sx?$")),
    ("reports", re.compile(r"(^|/)(reports?|outputs?|results?)/")),
    ("research-code", re.compile(r"(^|/)(research|research_algorithms|src)/.*\.(py|ipynb)$")),
]


def classify_scope(rel: str) -> str:
    for scope, rx in SCOPE_RULES:
        if rx.search(rel):
            return scope
    if ARTIFACT_SUFFIX.search(rel):
        return "artifacts"
    base = os.path.basename(rel)
    if rel.endswith((".json", ".toml", ".cfg", ".ini", ".yaml", ".yml")) or base in (".gitignore", "CLAUDE.md", "QUANTOS.md", "README.md"):
        # top-level markdown docs already caught by docs/ rule; these are config-ish
        if base.endswith(".md"):
            return "docs"
        return "config"
    if rel.endswith(".md"):
        return "docs"
    if rel.endswith(".py"):
        return "research-code"
    return "unknown"


def included(rel: str, pol: dict) -> bool:
    inc = pol.get("include", [])
    exc = pol.get("exclude", [])
    for e in exc:
        if e and (rel == e.rstrip("/") or rel.startswith(e)):
            return False
    if inc:
        return any(rel == i.rstrip("/") or rel.startswith(i) for i in inc)
    return True


# --------------------------------------------------------------------- status
def porcelain(repo: Path) -> tuple[list[str], list[str], list[str]]:
    """Return (working_changed, prestaged, untracked) relative paths.
    working_changed = files with working-tree changes the committer may stage."""
    # -uall expands untracked DIRECTORIES into individual files; without it git
    # collapses a brand-new dir to 'dir/', which would mis-classify as unknown.
    out = git(repo, "status", "--porcelain", "-uall", "-z").stdout
    working, prestaged, untracked = [], [], []
    parts = out.split("\0")
    i = 0
    while i < len(parts):
        ent = parts[i]
        if not ent:
            i += 1
            continue
        x, y, path = ent[0], ent[1], ent[3:]
        if x == "R" and i + 1 < len(parts):  # rename: next part is the source
            i += 1
        if x not in (" ", "?") and x != "":
            prestaged.append(path)
        if y not in (" ", ""):
            working.append(path)
        if x == "?" and y == "?":
            untracked.append(path)
            working.append(path)
        i += 1
    # de-dup
    return (sorted(set(working)), sorted(set(prestaged)), sorted(set(untracked)))


# ---------------------------------------------------------------------- checks
def _staged_files(repo: Path, paths: list[str], idx: str | None) -> list[str]:
    ps = ["--", *paths] if paths else []
    out = git(repo, "diff", "--cached", "--name-only", *ps, index_file=idx).stdout
    return [l.strip() for l in out.splitlines() if l.strip()]


def check_secret_scan(repo, paths, idx, pol):
    # Scan raw staged BLOB BYTES (not the textual diff): a binary or
    # .gitattributes -diff file cannot hide a key/token from a byte scan.
    for f in _staged_files(repo, paths, idx):
        if SENSITIVE_NAME.search(f):
            return False, f"sensitive file staged: {f}"
        blob = git(repo, "show", f":{f}", index_file=idx, binary=True).stdout
        if not isinstance(blob, (bytes, bytearray)):
            blob = str(blob).encode("utf-8", "replace")
        if KEY_BLOCK_B.search(blob) or TOKEN_B.search(blob):
            return False, f"key/token material in staged blob: {f}"
    return True, "no secrets"


def check_settings_json(repo, paths, idx, pol):
    sj = repo / ".claude" / "settings.json"
    if not sj.exists():
        return True, "no settings.json"
    try:
        json.loads(sj.read_text())
        return True, "settings.json valid"
    except Exception as e:
        return False, f"settings.json invalid: {e}"


def _py_compile(files: list[Path]) -> tuple[bool, str]:
    import py_compile
    for f in files:
        try:
            py_compile.compile(str(f), doraise=True)
        except Exception as e:
            return False, f"py_compile failed: {f.name}: {str(e)[:120]}"
    return True, f"py_compile OK ({len(files)} file(s))"


def check_py_compile_hooks(repo, paths, idx, pol):
    staged = _staged_files(repo, paths, idx)
    files = [repo / f for f in staged if f.endswith(".py") and (repo / f).exists()]
    return _py_compile(files) if files else (True, "no python staged")


check_py_compile_changed = check_py_compile_hooks


def check_no_workflow_todos(repo, paths, idx, pol):
    staged = _staged_files(repo, paths, idx)
    hits = []
    for f in staged:
        if "/.claude/" not in ("/" + f) and not f.startswith(".claude/"):
            continue
        fp = repo / f
        if not fp.is_file() or fp.suffix not in (".py", ".md", ".sh"):
            continue
        try:
            for i, line in enumerate(fp.read_text(errors="ignore").splitlines(), 1):
                if TODO_MARK.search(line):
                    hits.append(f"{f}:{i}")
        except Exception:
            continue
    return (False, "actionable TODO/FIXME markers: " + ", ".join(hits[:5])) if hits else (True, "no workflow TODOs")


def check_evidence_audit_if_reports_changed(repo, paths, idx, pol):
    staged = _staged_files(repo, paths, idx)
    reports = [repo / f for f in staged
               if re.search(r"(^|/)(reports?|outputs?|results?)/", f) and (repo / f).exists()]
    if not reports:
        return True, "no reports changed"
    ea = GITHUB_ROOT / ".claude" / "hooks" / "evidence_audit.py"
    if not ea.exists():
        return True, "evidence_audit.py absent (skipped)"
    r = subprocess.run([sys.executable, str(ea), "--strict", *map(str, reports)],
                       capture_output=True, text=True)
    return (r.returncode == 0,
            "evidence audit clean" if r.returncode == 0 else "evidence audit found unsupported claims")


def check_promotion_gate_if_metrics_changed(repo, paths, idx, pol):
    staged = _staged_files(repo, paths, idx)
    metricish = [f for f in staged if re.search(r"(?i)(metric|promotion|sharpe|pnl|backtest|result)", f)]
    if not metricish:
        return True, "no metrics/research files changed"
    # require a promotion gate artifact somewhere under the repo
    gate = list(repo.rglob("promotion_*.json")) + list(repo.rglob("*gate*.json"))
    if gate:
        return True, f"gate artifact present ({gate[0].name})"
    return False, ("metrics/research changed but no promotion gate artifact found "
                   "(run /gate-check or remove the metric claim)")


CHECKS = {
    "secret_scan": check_secret_scan,
    "settings_json": check_settings_json,
    "py_compile_hooks": check_py_compile_hooks,
    "py_compile_changed": check_py_compile_changed,
    "no_workflow_todos": check_no_workflow_todos,
    "evidence_audit_if_reports_changed": check_evidence_audit_if_reports_changed,
    "promotion_gate_if_metrics_changed": check_promotion_gate_if_metrics_changed,
}


# --------------------------------------------------------------------- message
def build_message(subject, scope, paths, files, summary, run_class, checks,
                  artifacts, lever, task, session, body_ctx) -> str:
    listing = "\n".join(f"  {f}" for f in files[:50])
    if len(files) > 50:
        listing += f"\n  ... (+{len(files) - 50} more)"
    arts = ", ".join(artifacts) if artifacts else "none"
    lines = [
        subject.strip(),
        "",
        "Context:",
        f"- {body_ctx}" if body_ctx else f"- {scope} changes grouped for an atomic, scoped commit.",
        "Changes:",
        listing or "  (none)",
        "Evidence:",
        f"- checks run and passed: {', '.join(checks) if checks else 'none'}",
        "Risk:",
        "- scoped to one repo and one scope; pathspec-staged so no unrelated file is bundled.",
        "Rollback:",
        "- `git revert <hash>` in this repo (atomic, single-scope).",
        "",
        f"Task: {task or '-'}",
        f"Scope: {scope} [{summary}]",
        f"Run-Class: {run_class}",
        f"Checks: {', '.join(checks) if checks else 'none'}",
        f"Artifacts: {arts}",
        f"Lever: {lever or 'none'}",
        f"Session: {session or '-'}",
    ]
    return "\n".join(lines)


# ----------------------------------------------------------------------- push
def do_push(repo: Path, pol: dict, allow_mismatch: bool, dry: bool) -> str:
    br = branch_of(repo)
    exp = pol.get("expected_branch", "main")
    if br == "HEAD":
        return "skip-push (detached HEAD)"
    if br != exp and not allow_mismatch:
        return f"BLOCKED push (on '{br}', expected '{exp}'; --allow-branch-mismatch to override)"
    if not pol.get("auto_push"):
        return "skip-push (auto_push disabled by policy)"
    has_up = git(repo, "rev-parse", "--abbrev-ref", "@{upstream}").returncode == 0
    cmd = ["push"] if has_up else ["push", "-u", "origin", br]
    if dry:
        return f"would: git -C {repo.name} {' '.join(cmd)}"
    r = git(repo, *cmd)
    if r.returncode != 0:
        last = r.stderr.strip().splitlines()[-1] if r.stderr.strip() else "unknown"
        return f"PUSH FAILED: {last}"
    return f"pushed {br}"


# --------------------------------------------------------------------- per-repo
def process_repo(repo: Path, pol: dict, args) -> dict:
    res: dict = {"repo": pol.get("id", repo.name), "path": str(repo),
                 "branch": branch_of(repo), "commits": [], "skipped": [],
                 "unknown": [], "notes": []}
    apply = args.apply and not pol.get("dry_run_only", False)
    if args.apply and pol.get("dry_run_only", False):
        res["notes"].append("dry_run_only: forced dry-run regardless of --apply")
    if pol.get("conservative") and args.apply and pol.get("id", repo.name) not in (args.repo or []):
        # conservative repos require being named explicitly with --repo to apply
        apply = False
        res["notes"].append("conservative: dry-run unless explicitly targeted with --repo")

    working, prestaged, untracked = porcelain(repo)
    if not working and not prestaged:
        res["status"] = "clean"
        return res

    # Pre-staged protection.
    if prestaged and not args.include_prestaged:
        res["status"] = "ABORTED"
        res["notes"].append(
            f"{len(prestaged)} pre-staged file(s) not owned by this run "
            f"(e.g. {', '.join(prestaged[:3])}). Pass --include-prestaged to fold "
            f"them in, or unstage them. Refusing to mix.")
        return res

    candidates = working[:] + (prestaged if args.include_prestaged else [])
    candidates = sorted(set(candidates))

    # Classify into scopes, applying include/exclude.
    by_scope: dict[str, list[str]] = {}
    for rel in candidates:
        if not included(rel, pol):
            res["skipped"].append(rel)
            continue
        # Artifact gate by SUFFIX, independent of dir-scope: a .pkl under
        # scripts/ is still an artifact and must clear allow_artifacts.
        if ARTIFACT_SUFFIX.search(rel) and not artifact_allowed(rel, pol):
            res["skipped"].append(rel + " (artifact not allowed by policy)")
            continue
        scope = classify_scope(rel)
        if scope == "unknown":
            res["unknown"].append(rel)
            continue
        if scope == "reports" and not pol.get("allow_reports", False):
            res["skipped"].append(rel + " (reports not allowed)")
            continue
        if args.scope and scope not in args.scope:
            continue
        by_scope.setdefault(scope, []).append(rel)

    if not by_scope:
        res["status"] = "nothing-to-commit (all filtered/unknown)"
        return res

    run_class = args.run_class or pol.get("default_run_class", "diagnostic")
    if run_class not in RUN_CLASSES:
        res["status"] = f"ABORTED (invalid run-class '{run_class}')"
        return res

    # One commit per scope, in a stable, readable order.
    order = ["contracts", "registry", "hooks", "scripts", "commands", "tests",
             "research-code", "config", "docs", "reports", "artifacts"]
    scopes = sorted(by_scope, key=lambda s: order.index(s) if s in order else 99)

    any_committed = False
    for scope in scopes:
        paths = sorted(by_scope[scope])
        # ALWAYS stage into a throwaway index seeded from HEAD — for dry-run AND
        # apply. The real index is never read or mutated, so a BLOCKED scope can
        # never leave a secret staged, and the commit contains exactly HEAD + this
        # scope's paths (no other staged content, no cross-scope bleed).
        idx = temp_index_for(repo)
        commit_rec = {"scope": scope, "files": paths, "checks": [], "status": ""}
        try:
            for p in paths:
                git(repo, "add", "--", p, index_file=idx)
            staged = _staged_files(repo, paths, idx)
            if not staged:
                commit_rec["status"] = "skip (nothing staged)"
                res["commits"].append(commit_rec)
                continue
            stat = git(repo, "diff", "--cached", "--shortstat", index_file=idx).stdout.strip()
            commit_rec["summary"] = stat or "no diff"

            # Run policy checks. An UNKNOWN check id fails CLOSED (a typo must not
            # silently disable a gate).
            ok_all = True
            for cname in pol.get("checks", []):
                fn = CHECKS.get(cname)
                if not fn:
                    ok_all = False
                    commit_rec["checks"].append(f"{cname}=UNKNOWN")
                    commit_rec["status"] = f"BLOCKED (unknown check '{cname}' — fail closed)"
                    break
                ok, detail = fn(repo, paths, idx, pol)
                commit_rec["checks"].append(f"{cname}={'PASS' if ok else 'FAIL'}")
                if not ok:
                    ok_all = False
                    commit_rec["status"] = f"BLOCKED ({cname}: {detail})"
                    break
            if not ok_all:
                res["commits"].append(commit_rec)
                continue

            artifacts = [p for p in paths if ARTIFACT_SUFFIX.search(p)]
            passed = [c.split("=")[0] for c in commit_rec["checks"] if c.endswith("PASS")]
            subject = args.message_subject or f"update {scope} ({pol.get('id', repo.name)})"
            msg = build_message(subject, scope, paths, staged, stat, run_class,
                                passed, artifacts, args.lever, args.task,
                                args.session, args.context)
            commit_rec["message_preview"] = msg.splitlines()[0]

            if not apply:
                commit_rec["status"] = "dry-run"
                res["commits"].append(commit_rec)
                continue

            # Commit FROM the throwaway index (= HEAD + this scope). The real
            # index is never touched here.
            c = git(repo, "commit", "-m", msg, index_file=idx)
            if c.returncode != 0:
                commit_rec["status"] = "COMMIT BLOCKED: " + (c.stderr.strip() or c.stdout.strip())[:200]
                res["commits"].append(commit_rec)
                continue
            commit_rec["commit"] = git(repo, "rev-parse", "--short", "HEAD").stdout.strip()
            commit_rec["status"] = "committed"
            any_committed = True
            res["commits"].append(commit_rec)
        finally:
            if idx and os.path.exists(idx):
                try:
                    os.unlink(idx)
                except OSError:
                    pass

    # Sync the real index to the new HEAD so git status is clean for what we
    # committed (we committed via throwaway indexes; the real index is stale).
    # Safe: unowned pre-staged content was already refused above unless folded in.
    if apply and any_committed:
        git(repo, "reset", "-q")

    # Push once if anything was committed (or preview the push in dry-run).
    committed = [c for c in res["commits"] if c.get("status") == "committed"]
    if args.push and (committed or not apply):
        res["push"] = do_push(repo, pol, args.allow_branch_mismatch, dry=not apply or not committed)
    res["status"] = "committed" if committed else ("dry-run" if not apply else "no-commit")
    return res


# ------------------------------------------------------------------------- main
def resolve_targets(args, policy) -> list[Path]:
    repos: list[Path] = []
    if args.repo:
        for r in args.repo:
            p = Path(os.path.expanduser(r))
            if p.exists() and is_git_repo(p):
                repos.append(toplevel(p) or p)
            else:
                cfg = (policy.get("repos", {}) or {}).get(r)
                if cfg and cfg.get("path"):
                    pp = Path(os.path.expanduser(cfg["path"]))
                    if is_git_repo(pp):
                        repos.append(toplevel(pp) or pp)
                    else:
                        emit(f"target '{r}' not a git repo on disk; skipping")
                else:
                    emit(f"target '{r}' not found; skipping")
        return repos
    # all dirty git surfaces under ~/GitHub (depth 1) + the root
    if is_git_repo(GITHUB_ROOT):
        repos.append(GITHUB_ROOT)
    for child in sorted(GITHUB_ROOT.iterdir()):
        if child.is_dir() and (child / ".git").exists():
            repos.append(child)
    return repos


def print_table(results: list[dict]) -> None:
    emit("=" * 60)
    for r in results:
        head = f"{r['repo']:<24} {r.get('status','?'):<12} branch={r['branch']}"
        emit(head)
        for n in r.get("notes", []):
            emit(f"    note: {n}")
        for c in r.get("commits", []):
            line = f"    [{c['scope']}] {c.get('status','')}"
            if c.get("commit"):
                line += f" {c['commit']}"
            if c.get("summary"):
                line += f"  ({c['summary']})"
            emit(line)
            if c.get("checks"):
                emit(f"        checks: {', '.join(c['checks'])}")
        if r.get("unknown"):
            emit(f"    unknown (left out): {', '.join(r['unknown'][:5])}"
                 + (f" +{len(r['unknown'])-5}" if len(r['unknown']) > 5 else ""))
        if r.get("skipped"):
            emit(f"    skipped: {', '.join(r['skipped'][:5])}"
                 + (f" +{len(r['skipped'])-5}" if len(r['skipped']) > 5 else ""))
        if r.get("push"):
            emit(f"    push: {r['push']}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Policy-driven, scope-granular, auditable committer.")
    ap.add_argument("--apply", action="store_true", help="Actually commit (default: dry-run).")
    ap.add_argument("--push", action="store_true", help="Push after committing (policy + branch gated).")
    ap.add_argument("--repo", action="append", default=[], help="Repo id or path (repeatable).")
    ap.add_argument("--task", default="", help="Task id for the Task: trailer.")
    ap.add_argument("--run-class", dest="run_class", default="", help="Override run-class.")
    ap.add_argument("--message-subject", dest="message_subject", default="", help="Commit subject line.")
    ap.add_argument("--context", default="", help="One-line Context: body for the message.")
    ap.add_argument("--scope", action="append", default=[], help="Restrict to these scopes (repeatable).")
    ap.add_argument("--lever", default="", help="Lever id for the Lever: trailer.")
    ap.add_argument("--session", default=os.environ.get("CLAUDE_SESSION_ID", ""))
    ap.add_argument("--include-prestaged", dest="include_prestaged", action="store_true")
    ap.add_argument("--allow-branch-mismatch", dest="allow_branch_mismatch", action="store_true")
    ap.add_argument("--json", action="store_true", help="Emit machine-readable results on stdout.")
    args = ap.parse_args()

    policy = load_policy()
    targets = resolve_targets(args, policy)
    results = []
    for repo in targets:
        if not is_git_repo(repo):
            continue
        pol = policy_for(repo, policy)
        results.append(process_repo(repo, pol, args))

    if args.json:
        print(json.dumps(results, indent=2))
    print_table(results)

    blocked = any(
        "ABORT" in r.get("status", "") or
        any("BLOCKED" in c.get("status", "") or "FAILED" in c.get("status", "")
            for c in r.get("commits", [])) or
        "FAILED" in str(r.get("push", ""))
        for r in results
    )
    return 1 if blocked else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        emit(f"internal error (no commits beyond those reported): {e}")
        sys.exit(2)

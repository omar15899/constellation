#!/usr/bin/env python3
"""commit_guard.py — standalone commit/push validator (constellation plane).

A belt-and-braces VALIDATOR for the git-as-research-ledger layer. It does NOT
commit and is NOT wired to auto-commit on PostToolUse — the committer
(research_committer.py via /commit-research) is the explicit command. Use this to
audit a repo's staged state, a drafted commit message, or a push intent before
or independently of the committer.

Posture (balanced): HARD signals exit 2; methodology heuristics warn (exit 0)
unless COMMIT_GUARD_STRICT=1.

  HARD (exit 2):
    - a dangerous file staged (.env / key / token / private-key block);
    - a push intent to a branch != expected (`--branch-expected`);
    - a drafted commit message missing required trailers (`--message FILE`);
    - a report claiming promotion with no gate artifact on disk (`--repo`).
  ADVISORY (warn; hard only under COMMIT_GUARD_STRICT=1):
    - broad claims (robust / confirmed / production-ready) in the message;
    - a staged python file that uses an RNG with no seed.

Usage:
    commit_guard.py --repo PATH [--branch-expected main] [--message MSGFILE]

Stdlib only. On internal error exits 0 (a validator must not brick a workflow).
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

TAG = "[constellation:commit_guard]"

KEY_BLOCK_B = re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----")
TOKEN_B = re.compile(
    rb"(AKIA[0-9A-Z]{12,}|ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}"
    rb"|sk-[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"
    rb"|xox[baprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_\-]{30,})"
)
SENSITIVE_NAME = re.compile(r"(?i)(^|/)(\.env(\.|$)|.*\.(pem|key|p12|pfx)$|id_rsa|id_ed25519"
                            r"|credentials(\.json)?$|secrets?\.(ya?ml|json|toml))")
REQUIRED_TRAILERS = ["Task:", "Scope:", "Run-Class:", "Checks:"]
BROAD = re.compile(r"(?i)\b(robust|confirmed|production[\s-]?ready|state[\s-]?of[\s-]?the[\s-]?art|guaranteed)\b")
PROMOTION = re.compile(r"(?i)\b(promot(e|ed|ion)|CONFIRMED|deployable|passes? the gate)\b")
RNG_USE = re.compile(r"(?i)\b(np\.random\.|numpy\.random\.|random\.(random|randint|shuffle|sample|choice)|default_rng\(|RandomState\()")
SEED_SET = re.compile(r"(?i)(seed|random_state|default_rng\(\s*\d|RandomState\(\s*\d|manual_seed)")


def emit(m: str) -> None:
    sys.stderr.write(f"{TAG} {m}\n")


def git(repo: Path, *a: str) -> subprocess.CompletedProcess:
    # errors='replace' so a non-UTF-8 byte can NEVER raise and fail the guard open.
    env = {**os.environ, "GIT_LITERAL_PATHSPECS": "1"}
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True,
                          text=True, errors="replace", env=env)


def blob_bytes(repo: Path, path: str) -> bytes:
    env = {**os.environ, "GIT_LITERAL_PATHSPECS": "1"}
    r = subprocess.run(["git", "-C", str(repo), "show", f":{path}"],
                       capture_output=True, env=env)
    return r.stdout if isinstance(r.stdout, (bytes, bytearray)) else b""


def staged_names(repo: Path) -> list[str]:
    return [l.strip() for l in git(repo, "diff", "--cached", "--name-only").stdout.splitlines() if l.strip()]


def main() -> int:
    ap = argparse.ArgumentParser(description="Commit/push validator (advisory + hard signals).")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--branch-expected", dest="branch_expected", default="")
    ap.add_argument("--message", default="")
    args = ap.parse_args()
    strict = os.environ.get("COMMIT_GUARD_STRICT", "").strip() in ("1", "true", "yes")

    repo = Path(os.path.expanduser(args.repo))
    if git(repo, "rev-parse", "--is-inside-work-tree").returncode != 0:
        emit(f"not a git repo: {repo}")
        return 0

    hard: list[str] = []
    soft: list[str] = []

    # HARD: dangerous staged files / secret material (scanned over BLOB BYTES,
    # not the textual diff — binary / .gitattributes -diff cannot hide a secret).
    names = staged_names(repo)
    for n in names:
        if SENSITIVE_NAME.search(n):
            hard.append(f"dangerous file staged: {n}")
        b = blob_bytes(repo, n)
        if KEY_BLOCK_B.search(b) or TOKEN_B.search(b):
            hard.append(f"key/token material in staged blob: {n}")

    # HARD: push to wrong branch (symbolic-ref resolves the unborn-branch case).
    if args.branch_expected:
        sr = git(repo, "symbolic-ref", "--short", "HEAD")
        cur = sr.stdout.strip() if sr.returncode == 0 else git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        if cur != args.branch_expected:
            hard.append(f"branch '{cur}' != expected '{args.branch_expected}' (push would be wrong-branch)")

    # HARD: --message given but missing/empty, or missing required trailers.
    if args.message:
        mp = Path(os.path.expanduser(args.message))
        if not mp.exists() or not mp.read_text(errors="replace").strip():
            hard.append(f"--message {args.message} given but the file is missing or empty")
        else:
            msg = mp.read_text(errors="replace")
            missing = [t for t in REQUIRED_TRAILERS if t not in msg]
            if missing:
                hard.append("commit message missing trailers: " + ", ".join(missing))
            if BROAD.search(msg):
                soft.append("message uses a broad claim (robust/confirmed/production-ready) — back it or soften")

    # HARD: report promotion without a gate artifact.
    report_promo = False
    for n in names:
        if re.search(r"(?i)(reports?|outputs?|results?)/.*\.(md|txt|json)$", n):
            fp = repo / n
            try:
                if PROMOTION.search(fp.read_text(errors="ignore")):
                    report_promo = True
            except Exception:
                pass
    if report_promo:
        gate = list(repo.rglob("promotion_*.json")) + list(repo.rglob("*gate*.json"))
        if not gate:
            hard.append("a staged report claims promotion but no gate artifact (promotion_*.json) exists")

    # ADVISORY: seedless RNG in staged python.
    for n in names:
        if n.endswith(".py") and "/.claude/" not in ("/" + n):
            fp = repo / n
            try:
                t = fp.read_text(errors="ignore")
                if RNG_USE.search(t) and not SEED_SET.search(t):
                    soft.append(f"{n} uses an RNG with no seed (reproducibility)")
            except Exception:
                pass

    if hard:
        emit("HARD signals (block):")
        for h in hard:
            emit(f"  - {h}")
    if soft:
        for s in soft:
            emit(f"advisory{' (strict→block)' if strict else ''}: {s}")
    if not hard and not soft:
        emit("clean — no commit/push concerns.")

    if hard or (strict and soft):
        return 2
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        # Fail CLOSED: a validator must not greenlight a commit because it crashed.
        sys.stderr.write(f"{TAG} internal error — failing closed: {e}\n")
        sys.exit(2)

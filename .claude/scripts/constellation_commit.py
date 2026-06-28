#!/usr/bin/env python3
"""constellation_commit.py — granular, per-repo, traceable committer + auto-push.

The constellation is N independent git surfaces: the root `constellation` repo
(~/GitHub, tracking only the control plane) plus every sub-repo, each with its
own remote and branch. A single working session routinely dirties several of
them at once. Constellation git policy is hard: ONE commit per repo, atomic,
never bundled across repos, never `--force`, never `--no-verify`.

This script makes that policy executable and adds machine-greppable
traceability trailers so the research/implementation history is reconstructable
from `git log` alone.

Two modes:

  1. Spec mode (full granularity — Claude decides the logical split):
       constellation_commit.py --spec spec.json [--push] [--dry-run]
     spec.json:
       {
         "session": "optional-id",
         "commits": [
           {
             "repo":    "ResearchLab" | "/abs/path" | ".",
             "subject": "imperative one-liner (that repo's change)",
             "body":    "optional why",
             "paths":   ["rel/path", ...],   # omit => all changes in repo
             "lever":   "headline-audit",    # optional research tie
             "task":    "slug"               # optional
           }
         ]
       }

  2. Quick mode (one commit per dirty repo, same subject):
       constellation_commit.py --intent "subject" [--repo NAME ...] [--push] [--dry-run]

Safety contract:
  - Atomic per repo. `git -C <repo>` only; never stages another repo's tree.
  - Aborts a repo's commit if its staged diff carries secret/.env material.
  - Never `--force`. Never `--no-verify` (per-repo hooks stay authoritative).
  - Push sets upstream on first push (`-u origin <branch>`), never to a
    detached HEAD. A push failure on one repo does not abort the others.
  - Dependency-free stdlib + system `git`. Idempotent: clean repo => skip.
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

TAG = "[constellation:commit]"
GITHUB_ROOT = Path.home() / "GitHub"
REPOS_YAML = GITHUB_ROOT / ".claude" / "registry" / "repos.yaml"

# Sort weights for non-numeric tiers. Lower lands first (Tier 0 before consumers).
_TIER_UI = 4.5      # UI consumes every code tier → land after them
_TIER_UNTIERED = 90.0   # adjacent / external repos (tier: null)
_TIER_ROOT = 200.0      # the root constellation control-plane repo → land last

KEY_BLOCK = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
TOKEN = re.compile(
    r"(AKIA[0-9A-Z]{12,}|ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}"
    r"|sk-[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"
    r"|xox[baprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_\-]{30,})"
)


def emit(m: str) -> None:
    sys.stderr.write(f"{TAG} {m}\n")


def git(repo: Path, *args: str, check: bool = False,
        index_file: str | None = None) -> subprocess.CompletedProcess:
    env = None
    if index_file:
        env = os.environ.copy()
        env["GIT_INDEX_FILE"] = index_file
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, check=check, env=env,
    )


def temp_index_for(repo: Path) -> str | None:
    """A throwaway index seeded from the repo's real index, so a dry-run can
    stage + diff without ever mutating the real index. Returns its path (caller
    must unlink) or None on failure."""
    try:
        gitdir = git(repo, "rev-parse", "--absolute-git-dir").stdout.strip()
        if not gitdir:
            return None
        real_index = Path(gitdir) / "index"
        fd, tmp = tempfile.mkstemp(prefix="cc_idx_")
        os.close(fd)
        if real_index.exists():
            shutil.copyfile(real_index, tmp)
        else:
            os.unlink(tmp)  # let git create a fresh one at this path
        return tmp
    except Exception:
        return None


def is_git_repo(p: Path) -> bool:
    return git(p, "rev-parse", "--is-inside-work-tree").returncode == 0


def resolve_repo(token: str) -> Path:
    """Map a spec 'repo' field to an absolute path."""
    if token in (".", ""):
        return GITHUB_ROOT
    p = Path(token)
    if p.is_absolute():
        return p
    return GITHUB_ROOT / token


def dirty(repo: Path) -> bool:
    return bool(git(repo, "status", "--porcelain").stdout.strip())


def discover_dirty_surfaces() -> list[Path]:
    """Root constellation repo + every immediate sub-repo, dirty ones only."""
    surfaces: list[Path] = []
    if is_git_repo(GITHUB_ROOT) and dirty(GITHUB_ROOT):
        surfaces.append(GITHUB_ROOT)
    for child in sorted(GITHUB_ROOT.iterdir()):
        if child.is_dir() and (child / ".git").exists():
            if dirty(child):
                surfaces.append(child)
    return surfaces


def branch_of(repo: Path) -> str:
    return git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def repo_tiers() -> dict[str, float]:
    """Parse registry/repos.yaml → {repo_name: sortable_tier}. Stdlib hand-parse
    (no PyYAML — constellation convention). Tier order is the landing order:
    Tier 0 first so consumers never see a broken intermediate `main`."""
    tiers: dict[str, float] = {}
    try:
        name = None
        for raw in REPOS_YAML.read_text().splitlines():
            m = re.match(r"\s*-\s*name:\s*(\S+)", raw)
            if m:
                name = m.group(1).strip()
                continue
            t = re.match(r"\s*tier:\s*(\S+)", raw)
            if t and name:
                v = t.group(1).strip()
                if v.lower() in ("null", "none", "~"):
                    tiers[name] = _TIER_UNTIERED
                elif v.upper() == "UI":
                    tiers[name] = _TIER_UI
                else:
                    try:
                        tiers[name] = float(v)
                    except ValueError:
                        tiers[name] = _TIER_UNTIERED
                name = None
    except Exception:
        return {}
    return tiers


def tier_key(repo: Path, tiers: dict[str, float]) -> float:
    if repo.resolve() == GITHUB_ROOT.resolve():
        return _TIER_ROOT
    return tiers.get(repo.name, _TIER_UNTIERED)


def staged_secret_hits(repo: Path, paths: list[str] | None = None,
                       index_file: str | None = None) -> list[str]:
    ps = ["--", *paths] if paths else []
    hits: list[str] = []
    names = git(repo, "diff", "--cached", "--name-only", *ps, index_file=index_file).stdout.splitlines()
    for n in (x.strip() for x in names if x.strip()):
        b = os.path.basename(n)
        if b == ".env" or b.startswith(".env."):
            hits.append(f"{n} (.env staged)")
    diff = git(repo, "diff", "--cached", *ps, index_file=index_file).stdout
    for ln in diff.splitlines():
        if ln.startswith("+") and (KEY_BLOCK.search(ln) or TOKEN.search(ln)):
            hits.append("staged diff contains key/token material")
            break
    return hits


def stat_line(repo: Path, paths: list[str] | None = None,
              index_file: str | None = None) -> tuple[str, list[str]]:
    """Return ('N (+a -b)', ['M path', 'A path', ...]) for the staged set."""
    ps = ["--", *paths] if paths else []
    shortstat = git(repo, "diff", "--cached", "--shortstat", *ps, index_file=index_file).stdout.strip()
    ins = re.search(r"(\d+) insertion", shortstat)
    dels = re.search(r"(\d+) deletion", shortstat)
    files = git(repo, "diff", "--cached", "--name-status", *ps, index_file=index_file).stdout.splitlines()
    files = [f.strip() for f in files if f.strip()]
    n = len(files)
    summary = f"{n} (+{ins.group(1) if ins else 0} -{dels.group(1) if dels else 0})"
    return summary, files


def build_message(subject: str, body: str, repo: Path, files: list[str],
                  summary: str, lever: str, task: str, session: str) -> str:
    parts = [subject.strip()]
    if body.strip():
        parts.append("")
        parts.append(body.strip())
    listing = "\n".join(f"  {f}" for f in files[:50])
    if len(files) > 50:
        listing += f"\n  ... (+{len(files) - 50} more)"
    parts.append("")
    parts.append(listing)
    parts.append("")
    # git-trailer block — greppable: `git log --grep 'Lever: <name>'`
    parts.append(f"Changed-files: {summary}")
    parts.append(f"Repo: {repo.name}")
    parts.append(f"Branch: {branch_of(repo)}")
    parts.append(f"Lever: {lever or '-'}")
    parts.append(f"Task: {task or '-'}")
    parts.append(f"Session: {session or '-'}")
    return "\n".join(parts)


def push(repo: Path, dry: bool) -> str:
    br = branch_of(repo)
    if br == "HEAD":
        return "skip-push (detached HEAD)"
    has_upstream = git(repo, "rev-parse", "--abbrev-ref",
                       "@{upstream}").returncode == 0
    cmd = ["push"] if has_upstream else ["push", "-u", "origin", br]
    if dry:
        return f"would: git -C {repo.name} {' '.join(cmd)}"
    r = git(repo, *cmd)
    if r.returncode != 0:
        return f"PUSH FAILED: {r.stderr.strip().splitlines()[-1] if r.stderr.strip() else 'unknown'}"
    return f"pushed {br}"


def commit_one(repo: Path, subject: str, body: str, paths: list[str] | None,
               lever: str, task: str, session: str, do_push: bool,
               dry: bool) -> dict:
    res: dict = {"repo": repo.name, "branch": branch_of(repo)}
    if not is_git_repo(repo):
        res["status"] = "skip (not a git repo)"
        return res
    if not dirty(repo):
        res["status"] = "skip (clean)"
        return res

    # A dry-run operates on a THROWAWAY index seeded from the real one, so neither
    # `git add` nor the secret-abort `git reset` ever touches the user's real
    # index (no clobbering of curated / `git add -p` partial staging).
    idx = temp_index_for(repo) if dry else None
    try:
        # Stage: only the listed paths (atomic intent) or the whole repo tree.
        if paths:
            for p in paths:
                git(repo, "add", "--", p, index_file=idx)
        else:
            git(repo, "add", "-A", index_file=idx)

        # Pathspec scopes the diff/secret-scan/commit to THIS commit's paths, so a
        # granular per-path commit never bundles other files already staged in the
        # index (each entry in a spec stays atomic to its own paths).
        ps = ["--", *paths] if paths else []

        if not git(repo, "diff", "--cached", "--name-only", *ps, index_file=idx).stdout.strip():
            res["status"] = "skip (nothing staged after filter)"
            return res

        secrets = staged_secret_hits(repo, paths, index_file=idx)
        if secrets:
            if not dry:
                git(repo, "reset", *ps)  # unstage these paths — never commit secrets
            res["status"] = "ABORTED (secret material staged): " + "; ".join(secrets)
            return res

        summary, files = stat_line(repo, paths, index_file=idx)
        msg = build_message(subject, body, repo, files, summary,
                            lever, task, session)
        res["changed"] = summary

        if dry:
            res["status"] = "dry-run"
            res["message"] = msg
            return res

        c = git(repo, "commit", "-m", msg, *ps)
        if c.returncode != 0:
            # most likely a per-repo pre-commit hook blocked it — that is authority
            res["status"] = "COMMIT BLOCKED: " + (c.stderr.strip() or c.stdout.strip())[:300]
            return res
        res["commit"] = git(repo, "rev-parse", "--short", "HEAD").stdout.strip()
        res["status"] = "committed"
        if do_push:
            res["push"] = push(repo, dry)
        return res
    finally:
        if idx and os.path.exists(idx):
            try:
                os.unlink(idx)
            except OSError:
                pass


def main() -> int:
    ap = argparse.ArgumentParser(description="Per-repo granular traceable committer.")
    ap.add_argument("--spec", help="JSON spec for granular per-repo commits.")
    ap.add_argument("--intent", help="Quick mode: one subject for every dirty repo.")
    ap.add_argument("--repo", action="append", default=[],
                    help="Quick mode: restrict to these repo names (repeatable).")
    ap.add_argument("--push", action="store_true", help="Push after committing.")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-tier-order", action="store_true",
                    help="Do not reorder commits by QuantOS tier (default: Tier 0 first).")
    ap.add_argument("--session", default=os.environ.get("CLAUDE_SESSION_ID", ""))
    args = ap.parse_args()

    results: list[dict] = []
    tiers = {} if args.no_tier_order else repo_tiers()

    if args.spec:
        spec = json.loads(Path(args.spec).read_text())
        session = spec.get("session") or args.session
        commits = list(spec.get("commits", []))
        if not args.no_tier_order:
            # stable sort: Tier 0 lands first, control plane last; ties keep order
            commits.sort(key=lambda c: tier_key(resolve_repo(c["repo"]), tiers))
        for c in commits:
            repo = resolve_repo(c["repo"])
            results.append(commit_one(
                repo, c.get("subject", ""), c.get("body", ""),
                c.get("paths"), c.get("lever", ""), c.get("task", ""),
                session, args.push, args.dry_run,
            ))
    elif args.intent:
        surfaces = discover_dirty_surfaces()
        if args.repo:
            wanted = set(args.repo)
            surfaces = [s for s in surfaces if s.name in wanted]
        if not surfaces:
            emit("no dirty repos to commit.")
            return 0
        if not args.no_tier_order:
            surfaces.sort(key=lambda s: tier_key(s, tiers))
        for repo in surfaces:
            results.append(commit_one(
                repo, args.intent, "", None, "", "", args.session,
                args.push, args.dry_run,
            ))
    else:
        emit("nothing to do: pass --spec FILE or --intent 'subject'.")
        return 2

    # report
    print(json.dumps(results, indent=2))
    blocked = [r for r in results if "ABORT" in r.get("status", "")
               or "BLOCKED" in r.get("status", "") or "FAILED" in str(r.get("push", ""))]
    for r in results:
        line = f"{r['repo']:<24} {r.get('status','?')}"
        if r.get("commit"):
            line += f"  [{r['commit']}]"
        if r.get("push"):
            line += f"  {r['push']}"
        emit(line)
    return 1 if blocked else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        emit(f"internal error (no commits beyond those reported): {e}")
        sys.exit(2)

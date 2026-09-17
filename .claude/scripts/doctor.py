#!/usr/bin/env python3
"""doctor.py — constellation health check for the ~/GitHub/.claude hub.

A read-only diagnostic that composes the existing validators and adds the
checks no single validator owns: settings.json integrity, referenced-hook
existence, the presence of the commands/ and contracts/ planes, and the hub's
own git state. With --repo it also profiles a target repo (branch, upstream,
dirty/untracked/merge-conflict, project type, available checks, raw-data
hygiene, oversized staged blobs).

It NEVER mutates anything — no index writes, no commits, no file edits. The
composed validators are run as subprocesses (python3); a missing validator is
marked `not-run`, never a crash. Stdlib-only; matches the style of
validate_levers.py and discover_repos.py.

Exit code: 0 on PASS/WARN, 1 on FAIL (a hard, actionable problem).

Usage:
    python3 .claude/scripts/doctor.py                       # hub health
    python3 .claude/scripts/doctor.py --repo ../MarketDataLab
    python3 .claude/scripts/doctor.py --json
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

HUB = Path(__file__).resolve().parents[1]
GITHUB_ROOT = HUB.parent
SETTINGS = HUB / "settings.json"
SCRIPTS = HUB / "scripts"

# Validators this doctor composes. A missing one is `not-run`, never fatal.
COMPOSED_VALIDATORS = [
    ("validate_levers", SCRIPTS / "validate_levers.py"),
    ("validate_settings", SCRIPTS / "validate_settings.py"),
    ("validate_repos", SCRIPTS / "validate_repos.py"),
]

# Raw research data must stay out of git. These extensions / dirs flag a leak.
RAW_DATA_EXTS = {".parquet", ".duckdb", ".db", ".feather", ".h5", ".hdf5", ".arrow"}
RAW_DATA_DIRS = {"data", "outputs"}
LARGE_STAGED_BYTES = 5 * 1024 * 1024  # 5 MiB

_RANK = {"PASS": 0, "INFO": 0, "NOT_RUN": 1, "WARN": 1, "FAIL": 2}


def _verdict(rank: int) -> str:
    return {0: "PASS", 1: "WARN", 2: "FAIL"}[rank]


@dataclass
class Check:
    label: str
    status: str  # PASS | WARN | FAIL | INFO | NOT_RUN
    detail: str = ""


@dataclass
class Section:
    name: str
    checks: list[Check] = field(default_factory=list)

    @property
    def rank(self) -> int:
        return max((_RANK.get(c.status, 0) for c in self.checks), default=0)

    @property
    def status(self) -> str:
        return _verdict(self.rank)


def _git(path: Path, args: list[str], timeout: int = 8) -> tuple[int, str]:
    try:
        r = subprocess.run(
            ["git", "-C", str(path)] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return r.returncode, (r.stdout or "").strip()
    except Exception as exc:  # pragma: no cover - defensive
        return 1, f"<git error: {exc}>"


# --------------------------------------------------------------------------- #
# Section 1 — composed validators
# --------------------------------------------------------------------------- #
def section_validators() -> Section:
    sec = Section("validators")
    for name, path in COMPOSED_VALIDATORS:
        if not path.exists():
            sec.checks.append(Check(name, "NOT_RUN", "validator not present"))
            continue
        try:
            r = subprocess.run(
                [sys.executable, str(path)],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except Exception as exc:
            sec.checks.append(Check(name, "NOT_RUN", f"could not invoke: {exc}"))
            continue
        out = (r.stdout or "").strip()
        first = out.splitlines()[0] if out else ""
        if r.returncode != 0:
            status = "FAIL"
        elif re.search(r"\bWARN(?:ING)?\b", out, re.IGNORECASE):
            status = "WARN"
        else:
            status = "PASS"
        detail = f"{first} (rc={r.returncode})" if first else f"rc={r.returncode}"
        sec.checks.append(Check(name, status, detail))
    return sec


# --------------------------------------------------------------------------- #
# Section 2 — hub structure
# --------------------------------------------------------------------------- #
def _referenced_paths(obj: object, acc: list[str]) -> None:
    if isinstance(obj, dict):
        for v in obj.values():
            _referenced_paths(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            _referenced_paths(v, acc)
    elif isinstance(obj, str):
        for m in re.finditer(r"\$CLAUDE_PROJECT_DIR/([^\"'\s]+)", obj):
            acc.append(m.group(1))


def section_hub_structure() -> Section:
    sec = Section("hub structure")

    settings: dict | None = None
    if not SETTINGS.exists():
        sec.checks.append(Check("settings.json present", "FAIL", str(SETTINGS)))
    else:
        try:
            settings = json.loads(SETTINGS.read_text())
            sec.checks.append(Check("settings.json parseable", "PASS", str(SETTINGS)))
        except json.JSONDecodeError as exc:
            sec.checks.append(Check("settings.json parseable", "FAIL", f"JSON error: {exc}"))

    if settings is not None:
        refs: list[str] = []
        _referenced_paths(settings, refs)
        seen: list[str] = []
        for r in refs:
            if r not in seen:
                seen.append(r)
        missing = [r for r in seen if not (GITHUB_ROOT / r).exists()]
        if not seen:
            sec.checks.append(Check("referenced hooks exist", "INFO", "no hooks referenced"))
        elif missing:
            sec.checks.append(
                Check("referenced hooks exist", "FAIL",
                      f"{len(missing)}/{len(seen)} missing: {', '.join(missing)}")
            )
        else:
            sec.checks.append(
                Check("referenced hooks exist", "PASS", f"{len(seen)}/{len(seen)} present")
            )

    for label, sub in (("commands/ dir", "commands"), ("contracts/ dir", "contracts")):
        d = HUB / sub
        if d.is_dir():
            n = sum(1 for _ in d.iterdir())
            sec.checks.append(Check(label, "PASS", f"{n} entries"))
        else:
            sec.checks.append(Check(label, "FAIL", f"missing: {d}"))

    return sec


# --------------------------------------------------------------------------- #
# Section 3 — hub git
# --------------------------------------------------------------------------- #
def _git_state(path: Path, prefix: str) -> list[Check]:
    checks: list[Check] = []
    rc, _ = _git(path, ["rev-parse", "--is-inside-work-tree"])
    if rc != 0:
        checks.append(Check(f"{prefix} git", "FAIL", f"not a git repository: {path}"))
        return checks

    _, branch = _git(path, ["rev-parse", "--abbrev-ref", "HEAD"])
    branch = branch or "?"
    up_rc, upstream = _git(path, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    has_upstream = up_rc == 0 and upstream
    _, porcelain = _git(path, ["status", "--porcelain"])

    dirty = bool(porcelain)
    detail = f"branch {branch}"
    if has_upstream:
        ab_rc, ab = _git(path, ["rev-list", "--left-right", "--count", "@{u}...HEAD"])
        ahead = behind = ""
        if ab_rc == 0 and "\t" in ab:
            behind, ahead = ab.split("\t")[:2]
        detail += f" -> {upstream}"
        if ahead and ahead != "0":
            detail += f", ahead {ahead}"
        if behind and behind != "0":
            detail += f", behind {behind}"
    detail += ", dirty" if dirty else ", clean"

    branch_status = "WARN" if (dirty or not has_upstream) else "PASS"
    checks.append(Check(f"{prefix} branch/upstream", branch_status, detail))
    if not has_upstream:
        checks.append(Check(f"{prefix} upstream", "WARN", "no tracking branch configured"))
    if dirty:
        n = len(porcelain.splitlines())
        checks.append(Check(f"{prefix} working tree", "WARN", f"{n} uncommitted path(s)"))
    return checks


def section_hub_git() -> Section:
    sec = Section("hub git")
    sec.checks.extend(_git_state(GITHUB_ROOT, "hub"))
    return sec


def section_codex() -> Section:
    """Check the profile in use without claiming client hook approval."""
    from codex_sync import Surface, native_profile, validate_native

    sec = Section("Codex control plane")
    try:
        native = native_profile(GITHUB_ROOT)
    except (OSError, ValueError) as exc:
        sec.checks.append(Check("Codex profile", "FAIL", str(exc)))
        return sec
    if native:
        try:
            validate_native(Surface("constellation-root", GITHUB_ROOT))
            sec.checks.append(Check("native Codex profile", "PASS",
                                    "native entry points valid; no projection or adapter required"))
        except (OSError, ValueError) as exc:
            sec.checks.append(Check("native Codex profile", "FAIL", str(exc)))
        sec.checks.append(Check("native hook activation", "INFO",
                                "not inferred by doctor; review configured hooks in Codex /hooks"))
        return sec
    try:
        config = tomllib.loads((GITHUB_ROOT / ".codex/config.toml").read_text())
        enabled = config.get("features", {}).get("hooks", True)
        if not isinstance(enabled, bool):
            raise ValueError("features.hooks must be boolean")
        sec.checks.append(Check("hooks feature", "PASS" if enabled else "FAIL",
                                "project setting; native trust is separate"))
        hooks = json.loads((GITHUB_ROOT / ".codex/hooks.json").read_text())
        if set(hooks) - {"description", "hooks"} or not isinstance(hooks.get("hooks"), dict):
            raise ValueError("unsupported hooks.json structure")
        count = 0
        for groups in hooks["hooks"].values():
            for group in groups:
                for hook in group["hooks"]:
                    timeout = hook.get("timeout")
                    if (hook.get("type") != "command" or not hook.get("command")
                            or isinstance(timeout, bool) or not isinstance(timeout, (int, float))
                            or not 0 < timeout <= 600):
                        raise ValueError("hook missing a command or bounded timeout")
                    count += 1
        if not count or not (GITHUB_ROOT / ".codex/hook_shim.py").is_file():
            raise ValueError("hooks or adapter missing")
        sec.checks.append(Check("hook configuration", "PASS", f"{count} bounded command handlers"))
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        sec.checks.append(Check("hook configuration", "FAIL", "invalid/missing project config, hooks or adapter"))

    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "codex_sync.py"), "--repo", str(GITHUB_ROOT), "--check", "--json"],
            capture_output=True, text=True, timeout=30,
        )
        sec.checks.append(Check("Codex projection", "PASS" if result.returncode == 0 else "FAIL",
                                "canonical sources agree" if result.returncode == 0 else "run codex_sync.py --repo . --check for details"))
    except (OSError, subprocess.TimeoutExpired):
        sec.checks.append(Check("Codex projection", "NOT_RUN", "projection check failed to execute"))
    sec.checks.append(Check("native hook activation", "INFO",
                            "not inferred by doctor; review current project hooks in Codex /hooks"))
    return sec


# --------------------------------------------------------------------------- #
# Section 4 — optional --repo target
# --------------------------------------------------------------------------- #
def _project_types(repo: Path) -> list[str]:
    types: list[str] = []
    if (repo / "pyproject.toml").exists() or (repo / "setup.py").exists() or (repo / "setup.cfg").exists():
        types.append("python")
    if (repo / "package.json").exists():
        types.append("node")
    if (repo / "Makefile").exists() or (repo / "makefile").exists():
        types.append("make")
    return types or ["unknown"]


def _tool_resolvable(repo: Path, name: str) -> bool:
    venv = repo / ".venv" / "bin" / name
    if venv.exists():
        return True
    return shutil.which(name) is not None


def _available_checks(repo: Path) -> list[str]:
    avail: list[str] = []
    py = (repo / "pyproject.toml").exists() or (repo / "setup.py").exists()
    pyproject = ""
    pp = repo / "pyproject.toml"
    if pp.exists():
        try:
            pyproject = pp.read_text()
        except Exception:
            pyproject = ""

    if (py or (repo / "tests").is_dir()) and _tool_resolvable(repo, "pytest"):
        avail.append("pytest")
    if _tool_resolvable(repo, "ruff") and ("ruff" in pyproject or (repo / "ruff.toml").exists() or py):
        avail.append("ruff")
    if _tool_resolvable(repo, "mypy") and ("mypy" in pyproject or (repo / "mypy.ini").exists() or py):
        avail.append("mypy")
    if (repo / "package.json").exists() and _tool_resolvable(repo, "npm"):
        avail.append("npm")
    if ((repo / "Makefile").exists() or (repo / "makefile").exists()) and _tool_resolvable(repo, "make"):
        avail.append("make")
    return avail


def _raw_data_leak(repo: Path) -> list[str]:
    """Tracked files that look like raw research data (should be gitignored)."""
    rc, out = _git(repo, ["ls-files"])
    if rc != 0 or not out:
        return []
    leaks: list[str] = []
    for rel in out.splitlines():
        p = Path(rel)
        if p.suffix.lower() in RAW_DATA_EXTS:
            leaks.append(rel)
        elif p.parts and p.parts[0] in RAW_DATA_DIRS:
            leaks.append(rel)
    return leaks


def _large_staged(repo: Path) -> list[tuple[str, int]]:
    rc, out = _git(repo, ["diff", "--cached", "--name-only"])
    if rc != 0 or not out:
        return []
    big: list[tuple[str, int]] = []
    for rel in out.splitlines():
        f = repo / rel
        try:
            size = f.stat().st_size
        except OSError:
            continue
        if size >= LARGE_STAGED_BYTES:
            big.append((rel, size))
    return big


def section_repo(repo_arg: str) -> Section:
    repo = Path(repo_arg).expanduser().resolve()
    sec = Section(f"repo: {repo.name}")

    if not repo.exists():
        sec.checks.append(Check("path", "FAIL", f"does not exist: {repo}"))
        return sec

    rc, _ = _git(repo, ["rev-parse", "--is-inside-work-tree"])
    if rc != 0:
        sec.checks.append(Check("git", "FAIL", f"not a git repository: {repo}"))
        return sec

    sec.checks.extend(_git_state(repo, "repo"))

    # untracked
    _, untracked = _git(repo, ["ls-files", "--others", "--exclude-standard"])
    if untracked:
        sec.checks.append(
            Check("untracked", "WARN", f"{len(untracked.splitlines())} untracked path(s)")
        )
    else:
        sec.checks.append(Check("untracked", "PASS", "none"))

    # merge conflicts (unmerged index entries)
    _, unmerged = _git(repo, ["ls-files", "--unmerged"])
    if unmerged:
        paths = sorted({line.split("\t", 1)[-1] for line in unmerged.splitlines()})
        sec.checks.append(
            Check("merge-conflict", "FAIL", f"{len(paths)} conflicted path(s): {', '.join(paths[:5])}")
        )
    else:
        sec.checks.append(Check("merge-conflict", "PASS", "none"))

    # project type + available checks
    types = _project_types(repo)
    sec.checks.append(Check("project-type", "INFO", ", ".join(types)))
    avail = _available_checks(repo)
    sec.checks.append(
        Check("available-checks", "INFO", ", ".join(avail) if avail else "none resolvable")
    )

    # raw-data hygiene
    leaks = _raw_data_leak(repo)
    if leaks:
        sec.checks.append(
            Check("gitignored-raw-data", "WARN",
                  f"{len(leaks)} raw-data file(s) tracked: {', '.join(leaks[:5])}")
        )
    else:
        sec.checks.append(Check("gitignored-raw-data", "PASS", "no raw data tracked"))

    # oversized staged blobs
    big = _large_staged(repo)
    if big:
        worst = ", ".join(f"{rel} ({size // (1024 * 1024)}MiB)" for rel, size in big[:5])
        sec.checks.append(Check("large-staged", "WARN", f"{len(big)} >=5MiB staged: {worst}"))
    else:
        sec.checks.append(Check("large-staged", "PASS", "none >=5MiB staged"))

    return sec


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #
def run(repo_arg: str | None) -> list[Section]:
    sections = [
        section_validators(),
        section_hub_structure(),
        section_codex(),
        section_hub_git(),
    ]
    if repo_arg:
        sections.append(section_repo(repo_arg))
    return sections


_LABEL = {"PASS": "PASS", "WARN": "WARN", "FAIL": "FAIL", "INFO": "info", "NOT_RUN": "not-run"}


def render_text(sections: list[Section], overall: str) -> str:
    lines = ["== CONSTELLATION DOCTOR =="]
    for sec in sections:
        lines.append("")
        lines.append(f"[ {sec.name} ]  {sec.status}")
        for c in sec.checks:
            tag = _LABEL.get(c.status, c.status)
            row = f"  {tag:<8} {c.label}"
            if c.detail:
                row += f"  —  {c.detail}"
            lines.append(row)
    lines.append("")
    lines.append(f"CONSTELLATION DOCTOR: {overall}")
    return "\n".join(lines)


def to_dict(sections: list[Section], overall: str) -> dict:
    return {
        "status": overall,
        "hub": str(GITHUB_ROOT),
        "sections": [
            {
                "name": s.name,
                "status": s.status,
                "checks": [
                    {"label": c.label, "status": c.status, "detail": c.detail} for c in s.checks
                ],
            }
            for s in sections
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--repo", default=None, help="Also profile a target repo (path).")
    ap.add_argument("--json", action="store_true", help="Emit JSON.")
    args = ap.parse_args()

    sections = run(args.repo)
    overall = _verdict(max((s.rank for s in sections), default=0))

    if args.json:
        print(json.dumps(to_dict(sections, overall), indent=2))
    else:
        print(render_text(sections, overall))

    return 1 if overall == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""newslab-daily-reports — once-per-day NewsLab → OmarOS study generator.

The launchd agent points here. One run does, in order:

  1. Deterministic NewsLab pipeline (live GDELT, or a replay fixture for tests)
     → governed markdown report + per-topic article-count history.
  2. Context assembly (regime wiring + empty-data guard) → a deterministic
     hand-off bundle.
  3. Safety gates: execution-safety config check; non-contamination is N/A for
     the training-free deterministic tagger (logged, see below).
  4. Headless Claude (Sonnet) elevates the bundle into a scholar-style study
     written into the vault — observation-only, never a trade signal.
  5. Post-write safety lint + frontmatter validation; on any violation the LLM
     output is discarded and the run aborts (the deterministic report survives).
  6. One scoped commit of exactly the report, then push (authorised), plus an
     explicit investigation-log entry (the launchd commit fires no Claude hooks,
     so traceability is honoured here rather than by post_commit_doc_tracer).

Idempotent per ``as_of`` date: a second fire the same day is a no-op.

Commit ownership (B2): the headless session runs with ``OMAROS_AUTO_COMMIT=0`` /
``OMAROS_AUTO_PUSH=0`` and no git tools, so the vault's Stop-hook auto-commit
never bundles unrelated files or races this script. This script, run by launchd,
triggers no Claude hooks at all and commits deterministically.

Runs under the OmarOS venv; shells out to the NewsLab venv for steps 1–2.
"""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import safety_lint  # noqa: E402
import state  # noqa: E402

REPO_ROOT = Path("/Users/omarkhalil/OmarOS")                 # OmarOS
SKILL_DIR = Path(__file__).resolve().parent
NEWSLAB = Path(os.environ.get("NLDR_NEWSLAB", "/Users/omarkhalil/GitHub/NewsLab"))
NEWSLAB_PY = NEWSLAB / ".venv" / "bin" / "python"
CLAUDE = Path(os.environ.get("NLDR_CLAUDE", "/Users/omarkhalil/.local/bin/claude"))

TOPICS = os.environ.get("NLDR_TOPICS", "energy,geopolitics,macro,markets,supply_chains,social_unrest,technology")
TIMESPAN = os.environ.get("NLDR_TIMESPAN", "1d")
MAX_RECORDS = os.environ.get("NLDR_MAX", "250")                # GDELT DOC artlist hard cap; honours platform.yaml osint.max_articles_per_topic
REPLAY = os.environ.get("NLDR_REPLAY", "").strip()              # fixture path → offline/test mode
SOURCE = os.environ.get("NLDR_SOURCE", "cache")                 # cache | live | replay-implied-by-NLDR_REPLAY
LLM_ON = os.environ.get("NLDR_LLM", "1") == "1"
PUSH = os.environ.get("NLDR_PUSH", "1") == "1"
COMMIT = os.environ.get("NLDR_COMMIT", "1") == "1"
FORCE = os.environ.get("NLDR_FORCE", "0") == "1"
# AS_OF must match the date run_daily_pipeline.py stamps (it uses now(UTC) and
# offers no override), so this is deliberately not env-configurable.
AS_OF = datetime.now(UTC).strftime("%Y-%m-%d")

REPORT_PATH = NEWSLAB / "outputs" / "reports" / f"{AS_OF}.md"
HISTORY_PATH = NEWSLAB / "outputs" / "features" / "history.json"
CONTEXT_PATH = NEWSLAB / "outputs" / "context" / f"{AS_OF}.md"
_DEST_OVERRIDE = os.environ.get("NLDR_DEST", "").strip()
DEST_PATH = (
    Path(_DEST_OVERRIDE)
    if _DEST_OVERRIDE
    else REPO_ROOT / "11_Documents_and_Reports" / "Generated_Reports" / "NewsLab" / f"{AS_OF}_global_news_intelligence.md"
)
try:
    DEST_REL = DEST_PATH.relative_to(REPO_ROOT)
except ValueError:
    DEST_REL = DEST_PATH  # outside the vault (validation only — commit is skipped)
LOG_DIR = REPO_ROOT / ".claude" / "logs"


def log(msg: str) -> None:
    print(f"[newslab-daily {AS_OF}] {msg}", flush=True)


def count_covered_topics() -> int:
    """Topics with >0 articles in the rendered report (for the importer's
    self-healing re-run decision)."""
    if not REPORT_PATH.exists():
        return 0
    n, in_table = 0, False
    for line in REPORT_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("## Global risk overview"):
            in_table = True
            continue
        if in_table and line.startswith("## "):
            break
        if in_table and line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 2 or cells[0] in {"Topic", "---"} or cells[0].startswith("-"):
                continue
            try:
                n += 1 if int(cells[1]) > 0 else 0
            except ValueError:
                continue
    return n


def run(cmd: list[str], *, cwd: Path, env: dict | None = None, timeout: int = 1800) -> int:
    log("$ " + " ".join(str(c) for c in cmd))
    proc = subprocess.run(cmd, cwd=str(cwd), env=env, timeout=timeout, check=False)
    return proc.returncode


def stage_pipeline() -> int:
    """Produce the deterministic report. Default 'cache' reads the drip corpus
    (no network burst); 'live' bursts GDELT (throttle-prone); NLDR_REPLAY forces
    an offline fixture build (tests)."""
    report_out = str(NEWSLAB / "outputs" / "reports")
    if REPLAY:
        cmd = [
            str(NEWSLAB_PY), "scripts/run_daily_pipeline.py",
            "--topics", TOPICS, "--timespan", TIMESPAN, "--max", MAX_RECORDS,
            "--report-out", report_out, "--history", str(HISTORY_PATH), "--replay", REPLAY,
        ]
        return run(cmd, cwd=NEWSLAB, env={**os.environ})
    if SOURCE == "cache":
        cmd = [
            str(NEWSLAB_PY), str(SKILL_DIR / "cache_pipeline.py"),
            "--as-of", AS_OF, "--newslab-root", str(NEWSLAB),
            "--topics", TOPICS, "--timespan", TIMESPAN, "--max", MAX_RECORDS,
            "--report-out", report_out, "--history", str(HISTORY_PATH),
        ]
        return run(cmd, cwd=NEWSLAB, env={**os.environ})
    cmd = [
        str(NEWSLAB_PY), "scripts/run_daily_pipeline.py",
        "--topics", TOPICS, "--timespan", TIMESPAN, "--max", MAX_RECORDS,
        "--report-out", report_out, "--history", str(HISTORY_PATH),
    ]
    return run(cmd, cwd=NEWSLAB, env={**os.environ})


def stage_context() -> int:
    cmd = [
        str(NEWSLAB_PY), str(SKILL_DIR / "assemble_context.py"),
        "--as-of", AS_OF, "--newslab-root", str(NEWSLAB),
        "--report", str(REPORT_PATH), "--history", str(HISTORY_PATH), "--out", str(CONTEXT_PATH),
    ]
    return run(cmd, cwd=NEWSLAB, env={**os.environ}, timeout=300)


def stage_safety_gates() -> bool:
    """Execution-safety config check; non-contamination is vacuous for the MVP."""
    code = run([str(NEWSLAB_PY), "scripts/check_execution_safety.py"], cwd=NEWSLAB, env={**os.environ}, timeout=120)
    if code != 0:
        log("execution-safety check failed — aborting")
        return False
    log(
        "non-contamination (I-8) N/A: tagger is the training-free deterministic "
        "ontology matcher and the LLM tagger is off, so there is no training set "
        "to leak into the live window. (Re-enable the audit before any trained tagger.)"
    )
    return True


_STYLE_FRAMING = (
    "You are writing a rigorous OSINT market-intelligence study for Omar's OmarOS vault, "
    "in the voice of the scholar-quant-docs skill: formal yet intuitive, layered exposition, "
    "every technical term defined inline, claims anchored to the data given. HARD CONSTRAINTS: "
    "(1) This is an OBSERVATION/monitoring study of a MEDIA-COVERAGE process, never a trade signal. "
    "Do NOT emit buy/sell calls, price targets, directional price forecasts, expected returns, or "
    "over/under-weight ratings. Hedged co-movement language only; no causal 'news X caused move Y'. "
    "(2) Use ONLY the data in the context bundle — invent no numbers, entities, or events. "
    "(3) Reproduce the mandatory Methodological caveats block VERBATIM under a '## Methodological caveats' heading. "
    "(4) Mathematics in Obsidian delimiters: $...$ inline, $$...$$ display. "
    "(5) Frontmatter must use ONLY these keys: title, status, note_type, created, updated, author, domain, tags, "
    "source, ai_generated, ai_reviewed — with note_type: report and status: active. No other frontmatter keys."
)


def _build_prompt() -> str:
    return (
        f"Read the deterministic context bundle at {CONTEXT_PATH} (use the Read tool). "
        f"It is your SOLE source of facts. Then write a comprehensive, scholarly daily global "
        f"news-intelligence study and SAVE it (Write tool) to exactly:\n"
        f"  {DEST_PATH}\n\n"
        f"The file must begin with this YAML frontmatter (fill the title/date for {AS_OF}):\n"
        f"---\n"
        f'title: "Global News Intelligence — {AS_OF}"\n'
        f"status: active\n"
        f"note_type: report\n"
        f"created: {AS_OF}\n"
        f"updated: {AS_OF}\n"
        f"author: NewsLab\n"
        f"domain: 11_Documents_and_Reports\n"
        f"tags: [osint, newslab, gdelt, market-intelligence]\n"
        f"source: gdelt\n"
        f"ai_generated: true\n"
        f"ai_reviewed: false\n"
        f"---\n\n"
        f"Structure: an executive read of the day's media-coverage state; a per-topic deep dive "
        f"(energy, geopolitics, macro, markets, supply chains, social unrest, technology) interpreting "
        f"article volume, the regime label and its rationale, top entities/domains/countries, and any "
        f"z-score anomalies; a cross-topic synthesis of the aggregate regime; and an explicit "
        f"epistemic-status / limitations discussion. Then reproduce the mandatory Methodological caveats "
        f"block VERBATIM under '## Methodological caveats'. Be thorough and analytical, but observation-only: "
        f"this measures what the media reported, not what the world did, and it is not a trading signal. "
        f"Do not run git; only write the file."
    )


def stage_llm() -> bool:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    child_env = {
        **os.environ,
        "OMAROS_AUTO_COMMIT": "0",     # neutralise the vault Stop-hook auto-commit
        "OMAROS_AUTO_PUSH": "0",       # and its auto-push, inside the headless session
    }
    # Run from a neutral directory so the headless session does NOT load the vault's
    # large CLAUDE.md (the dominant per-run cache cost) or fire OmarOS/NewsLab project
    # hooks. All facts come from the bundle and all instructions from the prompt; the
    # vault is reachable for the Write via --add-dir. (Red-team M5 cost lever.)
    run_cwd = Path.home() / ".cache" / "newslab-daily-run"
    run_cwd.mkdir(parents=True, exist_ok=True)
    out_log = LOG_DIR / "newslab_daily.out.json"
    err_log = LOG_DIR / "newslab_daily.err.log"
    cmd = [
        str(CLAUDE), "-p", _build_prompt(),
        "--model", "claude-sonnet-4-6",
        "--permission-mode", "acceptEdits",
        "--add-dir", str(REPO_ROOT),
        "--add-dir", str(NEWSLAB),
        "--allowedTools", "Read,Edit,Write,Grep,Glob",
        "--append-system-prompt", _STYLE_FRAMING,
        "--output-format", "json",
    ]
    log("invoking headless Claude (sonnet) to elevate the report")
    with out_log.open("a", encoding="utf-8") as out_f, err_log.open("a", encoding="utf-8") as err_f:
        proc = subprocess.run(
            cmd, cwd=str(run_cwd), env=child_env, timeout=1800,
            stdout=out_f, stderr=err_f, check=False,
        )
    if proc.returncode != 0:
        log(f"headless Claude exited {proc.returncode} — see {err_log}; aborting (deterministic report intact)")
        return False
    if not DEST_PATH.exists():
        log(f"headless Claude did not produce {DEST_PATH} — aborting")
        return False

    violations = safety_lint.lint(
        DEST_PATH.read_text(encoding="utf-8"),
        REPORT_PATH.read_text(encoding="utf-8"),
    )
    if violations:
        log("SAFETY LINT FAILED — discarding LLM output:")
        for v in violations:
            log(f"  - {v}")
        DEST_PATH.unlink(missing_ok=True)
        return False
    if not _frontmatter_ok(DEST_PATH):
        log("frontmatter validation failed — leaving file uncommitted for review; aborting")
        return False
    log("LLM report passed safety lint + frontmatter validation")
    return True


def stage_observation_only() -> bool:
    """LLM-off fallback: publish the deterministic report with vault frontmatter."""
    body = REPORT_PATH.read_text(encoding="utf-8")
    frontmatter = (
        "---\n"
        f'title: "Global News Intelligence — {AS_OF}"\n'
        "status: active\nnote_type: report\n"
        f"created: {AS_OF}\nupdated: {AS_OF}\nauthor: NewsLab\n"
        "domain: 11_Documents_and_Reports\n"
        "tags: [osint, newslab, gdelt, market-intelligence]\n"
        "source: gdelt\nai_generated: true\nai_reviewed: false\n---\n\n"
    )
    DEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEST_PATH.write_text(frontmatter + body, encoding="utf-8")
    return True


def _frontmatter_ok(path: Path) -> bool:
    try:
        sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
        from _common import NOTE_TYPE_ENUM, STATUS_ENUM, parse_frontmatter
        from metadata_enforcer import ALLOWED_KEYS, REQUIRED_KEYS
    except Exception as exc:  # degrade gracefully — never block on tooling import
        log(f"frontmatter validator unavailable ({exc!r}); skipping strict check")
        return True
    fm, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
    if not fm:
        log("no frontmatter parsed")
        return False
    for key in REQUIRED_KEYS:
        if key not in fm:
            log(f"missing required frontmatter key: {key}")
            return False
    if fm.get("note_type") not in NOTE_TYPE_ENUM:
        log(f"note_type {fm.get('note_type')!r} not in enum")
        return False
    if fm.get("status") not in STATUS_ENUM:
        log(f"status {fm.get('status')!r} not in enum")
        return False
    for key in fm:
        if key not in ALLOWED_KEYS:
            log(f"frontmatter key not allowed: {key}")
            return False
    return True


def git(*args: str, timeout: int = 60) -> int:
    return run(["git", "-C", str(REPO_ROOT), *args], cwd=REPO_ROOT, env={**os.environ}, timeout=timeout)


def stage_commit() -> bool:
    if git("add", "--", str(DEST_REL)) != 0:
        log("git add failed")
        return False
    # Nothing staged (e.g. byte-identical re-run) → treat as success, no empty commit.
    if subprocess.run(["git", "-C", str(REPO_ROOT), "diff", "--cached", "--quiet"], check=False).returncode == 0:
        log("no staged changes for the report — skipping commit")
        return True
    # "Add" on first publish of the day, "Refresh" when a drip-driven rerun upgrades it.
    status = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "diff", "--cached", "--name-status", "--", str(DEST_REL)],
        capture_output=True, text=True, check=False,
    ).stdout.strip()
    verb = "Add" if status.startswith("A") else "Refresh"
    covered = count_covered_topics()
    msg = f"{verb} NewsLab daily global news intelligence report for {AS_OF} ({covered} topics)"
    if git("commit", "-m", msg) != 0:
        log("git commit failed")
        return False
    _append_trace(msg)
    if PUSH:
        if git("push", "origin", "HEAD", timeout=120) != 0:
            log("git push failed (commit is local) — continuing")
        else:
            log("pushed to origin")
    return True


def _append_trace(commit_msg: str) -> None:
    """Honour 'no commit un-logged': launchd commits fire no doc-tracer hook."""
    log_path = REPO_ROOT / "docs" / "investigation_logs" / f"{AS_OF}_session.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = (
        f"\n### newslab-daily-reports (automated, {AS_OF})\n"
        f"- {commit_msg}\n"
        f"- report: `{DEST_REL}`\n"
        f"- mode: {'replay' if REPLAY else 'live-gdelt'}; llm: {'on' if LLM_ON else 'off'}\n"
    )
    with log_path.open("a", encoding="utf-8") as f:
        f.write(entry)


def main() -> int:
    st = state.load_state()
    if state.already_ran(st, AS_OF) and not FORCE:
        log("already ran today — no-op (set NLDR_FORCE=1 to override)")
        return 0

    if stage_pipeline() != 0:
        log("deterministic pipeline failed — aborting")
        return 1

    ctx_code = stage_context()
    if ctx_code == 2:
        log("empty data (zero articles) — no report, no commit. Will retry on next run.")
        return 0
    if ctx_code != 0:
        log("context assembly failed — aborting")
        return 1

    if not stage_safety_gates():
        return 1

    published = stage_llm() if LLM_ON else stage_observation_only()
    if not published:
        return 1

    if not COMMIT:
        log(f"dry run (NLDR_COMMIT=0): report at {DEST_PATH}; not committing, not claiming the day")
        return 0

    if not stage_commit():
        return 1

    state.save_state({"last_run_date": AS_OF, "topics_covered": count_covered_topics()})
    log("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())

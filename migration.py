"""Plan, protect and retire explicit legacy architecture files.

The default operation only inventories. Retirement requires the recorded replacement
checks, an unchanged manifest, and a verified private backup. Git histories and
indexes are backed up; no command stages, resets, rewrites or publishes a repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import plistlib
import shlex
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
from typing import Any

from constellation.install import _rename_exclusive

SOURCE = Path(__file__).resolve().parent
HOME = Path.home()
LEGACY_VAULT_DOCUMENTS = (
    '17_Dashboards/Constellation.md',
    '07_AI_and_Agents/Reference/skill_library_audit_2026-04-17.md',
    '20_System_Governance/Policies/Model_Tiering.md',
    '20_System_Governance/Policies/Never_Skip_Invariants.md',
    '20_System_Governance/Policies/Post_Git_Safety_Loop.md',
    '20_System_Governance/Policies/Semantic_Kernel_Hard_Law.md',
    '20_System_Governance/Policies/Skill_First_Dispatch.md',
    '20_System_Governance/Architecture/Worktree_State_Machine.md',
    '20_System_Governance/Decisions/2026-04-11_genesis_prompt_constitutional_rollout.md',
    '20_System_Governance/Decisions/2026-04-12_model_tiering_sonnet_default.md',
    '20_System_Governance/Decisions/2026-04-16_migrate_capa1_agents_to_skills.md',
    '20_System_Governance/Decisions/2026-06-11_skills_first_restructuring.md',
    '20_System_Governance/Decisions/2026-07-30_adapt_model_tiering_to_codex.md',
    '20_System_Governance/Decisions/2026-08-09_runtime_specific_hook_enforcement.md',
    '20_System_Governance/Decisions/2026-08-10_harden_claude_first_codex_parity_github.md',
    '20_System_Governance/Decisions/2026-09-05_simplify_native_codex.md',
    '20_System_Governance/Decisions/2026-10-19_constellation_document_sync.md',
    '11_Documents_and_Reports/Execution_Traces/2026-09-05/codex_hook_trust.md',
    '11_Documents_and_Reports/Execution_Traces/2026-09-05/codex_minimal_workflow.md',
    '11_Documents_and_Reports/Execution_Traces/2026-09-09/github_codex_native_profile.md',
    '11_Documents_and_Reports/Execution_Traces/2026-09-17/github_codex_coherencia.md',
    '11_Documents_and_Reports/Execution_Traces/2026-10-17/omaros_native_ai.md',
    '11_Documents_and_Reports/Execution_Traces/2026-10-18/constellation_constellation_5f8c2e04-c2ba-4eb1-b66b-1fc9f1a96758.md',
    '11_Documents_and_Reports/Execution_Traces/2026-10-18/constellation_constellation_81ad9a78-bf5f-42fa-af2d-3e475318a5d0.md',
    '11_Documents_and_Reports/Execution_Traces/2026-10-18/constellation_shared_runtime.md',
    '11_Documents_and_Reports/Execution_Traces/2026-10-18/omaros_constellation_v1_2_alignment.md',
    '11_Documents_and_Reports/Execution_Traces/2026-10-19/constellation_document_sync.md',
    '11_Documents_and_Reports/Execution_Traces/2026-10-27/claude_native_structure.md',
    '11_Documents_and_Reports/Execution_Traces/2026-10-29/constellation_english_distribution.md',
    '11_Documents_and_Reports/Execution_Traces/2026-10-29/constellation_legacy_cleanup.md',
    '11_Documents_and_Reports/Execution_Traces/2026-10-29/constellation_structure_and_runtime.md',
    '11_Documents_and_Reports/Execution_Traces/2026-11-02/centralizacion_constellation.md',
    '11_Documents_and_Reports/Execution_Traces/2026-11-02/consolidacion_codex_raiz_usuario.md',
    '11_Documents_and_Reports/Execution_Traces/2026-11-15/centralizacion_codex.md',
    '11_Documents_and_Reports/Incidents/2026-08-10_github_constellation_partial_write.md',
    'docs/recovery_logs/2026-08-10_github_constellation_partial_write.md',
)

REQUIRED_CHECKS = ("native_session", "omaros_note", "parallel_repositories",
                   "stale_review", "foreign_index", "private_outgoing", "interrupted_push")


def digest(path: Path) -> str:
    """Hash regular bytes or the exact symlink target without following a link."""
    value = os.readlink(path).encode() if path.is_symlink() else path.read_bytes()
    return hashlib.sha256(value).hexdigest()


def git(root: Path, *args: str) -> str:
    """Read one Git fact without shell interpretation or replacements."""
    result = subprocess.run(["git", "--no-replace-objects", "-C", str(root), *args],
                            capture_output=True, text=True, check=True)
    return result.stdout.strip()


def candidate_roots() -> list[tuple[Path, str]]:
    """List only architecture-owned roots; runtime/user data is not a candidate."""
    candidates: list[tuple[Path, str]] = []
    old = HOME / ".codex"
    for name in (".codex", ".github", "README.md", "REVIEW.md", ".gitignore"):
        candidates.append((old / name, "Retired source checkout; Git history preserved"))
    for name in ("constellation/catalog", "constellation/run", "constellation/hook.py",
                 "constellation/receipt.json", "constellation/.install.lock",
                 "constellation-vault-guards", "constellation-vault.json", "hooks/omaros_permission_guard.py",
                 "plugins/cache/constellation", "plugins/marketplaces/constellation"):
        candidates.append((old / name, "Replaced installed distribution and adapters"))
    projects = json.loads((SOURCE / "profiles/projects.json").read_text())["projects"]
    for project in projects:
        root = Path(project["root"])
        if project["management"] != "native" or root == SOURCE:
            continue
        folder = root / ".codex"
        if folder.exists():
            for child in folder.iterdir():
                if child.name not in {"config.toml", "hooks.json", "agents", "state", "sessions", "log", "cache"}:
                    candidates.append((child, "Central project profile and common entry replace local architecture"))
    candidates.append((HOME / "Library/LaunchAgents/org.constellation.codex-update.plist",
                       "Bundle updater obsolete with one source checkout"))
    # Technical architecture documents are named explicitly; domain notes,
    # execution evidence, imported knowledge and conversations are not selected.
    vault = HOME / "OmarOS"
    for name in LEGACY_VAULT_DOCUMENTS:
        candidates.append((vault / name, "Retired technical architecture document; local modifications protected"))
    # Setup audit paths were individually classified by an independent reader.
    # Keep their required skill templates centrally before retiring originals.
    selected = git(vault, "ls-files", "--", "07_AI_and_Agents/Setup_Audits", "07_AI_and_Agents/Registry").splitlines()
    for name in selected:
        candidates.append((vault / name, "Retired AI setup audit or duplicate capability registry"))
    for name in ("README.md", "architecture.md", "codex_parity.md", "control_plane_audit.md",
                 "git_as_research_ledger.md", "how_to_add_a_repo.md", "research_pipeline.md"):
        candidates.append((HOME / "GitHub/.claude/docs" / name, "Retired shared AI architecture documentation"))
    for name in (".claude/CLAUDE.md", ".claude/scripts/constellation_commit.py", ".claude/scripts/codex_sync.py",
                 ".claude/templates/codex_hook_shim.py", ".claude/hooks/secret_scan.sh",
                 ".claude/hooks/changed_python_syntax.sh", ".claude/commands/codex-sync.md",
                 ".claude/tests/test_codex_sync.py", ".claude/tests/test_codex_projection_safety.py",
                 ".claude/tests/test_codex_workflow.py", ".claude/templates/codex_hub_agents.md",
                 ".claude/registry/codex_repo_briefs.json", ".claude/scripts/research_committer.py",
                 ".claude/tests/test_research_committer_safety.py", ".claude/contracts/commit_policy.md",
                 ".claude/registry/repo_commit_policy.yaml"):
        candidates.append((HOME / "GitHub" / name, "Retired duplicate orchestrator or Codex projection"))
    for root in (HOME / "GitHub", vault):
        for name in ("REVIEW.md", ".claude/README.md"):
            candidates.append((root / name, "Central README and review policy replace duplicate instructions"))
    candidates.append((vault / ".claude/rules/native-workflow.md", "Shared instructions replace old Claude workflow rule"))
    candidates.append((vault / ".claude/hooks/constellation.py", "Shared CLI replaces Claude lifecycle adapter"))
    candidates.append((vault / ".claude/tests/test_constellation.py", "Retired old adapter regression suite"))
    candidates.append((HOME / ".claude/skills/constellation", "Retired duplicate distribution; native skills use central source"))
    candidates.append((HOME / ".claude/README.md", "Central README replaces obsolete device architecture guide"))
    maintenance = HOME / ".codex/docs/maintenance"
    candidates.append((maintenance / "README.md", "Retired native architecture and profile registry guide"))
    for release in ("release-0co6tip3", "release-apj40qy5", "release-r1_s5h6z"):
        for name in ("bundle", "AGENTS.md", "instructions-install.py", "sync.py"):
            candidates.append((maintenance / "updates" / release / name,
                               "Retired release staging copy; private recovery receipt is preserved"))
    return [(path, reason) for path, reason in candidates if path.exists() or path.is_symlink()]




def _sync_directory(path: Path) -> None:
    """Persist entry renames before the next recovery phase."""
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _quarantine(path: Path, destination: Path, expected_sha256: str) -> None:
    """Capture and validate an entry without deleting a concurrent version.

    Validation happens on the captured entry, closing the check-to-unlink race.
    Unexpected bytes return to the original name only if that name is still
    empty. Otherwise both versions remain reachable, and the error names the
    quarantine. Captures are retained even on success, including open inodes
    which an existing writer could still modify after the rename.
    """
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    _rename_exclusive(path, destination)
    _sync_directory(path.parent)
    _sync_directory(destination.parent)
    if digest(destination) != expected_sha256:
        try:
            _rename_exclusive(destination, path)
        except FileExistsError:
            pass
        else:
            _sync_directory(path.parent)
            _sync_directory(destination.parent)
        raise ValueError(f"Concurrent edit preserved: {path}; quarantine: {destination}")


def atomic_write(path: Path, content: bytes, *, mode: int = 0o600,
                 expected_sha256: str | None = None,
                 quarantine: Path | None = None) -> None:
    """Durably write a private journal or replace a protected consumer.

    Args:
        path: Destination file; its parent must already exist.
        content: Complete intended replacement bytes.
        mode: Permissions for the new file.
        expected_sha256: Required original digest for a consumer replacement.
            Omit only for migration-owned journals, with one migration writer.
        quarantine: Durable capture location in the private backup. If omitted
            for a protected replacement, retain a uniquely named sibling.

    Raises:
        ValueError: A captured entry differs from the expected original.
        OSError: A concurrent destination exists or an exclusive move fails.
    """
    descriptor, name = tempfile.mkstemp(prefix=".migration-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            os.fchmod(stream.fileno(), mode)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        if expected_sha256 is None:
            os.replace(temporary, path)
        else:
            captured = quarantine or temporary.with_name(temporary.name + ".before")
            _quarantine(path, captured, expected_sha256)
            # A writer can recreate the name after capture. Never replace it.
            _rename_exclusive(temporary, path)
        _sync_directory(path.parent)
    finally:
        if temporary.exists():
            temporary.unlink()


def record_intent(backup: Path, name: str, paths: list[str]) -> None:
    """Persist the recovery intent before its corresponding filesystem mutation."""
    record = backup / name
    previous = json.loads(record.read_text()) if record.exists() else []
    values = list(dict.fromkeys(previous + paths))
    atomic_write(record, (json.dumps(values, indent=2) + "\n").encode())


def consumer_edits() -> list[dict[str, str]]:
    """Prepare exact native entries and active automation rewires for review."""
    result = []
    projects = json.loads((SOURCE / "profiles/projects.json").read_text())["projects"]
    for project in projects:
        root = Path(project["root"])
        if project["management"] != "native" or root == SOURCE:
            continue
        path = root / "AGENTS.md"
        content = (f"# {root.name}\n\n"
                   f"Lee [{project['id']}]({SOURCE / project['profile']}) y "
                   f"las [instrucciones comunes]({SOURCE / 'instructions/AGENTS.md'}).\n"
                   "Respeta además los AGENTS.md de las carpetas afectadas.\n")
        if path.exists():
            result.append({"path": str(path), "sha256": digest(path), "content": content,
                           "reason": "Replace duplicated orchestration with central profile entry"})
    for path, content in [
        (HOME / ".claude/CLAUDE.md", f"# Omar\n\n@{SOURCE / 'instructions/AGENTS.md'}\n\nLee las skills nativas pertinentes. Respeta permisos y capacidad efectiva de Claude.\n"),
        (HOME / "GitHub/CLAUDE.md", f"# Workspace\n\n@{SOURCE / 'instructions/AGENTS.md'}\n@{SOURCE / 'profiles/workspace.md'}\n"),
        (HOME / "OmarOS/CLAUDE.md", f"# OmarOS\n\n@{SOURCE / 'instructions/AGENTS.md'}\n@{SOURCE / 'profiles/omaros.md'}\n\nUsa el CLI central y las herramientas nativas de Claude con los permisos de sesión.\n"),
    ]:
        result.append({"path": str(path), "sha256": digest(path), "content": content,
                       "reason": "Native Claude entry loads shared instructions and project profile"})
    documentation = HOME / ".claude/docs/README.md"
    content = documentation.read_text()
    old_paragraph = (
        "La [entrada global](../README.md) explica la estructura. La fuente reproducible\n"
        "y las reglas de mantenimiento están en\n"
        "[profiles](/Users/omarkhalil/.codex/.codex/profiles/README.md). Los recibos de operaciones\n"
    )
    replacement = (
        f"El [README de Constellation]({SOURCE / 'README.md'}) explica la arquitectura\n"
        "y su mantenimiento. Los recibos de operaciones\n"
    )
    if old_paragraph not in content and replacement not in content:
        raise ValueError("Provider documentation pointer differs from the reviewed paragraph")
    result.append({"path": str(documentation), "sha256": digest(documentation),
                   "content": content.replace(old_paragraph, replacement),
                   "reason": "Update architecture pointer while preserving official documentation guidance"})
    documentation = HOME / ".codex/docs/README.md"
    content = documentation.read_text()
    introduction = ("# Documentación oficial local de Codex\n\n"
                    f"Consulta el [README de Constellation]({SOURCE / 'README.md'}) "
                    "para instalar, usar y revertir la arquitectura de IA.\n\n")
    legacy_footer = (
        "\nLas [instrucciones para otros entornos](/Users/omarkhalil/.codex/.codex/profiles/README.md)\n"
        "explican qué se publica y qué se regenera. El registro local del perfil está en\n"
        "`docs/maintenance/profiles.json`; los registros locales de limpieza también\n"
        "permanecen bajo `docs/maintenance/`. Cada proyecto conserva sus propios contratos.\n"
    )
    if content.startswith("# Codex: mapa y documentación local\n") and legacy_footer in content:
        content = introduction + content[content.index("[INDEX.md](official/INDEX.md)"):].replace(legacy_footer, "")
    elif not content.startswith(introduction):
        raise ValueError("Codex documentation differs from the reviewed provider index")
    result.append({"path": str(documentation), "sha256": digest(documentation), "content": content,
                   "reason": "Replace obsolete source/profile pointers and retain official documentation directions"})
    monitor = HOME / "OmarOS/08_Systems_and_Infrastructure/Monitoring/notes_reminders_monitor.py"
    before = monitor.read_text()
    after = before.replace('entry = Path(__file__).resolve().parents[2] / ".codex/workflow.py"',
                           f'entry = Path({str(SOURCE / "constellation.py")!r})')
    after = after.replace('[sys.executable, "-I", "-B", str(entry), "--root", str(root), "guard-status"]',
                          '[sys.executable, "-I", "-B", str(entry), "guard-status", "--root", str(root)]')
    if after == before and str(SOURCE / "constellation.py") not in before:
        raise ValueError("Monitor guard call is not the reviewed original")
    result.append({"path": str(monitor), "sha256": digest(monitor), "content": after,
                   "reason": "Keep active monitor native guard verification"})
    settings = HOME / "OmarOS/.claude/settings.json"
    config = json.loads(settings.read_text())
    hooks = config.get("hooks", {})
    for event in list(hooks):
        kept = []
        for group in hooks[event]:
            group = {**group, "hooks": [h for h in group.get("hooks", [])
                                       if ".claude/hooks/constellation.py" not in h.get("command", "")
                                       and str(SOURCE / "constellation.py") + " hook " not in h.get("command", "")]}
            if group["hooks"]:
                kept.append(group)
        if kept:
            hooks[event] = kept
        else:
            del hooks[event]
    command = shlex.quote("/opt/homebrew/bin/python3") + " " + shlex.quote(str(SOURCE / "constellation.py"))
    hooks.setdefault("PreToolUse", []).append({"matcher": "^(Write|Edit|MultiEdit|NotebookEdit)$",
        "hooks": [{"type": "command", "command": command + " hook pre-tool", "timeout": 30}]})
    hooks.setdefault("Stop", []).append({"hooks": [{"type": "command", "command": command + " hook stop", "timeout": 30}]})
    config["hooks"] = hooks
    config.get("env", {}).pop("CONSTELLATION_HOOK_OWNER", None)
    result.append({"path": str(settings), "sha256": digest(settings),
                   "content": json.dumps(config, ensure_ascii=False, indent=2) + "\n",
                   "reason": "Use shared hooks without prompt routing or duplicate agent observation"})
    settings = HOME / "GitHub/.claude/settings.json"
    content = settings.read_text()
    for name in ("secret_scan.sh", "changed_python_syntax.sh"):
        content = content.replace('$CLAUDE_PROJECT_DIR/.claude/hooks/' + name,
                                  str(SOURCE / "resources/automations" / name))
    result.append({"path": str(settings), "sha256": digest(settings), "content": content,
                   "reason": "Preserve shared secret and syntax hooks from single central source"})
    for filename, name, purpose in [
        ("repo-doctor.md", "repo-doctor", "Inspect project state, native loading and relevant checks without edits."),
        ("commit-research.md", "commit-research", "Publish the exact reviewed task through the common CLI, preserving unrelated staging."),
    ]:
        path = HOME / "GitHub/.claude/commands" / filename
        content = (f"---\nname: {name}\ndescription: {purpose}\n---\n\n"
                   f"Read `{SOURCE / 'README.md'}` and the current task/profile.\n"
                   f"Use `{SOURCE / 'constellation.py'}` with native session and author identities.\n"
                   "For inspection, use status and relevant project checks; do not mutate or publish.\n"
                   "For authorized publication, use begin, check, independent review, commit, push and finish.\n"
                   "Report evidence and exact remote branch/SHA. Do not infer scientific validity from Git checks.\n")
        result.append({"path": str(path), "sha256": digest(path), "content": content,
                       "reason": "Native command delegates to single central diagnostic/publication contract"})
    launch = HOME / "Library/LaunchAgents/com.omar.constellation-knowledge-sync.plist"
    data = plistlib.loads(launch.read_bytes())
    argv = data["ProgramArguments"]
    argv[1] = str(SOURCE / "resources/automations/knowledge_sync.py")
    result.append({"path": str(launch), "sha256": digest(launch),
                   "content": plistlib.dumps(data).decode(), "reason": "Preserve active knowledge sync using central implementation"})
    return [row for row in result if Path(row["path"]).read_text() != row["content"]]


def apply_consumers(plan: dict[str, Any], backup: Path) -> list[str]:
    """Apply only reviewed consumer edits after every original is protected.

    launchd refresh is left explicit: unload the obsolete updater, bootout/bootstrap
    the changed sync plist and inspect its current program. This function never
    starts an automation or sends documents as a side effect.
    """
    saved = load(backup / "manifest.json")
    if saved != plan:
        raise ValueError("Consumer plan does not match protected inventory")
    for row in plan["consumer_edits"]:
        path = Path(row["path"])
        copy = backup / "files" / path.relative_to("/")
        if digest(path) != row["sha256"] or digest(copy) != row["sha256"]:
            raise ValueError(f"Consumer changed after protection: {path}")
    changed = []
    for row in plan["consumer_edits"]:
        path = Path(row["path"])
        if digest(path) != row["sha256"]:
            raise ValueError(f"Concurrent consumer edit: {path}")
        changed.append(str(path))
        record_intent(backup, "consumer-edits.json", changed)
        atomic_write(path, row["content"].encode(), mode=stat.S_IMODE(path.stat().st_mode),
                     expected_sha256=row["sha256"],
                     quarantine=backup / "quarantine/consumers" / path.relative_to("/"))
    return changed


def manifest() -> dict[str, Any]:
    """Return exact file hashes and Git owners for review before any removal."""
    rows: dict[str, dict[str, Any]] = {}
    for root, reason in candidate_roots():
        paths = [root] if root.is_file() or root.is_symlink() else sorted(root.rglob("*"))
        for path in paths:
            if path.is_dir() and not path.is_symlink():
                continue
            if not (path.is_file() or path.is_symlink()):
                raise ValueError(f"Unsupported file kind: {path}")
            rows[str(path)] = {"path": str(path), "sha256": digest(path),
                               "mode": stat.S_IMODE(path.lstat().st_mode),
                               "symlink": path.is_symlink(), "reason": reason}
    projects = json.loads((SOURCE / "profiles/projects.json").read_text())["projects"]
    owners = [Path(p["root"]) for p in projects if p["management"] == "native"] + [HOME / ".codex"]
    git_rows = []
    for root in owners:
        git_rows.append({"root": str(root), "git_dir": git(root, "rev-parse", "--absolute-git-dir"),
                         "head": git(root, "rev-parse", "HEAD"),
                         "branch": git(root, "symbolic-ref", "--short", "HEAD"),
                         "refs": git(root, "show-ref"),
                         "index": git(root, "rev-parse", "--path-format=absolute", "--git-path", "index")})
    return {"schema_version": 1, "source": str(SOURCE), "files": list(rows.values()),
            "git": git_rows, "preserved": [str(HOME / ".codex/constellation/state"),
            str(HOME / ".codex/knowledge-sync.json"), str(HOME / ".codex/progress-journal.json")],
            "required_checks": list(REQUIRED_CHECKS), "consumer_edits": consumer_edits(),
            "pending_consumers": ["Installer replaces all native entries before retirement",
                "Knowledge sync LaunchAgent must use central automation",
                "OmarOS notes monitor and Claude entry must use central CLI guard-status/hooks",
                "Remove obsolete global plugin registry entry through native installer"]}


def load(path: Path) -> dict[str, Any]:
    """Read a versioned JSON object."""
    value = json.loads(path.read_text())
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ValueError("Unsupported migration record")
    return value


def verify_files(plan: dict[str, Any]) -> None:
    """Reject drift or path substitution before protection and retirement."""
    permitted = {str(p): p for p, _ in candidate_roots()}
    for row in plan["files"]:
        path = Path(row["path"])
        if not path.is_absolute() or not any(path == p or path.is_relative_to(p) for p in permitted.values()):
            raise ValueError(f"Path outside explicit retirement scope: {path}")
        if path.is_symlink() != row["symlink"] or digest(path) != row["sha256"]:
            raise ValueError(f"File changed after migration plan: {path}")
        if stat.S_IMODE(path.lstat().st_mode) != row["mode"]:
            raise ValueError(f"Mode changed after migration plan: {path}")


def protect(plan: dict[str, Any], backup: Path) -> None:
    """Save exact local bytes, indexes, refs and old source Git history privately.

    Args:
        plan: Reviewed inventory from ``manifest``.
        backup: New absolute directory outside every participating repository.

    Raises:
        ValueError: Scope drift, reused backup, or unsafe backup destination.
    """
    backup = backup.absolute()
    if backup.exists() or any(backup.is_relative_to(Path(row["root"])) for row in plan["git"]):
        raise ValueError("Backup must be new and outside all participating repositories")
    if backup.resolve() != backup:
        raise ValueError("Backup must not traverse symlinks")
    verify_files(plan)
    backup.mkdir(parents=True, mode=0o700)
    os.chmod(backup, 0o700)
    for row in plan["files"]:
        path = Path(row["path"])
        target = backup / "files" / path.relative_to("/")
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        shutil.copy2(path, target, follow_symlinks=False)
        if digest(target) != row["sha256"]:
            raise ValueError(f"Backup verification failed: {path}")
    for row in plan["consumer_edits"]:
        path = Path(row["path"])
        if digest(path) != row["sha256"]:
            raise ValueError(f"Consumer changed after plan: {path}")
        target = backup / "files" / path.relative_to("/")
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        shutil.copy2(path, target, follow_symlinks=False)
        if digest(target) != row["sha256"]:
            raise ValueError("Consumer backup verification failed")
    for index, owner in enumerate(plan["git"]):
        folder = backup / "git" / str(index)
        folder.mkdir(parents=True, mode=0o700)
        path = Path(owner["index"])
        if path.exists():
            shutil.copy2(path, folder / "index")
            owner = {**owner, "index_sha256": digest(path)}
        (folder / "facts.json").write_text(json.dumps(owner, indent=2) + "\n")
        # A bundle keeps reachable Git history; source .git additionally keeps
        # reflogs, unreferenced objects and original local operational state.
        if Path(owner["root"]) == HOME / ".codex":
            subprocess.run(["git", "-C", owner["root"], "bundle", "create", str(folder / "history.bundle"), "--all"],
                           capture_output=True, check=True)
    old_git = HOME / ".codex/.git"
    if old_git.is_dir():
        shutil.copytree(old_git, backup / "source-git", symlinks=True)
    (backup / "manifest.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
    os.chmod(backup / "manifest.json", 0o600)


def retire(plan: dict[str, Any], backup: Path, evidence: dict[str, Any]) -> list[str]:
    """Remove exactly protected files only after replacement evidence is complete.

    The caller must stop the obsolete updater and repoint active consumers first.
    This operation never removes private operational state or the original .git;
    source checkout retirement is a separate final coordinator action after Git
    publication and exact remote SHA verification.
    """
    saved = load(backup / "manifest.json")
    if saved != plan or any(evidence.get(name) is not True for name in REQUIRED_CHECKS):
        raise ValueError("Backup or replacement evidence is incomplete")
    if evidence.get("consumers_repointed") is not True:
        raise ValueError("Active consumers have not been repointed")
    verify_files(plan)
    for row in plan["files"]:
        copy = backup / "files" / Path(row["path"]).relative_to("/")
        if digest(copy) != row["sha256"]:
            raise ValueError("Protected bytes no longer match")
    removed = []
    for row in plan["files"]:
        path = Path(row["path"])
        # Check again immediately before each mutation; a failure retains a
        # durable removal journal and every backup, allowing bounded recovery.
        if digest(path) != row["sha256"]:
            raise ValueError(f"Concurrent edit during retirement: {path}")
        removed.append(str(path))
        record_intent(backup, "removed.json", removed)
        _quarantine(path, backup / "quarantine/retired" / path.relative_to("/"), row["sha256"])
    return removed



def restore(backup: Path) -> list[str]:
    """Restore retired/rewired originals without overwriting subsequent edits.

    Clean versioned files are recovered from their recorded Git commit when
    available. Dirty/untracked bytes come from the verified local backup. The
    original indexes remain untouched: restoration never stages or resets work.
    """
    plan = load(backup / "manifest.json")
    deleted = json.loads((backup / "removed.json").read_text()) if (backup / "removed.json").exists() else []
    edited = json.loads((backup / "consumer-edits.json").read_text()) if (backup / "consumer-edits.json").exists() else []
    files = {row["path"]: row for row in plan["files"]}
    changes = {row["path"]: row for row in plan["consumer_edits"]}
    todo = []
    for name in dict.fromkeys(deleted + edited):
        row = files.get(name) or changes[name]
        path = Path(name)
        saved = backup / "files" / path.relative_to("/")
        if digest(saved) != row["sha256"]:
            raise ValueError(f"Invalid recovery bytes: {path}")
        expected = None
        if path.exists() or path.is_symlink():
            current = digest(path)
            if current == row["sha256"]:
                continue
            if name not in edited or current != hashlib.sha256(changes[name]["content"].encode()).hexdigest():
                raise ValueError(f"Recovery would overwrite subsequent edits: {path}")
            expected = current
        todo.append((path, saved, expected))
    restored = []
    for path, saved, expected in todo:
        present = path.exists() or path.is_symlink()
        if present != (expected is not None) or (present and digest(path) != expected):
            raise ValueError(f"Concurrent edit during recovery: {path}")
        # Read Git bytes as data. Never use checkout/reset, which can mutate an
        # occupied real index or silently discard another user's staged version.
        recovered = None
        for owner in sorted(plan["git"], key=lambda r: len(r["root"]), reverse=True):
            root = Path(owner["root"])
            if path.is_relative_to(root):
                git_dir = Path(owner["git_dir"])
                if not git_dir.exists() and root == HOME / ".codex":
                    git_dir = backup / "source-git"
                result = subprocess.run(["git", "--no-replace-objects", "--git-dir", str(git_dir),
                    "show", owner["head"] + ":" + path.relative_to(root).as_posix()], capture_output=True)
                if result.returncode == 0 and hashlib.sha256(result.stdout).hexdigest() == digest(saved) and not saved.is_symlink():
                    recovered = result.stdout
                break
        path.parent.mkdir(parents=True, exist_ok=True)
        staging = backup / "restore-staging"
        staging.mkdir(mode=0o700, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix="original-", dir=staging)
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            if recovered is not None:
                temporary.write_bytes(recovered)
                temporary.chmod(stat.S_IMODE(saved.stat().st_mode))
            else:
                if saved.is_symlink():
                    temporary.unlink()
                shutil.copy2(saved, temporary, follow_symlinks=False)
            if digest(temporary) != digest(saved):
                raise ValueError(f"Restoration staging verification failed: {path}")
            if not temporary.is_symlink():
                with temporary.open("rb") as stream:
                    os.fsync(stream.fileno())
            _sync_directory(staging)
            record_intent(backup, "restoring.json", [str(path)])
            if expected is not None:
                _quarantine(path, backup / "quarantine/restored" / path.relative_to("/"), expected)
            _rename_exclusive(temporary, path)
            _sync_directory(path.parent)
            if digest(path) != digest(saved):
                raise ValueError(f"Restoration verification failed: {path}")
        finally:
            if temporary.exists() or temporary.is_symlink():
                temporary.unlink()
        restored.append(str(path))
        record_intent(backup, "restored.json", restored)
    return restored


def main() -> None:
    """Expose reviewable planning and explicit protect/retire operations."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("plan", "protect", "consumers", "retire", "restore"))
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--backup", type=Path)
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    if args.operation == "plan":
        print(json.dumps(manifest(), ensure_ascii=False, indent=2))
        return
    if args.operation == "restore":
        if args.backup is None:
            parser.error("--backup is required")
        print(json.dumps(restore(args.backup), indent=2))
        return
    if args.plan is None or args.backup is None:
        parser.error("--plan and --backup are required")
    plan = load(args.plan)
    if args.operation == "protect":
        protect(plan, args.backup)
    elif args.operation == "consumers":
        print(json.dumps(apply_consumers(plan, args.backup), indent=2))
    else:
        if args.evidence is None:
            parser.error("--evidence is required")
        print(json.dumps(retire(plan, args.backup, load(args.evidence)), indent=2))


if __name__ == "__main__":
    main()

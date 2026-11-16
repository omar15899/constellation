#!/usr/bin/env python3
"""Mirror every non-OmarOS project .claude/ on this Mac into External_Setups/.

Implementation of the external-setups-mirror skill. Single entrypoint.

Steps (see SKILL.md for the full spec):
  1. Discover qualifying .claude/ directories under $HOME (bounded `find`).
  2. For each, rsync -a --delete into 07_AI_and_Agents/External_Setups/<slug>/.claude/.
  3. Copy CLAUDE.md if present. Write per-setup README.md with metadata.
  4. Regenerate External_Setups/README.md (inventory).
  5. Run a secret-pattern grep across the mirror. Report, do not block.

Idempotent. Never commits. Preserves symlinks (rsync -a).

Flags:
  --dry-run     Print what would be done; do not touch the filesystem.
  --only SLUG   Mirror only the named project (still regenerates index after).
  --prune       Delete snapshot subfolders whose source no longer exists.
  --quiet       Suppress per-project progress lines.

Exit codes:
  0  success
  2  bad CLI
  3  discovery failed
  4  rsync failed on one or more projects (partial success possible)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

VAULT_ROOT = Path(os.environ.get("OMAROS_ROOT", Path("/Users/omarkhalil/OmarOS")))
DEST_ROOT = VAULT_ROOT / "07_AI_and_Agents" / "External_Setups"
OMAROS_CLAUDE = (VAULT_ROOT / ".claude").resolve()
HOME = Path.home()
USER_CLAUDE = (HOME / ".claude").resolve()

EXCLUDE_PATH_GLOBS = [
    "*/node_modules/*",
    "*/.git/*",
    "*/.venv/*",
    "*/venv/*",
    "*/Library/*",
    "*/.cache/*",
    "*/site-packages/*",
]

SECRET_PATTERN = (
    r"api[_-]?key[\"':=]\s*[\"'][A-Za-z0-9_\-]{15,}"
    r"|bearer [A-Za-z0-9_\-\.]{20,}"
    r"|sk-[A-Za-z0-9]{20,}"
    r"|ghp_[A-Za-z0-9]{30,}"
    r"|xox[bpos]-[A-Za-z0-9\-]{20,}"
    r"|AKIA[0-9A-Z]{16}"
)

# Explicit slug overrides, keyed on absolute source path. These exist because the
# automated camelCase/non-alnum slug rule doesn't always produce the most
# meaningful name — e.g. `programming/` is too generic (it's the Imperial MSc
# programming umbrella), and `solver/` is the on-disk name of the project whose
# canonical upstream name is SweepLab. Manual overrides win; anything else is
# derived deterministically from the basename by `slugify()`.
SLUG_OVERRIDES: dict[str, str] = {
    "/Users/omarkhalil/Desktop/Universidad/ImperialCollege/Project/programming": "programming_imperial",
    "/Users/omarkhalil/Desktop/Universidad/ImperialCollege/Project/programming/solver": "sweeplab",
}


def _now_iso_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def _today_iso() -> str:
    return dt.date.today().isoformat()


def slugify(name: str) -> str:
    # Insert underscore at camelCase boundaries so "KarimSpecificCase" becomes
    # "Karim_Specific_Case" before the lowercase+collapse step.
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name)
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_") or "unnamed"


def discover() -> list[Path]:
    """Run the bounded `find` and post-filter to project-root .claude/ only."""
    cmd = ["find", str(HOME), "-type", "d", "-name", ".claude"]
    for g in EXCLUDE_PATH_GLOBS:
        cmd += ["-not", "-path", g]
    cmd += ["-not", "-path", f"{HOME}/.claude"]
    cmd += ["-not", "-path", f"{HOME}/.claude/*"]
    cmd += ["-not", "-path", f"{VAULT_ROOT}/.claude"]
    cmd += ["-not", "-path", f"{VAULT_ROOT}/.claude/*"]
    # Exclude the destination itself — the mirrored snapshots contain nested
    # .claude/ dirs by design, but re-discovering them would create infinite
    # recursion of snapshot-of-snapshot copies.
    cmd += ["-not", "-path", f"{DEST_ROOT}"]
    cmd += ["-not", "-path", f"{DEST_ROOT}/*"]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 and not result.stdout:
        sys.stderr.write(f"find failed: {result.stderr}\n")
        sys.exit(3)

    paths: list[Path] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        p = Path(line).resolve()
        if p == OMAROS_CLAUDE or p == USER_CLAUDE:
            continue
        # Post-filter: any .claude whose ancestor path contains another .claude is nested.
        # The outer rsync already captures it; snapshotting it separately double-counts.
        ancestors = p.parent.parts
        if ".claude" in ancestors:
            continue
        paths.append(p)
    return sorted(set(paths))


def _resolve_slug(project_root: Path, used: set[str]) -> str:
    # Manual overrides win — see SLUG_OVERRIDES note at the top of the file.
    override = SLUG_OVERRIDES.get(str(project_root))
    if override:
        return override
    base = slugify(project_root.name)
    if base not in used:
        return base
    parent = slugify(project_root.parent.name)
    combined = f"{parent}_{base}"
    n = 2
    while combined in used:
        combined = f"{parent}_{base}_{n}"
        n += 1
    return combined


def _claude_layout_summary(claude_dir: Path, limit: int = 60) -> str:
    """Top-two-level directory listing of the mirrored .claude/, sorted, truncated."""
    entries = []
    for p in sorted(claude_dir.rglob("*")):
        if len(entries) >= limit:
            break
        try:
            rel = p.relative_to(claude_dir)
        except ValueError:
            continue
        if len(rel.parts) > 2:
            continue
        entries.append(str(rel))
    return "\n".join(entries)


def _per_setup_readme(slug: str, source: Path, dest: Path, has_claude_md: bool,
                     snapshot_at: str) -> str:
    layout = _claude_layout_summary(dest / ".claude")
    return f"""---
title: "{slug} — external AI setup snapshot"
note_type: external_ai_snapshot
domain: 07_AI_and_Agents
source_path: "{source}"
snapshot_at: {snapshot_at}
has_claude_md: {str(has_claude_md).lower()}
tags: [ai_setup, external_project, snapshot]
author: Omar
ai_generated: true
ai_reviewed: false
created: {_today_iso()}
updated: {_today_iso()}
---

# {slug} — external AI setup snapshot

Verbatim mirror of `{source}/.claude/` as of {snapshot_at}. Reference-only — not an active harness. Do NOT `cd` into the nested `.claude/` and start Claude Code there.

## Source
- Origin path: `{source}`
- Snapshot taken: {snapshot_at}
- CLAUDE.md captured: {"yes" if has_claude_md else "no"}

## Top-level `.claude/` contents
```
{layout}
```

## How this snapshot is maintained
Produced by the `external-setups-mirror` skill (run `/refresh-external-setups` or `uv run /Users/omarkhalil/GitHub/Constellation/skills/omaros/external-setups-mirror/scripts/mirror.py`). Do not hand-edit — the next refresh will overwrite.
"""


def mirror_one(src_claude: Path, slug: str, snapshot_at: str, quiet: bool = False) -> dict:
    project_root = src_claude.parent
    dest_proj = DEST_ROOT / slug
    dest_claude = dest_proj / ".claude"
    dest_proj.mkdir(parents=True, exist_ok=True)

    rsync_cmd = ["rsync", "-a", "--delete",
                 f"{src_claude}/", f"{dest_claude}/"]
    r = subprocess.run(rsync_cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(f"rsync failed for {src_claude}: {r.stderr}\n")
        return {"slug": slug, "source": str(project_root), "ok": False,
                "error": r.stderr.strip()}

    claude_md = project_root / "CLAUDE.md"
    has_md = claude_md.exists() and claude_md.is_file()
    if has_md:
        shutil.copy2(claude_md, dest_proj / "CLAUDE.md")
    else:
        # If a previous snapshot had one and the source no longer does, remove it.
        orphan = dest_proj / "CLAUDE.md"
        if orphan.exists():
            orphan.unlink()

    (dest_proj / "README.md").write_text(
        _per_setup_readme(slug, project_root, dest_proj, has_md, snapshot_at),
        encoding="utf-8",
    )

    file_count = sum(1 for _ in dest_claude.rglob("*") if _.is_file())
    if not quiet:
        print(f"  mirrored {slug:<30} <- {project_root}  ({file_count} files)")

    return {
        "slug": slug,
        "source": str(project_root),
        "file_count": file_count,
        "has_claude_md": has_md,
        "ok": True,
    }


def prune_orphans(current_slugs: set[str], quiet: bool = False) -> list[str]:
    """Delete snapshot subdirs whose slug is no longer in the current discovery."""
    removed = []
    if not DEST_ROOT.exists():
        return removed
    for child in DEST_ROOT.iterdir():
        if not child.is_dir():
            continue
        if child.name in current_slugs:
            continue
        shutil.rmtree(child)
        removed.append(child.name)
        if not quiet:
            print(f"  pruned {child.name} (no longer on disk)")
    return removed


def mark_archived(current_slugs: set[str]) -> list[str]:
    """For snapshots whose source is gone, flag in their README rather than delete."""
    archived = []
    if not DEST_ROOT.exists():
        return archived
    for child in DEST_ROOT.iterdir():
        if not child.is_dir() or child.name in current_slugs:
            continue
        readme = child / "README.md"
        if not readme.exists():
            continue
        text = readme.read_text(encoding="utf-8")
        if "status: archived" in text:
            archived.append(child.name)
            continue
        new = text.replace(
            "note_type: external_ai_snapshot",
            "note_type: external_ai_snapshot\nstatus: archived",
        )
        if new != text:
            readme.write_text(new, encoding="utf-8")
        archived.append(child.name)
    return archived


def regenerate_index(results: list[dict], archived: list[str], snapshot_at: str) -> Path:
    lines = [
        "---",
        'title: "External AI setups — reference snapshots"',
        "note_type: external_ai_setups_index",
        "domain: 07_AI_and_Agents",
        f"snapshot_at: {snapshot_at}",
        "tags: [ai_setup, external_project, snapshots, index]",
        "author: Omar",
        "ai_generated: true",
        "ai_reviewed: false",
        f"created: {_today_iso()}",
        f"updated: {_today_iso()}",
        "---",
        "",
        "# External AI setups — reference snapshots",
        "",
        "Verbatim mirrors of every non-OmarOS project on this Mac that carries a `.claude/` directory. Each subfolder is a faithful copy of the project's AI harness at snapshot time — agents, commands, hooks, skills, settings, CLAUDE.md — so OmarOS always has an up-to-date reference of how each external project structures its AI layer.",
        "",
        "**Reference-only.** Do NOT `cd` into a nested `.claude/` and start Claude Code there — you would load a stale copy of that project's harness.",
        "",
        "## Inventory",
        "",
        "| slug | source | files in `.claude/` | has CLAUDE.md | status |",
        "|------|--------|---------------------|----------------|--------|",
    ]
    for r in sorted(results, key=lambda x: x["slug"]):
        lines.append(
            f"| `{r['slug']}` | `{r['source']}` | {r['file_count']} | "
            f"{'yes' if r['has_claude_md'] else 'no'} | live |"
        )
    for slug in sorted(archived):
        lines.append(
            f"| `{slug}` | _source disappeared_ | — | — | archived |"
        )
    lines += [
        "",
        f"Last refreshed: {snapshot_at}",
        "",
        "## Excluded from discovery",
        "",
        "The bounded `find` skips these trees (they are either irrelevant build/runtime artefacts, heavy macOS user-config, git internals, or configs that are not project-level):",
        "",
        "- `*/node_modules/*`, `*/site-packages/*`, `*/.venv/*`, `*/venv/*`",
        "- `*/.git/*`, `*/.cache/*`, `*/Library/*`",
        "- `~/.claude/` (Claude Code user-level config, not a project `.claude/`)",
        "- OmarOS's own `.claude/` (active harness, not a reference)",
        "",
        "Nested `.claude/` inside another `.claude/` is also filtered out — the outer rsync already captures it.",
        "",
        "## Refresh",
        "",
        "- NL: \"refresh external setups\", \"actualiza los external setups\", \"resnap\".",
        "- Command: `/refresh-external-setups`.",
        "- Direct: `uv run /Users/omarkhalil/GitHub/Constellation/skills/omaros/external-setups-mirror/scripts/mirror.py`.",
        "",
        "Skill spec: `/Users/omarkhalil/GitHub/Constellation/skills/omaros/external-setups-mirror/SKILL.md`.",
        "",
    ]
    out = DEST_ROOT / "README.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def security_scan() -> list[str]:
    if not DEST_ROOT.exists():
        return []
    cmd = ["grep", "-rIE", SECRET_PATTERN, str(DEST_ROOT)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    hits = []
    for line in r.stdout.splitlines():
        if not line or "Binary file" in line:
            continue
        # Filter doc-comment mentions that are clearly not a live secret.
        if "ANTHROPIC_API_KEY" in line and ("needed" in line or "not required" in line):
            continue
        hits.append(line)
    return hits


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", metavar="SLUG")
    ap.add_argument("--prune", action="store_true",
                    help="Delete snapshots whose source no longer exists")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    DEST_ROOT.mkdir(parents=True, exist_ok=True)
    snapshot_at = _now_iso_utc()

    sources = discover()
    if not args.quiet:
        print(f"Discovered {len(sources)} project .claude/ directories")

    used_slugs: set[str] = set()
    planned: list[tuple[Path, str]] = []
    for src in sources:
        slug = _resolve_slug(src.parent, used_slugs)
        used_slugs.add(slug)
        if args.only and slug != args.only:
            continue
        planned.append((src, slug))

    if args.dry_run:
        print(json.dumps({
            "dry_run": True,
            "would_mirror": [
                {"slug": s, "source": str(p.parent)} for p, s in planned
            ],
        }, indent=2))
        return

    results: list[dict] = []
    failures = 0
    for src, slug in planned:
        r = mirror_one(src, slug, snapshot_at, quiet=args.quiet)
        results.append(r)
        if not r.get("ok"):
            failures += 1

    # Orphan handling
    if args.prune:
        removed = prune_orphans(set(used_slugs), quiet=args.quiet)
        archived: list[str] = []
    else:
        removed = []
        archived = mark_archived(set(used_slugs))

    index_path = regenerate_index(
        [r for r in results if r.get("ok")], archived, snapshot_at
    )
    findings = security_scan()

    payload = {
        "action": "external_setups_mirror",
        "snapshot_at": snapshot_at,
        "discovered": len(sources),
        "mirrored": sum(1 for r in results if r.get("ok")),
        "failed": failures,
        "pruned": removed,
        "archived": archived,
        "projects": results,
        "security_findings": findings,
        "index_path": str(index_path.relative_to(VAULT_ROOT)),
    }
    print(json.dumps(payload, indent=2))
    if failures:
        sys.exit(4)


if __name__ == "__main__":
    main()

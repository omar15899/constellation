#!/usr/bin/env python3
"""Tests for the Claude -> Codex projection.

Runs standalone (`python3 .claude/tests/test_codex_sync.py`) or under pytest.
No third-party dependencies, matching the rest of the constellation hub.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import codex_sync as cs  # noqa: E402

ROOT = Path("/Users/omarkhalil/GitHub")


# --- semantic mapping -------------------------------------------------------


def test_deny_globs_translate_faithfully() -> None:
    """Token-trailing wildcards are exact; mid-token ones degrade to `prompt`."""
    cases = {
        "Bash(rm *)": (["rm"], "forbidden"),
        "Bash(curl *)": (["curl"], "forbidden"),
        "Bash(git reset --hard*)": (["git", "reset", "--hard"], "forbidden"),
        "Bash(git push -f*)": (["git", "push", "-f"], "forbidden"),
        "Bash(git filter-branch*)": (["git", "filter-branch"], "forbidden"),
        "Bash(git clean *-fd*)": (["git", "clean"], "prompt"),
    }
    for entry, (tokens, decision) in cases.items():
        rule = cs.deny_to_rule(entry)
        assert rule is not None, entry
        assert f'decision = "{decision}"' in rule, entry
        for t in tokens:
            assert f'"{t}"' in rule, (entry, t)
    # A mid-token wildcard must never widen into a forbidden `git` blanket.
    assert '["git"]' not in (cs.deny_to_rule("Bash(git filter-branch*)") or "")
    assert cs.deny_to_rule("Read(*)") is None


def test_matcher_split_preserves_argument_level_filtering() -> None:
    tool, glob = cs.split_matcher("Bash(git commit*)")
    assert glob == "git commit*"
    assert "Bash" in tool
    tool, glob = cs.split_matcher("Write|Edit|MultiEdit")
    assert glob is None
    assert "apply_patch" in tool  # Codex's own edit tool must be covered
    assert cs.split_matcher("*") == (None, None)
    assert cs.split_matcher(None) == (None, None)


def test_effort_and_sandbox_are_derived_not_invented() -> None:
    assert cs.effort_for({"model": "claude-opus-4-7"}) == "xhigh"
    assert cs.effort_for({"model": "claude-sonnet-4-6"}) == "high"
    assert cs.effort_for({"effort": "medium", "model": "claude-opus-4-7"}) == "medium"
    assert cs.effort_for({}) is None
    # No write tool granted => read-only sandbox.
    assert cs.sandbox_for({"tools": "Read, Glob, Grep, Bash"}) == "read-only"
    assert cs.sandbox_for({"tools": "Read, Write, Edit"}) is None
    assert cs.sandbox_for({}) is None


def test_frontmatter_parser_handles_the_real_shapes() -> None:
    meta, body = cs.split_frontmatter("---\nname: x\ndescription: a: b\n---\n\n# Body\n")
    assert meta["name"] == "x"
    assert meta["description"] == "a: b"
    assert body.strip() == "# Body"
    assert cs.split_frontmatter("no frontmatter")[0] == {}


def test_toml_multiline_survives_hostile_markdown() -> None:
    for raw in ['he said """hi"""', "back\\slash", 'ends with "', "# md\n\n| a | b |"]:
        parsed = tomllib.loads(f"x = {cs.toml_multiline(raw)}")
        assert parsed["x"].strip() == raw.strip(), raw


# --- the shim ---------------------------------------------------------------


def _shim_call(payload: dict, glob: str | None, exit_code: str = "0") -> tuple[int, str]:
    tmp = Path(tempfile.mkdtemp())
    shim = tmp / "hook_shim.py"
    shim.write_text(cs.HOOK_SHIM, encoding="utf-8")
    inner = tmp / "inner.py"
    inner.write_text(
        "import sys, os, json\n"
        "p = sys.stdin.read()\n"
        "d = json.loads(p)\n"
        "print('RAN', os.environ.get('CLAUDE_PROJECT_DIR'))\n"
        "print('CMD', (d.get('tool_input') or {}).get('command', ''))\n"
        "print('EVENT', d.get('event', ''))\n"
        "print('RESULT', json.dumps(d.get('tool_result', {}), sort_keys=True))\n"
        "sys.exit(int(os.environ.get('EXIT', '0')))\n",
        encoding="utf-8",
    )
    cmd = ["python3", str(shim), "--project-dir", "/tmp/proj"]
    if glob:
        cmd += ["--command-glob", glob]
    cmd += ["--", "python3", str(inner)]
    done = subprocess.run(
        cmd, input=json.dumps(payload), text=True, capture_output=True,
        env=dict(os.environ, EXIT=exit_code),
    )
    return done.returncode, done.stdout.strip()


def test_shim_restores_claude_matcher_semantics() -> None:
    commit = {"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}}
    status = {"tool_name": "Bash", "tool_input": {"command": "git status"}}

    rc, out = _shim_call(commit, "git commit*")
    assert rc == 0 and "CMD git commit -m x" in out
    assert "RAN /tmp/proj" in out, "CLAUDE_PROJECT_DIR must be exported"

    rc, out = _shim_call(status, "git commit*")
    assert rc == 0 and out == "", "a non-matching command must skip silently"

    rc, out = _shim_call(commit, None)
    assert rc == 0 and "RAN" in out, "no glob means always run"

    rc, _ = _shim_call(commit, "git commit*", exit_code="2")
    assert rc == 2, "exit 2 must propagate so Codex can still block the tool call"

    rc, _ = _shim_call({"hook_event_name": "SessionStart"}, "git commit*")
    assert rc == 0, "a payload without tool_input must not crash the hook runner"


def test_shim_normalises_codex_field_names() -> None:
    """The hooks read `event`/`tool_result`; Codex sends the other spelling.

    Without normalisation `HookPayload.from_stdin` fills them with empty
    defaults and every gate becomes a silent no-op instead of a loud failure.
    """
    codex_payload = {
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "git commit -m x"},
        "tool_response": {"exit_code": 0, "stdout": "ok"},
    }
    rc, out = _shim_call(codex_payload, None)
    assert rc == 0
    assert "EVENT PostToolUse" in out, "hook_event_name must be surfaced as `event`"
    assert '"exit_code": 0' in out, "tool_response must be surfaced as `tool_result`"

    # A payload already in Claude's dialect must pass through untouched.
    claude_payload = dict(codex_payload, event="PreToolUse", tool_result={"exit_code": 7})
    rc, out = _shim_call(claude_payload, None)
    assert "EVENT PreToolUse" in out and '"exit_code": 7' in out


# --- the projected tree -----------------------------------------------------


def test_every_generated_agent_toml_is_valid() -> None:
    checked = 0
    for toml_path in ROOT.glob("*/.codex/agents/*.toml"):
        parsed = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        for key in ("name", "description", "developer_instructions"):
            assert key in parsed, f"{toml_path}: missing {key}"
        assert parsed["developer_instructions"].strip(), f"{toml_path}: empty instructions"
        checked += 1
    assert checked > 100, f"expected the full constellation, saw {checked} agents"


def test_every_projected_skill_declares_itself() -> None:
    for skill in ROOT.glob("*/.codex/skills/*/SKILL.md"):
        meta, _ = cs.split_frontmatter(skill.read_text(encoding="utf-8", errors="replace"))
        assert meta.get("name"), f"{skill}: no name — invisible to both agents"
        assert meta.get("description"), f"{skill}: no description"


def test_skill_symlinks_point_at_the_canonical_claude_plane() -> None:
    links = [p for p in ROOT.glob("*/.codex/skills/*") if p.is_symlink()]
    assert links, "skills should be shared by symlink, not copied"
    for link in links:
        target = os.readlink(link)
        assert target.startswith("../../.claude/skills/"), f"{link} -> {target}"
        assert link.resolve().is_dir(), f"{link} is a broken symlink"


def test_no_agents_md_exceeds_the_codex_size_cap() -> None:
    for md in list(ROOT.glob("*/AGENTS.md")) + [ROOT / "AGENTS.md"]:
        if md.is_file():
            assert md.stat().st_size <= 32 * 1024, f"{md} exceeds project_doc_max_bytes"


def test_projection_is_idempotent() -> None:
    """A --check straight after a sync must report zero drift."""
    done = subprocess.run(
        [sys.executable, str(ROOT / ".claude/scripts/codex_sync.py"), "--all", "--check"],
        capture_output=True, text=True,
    )
    assert done.returncode == 0, f"projection drifted:\n{done.stdout}"


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print(f"PASS {name}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {name}: {exc}")
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)

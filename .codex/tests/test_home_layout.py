"""Check source ownership and publication boundaries without reading device state."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / ".codex"


class HomeLayoutTests(unittest.TestCase):
    def test_private_device_namespaces_are_ignored_by_default(self) -> None:
        """Exercise Git's actual ignore rules against synthetic publication candidates."""
        private = {
            "auth.json",
            "config.toml",
            "config.toml.pre-codex-sync",
            "hooks.json",
            "history.jsonl",
            "session_index.jsonl",
            ".codex-global-state.json",
            "state_5.sqlite",
            "state_5.sqlite-wal",
            "logs_2.sqlite-shm",
            "progress-journal.json",
            "learning/PROFILE.md",
            "sessions/2026/11/02/rollout-example.jsonl",
            "logs/daemon.log",
            "backups/2026-11-02/config.toml",
            "constellation/receipt.json",
            "constellation/state/update.json",
            "plugins/cache/example/plugin/1.0/skills/example/SKILL.md",
            "skills/.system/example/SKILL.md",
            "agents/constellation-coder.toml",
            "hooks/example.py",
            "rules/default.rules",
            "memories_v2/rollout_summaries/example.md",
            "attachments/example.pdf",
            "visualizations/2026/11/02/example.html",
            "new-provider-state/nested/payload.json",
            ".new-provider-state/nested/payload.json",
            ".claude/run/example.jsonl",
            ".github/workflows/example.yml",
            ".github/other-private-state.json",
            ".codex/ecosystem/__pycache__/core.cpython-313.pyc",
            ".codex/ecosystem/.pytest_cache/example",
        }
        maintained = {
            ".gitignore",
            "AGENTS.md",
            "README.md",
            "REVIEW.md",
            ".github/pull_request_template.md",
            ".codex/AGENTS.md",
            ".codex/repositories.json",
            ".codex/ecosystem/core.py",
            ".codex/ecosystem/agents/coder.toml",
            ".codex/skills/coding/SKILL.md",
            ".codex/tests/test_home_layout.py",
        }
        with tempfile.TemporaryDirectory(prefix="constellation-home-ignore-") as name:
            fixture = Path(name)
            subprocess.run(["git", "init", "-q", str(fixture)], check=True)
            (fixture / ".gitignore").write_bytes((ROOT / ".gitignore").read_bytes())
            for relative in (private | maintained) - {".gitignore"}:
                target = fixture / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("synthetic fixture\n", encoding="utf-8")
            result = subprocess.run(
                ["git", "-c", f"core.excludesFile={os.devnull}", "check-ignore",
                 "--no-index", "--stdin"],
                cwd=fixture,
                input="".join(f"{relative}\n" for relative in sorted(private | maintained)),
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(set(result.stdout.splitlines()), private)

    def test_source_has_its_own_git_owner_and_versioned_manifest(self) -> None:
        owner = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], cwd=ROOT, text=True,
        ).strip()
        self.assertEqual(Path(owner).resolve(), ROOT)
        manifest = ".codex/ecosystem/manifests/codex-plugin.json"
        entry = subprocess.check_output(
            ["git", "ls-tree", "HEAD", "--", manifest], cwd=ROOT, text=True,
        )
        self.assertTrue(entry.strip(), "The source identity manifest must belong to HEAD")
        self.assertTrue((SOURCE / "ecosystem/build.py").is_file())
        self.assertTrue((SOURCE / "ecosystem/cli.py").is_file())
        self.assertTrue((SOURCE / "skills/coding/SKILL.md").is_file())

    def test_source_registry_does_not_claim_sibling_workspaces(self) -> None:
        registry = json.loads((SOURCE / "repositories.json").read_text(encoding="utf-8"))
        self.assertEqual(registry, {
            "schema_version": 1,
            "repositories": [{"path": ".", "management": "native"}],
        })


if __name__ == "__main__":
    unittest.main()

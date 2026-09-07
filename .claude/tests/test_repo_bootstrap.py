#!/usr/bin/env python3
"""Integration tests for bootstrap planning, safe creation and draft CI failures."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

HUB = Path(__file__).resolve().parents[1]


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                          text=True, check=True, timeout=10)


def snapshot(root: Path) -> dict[str, tuple]:
    """Observe fixture work without following links or reading Git internals."""
    result = {}
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if ".git" in relative.parts:
            continue
        mode = path.lstat()
        if path.is_symlink():
            result[str(relative)] = ("link", os.readlink(path), mode.st_mtime_ns)
        elif path.is_file():
            result[str(relative)] = ("file", path.read_bytes(), mode.st_mtime_ns)
        else:
            result[str(relative)] = ("directory", mode.st_mtime_ns)
    return result


def actions(output: str) -> list[str]:
    return [line.strip() for line in output.splitlines()
            if line.startswith(("  mkdir ", "  create "))]


class BootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="bootstrap fixture '")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.hub = self.root / "control/.claude"
        (self.hub / "scripts").mkdir(parents=True)
        (self.hub / "templates").mkdir()
        (self.hub / "registry").mkdir()
        self.script = self.hub / "scripts/bootstrap_repo.sh"
        shutil.copyfile(HUB / "scripts/bootstrap_repo.sh", self.script)
        for name in ("CLAUDE.md.template", "importlinter.template", "lint.yml.template"):
            shutil.copyfile(HUB / "templates" / name, self.hub / "templates" / name)
        (self.hub / "registry/repos.yaml").write_text("version: 1\nrepos: []\n")
        self.repo = self.new_repo("target repo")

    def new_repo(self, name: str) -> Path:
        repo = self.root / name
        repo.mkdir()
        git(repo, "init", "--quiet")
        return repo

    def run_bootstrap(self, *args: str, repo: Path | None = None,
                      env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["bash", str(self.script), str(repo or self.repo), *args],
                              capture_output=True, text=True, timeout=15, env=env)

    def assert_success(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_dry_run_is_read_only_and_apply_matches_exact_plan(self) -> None:
        before = snapshot(self.repo)
        dry = self.run_bootstrap()
        self.assert_success(dry)
        self.assertEqual(snapshot(self.repo), before)
        applied = self.run_bootstrap("--apply")
        self.assert_success(applied)
        self.assertEqual(actions(dry.stdout), actions(applied.stdout))
        observed = snapshot(self.repo)
        self.assertEqual({line.split(" ", 1)[1] for line in actions(dry.stdout)}, set(observed))
        self.assertNotIn(".importlinter", observed)
        self.assertNotIn(".github", observed)
        self.assertNotIn(".claude/settings.json", observed)
        self.assertNotIn(".claude/registry/peers.yaml", observed)

    def test_quantos_copies_each_advertised_template_and_snapshot(self) -> None:
        dry = self.run_bootstrap("--variant", "quantos")
        self.assert_success(dry)
        applied = self.run_bootstrap("--variant", "quantos", "--apply")
        self.assert_success(applied)
        self.assertEqual(actions(dry.stdout), actions(applied.stdout))
        self.assertEqual({line.split(" ", 1)[1] for line in actions(dry.stdout)},
                         set(snapshot(self.repo)))
        for destination, template in (
            ("CLAUDE.md", "CLAUDE.md.template"),
            (".importlinter", "importlinter.template"),
            (".github/workflows/lint.yml", "lint.yml.template"),
        ):
            self.assertEqual((self.repo / destination).read_bytes(),
                             (self.hub / "templates" / template).read_bytes())
        self.assertTrue((self.repo / ".claude/tests").is_dir())
        peers = (self.repo / ".claude/registry/peers.yaml.snapshot").read_text()
        self.assertEqual(peers.split("\n\n", 1)[1],
                         (self.hub / "registry/repos.yaml").read_text())
        self.assertIn("drafts", applied.stdout)

    def test_preserves_existing_files_and_local_peer_policy(self) -> None:
        paths = ("CLAUDE.md", ".importlinter", ".github/workflows/lint.yml",
                 ".claude/registry/peers.yaml", ".claude/agents/custom.md")
        originals = {}
        for name in paths:
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"User content: {name}\n")
            originals[name] = (path.read_bytes(), path.stat().st_mtime_ns)
        self.assert_success(self.run_bootstrap("--variant", "quantos", "--apply"))
        for name, original in originals.items():
            path = self.repo / name
            self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), original)
        self.assertTrue((self.repo / ".claude/registry/peers.yaml.snapshot").is_file())

    def test_second_apply_needs_no_sources_and_preserves_all_mtimes(self) -> None:
        repos = [(self.repo, "adjacent"), (self.new_repo("quantos"), "quantos")]
        for repo, variant in repos:
            self.assert_success(self.run_bootstrap("--variant", variant, "--apply", repo=repo))
        shutil.rmtree(self.hub / "templates")
        (self.hub / "registry/repos.yaml").unlink()
        for repo, variant in repos:
            with self.subTest(variant=variant):
                before = snapshot(repo)
                result = self.run_bootstrap("--variant", variant, "--apply", repo=repo)
                self.assert_success(result)
                self.assertEqual(actions(result.stdout), [])
                self.assertEqual(snapshot(repo), before)

    def test_all_missing_sources_refuse_before_any_destination_write(self) -> None:
        for name in ("templates/CLAUDE.md.template", "templates/importlinter.template",
                     "templates/lint.yml.template", "registry/repos.yaml"):
            with self.subTest(source=name):
                source = self.hub / name
                content = source.read_bytes()
                source.unlink()
                try:
                    for mode in ((), ("--apply",)):
                        before = snapshot(self.repo)
                        result = self.run_bootstrap("--variant", "quantos", *mode)
                        self.assertEqual(result.returncode, 2)
                        self.assertIn("required source", result.stderr)
                        self.assertEqual(snapshot(self.repo), before)
                finally:
                    source.write_bytes(content)

    def test_symlink_destinations_including_dangling_links_refuse_without_writes(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "keep").write_text("untouched\n")
        destinations = (".claude", ".claude/registry", ".github/workflows",
                        "CLAUDE.md", ".importlinter", ".claude/registry/peers.yaml.snapshot")
        for index, name in enumerate(destinations):
            with self.subTest(destination=name):
                repo = self.new_repo(f"symlink-{index}")
                target = repo / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.symlink_to(outside if index < 3 else outside / "missing")
                before, external_before = snapshot(repo), snapshot(outside)
                result = self.run_bootstrap("--variant", "quantos", "--apply", repo=repo)
                self.assertEqual(result.returncode, 2)
                self.assertIn("symlink destination", result.stderr)
                self.assertEqual(snapshot(repo), before)
                self.assertEqual(snapshot(outside), external_before)

    def test_destination_type_conflicts_refuse_before_writes(self) -> None:
        for index, (name, directory) in enumerate(
            ((".claude", False), (".github/workflows", False), ("CLAUDE.md", True))
        ):
            with self.subTest(destination=name):
                repo = self.new_repo(f"conflict-{index}")
                path = repo / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.mkdir() if directory else path.write_text("preserve")
                before = snapshot(repo)
                result = self.run_bootstrap("--variant", "quantos", "--apply", repo=repo)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(snapshot(repo), before)

    def test_only_actual_git_roots_are_accepted(self) -> None:
        child = self.repo / "subdirectory"
        child.mkdir()
        ordinary = self.root / "not-a-repo"
        ordinary.mkdir()
        bare = self.root / "bare"
        bare.mkdir()
        git(bare, "init", "--quiet", "--bare")
        for target in (child, ordinary, bare):
            with self.subTest(target=target):
                result = self.run_bootstrap("--apply", repo=target)
                self.assertEqual(result.returncode, 2)
                self.assertFalse((target / ".claude").exists())

    def test_ambient_git_directory_cannot_select_another_repository(self) -> None:
        ordinary = self.root / "ordinary"
        ordinary.mkdir()
        env = dict(os.environ, GIT_DIR=str(self.repo / ".git"), GIT_WORK_TREE=str(ordinary))
        result = self.run_bootstrap("--apply", repo=ordinary, env=env)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(snapshot(ordinary), {})

    def test_cannot_write_through_nested_git_root(self) -> None:
        nested = self.repo / ".claude"
        nested.mkdir()
        git(nested, "init", "--quiet")
        before = snapshot(self.repo)
        result = self.run_bootstrap("--apply")
        self.assertEqual(result.returncode, 2)
        self.assertIn("another Git root", result.stderr)
        self.assertEqual(snapshot(self.repo), before)

    def test_linked_worktree_root_is_accepted(self) -> None:
        git(self.repo, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
            "-c", "commit.gpgsign=false", "commit", "--quiet", "--allow-empty", "-m", "Fixture")
        worktree = self.root / "linked worktree"
        git(self.repo, "worktree", "add", "--quiet", "-b", "codex/bootstrap-fixture", str(worktree))
        self.assertTrue((worktree / ".git").is_file())
        original = snapshot(self.repo)
        self.assert_success(self.run_bootstrap("--apply", repo=worktree))
        self.assertTrue((worktree / "CLAUDE.md").is_file())
        self.assertEqual(snapshot(self.repo), original)

    def test_invalid_arguments_are_errors_without_writes(self) -> None:
        for args in (("--variant",), ("--variant", "unknown"), ("--typo",), ("extra-path",)):
            with self.subTest(args=args):
                before = snapshot(self.repo)
                result = self.run_bootstrap(*args)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(snapshot(self.repo), before)

    def test_ci_template_does_not_turn_failed_checks_green(self) -> None:
        stub_dir = self.root / "fake tools"
        stub_dir.mkdir()
        uv = stub_dir / "uv"
        uv.write_text("#!/bin/sh\nexit 23\n")
        uv.chmod(0o755)
        commands = [line.split("run:", 1)[1].strip() for line in
                    (self.hub / "templates/lint.yml.template").read_text().splitlines()
                    if line.strip().startswith("run:")]
        self.assertTrue(commands)
        env = dict(os.environ, PATH=str(stub_dir) + os.pathsep + os.environ.get("PATH", ""))
        for command in commands:
            with self.subTest(command=command):
                result = subprocess.run(["bash", "-c", command], env=env, capture_output=True,
                                        text=True, timeout=5)
                self.assertEqual(result.returncode, 23, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()

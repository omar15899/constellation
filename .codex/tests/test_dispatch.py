"""Dispatch plans are deterministic, bounded and cannot execute their packets."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import io
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE))
from ecosystem import cli
from ecosystem import build as builder
from ecosystem.runtime import dispatch
from ecosystem.runtime import workspace as ws
from ecosystem.runtime.workflow import review_engine
from test_workflow import install_test_bundle


class DispatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / "hub"
        self.root.mkdir()
        (self.root / ".codex").mkdir()
        self.registry = {"schema_version": 1, "repositories": [
            {"path": name, "management": "native"} for name in (".", "Provider", "Consumer")]}
        (self.root / ".codex/repositories.json").write_text(json.dumps(self.registry))
        self.agent_policy = {"schema_version": 1, "defaults": {"max_concurrent_threads_per_session": 8},
                             "repositories": {"Provider": {"max_concurrent_threads_per_session": 2}}}
        self.agent_path = self.root / ".codex/agent-policy.json"
        self.agent_path.write_text(json.dumps(self.agent_policy))
        self.review_policy = json.loads((MODULE / "ecosystem/runtime/review-policy.json").read_text())
        self.review_policy["modes"] = {
            "quick": {"reviewers": 1, "focus": {"correctness": 1}},
            "standard": {"reviewers": 3, "focus": {"correctness": 3}},
            "deep": {"reviewers": 5, "focus": {"correctness": 3, "security": 2}},
        }
        self.policy_path = self.root / ".codex/review-policy.json"
        self.policy_path.write_text(json.dumps(self.review_policy))
        (self.root / ".gitignore").write_text("Provider/\nConsumer/\n")
        self.remotes = []
        for name in (".", "Provider", "Consumer"):
            root = self.root / name
            root.mkdir(exist_ok=True)
            remote = self.base / ("hub.git" if name == "." else name + ".git")
            self.remotes.append(remote)
            subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
            subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
            for key, value in (("user.name", "Test"), ("user.email", "test@example.invalid"),
                               ("commit.gpgsign", "false"), ("core.hooksPath", str(root / ".git/hooks"))):
                ws.git(root, "config", key, value)
            (root / "AGENTS.md").write_text("Local repository instructions\n")
            (root / "README.md").write_text("A fixture\n")
            ws.git(root, "add", "--all")
            ws.git(root, "commit", "-m", "Seed fixture")
            ws.git(root, "remote", "add", "origin", str(remote))
            ws.git(root, "push", "-u", "origin", "main")
        self.workspace = ws.Workspace(self.root, "dispatch-test")
        self.engine = review_engine()

    def tearDown(self):
        self.temp.cleanup()

    def plan(self, paths=None, **extra):
        paths = paths if paths is not None else ["Provider/lib.py", "Consumer/lib.py"]
        self.workspace.plan({"requirements": ["The selected artifacts satisfy the contract"], "paths": paths, **extra})
        for name in paths:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                target.write_text("pass\n")

    def fingerprints(self):
        return {str(path.relative_to(self.base)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in self.base.rglob("*") if path.is_file()}

    def test_repeat_is_byte_identical_and_never_writes_or_contacts_remote(self):
        self.plan(depends_on={"Consumer": ["Provider"]})
        before = self.fingerprints()
        original_run = subprocess.run

        def readonly(command, *args, **kwargs):
            self.assertEqual(command[0], "git")
            self.assertNotIn(command[1], {"fetch", "push", "commit", "add", "merge", "reset", "checkout"})
            return original_run(command, *args, **kwargs)

        with patch.object(subprocess, "run", side_effect=readonly), \
                patch.object(ws.Workspace, "save", side_effect=AssertionError("workspace mutation")), \
                patch.object(ws.Workflow, "save", side_effect=AssertionError("workflow mutation")), \
                patch.object(ws.Workspace, "lock", side_effect=AssertionError("workspace lock creation")), \
                patch.object(ws.Workflow, "lock", side_effect=AssertionError("workflow lock creation")):
            first = json.dumps(self.workspace.dispatch(4), ensure_ascii=False)
            second = json.dumps(self.workspace.dispatch(4), ensure_ascii=False)
        self.assertEqual(first, second)
        self.assertEqual(self.fingerprints(), before)
        for remote in self.remotes:
            self.assertNotIn(str(remote), first)
        self.assertNotIn("checked_at", first)
        self.assertNotIn('"started"', first)
        result = json.loads(first)
        self.assertEqual(result["execution_state"], "not_evaluated")
        self.assertEqual(result["repositories"]["Provider"]["target"],
                         {"branch": "main", "remote": "origin", "ref": "refs/heads/main"})

    def test_dependencies_and_shared_capacity_limit_every_wave(self):
        self.plan(["Provider/.codex/tool.py", "Consumer/lib.py"], depends_on={"Consumer": ["Provider"]})
        result = self.workspace.dispatch(3)
        tasks = {task["id"]: task for task in result["tasks"]}
        self.assertIn("Provider::check", tasks["Consumer::implement"]["depends_on"])
        self.assertNotIn("Provider::integrate", tasks["Consumer::implement"]["depends_on"])
        reviews = {task["id"] for task in result["tasks"] if task["phase"].startswith("review-")}
        self.assertLessEqual(reviews, set(tasks["Provider::integrate"]["depends_on"]))
        self.assertLessEqual(reviews, set(tasks["Consumer::integrate"]["depends_on"]))
        self.assertIn("Provider::integrate", tasks["Consumer::integrate"]["depends_on"])
        done = set()
        for wave in result["waves"]:
            agents = [tasks[key] for key in wave if tasks[key]["executor"] == "agent"]
            self.assertLessEqual(len(agents), 3)
            self.assertLessEqual(sum(task["repository"] == "Provider" for task in agents), 2)
            self.assertLessEqual(sum(tasks[key]["executor"] == "coordinator" for key in wave), 1)
            for key in wave:
                self.assertLessEqual(set(tasks[key]["depends_on"]), done)
            done.update(wave)
        self.assertEqual(done, set(tasks))
        for task in tasks.values():
            if task["phase"] == "implement":
                self.assertEqual(task["write_paths"], result["repositories"][task["repository"]]["paths"])
            else:
                self.assertEqual(task["write_paths"], [])

    def test_policy_selects_full_scope_distinct_review_slots(self):
        self.plan(["guide.md", "Provider/lib.py", "Consumer/.codex/tool.py"])
        result = self.workspace.dispatch()
        self.assertEqual(result["capacity"], 8)
        for repo, expected in ((".", 1), ("Provider", 3), ("Consumer", 5)):
            tasks = [task for task in result["tasks"] if task["repository"] == repo and task["phase"].startswith("review-")]
            self.assertEqual(len(tasks), expected)
            for task in tasks:
                self.assertEqual(task["paths"], result["repositories"][repo]["paths"])
                self.assertEqual(task["depends_on"], [f"{repo}::check"])
                self.assertIn("actual native agent identity", task["handoff"])
            if repo == "Consumer":
                self.assertEqual(sum("correctness" in task["focus"] for task in tasks), 3)
                self.assertEqual(sum("security" in task["focus"] for task in tasks), 2)

    def test_capacity_validation_and_policy_cannot_be_increased_by_caller(self):
        self.plan()
        for value in (0, -1, 65, True, 1.5, "2"):
            with self.subTest(capacity=value), self.assertRaisesRegex(ws.Blocked, "capacity"):
                self.workspace.dispatch(value)
        self.assertEqual(self.workspace.dispatch(64)["capacity"], 8)
        result = self.workspace.dispatch(1)
        self.assertEqual(result["repository_limits"], {"Consumer": 1, "Provider": 1})

    def test_paths_requirements_and_instructions_are_repo_local(self):
        nested = self.root / "Provider/src"
        nested.mkdir()
        (nested / "AGENTS.override.md").write_text("Nested instructions\n")
        (self.root / "Provider/.codex").mkdir()
        (self.root / "Provider/.codex/PROJECT.md").write_text("Invariants\n")
        self.plan(["Provider/src/lib.py"])
        result = self.workspace.dispatch()
        packet = result["repositories"]["Provider"]
        self.assertEqual(packet["paths"], ["src/lib.py"])
        self.assertIn(str(nested / "AGENTS.override.md"), packet["instructions"])
        self.assertIn(str(self.root / "Provider/.codex/PROJECT.md"), packet["instructions"])
        self.assertEqual(packet["requirements"], ["The selected artifacts satisfy the contract"])
        self.assertIn("review-author", next(task["handoff"] for task in result["tasks"] if task["phase"] == "implement"))

    def test_tokens_bind_artifacts_permissions_contract_and_policies(self):
        self.plan(["Provider/lib.py"])
        original = self.workspace.dispatch()
        path = self.root / "Provider/lib.py"
        path.write_text("print('changed')\n")
        content = self.workspace.dispatch()
        self.assertNotEqual(original["token"], content["token"])
        self.assertEqual([task["id"] for task in original["tasks"]], [task["id"] for task in content["tasks"]])
        path.chmod(0o755)
        executable = self.workspace.dispatch()
        self.assertNotEqual(content["token"], executable["token"])
        self.agent_policy["defaults"]["max_concurrent_threads_per_session"] = 4
        self.agent_path.write_text(json.dumps(self.agent_policy))
        agent_policy = self.workspace.dispatch()
        self.assertNotEqual(executable["token"], agent_policy["token"])
        self.review_policy["deep_patterns"].append("lib.py")
        self.policy_path.write_text(json.dumps(self.review_policy))
        review_policy = self.workspace.dispatch()
        self.assertNotEqual(agent_policy["token"], review_policy["token"])
        self.workspace.plan({"requirements": ["The selected artifacts satisfy the contract", "The new condition holds"],
                             "paths": ["Provider/lib.py"], "extend_existing": True})
        self.assertNotEqual(review_policy["token"], self.workspace.dispatch()["token"])

    def test_budget_deadline_changes_plan_but_clock_crossing_does_not(self):
        self.plan(["Provider/lib.py"])
        original = self.workspace.dispatch()
        flow = ws.Workflow(self.root / "Provider", self.workspace.session)
        flow.review_operation("budget", {"expected_budget_revision": 0,
                                        "deadline_at": "2030-01-01T00:00:00Z",
                                        "reason": "Allocate time for independent review."})
        with patch.object(self.engine, "_utc_now", return_value=datetime(2029, 1, 1, tzinfo=timezone.utc)):
            before_deadline = self.workspace.dispatch()
        with patch.object(self.engine, "_utc_now", return_value=datetime(2031, 1, 1, tzinfo=timezone.utc)):
            after_deadline = self.workspace.dispatch()
        self.assertNotEqual(original["token"], before_deadline["token"])
        self.assertEqual(before_deadline, after_deadline)
        review = before_deadline["repositories"]["Provider"]["review"]
        self.assertEqual(review["budget"], {"revision": 1, "deadline_at": "2030-01-01T00:00:00Z"})
        self.assertNotIn("max_rounds", review)

    def test_rejects_missing_or_changed_contract_and_upstream(self):
        with self.assertRaisesRegex(ws.Blocked, "No workspace contract"):
            self.workspace.dispatch()
        self.plan(["Provider/lib.py"])
        ws.git(self.root / "Provider", "remote", "set-url", "origin", str(self.base / "wrong.git"))
        with self.assertRaisesRegex(ws.Blocked, "destination changed"):
            self.workspace.dispatch()
        ws.git(self.root / "Provider", "remote", "set-url", "origin", str(self.base / "Provider.git"))
        flow = ws.Workflow(self.root / "Provider", self.workspace.session)
        state = flow.load()
        state["requirements"].append("An undeclared contract mutation")
        flow.save(state)
        with self.assertRaisesRegex(ws.Blocked, "Contract changed outside"):
            self.workspace.dispatch()

    def test_rejects_artifact_symlinks_and_concurrent_mutations(self):
        self.plan(["Provider/lib.py"])
        path = self.root / "Provider/lib.py"
        path.unlink()
        path.symlink_to(self.root / "Provider/README.md")
        with self.assertRaisesRegex(ws.Blocked, "Symlink"):
            self.workspace.dispatch()
        path.unlink()
        path.write_text("pass\n")
        original = dispatch.waves

        def mutate(*args):
            path.write_text("changed during dispatch\n")
            return original(*args)

        with patch.object(dispatch, "waves", side_effect=mutate), self.assertRaisesRegex(ws.Blocked, "artifacts changed"):
            self.workspace.dispatch()

    def test_rejects_private_paths_even_if_contract_was_tampered(self):
        self.plan(["Provider/lib.py"])
        flow = ws.Workflow(self.root / "Provider", self.workspace.session)
        state = flow.load()
        state["paths"] = [".codex/sessions/private.json"]
        flow.save(state)
        with self.assertRaisesRegex(ws.Blocked, "Private"):
            self.workspace.dispatch()

    def test_readonly_contract_does_not_invent_review_receipts(self):
        self.plan([])
        result = self.workspace.dispatch()
        self.assertFalse(result["repositories"]["."]["review"]["enabled"])
        self.assertFalse(any(task["phase"].startswith("review-") for task in result["tasks"]))
        self.assertTrue(all(not task["write_paths"] for task in result["tasks"]))
        self.assertFalse(any("review-author" in task["handoff"] for task in result["tasks"]))
        self.assertIsNone(ws.Workflow(self.root, self.workspace.session).load().get("review_gate"))
        self.assertEqual([task["phase"] for task in result["tasks"]], ["check", "integrate"])
        self.assertTrue(all(task["executor"] == "coordinator" for task in result["tasks"]))
        original_head = ws.git(self.root, "rev-parse", "HEAD")
        self.workspace.review({".": {"The selected artifacts satisfy the contract": "The read-only contract declares no deliverables."}})
        self.workspace.publish(".")
        self.assertTrue(self.workspace.finish()["completed"])
        self.assertEqual(ws.git(self.root, "rev-parse", "HEAD"), original_head)

    def test_single_repository_uses_coordinator_for_implementation(self):
        self.plan(["Provider/lib.py"])
        tasks = self.workspace.dispatch()["tasks"]
        self.assertFalse(any(task["phase"] in {"map", "research"} for task in tasks))
        implementation = [task for task in tasks if task["phase"] == "implement"]
        self.assertEqual(len(implementation), 1)
        self.assertEqual(implementation[0]["executor"], "coordinator")
        self.assertIsNone(implementation[0]["agent_role"])
        self.assertEqual(implementation[0]["write_paths"], ["lib.py"])
        agents = [task for task in tasks if task["executor"] == "agent"]
        self.assertEqual(len(agents), 3)
        self.assertTrue(all(task["phase"].startswith("review-") for task in agents))

    def test_multiple_repositories_delegate_only_scoped_implementation(self):
        self.plan(depends_on={"Consumer": ["Provider"]})
        tasks = self.workspace.dispatch()["tasks"]
        self.assertFalse(any(task["phase"] in {"map", "research"} for task in tasks))
        implementations = [task for task in tasks if task["phase"] == "implement"]
        self.assertEqual({task["repository"] for task in implementations}, {"Provider", "Consumer"})
        self.assertTrue(all(task["executor"] == "agent" and task["agent_role"]
                            for task in implementations))
        consumer = next(task for task in implementations if task["repository"] == "Consumer")
        self.assertIn("Provider::check", consumer["depends_on"])
        self.assertNotIn("Provider::integrate", consumer["depends_on"])

    def canonical_cli(self, package: Path, *arguments: str, cwd: Path):
        """Run a standalone package without compatibility modules in its source root."""
        shutil.copytree(MODULE / "ecosystem", package, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "tests"))
        if package == self.root / ".codex/ecosystem":
            self.own_source_manifest(package)
            arguments = ("--source", *arguments)
        return self.run_canonical_cli(package / "cli.py", *arguments, cwd=cwd)

    def own_source_manifest(self, source: Path) -> None:
        manifest = (source / "manifests/codex-plugin.json").relative_to(self.root)
        if not ws.git(self.root, "ls-tree", "HEAD", "--", manifest.as_posix()):
            ws.git(self.root, "add", "--", manifest.as_posix())
            ws.git(self.root, "commit", "-m", "Identify the source checkout for developer tests")

    def run_canonical_cli(self, entry: Path, *arguments: str, cwd: Path):
        result = subprocess.run([sys.executable, "-B", str(entry), *arguments],
                                cwd=cwd, capture_output=True, text=True,
                                env={**os.environ, "CODEX_HOME": str(self.base / "codex-home")})
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def native_child_workspace(self):
        child = self.root / "Provider"
        (child / ".codex").mkdir()
        (child / ".codex/repositories.json").write_text(json.dumps({
            "schema_version": 1, "repositories": [{"path": ".", "management": "native"}]}))
        (child / ".codex/agent-policy.json").write_text(json.dumps({
            "schema_version": 1, "defaults": {"max_concurrent_threads_per_session": 3},
            "repositories": {}}))
        return child

    def checkout_entry(self) -> Path:
        """Produce a real source Git owner and a sentinel against local imports."""
        source = self.root / ".codex/ecosystem"
        (source / "manifests").mkdir(parents=True)
        shutil.copy2(MODULE / "ecosystem/cli.py", source / "cli.py")
        (source / "manifests/codex-plugin.json").write_text('{"name":"constellation"}')
        ws.git(self.root, "add", ".codex/ecosystem")
        ws.git(self.root, "commit", "-m", "Own the source entry")
        (source / "__init__.py").write_text("raise AssertionError('Mutable runtime imported')\n")
        return source / "cli.py"

    def test_workspace_root_case_alias_retains_owner_and_registry_boundaries(self):
        alias = self.root.with_name(self.root.name.swapcase())
        if not alias.exists() or not self.root.samefile(alias):
            self.skipTest("The test filesystem uses case-sensitive root lookup")
        workspace = ws.Workspace(alias, "physical-owner")
        self.assertEqual(workspace.root, self.root)
        self.assertEqual(workspace.route(["Provider/README.md"])[0]["repository"], "Provider")
        nested = self.root / "nested"
        nested.mkdir()
        with self.assertRaisesRegex(ws.Blocked, "repository root"):
            ws.Workspace(nested, "not-an-owner")

    def test_unidentified_checkout_never_imports_its_siblings(self):
        source = self.root / ".codex/ecosystem"
        source.mkdir()
        entry = source / "cli.py"
        shutil.copy2(MODULE / "ecosystem/cli.py", entry)
        marker = self.root / "unverified-import"
        poison = f"open({str(marker)!r}, 'w').close()\nraise RuntimeError('unverified import')\n"
        (source / "__init__.py").write_text(poison)
        (source / "json.py").write_text(poison)
        for args in (["workspace", "route", "README.md"], ["--source", "workspace", "route", "README.md"]):
            result = subprocess.run([sys.executable, str(entry), *args], cwd=self.root / "Provider",
                                    env={**os.environ, "CODEX_HOME": str(self.base / "empty-home")},
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertFalse(marker.exists())
        # A caller-provided bundle marker cannot authorize local Python imports.
        (source.parent / "bundle.json").write_text('{"schema":1,"files":{}}')
        result = subprocess.run([sys.executable, str(entry), "workspace", "route", "README.md"],
                                cwd=self.root, env={**os.environ, "CODEX_HOME": str(self.base / "empty-home")},
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(marker.exists())

    def test_legacy_checkout_entry_requires_a_cli_capable_installation(self):
        entry = self.checkout_entry()
        home = self.base / "old-home"
        bootstrap = home / "constellation/hook.py"
        bootstrap.parent.mkdir(parents=True)
        for legacy in (False, True):
            with self.subTest(legacy=legacy):
                if legacy:
                    bootstrap.write_text("print('hook-only release')\n")
                    bootstrap.chmod(0o644)
                    (bootstrap.parent / ".install.lock").touch(mode=0o600)
                    leftover = bootstrap.parent / "run"
                    leftover.write_text("#!/bin/sh\nexit 0\n")
                    leftover.chmod(0o700)
                    old = {'mode': 0o644, 'sha256': hashlib.sha256(bootstrap.read_bytes()).hexdigest()}
                    (bootstrap.parent / 'receipt.json').write_text(json.dumps({
                        'schema': 3, 'hook': old, 'cache': {'ecosystem/hook_entry.py': old}}))
                result = subprocess.run([sys.executable, "-I", str(entry), "git", "git-hook", "pre-commit"],
                                        env={**os.environ, "CODEX_HOME": str(home)}, cwd=self.root / "Provider",
                                        text=True, capture_output=True)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn("verified CLI", result.stderr)
                self.assertEqual(result.stdout, "")

    @unittest.skipIf(os.name == "nt", "Codex installation is a POSIX target")
    def test_parent_and_child_use_one_verified_installation(self):
        entry = self.checkout_entry()
        child = self.native_child_workspace()
        home = self.base / "device-home"
        bundle = self.base / "release"
        builder.build_bundle(bundle, modules=["coding"], source_root=MODULE)
        install_test_bundle(bundle, home)
        stable = [str(home / "constellation/run"), "cli"]
        legacy = [sys.executable, str(entry)]

        def run(cmd, args, cwd, *, code=0, payload=None):
            result = subprocess.run([*cmd, *args], env={**os.environ, "CODEX_HOME": str(home)},
                                    cwd=cwd, text=True, input=json.dumps(payload) if payload is not None else None,
                                    capture_output=True, timeout=20)
            self.assertEqual(result.returncode, code, result.stdout + result.stderr)
            return json.loads(result.stdout) if code == 0 else result.stderr

        for cwd in (self.root, child):
            route = run(legacy, ["workspace", "route", "Consumer/README.md"], cwd)
            self.assertEqual(route[0]["repository"], "Consumer")
            explicit = run(legacy, ["workspace", "--root", str(child), "route", "README.md"], cwd)
            self.assertEqual(explicit[0]["repository"], ".")
        self.assertEqual(run(stable, ["workspace", "route", "README.md"], child)[0]["repository"], ".")
        outsider = child / "Unregistered"
        outsider.mkdir()
        subprocess.run(["git", "init", "-q", str(outsider)], check=True)
        (outsider / "README.md").write_text("outside the registry")
        member = "Provider/Unregistered/README.md"
        observed = run(stable, ["workspace", "--root", str(self.root), "route", member], child)
        self.assertEqual(observed[0]["management"], "unregistered")
        error = run(stable, ["workspace", "--root", str(self.root), "--session", "denied", "plan"], child,
                    code=2, payload={"requirements": ["Leave unregistered projects outside the task"], "paths": [member]})
        self.assertIn("register", error.lower())
        invalid = run(stable, ["native", "--codex-home", str(home), "--expected-bundle-sha256", "invalid"],
                      child, code=2)
        self.assertIn("requires --exclude-source-root", invalid)
        skill = run(stable, ["skill-read", "coding"], child)
        self.assertEqual(skill["content"], (bundle / "skills/coding/SKILL.md").read_text())
        self.assertEqual(Path(skill["path"]).name, "SKILL.md")
        for name in ("../coding", "coding/references/workflow.md", "mathematics"):
            self.assertTrue(run(stable, ["skill-read", name], child, code=2))

        # The owner's existing Git hook also enters through the legacy path.
        # Exercise both decisions on a disposable index and no user payload.
        guard = self.root / ".git/hooks/pre-commit"
        shutil.copy2(MODULE / "git-hooks/pre-commit", guard)
        shadow = self.base / "shadow-bin"
        shadow.mkdir()
        poison = shadow / "python3"
        poison.write_text("#!/bin/sh\nexit 91\n")
        poison.chmod(0o755)
        environment = {**os.environ, "CODEX_HOME": str(home),
                       "PATH": str(shadow) + os.pathsep + os.environ.get("PATH", "")}
        for filename, expected in (("public.txt", 0), (".env.fixture", 2)):
            (self.root / filename).write_text("synthetic fixture\n")
            ws.git(self.root, "add", "--", filename)
            guard_run = subprocess.run(["git", "hook", "run", "pre-commit"], env=environment,
                                       cwd=self.root, capture_output=True, text=True, timeout=20)
            self.assertEqual(guard_run.returncode, expected, guard_run.stdout + guard_run.stderr)

        # Damage to the registered executable cannot turn a guard into a successful no-op.
        launcher = home / "constellation/run"
        launcher.write_text("#!/bin/sh\nexit 0\n")
        denied = run(legacy, ["workspace", "route", "README.md"], self.root, code=2)
        self.assertIn("verified CLI", denied)

    def test_source_cli_defaults_to_its_hub_and_accepts_an_explicit_root(self):
        child = self.native_child_workspace()
        package = self.root / ".codex/ecosystem"
        route = self.canonical_cli(package, "workspace", "route", "Consumer/README.md", cwd=self.base)
        self.assertEqual(route[0]["repository"], "Consumer")
        policy = self.canonical_cli(package, "agent-policy", "show", "--repo", "Consumer", cwd=child)
        self.assertEqual(policy["repositories"][0]["max_concurrent_threads_per_session"], 8)
        route = self.canonical_cli(package, "workspace", "--root", str(child), "route", "README.md", cwd=self.base)
        self.assertEqual(route[0]["repository"], ".")
        policy = self.canonical_cli(package, "agent-policy", "--root", str(child), "show", cwd=self.base)
        self.assertEqual(policy["repositories"][0]["max_concurrent_threads_per_session"], 3)

    def test_invalid_source_registry_never_selects_the_callers_workspace(self):
        child = self.native_child_workspace()
        package = self.root / ".codex/ecosystem"
        shutil.copytree(MODULE / "ecosystem", package,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "tests"))
        self.own_source_manifest(package)
        registry = self.root / ".codex/repositories.json"
        for condition in ("missing", "malformed", "directory", "symlink"):
            with self.subTest(registry=condition):
                if registry.is_dir():
                    registry.rmdir()
                elif registry.exists() or registry.is_symlink():
                    registry.unlink()
                if condition == "malformed":
                    registry.write_text("{invalid")
                elif condition == "directory":
                    registry.mkdir()
                elif condition == "symlink":
                    try:
                        registry.symlink_to(child / ".codex/repositories.json")
                    except OSError as exc:
                        self.skipTest(f"Symlink fixture unavailable: {exc}")
                before = self.fingerprints()
                for arguments in (("workspace", "route", "README.md"), ("agent-policy", "show")):
                    with self.subTest(command=arguments[0]):
                        result = subprocess.run([sys.executable, "-B", str(package / "cli.py"), "--source", *arguments],
                                                cwd=child, capture_output=True, text=True,
                                                env={**os.environ, "CODEX_HOME": str(self.base / "codex-home")})
                        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertEqual(self.fingerprints(), before)

    def test_distributed_cli_discovers_the_callers_workspace(self):
        child = self.native_child_workspace()
        package = self.base / "bundle/ecosystem"
        route = self.canonical_cli(package, "workspace", "route", "README.md", cwd=child)
        self.assertEqual(route[0]["repository"], ".")
        policy = self.canonical_cli(package, "agent-policy", "show", cwd=child)
        self.assertEqual(policy["repositories"][0]["max_concurrent_threads_per_session"], 3)
        route = self.canonical_cli(package, "workspace", "--root", str(self.root),
                                   "route", "Consumer/README.md", cwd=child)
        self.assertEqual(route[0]["repository"], "Consumer")

    def test_verified_bundle_in_reserved_directory_uses_the_callers_workspace(self):
        child = self.native_child_workspace()
        bundle = self.base / "package-location/.codex"
        builder.build_bundle(bundle, modules=["coding"], source_root=MODULE)
        install_test_bundle(bundle, self.base / "codex-home")
        before = self.fingerprints()
        route = self.run_canonical_cli(bundle / "ecosystem/cli.py", "workspace", "route", "README.md", cwd=child)
        self.assertEqual(route[0]["repository"], ".")
        policy = self.run_canonical_cli(bundle / "ecosystem/cli.py", "agent-policy", "show", cwd=child)
        self.assertEqual(policy["repositories"][0]["max_concurrent_threads_per_session"], 3)
        route = self.run_canonical_cli(bundle / "ecosystem/cli.py", "workspace", "--root", str(self.root),
                                       "route", "Consumer/README.md", cwd=child)
        self.assertEqual(route[0]["repository"], "Consumer")
        self.assertEqual(self.fingerprints(), before)

    def test_source_directory_case_alias_preserves_its_workspace(self):
        child = self.native_child_workspace()
        package = self.root / ".codex/ecosystem"
        shutil.copytree(MODULE / "ecosystem", package,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "tests"))
        self.own_source_manifest(package)
        alias = self.root / ".CODEX/ecosystem/cli.py"
        if not alias.is_file() or not alias.samefile(package / "cli.py"):
            self.skipTest("The fixture volume has case-sensitive path lookup")
        before = self.fingerprints()
        route = self.run_canonical_cli(alias, "--source", "workspace", "route", "Consumer/README.md", cwd=child)
        self.assertEqual(route[0]["repository"], "Consumer")
        policy = self.run_canonical_cli(alias, "--source", "agent-policy", "show", "--repo", "Consumer", cwd=child)
        self.assertEqual(policy["repositories"][0]["max_concurrent_threads_per_session"], 8)
        self.assertEqual(self.fingerprints(), before)

    def test_unverified_bundle_markers_cannot_redirect_the_source_workspace(self):
        child = self.native_child_workspace()
        package = self.root / ".codex/ecosystem"
        shutil.copytree(MODULE / "ecosystem", package,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "tests"))
        self.own_source_manifest(package)
        genuine = builder.build_bundle(self.base / "genuine-bundle", modules=["coding"], source_root=MODULE)
        marker = package.parent / "bundle.json"
        records = ("{invalid", json.dumps({"schema": 1, "modules": ["coding"], "files": {}}),
                   json.dumps(genuine))
        for content in records:
            with self.subTest(marker=content[:45]):
                marker.write_text(content)
                before = self.fingerprints()
                route = self.run_canonical_cli(package / "cli.py", "--source", "workspace", "route", "Consumer/README.md", cwd=child)
                self.assertEqual(route[0]["repository"], "Consumer")
                policy = self.run_canonical_cli(package / "cli.py", "--source", "agent-policy", "show", "--repo", "Consumer", cwd=child)
                self.assertEqual(policy["repositories"][0]["max_concurrent_threads_per_session"], 8)
                self.assertEqual(self.fingerprints(), before)

    def test_cli_is_readonly_and_returns_json(self):
        self.plan(["Provider/lib.py"])
        before = self.fingerprints()
        result = subprocess.run([sys.executable, "-B", str(MODULE / "ecosystem/cli.py"),
                                 *(["--source"] if cli._source_checkout() else []), "workspace", "--root", str(self.root),
                                 "--session", self.workspace.session, "dispatch", "--capacity", "2"],
                                capture_output=True, text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["capacity"], 2)
        self.assertEqual(self.fingerprints(), before)

    def test_graph_rejects_cycles_unknown_prerequisites_and_duplicate_ids(self):
        a = {"id": "a", "repository": ".", "executor": "agent", "depends_on": ["b"]}
        b = {"id": "b", "repository": ".", "executor": "agent", "depends_on": ["a"]}
        with self.assertRaisesRegex(ws.Blocked, "cycle"):
            dispatch.waves([a, b], 1, {".": 1})
        with self.assertRaisesRegex(ws.Blocked, "dependencies"):
            dispatch.waves([a], 1, {".": 1})
        with self.assertRaisesRegex(ws.Blocked, "unique"):
            dispatch.waves([a, a], 1, {".": 1})

    def test_rejects_unregistered_participant_and_changed_dependency_order(self):
        self.plan(depends_on={"Consumer": ["Provider"]})
        self.workspace.repositories.pop("Provider")
        with self.assertRaisesRegex(ws.Blocked, "registry changed"):
            self.workspace.dispatch()
        self.workspace.repositories["Provider"] = "native"
        state = self.workspace.load()
        state["order"] = list(reversed(state["order"]))
        self.workspace.save(state)
        with self.assertRaisesRegex(ws.Blocked, "publication order"):
            self.workspace.dispatch()

    def remove_provider(self):
        registry = {**self.registry, "repositories": [entry for entry in self.registry["repositories"]
                                                      if entry["path"] != "Provider"]}
        (self.root / ".codex/repositories.json").write_text(json.dumps(registry))

    def test_rejects_registry_change_between_constructor_and_dispatch(self):
        self.plan(["Provider/lib.py"])
        self.assertIsNotNone(self.engine.policy_for(self.root / "Provider"))
        self.remove_provider()
        self.assertIsNone(self.engine.policy_for(self.root / "Provider"))
        with self.assertRaisesRegex(ws.Blocked, "registry changed since workspace construction"):
            self.workspace.dispatch()

    def test_rejects_registry_change_during_first_plan_read(self):
        self.plan(["Provider/lib.py"])
        load = self.workspace.load
        calls = 0

        def change_registry():
            nonlocal calls
            calls += 1
            if calls == 1:
                self.remove_provider()
            return load()

        with patch.object(self.workspace, "load", side_effect=change_registry):
            with self.assertRaisesRegex(ws.Blocked, "registry changed during dispatch"):
                self.workspace.dispatch()
        self.assertIsNone(self.engine.policy_for(self.root / "Provider"))

    def test_rejects_registry_change_during_final_context_recheck(self):
        self.plan(["Provider/lib.py"])
        prepare = self.engine.prepare
        calls = 0

        def change_after_prepare(*args, **kwargs):
            nonlocal calls
            calls += 1
            context = prepare(*args, **kwargs)
            if calls == 2:
                self.remove_provider()
            return context

        with patch.object(self.engine, "prepare", side_effect=change_after_prepare):
            with self.assertRaisesRegex(ws.Blocked, "registry changed during dispatch"):
                self.workspace.dispatch()

    def test_external_packet_preserves_local_review_without_native_author_command(self):
        self.registry["repositories"][2]["management"] = "external"
        (self.root / ".codex/repositories.json").write_text(json.dumps(self.registry))
        self.workspace = ws.Workspace(self.root, "external-dispatch")
        self.plan(["Consumer/lib.py"], external_repositories=["Consumer"])
        result = self.workspace.dispatch()
        self.assertEqual(result["repositories"]["Consumer"]["management"], "external")
        self.assertFalse(result["repositories"]["Consumer"]["review"]["enabled"])
        self.assertFalse(any("review-author" in task["handoff"] for task in result["tasks"]))
        self.assertFalse(any(task["phase"].startswith("review-") for task in result["tasks"]))
        integration = next(task for task in result["tasks"] if task["phase"] == "integrate")
        self.assertIn("Consumer::check", integration["depends_on"])

    def execute_dependent_plan(self, provider_mode="changed"):
        requirement = "The consumer uses the verified provider artifact"
        paths = ["Consumer/app.py"]
        extra = {}
        if provider_mode == "empty":
            extra["unrelated"] = {"Provider/README.md": "Tracked reference input, with no requested provider changes."}
        else:
            paths.append("Provider/lib.py" if provider_mode == "changed" else "Provider/README.md")
        original_provider_head = ws.git(self.root / "Provider", "rev-parse", "HEAD")
        self.workspace.plan({"requirements": [requirement], "paths": paths,
                             "depends_on": {"Consumer": ["Provider"]}, **extra})
        result = self.workspace.dispatch(3)
        tasks = {task["id"]: task for task in result["tasks"]}
        contexts = {}
        completed = set()
        integrations = []
        reviewed = False
        for wave in result["waves"]:
            for identifier in wave:
                task = tasks[identifier]
                self.assertLessEqual(set(task["depends_on"]), completed)
                repo, phase = task["repository"], task["phase"]
                root = self.root / repo
                if phase == "implement":
                    if repo == "Provider" and provider_mode == "changed":
                        (root / "lib.py").write_text("def value():\n    return 42\n")
                    elif repo == "Consumer":
                        self.assertIn("Provider::check", completed)
                        source = ("import runpy\nprovider = runpy.run_path('../Provider/lib.py')\n"
                                  "def value():\n    return provider['value']() + 1\n"
                                  if provider_mode == "changed" else
                                  "from pathlib import Path\ndef value():\n    return Path('../Provider/README.md').read_text()\n")
                        (root / "app.py").write_text(source)
                elif phase == "check":
                    authored_paths = sorted(set(task["paths"]) & ws.changed(root))
                    if result["repositories"][repo]["review"]["enabled"] and authored_paths:
                        self.workspace.review_operation(repo, "author", {
                            "author": f"fixture-{repo}-implementer", "paths": authored_paths})
                    if provider_mode == "changed":
                        expression = "import lib; assert lib.value() == 42" if repo == "Provider" else "import app; assert app.value() == 43"
                    else:
                        expression = ("from pathlib import Path; assert Path('README.md').read_text() == 'A fixture\\n'"
                                      if repo == "Provider" else "import app; assert app.value() == 'A fixture\\n'")
                    check = self.workspace.check(repo, [sys.executable, "-B", "-c", expression])
                    self.assertEqual(check["exit_code"], 0)
                elif phase.startswith("review-"):
                    if repo not in contexts:
                        contexts[repo] = self.workspace.review_operation(repo, "start")
                    self.workspace.review_operation(repo, "report", {
                        "token": contexts[repo]["token"], "reviewer": f"fixture-{repo}-{phase}-agent",
                        "role": "reviewer", "focus": task["focus"], "paths": task["paths"],
                        "summary": "0 actionable findings in the fixture implementation.",
                        "evidence": "Inspected the declared provider and consumer artifacts; recorded executions assert their expected results.",
                        "findings": [],
                    })
                elif phase == "integrate":
                    if not reviewed:
                        self.workspace.review({name: {requirement: "The provider check verifies its artifact and the consumer check asserts the derived result."}
                                               for name in result["repositories"]})
                        reviewed = True
                    if repo == "Consumer":
                        self.assertIn("Provider", integrations)
                    selected = [f"{repo}/{path}" for path in task["paths"] if path in ws.changed(root)]
                    if selected:
                        self.workspace.commit(selected, f"Publish verified {repo} fixture")
                    else:
                        with self.assertRaisesRegex(ws.Blocked, "Publish dependency Provider"):
                            self.workspace.commit(["Consumer/app.py"], "Wait for provider publication")
                        publication = self.workspace.publish(repo)
                        self.assertTrue(publication["repositories"][repo]["unchanged"])
                        self.assertEqual(publication["repositories"][repo]["head"], original_provider_head)
                    integrations.append(repo)
            completed.update(wave)
        self.assertEqual(completed, set(tasks))
        self.assertEqual(integrations, ["Provider", "Consumer"])
        self.assertTrue(self.workspace.finish()["completed"])
        for repo in integrations:
            head = ws.git(self.root / repo, "rev-parse", "HEAD")
            self.assertEqual(head, ws.git(self.base / f"{repo}.git", "rev-parse", "refs/heads/main"))
            state = ws.Workflow(self.root / repo, self.workspace.session).load()
            self.assertEqual(state["finished"]["head"], head)
            if repo == "Provider" and provider_mode != "changed":
                self.assertEqual(head, original_provider_head)
                self.assertEqual(state["commits"], [])

    def test_dispatch_executes_dependent_repositories_through_verified_publication(self):
        self.execute_dependent_plan()

    def test_dispatch_publishes_unchanged_provider_before_consumer(self):
        self.execute_dependent_plan("unchanged")

    def test_dispatch_publishes_empty_scope_provider_before_consumer(self):
        self.execute_dependent_plan("empty")

    def review_current_plan(self):
        result = self.workspace.dispatch()
        contexts = {}
        for repo in result["repositories"]:
            self.workspace.check(repo, ["git", "diff", "--check"])
        for task in result["tasks"]:
            if not task["phase"].startswith("review-"):
                continue
            repo = task["repository"]
            if repo not in contexts:
                contexts[repo] = self.workspace.review_operation(repo, "start")
            self.workspace.review_operation(repo, "report", {
                "token": contexts[repo]["token"], "reviewer": f"fixture-{repo}-{task['phase']}-agent",
                "role": "reviewer", "focus": task["focus"], "paths": task["paths"],
                "summary": "0 actionable findings in the fixture artifacts.",
                "evidence": "Read the declared fixture artifacts and checked their expected constant contents.", "findings": [],
            })
        self.workspace.review({repo: {requirement: "Read the selected fixture artifacts and recorded the required checks and reports."
                                      for requirement in packet["requirements"]}
                               for repo, packet in result["repositories"].items()})

    def test_publish_rejects_uncommitted_task_artifacts_even_when_reviewed(self):
        self.plan(["Provider/lib.py"])
        self.review_current_plan()
        original = ws.git(self.root / "Provider", "rev-parse", "HEAD")
        with self.assertRaisesRegex(ws.Blocked, "Uncommitted task files"):
            self.workspace.publish("Provider")
        self.assertEqual(ws.git(self.root / "Provider", "rev-parse", "HEAD"), original)
        self.assertEqual(ws.git(self.base / "Provider.git", "rev-parse", "refs/heads/main"), original)

    def test_publish_requires_current_review(self):
        self.plan(["Provider/README.md"])
        with self.assertRaisesRegex(ws.Blocked, "Missing or stale review"):
            self.workspace.publish("Provider")
        self.review_current_plan()
        (self.root / "Provider/README.md").write_text("Changed after review\n")
        with self.assertRaisesRegex(ws.Blocked, "Missing or stale review"):
            self.workspace.publish("Provider")

    def test_publish_requires_dependency_publication_for_unchanged_consumer(self):
        self.plan(["Provider/README.md", "Consumer/README.md"], depends_on={"Consumer": ["Provider"]})
        self.review_current_plan()
        heads = {repo: ws.git(self.root / repo, "rev-parse", "HEAD") for repo in ("Provider", "Consumer")}
        with self.assertRaisesRegex(ws.Blocked, "Publish dependency Provider"):
            self.workspace.publish("Consumer")
        for repo in ("Provider", "Consumer"):
            publication = self.workspace.publish(repo)
            self.assertEqual(publication["repositories"][repo]["head"], heads[repo])
            self.assertEqual(ws.git(self.base / f"{repo}.git", "rev-parse", "refs/heads/main"), heads[repo])
        self.assertTrue(self.workspace.finish()["completed"])

    def test_publish_rejects_out_of_plan_repository_and_changed_target(self):
        self.plan(["Provider/README.md"])
        self.review_current_plan()
        with self.assertRaisesRegex(ws.Blocked, "outside the plan"):
            self.workspace.publish("Consumer")
        ws.git(self.root / "Provider", "remote", "set-url", "origin", str(self.base / "wrong.git"))
        with self.assertRaisesRegex(ws.Blocked, "destination changed"):
            self.workspace.publish("Provider")
        self.assertIsNone(ws.Workflow(self.root / "Provider", self.workspace.session).load().get("publication"))

    def test_publish_rechecks_scope_after_remote_verification(self):
        self.plan(["Provider/README.md"])
        self.review_current_plan()
        original = ws.Workflow.publish

        observed_publications = []

        def mutate(flow, *, whole_head=False):
            self.assertFalse(whole_head)
            result = original(flow, whole_head=whole_head)
            observed_publications.append(result)
            (flow.root / "unexpected.py").write_text("pass\n")
            return result

        with patch.object(ws.Workflow, "publish", mutate):
            with self.assertRaisesRegex(ws.Blocked, "New undeclared files"):
                self.workspace.publish("Provider")
        self.assertEqual(len(observed_publications), 1)
        self.assertTrue((self.root / "Provider/unexpected.py").is_file())
        self.assertIsNone(ws.Workflow(self.root / "Provider", self.workspace.session).load().get("publication"))

    def test_publish_cli_verifies_head_without_an_empty_commit(self):
        self.plan(["Provider/README.md"])
        self.review_current_plan()
        original = ws.git(self.root / "Provider", "rev-parse", "HEAD")
        output = io.StringIO()
        argv = ["cli.py", "workspace", "--root", str(self.root), "--session", self.workspace.session, "publish", "--repo", "Provider"]
        with patch.object(sys, "argv", argv), patch.object(sys, "stdout", output):
            self.assertEqual(cli.main(), 0)
        result = json.loads(output.getvalue())
        self.assertTrue(result["repositories"]["Provider"]["unchanged"])
        self.assertEqual(result["repositories"]["Provider"]["head"], original)
        self.assertEqual(ws.git(self.root / "Provider", "rev-parse", "HEAD"), original)
        self.assertEqual(ws.git(self.base / "Provider.git", "rev-parse", "refs/heads/main"), original)
        self.assertEqual(self.workspace.load()["operation"], "publish")


if __name__ == "__main__":
    unittest.main()

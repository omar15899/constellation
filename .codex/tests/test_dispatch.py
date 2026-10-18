"""Dispatch plans are deterministic, bounded and cannot execute their packets."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE))
from ecosystem.runtime import dispatch
from ecosystem.runtime import workspace as ws
from ecosystem.runtime.workflow import review_engine


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

    def test_cli_is_readonly_and_returns_json(self):
        self.plan(["Provider/lib.py"])
        before = self.fingerprints()
        result = subprocess.run([sys.executable, "-B", str(MODULE / "workspace.py"), "--root", str(self.root),
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

        def mutate(flow):
            result = original(flow)
            (flow.root / "unexpected.py").write_text("pass\n")
            return result

        with patch.object(ws.Workflow, "publish", mutate):
            with self.assertRaisesRegex(ws.Blocked, "New undeclared files"):
                self.workspace.publish("Provider")
        self.assertIsNone(ws.Workflow(self.root / "Provider", self.workspace.session).load().get("publication"))

    def test_publish_cli_verifies_head_without_an_empty_commit(self):
        self.plan(["Provider/README.md"])
        self.review_current_plan()
        original = ws.git(self.root / "Provider", "rev-parse", "HEAD")
        output = io.StringIO()
        argv = ["workspace.py", "--root", str(self.root), "--session", self.workspace.session, "publish", "--repo", "Provider"]
        with patch.object(sys, "argv", argv), patch.object(sys, "stdout", output):
            self.assertEqual(ws.main(), 0)
        result = json.loads(output.getvalue())
        self.assertTrue(result["repositories"]["Provider"]["unchanged"])
        self.assertEqual(result["repositories"]["Provider"]["head"], original)
        self.assertEqual(ws.git(self.root / "Provider", "rev-parse", "HEAD"), original)
        self.assertEqual(ws.git(self.base / "Provider.git", "rev-parse", "refs/heads/main"), original)
        self.assertEqual(self.workspace.load()["operation"], "publish")


if __name__ == "__main__":
    unittest.main()

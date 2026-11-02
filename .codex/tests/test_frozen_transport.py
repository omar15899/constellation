"""A concurrent change of Git configuration must never redirect an outgoing commit."""
from __future__ import annotations

import json
import os
import shlex
from contextlib import nullcontext
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ecosystem.runtime import workflow as git_workflow
from ecosystem.vault import review_gate, workflow as vault_workflow


class FrozenPublication(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name).resolve()
        home = self.base / "home"
        home.mkdir()
        self.enterContext(patch.dict(os.environ, {"HOME": str(home), "XDG_CONFIG_HOME": str(home),
                                                  "CODEX_HOME": str(home / "codex")}))
        self.run_git = subprocess.run

    def git(self, root: Path, *args: str) -> str:
        return self.run_git(["git", *args], cwd=root, check=True, text=True,
                            capture_output=True).stdout.strip()

    def setup_owner(self, name: str, module, *, provider: bool | None = None, relative: bool = False):
        area = self.base / name
        area.mkdir()
        # The recipient exercises real Git operations in isolation from the
        # independent review protocol (covered by the native profile suite).
        registry = area / ".codex/repositories.json"
        registry.parent.mkdir()
        registry.write_text(json.dumps({"schema_version": 1, "repositories": [
            {"path": "owner", "management": "external"}]}))
        root, approved, other = (area / n for n in ("owner", "approved.git", "unrelated.git"))
        self.git(area, "init", "--bare", "--initial-branch=main", str(approved))
        self.git(area, "init", "--initial-branch=main", str(root))
        self.git(root, "config", "user.name", "Test")
        self.git(root, "config", "user.email", "test@example.invalid")
        self.git(root, "config", "commit.gpgSign", "false")
        self.git(root, "config", "core.hooksPath", str(root / ".git/hooks"))
        self.git(root, "remote", "add", "origin", os.path.relpath(approved, root) if relative else str(approved))
        self.git(root, "commit", "--allow-empty", "-m", "seed")
        self.git(root, "push", "-u", "origin", "main")
        self.git(area, "clone", "--bare", str(approved), str(other))
        seed = self.git(root, "rev-parse", "HEAD")
        provider = module is vault_workflow if provider is None else provider
        if provider:
            # Explicit provider publication covers its initial HEAD.
            self.git(root, "commit", "--allow-empty", "-m", "unpublished revision")
        flow = module.Workflow(root, "publication-race")
        flow.begin("new")
        requirement = "Verify the published source revision."
        flow.plan({"paths": [] if provider else ["answer.txt"], "requirements": [requirement]})
        if not provider:
            (root / "answer.txt").write_text("approved change\n")
        flow.review({requirement: "The source and the selected destination have been checked."})
        return root, approved, other, seed, flow

    @staticmethod
    def publish(flow):
        if isinstance(flow, vault_workflow.Workflow):
            with review_gate.selected_project(flow.root):
                return flow.finish(publish_readonly=True)
        return flow.commit(["answer.txt"], "Publish approved change")

    def test_configuration_races_at_transport_never_disclose_to_other_remote(self) -> None:
        for module, profile in ((git_workflow, "workspace"), (vault_workflow, "vault")):
            for change in ("remote", "extraPushUrl", "pushInsteadOf", "insteadOf", "receivepack", "helper"):
                with self.subTest(profile=profile, change=change):
                    root, approved, other, seed, flow = self.setup_owner(profile + change, module)
                    fired = False
                    programs = root.parent / "programs"
                    programs.mkdir()
                    marker = programs / "unauthorized-helper-ran"
                    executable = programs / ("git-remote-rogue" if change == "helper" else "receiver")
                    executable.write_text("#!/bin/sh\n"
                                          + "touch " + shlex.quote(str(marker)) + "\n"
                                          + "exec git receive-pack " + shlex.quote(str(other)) + "\n")
                    executable.chmod(0o755)

                    def race(args, *rest, **kwargs):
                        nonlocal fired
                        if not fired and ("push" in args or "send-pack" in args):
                            fired = True
                            if change == "remote":
                                self.git(root, "remote", "set-url", "origin", str(other))
                            elif change == "extraPushUrl":
                                self.git(root, "remote", "set-url", "--add", "--push", "origin", str(approved))
                                self.git(root, "remote", "set-url", "--add", "--push", "origin", str(other))
                            elif change == "receivepack":
                                self.git(root, "config", "remote.origin.receivepack", str(executable))
                            elif change == "helper":
                                self.git(root, "config", "remote.origin.vcs", "rogue")
                            else:
                                self.git(root, "config", f"url.{other}.{change}", str(approved))
                        return self.run_git(args, *rest, **kwargs)

                    helper_path = str(programs) + os.pathsep + os.environ["PATH"]
                    with patch.dict(os.environ, {"PATH": helper_path}), patch.object(subprocess, "run", side_effect=race):
                        try:
                            result = self.publish(flow)
                        except git_workflow.Blocked:
                            result = None
                    head = self.git(root, "rev-parse", "HEAD")
                    self.assertNotEqual(head, seed)
                    self.assertFalse(marker.exists(), "The repository selected a foreign transport executable.")
                    self.assertTrue(fired, "The race must occur at the real outgoing Git transport.")
                    self.assertEqual(self.git(other, "rev-parse", "refs/heads/main"), seed)
                    leaked = self.run_git(["git", "cat-file", "-e", head], cwd=other, capture_output=True)
                    self.assertNotEqual(leaked.returncode, 0, "The unrelated remote received commit objects.")
                    if result is not None:
                        self.assertEqual(self.git(approved, "rev-parse", "refs/heads/main"), head)
                        self.assertEqual(result.get("publication", result)["head"], head)

    def test_target_hook_runs_from_owner_and_can_veto_outgoing_commit(self) -> None:
        for module, profile in ((git_workflow, "workspace"), (vault_workflow, "vault")):
            for allow in (False, True):
                with self.subTest(profile=profile, allow=allow):
                    root, approved, _, seed, flow = self.setup_owner(profile + str(allow), module)
                    hooks = root / ".git/hooks"
                    self.git(root, "config", "core.hooksPath", str(hooks))
                    hook = hooks / "pre-push"
                    hook.write_text("#!/bin/sh\n"
                                    "pwd > .git/hook.cwd\n"
                                    'printf "%s\\n" "$1" "$2" > .git/hook.args\n'
                                    "cat > .git/hook.stdin\n"
                                    + ("exit 0\n" if allow else "exit 1\n"))
                    hook.chmod(0o755)
                    guard = nullcontext() if allow else self.assertRaises(git_workflow.Blocked)
                    with guard:
                        self.publish(flow)
                    head = self.git(root, "rev-parse", "HEAD")
                    self.assertNotEqual(head, seed)
                    self.assertEqual(Path((root / ".git/hook.cwd").read_text().strip()), root)
                    self.assertEqual((root / ".git/hook.args").read_text().splitlines(),
                                     ["origin", str(approved)])
                    fields = (root / ".git/hook.stdin").read_text().split()
                    self.assertEqual(fields[1:], [head, "refs/heads/main", seed])
                    self.assertEqual(self.git(approved, "rev-parse", "refs/heads/main"),
                                     head if allow else seed)

    def test_follow_tags_policy_cannot_add_an_undeclared_remote_ref(self) -> None:
        for module, profile in ((git_workflow, "workspace"), (vault_workflow, "vault")):
            with self.subTest(profile=profile):
                root, approved, _, seed, flow = self.setup_owner(profile, module)
                self.git(root, "config", "push.followTags", "true")
                self.git(root, "tag", "-a", "unrequested", "-m", "local-only tag", seed)
                self.publish(flow)
                head = self.git(root, "rev-parse", "HEAD")
                self.assertNotEqual(head, seed)
                self.assertEqual(self.git(approved, "rev-parse", "refs/heads/main"), head)
                self.assertEqual(self.git(approved, "for-each-ref", "--format=%(refname)", "refs/tags"), "")

    def test_verification_reads_the_claimed_destination_when_alias_changes_during_query(self) -> None:
        for module, profile in ((git_workflow, "workspace"), (vault_workflow, "vault")):
            with self.subTest(profile=profile):
                root, approved, other, seed, flow = self.setup_owner(profile, module)
                # Let the decoy already possess the candidate. Its answer must
                # never count as evidence of the approved repository's ref.
                fired = False

                def verify_race(args, *rest, **kwargs):
                    nonlocal fired
                    if not fired and "ls-remote" in args and "--get-url" not in args:
                        # Arm only once the real transfer reached A. Another
                        # writer displaces A's ref concurrently with verification.
                        head = self.git(root, "rev-parse", "HEAD")
                        if head != seed and self.git(approved, "rev-parse", "refs/heads/main") == head:
                            fired = True
                            self.git(root, "push", str(other), head + ":refs/heads/main")
                            self.git(approved, "update-ref", "refs/heads/main", seed, head)
                            self.git(root, "remote", "set-url", "origin", str(other))
                            upload = root.parent / "upload"
                            upload.write_text("#!/bin/sh\nexec git upload-pack " + shlex.quote(str(other)) + "\n")
                            upload.chmod(0o755)
                            self.git(root, "config", "remote.origin.uploadpack", str(upload))
                            try:
                                return self.run_git(args, *rest, **kwargs)
                            finally:
                                self.git(root, "remote", "set-url", "origin", str(approved))
                                self.git(root, "config", "--unset", "remote.origin.uploadpack")
                    return self.run_git(args, *rest, **kwargs)

                with patch.object(subprocess, "run", side_effect=verify_race):
                    with self.assertRaises(git_workflow.Blocked):
                        self.publish(flow)
                self.assertTrue(fired)
                self.assertEqual(self.git(approved, "rev-parse", "refs/heads/main"), seed)

    def test_ordinary_commit_cannot_send_an_unreviewed_ancestor(self) -> None:
        for module, profile in ((git_workflow, "workspace"), (vault_workflow, "vault")):
            with self.subTest(profile=profile):
                root, approved, _, seed, flow = self.setup_owner(profile, module, provider=False)
                (root / "someone-elses.txt").write_text("unreviewed work\n")
                self.git(root, "add", "--", "someone-elses.txt")
                self.git(root, "commit", "-m", "independent work")
                unrelated = self.git(root, "rev-parse", "HEAD")
                with self.assertRaises(git_workflow.Blocked):
                    flow.commit(["answer.txt"], "Publish approved change")
                self.assertEqual(self.git(approved, "rev-parse", "refs/heads/main"), seed)
                self.assertNotEqual(self.run_git(["git", "cat-file", "-e", unrelated], cwd=approved,
                                                 capture_output=True).returncode, 0)
                self.assertEqual((root / "someone-elses.txt").read_text(), "unreviewed work\n")

    def test_local_relative_upstream_keeps_owner_directory_semantics(self) -> None:
        for module, profile in ((git_workflow, "workspace"), (vault_workflow, "vault")):
            with self.subTest(profile=profile):
                root, approved, _, seed, flow = self.setup_owner(profile, module, relative=True)
                self.publish(flow)
                head = self.git(root, "rev-parse", "HEAD")
                self.assertNotEqual(head, seed)
                self.assertEqual(self.git(approved, "rev-parse", "refs/heads/main"), head)

    def test_inline_credentials_rejected_before_transport_and_redacted(self) -> None:
        for module, profile in ((git_workflow, "workspace"), (vault_workflow, "vault")):
            with self.subTest(profile=profile):
                root, _, _, _, flow = self.setup_owner(profile, module)
                token = "synthetic-private-value"
                self.git(root, "remote", "set-url", "origin", f"https://user:{token}@example.invalid/repo")

                def local_only(args, *rest, **kwargs):
                    if any(verb in args for verb in ("fetch", "push", "send-pack", "ls-remote")):
                        self.fail("Attempted to contact a URL carrying inline credentials")
                    return self.run_git(args, *rest, **kwargs)

                with patch.object(subprocess, "run", side_effect=local_only):
                    state = flow.begin("inline-credentials")
                self.assertTrue(state["sync_error"])
                self.assertNotIn(token, state["sync_error"])

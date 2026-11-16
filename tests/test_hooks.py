"""Native hook behavior using real Git owners and a small task-store boundary."""

from __future__ import annotations

from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest

from constellation.hooks import patch_paths, pre_tool, stop, HookError
from constellation.state import Store


class Tasks:
    def __init__(self, tasks):
        self.tasks = tasks

    def list_tasks(self):
        return self.tasks


class HooksTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.task = {"id": "note", "root": str(self.root), "session_id": "session",
                     "coordinator": "session", "assignments": {"note.md": "writer", "renamed.md": "writer"}}
        self.store = Tasks([self.task])

    def payload(self, patch, **changes):
        result = {"session_id": "session", "agent_id": "writer", "cwd": str(self.root),
                  "tool_name": "functions.apply_patch", "tool_input": {"command": patch}}
        result.update(changes)
        return result

    def test_declared_edit_and_both_rename_paths_are_allowed(self):
        patch = "*** Begin Patch\n*** Update File: note.md\n*** Move to: renamed.md\n@@\n-a\n+b\n*** End Patch"
        self.assertEqual(pre_tool(self.payload(patch), self.store), {})
        del self.task["assignments"]["renamed.md"]
        self.assertEqual(pre_tool(self.payload(patch), self.store)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_query_needs_no_task_but_edit_does(self):
        self.assertEqual(pre_tool({"tool_name": "read_file"}, Tasks([])), {})
        patch = "*** Begin Patch\n*** Add File: note.md\n+text\n*** End Patch"
        self.assertIn("hookSpecificOutput", pre_tool(self.payload(patch), Tasks([])))

    def test_other_author_cannot_edit_assigned_path(self):
        patch = "*** Begin Patch\n*** Add File: note.md\n+text\n*** End Patch"
        self.assertIn("hookSpecificOutput", pre_tool(self.payload(patch, agent_id="other"), self.store))
        self.assertEqual(pre_tool(self.payload(patch, agent_id="session"), self.store), {})

    def test_child_native_session_follows_registered_author(self):
        patch = "*** Begin Patch\n*** Add File: note.md\n+text\n*** End Patch"
        self.assertEqual(pre_tool(self.payload(patch, session_id="child-session"), self.store), {})

    def test_task_local_routing_uuid_resolves_to_the_assigned_native_agent(self):
        self.task["actor_sessions"] = {"writer": "writer-uuid", "session": "parent-uuid"}
        patch = "*** Begin Patch\n*** Add File: note.md\n+text\n*** End Patch"
        payload = self.payload(patch, session_id="writer-uuid", agent_id=None)
        self.assertEqual(pre_tool(payload, self.store), {})
        self.assertEqual(stop(payload, self.store)["decision"], "block")
        parent = self.payload(patch, session_id="parent-uuid", agent_id=None)
        self.assertEqual(pre_tool(parent, self.store), {})
        stranger = self.payload(patch, session_id="stranger-uuid", agent_id=None)
        self.assertIn("hookSpecificOutput", pre_tool(stranger, self.store))
        self.assertEqual(stop(stranger, self.store), {})

    def test_parent_session_group_does_not_grant_an_unmapped_actor_write_access(self):
        self.task["session_id"] = "parent-uuid"
        self.task["actor_sessions"] = {"writer": "writer-uuid"}
        patch = "*** Begin Patch\n*** Add File: note.md\n+text\n*** End Patch"
        payload = self.payload(patch, session_id="parent-uuid", agent_id=None)
        self.assertIn("hookSpecificOutput", pre_tool(payload, self.store))
        self.assertEqual(stop(payload, self.store)["decision"], "block")

    def test_conflicting_canonical_label_and_session_are_denied(self):
        self.task["actor_sessions"] = {"writer": "writer-uuid"}
        patch = "*** Begin Patch\n*** Add File: note.md\n+text\n*** End Patch"
        self.assertEqual(pre_tool(self.payload(patch, session_id="writer-uuid"), self.store), {})
        self.assertIn("hookSpecificOutput", pre_tool(self.payload(patch, session_id="other-uuid"), self.store))

    def test_conflicting_routing_uuid_and_session_are_denied(self):
        self.task["actor_sessions"] = {"writer": "writer-uuid"}
        patch = "*** Begin Patch\n*** Add File: note.md\n+text\n*** End Patch"
        matched = self.payload(patch, session_id="writer-uuid", agent_id="writer-uuid")
        self.assertEqual(pre_tool(matched, self.store), {})
        conflict = self.payload(patch, session_id="other-uuid", agent_id="writer-uuid")
        self.assertIn("hookSpecificOutput", pre_tool(conflict, self.store))
        self.assertEqual(stop(conflict, self.store), {})

    def test_native_parent_session_and_child_actor_keep_exact_child_scope(self):
        # Native contract: session_id is the parent session, while agent_id is
        # the subagent's thread UUID (learn.chatgpt.com/docs/hooks).
        self.task["actor_sessions"] = {"writer": "writer-uuid", "sibling": "sibling-uuid"}
        self.task["assignments"]["renamed.md"] = "sibling"
        patch = "*** Begin Patch\n*** Add File: note.md\n+text\n*** End Patch"
        for observed in ("writer", "writer-uuid"):
            with self.subTest(observed=observed):
                payload = self.payload(patch, session_id="session", agent_id=observed)
                self.assertEqual(pre_tool(payload, self.store), {})
                self.assertEqual(stop(payload, self.store)["decision"], "block")
        sibling = self.payload(patch, session_id="session", agent_id="sibling-uuid")
        self.assertIn("hookSpecificOutput", pre_tool(sibling, self.store))
        stranger = self.payload(patch, session_id="unrelated-parent", agent_id="writer-uuid")
        self.assertIn("hookSpecificOutput", pre_tool(stranger, self.store))

    def test_scope_denial_reports_only_bounded_routing_identifiers(self):
        patch = "*** Begin Patch\n*** Add File: note.md\n+private-tool-content\n*** End Patch"
        response = pre_tool(self.payload(patch, session_id="unregistered", agent_id="unknown"), self.store)
        reason = response["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn("session=unregistered actor=unknown", reason)
        self.assertNotIn("private-tool-content", reason)
        self.assertNotIn("note.md", reason)
        response = pre_tool(self.payload(patch, agent_id="private content\n"), self.store)
        self.assertIn("actor=<invalid-id>", response["hookSpecificOutput"]["permissionDecisionReason"])

    def test_actor_mapping_is_scoped_to_its_own_task(self):
        self.task["actor_sessions"] = {"writer": "writer-uuid"}
        unrelated = {**self.task, "id": "unrelated", "root": str(self.root / "other"),
                     "actor_sessions": {"writer": "other-uuid"}}
        self.store.tasks.insert(0, unrelated)
        patch = "*** Begin Patch\n*** Add File: note.md\n+text\n*** End Patch"
        payload = self.payload(patch, session_id="writer-uuid")
        self.assertEqual(pre_tool(payload, self.store), {})
        self.assertIn("note.", stop(payload, self.store)["reason"])
        self.assertNotIn("unrelated", stop(payload, self.store)["reason"])

    def test_ambiguous_and_historical_actor_mappings_do_not_grant_access(self):
        patch = "*** Begin Patch\n*** Add File: note.md\n+text\n*** End Patch"
        payload = self.payload(patch, session_id="old-uuid", agent_id=None)
        self.task["actor_sessions"] = {"writer": "new-uuid"}
        self.task["actor_session_history"] = {"writer": ["old-uuid"]}
        self.assertIn("hookSpecificOutput", pre_tool(payload, self.store))
        self.assertEqual(stop(payload, self.store), {})
        self.task["actor_sessions"] = {"writer": "old-uuid", "session": "old-uuid"}
        self.assertIn("hookSpecificOutput", pre_tool(payload, self.store))

    def test_symlink_and_parent_traversal_are_denied(self):
        (self.root / "linked").symlink_to(self.root, target_is_directory=True)
        self.task["assignments"]["linked/note.md"] = "writer"
        for name in ("linked/note.md", "../note.md"):
            with self.subTest(name=name):
                patch = f"*** Begin Patch\n*** Add File: {name}\n+text\n*** End Patch"
                self.assertIn("hookSpecificOutput", pre_tool(self.payload(patch), self.store))

    def test_nested_repository_requires_its_own_task(self):
        child = self.root / "child"
        subprocess.run(["git", "init", "-q", str(child)], check=True)
        self.task["assignments"]["child/note.md"] = "writer"
        patch = "*** Begin Patch\n*** Add File: child/note.md\n+text\n*** End Patch"
        self.assertIn("hookSpecificOutput", pre_tool(self.payload(patch), self.store))

    def test_conflicting_patch_fields_and_malformed_patch_are_denied(self):
        value = self.payload("*** Begin Patch\n*** Add File: note.md\n+x\n*** End Patch")
        value["tool_input"]["patch"] = "different"
        self.assertIn("hookSpecificOutput", pre_tool(value, self.store))
        with self.assertRaises(HookError):
            patch_paths("*** Begin Patch\n*** Move to: note.md\n*** End Patch")

    def test_destructive_guard_covers_native_shell_aliases(self):
        for tool in ("Bash", "functions.exec_command"):
            for command in ("git reset --hard", "git -C '/tmp/repo' push --force", "rm file",
                            "sudo /bin/rm file", "git clean -fd", "git checkout -- note.md",
                            "git filter-branch --all", "curl https://example.test"):
                with self.subTest(tool=tool, command=command):
                    payload = {"tool_name": tool, "tool_input": {"cmd": command}}
                    self.assertIn("hookSpecificOutput", pre_tool(payload, Tasks([])))
        self.assertEqual(pre_tool({"tool_name": "Bash", "tool_input": {"command": "git status --short"}}, Tasks([])), {})

    def test_stop_reports_pending_once_without_closing(self):
        payload = {"session_id": "session", "cwd": str(self.root)}
        self.assertEqual(stop(payload, self.store)["decision"], "block")
        self.assertIn("systemMessage", stop({**payload, "stop_hook_active": True}, self.store))
        self.assertEqual(len(self.store.tasks), 1)
        self.assertEqual(stop({"session_id": "unrelated"}, self.store), {})
        self.assertEqual(stop(payload, Tasks([])), {})

    def test_hooks_remain_responsive_while_publication_holds_the_ledger_lock(self):
        store = Store(self.root / "state")
        with store._lock():
            store.save_locked({**self.task, "schema": 1, "status": "open"})
            environment = {**os.environ, "CONSTELLATION_STATE_DIR": str(store.root)}
            patch = "*** Begin Patch\n*** Add File: note.md\n+text\n*** End Patch"
            for event, payload in (("pre-tool", self.payload(patch)),
                                   ("stop", {"session_id": "session"})):
                result = subprocess.run(
                    [sys.executable, "-c", f"from constellation.hooks import main; main('{event}')"],
                    input=json.dumps(payload), capture_output=True, text=True,
                    timeout=3, check=True, env=environment,
                )
                response = json.loads(result.stdout)
                self.assertEqual(response, {} if event == "pre-tool" else stop(payload, store))


if __name__ == "__main__":
    unittest.main()

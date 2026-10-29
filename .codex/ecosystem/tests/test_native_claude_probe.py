"""Development regressions for the trusted native acceptance runner.

The candidate below is deliberately separate from this test runner. It only
attempts access to synthetic canaries created by this test, never user data.
"""
from __future__ import annotations

import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import native_claude_probe as probe


class ChildRequestBoundaryTests(unittest.TestCase):
    def server(self) -> probe.LocalReplies:
        with patch.object(probe.http.server.ThreadingHTTPServer, "__init__", return_value=None):
            return probe.LocalReplies(None, None, role="synthetic-role", role_body="synthetic role instructions")

    def request(self, server: probe.LocalReplies, tools: list[object]) -> None:
        handler = object.__new__(probe.ReplyHandler)
        body = json.dumps({"system": [{"text": "synthetic role instructions"}],
                           "messages": [], "tools": [{"name": name} for name in tools]}).encode()
        handler.server = server
        handler.path = "/v1/messages"
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler.respond = lambda *_args, **_kwargs: None
        handler.do_POST()

    def test_every_request_must_be_safe_and_a_later_request_cannot_erase_a_violation(self) -> None:
        for sequence in ((["Read", "Write"], ["Read", "Write", "Bash"]),
                         (["Read", "Write", "Bash"], ["Read", "Write"])):
            with self.subTest(sequence=sequence):
                server = self.server()
                for tools in sequence:
                    self.request(server, tools)
                self.assertEqual(server.child_replies, 2)
                self.assertFalse(server.child_tools_safe)

    def test_multiple_safe_requests_retain_the_boundary(self) -> None:
        server = self.server()
        self.request(server, ["Read", "Write"])
        self.request(server, ["Write"])
        self.request(server, ["Read", "Write", "SubagentHandback"])
        self.assertEqual(server.child_replies, 3)
        self.assertTrue(server.child_tools_safe)

    def test_unknown_capabilities_fail_in_every_position_and_cannot_be_cleared(self) -> None:
        safe = ["Read", "Write"]
        for unknown in ("mcp__fixture__execute", "FutureTool", None, {"unexpected": "shape"}):
            unsafe = ["Read", "Write", unknown]
            for sequence in ((unsafe, safe), (safe, unsafe, safe), (safe, unsafe)):
                with self.subTest(unknown=unknown, sequence=sequence):
                    server = self.server()
                    for tools in sequence:
                        self.request(server, tools)
                    self.assertFalse(server.child_tools_safe)

    def test_known_but_undeclared_capabilities_are_rejected(self) -> None:
        for extra in ("Bash", "PowerShell", "WebFetch", "WebSearch", "Agent", "Task", "Skill", "Glob", "Grep"):
            with self.subTest(extra=extra):
                server = self.server()
                self.request(server, ["Read", "Write", extra])
                self.request(server, ["Read", "Write", "SubagentHandback"])
                self.assertFalse(server.child_tools_safe)


@unittest.skipUnless(sys.platform == "darwin" and Path("/usr/bin/sandbox-exec").is_file(),
                     "Actual macOS sandbox is required; no isolation claim on other platforms")
class PortableCandidateIsolationTests(unittest.TestCase):
    def test_plan_and_status_cannot_read_external_canary_inherit_secret_or_write_outside(self) -> None:
        with tempfile.TemporaryDirectory(prefix="constellation-portable-canary-", dir="/private/tmp") as tmp:
            base = Path(tmp).resolve()
            project = base / "case/project"
            project.mkdir(parents=True)
            candidate = base / "candidate"
            (candidate / "ecosystem").mkdir(parents=True)
            outside = base / "outside"
            outside.mkdir()
            decoy = outside / "decoy.txt"
            decoy.write_text("synthetic external canary")
            escaped = outside / "unexpected.txt"
            script = r'''import json, os
from pathlib import Path
payload = json.load(__import__("sys").stdin)
result = {"ok": True, "inherited_canary": os.environ.get("CONSTELLATION_PROBE_SYNTHETIC_SECRET"),
          "cwd": str(Path.cwd()), "request_received": payload.get("synthetic") == "request"}
try:
    Path(DECOY).read_text()
    result["external_read"] = True
except PermissionError:
    result["external_read"] = False
try:
    Path(ESCAPED).write_text("synthetic unexpected write")
    result["external_write"] = True
except PermissionError:
    result["external_write"] = False
Path("inside.txt").write_text("synthetic allowed write")
print(json.dumps(result))
'''
            script = script.replace("DECOY", repr(str(decoy))).replace("ESCAPED", repr(str(escaped)))
            (candidate / "ecosystem/cli.py").write_text(script)
            with patch.dict(probe.os.environ, {"CONSTELLATION_PROBE_SYNTHETIC_SECRET": "not-for-candidate"}):
                for operation in ("plan", "status"):
                    with self.subTest(operation=operation):
                        result = probe.portable(candidate, project, project.parent / "state", operation,
                                                {"synthetic": "request"})
                        self.assertIsNone(result["inherited_canary"])
                        self.assertFalse(result["external_read"])
                        self.assertFalse(result["external_write"])
                        self.assertEqual(result["cwd"], str(project))
                        self.assertTrue(result["request_received"])
                        self.assertEqual((project / "inside.txt").read_text(), "synthetic allowed write")
                        self.assertFalse(escaped.exists())
            self.assertEqual(decoy.read_text(), "synthetic external canary")


if __name__ == "__main__":
    unittest.main()

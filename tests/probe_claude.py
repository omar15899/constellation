"""Exercise a fresh Claude CLI against synthetic data and a loopback-only API.

The probe installs the real native projection into a temporary home, then uses
scripted Anthropic Messages responses to request two permitted writes and two
forbidden writes. No model provider, credentials, user sessions, or transcripts
are used. The macOS process sandbox prevents all non-loopback network traffic.
This verifies headless discovery and hook execution, not interactive trust.
"""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import tomllib
from typing import Any
from urllib.parse import urlsplit
import uuid

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE))

from constellation.install import apply_plan, build_plan
from constellation.state import Store


def native_names(value: Any) -> set[str]:
    """Read the observed Claude init schema without matching name prefixes."""
    if not isinstance(value, list) or not all(isinstance(name, str) for name in value):
        raise RuntimeError("Unsupported native discovery metadata; expected a list of names")
    return set(value)


class ScriptedAPI:
    """Serve deterministic Messages responses without retaining request bodies."""

    def __init__(self, root: Path, state: Path, role_marker: str):
        self.root = root
        self.state = state
        self.role_marker = role_marker
        self.turns = 0
        self.child_turns = 0
        self.child_id: str | None = None
        self.parent_model: str | None = None
        self.child_model: str | None = None
        self.child_registered = threading.Event()
        self.child_finished = threading.Event()
        self.errors: set[str] = set()
        self.tools: set[str] = set()
        self.denials: set[str] = set()
        self.successes: set[str] = set()
        self.stop_notice = False
        self.synthetic_auth_only = True
        self.lock = threading.Lock()

    def response(self, request: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
        """Select the next synthetic response and collect bounded observations.

        Args:
            request: Parsed local request, discarded when the handler returns.

        Returns:
            Message content blocks and the native stop reason.
        """
        child = self.role_marker in json.dumps(request.get("system", []), ensure_ascii=False)
        with self.lock:
            if child:
                self.child_model = request.get("model")
                self.child_turns += 1
                turn = self.child_turns
            else:
                self.parent_model = request.get("model")
                self.turns += 1
                turn = self.turns
            self.tools.update(tool.get("name", "") for tool in request.get("tools", []))
            for message in request.get("messages", []):
                content = message.get("content", [])
                if isinstance(content, str):
                    content = [{"type": "text", "text": content}]
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if (block.get("type") == "tool_result" and block.get("is_error")
                            and "Constellation:" in json.dumps(block)):
                        self.denials.add(block.get("tool_use_id", ""))
                    if block.get("type") == "tool_result" and not block.get("is_error"):
                        self.successes.add(block.get("tool_use_id", ""))
                    if "Constellation has pending local tasks" in json.dumps(block):
                        self.stop_notice = True
                    if not child and block.get("tool_use_id") == "toolu_child":
                        match = re.search(r'agentId:\s*([a-zA-Z0-9_-]+)', json.dumps(block))
                        if match and self.child_id is None:
                            self.child_id = match.group(1)
                            # Register the ID actually returned by the native
                            # Agent tool before its first write is served.
                            Store(self.state).assign("native-claude-fixture", "child.md",
                                self.child_id, "Native Agent returned this child identifier.")
                            self.child_registered.set()
        if child:
            if turn == 1:
                if not self.child_registered.wait(timeout=15):
                    self.errors.add("child_identifier_not_returned")
                    return [{"type": "text", "text": "Fixture cannot assign this child."}], "end_turn"
                return [
                    {"type": "tool_use", "id": "toolu_child_allowed", "name": "Write",
                     "input": {"file_path": str(self.root / "child.md"), "content": "Child-owned write.\n"}},
                    {"type": "tool_use", "id": "toolu_child_parent", "name": "Write",
                     "input": {"file_path": str(self.root / "parent-only.md"), "content": "Must be denied.\n"}},
                ], "tool_use"
            self.child_finished.set()
            return [{"type": "text", "text": "Synthetic child complete."}], "end_turn"
        if turn == 1:
            # Claude requires reading an existing notebook before editing;
            # satisfy that native prerequisite before testing our guard.
            return [{"type": "tool_use", "id": "toolu_read_" + name, "name": "Read",
                     "input": {"file_path": str(self.root / (name + ".ipynb"))}}
                    for name in ("allowed", "forbidden")], "tool_use"
        if turn == 2:
            return [
                {"type": "tool_use", "id": "toolu_allowed", "name": "Write",
                 "input": {"file_path": str(self.root / "allowed.md"),
                           "content": "Synthetic permitted write.\n"}},
                {"type": "tool_use", "id": "toolu_allowed_notebook", "name": "NotebookEdit",
                 "input": {"notebook_path": str(self.root / "allowed.ipynb"),
                           "new_source": "print('synthetic allowed cell')",
                           "edit_mode": "insert", "cell_type": "code"}},
                {"type": "tool_use", "id": "toolu_forbidden", "name": "Write",
                 "input": {"file_path": str(self.root / "forbidden.md"),
                           "content": "This write must be denied.\n"}},
                {"type": "tool_use", "id": "toolu_notebook", "name": "NotebookEdit",
                 "input": {"notebook_path": str(self.root / "forbidden.ipynb"),
                           "new_source": "raise RuntimeError('must not be written')",
                           "edit_mode": "insert", "cell_type": "code"}},
                {"type": "tool_use", "id": "toolu_selector_match", "name": "Bash",
                 "input": {"command": "printf 'synthetic selector\\n'"}},
                {"type": "tool_use", "id": "toolu_selector_other", "name": "Bash",
                 "input": {"command": "true"}},
            ], "tool_use"
        if turn == 3:
            return [{"type": "tool_use", "id": "toolu_child", "name": "Agent", "input": {
                "description": "Verify synthetic child scope", "prompt": "Verify only synthetic child ownership.",
                "subagent_type": "ecosystem_coder", "run_in_background": True}}], "tool_use"
        if turn == 4 and not self.child_finished.wait(timeout=20):
            self.errors.add("child_did_not_finish")
        return [{"type": "text", "text": "Synthetic fixture complete."}], "end_turn"


class LaunchFailureAPI(ScriptedAPI):
    """Request one write when the native hook executable is unavailable."""

    def __init__(self, root: Path, state: Path):
        super().__init__(root, state, "unused-failure-fixture-role")
        self.transport_denied = False

    def response(self, request: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
        """Observe the native transport rejection, without a working hook body."""
        self.turns += 1
        for message in request.get("messages", []):
            content = message.get("content", [])
            if not isinstance(content, list):
                continue
            for block in content:
                if (isinstance(block, dict) and block.get("tool_use_id") == "toolu_failure"
                        and block.get("is_error") and "hook" in json.dumps(block).lower()):
                    self.transport_denied = True
        if self.turns == 1:
            return [{"type": "tool_use", "id": "toolu_failure", "name": "Write",
                     "input": {"file_path": str(self.root / "failure.md"),
                               "content": "A missing hook must block this write.\n"}}], "tool_use"
        return [{"type": "text", "text": "Synthetic transport fixture complete."}], "end_turn"


def _events(blocks: list[dict[str, Any]], reason: str) -> bytes:
    """Encode one minimal streaming Messages response with native events."""
    events: list[tuple[str, dict[str, Any]]] = [("message_start", {
        "type": "message_start", "message": {"id": "msg_synthetic", "type": "message",
        "role": "assistant", "model": "claude-sonnet-4-6", "content": [],
        "stop_reason": None, "stop_sequence": None,
        "usage": {"input_tokens": 1, "output_tokens": 1}}})]
    for index, block in enumerate(blocks):
        initial = ({**block, "input": {}} if block["type"] == "tool_use"
                   else {"type": "text", "text": ""})
        events.append(("content_block_start", {"type": "content_block_start",
                                              "index": index, "content_block": initial}))
        delta = ({"type": "input_json_delta", "partial_json": json.dumps(block["input"])}
                 if block["type"] == "tool_use" else {"type": "text_delta", "text": block["text"]})
        events.append(("content_block_delta", {"type": "content_block_delta",
                                              "index": index, "delta": delta}))
        events.append(("content_block_stop", {"type": "content_block_stop", "index": index}))
    events.extend([
        ("message_delta", {"type": "message_delta", "delta": {"stop_reason": reason,
         "stop_sequence": None}, "usage": {"output_tokens": 10}}),
        ("message_stop", {"type": "message_stop"}),
    ])
    return "".join(f"event: {name}\ndata: {json.dumps(value)}\n\n"
                   for name, value in events).encode()


def _handler(api: ScriptedAPI) -> type[BaseHTTPRequestHandler]:
    """Build a localhost-only test handler that never logs raw requests."""
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args: Any) -> None:
            pass

        def do_POST(self) -> None:
            api.synthetic_auth_only = (api.synthetic_auth_only
                and self.headers.get("x-api-key") == "synthetic-local-fixture-key")
            length = int(self.headers.get("Content-Length", "0"))
            if length > 8_000_000:
                self.send_error(413)
                return
            request = json.loads(self.rfile.read(length))
            path = urlsplit(self.path).path
            if path.endswith("/messages/count_tokens"):
                content, mime = b'{"input_tokens":1}', "application/json"
            elif path.endswith("/messages"):
                blocks, reason = api.response(request)
                if request.get("stream"):
                    content, mime = _events(blocks, reason), "text/event-stream"
                else:
                    content = json.dumps({"id": "msg_synthetic", "type": "message",
                        "role": "assistant", "model": "claude-sonnet-4-6", "content": blocks,
                        "stop_reason": reason, "stop_sequence": None,
                        "usage": {"input_tokens": 1, "output_tokens": 10}}).encode()
                    mime = "application/json"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

    return Handler


def _fixture(source: Path, temporary: Path) -> tuple[Path, Path, Path, list[str], list[str]]:
    """Install actual code and canonical role/skill inputs in an isolated home.

    The fixture registry names only its temporary repository, so the normal
    installer cannot touch the user's registered repositories or settings.
    """
    fixture_source, home, root = (temporary / name for name in ("source", "home", "repo"))
    state = temporary / "state"
    for directory in (fixture_source, home, root, state):
        directory.mkdir()
    for name in ("constellation", "agents", "git-hooks"):
        shutil.copytree(source / name, fixture_source / name,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copy2(source / "constellation.py", fixture_source / "constellation.py")
    for name in ("instructions", "profiles", "skills"):
        (fixture_source / name).mkdir()
    (fixture_source / "instructions/AGENTS.md").write_text("Use only synthetic fixture data.\n")
    (fixture_source / "profiles/fixture.md").write_text("Synthetic repository profile.\n")
    (fixture_source / "profiles/projects.json").write_text(json.dumps({"projects": [{
        "id": "fixture", "root": str(root), "management": "native",
        "profile": "profiles/fixture.md", "private_patterns": []}]}))
    rows = [row for row in json.loads((source / "resource-inventory.json").read_text())["entries"]
            if row["group"] == "core"]
    for row in rows:
        destination = fixture_source / row["destination"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.symlink_to(source / row["destination"], target_is_directory=True)
    (fixture_source / "resource-inventory.json").write_text(json.dumps({"entries": rows}))
    subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
    (root / "baseline.md").write_text("Synthetic baseline.\n")
    notebook = {"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}
    for name in ("allowed.ipynb", "forbidden.ipynb"):
        (root / name).write_text(json.dumps(notebook) + "\n")
    subprocess.run(["git", "-C", str(root), "add", "baseline.md"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.name=Fixture", "-c",
                    "user.email=fixture@example.invalid", "-c", "core.hooksPath=/dev/null",
                    "commit", "-qm", "Create synthetic fixture"], check=True, capture_output=True)
    apply_plan(build_plan(fixture_source, home, state))
    # Exercise a project-owned hook's current native conditional selector with
    # harmless shell commands. It must not run for the unrelated Bash command.
    selector = temporary / "selector.py"
    selector.write_text(
        "import json,sys\nfrom pathlib import Path\n"
        "payload=json.load(sys.stdin)\n"
        "matched=payload.get('tool_input', {}).get('command', '').startswith('printf ')\n"
        "with Path(sys.argv[1]).open('a') as receipt:\n"
        "    receipt.write('match\\n' if matched else 'unexpected\\n')\n"
        "print('{}')\n")
    settings = root / ".claude/settings.json"
    settings.parent.mkdir(exist_ok=True)
    settings.write_text(json.dumps({"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{
        "type": "command", "command": sys.executable,
        "args": [str(selector), str(state / "selector.txt")],
        "if": "Bash(printf *)", "timeout": 10, "onFailure": "block"}]}]}}))
    roles = [tomllib.loads(path.read_text())["name"] for path in (source / "agents").glob("*.toml")]
    return home, root, state, sorted(roles), sorted(row["name"] for row in rows)


def _launch_failure(home: Path, root: Path, state: Path, command: list[str],
                    environment: dict[str, str], timeout: float) -> dict[str, Any]:
    """Verify the installed fail-closed setting in another fresh native process.

    Only the synthetic home's hook executable reference changes. The native
    onFailure setting must prevent a write even though no hook can return JSON.
    """
    settings = home / ".claude/settings.json"
    value = json.loads(settings.read_text())
    handler = value["hooks"]["PreToolUse"][0]["hooks"][0]
    configured = handler.get("onFailure") == "block"
    handler["command"] = str(root / "missing-hook-executable")
    handler.pop("args", None)
    settings.write_text(json.dumps(value))
    api = LaunchFailureAPI(root, state)
    server = ThreadingHTTPServer(("127.0.0.1", 0), _handler(api))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    arguments = list(command)
    arguments[arguments.index("--session-id") + 1] = str(uuid.uuid4())
    isolated_env = {**environment, "ANTHROPIC_BASE_URL": f"http://127.0.0.1:{server.server_port}"}
    try:
        process = subprocess.run(arguments, cwd=root, env=isolated_env, text=True,
                                 capture_output=True, timeout=timeout)
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
    result = {"configured_to_block": configured, "native_error_observed": api.transport_denied,
              "write_absent": not (root / "failure.md").exists(), "exit_code": process.returncode,
              "native_requests": api.turns, "synthetic_auth_only": api.synthetic_auth_only}
    result["ok"] = (configured and api.transport_denied and result["write_absent"]
                    and process.returncode == 0 and api.turns == 2 and api.synthetic_auth_only)
    return result


def probe(source: Path, executable: str, timeout: float = 60) -> dict[str, Any]:
    """Run isolated native discovery and behavior checks, returning metadata only.

    Args:
        source: Current Constellation candidate, including installer changes.
        executable: Installed Claude Code executable name or absolute path.
        timeout: Maximum duration for the one native Claude process.

    Returns:
        Bounded observations and an aggregate ``ok`` verdict.

    Raises:
        RuntimeError: The required native executable or network isolation is absent.
        subprocess.TimeoutExpired: Native execution exceeds the bounded duration.
    """
    claude = shutil.which(executable)
    sandbox = shutil.which("sandbox-exec")
    if not claude or not sandbox or sys.platform != "darwin":
        raise RuntimeError("This native probe requires Claude Code and macOS sandbox-exec")
    if any(name in os.environ for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR")):
        raise RuntimeError("Unset Git path overrides before creating the isolated fixture")
    version = subprocess.check_output([claude, "--version"], text=True, timeout=10).strip()
    with tempfile.TemporaryDirectory(prefix="constellation-claude-probe-") as folder:
        temporary = Path(folder).resolve()
        home, root, state, roles, skills = _fixture(source.resolve(), temporary)
        session = str(uuid.uuid4())
        Store(state).begin("native-claude-fixture", root,
            "Only the assigned Markdown and notebook may be written by this synthetic session.",
            {"allowed.md": session, "allowed.ipynb": session, "child.md": session,
             "parent-only.md": session}, coordinator=session, session_id=session,
            mode="local", required_checks=["fixture"])
        notebook_before = (root / "forbidden.ipynb").read_bytes()
        role = tomllib.loads((source / "agents/coder.toml").read_text())
        role_marker = role["developer_instructions"].strip().splitlines()[0]
        api = ScriptedAPI(root, state, role_marker)
        server = ThreadingHTTPServer(("127.0.0.1", 0), _handler(api))
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        environment = {
            "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
            "HOME": str(home), "TMPDIR": str(temporary), "LANG": "en_US.UTF-8",
            "CLAUDE_CODE_TMPDIR": str(temporary / "native-tmp"),
            "CLAUDE_CONFIG_DIR": str(home / ".claude"),
            "CONSTELLATION_STATE_DIR": str(state), "PYTHONDONTWRITEBYTECODE": "1",
            "ANTHROPIC_BASE_URL": f"http://127.0.0.1:{server.server_port}",
            "ANTHROPIC_API_KEY": "synthetic-local-fixture-key",
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
            "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1", "DISABLE_AUTOUPDATER": "1",
            "DISABLE_ERROR_REPORTING": "1", "DISABLE_TELEMETRY": "1",
        }
        network_policy = ('(version 1) (allow default) (deny network*) '
                          '(allow network-outbound (remote ip "localhost:*"))')
        command = [sandbox, "-p", network_policy, claude, "-p",
            "Run the synthetic Constellation fixture.", "--session-id", session,
            "--no-session-persistence", "--strict-mcp-config", "--no-chrome",
            "--setting-sources", "user,project", "--include-hook-events",
            "--output-format", "stream-json", "--verbose", "--permission-mode", "acceptEdits",
            "--permission-prompts", "none", "--tools", "Read,Write,NotebookEdit,Agent,Skill,Bash",
            "--allowedTools", "Bash(printf *)", "Bash(true)",
            "--model", "claude-sonnet-4-6"]
        try:
            process = subprocess.run(command, cwd=root, env=environment, text=True,
                                     capture_output=True, timeout=timeout)
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=5)
        events = []
        for line in process.stdout.splitlines():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        initialization = next((event for event in events if event.get("type") == "system"
                               and event.get("subtype") == "init"), {})
        known_roles = native_names(initialization.get("agents", []))
        known_skills = native_names(initialization.get("skills", initialization.get("slash_commands", [])))
        selector_receipt = state / "selector.txt"
        selector_lines = selector_receipt.read_text().splitlines() if selector_receipt.exists() else []
        selector_ok = (selector_lines == ["match"]
                       and {"toolu_selector_match", "toolu_selector_other"} <= api.successes)
        hook_events = [event for event in events if str(event.get("subtype", "")).startswith("hook_")]
        stop_sequence = []
        for event in hook_events:
            if event.get("subtype") == "hook_response" and event.get("hook_event") == "Stop":
                try:
                    decision = json.loads(event.get("stdout", ""))
                except (ValueError, TypeError):
                    decision = {}
                stop_sequence.append("block" if decision.get("decision") == "block" else
                                     "advisory" if decision.get("systemMessage") else "unknown")
        # A background child notification can start one further parent turn;
        # each stop cycle must block once and then permit its continuation.
        stop_bounded = stop_sequence in (["block", "advisory"], ["block", "advisory"] * 2)
        result = {"fresh_process": True, "isolated_home": True, "network": "loopback_only",
            "version": version, "exit_code": process.returncode,
            "interactive_trust": "not_checked", "native_requests": api.turns,
            "child_requests": api.child_turns, "native_child_id_returned": api.child_id is not None,
            "child_inherits_model": api.child_model is not None and api.child_model == api.parent_model,
            "child_write": (root / "child.md").exists(),
            "child_parent_path_denied": not (root / "parent-only.md").exists(),
            "errors": sorted(api.errors),
            "synthetic_auth_only": api.synthetic_auth_only,
            "roles_present": {name: name in known_roles for name in roles},
            "skills_present": {name: name in known_skills for name in skills},
            "project_hook_selector": {"matching_calls": selector_lines.count("match"),
                "unexpected_calls": selector_lines.count("unexpected"),
                "both_shell_commands_executed": {"toolu_selector_match", "toolu_selector_other"} <= api.successes,
                "ok": selector_ok},
            "allowed_write": (root / "allowed.md").exists(),
            "foreign_write_absent": not (root / "forbidden.md").exists(),
            "allowed_notebook_changed": (root / "allowed.ipynb").read_bytes() != notebook_before,
            "foreign_notebook_unchanged": (root / "forbidden.ipynb").read_bytes() == notebook_before,
            "denied_tool_ids": sorted(api.denials), "stop_notice_seen": api.stop_notice,
            "stop_sequence": stop_sequence, "stop_bounded": stop_bounded,
            "hook_events": len(hook_events),
            "task_remains_open": Store(state).get("native-claude-fixture")["status"] == "open"}
        result["ok"] = (process.returncode == 0 and api.synthetic_auth_only and len(roles) == 8
            and all(result["roles_present"].values()) and all(result["skills_present"].values())
            and result["allowed_write"] and result["foreign_write_absent"]
            and result["allowed_notebook_changed"] and result["foreign_notebook_unchanged"]
            and {"toolu_forbidden", "toolu_notebook", "toolu_child_parent"} <= api.denials
            and result["child_write"] and result["child_parent_path_denied"]
            and result["child_inherits_model"] and stop_bounded and selector_ok
            and api.child_id is not None and api.child_turns == 2 and not api.errors
            and api.stop_notice and 5 <= api.turns <= 7 and bool(hook_events)
            and result["task_remains_open"])
        result["hook_launch_failure"] = _launch_failure(home, root, state, command, environment, timeout)
        result["ok"] = result["ok"] and result["hook_launch_failure"]["ok"]
        return result


def main() -> int:
    """Print only safe metadata; do not write native prompt or event archives."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--claude", default="claude")
    parser.add_argument("--timeout", type=float, default=60)
    arguments = parser.parse_args()
    try:
        result = probe(arguments.source, arguments.claude, arguments.timeout)
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        result = {"ok": False, "error_type": type(error).__name__,
                  "error": "Isolated native probe could not complete; no live session was changed."}
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

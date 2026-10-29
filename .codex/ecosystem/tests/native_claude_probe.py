#!/usr/bin/env python3
"""Opt-in Claude CLI acceptance probe using synthetic, loopback-only responses.

This is not a model benchmark or an interactive trust certificate. It never
invokes Agent: native subagent dispatch remains outside this probe's evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import http.server
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import tomllib
from typing import Any
import uuid

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build import verify_bundle  # noqa: E402
from claude import install_bundle, verify_installation  # noqa: E402


class ProbeError(RuntimeError):
    """A synthetic acceptance obligation failed."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ProbeError(message)


def run(command: list[str], root: Path, env: dict[str, str], timeout: int = 45) -> subprocess.CompletedProcess[str]:
    process = subprocess.Popen(command, cwd=root, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        raise ProbeError("Native process exceeded its bounded deadline.") from exc
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


def environment(home: Path, config: Path, temporary: Path) -> dict[str, str]:
    # Do not inherit account credentials, proxy variables or parent customization.
    search = [str(Path(sys.executable).resolve().parent), "/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin"]
    return {"PATH": os.pathsep.join(dict.fromkeys(search)), "HOME": str(home),
            "CLAUDE_CONFIG_DIR": str(config), "TMPDIR": str(temporary), "TERM": "dumb",
            "XDG_CONFIG_HOME": str(temporary / "xdg"), "XDG_CACHE_HOME": str(temporary / "cache"),
            "DISABLE_TELEMETRY": "1", "DISABLE_ERROR_REPORTING": "1",
            "DISABLE_FEEDBACK_COMMAND": "1", "CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY": "1",
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1", "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"}


def sandbox(cli: Path, port: int | None = None) -> str:
    policy = (f"(version 1)(allow default)(deny network*)"
              f"(deny file-read* (subpath {json.dumps(str(Path.home().resolve()))}))"
              f"(allow file-read* (literal {json.dumps(str(cli))}))"
              '(deny mach-lookup (global-name "com.apple.securityd"))'
              '(deny mach-lookup (global-name "com.apple.securityd.xpc"))')
    if port is not None:
        policy += f'(allow network-outbound (remote ip "localhost:{port}"))'
    return policy


def metadata(cli: Path, args: list[str], root: Path, env: dict[str, str]) -> Any:
    result = run(["/usr/bin/sandbox-exec", "-p", sandbox(cli), str(cli), *args], root, env)
    require(result.returncode == 0, "Native plugin metadata validation failed.")
    try:
        return json.loads(result.stdout)
    except ValueError as exc:
        raise ProbeError("Native metadata response was not JSON.") from exc


def plan(project: Path, state: Path, session: str, profile: str) -> None:
    from ecosystem.core import Engine
    command = [sys.executable, "-I", "-B", "-c", "raise SystemExit(0)"]
    digest = hashlib.sha256(json.dumps(command, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    Engine(project, state).execute("plan", {
        "session_id": "claude-" + session, "task_id": "synthetic-native-probe",
        "agent_id": "synthetic-probe-coordinator", "expected_revision": 0,
        "requirements": [{"id": "r1", "text": "Synthetic output has independent evidence.",
                          "deliverables": ["result.md"], "checks": ["c1"], "acceptance": "editorial"}],
        "deliverables": [{"path": "result.md", "profiles": [profile]}],
        "checks": [{"id": "c1", "kind": "editorial", "definition_sha256": digest}],
        "inputs": [], "depends_on": [], "risk": "quick",
        "agents": [{"agent_id": "synthetic-probe-reviewer", "role": "reviewer"}],
    })


class LocalReplies(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, target: Path | None, fail_entry: Path | None) -> None:
        super().__init__(("127.0.0.1", 0), ReplyHandler)
        self.target, self.fail_entry = target, fail_entry
        self.requests = 0
        self.bootstrap = False
        self.scope_rejected = False


class ReplyHandler(http.server.BaseHTTPRequestHandler):
    server: LocalReplies

    def log_message(self, *_: Any) -> None:
        pass

    def respond(self, value: bytes, kind: str = "application/json") -> None:
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(value)))
        self.end_headers()
        self.wfile.write(value)

    def do_GET(self) -> None:
        self.respond(b"{}")

    def do_POST(self) -> None:
        # Request content is used only in memory, never retained or logged.
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        if "count_tokens" in self.path:
            self.respond(b'{"input_tokens":100}')
            return
        self.server.requests += 1
        self.server.bootstrap |= "Constellation shared research environment" in json.dumps(body)
        for message in body.get("messages", []):
            for item in message.get("content", []) if isinstance(message.get("content"), list) else []:
                if isinstance(item, dict) and item.get("type") == "tool_result":
                    self.server.scope_rejected |= "outside the registered scope" in str(item.get("content", ""))
        first = self.server.requests == 1
        if first and self.server.fail_entry is not None:
            # Only the caller's disposable negative-case copy is altered.
            self.server.fail_entry.write_text("raise SystemExit(17)\n")
        block = ({"type": "tool_use", "id": "toolu_synthetic_probe", "name": "Write",
                  "input": {"file_path": str(self.server.target), "content": "synthetic fixture\n"}}
                 if first and self.server.target is not None else
                 {"type": "text", "text": "Synthetic local verification complete."})
        stop = "tool_use" if block["type"] == "tool_use" else "end_turn"
        message = {"id": "msg_synthetic_probe", "type": "message", "role": "assistant",
                   "content": [block], "model": body.get("model"), "stop_reason": stop,
                   "stop_sequence": None, "usage": {"input_tokens": 100, "output_tokens": 12}}
        if not body.get("stream"):
            self.respond(json.dumps(message).encode())
            return
        initial = {**message, "content": [], "stop_reason": None,
                   "usage": {"input_tokens": 100, "output_tokens": 0}}
        content = {**block, "input": {}} if stop == "tool_use" else {"type": "text", "text": ""}
        delta = ({"type": "input_json_delta", "partial_json": json.dumps(block["input"])}
                 if stop == "tool_use" else {"type": "text_delta", "text": block["text"]})
        events = [("message_start", {"type": "message_start", "message": initial}),
                  ("content_block_start", {"type": "content_block_start", "index": 0, "content_block": content}),
                  ("content_block_delta", {"type": "content_block_delta", "index": 0, "delta": delta}),
                  ("content_block_stop", {"type": "content_block_stop", "index": 0}),
                  ("message_delta", {"type": "message_delta", "delta": {"stop_reason": stop, "stop_sequence": None},
                                     "usage": {"output_tokens": 12}}),
                  ("message_stop", {"type": "message_stop"})]
        self.respond("".join(f"event: {event}\ndata: {json.dumps(value)}\n\n" for event, value in events).encode(),
                     "text/event-stream")


def probe(cli: Path, bundle: Path, root: Path, modules: list[str], skills: set[str], agents: set[str],
          case: str, *, config: Path | None = None) -> dict[str, Any]:
    root.mkdir()
    project, home = root / "project", root / "home"
    project.mkdir(); home.mkdir()
    config = config if config is not None else root / "config"
    config.mkdir(exist_ok=True)
    write = case != "bootstrap"
    target = project / ("forbidden.md" if case in {"undeclared-write", "installed-autoload"} else "result.md")
    session = str(uuid.uuid4())
    if write:
        plan(project, root / "state", session, modules[0])
    server = LocalReplies(target if write else None,
                          bundle / "ecosystem/claude_hooks.py" if case == "process-failure" else None)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        env = environment(home, config, root)
        env.update(ANTHROPIC_BASE_URL=f"http://127.0.0.1:{server.server_port}",
                   ANTHROPIC_API_KEY="synthetic-local-only-key", CONSTELLATION_STATE_DIR=str(root / "state"))
        args = [str(cli), "-p", "Perform the synthetic local verification.", "--session-id", session,
                "--no-session-persistence", "--setting-sources", "user,project" if case == "installed-autoload" else "project",
                "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}', "--settings", '{"autoMemoryEnabled":false}',
                "--model", "claude-sonnet-4-6", "--output-format", "stream-json", "--verbose",
                "--include-hook-events", "--max-turns", "4", "--tools", "Read,Write" if write else "",
                "--allowedTools", "Read,Write"]
        if case != "installed-autoload":
            args += ["--plugin-dir", str(bundle)]
        result = run(["/usr/bin/sandbox-exec", "-p", sandbox(cli, server.server_port), *args], project, env)
        rows = []
        for line in result.stdout.splitlines():
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
        initial = next((row for row in rows if row.get("subtype") == "init"), {})
        require(result.returncode == 0, f"{case}: native CLI failed.")
        require(skills <= set(initial.get("skills", [])), f"{case}: shared skills missing.")
        require(agents <= set(initial.get("agents", [])), f"{case}: native agents missing.")
        require(any(item.get("name") == "constellation" for item in initial.get("plugins", [])), f"{case}: plugin missing.")
        require(server.bootstrap, f"{case}: shared context was not delivered.")
        hooks = [row for row in rows if row.get("subtype") == "hook_response"]
        for event in ("SessionStart", "UserPromptSubmit"):
            require(any(row.get("hook_event") == event and row.get("exit_code") == 0 for row in hooks),
                    f"{case}: {event} did not run successfully.")
        decisions = [json.loads(row.get("stdout") or "{}") for row in hooks if row.get("hook_event") == "Stop"]
        continuations = sum(item.get("decision") == "block" for item in decisions)
        if case == "declared-write":
            require(target.is_file() and target.read_text() == "synthetic fixture\n", "Declared Write did not succeed.")
        elif write:
            require(not target.exists(), f"{case}: a forbidden write occurred.")
        if case in {"undeclared-write", "installed-autoload"}:
            require(server.scope_rejected, f"{case}: shared scope denial was not observed.")
        if write and case != "process-failure":
            require(continuations == 2, f"{case}: Stop continuation budget was not enforced.")
            require(any("INCOMPLETE" in item.get("systemMessage", "") for item in decisions),
                    f"{case}: unfinished work was not reported.")
        if case == "process-failure":
            require(any(row.get("hook_event") == "PreToolUse" and row.get("exit_code") == 17 for row in hooks),
                    "The native operational-failure case did not execute.")
        return {"case": case, "passed": True, "local_requests": server.requests,
                "skills": len(skills), "agents": len(agents), "target_created": target.exists(),
                "scope_rejected": server.scope_rejected, "stop_continuations": continuations,
                "events": sorted({row.get("hook_event") for row in hooks})}
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=3)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--claude", default="claude")
    args = parser.parse_args()
    executable = shutil.which(args.claude)
    if sys.platform != "darwin" or not Path("/usr/bin/sandbox-exec").is_file() or executable is None:
        print(json.dumps({"status": "unavailable", "passed": False,
                          "reason": "Requires macOS sandbox-exec and an installed Claude CLI; no test was run."}))
        return 77
    try:
        source = args.bundle.resolve(strict=True)
        manifest = verify_bundle(source)
        cli = Path(executable).resolve(strict=True)
        skills = {"constellation:" + module for module in manifest["modules"]}
        anchor = Path("/private/tmp").resolve(strict=True)
        require(anchor.is_dir() and not anchor.is_relative_to(Path.home().resolve()),
                "Native verification requires temporary storage outside real HOME.")
        with tempfile.TemporaryDirectory(prefix="constellation-native-acceptance-", dir=anchor) as temporary:
            root = Path(temporary).resolve()
            # Keep HOME denied even when the user extracts the release there.
            # Preserve any racing symlink so verification rejects it without
            # following it into an unrelated file during the copy.
            bundle = root / "release"
            shutil.copytree(source, bundle, symlinks=True)
            require(verify_bundle(bundle) == manifest, "Release changed while creating its isolated copy.")
            agents = {"constellation:" + tomllib.loads((bundle / path).read_text())["name"].replace("_", "-")
                      for path in manifest["files"] if path.startswith("ecosystem/agents/")}
            home, config = root / "home", root / "Claude home with spaces"
            home.mkdir(); config.mkdir()
            env = environment(home, config, root)
            require(metadata(cli, ["plugin", "validate", "--strict", "--json", str(bundle)], root, env).get("success"),
                    "Strict native plugin validation failed.")
            first, second = install_bundle(bundle, config), install_bundle(bundle, config)
            require(first["status"] == "installed" and second["status"] == "unchanged", "Repeat install was not idempotent.")
            installed = config / "skills/constellation"
            verify_installation(installed)
            plugins = metadata(cli, ["plugin", "list", "--json"], root, env)
            require(any(item.get("id") == "constellation@skills-dir" and item.get("enabled") for item in plugins),
                    "Native skills-directory plugin discovery failed.")
            results = [probe(cli, bundle, root / case, manifest["modules"], skills, agents, case)
                       for case in ("bootstrap", "declared-write", "undeclared-write")]
            results.append(probe(cli, installed, root / "autoload", manifest["modules"], skills, agents,
                                 "installed-autoload", config=config))
            broken = root / "negative-release"
            shutil.copytree(bundle, broken)
            results.append(probe(cli, broken, root / "failure", manifest["modules"], skills, agents, "process-failure"))
        print(json.dumps({"passed": True, "native_schema_valid": True, "native_plugin_auto_discovered": True,
                          "repeat_install_unchanged": True, "cases": results, "actual_subagent_events_verified": False,
                          "isolation": "Synthetic local responses; external network and real HOME/Keychain reads denied."}))
        return 0
    except Exception as exc:
        print(json.dumps({"passed": False, "error": str(exc) if isinstance(exc, ProbeError) else type(exc).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

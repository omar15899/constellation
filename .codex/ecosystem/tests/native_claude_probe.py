#!/usr/bin/env python3
"""Opt-in Claude CLI acceptance probe using synthetic, loopback-only responses.

This is not a model benchmark or an interactive trust certificate. Native
subagent cases use one foreground Agent with only restricted file tools.
Requests and native output are inspected in memory and never saved.
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
import re
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


CASES = ("bootstrap", "declared-write", "undeclared-write", "installed-autoload",
         "process-failure", "subagent-declared-write", "subagent-undeclared-write")
SUBAGENT_TASK = "Perform the single synthetic file-tool check assigned by the isolated acceptance probe."
# Claude injects SubagentHandback to return the child result to its parent.
# It grants no extra file, execution, network or delegation capability.
ALLOWED_CHILD_TOOLS = frozenset({"Read", "Write", "SubagentHandback"})


class ProbeError(RuntimeError):
    """A synthetic acceptance obligation failed."""


class ProbeUnavailable(ProbeError):
    """A native dependency cannot be replaced by a synthetic decision."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ProbeError(message)


def run(command: list[str], root: Path, env: dict[str, str], timeout: int = 45,
        *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    process = subprocess.Popen(command, cwd=root, env=env,
                               stdin=subprocess.PIPE if input_text is not None else subprocess.DEVNULL,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        stdout, stderr = process.communicate(input=input_text, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        raise ProbeError("Native process exceeded its bounded deadline.") from exc
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


def environment(home: Path, config: Path, temporary: Path) -> dict[str, str]:
    # Do not inherit account credentials, proxy variables or parent customization.
    search = [str(Path(sys.executable).resolve().parent), "/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin"]
    return {"PATH": os.pathsep.join(dict.fromkeys(search)), "HOME": str(home),
            "CLAUDE_CONFIG_DIR": str(config), "TMPDIR": str(temporary),
            "CLAUDE_CODE_TMPDIR": str(temporary), "TERM": "dumb",
            "XDG_CONFIG_HOME": str(temporary / "xdg"), "XDG_CACHE_HOME": str(temporary / "cache"),
            "DISABLE_TELEMETRY": "1", "DISABLE_ERROR_REPORTING": "1",
            "DISABLE_FEEDBACK_COMMAND": "1", "CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY": "1",
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1", "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1",
            "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1", "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS": "1"}


def python_runtime_libraries() -> tuple[Path, ...]:
    """Allow exact images loaded by the trusted interpreter, including SQLite.

    Homebrew can link standard-library extensions outside sys.base_prefix.
    Inspecting loaded images avoids granting access to entire package prefixes
    or requiring developer-tool installation merely to discover dependencies.
    """
    import ctypes
    import sqlite3  # noqa: F401  -- initialize the candidate CLI's standard SQLite dependency

    process = ctypes.CDLL(None)
    count = process._dyld_image_count
    count.argtypes, count.restype = [], ctypes.c_uint32
    name = process._dyld_get_image_name
    name.argtypes, name.restype = [ctypes.c_uint32], ctypes.c_char_p
    return tuple(Path(os.fsdecode(value)).resolve() for index in range(count())
                 if (value := name(index)) and os.path.isabs(os.fsdecode(value)))


def sandbox(executable: Path, writable: Path, port: int | None = None,
            *, candidate: Path | None = None) -> str:
    policy = ("(version 1)(allow default)(deny network*)(deny file-write*)"
              f"(allow file-write* (subpath {json.dumps(str(writable.resolve()))}))"
              '(allow file-write* (literal "/dev/null"))'
              '(deny file-write* (regex "\\.jsonl$"))'
              '(deny mach-lookup (global-name "com.apple.securityd"))'
              '(deny mach-lookup (global-name "com.apple.securityd.xpc"))')
    if candidate is None:
        # The installed Claude executable is a trusted input. Retain its tested
        # OS runtime access while excluding the real user's data and keychain.
        policy += (f"(deny file-read* (subpath {json.dumps(str(Path.home().resolve()))}))"
                   f"(allow file-read* (literal {json.dumps(str(executable.resolve()))}))")
    else:
        # Bundle integrity does not make candidate code trusted. Plan/status
        # get only runtime code and the runner's explicit disposable inputs.
        system_roots = ("/System", "/usr/lib", "/usr/bin", "/usr/sbin", "/usr/libexec",
                        "/usr/share", "/bin", "/sbin", "/Library/Apple")
        read_roots = [Path(value) for value in system_roots]
        read_roots.extend((Path(sys.base_prefix).resolve(), writable.resolve(), candidate.resolve()))
        read_rules = "".join(f"(subpath {json.dumps(str(path.resolve()))})" for path in read_roots)
        library_rules = "".join(f"(literal {json.dumps(str(path))})" for path in python_runtime_libraries())
        policy += ("(deny file-read*)(allow file-read-metadata)"
                   f'(allow file-read-data (literal "/") {read_rules} {library_rules}'
                   f"(literal {json.dumps(str(executable.resolve()))})"
                   '(literal "/dev/null")(literal "/dev/random")(literal "/dev/urandom"))')
    if port is not None:
        policy += f'(allow network-outbound (remote ip "localhost:{port}"))'
    return policy


def metadata(cli: Path, args: list[str], root: Path, env: dict[str, str]) -> Any:
    result = run(["/usr/bin/sandbox-exec", "-p", sandbox(cli, root), str(cli), *args], root, env)
    require(result.returncode == 0, "Native plugin metadata validation failed.")
    try:
        return json.loads(result.stdout)
    except ValueError as exc:
        raise ProbeError("Native metadata response was not JSON.") from exc


def portable(bundle: Path, project: Path, state: Path, operation: str, payload: dict[str, Any]) -> dict[str, Any]:
    writable = project.resolve(strict=True).parent
    require(state.resolve().is_relative_to(writable), "Portable state must remain inside its disposable tree.")
    interpreter = Path(sys.executable).resolve(strict=True)
    env = environment(writable / "portable-home", writable / "portable-config", writable)
    policy = sandbox(interpreter, writable, candidate=bundle.resolve(strict=True))
    result = run(["/usr/bin/sandbox-exec", "-p", policy, str(interpreter), "-I", "-B",
                  str(bundle / "ecosystem/cli.py"), "--root", str(project), "--state-dir", str(state), operation],
                 project, env, timeout=20, input_text=json.dumps(payload))
    require(result.returncode == 0, "Isolated portable contract operation failed.")
    value = json.loads(result.stdout)
    require(value.get("ok") is True, "Isolated portable contract rejected the operation.")
    return value


def plan(bundle: Path, project: Path, state: Path, session: str, profile: str) -> None:
    command = [sys.executable, "-I", "-B", "-c", "raise SystemExit(0)"]
    digest = hashlib.sha256(json.dumps(command, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    portable(bundle, project, state, "plan", {
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

    def __init__(self, target: Path | None, fail_entry: Path | None, *,
                 role: str | None = None, role_body: str | None = None) -> None:
        super().__init__(("127.0.0.1", 0), ReplyHandler)
        self.target, self.fail_entry = target, fail_entry
        self.requests = 0
        self.bootstrap = False
        self.scope_rejected = False
        self.role, self.role_body = role, role_body
        self.root_replies = 0
        self.child_replies = 0
        self.role_context = False
        self.child_context = False
        self.agent_schema_valid = False
        self.tool_error_categories: set[str] = set()
        self.extra_request_kinds: set[str] = set()
        self.child_tools_safe = True


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
        if body.get("output_config"):
            self.server.extra_request_kinds.add("structured-output")
        self.server.bootstrap |= "Constellation shared research environment" in json.dumps(body)
        for message in body.get("messages", []):
            for item in message.get("content", []) if isinstance(message.get("content"), list) else []:
                if isinstance(item, dict) and item.get("type") == "tool_result":
                    self.server.scope_rejected |= "outside the registered scope" in str(item.get("content", ""))
                    if item.get("is_error"):
                        content = str(item.get("content", "")).lower()
                        for category in ("permission", "denied", "not found", "unknown", "invalid", "restricted", "classifier", "not allowed", "disabled", "error", "failed", "blocked"):
                            if category in content:
                                self.server.tool_error_categories.add(category)
        system = body.get("system", [])
        system_text = "\n".join(item.get("text", "") for item in system if isinstance(item, dict)) if isinstance(system, list) else str(system)
        child = bool(self.server.role_body and self.server.role_body in system_text)
        self.server.role_context |= child
        if child:
            self.server.child_replies += 1
            self.server.child_context |= "Constellation observed this native subagent" in json.dumps(body)
            listed = body.get("tools")
            known = isinstance(listed, list) and all(
                isinstance(item, dict) and isinstance(item.get("name"), str)
                and item["name"] in ALLOWED_CHILD_TOOLS for item in listed)
            tools = {item["name"] for item in listed} if known else set()
            if not known or "Write" not in tools:
                self.server.child_tools_safe = False
            first = self.server.child_replies == 1
        else:
            self.server.root_replies += 1
            first = self.server.root_replies == 1
        if first and not child and self.server.fail_entry is not None:
            # Only the caller's disposable negative-case copy is altered.
            self.server.fail_entry.write_text("raise SystemExit(17)\n")
        if first and not child and self.server.role is not None:
            agent = next((item for item in body.get("tools", []) if item.get("name") == "Agent"), {})
            properties = agent.get("input_schema", {}).get("properties", {})
            required = set(agent.get("input_schema", {}).get("required", []))
            values = {"description": "Synthetic restricted file check", "prompt": SUBAGENT_TASK,
                      "subagent_type": self.server.role}
            if "run_in_background" in properties:
                values["run_in_background"] = False
            self.server.agent_schema_valid = required <= set(values) and set(values) <= set(properties)
            block = {"type": "tool_use", "id": "toolu_synthetic_agent", "name": "Agent", "input": values}
        elif first and self.server.target is not None and (child or self.server.role is None):
            block = {"type": "tool_use", "id": "toolu_synthetic_write", "name": "Write",
                     "input": {"file_path": str(self.server.target), "content": "synthetic fixture\n"}}
        else:
            block = {"type": "text", "text": "Synthetic local verification complete."}
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
    child_case = case.startswith("subagent-")
    forbidden = case in {"undeclared-write", "installed-autoload", "subagent-undeclared-write"}
    target = project / ("forbidden.md" if forbidden else "result.md")
    session = str(uuid.uuid4())
    if write:
        plan(bundle, project, root / "state", session, modules[0])
    role_path = bundle / "ecosystem/agents/researcher.toml"
    role = tomllib.loads(role_path.read_text())
    role_name = "constellation:" + role["name"].replace("_", "-")
    server = LocalReplies(target if write else None,
                          bundle / "ecosystem/claude_hooks.py" if case == "process-failure" else None,
                          role=role_name if child_case else None,
                          role_body=role["developer_instructions"].strip() if child_case else None)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        env = environment(home, config, root)
        env.update(ANTHROPIC_BASE_URL=f"http://127.0.0.1:{server.server_port}",
                   ANTHROPIC_API_KEY="synthetic-local-only-key", CONSTELLATION_STATE_DIR=str(root / "state"),
                   CLAUDE_CODE_TMPDIR=str(root.parent))
        args = [str(cli), "-p", "Perform the synthetic local verification.", "--session-id", session,
                "--no-session-persistence", "--setting-sources", "user,project" if case == "installed-autoload" else "project",
                "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}', "--settings", '{"autoMemoryEnabled":false}',
                "--output-format", "stream-json", "--verbose", "--system-prompt-snapshot", "off", "--prompt-suggestions", "false",
                "--include-hook-events", "--max-turns", "5", "--permission-prompts", "none",
                "--tools", "Agent,Read,Write" if child_case else "Read,Write" if write else "",
                "--allowedTools", "Agent,Read,Write" if child_case else "Read,Write"]
        if child_case:
            args += ["--restricted", "--forward-subagent-text"]
        if case != "installed-autoload":
            args += ["--plugin-dir", str(bundle)]
        result = run(["/usr/bin/sandbox-exec", "-p", sandbox(cli, root.parent, server.server_port), *args], project, env)
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
        if (child_case and not any(row.get("hook_event") == "SubagentStart" for row in hooks)
                and "classifier" in server.tool_error_categories):
            raise ProbeUnavailable("blocked_classifier: the native Agent permission classifier requires its real provider; this probe does not simulate approval and verified no subagent event.")
        if case in {"declared-write", "subagent-declared-write"}:
            require(target.is_file() and target.read_text() == "synthetic fixture\n", f"Declared Write did not succeed (non_child_requests={server.root_replies}, child_requests={server.child_replies}, agent_schema_valid={server.agent_schema_valid}, role_context={server.role_context}, tool_error_categories={sorted(server.tool_error_categories)}, extra_request_kinds={sorted(server.extra_request_kinds)}, events={sorted({row.get('hook_event') for row in hooks})}).")
        elif write:
            require(not target.exists(), f"{case}: a forbidden write occurred.")
        if forbidden:
            require(server.scope_rejected, f"{case}: shared scope denial was not observed.")
        if write and case != "process-failure":
            require(continuations == 2, f"{case}: Stop continuation budget was not enforced.")
            require(any("INCOMPLETE" in item.get("systemMessage", "") for item in decisions),
                    f"{case}: unfinished work was not reported.")
        if case == "process-failure":
            require(any(row.get("hook_event") == "PreToolUse" and row.get("exit_code") == 17 for row in hooks),
                    "The native operational-failure case did not execute.")
        subagent_verified = False
        if child_case:
            require(server.agent_schema_valid, "Native Agent schema did not match the bounded fixture.")
            require(server.role_context and server.child_context, "Shared native role and hook context were not delivered to the child.")
            require(server.child_replies > 0 and server.child_tools_safe, "The child did not retain the restricted file-tool boundary on every request.")
            for event in ("SubagentStart", "SubagentStop"):
                require(sum(row.get("hook_event") == event and row.get("exit_code") == 0 for row in hooks) == 1,
                        f"{case}: expected exactly one successful {event}.")
            status = portable(bundle, project, root / "state", "status", {
                "session_id": "claude-" + session, "task_id": "synthetic-native-probe",
                "agent_id": "synthetic-probe-coordinator"})
            observed = status.get("observed_agents", {})
            require(len(observed) == 1 and set(observed.values()) == {"stop"}
                    and all(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,120}", identity) for identity in observed),
                    "Native child identity was not observed through a completed start/stop cycle.")
            require(set(observed).isdisjoint(status["agents"]), "Observation unexpectedly granted the child a role.")
            subagent_verified = True
        require(not list(root.rglob("*.jsonl")), "The native client persisted a conversation artifact.")
        return {"case": case, "passed": True, "local_requests": server.requests,
                "native_subagent_verified": subagent_verified, "child_requests": server.child_replies,
                "skills": len(skills), "agents": len(agents), "target_created": target.exists(),
                "scope_rejected": server.scope_rejected, "stop_continuations": continuations,
                "events": sorted({row.get("hook_event") for row in hooks})}
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=3)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--claude", default="claude")
    parser.add_argument("--cases", nargs="+", choices=CASES, default=list(CASES[:5]),
                        help="Default: five non-agent obligations. Subagent cases are opt-in and can be unavailable when the native permission classifier requires a real provider.")
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
        with tempfile.TemporaryDirectory(prefix="cn-", dir=anchor) as temporary:
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
            results = []
            for case in args.cases:
                selected_bundle = installed if case == "installed-autoload" else bundle
                if case == "process-failure":
                    selected_bundle = root / "negative-release"
                    shutil.copytree(bundle, selected_bundle)
                results.append(probe(cli, selected_bundle, root / case, manifest["modules"], skills, agents, case,
                                     config=config if case == "installed-autoload" else None))
        print(json.dumps({"passed": True, "native_schema_valid": True, "native_plugin_auto_discovered": True,
                          "repeat_install_unchanged": True, "cases": results,
                          "actual_subagent_events_verified": {"subagent-declared-write", "subagent-undeclared-write"} <= set(args.cases),
                          "evidence_scope": "Only the cases in this invocation; no claim about other native or model evaluations.",
                          "isolation": "Trusted Claude executable: clean environment, real HOME/Keychain and external network denied, temporary writes only, no JSONL. Candidate CLI plan/status: additionally allowlisted fixture/runtime reads, fixed cwd and bounded process group. Every child request checked."}))
        return 0
    except ProbeUnavailable as exc:
        print(json.dumps({"status": "unavailable", "passed": False, "reason": str(exc),
                          "subagent_events_verified_in_this_run": False}))
        return 77
    except Exception as exc:
        print(json.dumps({"passed": False, "error": str(exc) if isinstance(exc, ProbeError) else type(exc).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

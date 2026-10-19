"""Small real-filesystem fixtures for the portable engine's public protocol.

All ``fixture-*`` identities are synthetic test data, never attestations that
native agents performed an actual evaluation or independent review.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any


SOURCE_DIR = Path(__file__).resolve().parents[1]
CODEX_DIR = SOURCE_DIR.parent
AVAILABLE_PROFILES = tuple(profile for profile in ("coding", "mathematics", "quant-research", "writter")
                           if (CODEX_DIR / "skills" / profile / "SKILL.md").is_file())
if not AVAILABLE_PROFILES:
    raise RuntimeError("The test runtime must distribute at least one profile.")
DEFAULT_PROFILE = "writter" if "writter" in AVAILABLE_PROFILES else AVAILABLE_PROFILES[0]
PYTHON = sys.executable
COORDINATOR = "fixture-coordinator"
WORKER = "fixture-worker"
REVIEWERS = tuple(f"fixture-reviewer-{number}" for number in range(8))
if str(CODEX_DIR) not in sys.path:
    sys.path.insert(0, str(CODEX_DIR))


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode()).hexdigest()


def check_definition(identifier: str, argv: list[str], kind: str = "editorial") -> dict:
    return {"id": identifier, "kind": kind, "definition_sha256": digest(argv)}


def requirement(identifier: str = "r1", path: str = "result.md", check: str = "c1",
                acceptance: str = "editorial", text: str = "The result explains the verified outcome.") -> dict:
    return {"id": identifier, "text": text, "deliverables": [path],
            "checks": [check], "acceptance": acceptance}


class Scenario:
    """A standalone project without Git, using the installed public Engine API."""

    def __init__(self, *, session: str = "fixture-session", task: str = "fixture-task",
                 root: Path | None = None, state_dir: Path | None = None):
        from ecosystem.core import Engine

        self._temporary = tempfile.TemporaryDirectory(prefix="ecosystem-tests-")
        self.base = Path(self._temporary.name).resolve()
        self.root = root if root is not None else self.base / "project"
        self.state_dir = state_dir if state_dir is not None else self.base / "state"
        self.root.mkdir(parents=True, exist_ok=True)
        self.session, self.task = session, task
        self.revision = 0
        self.engine = Engine(self.root, self.state_dir)
        self.argv = [PYTHON, "-I", "-B", "-c",
                     "from pathlib import Path; assert Path('result.md').read_text().strip() == 'verified result'"]
        self.contract = {
            "requirements": [requirement()],
            "deliverables": [{"path": "result.md", "profiles": [DEFAULT_PROFILE]}],
            "checks": [check_definition("c1", self.argv)],
            "inputs": [], "depends_on": [], "risk": "quick",
            "agents": [{"agent_id": WORKER, "role": "worker"}]
                      + [{"agent_id": actor, "role": "reviewer"} for actor in REVIEWERS],
        }
        if not (self.root / "result.md").exists():
            (self.root / "result.md").write_text("verified result\n")

    def __enter__(self) -> Scenario:
        return self

    def __exit__(self, *_: object) -> None:
        self.cleanup()

    def cleanup(self) -> None:
        self._temporary.cleanup()

    def payload(self, *, actor: str = COORDINATOR, **fields: Any) -> dict:
        return {"session_id": self.session, "task_id": self.task, "agent_id": actor,
                "expected_revision": self.revision, **fields}

    def call(self, operation: str, *, actor: str = COORDINATOR, **fields: Any) -> dict:
        payload = self.payload(actor=actor, **fields)
        if operation == "active-tasks":
            payload = {"session_id": self.session}
        if operation in {"status", "review-context", "active-tasks"}:
            payload.pop("expected_revision", None)
        result = self.engine.execute(operation, payload)
        if "revision" in result:
            self.revision = result["revision"]
        return result

    def plan(self, **changes: Any) -> dict:
        contract = {**deepcopy(self.contract), **deepcopy(changes)}
        result = self.call("plan", **contract)
        self.contract = contract
        self.call("author", author=WORKER,
                  paths=[item["path"] for item in contract["deliverables"]])
        return result

    def check(self, identifier: str = "c1", argv: list[str] | None = None, **fields: Any) -> dict:
        return self.call("check", id=identifier, argv=self.argv if argv is None else argv, **fields)

    def start(self) -> dict:
        return self.call("review-start")

    def assessments(self) -> list[dict]:
        return [{"requirement_id": item["id"],
                 "verdict": "proved" if item["acceptance"] == "proof" else "satisfied",
                 "support": {"proof": "proof_review", "calculation": "experimental",
                             "behavior": "behavior", "editorial": "editorial"}[item["acceptance"]],
                 "evidence": f"Fixture inspection covers {item['id']} and its declared artifact."}
                for item in self.contract["requirements"]]

    def report(self, reviewer: int | str = 0, **changes: Any) -> dict:
        actor = REVIEWERS[reviewer] if isinstance(reviewer, int) else reviewer
        context = self.call("review-context")
        report = {"token": context["token"], "reviewer": actor, "role": "reviewer",
                  "focus": ["correctness"],
                  "paths": [item["path"] for item in self.contract["deliverables"]],
                  "summary": "Synthetic fixture review of the complete declared artifact.",
                  "evidence": "The fixture artifact contains the checked outcome and meets its obligation.",
                  "findings": [], "assessments": self.assessments(), **changes}
        return self.call("review-report", actor=actor, **report)

    def approve(self) -> dict:
        self.check()
        context = self.start()
        for index in range(context["required_focus"]["correctness"]):
            self.report(index)
        first_security = context["required_focus"]["correctness"]
        for index in range(context["required_focus"].get("security", 0)):
            self.report(first_security + index, focus=["security"], assessments=[])
        return context

    def close(self, mode: str = "complete") -> dict:
        return self.call("close", mode=mode)


PROCESS_SCRIPT = """\
import json, sys
sys.path.insert(0, sys.argv[1])
from pathlib import Path
from ecosystem.core import Engine
from ecosystem.storage import Error
request = json.load(sys.stdin)
try:
    value = Engine(Path(sys.argv[2]), Path(sys.argv[3])).execute(request['operation'], request['payload'])
except Error as exc:
    print(json.dumps({'ok': False, 'error': str(exc)}))
else:
    print(json.dumps({'ok': True, 'value': value}))
"""


def start_request(scenario: Scenario, operation: str, payload: dict,
                  *, environment: dict[str, str] | None = None) -> subprocess.Popen:
    process = subprocess.Popen(
        [PYTHON, "-I", "-B", "-c", PROCESS_SCRIPT, str(CODEX_DIR),
         str(scenario.root), str(scenario.state_dir)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, env=environment if environment is not None else dict(os.environ),
    )
    assert process.stdin is not None
    process.stdin.write(json.dumps({"operation": operation, "payload": payload}))
    process.stdin.close()
    process.stdin = None
    return process


def finish_request(process: subprocess.Popen, timeout: float = 15) -> dict:
    stdout, stderr = process.communicate(timeout=timeout)
    if process.returncode:
        raise AssertionError(f"Protocol fixture failed ({process.returncode}): {stderr}")
    return json.loads(stdout)

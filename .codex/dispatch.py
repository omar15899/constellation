"""Build deterministic native-agent work packets without executing their work.

The packets describe a schedule, not receipts of authorship, tests or review.
Publication and evidence acceptance remain owned by the existing workflow.
"""
from __future__ import annotations

import json
from typing import Any, TYPE_CHECKING
from urllib.parse import quote

from workflow import Blocked, Workflow, digest, git, review_engine, snapshot

if TYPE_CHECKING:
    from workspace import Workspace


def _token(value: Any) -> str:
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())


def _task_id(repository: str, phase: str) -> str:
    return f"{quote(repository, safe='/.')}::{phase}"


def waves(tasks: list[dict[str, Any]], capacity: int, limits: dict[str, int]) -> list[list[str]]:
    """Schedule ready tasks lexically under one shared agent budget.

    The primary coordinator has one serial lane and does not consume a subagent
    slot. Dependencies become ready only in a subsequent wave.
    """
    pending = {task["id"]: task for task in tasks}
    if len(pending) != len(tasks):
        raise Blocked("Dispatch task IDs must be unique.")
    if any(set(task["depends_on"]) - pending.keys() for task in tasks):
        raise Blocked("Dispatch dependencies must identify planned tasks.")
    done: set[str] = set()
    result: list[list[str]] = []
    while pending:
        selected: list[str] = []
        agents = 0
        coordinator = False
        counts: dict[str, int] = {}
        for identifier in sorted(pending):
            task = pending[identifier]
            if not set(task["depends_on"]) <= done:
                continue
            repo = task["repository"]
            if task["executor"] == "coordinator":
                if coordinator:
                    continue
                coordinator = True
            else:
                if agents >= capacity or counts.get(repo, 0) >= limits[repo]:
                    continue
                agents += 1
                counts[repo] = counts.get(repo, 0) + 1
            selected.append(identifier)
        if not selected:
            raise Blocked("Dispatch task dependency cycle or unavailable capacity.")
        result.append(selected)
        done.update(selected)
        for identifier in selected:
            del pending[identifier]
    return result


def _review_slots(context: dict[str, Any]) -> list[list[str]]:
    if not context["enabled"]:
        return []
    # Allocate distinct specialists where possible; a policy may legitimately
    # require overlapping focus coverage from the same reviewer population.
    count = context["required_reviewers"]
    slots: list[list[str]] = [[] for _ in range(count)]
    offset = 0
    for focus, required in sorted(context["required_focus"].items()):
        for index in range(required):
            slots[(offset + index) % count].append(focus)
        offset += required
    for slot in slots:
        if not slot:
            slot.append("correctness")
    return slots


def build(workspace: Workspace, capacity: int | None = None) -> dict[str, Any]:
    """Read the existing contract and return a complete prospective schedule."""
    from agent_policy import effective_limit, load_policy
    from workspace import names, topological

    if capacity is not None and (type(capacity) is not int or not 1 <= capacity <= 64):
        raise Blocked("Dispatch capacity must be an integer from 1 to 64, excluding booleans.")
    registry = workspace.read_repositories()
    if registry != workspace.repositories:
        raise Blocked("Repository registry changed since workspace construction; recreate the workspace and reconcile the plan.")
    state = workspace.load()
    roots = names(state.get("roots"), "Dispatch repositories")
    if not roots:
        raise Blocked("Dispatch requires a planned repository.")
    order = topological(roots, state["depends_on"])
    if order != state["order"]:
        raise Blocked("Workspace publication order does not match its dependencies; reconcile the plan.")
    policy = load_policy(workspace)
    shared = min(64, policy["defaults"]["max_concurrent_threads_per_session"], capacity or 64)
    limits = {repo: min(shared, effective_limit(policy, repo)) for repo in sorted(roots)}
    flows: dict[str, Workflow] = {}
    contracts: dict[str, Any] = {}
    repositories: dict[str, Any] = {}
    contexts: dict[str, Any] = {}
    bindings: dict[str, Any] = {}
    engine = review_engine()
    for repo in sorted(roots):
        if repo not in workspace.repositories:
            raise Blocked(f"Dispatch repository is no longer registered: {repo}")
        root_route = workspace.route_one(repo)
        if root_route["repository"] != repo:
            raise Blocked(f"Planned repository no longer owns its root: {repo}")
        flow = Workflow(workspace._target(repo), workspace.session)
        flows[repo] = flow
        contract = flow.load()
        contracts[repo] = contract
        target = flow.ensure_target(contract)
        if contract.get("sync_error"):
            raise Blocked(f"Resolve the planned upstream check before dispatch: {repo}")
        paths = sorted(contract["paths"])
        instructions = set(root_route["instructions"])
        for path in paths:
            name = path if repo == "." else f"{repo}/{path}"
            route = workspace.route_one(name, file=True, deletion=path in contract.get("deletions", []))
            if route["repository"] != repo:
                raise Blocked(f"Dispatch artifact changed Git owner: {name}")
            instructions.update(route["instructions"])
        for filename in (".codex/PROJECT.md", "REVIEW.md"):
            name = filename if repo == "." else f"{repo}/{filename}"
            candidate = workspace._target(name)
            if candidate.is_file():
                instructions.add(str(candidate))
        try:
            context = engine.prepare(flow.root, contract)
        except engine.ReviewError as exc:
            raise Blocked(str(exc)) from exc
        contexts[repo] = context
        artifacts = snapshot(flow.root, paths, contract.get("deletions", []))
        head = git(flow.root, "rev-parse", "HEAD")
        repositories[repo] = {
            "management": workspace.repositories[repo], "requirements": contract["requirements"],
            "paths": paths, "deletions": sorted(contract.get("deletions", [])),
            "instructions": sorted(instructions), "head": head,
            "target": {key: target[key] for key in ("branch", "remote", "ref")},
            "depends_on": sorted(state["depends_on"].get(repo, [])),
            "review": {key: context[key] for key in ("enabled", "mode", "required_reviewers", "required_focus", "max_rounds")
                       if key in context},
        }
        bindings[repo] = {"contract": workspace.signature(contract), "target": target,
                          "head": head, "artifacts": artifacts, "review_context": context}
    workspace.validate(state, flows)
    tasks: list[dict[str, Any]] = []

    def add(repo: str, phase: str, role: str | None, dependencies: list[str], handoff: str,
            *, write: bool = False, focus: list[str] | None = None) -> str:
        identifier = _task_id(repo, phase)
        tasks.append({
            "id": identifier, "repository": repo, "phase": phase,
            "executor": "agent" if role else "coordinator", "agent_role": role,
            "depends_on": sorted(dependencies), "paths": repositories[repo]["paths"],
            "write_paths": repositories[repo]["paths"] if write else [],
            "requirements": repositories[repo]["requirements"], "focus": focus or [],
            "handoff": handoff,
        })
        return identifier

    review_terminals: list[str] = []
    for repo in order:
        mapper = add(repo, "map", "repo_mapper", [],
                     "Read the listed instructions, verify Git ownership and local contracts, and identify relevant consumers and checks. Return public engineering evidence with exact paths; do not write or publish.")
        research = add(repo, "research", "researcher", [mapper],
                       "Inspect relevant existing evidence, assumptions, counterexamples and prior verdicts. Return a concrete implementation and verification proposal. For quantitative claims apply the existing promotion contract; no experiment rerun is authorized by this packet.")
        dependencies = [research] + [_task_id(provider, "check") for provider in repositories[repo]["depends_on"]]
        register_author = contexts[repo]["enabled"] and bool(repositories[repo]["paths"])
        author_handoff = (" The coordinator must register that ID and authored paths with review-author before review."
                          if register_author else "")
        implement = add(repo, "implement", "implementer", dependencies,
                        "Implement only write_paths under the declared contract. Return exact changed paths, rationale, checks and your actual native agent ID."
                        + author_handoff + " No commit or push from this agent.", write=True)
        author_check = " Register actual authors with review-author." if register_author else ""
        check = add(repo, "check", None, [implement],
                    "Inspect the implementation." + author_check
                    + " Execute relevant checks through workspace.py check for this repository. Repair failures before review; a packet is never evidence that a check ran.")
        reviewers = []
        for index, focus in enumerate(_review_slots(contexts[repo]), 1):
            role = "security_reviewer" if "security" in focus else "reviewer"
            reviewers.append(add(repo, f"review-{index:02d}", role, [check],
                                 "After checks pass, the coordinator opens review-start and supplies its current token and diff. Use a distinct actual native agent identity for every review slot, independent of every author. Review every listed path with the assigned focus; return reproducible findings or explicit zero findings. Register with review-report; this task ID and dispatch token are not reviewer identity or review authorization.",
                                 focus=focus))
        review_terminals.extend(reviewers or [check])
    for repo in order:
        dependencies = review_terminals + [_task_id(provider, "integrate") for provider in repositories[repo]["depends_on"]]
        add(repo, "integrate", None, dependencies,
            "After all repositories finish their checks and required reviews, inspect every handoff and resolve findings through the existing review protocol. Before the first integration, record workspace.py review with requirement evidence for every participating repository. If this repository has changed declared paths, publish only those selected workspace-relative paths through workspace.py commit, respecting provider integrations and verifying its remote. Otherwise use workspace.py publish --repo for this repository to record current HEAD publication without an empty commit, including when paths is empty. Call workspace.py finish once, only after every integration completes. An external repository retains its own review requirements. Completion cannot be inferred from this schedule.")
    tasks.sort(key=lambda task: task["id"])
    result = {
        "schema_version": 1, "kind": "execution_plan", "execution_state": "not_evaluated",
        "capacity": shared, "repository_limits": limits, "repositories": repositories,
        "tasks": tasks, "waves": waves(tasks, shared, limits),
        "repair_protocol": {
            "agent_role": "finding_verifier",
            "instructions": "For actionable findings, the assigned implementer repairs only declared paths; rerun affected checks and open the next permitted review round. A distinct finding_verifier, independent of authors and discoverers, verifies fixed or dismissed findings with evidence for review-resolve. Preserve findings and the existing round limit. Recompute dispatch after scope, policy or artifact changes.",
        },
        "limits": [
            "Read-only planning output: this command creates no agents, checks, review receipts, commits or pushes, and does not assess completion of previous work.",
            "Capacity is a maximum of concurrent subagents across the whole workspace, excluding the single coordinator lane; actual client capacity may be lower.",
            "The dispatch token binds the current declared artifacts, contracts and policies. It is not a review-start token and does not pin research datasets or undeclared inputs.",
            "The coordinator uses native tools and inherits the user's model, reasoning effort, permissions and hook trust.",
        ],
    }
    result["token"] = _token({"plan": result, "bindings": bindings, "agent_policy": policy, "registry": registry})
    # No locks are created by this read-only operation. Reject concurrent edits
    # rather than return a packet assembled from different contract versions.
    if workspace.read_repositories() != registry or workspace.repositories != registry:
        raise Blocked("Repository registry changed during dispatch; rerun dispatch.")
    if workspace.load() != state or load_policy(workspace) != policy:
        raise Blocked("Workspace contract or agent policy changed during dispatch; rerun dispatch.")
    for repo, flow in flows.items():
        if flow.load() != contracts[repo] or flow.ensure_target(contracts[repo]) != bindings[repo]["target"]:
            raise Blocked(f"Repository contract changed during dispatch: {repo}")
        if (git(flow.root, "rev-parse", "HEAD") != bindings[repo]["head"]
                or snapshot(flow.root, contracts[repo]["paths"], contracts[repo].get("deletions", [])) != bindings[repo]["artifacts"]):
            raise Blocked(f"Repository artifacts changed during dispatch: {repo}")
        try:
            if engine.prepare(flow.root, contracts[repo]) != contexts[repo]:
                raise Blocked(f"Review policy or context changed during dispatch: {repo}")
        except engine.ReviewError as exc:
            raise Blocked(str(exc)) from exc
    if workspace.read_repositories() != registry or workspace.repositories != registry:
        raise Blocked("Repository registry changed during dispatch; rerun dispatch.")
    return result

#!/usr/bin/env python3
"""Route an explicit workspace task to the Git repositories that own its files."""
from __future__ import annotations

import argparse
from contextlib import ExitStack, contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Iterator

# Inspection commands must not create incidental cache artifacts.
sys.dont_write_bytecode = True

from workflow import Blocked, Workflow, changed, digest, git, now, private_path, safe_path, staged_gate, staged_paths


def names(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(p, str) and p for p in value):
        raise Blocked(f"{label} must be a list of nonempty strings.")
    if len(set(value)) != len(value):
        raise Blocked(f"{label} must be unique.")
    return value


def mapping(value: Any, label: str) -> dict[str, str]:
    if not isinstance(value, dict) or not all(isinstance(k, str) and isinstance(v, str) and v.strip()
                                             for k, v in value.items()):
        raise Blocked(f"{label} must map file paths to nonempty explanations.")
    return value


def relative(name: str, *, root: bool = False) -> str:
    p = Path(name)
    if not isinstance(name, str) or p.is_absolute() or ".." in p.parts or (not p.parts and not (root and name == ".")):
        raise Blocked(f"Expected a workspace-relative path: {name}")
    if private_path(name):
        raise Blocked(f"Private path cannot be routed: {name}")
    return p.as_posix()


def topological(roots: list[str], dependencies: dict[str, list[str]]) -> list[str]:
    if set(dependencies) - set(roots):
        raise Blocked("Dependency keys must identify repositories participating in the plan.")
    for repo, deps in dependencies.items():
        names(deps, f"Dependencies of {repo}")
        if set(deps) - set(roots):
            raise Blocked(f"Dependencies of {repo} must participate in the plan.")
    pending = set(roots)
    ordered: list[str] = []
    while pending:
        ready = sorted(repo for repo in pending if set(dependencies.get(repo, [])) <= set(ordered))
        if not ready:
            raise Blocked("Repository dependency cycle; use an acyclic depends_on map.")
        ordered.extend(ready)
        pending.difference_update(ready)
    return ordered


class Workspace:
    def __init__(self, root: Path, session: str):
        self.root = root.resolve()
        if Path(git(self.root, "rev-parse", "--show-toplevel")).resolve() != self.root:
            raise Blocked("The workspace root must itself be a Git repository root.")
        self.session = session
        self.key = digest(session.encode())[:24]
        self.home = Path(git(self.root, "rev-parse", "--path-format=absolute", "--git-path", "constellation"))
        self.path = self.home / f"workspace-{self.key}.json"
        self.repositories = self.read_repositories()

    def read_repositories(self) -> dict[str, str]:
        """Read and validate current registry semantics without changing cached ownership."""
        registry = self._target(".codex/repositories.json")
        if registry.is_symlink() or not registry.is_file():
            raise Blocked("A regular .codex/repositories.json registry is required.")
        data = json.loads(registry.read_text())
        if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("repositories"), list):
            raise Blocked("Unsupported repositories.json schema; expected schema_version 1 and repositories.")
        repositories: dict[str, str] = {}
        for entry in data["repositories"]:
            if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
                raise Blocked("Each registered repository needs a relative path.")
            name = relative(entry["path"], root=True)
            management = entry.get("management")
            if name in repositories or management not in {"native", "external"}:
                raise Blocked("Registered repository paths must be unique with native or external management.")
            self._target(name)
            repositories[name] = management
        if repositories.get(".") != "native":
            raise Blocked("The workspace registry must include '.' with native management.")
        return repositories

    def _target(self, name: str) -> Path:
        target = self.root / name
        for component in (target, *target.parents):
            if component == self.root:
                break
            if component.is_symlink():
                raise Blocked(f"Symlink paths cannot be routed: {name}")
        if not target.resolve().is_relative_to(self.root):
            raise Blocked(f"Path leaves workspace: {name}")
        return target

    def route_one(self, name: str, *, file: bool = False, deletion: bool = False) -> dict[str, Any]:
        name = relative(name, root=not file)
        target = self._target(name)
        anchor = target if target.is_dir() and not file else target.parent
        while not anchor.exists():
            anchor = anchor.parent
        owner = Path(git(anchor, "rev-parse", "--show-toplevel")).resolve()
        if not owner.is_relative_to(self.root):
            raise Blocked(f"Git owner is outside the workspace: {name}")
        repo = owner.relative_to(self.root).as_posix()
        path = target.relative_to(owner).as_posix()
        for registered in self.repositories:
            boundary = self.root / registered
            if registered != "." and target.is_relative_to(boundary) and not owner.is_relative_to(boundary):
                raise Blocked(f"Registered repository has lost its Git boundary: {registered}")
        if file:
            path = safe_path(owner, path, deletion=deletion)
            # check-ignore rejects Git's literal-pathspec mode. Prefixing the
            # exact pathname with ./ prevents a leading colon becoming magic.
            ignored = subprocess.run(["git", "check-ignore", "-q", "--", "./" + path],
                                     cwd=owner, capture_output=True, timeout=25)
            if ignored.returncode == 0:
                raise Blocked(f"Ignored file requires an explicit repository policy change: {name}")
            if ignored.returncode != 1:
                raise Blocked(f"Could not establish ignore policy for {name}.")
        instructions = []
        directory = target if target.is_dir() else target.parent
        for ancestor in reversed((directory, *directory.parents)):
            for filename in ("AGENTS.override.md", "AGENTS.md"):
                candidate = ancestor / filename
                if candidate.is_file() and not candidate.is_symlink():
                    instructions.append(str(candidate))
                    break
        branch = self._optional_git(owner, "symbolic-ref", "--short", "HEAD")
        return {"input": name, "repository": repo, "path": path,
                "management": self.repositories.get(repo, "unregistered"),
                "instructions": instructions, "branch": branch,
                "remotes": git(owner, "remote").splitlines(),
                "upstream": self._optional_git(owner, "rev-parse", "--abbrev-ref", "@{upstream}")}

    @staticmethod
    def _optional_git(root: Path, *args: str) -> str | None:
        try:
            return git(root, *args)
        except Blocked:
            return None

    def route(self, paths: list[str]) -> list[dict[str, Any]]:
        return [self.route_one(p) for p in paths]

    def load(self) -> dict[str, Any]:
        if not self.path.is_file():
            raise Blocked("No workspace contract; run workspace.py plan first.")
        state = json.loads(self.path.read_text())
        if state.get("schema_version") != 1:
            raise Blocked("Unsupported workspace state schema.")
        return state

    def save(self, state: dict[str, Any]) -> None:
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")
        temp.replace(self.path)

    @contextmanager
    def lock(self) -> Iterator[None]:
        self.home.mkdir(parents=True, exist_ok=True, mode=0o700)
        with (self.home / "workspace.lock").open("a") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            yield

    @contextmanager
    def flows(self, roots: list[str]) -> Iterator[dict[str, Workflow]]:
        # Acquire every repository lock in the same lexical order, independent
        # of publication dependencies, to avoid cross-workspace deadlocks.
        with ExitStack() as stack:
            result = {}
            for name in sorted(roots):
                target = self._target(relative(name, root=True))
                if self.route_one(name)["repository"] != name:
                    raise Blocked(f"Registered repository no longer owns its root: {name}")
                flow = Workflow(target, self.session)
                stack.enter_context(flow.lock())
                result[name] = flow
            yield result

    def status(self) -> dict[str, Any]:
        state = self.load()
        return {**state, "repositories": {name: Workflow(self.root / name, self.session).load()
                                         for name in state["roots"]}}

    def dispatch(self, capacity: int | None = None) -> dict[str, Any]:
        from dispatch import build
        return build(self, capacity)

    def guard_patch(self, payload: dict[str, Any], cwd: Path) -> None:
        inputs = payload.get("tool_input", {})
        if not isinstance(inputs, (str, dict)):
            raise Blocked("Unrecognized patch payload; expected a patch string or object.")
        patch = inputs if isinstance(inputs, str) else inputs.get("input", inputs.get("patch", inputs.get("command", "")))
        if not isinstance(patch, str):
            raise Blocked("Unrecognized patch payload; expected a patch string.")
        actions = re.findall(r"^\*\*\* (Add File|Update File|Delete File|Move to): (.+)$", patch, re.M)
        if not actions:
            raise Blocked("Unrecognized patch payload; no declared file actions found.")
        with self.lock():
            state = self.load()
            with self.flows(state["roots"]) as flows:
                self.validate(state, flows)
                grouped: dict[str, list[str]] = {}
                for action, name in actions:
                    target = Path(name) if Path(name).is_absolute() else cwd.resolve() / name
                    workspace_name = os.path.relpath(target, self.root)
                    route = self.route_one(workspace_name, file=True, deletion=action == "Delete File")
                    repo = route["repository"]
                    if repo not in flows:
                        raise Blocked(f"Patch repository is outside the workspace plan: {repo}")
                    grouped.setdefault(repo, []).append(f"*** {action}: {route['path']}")
                for repo, headers in grouped.items():
                    # The local guard consumes action headers only. Do not
                    # persist or copy patch bodies into operational state.
                    reduced = {"tool_input": "*** Begin Patch\n" + "\n".join(headers) + "\n*** End Patch"}
                    flows[repo].guard_patch(reduced, flows[repo].root)
                state["finished"] = None
                self.save(state)

    def stop(self) -> dict[str, Any]:
        with self.lock():
            state = self.load()
            try:
                with self.flows(state["roots"]) as flows:
                    self.validate(state, flows)
                    incomplete = {repo: flow.stop() for repo, flow in flows.items()}
                pending = sorted(repo for repo, result in incomplete.items() if result)
                if pending:
                    raise Blocked(f"Repository lifecycle incomplete: {', '.join(pending)}. Inspect workspace.py status.")
                if not state.get("finished"):
                    raise Blocked("Run workspace.py finish to verify the entire workspace task.")
                return {}
            except Blocked as exc:
                state["finished"] = None
                state["stop_attempts"] = state.get("stop_attempts", 0) + 1
                self.save(state)
                if state["stop_attempts"] > 2:
                    return {"continue": False, "stopReason": f"Workspace task incomplete: {exc}",
                            "systemMessage": f"Workspace: INCOMPLETE. {exc}"}
                return {"decision": "block", "reason": f"[CONSTELLATION-CONTINUE:{self.key}] {exc}"}

    @staticmethod
    def signature(spec: dict[str, Any]) -> str:
        normalized = {key: spec.get(key, [] if key in {"requirements", "paths", "deletions"} else {})
                      for key in ("requirements", "paths", "deletions", "adoption", "unrelated")}
        return digest(json.dumps(normalized, sort_keys=True).encode())

    def plan(self, spec: dict[str, Any]) -> dict[str, Any]:
        requirements = names(spec.get("requirements"), "Requirements")
        if not requirements or not all(r.strip() for r in requirements):
            raise Blocked("Plan requires nonempty observable requirements.")
        paths = names(spec.get("paths", []), "Paths")
        deletions = names(spec.get("deletions", []), "Deletions")
        if not set(deletions) <= set(paths):
            raise Blocked("Deletions must be a subset of paths.")
        adoption = mapping(spec.get("adopt_existing", {}), "adopt_existing")
        unrelated = mapping(spec.get("unrelated", {}), "unrelated")
        if not set(adoption) <= set(paths):
            raise Blocked("adopt_existing keys must identify declared paths.")
        if set(unrelated) & set(paths):
            raise Blocked("Task paths cannot also be unrelated.")
        accepted = names(spec.get("external_repositories", []), "external_repositories")
        if any(self.repositories.get(name) != "external" for name in accepted):
            raise Blocked("external_repositories must name registered external repositories.")
        groups: dict[str, dict[str, Any]] = {}
        for name in paths + list(unrelated):
            route = self.route_one(name, file=True, deletion=name in deletions)
            repo, local = route["repository"], route["path"]
            if route["management"] == "unregistered":
                raise Blocked(f"Register Git owner before planning changes: {repo}")
            if route["management"] == "external" and repo not in accepted:
                raise Blocked(f"External repository {repo} needs explicit external_repositories acceptance.")
            group = groups.setdefault(repo, {"requirements": requirements, "paths": [], "deletions": [],
                                             "adopt_existing": {}, "unrelated": {}})
            if name in paths:
                group["paths"].append(local)
            if name in deletions:
                group["deletions"].append(local)
            if name in adoption:
                group["adopt_existing"][local] = adoption[name]
            if name in unrelated:
                group["unrelated"][local] = unrelated[name]
        if not groups:
            groups["."] = {"requirements": requirements, "paths": [], "deletions": [],
                           "adopt_existing": {}, "unrelated": {}}
        dependencies = spec.get("depends_on", {})
        if not isinstance(dependencies, dict):
            raise Blocked("depends_on must map repository paths to dependency lists.")
        order = topological(list(groups), dependencies)
        with self.lock(), self.flows(list(groups)) as flows:
            previous = self.load() if self.path.exists() else None
            if previous and not previous.get("finished") and set(previous["roots"]) - set(groups):
                raise Blocked("The new plan omits unfinished repositories; retain their scope.")
            # Inspect all active contracts before beginning or altering any.
            for name, flow in flows.items():
                if not flow.path.exists():
                    continue
                old = flow.load()
                group = groups[name]
                if old.get("requirements") and (not old.get("finished") or (previous and not previous.get("finished"))):
                    old_spec = {"requirements": old["requirements"], "paths": old["paths"],
                                "deletions": old.get("deletions", []),
                                "adopt_existing": old.get("adoption", {}), "unrelated": old.get("unrelated", {})}
                    if group != old_spec and not spec.get("extend_existing", False):
                        raise Blocked(f"Active contract in {name}; use extend_existing:true to preserve and extend it explicitly.")
                    if spec.get("extend_existing", False):
                        for key in ("requirements", "paths", "deletions"):
                            group[key] = list(dict.fromkeys(old_spec[key] + group[key]))
                        for key in ("adopt_existing", "unrelated"):
                            group[key] = {**old_spec[key], **group[key]}
            # Catch scope and ownership problems across the complete batch
            # before creating or replacing any repository's contract.
            for name, flow in flows.items():
                group = groups[name]
                old = flow.load() if flow.path.exists() else {}
                retain = bool(old) and (not old.get("finished") or (previous and not previous.get("finished")))
                baseline = set(old["baseline_dirty"] if retain else changed(flow.root))
                existing = set(group["paths"]) & baseline
                if any(not group["adopt_existing"].get(path) for path in existing):
                    raise Blocked(f"Existing changes in {name} need an adopt_existing explanation per file.")
                if set(group["paths"]) & set(group["unrelated"]):
                    raise Blocked(f"Task paths in {name} cannot also be unrelated.")
                if len(set(group["paths"])) != len(group["paths"]):
                    raise Blocked(f"Paths in {name} must be unique after normalization.")
                for path in group["deletions"]:
                    if path not in old.get("deletions", []):
                        git(flow.root, "--literal-pathspecs", "ls-files", "--error-unmatch", "--", path)
            state = {"schema_version": 1, "started": (previous or {}).get("started", now()),
                     "roots": sorted(groups), "order": order, "depends_on": dependencies,
                     "external_repositories": accepted, "contracts": {}, "finished": None,
                     "progress": {}, "operation": "plan"}
            self.save(state)
            for name in order:
                try:
                    flow = flows[name]
                    if not flow.path.exists() or (flow.load().get("finished") and not (previous and not previous.get("finished"))):
                        flow.begin("workspace")
                    contract = flow.plan(groups[name])
                    state["contracts"][name] = self.signature(contract)
                    state["progress"][name] = {"operation": "plan", "at": now()}
                    self.save(state)
                except Exception as exc:
                    self.failed(state, name, exc)
                    raise
            return state

    def failed(self, state: dict[str, Any], repo: str, exc: Exception) -> None:
        state["finished"] = None
        state["error"] = {"repository": repo, "type": type(exc).__name__,
                          "sha256": digest(str(exc).encode()), "at": now()}
        self.save(state)

    def validate(self, state: dict[str, Any], flows: dict[str, Workflow]) -> None:
        if set(state["contracts"]) != set(state["roots"]):
            raise Blocked("Workspace plan is incomplete; correct the blocker and rerun plan.")
        for name, flow in flows.items():
            if self.repositories.get(name) == "external" and name not in state["external_repositories"]:
                raise Blocked(f"External repository acceptance missing: {name}")
            if self.repositories.get(name) not in {"native", "external"}:
                raise Blocked(f"Repository is no longer registered: {name}")
            if self.signature(flow.load()) != state["contracts"][name]:
                raise Blocked(f"Contract changed outside this workspace plan: {name}; reconcile using plan.")

    def check(self, repo: str, command: list[str], *, timeout: int = 300) -> dict[str, Any]:
        if not command:
            raise Blocked("check needs a command after --.")
        with self.lock():
            state = self.load()
            if repo not in state["roots"]:
                raise Blocked(f"Repository does not participate in the plan: {repo}")
            with self.flows(state["roots"]) as flows:
                self.validate(state, flows)
                state.update(finished=None, operation="check")
                self.save(state)
                try:
                    result = flows[repo].check(command, timeout=timeout)
                    state["progress"][repo] = {"operation": "check", "at": now()}
                    self.save(state)
                    return result
                except Exception as exc:
                    self.failed(state, repo, exc)
                    raise

    def review(self, evidence: dict[str, Any]) -> dict[str, Any]:
        with self.lock():
            state = self.load()
            if not isinstance(evidence, dict) or set(evidence) != set(state["roots"]):
                raise Blocked("Review must map every participating repository to its requirement evidence.")
            with self.flows(state["roots"]) as flows:
                self.validate(state, flows)
                state.update(finished=None, operation="review")
                self.save(state)
                results = {}
                for name in state["order"]:
                    try:
                        results[name] = flows[name].review(evidence[name])
                        state["progress"][name] = {"operation": "review", "at": now()}
                        self.save(state)
                    except Exception as exc:
                        self.failed(state, name, exc)
                        raise
                return results

    def review_operation(self, repo: str, operation: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        with self.lock():
            state = self.load()
            if repo not in state["roots"]:
                raise Blocked(f"Repository does not participate in the plan: {repo}")
            with self.flows(state["roots"]) as flows:
                self.validate(state, flows)
                result = flows[repo].review_operation(operation, payload)
                if operation != "prepare":
                    state.update(finished=None, operation="review-" + operation)
                    state["progress"][repo] = {"operation": state["operation"], "at": now()}
                    self.save(state)
                return result

    def _preflight(self, state: dict[str, Any], flows: dict[str, Workflow],
                   selected: dict[str, list[str]] | None, *, preserve_index: bool = False) -> None:
        self.validate(state, flows)
        for name in state["order"]:
            flow = flows[name]
            contract = flow.load()
            flow.ensure_target(contract)
            if selected is None or name in selected:
                flow.reviewed(contract)
                if selected is None or not selected[name]:
                    flow.checked_scope(contract)
                elif not set(selected[name]) <= set(contract["paths"]):
                    raise Blocked(f"Undeclared commit paths in {name}.")
                if selected is not None:
                    staged = staged_paths(flow.root)
                    if staged and not preserve_index:
                        raise Blocked(f"Index already contains staged work in {name}; it was preserved.")
                    if staged & set(selected[name]):
                        raise Blocked(f"Selected task paths overlap staged work in {name}; preserve_index only accepts disjoint paths.")
                    if not preserve_index:
                        staged_gate(flow.root)
            for dependency in state["depends_on"].get(name, []):
                if selected is not None and name not in selected:
                    continue
                upstream = flows[dependency]
                dep_state = upstream.load()
                pending = set(dep_state["paths"]) & changed(upstream.root)
                if selected is not None and dependency in selected:
                    if pending - set(selected[dependency]):
                        raise Blocked(f"Dependency {dependency} has task files outside this commit batch.")
                else:
                    upstream.reviewed(dep_state)
                    upstream.checked_scope(dep_state)
                    publication = dep_state.get("publication")
                    if selected is not None and (not publication or publication["head"] != git(upstream.root, "rev-parse", "HEAD")):
                        raise Blocked(f"Publish dependency {dependency} before {name}.")

    def commit(self, paths: list[str], message: str, *, preserve_index: bool = False) -> dict[str, Any]:
        selected: dict[str, list[str]] = {}
        for path in names(paths, "Commit paths"):
            route = self.route_one(path, file=True, deletion=not (self.root / path).exists())
            selected.setdefault(route["repository"], []).append(route["path"])
        if not selected:
            raise Blocked("Commit needs explicit file paths.")
        return self._publish(selected, message, preserve_index=preserve_index)

    def finish(self) -> dict[str, Any]:
        return self._publish(None, None)

    def publish(self, repo: str) -> dict[str, Any]:
        """Verify a reviewed repository's current HEAD without creating a commit."""
        return self._publish({repo: []}, None)

    def _publish(self, selected: dict[str, list[str]] | None, message: str | None,
                 *, preserve_index: bool = False) -> dict[str, Any]:
        with self.lock():
            state = self.load()
            if selected is not None and set(selected) - set(state["roots"]):
                raise Blocked("Publication includes repositories outside the plan.")
            operation = "finish" if selected is None else "commit" if any(selected.values()) else "publish"
            state.update(finished=None, operation=operation, progress={})
            state.pop("error", None)
            self.save(state)
            with self.flows(state["roots"]) as flows:
                current = "preflight"
                try:
                    self._preflight(state, flows, selected, preserve_index=preserve_index)
                    # Complete local validation everywhere before synchronization
                    # or publication; a later remote rejection remains possible.
                    for current in state["order"]:
                        flows[current].sync_upstream(flows[current].load())
                    self._preflight(state, flows, selected, preserve_index=preserve_index)
                    results = {}
                    for current in state["order"]:
                        if selected is not None and current not in selected:
                            continue
                        flow = flows[current]
                        if selected is None:
                            result = flow.finish()
                        elif set(selected[current]) & changed(flow.root):
                            options = {"preserve_index": True} if preserve_index else {}
                            result = flow.commit(selected[current], message or "Update workspace artifacts", **options)
                        else:
                            # A rejected push may leave a valid local commit.
                            # Retrying the batch publishes it without an empty
                            # duplicate commit or losing the task's evidence.
                            contract = flow.load()
                            publication = flow.publish()
                            flow.reviewed(contract)
                            if not selected[current]:
                                flow.checked_scope(contract)
                            contract["publication"] = publication
                            flow.save(contract)
                            result = {**publication, "unchanged": True}
                        results[current] = result
                        state["progress"][current] = {"operation": state["operation"], "at": now(),
                                                      "head": git(flow.root, "rev-parse", "HEAD")}
                        self.save(state)
                    if selected is None:
                        # Detect writes in an earlier child while a later remote
                        # was publishing; never announce only the parent's success.
                        for current, flow in flows.items():
                            contract = flow.load()
                            flow.ensure_target(contract)
                            flow.reviewed(contract)
                            flow.checked_scope(contract)
                            if contract.get("finished", {}).get("head") != git(flow.root, "rev-parse", "HEAD"):
                                raise Blocked(f"Repository changed during workspace finish: {current}")
                        state["finished"] = {"at": now()}
                    self.save(state)
                    return {"completed": selected is None, "repositories": results}
                except Exception as exc:
                    self.failed(state, current, exc)
                    done = sorted(name for name, progress in state["progress"].items()
                                  if progress["operation"] == state["operation"])
                    raise Blocked(f"Workspace {state['operation']} incomplete at {current}; completed repositories: {', '.join(done) or 'none'}. {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--session", default=os.environ.get("CODEX_THREAD_ID", "manual"))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("route").add_argument("paths", nargs="+")
    dispatch = sub.add_parser("dispatch", help="Print a deterministic read-only native-agent execution plan.")
    dispatch.add_argument("--capacity", type=int, help="Current client subagent capacity, from 1 to 64.")
    for name in ("plan", "review", "status", "finish"):
        sub.add_parser(name)
    publish = sub.add_parser("publish", help="Publish and verify current HEAD without creating a commit.")
    publish.add_argument("--repo", required=True)
    for name in ("review-context", "review-start", "review-report", "review-resolve", "review-author"):
        command = sub.add_parser(name)
        command.add_argument("--repo", required=True)
        if name == "review-start":
            command.add_argument("--risk", choices=("quick", "standard", "deep"))
    check = sub.add_parser("check")
    check.add_argument("--repo", required=True)
    check.add_argument("--timeout", type=int, default=300)
    check.add_argument("argv", nargs=argparse.REMAINDER)
    commit = sub.add_parser("commit")
    commit.add_argument("-m", "--message", required=True)
    commit.add_argument("--preserve-index", action="store_true",
                        help="Commit only selected files while preserving disjoint staged work.")
    commit.add_argument("paths", nargs="+")
    args = parser.parse_args()
    workspace = Workspace(args.root, args.session)
    if args.command == "route":
        result = workspace.route(args.paths)
    elif args.command == "dispatch":
        result = workspace.dispatch(args.capacity)
    elif args.command == "publish":
        result = workspace.publish(args.repo)
    elif args.command in {"plan", "review"}:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise Blocked("Expected a JSON object.")
        result = getattr(workspace, args.command)(payload)
    elif args.command == "check":
        result = workspace.check(args.repo, args.argv[1:] if args.argv[:1] == ["--"] else args.argv, timeout=args.timeout)
    elif args.command.startswith("review-"):
        payload = json.load(sys.stdin) if args.command in {"review-report", "review-resolve", "review-author"} else None
        operation = args.command.removeprefix("review-")
        if operation == "start":
            payload = {"risk": args.risk}
        result = workspace.review_operation(args.repo, "prepare" if operation == "context" else operation, payload)
    elif args.command == "commit":
        result = workspace.commit(args.paths, args.message, preserve_index=args.preserve_index)
    else:
        result = getattr(workspace, args.command)()
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Blocked, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(f"Workspace: {exc}", file=sys.stderr)
        raise SystemExit(2)

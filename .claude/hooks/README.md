# `~/GitHub/.claude/hooks/`

Reusable hook scripts living at the constellation plane. These are
**library hooks** — a per-repo `.claude/settings.json` can opt-in by
calling them, but the hub never installs hooks into a repo silently.

| Hook                | When to fire                                    | Effect                                       |
| ------------------- | ----------------------------------------------- | -------------------------------------------- |
| `repo_discovery.py` | Session start; manual; before cross-repo work   | Refresh registry against on-disk state       |
| `peer_sync.py`      | After a registry change or new repo bootstrap   | Refresh `<repo>/.claude/registry/peers.yaml.snapshot` |

## Verification + research workflow hooks

Wired in this hub's own `.claude/settings.json` (see the
[expert-agent contract](../contracts/expert_agent_contract.md)). Posture is
**balanced**: hooks block only on hard, unambiguous signals; methodological
heuristics are advisory unless an opt-in env flag is set.

| Hook                          | Event                | Effect                                                                                       |
| ----------------------------- | -------------------- | -------------------------------------------------------------------------------------------- |
| `secret_scan.sh`              | Pre + PostToolUse    | Block writing / staging secrets, `.env`, key/token material. No entropy detector (SHA roots).|
| `bash_ledger.py`              | PostToolUse (Bash)   | Append `{cmd, exit, ok, signals}` per Bash call to `~/GitHub/.claude/run/<session>.jsonl` (git-ignored). The command-evidence the evidence audit cross-checks. Append-only, never blocks. `BASH_LEDGER_DISABLE=1`. |
| `changed_python_syntax.sh`    | PostToolUse          | `py_compile` the changed Python file.                                                        |
| `metric_provenance.py`        | PostToolUse          | **Hard-block** a report referencing a result artifact that does not exist on disk; advise on seedless RNG (`METRIC_PROVENANCE_STRICT=1` to enforce the latter). |
| `dead_lever_guard.py`         | PreToolUse (Bash)    | Surface a pending command that re-runs a CLOSED lever (`registry/levers.yaml` `rerun_guard`). Advisory; `DEAD_LEVER_STRICT=1` to block. |
| `research_session_loader.py`  | SessionStart         | Inject a research brief (OPEN next steps, CONFIRMED edges, DO-NOT-RE-RUN levers) from `registry/levers.yaml`. |
| `loop_guard.py`               | Stop                 | Block completion on staged secrets / workflow-dir TODO markers; completion-language heuristic opt-in via `LOOP_GUARD_STRICT=1`. |
| `evidence_audit.py`           | manual / `/evidence` | Flag metric/completion claims with no nearby artifact reference. With `--ledger` also cross-checks "tests pass" claims against the Bash run ledger and prints a command/test/failure summary. |
| `_levers.py`                  | library              | Dependency-free reader for `registry/levers.yaml` (no PyYAML; stdlib hand-parse).            |

Env switches to disable individually: `*_DISABLE=1` (`METRIC_PROVENANCE_DISABLE`,
`DEAD_LEVER_GUARD_DISABLE`, `RESEARCH_LOADER_DISABLE`, `LOOP_GUARD_DISABLE`).

## Conventions

- Dependency-free Python 3.12 (only stdlib, plus the system `git`).
- Idempotent. Running twice with no on-disk change must be a no-op.
- Stderr-tagged with `[constellation:<hook>]`. Never silent.
- Never overwrite a hand-maintained file. Write snapshots / proposals
  to a sibling location and let the repo's own logic merge.

## How a per-repo `.claude/settings.json` wires these

Example block for a per-repo `settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      { "type": "command", "command": "python3 ~/GitHub/.claude/hooks/repo_discovery.py" }
    ],
    "PostToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          { "type": "command", "command": "python3 ~/GitHub/.claude/hooks/peer_sync.py" }
        ]
      }
    ]
  }
}
```

Each repo decides whether to opt in. The constellation hub never
forces hook installation.

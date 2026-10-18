# `~/GitHub/.claude/hooks/`

Reusable hook scripts living at the constellation plane. These are
**library hooks** — a per-repo `.claude/settings.json` can opt-in by
calling them, but the hub never installs hooks into a repo silently.

| Hook                | When to fire                                    | Effect                                       |
| ------------------- | ----------------------------------------------- | -------------------------------------------- |
| `repo_discovery.py` | Optional session start; manual; before cross-repo work | Report registry drift without rewriting it |
| `peer_sync.py`      | After a registry change or new repo bootstrap   | Refresh `<repo>/.claude/registry/peers.yaml.snapshot` |

## Verification + research workflow hooks

Wired in this hub's own `.claude/settings.json` (see the
[expert-agent contract](../contracts/expert_agent_contract.md)). Posture is
**balanced**: hooks block only on hard, unambiguous signals; methodological
heuristics are advisory unless an opt-in env flag is set.

| Hook                          | Event                | Effect                                                                                       |
| ----------------------------- | -------------------- | -------------------------------------------------------------------------------------------- |
| `secret_scan.sh`              | Pre + PostToolUse; Stop via `loop_guard` | Scan pending text before a write, the full result afterward, and changed index blobs. Refuse protected filenames before reading them. Diagnostics omit values. |
| `bash_ledger.py`              | PostToolUse (Bash) | Private, git-ignored execution evidence under `.claude/run/`: command SHA-256, test classification, exit/unknown status and signals. Schema 2 stores no commands, arguments, descriptions, stdout or stderr; events are deduplicated under a file lock. `BASH_LEDGER_DISABLE=1`. |
| `changed_python_syntax.sh`    | PostToolUse          | `compile()` explicit and changed Python files plus changed index blobs; never execute source or write `.pyc` / `__pycache__`. |
| `metric_provenance.py`        | PostToolUse          | **Hard-block** a report referencing a result artifact that does not exist on disk; advise on seedless RNG (`METRIC_PROVENANCE_STRICT=1` to enforce the latter). |
| `dead_lever_guard.py`         | PreToolUse (Bash)    | Surface a pending command that re-runs a CLOSED lever (`registry/levers.yaml` `rerun_guard`). Advisory; `DEAD_LEVER_STRICT=1` to block. |
| `research_session_loader.py`  | SessionStart         | Inject a research brief (OPEN next steps, CONFIRMED edges, DO-NOT-RE-RUN levers) from `registry/levers.yaml`. |
| `loop_guard.py`               | Stop                 | Reuse the staged secret gate. Inspect only `last_assistant_message`; never read transcripts. Completion-language heuristic opt-in via `LOOP_GUARD_STRICT=1`; TODO markers in the current message are advisory. Honor `stop_hook_active` to avoid loops. |
| `evidence_audit.py`           | manual / `/evidence` | Flag metric/completion claims with no nearby artifact reference. With `--ledger` also cross-checks "tests pass" claims against the Bash run ledger and prints a command/test/failure summary. |
| `commit_guard.py`             | manual / pre-commit  | Standalone commit/push validator: HARD-blocks staged secrets/.env/keys, wrong-branch push, messages missing required trailers, and reports claiming promotion with no gate artifact; advisory on broad claims / seedless RNG (`COMMIT_GUARD_STRICT=1`). NOT wired to auto-commit — the committer (`/commit-research`) is the explicit command. |
| `_levers.py`                  | library              | Dependency-free reader for `registry/levers.yaml` (no PyYAML; stdlib hand-parse).            |

Env switches to disable individually: `*_DISABLE=1` (`METRIC_PROVENANCE_DISABLE`,
`DEAD_LEVER_GUARD_DISABLE`, `RESEARCH_LOADER_DISABLE`, `LOOP_GUARD_DISABLE`).

## Deterministic safety boundary

`secret_scan.sh` consumes the event on stdin; event contents never become
process arguments or temporary files. It rejects `.env*`, `*.pem`, `*.key`
and `credentials.json` before opening a file, together with known private
archive paths: `_conversations`, `.codex/sessions`, `.codex/archived_sessions`,
`rollout*.jsonl` and `.claude/run`. Ordinary research `manifest.json` files
remain allowed. Both the lexical path and symlink-resolved destination are
checked, preserving `..` until symlinks have been resolved. Pending `content`, `new_string` and
`edits[].new_string` are checked before a write; PostToolUse checks the complete
file. Codex's generated shim normalizes each `apply_patch` target into this
same event shape, including newly added files.

Git paths are NUL-delimited, so spaces, tabs and newlines stay intact. The
scanner reads changed stage-0 blobs directly from the index, after checking
their names; replacing or deleting the working copy cannot conceal staged
credentials. Staged deletions are safe to remove and are not scanned. Gitlinks
are commit references and have no file content to scan. Pattern detection
covers known token prefixes, private-key blocks and credential assignments;
it is a targeted gate, not an exhaustive secret detector.

Files above 5 MB and malformed events or failed inspections return exit 2
with a sanitized error instead of silently passing. Python syntax checks use
the same size bound and report only a path and position on failure, never the
source line. These hooks write no source, bytecode, transcript or log files.

The syntax hook includes an explicitly edited untracked `.py` file and the
changed/staged Python files in the current repository. Other untracked Python
files are outside its scope. Stop never searches unrelated TODOs and never
opens `transcript_path`; after a refused Stop, `stop_hook_active=true` lets the
next completion through. The secret scanner remains the deterministic gate;
completion wording is only a heuristic and is advisory by default.

Run the disposable-repository regression suite with:

```bash
python3 .claude/tests/test_hook_safety.py
```

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
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/GitHub/.claude/hooks/repo_discovery.py",
            "timeout": 15
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/GitHub/.claude/hooks/peer_sync.py",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
```

Each repo decides whether to opt in. The constellation hub never
forces hook installation. The discovery wrapper delegates to
`scripts/discover_repos.py`, which reports proposals without changing the
registry; its `--apply` flag is reserved. The example is optional wiring,
not the hub's active configuration.

# `~/GitHub/.claude/docs/`

Long-form documentation for the constellation hub.

| File                    | Purpose                                                                    |
| ----------------------- | -------------------------------------------------------------------------- |
| `architecture.md`       | Two-plane architecture (hub + per-repo), data flow, persistence.           |
| `how_to_add_a_repo.md`  | End-to-end walkthrough for adding a new repository to the constellation.   |

## Generated artefacts (also live here)

These files are *not* checked in by hand — they are produced by agents
running against the live state of the constellation:

- `drift_report.md` — produced by `perimeter-keeper`.
- `import_audit.md` — produced by `import-graph-auditor`.
- `orchestration_state.md` — produced by `multi-repo-orchestrator`
  when a pipeline is interrupted; consumed on resume.
- `escalation_drafts/` — short markdown drafts queued for the vault
  to pick up via its own routing pipeline.

These are ephemeral: stale reports get overwritten on the next run.
Drafts persist until the user routes them into the vault.

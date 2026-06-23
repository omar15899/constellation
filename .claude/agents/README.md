# `~/GitHub/.claude/agents/`

Cross-repo agent definitions. Each `.md` file is a Claude Code sub-agent
spec — frontmatter at the top, full operating instructions below.

| Agent                          | Tier   | Writes? | Role                                          |
| ------------------------------ | ------ | ------- | --------------------------------------------- |
| `constellation-cartographer`   | Opus   | `.claude/`  | Discovers + classifies + indexes              |
| `cross-repo-router`            | Opus   | none    | Routes free-form requests                     |
| `multi-repo-orchestrator`      | Opus   | repos   | Coordinates multi-repo work (with consent)    |
| `cross-repo-search`            | Sonnet | none    | Ripgrep + ranked search across constellation  |
| `repo-classifier`              | Sonnet | none    | Classifies a single unknown repo              |
| `perimeter-keeper`             | Sonnet | `.claude/`  | Detects drift; writes drift report            |
| `import-graph-auditor`         | Sonnet | `.claude/`  | Audits tier discipline across labs            |

## Doctrine

- Only `cross-repo-router` and `multi-repo-orchestrator` may spawn
  other constellation agents.
- No agent here writes inside a repo without explicit user
  authorisation routed through the orchestrator.
- All agents are read-only on `~/OmarOS/`. Vault writes happen via
  the vault-side orchestrator.

## How a per-repo `.claude/` can use these agents

Two options:

1. **Symlink in.** Per-repo `.claude/agents/_shared/` symlinked to
   `~/GitHub/.claude/agents/`. The repo can then reference the agents by
   the same name as the rest of the constellation.
2. **Delegate by name.** A per-repo orchestrator that needs a
   cross-repo capability emits a hand-off envelope, and the
   `multi-repo-orchestrator` picks it up from the constellation plane.

The recommended pattern is **option 2** — agents stay defined once,
in one place. The `.claude/templates/claude_subagent_link.sh` script
prepares option 1 for repos that prefer it.

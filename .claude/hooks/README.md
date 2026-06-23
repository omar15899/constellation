# `~/GitHub/.claude/hooks/`

Reusable hook scripts living at the constellation plane. These are
**library hooks** — a per-repo `.claude/settings.json` can opt-in by
calling them, but the hub never installs hooks into a repo silently.

| Hook                | When to fire                                    | Effect                                       |
| ------------------- | ----------------------------------------------- | -------------------------------------------- |
| `repo_discovery.py` | Session start; manual; before cross-repo work   | Refresh registry against on-disk state       |
| `peer_sync.py`      | After a registry change or new repo bootstrap   | Refresh `<repo>/.claude/registry/peers.yaml.snapshot` |

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

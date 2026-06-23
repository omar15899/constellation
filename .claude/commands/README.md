# `~/GitHub/.claude/commands/`

Constellation-level slash commands. Each delegates to a skill or agent
in this hub. The command spec is intentionally thin — operating
details live in the skill / agent it wraps.

| Command            | Wraps                              | Purpose                                                |
| ------------------ | ---------------------------------- | ------------------------------------------------------ |
| `/repos`           | `repo-discovery` skill             | Print constellation index (refresh registry if drift). |
| `/repo-status`     | `multi-repo-status` skill          | Aggregate `git status` across all repos.               |
| `/find-in-repos`   | `cross-repo-grep` skill            | Search across the constellation.                       |
| `/repo-route`      | `cross-repo-router` agent          | Inspect routing for a request without executing.       |
| `/repo-bootstrap`  | `repo-bootstrap` skill             | Apply standard layout to a new/legacy repo.            |
| `/constellation`   | `constellation-brief` skill        | One-page state snapshot.                               |
| `/tier-check`      | `tier-discipline` skill            | Audit the import graph against the tier hierarchy.     |

## How these are exposed to a Claude session

Two patterns:

1. **Constellation-level session** at `~/GitHub/`: Claude reads
   `~/GitHub/.claude/CLAUDE.md` and these commands are advertised by the
   kernel.
2. **Per-repo session** inside `<repo>/`: the repo's own `.claude/`
   may symlink this `commands/` directory under `.claude/commands/_shared/`,
   making the constellation commands available alongside the lab's own.

See `templates/claude_subagent_link.sh` for the symlink helper.

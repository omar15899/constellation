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

## Verification + research workflow commands

Prompt-discipline commands implementing the expert-directed loop (the user owns
planning, Claude owns execution; verified success needs hard evidence). Unlike
the hooks, these are not deterministically enforced — they instruct Claude.

| Command               | Purpose                                                                              |
| --------------------- | ------------------------------------------------------------------------------------ |
| `/verify-loop`        | Bounded Plan→Execute→Verify→Refute→Repair loop with an evidence table.                |
| `/intent-check`       | Reconstruct explicit vs inferred request; mark planning vs execution decisions.      |
| `/refute`             | Adversarial self-review — try to falsify the current solution.                       |
| `/evidence`           | Audit every numeric/completion claim against a backing artifact.                     |
| `/quant-loop`         | Validity-first quant loop (lookahead, survivorship, alpha-vs-beta, run-class).       |
| `/gate-check`         | Run a result through the promotion gate; record the verdict in `registry/levers.yaml`.|
| `/ship-loop`          | Final verified-success gate before committing.                                       |
| `/debug-metric`       | Trace a suspicious/NaN/empty metric from code → data → artifact.                      |
| `/review-claude-system` | Meta-review: does the workflow itself still hold?                                  |

Backing artifacts: [`contracts/`](../contracts/) (expert-agent, task, promotion
gate), [`registry/levers.yaml`](../registry/levers.yaml) +
[`research_ledger.md`](../research_ledger.md) (lever verdicts),
[`loop_ledger.md`](../loop_ledger.md) (per-session execution record).

## How these are exposed to a Claude session

Two patterns:

1. **Constellation-level session** at `~/GitHub/`: Claude reads
   `~/GitHub/.claude/CLAUDE.md` and these commands are advertised by the
   kernel.
2. **Per-repo session** inside `<repo>/`: the repo's own `.claude/`
   may symlink this `commands/` directory under `.claude/commands/_shared/`,
   making the constellation commands available alongside the lab's own.

See `templates/claude_subagent_link.sh` for the symlink helper.

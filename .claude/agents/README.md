# Shared agents

The specs in this directory are the canonical roster; there is no duplicate
agent registry. Each role inherits the session model and effort.

| Agent | Distinct responsibility | Writes |
| --- | --- | --- |
| constellation-cartographer | Discovery, classification and metadata drift | Authorized hub registry/index changes |
| import-graph-auditor | Cross-repository tier and perimeter dependencies | Requested hub reports only |
| multi-repo-orchestrator | Integration across repositories and production-sensitive decomposition | Authorized target repositories |

[Routing](../contracts/routing.md) happens in the current agent. Search and status
use skills and existing tools; neither needs a dedicated agent. Delegate bounded
work only when independent context or parallelism helps. Role tool restrictions
remain binding; available general workers can handle other authorized subtasks.

These are instructions, not proof that a client loaded or sandboxed each role.
See [Codex parity](../docs/codex_parity.md). All roles preserve neighboring changes
and treat OmarOS as read-only from this plane.

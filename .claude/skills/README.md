# Repository skills

These six reusable workflows complement the eight
[command skills](../commands/README.md). Claude and Codex use the same sources;
Codex invokes them with `$name`. Do not add a command wrapper for an existing skill.

| Skill | Responsibility |
| --- | --- |
| repo-status | Git state, inventory and constellation brief without metadata writes |
| find-in-repos | Scoped source search and consumer location |
| repo-discovery | Discovery, classification and registry metadata updates when requested |
| repo-bootstrap | Missing repository scaffolding, preserving existing files |
| tier-check | Tier and perimeter dependency audit with explicit coverage |
| cross-repo-refactor | Propagate a provider/API/schema change across repositories |

Descriptions determine selection. Detailed contracts and scripts load on demand.
Add a skill when it owns a distinct recurring decision or procedure; a new name
for an existing step does not justify another discoverable entry.

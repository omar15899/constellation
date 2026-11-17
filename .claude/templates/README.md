# Workspace templates

The existing `scripts/bootstrap_repo.sh` consumes this bundle. The
[Constellation workspace profile](../../Constellation/profiles/workspace.md)
defines the current repository discovery, ownership and bootstrap procedure.

| File | Purpose |
| --- | --- |
| `CLAUDE.md.template` | Minimal native entry with project and profile placeholders. |
| `importlinter.template` | Tier-discipline starting contract for a QuantOS lab. |
| `lint.yml.template` | Existing lint workflow template; installation or activation requires the owner's applicable policy. |

Templates are copied verbatim by the bootstrap script. Resolve every
placeholder and inspect the generated files before installing them; copying a
template is not a completed Constellation registration.

Native agents and skills are installed by Constellation. The historical
`claude_subagent_link.sh` helper is not the current installation procedure.
Do not create a parallel shared agent/skill tree.

Keep templates small and domain-specific. Never include secrets, credentials,
private conversation data or automatic publication steps.

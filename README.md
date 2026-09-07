# constellation

The shared AI control plane for independent repositories under `~/GitHub/`.
It provides discovery, routing, cross-repository agents, shared skills and
verification hooks. Repository classification lives in
[registry/repos.yaml](.claude/registry/repos.yaml); each neighboring repository
keeps its own history, toolchain and operating contract.

The structure is small at the point of use:

- [AGENTS.md](AGENTS.md) is the Codex entry point.
- [CLAUDE.md](CLAUDE.md) points both agents to the
  [canonical kernel](.claude/CLAUDE.md).
- [.claude/](.claude/) owns contracts, registry, hooks, agents and skills.
- [.codex/](.codex/) is generated from those sources.

The kernel loads specialized contracts when needed. QuantOS tier discipline,
research promotion gates and each adjacent project's autonomy remain explicit.
[QUANTOS.md](QUANTOS.md) describes the QuantOS architecture. OmarOS is the vault
for vision and decisions, and is read-only from this repository.

## Working on the control plane

Edit canonical files, regenerate only the intended repository, and verify:

```bash
python3 .claude/scripts/codex_sync.py --repo . --check
python3 .claude/scripts/codex_sync.py --repo .
python3 .claude/tests/test_codex_sync.py
python3 .claude/tests/test_codex_projection_safety.py
python3 .claude/tests/test_codex_workflow.py
python3 .claude/tests/test_hook_safety.py
python3 .claude/tests/test_promotion_enforcement.py
python3 .claude/tests/test_repo_bootstrap.py
python3 .claude/tests/test_discovery_state.py
python3 .claude/tests/test_research_committer_safety.py
python3 .claude/scripts/doctor.py
python3 .claude/scripts/codex_sync.py --repo . --verify
```

Choose checks appropriate to the change. Everything above uses the Python
standard library; no lab virtual environment is needed. The doctor reports
WARN for uncommitted work. No sync command implies permission to commit,
push, update neighboring repositories or change global configuration.

## Hooks

[settings.json](.claude/settings.json) wires shared local hooks for pending
content, staged secrets, Python syntax, research context and evidence.
Codex's adapter handles native patches, including multiple files and renames.
The execution ledger stores hashes and status metadata, without command text
or output. Stop does not read conversation transcripts.

[Hook behavior](.claude/hooks/README.md) and
[Codex integration](.claude/docs/codex_parity.md) document the precise coverage.
Script tests and valid configuration do not prove native activation: review
new or changed hooks with Codex's `/hooks` interface when prompted.

Nothing runs in the background. The hub is an on-demand library and contract.

The [control-plane audit](.claude/docs/control_plane_audit.md) records the
consolidation of skills and agents, capabilities retained and verified limitations.

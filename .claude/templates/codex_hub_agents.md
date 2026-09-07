# AGENTS.md — constellation

This private repository owns the shared AI control plane at `~/GitHub/`.
Neighboring directories are independent repositories with separate histories
and contracts. The hub has no QuantOS tier.

## Start here

Read [CLAUDE.md](CLAUDE.md) and the canonical
[kernel](.claude/CLAUDE.md) before non-trivial work. Follow its routing,
execution, verification and privacy rules. Load additional contracts when
the task reaches their subject; the kernel links the authoritative sources.

For work inside another repository, load its `AGENTS.md` and `CLAUDE.md`
before editing. Use [registry/repos.yaml](.claude/registry/repos.yaml)
for its perimeter and tier; verify current state instead of trusting old prose.

## Codex translation

`.claude/` is canonical. Edit source files and regenerate only the requested
repository. This entry point comes from `.claude/templates/codex_hub_agents.md`.

```bash
python3 .claude/scripts/codex_sync.py --repo . --check
python3 .claude/scripts/codex_sync.py --repo .
python3 .claude/scripts/codex_sync.py --repo . --check
```

Use `--all` only for an authorized constellation-wide projection.
Do not hand-edit managed `.codex/` files or `AGENTS.md`. Codex-only material
without a Claude counterpart belongs in `.codex/local/`.

| Canonical source | Codex surface |
| --- | --- |
| `.claude/agents/` | `.codex/agents/` |
| `.claude/skills/` | Shared through `.codex/skills/` symlinks |
| `.claude/commands/` | Skills invoked with `$name` |
| `.claude/settings.json` | Project configuration and hooks |

Inherit the user's model; do not pin a model family or inflate reasoning
effort as a substitute for clear instructions and evidence. Consult
[Codex parity](.claude/docs/codex_parity.md) for supported behavior and limits.

## Hooks and verification

Configured, tested and trusted are different states. Parsing a hooks file
or running scripts directly does not establish that Codex executes the
hooks in this session. Use the native `/hooks` review when required;
never manufacture trust or bypass approval.

Hub checks use Python's standard library, independently of neighboring labs:

```bash
python3 .claude/tests/test_codex_sync.py
python3 .claude/tests/test_codex_projection_safety.py
python3 .claude/tests/test_codex_workflow.py
python3 .claude/tests/test_hook_safety.py
python3 .claude/tests/test_promotion_enforcement.py
python3 .claude/tests/test_repo_bootstrap.py
python3 .claude/scripts/doctor.py
python3 .claude/scripts/codex_sync.py --repo . --verify
```

Choose checks relevant to the change. The doctor reports WARN for a dirty
worktree; its verdict and exit code are distinct. The Codex verifier checks
skill discovery and agent configuration syntax, not agent discovery or native
hook approval. Report executed checks and limitations.

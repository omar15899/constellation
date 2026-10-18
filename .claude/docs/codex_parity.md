# Claude-to-Codex projection compatibility

The hub and its own child repositories use independent native Codex profiles:
see [`.codex/README.md`](../../.codex/README.md) and the
[workspace workflow](../../.codex/WORKSPACE.md). Their `.codex/profile.json`
markers prevent projection from replacing those profiles. `ruflo` remains
external; operating on it requires explicit scope.

This guide covers compatibility for repositories that still use projection.
For those surfaces, `.claude/` contains the implementation and operating
contract, and `codex_sync.py --repo PATH` generates the selected Codex view.
Native profiles are edited directly under their own contracts.

## Design and sources

The projection design was reviewed on 2026-09-07 using `codex-cli 0.147.0` and
official docs; that historical baseline does not establish current activation.
The [model guide](https://developers.openai.com/api/docs/guides/latest-model)
informs the short outcome-focused kernel: autonomous follow-through, useful
parallel delegation and proportionate verification. Model selection remains
inherited from the user's runtime; this is not an API client migration.

[AGENTS.md discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
explains instruction layering. Projected entry points refer to the kernel and
task-specific contracts. Historical repo briefs remain available as reference
data and no longer supply the native hub's startup instructions.

## Mapping

| Source | Generated surface | Purpose |
| --- | --- | --- |
| `templates/codex_hub_agents.md` | Root `AGENTS.md` | Legacy projected hub entry; unused by the native hub |
| `.claude/CLAUDE.md` | Referenced directly | Shared operating contract |
| `agents/*.md` | `.codex/agents/*.toml` | Instructions and role constraints |
| `skills/<name>` | `.codex/skills/<name>` symlink | Same skill for both agents |
| `commands/*.md` | `.codex/skills/<name>/SKILL.md` | `$name` invocation |
| `settings.json` | `.codex/config.toml`, `hooks.json`, rules if present | Runtime wiring |
| `templates/codex_hook_shim.py` | `.codex/hook_shim.py` | Event and patch adapter |

The generated `.codex/AGENTS.md` is a reference to the kernel, without separate
policy. In projected repositories, Codex-only personal additions belong in
`.codex/local/`. The generator does not consume or remove that directory.
Claude hub roles specify `model: inherit`; their generated TOML omits both
model and reasoning effort overrides.

The [skills guide](https://learn.chatgpt.com/docs/build-skills) supports precise
selection descriptions and loading detailed procedures on demand. The
[subagent guide](https://learn.chatgpt.com/docs/agent-configuration/subagents)
supports separate roles when their responsibility benefits from independent
context. Neither a skill scaffold nor its metadata validator proves useful
behavior. The [historical audit](control_plane_audit.md) records the projection's
earlier consolidation decisions.

## Projection ownership

The v2 manifest records file SHA-256 fingerprints and symlink targets. Projection
plans all writes and retirements, checks ownership/collisions first, then applies.
A removed source retires only unchanged owned outputs; edited files, unknown
entries and `.codex/local/` survive. Conflicts stop the operation for inspection.
There is no recursive deletion or silent adoption of user files.

Old manifests lack those fingerprints. Migrate only with evidence captured from
the prior canonical sources and matching generated outputs before changing the
sources. A generated banner alone does not prove unchanged ownership. If that
evidence is unavailable, preserve conflicts and reconstruct/inspect the old
projection before proceeding; never manufacture ownership from current contents.
Markdown links in copied commands and agent instructions are rebased to their
canonical resources; symlinked skill resources remain shared.

## Hook behavior and limits

The [hook contract](https://learn.chatgpt.com/docs/hooks) distinguishes lifecycle
feedback from prevention. PreToolUse can reject a pending operation; PostToolUse
reports after it ran and cannot undo its effects. Matching handlers may execute
concurrently, so correctness must not depend on their order.

The adapter accepts native `Bash` and `apply_patch` payloads with
`tool_input.command`. It also accepts direct-tool `cmd`, shell argv and
string/`input`/`patch` forms. Argument globs run after normalization. Native
multi-file patches become individual file checks, including rename source and
destination. Pending checks see inserted content; post-write checks inspect
the resulting file. An unreadable payload or timed-out adapter reports failure
instead of silently skipping validation. This per-file adapter is for shared
file-checking hooks; hooks returning complex JSON decisions need a dedicated
integration before reuse across multi-file patches.

The canonical hooks implement secret-path rejection, pending content scans,
actual staged Git blob scans, Python compilation without bytecode artifacts,
research reminders/provenance and an execution ledger containing hashes and
status metadata. Stop checks staged secrets and current-message feedback,
without reading transcripts or blocking on unrelated TODOs. Reentry is bounded.
See [hooks/README.md](../hooks/README.md) for exact hard/advisory distinctions.

These hooks are workflow checks, not a replacement for the sandbox. Shell,
notebook, browser or external-service writes do not become `apply_patch`
events; the patch scanner cannot promise universal filesystem interception.
The staged scan and explicit final checks cover a different boundary. No hook
commits, pushes, fetches, approves tools, uploads data or starts a daemon.

## Activation

The [configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
defines `features.hooks`; the generated project config sets it explicitly.
Effective behavior also depends on trusted project configuration and the
client's native approval of new or modified hooks. Review the target project's
commands in `/hooks` and approve through Codex when prompted. Do not preseed
hashes, use a bypass setting, or equate JSON parsing with active protection.

`codex_sync.py --trust` changes user configuration; it is not part of ordinary
projection. `--verify` checks instruction and skill discovery with the
installed binary; agent TOML files are parsed, which does not demonstrate role
discovery. It does not verify trust or end-to-end hook execution. Activation for a
particular session must be observed through the native client.

## Verification

Run a targeted projection only when the task authorizes changing that surface.
From the hub, substitute the explicitly selected projected repository for PATH:

```bash
python3 .claude/scripts/codex_sync.py --repo PATH --check
python3 .claude/scripts/codex_sync.py --repo PATH
python3 .claude/scripts/codex_sync.py --repo PATH --check
python3 .claude/scripts/codex_sync.py --repo PATH --verify
```

The compatibility regression suites remain in the hub:

```bash
python3 .claude/tests/test_codex_sync.py
python3 .claude/tests/test_codex_projection_safety.py
python3 .claude/tests/test_codex_workflow.py
python3 .claude/tests/test_hook_safety.py
python3 .claude/tests/test_promotion_enforcement.py
python3 .claude/tests/test_repo_bootstrap.py
python3 .claude/tests/test_discovery_state.py
python3 .claude/tests/test_research_committer_safety.py
python3 .claude/scripts/doctor.py
```

Run the relevant subset for the change. Tests use temporary projection fixtures
and check preservation of the native hub, without requiring unrelated labs to
be installed or synchronized. A second projection is checked for zero writes.
The doctor recognizes native ownership and does not require a generated adapter
for native profiles. Projection drift, configuration errors, dirty state and
unverified native activation are distinct findings.

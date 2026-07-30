# Codex ↔ Claude Code parity

How the constellation is driven by **either** agent, what each one supports,
and where the two genuinely differ.

Ground truth established 2026-07-30 against **codex-cli 0.146.0-alpha.3.1**
(`/Applications/ChatGPT.app/Contents/Resources/codex`). Every claim marked
*probed* was verified by running the binary, not read from documentation.

---

## 1. The doctrine

`.claude/` is **canonical**. `.codex/` is a **generated projection** of it,
produced by [`.claude/scripts/codex_sync.py`](../scripts/codex_sync.py).

There is exactly one implementation of every behaviour:

- one instruction body per agent, in `.claude/agents/<n>.md`, embedded into
  the TOML that Codex reads;
- one skill directory per skill, in `.claude/skills/<n>/`, **symlinked** into
  `.codex/skills/`;
- one hook script per hook, in `.claude/hooks/`, invoked by both planes.

Nothing is copied that could instead be shared or generated. Edit `.claude/`,
re-run the sync, commit both.

```bash
~/GitHub/.claude/scripts/codex_sync.py --all          # project everything
~/GitHub/.claude/scripts/codex_sync.py --all --check  # drift only, writes nothing
~/GitHub/.claude/scripts/codex_sync.py --trust        # register project trust
```

---

## 2. Construct mapping

| Concept | Claude Code | Codex 0.146 | Fidelity |
| --- | --- | --- | --- |
| Root contract | `CLAUDE.md` | `AGENTS.md` | exact |
| Nested contract | `<dir>/CLAUDE.md` | `<dir>/AGENTS.md` | exact |
| Override file | — | `AGENTS.override.md` (wins over `AGENTS.md`) | Codex-only |
| Subagent | `.claude/agents/<n>.md` (YAML frontmatter + body) | `.codex/agents/<n>.toml` (`name`, `description`, `developer_instructions`) | exact |
| Skill | `.claude/skills/<n>/SKILL.md` | `.codex/skills/<n>/SKILL.md` | **identical format** — symlinked |
| Slash command | `.claude/commands/<n>.md`, `/n` | *no equivalent* → projected as a skill, `$n` | **degraded: invocation syntax differs** |
| Hooks | `.claude/settings.json` `hooks` | `.codex/hooks.json` | near-exact, see §4 |
| Permissions | `settings.json` `permissions` | `config.toml` `approval_policy` / `sandbox_mode` / `[permissions.<n>]` | coarser |
| Command denylist | `permissions.deny: Bash(rm *)` | `.codex/rules/*.rules` (Starlark `prefix_rule`) | near-exact, see §5 |
| Env for tools | `settings.json` `env` | `[shell_environment_policy.set]` | exact |
| MCP servers | `.mcp.json` | `[mcp_servers.<id>]` in `config.toml` | exact |
| Model pin | `model: claude-sonnet-4-6` | `model_reasoning_effort` | **intentionally not pinned**, see §3 |

---

## 3. AGENTS.md discovery (*probed*)

Codex walks **git root → cwd**, taking at most one file per directory:
`AGENTS.override.md` first, then `AGENTS.md`, then anything in
`project_doc_fallback_filenames`. Files concatenate root-downward; later
files override earlier guidance. Empty files are skipped. Default size cap is
32 KiB (`project_doc_max_bytes`).

Consequence for this constellation: each sub-repo is *its own git root*, so
running Codex inside `~/GitHub/BacktestLab` loads only
`BacktestLab/AGENTS.md`, **not** `~/GitHub/AGENTS.md`. That mirrors Claude's
behaviour and is why every repo gets a self-sufficient `AGENTS.md`.

`.codex/AGENTS.md` is *not* auto-loaded — `.codex/` is below the git root but
never the cwd. It is a referenced document, exactly like `.claude/CLAUDE.md`.

**Why no model pin.** Claude agents pin `model: claude-sonnet-4-6`. Pinning
an equivalent OpenAI model id into 247 generated files would rot on the next
model release. The projection instead translates *intent* — opus→`xhigh`,
sonnet→`high`, haiku→`low` — into `model_reasoning_effort`, and lets Codex
inherit whatever `model` is set in `~/.codex/config.toml`.

Verify what a session actually loaded:

```bash
codex debug prompt-input "hi" | python3 -m json.tool | less
```

---

## 4. Hooks

Event names are **identical** to Claude Code's, plus two Codex-only ones:

`PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `Stop`, `SubagentStop`,
`SessionStart`, `SessionEnd`, `PreCompact`, `PostCompact`
— plus **`PermissionRequest`** and **`SubagentStart`**.

Input on stdin, output on stdout, and exit-code semantics match Claude:
exit `0` = proceed, exit `2` = block with the reason on stderr, anything else
= hook failure that is reported but does not block.

Two real differences:

**Matchers are tool-name regexes only.** Codex cannot express Claude's
argument-level `Bash(git commit*)`. The projection emits matcher `Bash|shell|
exec_command` and hands the glob to [`hook_shim.py`](../../.codex/hook_shim.py),
which re-reads `tool_input.command` from the hook payload and exits 0 silently
when it does not match. Semantics are preserved; the filtering just moves one
layer down. The shim also exports `CLAUDE_PROJECT_DIR`, which Codex does not
set.

**Hooks require interactive trust** (*probed*). Codex stores a
`trusted_hash` per hook configuration and **silently skips untrusted hooks** —
`codex exec` runs to completion with no warning and no hook execution. This
was confirmed by running `codex exec` with a logging hook wired through
`~/.codex/hooks.json`, `~/.codex/config.toml` inline `[[hooks.*]]`, and `-c`
overrides: none fired.

> **Operational consequence.** After any `codex_sync.py` run that changes a
> `hooks.json`, start `codex` in that repo, run `/hooks`, and choose
> *Trust all and continue*. Until then the secret scanner, the commit gate
> and the metric-provenance hook are **not running** under Codex.

There is a `bypass_hook_trust` override in the binary. It is deliberately not
used here: pre-seeding trust would subvert a security control whose entire
purpose is that a human looked at the commands before they ran outside the
sandbox.

---

## 5. Permissions, sandbox, rules

Codex splits what Claude keeps in one `permissions` block:

- `approval_policy` — when to stop and ask (`untrusted` / `on-request` / `never`).
- `sandbox_mode` — `read-only` / `workspace-write` / `danger-full-access`.
- `[permissions.<name>]` — named filesystem/network profiles.
- `.codex/rules/*.rules` — Starlark `prefix_rule()`, the only place a
  *command denylist* can live.

The projection maps `permissions.deny` entries to `prefix_rule()`. Codex
matches whole argv tokens, so the translation is exact only when a glob's
wildcards are token-trailing:

| `settings.json` | `prefix_rule` pattern | decision |
| --- | --- | --- |
| `Bash(rm *)` | `["rm"]` | `forbidden` |
| `Bash(git reset --hard*)` | `["git","reset","--hard"]` | `forbidden` |
| `Bash(git clean *-fd*)` | `["git","clean"]` | `prompt` ← widened |

A mid-token wildcard cannot be expressed, so the rule degrades to the
shortest safe prefix and drops to `prompt` rather than silently forbidding a
much larger command family. Check a rule:

```bash
codex execpolicy check --pretty --rules .codex/rules/default.rules -- git clean -fd
```

**Project trust.** Codex ignores a project-local `config.toml`, `hooks.json`
and `rules/` entirely until the project is trusted
(`projects."<abs path>".trust_level = "trusted"` in `~/.codex/config.toml`).
`codex_sync.py --trust` writes those entries, backing the file up to
`config.toml.pre-codex-sync` first.

---

## 6. Skills (*probed*)

Codex discovers repo skills from **both** `.codex/skills/<n>/SKILL.md` and
`.agents/skills/<n>/SKILL.md`, and from `~/.codex/skills/` and
`~/.agents/skills/` at user scope. It does **not** read `.claude/skills/`.

**Symlinks are followed.** That is what makes zero-drift sharing possible:
`.codex/skills/<n>` is a symlink to `../../.claude/skills/<n>`, so both agents
read the same `SKILL.md` byte for byte. Verified by pointing a
`.codex/skills/` entry at a `.claude/skills/` directory and confirming the
skill appeared in `codex debug prompt-input`.

The frontmatter contract (`name`, `description`) is the same in both products,
which is why no translation is needed. A `SKILL.md` missing either key is
invisible to **both** agents — six Scilux skills were silently dead this way
until the verifier caught them.

> **`.agents/skills/` is a second front door.** Because Codex reads it too,
> anything left there is loaded alongside `.codex/skills/` and shadows it. A
> dead 2026-07-17 projection attempt was putting 20 stale duplicates into every
> root session. `--verify` now fails on any non-vendored repo with skills there.
> (`ruflo` ships its own upstream `.agents/skills/` and is exempt.)

Invocation differs: Claude auto-invokes skills or takes `/name`; Codex takes
`$name` (and `@name` in the ChatGPT UI).

---

## 7. What Codex has that Claude does not

- `AGENTS.override.md`, `project_doc_fallback_filenames`, `project_doc_max_bytes`.
- `PermissionRequest` / `SubagentStart` hook events.
- Starlark execpolicy rules with `allow` / `prompt` / `forbidden`.
- Named permission profiles with `extends`.
- `[agents]` global knobs: `max_concurrent_threads_per_session`,
  `default_subagent_model`, `default_subagent_reasoning_effort`.
- Plugin marketplaces (`~/.agents/plugins/marketplace.json`) — including the
  official Anthropic marketplace, already enabled in Omar's global config.

## 8. What Claude has that Codex does not

- **Custom slash commands.** 0.146 has no `prompts/` directory; the
  `/prompts:<name>` surface referenced in the docs is not present in this
  build. Projected onto skills.
- Per-agent tool allowlists. Codex has no `tools:` field on a subagent; the
  closest expression is `sandbox_mode = "read-only"`, which the projection
  applies to every agent whose Claude `tools:` list grants no write tool.
- `maxTurns`, `disallowedTools` — dropped, no equivalent.
- Argument-level permission matchers (restored by the shim, see §4).

---

## 9. Verification commands

```bash
# what instructions and skills did Codex actually load in this repo?
cd <repo> && codex debug prompt-input "hi" | python3 -m json.tool

# do all generated agent TOMLs parse?
python3 -c "import tomllib,glob;[tomllib.load(open(p,'rb')) for p in glob.glob('.codex/agents/*.toml')]"

# is the projection in sync with .claude/?
~/GitHub/.claude/scripts/codex_sync.py --all --check

# health of the whole Codex install
codex doctor
```

# `.codex/AGENTS.md` — constellation kernel, Codex head

This file is **not** loaded automatically. Codex reads `AGENTS.md` files from
the git root down to your working directory, and `.codex/` is never a working
directory. `~/GitHub/AGENTS.md` points here; read it when it tells you to,
exactly as Claude Code reads `.claude/CLAUDE.md`.

## The kernel is not here

The constitutional kernel for `~/GitHub/` — perimeters, tier discipline, the
agent roster, shared-vs-local doctrine, git policy, risk classification — lives
in **[`../.claude/CLAUDE.md`](../.claude/CLAUDE.md)** and is agent-neutral.
Read it in full before any non-trivial cross-repo work.

It is deliberately not duplicated here. Two copies of a constitution drift,
and a drifted constitution is worse than none. Where it says *Claude*, read
*the agent*. Where it names a `.claude/` path, use the mapping below.

## Layer composition for a Codex session

```
~/.codex/AGENTS.md           ← Omar's user contract (Codex home)
~/GitHub/AGENTS.md           ← root pointer + reading order
~/GitHub/.claude/CLAUDE.md   ← THE KERNEL (agent-neutral, canonical)
~/GitHub/<repo>/AGENTS.md    ← lab contract, Codex head
~/GitHub/<repo>/CLAUDE.md    ← lab contract, canonical doctrine
```

More specific wins. When the most specific layer is silent, fall back.

Note that each sub-repo is **its own git root**. Running Codex inside
`~/GitHub/BacktestLab` loads `BacktestLab/AGENTS.md` and *not* this file —
which is why every repo's `AGENTS.md` stands on its own.

## Mandatory reading order

1. `~/GitHub/.claude/CLAUDE.md` — the constellation kernel.
2. `~/GitHub/.claude/REPOS.md` — repo index (perimeter + tier + stack).
3. `~/GitHub/QUANTOS.md` — canonical QuantOS map (tier hierarchy + data flow).
4. `~/GitHub/.claude/docs/codex_parity.md` — what Codex can and cannot do here.

## Construct mapping

| Concept | Claude Code | Codex | Invoke |
| --- | --- | --- | --- |
| kernel | `.claude/CLAUDE.md` | *same file* | read it |
| repo contract | `CLAUDE.md` | `AGENTS.md` | automatic |
| cross-repo agents | `.claude/agents/*.md` | `.codex/agents/*.toml` | spawn by name |
| skills | `.claude/skills/<n>/` | `.codex/skills/<n>` (symlink to the same files) | `$<n>` |
| slash commands | `/<n>` | `.codex/skills/<n>/` | `$<n>` |
| hooks | `.claude/settings.json` | `.codex/hooks.json` → same `.claude/hooks/` scripts | automatic once trusted |
| denylist | `permissions.deny` | `.codex/rules/default.rules` | automatic once trusted |
| registry | `.claude/registry/*.yaml` | *same files* — data, not agent config | read directly |

Codex 0.146 has no custom slash commands, so everything Claude exposes as
`/name` is a skill here, invoked `$name`.

## Cross-repo entry points

The seven constellation agents live in `.codex/agents/` and are the same
agents as Claude's, projected: `cross-repo-router` (front door for any
free-form request), `multi-repo-orchestrator` (the only agent allowed to
spawn others and write across repos), `constellation-cartographer`,
`cross-repo-search`, `repo-classifier`, `perimeter-keeper`,
`import-graph-auditor`.

Routing doctrine is §7 of the kernel and applies unchanged.

## Codex-specific operating rules

- **Trust.** Codex ignores project-local `config.toml`, `hooks.json` and
  `rules/` until a project is trusted. `.claude/scripts/codex_sync.py --trust`
  registers every repo in `~/.codex/config.toml`.
- **Hook trust.** Codex will not run hooks until you approve them: `/hooks`
  → *Trust all and continue*, once per repo, and again whenever `hooks.json`
  changes. Until then the secret scanner and commit gates are silently
  inactive under Codex.
- **Regeneration.** Never hand-edit anything under `.codex/` or any
  `AGENTS.md`. Edit `.claude/`, then run
  `.claude/scripts/codex_sync.py --all`. Codex-only material goes in
  `.codex/local/`.
- **Git policy is unchanged**: atomic commits per repo, one PR per repo for
  cross-repo work, no `--no-verify`, no force-push to main.

---

<!-- Hand-written. Not produced by codex_sync.py. -->

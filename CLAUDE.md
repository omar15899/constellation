# CLAUDE.md — `~/GitHub/`

This is the **root-level kernel** for any Claude session whose working
directory is `~/GitHub/` itself (the constellation root, not an
individual repo). The full constitutional kernel — agents, skills,
commands, policies, registry — lives one level down at:

→ **[`~/GitHub/.claude/CLAUDE.md`](.claude/CLAUDE.md)** — read this next.

## TL;DR for the session

`~/GitHub/` is a constellation of 18 registered repositories (plus
transient git worktrees, which are never registered):

- **14 QuantOS repos** (Shared, BacktestLab, MonteCarloLab, Sweeplab,
  PricingLab, MarketDataLab, NewsLab, ResearchLab, IntelligenceLab,
  PortfolioLab, RiskLab, ExecutionLab, StrategyOrchestrationLab,
  tradinginterface) — tiered 0..4 + UI.
- **3 adjacent repos** (Scilux, MMARV1, KarimSpecificCase) — independent.
- **1 external repo** (ruflo) — vendored third-party, ungoverned.

Above this directory sits the **OmarOS vault** at `~/OmarOS/` —
canonical for vision, decisions, reflections, project governance.
Read-only from any session running here.

## Layer composition

Three layers compose for any session at `~/GitHub/` or below:

```
~/CLAUDE.md                  ← user identity, tone, mathematics, git defaults
~/GitHub/CLAUDE.md           ← THIS FILE — root pointer + reading order
~/GitHub/.claude/CLAUDE.md   ← the constellation kernel (long form)
~/GitHub/<repo>/CLAUDE.md    ← lab-specific contract (when inside a repo)
```

More specific wins. When the most specific layer is silent, fall back.

## Mandatory reading order (this session)

Before any non-trivial work:

1. `~/CLAUDE.md` — Omar's user contract.
2. `~/GitHub/.claude/CLAUDE.md` — the full constellation kernel.
3. `~/GitHub/.claude/REPOS.md` — repo index (15 repos, perimeter + tier + stack).
4. `~/GitHub/QUANTOS.md` — canonical QuantOS map (tier hierarchy + data flow).

## Constellation control plane

Everything cross-repo lives under `.claude/`:

| Path                                | What                                                   |
| ----------------------------------- | ------------------------------------------------------ |
| `.claude/CLAUDE.md`                 | Constitutional kernel (long form).                     |
| `.claude/REPOS.md`                  | Repo index (human-readable).                           |
| `.claude/registry/repos.yaml`       | Machine-readable repo registry.                        |
| `.claude/registry/perimeters.yaml`  | Perimeter definitions + cross-perimeter rules.         |
| `.claude/registry/stacks.yaml`      | Stack profiles per repo.                               |
| `.claude/registry/agents.yaml`      | Cross-repo agent roster.                               |
| `.claude/agents/`                   | 7 cross-repo agents (cartographer, router, …).         |
| `.claude/skills/`                   | 8 cross-repo skills (status, grep, refactor, …).       |
| `.claude/commands/`                 | 7 slash commands wrapping the skills/agents.           |
| `.claude/hooks/`                    | Reusable Python hooks (peer_sync, repo_discovery).     |
| `.claude/scripts/`                  | Executable utilities (discover, status, grep, bootstrap). |
| `.claude/templates/`                | Bootstrap templates (CLAUDE.md, importlinter, lint.yml). |
| `.claude/policies/`                 | 6 doctrine files (perimeter, tier, commits, …).        |
| `.claude/docs/`                     | Architecture + how-to-add-a-repo.                      |

## Per-repo planes

Each repo under `~/GitHub/<repo>/` has its own `.claude/` directory.
When the session descends into a single repo, that repo's `.claude/`
is authoritative for everything internal to it. The constellation
plane composes; per-repo planes execute.

## Two agent heads, one plane

Every surface here is drivable by **Claude Code or OpenAI Codex,
interchangeably**. `.claude/` is canonical; `.codex/` and every `AGENTS.md`
are a *generated projection* of it:

| Claude Code | Codex | Invoke |
| ----------- | ----- | ------ |
| `CLAUDE.md` | `AGENTS.md` | automatic |
| `.claude/agents/<n>.md` | `.codex/agents/<n>.toml` | spawn by name |
| `.claude/skills/<n>/` | `.codex/skills/<n>` (symlink — same files) | `$<n>` |
| `/<n>` slash command | `.codex/skills/<n>/` | `$<n>` |
| `settings.json` hooks | `.codex/hooks.json` → same `.claude/hooks/` scripts | automatic once trusted |
| `permissions.deny` | `.codex/rules/default.rules` | automatic once trusted |

Never hand-edit `.codex/` or an `AGENTS.md`. Edit `.claude/`, then run
`/codex-sync` (or `.claude/scripts/codex_sync.py --all`). Codex-only
material with no Claude counterpart goes in `.codex/local/`.

Codex needs two things Claude does not: project trust
(`codex_sync.py --trust`) and a one-time interactive hook approval
(`/hooks` → *Trust all and continue*) — **until then Codex silently runs no
hooks at all**. Full mapping, limits and empirical basis:
[`.claude/docs/codex_parity.md`](.claude/docs/codex_parity.md).

## Fast operations

- `~/GitHub/.claude/scripts/discover_repos.py --state` — registry sync + git state.
- `~/GitHub/.claude/scripts/status_all.sh [--perimeter <p>] [--dirty-only]` — aggregate git status.
- `~/GitHub/.claude/scripts/grep_all.sh "<pattern>" [--perimeter <p>]` — cross-repo search.
- `~/GitHub/.claude/scripts/bootstrap_repo.sh <path> [--variant quantos|adjacent]` — apply standard layout.

## Routing

Every free-form request goes through `cross-repo-router` first.
Vault-class work (vision, decisions, reflections) is **escalated to
OmarOS** — see `.claude/policies/escalation_to_omaros.md`.

## Git policy (constellation-specific overrides)

- One commit per repo per logical change. Never bundle across repos.
- Cross-repo refactors: same branch name across repos, one PR per repo.
- Tier discipline (QuantOS): enforced by `import-linter` per lab plus
  the constellation-level `import-graph-auditor`.
- No `--no-verify`, no `--force` to main. Ever.

## What this directory is NOT

- Versioned as its own repo: **`constellation`**
  (`github.com/omar15899/constellation`, private). The root is now a git repo
  whose `.gitignore` is an allowlist — it tracks only the control plane
  (`.claude/`, `CLAUDE.md`, `QUANTOS.md`, `README.md`) and ignores the 18
  sub-repos, which keep their own independent histories.
- Not a replacement for per-repo `.claude/` configs.
- Not the vault. Vision and decisions live in `~/OmarOS/`.

---

**Next file to read:** [`.claude/CLAUDE.md`](.claude/CLAUDE.md).

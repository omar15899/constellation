# Constellation Architecture

Two-paragraph version, then the diagram, then the detail.

## Brief

`~/GitHub/` hosts a constellation of 15 active repositories — 12
forming the **QuantOS** quantitative-finance operating system, plus 3
adjacent independent projects. The constellation is layered by tier
(0 to 3, plus UI), perimeter (`quantos-*` / `adjacent`), and stack
profile.

`~/GitHub/.claude/` is the **cross-repo AI control plane** for this
constellation. It owns discovery, classification, routing,
cross-repo skills, shared agents, and the policies that bind it all.
The vault at `~/OmarOS/` is one layer above — it owns vision,
decisions, reflections, and project governance.

## Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ~/OmarOS/  ← semantic / governance / reflection / vision               │
│            ← read-only from ~/GitHub/.claude/                                │
└─────────────────────────────────────────────────────────────────────────┘
                                ▲
                                │ escalation (drafts only)
                                │
┌─────────────────────────────────────────────────────────────────────────┐
│  ~/GitHub/.claude/  ← CROSS-REPO AI CONTROL PLANE                            │
│  ───────────────                                                         │
│  CLAUDE.md   REPOS.md   registry/   agents/   skills/   commands/        │
│  hooks/      scripts/   templates/  policies/  docs/                     │
└─────────────────────────────────────────────────────────────────────────┘
                                │ composes
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  ~/GitHub/<repo>/.claude/  ← per-repo AI surface (one per lab)           │
│                                                                          │
│  Shared       ◄── Tier 0    (substrate)                                  │
│  BacktestLab  ◄── Tier 1    MonteCarloLab  ◄── Tier 1                    │
│  Sweeplab     ◄── Tier 1                                                 │
│  PricingLab   ◄── Tier 1.5                                               │
│  NewsLab      ◄── Tier 2    ResearchLab    ◄── Tier 2                    │
│  IntelligenceLab ◄── Tier 2                                              │
│  PortfolioLab ◄── Tier 2.5                                               │
│  RiskLab      ◄── Tier 3    ExecutionLab   ◄── Tier 3                    │
│  tradinginterface ◄── UI                                                 │
│                                                                          │
│  Scilux, MMARV1, KarimSpecificCase ◄── adjacent (not bound by QuantOS)   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Layer responsibilities

### Vault (`~/OmarOS/`)
- Vision, roadmap, ADRs, project status, reflections, knowledge base.
- Bound by its own constitutional kernel (`~/OmarOS/CLAUDE.md`).
- Read-only for the constellation hub.

### Constellation hub (`~/GitHub/.claude/`)
- Discovery and classification (`constellation-cartographer`,
  `repo-classifier`, `repo-discovery`).
- Routing (`cross-repo-router`).
- Multi-repo coordination (`multi-repo-orchestrator`).
- Cross-repo skills (status, grep, refactor, bootstrap, tier-check,
  brief).
- Policies: perimeter, tier, shared-vs-local, commits, escalation,
  invariants.

### Per-repo plane (`<repo>/.claude/`)
- Lab-internal agents, skills, commands, hooks.
- Authoritative for everything inside the repo.
- Read by the constellation when descending into a repo for execution.

## Information flow

**Request lands.** `cross-repo-router` reads the request. Classifies
into one of {SEARCH, STATUS, REFACTOR, BOOTSTRAP, AUDIT, CLASSIFY,
IN-REPO, VAULT, REASONING, MIXED, OPERATIONAL}.

**Single-repo path.** Class is `IN-REPO` → router hands off to that
repo's `.claude/` and stops.

**Multi-repo path.** Class is `REFACTOR | BOOTSTRAP | AUDIT | MIXED`
→ `multi-repo-orchestrator` decomposes, orders by tier, dispatches
per-repo work, validates with `import-graph-auditor` between stages.

**Vault path.** Class is `VAULT` → router emits an escalation
envelope and stops. The user runs the vault-side command (or invokes
the vault's `content-router` directly).

**Operational / informational path.** Class is `STATUS | SEARCH |
REASONING | OPERATIONAL` → executes directly via the relevant skill.

## Persistence

The hub is intentionally **not a git repo**. Its state is:

- The YAML registry files (canonical).
- The markdown policies (canonical).
- The Python scripts and hooks (canonical).
- Per-session caches under `~/GitHub/.claude/.cache/` (ephemeral).
- Escalation drafts under `~/GitHub/.claude/docs/escalation_drafts/`
  (ephemeral; cleaned up after the vault picks them up).

If the hub ever needs to be versioned, it can become its own git repo
without restructure — but that decision waits until the surface
stabilises.

## Why two planes (hub + per-repo)?

Because some questions are *only* answerable across repos (status,
grep, refactor, tier audit, perimeter drift), and some are *only*
answerable inside one repo (lab-specific commands, lab-specific
content routing, lab-specific test suites). Forcing one plane to do
both would either bloat the per-repo `.claude/` with cross-cutting
concerns or strip the hub of the lab-internal nuance.

The two-plane split makes both planes thinner.

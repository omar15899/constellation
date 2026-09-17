# REPOS.md — Constellation Index

Human-readable mirror of [`registry/repos.yaml`](registry/repos.yaml).
Refreshed by the `constellation-cartographer` agent or the
`repo-discovery` skill.

Directory membership updated: **2026-09-17**. Maturity and stack labels retain
the earlier domain inventory; they are not a fresh code audit. Git determines
file ownership, and [Codex's registry](../.codex/repositories.json) determines
native or external workspace participation. There are 19 own child repositories
and one external repository, in addition to the constellation hub.

---

## QuantOS perimeter (14 repos)

### Tier 0 — Substrate

| Repo | Stack | Status | Role |
| ---- | ----- | ------ | ---- |
| **Shared** | python-uv-strict | stub | `quant_core`, `quant_data`, `quant_observability`, KnownAt[T], BLAKE3 audit DAG |

### Tier 1 — Causal evaluators & market data

| Repo | Stack | Status | Role |
| ---- | ----- | ------ | ---- |
| **BacktestLab**   | mixed (Py+Rust+C++) | mature      | Four-tier causal backtester, audit-DAG identity |
| **MonteCarloLab** | mixed (Py+Rust)     | mature      | JAX+Rust MC runtime, AAD-from-day-1 |
| **Sweeplab**      | python              | substantive | Parameter sweeps + Firedrake/SDC PDE backend |
| **MarketDataLab** | python              | stub        | EODHD tick/intraday/EOD ingestion → content-addressed tick store → typed `Tick`/`MarketBar` |

### Tier 1.5 — Pricing

| Repo | Stack | Status | Role |
| ---- | ----- | ------ | ---- |
| **PricingLab** | python | stub | Calibrated model + market data → certified `PricingRun` |

### Tier 2 — Information channels

| Repo | Stack | Status | Role |
| ---- | ----- | ------ | ---- |
| **NewsLab**         | python | stub | News ingestion + LLM event tagging → `FeatureSet` |
| **ResearchLab**     | python | stub | Experiment orchestrator + Study + Report + provenance |
| **IntelligenceLab** | python | stub | SCM / counterfactual / causal-inference (DoWhy + Pyro) |

### Tier 2.5 — Allocation

| Repo | Stack | Status | Role |
| ---- | ----- | ------ | ---- |
| **PortfolioLab** | python | stub | Mean-var, RP, BL, HRP, intelligence-weighted allocation |

### Tier 3 — Production (touches money)

| Repo | Stack | Status | Role |
| ---- | ----- | ------ | ---- |
| **RiskLab**      | python | stub | VaR, exposure, factor decomp, drawdown, regimes, limits |
| **ExecutionLab** | python | stub | `OrderProposal → Order → Fill`, IBKR adapter, ledger |

### Tier 4 — Orchestration

| Repo | Stack | Status | Role |
| ---- | ----- | ------ | ---- |
| **StrategyOrchestrationLab** | python | substantive | Integration layer: composes ResearchLab + MarketDataLab + BacktestLab → Trading Interface. Coordinates, never computes (typed glue only). |

### UI tier

| Repo | Stack | Status | Role |
| ---- | ----- | ------ | ---- |
| **tradinginterface** | typescript-vite | substantive | Helix — 3 workspaces (Market / Research / Strategy) |

---

## Adjacent perimeter (5 repos)

These live next to QuantOS on disk but are **independent projects** —
not bound by QuantOS tier discipline or vault governance.

| Repo | Stack | Status | Role |
| ---- | ----- | ------ | ---- |
| **Scilux**            | typescript-vite  | external | Scientific UI / visualisation toolkit |
| **MMARV1**            | python-light     | external | Multifractal analysis library |
| **KarimSpecificCase** | vanilla-web      | external | gas-storage operations monitor (adjacent client UI) |
| **GasStorageOptimiserEngie** | python | active | Rolling-intrinsic gas-storage valuation and hedging; frozen original and working implementation |
| **brainteasers-asincronas** | mixed (LaTeX+py+sh) | active | Async-lecture production system (Hespérides Beamer + teleprompter) for the Brainteasers Quant course |

---

## External perimeter (1 repo)

Third-party code vendored on disk for development convenience. **Not**
authored by Omar and **not** under QuantOS governance, tiering, or vault.
Excluded from constellation audits, refactors, and peer propagation.

| Repo | Stack | Status | Role |
| ---- | ----- | ------ | ---- |
| **ruflo** | mixed (TS+Py) | external | Third-party multi-agent orchestration framework (ruvnet) — upstream `github.com/ruvnet/ruflo` |

---

## Agent planes

Claude Code keeps its own `.claude/` contracts and tools. Codex uses native
`AGENTS.md` and `.codex/` profiles in the hub and the 19 own projects. A native
`profile.json` excludes that entire profile from projection: edit it directly.
Domain rules remain shared, while each client controls its own execution.

| | Claude Code | Codex |
| --- | --- | --- |
| contract | `CLAUDE.md` | `AGENTS.md` |
| plane | `.claude/` | native `.codex/` |
| skill | model-invoked or `/name` | `$name` |
| workflow | project commands | shared `workspace.py` plus project tools |

`ruflo` is vendored: its `AGENTS.md` is upstream-owned and the projection
refuses to touch it. `MMARV1`, `GasStorageOptimiserEngie` and
`brainteasers-asincronas` use the same minimal native Codex contract without
needing a `.claude/` plane. New repositories join the Codex workspace through
an explicit entry in [repositories.json](../.codex/repositories.json); this
does not install Claude or change Codex trust.

Mapping, limits and empirical basis: [`docs/codex_parity.md`](docs/codex_parity.md).

## Quick navigation

- Constellation kernel: [`CLAUDE.md`](CLAUDE.md).
- Machine-readable registry: [`registry/repos.yaml`](registry/repos.yaml).
- Perimeter definitions: [`registry/perimeters.yaml`](registry/perimeters.yaml).
- Stack profiles: [`registry/stacks.yaml`](registry/stacks.yaml).
- QuantOS canonical map (tier hierarchy + data flow): [`~/GitHub/QUANTOS.md`](../QUANTOS.md).
- Vault-side governance: [`~/OmarOS/05_Projects/QuantOS/`](../../OmarOS/05_Projects/QuantOS/).

## Dependency rule (QuantOS perimeters only)

A Tier *k* component may import from Tiers *0..k−1*, never from
*k..4*. Enforced by `import-linter` in each lab and audited across
the constellation by [`agents/import-graph-auditor.md`](agents/import-graph-auditor.md).

## How to add a repo

1. Drop the repo under `~/GitHub/`.
2. Run `/repos` or invoke `constellation-cartographer`.
3. Confirm the proposed classification (perimeter, tier, stack, role).
4. If the repo should join QuantOS governance, run the `repo-bootstrap`
   skill — adds standard `.claude/`, CI, import-linter, hooks, peers.
5. Open a vault-side vision note under `05_Projects/<project>/Vision/`.

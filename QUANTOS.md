# QUANTOS.md — Constellation Map

> **Single map for every QuantOS lab on disk. Read this when an agent in
> one lab needs to know what the other labs do, where they live, and how
> they compose.**

This file is the canonical map of the QuantOS multi-repo constellation.
Every lab's orchestrator reads it on session start so that agents can
delegate, consume artefacts, and reason about cross-lab dependencies.

The vault-side governance is at
[`~/OmarOS/05_Projects/QuantOS/`](../OmarOS/05_Projects/QuantOS/AGENTS.md);
that is the constitutional layer. This file is its operational mirror at
the GitHub-folder level.

Last updated: **2026-06-15** — see commit history for changes.

---

## 1. The 14 repositories

| Repo | Tier | Role | Stack | Status | Vault Vision |
|------|------|------|-------|--------|--------------|
| `Shared` | 0 | Substrate: `quant_core`, `quant_data`, `quant_observability`, `KnownAt[T]`, BLAKE3 audit DAG, Capability | Python | stub | [Labs/Shared/Vision/00_Substrate.md](../OmarOS/05_Projects/QuantOS/Labs/Shared/Vision/00_Substrate.md) |
| `BacktestLab` | 1 | Causal backtester, four-tier engine, three backends, audit-DAG identity | Python (+ Rust, C++) | mature | [Labs/BacktestLab/Vision/](../OmarOS/05_Projects/QuantOS/Labs/BacktestLab/Vision/) |
| `MonteCarloLab` | 1 | Monte Carlo / stochastic runtime, JAX + Rust backends, AAD-from-day-1 | Python (+ Rust) | mature | [Labs/MonteCarloLab/Vision/](../OmarOS/05_Projects/QuantOS/Labs/MonteCarloLab/Vision/) |
| `Sweeplab` | 1 | Parameter / hyperparameter / grid sweeps + Firedrake/SDC PDE backend | Python | substantive | [Labs/SweepLab/Vision/](../OmarOS/05_Projects/QuantOS/Labs/SweepLab/Vision/) |
| `MarketDataLab` | 1 | Market/tick data ingestion (EODHD adapter) → content-addressed tick store → typed `Tick`/`MarketBar` | Python | stub | [Labs/MarketDataLab/Vision/](../OmarOS/05_Projects/QuantOS/Labs/MarketDataLab/Vision/) |
| `PricingLab` | 1.5 | Calibrated model + market data → certified `PricingRun` (four-layer chain) | Python | stub | [Labs/PricingLab/Vision/](../OmarOS/05_Projects/QuantOS/Labs/PricingLab/Vision/) |
| `NewsLab` | 2 | News ingestion + LLM event tagging → `FeatureSet` | Python | stub (target) | [Labs/NewsLab/Vision/](../OmarOS/05_Projects/QuantOS/Labs/NewsLab/Vision/) |
| `ResearchLab` | 2 | Experiment orchestrator + Study + Report + provenance | Python | stub | [Labs/ResearchLab/Vision/](../OmarOS/05_Projects/QuantOS/Labs/ResearchLab/Vision/) |
| `IntelligenceLab` | 2 | SCM / counterfactual / causal-inference layer (DoWhy + Pyro) | Python | stub | [Labs/IntelligenceLab/Vision/](../OmarOS/05_Projects/QuantOS/Labs/IntelligenceLab/Vision/) |
| `PortfolioLab` | 2.5 | Portfolio construction + allocation (mean-var, RP, BL, HRP, intelligence-weighted) | Python | stub | [Labs/PortfolioLab/Vision/](../OmarOS/05_Projects/QuantOS/Labs/PortfolioLab/Vision/) |
| `RiskLab` | 3 | Exposure aggregation, factor decomp, drawdown, regime, limits, VaR, stress | Python | stub | [Labs/RiskLab/Vision/](../OmarOS/05_Projects/QuantOS/Labs/RiskLab/Vision/) |
| `ExecutionLab` | 3 | `OrderProposal → Order → Fill` lifecycle, IBKR adapter, Postgres ledger, four trading modes | Python | stub | [Labs/ExecutionLab/Vision/](../OmarOS/05_Projects/QuantOS/Labs/ExecutionLab/Vision/) |
| `StrategyOrchestrationLab` | 4 | Orchestration / integration layer — composes ResearchLab + MarketDataLab + BacktestLab and exposes typed results to the Trading Interface (coordinate, never compute) | Python | substantive | [Labs/StrategyOrchestrationLab/Vision/](../OmarOS/05_Projects/QuantOS/Labs/StrategyOrchestrationLab/Vision/) |
| `tradinginterface` | UI | Helix Trading Interface — 3 workspaces (Market / Research / Strategy) | React + TS + Vite | substantive | [Labs/tradinginterface/Vision/](../OmarOS/05_Projects/QuantOS/Labs/tradinginterface/Vision/) |

Adjacent (out of QuantOS perimeter, but on disk under `~/GitHub/`):

| Repo | Role | Tier | Stack |
|------|------|------|-------|
| `KarimSpecificCase` | gas-storage operations monitor (adjacent client UI; sister UI to `tradinginterface`) | UI (external) | Vanilla HTML/CSS/JS + Playwright |
| `Scilux` | Scientific UI / visualisation | external | TS |
| `MMARV1` | Multifractal analysis library | external | Python |

The adjacent repos are not bound to QuantOS governance; they are listed here
so QuantOS agents do not mistake them for stale labs.

---

## 2. Tier hierarchy (canonical)

```
Tier 4 — Orchestration
        StrategyOrchestrationLab (composes ResearchLab / MarketDataLab / BacktestLab → UI);
        plus Claude Code workflows across all labs. Coordinates, never computes;
        imports Tiers 0–3, never inverts.

Tier 3 — Risk & Execution                      (touch money)
        RiskLab → ExecutionLab

Tier 2.5 — Portfolio                           (allocation)
        PortfolioLab

Tier 2 — Information                           (consume Tier 1, add information channels)
        ResearchLab, NewsLab, IntelligenceLab

Tier 1.5 — Pricing                             (between numerical and risk)
        PricingLab

Tier 1 — Research labs                         (compute substrate over Tier 0)
        BacktestLab, MonteCarloLab, Sweeplab

Tier 0 — Foundations                           (substrate, no upward imports)
        Shared

UI — outside the import graph
        tradinginterface (depends on T2/T3 over HTTP/WS)
```

The dependency rule: a Tier *k* component may import from Tiers
*0..k-1*, never from *k..4*. CI enforces this with `import-linter`
contracts. Inverting an arrow is a release blocker.

---

## 3. Production data flow (target)

```
quant_data ─┐                                         ┌─ FeatureSet ─┐
            │                                         │              │
Shared ──┬──┼─► MonteCarloLab ──► PricingRun ─────────┘              │
         │  │                              │                          │
         │  └─► BacktestLab ──► BacktestRun├─► RiskLab ──► RiskCert ──┤
         │                                  │                          │
         └──► Sweeplab ──► SweepRun ────────┘                          │
                                                                       │
NewsLab ──► FeatureSet ─────────────────────────────┐                  │
IntelligenceLab ──► CounterfactualEstimate ─────────┤                  │
                                                    │                  │
                                                    ▼                  │
                                              ResearchLab ──► Study + Report
                                                    │
                                                    ▼
                                              PortfolioLab ──► Allocation
                                                    │
                                                    ▼
                                              RiskLab (gate) ──► RiskCert
                                                    │
                                                    ▼
                                              ExecutionLab ──► OrderProposal → Order → Fill
                                                    │
                                                    ▼
                                              tradinginterface (renders all of the above over HTTP/WS)
```

Every artefact between two labs is **typed**, **content-addressed**
(BLAKE3 root hash), and **regenerable** from its manifest.

---

## 4. Cross-lab invocation pattern (current and target)

### Current (manual)

A change in one lab that needs work in another lab today is a
human-in-the-loop event:

1. The user (or an agent in lab A) identifies the cross-lab dependency.
2. The user opens lab B in a separate Claude Code session.
3. Work happens in lab B; a typed artefact is produced.
4. Lab A consumes the artefact via path / hash reference.

### Target (wired)

When all labs are wired (planned, not yet implemented):

1. An orchestrator in lab A declares a cross-lab need via `peers.yaml`.
2. The QuantOS-wide orchestrator dispatches to lab B's orchestrator.
3. Lab B produces the artefact under its own `outputs/` and emits the
   hash to a shared bus.
4. Lab A consumes the artefact by hash reference; the audit DAG records
   the dependency.

Until the wiring exists, every lab's orchestrator MUST know about its
peers (this file) so that it can:

- recognise when a request belongs to a sibling lab and *say so*,
  rather than implement the work locally and duplicate the abstraction;
- read sibling Vision documents when relevant;
- consume sibling artefacts via path / hash reference.

---

## 5. Peer registry per lab

Every lab carries `.claude/registry/peers.yaml` listing the labs it
consumes from / produces for. The vault-side `Documentation/meta_architecture.md` §6
declares the integration arrow; this file is the per-lab projection.

---

## 6. The shared Python environment

Per [[ADR-0033]], the canonical Python environment for every lab is
`~/GitHub/.venv/`. Every lab's `.claude/settings.json` sets
`UV_PROJECT_ENVIRONMENT` and `VIRTUAL_ENV` to that path. `uv sync` from
any lab updates the shared venv (with the caveat that `uv sync`
reconciles to the calling lab's lockfile — see ADR-0033 §Consequences).

Bootstrap:
```bash
cd ~/GitHub
uv venv --python 3.12 .venv
# Then sync from BacktestLab last (largest dep set) to maximise the venv:
for lab in Shared MonteCarloLab PricingLab ResearchLab IntelligenceLab \
           PortfolioLab RiskLab ExecutionLab NewsLab BacktestLab; do
  (cd ~/GitHub/$lab && uv sync)
done
```

Vault-side hooks continue to use `~/.venvs/omaros/`. Lab code uses
`~/GitHub/.venv/`. The boundary is in OmarOS CLAUDE.md §14.

---

## 7. Pointers

- Vault entrypoint: [`~/OmarOS/05_Projects/QuantOS/AGENTS.md`](../OmarOS/05_Projects/QuantOS/AGENTS.md)
- Reading order: [`Documentation/ai_reading_order.md`](../OmarOS/05_Projects/QuantOS/Documentation/ai_reading_order.md)
- Development contract: [`Documentation/ai_development_contract.md`](../OmarOS/05_Projects/QuantOS/Documentation/ai_development_contract.md)
- Meta-architecture: [`Documentation/meta_architecture.md`](../OmarOS/05_Projects/QuantOS/Documentation/meta_architecture.md)
- ADR-0030 (multi-repo regime): [`Decisions/ADR-0030-multi-repo-transition-monorepo-target.md`](../OmarOS/05_Projects/QuantOS/Decisions/ADR-0030-multi-repo-transition-monorepo-target.md)
- ADR-0031 (substrate extraction): [`Decisions/ADR-0031-substrate-extraction.md`](../OmarOS/05_Projects/QuantOS/Decisions/ADR-0031-substrate-extraction.md)
- ADR-0032 (uniform AI scaffold): [`Decisions/ADR-0032-lab-ai-scaffold-uniform.md`](../OmarOS/05_Projects/QuantOS/Decisions/ADR-0032-lab-ai-scaffold-uniform.md)
- ADR-0033 (shared venv): [`Decisions/ADR-0033-shared-venv-github-centralized.md`](../OmarOS/05_Projects/QuantOS/Decisions/ADR-0033-shared-venv-github-centralized.md)

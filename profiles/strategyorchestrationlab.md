# StrategyOrchestrationLab

Raíz: `/Users/omarkhalil/GitHub/StrategyOrchestrationLab`. Las rutas de este perfil se interpretan desde esa raíz.
Las reglas de dominio se conservan; versiones y comandos se contrastan con los archivos actuales.
La coordinación y publicación usan el único `constellation.py`.

## Identidad

StrategyOrchestrationLab (SOL) is the integration layer of QuantOS: perimeter `quantos-orchestration`, Tier 4, stack python, status `substantive` in ~/GitHub/.claude/registry/repos.yaml. It connects ResearchLab (research logic/signals), MarketDataLab (data access) and BacktestLab (simulation/PnL) and exposes one standardised, typed `ExperimentResult` to the Trading Interface (Helix). Its whole reason to exist is the golden rule stated in both README.md and CLAUDE.md — "Coordinate, do not compute": no ML models, no financial logic, no backtest internals, no concrete data loaders, only formal typed glue (specs, protocols, adapters, registries, runners) over payloads it forwards as opaque `object`s and never inspects. Two lab seams are real today (GatewayMarketDataAdapter in-process via `quant_market`; HelixStoreInterfaceAdapter writing the `<run_id>/{config,summary,equity,trades}.json` bundle Helix reads); the ResearchLab leg is specified but unbuilt, and the BacktestLab leg is partially begun — MarketDataLabBacktestFeed (adapters/marketdata_backtest_feed.py, commit 4538288) already projects cache-first bars into the `series` JSON fragment BacktestLab's out-of-process runner ingests, but SubprocessBacktestAdapter itself does not exist.

## Fuentes del dominio

- CLAUDE.md

- README.md

- docs/INTEGRATION.md

- .importlinter

- .claude/registry/peers.yaml

- pyproject.toml

- configs/momentum_v1_backtest.yaml

## Invariantes

- "Coordinate, do not compute. No ML models, no financial logic, no backtest internals, no concrete data loaders. Only formal, typed glue: specs, protocols, adapters, registries, runners." (CLAUDE.md, verbatim)

- "Payloads (market data, signals, backtest output) are opaque `object`s the orchestrator forwards but never inspects." (CLAUDE.md, verbatim; restated in .claude/registry/peers.yaml)

- "If a new strategy seems to need a special case in the orchestrator, the answer is a new adapter or an extended spec — never a conditional inside the runner." (CLAUDE.md, verbatim) — README.md restates it as a hard exclusion under 'What does not belong in this library': "Strategy-specific `if` branches in the orchestrator."

- Internal layer order, enforced by .importlinter (both contracts verified KEPT on 2026-07-30, 59 files / 239 dependencies analysed). MIND THE DIRECTION: `core` is the BOTTOM and imports nothing else in the package; above it sit {registry, adapters, config, persistence, diagnostics}; above those `pipeline`; `examples` at the top. CLAUDE.md renders this as `core → { registry, adapters, config, persistence, diagnostics } → pipeline → examples`, which is a low-to-high ordering, NOT an import direction — the arrows point OPPOSITE to the allowed imports. .importlinter lists the same layers high-to-low (`examples / pipeline / config|persistence|diagnostics|adapters|registry / core`) and its comment is authoritative: "a higher layer may import from any lower layer, never the reverse." The two contracts are `layered` and `core-is-independent` (forbidden: core → registry, adapters, config, persistence, diagnostics, pipeline, examples).

- Constellation tier discipline: Tier 4 may import Tiers 0–3 and never inverts. STATED in CLAUDE.md ("Tier 4 — sits atop the stack, imports Tiers 0–3, feeds the UI"), in the registry notes, and in ~/GitHub/.claude/CLAUDE.md §3.2 — but NOT mechanically enforced inside this repo: the local .importlinter constrains only the internal package layering, not cross-lab imports. Observed state honours it: src/ imports only quant_data, quant_market and quant_substrate (Tiers 0–1) and nothing from BacktestLab, ResearchLab, PortfolioLab, RiskLab or ExecutionLab.

- Ownership boundaries are absolute (CLAUDE.md "Boundaries with the other labs" / README "What does not belong in this library"): research logic, models, features, training → ResearchLab; data loading, cleaning, alignment, caching, corporate actions → MarketDataLab; fills, costs, slippage, accounting, PnL, metrics → BacktestLab; dashboards, plots, controls → Trading Interface.

- "The adapters shipped here (`InMemory…`, `SimpleVector…`, `Json…`) are reference test doubles only" (CLAUDE.md, verbatim) — they are not production engines and must not acquire production behaviour; production adapters live in the consumed labs and satisfy the protocols in `core/protocols.py`.

- Adding a strategy must require no orchestration-layer change: "Add a strategy: implement a `ResearchAdapter`, define a `StrategySpec`, register it, write a YAML config. No orchestration-layer changes." (CLAUDE.md). README specifies subclassing `BaseResearchAdapter` and implementing prepare_features / train / load_model / generate_signals.

- .claude/registry/peers.yaml cross-lab discipline, verbatim: "If the request belongs to a sibling lab, SAY SO and stop — do not duplicate an abstraction that belongs there." and "Consume sibling artefacts by content hash from their outputs/ tree."

- Constellation git policy applies but is NOT locally enforced here: one commit per repo per logical change, never bundled across repos, and no force-push to main (~/GitHub/.claude/CLAUDE.md §9); no `--no-verify` (~/GitHub/CLAUDE.md git policy). This repo has no pre-commit config and no installed git hooks, so the discipline is manual plus CI.

## Comandos de referencia

- uv sync

- uv run ruff check .

- uv run ruff format --check .

- uv run mypy src/

- uv run lint-imports

- uv run pytest -q

- uv sync --frozen || uv sync

- uv run pytest tests/ -x --tb=short -q

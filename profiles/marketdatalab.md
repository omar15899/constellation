# MarketDataLab

Raíz: `/Users/omarkhalil/GitHub/MarketDataLab`. Las rutas de este perfil se interpretan desde esa raíz.
Las reglas de dominio se conservan; versiones y comandos se contrastan con los archivos actuales.
La coordinación y publicación usan el único `constellation.py`.

## Identidad

MarketDataLab is QuantOS's Tier-1 market-data ingestion lab in the `quantos-core` perimeter — the single owner of external price/tick/intraday/EOD acquisition. It turns vendor feeds (EODHD first: EOD, intraday, tick, and the live WebSocket) into typed, time-stamped, content-addressed `Tick` / `MarketBar` artefacts that PricingLab, BacktestLab, MonteCarloLab, RiskLab, PortfolioLab and ExecutionLab consume. The *contract* (the value types and the `TickSource`/`MarketDataSource` Protocols) is Tier-0 and lives in `Shared/packages/quant_data`; only the side-effecting *engine* lives here, in the single workspace package `packages/quant_market` (adapters / service / storage / universe). It also hosts the Trading 212 Public API v0 connector (`quant_market.adapters.trading212`) — instruments, account, portfolio, a pure rebalance planner and a triple-gated execution engine — plus an 80 GB on-disk content-addressed market store under `outputs/market` and the canonical 268-symbol `v2_no_crypto_research_universe`.

## Fuentes del dominio

- CLAUDE.md

- README.md

- .importlinter

- docs/adr/ADR-LOCAL-0001-eodhd-ingestion.md

- docs/adr/ADR-LOCAL-0002-streaming-service.md

- docs/trading212_connector.md

- docs/research/eodhd_budget.md

- docs/research/eodhd_tick_data.md

- packages/quant_market/src/quant_market/config_data/service.yaml

- packages/quant_market/src/quant_market/config_data/eodhd_source.yaml

## Invariantes

- Tier discipline: MarketDataLab is Tier 1 and may import quant_substrate and quant_data (both Tier 0) ONLY. .importlinter contract `no-higher-or-sibling-tier-imports` forbids all 15 higher/sibling lab packages by name (quant_backtest, quant_mc_core, quant_sweep_core, quant_pricing, quant_news, quant_research_core, quant_research_runner, quant_research_report, quant_intel_features, quant_intel_models, quant_intel_news, quant_intel_signals, quant_portfolio_core, quant_risk_core, quant_exec_core).

- Stage independence: the second .importlinter contract makes quant_market.adapters and quant_market.storage mutually independent — they may share only the neutral records / substrate / quant_data layers. Adapters must never import storage and vice versa.

- CLAUDE.md: "The substrate is **never duplicated** here; it is imported via path dependency during local development." quant_substrate / quant_data / quant_cache come from ~/GitHub/Shared as editable path deps.

- CLAUDE.md: "Never `--no-verify`. Never `--force` to main." Mechanically backed by the 7 permissions.deny patterns in .claude/settings.json, which also forbid rm, rmdir, git reset --hard, git clean -f and git filter-branch.

- CLAUDE.md: "One commit per logical change. Atomic per repo — the `quant_data` contract in `Shared` and the ingestion engine here are two repos and two commits." Plain English, present tense, no AI attribution, no Co-authored-by.

- Cross-repo work: same branch name across affected repos, one PR per repo with the cross-reference block, stop on the first failing pre-commit gate.

- Every adapter sits behind an explicit `Capability` grant and delegates network I/O to an injected `Transport`; adapters never touch the network or the store directly. Calling any fetch_* with capability=None raises CapabilityError.

- Temporal admissibility (KnownAt[T]): a bar is decision-admissible at bar-close for historical pulls, a tick at receipt for live feeds — never at a source-claimed instant earlier than we could have known it.

- Python 3.12, mypy --strict, frozen+slots dataclasses for value types, typing.Protocol for interfaces, hypothesis property tests; "Every public abstraction ships with at least one test."

- T212 live execution is gated by three simultaneous conditions (--execute, the exact --confirm phrase, and a clear T212_DISABLE_LIVE_TRADING kill switch); anything missing collapses the entire run back to dry-run and it never partially executes. Defaults in .env.example are T212_ENV=demo, T212_DRY_RUN=1, T212_DISABLE_LIVE_TRADING=1, T212_ALLOW_MARKET_ORDERS_LIVE=0.

- The EODHD token is read from the EODHD_API_TOKEN environment variable and is NEVER stored in eodhd_source.yaml or any config file.

- Do not regenerate or reorganise outputs/market or data/ — they are gitignored, 80 GB, and the store is the shared cross-process cache several other repos read.

## Comandos de referencia

- uv run ruff check .

- uv run ruff format --check .

- uv run mypy packages/

- uv run lint-imports

- uv run pytest

- uv run python scripts/run_scheduler.py --universe macro --replay --once

- uv run python scripts/run_scheduler.py --universe full

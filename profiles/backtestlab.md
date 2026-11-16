# BacktestLab

Raíz: `/Users/omarkhalil/GitHub/BacktestLab`. Las rutas de este perfil se interpretan desde esa raíz.
Las reglas de dominio se conservan; versiones y comandos se contrastan con los archivos actuales.
La coordinación y publicación usan el único `constellation.py`.

## Identidad

BacktestLab is the causal backtesting laboratory of QuantOS — perimeter `quantos-core`, Tier 1, status `mature`, stack `mixed` (Python + Rust + C++), per ~/GitHub/.claude/registry/repos.yaml. Its governing principle is "an evidence factory, not a trading button": a backtest is a replay of a causal information process through a decision-execution-state-accounting machine, and the output of a run is not a P&L number but an audit DAG whose BLAKE3 root hash IS the run identity. The Python engine is organised into four strictly ordered tiers under packages/ — quant_core (Tier 1, causal clock/state/kernel Φ/capability/audit DAG/IR), quant_trade (Tier 2, orders/positions/cash/PnL/MTM/commission/holding cost), quant_domain (Tier 3, corporate actions/FX/typed events), quant_backtest (Tier 4, event sources/backends/runner/reporter/wire) — plus the orthogonal quant_tridata tritemporal DuckDB store. Per .claude/registry/peers.yaml it consumes Shared, MonteCarloLab (PricingRun by hash) and Sweeplab (SweepRun by hash), and produces the typed content-addressed BacktestRun artefact consumed by RiskLab, ResearchLab, IntelligenceLab and PortfolioLab; per the constellation memory, no strategy may be promoted without BacktestLab provenance.

## Fuentes del dominio

- CLAUDE.md

- docs/architecture/AGENTS.md

- docs/architecture/kernel_contract.md

- docs/architecture/KERNEL_MAP.md

- docs/architecture/ai_development_contract.md

- docs/architecture/backtester_architecture.md

- docs/architecture/testing_and_hooks_contract.md

- docs/architecture/PEERS.md

- .importlinter

- docs/vault/labs/backtestlab/00_Doctrine.md

- docs/vault/labs/backtestlab/05_Invariants.md

- docs/adr/ADR-0003-minimal-dependency-engine.md

- docs/adr/ADR-0004-long-term-roadmap-option-c.md

- docs/adr/ADR-0043-canonical-kernel-contract.md

- docs/contributing.md

## Invariantes

- The seven non-negotiables (CLAUDE.md §'The seven non-negotiables', docs/architecture/AGENTS.md §3 — 'These are not style preferences. Violations are CI failures.'): (1) No look-ahead: `available_at(I) ≼ u` for every item read at event u; (2) Bitwise replay: same (EventSource, Capability env, RNG seed, code commit) -> bit-identical audit DAG, always; (3) Conservation: cash + position value conserved across every Fill, property-tested; (4) Capability gating: no effect fires without an explicit token in the capability environment; (5) Total transition kernel: Φ defined on every (State, Event) pair, no partial function; (6) Deterministic IR dispatch: same Plan across backends -> bitwise identical audit DAG roots; (7) Tritemporal integrity: data reads are always KnownAt[decision_time], never raw. CAVEAT for an agent: the property suites that actually test these are packages/quant_core/tests/property/test_seven_nonnegotiables.py and packages/quant_backtest/tests/property/test_seven_nonnegotiables_n6.py — the per-invariant test_file paths in .claude/registry/capabilities.yaml are all stale and resolve to nothing.

- Tier discipline: 'Lower tiers know nothing of upper tiers. Reverse imports are CI failures.' quant_core imports nothing from this repo; quant_tridata imports only quant_core; quant_trade imports quant_core; quant_domain imports quant_core + quant_trade + quant_tridata; quant_backtest imports all. Enforced mechanically by the .importlinter contract `tier-ordering` (type=layers; layers: quant_backtest > quant_domain > quant_trade | quant_tridata > quant_core). Note both CLAUDE.md and AGENTS.md state this rule using the non-existent name `quant_data`; the enforced root package is `quant_tridata`.

- ADR-0003 stdlib-first engine policy (CLAUDE.md): 'Every line in packages/ must be writable in Rust/C++ without semantic loss.' 'A new dependency in packages/ is an architectural decision and requires an ADR.' Only pyrsistent, blake3, duckdb (data tier only) and numpy (numpy_backend only) are pre-approved. .importlinter carries TEN contracts total, of which SEVEN enforce ADR-0003 (forbidding pandas; polars; scipy; sklearn+statsmodels; torch+tensorflow+jax; requests+aiohttp+httpx+fsspec; and numpy outside quant_backtest.engine.numpy_backend). Precision matters: `pyarrow` is named as forbidden in CLAUDE.md prose but is NOT enforced by any contract, while `httpx` IS enforced but is not in the prose list. The remaining three contracts are tier-ordering, capnp-only-in-wire (ADR-0005) and opentelemetry-only-in-observability (ADR-0006).

- ADR-0004 Option C gate: 'No decision that forecloses Option C.' Every change must pass: 'Does this decision preclude reaching Option C without rewriting?' (CLAUDE.md and AGENTS.md §5, both verbatim.)

- Typing discipline (CLAUDE.md §Coding standards): 'Python 3.12. mypy --strict on every package. No exceptions.' 'No `Any`. No `cast`. No `# type: ignore` without an inline explanation.' State is pyrsistent.PMap — 'Never a mutable dict for accumulated state.' Interfaces via typing.Protocol; value types via frozen dataclasses. All timestamps carry a temporal domain tag (valid_at, transaction_time, decision_time). pyproject enforces mypy strict=true with tests/ excluded.

- AGENTS.md §5 'What must never happen': no mutable dict for accumulated state; no Any/cast/type-ignore without inline justification; no partial functions on (State, Event); no raw timestamp comparisons; no side effects without a Capability token; no one-off scripts inside core package modules; no hard-coded asset class, broker, frequency, calendar, data provider, or strategy interface; no report without provenance; no numerical-method change without a convergence or regression test; no destructive bulk operation without tests; no unpublished uncertainty — 'if you do not know, say so'.

- The kernel contract docs/architecture/kernel_contract.md is BINDING (CLAUDE.md: 'The kernel contract is binding'), as is docs/architecture/ai_development_contract.md. CLAUDE.md: 'Read docs/architecture/AGENTS.md before every coding session.'

- The perf baseline (benchmarks/baseline.json) is never regenerated automatically (.github/workflows/bench.yml: 'The baseline is NEVER updated automatically'); the docs/vault/ tree is a mirror and must not be hand-edited (the OmarOS vault is the source of truth — re-sync with scripts/sync_vault.sh).

- Commit granularity: 'Commit granularly — one conceptual change per commit' (AGENTS.md §8 step 10), then report what changed, why, which invariant was preserved or added, and which tests were run (step 11).

## Comandos de referencia

- bash scripts/setup_venv.sh

- bash scripts/setup_venv.sh --clean

- bash scripts/check.sh

- bash scripts/check.sh --quick

- .venv/bin/mypy packages/

- .venv/bin/pytest packages/ -q

- .venv/bin/pytest packages/ -q -m 'not property'

- .venv/bin/lint-imports

- .venv/bin/python .claude/tests/run_tests.py

- .venv/bin/python .claude/tests/run_tests.py --quick

- .venv/bin/python benchmarks/perf_check.py --baseline benchmarks/baseline.json --current benchmarks/results/rust_results.json --lang rust

- cargo test --workspace --manifest-path rust/Cargo.toml

- cargo bench --manifest-path rust/quant_core/Cargo.toml

- cargo bench --manifest-path rust/quant_trade/Cargo.toml

- .venv/bin/python benchmarks/parse_criterion.py

- UV_PROJECT_ENVIRONMENT=.venv uv venv --python 3.12 .venv

- UV_PROJECT_ENVIRONMENT=.venv uv sync --all-packages --extra test --extra dev --group dev

- uv sync --all-packages --extra test --extra dev --group dev

- .venv/bin/pytest packages/ tests/ -x --tb=short -q -m "not slow"

- .venv/bin/pytest packages/ --cov --cov-report=term-missing --cov-report=html:.coverage_html

- .venv/bin/ruff check packages/

- .venv/bin/ruff format packages/

- .venv/bin/ruff check packages/ --statistics

- .venv/bin/pre-commit install

- .venv/bin/pre-commit run --all-files

- uv run lint-imports

- bash scripts/sync_vault.sh

- bash scripts/refresh_baseline.sh

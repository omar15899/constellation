# PortfolioLab

Raíz: `/Users/omarkhalil/GitHub/PortfolioLab`. Las rutas de este perfil se interpretan desde esa raíz.
Las reglas de dominio se conservan; versiones y comandos se contrastan con los archivos actuales.
La coordinación y publicación usan el único `constellation.py`.

## Identidad

PortfolioLab is the QuantOS Tier-2.5 portfolio-construction lab and the sole member of the `quantos-alloc` perimeter (verified in ~/GitHub/.claude/registry/repos.yaml). Per .claude/registry/peers.yaml it consumes Shared (Tier 0), BacktestLab BacktestRun (Tier 1), IntelligenceLab CounterfactualEstimate and ResearchLab Study (Tier 2), and produces the `Allocation` and `PortfolioSnapshot` artefacts consumed by RiskLab and ExecutionLab (Tier 3); per ADR-0026 it is the single source of truth for portfolio state at runtime. Its doctrine, architecture and invariants are canonical in the OmarOS vault, not here — this repo mirrors them into docs/vault/ and CLAUDE.md requires they be read before any code is written. Both CLAUDE.md and the constellation registry still label the repo a "stub"; that is stale — two real workspace packages ship (quant_portfolio: the Allocation artefact plus optimize; quant_portfolio_core: live-account reconciliation), 17 tests pass when run per package, and the Tier-2.5 import contract is enforced and green.

## Fuentes del dominio

- CLAUDE.md

- README.md

- docs/architecture/AGENTS.md

- docs/HANDOFF_PROMPT.md

- docs/architecture/PEERS.md

- docs/architecture/lab_architecture.md

- .claude/registry/peers.yaml

- /Users/omarkhalil/OmarOS/05_Projects/QuantOS/Labs/PortfolioLab/Vision/00_Doctrine.md

- docs/architecture/ai_development_contract.md

- docs/architecture/testing_and_hooks_contract.md

- docs/vault/AGENTS.md

- docs/vault/documentation/ai_reading_order.md

- docs/vault/documentation/ai_development_contract.md

- docs/vault/decisions/ADR-0026-portfolio-intelligence-layer.md

- docs/vault/decisions/ADR-0020-shared-substrate-not-duplicated.md

- docs/vault/decisions/ADR-0031-substrate-extraction.md

- docs/vault/decisions/ADR-0033-shared-venv-github-centralized.md

- docs/vault/decisions/ADR-0032-lab-ai-scaffold-uniform.md

- docs/vault/vision/01_Architecture.md

- .importlinter

- tests/cross_repo/README.md

- docs/adr/ADR-LOCAL-TEMPLATE.md

## Invariantes

- Tier-2.5 import discipline, machine-enforced. .importlinter declares contract `no-higher-or-sibling-tier-imports`: source_modules quant_portfolio, quant_portfolio_core may never import quant_risk, quant_risk_core, quant_risk_metrics, quant_risk_monitor, quant_risk_limits, quant_exec_core, quant_exec_broker, quant_exec_ledger, quant_exec_pretrade, strategy_orchestration_lab. Verified 2026-07-30: `uv run lint-imports` -> 'Analyzed 12 files, 16 dependencies. ... Contracts: 1 kept, 0 broken.' Its own comment: 'PortfolioLab is Tier 2.5: it may import the Tier-0 substrate ... and strictly lower-tier lab packages (Tiers 1, 1.5, 2). It must never import an equal-or-higher-tier QuantOS lab package.' Enforced un-masked in both lint.yml and import-linter.yml.

- The substrate is never duplicated. CLAUDE.md: 'Per [[ADR-0020]] and [[ADR-0031]] the substrate is **never duplicated** in this repo; it is imported from `Shared` via path dependency during local development.'

- The vault is canonical, this repo is not. CLAUDE.md: 'The doctrine, architecture, schema strategy, and invariants are canonical in the OmarOS vault and **must be read before any code is written here**.' docs/architecture/AGENTS.md is headed '> **Read first. Always.**'

- The eight allocation invariants I-1..I-8 (retained allocation doctrine) bind every allocation: I-1 universe_hash(w*) = universe_hash(Sigma) = universe_hash(mu) = universe_hash(IntelligenceBundle); I-2 Sigma >= 0 verified by Cholesky, projection method recorded when used; I-3 ConstraintSet certified non-empty before solver dispatch (typed feasibility, not an exception handler); I-4 available_at(I) <= decision_time for every input; I-5 every contributing CF estimator id and BacktestRun ancestry present in Allocation.metadata; I-6 same (Sigma, mu, ConstraintSet, pi, w_prev, IntelligenceBundle) -> bit-identical w*; I-7 no input window strictly later than decision_time; I-8 AuditDAG chains back to every input and replay reproduces w*. NOTE: these are doctrine text plus AST-heuristic warnings in portfolio_preflight.py — nothing in packages/ enforces them in code today.

- Constraints are typed leaves, never strings, never lambdas (LongOnly | LeverageCap | TurnoverCap | SectorCap | FactorBox | PositionBox | Cardinality | And). Infeasibility is a typed error, not a silently-returned zero vector.

- Determinism: no global RNG in allocators. Any randomness routes through a counter-based RNG keyed by the allocation context (the counter-based RNG discipline of ADR-0016). The portfolio_preflight hook greps for np.random.normal/uniform/randn, numpy.random.normal/uniform, random.random(, random.gauss(.

- State is immutable: pyrsistent.PMap for accumulated state, dataclasses(frozen=True) for value types, typing.Protocol for interfaces, side effects through the Capability environment (ADR-0013). Source: CLAUDE.md §Coding standards. The preflight hook additionally warns on `= {}` and `= dict()`.

- Engine/application boundary (ADR-0003): packages/quant_portfolio is stdlib-first. cvxpy, scipy.optimize, osqp, ecos, numpy, pandas belong in allocators/, not in packages/. The engine consumes typed Allocator protocols; solver choice is a property of the script. (packages/quant_portfolio does declare numpy>=1.26 as a dependency, so the stdlib-first rule is aspirational for numpy.)

- Python 3.12, mypy --strict, hypothesis property tests + pytest unit tests, and 'Every public abstraction ships with at least one test' (CLAUDE.md §Coding standards).

- Cross-repo contract tests pin siblings by commit hash, never by main: tests/cross_repo/README.md — 'Pin by commit hash. Never test against `main` of a sibling — pin in pinned_versions.yaml and bump explicitly.' (Currently unenforced: the Shared pin is the literal string HEAD and the tests skip.)

- If the request belongs to a sibling lab, say so and stop. Stated twice: docs/architecture/AGENTS.md §Cross-lab awareness and .claude/registry/peers.yaml §'Cross-lab invocation discipline' rule 1.

- Every non-trivial change reports in the ai_development_contract §3 shape, verbatim from docs/architecture/AGENTS.md §Output contract: What changed / Why / Files touched / Public API delta / Tests added-updated / Tests run (command + outcome) / Invariants checked (I-N list, or N/A) / Risks remaining.

- The shared Constellation publication contract applies: one commit per repo per logical change, never bundled across repos; no --no-verify; no --force to main. This repo's own .claude/settings.json deny list additionally blocks rm, rmdir, curl, wget, git reset --hard, git push --force/-f, git clean -f/-fd and git filter-branch outright.

- Publication uses the common reviewed Constellation workflow; retired automatic Git hooks are not an enforcement mechanism.

## Retained domain procedure

A BacktestRun supplying an allocation, directly or through a counterfactual estimator, must close before the allocation's decision time. Record contributing estimator IDs, BacktestRun ancestry, dataset hashes and weighting parameters. Record covariance projection methods instead of hiding repairs. Reconciliation failure blocks an ExecutionIntent until the portfolio snapshot is reconciled; replay must reconstruct the allocation from its recorded inputs.

Consult `docs/vault/decisions/ADR-0026-portfolio-intelligence-layer.md`; preserve typed feasibility, causal input timing and deterministic-RNG obligations.

## Validation and publication

The commands below are references, not automatic authorization. Create, change or run tests only when Omar explicitly requests them. Record permitted checks and independent review through Constellation; any test-dependent gate without authorized evidence remains unmet. Domain hooks are additional controls, not proof that the outer Constellation commit ran the required checks. No startup, documentation or skill workflow publishes automatically.

## Reference commands

- uv sync --all-packages

- uv sync --frozen || uv sync

- uv run pytest packages/ tests/ -x --tb=short -q -m "not slow"

- uv run pytest packages/quant_portfolio/tests -q

- uv run pytest packages/quant_portfolio_core/tests -q

- uv run ruff check .

- uv run ruff format --check .

- uv run mypy packages/

- uv run mypy packages/quant_portfolio/src

- uv run mypy packages/quant_portfolio_core/src

- uv run lint-imports

- python3 /Users/omarkhalil/GitHub/PortfolioLab/.claude/tests/run_tests.py

- PYTHONPATH=/Users/omarkhalil/GitHub/PortfolioLab/packages/quant_portfolio_core/src /Users/omarkhalil/GitHub/MarketDataLab/.venv/bin/python /Users/omarkhalil/GitHub/PortfolioLab/scripts/reconcile_t212_v1.py

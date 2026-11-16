# PricingLab

Raíz: `/Users/omarkhalil/GitHub/PricingLab`. Las rutas de este perfil se interpretan desde esa raíz.
Las reglas de dominio se conservan; versiones y comandos se contrastan con los archivos actuales.
La coordinación y publicación usan el único `constellation.py`.

## Identidad

PricingLab is the QuantOS pricing evaluator: it turns a calibrated model plus market data into certified prices, emitted as typed `PricingRun` artefacts whose root hash is the price's identity and which are regenerable bit-for-bit from config plus audit DAG. Perimeter `quantos-core`, Tier 1.5, stack python, status `stub` — as declared in ~/GitHub/.claude/registry/repos.yaml and enforced by this repo's .importlinter. Per .claude/registry/peers.yaml it consumes Shared and MonteCarloLab and produces PricingRun artefacts for BacktestLab, RiskLab, ResearchLab and ExecutionLab, sitting between the Tier-1 numerical labs and the Tier-2.5+ allocation/risk labs. The repo is deliberately thin: the doctrine, architecture, calibration model, schema strategy and invariants are canonical in the OmarOS vault at ~/OmarOS/05_Projects/QuantOS/Labs/PricingLab/Vision/ (mirrored locally under docs/vault/lab_vision/) and must be read before any code is written here.

## Fuentes del dominio

- CLAUDE.md

- docs/HANDOFF_PROMPT.md

- docs/architecture/AGENTS.md

- docs/architecture/PEERS.md

- .claude/registry/peers.yaml

- docs/vault/AGENTS.md

- docs/vault/documentation/ai_reading_order.md

- docs/vault/documentation/ai_development_contract.md

- docs/vault/documentation/testing_and_hooks_contract.md

- docs/vault/lab_vision/00_Doctrine.md

- docs/vault/lab_vision/01_Architecture.md

- docs/vault/lab_vision/02_Calibration_Model.md

- docs/vault/lab_vision/03_Schema_Strategy.md

- docs/vault/lab_vision/05_Invariants.md

- docs/vault/lab_vision/07_Build_Order_A_Lean.md

- docs/vault/lab_vision/08_Smile_Interpolators.md

- docs/architecture/lab_architecture.md

- .importlinter

- tests/cross_repo/README.md

## Invariantes

- Tier 1.5 import discipline, machine-enforced. The .importlinter contract `no-higher-tier-imports` forbids quant_pricing from importing any of 25 named Tier-2+ packages (quant_news, quant_research + 3 variants, quant_insights, quant_intel + 4 variants, quant_portfolio + 3 variants, quant_risk + 4 variants, quant_exec_core/pretrade/broker/ledger, strategy_orchestration_lab). The file states: "CI enforces this; inverting an arrow is a release blocker." Run by `uv run lint-imports` in both lint.yml and import-linter.yml; currently PASSES (1 kept, 0 broken, 9 files / 13 dependencies analysed).

- Read the vault first. CLAUDE.md: "The doctrine, architecture, schema strategy, calibration model, invariants and build orders are already canonical in the OmarOS vault and **must be read before any code is written here**."

- Never duplicate Shared abstractions. CLAUDE.md: "No duplication of `quant_core` / `quant_data` abstractions — import from `Shared/`." ADR-0020 is cited in the Closest-siblings section; docs/architecture/AGENTS.md repeats it alongside ADR-0031.

- mypy --strict is the type bar. CLAUDE.md coding standards: "Python 3.12, `mypy --strict`, `pyrsistent.PMap` for state, `typing.Protocol` for interfaces, `dataclasses(frozen=True)` for value types." Both pyproject.toml files set [tool.mypy] strict = true; the package one additionally sets disallow_any_generics.

- Every public abstraction ships with a test. CLAUDE.md: "Every numerical method change ships with a closed-form moment match and a convergence-rate test." Property tests with hypothesis, unit tests with pytest.

- Every non-trivial change reports in the ai_development_contract §3 output shape (What changed / Why / Files touched / Public API delta / Tests added-updated / Tests run / Invariants checked / Risks remaining) — verbatim template in docs/architecture/AGENTS.md §Output contract.

- Destructive git and network commands are denied at the settings level: rm, rmdir, curl, wget, git reset --hard, git push --force, git push -f, git clean -f, git clean *-fd*, git filter-branch. This is a permissions deny list, not a hook.

- Auto-push is off: PRICINGLAB_AUTO_PUSH=0 in .claude/settings.json env; post_git_safety_loop.py pushes only when that var is 1/true/yes.

- Cross-repo contract tests pin siblings by commit hash, never against main — tests/cross_repo/README.md §Discipline 1, mandated by ADR-0030 §3. (Documentary only: the pin currently reads `HEAD`.)

- DOCTRINAL, NOT MACHINE-ENFORCED — the following six come from .claude/skills/pricing-pipeline-doctrine/SKILL.md contract_invariants, which is a reviewer contract; the only in-repo mechanism (pricing_preflight.py) implements weak source-level heuristics for four of them and is warn-only by default. (1) MeasureSpec discipline — "A Price without a declared measure is rejected — never warned." (2) Calibration provenance is eight fields or it is not a CalibratedModel: market_state_hash, instrument_set, loss_spec, optimiser_spec, residual_surface, convergence_trace, calibration_timestamp, bundle_hash, BLAKE3-hashed canonically (ADR-0023). (3) Repricing closure — CalibrationSpec.production_algorithm_id must equal the algorithm dispatched at production; a mismatch without an explicit waiver is flagged RepricingClosureViolation. (4) Roper static no-arbitrage is a hard constraint: every Surface/SmileFit carries a certificate covering calendar (∂_T w ≥ 0), butterfly (Gatheral g(k) ≥ 0) and vertical (put-call parity) on a fine grid; "Penalty methods are forbidden... A surface without a certificate is not a Surface." (5) Discounting separation — D(t,T) lives in MarketState; a Payoff taking a `risk_free_rate: float` constructor argument or hard-coding a D(t,T) literal fails review (doctrine non-negotiable #1). (6) Verdict alphabet is closed: CERTIFIED / PROVISIONAL / REJECTED, and "PROVISIONAL is never a free pass."

- The Claude Code PreToolUse commit gate fires only when packages/ is staged. Non-packages commits bypass its mypy and tests.

## Comandos de referencia

- uv run ruff check .

- uv run ruff format --check .

- uv run mypy packages/

- uv run lint-imports

- uv run pytest packages/ tests/ -x --tb=short -q -m "not slow"

- uv sync --frozen || uv sync

- uv run pytest packages/ -x --tb=short -q -m "not slow"

- python3 /Users/omarkhalil/GitHub/PricingLab/.claude/tests/run_tests.py

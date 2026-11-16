# MonteCarloLab

Raíz: `/Users/omarkhalil/GitHub/MonteCarloLab`. Las rutas de este perfil se interpretan desde esa raíz.
Las reglas de dominio se conservan; versiones y comandos se contrastan con los archivos actuales.
La coordinación y publicación usan el único `constellation.py`.

## Identidad

MonteCarloLab is the stochastic-pricing laboratory of QuantOS: perimeter quantos-core, tier 1, status mature in ~/GitHub/.claude/registry/repos.yaml. Its governing doctrine is that a Monte Carlo run is not a price but an EstimatedQuantity (value + standard error + confidence interval + diagnostics + audit hash) whose root in a BLAKE3 content-addressed audit DAG is the run identity — "no construyas un botón para tradear, construye una fábrica de evidencia". The code is an eighteen-layer measure-theoretic stack grouped into four uv-workspace packages (quant_mc_core layers 0 + 17, quant_mc_paths layers 1-8, quant_mc_pricer layers 9-11 + 13-16, quant_mc_aad layer 12) exposing four primitives: Sample, Observe, Score, Condition. It is intended to consume the Tier-0 Shared substrate (quant-core) read-only — that coupling is documented but not yet declared in any package's dependencies — and it produces PricingRun / EstimatedQuantity artefacts for BacktestLab, PricingLab and ResearchLab (.claude/registry/peers.yaml).

## Fuentes del dominio

- CLAUDE.md

- docs/architecture/AGENTS.md

- docs/architecture/ai_development_contract.md

- docs/vault/labs/montecarlolab/00_Doctrine.md

- docs/vault/labs/montecarlolab/01_Architecture.md

- docs/vault/labs/montecarlolab/05_Invariants.md

- docs/architecture/montecarlolab_architecture.md

- .importlinter

- docs/adr/README.md

- docs/design/condition_primitive.md

- docs/architecture/testing_and_hooks_contract.md

- docs/architecture/PEERS.md

- .claude/registry/peers.yaml

## Invariantes

- Measure-First Rule (CLAUDE.md §Routing, labelled 'non-negotiable'): for any PIPELINE or MIXED request involving a new pricer, model family, estimator, or measure change, the chain `mc-intake -> measure-architect -> rng-architect -> estimator-strategist` MUST run BEFORE kernel-engineer or pricer-builder. 'Measure-theoretic correctness ... cannot be retrofit.' Encoded in commands.yaml (requires_measure_first) and intent_taxonomy.yaml (mandatory_sequence).

- Package dependency ordering: quant_mc_core -> quant_mc_paths -> quant_mc_pricer -> quant_mc_aad, one direction only. CLAUDE.md, twice: 'Reverse imports are CI failures.' Enforced by .importlinter contract [importlinter:contract:layer-ordering] (type = layers).

- The eight doctrinal non-negotiables (CLAUDE.md: 'These are not style preferences. Violations are CI failures.'): (1) separation of concerns across eight independently configurable components; (2) counter-based RNG, partition-invariant — bit-identical samples under any partition (1 thread, 1024 threads, 8 GPUs); (3) CRN preserved across bumps — a greek bump uses the same coordinates as the base run; (4) AAD modular, JAX primary (vault ADR-0017), Enzyme secondary, custom-tape didactic-only; (5) result = SE + CI + diagnostics + audit, 'a bare price never escapes the Score layer'; (6) serialisable, hashable, replayable Cap'n Proto MonteCarloPlan; (7) cashflow accrual != numeraire conversion; (8) explicit measure on every estimator — 'An estimator without a MeasureSpec is rejected.'

- No global RNG (invariant I-3, CLAUDE.md §Coding standards and AGENTS.md §5): 'Every random draw is addressable by an explicit RandomCoordinate. No global RNG. No np.random.normal() outside the RNG adapter.'

- State that accumulates is pyrsistent.PMap, never a mutable dict. Interfaces via typing.Protocol, value types via @dataclass(frozen=True, slots=True).

- mypy --strict on every package (pyproject [tool.mypy] strict = true, python_version 3.12, tests excluded). CLAUDE.md: 'No Any. No cast. No # type: ignore without an inline explanation.'

- Dependency policy in packages/ is closed (CLAUDE.md §Dependency policy, per-package table): quant_mc_core may use pyrsistent, blake3, numpy; quant_mc_paths and quant_mc_pricer add scipy, jax, jaxlib; quant_mc_aad is jax/jaxlib only. Forbidden in packages/: pandas, polars, pyarrow (outside DuckDB), pytorch, tensorflow, requests, aiohttp, fsspec. 'A new dependency in packages/ is an architectural decision and requires an ADR.' pricers/ and review/ are unconstrained. NOTE the enforcement is narrower than the prose: .importlinter has forbidden contracts for pandas, polars, torch, tensorflow, requests, aiohttp, httpx and fsspec only — pyarrow is NOT machine-enforced.

- Two further .importlinter contracts beyond layering: [no-jax-in-core] forbids jax/jaxlib inside quant_mc_core ('core is the value-type substrate'), and [capnp-only-in-wire] forbids capnp in quant_mc_core.{coordinate,seed,measure,plan,estimated,audit} — serialisation must go through dedicated wire/ adapters.

- Option C gate (local ADR-0004, restated in AGENTS.md §5): every decision must answer 'Does this decision preclude reaching Option C without rewriting?' The Option C documents (docs/vault/labs/montecarlolab/06_Build_Order_C_Granular.md) are the target, not deferred work.

- AGENTS.md §5 'What must never happen': no raw value escaping the Score layer — always wrapped in EstimatedQuantity (D5); no discount/numeraire factor bundled inside a cashflow expression (D7, I-11); no estimator without a MeasureSpec (D8, I-12); no AAD pathwise greek on a non-smooth payoff without a typed I-13 warning; no MonteCarloPlan whose Cap'n Proto round-trip loses information (D6).

- docs/architecture/AGENTS.md must be read before every coding session (CLAUDE.md line 126; ADR-0002 calls it 'the canonical entrypoint for every coding session'); docs/architecture/ai_development_contract.md is binding; repo-local ADRs live in docs/adr/ and QuantOS-wide ADRs in docs/vault/decisions/ (see docs/adr/README.md — the two numbering schemes are independent).

- docs/vault/ is a read-only mirror of the OmarOS vault — the vault is the source of truth, re-sync with `bash scripts/sync_vault.sh`, never hand-edit the mirror.

- Constellation git policy applies: one commit per repo per logical change, natural human commit messages, no AI attribution or Co-authored-by, no --no-verify, no --force to main. settings.json hard-denies rm, rmdir, curl, wget, git reset --hard, git push --force, git push -f, git clean -f, git clean *-fd*, git filter-branch.

- Canonical AI development loop (docs/architecture/AGENTS.md §9, 'Do not skip steps'): read AGENTS.md + CLAUDE.md -> read the relevant Vision doc and ADRs -> read existing code -> smallest safe change -> implement -> add/update the named invariant test -> `uv run pytest packages/<pkg>/ -q` -> `uv run mypy packages/ && uv run pytest packages/ -q` -> update docs -> commit granularly -> report what changed, why, and which invariant was preserved.

## Comandos de referencia

- bash scripts/setup_venv.sh

- bash scripts/check.sh

- bash scripts/sync_vault.sh

- .venv/bin/mypy packages/

- .venv/bin/pytest packages/ -q

- .venv/bin/lint-imports

- uv sync --all-extras --all-packages

- uv run ruff check .

- uv run ruff format --check .

- uv run mypy packages/

- uv run pytest packages/ tests/ -x --tb=short -q -m "not slow"

- uv run lint-imports

- uv run pytest packages/<pkg>/ -q

- uv run pytest packages/ -q

- python3 .claude/tests/run_tests.py --quick

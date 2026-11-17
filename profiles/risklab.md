# RiskLab

Raíz: `/Users/omarkhalil/GitHub/RiskLab`. Las rutas de este perfil se interpretan desde esa raíz.
Las reglas de dominio se conservan; versiones y comandos se contrastan con los archivos actuales.
La coordinación y publicación usan el único `constellation.py`.

## Identidad

RiskLab is the QuantOS Tier-3 risk-certification lab and the mandatory gate between allocation and execution: exposure aggregation, factor decomposition, VaR/CVaR, drawdown monitors, regime classifiers, stress batteries and limit enforcement. Its output artefact is the content-addressed RiskCert — per CLAUDE.md, "Every BacktestRun must pass RiskLab before becoming an OrderProposal-eligible artefact." It sits in perimeter `quantos-prod` alongside ExecutionLab, and per .claude/registry/peers.yaml consumes from Shared (Tier 0 substrate), BacktestLab (BacktestRun), PricingLab (PricingRun) and PortfolioLab (Allocation), producing RiskCert/ExposureReport for ExecutionLab. The repo is registered as `status: stub` and its own docs still describe it as one: a 16-agent AI scaffold, 14 commands and a 112-file vault mirror sit on top of exactly one implemented package (packages/quant_risk: RiskCert/certify, historical/parametric VaR, Limit — 11 passing tests) plus four git-tracked package skeletons whose __init__.py files do not even parse.

## Fuentes del dominio

- CLAUDE.md

- README.md

- docs/HANDOFF_PROMPT.md

- docs/architecture/AGENTS.md

- docs/architecture/lab_architecture.md

- docs/architecture/PEERS.md

- .claude/registry/peers.yaml

- /Users/omarkhalil/OmarOS/05_Projects/QuantOS/Labs/RiskLab/Vision/00_Doctrine.md

- .importlinter

- docs/architecture/ai_development_contract.md

- docs/architecture/testing_and_hooks_contract.md

- docs/vault/AGENTS.md

- docs/vault/documentation/ai_reading_order.md

- docs/vault/documentation/meta_architecture.md

- docs/vault/vision/01_Architecture.md

- docs/vault/decisions/ADR-0020-shared-substrate-not-duplicated.md

- docs/vault/decisions/ADR-0031-substrate-extraction.md

- docs/vault/decisions/ADR-0032-lab-ai-scaffold-uniform.md

- docs/vault/decisions/ADR-0033-shared-venv-github-centralized.md

- tests/cross_repo/README.md

## Invariantes

- Tier discipline (hard, machine-enforced, and currently GREEN). .importlinter contract `no-higher-or-sibling-tier-imports`: "quant_risk does not import higher-tier or sibling QuantOS labs" — forbidden_modules = quant_exec_core, quant_exec_broker, quant_exec_ledger, quant_exec_pretrade, strategy_orchestration_lab. Per the contract's own comment, RiskLab (Tier 3) may import the Tier-0 substrate and any strictly lower tier (1, 1.5, 2, 2.5), never the sibling Tier-3 ExecutionLab nor Tier-4 orchestration. Verified: `uv run lint-imports` analysed 9 files / 14 dependencies, 1 kept, 0 broken. import-linter.yml is the only hard-failing workflow.

- Substrate is never duplicated. CLAUDE.md: "Per [[ADR-0020]] and [[ADR-0031]] the substrate is **never duplicated** in this repo; it is imported from `Shared` via path dependency during local development."

- The retained risk doctrine has ten invariants (I1..I10). A single FAIL on the ENFORCEMENT subset — I1, I3, I4, I6, I10 — is BLOCKING: the artefact does not leave RiskLab. The native coordinator assigns the failure to an author applying this profile and the canonical risk doctrine, then commissions independent verification before publication.

- I1-Gate: for every BacktestRun that is order-proposal-eligible there must exist a RiskReport with cert.run_id = run.id, recommendation != block, age <= MAX_RISK_REPORT_AGE, cert.limits_version = run.limits_version and cert.dataset_version = run.dataset_version. (policy_linkage RISK_POLICY R5, R6)

- I2-TypedLimits: every limit dimension is a typed field on RiskLimits with BOTH a red and an amber threshold; RiskLimits is append-only — every amendment is a new version with a valid_from timestamp and a stated rationale. (R1, R10)

- I3-DimensionAdditive: a breached limit blocks ExecutionIntents that would worsen THAT dimension; intents that improve a breached dimension pass. Global stops live in the kill-switch (R4), never in the limit machinery.

- I4-BlockIsFinal: a `block` PreTradeRiskReport is non-advisory. There is no override path inside RiskLab. Code that catches a Breach exception and continues, or maps `block` -> `pass`, violates the invariant. (R6)

- I5-PricingProvenance: every Exposure / RiskReport records the PricingRun id (or analytic equivalent) of the Greeks it consumed. RiskLab never recomputes Greeks silently; aggregation is linear in positions.

- I6-DatasetVersionPin: the certificate's dataset_version equals the BacktestRun's dataset_version; a mismatch is a hard preflight failure.

- I7-FactorModelVersioned: the factor model used in any RiskReport is identified by version and stored as a ModelArtifact; out-of-sample validation must precede promotion to live use.

- I8-RegimeNeverOverridesLimits — STATED PRECISELY (an earlier brief hardened this into a false absolute): "The regime tag is informative. It MAY modulate amber thresholds when authorised by risk-architect. It MAY NOT override a red limit." Amber modulation is permitted with risk-architect authorisation; only red override is forbidden.

- I9-StressOnEverySnapshot: the standard stress battery (Doctrine §4) runs on every PortfolioSnapshot and the results are stored on the snapshot; ΔNAV <= −25% under any standard scenario emits an amber alert. (R7)

- I10-NoSilentBreach: a breach is an event — it must be logged, surfaced, and resolve to a block, an amber, or a structural amendment. Swallowed breaches (try/except pass; recommendation flipped without a new RiskLimits version) are a doctrinal violation. (R1, R6)

- Coding standards (CLAUDE.md, aspirational — see gotchas for what is actually enforced): Python 3.12, `mypy --strict`, `pyrsistent.PMap` for state, `typing.Protocol` for interfaces, `dataclasses(frozen=True)` for value types; property tests with hypothesis, unit tests with pytest; "Every public abstraction ships with at least one test"; side effects flow through the `Capability` environment ([[ADR-0013]]).

- Cross-repo contract tests pin siblings by commit hash. tests/cross_repo/README.md: "1. **Pin by commit hash.** Never test against `main` of a sibling — pin in `pinned_versions.yaml` and bump explicitly. 2. **One test file per sibling.** 3. **Test the contract, not the implementation.**" (Currently unsatisfied — the Shared pin is the literal string HEAD.)

- Vault beats repo. CLAUDE.md: "The doctrine, architecture, schema strategy, and invariants are canonical in the OmarOS vault and **must be read before any code is written here**." ~/OmarOS/ is read-only from any session running under ~/GitHub/.

- The pre-commit gate is not advisory (with two caveats). pre_commit_gate.py fires on PreToolUse Bash(git commit*); if any staged path starts with packages/ it runs `uv run mypy packages/` then `uv run pytest packages/ -x --tb=short -q -m "not slow"` from the lab root and emits {"decision":"block"} + exit 2 on failure. Caveat 1: it skips entirely when nothing under packages/ is staged. Caveat 2: it fails OPEN if uv is missing or either subprocess times out (120s mypy / 300s pytest).

## Retained domain procedure

A risk review identifies the artifact and subject, each invariant verdict and its supporting evidence, an overall verdict, failing invariants and required actions. Failure of I1, I3, I4, I6 or I10 blocks release. Policy-authorized review may permit the stated amber-threshold modulation; it never permits overriding a red limit or silently converting a blocking result into a pass.

The canonical `/Users/omarkhalil/OmarOS/05_Projects/QuantOS/Vision/Policies/RISK_POLICY.md` governs these decisions alongside the ten invariants above.

## Validation and publication

The commands below are references, not automatic authorization. Create, change or run tests only when Omar explicitly requests them. Record permitted checks and independent review through Constellation; any test-dependent gate without authorized evidence remains unmet. Domain hooks are additional controls, not proof that the outer Constellation commit ran the required checks. No startup, documentation or skill workflow publishes automatically.

## Reference commands

- uv sync --all-packages --frozen

- uv sync --frozen

- uv run pytest packages/ tests/ -x --tb=short -q -m "not slow"

- uv run pytest packages/ -x --tb=short -q -m "not slow"

- uv run ruff check .

- uv run ruff format --check .

- uv run mypy packages/

- uv run lint-imports

- python3 /Users/omarkhalil/GitHub/RiskLab/.claude/tests/run_tests.py

# IntelligenceLab

Raíz: `/Users/omarkhalil/GitHub/IntelligenceLab`. Las rutas de este perfil se interpretan desde esa raíz.
Las reglas de dominio se conservan; versiones y comandos se contrastan con los archivos actuales.
La coordinación y publicación usan el único `constellation.py`.

## Identidad

IntelligenceLab is the QuantOS Tier-2 counterfactual / causal-inference lab, perimeter `quantos-info` (sibling to NewsLab and ResearchLab), registry status `stub` in ~/GitHub/.claude/registry/repos.yaml. Its mission is to build Structural Causal Models and surface typed, content-addressed `CounterfactualEstimate` artefacts (via DoWhy for graph utilities/identification and Pyro for the do-operator and twin-network counterfactuals, per ADR-0019) consumed downstream by ResearchLab and PortfolioLab. It consumes the Tier-0 substrate from ~/GitHub/Shared (an editable path dependency on quant_substrate) plus — declared in .claude/registry/peers.yaml but not yet wired in code — NewsLab FeatureSets and BacktestLab BacktestRuns, and is forbidden by its .importlinter contract from importing sibling Tier-2 or any higher-tier lab. The repo is deliberately thin — one working package (quant_intel: a pure-Python IPW ATE estimator) plus four empty scaffold packages, with no DoWhy/Pyro code present — because the doctrine, architecture and invariants are canonical in the OmarOS vault, mirrored read-only into docs/vault/.

## Fuentes del dominio

- CLAUDE.md

- README.md

- docs/architecture/AGENTS.md

- docs/HANDOFF_PROMPT.md

- docs/architecture/lab_architecture.md

- docs/architecture/PEERS.md

- .claude/registry/peers.yaml

- .claude/skills/causal-inference-doctrine/SKILL.md

- .importlinter

- docs/vault/AGENTS.md

- docs/vault/lab_vision/00_Doctrine.md

- docs/vault/documentation/ai_reading_order.md

- docs/vault/documentation/ai_development_contract.md

- docs/vault/documentation/testing_and_hooks_contract.md

- docs/vault/decisions/ADR-0019-counterfactual-scm-dowhy-pyro.md

- docs/vault/decisions/ADR-0020-shared-substrate-not-duplicated.md

- docs/vault/decisions/ADR-0027-intelligence-pipeline.md

- docs/vault/decisions/ADR-0031-substrate-extraction.md

- docs/vault/decisions/ADR-0032-lab-ai-scaffold-uniform.md

- docs/vault/decisions/ADR-0033-shared-venv-github-centralized.md

- tests/cross_repo/README.md

- outputs/README.md

- docs/adr/ADR-LOCAL-TEMPLATE.md

## Invariantes

- Tier-2 import contract (.importlinter, contract `no-higher-or-sibling-tier-imports`): "quant_intel does not import higher-tier or sibling QuantOS labs" — forbidden modules are quant_news, quant_research_core, quant_research_runner, quant_research_report, quant_research, quant_insights, quant_portfolio_core, quant_portfolio_analytics, quant_portfolio_optimizer, quant_portfolio, quant_risk_core, quant_risk_limits, quant_risk_metrics, quant_risk_monitor, quant_risk, quant_exec_core, quant_exec_broker, quant_exec_ledger, quant_exec_pretrade, strategy_orchestration_lab. Enforced by `uv run lint-imports` in a hard-failing CI job — this is the ONLY genuinely hard gate in CI besides ruff.

- I-CI-1 (causal-inference-doctrine skill): "Assumptions are declared, not implicit. Every counterfactual carries a typed list of assumptions; an empty list is a doctrine violation."

- I-CI-2: "Identifiability before estimation. No estimator runs without an Estimand record whose verdict is identifiable or identifiable-on-subregion."

- I-CI-3: "Acyclicity. The SCM graph is acyclic. The intelligence_preflight hook enforces this on every run." (Doctrine text. In fact the hook is warn-only unless INTELLIGENCELAB_ENFORCE_PREFLIGHT=1 — settings.json sets it to 0 — and it currently matches no path in the repo. Honour the invariant as doctrine; do not rely on the hook to catch a violation.)

- I-CI-4: "Distribution kind is typed. Every CounterfactualEstimate carries distribution_kind in {observational, interventional, counterfactual}; conflating P(Y|X), P(Y|do(X)), P(Y_x|.) is a doctrine violation." (Note: the shipped CounterfactualEstimate dataclass in packages/quant_intel/src/quant_intel/causal.py has no distribution_kind field yet — adding it is required work, not an existing guarantee.)

- I-CI-5: "Sensitivity is mandatory. No effect leaves IntelligenceLab without a sensitivity envelope (E-value, Rosenbaum, partial-R2, Manski, or twin-network)."

- I-CI-6: "Backend through Capability. dowhy and pyro are imported only by dowhy-adapter and pyro-adapter respectively (ADR-0019)." The intelligence_preflight hook greps run scripts for direct `import dowhy` / `import pyro` (regex over the source, warn-only by default).

- I-CI-7: "Portfolio independence. IntelligenceLab reads a stamped PortfolioSnapshot for relevance filtering; it never writes portfolio state (ADR-0027)."

- I-CI-8: "Twin-network for variance reduction. When a counterfactual delta is reported, prefer shared-noise twin-network coupling over naive resampling (ADR-0019)."

- CLAUDE.md: "Per [[ADR-0020]] and [[ADR-0031]] the substrate is never duplicated in this repo; it is imported from Shared via path dependency during local development."

- CLAUDE.md coding standards (stated standards, not all machine-enforced): "Python 3.12, mypy --strict, pyrsistent.PMap for state, typing.Protocol for interfaces, dataclasses(frozen=True) for value types"; "Property tests with hypothesis, unit tests with pytest"; "Every public abstraction ships with at least one test"; "Side effects flow through the Capability environment ([[ADR-0013]])." Write code to the --strict bar by hand: the repo's mypy invocation does not actually apply it (see gotchas).

- Cross-lab discipline (docs/architecture/AGENTS.md + PEERS.md + .claude/registry/peers.yaml): "If the request belongs to a sibling lab, say so and stop." Sibling artefacts are referenced by content hash from their outputs/ tree, never reimplemented.

- tests/cross_repo/README.md: "Pin by commit hash. Never test against main of a sibling — pin in pinned_versions.yaml and bump explicitly." One test file per sibling; test the contract, not the implementation.

- docs/architecture/AGENTS.md output contract — every non-trivial change reports: What changed / Why / Files touched / Public API delta / Tests added-updated / Tests run (command + outcome) / Invariants checked / Risks remaining.

- settings.json deny list (prefix-matched, so treat it as intent rather than a sandbox): no `rm`, `rmdir`, `curl`, `wget`, `git reset --hard`, `git push --force`, `git push -f`, `git clean -f`, `git clean *-fd*`, `git filter-branch`. Constellation policy adds: no `--no-verify`, no force-push to main, one commit per repo per logical change.

- outputs/ artefacts follow the fixed per-run layout (config.yaml, manifest.json with BLAKE3 content addressing per ADR-0023, provenance.json lineage chain, data/, figures/, tables/, report.md) and are gitignored — never commit them. outputs/README.md: "Reports are regenerable from the manifest, never hand-edited."

- Determinism contract in packages/quant_intel/src/quant_intel/causal.py: "same column data + same column order (we sort covariate names) => identical audit_root.digest".

## Comandos de referencia

- uv sync --frozen || uv sync   # install (.github/workflows/test.yml, import-linter.yml)

- uv run pytest packages/ tests/ -x --tb=short -q -m "not slow" || echo "no tests yet"   # test (.github/workflows/test.yml — note the failure mask)

- uv run pytest packages/ -x --tb=short -q -m "not slow"   # fast tests as run by .claude/hooks/pre_commit_gate.py

- uv run ruff check .   # lint (.github/workflows/lint.yml)

- uv run ruff format --check .   # format check (.github/workflows/lint.yml)

- uv run mypy packages/ || echo "mypy: no packages yet"   # typecheck (.github/workflows/lint.yml — failure-masked, and NOT strict; see gotchas)

- uv run mypy packages/   # typecheck as run by .claude/hooks/pre_commit_gate.py (unmasked, but still runs with mypy DEFAULTS, not --strict; see gotchas)

- uv sync --all-packages && uv run lint-imports   # tier contract (.github/workflows/lint.yml)

- uv run lint-imports   # tier contract (.github/workflows/import-linter.yml — the only hard-failing gate besides ruff)

- python3 /Users/omarkhalil/GitHub/IntelligenceLab/.claude/tests/run_tests.py   # .claude scaffold smoke test (real script; wired into no CI job and no hook)

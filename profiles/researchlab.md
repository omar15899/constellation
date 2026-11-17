# ResearchLab

Raíz: `/Users/omarkhalil/GitHub/ResearchLab`. Las rutas de este perfil se interpretan desde esa raíz.
Las reglas de dominio se conservan; versiones y comandos se contrastan con los archivos actuales.
La coordinación y publicación usan el único `constellation.py`.

## Identidad

ResearchLab is the QuantOS Tier-2 experiment orchestrator, perimeter `quantos-info` (siblings NewsLab and IntelligenceLab). Its declared mission is to compose (Hypothesis, Dataset, FeatureSet, ModelClass) tuples, dispatch them to Tier-1 evaluator labs (BacktestLab, MonteCarloLab, SweepLab), register outcomes in the ExperimentRegistry, and emit Study/Report artefacts with a full BLAKE3 provenance chain. In practice it is the constellation's alpha-research lab: it hosts the R-program (ridge ranker, category interactions, HRP/ERC construction, XGBoost sleeve gating, risk overlays, promotion gate, deployable T212/UCITS target books) and six research sub-labs under research_algorithms/, four of which (learning_to_rank_cross_sectional, rmt_covariance_lab, volatility_surface_lab, discount_curve_lab) are self-contained uv projects and two of which (gas_storage_papers_lab, t212_broad_sleeve_factory) are bare src/tests trees with no project definition. It is mid-migration (the documented M1..M14 plan) from ungoverned-but-real alpha into a tier-disciplined lab, so a large part of the code is a tested component library that is deliberately NOT on the live run path — docs/component_status.md classifies each piece as LIVE_PIPELINE / OPT_IN_COMPONENT / COMPONENT_LIBRARY_ONLY / STALE_OR_DEAD.

## Fuentes del dominio

- CLAUDE.md

- README.md

- docs/README.md

- docs/architecture/2026-06-29_rprogram_audit_and_migration_plan.md

- docs/architecture.md

- docs/research_program.md

- docs/repo_boundaries.md

- docs/research_objects.md

- docs/validation_matrix.md

- docs/migration_plan.md

- docs/component_status.md

- .claude/registry/peers.yaml

- /Users/omarkhalil/OmarOS/05_Projects/QuantOS/Documentation/research_pipelines/index.md

- research_algorithms/learning_to_rank_cross_sectional/README.md

## Invariantes

- Vault first — WITH A CORRECTION THE AGENT MUST KNOW: CLAUDE.md says the doctrine, architecture, schema strategy and invariants 'are canonical in the OmarOS vault and **must be read before any code is written here**' and names ~/OmarOS/05_Projects/QuantOS/Labs/ResearchLab/Vision/{00_Doctrine,01_Architecture,05_Invariants}.md. THOSE THREE FILES DO NOT EXIST — the vault directory ~/OmarOS/05_Projects/QuantOS/Labs/ResearchLab/Vision/ is EMPTY, and so is its in-repo mirror docs/vault/lab_vision/. Do not loop trying to read them. The QuantOS-WIDE governance docs CLAUDE.md also requires DO all exist and are the real prerequisite: ~/OmarOS/05_Projects/QuantOS/AGENTS.md, Documentation/{ai_reading_order,ai_development_contract,meta_architecture,testing_and_hooks_contract}.md and Vision/{01_Architecture,03_AI_Operating_Doctrine}.md (mirrored in-repo under docs/vault/).

- Never duplicate the Tier-0 substrate: CLAUDE.md — 'Per [[ADR-0020]] and [[ADR-0031]] the substrate is **never duplicated** in this repo; it is imported from `Shared` via path dependency during local development.'

- Tier discipline: a Tier-2 component may import Tiers 0..1.5 and never Tiers 2..4. Stated concretely in research_algorithms/learning_to_rank_cross_sectional/pyproject.toml lines 30-32: 'Tier-correct: ResearchLab (T2) -> MarketDataLab quant_market (T1) + Shared quant_cache/quant_data/quant_substrate (T0). It NEVER imports StrategyOrchestrationLab (T4).' NOTE: this is a documented rule only — .importlinter enforces NOTHING in this repo (root_packages is empty).

- Coding standards inherited from QuantOS (CLAUDE.md): 'Python 3.12, `mypy --strict`, `pyrsistent.PMap` for state, `typing.Protocol` for interfaces, `dataclasses(frozen=True)` for value types', property tests with hypothesis, unit tests with pytest, and 'Every public abstraction ships with at least one test.' Side effects flow through the `Capability` environment ([[ADR-0013]]). Caveat: `strict = true` is configured in packages/*/pyproject.toml, not at the root, so the root `uv run mypy packages/` does not itself apply it.

- Deterministic regeneration is the central invariant (/Users/omarkhalil/OmarOS/05_Projects/QuantOS/Documentation/research_pipelines/index.md:7): 'Same (code_commit, dataset_version_hash, config_hash, seed_pack) -> bit-identical audit_dag_root and bit-identical report.md (modulo a documented timestamp non-determinism floor).'

- Five-link lineage chain mandatory (retained study doctrine): 'code_commit -> dataset_version_hash -> config_hash -> audit_dag_root -> artefact_hashes. Every link content-addressed via BLAKE3 over a canonical encoding (Cap'n Proto for binary, sorted-key UTF-8 JSON for text).'

- 'as_of_decision_time is part of the config. A config that does not pin it is invalid; refuse to scaffold or run.'. .claude/hooks/research_preflight.py does check for the string, but only WARNS unless RESEARCHLAB_ENFORCE_PREFLIGHT=1 (settings.json pins it to 0) — the absolute form of this rule is doctrine, not machine-enforced.

- 'Falsifiability is a precondition. A study cannot run against a hypothesis whose falsifiability statement does not name a metric, threshold, and horizon.'. Doctrine only — no hook or CI job checks it.

- Two-numbers rule (retained study doctrine): reports of kind single_strategy_backtest or cost_robustness 'must quote a Sharpe under 3x the calibrated cost in addition to the headline Sharpe.'

- 'outputs/ is gitignored. Study artefacts are runtime state, not source. Never commit outputs/<study>/<ts>/.' (Excluded by .gitignore and re-checked, advisory-only, by research_preflight.py.)

- Registry idempotence and append-only (retained study doctrine): 'A second registry write with the same run_id (= audit_dag_root) is a no-op. Records are append-only; never deleted.'

- 'AI-authored reports are not evidence on their own... a study published without ai_reviewed: true is opinion, not evidence.'

- Never claim an edge without the promotion gate. docs/component_status.md:17-19: 'None of the four asserts an alpha edge... **No verdict is recorded for any of them**, and none should be reported as a live edge.' Verdicts come from DSR / PBO-CSCV / reality-check / BH-FDR / bootstrap-CI at the honest family size.

- Code computes; `.claude` decides and records. docs/validation_matrix.md:130 — the gate math lives in LTR/src/evaluation/promotion.py, but 'the **policy** — thresholds, the canonical vocabulary, the honest family m, and the per-lever ledger — is owned by the `.claude` control plane in ~/GitHub/.claude/contracts/promotion_gate.md and ~/GitHub/.claude/registry/levers.yaml.'

- Do not re-run closed levers. docs/README.md:32 names eight DO-NOT-RE-RUN levers that 'stay closed': gdelt-news-tone, edgar-fundamentals, gdelt-cameo-events, t212-universe-zoo, long-only-equity-sleeves, ml-sleeve-zoo, regime-risk-allocation, multi-asset-diversifiers.

- Three CONFIRMED incumbents are the bar to beat (docs/README.md:31): broad-linear-ridge-h63 (broad floor), multisleeve-hrp-book (net Sharpe 1.45 OOS, edges corr -0.07), t212-score-weighting (Sharpe 1.30, deployable). Two items remain genuinely OPEN: headline-audit and short-leg-cost.

- Cross-lab discipline (.claude/registry/peers.yaml:41-44): 'If the request you receive belongs to a sibling lab, SAY SO and stop. Do not duplicate an abstraction that belongs there.' Sibling artefacts are referenced by content hash from their outputs/ tree.

- Git: atomic per repo, never bundle across repos; no `--no-verify`; no force-push to main. settings.json hard-denies Bash(rm *), Bash(rmdir *), Bash(curl *), Bash(wget *), Bash(git reset --hard*), Bash(git push --force*), Bash(git push -f*), Bash(git clean -f*), Bash(git clean *-fd*), Bash(git filter-branch*). Under defaultMode bypassPermissions this deny list is the only guardrail.

- Never commit real positions: .gitignore excludes `data/private/` and `*.account.json` under the comment 'Private T212 account snapshots / real holdings — NEVER commit real positions.'

## Retained domain procedure

Before scaffolding or regenerating a study, read its configuration, existing manifest and applicable research-pipeline chapter. Keep configuration, manifest, provenance, data, figures, tables and rendered report together under the declared run layout. Reports derive from recorded artifacts and never invent metrics.

Completion records data sources, model/code versions, assumptions, explicit conclusions, limitations and archival/publication disposition. Preserve reproducibility limits, the five-link lineage chain, honest falsifiability, append-only run registration and human-review status. Runtime outputs remain outside source publication.

The canonical directory is `/Users/omarkhalil/OmarOS/05_Projects/QuantOS/Documentation/research_pipelines/`: consult `studies.md`, `reports.md`, `provenance.md`, `reproducibility.md` and `figures_and_tables.md` as the task requires.

## Validation and publication

The commands below are references, not automatic authorization. Create, change or run tests only when Omar explicitly requests them. Record permitted checks and independent review through Constellation; any test-dependent gate without authorized evidence remains unmet. Domain hooks are additional controls, not proof that the outer Constellation commit ran the required checks. No startup, documentation or skill workflow publishes automatically.

## Reference commands

- uv run ruff check .   # .github/workflows/lint.yml, working-directory ResearchLab

- uv run ruff format --check .   # .github/workflows/lint.yml

- uv run mypy packages/ || echo "mypy: no packages yet"   # .github/workflows/lint.yml — NOTE: root pyproject.toml declares NO [tool.mypy]; strict=true lives only in packages/*/pyproject.toml

- uv sync --all-packages --frozen || uv sync --all-packages   # .github/workflows/test.yml, job `pytest`, install step

- uv run --all-packages pytest packages/ tests/ -x --tb=short -q -m "not slow"   # .github/workflows/test.yml, job `pytest`

- uv run --with import-linter lint-imports   # .github/workflows/import-linter.yml, guarded by `grep -qE '^[[:space:]]*root_packages[[:space:]]*=[[:space:]]*[^[:space:]#]' .importlinter` — root_packages is EMPTY, so this NEVER RUNS; the job emits ::notice:: and passes

- uv sync --extra full --extra engine   # .github/workflows/test.yml, job `research-algorithms`, cwd research_algorithms/learning_to_rank_cross_sectional

- uv run pytest -q   # .github/workflows/test.yml, cwd research_algorithms/learning_to_rank_cross_sectional

- learning_to_rank_cross_sectional/.venv/bin/python -m pytest _harness/tests -q   # .github/workflows/test.yml, cwd research_algorithms

- uv run mypy packages/   # .claude/hooks/pre_commit_gate.py, cwd=repo root, 120s timeout, blocking on failure only

- uv run pytest packages/ -x --tb=short -q -m "not slow"   # .claude/hooks/pre_commit_gate.py, 300s timeout, blocking on failure only

- PYTHONPATH=src .venv/bin/python -m pytest tests/ -q   # research_algorithms/learning_to_rank_cross_sectional/README.md:158

- PYTHONPATH=src .venv/bin/python -m ltr_cross_sectional.cli --quick   # LTR README:142, offline synthetic smoke run

- uv venv --python 3.12 .venv   # LTR README:137, bootstrap

- uv pip install --python .venv/bin/python -e .   # LTR README:138, bootstrap

- uv run pytest -q   # research_algorithms/rmt_covariance_lab/README.md:27 (full suite) and research_algorithms/volatility_surface_lab/README.md:94

- .venv/bin/python -m pytest   # research_algorithms/discount_curve_lab/README.md:18

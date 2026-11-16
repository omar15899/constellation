# NewsLab

Raíz: `/Users/omarkhalil/GitHub/NewsLab`. Las rutas de este perfil se interpretan desde esa raíz.
Las reglas de dominio se conservan; versiones y comandos se contrastan con los archivos actuales.
La coordinación y publicación usan el único `constellation.py`.

## Identidad

NewsLab is the QuantOS Tier-2 information lab in the `quantos-info` perimeter: it turns external textual/OSINT streams (GDELT via BigQuery and raw files, ACLED, FIRMS, ADS-B, USGS ComCat, GDACS, NWS) into typed, time-stamped, content-addressed NewsEvent and FeatureSet artefacts consumed by ResearchLab, BacktestLab and IntelligenceLab. Its governing premise, stated in README.md §"The vision: an observation model, not a signal generator", is Y_t = h(Z_t) + eps_t — media is a filtered, lagged, duplicated projection of the latent world state — and the lab produces the causal estimator Z_hat_t = phi(Y_{<=t}, M_{<=t}), explicitly NOT a trading signal. Per ADR-LOCAL-0001 it holds boundary contracts only (Protocols and frozen dataclasses) for pricing, backtesting, risk and execution; those engines live in sibling labs and are consumed by content hash, and the `.importlinter` tier contract makes importing them a release blocker. The single shipped package is `quant_news` (the only workspace member, under packages/), at pipeline_version 0.2.0 with a deterministic ontology tagger and LLM tagging disabled.

## Fuentes del dominio

- CLAUDE.md

- docs/architecture/AGENTS.md

- README.md

- docs/adr/ADR-LOCAL-0001-osint-platform-boundary-not-engines.md

- docs/architecture.md

- .importlinter

- schemas/manifest.yaml

- docs/architecture/PEERS.md

- .claude/registry/peers.yaml

- docs/architecture/ai_development_contract.md

- docs/architecture/testing_and_hooks_contract.md

- docs/vault/documentation/ai_reading_order.md

- docs/vault/documentation/constellation_map.md

- docs/safety_and_governance.md

- docs/adr/ADR-LOCAL-0002-fusion-report-destination-and-independence-weighting.md

- docs/adr/ADR-LOCAL-0003-llm-intelligence-report.md

- docs/adr/ADR-LOCAL-0004-universe-aware-intelligence-report.md

- .claude/skills/news-causal-admissibility/SKILL.md

## Invariantes

- Tier 2 discipline, machine-enforced. .importlinter contract `no-higher-or-sibling-tier-imports` forbids quant_news from importing quant_core, quant_backtest, quant_data, quant_market, quant_domain, quant_trade, quant_mc_core, quant_research_core, quant_research_runner, quant_research_report, quant_intel_features, quant_intel_models, quant_intel_news, quant_intel_signals, quant_portfolio_core, quant_risk_core, quant_exec_core. quant_market is forbidden specifically because NewsLab consumes a LOCAL projection (config_data/trading_universe.yaml), never the sibling package. Note the contract is only advisory in CI (`lint-imports || echo`), so run `uv run lint-imports` yourself.

- Stage independence. The .importlinter `stage-independence` contract makes quant_news.adapters, quant_news.events and quant_news.features mutually independent; only the composition root quant_news.build may wire them.

- No engines in this repo. ADR-LOCAL-0001: packages/quant_news/src/quant_news/{pricing,risk,strategies,backtesting,execution}/ and the market-data data_sources are boundary surfaces ONLY — the engine lives in the sibling lab and is consumed by content hash. Do not implement an engine here.

- The substrate is never duplicated. CLAUDE.md: "Per [[ADR-0020]] and [[ADR-0031]] the substrate is never duplicated in this repo; it is imported from Shared via path dependency during local development."

- The vault is canonical, this repo is not. CLAUDE.md: "The doctrine, architecture, schema strategy, and invariants are canonical in the OmarOS vault and must be read before any code is written here." docs/vault/README.md: "The vault is canonical. This mirror is a cache. If a file here disagrees with the source under ~/OmarOS/, the source wins."

- I-1 causal admissibility typed (news-causal-admissibility SKILL.md, verbatim): "Every emitted FeatureSet row carries a KnownAt[T] wrapper. The type system rejects the construction of a row whose decision_admissible_at precedes any contributing event's decision_admissible_at."

- I-2 content-hash dedup (SKILL.md, verbatim): "Two RawArticles with identical normalised body collapse to one Event. Hash is BLAKE3 (ADR-0023). The Event.sources list cites every contributing raw row. Hash collisions across distinct bodies are fatal."

- I-3 verifier soundness (SKILL.md, verbatim): "A tag accepted by the verifier has at least one supporting span in the event body, locatable within bounded edit distance delta. Accepting with no locatable span is a hard test failure."

- I-8 tagging non-contamination (SKILL.md, verbatim): "The tagger training-set content hashes are disjoint from any consumer's live-window contributing-event content hashes. Overlap is a release-blocking finding."

- Versions are pinned or the run is refused. SKILL.md: "The skill refuses to run a tagger-or-feature pipeline whose tagger_version is unpinned or whose ontology version is unpinned. The news_preflight hook is the runtime mirror of this clause." Caveat: the hook only blocks when NEWSLAB_ENFORCE_PREFLIGHT=1, which settings.json sets to 0.

- Test for every invariant touched. SKILL.md: "A change that touches I-1, I-2, I-3, or I-8 ships with the corresponding test under tests/invariants/test_I_<n>.py. Untested touch is rejected." (Currently only test_I_1, test_I_2 and test_I_5 exist.)

- Capability boundary. SKILL.md: "Adapters never write to the store directly. Tagger / verifier / feature-builder never bypass the Capability layer." (ADR-0013.) Every LLM call is gated behind require(capability, CAP_LLM_CLASSIFY).

- Two-pass discipline for new components. SKILL.md: "The skill first proposes the component outline + invariant impact analysis; only after confirmation does it write code."

- Coding standards (CLAUDE.md, aspirational where unenforced): Python 3.12, mypy --strict, typing.Protocol for interfaces, frozen dataclasses for value types, hypothesis property tests, pytest, "Every public abstraction ships with at least one test." CLAUDE.md also names pyrsistent.PMap for state, but pyrsistent is not a dependency and appears nowhere in the codebase — do not add it on the strength of that line.

- Output contract for every non-trivial change (docs/architecture/AGENTS.md, per ai_development_contract.md §3): What changed / Why / Files touched / Public API delta / Tests added-updated / Tests run (command + outcome) / Invariants checked / Risks remaining.

- Cross-lab stop rule (.claude/registry/peers.yaml, verbatim): "If the request you receive belongs to a sibling lab, SAY SO and stop. Do not duplicate an abstraction that belongs there." docs/architecture/AGENTS.md restates it: "If the request belongs to a sibling lab, say so and stop."

## Comandos de referencia

- uv sync --frozen || uv sync

- uv sync --all-packages

- uv sync --all-packages --extra analysis

- uv sync --all-packages --extra dashboard

- uv sync --all-packages --extra llm

- uv run ruff check .

- uv run ruff format --check .

- uv run mypy packages/

- uv run pytest packages/ tests/ -x --tb=short -q -m "not slow"

- uv run lint-imports

- uv run pytest packages/ -x --tb=short -q -m "not slow"

- uv run pytest tests/invariants -v

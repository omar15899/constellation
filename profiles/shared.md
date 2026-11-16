# Shared

Raíz: `/Users/omarkhalil/GitHub/Shared`. Las rutas de este perfil se interpretan desde esa raíz.
Las reglas de dominio se conservan; versiones y comandos se contrastan con los archivos actuales.
La coordinación y publicación usan el único `constellation.py`.

## Identidad

Shared is QuantOS Tier 0 — the substrate at the bottom of the QuantOS constellation, perimeter `quantos-core`, remote git@github.com:omar15899/QuantOS_Shared.git. It is explicitly not a utility library: CLAUDE.md defines it as "the single causal / deterministic / auditable runtime kernel" that BacktestLab, MonteCarloLab and PricingLab "share by construction", and every other lab imports it downward-only. It is a uv workspace of five packages under packages/: quant_substrate (clocks.py, known_at.py, hashing.py, audit.py, capability.py, root.py — the four-clock model, KnownAt[T], BLAKE3 artefact roots, audit DAG, capability tokens), quant_data (market.py value types and sources.py boundary Protocols), quant_cache (async TTL + single-flight + stale-while-revalidate caching core with pluggable durable backends), and grid_expansion / grid_expansion_simple (an abstract sparse-to-dense pushforward calculus, the second a deliberately duck-typed variant). Its governing rule is ADR-0020: a substrate component is never duplicated or vendored in a lab repo — a lab that needs a missing primitive opens an ADR here instead.

## Fuentes del dominio

- CLAUDE.md

- docs/HANDOFF_PROMPT.md

- docs/architecture/AGENTS.md

- docs/architecture/PEERS.md

- docs/architecture/lab_architecture.md

- .claude/registry/peers.yaml

- .claude/skills/shared-substrate-doctrine/SKILL.md

- docs/vault/AGENTS.md

- docs/vault/documentation/ai_reading_order.md

- docs/vault/documentation/ai_development_contract.md

- docs/vault/documentation/testing_and_hooks_contract.md

- docs/vault/decisions/ADR-0020-shared-substrate-not-duplicated.md

- docs/vault/decisions/ADR-0031-substrate-extraction.md

- docs/vault/vision/01_Architecture.md

- docs/vault/lab_vision/00_Substrate.md

## Invariantes

- ADR-0020, single-source. Verbatim from CLAUDE.md: "components in Shared are never duplicated in a lab repo. A lab that needs a primitive that does not yet exist in Shared opens an ADR and proposes the addition; the lab does not vendor its own copy." The skill escalates it: "Forking a schema in a lab is a release blocker." Doctrinal, not mechanically enforced.

- Tier 0 isolation, no upward import. Stated in the SKILL's contract_invariants (NOT in CLAUDE.md): "quant_core imports nothing from QuantOS. quant_data and quant_observability import only from quant_core. No upward import." MECHANICAL COVERAGE IS PARTIAL: the only .importlinter contract is `quant-cache-is-tier0-infra` (quant_cache must not import quant_data or grid_expansion). /audit-imports rule 4 declares any import of a downstream lab from packages/ "a release blocker", but that check is a grep in a markdown command file, not CI.

- Typing. Verbatim from CLAUDE.md: "Python 3.12, `mypy --strict`. No `Any`, no `cast`, no `# type: ignore` without an inline explanation." Every package pyproject sets strict = true; the root sets warn_return_any, explicit_package_bases and namespace_packages. Note the repo venv actually runs Python 3.13.3.

- State discipline. Verbatim from CLAUDE.md: "State is `pyrsistent.PMap`; never a mutable dict for accumulated state" (ADR-0011); "`typing.Protocol` for interfaces; `dataclasses(frozen=True)` for value types." ASPIRATIONAL — pyrsistent is not installed and not declared in any pyproject.

- Effects. Verbatim from CLAUDE.md: "Side effects flow through the `Capability` environment (ADR-0013)." Skill: "No effect without a token. No token without a registry entry."

- Four-clock model. From the SKILL's contract_invariants (not CLAUDE.md): "Every datum carries (T_event, T_available, T_logical) and a wall-clock origin used only for telemetry. Decision paths take time from CausalClock, never from time.time() or datetime.now()." The skill's anti-pattern list repeats it.

- KnownAt[T] monotonicity. From the SKILL: "A function consuming KnownAt[T] cannot produce KnownAt[T'] with T' < T. Information does not travel backwards."

- Run identity. From the SKILL: "BLAKE3 audit DAG. Run identity is the root hash. Replays match iff root hashes match. No alternative notion of run identity is admitted." Paired with: "Schema, RNG, or canonicalisation changes must come with a replay-equivalence argument on the regression corpus."

- Dependencies. CLAUDE.md: substrate dependencies are "minimal by design" and "Any addition is an ADR-recorded architectural decision." Skill: "Stdlib-first. New dependencies in packages/*/pyproject.toml require an ADR proposed first", with pandas/polars/scipy/sklearn/pytorch/tensorflow imports in packages/quant_* named as review-rejected anti-patterns.

- Tests. Verbatim from CLAUDE.md: "Property tests (`hypothesis`) for every kernel primitive. Every named invariant in the lab Vision documents has at least one test in this repo." Skill anti-pattern: "A public symbol added to packages/quant_*/src/ without a paired test."

- ADR-first workflow. From the SKILL: "New substrate components follow /new-substrate-component: intake → architect → ADR (proposed) → tests → implementation → validate → ADR (accepted)."

- Read first, write second. From the SKILL: "Every substrate change reads Vision/00_Substrate.md, the relevant ADRs, and the affected sub-package before any line of code is written."

- /validate-substrate gate. The command file states: "No commit, no run touching `packages/quant_*` should be considered green until this passes… Any failed step blocks downstream work. Do not commit until clean." TREAT WITH CARE: as written the command targets quant_core/quant_observability, which do not exist, so it CANNOT pass. The honest operational form of this invariant is the per-package equivalents listed under commands.

- Cross-lab discipline, verbatim from .claude/registry/peers.yaml: "If the request you receive belongs to a sibling lab, SAY SO and stop. Do not duplicate an abstraction that belongs there." Sibling artefacts are referenced by content hash from that lab's outputs/ tree; orchestrator-to-orchestrator dispatch is declared "planned, not yet implemented".

- Hook contract, from _common.py's own docstring: "Every hook must import this module. Direct sys.exit(0) without logging is forbidden (invariant I09). Use hook_log() for all structured output."

- Voice, from the SKILL: English-first in code, comments and ADRs; terse doctrinal prose; "No emojis in code, ADRs, or commit messages. None. Ever."; no AI-attribution footer in any commit message; never bundle two unrelated logical units in one commit.

## Comandos de referencia

- uv sync --frozen || uv sync    # install (test.yml and import-linter.yml; lint.yml has NO install step)

- uv run ruff check .    # .github/workflows/lint.yml — unmasked

- uv run ruff format --check .    # .github/workflows/lint.yml — unmasked

- uv run mypy packages/ || echo "mypy: no packages yet"    # .github/workflows/lint.yml — masked

- uv run pytest packages/ tests/ -x --tb=short -q -m "not slow" || echo "no tests yet"    # .github/workflows/test.yml — masked

- uv run lint-imports || echo "no contracts yet"    # .github/workflows/import-linter.yml — masked

- uv run mypy packages/    # .claude/hooks/pre_commit_gate.py, run with cwd=repo root, only when packages/ is staged — BLOCKING, unmasked, currently FAILS

- uv run pytest packages/ -x --tb=short -q -m "not slow"    # .claude/hooks/pre_commit_gate.py — BLOCKING, unmasked

- uv run lint-imports    # .claude/commands/audit-imports.md and validate-substrate.md — this one works: 1 kept, 0 broken

- uv run mypy --strict packages/quant_core packages/quant_data packages/quant_observability    # .claude/commands/validate-substrate.md — STALE, quant_core/quant_observability do not exist

- uv run pytest -q packages/quant_core packages/quant_data packages/quant_observability    # .claude/commands/validate-substrate.md — STALE, same reason

- uv run pytest -q -m replay_equivalence packages/quant_core    # .claude/commands/validate-substrate.md step 4 — STALE path; the marker itself is harmless (unknown -m expressions deselect, they do not error)

- cd packages/quant_substrate && uv run mypy -p quant_substrate    # VERIFIED WORKING substitute: Success, 7 source files

- cd packages/quant_cache && uv run mypy src    # VERIFIED WORKING: Success, 15 source files (only because quant_cache/pyproject.toml sets mypy_path = "src:tests")

- uv run pytest packages/quant_substrate packages/quant_data packages/quant_cache -q    # VERIFIED WORKING: 165 passed

- uv run pytest packages/grid_expansion -q    # VERIFIED WORKING: 15 passed

- python3 .claude/tests/run_tests.py    # .claude/ scaffold smoke test

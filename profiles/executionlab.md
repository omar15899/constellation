# ExecutionLab

Raíz: `/Users/omarkhalil/GitHub/ExecutionLab`. Las rutas de este perfil se interpretan desde esa raíz.
Las reglas de dominio se conservan; versiones y comandos se contrastan con los archivos actuales.
La coordinación y publicación usan el único `constellation.py`.

## Identidad

ExecutionLab is the QuantOS Tier-3 lab that owns the OrderProposal -> Order -> Fill lifecycle: the pre-trade gate, the broker boundary, the append-only ledger, and the PostTradeReview writer. Its perimeter is `quantos-prod` (with RiskLab); ~/GitHub/.claude/registry/repos.yaml notes "The only repo that touches real money. Highest blast radius." Concretely it is a uv workspace of four packages — quant_exec_core (OrderProposal / Order / Fill / PreTradeCheck frozen value types), quant_exec_pretrade (a runner that refuses to mint an Order unless every gate passes), quant_exec_broker (PaperBroker only in v0.1; no IBKR code exists yet), quant_exec_ledger (append-only SQLite ledger) — all sitting on the Tier-0 substrate `quant-substrate`, imported by relative path from the sibling ~/GitHub/Shared checkout and never duplicated. Remote is git@github.com:omar15899/QuantOS_ExecutionLab.git (origin/main). The repo's own docs still describe it as a stub, which is no longer true; doctrine and Vision remain canonical in the OmarOS vault at ~/OmarOS/05_Projects/QuantOS/Labs/ExecutionLab/Vision/, mirrored read-only into docs/vault/.

## Fuentes del dominio

- CLAUDE.md

- docs/architecture/AGENTS.md

- docs/vault/lab_vision/00_Doctrine.md

- .importlinter

- docs/architecture/lab_architecture.md

- docs/architecture/PEERS.md

- .claude/registry/peers.yaml

- docs/architecture/ai_development_contract.md

- docs/architecture/testing_and_hooks_contract.md

- docs/vault/documentation/ai_reading_order.md

- tests/cross_repo/README.md

- outputs/README.md

## Invariantes

- Tier discipline, machine-enforced and currently PASSING. .importlinter contract `no-higher-or-sibling-tier-imports` (type = forbidden, include_external_packages = True): the four quant_exec_* packages must never import quant_backtest, quant_domain, quant_trade, quant_mc_core/paths/pricer/aad, quant_sweep, quant_pricing, quant_market, quant_news, quant_research*, quant_insights, quant_intel*, quant_portfolio*, quant_risk* or strategy_orchestration_lab. Its comment: "ExecutionLab is Tier 3: it may import the Tier-0 substrate (quant_substrate, quant_data, quant_cache) only ... It must never import a sibling Tier-3 lab (RiskLab) or the Tier-4 orchestration layer." Verified by running `uv run lint-imports`: "Analyzed 17 files, 36 dependencies. ... Contracts: 1 kept, 0 broken."

- Substrate is never duplicated. CLAUDE.md, verbatim: "Per [[ADR-0020]] and [[ADR-0031]] the substrate is **never duplicated** in this repo; it is imported from `Shared` via path dependency during local development." (Note the naming drift: CLAUDE.md names the substrate `quant_core, quant_data, quant_observability`; the actual path dependency is `quant-substrate`.)

- I1 IAR triple separation (execution doctrine): Intent=OrderProposal, Action=Order, Realization=Fill are never collapsed. "A function that builds an `Order` from raw inputs without going through `OrderProposal` is a violation. A function that produces a `Fill` not tied to a parent `Order` row is a violation." Doctrinal — no automated check exists for this.

- I2 append-only ledger (ADR-0002): no in-place mutation of ledger rows; corrections are new rows, status transitions are new rows. Honoured in the shipped code by construction — sqlite_ledger.py contains only `INSERT OR IGNORE`, is digest-keyed, and resolves current status via `MAX(rowid) GROUP BY order_id`. NOT enforced at the DB privilege level as the inherited design claims (that text describes an unbuilt Postgres schema).

- I3 idempotency key required on every OrderProposal; "A submission without an idempotency_key is rejected at the gateway, before the broker is contacted." Checked at hook level as P3, warn-only today.

- I4 RiskLab-certificate gate: no broker call without a `passed` RiskLab certificate for the cited proposal. Doctrinal — the cited enforcement point `IBKRExecutionGateway.submit_approved_order` does not exist in the tree; the only live check is execution_preflight.py P2, which is warn-only and reads var/proposals/<id>.json (a path that does not exist).

- I5 never auto-promote to live. .claude/commands/mode.md, verified verbatim: `dry-run -> live` requires `--human-override=<id>` present and resolvable, typed passphrase confirmation, clean reconciliation in the last 30 minutes, fresh market data, all kill switches green, and a daily re-confirmation gesture if a previous live session ran today. Downgrades are immediate; upgrades are explicit and logged; "Auto-upgrade to a higher mode is **forbidden** and refused." The execution doctrine adds: the system auto-reverts to dry-run on restart, exception, or health-check failure (ADR-0025).

- I6 single execution surface (E1); I7 capability split, read by default; I8 human override required for live. All three are doctrine in the domain contract and reference an unbuilt IBKR gateway; I6's stated enforcement file `tests/contract/test_no_orphan_broker_calls.py` does not exist. Side effects flowing through the `Capability` environment (ADR-0013) IS real in shipped code — quant_exec_pretrade's runner gates on a Capability and raises CapabilityError.

- Coding standards, from CLAUDE.md verbatim: "Python 3.12, `mypy --strict`, `pyrsistent.PMap` for state, `typing.Protocol` for interfaces, `dataclasses(frozen=True)` for value types. Property tests with `hypothesis`, unit tests with `pytest`. Every public abstraction ships with at least one test. Side effects flow through the `Capability` environment ([[ADR-0013]])." Of these, frozen dataclasses, mypy strict config and pytest are real today; pyrsistent, Protocol and hypothesis are declared but unused (see gotchas).

- Cross-lab discipline (docs/architecture/AGENTS.md, verbatim): "If the request belongs to a sibling lab, say so and stop."

- Consume sibling artefacts by hash, never re-derive. Source is docs/architecture/PEERS.md §2 (NOT AGENTS.md as previously attributed), verbatim: "Sibling artefacts (BacktestRun, PricingRun, FeatureSet, CounterfactualEstimate, Allocation, RiskCert, Order, Fill) are typed and content-addressed. When you need one, reference it by hash from its `outputs/` tree — never by recomputing it."

- Cross-repo contract tests pin by commit hash, never against a sibling's `main` (tests/cross_repo/README.md: "Pin by commit hash. Never test against `main` of a sibling — pin in `pinned_versions.yaml` and bump explicitly."). Declared only — the Shared pin is the literal string `HEAD`.

- Every non-trivial change reports in the fixed output shape from docs/architecture/AGENTS.md: What changed / Why / Files touched / Public API delta / Tests added-updated / Tests run / Invariants checked / Risks remaining.

- outputs/ is content-addressed and never committed (outputs/README.md rule 5: "Nothing under `outputs/` is committed to git"; rule 2: run_id is the BLAKE3 root of `(config.yaml ⊕ all input hashes ⊕ code revision)` per ADR-0023; rule 4: reports are regenerable from the manifest, never hand-edited).

- Destructive git and network commands are denied in Claude's .claude/settings.json — ten entries under `defaultMode: bypassPermissions` with `allow: ["Bash(*)"]`: `rm *`, `rmdir *`, `curl *`, `wget *`, `git reset --hard*`, `git push --force*`, `git push -f*`, `git clean -f*`, `git clean *-fd*`, `git filter-branch*`. These are Claude permissions, not a generated Codex configuration; Codex follows [AGENTS.md](../AGENTS.md) and its effective permissions.

- docs/vault/ is a cache, not a source. docs/vault/README.md: "**The vault is canonical.** This mirror is a cache. If a file here disagrees with the source under `~/OmarOS/`, the source wins." Refresh only via `~/GitHub/.scripts/mirror_quantos_vault.sh` or /refresh-docs; never hand-edit.

## Retained domain procedure

Derive a proposal's deterministic idempotency key from `(strategy_id, decision_record_id, instrument_id, side, quantity, bar_timestamp)`. Preserve the relationship between proposal identity, broker client identity and grouped fills. A missing key, missing passing risk certificate or absent live authorization must not become implicit permission to contact a broker. Distinguish the specified IBKR/Postgres design from the implemented paper-broker/SQLite behavior.

Consult `docs/vault/decisions/ADR-0025-four-trading-modes.md` and the canonical `/Users/omarkhalil/OmarOS/05_Projects/QuantOS/Vision/Policies/EXECUTION_POLICY.md` for mode transitions.

## Validation and publication

The commands below are references, not automatic authorization. Create, change or run tests only when Omar explicitly requests them. Record permitted checks and independent review through Constellation; any test-dependent gate without authorized evidence remains unmet. Domain hooks are additional controls, not proof that the outer Constellation commit ran the required checks. No startup, documentation or skill workflow publishes automatically.

## Reference commands

- uv sync --all-packages --frozen || uv sync --all-packages   # .github/workflows/import-linter.yml

- uv sync --frozen || uv sync   # .github/workflows/test.yml

- uv run pytest packages/ tests/ -x --tb=short -q -m "not slow"   # .github/workflows/test.yml (CI appends `|| echo "no tests yet"`)

- uv run pytest packages/ -x --tb=short -q -m "not slow"   # .claude/hooks/pre_commit_gate.py::_run_tests (subprocess arg list, verified)

- uv run ruff check .   # .github/workflows/lint.yml

- uv run ruff format --check .   # .github/workflows/lint.yml

- uv run mypy packages/   # .github/workflows/lint.yml (CI appends `|| echo "mypy: no packages yet"`) and .claude/hooks/pre_commit_gate.py::_run_mypy

- uv run lint-imports   # .github/workflows/import-linter.yml

- python3 /Users/omarkhalil/GitHub/ExecutionLab/.claude/tests/run_tests.py   # .claude scaffold smoke test (passes)

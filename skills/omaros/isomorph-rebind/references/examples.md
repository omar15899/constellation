# Isomorph Rebind — Worked Example

One end-to-end example. Input: a pricing-engine scaffold (the kind `isomorph-synth` emits) plus a minimal private-side description from the user. Output: the 8-section reintegration map. Both are synthetic.

---

## Input

### The scaffold

A 6-section isomorph-synth artefact describing a pricing-engine scaffold with: `Module_Ingestion`, `Module_Calibration`, `Module_Valuation`, `Module_Reporting`; an `ObservationIngestorComponent`, a `ClosedFormValuationComponent`, a `SimulationValuationComponent`, a `ReportRendererComponent`, an `EventPublisherComponent`; three external integrations (`MarketDataVendor`, `OperationalStore`, `DownstreamPnL topic`); three datasets (`RawObservations`, `CalibratedParameters`, `DerivedValuations`); six adaptation points labelled USER-INTEGRATION REQUIRED or ADAPTATION POINT. Stack is Python 3.11 + `uv` + `pytest`.

### What the user said about their private system

> "We run on Python 3.11, use `poetry` not `uv`, have an internal market-data client called [redacted] that returns iterator-of-records, store results in Postgres, and publish downstream via RabbitMQ. No shadow-deploy infrastructure. Credentials are all Vault-backed."

That's it. Everything else about the private system is unknown.

---

## Output (the reintegration map — condensed)

```markdown
# 1. Reintegration assumptions

## Known from the generic scaffold
- Four modules (ingestion / calibration / valuation / reporting) plus infrastructure adapters.
- Six adaptation markers: `USER-INTEGRATION REQUIRED` × 3 (MarketData, OperationalStore, EventPublisher), `ADAPTATION POINT` × 3 (closed-form valuation, simulation valuation, calibration).
- Interface signatures are typed via Python `Protocol`; tests exist for every component.
- Stack is Python 3.11 + `uv` + `pytest`; lockfile is `uv.lock`.

## Known about the private system (as stated by the user)
- Python 3.11.
- Package manager is `poetry`, not `uv`.
- Internal market-data client returns an iterator of records (shape unspecified).
- Storage is PostgreSQL.
- Downstream messaging is RabbitMQ.
- No shadow-deploy / dark-launch infrastructure.
- Credentials are Vault-backed.

## Unknown about the private system
- Name / path of the private market-data client class.
- Record type yielded by the iterator (dict? dataclass? pydantic model?).
- Postgres schema for calibration results and derived valuations.
- RabbitMQ topology (exchange / routing key / ack mode).
- Presence or absence of a dependency-injection container.
- Existing test framework and conventions (pytest assumed, but not confirmed).
- Observability sink(s).
- Deployment cadence and CI gating.

## Assumptions made to proceed
- The private codebase can accept new files under a `/adapters/` directory (or equivalent seam location chosen by the user).
- Poetry can resolve the scaffold's dependency list; where the scaffold's pins conflict with the private lockfile, the private pin wins and the scaffold is loosened.
- The private market-data client's iterator can be materialised to a DataFrame in bounded memory for the observation universes in use.

# 2. System correspondence map

| Generic artefact | Likely private counterpart category | Correspondence type | Confidence | Integration mode | Notes |
|------------------|--------------------------------------|---------------------|------------|-------------------|-------|
| `Module_Ingestion` | ingestion subsystem | exact structural analogue | high | adapter-mediated | One private adapter maps the internal client to `MarketDataInterface`. |
| `Module_Calibration` | calibration subsystem | exact structural analogue | high | adapter-mediated | Private calibration routine binds to `ADAPTATION POINT` on `calibrate_parameters`. |
| `Module_Valuation` | valuation subsystem | exact structural analogue | high | adapter-mediated | Two ADAPTATION POINTs (closed-form, simulation); each body swappable. |
| `Module_Reporting` | reporting / publishing subsystem | interface-level analogue | medium | adapter-mediated | Private system may have a different report format; scaffold's interface is the contract. |
| `MarketDataInterface` + `MarketDataAdapter` | internal market-data client wrapper | integration wrapper | high | adapter-mediated | Maps internal-client iterator → DataFrame conforming to `RawObservations`. |
| `OperationalStoreInterface` + adapter | Postgres DAO layer | infrastructure placeholder | high | adapter-mediated | Scaffold stub was SQLite; bind to Postgres via `psycopg` / `SQLAlchemy` (user choice). |
| `EventPublisherInterface` + adapter | RabbitMQ publisher | infrastructure placeholder | high | adapter-mediated | Scaffold stub was aio-pika; real binding may keep aio-pika or swap to `pika`. |
| `Dataset_RawObservations` (schema) | internal observation DTO | schema placeholder | medium | schema rebinding | Column roles match; names and types need alignment. |
| `Dataset_CalibratedParameters` (schema) | internal calibration-params table | schema placeholder | medium | schema rebinding | Postgres schema almost certainly exists; roles must match. |
| `Dataset_DerivedValuations` (schema) | internal valuations table | schema placeholder | medium | schema rebinding | Same remark. |
| `pyproject.toml` (uv) | private `pyproject.toml` (poetry) | infrastructure placeholder | high | partial manual transplantation | Merge dependency lists; loosen pins where private pins exist. |
| Settings / config | Vault-backed settings provider | infrastructure placeholder | medium | adapter-mediated | Scaffold reads `.env`; the private path is Vault → env var → settings object. |
| Tests / fixtures | private test conventions | test harness | low | partial manual transplantation | Scaffold ships pytest; if private system uses a different runner, tests are references only. Alternative: keep pytest tests as a contract suite even if the private project uses another framework at integration level. |

# 3. Adaptation points

## AP-1 — MarketData adapter

- **Tag**: `USER-INTEGRATION REQUIRED` + `INFRASTRUCTURE SUBSTITUTION REQUIRED`
- **Location (generic scaffold)**: `src/pricing_engine/infrastructure/adapters/market_data_adapter.py:MarketDataAdapter.fetch_observations`
- **What must change**: replace the fixture-loading stub body with a call to the private market-data client; materialise the iterator of records into a pandas DataFrame conforming to `MarketObservation`.
- **Why**: the private market-data client is the only authoritative source for live observations; the stub exists only so the scaffold boots without network.
- **What must be bound**: a provider satisfying `fetch_observations(universe: list[InstrumentHandle]) -> DataFrame[N, 5]` with columns conforming to `MarketObservation`; tolerant to transient failures; no cross-call caching.
- **Mandatory / optional**: mandatory.
- **Invariants**: interface signature, DataFrame column set, transient-failure tolerance.

## AP-2 — OperationalStore adapter

- **Tag**: `USER-INTEGRATION REQUIRED` + `INFRASTRUCTURE SUBSTITUTION REQUIRED`
- **Location (generic scaffold)**: `src/pricing_engine/infrastructure/adapters/operational_store_adapter.py:OperationalStoreAdapter`
- **What must change**: replace the SQLite-based stub with a Postgres-backed implementation using the private DB connection path.
- **Why**: production persistence for `Dataset_CalibratedParameters` and `Dataset_DerivedValuations`; the stub is dev-time only.
- **What must be bound**: a provider satisfying `read_calibrated(...)`, `write_calibrated(...)`, `write_valuations(...)`; schema conforming to the scaffold's dataclasses; Vault-sourced credentials.
- **Mandatory / optional**: mandatory.
- **Invariants**: transactional semantics (write-then-publish must be atomic or compensating); append-only on `valuations`.

## AP-3 — EventPublisher adapter (RabbitMQ)

- **Tag**: `USER-INTEGRATION REQUIRED` + `INFRASTRUCTURE SUBSTITUTION REQUIRED`
- **Location**: `src/pricing_engine/infrastructure/adapters/event_publisher_adapter.py:EventPublisherAdapter.publish`
- **What must change**: replace the aio-pika stub with the private RabbitMQ publisher configuration (exchange, routing key, ack mode as defined by the private system).
- **What must be bound**: a publisher satisfying `publish(valuations: DataFrame) -> None` with declared ack semantics; mTLS if the private system uses it, plain TCP otherwise.
- **Mandatory / optional**: mandatory.
- **Invariants**: per-record publish ordering (if the consumer depends on order); retry semantics on transient broker failures; no partial batches silently dropped.

## AP-4 — Closed-form valuation body

- **Tag**: `ADAPTATION POINT`
- **Location**: `src/pricing_engine/domain/valuation.py:compute_closed_form_valuation`
- **What must change**: replace the vanilla Black–Scholes body with the private valuation routine.
- **Why**: the scaffold's body is generic; the private firm has its own parametrisation.
- **What must be bound**: a routine satisfying the same signature; determinism under fixed inputs; output shape unchanged.
- **Mandatory / optional**: mandatory (marked as non-preserved in the scaffold's Section 8).
- **Invariants**: signature, output shape, determinism.

## AP-5 — Simulation valuation body

- **Tag**: `ADAPTATION POINT`
- **Location**: `src/pricing_engine/domain/valuation.py:compute_simulation_valuation`
- **What must change**: replace the generic GBM + vanilla-payoff body with the private simulation routine; preserve seed-based determinism.
- **Mandatory / optional**: mandatory.
- **Invariants**: signature, output shape, seed determinism, `standard_error` field semantics.

## AP-6 — Calibration body

- **Tag**: `ADAPTATION POINT`
- **Location**: `src/pricing_engine/calibration.py:calibrate_parameters`
- **What must change**: replace the generic least-squares body with the private calibration routine.
- **Mandatory / optional**: mandatory.
- **Invariants**: signature, `col_residual_norm` monotone-decreasing across iterations.

# 4. Required private bindings

## PB-1 — Market-data provider (implements AP-1)

- **Target contract**: `MarketDataInterface` (see scaffold `src/pricing_engine/interfaces/market_data_interface.py`).
- **Required methods**:
  - `fetch_observations(universe: list[InstrumentHandle]) -> DataFrame`
- **Invariants**:
  - Returned frame has columns `[col_timestamp, col_identifier, col_bid, col_ask, col_volume_bucket]` with the types defined in `MarketObservation`.
  - Adapter tolerates transient upstream 5xx without propagating them; caller only sees durable failures.
  - No cross-call caching — each call reads fresh from upstream.
- **Failure modes if bound incorrectly**:
  - Wrong column set → pydantic validation error at construction (easy, loud).
  - Propagated transient failures → batch failures cascade downstream (hard, misattributed).
  - Caching that hides upstream staleness → silent calibration drift (invisible-until-production).

## PB-2 — Operational store (implements AP-2)

- **Target contract**: `OperationalStoreInterface`.
- **Required methods**:
  - `write_calibration(record: CalibratedParameterSet) -> None`
  - `read_latest_calibration(model_class: ModelClass) -> CalibratedParameterSet | None`
  - `write_valuations(frame: DataFrame) -> None`
- **Invariants**:
  - Writes are transactional; partial writes leave no observable state.
  - Valuations table is append-only; duplicate `(col_identifier, col_calibration_timestamp)` rows are rejected at the DB level.
  - Credentials loaded from Vault at process start; not re-read per-call.
- **Failure modes if bound incorrectly**:
  - Non-transactional writes → corruption visible to downstream consumers (high / hard).
  - Duplicate-row tolerance → double-reporting (medium / hard).

## PB-3 — Event publisher (implements AP-3)

- **Target contract**: `EventPublisherInterface`.
- **Required methods**:
  - `publish(valuations: DataFrame) -> None`
- **Invariants**:
  - Publisher acks every message before returning success.
  - Retries with exponential backoff on transient broker failures.
  - Preserves per-identifier ordering within a batch if the downstream consumer depends on it (confirm with the owners of the topic).
- **Failure modes if bound incorrectly**:
  - Fire-and-forget without ack → silent message loss (critical / invisible-until-production).
  - Ordering mismatch → downstream state machine drift.

## PB-4 / PB-5 / PB-6 — Valuation / simulation / calibration bodies

(omitted for brevity — each specifies the scaffold's Protocol or function signature as the contract, lists determinism / monotonicity / output-shape invariants, and names the failure modes of silent numerical divergence.)

# 5. File-level integration strategy

(Every file in the scaffold's Section 2 tree appears here. Condensed below.)

## `src/pricing_engine/domain/schemas.py`
- **Action**: `keep as is`
- **Rationale**: pure dataclasses / pydantic models; no private dependency; schema names are generic by construction.
- **Effort**: `trivial`
- **Validation**: Section 6 item 2 (schema round-trip on a private sample).

## `src/pricing_engine/domain/valuation.py`
- **Action**: `keep with local adapter injection`
- **Rationale**: structure is correct; bodies of two ADAPTATION POINTs are swapped via dependency injection (e.g. a `ValuationProvider` parameter wired in `pipeline.py`).
- **Effort**: `medium`
- **Validation**: Section 6 items 1, 6, 11.

## `src/pricing_engine/interfaces/*.py`
- **Action**: `keep as is`
- **Rationale**: Protocols define the contracts; should not be edited during binding.
- **Effort**: `trivial`

## `src/pricing_engine/infrastructure/adapters/*.py`
- **Action**: `keep as is` for the files themselves; adapter bodies get `PRIVATE BINDING REQUIRED` replacements during binding.
- **Rationale**: each adapter file is the intended seam.
- **Effort**: `medium` per adapter.

## `src/pricing_engine/config/settings.py`
- **Action**: `merge manually into an existing private file`
- **Rationale**: the private system almost certainly has its own settings entry point (Vault-backed); the scaffold's one is a reference for the shape, not a file to copy in.
- **Effort**: `small`.
- **Validation**: Section 6 item 5.

## `src/pricing_engine/pipeline.py`
- **Action**: `keep with local adapter injection`
- **Rationale**: pipeline orchestrator wires the private adapters through the DI container (if present) or via explicit factory calls (if not).
- **Effort**: `medium`.

## `tests/*.py`
- **Action**: `keep as is` (as contract tests) + `partial manual transplantation` (into any existing private test suite convention).
- **Rationale**: scaffold's tests serve as a fixed contract-test suite; the private project may additionally need integration tests that exercise the real adapters.
- **Effort**: `small`.

## `pyproject.toml`
- **Action**: `use only as a design reference`
- **Rationale**: private system uses poetry; scaffold is uv; dependency list is cherry-picked and added to the private `pyproject.toml`.
- **Effort**: `small`.

## `.env.example`
- **Action**: `use only as a design reference`
- **Rationale**: private system uses Vault, not env-files; but the scaffold's keys indicate what settings the bind needs to provide.
- **Effort**: `trivial`.

# 6. Validation and regression checklist

1. **Interface conformance** — `mypy src/pricing_engine/infrastructure/adapters/` passes with no errors.
2. **Schema round-trip** — a representative Postgres row (loaded via the private DB client) parses into `MarketObservation` / `CalibratedParameterSet` / `ValuationResult` without errors.
3. **Shape consistency** — `DataFrame.shape[1]` matches the scaffold's declared column count on a batch of ≥100 instruments.
4. **Dependency resolution** — `poetry lock` completes with no conflicts after merging the scaffold's dependencies.
5. **Config loading** — the settings provider resolves every key expected by the scaffold on both staging and prod.
6. **Unit tests** — `pytest tests/` passes for every test file the scaffold shipped, against the bound adapters.
7. **Integration smoke** — a single-instrument end-to-end run in staging returns a non-null `ValuationResult` and publishes one event.
8. **Side-effect correctness** — publisher acks match count of published messages; DB rows match count of valuations.
9. **Logging** — scan staging logs for any substring on an agreed private-identifier blocklist; assert zero matches.
10. **Backward compatibility** — no pre-existing private test fails after the merge.
11. **Output equivalence** — bit-identical valuations on a fixed synthetic input before and after the binding (closed-form branch); within declared tolerance on the seeded simulation branch.
12. **Performance sanity** — single-batch latency within 10× of the pre-bind baseline.

# 7. Reintegration risks

| # | Risk | Severity | Detectability | Mitigation |
|---|------|----------|---------------|------------|
| 1 | Contract mismatch on adapter boundary | high | moderate | Section 6 item 1 before merge; contract tests per adapter. |
| 2 | Schema drift between `Dataset_RawObservations` and the private observation DTO | medium | hard | Section 6 items 2, 3 plus a one-time schema diff on a representative sample. |
| 3 | Silent behavioural divergence in AP-4 / AP-5 / AP-6 replacements | high | invisible-until-production | Section 6 item 11; user has no shadow-deploy, so require a golden-file comparison run on historic snapshots before cutover. |
| 4 | No rollback path (private system has no feature flag described) | critical | invisible-until-production | Introduce a runtime flag gating the new pipeline behind the old one for at least one release cycle. |
| 5 | Dependency conflict between scaffold pins and private poetry lockfile | medium | easy | Section 6 item 4 before merge; loosen scaffold pins where private pins are authoritative. |
| 6 | RabbitMQ ordering mismatch (downstream consumer assumptions unknown) | medium | hard | Confirm ordering requirements with the topic owners before binding; feature-flag the publisher; run a staging consumer check. |
| 7 | Credential path deviation (Vault vs. scaffold's env-var path) | high | hard | Section 6 item 5 on every target environment; explicit settings integration test. |

# 8. Minimal safe integration order

1. **Bind configuration** — merge scaffold's settings shape into the private Vault-backed settings module. Gate: Section 6 item 5 on staging.
2. **Bind interfaces** — copy `src/pricing_engine/interfaces/*.py` into the private repo (`keep as is`). Gate: Section 6 item 1 on a pure-types build.
3. **Bind schemas** — copy `src/pricing_engine/domain/schemas.py` (`keep as is`); wire to the private normalisation layer for `Dataset_RawObservations`. Gate: Section 6 items 2, 3 on real samples.
4. **Integrate pure domain logic** — copy the rest of `domain/` (`keep as is`); bodies of AP-4, AP-5 are initially stubbed to raise, so that the pipeline boots but explicitly flags the replacement seams. Gate: Section 6 item 6 on the scaffold's unit tests only.
5. **Integrate adapters one at a time** — (a) MarketData, (b) OperationalStore, (c) EventPublisher. Each adapter: write the private body, run its contract test, merge. Gate after each: Section 6 item 1 (adapter alone), Section 6 item 7 (smoke test on the branch).
6. **Swap in AP-4, AP-5, AP-6 real bodies** — inject the private valuation and calibration routines. Gate: Section 6 item 11 (golden-file) on historic inputs.
7. **Run full battery** — all Section 6 items.
8. **Ship behind a feature flag** — cutover is gated by the flag; flag starts at 0% traffic.
9. **Ramp / observe / cutover** — ramp the flag gradually; observe Section 6 items 8, 9 at each ramp step. Full cutover only after the flag has been at 100% in staging for at least one batch cycle.

Rollback: flip the feature flag back to the prior pipeline. The prior implementation is preserved in-tree for at least one release cycle after cutover.
```

---

## Commentary

Notice what the map does and doesn't do:

- It **names the scaffold's symbols** (`MarketDataInterface`, `compute_closed_form_valuation`) because those are Claude's to name.
- It **refuses to name the private market-data client**, the private Postgres schema, the private RabbitMQ exchange. Every binding is specified by contract.
- It **calls out the user's lack of shadow-deploy infrastructure** as a risk and specifies a compensating mechanism (feature flag + historic golden-file comparison).
- It **distributes uncertainty honestly**: `low confidence` on the test-harness row because the user didn't describe their private test conventions; `medium confidence` on the schema rebindings because the roles match but the field names don't.
- It **ends with a concrete integration order** where every step has a gate tied to a Section 6 item.

That is the shape every reintegration map should take.

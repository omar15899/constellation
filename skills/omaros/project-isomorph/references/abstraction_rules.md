# Project Isomorph — Abstraction Rules (full decision tree)

This file is the authoritative reference for every transformation the skill applies. The SKILL.md gives the summary table; this file is the long-form specification. Consult when a naming decision is non-obvious or when verifying that no leak remains.

## The two-pass rule

Do two passes over every identifier, in this order:

1. **Classify the role.** Decide what kind of thing this identifier names — a module, a class, a function, a dataset, a column, an external service, a credential handle, etc. Never rename before classifying; otherwise the placeholder carries no semantic weight.
2. **Derive a canonical placeholder.** Use the role-specific template from the tables below. Preserve the role in the placeholder so the dossier still reads as a coherent system.

The reason for two passes: a naive rename (e.g. `f_price_option` → `func_a`) destroys the reader's ability to follow the architecture. A role-aware rename (`f_price_option` → `compute_derivative_valuation`) keeps the structure legible while erasing the business detail.

## Role classification

Classify every real identifier into exactly one of these role classes before renaming.

| Role class | What qualifies |
|------------|----------------|
| `Structural/Module` | Top-level directory, package, or namespace |
| `Structural/Submodule` | A sub-package within a module |
| `Structural/Class` | A class definition |
| `Structural/Function` | A named function or method |
| `Structural/Script` | An executable script (entry point) |
| `Structural/Service` | A long-running process, daemon, or server |
| `Data/Dataset` | A named collection of records (table, file, stream) |
| `Data/Entity` | A domain entity (the rows of a dataset) |
| `Data/Column` | A single field inside a dataset/entity |
| `Data/Schema` | A named schema, message type, or protobuf definition |
| `Domain/Concept` | A business-specific term the code adopts (product, region, desk, book) |
| `External/API` | A third-party service the code calls |
| `External/Endpoint` | A URL path or gRPC method on such a service |
| `External/Database` | A database, warehouse, or lake the code reads/writes |
| `External/Queue` | A message broker topic or queue |
| `Config/Env` | An environment variable name |
| `Config/Flag` | A feature flag or boolean switch |
| `Config/Secret` | A credential handle (never a credential value) |
| `Temp/Local` | A local variable inside a function (usually doesn't need listing) |

## Placeholder templates by role

For each role, use the pattern on the left; examples on the right.

| Role | Placeholder pattern | Examples (generic, do not reuse verbatim) |
|------|---------------------|-------------------------------------------|
| `Structural/Module` | `Module_<Role>` where `<Role>` is a verb-or-noun summary of the module's responsibility | `Module_Ingestion`, `Module_Calibration`, `Module_Valuation`, `Module_Reporting`, `Module_Monitoring` |
| `Structural/Submodule` | `<ParentModule>.<SubRole>` | `Module_Ingestion.VendorAdapters`, `Module_Modelling.DiagnosticsPanel` |
| `Structural/Class` | `<Role>Component` or `<Role>Service` | `PricingEngineComponent`, `CalibrationOrchestratorService`, `RiskAggregatorComponent` |
| `Structural/Function` | `<verb>_<object_role>` (snake_case) | `compute_valuation`, `calibrate_parameters`, `assemble_report`, `publish_metrics` |
| `Structural/Script` | `run_<role>.py` or `<role>_cli` | `run_daily_valuation.py`, `run_calibration_batch.py` |
| `Structural/Service` | `<Role>Service` | `ValuationService`, `ObservationIngestorService` |
| `Data/Dataset` | `Dataset_<Role>` | `Dataset_RawObservations`, `Dataset_CalibratedParameters`, `Dataset_DerivedValuations` |
| `Data/Entity` | `<Role>Record` (singular) | `ObservationRecord`, `ValuationRecord`, `CalibrationSnapshotRecord` |
| `Data/Column` | `col_<role>` | `col_timestamp`, `col_identifier`, `col_numeric_measure`, `col_category`, `col_status_flag`, `col_free_text_note`, `col_enum_N_values` |
| `Data/Schema` | `Schema_<Role>_v<n>` | `Schema_ObservationPayload_v2`, `Schema_ValuationResult_v1` |
| `Domain/Concept` | `Concept_<Role>` | `Concept_TradeableInstrument`, `Concept_RiskFactor`, `Concept_BookingEntity` |
| `External/API` | `ExternalService_<Role>` | `ExternalService_MarketDataVendor`, `ExternalService_PaymentProcessor`, `ExternalService_AuthProvider` |
| `External/Endpoint` | `/api/<resource>/<sub>` using role-labelled segments | `/api/resources`, `/api/resources/{resource_id}/events`, `/api/reports/{report_id}` |
| `External/Database` | `Database_<Role>` | `Database_OperationalStore`, `Database_AnalyticsWarehouse`, `Database_EventLog` |
| `External/Queue` | `Topic_<Role>` or `Queue_<Role>` | `Topic_IncomingObservations`, `Queue_CalibrationJobs` |
| `Config/Env` | `ENV_<ROLE>` | `ENV_API_KEY_VENDOR`, `ENV_DB_CONNECTION_STRING`, `ENV_FEATURE_FLAG_X` |
| `Config/Flag` | `FLAG_<ROLE>` | `FLAG_USE_NEW_CALIBRATION`, `FLAG_ENABLE_DIAGNOSTICS` |
| `Config/Secret` | `SECRET_HANDLE_<ROLE>` | `SECRET_HANDLE_VENDOR_AUTH` (never the value itself) |

## Collision resolution

If two real names map to the same placeholder under these rules, disambiguate deterministically by appending `_1`, `_2`, etc., in encounter order (by a stable traversal — e.g. alphabetical by real name before renaming). Never renumber across dossier revisions for the same project; the mapping must be stable so a reader comparing two versions can trace changes.

## Algorithmic class preservation

When describing internal logic, name the **algorithmic class** and nothing more specific. The class tells a downstream AI what to reach for; the specifics are proprietary.

Acceptable phrasings (preserve class):

- "applies a closed-form option-pricing formula under a log-normal asset model"
- "performs stochastic gradient descent on a mean-squared-error objective"
- "runs a Kalman filter update given observation residuals"
- "executes a depth-first traversal over the dependency graph and emits a topological order"
- "fits a linear regression by ordinary least squares on the transformed features"
- "samples the posterior via Metropolis–Hastings with a Gaussian proposal"
- "solves a boundary-value PDE by finite-differences on a uniform grid"
- "reduces a batch of records by grouping on a key and aggregating with sum/mean/count"
- "constructs a confidence interval via non-parametric bootstrap resampling"

Unacceptable (leaks specifics):

- The actual Black–Scholes formula text. (Named algorithms are public; the *combination* of a public algorithm with a proprietary parametrisation is what leaks.)
- Actual hyperparameter values: learning rate 3e-4, 128 hidden units, 5 trees of depth 6, window=240.
- Proprietary scoring rules written in inequalities.
- The exact loss function weighting applied to the business objective.

Rule of thumb: if removing the detail still lets a downstream AI pick the right library / technique, keep removing.

## Parameter abstraction

Concrete numerical tuning is almost always a leak — it's often hand-calibrated to the business and reveals the scale, risk appetite, or data profile of the operation. Replace numeric constants with symbolic names indicating class and, if needed, order of magnitude.

| Concrete form | Abstracted form |
|---------------|-----------------|
| `timeout=30` | `timeout=T_seconds`, "O(10 s) timeout" |
| `batch_size=128` | `batch_size=B`, "B in the O(10²)–O(10³) range" |
| `learning_rate=3e-4` | `learning_rate=η`, "small positive step size" |
| `window=240` (of daily bars) | `window=W`, "W observations covering roughly one business year" |
| `num_layers=3` | `num_layers=L`, "L = small constant" |
| `threshold=0.87` | `threshold=τ`, "τ in (0, 1) tuned on a held-out set" |
| `retries=5` | `retries=K`, "K = small constant with exponential back-off" |

When a specific value is load-bearing for correctness (not just tuning), note it as "class X, specific value preserved implicitly — must be re-tuned in the reconstruction". Don't leak it; flag it in Section 8 as known non-preservation.

## String abstraction

Log messages, error messages, exception types, and comments are high-leak because they are written for humans and often spell out the domain. Always paraphrase before quoting.

| Original | Abstracted |
|----------|------------|
| `"failed to fetch prices for ticker AAPL"` | `"failed to fetch <input-record> for <record-identifier>"` |
| `"warning: book X exceeded var limit"` | `"warning: <aggregation-unit> exceeded <policy-threshold>"` |
| `raise InvalidTradeError(...)` | `raise DomainValidationError(...)` (class renamed generically) |
| comment: `# TODO: handle end-of-day roll for FX forwards` | comment: `# TODO: handle <lifecycle-event> for <instrument-class>` |

Custom exception types should be renamed with the same role-aware scheme used for classes.

## File-path abstraction

File paths reveal directory structure, deployment layout, and often brand names. Redact every path to a role-labelled form.

| Original | Abstracted |
|----------|------------|
| `/opt/acme/pricer/src/bs_pricer.py` | `<install-root>/<pricing-module>/<option-pricing-script>` |
| `s3://acme-prod-observations/2025/01/` | `<object-store>://<observations-bucket>/<partition>/` |
| `/etc/acme/config/vendor_keys.yaml` | `<config-root>/<credential-manifest>` |
| `C:\ProgramData\AcmeTools\cache` | `<program-data-root>/<tool-family>/<cache-dir>` |

## Comment and docstring abstraction

Docstrings and comments often carry a decade of institutional knowledge — they are the densest leak surface per line. Paraphrase into the dossier; never copy. When the docstring conveys architectural intent, translate its content into a bullet under the corresponding component spec. When the docstring is business narrative, drop it — the dossier's audience doesn't need it to rebuild.

## Credentials, tokens, and anything that looks like a secret

Treat everything matching these patterns as a credential — even if it "looks fake":

- `api[_-]?key`, `secret`, `token`, `password`, `bearer`, `sk-…`, `ghp_…`, `AKIA…`
- Any hex or base64 string longer than 16 characters that isn't obviously a hash

For each found instance, emit only the role (`SECRET_HANDLE_VENDOR_AUTH`) in Section 7, with a brief note on the auth model. Never the value. Never the handle's real name (it often encodes the business).

## When a public library gets identifying

Most public libraries (numpy, pandas, requests, fastapi, etc.) are fine to name; they don't identify the business. But some dependencies, when combined with the project's shape, are highly identifying — e.g. a niche vendor SDK, an internal fork of a public library, a proprietary wrapper. When in doubt:

- Replace the dependency with a generic role: `dependency on a vendor SDK for market-data retrieval`, `dependency on an internal wrapper around an HTTP client`.
- Preserve the shape (sync/async, streaming/batch) so the downstream AI picks the right replacement.

## What to keep, what to drop

| Keep | Drop |
|------|------|
| Number of modules, components, datasets | Their real names |
| Type of every interface (sync/async, streaming/batch, push/pull) | The actual function signature with real parameter names |
| Every dependency edge (A calls B, B writes to C) | Which specific business operation each edge implements |
| Algorithmic class used at each step | The specific formula, threshold, coefficient |
| Shape of every dataset (rows × columns, row cardinality class) | The real column names and their business meaning beyond a generic role |
| Nature of every external integration | The vendor identity, endpoint URL, credential handle |
| Invariants each component maintains | The private docstring explaining why those invariants exist |

## Final sanity check

Before returning the dossier, ask yourself:

1. Could a reader who knew nothing about the project guess the real business domain from what remains? If yes, redact further.
2. Could a downstream AI, given only the dossier, rebuild a system that satisfies the Section 8 behaviours? If no, add more structural detail.

Dual fails on (1) *or* (2) are the only failure modes — they are symmetric: too little redaction, or too little structure. Iterate until both pass.

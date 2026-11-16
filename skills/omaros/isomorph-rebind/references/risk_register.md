# Isomorph Rebind — Risk Register

Catalog of typical reintegration failure modes. Use as the default menu when populating Section 7 of the reintegration map. Add project-specific rows when the scaffold's shape demands them. Every row in Section 7 must pick a severity, a detectability, and a concrete mitigation.

---

## Severity values (closed)

| Severity | Meaning |
|----------|---------|
| `low` | Annoyance; caught in dev, no production impact. |
| `medium` | Wastes engineering time; might cause a bad release if missed; recoverable. |
| `high` | Incident-class; users / downstream systems feel it; on-call involved. |
| `critical` | Data loss, security breach, silent corruption of records that persist. |

## Detectability values (closed)

| Detectability | Meaning |
|---------------|---------|
| `easy` | Fails loudly at the boundary (type error, schema validation error, import error). |
| `moderate` | Fails a targeted test but needs the test to exist and to run. |
| `hard` | Only shows up under specific load / data / timing combinations. |
| `invisible-until-production` | Produces wrong-looking output silently; caught only by downstream users or by a much later comparison. |

Detectability is NOT the same as severity. A critical risk can be easy (schema mismatch blocking deploy) or invisible (silent rounding error in a pricing formula).

---

## The default catalog

Pick from these; add project-specific rows when the scaffold's shape suggests them. Each row here is the template — fill in the specifics for the actual reintegration.

### Contract risks

- **Contract mismatch at an adapter boundary.** The private adapter does not satisfy the generic interface exactly (missing method, wrong return type, wrong exception semantics). Severity: `high`. Detectability: `easy` if the user runs the type-checker; `invisible-until-production` if they don't. Mitigation: `mypy` / `tsc` / equivalent on the adapter seam as the first gate in Section 8; contract tests that exercise every method with a representative input.
- **Invariant violated silently.** Adapter satisfies the interface shape but breaks an invariant stated in the scaffold's docstring (determinism, ordering, idempotency, bounded retries). Severity: `high`. Detectability: `hard`. Mitigation: property-based test (hypothesis / fast-check) over the invariant; re-read the scaffold's docstring during the bind.
- **Signature drift on future scaffold regeneration.** A later `isomorph-synth` run produces a slightly different interface, and the private adapter silently diverges. Severity: `medium`. Detectability: `moderate` via a diff-check in CI against the prior scaffold. Mitigation: pin the scaffold artefact used; re-run the reintegration map when the scaffold changes.

### Schema / data risks

- **Schema drift between `Dataset_<Role>` and the private analogue.** Column names / types / nullability differ silently; the scaffold's pydantic models accept but downstream consumers break. Severity: `high`. Detectability: `hard`. Mitigation: run a schema-diff tool on a representative sample; schema tests (Section 6 item 2) with strict validation.
- **Shape mismatch on DataFrames / tensors.** Right columns, wrong order; or right shape, wrong dtype. Severity: `medium`. Detectability: `easy` if tests assert shape; `invisible-until-production` otherwise. Mitigation: explicit shape assertions in the adapter; dtype assertions in the test suite.
- **Temporal consistency violated.** Private data is update-in-place but the scaffold expects append-only (or vice versa). Severity: `high`. Detectability: `invisible-until-production` — works on static snapshots, fails when history matters. Mitigation: explicit effective-dating check; mirror the scaffold's temporal invariants in the adapter.

### Naming / boundary risks

- **Naming collision with the private codebase.** A scaffold module name happens to match a private module of a different role. Severity: `medium`. Detectability: `easy` (import error) when it breaks; `hard` when two importable things coexist. Mitigation: rename via the "keep with renaming" disposition in Section 5.
- **Wrong abstraction boundary.** Scaffold's module boundary doesn't match where the private system's own boundary lives; forces a seam to run through the middle of a private module. Severity: `medium`. Detectability: `moderate` — shows up as integration pain during the bind. Mitigation: prefer `interface-only reuse` or `partial manual transplantation` when the boundary doesn't align; consider `non-reintegrable without redesign` if the scaffold's layering fundamentally disagrees.
- **Over-integration.** The user pulls more of the scaffold in than the spec warranted, dragging in generic code that duplicates existing private code and causes maintenance drift. Severity: `medium`. Detectability: `hard`. Mitigation: strictly honour Section 5 dispositions; resist the urge to copy extra files "because they're there".

### Safety risks

- **Accidental replacement of trusted private logic.** User merges a scaffold file over a private file that had proprietary logic; the merge looks clean but business rules silently change. Severity: `critical`. Detectability: `invisible-until-production`. Mitigation: default Section 5 disposition for any file that would overwrite existing private code is `merge manually` or `use only as a design reference`, never `keep as is`; code review is mandatory; git history must preserve the prior version.
- **Accidentally leaking private content via scaffold logging / metrics / error strings.** Scaffold emits generic log lines; user binds to a private identifier; the identifier ends up in logs that ship to a shared observability sink. Severity: `high`. Detectability: `hard`. Mitigation: Section 6 item for log-scanning a private-identifier blocklist; redact at the logger boundary; keep sensitive values out of exception messages.
- **Credential handling deviation.** Scaffold's `.env.example` uses generic placeholders; user binds differently than the scaffold expected (env var vs. secrets manager vs. mounted file) and credential loads fail silently at runtime. Severity: `high`. Detectability: `hard`. Mitigation: explicit config-loading validation (Section 6 item 5) in every deployment environment; document the credential source in Section 4's binding.

### Silent divergence risks

- **Behavioural divergence between the scaffold's generic default and the proprietary body.** A numerical routine is swapped with a private version; all shape tests pass; but outputs differ meaningfully. Severity: `high`. Detectability: `invisible-until-production`. Mitigation: golden-file equivalence test (Section 6 item 11); shadow deploy before cutover; explicit reconciliation report comparing scaffold output and private output on a representative sample.
- **Caching behaviour changed.** Scaffold is stateless; user's adapter introduces caching (or vice versa), breaking idempotency expectations elsewhere in the pipeline. Severity: `medium`. Detectability: `hard`. Mitigation: explicit test for idempotency on repeated calls; Section 4 binding's invariant list must name caching behaviour.
- **Test coverage degradation.** The scaffold's tests all pass because the adapter stubs them out; the real private binding is never actually exercised. Severity: `high`. Detectability: `hard`. Mitigation: mark the scaffold's tests as "contract tests" and require a separate integration-test suite that exercises the bound adapter against a staging environment.

### Process risks

- **No rollback path.** The reintegration is merged, the prior implementation is deleted, and the new binding fails. Severity: `critical`. Detectability: `invisible-until-production`. Mitigation: feature flag / DI registration that can be flipped off; prior implementation kept in the codebase for at least one release cycle.
- **Concurrent changes to the scaffold source while integrating.** `isomorph-synth` is re-run mid-integration and the scaffold shifts underneath. Severity: `medium`. Detectability: `moderate`. Mitigation: pin the scaffold version (commit hash or versioned artefact) referenced by the reintegration map.
- **Dependency conflict.** Scaffold declares a pinned version of a library that conflicts with the private repo's existing pins. Severity: `medium`. Detectability: `easy` (lockfile resolution fails). Mitigation: verify Section 6 item 4 before merging; loosen the scaffold's pin if the private pin is the authoritative one.

---

## Choosing rows for Section 7

For a typical reintegration, 5–8 rows from the catalog above cover the real risks. Select based on:

- The scaffold's integration surface. (Many external integrations → more contract and schema risks.)
- The private system's maturity. (Stable long-lived codebase → more naming-collision risk. Greenfield → more silent-divergence risk as nothing canary-compares.)
- The user's described deployment norms. (If they mention shadow deploys, silent-divergence mitigation is already partly in place; if not, it needs to be surfaced.)

Under-listing is worse than over-listing. An unlisted risk that materialises is a reintegration failure. A listed but benign risk is a one-line reassurance.

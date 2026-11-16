# Isomorph Rebind — Output Protocol (authoritative)

This is the exact shape of the reintegration map. The 8-section contract is load-bearing — `validate_rebind_map.py` parses it, and the user reading the plan during the bind depends on the stability of the layout. Deviate from the sections only by explicitly marking one `_not applicable — <reason>_` rather than omitting.

---

## Top-level skeleton

```markdown
# 1. Reintegration assumptions
# 2. System correspondence map
# 3. Adaptation points
# 4. Required private bindings
# 5. File-level integration strategy
# 6. Validation and regression checklist
# 7. Reintegration risks
# 8. Minimal safe integration order
```

Each section's required shape is below.

---

## 1. Reintegration assumptions

Four explicit sub-groups, in order. Bulleted. Keep short — this is the reader's quick map of what the plan is standing on.

```markdown
## Known from the generic scaffold
- <bullet>: <fact sourced directly from the scaffold — module count, interface names, declared markers, …>

## Known about the private system
- <bullet>: <only what the user has told you in this conversation; nothing inferred, nothing guessed>

## Unknown about the private system
- <bullet>: <every load-bearing detail you don't know: specific framework version, test-runner conventions, deployment targets, credential mechanism, observability sink, DB engine, …>

## Assumptions made to proceed
- <bullet>: <each assumption this plan depends on, stated so the user can veto it before following the plan>
```

The "Unknown" sub-group is the one readers skip and regret skipping. Do not let it be empty unless the user has provided a very detailed private-system description.

---

## 2. System correspondence map

A table, one row per major generic artefact (module, component, dataset, interface, integration point). Six columns:

```markdown
| Generic artefact | Likely private counterpart category | Correspondence type | Confidence | Integration mode | Notes |
|------------------|--------------------------------------|---------------------|------------|-------------------|-------|
| `Module_Calibration` | calibration subsystem | exact structural analogue | high | adapter-mediated | Private system almost certainly has a calibration step; the scaffold's interface should map cleanly. |
| `ClosedFormValuationComponent` | valuation routine | domain-logic placeholder | high | adapter-mediated | Body replaces; signature and output shape preserved. |
| `ExternalService_MarketDataVendor` | vendor SDK wrapper | infrastructure placeholder | high | interface-only reuse | Scaffold provides the interface; the private system has its own wrapper that must conform. |
| `Dataset_CalibratedParameters` | private calibration-params schema | schema placeholder | medium | schema-rebinding | Semantic role matches; column names and types need verification. |
| `Topic_DownstreamPnL` | message broker topic | infrastructure placeholder | low | architectural reference reuse | User did not describe their messaging infrastructure; alternatives listed in Notes. |
```

**Category** values are closed: `exact structural analogue`, `interface-level analogue`, `infrastructure placeholder`, `schema placeholder`, `domain-logic placeholder`, `integration wrapper`, `test harness`.

**Correspondence type** values are closed: `exact`, `interface-level`, `placeholder`, `wrapper`, `reference`.

**Confidence** is `high` / `medium` / `low` — see `confidence_discipline.md`. Every `low` row must name at least one alternative in Notes.

**Integration mode** is one of: `direct drop-in`, `adapter-mediated`, `interface-only reuse`, `architectural reference reuse`, `partial manual transplantation`, `non-reintegrable without redesign`. See `integration_modes.md` for when each applies.

---

## 3. Adaptation points

One subsection per adaptation marker in the scaffold. Extracted via `extract_adaptation_points.py`.

```markdown
## AP-<N> — <short-role-label>

- **Tag**: `ADAPTATION POINT` / `PRIVATE BINDING REQUIRED` / `LOCAL NAME REBINDING` / `SCHEMA REBINDING REQUIRED` / `INFRASTRUCTURE SUBSTITUTION REQUIRED` / `SAFE TO KEEP GENERIC`
- **Location (generic scaffold)**: `<file>:<symbol>`
- **What must change**: <concrete statement — the body, the adapter, the import path, the config entry, …>
- **Why**: <the private contract that imposes the change>
- **What must be bound**: <contract, not a name — "a provider satisfying methods X, Y, Z with invariants I_1, I_2">
- **Mandatory / optional**: `mandatory` / `optional` (with a reason for `optional`)
- **Invariants post-change**: <signature, shape, determinism, idempotency, error semantics — whatever must still hold for the rest of the plan to work>
```

Numbering (`AP-1`, `AP-2`, …) is stable across revisions of the same map, so the user can refer to points by ID in code reviews.

Tag semantics:

- `ADAPTATION POINT` — scaffold has a runnable generic default; replace the body with the private routine, preserve signature.
- `PRIVATE BINDING REQUIRED` — scaffold has a stub; the user must provide a concrete implementation.
- `LOCAL NAME REBINDING` — the scaffold uses generic names; the user renames to match private conventions. No semantic change.
- `SCHEMA REBINDING REQUIRED` — generic schema names → private schema names; semantic role preserved.
- `INFRASTRUCTURE SUBSTITUTION REQUIRED` — scaffold's dev-time stub (SQLite, stdout logger, in-memory queue) → the private real infrastructure.
- `SAFE TO KEEP GENERIC` — the scaffold's implementation is appropriate as-is; no change needed.

Some adaptation points may carry multiple tags (e.g. both `INFRASTRUCTURE SUBSTITUTION REQUIRED` and `LOCAL NAME REBINDING`). That's fine; list all applicable tags.

---

## 4. Required private bindings

Translate each adaptation point that requires a private implementation into a binding specification. Not every adaptation point becomes a binding — `LOCAL NAME REBINDING` and `SAFE TO KEEP GENERIC` usually don't.

```markdown
## PB-<N> — <short-role-label> (implements AP-<N> / AP-<M>)

- **Target contract**: <the interface / protocol / shape the private implementation must satisfy>
- **Required methods or fields**:
  - `<method_name>(<typed args>) -> <typed return>` — <short role description>
  - `<field_name>: <type>` — <short role description>
- **Invariants**:
  - <determinism for fixed inputs / seed>
  - <idempotency on retry>
  - <tolerance for transient failure modes>
  - <ordering / cardinality / nullability guarantees on returned data>
- **Failure modes if bound incorrectly**:
  - <what happens if the return shape is wrong>
  - <what happens if the invariant is violated>
  - <how the wrongness will manifest — test failure, silent drift, production outage>
```

Each binding cross-references the adaptation point(s) it implements so the user can navigate Section 3 ↔ Section 4 during the bind.

---

## 5. File-level integration strategy

For every file in the scaffold, a disposition from the closed set:

- `keep as is` — copy into the private repo, unchanged.
- `keep with renaming` — rename to match private conventions; contents unchanged.
- `keep with local adapter injection` — generic body stays; a private adapter is injected (DI, factory, partial, decorator).
- `merge manually into an existing private file` — file already exists privately; user cherry-picks portions.
- `use only as a design reference` — scaffold file is illustrative; private analogue is written from scratch with the scaffold as a sketch.
- `do not integrate directly` — stub / fixture / test helper the private side already owns.

Shape:

```markdown
## <relative/path/in/scaffold>

- **Action**: `<disposition>`
- **Rationale**: <why this disposition for this file>
- **Effort**: `trivial` / `small` (under 1 hour) / `medium` (1–4 hours) / `large` (full day or more)
- **Dependencies**: <other files in the scaffold this one requires, and any private-side dependencies the action presupposes>
- **Post-integration validation**: <the specific item(s) from Section 6 that validate this file's integration>
```

Every file in the scaffold's `Section 2 — Generated folder structure` must appear here. If genuinely nothing meaningful can be said about a file (e.g. empty `__init__.py`), state that explicitly with `Action: keep as is, Rationale: empty package marker`.

---

## 6. Validation and regression checklist

A numbered list of **deterministic** checks. Each item carries the tools / commands / assertions to run. The reader should be able to execute any item mechanically.

```markdown
1. **Interface conformance** — run `<type-checker>` on `<adapter file>`; assert no errors on the public boundary.
2. **Schema conformance** — parse a representative sample of the private dataset through the scaffold's pydantic/dataclass models; assert no validation errors.
3. **Shape consistency** — assert `DataFrame.shape[1]` matches the declared column count for `Dataset_<Role>`.
4. **Dependency resolution** — `uv sync` / `pnpm install` completes without conflicts in the private repo's lockfile.
5. **Config loading** — boot the pipeline with the private settings provider on each target environment; assert no unresolved keys.
6. **Unit tests** — `pytest tests/test_<module>.py` passes for every test file the scaffold shipped.
7. **Integration test** — a staging-env end-to-end run produces an output that matches a golden-file contract.
8. **Side-effect correctness** — count events emitted per batch; assert within the declared cardinality class.
9. **Logging behaviour** — scan logs for any string from a private-identifier blocklist; assert zero matches (protects against accidental leak of private content through the scaffold's generic log lines).
10. **Backward compatibility** — if reintegrating into an existing module, run the prior test suite; assert no pre-existing test now fails.
11. **Output equivalence** — compare against a prior golden output on a fixed synthetic input; assert bit-identical at the contract level (or within a declared tolerance for stochastic branches with controlled seeds).
12. **Performance sanity** — an order-of-magnitude regression check; flag anything worse than 10× the pre-bind baseline.
```

Not every checklist has all items; include only those relevant to the reintegration. Each item should name the actual tool / command, not a hand-wavy intent.

---

## 7. Reintegration risks

A table, one row per risk. Use the catalog in `risk_register.md` as the default menu; add project-specific rows when the scaffold's shape suggests them.

```markdown
| # | Risk | Severity | Detectability | Mitigation |
|---|------|----------|---------------|------------|
| 1 | Contract mismatch between the generic interface and the private implementation | high | moderate (caught by Section 6 item 1 if type-checking is run) | Section 6 items 1, 6 before merge; feature-flag the new binding for the first 24h. |
| 2 | Schema drift between `Dataset_<Role>` and the private analogue | medium | hard (will manifest as corrupted output downstream, not as an error at the boundary) | Section 6 items 2, 3, 8 + a one-time schema diff run on representative data. |
| 3 | Silent behavioral divergence in the proprietary body vs. the generic placeholder | high | invisible-until-production | Golden-file equivalence test (Section 6 item 11); shadow deploy for N hours before full cutover. |
| ... | ... | ... | ... | ... |
```

Severity values (closed): `low`, `medium`, `high`, `critical`.
Detectability values (closed): `easy`, `moderate`, `hard`, `invisible-until-production`.

---

## 8. Minimal safe integration order

Numbered ordering with one line per step: what is bound / integrated / run, and the validation check(s) that gate progression to the next step.

```markdown
1. **Bind configuration** — update the private settings provider to recognise the scaffold's config keys. Gate: Section 6 item 5.
2. **Bind interfaces** — register the scaffold's `Protocol` / `interface` definitions in the private DI container; no implementations yet. Gate: Section 6 item 1 on a pure-types build.
3. **Bind schemas** — wire the scaffold's dataclasses / pydantic models to the private normalisation layer. Gate: Section 6 items 2, 3.
4. **Integrate pure domain logic** — copy the scaffold's `domain/` tree; run its unit tests. Gate: Section 6 item 6 on domain tests.
5. **Integrate infrastructure adapters** — implement private adapters behind the interfaces bound in step 2. Gate: Section 6 items 1, 6 on adapter tests.
6. **Integrate orchestration layer** — wire the scaffold's `pipeline.py` to the private entry point. Gate: Section 6 item 7 on a staging end-to-end.
7. **Side-effect-safe smoke** — read-only end-to-end pass against the private dataset. Gate: Section 6 items 8, 9.
8. **Production-like validation** — shadow deploy or dark launch per the private system's norms; full Section 6 battery. Gate: all items green.
9. **Cutover** — switch traffic / schedule to the new binding. Rollback path: unregister the DI binding and revert to the prior implementation.
```

If the scaffold's shape warrants a different order (e.g. the scaffold is entirely a UI, so config-first doesn't apply), state it at the top of the section and proceed with the adapted sequence.

---

## Shape checklist before returning

- [ ] All 8 top-level headings present, in order, spelled exactly.
- [ ] Section 1 has all four sub-groups, including the Unknown sub-group.
- [ ] Every row in Section 2 carries a confidence label; every `low` confidence row names at least one alternative.
- [ ] Section 3 enumerates every marker found by `extract_adaptation_points.py`.
- [ ] Every mandatory AP in Section 3 has a matching PB in Section 4.
- [ ] Every PB in Section 4 has a contract, required methods/fields, invariants, and failure modes.
- [ ] Every file in the scaffold's tree appears in Section 5 with one of the six closed dispositions.
- [ ] Every check in Section 6 names the actual tool / command.
- [ ] Every row in Section 7 has severity + detectability + a concrete mitigation.
- [ ] Section 8 is numbered and each step has a gate tied to a Section 6 item.
- [ ] No real private name appears anywhere in the artefact. Everything is either a scaffold-generic name or a contract.

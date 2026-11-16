# Isomorph Synth — Adaptation Markers (authoritative taxonomy)

Adaptation markers are the grammar of the reintegration surface. Every place in a generated scaffold where a private binding will eventually happen must carry a labelled marker — not a bare `TODO`, not a `FIXME`, not a silent `pass`. Ad-hoc notes rot; labelled markers are machine-parseable, round-trip to the Reintegration Map, and survive the multi-month gap between scaffold generation and actual binding.

There are three marker kinds, organised by what the downstream binding replaces.

---

## `USER-INTEGRATION REQUIRED`

Use when the scaffold provides an **adapter** behind an interface and the downstream binding must connect the adapter to a real external system — a vendor SDK, a company database, a message broker, an identity provider, a storage bucket, a feature flag service.

The interface is fully defined. The generic implementation is a minimal stub (often an in-memory fake or a fixture loader) sufficient for tests. The downstream binder swaps the stub for the real thing.

### Canonical emission

Python:

```python
class MarketDataAdapter(MarketDataInterface):
    """
    USER-INTEGRATION REQUIRED
    Adapter for the upstream market-data vendor.
    Replace the stub body of `fetch_observations` with a call to the firm's
    real vendor client. The return shape must match Dataset_RawObservations
    as defined in src/pkg/domain/schemas.py; the adapter must tolerate
    transient 5xx without propagating them and must not cache across
    calibration runs.
    """

    def fetch_observations(self, universe: list[InstrumentHandle]) -> DataFrame:
        # USER-INTEGRATION REQUIRED: bind to the real market-data client.
        # The stub below reads a fixture so tests can run without network.
        return _load_stub_observations(universe)
```

TypeScript:

```typescript
/**
 * USER-INTEGRATION REQUIRED
 * Adapter for the upstream market-data vendor.
 * Replace `fetchObservations` with a call to the real vendor client.
 * The returned array must match `RawObservation[]` in `domain/schemas.ts`.
 */
export class MarketDataAdapter implements MarketDataInterface {
  async fetchObservations(universe: InstrumentHandle[]): Promise<RawObservation[]> {
    // USER-INTEGRATION REQUIRED: bind to real vendor client.
    return loadStubObservations(universe);
  }
}
```

### What Section 4 records

```markdown
- **USER-INTEGRATION REQUIRED** in `src/pkg/infrastructure/adapters/market_data_adapter.py:MarketDataAdapter.fetch_observations` — bind to the firm's real market-data vendor SDK; returned DataFrame must match `Dataset_RawObservations`, must tolerate transient 5xx, must not cache across calibration runs.
```

---

## `ADAPTATION POINT`

Use when the scaffold provides a **generic default implementation** (not just an interface) that the downstream binding will replace with a proprietary version. The default should be runnable end-to-end so the scaffold boots on synthetic data and tests pass; the private version later preserves the same signature and contract but diverges in the body.

The prototypical case: a numerical routine where the spec preserves the algorithmic class ("closed-form option pricing under a log-normal asset model") but the firm has a proprietary parametrisation. The scaffold ships with a textbook Black–Scholes body; the bind step replaces just the body.

### Canonical emission

```python
def compute_closed_form_valuation(
    instrument: InstrumentHandle,
    params: CalibratedParameterSet,
    observation: MarketObservation,
) -> ValuationResult:
    """
    ADAPTATION POINT
    Generic closed-form valuation under a log-normal asset model.
    Replace this body with the firm's proprietary valuation routine while
    preserving the exact signature. The returned ValuationResult must remain
    deterministic for a fixed (instrument, params, observation) triple.
    """
    # ADAPTATION POINT: swap body for the proprietary valuation routine.
    # Generic Black–Scholes below; serves as a runnable default for tests.
    S = observation.underlying_price
    K = instrument.strike
    T = (instrument.maturity - observation.as_of).total_seconds() / SECONDS_PER_YEAR
    r = params.short_rate
    sigma = params.implied_vol
    ...
    return ValuationResult(present_value=pv, sensitivities=deltas)
```

Key differences from `USER-INTEGRATION REQUIRED`:

- There is a real generic body, not a stub that reads a fixture.
- The binding preserves the exact signature; the rest is swapped wholesale.
- Tests written against the generic implementation may or may not continue to hold after binding — see the Reintegration Map's "what must remain true" column.

### What Section 4 records

```markdown
- **ADAPTATION POINT** in `src/pkg/domain/valuation.py:compute_closed_form_valuation` — replace the generic Black–Scholes body with the firm's proprietary valuation routine; signature and output shape must be unchanged so the end-to-end tests still run; determinism requirement must be preserved.
```

---

## `PROJECT-SPECIFIC IMPLEMENTATION GOES HERE`

Use when the scaffold **intentionally leaves a block empty** because no generic default is possible or appropriate — often because the block is configuration, a policy rule, a wiring decision, or a strongly domain-specific branch. The downstream binding supplies the block wholesale; the scaffold's default is `pass` / `raise NotImplementedError` / a commented empty block.

This is the least-preferred marker because it leaves the scaffold non-runnable at that point — prefer `ADAPTATION POINT` (runnable default) or `USER-INTEGRATION REQUIRED` (runnable stub) when either is feasible. Use `PROJECT-SPECIFIC IMPLEMENTATION GOES HERE` only when there genuinely is no reasonable generic.

### Canonical emission

```python
def business_specific_scoring_rule(candidate: Candidate) -> float:
    """
    PROJECT-SPECIFIC IMPLEMENTATION GOES HERE
    This scoring rule is proprietary and has no generic default. The scaffold
    intentionally leaves it unimplemented; tests that depend on it are marked
    xfail (see tests/test_scoring.py).

    Contract:
      - Input: Candidate record.
      - Output: bounded float score in [0, 1].
      - Monotonicity: for two candidates a, b, if a's observable features
        dominate b's, the score of a must be >= score of b.
      - Determinism: pure function of `candidate`.
    """
    # PROJECT-SPECIFIC IMPLEMENTATION GOES HERE — bind the firm's scoring rule.
    raise NotImplementedError(
        "business_specific_scoring_rule has no generic default; see "
        "adaptation_markers.md and the Reintegration Map."
    )
```

### What Section 4 records

```markdown
- **PROJECT-SPECIFIC IMPLEMENTATION GOES HERE** in `src/pkg/domain/scoring.py:business_specific_scoring_rule` — bind the firm's proprietary scoring rule; must return a bounded `[0,1]` float, must be monotonic on feature dominance, must be deterministic.
```

---

## Emission rules

1. **One marker per adaptation seam, not per line.** A function body that has five branches all binding to the same private system gets one marker at the top with the contract, not five interleaved markers.

2. **Marker at the declaration, comment-echo at the body.** The docstring (or block comment in languages without docstrings) carries the full marker + contract. A short inline comment at the exact point of substitution echoes the marker kind, so a reader skimming the body immediately sees the seam without re-reading the doc.

3. **Contract on the marker.** Every marker is followed by a short description of what the downstream binding must preserve: signature, type, shape, determinism, idempotency, error-handling behaviour. Vague markers ("this needs the real implementation") are useless at bind time.

4. **No marker without a row in the Reintegration Map.** Section 4 enumerates every marker; Section 6 gives each one a full row with the six columns. If the marker isn't in both, fix it.

5. **Mixed markers are allowed.** A module can have a `USER-INTEGRATION REQUIRED` adapter at the top and a `PROJECT-SPECIFIC IMPLEMENTATION GOES HERE` policy rule further down. They are independent seams with independent contracts.

---

## Anti-patterns

- **Bare `TODO` / `FIXME` / `XXX`.** Not a marker — the validator will flag and the reader has no way to navigate.
- **Silent `pass`.** Worst kind of leak: the scaffold looks complete but silently does nothing at the bind site. Always raise or return something observable from an unimplemented marker, and label it.
- **Marker in a comment that isn't adjacent to the seam.** A marker 20 lines away from the actual bind site is lost.
- **Marker without contract.** "USER-INTEGRATION REQUIRED: bind this" is useless. The marker carries the contract, not just the flag.
- **Over-marking.** If the body is genuinely generic and reusable as-is, don't mark it. Markers are reserved for seams where **private material must later enter the code**. Marking trivial helper functions pollutes the Reintegration Map and teaches the binder to ignore markers.
- **Under-marking.** If the body is quietly carrying a domain assumption, mark it. A scaffold that omits markers because "the generic implementation looks fine" is a scaffold that fails at bind time because the binder didn't realise something was coupled.

---

## Grep-friendliness

The markers are designed to be machine-parseable with one line of grep:

```bash
grep -RnE '(USER-INTEGRATION REQUIRED|ADAPTATION POINT|PROJECT-SPECIFIC IMPLEMENTATION GOES HERE)' src/ tests/
```

This is how the `validate_scaffold.py` script enumerates markers to cross-check against Section 4 of the artefact, and how a downstream binder finds every seam at bind time. Keep the strings exact — no punctuation variations, no Spanish translations, no paraphrasing. Consistency across scaffolds is the whole point.

---
name: pricing-pipeline-doctrine
description: Enforce the PricingLab four-layer chain (MarketServices → Model → PricingAlgorithm → Product), MeasureSpec discipline on every algorithm, the eight-field calibration provenance bundle, and Roper static no-arbitrage on every smile interpolator. Use this skill whenever the user says "review this pricer", "audit this calibration", "is this pricing run compliant", "check the four-layer chain", "verify provenance", "is the smile arbitrage-free", "does this satisfy repricing closure", "is the numeraire declared", or whenever a user proposes a change that touches L1–L17 of the PricingLab architecture, a `CalibratedModel`, a `Surface`, an `AlgorithmSpec`, or a `PricingPlan`. The skill never writes pricing code itself — it certifies that proposed code respects the doctrinal contract before any implementation specialist runs. Do NOT trigger for (a) running a pricer end-to-end (use /price); (b) running a calibration (use /calibrate); (c) authoring an ADR (pricing-architect); (d) writing scholar documentation (scholar-quant-docs).
license: Proprietary. OmarOS internal.
contract_invariants:
  - "Four-layer chain. Every artefact under review is classified as living in MarketServices (L1–L7), Model (L8–L11), PricingAlgorithm (L13–L15), or Product (L12). A change that bridges layers in the wrong direction (e.g. a Product that imports a curve, an Algorithm that mutates a Model) is flagged as a layer-boundary breach."
  - "MeasureSpec discipline. Every Algorithm, every PricingPlan, every CalibratedModel under review carries a typed Numeraire / MeasureSpec field. A Price without a declared measure is rejected — never warned. The change-of-measure (Radon-Nikodym) chain to the production measure is part of the artefact when calibration measure ≠ production measure."
  - "Calibration provenance. A CalibratedModel under review must carry the eight provenance fields: market_state_hash, instrument_set, loss_spec, optimiser_spec, residual_surface, convergence_trace, calibration_timestamp, bundle_hash. Missing any field → not a CalibratedModel. The bundle is BLAKE3-hashed canonically (ADR-0023)."
  - "Repricing closure. Every CalibrationSpec carries a production_algorithm_id; that id must equal the algorithm dispatched at production. A reviewer that detects calibration_algorithm ≠ production_algorithm without an explicit waiver flags RepricingClosureViolation."
  - "Roper static no-arbitrage. Every Surface / SmileFit under review carries a Roper certificate covering calendar (∂_T w ≥ 0), butterfly (Gatheral g(k) ≥ 0), and vertical (put-call parity) on a fine grid. Penalty methods are forbidden — Roper conditions are hard constraints, not soft penalties. A surface without a certificate is not a Surface."
  - "Discounting separation. The discount factor D(t,T) lives in MarketState. A Payoff that takes a `risk_free_rate: float` constructor argument or hard-codes a D(t,T) literal fails review (doctrine non-negotiable #1)."
  - "Multi-asset correlations are extracted, not assumed. Any artefact under review that ships a correlation tensor must declare its estimator (Hayashi-Yoshida, Ledoit-Wolf shrinkage, graphical lasso). Sample covariance on d ≳ N/2 fails the conditioning gate."
  - "Read first, certify second. The skill never issues a verdict without reading: (i) the relevant Vision document(s) under 05_Projects/QuantOS/Labs/PricingLab/Vision/ or the local mirror under docs/vault/labs/pricinglab/; (ii) the artefact under review; (iii) the calibration provenance bundle when applicable; (iv) the audit category outputs when a CertifiedResult is in scope."
  - "Verdict alphabet. Every certification produces one of: CERTIFIED (all gates pass), PROVISIONAL (gates pass with ≥ 1 acknowledged calibration failure mode + model-risk markdown), REJECTED (any gate fails or unacknowledged failure mode). PROVISIONAL is never a free pass."
  - "Math is real. Every claim about a measure change, a no-arb condition, or a calibration objective is stated with proper notation. Obsidian MathJax: $...$ inline, $$...$$ display. Never \\(...\\) or \\[...\\]."
  - "Cite doctrine. Every flagged issue cites the specific Vision section that the artefact violates: 00_Doctrine §N, 01_Architecture §LM, 02_Calibration_Model §K, 05_Invariants §I-X, 08_Smile_Interpolators §J. Vague citations are not acceptable."
  - "Scholar voice. No 'this looks robust'; instead 'this satisfies invariant I-X because Y'. No 'this seems arbitrage-free'; instead 'the Gatheral g(k) certificate is present on a 401-strike grid; minimum value 0.012'."
---

# Pricing Pipeline Doctrine

Doctrinal enforcer for PricingLab. The skill is short. Its job is to certify that an artefact under review respects the four-layer chain, MeasureSpec discipline, calibration provenance, and Roper static no-arbitrage — *before* any implementation specialist runs.

The substantive content lives in the Vision corpus at `~/OmarOS/05_Projects/QuantOS/Labs/PricingLab/Vision/`, mirrored under `docs/vault/labs/pricinglab/`. The skill loads the doctrine; the doctrine enforces the contract.

## When to invoke

Trigger when the user asks for any of:

- "review this pricer / pricing run / calibration / smile fit"
- "audit this calibration"
- "is this pricing run compliant"
- "check the four-layer chain"
- "verify provenance"
- "is the smile arbitrage-free"
- "does this satisfy repricing closure"
- "is the numeraire declared on this algorithm"

Do **not** trigger for: running a pricer end-to-end (`/price`); running a calibration (`/calibrate`); authoring an ADR (use `pricing-architect`); generating scholar documentation (use `scholar-quant-docs`).

## Protocol (in order)

1. **Locate doctrine.** Read `00_Doctrine.md`, `01_Architecture.md`, `02_Calibration_Model.md`, `05_Invariants.md`, `08_Smile_Interpolators.md` — the canonical Vision in OmarOS, or the local mirror.
2. **Locate artefact.** Resolve the artefact under review (a PR, a code path, a `CalibratedModel`, a `Surface`, a `PricingRun`).
3. **Layer classification.** Place the artefact at exactly one of L0–L18. Reject layer-boundary breaches with the cited reverse-import.
4. **Run the four gates** (in order):
   1. **Measure gate.** `MeasureSpec` declared? Numeraire compatibility predicate satisfied across (Algorithm, Model, Product)?
   2. **Provenance gate.** Eight calibration fields present? `calibration_hash` resolves?
   3. **Closure gate.** `production_algorithm_id` set? Equals the dispatch target?
   4. **No-arb gate.** Roper certificate on the surface? Calendar / butterfly / vertical pass on a fine grid?
5. **Failure-mode catalogue.** Run the §12 diagnostics (Heston Feller, SABR wings, HW1F mean-reversion, BGM caplets, rough-vol Hurst, PSD, ITM/OTM).
6. **Verdict.** `CERTIFIED` / `PROVISIONAL` / `REJECTED` with cited section refs.

## What the skill never does

- Write production pricing code (that is `model-architect`, `calibration-engineer`, `algorithm-router`, `product-builder`).
- Issue verdicts without reading the Vision and the artefact.
- Treat a Roper violation as a warning.
- Permit a `CalibratedModel` missing any of the eight provenance fields.
- Permit `calibration_algorithm ≠ production_algorithm` without an explicit logged waiver.

## Cross-references

- Doctrine: `docs/vault/labs/pricinglab/00_Doctrine.md`.
- Architecture: `docs/vault/labs/pricinglab/01_Architecture.md`.
- Calibration: `docs/vault/labs/pricinglab/02_Calibration_Model.md`.
- Invariants: `docs/vault/labs/pricinglab/05_Invariants.md`.
- Smile interpolators: `docs/vault/labs/pricinglab/08_Smile_Interpolators.md`.
- ADRs: ADR-0010 (Cap'n IR), ADR-0017 (AAD), ADR-0018 (rough paths), ADR-0020 (shared substrate), ADR-0023 (BLAKE3 audit DAG).

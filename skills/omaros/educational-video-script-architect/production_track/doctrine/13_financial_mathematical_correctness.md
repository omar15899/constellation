# 13 — Financial & Mathematical Correctness

When the topic is quantitative, the visual must respect the quantitative content. Sign conventions, FX directions, compounding choices, and shock magnitudes are part of the explanation, not stylistic flourishes. Getting them wrong undermines the entire video.

This doctrine is invoked whenever a shot involves valuation, risk, basis / CIP, FX conversion, present-value computation, or any quantitative claim. The visual director and animation_spec agent are responsible for filling the relevant block in the shot spec; the implementer is responsible for honouring it.

## Valuation shots

For any shot that depicts present-value calculation, swap value, or cashflow valuation:

```yaml
valuation:
  cashflow_direction: receive_EUR_pay_USD   # who receives what
  discount_currency: EUR                     # which curve discounts EUR legs, which discounts USD legs
  fx_conversion_direction: USD_to_EUR_at_spot_S
  sign_convention:
    PV_positive_means: "we are owed value"
    PV_negative_means: "we owe value"
  perspective: receiver_of_EUR_leg           # whose book are we drawing
  PV_sign_in_this_shot: positive             # explicit
  notionals_included: false                  # is the principal exchange part of the PV shown
  accrued_payments_included: false           # is the most recent unpaid coupon included
  value_classification: illustrative         # exact | illustrative | stylized
```

The implementer reads this block before drawing a single bar. The colour of the bar (`EUR_BLUE` for EUR legs, `USD_AMBER` for USD legs), its sign (above or below the axis), and the formula it eventually morphs into all derive from these choices.

## Risk shots

For any shot that depicts a DV01, sensitivity, or duration concept:

```yaml
risk:
  shocked_curve: EUR_OIS
  shock_size_bps: 1
  shock_shape: parallel       # parallel | non_parallel | KR(<bucket>)
  currency_of_DV01: EUR
  conversion_convention: |
    DV01 reported in EUR.
    For USD shock equivalence, DV01 USD = DV01 EUR × FX_spot.
  sign_convention:
    positive_DV01_means: "PV rises when rates rise"
  expected_qualitative_direction: |
    A 1 bp parallel shock to EUR OIS reduces PV_EUR by DV01_EUR.
    Visually, the EUR bar should shorten by an amount proportional
    to DV01_EUR; the BASIS_RED indicator on the swap value should
    move downward.
```

If the shock is non-parallel (steepener, flattener, key-rate), the spec names the affected buckets explicitly. The animation must show the buckets that move, not a generic curve-rotation.

## Basis / CIP shots

For any shot that depicts cross-currency basis, CIP, or the forward FX market:

```yaml
basis_cip:
  spot_convention: USD_per_EUR        # 1.08 means 1.08 USD per 1 EUR
  forward_convention: same_as_spot
  compounding: continuous              # continuous | simple | discrete_with_day_count
  basis_leg: USD_leg                   # which leg receives the basis spread
  basis_sign_convention:
    negative_basis_means: |
      The USD leg pays Libor + spread where the spread is *negative*,
      i.e., the USD borrower pays less than Libor — a discount to the
      US borrower for funding via the EUR side.
    convention_note: |
      Market convention quotes EUR/USD basis as negative for "USD funding
      via EUR is cheaper than via USD itself". This matches the spec.
  market_vs_pedagogical_convention: |
    Market convention quotes the basis on the EUR-leg side of an
    EUR/USD swap. This is also our pedagogical convention. No reversal.
```

Sign conventions on the basis are *the* easy place to introduce a misconception. The visual must match the convention declared in the spec — including which curve sits above which, which colour carries which sign of the spread, and what a "negative basis" looks like.

## What the visual must reflect

For every quantitative shot:

- **Sign on the axis.** Above-axis vs below-axis must correspond to the declared sign convention. A bar that the spec calls "positive PV" appears above the axis.
- **Direction of arrows.** Cashflow arrows point from payer to receiver per the declared convention. An arrow that points the wrong way visually inverts the perspective.
- **FX conversion direction.** When a USD quantity is converted to EUR, the visual flow shows USD → EUR (with the converter in between). The opposite direction is a different operation and must look different.
- **Order of magnitude.** Illustrative values that are an order of magnitude off (a 1 bp shock drawn as if it were a 100 bp shock) are rejected even when labelled "illustrative" — illustrative ≠ wrong-scale.

## Value classification

Every numeric value in the spec must be classified:

- **exact** — taken from a verified source, must be cited in the data manifest.
- **illustrative** — chosen by the visual director to clarify the shape of the relationship, not a real market value. The shot's annotations must not imply otherwise.
- **stylized** — deliberately rounded or simplified for visual clarity (e.g., a basis of "-30 bps" when the real-world value oscillates around -27 bps in the relevant period).

The render_review agent rejects shots that show "real-looking" tickers when the underlying values are illustrative without a label clarifying that, and rejects shots that show stylized values without acknowledging the simplification.

## Why this matters

A video whose visuals look polished but whose quantitative content is wrong is the worst kind of failure mode: it teaches the wrong thing convincingly. The doctrine is to *front-load* the conventions into the spec, where they are reviewable, and forbid the implementer from making them up on the fly. The implementer's job is to render the convention; the visual director's job is to *choose* the convention.

# 07 — Registered Metaphors

## The rule

**A metaphor is allowed only if it appears in the conceptual blueprint or has been explicitly approved. Casual metaphor invention is forbidden.**

Visual metaphors are the load-bearing pedagogical move of this medium. A good metaphor compresses the concept; a bad one introduces a misconception that survives the video. Because the consequences are asymmetric, metaphors are *registered* like APIs, not improvised like prose.

## The registered metaphor catalogue (canonical seed)

This catalogue is the seed; project-specific blueprints may extend it (with the approval procedure below). The catalogue is the surface contract between the visual director and the implementer.

| Metaphor | Maps to |
|---|---|
| rivers / pipes | currency cashflow streams |
| mechanical lock | fixed notional re-exchange |
| shrinking arrows | discounting to present value |
| bars | present values |
| coupled turbines | opposing DV01 sensitivities |
| tightrope / cable | CIP equilibrium |
| gravity field | global dollar funding pressure |
| EKG | cross-currency basis as systemic stress signal |
| valve | central bank swap line intervention |

Each entry has a corresponding component in `11_manim_component_library.md` (`PipeSystem`, `LockedNotionalExchange`, `DiscountArrow`, `PresentValueBar`, `CoupledTurbines`, `CIPTightrope`, `DollarGravityField`, `BasisEKG`, `FedSwapValve`).

## What counts as introducing a new metaphor

A new metaphor is introduced whenever the visual director proposes a *non-trivial physical or structural analogy* between the financial / mathematical concept and a non-financial / non-mathematical visual. Examples that count as new metaphors:

- "The yield curve is a spring."
- "The repo market is a heart."
- "The dealer balance sheet is a battery."
- "Volatility is weather."

Examples that do *not* count as new metaphors (they are mathematical depictions, not analogies):

- "The yield curve is plotted as a smooth line in (tenor, rate) space."
- "The repo rate is a number that fluctuates over time."

## Approval procedure for a new metaphor

If a shot needs a metaphor that is not in the registered catalogue, the visual director must, before specifying the shot, propose the metaphor explicitly:

```yaml
proposed_metaphor:
  name: spring_yield_curve
  conceptual_mapping:
    spring rest length ↔ neutral term structure
    spring compression ↔ inversion
    spring extension ↔ steep curve
    spring restoring force ↔ mean-reverting dynamics
  pedagogical_purpose: |
    Make the viewer feel that a yield-curve inversion is a *state*, not a *number*,
    and that something is being held against equilibrium.
  visual_form: a vertical spring drawn between two reference horizontal planes; compression / extension animates as the curve evolves
  risk_of_misconception: |
    Risk: a viewer may believe yield-curve dynamics are physically restorative when
    they are economically restorative (regime-dependent). Mitigation: a labelled
    boundary scene that explicitly names this as analogy, not mechanism.
  approval_status: pending  # → approved | rejected
```

The metaphor is recorded in `01_conceptual_blueprint.md` §"Registered metaphors" and added to the catalogue table here in subsequent versions of the skill. Until approved, no shot may rely on it.

## Why this matters

A casually invented metaphor has three failure modes:

1. **It is structurally wrong.** The cute analogy maps the wrong feature of the concept. The viewer learns the analogy and inherits the wrong intuition.
2. **It is internally inconsistent.** The visual director uses "the river" metaphor for cashflow in one scene and "the road" metaphor for cashflow in another. The viewer cannot tell whether the two visualisations are the same concept or two different concepts.
3. **It is unbacked by a component.** The metaphor exists only as a one-off drawing in scene code. It cannot be re-used, cannot be made consistent across shots, cannot be morphed or extended.

Registration solves all three: the metaphor is reviewed before it ships, it is named in the blueprint so it can be referenced by all later shots, and it has a component implementing it.

## What the implementer does

When the spec calls for a registered metaphor, the implementer uses the corresponding component from the library. If the component does not yet exist, the implementer surfaces this through the component_architect role — proposing a constructor signature and animation methods, getting them reviewed, then implementing the scene that uses them. The implementer does not improvise the metaphor on the fly.

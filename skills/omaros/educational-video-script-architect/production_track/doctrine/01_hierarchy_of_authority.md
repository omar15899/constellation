# 01 — Hierarchy of Authority

When two layers of the production stack conflict, the higher one wins. The hierarchy is the load-bearing rule that prevents convenient implementation choices from corrupting the explanation.

## The stack

```
1. Conceptual truth          ← what the concept is, mathematically / scientifically
2. Pedagogical objective     ← what the viewer must come to recognise
3. Scene function            ← what this scene must accomplish in the arc
4. Narration timing          ← what is being said when
5. Visual language           ← palette, motion vocabulary, semantic registers
6. Shot specification        ← composition + cognitive purpose of one visual unit
7. Animation specification   ← exact movement, position, colour, easing
8. Implementation code       ← the Manim file that renders the shot
```

Higher numbers are subordinate to lower numbers. **Code is the lowest layer. The concept is the highest layer.** A convenient implementation choice may never violate the conceptual or pedagogical layer.

## What this means

If the implementation tempts you to draw the basis gap as a *negative spike* because it is easier to render, but the conceptual blueprint says the basis is a *gap between two curves*, the conceptual layer wins. Refactor the implementation, propose a new component, or report `MISSING_SPEC` — but do not silently rewrite the metaphor in code.

If the visual language fixes EUR objects as `EUR_BLUE`, and you discover at implementation time that the EUR bar in this shot would have better contrast in white, the visual language wins. Whatever you gain in local contrast you lose in semantic consistency across the entire video.

If the shot spec calls for a `CashflowArrow` of length proportional to the cashflow magnitude, and the data manifest says today's value is 75 bps but illustrative scaling would put it off-screen, the data layer is consulted (is this exact or illustrative?), the shot spec is consulted (what's the canvas scale?), and the *spec* is adjusted — the code does not silently rescale to keep the arrow on screen.

## Resolution protocol

When a conflict surfaces during implementation:

1. **Name the conflict.** State which two layers disagree and how.
2. **Identify the higher layer's decision.** Quote the relevant sentence from the higher-layer file.
3. **Either implement the higher layer's decision** (potentially harder, but correct), **or** propose an amendment to the higher layer and stop implementing until it is reviewed.
4. **Never** edit the lower layer alone to escape the higher layer's constraint. That is silent drift.

## A worked case

> The implementer notices that drawing the `LockedNotionalExchange` mechanism (registered metaphor: mechanical lock = fixed notional re-exchange) requires three nested groups and tedious frame-by-frame animation. The implementer wonders if a simpler "double-headed arrow" would suffice.

**Resolution.** The metaphor is registered (see `07_registered_metaphors.md`) in the conceptual blueprint. A double-headed arrow is *not* the same metaphor — it implies bidirectional flow, not a one-shot re-exchange of identical principals. The conceptual layer wins. The implementer either (a) implements the lock, possibly creating a new reusable component in the library, or (b) emits `MISSING_SPEC` arguing that the lock metaphor is too expensive and proposing an alternative metaphor in writing — but does not unilaterally swap the visual.

## A second worked case

> The implementer notices that the `09_animation_spec.yaml` for shot IP-S2-F03 specifies `easing: ease_out_cubic` for the cashflow arrow but the previous shot used `ease_in_out_quad`. Implementing both feels inconsistent.

**Resolution.** Inconsistency *across shots* is the kind of thing the spec resolves deliberately. The implementer either (a) implements both easings as specified, (b) checks `04_visual_language.md` for a global easing policy, or (c) reports the inconsistency to the animation spec agent as a possible spec defect — but does not unify them in code on their own authority.

## The point

The hierarchy is not bureaucracy. It is what keeps the explanation coherent across hundreds of decisions made by potentially many agents. Code that silently overrides the spec corrupts the explanation in a way that is invisible at the file level and only visible in the finished render, by which point fixing it is expensive.

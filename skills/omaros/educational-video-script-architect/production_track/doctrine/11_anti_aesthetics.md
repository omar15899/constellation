# 11 — Anti-Aesthetics

## The rule

**Reject "generic AI aesthetics" ruthlessly.** Be specific about what the output should *not* look like. Be specific about what it *should* look like.

This is the doctrine of taste. It is the hardest to enforce because the failures are often technically correct — the code compiles, the colours are in the palette, the durations match the spec — but the output still looks like every other AI-produced fintech video. The cure is to name the failure modes explicitly and refuse them.

## What to refuse

Outputs that look like:

- **Generic corporate explainer.** Soft-edged cartoon icons. A narrator-style avatar. Faux-friendly typography. Background music that sounds like a hold queue.
- **Stock-market YouTube intro.** Ticker tape with random green/red numbers scrolling. A skyline of glass towers. An exaggerated chart with an arrow climbing the upper-right.
- **Crypto promo.** Neon gradients. Floating coins. Particle bursts around a logo. The colour palette of a casino.
- **PowerPoint with animations.** A title at the top, bullet points in the middle, a chart at the bottom. Transitions that "wipe" or "spin". The frame stays static for most of each shot.
- **Randomly glowing fintech dashboard.** Multiple panels, each glowing at a different intensity, with sparkline charts in each. No focal point.
- **Meaningless particle field.** Dots floating in the background. Lines connecting dots randomly. The "network" or "data" aesthetic without any actual data.
- **Excessive neon finance collage.** A montage of dollar signs, candlestick charts, hexagonal networks, and abstract code — all simultaneously.
- **Visually impressive but pedagogically empty montage.** A shot that wows the eye but, when read for content, says nothing.

If a render looks like any of the above, it is rejected regardless of whether the formal rules (palette, motion vocabulary, sync) check out. The formal rules are necessary, not sufficient.

## What to prefer

Outputs that look like:

- **Precise mathematical animation.** In the lineage of 3Blue1Brown: clean lines, semantic colour, one diagram on screen at a time, continuous parametric motion, formulas built term-by-term from visible quantities.
- **Institutional financial visualization.** In the lineage of *Bloomberg Terminal* or *the Yield Book*, but reframed as explanation rather than tool: precise tickers, dense numeric labels in monospace, dark background, deliberate composition, no decoration.
- **Cinematic but restrained data display.** A field of data shown with weight and gravitas — not "exciting" data, real data with high information density and minimal ornament.
- **Carefully staged conceptual mechanism.** The `LockedNotionalExchange`, the `CoupledTurbines`, the `FedSwapValve` — drawn as if they were illustrations from a precise physics textbook, with labels naming the parts and an implied mechanism the viewer can follow.
- **High-end educational diagram.** What a publication-quality figure would look like if it were animated: axes, labels, an object, a relationship, and one transformation revealing the structure.
- **Clean 3Blue1Brown-level abstraction with stronger financial texture.** Retain the abstraction discipline; add the institutional / financial register where it earns its place.
- **Quantum Fracture-style narrative energy when appropriate, but without visual chaos.** Big-stakes framing, dramatic reveals, cinematic pacing — without the visual clutter of an entertainment-first explainer.

## How to apply this in practice

At spec time, the visual director writes a `style_reference` field per scene (or per shot, when shots within a scene have different registers):

```yaml
style_reference:
  positive_anchor: "3Blue1Brown — Essence of Linear Algebra, chapter 1, the linear-combination scene at 02:14"
  negative_anchor: "a generic crypto-explainer with floating coins"
  register: precise_mathematical_animation
  permitted_textures:
    - dense numeric tickers in monospace, NEUTRAL_GREY on DEEP_BACKGROUND
    - hand-drawn-feel curve roughness disabled (smooth Bezier)
  prohibited_textures:
    - particle backgrounds
    - logo / brand watermark
    - dropshadow on text
    - gradient fills on bars (use flat semantic colour)
```

The render_review agent uses the `negative_anchor` and `prohibited_textures` as part of the rejection criteria. The implementer reads the positive anchor as a quality target.

## The hard discipline

It is harder to refuse a technically-correct-but-generic render than to refuse a render with an outright bug. The temptation is to say "it works — ship it". The doctrine of taste exists to make that temptation unavailable. The video either looks like institutional / educational work of the kind it aspires to be, or it does not ship in this form.

If a render passes every formal check and still looks like a stock-market YouTube intro, the right move is to revisit the spec — the composition, the typography choices, the motion design — and refine. The fault is in the spec, not in the discipline of taste.

# CSS Systems Reference

CSS is a real engineering discipline. The quality of the CSS determines the stability and legibility of the interface. This document covers how to think about CSS as a system, how to use Tailwind well, and how to make layout decisions that hold.

---

## CSS as a system

### The spacing scale

Never introduce a pixel value that does not belong to the spacing scale. Ad-hoc spacing is the first sign that CSS is becoming a pile of patches.

- **For Helix:** 4px base unit. All gaps, paddings, and margins are multiples of 4 (4 / 8 / 12 / 16 / 24 / 32 / 48).
- **For Tailwind projects:** Use the Tailwind spacing scale exclusively. `gap-3` (12px) is fine. `gap-[13px]` is a smell — find the nearest scale value.

When you want 5px and the scale says 4 or 8: the answer is almost never 5px. Either 4 is correct and you are looking at it wrong, or something upstream is wrong and you should fix that instead of papering over it with a magic number.

### Visual hierarchy

CSS should express hierarchy deliberately. The reader's eye should land on the most important information first. Enforce this through:

- **Size contrast** — important text is larger, supporting text is smaller. Maintain a clear size ratio between levels.
- **Color contrast** — primary information is `--text-primary`, supporting information is `--text-secondary`, metadata is `--text-tertiary`. Do not reuse the same color for everything and expect hierarchy to emerge.
- **Weight contrast** — use font weight sparingly. A page where everything is `font-medium` has no hierarchy. Reserve bold for the thing that must be noticed first.
- **Spatial grouping** — related items are close together. Sections are separated by space, not just borders. The gap between groups should be larger than the gap within groups.

### Layout primitives

Prefer declarative layout over positional tricks.

**Flexbox** — for one-dimensional arrangements (rows, columns) where items flow naturally. Do not use flexbox to make a grid — that is what grid is for.

**CSS Grid** — for two-dimensional layouts, template areas, and structured panels. Grid areas are more readable and more maintainable than nested flex containers.

**Normal flow** — for content that should read top-to-bottom. Block elements in normal flow rarely need help. If you find yourself fighting the normal flow, you are probably making it worse.

**Avoid:**
- `position: absolute` for layout that should be responsive. Absolute positioning is for elements that need to escape their context (tooltips, dropdowns, overlays).
- `margin: auto` tricks that obscure what the layout is doing.
- Negative margins to correct for something that should have been laid out differently.
- Hardcoded `width` and `height` on container elements. Let content determine dimensions, constrain with `min-`/`max-`.

### State styling

Every interactive element has visual states: default, hover, focus, active, disabled. CSS should express all of them, not just the default.

- Focus states must be visible. Do not `outline: none` without providing a replacement. Keyboard users rely on focus indicators.
- Disabled states must look disabled — not just inactive. `opacity: 0.5` alone is not enough; the cursor should also communicate the state.
- Hover states should respond immediately (no transition delay) but can transition out smoothly.

### Motion restraint

Animation should communicate information, not decorate. Before adding a transition or animation, answer: what does the user learn from seeing this move?

- **Acceptable:** a drawer sliding in (communicates spatial relationship), a spinner (communicates loading), a value flashing (communicates change).
- **Not acceptable:** a button that grows on hover (no information conveyed), a page that fades in from nothing (costs time, provides nothing).

Use `prefers-reduced-motion` for any animation that is purely aesthetic.

---

## Tailwind craft

Tailwind is a tool. It produces good results when used systematically and poor results when used as a grab-bag of utilities.

### Class organization

Group utilities in a consistent order so class strings are scannable:

```
layout → spacing → sizing → typography → color → border → state/interaction
```

Example:
```html
<div class="flex items-center gap-3 px-4 py-2 w-full text-sm font-medium text-gray-200 bg-gray-800 border border-gray-700 rounded hover:bg-gray-750 focus:ring-1 focus:ring-blue-500">
```

The reader's eye can scan: "flex row, 12px gap, padded, full-width, small medium text, dark background, subtle border, rounded, hover darker, focus ring."

### Extraction signals

Extract a cluster of utilities when:
- The same cluster appears in 3+ places and represents the same concept
- The cluster is long enough that it obscures the component's structure
- The concept has a name in your domain (e.g., "pill badge", "data cell", "panel header")

Where to extract:
- Into a React component — for HTML + utility combinations that represent a reusable UI element
- Into a Tailwind `@apply` class — for styling patterns applied to HTML elements that can't be easily componentized (e.g., prose styles, table cells)
- Into a `className` helper — for conditional class assembly (`clsx`, `cn`)

Do not extract because a class string is long. Extract because a concept is repeated.

### Avoiding utility overload

A component that renders 40 utility classes on a single element is hard to read and hard to modify. Signals that the abstraction is missing:

- You cannot describe what the element is in one sentence
- The same element appears with the same 20 classes in multiple files
- Developers avoid touching the class string because it's fragile

In these cases, the right answer is a component, not more utilities.

### Responsive design

Tailwind's breakpoint prefixes (`sm:`, `md:`, `lg:`) should follow a consistent strategy:

- **Mobile-first by default** — base classes apply to small screens; breakpoint prefixes add or override for larger screens.
- **Coherent breakpoints** — pick 2–3 breakpoints and use them consistently. Do not introduce `sm:` overrides in one component and `lg:` overrides in another for the same layout concern.
- **Layout changes, not cosmetic changes** — responsive breakpoints should change structure (column → row, hidden → visible, 1-col → 2-col). Font size differences of 1-2px are not a layout concern.

### Dark mode

If the project uses Tailwind's dark mode, apply it consistently:
- Use semantic token names (`bg-surface`, `text-primary`) via CSS variables rather than explicit `dark:` prefixes on every element.
- Reserve `dark:` prefixes for exceptions, not the rule.

---

## CSS custom properties (design tokens)

CSS custom properties are the correct mechanism for design system values. They allow:
- Consistent values across the entire stylesheet
- Runtime overrides (theming, user preferences)
- Readable names in the stylesheet (`--text-primary` vs. `#e2e8f0`)

### Rules

- **Never hardcode a design system value.** Colors, font sizes, border radii, spacing scale — all of these belong in the `:root` block, referenced via `var(--token)`.
- **Token names should be semantic**, not literal. `--text-primary` is semantic. `--gray-200` is literal. Literal tokens are fine as primitives, but component-level usage should be semantic.
- **Scope tokens to their context.** A token that only makes sense inside a table does not belong in `:root`. Use component-scoped custom properties.
- **Document the contract.** If you add a new token to the design system, its name should make its purpose obvious without a comment.

---

## Common mistakes

**Fighting the cascade.** Adding `!important` to fix a specificity problem is a sign that the CSS architecture has a problem. Fix the specificity, do not paper over it.

**Over-nesting.** BEM had a reason for its naming conventions; CSS-in-JS has a reason for scoped styles. In vanilla CSS, deeply nested selectors create specificity that is hard to override and hard to reason about. Prefer flat selectors with meaningful class names.

**Using JS for layout.** If you are computing element dimensions or positions in JavaScript to position other elements, there is almost certainly a CSS layout primitive that does this correctly. `position: absolute` + JS measurement is the wrong answer for 90% of the cases that reach for it.

**Transitions on all properties.** `transition: all 0.2s` is a performance and visual hazard. Only transition properties that you intend to animate, and only on elements that actually have hover/focus/active states.

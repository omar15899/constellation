---
name: frontend-design
description: Reviews, plans, and refines the visual design, layout, and UX of the Helix trading interface. Use this skill when evaluating visual consistency, proposing layout changes, designing new pane arrangements, auditing the design system for drift, implementing UI refinements (spacing, typography, color), or deciding between layout patterns. Trigger on: "how should this look", "design a layout", "review the UI", "is this consistent", "what color/spacing should I use", "redesign [pane/section]", "audit the design system".
---

# Frontend Design

Design decisions and visual refinements for the Helix trading interface.

## Design Philosophy

This is an **institutional trading terminal**, not a consumer product.

**Canonical design language:**
- Dense: 9–13px text, 1px hairline borders, 4–8px gaps
- Dark graphite: deep background, subtle raised surfaces, no pure black
- Functional: every visual element carries information — no decoration
- Precise: numbers are always monospace, always right-aligned
- Consistent: source badges on every pane, always color-correct

**Anti-patterns to reject:**
- Rounded corners on data tables (trading terminals use sharp corners)
- Color gradients in data areas
- Large whitespace margins
- Consumer typography (Inter, system-ui, -apple-system)
- Centered layouts (left-aligned is canonical)
- Drop shadows (use border-hairline instead)

## Design System Reference

**Always read the `:root` block in `src/styles/helix.css` before proposing any change.** The token set is authoritative.

### Layout constants

| Element | Height |
|---|---|
| TopBar | 40px |
| ContextBar | 32px |
| StatusBar | 22px |
| Pane header | 28px |
| Rail width | 48px |
| SideDrawer width | 320px |
| TweaksPanel width | 280px (float) |
| Min row height | 120px |
| Min col width | 180px |

### Spacing grid

Always multiples of 4px: 4 / 8 / 12 / 16 / 24. Never 5px, 7px, 10px, 15px.

### Typography scale

| Use | Size | Font | Weight |
|---|---|---|---|
| Pane title | 11px | IBM Plex Sans | 500 |
| Label / body | 10–11px | IBM Plex Sans | 400 |
| Compact label | 9px | IBM Plex Sans | 400 |
| Numeric value | 10–12px | IBM Plex Mono | 400/500 |
| Source badge | 9px | IBM Plex Sans | 500 |
| Status bar | 10px | IBM Plex Mono | 400 |

### Color semantics (non-negotiable)

| Token | Color | Meaning |
|---|---|---|
| `--bid` | green | buy-side, positive delta, long |
| `--ask` | red | sell-side, negative delta, short / loss |
| `--live` | amber | real-time market data only |
| `--internal` | indigo | model output / fair value only |
| `--sim` | purple | simulated / backtested data only |
| `--rec` | cyan | AI/system recommendations only |

These colors carry semantic meaning — never repurpose them.

## Workspace Layouts

### Market (4 columns)
```
| Watchlist (180px) | OrderBook + Depth + Curve + Microstructure (1fr) | FV + Spreads (220px) | Tape + Position (200px) |
```

### Research (3 columns)
```
| ExperimentHeader + Config (320px) | Comparator + PnL + Runs (1fr) | Sensitivity + Diagnostics + Inspector + Console (280px) |
```

### Strategy (4 columns)
```
| StrategyTree (240px) | Valuation + ScenarioCube (1fr) | SensitivitySurface (280px) | Compare + Decomp + Stress (240px) |
```

## Design Review Procedure

1. **Identify the issue:** visual inconsistency, density problem, information hierarchy issue, or layout gap
2. **Check the token:** does a CSS variable already exist for the proposed value?
3. **Propose the change:** give the exact CSS property + value change
4. **Check side effects:** does the change affect other components?

## Common Design Decisions

### Adding a new pane

1. Identify which column it belongs to
2. Check vertical space — stacking vs. tab/toggle pattern
3. Set the correct source badge
4. Ensure pane header height is 28px

### Information density

Three density modes driven by TweaksPanel:

| Mode | Font size | Row padding | Use when |
|---|---|---|---|
| compact | 9px | 2px | Maximum information density (default for trading) |
| normal | 11px | 4px | Standard readability |
| relaxed | 13px | 6px | Presentation / review mode |

### Tab patterns

Use tabs when:
- A panel has 3+ sub-views (like ConfigPanel in Research)
- Vertical stacking would create panels shorter than 120px
- The sub-views are mutually exclusive

Tab strip: 28px height, `--border-hairline` bottom border, active tab uses `--accent` underline.

### When to use each chart type

| Data type | Chart type |
|---|---|
| Time series | SVG line chart |
| Price levels vs. quantity | SVG bar / depth chart |
| 2D parameter sensitivity | SVG heatmap |
| Discrete scenario comparison | SVG bar chart (horizontal or vertical) |
| P&L waterfall | SVG stacked/waterfall bar |
| Spark / mini trend | Inline SVG path (no axes) |

Never: pie charts, donut charts, 3D anything.

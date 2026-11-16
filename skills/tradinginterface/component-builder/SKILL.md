---
name: component-builder
description: Scaffolds and writes new React TSX components for the Helix energy trading interface. Use this skill when adding a new pane, workspace panel, SVG chart, config panel, data table, or heatmap to market.tsx, research.tsx, strategy.tsx, assets.tsx, or shell.tsx. Knows the full design system, Pane wrapper pattern, seeded fake-data generation, hand-coded SVG chart conventions, and CSS variable usage of the project. Trigger on: "add a pane", "new chart", "create a component", "scaffold", "add [name] panel", "add [name] to [workspace]".
---

# Component Builder

Scaffolds new trading UI components following the exact conventions of the Helix codebase.

## Invocation Patterns

| User says | Action |
|---|---|
| "add a [name] pane to the market workspace" | New Pane component in `src/workspaces/market.tsx` |
| "add a [type] chart to [pane]" | SVG chart subcomponent |
| "create a config panel for [feature]" | Tabbed config panel (follow ResearchWorkspace ConfigPanel pattern) |
| "add a [name] table" | Data table following trading table conventions |
| "new workspace for [domain]" | Full workspace component with CSS Grid layout under `src/workspaces/` |

## Step 0 — Read target file first

Always read the target `.tsx` file before writing anything to understand:
- Existing components (avoid name collisions)
- CSS classes in use
- The seeded RNG setup (copy `seed`/`rng` pattern exactly)
- Grid layout structure

## Step 1 — Decide component type

| Type | Name suffix | Wraps in `<Pane>`? |
|---|---|---|
| Workspace panel with title bar | `Pane` | Yes |
| SVG line/area chart | `Chart` | No (subcomponent) |
| SVG heatmap | `HeatChart` or `Surface` | No (subcomponent) |
| Config panel with tabs | `Config` or `ConfigPanel` | Yes |
| Data table | inline in Pane or `Table` | No |
| Full workspace | `Workspace` | N/A (is the parent) |

## Step 2 — Write the component

### Pane wrapper (mandatory for all workspace panels)

```jsx
function MyNewPane() {
  return (
    <Pane title="My Title" source="live" sub="optional subtext">
      {/* content */}
    </Pane>
  );
}
```

Source badge mapping:
- `"live"` → amber — real-time market data
- `"internal"` → indigo — model output, fair value, internal analytics
- `"sim"` → purple — simulated, backtested, hypothetical
- `"rec"` → cyan — system recommendations

### Seeded fake data

```javascript
let seed = 9999; // choose a unique value — each component needs its own seed
const rng = () => { seed = (seed * 1664525 + 1013904223) & 0xffffffff; return (seed >>> 0) / 0xffffffff; };
const prices = Array.from({ length: 60 }, () => 45 + rng() * 10);
```

### SVG line chart

```jsx
function MyChart({ data, width = 300, height = 70 }) {
  const pad = { t: 6, r: 6, b: 14, l: 28 };
  const w = width - pad.l - pad.r;
  const h = height - pad.t - pad.b;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const xs = i => (i / (data.length - 1)) * w;
  const ys = v => h - ((v - min) / (max - min || 1)) * h;
  const d = data.map((v, i) => `${i === 0 ? 'M' : 'L'}${xs(i).toFixed(1)},${ys(v).toFixed(1)}`).join(' ');
  return (
    <svg width={width} height={height} style={{ display: 'block' }}>
      <g transform={`translate(${pad.l},${pad.t})`}>
        {/* grid lines */}
        {[0, 0.5, 1].map(t => (
          <line key={t} x1={0} y1={h * (1 - t)} x2={w} y2={h * (1 - t)}
            stroke="var(--border-hairline)" strokeWidth={1} />
        ))}
        <path d={d} fill="none" stroke="var(--accent)" strokeWidth={1.5} />
      </g>
    </svg>
  );
}
```

### SVG heatmap

```jsx
function HeatChart({ grid, rows, cols }) {
  const cellW = 14, cellH = 9;
  const heat = v => {
    // v in [-1, 1]: negative=ask, positive=bid
    if (v > 0) return `rgba(74, 222, 128, ${Math.min(v, 1) * 0.8})`;
    return `rgba(248, 113, 113, ${Math.min(-v, 1) * 0.8})`;
  };
  return (
    <svg width={cols * cellW} height={rows * cellH} style={{ display: 'block' }}>
      {grid.map((row, r) => row.map((val, c) => (
        <rect key={`${r}-${c}`}
          x={c * cellW} y={r * cellH}
          width={cellW - 1} height={cellH - 1}
          fill={heat(val)} />
      )))}
    </svg>
  );
}
```

### Data table

```jsx
<div style={{ overflowY: 'auto', flex: 1 }}>
  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '10px' }}>
    <thead>
      <tr style={{ position: 'sticky', top: 0, background: 'var(--bg-raised)' }}>
        <th style={{ textAlign: 'left', padding: '3px 6px', color: 'var(--text-secondary)', fontWeight: 500 }}>Name</th>
        <th style={{ textAlign: 'right', padding: '3px 6px', color: 'var(--text-secondary)', fontWeight: 500, fontFamily: 'var(--font-mono)' }}>Value</th>
        <th style={{ textAlign: 'right', padding: '3px 6px', color: 'var(--text-secondary)', fontWeight: 500, fontFamily: 'var(--font-mono)' }}>Δ</th>
      </tr>
    </thead>
    <tbody>
      {rows.map((r, i) => (
        <tr key={i} style={{ borderTop: '1px solid var(--border-hairline)' }}>
          <td style={{ padding: '2px 6px', color: 'var(--text-primary)' }}>{r.name}</td>
          <td style={{ padding: '2px 6px', textAlign: 'right', fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>{r.value}</td>
          <td style={{ padding: '2px 6px', textAlign: 'right', fontFamily: 'var(--font-mono)', color: r.delta >= 0 ? 'var(--bid)' : 'var(--ask)' }}>
            {r.delta >= 0 ? '+' : ''}{r.delta.toFixed(2)}
          </td>
        </tr>
      ))}
    </tbody>
  </table>
</div>
```

## Step 3 — Insert into workspace grid

After writing the component, insert it into the workspace's `grid-template-areas`. Use the existing column structure and add a new row or area as needed.

## Step 4 — Add CSS to src/styles/helix.css

If the component needs new CSS, add it to `src/styles/helix.css` — never inline magic values, never a new stylesheet file.

## Constraints

- Never hardcode hex colors — always `var(--token-name)`
- Never import chart libraries
- Every workspace panel gets a `<Pane>` wrapper
- Seed values must be unique per component (use `seeded` imported from `src/workspaces/market.tsx`)
- Numbers: `textAlign: 'right'`, `fontFamily: 'var(--mono)'`
- TypeScript is required — give props real types, not `any`
- CSS lives in `src/styles/helix.css`; no per-component CSS files

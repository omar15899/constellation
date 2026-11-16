---
name: helix-artisan
description: Core implementation craft skill for the Helix trading interface and modern React/TypeScript frontend engineering. Use whenever the user asks to build, extend, redesign, refactor, or polish any part of the Helix frontend (panes, charts, tables, workspaces, layout, tokens, shell chrome) OR any React/TypeScript/Vite/Tailwind/shadcn/ui application. This is the default engineering standard — it governs how code is inspected, designed, written, refactored, and polished. Trigger on: multi-step UI implementation, component architecture work, frontend refactoring, "clean this up", "architect this", "add [X] with [Y] and [Z]", "refactor [component/module]", "haz que se vea increíble", "construye", "añade", "refina", "rediseña", any serious frontend engineering task where craft and coherence matter, not just compilation.
---

# Helix Artisan

Craftsman-mode implementation skill for the Helix trading interface and serious React frontend engineering. The goal is not to generate code — it is to produce work that is coherent, readable, and ready to ship: correct architecture, strong types, deliberate CSS, semantic markup, and a git history that reads as a narrative of intentional changes.

## Why this skill exists

Frontend work is easy to do poorly. Components balloon with mixed concerns. CSS becomes a pile of exceptions. TypeScript gets used cosmetically. HTML collapses into div soup. The result compiles and looks correct at a glance, but is fragile, hard to read, and miserable to extend.

This skill enforces a different standard: **understand before writing, design before coding, build small, verify, commit one thing at a time.** Every increment should leave the codebase in a state you would be proud to show someone.

For the Helix interface specifically: institutional trading terminals demand the density, precision, and information architecture of professional tools. A stray hex value, a 10px gap, a semantic color misused — these degrade the whole thing. The skill preserves Helix's design language as a hard invariant.

---

## The four phases

Every non-trivial task follows four phases. Do not collapse them.

### Phase 1 — AUDIT

Before writing a single line, read the codebase.

- Map the file structure. Identify where different concerns live. If the placement of new code is ambiguous, resolve it before writing — not after.
- Find existing patterns: component naming, CSS class conventions, data shapes, state locations. New code should read like it was always there.
- Identify inconsistencies, technical debt, and weak abstractions. If you are about to add code to a broken area, surface that to the user before adding more to it.
- Locate the minimal intervention surface. The correct fix is often smaller than it first appears.

For Helix specifically: read `src/styles/helix.css` (at minimum the `:root` block and the style rules for the target area) and the target `.tsx` file end-to-end. Note component names, grid areas, the seeded RNG pattern. A skipped read causes name collisions and reintroduces ad-hoc values.

### Phase 2 — DESIGN

Think about architecture before touching code.

- Decide where the code lives. Which file, which layer, which component boundary.
- Define the prop surface before writing the implementation. A bad API is harder to change later than bad internals.
- Check whether the correct intervention is a refactor, not a patch. If you are about to add code to mask a structural problem, stop and propose the refactor instead.
- For non-trivial additions, state the decomposition plan (3–6 bullets) before writing. This surfaces disagreements early and is cheaper than unwinding bad work.

See `references/frontend_architecture.md` for guidance on layer separation, file structure, and naming.

### Phase 3 — IMPLEMENT

Execute with discipline.

- Write one logical unit at a time. A logical unit is independently commitable and leaves the UI in a coherent state.
- Keep types explicit. TypeScript should express domain knowledge, not just satisfy the compiler.
- Preserve readability at every step. Prefer clear over clever.
- Avoid ad hoc workarounds. If you find yourself fighting the framework or the design system, that is a signal the design is wrong, not a reason for a hack.

See `references/react_typescript_patterns.md` for React and TypeScript craft standards.

### Phase 4 — POLISH

Before committing, make the result feel intentional.

- CSS coherence: spacing consistent with the scale, colors from the token system, layout that holds at edge cases. No magic numbers.
- JSX legibility: clean tree structure, no bloated wrapper chains, readable prop surfaces.
- HTML semantics: correct landmarks, interactive elements that are actually interactive elements, no div-as-button.
- Remove complexity that crept in during implementation. If you added something "just in case," remove it.
- Run the [Aesthetic checklist](#aesthetic-checklist) for Helix work. Run visual verification for any UI change.

See `references/css_systems.md` and `references/jsx_html_guidelines.md` for depth.

### Phase 4b — PLAYWRIGHT GATE (mandatory, non-negotiable)

**Every commit that touches `src/`, `index.html`, or `vite.config*` must pass the full Playwright suite.** This is enforced by the `playwright_gate.py` pre-commit hook — the hook will block the commit if any test fails.

Run manually at any point:
```bash
npx playwright test
```

The suite covers:
- App mounts without JS errors
- Brand chrome visible (`.topbar`, `.ctxbar`, `.brand-name`)
- All three workspace tabs present
- Market/Research/Strategy render and switch without page errors
- Design system invariants: pane headers 28px, topbar 40px, status bar 22px, no transparent backgrounds

**If any test fails, fix the code — not the test.** Tests represent invariants that must hold. The only acceptable edit to `tests/helix.spec.cjs` is adding coverage, not loosening assertions.

---

## Architectural principles

These apply to all work done under this skill, regardless of project.

**Separation of concerns** — UI, application state, domain logic, data access, and persistence are distinct layers. A component that fetches its own data, derives business logic, and renders HTML has three jobs. Give each concern its own home.

**Explicitness over magic** — Hidden coupling is a future debugging session. Prefer explicit data flow: props over ambient context for local state, well-named callbacks over mysterious side effects, typed interfaces over `any` or loose objects.

**Coherent naming** — Names should tell you what something is and where it belongs. A component named `DataWrapper` has failed. `PositionTableRow` has not. File names should match export names. Directory names should match domain boundaries.

**Refactor courage** — When the structure is wrong, fix the structure. Do not add a workaround that patches a symptom. But: refactor only what is necessary. Gratuitous churn for aesthetic reasons is not craft, it is noise.

**Justified abstractions only** — Three similar lines is better than a premature abstraction. Extract a reusable component or hook when duplication is clearly structural and the abstraction is genuinely stable. Do not extract for the sake of feeling organized.

**Future extensibility, not future requirements** — Write code that is easy to change, not code that anticipates every possible change. Avoid accidental complexity.

For detailed guidance: `references/frontend_architecture.md`.

---

## Frontend craft standards

### CSS and Tailwind

CSS is an engineering discipline, not a styling afterthought. The quality of CSS directly determines the quality of the interface.

**As a system:**
- Work within the spacing scale. Never introduce a magic pixel value. For Helix: multiples of 4px. For Tailwind projects: the Tailwind scale.
- Preserve visual hierarchy. The reader's eye should find the most important information first.
- Think in layout primitives (flex, grid, flow) rather than one-off positioning. Fragile absolute/fixed positioning should be rare and clearly justified.
- State styling belongs with the component it describes, not scattered across files.
- Motion should be restrained. Animation earns its presence; it does not decorate.

**Tailwind specifically:**
- Group classes by concern: layout → spacing → typography → color → state. A class string should be readable, not a wall of utilities.
- When the same cluster of utilities appears in 3+ places, extract it — into a component, a Tailwind component class, or a named CSS class. Repeated utility dumps are a smell.
- Avoid using Tailwind to fight Tailwind. If you are stacking overrides on overrides, the approach is wrong.

For depth: `references/css_systems.md`.

### React and TypeScript

**React:**
- Presentation components render. They do not fetch, they do not derive business logic, they do not manage application state. They receive props and return JSX.
- State ownership should be clear. If two components need the same state, it lives in their lowest common ancestor — not duplicated, not synchronized via effects.
- Keep prop surfaces minimal. A component that accepts 12 props is probably doing too many jobs. Compose instead.
- Avoid pushing logic into JSX. Ternaries are readable; nested ternaries are not. Extract complex conditions into variables or helpers.

**TypeScript:**
- Types express domain knowledge. `Position`, `OrderBook`, `InstrumentId` communicate intent. `data: any` does not.
- Prefer interfaces for object shapes that represent domain entities. Use type aliases for unions and computed types.
- Avoid type assertions (`as`) except at genuine runtime boundaries. If you are asserting away a type error, the types are probably wrong.
- `unknown` over `any`. `never` for exhaustiveness. Discriminated unions for state machines.

For depth: `references/react_typescript_patterns.md`.

### JSX and HTML

JSX quality is frontend craft — not just making the tree compile.

**JSX:**
- Avoid unnecessary wrapper elements. A `<div className="wrapper"><div className="inner">` chain is div soup in JSX form.
- Readable prop surfaces first, implementation second. A component's API is its public contract.
- Separate view logic from domain logic. A component that renders a price table should not contain the sorting algorithm.

**HTML:**
- Use semantic elements. A navigation is `<nav>`, a button is `<button>`, a heading is `<h1>`–`<h6>`. Do not use `<div onClick>` for interactive elements.
- Landmark elements make the page comprehensible to assistive technology and are correct engineering, not optional accessibility theater.
- Forms use `<label>` and `<input>` with correct association. `aria-label` is a last resort, not a first tool.

For depth: `references/jsx_html_guidelines.md`.

---

## Helix-specific rules

The following rules apply to work on the Helix trading interface (`src/**/*.tsx`, `src/styles/helix.css`, `index.html`). They are Helix-specific and do not necessarily apply to other React projects.

### Aesthetic checklist

Run through this before every commit that touches pixels. If you cannot answer yes to each, fix it inside this unit — do not defer it.

- Every color comes from a `var(--token)` — grep the diff for `#` to catch stray hex.
- Every size and gap is a multiple of 4px (4 / 8 / 12 / 16 / 24). No 5, 7, 10, 15.
- Text is 9–13px. Labels: IBM Plex Sans. All numeric values: `var(--font-mono)`, `textAlign: 'right'`.
- Borders are 1px hairlines using `var(--border-hairline)` or `var(--border-subtle)`. No drop shadows.
- Every workspace panel is wrapped in `<Pane>` with a correct `source` badge (`live` / `internal` / `sim` / `rec`) and a title at 11px.
- Pane header: 28px. TopBar: 40px. ContextBar: 32px. StatusBar: 22px. Rail: 48px.
- Trading semantics respected: `--bid` for positive/long/buy, `--ask` for negative/short/sell. Never repurposed.
- Data tables: sharp corners, sticky headers on `var(--bg-raised)`, `fontSize: '10px'`, right-aligned numerics.
- New CSS lives in `src/styles/helix.css`. Not inline, not in a new file.
- No imported chart libraries, no media queries, no consumer fonts (Inter, system-ui, -apple-system).

### Functional verification

| Change | Minimum verification |
|---|---|
| New pane / chart / table | Open http://127.0.0.1:5173/ in a browser (prod bundle via LaunchAgent) or run `npm run dev` for HMR, navigate to the workspace, confirm renders without console errors, hover and tooltip interactions fire, numbers update on re-render. |
| Layout / grid edit | Resize the window; no horizontal scrollbar, no pane clipped, no area collapsed below its min dimension. |
| Token / `:root` edit | Scan every workspace that consumes the token; confirm no regression elsewhere. |
| New interaction (drawer, palette, tab) | Exercise the full state machine: open, switch, close, reopen, keyboard where relevant. |
| Pure refactor, no visual delta | Diff the rendered DOM; eyeball all three workspaces for regression. |

**Serving the app:** the `com.helix.devserver` LaunchAgent serves the prod Vite bundle from `dist/` on http://127.0.0.1:5173/. Rebuild with `npm run build`; the server picks up new files on the next request. For HMR during active development, run `npm run dev` (stop the LaunchAgent first via `/serve stop`, same port).

If the environment has no browser access, say so explicitly. Do not claim "verified in browser" based on a green type check or a clean diff.

### When the user says "haz que se vea increíble"

This is the highest-stakes mode. The instinct to over-engineer is wrong — Helix's aesthetic is restraint. "Increíble" in this codebase means: correct density, ruthless alignment, monospace numerics, zero ad-hoc values, semantic color, information hierarchy that lets the eye land on the trade-relevant number first. Before adding anything, ask whether you can *remove* something — a border, a padding, a second color — and make the remaining signal sharper.

---

## Commit style

One logical unit per commit. Natural, human, imperative messages. No AI attribution, no `Co-authored-by`. Scope the subject to the surface that changed.

**Before staging a UI commit:** run `npx playwright test`. The pre-commit hook will also run it automatically, but catching failures before staging is faster. A red test suite means the commit does not happen.

**Good:**
- `Add spread monitor pane to market workspace`
- `Extract CurveChart into standalone component`
- `Fix bid/ask color inversion in depth ladder`
- `Tighten ContextBar gap to 8px`
- `Add --bg-float token for drawer backgrounds`

**Bad:**
- `Update market.jsx` — what changed? why?
- `Add pane, fix colors, refactor chart` — three commits, not one
- `wip` — only acceptable on a throwaway branch

Stage explicit paths with `git add <file>`. Never `git add -A` — this repo has hooks, session logs, and settings files that must not ride along with a UI commit.

---

## Decomposition example

### "Build a new volatility surface pane in the Strategy workspace"

1. `Add --vol-surface-cell token group for heatmap cells`
2. `Add VolSurface grid area to StrategyWorkspace layout`
3. `Scaffold VolSurfacePane with Pane wrapper and seeded data`
4. `Add VolSurfaceHeatmap SVG subcomponent`
5. `Wire tenor/strike axes and tooltip`
6. `Tighten cell spacing and legend typography`

Six commits, each of which leaves the UI in a coherent state. Any one can be reverted in isolation.

---

## Guardrails

- **Helix only:** The project is Vite + React 18 + TypeScript. Do not introduce a chart library, a CSS-in-JS runtime, or a new package manager. Bundle additions require explicit approval. These constraints do not apply to other React/Vite/TS projects.
- Never write comments that narrate what the code does. A comment exists only to pin a non-obvious invariant or constraint.
- Never bypass hooks on commit (`--no-verify`). The `playwright_gate.py` hook is a hard gate — if it blocks, fix the UI, don't skip the hook.
- Never touch `session_logs/`, `settings.json`, or `.claude/hooks/` as part of a UI change commit.
- If a requested change conflicts with the design system, push back with the canonical alternative before executing.
- If the correct action is a refactor and the user asked for a patch, surface the refactor option. Then do what they decide.

---

## Reference documents

Read these when depth is needed beyond the SKILL.md overview.

| Document | When to read |
|---|---|
| `references/frontend_architecture.md` | Placement decisions are ambiguous; separation of concerns; file/folder naming; refactoring discipline |
| `references/react_typescript_patterns.md` | Writing React components and hooks; TypeScript usage; state ownership patterns |
| `references/css_systems.md` | CSS/Tailwind craft; spacing systems; layout patterns; responsive behavior |
| `references/jsx_html_guidelines.md` | JSX composition quality; HTML semantics; accessibility; reducing div soup |

---

## Handoffs to sibling skills and agents

- `component-builder` — code templates for Helix components (Pane, SVG chart, heatmap, table). Does not duplicate those snippets.
- `frontend-design` — design decisions (when to tab vs. stack, density modes, layout geometry per workspace).
- `ui-architect` — when the decomposition itself is the hard part on a large multi-pane redesign, this agent produces the component hierarchy plan first; this skill executes it unit-by-unit.
- `git-steward` — when staging a complex set of changes across multiple files.

This skill is the implementation spine. Specialized Helix skills build on it as the default quality standard.

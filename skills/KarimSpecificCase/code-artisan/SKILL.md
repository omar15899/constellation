---
name: code-artisan
description: Core implementation craft skill for the ENGIE · Storengy gas-storage monitor and, more broadly, any serious frontend engineering task. Use whenever the user asks to build, extend, redesign, refactor, or polish any part of the dashboard (panes, charts, tables, workspaces, layout engine, tokens, shell chrome) OR any HTML/CSS/JS (vanilla, React, TypeScript, Vite, Tailwind, shadcn/ui) application. This is the default engineering standard — it governs how code is inspected, designed, written, refactored, and polished. Trigger on: multi-step UI implementation, component architecture work, frontend refactoring, "clean this up", "architect this", "add [X] with [Y] and [Z]", "refactor [component/module]", "haz que se vea increíble", "construye", "añade", "refina", "rediseña", any serious frontend engineering task where craft and coherence matter, not just compilation.
---

# Code Artisan

Craftsman-mode implementation skill for the ENGIE · Storengy gas-storage monitor and serious frontend engineering in general. The goal is not to generate code — it is to produce work that is coherent, readable, and ready to ship: correct architecture, deliberate CSS, semantic markup, and a git history that reads as a narrative of intentional changes.

## Why this skill exists

Frontend work is easy to do poorly. Components balloon with mixed concerns. CSS becomes a pile of exceptions. Types, when they exist, get used cosmetically. HTML collapses into div soup. The result compiles and looks correct at a glance, but is fragile, hard to read, and miserable to extend.

This skill enforces a different standard: **understand before writing, design before coding, build small, verify, commit one thing at a time.** Every increment should leave the codebase in a state you would be proud to show someone.

For the Storengy dashboard specifically: institutional operational tools demand the density, precision, and information architecture of professional trading terminals. A stray hex value, a 10px gap, a flow colour misused — these degrade the whole thing. The skill preserves the dashboard's design language as a hard invariant: injection is green, withdrawal is red, 4px base grid, hairline borders, IBM Plex Mono for every digit.

---

## The four phases

Every non-trivial task follows four phases. Do not collapse them.

### Phase 1 — AUDIT

Before writing a single line, read the codebase.

- Map the file structure. Identify where different concerns live. If the placement of new code is ambiguous, resolve it before writing — not after.
- Find existing patterns: factory function naming, CSS variable conventions, DOM shapes, state locations. New code should read like it was always there.
- Identify inconsistencies, technical debt, and weak abstractions. If you are about to add code to a broken area, surface that to the user before adding more to it.
- Locate the minimal intervention surface. The correct fix is often smaller than it first appears.

For this project specifically: read the `:root` block of `index.html` / `monitor.html` and the factory function for whichever pane you're about to touch, end-to-end. Note the naming, the pane-head structure, the seeded RNG, the layout-engine contract (`karim.layout.<workspace>.<orientation>`). A skipped read causes name collisions and reintroduces ad-hoc values.

### Phase 2 — DESIGN

Think about architecture before touching code.

- Decide where the code lives. Which file, which section, which factory boundary.
- Define the pane's public surface (title, subtitle/tag, actions, body contract) before writing the implementation. A bad API is harder to change later than bad internals.
- Check whether the correct intervention is a refactor, not a patch. If you are about to add code to mask a structural problem, stop and propose the refactor instead.
- For non-trivial additions, state the decomposition plan (3–6 bullets) before writing. This surfaces disagreements early and is cheaper than unwinding bad work.

See `references/frontend_architecture.md` for guidance on layer separation, file structure, and naming.

### Phase 3 — IMPLEMENT

Execute with discipline.

- Write one logical unit at a time. A logical unit is independently commitable and leaves the UI in a coherent state.
- Keep types or JSDoc explicit when the domain is non-trivial (flow rates, tenors, inventory curves). Names should express the domain — `injectionRate`, `withdrawalCurve`, `cavernId` — not `data`, `val`, `x`.
- Preserve readability at every step. Prefer clear over clever.
- Avoid ad hoc workarounds. If you find yourself fighting the layout engine or the design system, that is a signal the design is wrong, not a reason for a hack.

See `references/react_typescript_patterns.md` for React/TS craft when working on other projects; for this repo (vanilla JS), apply the same principles: factory functions over classes, event handlers attached near the DOM they own, no hidden globals, small pure helpers for derivations.

### Phase 4 — POLISH

Before committing, make the result feel intentional.

- CSS coherence: spacing consistent with the 4px scale, colours from the token system, layout that holds at edge cases. No magic numbers.
- DOM legibility: clean tree structure, no bloated wrapper chains, readable class surfaces.
- HTML semantics: correct landmarks, interactive elements that are actually interactive elements, no `<div onClick>`.
- Remove complexity that crept in during implementation. If you added something "just in case," remove it.
- Run the [Aesthetic checklist](#aesthetic-checklist). Run visual verification for any UI change.

See `references/css_systems.md` and `references/jsx_html_guidelines.md` for depth.

### Phase 4b — HTML LINT GATE (mandatory, non-negotiable)

**Every commit that touches `index.html`, `monitor.html`, or files under `assets/` must pass the `html_lint_gate.py` pre-commit hook.** The gate parses the HTML tree, checks nesting balance, scans for leaked secrets, and blocks `debugger;` / `console.trace` leftovers. It is enforced by the hook wiring in `.claude/settings.json`.

Run manually at any point:
```bash
python3 .claude/hooks/html_lint_gate.py < /dev/null
```

If the gate blocks, **fix the code — not the gate.** Loosening the gate is not the intervention.

### Phase 4c — PLAYWRIGHT GATE (mandatory, non-negotiable)

**Every commit that touches `index.html`, `monitor.html`, `assets/**`, `package.json`, `playwright.config*`, or `tests/**` must pass the full Playwright suite.** This is the only automatic proof that the app actually mounts, renders its panes, and keeps the design-system invariants under real browser conditions. HTML-lint catches tree-shape issues; Playwright catches everything downstream (layout regressions, missing elements, console errors, flow-semantic inversions).

The gate is enforced by `playwright_gate.py` as a `PreToolUse` hook on `Bash(git commit*)`. The hook:
- Only triggers when UI-relevant files are staged (skips docs, settings, hook edits)
- Spins up `python3 -m http.server 5199` via Playwright's `webServer` block
- Runs headless Chromium against both `index.html` and `monitor.html`
- Blocks the commit with a JSON `{"decision":"block"}` and a tail of the failing output if any test fails

Run manually at any point:
```bash
npx playwright test                     # all specs
npx playwright test tests/monitor.spec.cjs   # monitor only
npx playwright test --headed            # visual debug
npx playwright test --ui                # interactive runner
```

The suite (under `tests/`) covers:
- **`shell.spec.cjs`** — shared invariants across both pages: no JS console errors on load, topbar 56 px, ctxbar 32 px, statusbar 22 px, pane-head 28 px, no horizontal overflow at 1024/1280/1440/1680/1920, range slider interactive, flow semantics (`.up` green / `.dn` red), mono numerics.
- **`monitor.spec.cjs`** — all 10 commercial panes render, heatmap has SVG cells, counterparty ledger has 18 rows, pipeline funnel has 4 stages, spread chart has history + forward paths, context-menu restore flow, reset-layout flow, trader panes are NOT registered.
- **`index.spec.cjs`** — both workspace tabs present, switching to Trader renders trader panes, ticket round-trip (submit adds a blotter row, removes a row, tab-count indicator updates).

**When to extend the suite:** any new pane, any new interaction, any new design-system token — add a spec before (or at the same commit as) the code. A pane without test coverage is half-built. See the existing specs for the idiom; new specs go under `tests/<feature>.spec.cjs`.

**If the gate blocks, fix the code — not the test.** Tests encode invariants that must hold. The only acceptable edits to existing specs are *adding* coverage, not loosening assertions. If you change an invariant on purpose (e.g. moving the statusbar from 22 px to 24 px), update the spec in the same commit with a short note in the message.

**Kill switches (discouraged; only when the hook itself is broken):**
```bash
PROJECT_PLAYWRIGHT_GATE=0             # skip entirely for this commit
PROJECT_PLAYWRIGHT_GATE_TIMEOUT=300   # stretch the 180s default
```

Never use `--no-verify` on a UI commit. That bypasses both this gate and the HTML lint gate.

---

## Architectural principles

These apply to all work done under this skill, regardless of project.

**Separation of concerns** — view (DOM), application state (in-memory / localStorage), domain logic (flow math, inventory, curve math), data access, and persistence are distinct layers. A factory function that fetches its own data, derives business logic, and renders HTML has three jobs. Give each concern its own home.

**Explicitness over magic** — Hidden coupling is a future debugging session. Prefer explicit data flow: parameters over ambient globals, well-named callbacks over mysterious side effects, typed shapes (TS or JSDoc) over loose object soup.

**Coherent naming** — Names should tell you what something is and where it belongs. A function named `renderData` has failed. `renderCavernInventory` has not. File names should match export names. Directory names should match domain boundaries.

**Refactor courage** — When the structure is wrong, fix the structure. Do not add a workaround that patches a symptom. But: refactor only what is necessary. Gratuitous churn for aesthetic reasons is not craft, it is noise.

**Justified abstractions only** — Three similar lines is better than a premature abstraction. Extract a reusable factory when duplication is clearly structural and the abstraction is genuinely stable. Do not extract for the sake of feeling organized.

**Future extensibility, not future requirements** — Write code that is easy to change, not code that anticipates every possible change. Avoid accidental complexity.

For detailed guidance: `references/frontend_architecture.md`.

---

## Frontend craft standards

### CSS and tokens

CSS is an engineering discipline, not a styling afterthought. The quality of CSS directly determines the quality of the interface.

**As a system:**
- Work within the spacing scale. Never introduce a magic pixel value. For this project: multiples of 4px.
- Preserve visual hierarchy. The reader's eye should find the most important operational number first — inventory level, injection rate, withdrawal rate, next-hour forecast.
- Think in layout primitives (flex, grid, flow) rather than one-off positioning. Fragile absolute/fixed positioning should be rare and clearly justified.
- State styling belongs with the component it describes, not scattered across files.
- Motion should be restrained. `--ease-ui` for hover/state; `--ease-spring` for drag/drop feedback. Animation earns its presence; it does not decorate.

**Tokens:**
- Every colour from `var(--token)`. No raw hex in source, ever.
- `--inj` and `--wth` are the flow anchors. Never invert. Never repurpose them for non-flow encoding.
- `--engie-*` tokens are brand surfaces. Do not use them to encode data.

For depth: `references/css_systems.md`.

### Vanilla JS (this project) and React/TS (other projects)

**Vanilla JS (Storengy dashboard):**
- Small factory functions that build DOM and attach behaviour, colocated in the relevant section of `index.html` / `monitor.html`.
- Event handlers attached at the nearest relevant element; no delegation gymnastics unless the DOM is dynamic and justifies it.
- State lives in closures or a shared `state` object the factory returns. Avoid globals except for the layout engine's `karim.*` localStorage keys.
- No frameworks. No React. No bundler. If a task seems to need React, the task is wrong for this repo — discuss with the user before adding any dependency.

**React / TypeScript (other projects):**
- Presentation components render. They do not fetch, they do not derive business logic, they do not manage application state.
- State ownership should be clear. If two components need the same state, it lives in their lowest common ancestor.
- Keep prop surfaces minimal. A component that accepts 12 props is probably doing too many jobs. Compose instead.
- Types express domain knowledge. `Position`, `OrderBook`, `CavernInventory` communicate intent. `data: any` does not.
- Prefer interfaces for object shapes that represent domain entities. Use type aliases for unions and computed types.
- Avoid type assertions (`as`) except at genuine runtime boundaries.

For depth: `references/react_typescript_patterns.md`.

### HTML

- Use semantic elements. A navigation is `<nav>`, a button is `<button>`, a heading is `<h1>`–`<h6>`. Do not use `<div onClick>` for interactive elements.
- Landmark elements make the page comprehensible to assistive technology and are correct engineering, not optional accessibility theater.
- Avoid unnecessary wrapper elements. A `<div class="wrapper"><div class="inner">` chain is div soup.
- Form controls use `<label>` and `<input>` with correct association. `aria-label` is a last resort, not a first tool.

For depth: `references/jsx_html_guidelines.md` (the principles apply one-for-one to vanilla HTML).

---

## Storengy-specific rules

The following rules apply to work on the ENGIE · Storengy dashboard (`index.html`, `monitor.html`, `assets/**`).

### Aesthetic checklist

Run through this before every commit that touches pixels. If you cannot answer yes to each, fix it inside this unit — do not defer it.

- Every colour comes from a `var(--token)` — grep the diff for `#` to catch stray hex.
- Every size and gap is a multiple of 4px (4 / 8 / 12 / 16 / 24). No 5, 7, 10, 15.
- Text is 9–13px. Labels: IBM Plex Sans. All numeric values: `var(--mono)`, `text-align: right`.
- Borders are 1px hairlines using `var(--hair)` or `var(--hair-2)`. No drop shadows. No rounded corners above 4px.
- Every workspace panel is wrapped in `.pane` with `.pane-head` (title + tag + tools) and `.pane-body`. Tags use `.pane-tools .tag`.
- TopBar: 56px. ContextBar: 32px. StatusBar: 22px. Pane header: 28px.
- Flow semantics respected: `--inj` (green) for injection / stock-in / long, `--wth` (red) for withdrawal / stock-out / short. **Never repurposed. Never inverted.**
- Data tables: sharp corners, sticky headers on `var(--panel-2)`, 10px numeric cells, right-aligned.
- New CSS lives in the `<style>` block of the file it applies to. No external stylesheet, no new `.css` file.
- No chart libraries, no media queries, no consumer fonts (Inter, system-ui, -apple-system).

### Functional verification

Two layers: **(1) Playwright** for deterministic, machine-enforced coverage, **(2) manual browser pass** for anything Playwright cannot see (font rendering, transitions, colour feel, interactive timing).

| Change | Minimum verification |
|---|---|
| New pane / chart / table | **Add a Playwright spec** asserting the pane renders, its key DOM elements exist, and its hover/click interactions fire. Then open `http://127.0.0.1:5173/index.html` or `/monitor.html` in a browser and confirm it feels right (density, alignment, tooltip position). |
| Layout / grid edit | Run `npx playwright test tests/shell.spec.cjs` (overflow checks cover 1024/1280/1440/1680/1920). Then resize the window manually; drag/resize/swap should still feel correct. |
| Token / `:root` edit | Run the full Playwright suite — shell.spec asserts heights and flow semantics. Then scan every pane that consumes the token for visual regression. |
| New interaction (drawer, palette, menu) | **Add a spec** exercising the full state machine: open → switch → close → reopen, keyboard where relevant. Manual pass for timing feel. |
| Layout engine edit | Run the suite; monitor.spec.cjs + index.spec.cjs cover context-menu restore, reset-layout, workspace switching. Exercise portrait and landscape manually. |
| `:root` token addition | Add coverage to `tests/shell.spec.cjs` if the token gates a structural invariant (height, spacing, colour semantic). |

**Serving the app:** the `dev_server.py` SessionStart hook ensures `python3 -m http.server 5173` is listening from the repo root for manual browsing. Playwright boots its own server on port 5199 via the `webServer` block in `playwright.config.cjs` — no conflict.

**Running the suite:**
```bash
npx playwright test                                # all specs (~18s)
npx playwright test tests/monitor.spec.cjs         # subset
npx playwright test --ui                           # interactive runner
npx playwright test --headed --project=chromium    # watch it click through
```

If the environment has no browser access, say so explicitly. **A green Playwright run is not a substitute for a manual pass; a manual pass is not a substitute for a green Playwright run.** Both are mandatory for any commit that changes pixels.

### When the user says "haz que se vea increíble"

This is the highest-stakes mode. The instinct to over-engineer is wrong — this dashboard's aesthetic is restraint. "Increíble" in this codebase means: correct density, ruthless alignment, monospace numerics, zero ad-hoc values, semantic flow colour, information hierarchy that lets the eye land on the operationally critical number first (current stock → net flow → alert → forecast). Before adding anything, ask whether you can *remove* something — a border, a padding, a second colour — and make the remaining signal sharper.

---

## Commit style

One logical unit per commit. Natural, human, imperative messages. No AI attribution, no `Co-authored-by`. Scope the subject to the surface that changed.

**Before staging a UI commit:** run `npx playwright test` locally. The pre-commit hook runs it automatically, but catching failures before staging is faster. A red gate means the commit does not happen. The same applies to `python3 .claude/hooks/html_lint_gate.py` — run it in doubt.

**Good:**
- `Add injection forecast pane to monitor workspace`
- `Extract CavernStackChart into standalone factory`
- `Fix inj/wth colour inversion in net-flow ribbon`
- `Tighten ContextBar gap to 8px`
- `Add --inv-bar-cell token group for inventory heatmap`

**Bad:**
- `Update monitor.html` — what changed? why?
- `Add pane, fix colours, refactor chart` — three commits, not one
- `wip` — only acceptable on a throwaway branch

Stage explicit paths with `git add <file>`. Never `git add -A` — this repo has hooks, session logs, and settings files that must not ride along with a UI commit.

---

## Decomposition example

### "Build a net-flow ribbon in the Monitor workspace"

1. `Add --ribbon-cell and --ribbon-tick tokens for net-flow strip`
2. `Scaffold NetFlowRibbon factory inside pane wrapper`
3. `Wire 24-hour inj/wth series to ribbon renderer`
4. `Add hover tooltip with hourly breakdown`
5. `Tighten ribbon spacing and legend typography`

Five commits, each of which leaves the UI in a coherent state. Any one can be reverted in isolation.

---

## Guardrails

- **This project only:** the served artefact is vanilla HTML + CSS + JS. Do not introduce a bundler, a framework, a chart library, or a CSS preprocessor into the served page. **Playwright is the only test-only dev dependency** (see `package.json`) and it does not touch the served output. Any additional runtime dependency requires explicit approval.
- Never write comments that narrate what the code does. A comment exists only to pin a non-obvious invariant or constraint — e.g., "flow semantic: inj never red" or "layout key shape must stay backward-compatible".
- Never bypass hooks on commit (`--no-verify`). The `html_lint_gate.py` and `playwright_gate.py` hooks are hard gates — if either blocks, fix the code, don't skip.
- Never touch `session_logs/`, `settings.json`, or `.claude/hooks/` as part of a UI change commit.
- If a requested change conflicts with the design system, push back with the canonical alternative before executing.
- If the correct action is a refactor and the user asked for a patch, surface the refactor option. Then do what they decide.
- When you add a new pane, chart, table, or interaction, **add Playwright coverage in the same commit (or one immediately before)**. A feature without a spec silently drifts until someone notices — the spec makes it a permanent invariant.

---

## Reference documents

Read these when depth is needed beyond the SKILL.md overview.

| Document | When to read |
|---|---|
| `references/frontend_architecture.md` | Placement decisions are ambiguous; separation of concerns; file/folder naming; refactoring discipline |
| `references/react_typescript_patterns.md` | Working on a React/TS project, or translating those patterns to the vanilla factory functions used here |
| `references/css_systems.md` | CSS craft; spacing systems; layout patterns; responsive behaviour (noting that this repo is desktop-only) |
| `references/jsx_html_guidelines.md` | DOM composition quality; HTML semantics; accessibility; reducing div soup |

---

## Handoffs to sibling skills and agents

- `component-builder` — code templates for panes, SVG charts, heatmaps, tables. Consult when the shape of a new widget is unclear.
- `frontend-design` — design decisions (when to tab vs. stack, density modes, layout geometry per workspace).
- `storage-architect` agent — when the decomposition itself is the hard part on a large multi-pane redesign, this agent produces the component hierarchy plan first; this skill executes it unit-by-unit.
- `design-system-guardian` agent — when the design system is drifting or a new token group is needed.
- `code-backend-foundation` skill — when the task is explicitly about moving from demo data to real SCADA/market/inventory feeds, persistence, auth, or real-time transport.
- `git-steward` agent — when staging a complex set of changes across multiple files.

This skill is the implementation spine. Specialized skills and agents build on it as the default quality standard.

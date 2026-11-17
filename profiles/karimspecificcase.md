# KarimSpecificCase

Root: `/Users/omarkhalil/GitHub/KarimSpecificCase`. This adjacent, untiered client UI is outside the QuantOS import graph. It contains independent vanilla HTML applications; identify the requested target before editing.

## Choose the target and contract

- `index.html` and `monitor.html` are the legacy ENGIE/Storengy Trader/Monitor entries. Use the common coding method and the factory/design rules below.
- `GS_trading_interface.html` has its own replacement and backend integration contract. Read `README.md`, `GS_INTERFACE.md` and the [gs-interface-editor method](../skills/KarimSpecificCase/gs-interface-editor/SKILL.md). The legacy entries are not alternative targets for a GS change.
- Read the current owner's instructions and working diff. Preserve existing edits, backend contracts and the user's selected appearance/scope. A UI request does not authorize a backend migration or broker execution.

## Legacy dashboard invariants

The served applications remain standalone vanilla HTML/CSS/JavaScript, with no runtime framework, bundler or required build step. Use small DOM factory functions and plain state/listener ownership; introduce JSDoc when it clarifies a contract. Reuse existing pane wrappers, charts and layout mechanisms instead of importing the retired Helix React recipes.

Preserve workspace/orientation-aware drag, swap, resize, alignment and aspect-fit behavior, and persistence keys `karim.layout.<workspace>.<orientation>` and `karim.mon.layout.<orientation>`. Preserve chart zoom/pan/brush interactions and clean up owned listeners, timers and resources. Keep the distinction between persisted layout, live data and transient view state.

Visual constants belong to the owning inline `:root` tokens. Injection/stock-in/long uses `--inj` (green); withdrawal/stock-out/short uses `--wth` (red). Never invert or hardcode that mapping. Reserve `--engie-*` and `--storengy-amber` for brand surfaces, not data encoding.

Retain the compact desktop design: 4px spacing grid, 9–13px labels, IBM Plex Mono for numbers, right-aligned tabular values, 1px hairlines and no decorative drop shadows. The legacy shell uses topbar 56px, contextbar 32px, statusbar 22px and pane header 28px. Reuse sharp-corner tables and sticky headers on the existing panel token. Treat these as owner design constraints, not instructions to overwrite a deliberate requested redesign.

Legacy orientation changes belong to the layout engine, not new mobile breakpoints. Keep the hand-coded SVG chart system. One-off inline SVG is allowed in these vanilla files; reuse shared glyph functions when repeated. This differs from Helix's module/icon contract.

## GS replacement contract

Read the current `GS_INTERFACE.md` endpoint table and the README replacement instructions before changing `GS_trading_interface.html`. The result must remain one HTML with embedded CSS, JavaScript, SVG and fonts that can replace the prior file without changing the backend or deploying companion assets.

Preserve routes, HTTP methods, bodies/envelopes, units, authentication/CSRF, same-origin credentials, `__RAW__`, `__CSP_NONCE__`, integration identifiers, public refresh APIs and connected persistence formats. Preserve refresh/cancellation and failure semantics. Keep demo explicit, isolated in storage and API-free; a failed connected feed must not silently become synthetic data.

Read `GS_WORKSPACES.md`, `GS_GEOMETRY.md`, `GS_UNITS.md`, `GS_PERFORMANCE.md` and `GS_RESEARCH_API.md` for the affected mechanism. The retained skill covers supplied HTML decoding, lifecycle, motion, pane identity, geometry and units. Distinguish backend therms/GBP, operational GWh/£M and research MWh/GBP-per-MWh/GBP. A unit switch preserves the canonical quantity and input precision.

## Backend boundaries

Distinguish demonstration, connected, persisted and derived state. Any separately authorized backend work first establishes real data sources, authentication versus authorization, persistence ownership, typed API boundaries and deployment constraints. Do not add a generic streaming/auth/database stack simply because an interface needs data. Existing application contracts take precedence over retired prototype-migration recipes.

## Native operation and evidence

Constellation supplies shared roles, task scope, review and authorized publication. Native client settings remain client-owned. Preserve the domain `pre_commit_gate.py`, `html_lint_gate.py`, `playwright_gate.py` and `dev_server.py`; their presence or configuration is not evidence that a particular candidate passed them. Direct Git-command listeners do not intercept the outer Constellation commit automatically.

Declare exact paths and appropriate required checks; preserve foreign staging. Create, change or run tests only when Omar explicitly requests them. Existing test suites remain intact, and a test-dependent acceptance gate without authorized evidence remains unmet. Static parsing and review do not establish browser behavior, and mocked backend responses do not establish production-server compatibility.

When explicitly requested, select the current Playwright suites by actual target and impact. `playwright.config.cjs` normally uses port 5199; the development server normally uses 5173. Verify the selected origin and checkout rather than inferring them from an open port. GS suites and validation configuration are described in the retained skill and `GS_VALIDATION.md`; legacy shell/index/monitor suites cover their respective entries.

Read-only review can inspect design tokens, flow semantics, state ownership and the scoped diff without executing tests. Use logical commit boundaries and natural messages through the common workflow; never bypass a failing gate or publish automatically.


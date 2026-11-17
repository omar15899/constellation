---
name: "gs-interface-editor"
description: "Edit KarimSpecificCase/GS_trading_interface.html and supplied HTML replacements. Preserve its integration contract, lifecycle, motion, geometry and units, and report validation within the user's authorized scope."
---
# GS interface editor

## Locate the contract and the change

Use the project selected by the user. From its working directory, resolve its actual Git root and verify it owns `GS_trading_interface.html` and `GS_INTERFACE.md`. From the registered workspace, route `KarimSpecificCase/GS_trading_interface.html` to its Git owner. Resolve every project document and test below against that root. If the project is absent, request its checkout or the file supplied by the user.

Read `AGENTS.md`, `README.md` (especially “Contrato permanente: plug and play”), and `GS_INTERFACE.md` (especially “Sustituir en el backend”). Read the [Karim profile](../../../profiles/karimspecificcase.md) listed in the central `profiles/projects.json` and applicable directory instructions, treating its historical observations as leads to verify against current files. Follow the active workspace contract when working through the hub. The current user request sets scope, including any no-commit or restricted-file instruction.

Inspect the working diff before editing; preserve existing work. Translate the requested iteration into observable acceptance criteria, then locate the responsible shared mechanism in the HTML's script map and CSS. Keep the change focused; internal refactoring is appropriate when needed to make the interaction reliable. Preserve appearance unless the request changes it. `index.html` and `monitor.html` are independent entries, not alternate targets.

## Inspect supplied replacements before promotion

When a user supplies `GS_trading_interface_new.html` or another replacement, inspect its contents rather than trusting its extension or assuming it supersedes the current file. Cocoa HTML Writer exports can contain an outer HTML document with the actual source escaped inside paragraph elements: look for `Generator="Cocoa HTML Writer"` or the equivalent meta tag, `Apple-converted-space`, and paragraphs beginning with `&lt;!doctype html&gt;`.

For a wrapper, decode to a temporary candidate outside the repository. Parse the outer document as HTML, extract body paragraph text in order with line boundaries, and decode that outer layer once. Preserve nested source entities, quotes, script text and meaningful whitespace; handle wrapper indentation without globally replacing nonbreaking spaces in application strings. Do not strip tags or repeatedly unescape the whole file. Confirm that the result is the actual application with inline style/script sections, parse its JavaScript, and inspect the decoded diff before running it locally. Preserve the supplied original unless its replacement or removal is explicitly in scope.

Compare the candidate with the current working HTML for both user changes and backend changes. Trace added fields through parsing, state, refresh/rollback and display; for example, `master_initial_levels` becomes `DATA.masterInitialLevels` in the present implementation. Preserve legitimate supplied integration changes when merging, without inferring a new transport contract. Promote only when requested, preserving the actual delivered HTML as the target of any separately authorized validation.

## Keep one coherent implementation

The deliverable remains one standalone vanilla HTML with embedded CSS, JavaScript, SVG and fonts. Add no runtime dependency, bundler or required companion asset.

- **CSS:** Edit the owning rules and shared `:root` tokens rather than accumulating overrides. Reuse component styles, spacing, typography and semantic colors; injection uses `--inj`, withdrawal `--wth`. Keep numeric-editor styling centralized when changing steppers or input treatment.
- **JavaScript and lifecycle:** Reuse `registerPaneCleanup`, `subscribePane`, subscription adapters and `frameTask`. Register ownership during synchronous pane mounting, including cancellers for later asynchronous work. Hidden panes defer updates; retained panes preserve drafts, focus, scroll and zoom; disposed panes release listeners, observers, animation frames and subscriptions. Reuse `makeReactiveChart` for chart interaction.
- **Motion:** Route animations through `Motion` and the CSS duration/easing/displacement tokens. Support interruption, immediate reversal, reduced motion and page hiding without stranded inline styles or delayed close callbacks. Consult `GS_WORKSPACES.md` for motion and pane lifecycle, and `GS_PERFORMANCE.md` when changing scheduling or responsiveness.
- **Geometry and workspaces:** Use `PanelIdentity`, `LayoutGeometry`, `WORKSPACES`, `WIDGETS` and `DEFAULTS`; preserve the distinction between a module type and each pane instance (including unique DOM IDs and labels); consult `GS_GEOMETRY.md` and `GS_WORKSPACES.md`. Keep previews separate from committed layout, validate bounds/minimums/nonoverlap, and commit the complete gesture to Undo/Redo. Canvas growth must not compress neighbors. Preserve both orientations, cancellation, persistence and retained pane state. Reuse these mechanisms for custom workspaces rather than introducing another layout engine.
- **Units:** Consult `GS_UNITS.md` before changing a quantity, selector, input or export. Reuse `UNIT_DEFS`, `UNIT`, `MONEY`, `TH_PER_MWH` and the shared converters/formatters. Operational state uses GWh and £M, backend data uses therms and GBP, and research contracts use MWh, GBP/MWh and GBP. Keep quantities, daily rates, per-unit prices and cash distinct. Unit switches must preserve canonical quantities, ticket prices and fractional editor precision. Derive labels and widget tags from the same definitions. For research work also read `GS_RESEARCH_API.md`; retain the study availability flag unless changing it is requested.

## Preserve backend compatibility

Use the integration table in `GS_INTERFACE.md` as the maintained endpoint reference. Preserve routes, HTTP methods, bodies, envelopes, units, authentication/CSRF, same-origin credentials, ETag/304/503 behavior, refresh cadence and cancellation of stale responses. Preserve `const __RAW__ = null;`, `__CSP_NONCE__`, integration identifiers, `window.LiveRefresh` methods and connected persistence keys/formats. Do not change business calculations or weaken CSP incidentally.

Demo remains explicit (`?demo=1` or direct file opening), isolated in storage and free of API calls. A failed connected feed must report failure, never silently substitute synthetic data. Treat frontend improvements as no authorization for backend migration or live order submission.

## Validate within the requested scope

Create, change or run tests only when Omar explicitly requests them. For a source-only task, use static review and permitted syntax checks, and state that interactive behavior remains untested. A required test-dependent gate remains unmet; do not bypass it or disguise a behavioral test as a check.

When browser/behavior testing is explicitly requested, exercise the actual delivered HTML and selected origin. `playwright.config.cjs` normally serves a separate test origin on port 5199; verify overrides and avoid an existing server from another checkout. `tests/gs-interface.spec.cjs` covers integration/demo boundaries; select existing GS motion, geometry, setups, units, chart-gesture, responsive, adversarial or research suites by impact. Confirm current filenames before invoking them.

Use `GS_VALIDATION.md` and `playwright.gs-validation.config.cjs` for the documented Chromium/WebKit acceptance scenarios when that scope is authorized. Preserve observations about the first pointer click after input blur, repeated naming, immediate shortcuts after closing dialogs, and controls clipped before automatic scrolling/focus. Include relevant repeated use, interruption, reload/persistence and failure behavior.

For ticket changes, distinguish deliberate repeated submissions from accidental double clicks, and check editing, limit acknowledgement and unit round trips. For panes and layouts, diagnostics such as `window.KarimUI.getDiagnostics()` and `getGeometry()` supplement observed pointer/keyboard behavior; they do not replace it. Keep demo/direct-file operation API-free and use explicitly scoped, backend-shaped fixtures for connected validation.

Report the validation actually performed and its limits. Mocks establish only their local contract scenario, not compatibility with Karim's production server. Preserve independent review and the common publication contract. A skill-only edit does not require running or modifying the application.

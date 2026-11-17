---
name: component-builder
description: Build or revise Helix panes, charts, tables and workspace layouts while preserving registration, data provenance, shared polling and project boundaries. Use only for tradinginterface.
---
# Helix components

Read the [Helix profile](../../../profiles/tradinginterface.md), the owner's `CLAUDE.md` and relevant architecture instructions. Resolve project paths against `/Users/omarkhalil/GitHub/tradinginterface`. Use the common coding method and native independent review; this skill supplies the Helix-specific decisions.

## Extend the current interface

Locate the actual workspace, widget and layout registration. Extend the existing modules and preserve widget IDs, layout identities and `helix.*` persistence formats. Use the typed exports in `src/engine/registry.ts`; `src/workspaces/markets/index.ts` demonstrates registration. Do not restore migration-era barrels or depend on browser-global compatibility aliases.

Reuse `src/ui/Pane.tsx` and its current types. Its source metadata uses `sources: string[]`, not the former singular `source` prop. Inside `ModularGrid`, the slot owns the chrome: `Pane` publishes response sources and subtitle without adding a second header. Retain timestamps, units, run identity and freshness indicators.

Read current tokens in `src/styles/tokens.css` and extend the owning style module. Preserve the desktop density, semantic colours, numeric alignment/typography and accessible controls. Reuse `src/ui/icons.tsx` and the existing hand-written SVG/canvas chart kit; do not introduce a chart library or hardcoded visual constants. Source badges must describe the actual response: a fixture or simulation must not appear live.

## Preserve state and lifecycle

Use the existing API client and `createPolledStore`/`usePolled` in `src/lib/store.ts`. Preserve single-flight requests, shared subscriber-owned timers, invalidation ordering and cleanup. Distinguish an initial failure from stale last-good data, and make both visible. Avoid a separate polling loop per component or synthetic fallback for a failed connected feed.

Keep live server state, persisted user/workspace state and ephemeral view state distinct. Preserve cancellation, resource release and the user's drafts, focus and layout when components remount or hide. Demonstration data belongs in an explicit fixture/demo path, with its origin visible.

## Respect backend and execution boundaries

Backend changes need their own exact scope and current owner contracts. Preserve `routers → services → bridges`, synchronous market-data requests, vendor quotas and shared cache/usage-ledger ownership. Do not add streaming, extra backend replicas, another state framework or an authentication stack merely because a pane needs data.

Distinguish authentication from application authorization: the documented Cognito deployment is a trusted shared workspace, not per-user account isolation. Do not expose server credentials to the frontend. Keep the T212 execution freeze and all live-trading switches intact; UI work is no authorization for broker execution or new order paths. Preserve the mandatory `uv run --no-sync` backend launch convention.

## Evidence

Use static inspection and independent review within the authorized task. Create, change or run tests only when Omar explicitly requests them. Report the verification actually performed and any unmet required gate; file presence, types and configuration alone do not establish runtime behavior.

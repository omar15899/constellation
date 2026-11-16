---
name: helix-backend-foundation
description: Specialized architecture-and-implementation workflow for transforming a frontend/demo prototype into a real backend-capable application foundation. Use this skill whenever a project needs to move from fake/mock data, no auth, no persistence, and no real-time architecture into a grounded system with real authentication, database persistence, backend API boundaries, and WebSocket/event-stream live data. Trigger on: "add auth", "add a database", "make this real", "persist user strategies/settings/layouts", "add websockets", "real-time data", "wiring up a backend", "stop using fake data", "move from prototype to production", "I want real users", "make this production-ready", "add login", "persist this across sessions", "hook up a real API", "I need a backend", any request that implies the prototype-to-real-system transition for a trading interface, dashboard, or internal operational tool.
---

# Helix Backend Foundation

Architecture and implementation skill for the most important transition in a project's lifecycle: moving from a working frontend demo to a grounded, backend-capable system.

This skill governs the transformation of a prototype with fake data, no auth, and no persistence into a system with:
- real authentication and user identity
- database-backed persistence
- typed API boundaries
- a real-time transport layer
- clean separation between what is live, what is persisted, and what is derived

## Relationship to `/helix-artisan`

This skill is a specialization, not a replacement. When touching UI code, component architecture, JSX, CSS, or TypeScript craft during implementation, follow the standards defined in `/helix-artisan`. That skill governs code quality. This skill governs the system transformation.

Do not duplicate implementation craft guidance here. Import it by reference.

---

## Why this transition matters

A prototype has a structural lie at its core: it looks like a real system but is built on fake state. Every user action that should persist does not. Every "live" value is generated randomly. The gap between the demo and the real tool is not a matter of adding features — it requires replacing the structural foundation.

The risk here is half-measures: adding a login page that does not actually authenticate, wiring "real data" that is still random, or using localStorage as a database. These create the appearance of progress while making the actual transition harder. This skill is designed to prevent that.

---

## The three-state principle

This is the single most important architectural constraint. Before writing a line of implementation code, map every piece of state in the system to one of these three categories:

**1. Live market state** — ephemeral data from a streaming source. Price feeds, order book updates, tick data, system health events. This state is *received*, not *fetched*. It is not persisted — you consume it and it passes through. Persisting it is a separate pipeline concern (time-series DB, data lake), not a UI concern.

**2. Persisted user/application state** — database-backed state that belongs to a user and survives sessions. Strategies, watchlists, saved layouts, settings, preferences, positions (if the system tracks them). This state must be read from and written to a real store. It cannot live in `useState` alone, and it must not be conflated with live market state.

**3. Derived or view UI state** — transient state that is computed from categories 1 and 2. Filter selections, sort order, currently selected row, hover state, expanded/collapsed panels. This lives in component state or the URL. It does not need to be persisted (unless the user explicitly saves a "view configuration"), and it does not come from the server.

Mixing these three causes almost every architectural problem in demo-to-real transitions. The key symptom: a component that receives a WebSocket update and also reads from localStorage and also derives a computed value from a React state variable, with no clear mental model of which is which.

Read `references/state_separation.md` for detailed guidance on where each type lives and how they interact.

---

## Execution phases

Every backend foundation task follows these phases in order. Do not compress them.

### Phase 1 — Repository audit

Read the project before proposing anything.

Produce a written audit covering:
- **Fake-data entry points** — where is fake data generated? LCG seeds, `Math.random()`, hardcoded arrays, mock JSON. These are the replacement targets.
- **Implied domain entities** — what does the UI already model? Positions, strategies, instruments, watchlists, orders? These are your schema seeds.
- **Current state model** — where does state live? `useState` in components? A top-level object? localStorage? Identify what is local UI state, what should be persisted, and what should be streamed.
- **User flows and routing** — what does the user navigate? Which screens require authentication to be meaningful? Which state should be user-scoped?
- **Existing backend scaffolding** — is there any? An existing API, a partial schema, auth wiring that's half-done? Identify what to build on vs. what to replace.
- **Conflation points** — where are backend concerns baked into the UI? A component that constructs a data shape that should come from the API, or applies business rules that belong in the domain layer.

Do not skip this step. The audit determines the correct sequence of implementation phases and prevents building a backend layer that is incompatible with the frontend's assumptions.

### Phase 2 — Target architecture

Produce an architecture proposal before writing any implementation.

The proposal must define:
- **Auth boundary** — how users are authenticated, what the session/token model is, which routes are protected, how the frontend carries identity to the backend.
- **Database model** — which entities exist, how they are related, which are user-scoped, which are shared. A rough schema is enough at this stage — not a full migration file.
- **API surface** — what endpoints or RPC methods the frontend calls for CRUD on persisted state. REST or tRPC or GraphQL — choose one and be consistent.
- **Real-time transport** — what events flow over WebSocket or SSE, what the message schema looks like, how the frontend subscribes and handles updates.
- **Frontend state integration** — how the three state types wire together in the React layer. Which hooks handle live data, which handle persisted data, which handle UI state.
- **User-specific persistence** — what objects are user-owned, what their schema looks like, whether lightweight versioning is warranted.

Present this to the user before implementation. Architecture disagreements are cheap to resolve in a document; they are expensive to resolve after a DB migration.

See `references/state_separation.md`, `references/auth_patterns.md`, `references/persistence_schema_guidelines.md`, `references/realtime_transport_architecture.md`.

### Phase 3 — Staged implementation plan

Break the transformation into a sequence of phases, each of which leaves the system in a coherent runnable state.

A typical sequence:

| Phase | What happens |
|---|---|
| Auth foundation | User model, sign-up/in/out, session/token layer, protected routes |
| Schema + migrations | Database schema for domain entities, migration tooling |
| API layer | Backend routes/handlers for persisted state CRUD |
| Persistence wiring | Frontend hooks that read/write through the API instead of fake data |
| Real-time transport | WebSocket/SSE server, event model, frontend subscription layer |
| Live data integration | Replace fake streaming with real-time consumption |
| User domain objects | Strategies, watchlists, layouts — full round-trip from DB to UI |
| Finalization | Audit, cleanup, handoff documentation |

The sequence is not rigid — adapt it to what the project needs. But each phase must end with the system running correctly, not just "the migration is in progress."

See `references/migration_from_demo_to_real.md` for migration patterns and adapter strategies.

### Phase 4 — Implementation

Execute the staged plan. For each phase:
- Implement one logical unit at a time.
- Replace fake data structures progressively, not all at once.
- Use adapter patterns to isolate the fake-to-real transition boundary — the UI should not need to change when the data source changes, only the hook/service layer.
- Keep the frontend compilable and runnable at each step. A broken frontend during a backend migration is a morale and debugging liability.
- Follow `/helix-artisan` implementation standards for all code written.

Specific implementation guidance is in the reference documents:
- Auth: `references/auth_patterns.md`
- Schema and persistence: `references/persistence_schema_guidelines.md`
- Real-time: `references/realtime_transport_architecture.md`
- State integration: `references/state_separation.md`

### Phase 5 — Finalization

Produce a handoff summary covering:
1. **What changed** — what was fake and is now real
2. **What is still pending** — what remains mocked, what needs vendor credentials, what is intentionally deferred
3. **How to run the system** — environment setup, env vars, dev server commands, database setup steps
4. **System structure** — a brief map of what lives where (backend routes, schema location, transport layer, frontend hooks)
5. **Extension points** — how to add a new persisted entity, how to add a new real-time event type, how to extend the auth model

This summary is the difference between a completed backend foundation and a completed backend foundation that the next engineer can work with.

---

## Auth requirements

See `references/auth_patterns.md` for detailed patterns.

The minimum viable auth implementation:
- Real user identity (not simulated)
- Sign up, sign in, sign out
- Session or token with a defined lifecycle
- Protected routes that redirect unauthenticated users
- Backend routes that reject unauthenticated requests
- User ID propagated to all persisted state

Do not:
- Use localStorage as a session store
- Hardcode test credentials and call that "auth"
- Leave unprotected routes that should require authentication
- Conflate "user is logged in" (UI state) with "request is authenticated" (backend state)

---

## Persistence requirements

See `references/persistence_schema_guidelines.md` for schema patterns.

The minimum viable persistence layer:
- A real database (relational preferred for structured domain entities)
- A migration system (so the schema is versioned and reproducible)
- User-scoped entities with proper foreign keys
- An API layer that mediates all access — no direct DB access from the frontend

Do not:
- Use localStorage as the persistence layer for domain entities
- Dump everything into a single JSON blob per user unless the entity genuinely has schemaless structure
- Skip migrations and rely on "just recreate the DB" during development

---

## Real-time transport requirements

See `references/realtime_transport_architecture.md` for architecture patterns.

The minimum viable real-time layer:
- A defined event/message schema (not raw JSON blobs)
- A server-side transport (WebSocket or SSE)
- A client-side subscription hook that is separate from UI components
- A clear adapter boundary between the transport and the data shapes the UI consumes

Do not:
- Create a WebSocket server that streams random numbers and call it "live data integration"
- Inline WebSocket logic in components
- Use a single catch-all message type for all events

If real vendor credentials or data sources are not yet available, create an adapter boundary with a typed stub. The stub should produce realistic, schema-valid data — not random noise. This makes the real integration a one-file swap.

---

## Playwright gate (mandatory before every UI commit)

Any commit touching `src/`, `index.html`, or `vite.config*` is blocked by the `playwright_gate.py` pre-commit hook unless the full test suite passes. This applies even when the backend work is the primary change — if a migration or API wiring accidentally breaks the frontend, the gate catches it.

Run manually:
```bash
npx playwright test
```

The suite checks: app mounts without JS errors, all three workspaces render and switch cleanly, chrome dimensions hold (topbar 40px, pane headers 28px, status bar 22px). If a test fails, fix the code. The only valid edit to `tests/helix.spec.js` is adding coverage.

---

## Anti-goals

This skill actively resists these common failure modes:

- **Fake auth** — a login form that sets `isLoggedIn: true` in React state and routes accordingly. This is not auth.
- **localStorage as database** — workable for UI preferences, not for domain entities that must be server-authoritative.
- **Random-number WebSocket** — a streaming endpoint that pushes `Math.random() * 100` every 500ms is not a real-time architecture.
- **Monolithic backend** — a single 2000-line `server.js` with all routes, all business logic, and no boundaries is not an API layer.
- **Backend logic in components** — a React component that constructs raw SQL or makes direct fetch calls to external data vendors is the wrong layer.
- **Demo preservation** — if the correct move is a meaningful refactor of the demo architecture, make the refactor. Do not bolt real infrastructure onto a fundamentally fake structural foundation.
- **Enterprise overengineering** — this skill produces a *foundation*, not a SOA diagram. A clean Express + Postgres + WebSocket stack is a correct answer. A 12-service microservices mesh is not.

---

## Reference documents

| Document | When to read |
|---|---|
| `references/auth_patterns.md` | Choosing auth strategy, implementing sign-up/in/out, session/token lifecycle, protected routes |
| `references/persistence_schema_guidelines.md` | Schema design for domain entities, migration approach, user-scoped data, versioning |
| `references/realtime_transport_architecture.md` | WebSocket/SSE architecture, event model, adapter pattern, frontend subscription |
| `references/state_separation.md` | Mapping state to live / persisted / derived, integration patterns, common conflation mistakes |
| `references/migration_from_demo_to_real.md` | Progressive migration strategy, adapter boundaries, fake-to-real replacement patterns |

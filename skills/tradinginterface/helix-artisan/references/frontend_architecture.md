# Frontend Architecture Reference

Deep guidance on application structure, layer separation, naming, and refactoring discipline.

---

## Layer separation

A frontend application has distinct layers. Mixing them is the most common source of fragile, hard-to-change code.

### The layers

**UI layer** — Components that render. They receive data through props or hooks, and return JSX. They know about layout, visual state, interaction events. They do not know about API endpoints, business rules, or database shapes.

**Application state layer** — Coordinates what the user is doing right now: which view is active, what is selected, which drawer is open, whether a form is submitting. In React this lives in `useState`/`useReducer` at the appropriate ancestor, or in a state manager for global state.

**Domain logic layer** — Business rules and derivations: calculating P&L, determining whether an order is valid, aggregating a position from trades. These are pure functions. They do not touch React, they do not touch the DOM, they are independently testable.

**Data access layer** — API calls, WebSocket subscriptions, cache management. Encapsulated in hooks or service functions. Components call a `useTrades()` hook — they do not call `fetch('/api/trades')` inline.

**Persistence layer** — localStorage, sessionStorage, IndexedDB. Components do not read/write persistence directly. A hook or service mediates access.

### Practical tests

- "Can I test this function without rendering anything?" → domain logic candidate
- "Does this component need to know the API URL?" → no, it should call a hook
- "Does this hook contain any JSX?" → no, it is not a component
- "Can this component render with any data source, real or mocked?" → yes, if the layers are clean

---

## File and folder structure

Structure should communicate ownership and purpose at a glance.

### Principles

**Match exports to files.** A file named `PositionTable.tsx` exports `PositionTable`. A file named `usePositions.ts` exports `usePositions`. Avoid files that export 10 unrelated things.

**Domain directories over type directories.** Prefer:
```
src/
  positions/
    PositionTable.tsx
    usePositions.ts
    positions.types.ts
    positions.utils.ts
```
Over:
```
src/
  components/
    PositionTable.tsx
  hooks/
    usePositions.ts
  types/
    positions.ts
```
Type-based directories scatter related code. Domain directories keep related code together.

**Colocation.** If a component, its hook, and its types are only used together, put them in the same directory or even the same file. Move them apart only when they are genuinely reused across domains.

**Barrel files (`index.ts`) are optional.** They help public module APIs but add indirection for internal code. Do not create them reflexively.

### When to split a file

- The file is over ~300 lines and the split corresponds to a real domain boundary (not just "it's long")
- Two parts of the file are used independently by different consumers
- The file mixes two different layers (renders AND fetches, for example)

Do not split files because they "feel big." Long, focused files are better than many tiny files with no clear reason to exist.

---

## Naming

Naming is design. A good name makes the code's intent visible without a comment.

### Components

`PascalCase`. Names should be noun phrases describing what the component represents, not what it does.

- `PositionTable` — a table showing positions
- `OrderEntryForm` — a form for entering orders
- `SpreadMonitorPane` — a pane showing spread monitoring

Avoid: `DataWrapper`, `TableContainer`, `MyComponent`, `New[Anything]`

### Hooks

`useCamelCase`. The name should complete the sentence "this hook gives me ___".

- `usePositions` — gives me the current positions
- `useOrderBook` — gives me the live order book
- `useKeyboardShortcut` — gives me keyboard shortcut registration

### Functions and utilities

`camelCase`. Verb phrases for transformations, noun phrases for derivations.

- `calculatePnL(position)` — computes something
- `sortByExpiry(instruments)` — transforms something
- `isExpired(instrument)` — tests something

### Types and interfaces

`PascalCase`. Represent domain concepts, not implementation details.

- `Position`, `OrderBook`, `Instrument`, `Trade`
- Not `IPosition`, `TOrderBook`, `PositionData`

### Constants

`SCREAMING_SNAKE_CASE` for truly global constants. `camelCase` for module-scoped values that are effectively constants. Use judgment — a `const MAX_SPREAD = 0.05` near the function that uses it does not need to be `MAX_SPREAD`.

---

## Refactoring discipline

Refactoring is a professional obligation, not optional cleanup. But it requires judgment.

### When to refactor

**Refactor now:**
- The structure is so wrong that adding correct code on top of it is not possible
- You are about to duplicate structural logic for the third time
- A bug was caused by the structural problem, not the symptom you were asked to fix

**Propose, then refactor:**
- The structure is wrong but the current task could work around it
- The refactor is larger than the task that surfaced it
- Surface the issue to the user, explain the tradeoff, let them decide when

**Do not refactor:**
- Because the code "feels messy" without a concrete harm
- When it would break other in-progress work
- When you are on a deadline and the task is a patch, not a rewrite

### How to refactor

**One concern at a time.** A refactor that moves code, renames things, and changes behavior simultaneously is a debugging nightmare. Separate the moves from the behavioral changes — each gets its own commit.

**Preserve behavior at each step.** A refactor that changes structure should not change outputs. If you cannot verify this, you are combining refactor and feature work.

**Start with types.** In a TypeScript codebase, getting the types right first surfaces most structural problems before you write a single line of implementation.

**Refactor toward the seam.** Identify the boundary you want to create (e.g., "data access should be here, not there") and move code incrementally toward that boundary. Do not attempt a full restructure in one step.

### What not to do

- Do not rename symbols gratuitously. Rename when the name is wrong, not when you prefer a different style.
- Do not extract tiny helpers that are only called once and add no clarity. Indirection costs.
- Do not add abstractions "for future use." Abstract when the abstraction is needed now.
- Do not refactor and fix bugs in the same commit. The commit history loses meaning.

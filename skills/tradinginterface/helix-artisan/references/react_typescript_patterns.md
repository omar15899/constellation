# React and TypeScript Patterns

Concrete craft standards for writing clean React and TypeScript in production frontends.

---

## React component design

### The single responsibility rule, applied

A component has one job. The test: if you had to explain what the component does and you needed the word "and", it has two jobs.

- `PositionTable` renders a list of positions. It does not fetch them. It does not sort them (unless sorting is purely visual).
- `usePositions` provides positions. It does not render anything.
- `sortPositionsByExpiry` transforms a list. It is a pure function, not a hook, not a component.

### Presentation vs. container

**Presentation components** — receive all data via props, return JSX, contain no side effects, no data fetching, no direct state management beyond local UI state (hover, focus, open/closed).

**Container components / hooks** — coordinate data and pass it down. The goal is that presentation components are fully dumb: given the same props, they always render the same thing.

This separation is not about creating two files for every component. It is about knowing which kind of code belongs where. A `PositionTable` that receives `positions: Position[]` and `onRowClick: (id: string) => void` is presentation code. The same component containing `const { data } = useFetch('/api/positions')` is a container — and the two concerns should be separated.

### Props

**Keep prop surfaces minimal.** If a component accepts 8+ props, it is probably doing too many jobs, or the props should be grouped into an object representing a domain entity.

**Use explicit types, not `object` or `Record<string, unknown>`.**
```typescript
// Bad
function OrderRow({ order }: { order: Record<string, unknown> }) {}

// Good
function OrderRow({ order }: { order: Order }) {}
```

**Avoid boolean props that flip meaning.**
```typescript
// Bad — the reader must remember what `inverted` means
<PriceCell value={price} inverted />

// Good
<PriceCell value={price} side="ask" />
```

**Event handlers should be named `onNoun` or `onNounVerb`:**
- `onRowClick`, `onOrderSubmit`, `onFilterChange`
- Not `handleClick`, `click`, `doThing`

### State

**State lives at the right level.** State that only one component needs lives in that component. State that two sibling components share lives in their common ancestor. State that is truly global (auth, theme, global filters) lives in a context or external store — but reach for global state last, not first.

**Do not synchronize state.** Derived values should be derived, not stored. If you have `items` and `filteredItems` in state and a `useEffect` that syncs them, you have one piece of state and one derived value masquerading as two pieces of state.
```typescript
// Bad
const [items, setItems] = useState<Item[]>([]);
const [filteredItems, setFilteredItems] = useState<Item[]>([]);
useEffect(() => setFilteredItems(items.filter(predicate)), [items]);

// Good
const [items, setItems] = useState<Item[]>([]);
const filteredItems = useMemo(() => items.filter(predicate), [items]);
```

**`useEffect` is for synchronization with external systems**, not for reacting to state changes. If your `useEffect` has no dependency on an external system (DOM, timer, subscription, API), question whether it should be an effect at all.

### Hooks

A custom hook is justified when:
- The logic is shared across multiple components
- The logic is complex enough that embedding it in the component would obscure the component's purpose
- The logic has its own lifecycle (subscriptions, timers, cleanup)

A custom hook is not justified just to "move code out of the component" for tidiness. A 10-line calculation inside a component is fine. A 100-line data fetching and transformation pipeline probably belongs in a hook.

---

## TypeScript

### Types as domain documentation

Types are the most valuable documentation in a TypeScript codebase because they are checked. They should express what the domain looks like, not just what the compiler needs.

```typescript
// Structurally correct but meaningless
function getSpread(a: number, b: number): number {}

// Documents the domain
function getSpread(bid: Price, ask: Price): Spread {}
```

Use type aliases for domain concepts even when the underlying type is a primitive:
```typescript
type InstrumentId = string;
type Price = number;
type Quantity = number;
```

This costs nothing at runtime and makes function signatures self-documenting.

### Interfaces vs. type aliases

Use `interface` for object shapes that represent domain entities — things that will be implemented, extended, or passed around as contracts.

Use `type` for:
- Union types: `type Side = 'bid' | 'ask'`
- Mapped types: `type Partial<T> = { [K in keyof T]?: T[K] }`
- Intersections: `type AdminUser = User & { permissions: Permission[] }`
- Computed/conditional types

The distinction is not about preference — it is about what the type means. An `Order` is an interface. A `Side` is a type alias.

### Avoiding `any`

`any` disables type checking for everything it touches — including the code that uses the `any` value downstream.

**At runtime boundaries** (API responses, localStorage, user input), use `unknown` and validate before narrowing:
```typescript
const raw: unknown = JSON.parse(localStorage.getItem('positions') ?? 'null');
if (isPosition(raw)) {
  // raw is now Position
}
```

**Never use `as T` to silence a type error** unless you are at a genuine boundary where you know more than the compiler. If you are using `as` to fix a "type mismatch", the types are probably wrong.

### Discriminated unions for state machines

Avoid boolean flag combinations to represent component state:
```typescript
// Bad — 4 booleans create 16 possible states, most of which are invalid
interface FetchState {
  loading: boolean;
  error: boolean;
  data: Position[] | null;
  empty: boolean;
}

// Good — only valid states are representable
type FetchState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'success'; data: T };
```

### Exhaustiveness

Use `never` to ensure all union members are handled:
```typescript
function formatSide(side: Side): string {
  switch (side) {
    case 'bid': return 'Buy';
    case 'ask': return 'Sell';
    default: {
      const _exhaustive: never = side;
      throw new Error(`Unhandled side: ${_exhaustive}`);
    }
  }
}
```

This ensures that if `Side` gains a new member, the compiler points to every place that needs updating.

### Generic constraints

Prefer specific constraints over `any` or unconstrained generics:
```typescript
// Too permissive
function pick<T>(obj: T, key: string): any {}

// Correct
function pick<T extends object, K extends keyof T>(obj: T, key: K): T[K] {}
```

---

## Component composition patterns

### Compound components

When a component has complex internal structure with multiple interacting parts, use compound components rather than a prop-per-feature API:
```typescript
// Bad — prop explosion
<DataTable
  showHeader
  showFooter
  headerSticky
  footerContent={<Pagination />}
  emptyState={<EmptyMessage />}
/>

// Good — composed structure
<DataTable>
  <DataTable.Header sticky />
  <DataTable.Body emptyState={<EmptyMessage />} />
  <DataTable.Footer>
    <Pagination />
  </DataTable.Footer>
</DataTable>
```

### Render props and slot patterns

When a component needs to delegate rendering of a sub-section without knowing what goes there, use children or named render props rather than passing components as props through several layers.

### When to stop abstracting

An abstraction is justified when it reduces genuine duplication and the API is stable. It is not justified when:
- The "duplication" is only visual similarity (two things that look alike but do different things)
- The abstraction requires more config props than the concrete implementation it replaces
- The abstraction has only one consumer

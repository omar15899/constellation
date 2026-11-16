# State Separation

The three-state model for real-time, data-intensive applications. This is the foundational architectural principle for any system that combines live market feeds, user-specific persistence, and a UI.

---

## The three categories

### 1. Live market state

**Definition:** Data that arrives from an external streaming source. Price feeds, order book snapshots and deltas, tick data, system alerts, real-time analytics. This data is *received*, not *owned*.

**Characteristics:**
- Ephemeral — individual updates are not meant to be stored in the application state layer
- High velocity — can arrive many times per second
- Authoritative at the source — your application is a consumer, not the authority
- Stateless from the persistence perspective — you do not write this to your database (unless you're building a time-series database, which is a separate system)
- Can become stale — a price update from 5 seconds ago is not the current price

**Where it lives:**
- In-memory, in a service layer (`MarketDataService`, `FeedAdapter`)
- In component-local state when consumed by UI (`useState` updated by a subscription hook)
- Potentially in a shared store if multiple components need the same live value

**Does not live in:**
- The database (application database, not time-series database)
- localStorage
- URL state
- Persisted React state

---

### 2. Persisted user/application state

**Definition:** Data that belongs to a user or the application and must survive sessions, reloads, and device changes. Strategies, watchlists, saved layouts, user settings, preferences, application configuration.

**Characteristics:**
- User-owned and user-scoped
- Durable — must be readable in the next session
- Server-authoritative — the database is the source of truth
- Slow-changing — user modifies this explicitly, not continuously
- Must be versioned or auditable in some cases (strategy history)

**Where it lives:**
- The database (primary source of truth)
- In-memory in the React application as a cache of the server state (hydrated from the API on load, updated optimistically on mutation)
- Managed by data-fetching hooks (`useStrategies`, `useWatchlist`)

**Does not live in:**
- `useState` alone (not durable across sessions)
- localStorage (not server-authoritative, not shared across devices)
- The WebSocket connection (not appropriate for request-response patterns)

---

### 3. Derived or view UI state

**Definition:** Transient state that is computed from categories 1 and 2, or that represents the user's current interaction state. Which row is selected, which tab is active, which filter is applied, whether a dropdown is open, what text is in a search field.

**Characteristics:**
- Derived or ephemeral — either computable from other state, or meaningless outside the current session
- No persistence required (unless the user explicitly saves a "view configuration")
- Component-local or navigation-state-level
- Does not come from the server; does not go to the server

**Where it lives:**
- `useState` in the component that owns it
- URL params (for state that should survive navigation or be shareable: selected instrument, active workspace)
- URL hash (for scroll position)

**Does not live in:**
- The database (unless it's been explicitly "saved" as a layout or preference)
- A global store (unless it's genuinely application-wide state like a selected theme)
- The WebSocket connection

---

## Why this matters

The most common architectural problem in demo-to-real transitions is collapsing these three categories together. This happens in several recognizable patterns:

### Pattern 1: Using useState as a database

```typescript
// Wrong: treating component state as the source of truth for persisted data
function StrategyPanel() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  
  const addStrategy = (s: Strategy) => setStrategies(prev => [...prev, s]);
  // This strategy is lost on page reload
}
```

The symptoms: "data disappears on refresh", "changes don't sync between tabs", "we can't share state between users".

The fix: persisted state lives in the database. The component's `useState` holds a *local copy* that is read from the API on mount and updated on mutation. The database is always the source of truth.

### Pattern 2: Persisting live market state

```typescript
// Wrong: writing every price tick to the database
ws.on('price.update', (update) => {
  setPriceState(update);           // ok: update live display
  localStorage.setItem('lastPrice', JSON.stringify(update));  // wrong: persistence for a live value
  await db.prices.insert(update);  // maybe ok if this is a time-series store, definitely wrong if it's the same user DB
});
```

The symptoms: database write storms, stale "last price" data that is wrong as soon as the market moves, conflated state that makes it impossible to answer "what is the current price" vs. "what was the saved price".

The fix: live market state is received and displayed. It is not persisted by the application layer. If you need a "last known price" for display, keep it in memory in the service layer. If you need historical prices, that is a time-series database, not your application database.

### Pattern 3: Deriving everything in the component

```typescript
// Wrong: mixing all three state types in one component
function TradingDashboard() {
  const [price, setPrice] = useState(null);           // live market state
  const [strategies, setStrategies] = useState([]);   // persisted state (wrong layer)
  const [activeTab, setActiveTab] = useState('market'); // UI state
  const [filter, setFilter] = useState('active');     // UI state
  
  // All loaded and mixed in the same useEffect
  useEffect(() => {
    subscribeToPrice('AAPL', setPrice);
    fetch('/api/strategies').then(r => r.json()).then(setStrategies);
  }, []);
}
```

The symptoms: impossible to understand which state is fresh, stale, or stale-by-design; impossible to test; impossible to extract either concern.

The fix: each type of state has its own hook with its own lifecycle.

---

## Integration pattern

How the three state types compose in a well-structured component:

```typescript
function PositionPane({ instrumentId }: { instrumentId: string }) {
  // 1. Live market state — subscription hook, ephemeral
  const price = usePriceFeed(instrumentId);
  
  // 2. Persisted user state — data-fetching hook, database-backed
  const { positions, updatePosition } = usePositions();
  
  // 3. Derived UI state — component-local, ephemeral
  const [selectedRow, setSelectedRow] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<keyof Position>('instrument');
  
  // Derived value (from persisted state) — computed, not stored
  const sortedPositions = useMemo(
    () => [...positions].sort((a, b) => compare(a[sortKey], b[sortKey])),
    [positions, sortKey]
  );
  
  // Derived value enriched with live data (merge live + persisted)
  const enrichedPositions = useMemo(
    () => sortedPositions.map(pos => ({
      ...pos,
      currentPrice: pos.instrument === instrumentId ? price?.mid ?? pos.lastPrice : pos.lastPrice,
      unrealizedPnL: price ? (price.mid - pos.avgPrice) * pos.quantity : pos.unrealizedPnL,
    })),
    [sortedPositions, price, instrumentId]
  );
  
  return (
    <PositionTable
      positions={enrichedPositions}
      selectedRowId={selectedRow}
      onRowSelect={setSelectedRow}
      sortKey={sortKey}
      onSort={setSortKey}
      onPositionUpdate={updatePosition}
    />
  );
}
```

The component does not need to know about WebSockets, database queries, or API calls. It composes three hooks and produces a view.

---

## State type decision tree

When deciding where a piece of state belongs:

1. **Is it received from a streaming source?** → Live market state. Keep in memory, do not persist to database.

2. **Does it need to survive a page reload?** → Persisted state. It must live in the database and be loaded via the API.

3. **Is it specific to this user's session?** → If yes and must persist: database with user_id FK. If yes and ephemeral: component state or URL.

4. **Can it be computed from other state?** → Derived value. Do not store it. Compute it in `useMemo` or a selector function.

5. **Does it affect the URL?** → URL state (for navigability and shareability). React Router's `useSearchParams` or path params.

6. **Is it only relevant to this component right now?** → Component-local `useState`.

---

## The full picture

```
External data source
         │ WebSocket / SSE
         ▼
┌────────────────────┐
│ MarketDataService  │ ─── Live market state
│ (in-memory only)   │     (never persisted to app DB)
└────────┬───────────┘
         │ subscription hooks (usePriceFeed, useOrderBook)
         ▼

React components ◄── Derived UI state (useState, useMemo)

         ▲
         │ data-fetching hooks (useStrategies, useWatchlist)
┌────────┴───────────┐
│    API layer       │ ─── Persisted user/app state
│  (HTTP REST / RPC) │     (database is source of truth)
└────────┬───────────┘
         │
┌────────┴───────────┐
│    Database        │
└────────────────────┘
```

Each layer has one job. The WebSocket path never touches the database. The database path never receives WebSocket messages. The UI composes from both.

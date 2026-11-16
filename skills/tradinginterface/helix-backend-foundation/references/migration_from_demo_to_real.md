# Migration from Demo to Real

Practical patterns for transforming a frontend prototype with fake data into a grounded system with real infrastructure. The goal is an incremental, always-runnable migration — not a big-bang rewrite.

---

## The fundamental challenge

A demo is built on a lie: fake data generators, localStorage pretending to be a database, mock functions pretending to be API calls. This is fine for demos. The problem comes when you try to layer real infrastructure on top of the lie without fixing the lie first.

The correct approach is not to bolt a database onto a demo. It is to identify the lie, fix the structural boundary, and replace the fake implementation with a real one — one concern at a time.

---

## The adapter boundary

The most important pattern in demo-to-real migration is the adapter boundary. Before migrating anything, introduce an explicit service layer that the UI already calls. The fake implementation goes behind this layer; the real implementation replaces it.

### Before: fake data in the component

```typescript
function StrategyList() {
  const [strategies, setStrategies] = useState(() => generateFakeStrategies(42)); // LCG seed
  // UI is directly coupled to the fake implementation
}
```

### Step 1: Introduce the service boundary

```typescript
// src/services/strategyService.ts
export interface StrategyService {
  list(): Promise<Strategy[]>;
  create(strategy: Omit<Strategy, 'id' | 'createdAt'>): Promise<Strategy>;
  update(id: string, patch: Partial<Strategy>): Promise<Strategy>;
  delete(id: string): Promise<void>;
}

// src/hooks/useStrategies.ts
export function useStrategies() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    strategyService.list().then(setStrategies).finally(() => setLoading(false));
  }, []);
  
  return { strategies, loading };
}
```

### Step 2: Implement the fake service (existing behavior, new location)

```typescript
// src/services/fakeStrategyService.ts
export const fakeStrategyService: StrategyService = {
  list: async () => generateFakeStrategies(42),
  create: async (s) => ({ ...s, id: uuid(), createdAt: new Date().toISOString() }),
  update: async (id, patch) => { /* mutate in-memory array */ },
  delete: async (id) => { /* remove from in-memory array */ },
};
```

### Step 3: Wire the hook to the fake service

```typescript
// For now, inject the fake service
import { fakeStrategyService as strategyService } from './fakeStrategyService';
```

The UI now calls `useStrategies()` which calls `strategyService.list()`. The component does not know whether the data is fake or real. The migration is invisible from the outside.

### Step 4: Implement the real service

```typescript
// src/services/apiStrategyService.ts
export const apiStrategyService: StrategyService = {
  list: async () => {
    const res = await fetch('/api/strategies', { credentials: 'include' });
    if (!res.ok) throw new ApiError(res.status, await res.text());
    return res.json();
  },
  create: async (strategy) => {
    const res = await fetch('/api/strategies', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(strategy),
      credentials: 'include',
    });
    if (!res.ok) throw new ApiError(res.status, await res.text());
    return res.json();
  },
  // ...
};
```

### Step 5: Swap

```typescript
// Change one import
import { apiStrategyService as strategyService } from './apiStrategyService';
```

The UI does not change at all. The migration is complete for this entity.

---

## Migration sequence

Sequence matters. Dependencies determine the order: auth must come first because persisted state is user-scoped.

### Phase 1: Auth foundation (blocker for everything else)

Add auth before touching any persistence. User identity is required to scope all subsequent data operations.

1. Install and configure auth library (or implement from scratch per `auth_patterns.md`)
2. Create `users` table and migration
3. Implement sign-up, sign-in, sign-out API routes
4. Implement `useAuth` hook on the frontend
5. Add `ProtectedRoute` wrapper
6. Test the full auth lifecycle before proceeding

Do not add a fake auth boundary ("I'm logged in as user 1") as a temporary measure. The cost of real auth at this stage is low; the cost of ripping out fake auth later is high.

### Phase 2: Schema and migrations

With auth in place, design the schema for domain entities:

1. Write the schema (per `persistence_schema_guidelines.md`)
2. Set up migration tooling
3. Apply migrations to development database
4. Verify schema with seed data

At this point, the database exists and has the right tables. Nothing is wired yet.

### Phase 3: API layer

Add backend routes for CRUD on the most important domain entities first (usually strategies and watchlists):

1. Add route files for each entity
2. Apply `requireAuth` middleware
3. Implement CRUD handlers scoped to `req.user.id`
4. Test with a REST client (not the frontend yet)

This phase is backend-only. The frontend still uses fake services.

### Phase 4: Wire the frontend — entity by entity

Now swap fake services for real ones, one entity at a time. The adapter boundary makes this a series of isolated swaps:

1. Swap `strategyService` — frontend now reads/writes strategies to the API
2. Test: create, update, delete, reload — data persists
3. Swap `watchlistService`
4. Test: same
5. Continue for remaining entities

After each swap, verify the entity is fully functional before moving to the next.

### Phase 5: Real-time transport

With the REST layer working, add the real-time layer:

1. Set up the WebSocket server
2. Implement the feed adapter with a stub (per `realtime_transport_architecture.md`)
3. Add subscription management on the server
4. Add the `MarketDataService` on the frontend
5. Add subscription hooks (`usePriceFeed`, `useOrderBook`)
6. Wire components to the hooks — remove fake streaming timers

At this point, "live" data still comes from the stub adapter. The architecture is real; the data source is not yet.

### Phase 6: Real data source integration

Replace the stub adapter with the real vendor adapter:

1. Implement `VendorFeedAdapter implements FeedAdapter`
2. Normalize vendor messages to the typed event schema
3. Swap the adapter in the WebSocket server
4. Verify the full data path end-to-end

This is a one-file change at the adapter boundary.

---

## Identifying fake-data entry points

During the Phase 1 audit, locate every place fake data enters the system:

**LCG/seeded generators:**
- Grep for `Math.sin`, `Math.cos`, `seed`, `lcg`, `prng`, `faker`
- These are usually in workspace files or a `data.js` / `mockData.ts` module

**Hardcoded arrays:**
- Search for large array literals with domain objects (`instruments`, `strategies`, `positions`)
- These are direct migration targets

**`Math.random()` in rendering logic:**
- Data that should be consistent but is re-randomized on every render
- Sign that fake data is generated at render time rather than at load time

**`localStorage` reads at startup:**
- These are often the "persistence layer" in demos — data that was manually seeded once

**`setTimeout` / `setInterval` streaming simulations:**
- These simulate real-time updates with fake data; they are replaced by the WebSocket subscription layer

For each fake-data entry point, answer: *What is the real source for this data?* This answer determines whether it becomes:
- An API call (persisted user data → database → API)
- A WebSocket subscription (live market data → feed adapter → WebSocket)
- A derived computation (value computed from other data → stays in frontend logic)

---

## Keeping the app runnable during migration

The adapter boundary ensures the app is always runnable. But maintain a few other habits:

**Feature the fake service as the fallback.** If the API is not yet available, the fake service is a graceful degradation, not a dependency:

```typescript
const strategyService = config.useRealApi
  ? apiStrategyService
  : fakeStrategyService;
```

**Migrate one route at a time.** If `/api/strategies` is implemented but `/api/watchlists` is not, the strategies page can use real data while watchlists still uses fake data. This is fine — it is progress.

**Do not remove fake services until the real service is verified.** Keep the fake implementation until the real one passes a basic smoke test. Deleting it prematurely makes rollback painful.

**Use TypeScript to enforce the contract.** If `fakeStrategyService` and `apiStrategyService` both implement `StrategyService`, the TypeScript compiler enforces that they have the same interface. Drift in the fake service's return types will be caught before it causes runtime bugs in the real one.

---

## Handling legacy state shape mismatches

Demo code often accumulates informal state shapes that differ from what the real schema produces:

```typescript
// Demo shape (accumulated informally)
interface FakeStrategy {
  id: number;           // auto-increment integer
  name: string;
  params: any;          // untyped
  enabled: boolean;     // boolean instead of status enum
}

// Real schema shape
interface Strategy {
  id: string;           // UUID
  name: string;
  config: StrategyConfig;  // typed JSONB
  status: 'draft' | 'active' | 'paused' | 'archived';
  userId: string;
  createdAt: string;
  updatedAt: string;
}
```

When the shapes diverge, update the TypeScript types to match the real schema and fix compilation errors. Do not add a translation layer that maps the old shape to the new one — that layer accumulates debt and is never removed. Accept the shape mismatch as a TypeScript error, fix it throughout the codebase, and commit the fix. This is one of the legitimate "big" changes that migration sometimes requires.

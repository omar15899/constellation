# Real-Time Transport Architecture

Design and implementation patterns for the real-time data layer in trading interfaces and operational dashboards. Covers WebSocket and SSE architecture, event modeling, the adapter pattern, and frontend consumption.

---

## Table of contents
1. [Choosing a transport](#choosing-a-transport)
2. [Event model](#event-model)
3. [Server-side architecture](#server-side-architecture)
4. [The adapter pattern](#the-adapter-pattern)
5. [Frontend subscription layer](#frontend-subscription-layer)
6. [Connection management](#connection-management)
7. [Stubs and vendor-absent environments](#stubs-and-vendor-absent-environments)
8. [Common mistakes](#common-mistakes)

---

## Choosing a transport

### WebSocket
Bidirectional, low-latency, full-duplex. The right choice when:
- The frontend needs to send data upstream (order submission, subscription requests, heartbeats)
- Sub-100ms latency matters (order book, tick data)
- You have many clients and need efficient multiplexing

### Server-Sent Events (SSE)
Unidirectional (server → client), built on HTTP. The right choice when:
- The client is read-only (receives data, never sends)
- You want to avoid WebSocket infrastructure complexity
- HTTP/2 multiplexing over a single connection is acceptable

**For a trading interface with live price feeds and order books: WebSocket.** For a dashboard that displays slowly-updating metrics: SSE is sufficient.

---

## Event model

The most important design decision in the real-time layer is the event schema. Get this wrong and you end up with untyped JSON blobs and frontend code that cannot trust anything it receives.

### Typed event envelope

Every message over the transport should have the same outer envelope:

```typescript
interface WsMessage<T = unknown> {
  type: string;       // discriminant for routing
  payload: T;         // typed per event type
  timestamp: number;  // unix ms, server-assigned
  seq?: number;       // optional sequence number for ordering/gap detection
}
```

### Event type registry

Define event types as a discriminated union. This ensures exhaustive handling at the consumer:

```typescript
type MarketEvent =
  | { type: 'price.update'; payload: PriceUpdate }
  | { type: 'orderbook.snapshot'; payload: OrderBookSnapshot }
  | { type: 'orderbook.delta'; payload: OrderBookDelta }
  | { type: 'trade.print'; payload: TradePrint }
  | { type: 'system.heartbeat'; payload: { serverTime: number } }
  | { type: 'subscription.confirmed'; payload: { channel: string } }
  | { type: 'subscription.error'; payload: { channel: string; reason: string } };
```

Define the payloads as separate interfaces:

```typescript
interface PriceUpdate {
  instrumentId: string;
  bid: number;
  ask: number;
  mid: number;
  timestamp: number;
}

interface OrderBookDelta {
  instrumentId: string;
  side: 'bid' | 'ask';
  price: number;
  quantity: number;  // 0 = remove this level
  timestamp: number;
}
```

This schema is the contract between the backend and frontend. It belongs in a shared types package if the project is TypeScript end-to-end.

### Subscription model

Trading interfaces do not broadcast all market data to all clients. Clients subscribe to specific instruments or channels:

```typescript
// Client → Server: subscribe request
interface SubscribeRequest {
  type: 'subscribe';
  channels: string[];  // e.g. ['price.AAPL', 'orderbook.AAPL.L1']
}

// Client → Server: unsubscribe
interface UnsubscribeRequest {
  type: 'unsubscribe';
  channels: string[];
}
```

The server tracks which clients have subscribed to which channels and routes events accordingly. This prevents every client from receiving the entire market data firehose.

---

## Server-side architecture

The server-side real-time architecture has three responsibilities: receiving data from the vendor, managing client subscriptions, and routing data to subscribed clients.

```
Vendor Data Feed
      │
      ▼
┌─────────────────┐
│  Feed Adapter   │  Normalizes vendor-specific messages
│  (per vendor)   │  into your typed event schema
└────────┬────────┘
         │ MarketEvent stream
         ▼
┌─────────────────┐
│ Event Bus /     │  Pub/sub layer. Clients subscribe to channels.
│ Subscription    │  Fan-out to subscribed WebSocket connections.
│ Manager         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ WebSocket       │  Connection management, auth, heartbeat,
│ Server          │  message serialization
└─────────────────┘
         │
         ▼
     Clients
```

The key principle: **the feed adapter knows about vendor formats; the subscription manager knows about channels; the WebSocket server knows about connections.** These three concerns must not be conflated into a single module.

### WebSocket server (Node.js with `ws`)

```typescript
import { WebSocketServer, WebSocket } from 'ws';
import { verifySession } from './auth';

const wss = new WebSocketServer({ port: 8080 });

wss.on('connection', async (ws, req) => {
  // Authenticate the connection
  const user = await verifySession(req);
  if (!user) {
    ws.close(4001, 'Unauthorized');
    return;
  }
  
  const client = new AuthenticatedClient(ws, user);
  subscriptionManager.addClient(client);
  
  ws.on('message', (data) => {
    const message = parseClientMessage(data);
    if (!message) return;
    
    if (message.type === 'subscribe') {
      subscriptionManager.subscribe(client, message.channels);
    } else if (message.type === 'unsubscribe') {
      subscriptionManager.unsubscribe(client, message.channels);
    }
  });
  
  ws.on('close', () => subscriptionManager.removeClient(client));
});
```

---

## The adapter pattern

The adapter pattern is the most important structural decision for the real-time layer. It isolates vendor-specific message formats from the rest of the system.

```
Vendor SDK / REST / FTP
         │
         ▼
┌─────────────────────────────────┐
│         Feed Adapter            │
│  - implements FeedAdapter       │
│  - translates vendor → domain   │
│  - normalizes timestamps        │
│  - handles vendor reconnection  │
└────────────────┬────────────────┘
                 │ Observable<MarketEvent>
                 ▼
          Rest of system
```

```typescript
interface FeedAdapter {
  subscribe(channel: string): void;
  unsubscribe(channel: string): void;
  events$: Observable<MarketEvent>; // or EventEmitter, or AsyncIterable
  connect(): Promise<void>;
  disconnect(): void;
}
```

With this interface, the rest of the system never touches the vendor SDK directly. To swap vendors or add a second feed, you implement a new adapter.

This also makes the stub trivial:

```typescript
class StubFeedAdapter implements FeedAdapter {
  // Emits realistic, schema-valid synthetic data on a timer
  // Deterministically seeded for consistent development behavior
  // NOT random noise — realistic market microstructure (bid/ask spread, mid drift)
}
```

---

## Frontend subscription layer

The frontend should not connect to WebSockets directly in components. The real-time layer is a service that components subscribe to.

### WebSocket service

```typescript
class MarketDataService {
  private ws: WebSocket | null = null;
  private subscribers = new Map<string, Set<(event: MarketEvent) => void>>();
  
  connect(url: string): void {
    this.ws = new WebSocket(url);
    this.ws.onmessage = (msg) => {
      const event = JSON.parse(msg.data) as WsMessage<MarketEvent['payload']>;
      this.dispatch(event as MarketEvent);
    };
  }
  
  subscribe<T extends MarketEvent['type']>(
    channel: string,
    type: T,
    handler: (event: Extract<MarketEvent, { type: T }>) => void
  ): () => void {
    // Register handler, return unsubscribe function
  }
  
  private dispatch(event: MarketEvent): void {
    const handlers = this.subscribers.get(event.type);
    handlers?.forEach(h => h(event));
  }
}

export const marketData = new MarketDataService();
```

### React hook for live data

```typescript
function usePriceFeed(instrumentId: string): PriceUpdate | null {
  const [price, setPrice] = useState<PriceUpdate | null>(null);
  
  useEffect(() => {
    const unsubscribe = marketData.subscribe(
      `price.${instrumentId}`,
      'price.update',
      (event) => setPrice(event.payload)
    );
    
    return unsubscribe;
  }, [instrumentId]);
  
  return price;
}
```

Components call `usePriceFeed('AAPL')` and receive typed `PriceUpdate | null`. They have no knowledge of WebSockets, message formats, or connection state.

---

## Connection management

The WebSocket connection lifecycle requires explicit management:

**Reconnection.** Network interruptions are normal. Implement exponential backoff with jitter for reconnection. Do not reconnect immediately on close — this can create a storm of connections if the server is down.

**Heartbeat / ping-pong.** Detect dead connections. The server sends a ping every 30s; clients that do not respond within 10s are disconnected. Most WebSocket libraries support this natively.

**Subscription re-establishment.** After reconnection, re-subscribe to all previously subscribed channels. The client should track its own subscription state.

**Gap detection.** If events have sequence numbers, track them. A gap (seq jumped from 100 to 103) means missed events. Request a snapshot to resynchronize.

**Backpressure.** If the frontend cannot process messages as fast as they arrive (order book with 10,000 updates/second), implement a merge/throttle layer. Sending every tick to React state will cause severe performance problems.

```typescript
// Throttle rapid price updates to UI frame rate
function useThrottledPriceFeed(instrumentId: string, intervalMs = 100) {
  const [price, setPrice] = useState<PriceUpdate | null>(null);
  const latestRef = useRef<PriceUpdate | null>(null);
  
  useEffect(() => {
    const unsubscribe = marketData.subscribe(`price.${instrumentId}`, 'price.update', 
      (event) => { latestRef.current = event.payload; }
    );
    
    const interval = setInterval(() => {
      if (latestRef.current) setPrice(latestRef.current);
    }, intervalMs);
    
    return () => { unsubscribe(); clearInterval(interval); };
  }, [instrumentId, intervalMs]);
  
  return price;
}
```

---

## Stubs and vendor-absent environments

When vendor credentials or data sources are not yet available, create a stub that:
- Implements the `FeedAdapter` interface
- Produces schema-valid, realistic synthetic data
- Uses a deterministic seed for consistent development behavior
- Simulates realistic market microstructure (bid/ask spread, mid drift, occasional spikes)

The stub is a first-class implementation, not a placeholder with random numbers. It must be realistic enough that:
- Frontend components cannot tell it from a real feed
- The frontend state management can be fully developed and tested against it
- The real adapter is a drop-in replacement, not a refactor

This is what the adapter pattern buys: the rest of the system is fully implemented before the vendor integration is complete.

---

## Common mistakes

**WebSocket logic in components.** A component that opens a `new WebSocket()` in a `useEffect` creates a new connection per mount, cannot be shared between components, and leaks connections on unmount if cleanup is incomplete.

**Untyped message handling.** Parsing WebSocket messages as `any` and accessing properties by string key is how you spend three hours debugging why a field is `undefined` in production.

**Random-number stubs.** A stub that emits `Math.random() * 100` every 500ms is not a real-time architecture stub — it is fake data that happens to arrive over a WebSocket. It does not validate the schema, does not simulate realistic market structure, and does not meaningfully test the subscription/routing layer.

**Resubscribing on every render.** A `useEffect` with a missing dependency or an object literal in the dependency array will resubscribe on every render, creating and destroying subscriptions continuously.

**Mixing live and persisted state updates in the same handler.** A WebSocket message that updates both live price state and triggers a write to the database (e.g., to persist the latest price for "last seen") conflates live market state with persistence concerns. Keep them separate.

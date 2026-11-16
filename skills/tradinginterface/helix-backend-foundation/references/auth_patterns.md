# Authentication Patterns

Practical guidance for adding real authentication to a web application. Covers strategy selection, implementation patterns, and the specific mistakes that demo projects make when "adding auth".

---

## Strategy selection

Three viable patterns for internal tools and trading interfaces:

### 1. Session-based auth (server sessions + cookies)
The server maintains a session store (Redis, database table). On login, the server creates a session, issues a cookie, and subsequent requests carry the cookie. The server validates the session on each request.

**Good for:** Internal tools, dashboards, single-origin apps where the frontend and API are served from the same domain. Simple to reason about. Secure by default (HttpOnly cookies, no token storage in JS).

**Implementation stack:** Express + express-session + Redis/PostgreSQL session store. Or a framework like Next.js with `iron-session` or `next-auth`.

### 2. JWT-based auth (stateless tokens)
The server issues a signed JWT on login. The client stores it (preferably in an HttpOnly cookie, not localStorage) and sends it with each request. The server verifies the signature without a round-trip to a session store.

**Good for:** Apps with a separate API server, multiple API consumers, or where horizontal scaling makes shared session state expensive.

**Critical detail:** Store JWTs in HttpOnly cookies, not localStorage. Storing JWTs in localStorage exposes them to XSS. A JWT in an HttpOnly cookie has the same XSS protection as a session cookie.

**Implementation stack:** `jsonwebtoken` for signing/verification, HttpOnly cookie for transport. Access token (short-lived: 15min) + refresh token (long-lived: 7-30 days) in a separate HttpOnly cookie.

### 3. Delegated auth via OAuth/OIDC provider
Delegate authentication to an external provider (Google, GitHub, an internal IdP). The provider handles credential management; your app receives an identity token.

**Good for:** Internal tools where the company already has an SSO provider. Eliminates password management entirely.

**Implementation stack:** `passport.js` with the relevant strategy, or `next-auth`/`auth.js` which handles the OAuth dance.

---

## The auth boundary

Authentication happens at the boundary between the public internet and your application's protected resources. This boundary exists in two places:

**Frontend:** Routes that require authentication redirect to login if the user is unauthenticated. This is UI-level enforcement — it improves UX but is not security. The backend cannot trust the frontend's claim that a user is logged in.

**Backend:** Every API route that returns user-specific or sensitive data must verify the session/token independently. The backend treats every request as potentially unauthenticated until proven otherwise.

The failure mode to avoid: only enforcing auth in the frontend router, with backend routes that accept any request. A user who bypasses the frontend can access all data.

---

## Protected routes in React

A simple approach that works for SPAs:

```typescript
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  
  if (loading) return <LoadingScreen />;
  if (!user) return <Navigate to="/login" replace />;
  
  return <>{children}</>;
}

// Usage in router
<Route path="/app/*" element={<ProtectedRoute><AppLayout /></ProtectedRoute>} />
```

The `useAuth` hook is the source of truth for auth state on the frontend. It should:
- Read from the server (validate the session cookie or check token validity) on mount
- Expose `user`, `loading`, and `error` state
- Expose `signIn`, `signOut`, and optionally `signUp` actions
- Handle the loading state explicitly — components should not flash unauthenticated content while auth is being verified

---

## Backend middleware pattern

```typescript
// Auth middleware — verify the session/token
export function requireAuth(req: Request, res: Response, next: NextFunction) {
  const user = verifySession(req); // or verifyJWT(req)
  if (!user) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  req.user = user;
  next();
}

// Apply to protected routes
app.use('/api/strategies', requireAuth, strategiesRouter);
app.use('/api/watchlists', requireAuth, watchlistsRouter);
```

The middleware sets `req.user` so that route handlers can access the authenticated user's ID for scoped queries.

---

## User-scoped data access

Every query for user-specific data must filter by the authenticated user's ID. This is not optional, and it must be enforced in the data access layer, not just in the route handler.

```typescript
// Enforce user scope in the query, not just in the route
async function getStrategies(userId: string): Promise<Strategy[]> {
  return db.select().from(strategies).where(eq(strategies.userId, userId));
}

// Route handler receives userId from req.user, not from the request body/params
app.get('/api/strategies', requireAuth, async (req, res) => {
  const strategies = await getStrategies(req.user.id);
  res.json(strategies);
});
```

Never accept a `userId` from the request body/query params for data scoping. The user ID comes from the verified session/token.

---

## Sign-up / Sign-in / Sign-out flows

### Sign-up
1. Validate input (email format, password strength)
2. Check email is not already registered
3. Hash password with bcrypt (cost factor ≥ 12)
4. Insert user record
5. Create session / issue tokens
6. Return authenticated session to frontend

### Sign-in
1. Find user by email (use a constant-time lookup to avoid timing attacks on email existence)
2. Verify password with `bcrypt.compare`
3. Create session / issue tokens
4. Return authenticated session

### Sign-out
1. Invalidate the session (delete from store, or add JWT to blocklist if using stateless tokens)
2. Clear the cookie
3. Redirect to login

The most common sign-out mistake: clearing the cookie on the frontend without invalidating the session on the backend. A user with a stolen cookie would remain authenticated until the session naturally expires.

---

## Secrets and configuration

- JWT secret: minimum 256-bit random value, stored in env var, never in source
- Session secret: same
- Never log auth tokens, session IDs, or passwords
- Use env vars for all secrets — never hardcode, never commit to git

```
JWT_SECRET=<256-bit-random>
SESSION_SECRET=<256-bit-random>
DATABASE_URL=postgres://...
```

---

## Common mistakes to avoid

**"Auth" that is just UI routing.** Setting `isLoggedIn: true` in React state after a fake login form is not authentication.

**Storing tokens in localStorage.** Accessible to any JavaScript on the page, including injected scripts.

**Trusting the frontend for user identity.** A request that includes `userId: "123"` in the body could come from anywhere.

**Skipping session invalidation on sign-out.** The server must invalidate the session; the frontend cannot do it alone.

**Single generic "protected" middleware that does not distinguish read from write.** Some routes might allow read access for authenticated-but-unprivileged users while restricting writes. Design the middleware to be composable.

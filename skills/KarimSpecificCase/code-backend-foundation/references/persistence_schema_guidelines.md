# Persistence Schema Guidelines

Schema design, migration patterns, and persistence strategy for domain entities in trading interfaces, dashboards, and internal operational tools.

---

## Table of contents
1. [Core entities](#core-entities)
2. [Schema design principles](#schema-design-principles)
3. [User-scoped data](#user-scoped-data)
4. [JSON columns vs. normalized tables](#json-columns-vs-normalized-tables)
5. [Versioning strategies](#versioning-strategies)
6. [Migration discipline](#migration-discipline)
7. [Common mistakes](#common-mistakes)

---

## Core entities

The following entities recur across trading interface and dashboard projects. Use these as starting templates, adjusted to the actual domain.

### Users
```sql
CREATE TABLE users (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email       TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Strategies
Strategies are the most important user-owned domain object in a trading tool. They represent a defined approach — parameters, configuration, state.

```sql
CREATE TABLE strategies (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name        TEXT NOT NULL,
  description TEXT,
  status      TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'paused', 'archived')),
  config      JSONB NOT NULL DEFAULT '{}',  -- strategy-specific parameters
  version     INTEGER NOT NULL DEFAULT 1,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX strategies_user_id_idx ON strategies(user_id);
```

The `config` JSONB column holds strategy-specific parameters. This is appropriate here because different strategy types have structurally different parameters — a relational approach would require a complex EAV schema or a separate table per strategy type. JSONB with application-level validation is the right tradeoff.

### Watchlists
```sql
CREATE TABLE watchlists (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name        TEXT NOT NULL,
  is_default  BOOLEAN NOT NULL DEFAULT false,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE watchlist_items (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  watchlist_id  UUID NOT NULL REFERENCES watchlists(id) ON DELETE CASCADE,
  instrument_id TEXT NOT NULL,  -- external identifier (e.g. ISIN, ticker)
  sort_order    INTEGER NOT NULL DEFAULT 0,
  added_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX watchlist_items_watchlist_idx ON watchlist_items(watchlist_id);
```

### Saved layouts / dashboards
Workspace layout configuration is a common persistence target for tools with configurable UIs.

```sql
CREATE TABLE layouts (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name        TEXT NOT NULL,
  workspace   TEXT NOT NULL,  -- e.g. 'market', 'research', 'strategy'
  is_default  BOOLEAN NOT NULL DEFAULT false,
  config      JSONB NOT NULL DEFAULT '{}',  -- panel positions, sizes, active panes
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Layout config is JSONB — this is appropriate because the structure is dynamic and workspace-specific. It does not benefit from normalization.

### User settings
```sql
CREATE TABLE user_settings (
  user_id       UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  theme         TEXT NOT NULL DEFAULT 'dark',
  timezone      TEXT NOT NULL DEFAULT 'UTC',
  notifications JSONB NOT NULL DEFAULT '{}',
  preferences   JSONB NOT NULL DEFAULT '{}',
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

One row per user, created on sign-up. Settings that are structured and queried should be columns. Settings that are miscellaneous preferences can go in the `preferences` JSONB.

---

## Schema design principles

**Use UUIDs for primary keys**, not auto-increment integers. UUIDs are safe to generate client-side, work across distributed systems, and do not leak record counts.

**Every table has `created_at` and `updated_at`** timestamps. These cost almost nothing and save debugging sessions later. Use a trigger or ORM lifecycle hook to auto-update `updated_at`.

**Soft-delete with `archived_at` for domain objects, not hard-delete.** Strategies, watchlists, and layouts should not be permanently deleted — users who delete something by accident expect undo or history. A `deleted_at TIMESTAMPTZ` column and filtered queries (`WHERE deleted_at IS NULL`) is sufficient.

**Foreign keys with `ON DELETE CASCADE`** for owned entities (a user's strategies should be deleted when the user is deleted). Use `ON DELETE RESTRICT` or `SET NULL` for references that should not cascade.

**Indices on foreign keys.** PostgreSQL does not auto-index foreign keys. Every `user_id` column, every `watchlist_id` column — add an index. Queries that filter by `user_id` without an index will full-scan as the table grows.

**Enums as CHECK constraints first.** Use `CHECK (status IN ('draft', 'active', 'archived'))` rather than a PostgreSQL enum type. Adding a value to a CHECK constraint is a non-destructive migration; adding a value to an enum type requires a table lock in older Postgres versions.

---

## User-scoped data

Every user-owned entity must have a `user_id` foreign key. Queries must always filter by the authenticated user's ID, enforced in the data access layer.

The pattern:

```typescript
// Data access layer — always scoped
export async function listStrategies(userId: string): Promise<Strategy[]> {
  return db.select().from(strategies)
    .where(and(eq(strategies.userId, userId), isNull(strategies.deletedAt)))
    .orderBy(desc(strategies.updatedAt));
}

export async function getStrategy(id: string, userId: string): Promise<Strategy | null> {
  const rows = await db.select().from(strategies)
    .where(and(eq(strategies.id, id), eq(strategies.userId, userId)));
  return rows[0] ?? null;
}
```

The `userId` parameter comes from the authenticated session, passed by the route handler. Never trust a `userId` from the request body for scoping data access.

---

## JSON columns vs. normalized tables

JSONB columns are appropriate when:
- The structure is dynamic and genuinely schema-less (strategy parameters that vary by type)
- The data is always read/written as a whole (layout config, notification preferences)
- Querying into the JSON structure is rare or not required

Normalized tables are appropriate when:
- Individual fields are queried, filtered, or sorted (`WHERE status = 'active'`)
- The data participates in joins (`watchlist_items JOIN instruments`)
- The fields need indexing
- There is a well-defined, stable schema

The most common mistake: putting everything in a single `data: JSONB` column per user and calling it persistence. This makes querying impossible and schema evolution opaque.

---

## Versioning strategies

For domain objects where history matters (strategies with backtested results, saved reports, layout configurations that users iterate on), a simple versioning approach:

### Append-only versioning
```sql
CREATE TABLE strategy_versions (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_id   UUID NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
  version       INTEGER NOT NULL,
  config        JSONB NOT NULL,
  created_by    UUID NOT NULL REFERENCES users(id),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  
  UNIQUE(strategy_id, version)
);
```

The `strategies` table holds the current state. `strategy_versions` holds the history. When a strategy is updated, write the new config to `strategies` and append a row to `strategy_versions`.

This is lightweight enough to be correct and does not require a full audit log system.

### When not to version
Not everything needs versioning. Watchlists, layout config, and user settings do not usually require version history. `updated_at` timestamps are enough to know when something changed.

---

## Migration discipline

Migrations are the version control of your database schema. Without them, the schema is undocumented, irreproducible, and dangerous to modify in production.

**Use a migration tool.** Options: Drizzle ORM's migrations, Knex.js, Flyway, Liquibase, or plain SQL files with a custom runner. The choice matters less than the discipline of using it consistently.

**Every schema change is a migration.** Adding a column, changing a constraint, creating an index — all migrations.

**Migrations are append-only.** Do not edit an already-applied migration. Write a new one. Edit → commit → apply is the sequence.

**Make migrations idempotent where possible.** `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`. This makes re-running migrations safe in development.

**Separate additive from destructive migrations.** An additive migration (adding a column, adding a table) can be applied to production before code that uses it is deployed. A destructive migration (dropping a column, renaming a column) must only be applied after the code that depended on the old schema is removed from production. This is the blue/green migration pattern — it prevents downtime from schema-code mismatches.

---

## Common mistakes

**One giant JSON blob per user.** A `user_data: JSONB` column that holds everything is not a schema — it is a serialized object. You lose querying, indexing, constraints, and the ability to reason about data shape.

**No foreign keys.** Skipping foreign keys to "keep it simple" removes the database's ability to enforce integrity. Orphaned records accumulate silently.

**No indices on foreign keys.** The query `SELECT * FROM strategies WHERE user_id = $1` does a full table scan without an index. At 10,000 rows this is invisible; at 10,000,000 rows it is a production incident.

**Storing derived data.** If a value can be computed from other columns, do not store it. Store the source data and compute on read (or cache the computation with a materialized view if performance demands it).

**Using `TEXT` for structured data.** A status field that is logically an enum stored as `TEXT` with no constraint will eventually contain values like `'Active'`, `'ACTIVE'`, `'active'`, and `null`.

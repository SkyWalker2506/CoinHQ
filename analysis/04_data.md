# Data & Database Analysis — CoinHQ
_Date: 2026-04-10 · Lead: CodeLead (A10) · Model: Sonnet 4.6_

## Delta vs 2026-04-06

| Item | April 6 | April 10 | Status |
|------|---------|----------|--------|
| Alembic migrations | Ad-hoc | 7 versioned migrations | ✅ |
| Indexes on core tables | Missing | Migration 007 adds indexes | ✅ |
| `view_count` / `last_viewed_at` on share links | Missing | COIN-3 added both | ✅ |
| `UserTier` enum | Missing | COIN-5 added `005_add_user_tier.py` | ✅ |
| `check_exchange_limit` enforcement | N/A | Defined but **never called** | 🔴 |
| `DateTime(timezone=True)` consistency | — | Inconsistent across migrations | 🟡 |
| `UserTier` as DB Enum type | N/A | String(50) in DB, not Enum | 🟡 |
| Backup strategy | Missing | Still missing | 🟡 |

## Current State

7 Alembic migrations track schema history. Migration `007_add_indexes_and_constraints.py` adds composite indexes on the most-queried paths. `share_links.token` is unique + indexed.

COIN-3 (`view_count`, `last_viewed_at`) uses an atomic SQL `UPDATE ... SET view_count = view_count + 1` at `backend/app/api/public.py:195` — correct, no race condition.

COIN-5 adds `user.tier` as `String(50)` with default `"free"`. The `UserTier(StrEnum)` is defined in `backend/app/models/user.py:10` but the column is not typed as a DB Enum — just a plain string column. Anything can be written to it at the DB level.

`check_exchange_limit` is defined in `backend/app/core/limits.py:25` and is the function that enforces free-tier exchange-key limits. It is not called anywhere in the codebase — free-tier users can add unlimited exchange keys.

## Findings

### 🔴 Critical

**F1 — `check_exchange_limit` is dead code — free tier can add unlimited exchange keys**
`backend/app/core/limits.py:25` — Function defined, returns 403 if limit exceeded. Grep across codebase: called 0 times. `backend/app/api/v1/keys.py` creates keys without calling this function. A free user can bypass the 2-key limit entirely by using the API directly. Profile limit gate works (`profiles.py:37`) but key limit gate does not.

Fix: call `check_exchange_limit(current_user, db)` in `keys.py` before creating a new key.

### 🟡 Important

**F2 — `UserTier` defined as StrEnum but DB column is `String(50)`**
`backend/app/models/user.py:24` — `tier = Column(String(50), nullable=False, default="free")`. A DB CHECK constraint or `Enum(UserTier)` column type is absent. Any string can be written directly to the `tier` column — no DB-level enforcement. Fix: Alembic migration to `Enum(UserTier)` with CHECK constraint.

**F3 — Timezone inconsistency across migrations**
Migration `001` uses `DateTime(timezone=True)` for timestamps. Migration `004` (COIN-3) adds `last_viewed_at` as `DateTime()` without `timezone=True`. Queries mixing these columns can produce inconsistent UTC comparisons. Fix: consistently use `DateTime(timezone=True)` and verify `last_viewed_at` stores UTC via `func.now()` rather than Python `datetime.now(UTC)` (which may store without tz info in some drivers).

**F4 — `exchange_keys.exchange` column has no index**
`backend/app/models/exchange_key.py` — `exchange` column (e.g. `"binance"`, `"okx"`) is used in the admin stats GROUP BY query (`admin.py:34`) and potentially in future filtering. No index. On a large user base, this full-table scan will be costly. Fix: add index in next migration.

**F5 — `last_viewed_at` has no index (analytics queries)**
`backend/app/models/share_link.py:26` — `last_viewed_at` will be queried for "links viewed in last 30 days" type analytics. No index. Fix: add index alongside `view_count` if analytics queries are planned.

**F6 — No DB backup strategy documented**
`docker-compose.yml` and `docker-compose.prod.yml` use named volumes for Postgres. No pg_dump cron, no Supabase PITR, no Railway backup policy documented. Data loss on volume corruption = unrecoverable. Fix: enable Railway Postgres backups or add a daily pg_dump cron.

**F7 — Migration `005_add_user_tier` doesn't backfill existing users**
`backend/alembic/versions/005_add_user_tier.py` — Adds `tier` column with server_default `"free"`. Alembic `server_default` applies to new rows, but existing rows at migration time may receive NULL depending on DB engine behavior. Confirm all existing rows got `"free"` default.

### 🟢 Good

**F8 — Atomic `view_count` increment.** `view_count = view_count + 1` at SQL level — no read-modify-write race.

**F9 — `share_links.token` unique + indexed.** Public lookup by token is O(log n).

**F10 — 7 versioned Alembic migrations.** Clean schema history; Railway auto-runs `alembic upgrade head`.

## Action Items

| # | P | Fix | File | Effort |
|---|---|-----|------|--------|
| 1 | 🔴 | Call `check_exchange_limit` in key create endpoint | `backend/app/api/v1/keys.py` | XS |
| 2 | 🟡 | Migrate `tier` column to `Enum(UserTier)` + CHECK constraint | new Alembic migration | S |
| 3 | 🟡 | Standardize `DateTime(timezone=True)` across all migrations | migrations 004+ | S |
| 4 | 🟡 | Add index on `exchange_keys.exchange` | new Alembic migration | XS |
| 5 | 🟡 | Add index on `share_links.last_viewed_at` | new Alembic migration | XS |
| 6 | 🟡 | Document + enable DB backup strategy | `docker-compose.prod.yml` / Railway | S |
| 7 | 🟢 | Verify migration 005 backfilled existing rows | Alembic + SQL verify script | XS |

## References
- `backend/app/core/limits.py`
- `backend/app/api/v1/keys.py`
- `backend/app/models/user.py`, `share_link.py`, `exchange_key.py`
- `backend/alembic/versions/` (all 7 migrations)
- `analysis/archive_2026-04-06/` (no prior data report — new category)

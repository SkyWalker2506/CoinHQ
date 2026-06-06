# Performance Analysis — CoinHQ
_Date: 2026-04-10 · Lead: CodeLead (A10) · Model: Sonnet 4.6_

## Delta vs 2026-04-06

| Item | April 6 | April 10 | Status |
|------|---------|----------|--------|
| `asyncio.gather` for parallel exchange calls | Missing | Implemented | ✅ |
| Binance ticker fetch (per-asset vs bulk) | Per-asset | Single bulk ticker | ✅ |
| `selectinload` on ORM relationships | Missing | Implemented | ✅ |
| `app.state` singleton (Redis, httpx) | Per-request | Singleton on startup | ✅ |
| SWR for frontend data fetching | Missing | `usePortfolio` hook | ⚠️ Bug (wrong URL) |
| `public_share_view` cache passthrough | N/A | **Missing** — bypasses cache | 🔴 |
| Dashboard `useEffect` raw fetch | Old pattern | SWR hook exists but unused | 🟡 |
| Binance price cache size | — | ~500KB blob per cache entry | 🟡 |

**Score: 4/10 → 7/10**

## Current State

Backend portfolio fetch now uses `asyncio.gather` for parallel exchange API calls. Binance price lookup uses a single bulk ticker endpoint cached in Redis. `selectinload` prevents N+1 queries on ORM relationships. Redis client and httpx client are initialized as `app.state` singletons at startup.

Frontend has a `usePortfolio` SWR hook at `frontend/src/hooks/usePortfolio.ts:11` but the URL is constructed as `/portfolio/${profileId}` while the actual route is `/portfolio/profile/{profile_id}` — the `/profile/` segment is missing. This is a live functional bug that silently falls back to refetch.

## Findings

### 🔴 Critical

**F1 — `public_share_view` bypasses app.state singletons (cache miss on every public view)**
`backend/app/api/v1/share.py:208` — `get_portfolio(link.profile_id, profile.name, keys)` is called without passing `redis` or `http_client` arguments. The function signature accepts optional `redis` and `http_client` params; when absent, it creates fresh `httpx.AsyncClient()` instances per call and skips Redis caching. Every public share page view hits all exchanges fresh.

Impact: Popular share links hammered by social/bots will drain exchange API quotas and spike latency. Fix: pass `request.app.state.redis` and `request.app.state.http_client` in the call at `share.py:208`.

**F2 — `usePortfolio.ts:11` URL bug — wrong route, silent miss**
`frontend/src/hooks/usePortfolio.ts:11` — URL is `/portfolio/${profileId}` but the backend route is `/api/v1/portfolio/profile/{profile_id}`. The SWR request 404s or hits a wrong endpoint, causing silent fallback. This defeats the SWR caching benefit entirely.

### 🟡 Important

**F3 — Dashboard uses `useEffect` + raw fetch instead of SWR hook**
Several dashboard components (`dashboard/page.tsx`) still use `useEffect(() => { fetch(...) }, [])` patterns despite the SWR hook existing. No deduplication, no background revalidation, no cache-while-revalidate. Fix: migrate to SWR hooks.

**F4 — Binance price cache writes ~500KB per entry**
Binance bulk ticker response includes all 1000+ trading pairs. The full JSON blob is cached under a single Redis key per update cycle. At 60s TTL and any concurrent users, this is acceptable — but deserialization overhead on every cache hit is measurable. Fix: cache only the subset of assets a user actually holds.

**F5 — OAuth callback creates two separate `httpx.AsyncClient` instances**
`backend/app/api/v1/auth.py:96-119` — Two separate `async with httpx.AsyncClient() as client:` blocks for token exchange and userinfo fetch, ignoring `app.state.http_client`. Extra connection overhead on login.

**F6 — Thundering herd on Binance price cache expiry**
Binance price cache has a 30s TTL with no Redis lock. Multiple concurrent requests on cache miss will all fan out to the Binance API simultaneously. Fix: use Redis `SET NX` lock pattern during refresh.

### 🟢 Good

**F7 — `asyncio.gather` for parallel exchange calls.** Portfolio fetch now fires all exchange API calls concurrently. 3-exchange user: 3× speedup.

**F8 — `selectinload` prevents N+1.** ORM relationship loading now uses joined loading strategy.

**F9 — `app.state` singletons.** Redis and httpx client initialized once at startup.

## Action Items

| # | P | Fix | File | Effort |
|---|---|-----|------|--------|
| 1 | 🔴 | Pass `redis`/`http_client` to `get_portfolio` in share endpoint | `backend/app/api/v1/share.py:208` | XS |
| 2 | 🔴 | Fix SWR hook URL (`/portfolio/${id}` → `/portfolio/profile/${id}`) | `frontend/src/hooks/usePortfolio.ts:11` | XS |
| 3 | 🟡 | Migrate dashboard `useEffect` fetches to SWR hooks | `frontend/src/app/dashboard/page.tsx` | S |
| 4 | 🟡 | Cache Binance price subset per user, not full ticker | `backend/app/exchanges/binance.py` | M |
| 5 | 🟡 | Redis lock for Binance cache refresh (thundering herd) | backend cache layer | S |
| 6 | 🟡 | Auth callback — use `app.state.http_client` | `backend/app/api/v1/auth.py:96-119` | XS |
| 7 | 🟢 | Per-minute public share Redis cache keyed by token | `backend/app/api/v1/share.py` | S |

## References
- `backend/app/api/v1/share.py`
- `backend/app/api/v1/auth.py`
- `frontend/src/hooks/usePortfolio.ts`
- `analysis/archive_2026-04-06/02_performance.md`

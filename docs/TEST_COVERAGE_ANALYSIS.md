# Test Coverage Analysis — CoinHQ

**Date:** 2026-04-14

---

## Current State

### Backend: 9 tests across 3 files

| File | Tests | What's Covered |
|------|-------|---------------|
| `test_exchanges.py` | 2 | Binance adapter: non-zero balance retrieval, zero balance filtering |
| `test_isolation.py` | 4 | Multi-user data isolation: profile 403/404 guards, `_get_owned_profile` helper |
| `test_portfolio_service.py` | 4 | Portfolio service: parallel exchange calls, single price API call, graceful degradation on exchange failure, Redis cache hit |

### Frontend: 0 tests

No test framework installed. No test files, no test config, no test dependencies.

---

## Coverage Gaps (Prioritized)

### Priority 1 — Security-Critical (Missing tests create real risk)

#### 1a. `core/security.py` — Encryption & JWT (0% covered)

**Why it matters:** This module guards every authenticated endpoint and protects exchange API keys at rest. A regression here leaks secrets or breaks auth for all users.

**Proposed tests:**
- `encrypt()` then `decrypt()` round-trips correctly
- `decrypt()` raises on tampered ciphertext
- `create_access_token()` produces a valid JWT with correct `sub`, `exp`, `type` claims
- `create_refresh_token()` produces a valid JWT with `type: "refresh"`
- `decode_refresh_token()` rejects an access token (wrong `type`)
- `decode_refresh_token()` rejects an expired token
- `decode_refresh_token()` rejects a token signed with a wrong secret
- `get_current_user()` returns user on valid token, raises 401 on invalid/expired/missing token
- `get_multi_fernet()` decrypts with old key after rotation

#### 1b. `api/v1/keys.py` — API Key Management (partially covered)

**Why it matters:** This endpoint encrypts and stores exchange credentials. A bug here could store plaintext keys or accept write-enabled keys.

**Proposed tests:**
- `add_key()` encrypts key/secret before DB write (assert `encrypt()` called)
- `add_key()` rejects unsupported exchange names (400)
- `add_key()` rejects keys that fail `validate_key()` (400)
- `add_key()` returns 502 when exchange API is unreachable
- `delete_key()` returns 404 when key doesn't belong to profile
- `list_keys()` returns only keys for the owned profile

#### 1c. `api/v1/auth.py` — OAuth Flow (0% covered)

**Why it matters:** Handles user identity. CSRF state validation, token exchange, and user upsert are all untested.

**Proposed tests:**
- `google_callback()` rejects missing `code` parameter (401)
- `google_callback()` rejects invalid/missing `state` (CSRF — 403)
- `google_callback()` rejects expired state token (403)
- `google_callback()` upserts new user on first login
- `google_callback()` updates name/email for existing user
- `refresh_access_token()` returns new access token for valid refresh token
- `refresh_access_token()` rejects invalid refresh token (401)

---

### Priority 2 — Business Logic (Bugs here cause wrong data)

#### 2a. `services/price_service.py` (0% covered)

**Why it matters:** Incorrect prices mean the dashboard shows wrong portfolio values.

**Proposed tests:**
- `get_usd_prices()` returns cached prices from Redis on cache hit
- `get_usd_prices()` fetches from Binance and writes to Redis on cache miss
- `get_usd_prices()` handles Redis read failure gracefully (falls back to fetch)
- `get_usd_prices()` returns empty dict for empty asset list
- `_fetch_binance_all_prices()` correctly parses USDT pairs and strips suffix
- `_fetch_binance_all_prices()` returns stablecoin prices (USDT=1, USDC=1, etc.)
- `_fetch_binance_all_prices()` returns empty dict on Binance API failure

#### 2b. `api/v1/share.py` — Share Links & Public View (0% covered)

**Why it matters:** The public share endpoint has complex permission filtering logic (`show_total_value`, `show_coin_amounts`, `show_exchange_names`, `show_allocation_pct`). Bugs could leak private data to public viewers.

**Proposed tests:**
- `create_share_link()` returns 404 for non-owned profile
- `revoke_share_link()` sets `is_active = False`
- `public_share_view()` returns 404 for revoked links
- `public_share_view()` returns 410 for expired links
- `public_share_view()` increments `view_count` atomically
- `public_share_view()` masks exchange names when `show_exchange_names=False`
- `public_share_view()` omits coin amounts when `show_coin_amounts=False`
- `public_share_view()` omits total USD when `show_total_value=False`
- `public_share_view()` computes allocation percentages correctly
- `follow_portfolio()` rejects tokens with `allow_follow=False` (403)
- `follow_portfolio()` is idempotent (returns existing record on duplicate)
- `unfollow_portfolio()` rejects another user's follow (404)

#### 2c. `core/limits.py` — Tier Limits (0% covered)

**Why it matters:** Controls whether free users can create profiles/add exchanges. Simple logic but critical for the business model.

**Proposed tests:**
- `check_profile_limit()` returns `False` when free user at limit (1 profile)
- `check_profile_limit()` returns `True` for premium user (unlimited)
- `check_profile_limit()` defaults to free-tier limits for unknown tier
- `check_exchange_limit()` returns `False` when free user at limit (2 exchanges)
- `check_exchange_limit()` returns `True` for premium user (unlimited)

---

### Priority 3 — Exchange Adapters (5 of 6 adapters untested)

Only `BinanceAdapter.get_balances()` has tests. The other 5 adapters and all `validate_key()` methods are untested.

**Proposed tests (per adapter: Bybit, OKX, Coinbase, Kraken, BinanceTR):**
- `get_balances()` returns non-zero balances correctly
- `get_balances()` filters out zero balances
- `validate_key()` returns `True` for read-only key
- `validate_key()` raises `ValueError` for write-enabled key

**Additional Binance adapter tests:**
- `validate_key()` rejects keys with `enableWithdrawals` or `enableInternalTransfer`

**Factory tests (`exchanges/factory.py`):**
- `get_adapter()` returns correct adapter class for each exchange name
- `get_adapter()` raises `ValueError` for unsupported exchange

---

### Priority 4 — API Endpoint Integration Tests

Currently all tests call endpoint functions directly with mocked `db` objects. There are no tests using FastAPI's `TestClient` / `httpx.AsyncClient` against the actual app.

**Proposed integration test infrastructure:**
- `conftest.py` with in-memory SQLite, test app, and authenticated test client fixture
- Test the full HTTP request/response cycle including middleware, dependency injection, and serialization

**Key endpoints to cover:**
- `GET /api/v1/profiles/` — returns only current user's profiles
- `POST /api/v1/profiles/` — enforces tier profile limit
- `GET /api/v1/portfolio/profile/{id}` — returns serialized portfolio
- `GET /api/v1/portfolio/aggregate` — aggregates across profiles
- `GET /api/v1/admin/stats` — returns 403 for non-admin users
- `GET /health` — validates DB + Redis connectivity check

---

### Priority 5 — Frontend Tests (0% coverage)

#### 5a. Test Infrastructure Setup

Install a test framework and configure it:
- **Recommended:** Vitest + React Testing Library + MSW (Mock Service Worker)
- Add `vitest.config.ts`, test scripts to `package.json`

#### 5b. Unit Tests — Utilities & Hooks

- `lib/api.ts` — Token refresh retry logic, auth header construction, 401 handling
- `hooks/usePortfolio.ts` — SWR data fetching, refresh interval, error states
- `hooks/useFocusTrap.ts` — Focus cycling within modals
- `lib/analytics.ts` — Event tracking calls
- `lib/sentry.ts` — Lazy loading, error capture

#### 5c. Component Tests

- `AddKeyModal` — Form validation, exchange selection, submission
- `CreateShareLinkModal` — Permission toggle logic, expiration handling
- `AllocationChart` — Renders correctly with data, handles empty/edge cases
- `ExchangeList` — Search filtering, expand/collapse behavior
- `ProfileSwitcher` — Profile selection, "All Profiles" aggregate mode
- `ShareLinkManager` — Copy link, revoke link
- `OnboardingWizard` — Step progression logic
- `Navigation` — Logout clears token from localStorage
- `FollowButton` — Follow/unfollow state management

#### 5d. Page-Level Tests

- `auth/callback` — Token extraction from URL params, localStorage storage, redirect
- `dashboard` — Renders portfolio data, handles loading/error states
- `settings` — Profile CRUD, key management UI flow
- `share/[token]` — Public view renders with permission-filtered data

---

## Summary

| Area | Files/Modules | Current Tests | Proposed Tests | Priority |
|------|--------------|--------------|---------------|----------|
| Security (encryption, JWT, auth) | 3 | 0 | ~20 | P1 |
| API key management | 1 | 1 (partial) | 6 | P1 |
| Price service | 1 | 0 | 7 | P2 |
| Share links & public view | 1 | 0 | 12 | P2 |
| Tier limits | 1 | 0 | 5 | P2 |
| Exchange adapters (5 untested) | 5 | 0 | 20+ | P3 |
| Integration tests (full HTTP) | all endpoints | 0 | 10+ | P4 |
| Frontend (all) | ~34 files | 0 | 40+ | P5 |
| **Total** | | **9** | **~120+** | |

### Recommended First Steps

1. **Add `test_security.py`** — encrypt/decrypt round-trip, JWT creation/validation, token rejection. Highest ROI: protects auth and secrets with ~10 quick tests.
2. **Add `test_share.py`** — Permission filtering in the public share view. Bugs here leak private data publicly.
3. **Add `test_price_service.py`** — Redis caching, Binance parse logic, stablecoin handling.
4. **Add `test_limits.py`** — Tier enforcement. 5 trivial tests that protect the billing model.
5. **Install Vitest in frontend** — Even a basic smoke test for the auth callback and API client would be a huge step up from zero.

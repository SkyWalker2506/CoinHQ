# Forge Run 3 — CoinHQ Summary

**Date:** 2026-04-22
**Model:** Claude Sonnet 4.6
**Project:** SkyWalker2506/CoinHQ

---

## Tasks Completed

| Issue | Title | PR | Status |
|-------|-------|----|--------|
| #29 | Fix: migrate OAuth state storage from in-memory dict to Redis | #30 | Merged |
| #31 | Add Sentry beforeSend PII scrubbing to strip tokens from URLs | #32 | Merged |
| n/a | Add test coverage for exchange key tier limit enforcement | #33 | Merged |

---

## What Was Implemented

### PR #30 — OAuth Redis state migration
- Removed module-level `_oauth_states: dict[str, float]` and `_cleanup_expired_states()` helper
- State tokens now stored in Redis as `oauth_state:{state}` keys with 600s TTL
- Atomic `redis.delete()` returns 1 (valid) or 0 (invalid) — CSRF check and removal in one op
- Multi-replica Railway deployments now work correctly (state visible to all replicas)
- Updated `test_auth.py` to mock `request.app.state.redis`; removed obsolete cleanup test class

### PR #32 — Sentry PII scrubbing
- Added `_scrubEvent()` helper function and wired it as `beforeSend` in Sentry.init
- Strips entire query string from event request URLs (prevents JWT leaks from `/auth/callback?token=...`)
- Redacts share link tokens in paths: `/share/<token>` → `/share/[token]`
- All analytics tests pass

### PR #33 — Key limit test coverage
- Added `test_rejects_free_user_over_exchange_limit` — verifies 403 + `tier_limit` detail
- Added `test_allows_premium_user_beyond_exchange_limit` — verifies premium bypass
- Added `_setup_db_execute()` and `_make_free_user()` helpers
- Updated all existing `TestAddKey` tests to mock `db.execute` for the new limit check

---

## Files Changed

- `backend/app/api/v1/auth.py` — Redis OAuth state
- `backend/tests/test_auth.py` — Updated for Redis mocking
- `frontend/src/lib/sentry.ts` — beforeSend PII scrubbing
- `backend/tests/test_keys_api.py` — 2 new tests + helper functions

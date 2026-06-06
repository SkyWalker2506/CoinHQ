# Forge Run 3 — Lessons Learned

**Date:** 2026-04-22

## What Worked

1. **Lessons from Run 2 were actionable** — All 3 Run 3 tasks came directly from the Run 2 lessons list. The lesson → task pipeline worked well.
2. **Redis already wired** — `app.state.redis` was available via dependency injection pattern, making the OAuth state migration straightforward.
3. **`_scrubEvent` pattern** — Pure function for Sentry scrubbing is easily testable and reusable. Good pattern to continue.

## What to Watch

1. **Test isolation complexity** — When mocking `ExchangeKey` (the class) for storage tests, the same mock breaks SQLAlchemy's `select()` call. Pattern fix: also patch `select` in those tests, or use a module-level fixture. Note for future test authors.
2. **Pre-existing frontend test failures** — `navigation.test.tsx` has 12 pre-existing failures due to `localStorage.clear is not a function` in the test environment. These are not related to forge changes but should be fixed.
3. **`test_auth.py` expired-state test removed** — The Redis TTL handles expiry automatically so there's no need to test it at the unit level, but integration test coverage for expired states is now zero.

## Recommendations for Run 4

1. **Fix pre-existing navigation.test.tsx failures** — Set up `localStorage` mock in vitest setup
2. **Add integration test for OAuth expired state** — Mock Redis to return 0 (TTL expired) and verify 403
3. **JWT in localStorage → httpOnly cookie** — The `/auth/callback?token=...` redirect pattern is still XSS-vulnerable; moving to httpOnly cookies is the correct fix (noted as Security C-3 in MASTER_ANALYSIS)
4. **Pricing page dead CTA** — "Join waitlist" anchor links nowhere; connect to a real email capture form
5. **Wire `get_multi_fernet()` for key rotation** — Still orphaned in `security.py`; run 4 should either wire it or delete it with a comment explaining why rotation isn't needed yet

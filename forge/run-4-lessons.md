# Lessons Learned — Run 4

**Date:** 2026-04-26

## What Worked

1. **Lessons → tasks remained 1:1.** Run 3's 5 "Recommendations for Run 4" mapped cleanly to 4 tasks (the JWT→httpOnly cookie was deferred for risk). The lesson-feed pipeline keeps producing well-scoped sprints.
2. **Sequential execution was the right call.** All 4 tasks merged with zero conflicts and zero fix-loop retries. Sequential branch/PR/merge keeps history linear, makes self-review trivial, and avoided the test-order-dependence pitfalls Run 3 documented for `ExchangeKey` mocks.
3. **Inline test stubs > new dev deps.** `_StatefulRedisStub` (≈15 LOC inline in `test_auth.py`) covered the exact scenarios needed without pulling fakeredis. Same pattern as Run 2's `ShareViewTracker` — small inline helpers compose cleanly.
4. **Codifying environment fixes as infrastructure** (T-009): even when the bug doesn't reproduce, leaving a defensive shim guarantees the next jsdom upgrade can't silently regress.
5. **Plausible analytics event before persistence.** The waitlist form fires the analytics event whether or not localStorage succeeds — the durable signal is the event, not the storage. Pattern worth reusing for any future capture forms.

## What to Watch

1. **Stale lesson detection.** Run 3 reported "12 pre-existing localStorage failures" — by Run 4 the env had upgraded and the bug was gone. **Add a Phase 0 step that re-runs the failing tests cited in lessons before planning** — saves planning a fix that's already implicit.
2. **Pre-existing `@sentry/nextjs` missing-package TS errors.** `tsc --noEmit` reports 4 errors in `src/lib/sentry.ts` because `@sentry/nextjs` isn't a hard dep. Either install it (and gate at runtime) or move the file behind a dynamic `import()`.
3. **Open dependabot PRs (10+ stale since Apr 5).** None were touched by forge. They likely include the tailwind 3→4 jump that would block the build. Worth a triage sprint.
4. **`secrets` import** in `auth.py` — not directly tested today. Future security run should add a randomness-source check (assert state ≥ 32 chars / `token_urlsafe(32)`).

## Recommendations for Run 5

1. **JWT in localStorage → httpOnly cookie** (deferred from Runs 3 & 4). This is the single highest-impact security fix left. Plan as its own focused sprint — touches `auth/callback/page.tsx`, `lib/api.ts`, `usePortfolio.ts`, plus a new server-side `/auth/refresh` cookie middleware. Should be one task with clear migration plan, not multiple parallel tasks.
2. **Triage dependabot PRs** — at minimum: tailwindcss 3→4 (breaking), eslint-config-next 14→15, recharts 2→3. Run codemod + visual sanity check.
3. **Backend integration test for waitlist endpoint** — when the real `/api/v1/waitlist` lands, replace `localStorage` queue with a `POST` and add an integration test.
4. **Wire OG metadata caching** (Run 2 lesson, still open). The `generateMetadata` in `share/[token]/page.tsx` makes uncached fetches.
5. **Add a `tsc --noEmit` step to backend & frontend pre-commit** — would have caught the typo in `events.waitlistSubmitted` before commit.

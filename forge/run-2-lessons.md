# Forge Run 2 — Lessons Learned

**Date:** 2026-04-22

## What Worked

1. **P0-first approach** — Tackling the data leak and dead code before new features delivered maximum impact with minimal code change (4 lines total for the two P0 bugs).
2. **Small, targeted PRs** — Each PR addressed exactly one concern. Reviews were fast, no merge conflicts.
3. **Client boundary pattern** — The `ShareViewTracker` (renders null, fires useEffect) is the correct pattern for adding browser-side behavior to Next.js server components. Reuse this pattern.
4. **Using existing label field** — Instead of adding a new DB column for profile name privacy, using `link.label` (already present) kept the change minimal and backward-compatible.

## What to Watch

1. **"Scaffold merged, wire-up forgotten"** — Run 2 fixed the same category of bugs as identified in the MASTER_ANALYSIS T1 theme. Next run should check for more orphaned functions in `limits.py`, `security.py`, and `analytics.ts`.
2. **Test coverage gaps** — The `test_keys_api.py` tests don't cover the tier limit 403 case. Future run should add that.
3. **OG metadata still fetches uncached** — The `generateMetadata` function in `share/[token]/page.tsx` makes a separate uncached fetch. Consider whether `revalidate: 60` is sufficient or if this should be deduped.

## Recommendations for Run 3

1. **Wire `get_multi_fernet()` for key rotation** — Identified in MASTER_ANALYSIS T1; still orphaned in `security.py`
2. **Fix `_oauth_states` module-level dict** — Will break on multi-replica Railway deploy (T6)
3. **Add missing test: add_key 403 on tier limit** — Verify the new limit enforcement has test coverage
4. **Add Sentry PII scrubbing** — `frontend/src/lib/sentry.ts` needs `beforeSend` to strip `/share/<token>` and `?token=` from URLs
5. **Pricing page dead CTA** — "Join waitlist" anchor still goes nowhere; connect to a real email capture

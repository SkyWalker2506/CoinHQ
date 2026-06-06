# Forge Run 2 — CoinHQ Summary

**Date:** 2026-04-22
**Model:** Claude Sonnet 4.6
**Project:** SkyWalker2506/CoinHQ

---

## Tasks Completed

| Issue | Title | PR | Status |
|-------|-------|----|--------|
| #20 | Fix share link data leak: respect show_total_value for asset/exchange USD values | #24 | Merged |
| #21 | Enforce exchange key cap for free-tier users in add_key endpoint | #25 | Merged |
| #22 | Track share link views in Plausible analytics | #26 | Merged |
| #23 | Add analytics tracking to UpgradeBanner (impressions + clicks) | #27 | Merged |
| n/a | Redact profile_name in public share view | #28 | Merged |

---

## What Was Implemented

### PR #24 — Share link USD value leak fix
- `SharedAsset.usd_value` now returns `None` when `show_total_value=False`
- `SharedExchange.total_usd` now returns `None` when `show_total_value=False`
- Closes the P0 data leak where viewers could reconstruct hidden portfolio totals

### PR #25 — Exchange key tier limit enforcement
- `check_exchange_limit()` from `limits.py` is now imported and called in `add_key()`
- Counts existing keys per profile before inserting
- Returns HTTP 403 with `tier_limit:` detail message when free cap is exceeded
- Premium users unaffected

### PR #26 — Share link view analytics
- New `ShareViewTracker` client component fires `events.shareLinkViewed(token)` on mount
- Included in the server-side `SharePage` component via Next.js App Router client boundary

### PR #27 — UpgradeBanner analytics
- Fires `'Upgrade Banner Shown'` event on mount (impression tracking)
- Fires `'Upgrade Clicked'` event when Upgrade link is clicked
- Accepts `source` prop for attribution (default: `'settings'`)

### PR #28 — Profile name privacy
- Public share endpoint returns `link.label || 'Crypto Portfolio'` instead of `profile.name`
- Protects real names/sensitive info from leaking via OG metadata and public API

---

## Files Changed

- `backend/app/api/v1/share.py` — usd_value/total_usd gating + profile_name redaction
- `backend/app/api/v1/keys.py` — exchange limit enforcement
- `frontend/src/components/ShareViewTracker.tsx` (new)
- `frontend/src/app/share/[token]/page.tsx` — added ShareViewTracker
- `frontend/src/components/UpgradeBanner.tsx` — analytics events

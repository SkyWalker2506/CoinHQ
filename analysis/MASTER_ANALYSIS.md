# CoinHQ Master Analysis — 2026-04-10
_6 Leads · 12 Categories · Opus 4.6 Synthesis_
_Previous baseline: 2026-04-06 (archived) · Score jump: 3.4 → 5.6 / 10_

---

## Executive Summary

In the four days since the 2026-04-06 audit, CoinHQ has shipped its entire Phase 1 backbone: Google OAuth + JWT, multi-user isolation, Alembic migrations, structured logging, an exchange adapter pattern that actually works, a `UserTier` enum (COIN-5), share-link view tracking (COIN-3), env-gated Sentry/Plausible (COIN-4), an onboarding wizard, a pricing page, and an `UpgradeBanner`. This is a material jump — the product is no longer "anonymous-open and trivially broken." **However, every one of the three ticket streams (COIN-3/4/5) shipped with a freshly-introduced critical bug** that re-opens either a data leak, a revenue gate, or an observability hole. The headline risk is a **share-link visibility leak** (`usd_value`, `total_usd`, and `profile_name` ignore the `show_*` flags) paired with **unscrubbed Sentry and a JWT stored in `localStorage` after being delivered via URL query string** — any one of these on its own is a launch blocker. The biggest opportunity is that **revenue plumbing is now only one Stripe integration away**: tiers, gates, banners, and a pricing page already exist, but `check_exchange_limit` is dead code, "Join waitlist" is a silent anchor, and no impression/click events flow from the upgrade surface. If the next sprint closes the security criticals and wires Stripe Checkout into the existing tier scaffolding, CoinHQ converts from "demo-grade" to "revenue-ready" in ~10 working days.

---

## Overall Score Card

| # | Category | Apr 6 | Apr 10 | Δ | Trend |
|---|----------|-------|--------|---|-------|
| 01 | UI/UX Design | 4.5 | 6 | +1.5 | ▲ |
| 02 | Performance | 4 | 7 | +3 | ▲▲ |
| 03 | SEO | 2 | 5 | +3 | ▲▲ |
| 04 | Data & Database | — | 6 | new | ▲ |
| 05 | Monetization | 2 | 4 | +2 | ▲ |
| 06 | Growth & Engagement | 3 | 6 | +3 | ▲▲ |
| 07 | Security & Infra | 4 | 6.5 | +2.5 | ▲ |
| 08 | Content Strategy | 5 | 5 | 0 | ► |
| 09 | Analytics & Tracking | 1 | 5 | +4 | ▲▲▲ |
| 10 | Architecture & Code | 5 | 7 | +2 | ▲ |
| 11 | Accessibility | 2.5 | 5 | +2.5 | ▲ |
| 12 | Competitive | 4 | 4 | 0 | ► |
| — | **Weighted avg** | **3.4** | **5.6** | **+2.2** | ▲▲ |

**Best-in-class now:** Performance (7), Architecture (7).
**Still underwater:** Monetization (4), Competitive (4), Content (5) — all three rely on the same missing piece (landing page + payment).

---

## Cross-Cutting Themes

These are patterns that surface in **three or more** category reports. Fixing any single one of them yields multi-category leverage.

### T1 — The "defined but never called" anti-pattern
The COIN-5 sprint introduced three dead-code / dead-event situations that each break the feature they were supposed to enable:

- `check_exchange_limit()` is defined in `backend/app/core/limits.py:25` and never called anywhere. Free users bypass the key cap. **(Data, Architecture, Monetization)**
- `events.shareLinkViewed()` is defined in `frontend/src/lib/analytics.ts:11` and never called. Plausible never sees share views. **(Analytics, Growth)**
- `UpgradeBanner` has no impression or click tracking — the conversion funnel endpoint is invisible. **(Analytics, Monetization, Growth)**
- `get_multi_fernet()` exists in `backend/app/core/security.py` and is never called — the key-rotation scaffold is inert. **(Security)**

Root cause: these are all "scaffold merged, wire-up forgotten." A CI check for unused public symbols, or a PR-template checklist item ("does any new function have ≥1 call site?"), would catch all four.

### T2 — Upgrade / conversion surface is a single point, and it's at the end of the funnel
The `UpgradeBanner` only appears on **settings**, only after a **403**, and only for the **profile** gate (`AddKeyModal` has no `onTierLimit` prop at all). Meanwhile pricing page's premium CTA is a dead `#waitlist` anchor. The entire revenue funnel is one narrow pipe at the exit. Appears in: **UI/UX F7**, **Monetization F1/F3/F7**, **Growth F3**, **Analytics F2**.

### T3 — Share-link surface is both the growth engine and the data-leak surface
Share links are the only viral loop (competitive F7, growth F8), the only indexable content (SEO F2/F3), and the only public attack surface. The one place the product differentiates is also the one place that:
- leaks `usd_value`/`total_usd`/`profile_name` regardless of flags (Security C-1),
- bypasses Redis cache + app-state singletons on every view (Performance F1),
- has no canonical URL or `og:image` (SEO F2/F3, Content F3),
- never fires a `shareLinkViewed` event (Analytics F1),
- increments `view_count` on every bot preview / prefetch (Security M-1, Data).

One file — `backend/app/api/v1/share.py` — sits at the intersection of five categories' P0 findings.

### T4 — Analytics blindspots are concentrated on revenue-critical events
Plausible and Sentry are installed, but the three events that matter for unit economics all missing: **onboarding funnel**, **upgrade impression/click**, **share link view**. Every scored category that talks about measurement (Analytics, Growth, Monetization) flags this. Current state: we can see page views but not whether we're converting anything.

### T5 — Design tokens and a11y patterns exist but are not adopted
`tailwind.config.ts` defines `brand`/`surface`/`border` tokens — components still use raw `bg-gray-900`. `ConfirmModal.tsx` implements focus trap + `role="dialog"` + ESC — `OnboardingWizard.tsx` does none of it. The reference implementations exist; the codemod to propagate them is the missing step. **(UI/UX F2, A11y F1, Content F4)**.

### T6 — Single-instance architectural assumptions hidden in "works on my machine" code
`_oauth_states` is a module-level dict. `init_db()` runs under `DEBUG=True`. Both will break silently on a Railway blue/green or multi-replica deploy. The product looks multi-user but is deployed as if it were single-process. **(Architecture F2/F6, Security C-4, Data F6)**.

### T7 — Copy and constraints are drifting apart
Pricing page claims "All 5 exchanges"; `limits.py` says 2. README pitches "multi-user tracker" (generic); the actual differentiators (granular share + read-only + delegated access roadmap) are not in any marketing copy. **(Content F2, Monetization F4, Competitive F4)**.

---

## Critical Blockers — Must Fix This Sprint

Consolidated from all 12 reports, de-duplicated, ranked by impact × urgency. These are items that **block revenue, leak user data, or break the product under normal operating conditions**.

1. **Share-link visibility-flag leak** — `backend/app/api/v1/share.py:208-243` returns `usd_value`, `total_usd`, and `profile_name` regardless of `show_*` flags. `show_total_value=False` is trivially reversible by summing `usd_value`. `profile_name` is also injected into OG metadata. [Security C-1, Data implicit]

2. **`check_exchange_limit` is dead code — free-tier cap is unenforced** — defined in `backend/app/core/limits.py:25`, called from nowhere. Free users can add unlimited exchange keys. Direct revenue leak. [Data F1, Architecture F1, Monetization F3]

3. **Frontend Sentry has no PII scrubbing; backend Sentry doesn't exist** — `frontend/src/lib/sentry.ts` has no `beforeSend`, ships URLs including `/share/<token>` and OAuth-callback `?token=` query strings. Violates CLAUDE.md hard rule that exchange keys never leak to logs (Sentry is effectively an external log sink). [Security C-2, Analytics F6]

4. **JWT delivered via query string → `localStorage` → 24 h TTL → no revocation** — the XSS-chain trifecta. `auth.py:149-153` redirects with `?token=...`, frontend stuffs into `localStorage`, TTL is 1440 min, no `jti`, no deny-list. [Security C-3]

5. **`_oauth_states` in-memory dict breaks multi-instance deploys** — Railway blue/green and horizontal scale both yield 100% login failure with "Invalid OAuth state." [Security C-4, Architecture F2]

6. **`public_share_view` bypasses `app.state` cache singletons** — `share.py:208` calls `get_portfolio` without `redis` or `http_client` args; every public share view hits all exchanges fresh. Popular share links will drain exchange API quotas and spike latency. [Performance F1]

7. **`usePortfolio.ts:11` SWR URL bug — wrong route** — hook hits `/portfolio/${profileId}` while backend route is `/api/v1/portfolio/profile/{profile_id}`. Silent 404, SWR caching benefit entirely defeated. [Performance F2]

8. **Pricing page "Join waitlist" CTA is a dead anchor** — `#waitlist` has no matching element. The only self-service revenue path is a broken link. [UI/UX F3, Monetization F1, Growth F4, Content implicit]

9. **`OnboardingWizard` is an inaccessible modal** — no `role="dialog"`, no focus trap, no ESC handler. Screen reader + keyboard users locked out of the first-run experience. `ConfirmModal.tsx` already has the pattern and the `useFocusTrap` hook — just not wired up. [UI/UX F1, A11y F1]

10. **SEO sitemap + share canonical** — `sitemap.ts:6` hard-codes `yourdomain.com`; share page has no `canonical` and no `og:image`. Google indexes the wrong domain; social previews are blank. [SEO F1/F2/F3, Content F3/F5]

11. **No analytics on upgrade banner, onboarding, or share view** — the only three funnels the business cares about are all invisible. [Analytics F1/F2/F3, Growth F1]

---

## Top 20 Action Items — Ranked by ROI

Impact × Urgency / Effort. Pulled from all 12 reports, de-duplicated.

| # | Action | Cat | Effort | Impact | Files |
|---|--------|-----|--------|--------|-------|
| 1 | Gate `usd_value`/`total_usd`/`profile_name` behind `show_*` flags; add `show_profile_name` | Sec/Data | 2h | 🔴 Critical | `share.py`, `schemas/share_link.py`, `models/share_link.py`, new Alembic, `ShareLinkManager.tsx`, `share/[token]/page.tsx` |
| 2 | Call `check_exchange_limit` in key create endpoint | Data/Arch/Mon | 15m | 🔴 Critical | `backend/app/api/v1/keys.py` |
| 3 | Fix SWR URL: `/portfolio/${id}` → `/portfolio/profile/${id}` | Perf | 5m | 🔴 High | `frontend/src/hooks/usePortfolio.ts:11` |
| 4 | Pass `redis` + `http_client` to `get_portfolio` in share view | Perf | 15m | 🔴 High | `backend/app/api/v1/share.py:208` |
| 5 | Move OAuth `state` store to Redis | Sec/Arch | 1h | 🔴 Critical | `backend/app/api/v1/auth.py:29` |
| 6 | Frontend Sentry `beforeSend` scrubber + `tracesSampleRate: 0.0` | Sec/Anl | 1h | 🔴 Critical | `frontend/src/lib/sentry.ts` |
| 7 | Stripe Checkout integration + webhook; replace "Join waitlist" anchor | Mon/UX/Growth | L (2–3d) | 🔴 Revenue | `app/pricing/page.tsx`, new `webhooks.py`, `User` model (`stripe_customer_id`, `subscription_id`, `plan_expires_at`) |
| 8 | JWT → `HttpOnly` cookie; TTL 15 min; `jti` + Redis deny-list; drop `localStorage` | Sec | 1d | 🔴 Critical | `config.py`, `security.py`, `auth.py`, `api.ts`, `callback/page.tsx` |
| 9 | `UpgradeBanner` impression + click events + render on dashboard + onboarding end + share creation | Anl/Mon/Growth | S | 🟠 High | `UpgradeBanner.tsx`, `dashboard/page.tsx`, `OnboardingWizard.tsx`, `CreateShareLinkModal.tsx` |
| 10 | Onboarding funnel events (step/complete/skip) | Anl/Growth | 30m | 🟠 High | `OnboardingWizard.tsx` |
| 11 | `shareLinkViewed` client-component tracker on share page | Anl/Growth | 30m | 🟠 High | `app/share/[token]/page.tsx` |
| 12 | `OnboardingWizard` ARIA dialog + `useFocusTrap` + ESC | UX/A11y | S | 🟠 High | `OnboardingWizard.tsx` |
| 13 | Sitemap domain → `NEXT_PUBLIC_APP_URL`; add canonical + `og:image` + `og:url` on share | SEO/Content | S | 🟠 High | `sitemap.ts:6`, `share/[token]/page.tsx`, `public/og-default.png`, `layout.tsx` |
| 14 | Rate limit `/auth/*`, `/admin/*`, `/profiles/*/keys/*`, `POST /share` | Sec | 2h | 🟠 High | multiple |
| 15 | `AddKeyModal` — add `onTierLimit` → show `UpgradeBanner` | Mon/Growth | S | 🟠 High | `AddKeyModal.tsx` |
| 16 | Pricing copy audit — align "All 5 exchanges" with `limits.py`; add $79/yr annual plan + TR PPP pricing | Content/Mon | S | 🟠 High | `app/pricing/page.tsx` |
| 17 | Landing page at `/` — hero + value prop + CTA (replaces blanket redirect) | Content/SEO/Growth | M | 🟠 High | `app/page.tsx` |
| 18 | Admin audit log + `Enum(UserTier)` + `ADMIN_EMAILS` double-gate + use `UserTier.ADMIN` enum in admin gate | Sec/Data/Arch | 2h | 🟠 High | `admin.py`, `user.py`, new Alembic |
| 19 | Coinbase & Binance TR: enforce read-only or refuse to enable | Sec | 4h | 🟠 High | `exchanges/coinbase.py`, `exchanges/binancetr.py` |
| 20 | CI workflow: `ruff`, `pytest`, `pnpm lint`, `pip-audit`, Bandit/Semgrep | Arch/Sec | 2h | 🟡 Medium | `.github/workflows/ci.yml` |

**Notable "just below the cut-off":** social share buttons after link copy (Growth F2), Redis lock on Binance cache refresh (Perf F6), `TrustedHost` + HSTS + trim `/health` (Sec H-4), design-token codemod (UX F2), skip-to-main link (A11y F4), PWA manifest (Competitive), Coinbase + Kraken adapters (Competitive F1).

---

## Sprint Recommendation — Next 2 Weeks

Three columns: **Must** (blocks launch / leaks data / blocks revenue), **Should** (foundation for the next month of work), **Could** (nice-to-have if time permits).

### Must (target: days 1–7)
1. Share-link visibility-flag fix + `show_profile_name` column (#1)
2. `check_exchange_limit` wire-up (#2)
3. SWR URL fix (#3)
4. Share endpoint cache singletons (#4)
5. Redis-backed OAuth state (#5)
6. Sentry `beforeSend` scrubber + tracing off (#6)
7. JWT → HttpOnly cookie migration (#8)
8. Stripe Checkout MVP — $9/mo plan + webhook + replace "Join waitlist" anchor (#7)
9. `AddKeyModal` → `onTierLimit` → upgrade banner (#15)
10. Rate limits on auth/admin/keys/share-create (#14)

### Should (target: days 8–14)
11. Analytics wire-up: `shareLinkViewed`, onboarding funnel, upgrade impression/click (#9–11)
12. `OnboardingWizard` a11y + ARIA dialog (#12)
13. Sitemap + canonical + OG image (#13)
14. Admin hardening: audit log, Enum(UserTier), ADMIN_EMAILS double-gate (#18)
15. Pricing copy audit + annual plan + TR PPP (#16)
16. Coinbase/Binance TR read-only enforcement (#19)
17. CI workflow (#20)
18. Landing page at `/` (#17)

### Could (stretch)
- Social share buttons after copy (Growth F2)
- Design token codemod (UX F2)
- `text-gray-500` → `text-gray-400` contrast fix (A11y F3)
- Skip-to-main link (A11y F4)
- `TrustedHost` + HSTS + security-headers middleware (Sec H-4)
- `python-jose` → `pyjwt` migration (Sec M-6)
- Binance bulk-ticker cache narrowed to held assets (Perf F4)
- PWA manifest + service worker (Competitive)
- Dashboard `useEffect` → SWR migration (Perf F3)

---

## Progress vs 2026-04-06

### What improved (major)
- **Authentication shipped end-to-end.** Google OAuth → JWT → `get_current_user` dependency on 16 protected endpoints. Multi-user isolation enforced everywhere. This single change closed the biggest April 6 cross-cutting theme.
- **Performance bottleneck fixed.** `asyncio.gather` for parallel exchange fetch; Binance bulk ticker; `selectinload` on ORM; `app.state` singletons for Redis + httpx.
- **Binance `await` bug** (flagged in 3 April 6 reports) — fixed.
- **Analytics jumped 1 → 5.** Plausible + env-gated Sentry + `view_count` + admin stats endpoint + exchange/tier distribution. Foundation is solid; wire-up is not.
- **A11y jumped 2.5 → 5.** `useFocusTrap`, `ConfirmModal` correct, `aria-live` on loading, `role="alert"` on errors.
- **SEO jumped 2 → 5.** `robots.txt`, `sitemap.ts`, OG tags, Twitter Card, `generateMetadata()` on share page, favicon.
- **Data category is new.** 7 Alembic migrations, indexes, atomic `view_count` increment, COIN-3/5 schema work.
- **Monetization scaffold exists.** `UserTier` enum, `limits.py`, `UpgradeBanner`, `/pricing` page, tier distribution in admin stats.

### What regressed / new critical issues
- **Share-link visibility leak (C-1)** — introduced by COIN-3 work. Was not present on April 6 because there was no public share view endpoint.
- **Unscrubbed Sentry (C-2)** — COIN-4 claim was "Sentry with PII scrubbing"; it shipped with neither scrubbing nor a backend SDK.
- **`check_exchange_limit` dead code** — COIN-5 introduced the limit function but forgot to call it.
- **`_oauth_states` in-memory dict** — pre-existing but now more dangerous, because the product is about to have real users.
- **`usePortfolio` SWR URL bug** — new in the performance push; silently 404s.
- **`OnboardingWizard` a11y regression** — the new modal does none of what `ConfirmModal` does.

### What stayed flat
- **Content (5/10)** — still no landing page, pricing copy still wrong, no error pages.
- **Competitive (4/10)** — still 3 exchanges; no Coinbase, no Kraken, no mobile, no tax export, no TR localization.

### New-ticket attribution
All three recently-merged ticket streams (COIN-3, COIN-4, COIN-5) shipped a critical bug. That is a **100% regression rate on recent feature work** — not because the code is bad, but because there is no CI, no integration-test coverage of the new features, and no PR checklist for "did you wire it up." This is the single strongest argument for Action Item #20 (CI workflow).

---

## Cost & Risk Estimate

Rough engineering cost to clear the backlog, assuming one senior full-stack engineer working solo.

| Severity | Count | Est hours | Calendar days |
|----------|-------|-----------|----------------|
| 🔴 Critical (Must this sprint) | 11 | 32–40 h | 5–6 d |
| 🟠 High (Should this sprint) | 18 | 40–60 h | 6–9 d |
| 🟡 Medium (backlog) | 22 | 40–60 h | 6–9 d |
| 🟢 Hardening (nice-to-have) | 15 | 30–40 h | 4–6 d |
| **Total** | **~66** | **140–200 h** | **21–30 d** |

**Risk ranking (what hurts worst if left unfixed this sprint):**

1. **Share-link visibility leak** — CVSS ~7.5 confidentiality; one tweet from a security researcher = brand event.
2. **Unscrubbed Sentry** — every exception currently leaks share tokens and potentially balances to a third party. Every hour un-fixed = more leaked events.
3. **JWT-via-URL + localStorage** — XSS chain; any reflected XSS in any share-page input = account takeover.
4. **`check_exchange_limit` dead code** — direct revenue leak, proportional to the number of free users who notice (low today, 100% tomorrow when a Reddit thread discovers it).
5. **`_oauth_states` in-memory** — 100% login failure on first Railway scale-out or blue/green deploy. Currently masked because deploys are rare.
6. **Stripe not integrated** — opportunity cost: ~$54K–$216K ARR per the monetization report's 12-month target. Every week of delay = ~$1K–4K ARR lost.

---

## Appendix — Category Summaries

### 01 — UI/UX Design — 6/10
Big jump from 4.5. Login redesign, unified nav, `SkeletonCard`, `ConfirmModal` (a correct a11y reference), `UpgradeBanner`, `AllocationChart` "Others" grouping. But design tokens are decorative only, `OnboardingWizard` has none of `ConfirmModal`'s a11y patterns, and the pricing "Join waitlist" CTA is a dead anchor at the exact revenue-funnel exit point. **Top finding:** scaffold exists; adoption is the missing codemod.

### 02 — Performance — 7/10
The biggest single-category jump (+3). `asyncio.gather`, bulk Binance ticker, `selectinload`, `app.state` singletons. **Two critical bugs undo much of it:** share endpoint bypasses the cache singletons on every view, and the SWR hook URL is wrong. Both are <30-min fixes that recover the full gain.

### 03 — SEO — 5/10
`robots.txt`, sitemap, OG tags, `generateMetadata()`, favicon — all new. But the sitemap hard-codes `yourdomain.com`, there's no canonical, no `og:image`, and `/` still redirects to `/dashboard` so Google has nothing to index. **Top finding:** 90% of the plumbing is in, but one stray placeholder and one missing landing page cap the ceiling at 5.

### 04 — Data & Database — 6/10 (new)
7 Alembic migrations, indexes, atomic `view_count`, COIN-3/5 schema work. **Top finding:** `check_exchange_limit` is defined and never called — the free-tier cap is unenforceable at the API layer. Also `UserTier` is `String(50)` at the DB level instead of `Enum`, timezone handling is inconsistent across migrations 004+, and there's no backup policy.

### 05 — Monetization — 4/10
Up from 2 because the scaffold exists: `UserTier` enum, `limits.py`, `UpgradeBanner`, `/pricing` page, tier distribution in admin stats. **Stays at 4** because no payment integration exists and "Join waitlist" is a dead anchor. **Top finding:** revenue is one Stripe integration away; the infrastructure is already there.

### 06 — Growth & Engagement — 6/10
`OnboardingWizard`, share-page viral footer with "Start with CoinHQ" CTA, `view_count` display, `EmptyState`, `UpgradeBanner`. **Top finding:** the viral loop has a footer CTA but no "share on Twitter/Telegram" after copy, and the upgrade prompt only fires on a settings-page 403 — three more conversion surfaces are missed (dashboard, onboarding end, share creation).

### 07 — Security & Infrastructure — 6.5/10
Opus-graded. The biggest jump in absolute posture since April 6: auth, tenant isolation, read-only key validation (except Coinbase/BinanceTR), structured logging, Alembic, CORS narrowed. **Four 🔴 critical** items — share-link leak (C-1), unscrubbed Sentry (C-2), JWT-URL+localStorage chain (C-3), in-memory OAuth state (C-4) — and 7 🟠 high. **Top finding:** good fundamentals, but COIN-3/4/5 each shipped a critical, and several pre-existing weaknesses (JWT hygiene, HSTS, rate-limit coverage) remain.

### 08 — Content Strategy — 5/10
Flat. OG tags + `generateMetadata` shipped, but there's still no landing page, pricing copy says "All 5 exchanges" (actual limit is 2), and no custom 404 for expired/broken share links. **Top finding:** the product has no crawlable, human-readable explanation of what it is.

### 09 — Analytics & Tracking — 5/10
Biggest categorical jump (+4). Plausible, env-gated Sentry, `view_count`, admin stats with tier/exchange distribution. **Top finding:** the three events that matter — onboarding funnel, upgrade impression/click, share-link view — are all either undefined or defined-but-never-called. The pipes are laid; nothing flows through them.

### 10 — Architecture & Code Quality — 7/10
Auth complete, adapter pattern clean, `asyncio.gather`, `selectinload`, `structlog`, `_mask_key()` helper, test suite bootstrapped. **Top finding:** `_oauth_states` module-level dict is a single-instance architectural assumption hidden in 3 lines of code; Railway deploys will break on first scale-out. Also no CI workflow, so every regression ships.

### 11 — Accessibility — 5/10
Up from 2.5. `useFocusTrap`, `ConfirmModal` is a correct reference, `aria-live` on loading, `role="alert"` on errors, form label pairs. **Top finding:** `OnboardingWizard` is a modal that doesn't declare itself as one — no `role="dialog"`, no focus trap, no ESC. The hook is already written; it just isn't imported. Also `text-gray-500` on `bg-gray-900` fails WCAG AA at ~3.9:1.

### 12 — Competitive Analysis — 4/10
Flat. Still 3 exchanges vs rivals' 100–700+, no mobile, no tax reporting, README still says "multi-user crypto tracker" (generic). **Top finding:** the differentiators (granular share + view tracking + read-only + delegated access roadmap) are real and rivals don't have them — but they aren't in any marketing copy. Quick wins: Coinbase adapter (unlocks US market), TR localization + BtcTurk/Paribu (unlocks a rival-free niche), PWA manifest (cheapest mobile play).

---

## Narrative — What is the story of this product right now?

Four days ago, CoinHQ was a scaffold without an identity: no auth, no tracking, no money path, no viral loop, no content. The April 6 audit scored it 3.4/10 and the dominant theme was "authentication missing, everything downstream blocked."

Today, CoinHQ is a working multi-user product with a complete Phase 1 surface. The authentication theme is closed. A share-link viral loop exists. A tier system exists. An onboarding wizard exists. A pricing page exists. The weighted score is 5.6.

But the new picture is more subtle: **every COIN-3/4/5 ticket shipped with a critical bug that undid the feature.** COIN-3 (share view tracking) shipped with a visibility-flag leak. COIN-4 (error tracking) shipped with no scrubbing. COIN-5 (tier gate) shipped with the gate function never called. That is a process signal, not a code signal — it means the team is shipping faster than the verification layer can keep up.

The good news is that the "last mile" is cheap. The share-link leak is a 2-hour fix. The cache-singleton bug is 15 minutes. The dead-code gate is 15 minutes. Stripe Checkout is 2–3 days. A CI workflow is 2 hours. **If the next sprint treats "wire-up verification" as a first-class deliverable — CI, integration tests, a PR checklist — then the 2026-04-10 → 2026-04-20 jump will be as large as the 2026-04-06 → 2026-04-10 jump, and CoinHQ converts from demo-grade to revenue-ready.**

The risk is the opposite trajectory: more features ship, more scaffolds are merged without wire-up, and the "defined but never called" list grows. Theme T1 is the single most important thing to watch in the next audit.

---

**Totals across all reports:**
- 🔴 Critical: **14** (consolidated from 18 raw)
- 🟠 High: **24**
- 🟡 Medium: **35**
- 🟢 Good / hardening: **28**
- **Total findings:** ~101 across 12 categories

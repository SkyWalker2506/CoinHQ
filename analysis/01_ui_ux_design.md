# UI/UX Design Analysis — CoinHQ
_Date: 2026-04-10 · Lead: ArtLead (A9) · Model: Sonnet 4.6_

## Delta vs 2026-04-06

| Item | April 6 | April 10 | Status |
|------|---------|----------|--------|
| Login page | Basic | Redesigned with branding | ✅ |
| `SkeletonCard` loading states | Missing | Component added | ✅ |
| Navigation bar | Inconsistent | Unified across pages | ✅ |
| `ConfirmModal` (replaces browser `confirm()`) | Missing | Custom modal with a11y | ✅ |
| Design tokens in `tailwind.config.ts` | None | `brand`/`surface`/`border` defined | ⚠️ Defined but not adopted |
| `AllocationChart` "Others" grouping | Missing | Implemented | ✅ |
| `UpgradeBanner` (COIN-5) | N/A | Added | ✅ |
| Cached data indicator | Missing | Added | ✅ |
| `OnboardingWizard` a11y | N/A | No `role="dialog"`, no focus trap | 🔴 |
| Pricing `#waitlist` dead anchor | N/A | Still broken | 🔴 |

**Score: 4/10 → 6/10**

## Current State

Login (`frontend/src/app/login/page.tsx`), dashboard, settings, and share view all share a consistent dark theme with the unified navigation component. `SkeletonCard` component handles loading states gracefully across the dashboard.

`tailwind.config.ts` defines semantic tokens (`brand`, `surface`, `border`) but components still use raw Tailwind utilities like `bg-gray-900`, `border-gray-800`. The token layer is decorative only.

`OnboardingWizard.tsx` is a 3-step modal (profile → exchange → share) triggered via `localStorage['onboarding_done']`. It lacks `role="dialog"`, `aria-modal="true"`, focus trap, and ESC key handling — unlike `ConfirmModal.tsx` which implements these correctly.

Pricing page (`frontend/src/app/pricing/page.tsx`) has a "Join waitlist" CTA linked to `#waitlist` anchor that doesn't exist on the page. Silent click failure.

## Findings

### 🔴 Critical

**F1 — OnboardingWizard missing ARIA dialog attributes and focus trap**
`frontend/src/components/OnboardingWizard.tsx` — No `role="dialog"`, `aria-modal`, focus trap, or ESC key support. Screen reader users cannot detect the modal. Keyboard users can tab out. Compare with `ConfirmModal.tsx` which is correctly built with focus trap hook. Fix: port the ConfirmModal a11y pattern to OnboardingWizard.

**F2 — Design tokens defined but not adopted**
`frontend/tailwind.config.ts` — `brand`, `surface`, `border` tokens declared but all components use raw `bg-gray-900`, `border-gray-800`, `text-gray-100` etc. Theme changes (white-label, dark/light toggle, future branding update) require touching every component. Fix: systematic codemod to replace raw grays with semantic tokens.

**F3 — Pricing page `#waitlist` CTA goes nowhere**
`frontend/src/app/pricing/page.tsx:28` — Premium plan button links to `#waitlist` anchor but no element with `id="waitlist"` exists. Click = silent failure at the monetization funnel exit point. Fix: implement a form, waitlist modal, or redirect to Stripe.

### 🟡 Important

**F4 — No dark/light mode toggle** — App is dark-only. Mobile users in bright environments struggle. `next-themes` is a ~30-min integration.

**F5 — Mobile responsive gaps** — Settings page key list overflows on <375px viewports; `ShareLinkManager` copy button hit area too small for thumb navigation.

**F6 — Color contrast on secondary text** — `text-gray-500` on `bg-gray-900` fails WCAG AA (contrast ratio ~3.9:1, requirement: 4.5:1). Affects placeholder text, descriptions, timestamps.

**F7 — Upgrade prompt placement too narrow** — `UpgradeBanner` only appears in settings after a 403 error. Users who never hit the limit never see a conversion surface.

### 🟢 Good

**F8 — `ConfirmModal` correctly implements a11y patterns.** Focus trap hook, `role="dialog"`, `aria-modal`, ESC close. Can be reused as template for all new modals.

**F9 — `AllocationChart` "Others" grouping.** Prevents chart clutter when user holds 20+ tokens.

**F10 — `SkeletonCard` loading states.** Provides perceived performance improvement across dashboard.

## Action Items

| # | P | Fix | File | Effort |
|---|---|-----|------|--------|
| 1 | 🔴 | OnboardingWizard ARIA + focus trap | `components/OnboardingWizard.tsx` | S |
| 2 | 🔴 | Pricing `#waitlist` — live form or Stripe link | `app/pricing/page.tsx` | S |
| 3 | 🔴 | Adopt design tokens across components | codemod `frontend/src/` | M |
| 4 | 🟡 | `next-themes` light/dark toggle | app layout | S |
| 5 | 🟡 | Mobile responsive fixes (<375px) | settings, `ShareLinkManager.tsx` | S |
| 6 | 🟡 | Secondary text contrast fix | design tokens | XS |
| 7 | 🟡 | Upgrade prompt → dashboard + onboarding end | `dashboard/page.tsx`, `OnboardingWizard.tsx` | S |
| 8 | 🟢 | Empty state consistency audit | dashboard views | S |

## References
- `frontend/src/components/OnboardingWizard.tsx`, `ConfirmModal.tsx`, `UpgradeBanner.tsx`, `SkeletonCard.tsx`
- `frontend/tailwind.config.ts`
- `frontend/src/app/pricing/page.tsx`
- `analysis/archive_2026-04-06/01_ui_ux_design.md`

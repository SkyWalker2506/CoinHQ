# Accessibility Analysis — CoinHQ
_Date: 2026-04-10 · Lead: ArtLead (A9) · Model: Sonnet 4.6_

## Delta vs 2026-04-06

| Item | April 6 | April 10 | Status |
|------|---------|----------|--------|
| Focus trap hook | Missing | `useFocusTrap` implemented | ✅ |
| `aria-live` on loading state | Missing | Added on portfolio loading | ✅ |
| `role="alert"` on error messages | Missing | Added | ✅ |
| `htmlFor`/`id` on modal forms | Missing | Implemented in modal forms | ✅ |
| `OnboardingWizard` ARIA dialog | N/A | Missing `role="dialog"`, no focus trap | 🔴 |
| Color contrast on secondary text | — | Fails WCAG AA (`text-gray-500` on `bg-gray-900`) | 🟡 |
| Keyboard nav for share link list | — | No keyboard-accessible copy action | 🟡 |
| Skip-to-main link | Missing | Still missing | 🟡 |
| `alt` text on images/charts | — | Charts have no `aria-label` | 🟡 |

**Score: 2/10 → 5/10**

## Current State

Significant a11y progress since April 6. `ConfirmModal.tsx` is the reference implementation: focus trap via `useFocusTrap` hook, `role="dialog"`, `aria-modal="true"`, ESC key close, `aria-labelledby`. Portfolio loading has `aria-live="polite"` announcement. Error states use `role="alert"`.

`OnboardingWizard.tsx` is a major regression point relative to `ConfirmModal` — it's a modal that doesn't declare itself as one. Screen readers will read through it as if it were inline page content. Focus is not trapped; keyboard users can tab to elements behind the overlay.

Color contrast: `text-gray-500` on `bg-gray-900` background yields a contrast ratio of approximately 3.9:1 — below the WCAG AA requirement of 4.5:1 for normal text. This affects timestamps, secondary labels, and description text throughout the app.

## Findings

### 🔴 Critical

**F1 — `OnboardingWizard` is an inaccessible modal**
`frontend/src/components/OnboardingWizard.tsx` — No `role="dialog"`, no `aria-modal`, no `aria-labelledby`, no focus trap, no ESC key handler. The wizard renders as a visually-positioned overlay but semantically as inline content. Screen reader users receive no dialog announcement, and keyboard users can navigate past the overlay into the background page.

Compare `ConfirmModal.tsx` which has all of these correctly. The `useFocusTrap` hook already exists in the codebase — it just isn't wired to `OnboardingWizard`.

Fix (concrete):
```tsx
// OnboardingWizard.tsx
<div
  role="dialog"
  aria-modal="true"
  aria-labelledby="onboarding-title"
  ref={dialogRef}  // useFocusTrap(dialogRef)
>
  <h2 id="onboarding-title">Set up your portfolio</h2>
  ...
</div>
```

### 🟡 Important

**F2 — `AllocationChart` has no accessible label or data table fallback**
`frontend/src/components/AllocationChart.tsx` — Chart is rendered via a canvas/SVG element with no `aria-label`, no `title`, no hidden data table. Screen readers see nothing. Fix: `aria-label="Portfolio allocation by asset"` on the chart container; consider a hidden `<table>` with the same data for screen reader users.

**F3 — Color contrast failures — `text-gray-500` on dark backgrounds**
Multiple components — description text, timestamps (`ShareLinkManager.tsx:165`, `dashboard/page.tsx`), placeholder text in forms. Contrast ratio ~3.9:1 vs WCAG AA 4.5:1. Fix: shift to `text-gray-400` (contrast ~5.2:1 on `bg-gray-900`) for secondary text.

**F4 — No skip-to-main link**
`frontend/src/app/layout.tsx` — No `<a href="#main-content" className="sr-only focus:not-sr-only">Skip to main content</a>` at top of page. Keyboard-only users must tab through the entire navigation on every page load. One-line fix with Tailwind `sr-only focus:not-sr-only` pattern.

**F5 — Share link copy button not keyboard-accessible**
`frontend/src/components/ShareLinkManager.tsx:59–76` — The "Copy" icon button has no visible label beyond the icon. `aria-label="Copy share link"` is missing. Keyboard-accessible tooltip or visible label needed.

**F6 — `FollowButton` has incomplete semantic markup**
`frontend/src/app/share/[token]/page.tsx:79` — `FollowButton` renders but its purpose is unclear even visually. No `aria-pressed` to indicate follow state. Fix when the feature is completed.

### 🟢 Good

**F7 — `ConfirmModal` is a correct reference implementation.** `role="dialog"`, focus trap, ESC close, `aria-labelledby`. Port this pattern to all future modals.

**F8 — Form fields have `htmlFor`/`id` pairs.** Modal forms now correctly associate labels with inputs.

**F9 — `aria-live="polite"` on portfolio loading.** Screen reader users are informed when portfolio data finishes loading.

**F10 — `role="alert"` on error states.** API errors are announced by screen readers.

## Action Items

| # | P | Fix | File | Effort |
|---|---|-----|------|--------|
| 1 | 🔴 | OnboardingWizard ARIA dialog + focus trap | `components/OnboardingWizard.tsx` | S |
| 2 | 🟡 | `AllocationChart` `aria-label` + hidden data table | `components/AllocationChart.tsx` | S |
| 3 | 🟡 | Color contrast fix — `text-gray-400` for secondary text | design tokens, components | XS |
| 4 | 🟡 | Skip-to-main link in layout | `app/layout.tsx` | XS |
| 5 | 🟡 | `aria-label="Copy share link"` on copy button | `components/ShareLinkManager.tsx:59` | XS |
| 6 | 🟢 | `aria-pressed` on FollowButton when feature completes | `components/FollowButton.tsx` | XS |
| 7 | 🟢 | WCAG 2.1 AA audit with axe-core in CI | `frontend/package.json` | S |

## References
- `frontend/src/components/OnboardingWizard.tsx`, `ConfirmModal.tsx`
- `frontend/src/components/AllocationChart.tsx`, `ShareLinkManager.tsx`
- `frontend/src/app/layout.tsx`
- `analysis/archive_2026-04-06/11_accessibility.md`

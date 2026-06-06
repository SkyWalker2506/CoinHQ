# Content Strategy Analysis — CoinHQ
_Date: 2026-04-10 · Lead: ArtLead (A9) · Model: Sonnet 4.6_

## Delta vs 2026-04-06

| Item | April 6 | April 10 | Status |
|------|---------|----------|--------|
| OG meta tags (`og:title`, `og:description`) | Missing | Added in `layout.tsx` | ✅ |
| Twitter Card metadata | Missing | `summary` card added | ✅ |
| Share page dynamic `generateMetadata()` | Missing | Implemented with profile name | ✅ |
| Favicon | Missing | `favicon.ico` added | ✅ |
| Landing page at `/` | Missing | Still redirects to `/dashboard` | 🔴 |
| Product description / value prop copy | Weak | Still only README | 🟡 |
| Pricing page copy accuracy | — | "All 5 exchanges" — incorrect | 🟡 |
| Onboarding tooltip/guide copy | — | Wizard has copy, no review | 🟡 |

**Score: 2/10 → 5/10**

## Current State

Global metadata is now set in `frontend/src/app/layout.tsx:9–25` with `og:title`, `og:description`, `og:type: "website"`, and `twitter:card: "summary"`. The share page (`share/[token]/page.tsx:7–27`) uses `generateMetadata()` to generate dynamic per-share titles and descriptions based on `profile_name`.

There is no marketing landing page. The root route (`app/page.tsx:3`) redirects authenticated users to `/dashboard` and unauthenticated users to `/login`. Google bots and cold organic traffic have nothing to index. The only public, indexable, SEO-valuable pages are `/share/[token]` and `/pricing`.

Pricing page copy (`frontend/src/app/pricing/page.tsx`) states "All 5 exchanges" for the free tier, but the actual exchange limit is 2, not 5. The "5 exchanges" figure appears to be from an earlier design. Copy and constraints are out of sync.

## Findings

### 🔴 Critical

**F1 — No marketing landing page at `/`**
`frontend/src/app/page.tsx:3` — Root redirects all traffic. There is no crawlable, human-readable landing page explaining the product. This is the single biggest content gap: users arriving from share links, social media, or organic search hit `/login` with no context. Fix: a minimal landing page (hero + value prop + "Get started free" CTA) at `/`.

**F2 — Pricing page copy is factually incorrect**
`frontend/src/app/pricing/page.tsx` — "All 5 exchanges" appears in the feature list for both free and premium plans, but the actual free-tier limit (`backend/app/core/limits.py:5–13`) is 2 exchange keys per profile, not 5. This creates false expectations and will drive support tickets. Fix: audit every feature claim on the pricing page against actual `limits.py` values.

### 🟡 Important

**F3 — Share page OG tags missing `og:image`**
`frontend/src/app/share/[token]/page.tsx:17–20` — `generateMetadata()` returns `og:title` and `og:description` but no `og:image`. Twitter/Discord/Telegram link unfurls show a blank card. Fix: add `public/og-default.png` (1200×630) as static fallback in `layout.tsx`.

**F4 — Onboarding wizard copy not reviewed for tone/clarity**
`frontend/src/components/OnboardingWizard.tsx` — 3-step wizard exists but copy hasn't been reviewed for clarity. Step 2 ("Connect Exchange") may confuse users about what "read-only" means and why it's safe. Fix: add a short "Why read-only? We never trade." reassurance in step 2.

**F5 — `sitemap.ts` has `yourdomain.com` placeholder**
`frontend/src/app/sitemap.ts:6` — The sitemap URL uses a literal `yourdomain.com`. Robots.txt references this sitemap. Search engines indexing this sitemap will follow the wrong domain. Fix: `process.env.NEXT_PUBLIC_APP_URL`.

**F6 — No error page copy (404, 500)**
No custom `not-found.tsx` or `error.tsx` at the app level. Users hitting broken share links or expired tokens see Next.js default error pages. Fix: add branded 404 with "This portfolio may have been made private" copy for share link not-found scenarios.

### 🟢 Good

**F7 — Share page `generateMetadata` is well-structured.** Dynamic title pattern "username's Crypto Portfolio — CoinHQ" is shareable and SEO-friendly.

**F8 — `UpgradeBanner` copy is clear and actionable.** "You've reached the free tier limit. Upgrade to Premium." is straightforward.

## Action Items

| # | P | Fix | File | Effort |
|---|---|-----|------|--------|
| 1 | 🔴 | Landing page at `/` — hero + value prop + CTA | `app/page.tsx`, new landing component | M |
| 2 | 🔴 | Pricing copy audit — align with `limits.py` actual values | `app/pricing/page.tsx` | S |
| 3 | 🟡 | `og:image` static fallback (1200×630) | `public/og-default.png` + `layout.tsx` | S |
| 4 | 🟡 | Onboarding step 2 — add read-only safety reassurance | `components/OnboardingWizard.tsx` | XS |
| 5 | 🟡 | `sitemap.ts` domain — use `NEXT_PUBLIC_APP_URL` | `app/sitemap.ts:6` | XS |
| 6 | 🟡 | Custom 404 / error pages | `app/not-found.tsx`, `app/error.tsx` | S |
| 7 | 🟢 | JSON-LD `SoftwareApplication` schema on landing/pricing | new landing page | S |

## References
- `frontend/src/app/layout.tsx`
- `frontend/src/app/share/[token]/page.tsx`
- `frontend/src/app/pricing/page.tsx`
- `frontend/src/app/sitemap.ts`
- `frontend/src/components/OnboardingWizard.tsx`
- `backend/app/core/limits.py`
- `analysis/archive_2026-04-06/08_content_strategy.md`

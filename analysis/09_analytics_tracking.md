# Analytics & Tracking Analysis — CoinHQ
_Date: 2026-04-10 · Lead: GrowthLead (A11) · Model: Sonnet 4.6_

## Delta vs 2026-04-06

| Item | April 6 | April 10 | Status |
|------|---------|----------|--------|
| Frontend analytics (Plausible) | Yoktu | Env-gated script + `analytics.ts` util | ✅ |
| Share link `view_count` | Yoktu | Backend model + API + frontend display | ✅ |
| Frontend error tracking (Sentry) | Yoktu | Env-gated `sentry.ts` + `ErrorBoundaryWrapper` | ✅ |
| Key action events (exchange, share, profile) | Yoktu | `events.exchangeConnected`, `shareLinkCopied`, `profileCreated` | ✅ |
| Admin stats endpoint | Yoktu | `/api/v1/admin/stats` — users/profiles/keys/tiers/exchanges | ✅ |
| `shareLinkViewed` event called on share page | — | Defined in `analytics.ts` but **never called** | 🔴 |
| Onboarding funnel events | — | Missing | 🔴 |
| Upgrade conversion events | — | Missing | 🔴 |
| Backend structured logging | Yoktu | Hâlâ yok | 🟡 |
| Admin frontend UI | Yoktu | Hâlâ yok (API-only) | 🟡 |

**Score: 1/10 → 5/10**

## Current State

**Plausible integration:** `frontend/src/app/layout.tsx:35–40` — `NEXT_PUBLIC_PLAUSIBLE_DOMAIN` env var varsa Next.js `<Script defer>` ile Plausible script yükleniyor. Env yoksa script yüklenmiyor — self-hosted için doğru tasarım.

**Analytics util:** `frontend/src/lib/analytics.ts:1–12` — `trackEvent()` wrapper tanımlanmış. `events` nesnesi: `exchangeConnected`, `shareLinkCopied`, `profileCreated`, `shareLinkViewed`. Plausible `window.plausible` objesi üzerinden çalışıyor.

**Event usage:** `analytics.ts` eventi kullanan yerler:
- `ShareLinkManager.tsx:62` → `events.shareLinkCopied()`
- `AddProfileModal.tsx:35` → `events.profileCreated()`
- `AddKeyModal.tsx:114` → `events.exchangeConnected(exchange)`
- `shareLinkViewed` → **tanımlanmış ama hiçbir yerde çağrılmıyor**

**Sentry:** `frontend/src/lib/sentry.ts` — `NEXT_PUBLIC_SENTRY_DSN` yoksa yüklenmez (dynamic import). `captureError()` fonksiyonu `@sentry/nextjs`'i lazy load ediyor. `ErrorBoundaryWrapper` (`lib/error-boundary-wrapper.tsx`) ile entegre.

**Backend admin stats:** `backend/app/api/v1/admin.py:20–49` — `/admin/stats` endpoint'i: user count, profile count, active share links, exchange key count, exchange distribution (per-exchange), tier distribution (free/pro/admin). Admin tier kontrolü var.

**View count:** `backend/app/models/share_link.py:25–26` — `view_count: Mapped[int]`, `last_viewed_at: Mapped[datetime | None]`. Backend `public.py:195` — `view_count = view_count + 1` + `last_viewed_at = now()` atomic update. `ShareLinkManager.tsx:162–166` — frontend'de gösteriliyor.

## Findings

### 🔴 Critical

**F1 — `shareLinkViewed` eventi tanımlı ama asla çağrılmıyor**
`frontend/src/lib/analytics.ts:11` — `shareLinkViewed: (token: string) => trackEvent('Share Link Viewed')` tanımlanmış. Ancak `share/[token]/page.tsx`'te hiçbir yerde kullanılmıyor. Share sayfası SSR — event'i client tarafında tetiklemek için `useEffect` ile bir client component gerekli. Bu eksik olduğu için Plausible dashboard'da share link görüntüleme sayısı görünmüyor; sadece DB'deki `view_count` var. Fix: Share page'e küçük bir `<SharePageTracker token={token} />` client component ekle.

**F2 — Upgrade impression ve click conversion tracking yok**
`frontend/src/components/UpgradeBanner.tsx` — `UpgradeBanner` gösterilince ve "Upgrade" butonuna tıklanınca hiç event yok. Kaç kullanıcının banner gördüğü, kaçının tıkladığı bilinmiyor. Bu, tier upgrade funnel'ının temel metriği. Fix: `useEffect(() => trackEvent('Upgrade Banner Shown'), [])` ve button `onClick`'e `trackEvent('Upgrade Clicked')` ekle.

**F3 — Onboarding funnel tamamen kör**
`frontend/src/components/OnboardingWizard.tsx` — `handleComplete()` ve "Skip setup" click'i için event yok. Adım geçişleri (`step → step+1`) de takip edilmiyor. "Kaç kullanıcı onboarding'i tamamlıyor?" sorusu yanıtsız. Fix: her adım geçişinde `trackEvent('Onboarding Step', { step: step + 1 })`, tamamlanınca `trackEvent('Onboarding Completed')`, skip'te `trackEvent('Onboarding Skipped', { at_step: step })`.

### 🟡 Medium

**F4 — Admin stats'ta `total_view_count` yok**
`backend/app/api/v1/admin.py:26–48` — Endpoint user/profile/key sayılarını, tier dağılımını ve exchange dağılımını veriyor ama toplam share link görüntüleme sayısını (`SUM(view_count)`) vermiyor. Bu, ürünün viral reach'ini gösteren en önemli agregat metrik. Fix: `total_views = await db.scalar(select(func.sum(ShareLink.view_count)))` ekle.

**F5 — Backend yapısal loglama yok**
FastAPI backend'de `structlog` veya JSON loglama yok. Exchange API hataları (`ExchangeList.tsx`, backend adapter) sessizce geçebiliyor. Hangi exchange'in hata verdiği, hangi kullanıcının etkilendiği bilinemez. Monitoring'in Sentry dışında backend logu da olmalı.

**F6 — Sentry sadece frontend, backend'de yok**
`frontend/src/lib/sentry.ts` — Sentry yalnızca Next.js tarafında. FastAPI backend'de Sentry SDK (`sentry-sdk[fastapi]`) entegre değil. Backend exception'ları Sentry'de görünmüyor.

**F7 — Admin stats için frontend UI yok**
`/admin/stats` endpoint var ama bunu görselleştiren bir sayfa yok. Admin kullanıcısı curl veya Postman kullanmak zorunda. En basit hâliyle bile bir `/admin` Next.js sayfası deployment'ı kolaylaştırır.

### 🟢 Good

**F8 — Analytics env-gated: self-hosted kullanıcılar etkilenmiyor**
`layout.tsx:35` ve `sentry.ts:3` — Her iki tracking sistemi de env var yoksa tamamen devre dışı. Bundle'a extra kod eklemiyor. Privacy-first self-hosted kullanıcılar için doğru yaklaşım.

**F9 — `view_count` atomic update**
`backend/app/api/public.py:195` — `values(view_count=ShareLink.view_count + 1)` SQL atomic update. Race condition riski yok.

**F10 — Exchange bazlı granüler admin stats**
`admin.py:34–36` — `GROUP BY ExchangeKey.exchange` ile hangi exchange'in en çok kullanıldığı görülüyor. Tier breakdown (`admin.py:38–40`) da eklendi (COIN-5). Bu ürün kararları için değerli.

## Action Items

| # | P | Fix | File | Effort |
|---|---|-----|------|--------|
| 1 | 🔴 | `shareLinkViewed` event'ini share page'de çağır | `app/share/[token]/page.tsx` (new client component) | S |
| 2 | 🔴 | Upgrade banner impression + click event | `components/UpgradeBanner.tsx` | XS |
| 3 | 🔴 | Onboarding step/complete/skip events | `components/OnboardingWizard.tsx` | XS |
| 4 | 🟡 | Admin stats'a `total_view_count` ekle | `backend/app/api/v1/admin.py` | XS |
| 5 | 🟡 | Backend Sentry entegrasyonu | `backend/app/main.py` | S |
| 6 | 🟡 | Backend structlog JSON loglama | backend middleware | M |
| 7 | 🟡 | `/admin` Next.js sayfası (stats görselleştirme) | `frontend/src/app/admin/page.tsx` | M |
| 8 | 🟢 | Pricing page waitlist form conversion tracking | `app/pricing/page.tsx` | S |

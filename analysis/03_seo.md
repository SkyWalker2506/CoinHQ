# SEO Analysis — CoinHQ
_Date: 2026-04-10 · Lead: GrowthLead (A11) · Model: Sonnet 4.6_

## Delta vs 2026-04-06

| Item | April 6 | April 10 | Status |
|------|---------|----------|--------|
| `robots.txt` | Yoktu | `public/robots.txt` eklendi | ✅ |
| `sitemap.ts` | Yoktu | `app/sitemap.ts` eklendi | ⚠️ Partial |
| OG tags in `layout.tsx` | Yoktu | `og:title`, `og:description`, `og:type` eklendi | ✅ |
| Twitter Card | Yoktu | `summary` card eklendi | ✅ |
| `generateMetadata()` share sayfasında | Yoktu | Profil adıyla dinamik metadata | ✅ |
| Canonical URL | Yoktu | Hâlâ yok | 🔴 |
| `og:image` share sayfasında | Yoktu | Hâlâ yok | 🔴 |
| Landing page `/` | Yoktu | Hâlâ redirect → `/dashboard` | 🔴 |
| `sitemap.ts` domain placeholder | — | `yourdomain.com` değiştirilmemiş | 🔴 |
| Favicon | Yoktu | `favicon.ico` eklendi | ✅ |

**Score: 2/10 → 5/10**

## Current State

`frontend/src/app/layout.tsx:9–25` — Global metadata artık `og:title`, `og:description`, `og:type: "website"`, `twitter:card: "summary"` içeriyor.

`frontend/src/app/share/[token]/page.tsx:7–27` — `generateMetadata()` implement edilmiş, `profile_name` ile dinamik title/description üretiyor, `og:title`/`og:description` ekliyor. Fallback da var.

`frontend/public/robots.txt` — `/share/` allow, `/dashboard` `/settings` `/api/` disallow. Doğru yapılandırılmış.

`frontend/src/app/sitemap.ts` — Mevcut fakat içeriği eksik (sadece root, `yourdomain.com` placeholder).

## Findings

### 🔴 Critical

**F1 — `sitemap.ts:6` → `yourdomain.com` placeholder**
`robots.txt` bu sitemap URL'ini gösteriyor. Gerçek deploy'da search engine yanlış domain'e yönleniyor. Fix: `process.env.NEXT_PUBLIC_APP_URL` kullan.

**F2 — Share sayfasında canonical URL yok**
`app/share/[token]/page.tsx:14` — `generateMetadata()` içinde `alternates: { canonical }` eksik. Birden fazla token aynı portföyü paylaşırsa duplicate content riski.

**F3 — `og:image` / `twitter:image` yok**
`app/share/[token]/page.tsx:17–20` — OpenGraph bloğunda resim yok. Twitter/Discord/Telegram'da önizleme boş gelecek → CTR düşük. En hızlı fix: `/public/og-default.png` (1200×630) + `layout.tsx`'e ekle.

**F4 — `/` root hâlâ `/dashboard`'a redirect**
`app/page.tsx:3` — Giriş yapmamış kullanıcı ve Google botu redirect alıyor. Hiç crawlable landing page yok. Pricing page (`/pricing`) var ama `/` → `/pricing`/`/login` gibi bir yönlendirme bile yok.

### 🟡 Medium

**F5 — `/pricing` ve `/login` sitemap'te yok** — `app/sitemap.ts` sadece root içeriyor.

**F6 — `og:url` eksik** — Share page OG bloğunda `url` field'ı yok, sosyal share attribution yanlış olabilir.

**F7 — `twitter:card: "summary"` değil `"summary_large_image"` olmalı** — `layout.tsx:19`. Resim eklenince bunu da değiştir.

### 🟢 Good

**F8** — Share page'de `next: { revalidate: 60 }` doğru; hem `generateMetadata` hem `fetchShare` için uygulanmış (`page.tsx:11,31`).

## Action Items

| # | P | Fix | File | Effort |
|---|---|-----|------|--------|
| 1 | 🔴 | `yourdomain.com` → `NEXT_PUBLIC_APP_URL` | `app/sitemap.ts:6` | XS |
| 2 | 🔴 | `/pricing`, `/login` sitemap'e ekle | `app/sitemap.ts` | XS |
| 3 | 🔴 | Share page canonical URL | `app/share/[token]/page.tsx` | XS |
| 4 | 🔴 | Static `og:image` fallback (1200×630) | `public/og-default.png` + `layout.tsx` | S |
| 5 | 🔴 | `og:url` share page OG bloğuna ekle | `app/share/[token]/page.tsx:17` | XS |
| 6 | 🟡 | Twitter card → `summary_large_image` | `app/layout.tsx:19` | XS |
| 7 | 🟡 | Landing page at `/` | `app/page.tsx` | M |
| 8 | 🟢 | JSON-LD `SoftwareApplication` schema | pricing/landing page | S |

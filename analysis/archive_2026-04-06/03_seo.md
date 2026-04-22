## #3 SEO & Discoverability Analiz Raporu
> Lead: GrowthLead (A11) | Model: Sonnet 4.6

---

### Bağlam Notu

CoinHQ self-hosted, OAuth-gated bir uygulamadır. Dashboard, settings ve profil sayfaları giriş gerektirdiğinden geleneksel SEO kapsamının dışındadır. Bununla birlikte, iki alan SEO'dan doğrudan etkilenir:

1. **Share sayfası** (`/share/[token]`) — auth gerektirmez, herkese açık
2. **Login/landing sayfası** — indexlenebilir, marka bilinirliği oluşturabilir

---

### Mevcut Durum

**Yapılmış olanlar:**
- `layout.tsx` içinde temel `<title>` ve `description` metadata tanımlanmış
- Share sayfası (`/share/[token]`) public ve server-side rendered (SSR) — bu SEO açısından sağlam bir temel
- Share sayfasına "CoinHQ" marka etiketi eklenmiş (footer ve header)
- `lang="en"` attribute `<html>` etiketinde mevcut

**Puan: 2/10**

Temel metadata var ancak Open Graph, Twitter Card, robots.txt, sitemap.xml, canonical URL, yapısal veri (JSON-LD) gibi tüm SEO standartları eksik.

---

### Kritik Eksikler (hemen yapılmalı)

| # | Sorun | Etki | Çözüm | Efor |
|---|-------|------|-------|------|
| 1 | `robots.txt` yok | High | `public/robots.txt` oluştur; `/share/*` crawl'a izin ver, `/dashboard`, `/settings`, `/api/*` disallow et | S |
| 2 | Open Graph metadata yok | High | `layout.tsx` ve `share/[token]/page.tsx`'e `og:title`, `og:description`, `og:image`, `og:url` ekle | S |
| 3 | `sitemap.xml` yok | Med | Next.js `app/sitemap.ts` ile otomatik oluştur; `/share/*` hariç statik sayfaları dahil et | S |
| 4 | Share sayfasında dinamik metadata yok | High | Share page'e `generateMetadata()` ekle — token verisine göre dinamik `og:title` (ör. "Portfolio — CoinHQ") | M |
| 5 | Twitter Card meta etiketleri yok | Med | `twitter:card`, `twitter:title`, `twitter:description` ekle | S |

---

### İyileştirme Önerileri (planlı)

| # | Öneri | Etki | Çözüm | Efor |
|---|-------|------|-------|------|
| 1 | Share sayfasına canonical URL ekle | Med | Her token için `<link rel="canonical">` — duplicate content riskini engeller | S |
| 2 | JSON-LD yapısal veri (WebSite schema) | Low | Ana layout'a `WebSite` schema ekle — Google Knowledge Panel için zemin hazırlar | S |
| 3 | `viewport` meta etiketini açıkça tanımla | Low | Next.js metadata API ile `viewport` export et — mobile-first index için | S |
| 4 | Favicon ve maskable icon ekle | Med | `public/favicon.ico`, `public/apple-touch-icon.png` — PWA ve bookmark görünümü | M |
| 5 | Landing / marketing sayfası oluştur | High | OAuth ile korunan app'ın önüne SEO-friendly bir tanıtım sayfası koy (`/`) | L |

---

### Kesin Olmalı (industry standard)
- `robots.txt` — tüm self-hosted uygulamalarda zorunlu
- Open Graph meta etiketleri — sosyal paylaşım önizlemesi
- `sitemap.xml` — crawler discovery
- `lang` attribute — mevcut, devam etmeli

### Kesin Değişmeli (mevcut sorunlar)
- `page.tsx` (root) doğrudan `/dashboard`'a yönlendiriyor — crawlanabilir landing sayfası yok
- Share sayfasında `generateMetadata()` eksik — her share linki aynı title/description gösteriyor
- `public/` klasörü hiç yok — statik asset servisi yapılamıyor

### Nice-to-Have (diferansiasyon)
- Share linki paylaşılınca Twitter/LinkedIn önizlemesi için OG image (dinamik, `og:image` ile)
- `hreflang` — ileride çok dil desteği gelirse
- Structured data: `SoftwareApplication` schema için Google Play / app store alternatifi

---

> **Not:** Bu proje MVP aşamasında. SEO yatırımının en yüksek ROI'u share sayfasından gelir — çünkü share linkleri dışarıya paylaşılıyor ve organik backlink/trafik üretebilir.

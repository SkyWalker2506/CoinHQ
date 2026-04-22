# Monetization Analysis — CoinHQ
_Date: 2026-04-10 · Lead: BizLead (A12) · Model: Sonnet 4.6_

## Delta vs 2026-04-06

Nisan 6 arşivi monetizasyonu **2/10** olarak değerlendirdi: "tier sistemi, ödeme entegrasyonu, fiyatlandırma sayfası — hiçbiri yok." Bu değerlendirme artık geçersiz.

**COIN-5 ile gelenler:**
- `UserTier` enum eklendi: `free | premium | admin` (`backend/app/models/user.py:10`)
- Tier limitleri: Free = 1 profil, 2 exchange; Premium = unlimited (`backend/app/core/limits.py:5–13`)
- `POST /api/v1/profiles` 403 gate: _"Free tier limit: 1 profile. Upgrade to Premium..."_ (`backend/app/api/v1/profiles.py:37–39`)
- `UpgradeBanner` bileşeni 403'te render olur, `/pricing`'e link verir (`frontend/src/components/UpgradeBanner.tsx`)
- `/pricing` sayfası: 3 plan — Self-Hosted / Cloud Free / Cloud Premium $9/mo (`frontend/src/app/pricing/page.tsx`)
- Admin `/stats` endpoint'i artık `tiers` dağılımı döndürüyor (`backend/app/api/v1/admin.py:38–48`)

**Hâlâ değişmeyen:** Ödeme entegrasyonu yok, subscription yönetimi yok, webhook yok, trial mantığı yok, self-service tier yükseltme yok.

**Güncel puan: 4/10** — iskelet sağlam, gelir toplama hâlâ eksik.

## Current State

### Tier Yapısı

| Tier | Profil | Exchange/profil | Ödeme |
|------|--------|-----------------|-------|
| free | 1 | 2 | — |
| premium | sınırsız | sınırsız | Implement edilmemiş |
| admin | sınırsız | sınırsız | N/A |

`tier` kolonu `String(50)`, default `"free"` (migration `005_add_user_tier.py`). Ödeme tablosu, `subscription_id`, `plan_expires_at` yok. Premium'a geçiş yalnızca manuel DB yazımıyla mümkün.

### Pricing Page

`/pricing` statik JSX; backend bağlantısı yok. "Join waitlist" butonu `#waitlist` anchor'ına bağlı — bu anchor sayfada mevcut değil. $9/mo fiyatı belirlenmiş ama tahsil edilemiyor.

### Upgrade Prompt Flow

`AddProfileModal` 403 yakalarsa `onTierLimit?.(msg)` → Settings'te `UpgradeBanner` render. Exchange key eklemede eşdeğer frontend gate yok (`AddKeyModal`'da `onTierLimit` prop'u tanımsız).

## Findings

### 🔴 Kritik — Gelir Engelleyiciler

**F1 — Ödeme entegrasyonu sıfır.** "Join waitlist" ölü anchor. Email capture yok, Stripe/Paddle yok. Dönüşüm tamamen sıfır.

**F2 — Tier yükseltme yalnızca admin DB yazımıyla.** `User` modelinde `stripe_customer_id`, `subscription_id`, `plan_expires_at` kolonu yok. Self-service imkânsız.

**F3 — Exchange limit gate frontend'de görünmez.** `check_exchange_limit` backend'de var ama `AddKeyModal` kullanıcıya ham API hatası gösterir, upgrade banner'ı göstermez.

### 🟡 Önemli — Değer Merdiveni Sorunları

**F4 — Fiyat sayfası kopyası gerçekle çelişiyor.** "All 5 exchanges" yazıyor ama asıl kısıtlama exchange sayısı değil, profil/anahtar sayısı. Free kullanıcı da tüm exchange'lere erişebilir.

**F5 — Yıllık plan yok.** $9/mo Türkiye'de ~290 TRY — ağır. $79/yr (%12 indirim) + TR yerel fiyatı ($4–5/mo) conversion'ı artırır.

**F6 — Trial yok.** Soğuk upgrade talebi: kullanıcı ilk meaningful aksiyonunda (ikinci profil oluşturma) wall'a çarpıyor.

**F7 — "Join waitlist" momentumu öldürüyor.** Kullanıcı gate'e çarptı → banner'a tıkladı → pricing sayfasında tıklanamaz buton. Conversion graveyard.

### 🟡 Mimari Eksikler

- Subscription lifecycle yok (churn, dunning, cancellation)
- Admin stats'ta gelir metrikleri yok (MRR, ARPU, trial-to-paid %)
- Webhook endpoint yok (ödeme işlemcileri için zorunlu)

### 🟢 Güçlü Yanlar

- Gate placement doğru: profil oluşturma en iyi fırsat noktası
- $9/mo fiyat savunulabilir (CoinStats $9.9/mo'nun altında)
- Free vs Premium iki kademeli yapı: bilişsel yük düşük
- Admin stats'ta tier dağılımı: analitik temeli var

## Action Items

| Öncelik | İş | Efor |
|---------|-----|------|
| P0 | Stripe Checkout entegre et ($9/mo Cloud Premium) + webhook endpoint | L |
| P0 | "Join waitlist" → canlı Stripe link veya email capture | S |
| P0 | `AddKeyModal`'a `onTierLimit` + `UpgradeBanner` ekle | S |
| P1 | Pricing sayfası kopyasını düzelt ("All 5 exchanges" yanlış) | XS |
| P1 | $79/yr yıllık plan ekle | S |
| P1 | 14 günlük trial: `trial_ends_at` kolonu + frontend sayaç banner | M |
| P1 | TR PPP fiyatı: ~150–180 TRY/mo veya $4–5/mo | S |
| P2 | Admin stats'a MRR, ARPU, trial-to-paid % ekle | M |
| P2 | Nav/Settings'te "Premium" badge | S |

## TAM/SAM

- **Global:** 25–50M aktif tracker kullanıcısı, %5 ödeme eğilimi → $135–270M ARR SAM
- **Türkiye:** 800K–1.6M aktif, PPP'de %3 → $1.2–2.3M ARR (yerel fiyatlama ile)
- **CoinHQ 12 ay hedefi:** 500–2,000 paying user = $54K–$216K ARR

# Growth & Engagement Analysis — CoinHQ
_Date: 2026-04-10 · Lead: GrowthLead (A11) · Model: Sonnet 4.6_

## Delta vs 2026-04-06

| Item | April 6 | April 10 | Status |
|------|---------|----------|--------|
| Onboarding wizard | Yoktu | `OnboardingWizard.tsx` implement edilmiş | ✅ |
| Share page CTA "Start with CoinHQ" | Yoktu | Footer'da CTA + "Powered by CoinHQ" var | ✅ |
| Share link view_count | Yoktu | Backend + frontend gösterimi var | ✅ |
| Empty state | Yoktu | `EmptyState.tsx` component mevcut | ✅ |
| Tier upgrade prompt | Yoktu | `UpgradeBanner.tsx` + settings page entegrasyon | ✅ |
| Social share buttons after copy | Yoktu | Hâlâ yok | 🔴 |
| Onboarding completion tracking | — | Yok (localStorage flag, event yok) | 🟡 |
| Referral / invite mechanism | Yoktu | Hâlâ yok | 🟡 |
| Email retention | Yoktu | Hâlâ yok | 🟡 |

**Score: 3/10 → 6/10**

## Current State

**Onboarding:** `frontend/src/components/OnboardingWizard.tsx` — 3 adımlı modal wizard implement edilmiş (profil → exchange → share). `localStorage['onboarding_done']` ile tekrar gösterilmiyor. "Skip setup" butonu mevcut.

**Share page viral CTA:** `frontend/src/app/share/[token]/page.tsx:164–170` — Footer'da "Track your own crypto portfolio" + mavi "Start with CoinHQ — Free" butonu + "Powered by CoinHQ" var. Bu April 6'daki en kritik eksikti, çözülmüş.

**Upgrade prompt:** `frontend/src/components/UpgradeBanner.tsx` — 403 tier-limit hatası gelince settings sayfasında (`settings/page.tsx:88–90`) gösterilen amber renkli banner. `/pricing`'e link veriyor.

**View count gösterimi:** `frontend/src/components/ShareLinkManager.tsx:162–166` — `{link.view_count} views` ve `Last: {date}` gösteriliyor. Kullanıcı danışmanının linki kaç kez açtığını görüyor.

## Findings

### 🔴 Critical

**F1 — Onboarding wizard'da completion/skip analytics yok**
`OnboardingWizard.tsx:13–16` — `handleComplete()` sadece `localStorage.setItem` yapıyor; `events.profileCreated()` veya benzeri event yok. Kaç kullanıcının onboarding'i tamamladığı vs skip ettiği bilinmiyor. Activation rate ölçülemez. Fix: `trackEvent('Onboarding Completed', { step: step + 1 })` ve `trackEvent('Onboarding Skipped', { step })` ekle.

**F2 — Share link kopyalandıktan sonra social share butonu yok**
`ShareLinkManager.tsx:59–76` — Kopyalama sonrası sadece "Copied!" feedback'i var; Twitter/Telegram/WhatsApp paylaşım seçeneği yok. Share link viral loop'un en kritik noktası bu. Fix: kopyalama sonrası küçük bir modal veya inline buton grubu: "Share on Twitter", "Copy link".

**F3 — Upgrade prompt sadece settings sayfasında, tek temas noktası**
`frontend/src/app/settings/page.tsx:88–90` — `UpgradeBanner` sadece 403 hatası gelince settings sayfasında gösteriliyor. Dashboard'da (limit yaklaşırken), onboarding sonu (kullanıcı motivasyonu yüksekken), share link oluşturma ekranında (premium özellik açıkken) hiç gösterilmiyor. Conversion surface çok dar.

### 🟡 Medium

**F4 — Pricing page'de waitlist formu çalışmıyor**
`frontend/src/app/pricing/page.tsx:10` — Premium plan CTA'sı `href="#waitlist"` gösteriyor ama `id="waitlist"` olan bir element yok. Kullanıcı tıklayınca hiçbir şey olmuyor. Lead capture fırsatı kaçıyor.

**F5 — Share link oluşturma sonrası modal UX'i zayıf**
`CreateShareLinkModal.tsx` — Modal kapatılınca link kayboluyor. "Share on Twitter/Telegram" gibi one-click paylaşım seçenekleri yok. Link oluşturulduktan hemen sonra kullanıcı motivasyonu en yüksek noktada — bu momentum kullanılmıyor.

**F6 — `FollowButton` component'i — feature tamamlanmamış**
`share/[token]/page.tsx:79` — `data.allow_follow && <FollowButton />` var, `FollowButton.tsx` mevcut. Ama "follow" ne anlama geliyor, kullanıcıya bildirim geliyor mu? UX tamamlanmamış görünüyor.

**F7 — Onboarding wizard triggerlama koşulu belirsiz**
`OnboardingWizard.tsx` — Wizard'ın ne zaman tetiklendiği bu dosyada değil; parent component'te (`dashboard/page.tsx` gibi). `localStorage` check ile ilk giriş tespiti MVP için yeterli ama server-side onboarding state daha güvenilir.

### 🟢 Good

**F8 — Share page viral footer doğru konumlandırılmış**
`share/[token]/page.tsx:164–170` — Footer'daki CTA, görünürlük hiyerarşisi açısından doğru yerde (portfolio görüldükten sonra). Mavi buton rengi dikkat çekici.

**F9 — View count kullanıcıya değer hissettiriyor**
`ShareLinkManager.tsx:162` — "5 views · Last: Apr 8" gibi bilgi, kullanıcının ürüne geri dönmesini teşvik ediyor. Retention hook olarak iyi çalışır.

## Action Items

| # | P | Fix | File | Effort |
|---|---|-----|------|--------|
| 1 | 🔴 | Onboarding analytics ekle (complete/skip events) | `OnboardingWizard.tsx:13,29` | XS |
| 2 | 🔴 | Share sonrası social share butonları | `ShareLinkManager.tsx` | S |
| 3 | 🔴 | Upgrade prompt → dashboard + share creation | `dashboard/page.tsx`, `CreateShareLinkModal.tsx` | S |
| 4 | 🟡 | Pricing page waitlist form implement et | `pricing/page.tsx` | M |
| 5 | 🟡 | Share link modal'a Twitter/Telegram paylaşım ekle | `CreateShareLinkModal.tsx` | S |
| 6 | 🟡 | Upgrade event tracking (impression + click) | `UpgradeBanner.tsx` | XS |
| 7 | 🟢 | `FollowButton` feature'ı tamamla veya gizle | `FollowButton.tsx` | M |
| 8 | 🟢 | Onboarding server-side state (DB flag) | backend + dashboard | M |

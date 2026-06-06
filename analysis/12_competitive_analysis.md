# Competitive Analysis — CoinHQ
_Date: 2026-04-10 · Lead: BizLead (A12) · Model: Sonnet 4.6_

## Delta vs 2026-04-06

Nisan 6 rekabet analizi CoinHQ'yu **4/10** olarak değerlendirdi. Temel bulgular geçerliliğini koruyor. Değişen tek şey: tier sistemi artık Cloud Free vs Cloud Premium olarak netleşti. Bu, CoinHQ'nun "self-hosted free + cloud paid" konumlandırmasını Ghostfolio'nun modeliyle örtüştürüyor.

**Güncel puan: 4/10** — konumlandırma potansiyeli güçlü, özellik seti rakiplerin gerisinde.

## Current State

**Desteklenen exchange'ler:** Binance, Bybit, OKX (3 adet). Rakipler 100–700+ destekliyor.

**Mevcut farklılaştırıcılar:**
1. Granüler share link (show_* flag'leri, view tracking COIN-3 ile)
2. Read-only enforced + AES-256 şifreleme
3. Multi-profil + aggregate görünüm
4. Self-hosted seçeneği
5. Tier sistemi (COIN-5: yeni, henüz pazarlanmıyor)

## Findings

### 🔴 Kritik — Rekabetçilik Engelleri

**F1 — 3 exchange yetersiz — Coinbase ve Kraken eksik.** Coinbase tek başına ABD kripto kullanıcılarının ~%30'unu kapsar. Bu iki exchange olmadan ABD pazarına giriş fiilen kapalı. Kraken ise Avrupa'da dominant. Güncel kayıp: gelen potansiyel kullanıcıların %30–40'ı ürünü kullanamaz.

**F2 — Mobil yokluğu 2026'da artık kritik.** CoinStats ve Delta mobil-first. CoinHQ yalnızca web. Mobil crypto kullanımı masaüstünü geçeli 3+ yıl oldu. PWA en hızlı çözüm.

**F3 — rotki doğrudan rakip ve daha olgun.** Self-hosted + CEX + gizlilik kombinasyonunda rotki daha derin özellik setine sahip (vergi raporu, on-chain). CoinHQ'nun avantajları: share link, web-first UX, delegated access roadmap'i. Bu 3 özellik pazarlama mesajında öne çıkarılmalı.

### 🟡 Önemli — Konumlandırma Sorunları

**F4 — Diferansiasyon mesajı README'de yok.** README "multi-user crypto portfolio tracker" diyor. Rakiplerin %95'i de bu tanıma giriyor. "Privacy-first + shareable + delegated access" mesajı hiçbir yerde net biçimde ifade edilmiyor.

**F5 — Tier sistemi yeni fırsat ama pazarlanmıyor.** Cloud Free/Premium ayrımı yapılmış ama pricing page link neredeyse hiçbir yerde yok; kullanıcılar ürünü self-hosted ücretsiz sandığı için yanlış beklentiyle geliyor.

**F6 — Vergi raporlaması eksikliği ciddi kitle dışı bırakıyor.** Koinly ve Blockpit bu segmenti domine ediyor. Basit CSV export bile kullanıcı tabanını genişletir.

### 🟢 Güçlü Yanlar

**F7 — Share link granülaritesi rakipsiz.** Muhasebeci/danışman use-case için `show_*` flag'leri + view tracking (COIN-3) kombinasyonu hiçbir doğrudan rakipte yok. Ghostfolio'nun partial share özelliği çok daha kısıtlı.

**F8 — Privacy-first + cloud hybrid nadir.** rotki self-hosted only; CoinStats cloud-only. CoinHQ her ikisini sunuyor — bu Ghostfolio modeliyle örtüşüyor ama kripto odaklı.

**F9 — COIN-5 tier sistemi yatırımcı/B2B anlatısı için zemin.** "Admin görür kaç kullanıcı premium" metriği toplanıyor. Data-driven monetizasyon için başlangıç noktası.

## Feature Matrix

| Özellik | CoinHQ | rotki | Ghostfolio | CoinStats | Delta | Koinly |
|---------|--------|-------|------------|-----------|-------|--------|
| Self-hosted | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Cloud SaaS | ✅ ($9/mo) | Kısmi | ✅ ($19/mo) | ✅ | ✅ | ✅ |
| CEX desteği | 3 | Çok | Sınırlı | 300+ | 200+ | 700+ |
| Granüler share link | ✅ | ❌ | Kısmi | ❌ | ❌ | ❌ |
| View tracking | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| DeFi/on-chain | ❌ | ✅ | ❌ | ✅ | ❌ | Kısmi |
| Delegated trading | Phase 2 | ❌ | ❌ | ❌ | ❌ | ❌ |
| Vergi raporu | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ |
| Mobil app | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| AI insight | Phase 4 | ❌ | ❌ | Kısmi | ❌ | ❌ |
| Açık kaynak | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Fiyat (paid) | $9/mo | Ücretsiz | $19/mo | $3.49/mo | $59.99/yr | $49/yr+ |

## Pricing Benchmark

| Ürün | Ücretsiz Katman | Ücretli Başlangıç | Yıllık |
|------|-----------------|-------------------|--------|
| CoinHQ Cloud | 1 profil, 2 exchange | $9/mo | — (yok) |
| Ghostfolio | Sınırlı | $19/mo | $190/yr |
| CoinStats | Temel | $3.49/mo | ~$35/yr |
| Delta | Temel | — | $59.99/yr |
| Koinly | 25 işlem | $49/yr | $49/yr |
| rotki | Sınırsız (self) | — | — |

**Sonuç:** CoinHQ $9/mo ile orta bant. CoinStats'ın altında ($3.49) ama Ghostfolio'nun ($19) altında. Self-hosted free option = güçlü freemium kanca. Annual plan eksikliği fiyat algısını dezavantajlı kılıyor.

## Türkiye Pazarı Fırsatları

- Türkiye global kripto sahipliği oranında top 10 ülke (~%20+ nüfus etkileşimi)
- Yerel rakip yok: Türkçe arayüzlü, TR borsalarını (ICRYPEX, BtcTurk, Paribu) destekleyen portfolio tracker mevcut değil
- **CoinHQ için hızlı kazanç:** TR lokalizasyonu (Türkçe UI) + BtcTurk/Paribu adapter = Türkiye'de rakipsiz niche
- Regülasyon: MASAK uyumlu kripto raporlama giderek zorunlu → vergi raporu özelliği TR'de muhasebeci B2B pazarı açar
- PPP fiyatlandırma şart: $9/mo → ~290 TRY; ~150 TRY/mo TR fiyatı çok daha uygun

## Moat Değerlendirmesi

| Moat Kaynağı | Güç | Neden |
|--------------|-----|-------|
| Share link virality | Orta | Görüntüleyiciler CoinHQ markasını görüyor ama kayıt yok → viral loop zayıf |
| Privacy / read-only | Güçlü | Kurumsal güven için kritik; rotki dışında rakipler bunu vurgulamıyor |
| Open source | Orta | Topluluk büyütür ama fork riski var (Ghostfolio'dan öğren) |
| Delegated trading (Phase 2) | Potansiyel güçlü | Hiçbir rakipte yok; fon yöneticisi nişi için gerçek moat |
| TR lokalizasyonu | Potansiyel güçlü | Erken girişimci avantajı; yapılırsa 1–2 yıl rakipsiz |

## Action Items

| Öncelik | İş | Etki | Efor |
|---------|-----|------|------|
| P0 | Coinbase + Kraken adapter ekle | Yüksek | M per exchange |
| P0 | README + landing page'de diferansiasyon mesajı netleştir | Yüksek | S |
| P1 | rotki karşılaştırma sayfası | Yüksek | S |
| P1 | PWA manifest + service worker | Orta | S |
| P1 | TR lokalizasyonu: Türkçe UI + BtcTurk/Paribu adapter | Yüksek | M |
| P1 | Share link viral loop güçlendir: "Create your own" CTA | Orta | S |
| P2 | CSV export (vergi raporu başlangıcı) | Orta | M |
| P2 | On-chain wallet tracking (public address) | Orta | L |
| P3 | MASAK-uyumlu vergi raporu format | Orta | L |

## References

- `README.md` — mevcut ürün konumlandırması
- `frontend/src/app/pricing/page.tsx` — 3-plan pricing UI
- `backend/app/core/limits.py` — tier gate definitions
- `backend/app/models/user.py` — `UserTier` enum
- `analysis/archive_2026-04-06/12_competitive_analysis.md` — önceki rekabet matrisi

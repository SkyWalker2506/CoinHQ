# Monetization & Business Model Analiz Raporu

> Lead: BizLead (A12) | Tarih: 2026-04-05

---

## Mevcut Durum

### Ne Yapılmış (Güçlü Yanlar)

- **Self-hosted model:** Gizlilik odaklı kullanıcılara güçlü bir değer önerisi — "senin sunucunda, senin verinde"
- **Granüler paylaşım linkleri:** Danışman/muhasebeci use-case'i monetize edilebilir B2B katmana zemin hazırlıyor
- **Delegated trading (Phase 2):** Fon yöneticisi → müşteri ilişkisini kapsayan nadir bir özellik; rakiplerin büyük çoğunluğunda yok
- **Read-only API güvenliği:** Kurumsal güven inşası için kritik temel mevcut
- **Roadmap'te AI (Phase 4) ve Premium (Phase 5):** Üst katmanlar planlanmış ama gelir modeli tanımsız

### Eksik / Sorunlar

Şu anda **hiçbir gelir modeli** mevcut değil. Premium/tier sistemi, ödeme entegrasyonu, fiyatlandırma sayfası — bunların hiçbirinin izine backend veya frontend'de rastlanmıyor. Proje MVP aşamasında; monetizasyon mimarisi daha çizilmemiş.

**Puan: 2/10** — Altyapı sağlam ama gelir modeli sıfır.

---

## Kritik Eksikler (hemen yapılmalı)

| # | Sorun | Etki | Çözüm | Efor |
|---|-------|------|-------|------|
| 1 | Hiçbir fiyatlandırma modeli yok — "nasıl para kazanılacak" belirsiz | High | Tier stratejisi belirle (self-hosted free + cloud SaaS paid) | S |
| 2 | Self-hosted dağıtım tamamen ücretsiz; değer yakalanamıyor | High | Cloud-hosted "CoinHQ Cloud" seçeneği planla — aylık $9-15 | M |
| 3 | Phase 2 Delegated Trading'in gelir modeliyle ilişkisi kurulmamış | High | Bu özelliği B2B (fon yöneticisi) segmentinin premium katmanına bağla | S |
| 4 | Fiyatlandırma sayfası / landing page yok — kullanıcıyı ikna edecek materyal yok | Med | Basit bir pricing.md veya landing page tasarımı başlat | M |

---

## İyileştirme Önerileri (planlı)

| # | Öneri | Etki | Çözüm | Efor |
|---|-------|------|-------|------|
| 1 | **Freemium + Cloud SaaS katmanı:** Self-hosted daima ücretsiz; Cloud hosted $9/ay (3 profil) / $19/ay (sınırsız profil) | High | Ayrı bir SaaS sunucu ayağı + Stripe entegrasyonu | L |
| 2 | **B2B tier — "CoinHQ Pro":** Delegated trading, fon yöneticisi whitelist, audit log → $49-99/ay | High | Phase 2 tamamlanınca API üstüne billing katmanı | M |
| 3 | **API erişimi (Geliştirici tier):** Kendi portföy verisine REST API key ile erişim → $19/ay ek modül | Med | Mevcut backend üstüne API key tablosu + rate limit tier'ı | M |
| 4 | **Muhasebe/vergi raporu ek modülü:** Koinly modeli — $49/yıl işlem raporu export | Med | Phase 3 PnL tamamlanınca CSV/PDF export + paywall | M |
| 5 | **"Bring Your Own Server" + Premium Support:** Self-host kullanıcısına yıllık $99 destek planı | Low | Destek sistemi (e-posta/Discord) + SLA belgesi | S |

---

## Kesin Olmalı (Industry Standard)

- **Freemium giriş noktası:** Piyasadaki tüm rakipler (CoinStats, Delta, Koinly) ücretsiz katman sunuyor; CoinHQ'nun self-hosted açık kaynak versiyonu bu rolü üstlenebilir
- **Yıllık ödeme indirimi:** Aylık fiyatın %20-30 altında yıllık plan (Delta: $59.99/yıl modeli)
- **Kredi kartı gerektirmeyen deneme:** SaaS versiyonu için 14 günlük ücretsiz deneme
- **Şeffaf fiyatlandırma sayfası:** Feature matrix ile — rakiplerin tamamında var

## Kesin Değişmeli (Mevcut Sorunlar)

- **"Nasıl sürdürülebilir?" sorusu yanıtsız:** README ve docs'ta hiçbir gelir hedefi yok — bu, yatırımcı veya kullanıcı güveni için sorun
- **Self-hosted = sadece teknik kullanıcılar:** Geniş kitlelere ulaşmak için cloud seçeneği şart; bu olmadan büyüme tavanı düşük kalır
- **Phase 5 "Premium" çok geç planlanmış:** Gelir modeli Phase 1'den itibaren mimariyle birlikte düşünülmeli

## Nice-to-Have (Diferansiasyon)

- **Affiliate geliri:** Kullanıcılar CoinHQ üzerinden exchange'e kaydolunca referral komisyonu (Binance affiliate programı: %20-40)
- **"CoinHQ for Teams":** Şirket içi kripto yönetim dashboardu — CFO + trader + muhasebeci aynı workspace
- **White-label lisans:** Fon yönetim şirketlerine CoinHQ altyapısını lisanslama ($500-2000/ay)
- **Marketplace:** Özel alert template, strateji şablonları, AI model eklentileri (Phase 4 sonrası)

---

## Gelir Modeli Önerisi (Kısa Vade)

```
Tier 1 — Open Source (Ücretsiz)
  Self-host, sınırsız profil, temel özellikler
  → Topluluk büyütme, marka bilinirliği

Tier 2 — CoinHQ Cloud Personal ($9/ay | $79/yıl)
  Barındırma dahil, 5 profil, paylaşım linkleri
  → Teknik olmayan kullanıcılar

Tier 3 — CoinHQ Cloud Pro ($29/ay | $249/yıl)
  Sınırsız profil, delegated trading, vergi raporu, API erişimi
  → Aktif trader, danışman

Tier 4 — CoinHQ Business (custom fiyat)
  Çok kullanıcılı workspace, audit log, white-label
  → Fon yöneticisi, kripto şirketleri
```

# Competitive Analysis Analiz Raporu

> Lead: BizLead (A12) | Tarih: 2026-04-05

---

## Mevcut Durum

### Rakip Haritası

| Rakip | Odak | Fiyat | Güçlü Yan | Zayıf Yan |
|-------|------|-------|-----------|-----------|
| **CoinStats** | CEX + DeFi tracker | Ücretsiz / ~$3.49-9.9/ay | 120 blockchain, 300+ entegrasyon, sosyal özellikler | Karmaşık UI, veri mahremiyeti yok |
| **Delta (eToro)** | Multi-asset (kripto + hisse) | Ücretsiz / $59.99/yıl | Hisse + kripto birlikte, temiz UI | API key delegasyonu yok, sınırlı DeFi |
| **Koinly** | Vergi + portföy | Ücretsiz / $49-280/yıl | Vergi raporlama, 700+ entegrasyon | Vergi odaklı, trading özelliği yok |
| **Blockpit/Accointing** | Vergi (Avrupa) | $4.99/ay+ | AB uyumu | 50k+ işlemde sorun, pahalı |
| **Zapper** | DeFi on-chain | Ücretsiz | Wallet-based, DEX tracking, "zap" | Sadece on-chain, CEX desteği zayıf |
| **DeBank** | DeFi analytics | Ücretsiz + ücretli mesaj | 56+ blockchain, sosyal özellikler | Ticari model belirsiz, CEX yok |
| **rotki** | Self-hosted gizlilik | Açık kaynak ücretsiz | Tam gizlilik, lokal şifreleme | Teknik kurulum, mobil yok |
| **Ghostfolio** | Self-hosted çoklu varlık | Açık kaynak / $19/ay cloud | Hisse + kripto, gizlilik | Kripto derinliği sınırlı |
| **Cryptofolio** | Self-hosted basit | Açık kaynak | Hafif, kolay kurulum | Sınırlı özellik, bakımsız |

### CoinHQ'nun Mevcut Konumu

CoinHQ Phase 1 itibarıyla **self-hosted + CEX odaklı + güvenlik öncelikli** bir nişte konumlanıyor. Bu kombinasyon rakiplerin çoğunda tam olarak karşılanmıyor.

**Güçlü Yanlar (şu an):**
- Granüler paylaşım linkleri (muhasebeci/danışman use-case)
- Read-only API zorunluluğu + AES-256 şifreleme
- Multi-profil + aggregate görünüm
- Self-hosted seçeneği (tam veri kontrolü)

**Zayıf Yanlar (şu an):**
- Yalnızca 3 exchange (Binance, Bybit, OKX) — rakipler 300-700+ destekliyor
- Mobil uygulama yok
- On-chain / DeFi desteği yok
- Vergi raporlaması yok
- Yalnızca MVP — AI, PnL, alert henüz yok

**Puan: 4/10** — Diferansiasyon vaadi güçlü ama mevcut özellik seti rakiplerin gerisinde.

---

## Kritik Eksikler (hemen yapılmalı)

| # | Sorun | Etki | Çözüm | Efor |
|---|-------|------|-------|------|
| 1 | Sadece 3 exchange — Coinbase, Kraken, KuCoin en sık istenen; kullanıcı kaybı yaratır | High | Phase 2'ye Coinbase + Kraken adaptörü ekle | M |
| 2 | Diferansiasyon mesajı net değil — rakiplerden ne farkı var, neden tercih edilmeli? | High | "Privacy-first, delegated-control portfolio manager" konumlandırması oluştur | S |
| 3 | rotki doğrudan rakip: self-hosted + gizlilik + CEX — CoinHQ'dan daha olgun | High | Delegated trading + paylaşım linkleri ön plana çıkar; rotki'de bunlar yok | S |
| 4 | Mobil uygulama yokluğu — Delta ve CoinStats mobil öncelikli; CoinHQ yalnızca web | Med | PWA kısa vadede; Phase 3-4'te native mobil | L |

---

## İyileştirme Önerileri (planlı)

| # | Öneri | Etki | Çözüm | Efor |
|---|-------|------|-------|------|
| 1 | **Exchange adaptör sayısını artır:** Coinbase, Kraken, KuCoin, Gate.io (top 7-8) → kullanım tabanını genişletir | High | Mevcut adapter pattern'ı kullanarak yeni exchange'ler ekle | M per exchange |
| 2 | **"Delegated Trading" farklılaştırıcısı olarak pazarla:** Hiçbir self-hosted rakip bu kadar granüler izin yönetimi sunmuyor | High | Phase 2 tamamlanınca bu özellik etrafında içerik + PR çalışması | S |
| 3 | **rotki ile fark yaratan özellikler:** rotki'nin olmadığı: paylaşım linkleri + delegated access + web-first UX — bunları öne çıkar | High | Karşılaştırma landing page'i | M |
| 4 | **Vergi raporu entegrasyonu (Phase 3+):** Koinly ve Blockpit bu segmenti domine ediyor; basit CSV export bile rekabetçilik katar | Med | PnL tamamlanınca CSV/PDF export + ülke bazlı format | M |
| 5 | **On-chain cüzdan desteği (okuma):** Zapper/DeBank tamamen on-chain; CoinHQ hybrid yapı sunarsa daha geniş kitleye ulaşır | Med | Public address izleme (API key gerektirmeden) ekle | L |
| 6 | **PWA (Progressive Web App):** Mobil uygulama olmadan mobil kullanıcı kaybı yaşanır | Med | next.js PWA manifest + service worker | S |

---

## Kesin Olmalı (Industry Standard)

- **En az 8-10 major exchange desteği:** Binance + Bybit + OKX yalnızca ~%55-60 pazar payını kapsıyor; Coinbase, Kraken, KuCoin olmadan kalan %40 kullanıcıya ulaşılamaz
- **Responsive / mobil-uyumlu frontend:** Tüm rakipler mobil-first; web-only yaklaşım 2026'da rekabetçi değil
- **Portfolio performans geçmişi (PnL):** Kullanıcıların portföy değişimini zaman içinde görememesi temel eksik — Phase 3 önceliklendirilmeli
- **Arama ve filtre:** Coin arama, tarih filtresi, exchange filtresi — dashboard temel UX gereklilikleri

## Kesin Değişmeli (Mevcut Sorunlar)

- **"Self-hosted" vurgusu teknik kullanıcı dışını dışlıyor:** README'de kurulum talimatları çok teknik; geniş kitle için cloud seçeneği + kurulum sihirbazı şart
- **Rakip karşılaştırması yapılmamış:** Ürün hiçbir yerde "neden CoinHQ, neden rotki değil" sorusunu yanıtlamıyor
- **3 exchange ile MVP çıkmak risk:** İlk 100 kullanıcının önemli kısmı Coinbase veya Kraken kullanıcısı olabilir; onlar için ürün işe yaramaz

## Nice-to-Have (Diferansiasyon)

- **"Social Portfolio" — takip/karşılaştırma:** CoinStats'ın sosyal özellikleri var; CoinHQ da anonim portföy paylaşımını sosyal platforma dönüştürebilir
- **AI Insight (Phase 4):** Zapper ve DeBank'te olmayan; "şu coin portföyünün %40'ını oluşturuyor, risk yüksek" tarzı uyarılar ciddi diferansiasyon sağlar
- **Audit-ready paylaşım:** Muhasebeci için read-only + zaman damgalı, imzalı portföy raporu — Koinly benzeri ama daha basit; B2B segment için güçlü kanca
- **Telegram alert entegrasyonu (Phase 3):** DeBank ve rotki'nin zayıf olduğu bir alan; CoinHQ için düşük maliyetli yüksek değerli özellik

---

## Rekabet Matrisi — CoinHQ vs Doğrudan Rakipler

| Özellik | CoinHQ | rotki | Ghostfolio | CoinStats |
|---------|--------|-------|------------|-----------|
| Self-hosted | ✅ | ✅ | ✅ | ❌ |
| Cloud SaaS | Planlanıyor | Kısmi | ✅ ($19/ay) | ✅ |
| CEX desteği | 3 | Çok | Sınırlı | 300+ |
| DeFi/on-chain | ❌ | ✅ | ❌ | ✅ |
| Delegated trading | Phase 2 | ❌ | ❌ | ❌ |
| Paylaşım linkleri | ✅ (granüler) | ❌ | Kısmi | ❌ |
| Vergi raporu | ❌ | ✅ | ❌ | ❌ |
| Mobil | ❌ | ❌ | ❌ | ✅ |
| AI insight | Phase 4 | ❌ | ❌ | Kısmi |
| Fiyat | Ücretsiz (self-h.) | Ücretsiz | Ücretsiz/$19 | $3.49/ay+ |

**Sonuç:** CoinHQ'nun en net farkı = **Delegated Trading + Granüler Paylaşım + Self-hosted + Modern Web UX**. Bu kombinasyona sahip başka bir araç yok. Odak bu 3-4 özellikte tutulmalı, rakiplerin her özelliğini kopyalamaya çalışılmamalı.

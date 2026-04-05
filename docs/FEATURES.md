# CoinHQ — Feature Listesi

Bu dosya ürün gereksinimlerini içerir. Implementasyon detayları için `README.md` ve `CLAUDE.md`'ye bak.

---

## Phase 1 — Temel (MVP)

### Multi-Profil Portföy Takibi
- Birden fazla kişinin portföyü aynı uygulamada tutulur
- Her profil bir kişiyi veya hesap setini temsil eder (login yok, profil seçici var)
- Tüm profiller aynı anda görüntülenebilir veya tek tek geçiş yapılabilir
- Profil sahibi ve o profili yöneten/danışmanlık yapan kişi farklı olabilir

### Exchange Bağlantısı
- Desteklenen borsalar: Binance, Bybit, OKX (Phase 1)
- API key ve secret uygulama içinden girilir — exchange paneline gitmek gerekmez
- Yalnızca read-only key kabul edilir; write izni olan key reddedilir
- API secret şifreli (AES-256) saklanır, hiçbir zaman loglanmaz veya response'a yazılmaz

### Dashboard
- Toplam portföy değeri (USD)
- Coin bazlı dağılım (pie chart)
- Borsa bazlı bakiyeler
- Tüm profiller için aggregate görünüm

---

## Phase 1 — Paylaşım & Danışmanlık

### Paylaşım Linki
- Profil sahibi, portföy verisini başkasıyla paylaşmak için link oluşturur
- Karşı taraf (danışman, muhasebeci, ortak) linki açar — API secret'a erişemez, sisteme giriş yapmak zorunda değildir
- Her link için izinler ayrı ayrı ayarlanır:
  - Toplam portföy değerini göster / gizle
  - Coin miktarlarını göster / gizle
  - Borsa isimlerini göster / gizle
  - Yüzde dağılımı göster / gizle
  - Profil sahibinin kimliğini göster / gizle
- Link süresi: 1 gün / 7 gün / 30 gün / süresiz
- Link etiketi verilebilir: "Muhasebeci", "Ortak", "Yatırım danışmanı"
- Link istediğinde iptal edilir

### Danışman Görünümü
- Danışman yalnızca profil sahibinin izin verdiği verileri görür
- Borsa isimleri gizlenince "Exchange #1", "Exchange #2" gibi anonim isimler gösterilir (tutarlı ama geri döndürülemez)
- Profil sahibi kimliği gizlenebilir — danışman kimin portföyünü gördüğünü bilmeyebilir

---

## Güvenlik

- Read-only API key doğrulaması: bağlanırken write izni test edilir, varsa key reddedilir
- API key/secret asla log'a, commit'e veya HTTP response'a yazılmaz
- Paylaşım tokenleri 256-bit entropi ile üretilir
- Public (paylaşım) endpointlerinde IP başına rate limiting
- HTTPS zorunlu (production)

---

## Phase 2+ (Sonraki)

- PnL hesaplama (realized / unrealized)
- Trade history görüntüleme
- Gelişmiş grafikler
- Email / Telegram uyarıları
- AI insight katmanı (trend analizi, risk uyarıları)
- Trade otomasyonu (opsiyonel, ayrı izin)

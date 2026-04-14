## #9 Analytics & Tracking Analiz Raporu
> Lead: GrowthLead (A11) | Model: Sonnet 4.6

---

### Bağlam Notu

CoinHQ self-hosted bir uygulama. Bu, third-party analytics araçlarının entegrasyonunda kullanıcı onayı (GDPR/KVKK) ve veri egemenliği konularının önem kazandığı anlamına gelir. Self-hosted kullanıcılar genellikle gizlilik odaklıdır; bu yüzden Plausible veya Umami gibi privacy-first araçlar GA'ya göre daha uygun olabilir.

---

### Mevcut Durum

**Yapılmış olanlar:**
- Hiçbir analytics/tracking kodu yok
- Backend'de `cached: boolean` alanı response'da mevcut — teknik monitoring için temel var
- Rate limiting (`slowapi`) — dolaylı olarak trafik anomalilerini yakalar

**Eksik olanlar:**
- Sayfa görüntüleme, tıklama, funnel takibi
- Kullanıcı aktivasyon/retansiyon metrikleri
- Hata izleme (error tracking)
- Performance monitoring
- Share link tıklama takibi
- Backend API log metrikleri

**Puan: 1/10**

Sıfırdan başlanıyor — tek pozitif nokta, temiz bir slate olması.

---

### Kritik Eksikler (hemen yapılmalı)

| # | Sorun | Etki | Çözüm | Efor |
|---|-------|------|-------|------|
| 1 | Frontend'de hiç analytics yok | High | Privacy-first çözüm ekle: Plausible veya Umami (self-hosted) — script tag yeterli | S |
| 2 | Share link görüntüleme sayısı takip edilmiyor | High | Backend'e share_links tablosuna `view_count` ve `last_viewed_at` ekle | S |
| 3 | Frontend hata takibi yok | High | Sentry (veya self-hosted Glitchtip) — Next.js entegrasyonu 30 dakika | M |
| 4 | Kullanıcı aktivasyon hunisi görünmüyor | Med | Exchange ekleme, share link oluşturma eventlerini logla (backend audit log) | M |

---

### İyileştirme Önerileri (planlı)

| # | Öneri | Etki | Çözüm | Efor |
|---|-------|------|-------|------|
| 1 | Backend yapısal loglama | High | FastAPI'ye structlog ekle — JSON formatında request/response logları; exchange bazlı hata oranı takibi | M |
| 2 | Custom event tracking | Med | Share link kopyalama, profil ekleme, exchange bağlantısı gibi key action'ları Plausible custom event olarak gönder | M |
| 3 | Portfolio yükleme süresi metrikleri | Med | Exchange API response sürelerini backend'de logla — hangi exchange yavaş? | M |
| 4 | Admin panel / basit dashboard | Med | Kayıtlı kullanıcı sayısı, aktif share link sayısı, exchange dağılımı — bile basit bir `/admin/stats` endpoint | M |
| 5 | Health check endpoint metrikleri | Low | `/health` endpoint'ini genişlet — Redis durumu, DB bağlantısı, son exchange API başarı oranı | S |
| 6 | Uptime monitoring | Low | Self-hosted: Uptime Kuma — docker-compose'a eklenebilir | S |

---

### Kesin Olmalı (industry standard)
- Temel sayfa görüntüleme takibi (Plausible/Umami — privacy-first, self-host edilebilir)
- Frontend hata izleme (Sentry veya Glitchtip)
- Yapısal backend loglama (JSON logları)
- Share link view_count — en kritik ürün metriği

### Kesin Değişmeli (mevcut sorunlar)
- Kör uçuş: hangi sayfanın, özelliğin kullanıldığı bilinmiyor
- Exchange API başarısızlıkları sessizce geçiyor — kullanıcı kaybediliyor
- Share link etkisi ölçülemiyor — viral loop'un çalışıp çalışmadığı bilinmiyor

### Nice-to-Have (diferansiasyon)
- Self-hosted Metabase/Grafana ile ürün metrikleri dashboard'u
- Exchange API latency breakdown — Binance/Bybit/OKX karşılaştırmalı
- Cohort analizi: hangi ay kaydolan kullanıcılar portföy ekliyor?
- A/B test altyapısı — share link CTA metni optimizasyonu için

---

### Öneri: Self-Hosted Analytics Stack

Self-hosted kullanıcılara önerilecek stack:

```
Plausible Analytics (privacy-first) → sayfa görüntüleme, custom events
Glitchtip (Sentry alternatifi) → hata takibi
Uptime Kuma → uptime monitoring
Grafana + Loki → backend log görselleştirme (Phase 3+)
```

Hepsi Docker ile deploy edilebilir — CoinHQ'nun docker-compose.yml'ine ek servis olarak eklenebilir.

---

> **Not:** Analytics olmadan hangi özelliğin işe yaradığı bilinmez. MVP bitse bile en az Plausible + share link view_count mutlaka eklenmeli — aksi hâlde Phase 2 kararları tahmine dayalı olur.

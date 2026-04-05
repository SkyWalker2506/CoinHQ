## #2 Performance & Core Web Vitals Analiz Raporu
> Lead: CodeLead (A10) | Model: Sonnet

---

### Mevcut Durum

**Güçlü Yanlar:**
- Redis cache var: portfolio verisi 60 saniye TTL ile Redis'te tutulur (`portfolio_service.py:162`)
- Rate limiting uygulanmış: slowapi ile `/portfolio` endpoint'leri `10/minute` korumalı
- Async mimari: tüm backend IO async (asyncpg, httpx async, redis.asyncio) — event loop bloke edilmiyor
- Connection reuse: asyncpg connection pool SQLAlchemy üzerinden yönetiliyor
- Next.js `output: "standalone"` — Docker imajı optimize

**Puan: 4/10**

Temel cache altyapısı mevcut ama kritik performans sorunları çözülmemiş: exchange çağrıları seri yapılıyor, fiyat verileri her key için ayrı çekiliyor, frontend'de hiç caching yok.

---

### Kritik Eksikler (hemen yapılmalı)

| # | Sorun | Etki | Çözüm | Efor |
|---|-------|------|-------|------|
| 1 | **Exchange çağrıları seri** — `_fetch_exchange_balance` loop'ta sırayla çağrılıyor (`portfolio_service.py:147`). 3 exchange varsa 3x gecikme birikir. | High | `asyncio.gather(*[_fetch_exchange_balance(k) for k in keys])` ile paralel çalıştır | S |
| 2 | **CoinGecko her exchange için ayrı çağrı** — her `_fetch_exchange_balance` içinde `_get_usd_prices` çağrılıyor. 3 exchange × 1 API call = 3 CoinGecko isteği | High | Tüm asset'leri önce topla, tek `_get_usd_prices` çağrısıyla al, sonra dağıt | S |
| 3 | **Aggregate endpoint N+1 sorgu** — `aggregate_portfolio` her profil için ayrı `get_portfolio` çağırıyor, her biri ayrı exchange + CoinGecko isteği yapıyor (`portfolio.py:48-52`) | High | Tüm profilleri paralel fetch et (`asyncio.gather`), ortak CoinGecko fiyatını paylaş | M |
| 4 | **Binance `get_balances` await eksik** — `binance.py:32` satırında `resp = client.get(...)` — `await` yok. Bu coroutine'i block eder, hata fırlatmaz ama sessizce yanlış çalışır | High | `resp = await client.get(...)` olmalı | S |
| 5 | **Redis singleton güvensiz** — `get_redis()` global `_redis` değişkeni kontrol ediyor ama async race condition var: birden fazla coroutine aynı anda `None` görüp birden fazla bağlantı açabilir | Med | `asyncio.Lock` veya startup'ta tek seferlik init + `app.state.redis` pattern kullan | S |

---

### İyileştirme Önerileri (planlı)

| # | Öneri | Etki | Çözüm | Efor |
|---|-------|------|-------|------|
| 1 | **Frontend'de SWR/React Query kullan** — şu an `useEffect` + raw `fetch`, her render'da yeniden istek atılabilir, loading state basit | Med | `swr` veya `@tanstack/react-query` ekle; stale-while-revalidate ile kullanıcı beklemez | M |
| 2 | **CoinGecko fiyatlarını ayrı cache'le** — şu an portfolio cache fiyatları içeriyor ama fiyatlar sık değişiyor, portfolio nadiren değişir; ayrı `prices:{ids}` key ile 30s TTL | Med | `_get_usd_prices` içinde Redis cache ekle | S |
| 3 | **httpx.AsyncClient yeniden kullanımı** — her `get_balances` çağrısında yeni `AsyncClient` açılıp kapanıyor. Bağlantı kurma maliyeti tekrarlanıyor | Med | `app.state.http_client` olarak lifespan'da tek client yönet | M |
| 4 | **Next.js Image optimization** — `next/image` kullanılmıyor, exchange logo veya kullanıcı görseli gelirse yavaş yüklenecek | Low | Exchange eklenince `next/image` ile logo serve et | S |
| 5 | **`pool_size` ve `max_overflow` konfigürasyonu** — SQLAlchemy engine default pool ayarlarıyla çalışıyor | Low | `create_async_engine(..., pool_size=10, max_overflow=20)` ekle | S |
| 6 | **Frontend bundle analizi** — recharts tek başına ~400KB, tree-shake kontrolü yapılmamış | Low | `@next/bundle-analyzer` ekle, recharts lazy import ile sadece kullanılan chart'ı yükle | M |

---

### Kesin Olmalı (industry standard)

- Exchange API çağrıları **paralel** olmalı — seri çalışmak production'da kabul edilemez
- CoinGecko API'ye **tek toplu çağrı** yapılmalı — per-exchange ayrı çağrı hem yavaş hem rate limit riski
- Redis bağlantısı **application startup**'ta tek seferlik açılmalı, her request'te kontrol edilmemeli
- Frontend **loading skeleton** kullanmalı — "Loading portfolio..." text kabul edilemez UX

### Kesin Değişmeli (mevcut sorunlar)

- `binance.py:32` — `await` eksikliği kritik bug: Binance balance fetch sessizce çalışmıyor
- `_fetch_exchange_balance` loop → `asyncio.gather` dönüşümü yapılmadan prod'a çıkılmamalı
- Her exchange için ayrı CoinGecko çağrısı → CoinGecko free tier'da 10-50 req/min limiti var, çok kullanıcıda limit aşılır

### Nice-to-Have (diferansiasyon)

- **WebSocket push**: portfolio değişince server'dan push yerine polling — gerçek zamanlı deneyim
- **Service Worker cache**: offline mod veya arka planda güncelleme
- **Core Web Vitals monitoring**: Vercel Analytics veya Sentry performance
- **Streaming SSR**: Next.js 14 Suspense + streaming ile dashboard parça parça gelsin
- **Edge Runtime**: Public share endpoint (`/share/[token]`) CDN edge'de çalışabilir, gecikme sıfırlanır

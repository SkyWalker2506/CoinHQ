# CoinHQ — Sistem Test Planı (Uçtan Uca Davranış + Koşul Matrisi)

Bu doküman, sistemin uçtan uca **nasıl çalışması gerektiğini** ve test edilecek
**koşul matrisini** tanımlar. Kaynak: `docs/FEATURES.md`, `README.md`,
`backend/app/api/v1/*.py`, `backend/app/core/{limits.py,trade_limits.py,security.py}`,
`backend/app/services/*.py`, `backend/app/models/*.py`, `frontend/src/app/**/page.tsx`
ve `frontend/src/components/`.

**Okuma kılavuzu:** Her koşul `C-XXX` ile numaralandırılmıştır ve tek satırlık,
test-edilebilir bir kuraldır: *verilen durum → beklenen sonuç (HTTP kodu / davranış)*.
`EDGE` etiketli koşullar mevcut kod davranışını pinler; ürün kararı gerektirebilir.

---

## 1. Sistem Akışları (Kısa)

### 1.1 Auth — Google OAuth → JWT → Refresh
1. `GET /api/v1/auth/google` → Redis'e tek kullanımlık CSRF `state` yazılır (TTL 10 dk) → Google consent'e redirect.
2. `GET /api/v1/auth/google/callback` → `state` Redis'ten atomik silinerek doğrulanır (yoksa 403) → code→token exchange → userinfo → `google_id` üzerinden user **upsert** (email/name güncellenir) → access token (24 saat, `type=access`) + refresh token (7 gün, `type=refresh`) üretilir → `{FRONTEND_URL}/auth/callback?token=...&refresh_token=...` redirect.
3. Frontend token'ları `localStorage`'a yazar; her istekte `Authorization: Bearer`. 401 alınca **bir kez** `POST /auth/refresh` denenir; başarısızsa token'lar silinip `/login`'e yönlendirilir.
4. Korumalı her endpoint `get_current_user` dependency'sinden geçer (JWT decode + DB'den user).

### 1.2 Profil / Key Yönetimi
- Profiller kullanıcıya aittir; tüm CRUD `profile.user_id == current_user.id` ile izole edilir.
- Key ekleme: `key_type` `read_only` veya `trade`. Kaydetmeden **önce** adapter ile canlı validasyon:
  - `read_only` → `validate_key()`: herhangi bir write/trade izni varsa `ValueError` → **400 (KEY REDDEDİLİR)**.
  - `trade` → `validate_trade_key()`: spot trade yapabilmeli; **withdrawal/transfer izni varsa reddedilir** (400).
- Key + secret Fernet (AES-256) ile şifrelenip saklanır; response şeması (`ExchangeKeyRead`) yalnız `id, profile_id, exchange, key_type, created_at` içerir.
- Aynı profil + exchange için bir `read_only` VE bir `trade` key olabilir (DB unique: `profile_id+exchange+key_type`). Tier limiti **distinct exchange** sayısına bakar; aynı borsanın ikinci tip key'i limite sayılmaz.

### 1.3 Portföy — Exchange Fetch → Fiyatlama → Cache → Snapshot
1. `GET /portfolio/profile/{id}` (rate limit `10/minute`/IP): Redis `portfolio:profile:{id}` cache'i kontrol edilir (TTL 60 sn, hit'te `cached=true`).
2. Cache miss'te tüm exchange bakiyeleri paralel çekilir (`asyncio.gather`); hata veren borsa **atlanır** (partial 200).
3. Fiyatlama: Binance public ticker (tüm USDT çiftleri, Redis 30 sn) → bulunamayan asset'ler için CoinGecko fallback (60 sn/coin) → stablecoin'ler $1 → hiçbirinde yoksa $0.
4. Cache miss'te profil başına **saatte en fazla 1** `PortfolioSnapshot` yazılır (best-effort).
5. `GET /portfolio/aggregate`: kullanıcının tüm profilleri paralel; `grand_total_usd` + `asset_totals`; snapshot yazmaz.

### 1.4 Share Link — İzin Bayrakları + Maskeleme + Expiry + Follow
- Owner kendi profili için link üretir: token `secrets.token_urlsafe(32)` (256-bit). Bayraklar: `show_total_value` (default T), `show_coin_amounts` (F), `show_exchange_names` (F), `show_allocation_pct` (T), `allow_follow` (T) + expiry, label, trade alanları.
- `GET /public/share/{token}` (auth yok, 30/dk/IP): revoked/yok → 404; expired → **410** (view_count artmadan); başarıda `view_count+1` atomik, `last_viewed_at` güncellenir. Bayraklara göre alanlar `null`'lanır; borsa adları `sha256[:8]` ile deterministik maskelenir; gerçek profil adı hiç dönmez (label yoksa "Crypto Portfolio"); sıfır bakiyeler elenir.
- Revoke (`DELETE /share/{id}`) `is_active=false` yapar → link anında ölür (404). `PATCH` değişiklikleri public view'a anında yansır.
- Follow: giriş yapmış kullanıcı `POST /followed/{token}` ile takip eder; `allow_follow=false` → 403; idempotent (unique `user_id+token`).

### 1.5 Delegated Trading (Share Token ile) — ÇEKİM ASLA YOK
1. `POST /public/share/{token}/trade` (auth yok, 10/dk/IP): token aktif mi (404), expired mı (410), `can_trade` mı (403).
2. `execute_trade`: profilin ilgili borsadaki **trade** key'i çözülür (yoksa 400) → `check_delegate_trade` sırayla: `can_trade` → yön (`trade_direction`: both|buy|sell) → coin whitelist (CSV, boş=hepsi) → tutar>0 → emir başı USD limiti → 24 saatlik birikimli USD limiti (`spent_today + emir > limit` → red). Her ihlal **403**.
3. 24s harcama = **aynı linkin** son 24 saatteki `status=filled` order'larının `usd_value` toplamı (owner ve başka linklerin emirleri sayılmaz).
4. Uygunsa spot MARKET emri backend proxy'den imzalı gider (trade key delegate'e asla gösterilmez); `TradeOrder` kaydı: `actor=delegate`, `share_link_id`, `symbol={ASSET}USDT`, `status=filled`, `amount=executedQty`.
5. Withdrawal/transfer **hiçbir kod yolunda yoktur**: adapter'larda withdrawal endpoint'i yok + trade key validasyonu withdrawal iznini reddeder.

### 1.6 Owner Trading
- `POST /profiles/{id}/trade`: sadece profil sahibi (aksi 404). Delegate limitleri **uygulanmaz** (yön/whitelist/limit yok — owner kendi anahtarının sahibidir). Trade key yoksa 400. `actor=owner`, `share_link_id=NULL`.

### 1.7 Trade Audit Log
- Her emir (owner+delegate, filled/failed) `trade_orders` tablosuna yazılır; `GET /profiles/{id}/trade` son 50 kaydı yeniden-eskiye döner. Bu log aynı zamanda 24s limitinin veri kaynağıdır.

### 1.8 P&L (AVCO)
- `GET /profiles/{id}/pnl`: yalnız CoinHQ üzerinden geçen `filled` + `amount IS NOT NULL` emirlerle, `created_at` sırasında average-cost yöntemi. Sell'de realized = `satılan_qty × (satış_birim_fiyatı − avg_cost)`; over-sell takip edilen miktara **clamp** edilir. Veriler **kısmidir** (borsada dışarıdan yapılan işlemler görünmez) — UI bunu belirtmelidir.

### 1.9 Portfolio Snapshots / History
- Snapshot: portföy fetch'inde (cache miss) saatte en fazla 1 kayıt (`total_usd`).
- `GET /profiles/{id}/history?days=N` (default 30, 1–365): cutoff sonrası snapshot'lar **eski→yeni** döner; dashboard grafiğini besler.

### 1.10 Waitlist
- `POST /waitlist` (auth yok): email normalize (trim+lowercase) + regex; yeni → 201, duplicate → **200** ile mevcut kayıt (idempotent).

### 1.11 Admin Stats
- `GET /admin/stats`: yalnız `tier == "admin"` (aksi 403). Döner: `users`, `profiles`, `exchange_keys`, `active_share_links`, borsa dağılımı, tier dağılımı.

### 1.12 Tier Limitleri
- `free`: **1 profil**, profil başına **2 distinct exchange**. `premium`: sınırsız (-1). Bilinmeyen tier → free'ye düşer. İhlaller **403** (`tier_limit` detayıyla) döner; frontend `UpgradeBanner` gösterir.

---

## 2. KOŞUL MATRİSİ

### A. Auth & Oturum

| ID | Verilen durum | Beklenen sonuç |
|----|----------------|----------------|
| C-001 | `GET /auth/google` çağrılır | Google consent'e redirect; Redis'e `oauth_state:{state}` yazılır (TTL 600 sn) |
| C-002 | Callback'e `error` parametresi veya `code`'suz gelinir | 401 "OAuth error" |
| C-003 | Callback `state` parametresi olmadan çağrılır | 403 "Invalid OAuth state" |
| C-004 | Callback bilinmeyen/daha önce kullanılmış `state` ile çağrılır | 403 (state tek kullanımlık — Redis delete atomik) |
| C-005 | Google token exchange non-200 döner | 401 "Failed to exchange OAuth code" |
| C-006 | Google userinfo non-200 döner | 401 "Failed to fetch user info" |
| C-007 | Userinfo'da `sub` veya `email` eksik | 400 "Incomplete user info" |
| C-008 | İlk kez giriş yapan Google hesabı | User kaydı oluşur; `{FRONTEND_URL}/auth/callback?token=...&refresh_token=...` redirect |
| C-009 | Aynı `google_id` ikinci kez giriş yapar | Duplicate user oluşmaz; email/name güncellenir (upsert) |
| C-010 | `POST /auth/refresh` geçerli refresh token ile | 200 `{access_token, token_type:"bearer"}` |
| C-011 | Refresh süresi dolmuş/imzası bozuk token ile | 401 "Invalid or expired refresh token" |
| C-012 | Refresh endpoint'ine **access** token verilir (`type != refresh`) | 401 |
| C-013 | Korumalı endpoint `Authorization` header'sız çağrılır | 403 (HTTPBearer "Not authenticated") |
| C-014 | Korumalı endpoint geçersiz/expired access JWT ile | 401 "Could not validate credentials" |
| C-015 | JWT geçerli ama user DB'den silinmiş | 401 |
| C-016 | Access token 24 saat, refresh 7 gün sonra kullanılır | Süre sonunda 401; frontend 401'de bir kez otomatik refresh dener, o da düşerse `/login`'e atar |

### B. Profil Yönetimi (Sahiplik / İzolasyon / Tier)

| ID | Verilen durum | Beklenen sonuç |
|----|----------------|----------------|
| C-017 | `GET /profiles/` | Yalnız kendi profilleri döner (başka kullanıcınınki asla listelenmez), isme göre sıralı |
| C-018 | Free kullanıcı 1 profili varken 2.'yi oluşturur | 403 "Free tier limit: 1 profile..." |
| C-019 | Premium kullanıcı çok sayıda profil oluşturur | Her biri 201 (sınırsız) |
| C-020 | Aynı kullanıcı aynı isimde ikinci profil | 400 "Profile name already exists" |
| C-021 | Farklı kullanıcı aynı isimde profil | 201 (isim tekilliği kullanıcı-bazlı) |
| C-022 | Boş / başında-sonunda boşluklu / 100+ karakter isim | 422 (Pydantic pattern + length) |
| C-023 | `GET /profiles/{id}` var olmayan id | 404 "Profile not found" |
| C-024 | `GET /profiles/{id}` başka kullanıcının profili | 403 "Access denied" |
| C-025 | `DELETE /profiles/{id}` kendi profili | 204; keys, share links, trade orders, snapshots **cascade** silinir |
| C-026 | `DELETE /profiles/{id}` başka kullanıcının profili | 403 |
| C-027 | `DELETE /profiles/{id}` var olmayan id | 404 |

### C. API Key Yönetimi (Validasyon / Şifreleme)

| ID | Verilen durum | Beklenen sonuç |
|----|----------------|----------------|
| C-028 | `GET /profiles/{id}/keys/` kendi profili | 200; response'ta **api_key/secret alanı yok** (yalnız id, exchange, key_type, created_at) |
| C-029 | Keys endpoint'leri başka kullanıcının profiliyle | 403; var olmayan profil → 404 |
| C-030 | Desteklenmeyen exchange (`"kucoin"`) ile key ekleme | 400 "Unsupported exchange" (desteklenen: binance, bybit, okx, coinbase, kraken, binancetr, gateio) |
| C-031 | Free kullanıcı 2 distinct exchange'i olan profile 3. borsayı ekler | 403, detay `tier_limit:` ile başlar |
| C-032 | Free kullanıcı mevcut borsaya (ör. binance read_only varken) **aynı borsanın** trade key'ini ekler | 201 — aynı exchange limite ikinci kez sayılmaz |
| C-033 | Premium kullanıcı 3+ farklı borsa ekler | Hepsi 201 |
| C-034 | `read_only` key'in exchange'de write/trade izni var | 400 — KEY REDDEDİLİR ("Write permissions detected...") |
| C-035 | Geçerli salt-okunur key eklenir | 201, `key_type=read_only` |
| C-036 | `trade` key'in withdrawal/internal-transfer izni var | 400 — REDDEDİLİR ("withdrawals and transfers disabled" mesajı) |
| C-037 | `trade` key spot trade yapamıyor | 400 "This key cannot trade..." |
| C-038 | `trade` key spot yapabiliyor, withdrawal kapalı | 201, `key_type=trade` |
| C-039 | Key/secret yanlış (exchange auth hatası) | 400 "API key validation failed..." |
| C-040 | Exchange API'ye ulaşılamıyor (timeout/network) | 502 "Could not reach exchange API" — key kaydedilmez |
| C-041 | Adapter trade validasyonu implemente değil | 400 (NotImplementedError mesajı) |
| C-042 | `key_type` alanına "read_only"/"trade" dışı değer | 422 (Literal şema) |
| C-043 | 8 karakterden kısa api_key/api_secret | 422 |
| C-044 | Aynı profil+exchange+key_type için ikinci key | DB unique constraint reddeder — beklenen anlamlı 400/409 (mevcutta yakalanmayan IntegrityError; test pinlemeli) |
| C-045 | Başarıyla eklenen key DB'de incelenir | Yalnız Fernet ciphertext var; plaintext key/secret hiçbir kolonda yok |
| C-046 | `DELETE .../keys/{key_id}` başka profile ait key id ile | 404; kendi key'i → 204 |

### D. Portföy (Fetch / Cache / Fiyatlama / Aggregate)

| ID | Verilen durum | Beklenen sonuç |
|----|----------------|----------------|
| C-047 | `GET /portfolio/profile/{id}` var olmayan → 404; başkasının → | 403 |
| C-048 | Aynı IP'den dakikada 10'dan fazla portfolio isteği | 429 (slowapi, `RATE_LIMIT_PORTFOLIO=10/minute`) |
| C-049 | İlk istek (cache miss) → `cached=false`; 60 sn içinde ikinci istek | `cached=true`, exchange'e gidilmez |
| C-050 | Cache TTL (60 sn) dolduktan sonra istek | Yeniden canlı fetch, `cached=false` |
| C-051 | Profilin 2 borsasından biri hata veriyor | 200 partial: hatalı borsa yanıttan düşer, diğeri döner (500 fırlatılmaz) |
| C-052 | Binance USDT çifti olan asset (BTC) + stablecoin (USDT/USDC) | BTC ticker fiyatıyla, stablecoin $1.0 ile fiyatlanır |
| C-053 | Binance'te çifti olmayan asset | CoinGecko fallback'ten fiyatlanır; orada da yoksa `usd_value=0` (istek patlamaz) |
| C-054 | Cache miss + son 1 saatte snapshot yok | Yeni `PortfolioSnapshot(total_usd)` yazılır |
| C-055 | Son 1 saat içinde snapshot varken tekrar fetch | Yeni snapshot yazılmaz (throttle 1/saat) |
| C-056 | `GET /portfolio/aggregate` | Kullanıcının tüm profilleri; `grand_total_usd` = toplam; `asset_totals` asset bazında birleşik USD |
| C-057 | Aggregate'te bir profilin fetch'i exception atar | O profil atlanır, kalanlar döner (200) |

### E. Share Link CRUD (Owner Tarafı)

| ID | Verilen durum | Beklenen sonuç |
|----|----------------|----------------|
| C-058 | Kendi profili için `POST /share` | 201; token ~43 karakter URL-safe (256-bit entropi); `share_url=/share/{token}` |
| C-059 | Başkasının/var olmayan profili için `POST /share` | 404 "Profile not found" (403 değil — kaynak varlığı sızdırılmaz) |
| C-060 | Bayraklar gönderilmeden link oluşturulur | Default'lar: total=T, amounts=F, exchange_names=F, alloc=T, allow_follow=T, can_trade=F, direction=both, view_count=0 |
| C-061 | `can_trade=true` ama profilde trade key yok | 400 "Add a trade key ... before enabling trading" |
| C-062 | `can_trade=true` ve profilde trade key var | 201 |
| C-063 | `PATCH /share/{id}` kısmi payload | 200; yalnız gönderilen alanlar değişir (PATCH semantiği) |
| C-064 | `PATCH` başkasının linki / var olmayan link | 404 |
| C-065 | `PATCH` ile trade key'siz profilde `can_trade=true` yapılır | 400 |
| C-066 | `PATCH` ile limit düşürülür (ör. daily 2000→100) | Sonraki delegate emri **anında** yeni limite göre değerlendirilir |
| C-067 | `GET /share` | Yalnız kendi profillerinin **aktif** linkleri (revoked görünmez), yeni→eski |
| C-068 | `GET /share?profile_id=X` | Yalnız o profilin linkleri |
| C-069 | `DELETE /share/{id}` kendi linki | 204; `is_active=false` |
| C-070 | `DELETE /share/{id}` başkasının/var olmayan link | 404 |

### F. Public Share View (Maskeleme / Expiry / View Count)

| ID | Verilen durum | Beklenen sonuç |
|----|----------------|----------------|
| C-071 | `GET /public/share/{token}` bilinmeyen token | 404 "Link not found or has been revoked" |
| C-072 | Revoke edilmiş linkin token'ı | 404 (revoke anında etkili) |
| C-073 | `expires_at` geçmiş link | **410** "This link has expired"; `view_count` ARTMAZ |
| C-074 | Geçerli link görüntülenir (eşzamanlı istekler dahil) | 200; `view_count` atomik +1, `last_viewed_at` güncellenir; owner listede artışı görür |
| C-075 | `show_total_value=false` | `total_usd`, her asset'in `usd_value`'su ve exchange `total_usd` → `null` |
| C-076 | `show_coin_amounts=false` | Her asset'in `amount` alanı → `null` |
| C-077 | `show_exchange_names=false` | Borsa adı → `"Exchange <sha256 ilk 8 hex>"`; deterministik (aynı borsa her görüntülemede aynı maske) ve geri döndürülemez |
| C-078 | `show_allocation_pct=true` ve toplam > 0 | `allocation_pct = usd/grand_total*100` (2 hane); `false` → `null` |
| C-079 | `show_allocation_pct=true` + `show_total_value=false` | Yüzdeler görünür ama hiçbir USD değeri görünmez (bayraklar bağımsız) |
| C-080 | 4 bayrağın 16 kombinasyonu (aşağıdaki tablo) | Her kombinasyonda yalnız ilgili alanlar dolu; diğerleri null/maskeli |
| C-081 | Bakiyesi 0 olan asset | Public görünümde hiç listelenmez |
| C-082 | Link label'lı / label'sız | `profile_name` = label ya da "Crypto Portfolio"; **gerçek profil adı ve owner kimliği asla dönmez** |
| C-083 | Aynı IP'den dakikada 30+ public view isteği | 429 |
| C-084 | `can_trade=true` link görüntülenir | `tradable_exchanges` trade key'li borsaların **gerçek adları** + `trade_spent_today_usd` döner (delegate nereye emir vereceğini bilmeli) |
| C-085 | `can_trade=false` link görüntülenir | `tradable_exchanges=[]`, trade limit alanları default |
| C-086 | Public view auth'suz çağrılır | 200 — login/JWT gerekmez |
| C-087 | Public view response'u taranır | api_key/secret, user email, user id, profil gerçek adı yok |

**C-080 kombinasyon tablosu** (TV=show_total_value, CA=show_coin_amounts, EN=show_exchange_names, AP=show_allocation_pct):

| TV | CA | EN | AP | USD alanları (total/asset/exchange) | amount | exchange_name | allocation_pct |
|----|----|----|----|-----------------------------------|--------|---------------|----------------|
| T | T | T | T | değer | değer | gerçek ad | % |
| T | T | T | F | değer | değer | gerçek ad | null |
| T | T | F | T | değer | değer | maskeli | % |
| T | T | F | F | değer | değer | maskeli | null |
| T | F | T | T | değer | null | gerçek ad | % |
| T | F | T | F | değer | null | gerçek ad | null |
| T | F | F | T | değer | null | maskeli | % |
| T | F | F | F | değer | null | maskeli | null |
| F | T | T | T | null | değer | gerçek ad | % |
| F | T | T | F | null | değer | gerçek ad | null |
| F | T | F | T | null | değer | maskeli | % |
| F | T | F | F | null | değer | maskeli | null |
| F | F | T | T | null | null | gerçek ad | % |
| F | F | T | F | null | null | gerçek ad | null |
| F | F | F | T | null | null | maskeli | % |
| F | F | F | F | null | null | maskeli | null (yalnız asset adları görünür) |

### G. Follow (Takip)

| ID | Verilen durum | Beklenen sonuç |
|----|----------------|----------------|
| C-088 | Giriş yapmış kullanıcı `POST /followed/{token}` (allow_follow=T) | 201 `FollowedPortfolio` kaydı |
| C-089 | Auth'suz follow denemesi | 403 (bearer yok) |
| C-090 | `allow_follow=false` linke follow | 403 "This portfolio does not allow following" |
| C-091 | Revoked/bilinmeyen token'a follow | 404 |
| C-092 | Aynı kullanıcı aynı token'ı ikinci kez follow eder | İdempotent: 201 ile **aynı** kayıt döner, duplicate oluşmaz (unique `user_id+token`) |
| C-093 | `GET /followed` | Yalnız kendi takip listesi, yeni→eski |
| C-094 | `DELETE /followed/{id}` kendi kaydı → 204; başkasının/yok → | 404 |
| C-095 | EDGE: expired ama `is_active=true` linke follow | Mevcut kod izin verir (expiry follow'da kontrol edilmez) — davranış testle pinlenmeli / ürün kararı |

### H. Delegated Trading (Share Token ile)

| ID | Verilen durum | Beklenen sonuç |
|----|----------------|----------------|
| C-096 | `POST /public/share/{token}/trade` bilinmeyen/revoked token | 404 |
| C-097 | Expired linkle trade | **410** |
| C-098 | `can_trade=false` linkle trade | 403 "not permitted to trade" |
| C-099 | `side` "buy"/"sell" dışı ("hold") | 422 (Pydantic pattern) |
| C-100 | `usd_amount <= 0` veya sayı değil | 422 (Field gt=0) |
| C-101 | `exchange`/`asset` eksik ya da boş | 422 |
| C-102 | Seçilen borsa için profilde **trade** key yok (başka borsada olsa bile) | 400 "No trade key configured for {exchange}..." |
| C-103 | Profilde yalnız read_only key varken trade | 400 (read_only key ile asla emir verilmez) |
| C-104 | `trade_direction=buy` iken `side=sell` | 403 "Only buy orders are permitted" |
| C-105 | `trade_direction=sell` iken `side=buy` | 403 "Only sell orders are permitted" |
| C-106 | `trade_direction=both` | Her iki yön de yön kontrolünden geçer |
| C-107 | Whitelist "BTC,ETH" iken `asset=SOL` | 403 "SOL is not in the allowed coin list" |
| C-108 | Whitelist " btc , eth " iken `asset=eth` | Geçer (trim + case-insensitive eşleşme) |
| C-109 | `trade_allowed_coins` null/boş string | Tüm coinler serbest |
| C-110 | `usd_amount > trade_max_per_order_usd` → 403; `== max` | Sınır değeri **izinli** (yalnız aşım reddedilir) |
| C-111 | `spent_24h + usd_amount > trade_daily_limit_usd` | 403 "would exceed the 24h limit" |
| C-112 | `spent_24h + usd_amount == trade_daily_limit_usd` | İzinli (limitin tam dolması red sebebi değil) |
| C-113 | 24s hesabı: 25 saat önceki filled order, `failed` order, **owner** order ve **başka linkin** orderları | Hiçbiri `spent_today`'e sayılmaz; yalnız aynı linkin son 24 saatteki `filled` delegate orderları sayılır |
| C-114 | Tüm kontrollerden geçen delegate emri | 200; `TradeOrder`: `status=filled`, `actor=delegate`, `share_link_id` dolu, `symbol={ASSET}USDT`, `exchange_order_id` ve `amount` (executedQty) kaydedilir |
| C-115 | Exchange API'ye ulaşılamıyor (httpx hatası) | 502 + `TradeOrder` **status=failed** ve `error` alanıyla loglanır (audit'te görünür, 24s limitine sayılmaz) |
| C-116 | Adapter `ValueError` (ör. emir boyutlandırma için fiyat bulunamadı) | 400; order kaydı oluşmaz |
| C-117 | Aynı IP'den dakikada 10+ delegate trade isteği | 429 |

### I. Owner Trading

| ID | Verilen durum | Beklenen sonuç |
|----|----------------|----------------|
| C-118 | `POST /profiles/{id}/trade` başkasının/var olmayan profili | 404 "Profile not found" (owner-trade'de non-owner da 404 alır) |
| C-119 | Kendi profilinde ilgili borsa için trade key yok | 400 |
| C-120 | Owner çok büyük emir / whitelist dışı coin / tek yön kısıtı | **Limit kontrolü YOK** — delegate kuralları (yön/whitelist/emir başı/24s) owner'a uygulanmaz, emir borsaya gider |
| C-121 | Başarılı owner emri | `actor=owner`, `share_link_id=NULL`, `status=filled` |
| C-122 | Geçersiz `side` / `usd_amount<=0` | 422 |
| C-123 | Herhangi bir trade yolu (owner/delegate) ile çekim/transfer denemesi | İmkânsız — adapter'larda withdrawal/transfer endpoint'i yok; trade key validasyonu withdrawal iznini zaten reddediyor (kod + validasyon çift bariyer) |
| C-124 | EDGE: owner trade endpoint'inde rate limit | Yok (mevcut durum) — bilinçli mi, testle/kararla pinlenmeli |

### J. Trade Audit Log

| ID | Verilen durum | Beklenen sonuç |
|----|----------------|----------------|
| C-125 | `GET /profiles/{id}/trade` kendi profili | 200; en fazla son 50 order, `created_at` desc |
| C-126 | Profilde hem owner hem delegate orderlar var | İkisi de listede; `actor` alanından ayırt edilir |
| C-127 | Başkasının profili için trade listesi | 404 |
| C-128 | Her order kaydı | exchange, symbol, base_asset, side, usd_value, actor, status, created_at (+ varsa amount, exchange_order_id, error) içerir — kim/ne zaman/hangi coin/kaç USD izlenebilir |

### K. P&L (AVCO)

| ID | Verilen durum | Beklenen sonuç |
|----|----------------|----------------|
| C-129 | `GET /profiles/{id}/pnl` var olmayan → 404; başkasının → | 403 |
| C-130 | Hiç trade yok | 200; `assets=[]`, `total_realized_pnl_usd=0` |
| C-131 | Yalnız buy'lar (BTC: 1 adet $100 + 1 adet $200) | realized=0; `current_qty=2`, `avg_cost=150`, `total_bought_usd=300`, `buy_count=2` |
| C-132 | Ardından 1 adet $300'a sell | `realized_pnl_usd=+150` (300−150); `current_qty=1`, `avg_cost=150` kalır, `sell_count=1` |
| C-133 | Pozisyonun tamamı satılır | `current_qty=0`, `avg_cost=null` |
| C-134 | Over-sell: CoinHQ 1 adet izlerken 2 adet satılır | Satış izlenen 1 adete **clamp**; qty negatife düşmez; fazlalık P&L'e katılmaz, `total_sold_usd` tam yazılır |
| C-135 | `failed`/`pending` veya `amount=NULL` orderlar | Hesaba katılmaz (yalnız `filled` + amount dolu) |
| C-136 | Orderlar karışık sırada eklenmiş | `created_at` asc işlenir (deterministik AVCO); asset'ler alfabetik döner |
| C-137 | Çoklu asset | `total_realized_pnl_usd` = asset'lerin realized toplamı; UI "yalnız CoinHQ işlemleri — kısmi veri" notunu gösterir |

### L. Snapshots / History

| ID | Verilen durum | Beklenen sonuç |
|----|----------------|----------------|
| C-138 | `GET /profiles/{id}/history` var olmayan → 404; başkasının → | 403 |
| C-139 | `days` verilmez → 30; `days=0` veya `days=366` → | 422 (1 ≤ days ≤ 365) |
| C-140 | Snapshot'lar varken history istenir | Liste **eski→yeni** (`created_at` asc) `{created_at, total_usd}` noktaları |
| C-141 | `days=7` istenir, 10 gün önceki snapshot var | Cutoff dışındaki nokta dönmez |
| C-142 | Portföy 1 saat içinde 5 kez fetch edilir (cache'ler düşürülerek) | En fazla 1 yeni snapshot (throttle) |
| C-143 | Aggregate endpoint'i ve public share view çağrılır | Snapshot **yazılmaz** (yalnız tekil profil portfolio fetch'i yazar) |

### M. Waitlist

| ID | Verilen durum | Beklenen sonuç |
|----|----------------|----------------|
| C-144 | Yeni email ile `POST /waitlist` | **201** `{id, email, plan, source:"web", created_at}` |
| C-145 | Aynı email ikinci kez gönderilir | **200** ile mevcut kayıt döner (idempotent; duplicate satır oluşmaz) |
| C-146 | Geçersiz email ("abc", "a@b") | 422 |
| C-147 | `" A@B.CoM "` gönderilir | Normalize edilir → `a@b.com`; sonraki `a@b.com` duplicate sayılır |
| C-148 | Auth'suz istek; `plan` opsiyonel | 201 — JWT gerekmez |

### N. Admin

| ID | Verilen durum | Beklenen sonuç |
|----|----------------|----------------|
| C-149 | `tier=free` veya `premium` kullanıcı `GET /admin/stats` | 403 "Admin access required" |
| C-150 | Auth'suz `GET /admin/stats` | 403 (bearer yok) |
| C-151 | `tier=admin` kullanıcı | 200: `users`, `profiles`, `exchange_keys`, `active_share_links`, `exchanges` (borsa dağılımı), `tiers` (tier dağılımı) |
| C-152 | Revoked linkler varken stats | `active_share_links` yalnız `is_active=true` olanları sayar |

### O. Tier Limitleri

| ID | Verilen durum | Beklenen sonuç |
|----|----------------|----------------|
| C-153 | `free` kullanıcı | Max **1 profil** (2.si → 403, C-018) |
| C-154 | `free` kullanıcı | Profil başına max **2 distinct exchange** (3.sü → 403, C-031); aynı borsanın read_only+trade çifti 1 sayılır |
| C-155 | `premium` kullanıcı | Profil ve exchange sınırsız (-1) |
| C-156 | Tanımsız/bozuk tier değeri | Free limitlerine fallback |
| C-157 | EDGE: `tier=admin` kullanıcı profil/key limiti | `TIER_LIMITS`'te "admin" yok → **free limitlerine düşer** (muhtemel istenmeyen davranış; test pinlemeli / karar) |

### P. Güvenlik (Cross-Cutting)

| ID | Verilen durum | Beklenen sonuç |
|----|----------------|----------------|
| C-158 | Tüm endpoint response'ları taranır (keys, portfolio, share, trade, admin) | Hiçbirinde plaintext api_key/api_secret yok |
| C-159 | Uygulama logları taranır (key ekleme, portfolio fetch, trade) | Plaintext key/secret/JWT loglanmaz; yalnız id'ler ve maskelenmiş key (`abc123...`) |
| C-160 | `ENCRYPTION_KEY` veya `JWT_SECRET` env'siz başlatma | Uygulama başlamaz (pydantic-settings required field hatası) |
| C-161 | Key rotasyonu: eski `ENCRYPTION_KEYS` ile şifrelenmiş secret | MultiFernet ile decrypt edilir; yeni yazımlar her zaman primary key ile şifrelenir |
| C-162 | Üretilen share token'lar | `token_urlsafe(32)` = 256-bit entropi; DB'de unique |
| C-163 | Yapılandırılmamış origin'den CORS isteği | Reddedilir (yalnız `CORS_ORIGINS` + `FRONTEND_URL`) |
| C-164 | `read_only` key ile herhangi bir akış | Adapter yalnız GET/okuma çağrıları yapar; emir yerleştirme yolu trade key gerektirir (C-103) |
| C-165 | Frontend kodu ve network trafiği | API secret yalnız key-ekleme isteğinde frontend→backend gider; backend hiçbir zaman secret'ı frontend'e geri göndermez |

**Toplam: 165 koşul (C-001 … C-165).**

---

## 3. Fake / Demo Data Planı

Testler (pytest fixture'ları) ve UI demo ortamı için gereken veri seti. Exchange
çağrıları testte **mock'lanır** (respx/monkeypatch ile adapter yanıtları); gerçek
borsaya asla gidilmez.

### 3.1 Kullanıcılar

| Kullanıcı | tier | Amaç |
|-----------|------|------|
| `free@demo.test` (U1) | free | Tier limitleri (1 profil, 2 borsa), limit-dolu durumlar |
| `premium@demo.test` (U2) | premium | Çoklu profil, trade akışları, share linkler — ana demo kullanıcısı |
| `admin@demo.test` (U3) | admin | `/admin/stats`; ayrıca C-157 (admin'in profil limiti) |
| `empty@demo.test` (U4) | free | Hiç profil yok — empty state / onboarding |
| `attacker@demo.test` (U5) | free | İzolasyon testleri: U1/U2 kaynaklarına 403/404 beklenir |

### 3.2 Profiller ve Key Kombinasyonları

| Profil | Sahip | Key'ler | Amaç |
|--------|-------|---------|------|
| P1 "Main" | U1 | binance `read_only` + bybit `read_only` | Free exchange limiti dolu (3. borsa → 403); read-only dashboard |
| P2 "Trading" | U2 | binance `read_only` + binance `trade` + okx `read_only` | Aynı borsada çift key; owner trade; share+delegate trade kaynağı |
| P3 "Kraken Spot" | U2 | kraken `trade` (read_only yok) | Yalnız trade key'li profil; trade var/bakiye akışı ayrı |
| P4 "Boş Profil" | U2 | key yok | "No API keys added yet" durumu; portföy 0 |

Mock bakiyeler (P2/binance): BTC 0.5, ETH 2.0, USDT 1_000, ayrıca Binance'te
listelenmeyen düşük hacimli 1 coin (CoinGecko fallback testi, C-053) ve 0 bakiyeli
1 asset (C-081).

### 3.3 Share Link Kombinasyonları (hepsi P2 üzerinde)

| Link | Bayraklar / alanlar | Amaç |
|------|---------------------|------|
| SL1 | default'lar (total+alloc açık), expiry yok, label "Muhasebeci" | Temel public view |
| SL2 | 4 bayrak da **true**, expiry +7 gün, allow_follow=T | Tam görünürlük + expiry yaklaşan |
| SL3 | 4 bayrak da **false** | Maksimum maskeleme (yalnız asset adları) |
| SL4 | expires_at **geçmişte** | 410 testi (C-073, C-097) |
| SL5 | is_active=false (revoked) | 404 testi (C-072) |
| SL6 | allow_follow=false | Follow 403 (C-090) |
| SL7 | can_trade=T, direction=both, whitelist "BTC,ETH", max_per_order=500, daily=2000 | Tüm delegate limitlerinin ana senaryosu |
| SL8 | can_trade=T, direction=**buy**, limitler null | Yön ihlali + limitsiz davranış |
| SL9 | can_trade=T, direction=**sell** | Ters yön ihlali |
| SL10 | can_trade=T + expires_at geçmiş | Expired linkle trade → 410 |
| SL11 | view_count>0, last_viewed_at dolu | Owner panelinde sayaç görünümü |

Not: `can_trade=true` linkler ancak P2'ye trade key eklendikten **sonra**
oluşturulabilir (C-061) — seed sırası buna göre kurulmalı.

### 3.4 Trade Geçmişi Senaryoları (P2, `trade_orders`)

| # | Kayıt | Amaç |
|---|-------|------|
| T1 | buy 0.001 BTC / $100, owner, filled, 10 gün önce | AVCO taban |
| T2 | buy 0.001 BTC / $200, owner, filled, 8 gün önce | avg_cost=150 senaryosu |
| T3 | sell 0.001 BTC / $300, owner, filled, 5 gün önce | realized +$150 (C-132) |
| T4 | buy ETH / $400, **delegate (SL7)**, filled, 2 saat önce | 24s harcama = 400 |
| T5 | buy ETH / $300, delegate (SL7), **failed**, 1 saat önce | Failed 24s'e sayılmaz (C-113/115) |
| T6 | buy BTC / $1500, delegate (SL7), filled, **25 saat önce** | Pencere dışı — sayılmaz (C-113) |
| T7 | sell 5 SOL / $500, owner, filled (SOL hiç alınmamış) | Over-sell clamp (C-134) |
| T8 | buy DOGE / $50, delegate (**SL8**), filled, 3 saat önce | Link bazlı izolasyon: SL7'nin harcamasına karışmaz |

Bu setle: SL7 için `trade_spent_today_usd=400`; $1601+ yeni delegate emri daily
limitten 403; tam $1600 emir geçer (C-111/112).

### 3.5 Snapshot / History / Waitlist

- P2 için 30 gün boyunca günde 1 `PortfolioSnapshot` (artan trend: 8.000→12.500 USD) + son 30 dk içinde 1 kayıt (throttle testi C-142).
- P1 için yalnız 3 nokta (kısa geçmiş grafiği); P4 için hiç (boş grafik durumu).
- Waitlist: `existing@demo.test` kayıtlı (duplicate→200 testi C-145).

---

## 4. UI Doğrulama Listesi

### /login
- "Sign in with Google" butonu `{API}/api/v1/auth/google`'a gider.
- `?error=auth_failed` ile gelindiğinde hata mesajı görünür.

### /auth/callback
- `?token=...` varsa localStorage'a yazılır → `/dashboard`'a replace; token yoksa `/login?error=auth_failed`.

### /dashboard
- localStorage'da token yoksa `/login`'e redirect.
- İlk girişte OnboardingWizard açılır (`onboarding_done` yazılınca bir daha açılmaz).
- ProfileSwitcher: "Aggregate" + kullanıcının profilleri; seçim değişince veri yeniden yüklenir.
- PortfolioSummary: toplam USD (aggregate'te `grand_total_usd`); tekil profil görünümünde `cached` göstergesi.
- PortfolioHistoryChart: yalnız tekil profil seçiliyken dolu (aggregate'te profileId=null); gün aralığı seçimi history endpoint'ini çağırır.
- AllocationChart (pie) + ExchangeList yan yana; exchange listesinde borsa başına bakiyeler/USD.
- "Realized P&L" tablosu: asset, qty, avg cost, +yeşil/−kırmızı realized, B/S sayıları; **kısmi veri (yalnız CoinHQ işlemleri)** notu.
- "Recent Trades": son emirler; delegate/owner ve filled/failed ayırt edilebilir.
- Hata durumu: kırmızı `role=alert` banner; yüklenirken skeleton; hiç profil yoksa Settings'e link veren empty state.

### /settings
- Profil CRUD: "Add Profile" modal; free limitte 403 gelince **UpgradeBanner** görünür; silmede ConfirmModal ("cannot be undone").
- Her profil kartında key listesi: borsa adı + **Read-only / Trade rozeti** + eklenme tarihi; secret hiçbir yerde görüntülenmez; "Remove" onaylı siler.
- AddKeyModal: 7 borsa seçeneği (binance, binancetr, bybit, okx, coinbase, kraken, gateio), key_type seçimi, borsa API sayfası linkleri; read_only'de write-permission hatası, trade'de withdrawal hatası kullanıcıya aynen gösterilir.
- Owner TradePanel **yalnız** profilde trade key varsa görünür (yoksa hiç render edilmez); buy/sell toggle, asset, USD tutar; sonuç satırı "Order filled: buy BTC for $X" / hata `role=alert`.
- ShareLinkManager: profil filtresi; her linkte label/kısaltılmış URL, expiry, **view_count** ("N views") ve last viewed, açık bayrakların özeti ("total, %"), can_trade için amber "Trade" rozeti; Copy URL; "Trade" edit modalı (PATCH — trade key yoksa can_trade açılamaz/400 gösterilir); Revoke onaylı ve liste anında güncellenir; yeni link oluşturulunca tam URL kopyalanabilir kutuda gösterilir.

### /share/[token] (public)
- Geçersiz/revoked/expired token → "Link not available — expired, revoked, or does not exist" sayfası.
- Header: allow_follow=true ise FollowButton; "Trading enabled" (amber) veya "Read-only view" rozeti.
- Toplam kartı: `show_total_value=false` iken "—" + "Total value is hidden by the link owner" notu.
- Tablo: Amount sütunu yalnız `show_coin_amounts`, Allocation sütunu yalnız `show_allocation_pct` açıkken render edilir; `show_exchange_names=false` iken başlıklar "Exchange xxxxxxxx".
- `can_trade=true` → DelegateTradePanel: limit özeti (Allowed coins, Max per order, "24h limit: $X (used $Y)"), yön kısıtında tek taraflı buton ("buy only"); backend 403 mesajları (yön/whitelist/limit) panelde aynen görünür; "Withdrawals are never possible" metni.
- Sıfır bakiyeli asset görünmez; footer "read-only shared view / API secrets are never exposed" + CoinHQ CTA.
- FollowButton: JWT yoksa "Sign in to follow" akışı; başarıda "Added to your portfolio".
- EDGE: sayfa ISR ile 300 sn revalidate — revoke/expiry sonrası public sayfa 5 dk'ya kadar stale görünebilir; API yine 404/410 döndüğü için trade/follow çalışmaz (bilinen davranış, testte doğrulanmalı).

### /pricing + WaitlistForm
- Plan kartları; "Join waitlist" formu: geçersiz email inline hata; başarıda teşekkür durumu; aynı email tekrar gönderilince "already subscribed" davranışı (backend 200 duplicate).

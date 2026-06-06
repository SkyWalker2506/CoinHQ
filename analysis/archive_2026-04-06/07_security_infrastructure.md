## Security & Infrastructure Analiz Raporu
> Lead: SecLead (A13) | Model: Opus 4.6 | Tarih: 2026-04-05

---

### Mevcut Durum

**Guvenlik mimarisi ozeti:**
- Fernet (AES-256-CBC) ile exchange API key sifreleme (`security.py`)
- SQLAlchemy ORM ile parametrik sorgular (SQL injection koruması)
- Pydantic model validasyonu (input sanitization)
- slowapi ile rate limiting (portfolio: 10/min, public share: 30/min)
- CORS whitelist konfigurasyonu
- Share link: `secrets.token_urlsafe(32)` ile kriptografik token uretimi
- Exchange key response'da plaintext key/secret DONMUYOR (`ExchangeKeyRead` modeli)
- Encrypted key DB'de saklanıyor, log'a yazılmıyor

**Guclu yanlar:**
- Encryption-at-rest dogru implemente edilmis
- ORM kullanimi SQL injection'i buyuk olcude onluyor
- Rate limiting mevcut
- Response model'ler hassas veriyi filtreleyen ayri schema kullaniyor
- Share link token'lari kriptografik guvenli (32 byte urlsafe)
- Share link expiry ve revoke mekanizmasi var

**Puan: 4/10**

> Ciddi eksikler: Auth/authz YOK, JWT henuz implemente degil, Google OAuth sadece planda. Tum endpoint'ler acik.

---

### OWASP Top 10 Degerlendirmesi

| # | Zafiyet | Durum | Risk | Onlem |
|---|---------|-------|------|-------|
| A01 | Broken Access Control | **AUTH YOK** — tum endpoint'ler anonim erisime acik | **Critical** | `get_current_user` dependency henuz implemente edilmemis; herhangi biri herkesin profil/key/portfolio'suna erisebilir |
| A02 | Cryptographic Failures | Fernet encryption dogru ama key rotation yok | **Medium** | ENCRYPTION_KEY tek statik key; rotation mekanizmasi planlanmali |
| A03 | Injection | SQLAlchemy ORM parametrik sorgular kullanıyor | **Low** | Mevcut durum yeterli; raw SQL kullanilmadigi surece guvenli |
| A04 | Insecure Design | Multi-user izolasyonu (user_id filter) henuz yok | **Critical** | Auth olmadan user_id scope'u anlamsiz; auth gelince `profile.user_id == current_user.id` enforce edilmeli |
| A05 | Security Misconfiguration | `DEBUG=False` default, CORS whitelist var | **Low** | `allow_methods=["*"]` ve `allow_headers=["*"]` daraltilabilir |
| A06 | Vulnerable Components | Dependency'ler guncel (2024 surumler) | **Low** | Duzgun; periyodik `pip-audit` eklenmeli |
| A07 | Auth Failures | JWT/OAuth implemente DEGIL | **Critical** | `.env.example`'da JWT_SECRET ve Google OAuth var ama kodda kullanilmiyor |
| A08 | Software & Data Integrity | Alembic migration yerine `create_all` kullaniliyor | **Medium** | Prod'da Alembic migration'a gecilmeli |
| A09 | Logging & Monitoring | Logging mekanizmasi yok | **Medium** | Structured logging (audit trail) eklenmeli |
| A10 | SSRF | Exchange API call'lari sabit URL'lere gidiyor | **Low** | URL user input'tan gelmiyor; guvenli |

---

### Kritik Aciklar (hemen kapatilmali)

| # | Sorun | Etki | Cozum | Efor |
|---|-------|------|-------|------|
| K1 | **Authentication tamamen eksik** — JWT ve Google OAuth kodda implemente degil | Herkes tum endpoint'lere anonim erisebilir; baskasinin API key'lerini gorebilir, silebilir, profil olusturabilir | JWT middleware + Google OAuth callback + `get_current_user` dependency implemente et; `.env.example`'daki JWT_SECRET/Google cred'leri kodda kullan | **High** (3-5 gun) |
| K2 | **Authorization (multi-user scope) yok** — profile'lar user_id'ye bagli degil | Auth gelse bile biri baskasinin profilini gorebilir | Profile modeline `user_id` FK ekle; her query'de `profile.user_id == current_user.id` filtrele | **Medium** (1-2 gun) |
| K3 | **Exchange API key read-only enforcement kodda yok** — `validate_key()` sadece key'in calisip calismadigini kontrol ediyor, write izni olup olmadigini KONTROL ETMIYOR | CLAUDE.md'de "write izni varsa KEY REDDEDILIR" diyor ama bu kural implemente edilmemis; kullanici write yetkili key ekleyebilir | Her exchange adapter'inda permission check ekle (Binance: `enableSpotAndMarginTrading` flag'i vb.) | **Medium** (2-3 gun) |
| K4 | **`keys` endpoint'leri auth-gated degil** — biri `GET /api/v1/profiles/1/keys/` ile herkesin encrypted key metadata'sini gorebilir, `DELETE` ile silebilir | Veri manipulasyonu ve bilgi sizintisi | Auth middleware eklenmesiyle birlikte cozulecek (K1) | K1 ile birlikte |

---

### Iyilestirme Onerileri

| # | Oneri | Etki | Cozum | Efor |
|---|-------|------|-------|------|
| I1 | Encryption key rotation mekanizmasi | Tek key compromise olursa tum veriler aciga cikar | Key versioning + re-encrypt migration script'i | Medium (2 gun) |
| I2 | Binance adapter'da `get_balances()` icinde `await` eksik | `resp = client.get(...)` sync cagri — runtime hatasi verecek | `resp = await client.get(...)` olarak duzelt | Low (5 dk) |
| I3 | CORS `allow_methods` ve `allow_headers` daraltilmali | Gereksiz genis erisim | Sadece `GET, POST, DELETE, OPTIONS` ve gerekli header'lar | Low (15 dk) |
| I4 | Structured logging ve audit trail | Guvenlik olaylari izlenemiyor | `structlog` veya `logging` ile auth event, key CRUD, share link islemlerini logla | Medium (1 gun) |
| I5 | `pip-audit` CI'a eklenmeli | Bilinen CVE'li dependency tespiti | GitHub Actions'a `pip-audit` step'i ekle | Low (30 dk) |
| I6 | HTTPS zorunlulugu / HSTS header | Man-in-the-middle riski | Prod'da reverse proxy (nginx/traefik) ile TLS enforce et | Low (yapilandirma) |
| I7 | Share link create/list/revoke endpoint'leri auth gerektirmiyor | Herkes baskasinin share link'ini revoke edebilir | Auth middleware ile kapat | K1 ile birlikte |

---

### Kesin Olmali (security standard)

1. **JWT Authentication** — Her korunmasi gereken endpoint `get_current_user` dependency kullanmali
2. **Google OAuth 2.0 flow** — Login/callback/token refresh implemente edilmeli
3. **User-scoped data isolation** — Profile, key, share link sorguları `user_id` filtreli olmali
4. **Read-only key enforcement** — Exchange API key ekleme sirasinda write permission kontrolu
5. **HTTPS/TLS** — Prod ortamda zorunlu

### Kesin Degismeli (mevcut riskler)

1. **Tum endpoint'ler su an anonim acik** — en buyuk ve en acil risk
2. **Binance adapter `await` eksigi** — runtime'da hata verecek (`I2`)
3. **Share link CRUD auth'suz** — herkes baskasinin link'ini yonetebilir
4. **`allow_methods=["*"]` CORS** — gereksiz genis

### Nice-to-Have (guvenlik derinlestirme)

1. Encryption key rotation ve versioning
2. API key usage audit log'u (hangi key ne zaman kullanildi)
3. IP-based rate limiting yerine user-based rate limiting (auth sonrasi)
4. Content Security Policy header'lari (frontend)
5. Dependency auto-update (Dependabot/Renovate)
6. Penetration test / SAST tooling (Bandit, Semgrep)

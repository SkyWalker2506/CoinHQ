## #10 Architecture & Code Quality Analiz Raporu
> Lead: CodeLead (A10) | Model: Sonnet

---

### Mevcut Durum

**Güçlü Yanlar:**
- Exchange adapter pattern doğru uygulanmış: `base.py` ABC → `binance.py`, `bybit.py`, `okx.py` implementasyonları; yeni exchange eklemek için sadece `ExchangeAdapter` implement et
- Katmanlı mimari var: `models/` → `schemas/` → `services/` → `api/` ayrımı temiz
- Pydantic v2 kullanılıyor, type-safety ön planda
- `asyncpg` + SQLAlchemy async — doğru teknoloji seçimi
- Alembic migration altyapısı kurulu
- `pyproject.toml` + `uv` — modern Python toolchain
- Ruff lint konfigürasyonu mevcut (`E, F, I, N, W, UP` kuralları)
- Security katmanı ayrı: `security.py` Fernet encrypt/decrypt, plaintext log yasağı belgelenmiş
- Docker Compose ile postgres + redis healthcheck var

**Puan: 5/10**

Mimari iskelet doğru, ancak auth tamamen eksik (Phase 1 gereksinimi olan Google OAuth yok), test altyapısı boş, birkaç kritik bug var ve frontend ile backend tip tanımları senkronize değil.

---

### Kritik Eksikler (hemen yapılmalı)

| # | Sorun | Etki | Çözüm | Efor |
|---|-------|------|-------|------|
| 1 | **Auth tamamen yok** — CLAUDE.md'de "Phase 1: Google OAuth" deniyor ama hiçbir endpoint'te auth dependency yok. Herkes tüm profilleri ve portfolio verilerini görebilir. `/profiles/` ve `/portfolio/` public | High | `get_current_user` dependency + Google OAuth 2.0 + JWT implementasyonu; tüm endpoint'lere ekle | L |
| 2 | **Multi-user yalıtımı yok** — `list_profiles`, `aggregate_portfolio` tüm kullanıcıların profillerini döndürüyor. `profile.user_id == current_user.id` filtresi yok | High | Auth tamamlanınca `user_id` FK model'e ekle, tüm sorguları filtrele | M |
| 3 | **Binance adapter `await` bug** — `binance.py:32` `resp = client.get(...)` `await` yok; coroutine çalıştırılmıyor, balance fetch sessizce boş dönebilir veya crash edebilir | High | `resp = await client.get(...)` | S |
| 4 | **Test altyapısı boş** — `pyproject.toml`'da `tests` testpath tanımlı ama test dosyası yok | Med | `tests/test_portfolio_service.py`, `tests/test_exchanges.py` ekle; mock ile exchange adapter test et | M |
| 5 | **`get_db` generator pattern yanlış** — `database.py:23` `get_db` hem `yield` hem `async with` kullanıyor ama `AsyncGenerator` return type tanımlı değil; FastAPI'nin dependency injection için doğru imza `AsyncGenerator[AsyncSession, None]` | Med | Return type annotation ekle: `async def get_db() -> AsyncGenerator[AsyncSession, None]` | S |

---

### İyileştirme Önerileri (planlı)

| # | Öneri | Etki | Çözüm | Efor |
|---|-------|------|-------|------|
| 1 | **`aggregate_portfolio` type hint gevşek** — `profiles: List[tuple]` tipi belirsiz; `List[tuple[Profile, List[ExchangeKey]]]` olmalı | Med | TypeAlias veya dataclass ile tip netleştir | S |
| 2 | **Frontend tip senkronizasyonu** — `frontend/src/lib/types.ts` manuel yazılmış, backend schema'dan üretilmiyor. Schema değişince frontend bozulabilir | Med | OpenAPI → TypeScript codegen ekle (`openapi-typescript` veya `orval`) | M |
| 3 | **Exchange factory error handling** — `factory.py` bilinmeyen exchange için muhtemelen `KeyError` veya `None` dönüyor; açık `ValueError` ile kullanıcıya net hata | Med | `raise ValueError(f"Unsupported exchange: {exchange}")` | S |
| 4 | **Docker volumes mount tehlikeli** — `docker-compose.yml:43` `./backend:/app` tüm backend dizinini mount ediyor; production'da kod değişiklikleri anında uygulanır, güvenlik riski | Med | Production compose'da volume mount'u kaldır, sadece dev'de kullan | S |
| 5 | **Fernet key her şifreleme/çözme işleminde yeniden oluşturuluyor** — `security.py:11` `_get_fernet()` her çağrıda `Fernet(...)` objesi kuruyor | Low | Module düzeyinde singleton: `_fernet = Fernet(settings.ENCRYPTION_KEY.encode())` | S |
| 6 | **`init_db` + Alembic çakışması** — `main.py:18` startup'ta `create_all` çağrılıyor; production'da Alembic varken `create_all` migration geçmişini bozabilir | Med | `DEBUG` modda tutulabilir ama production'da `init_db` devre dışı bırakılmalı | S |
| 7 | **Frontend'de API URL hardcode** — `api.ts:11` `"http://localhost:8000"` fallback; Docker'da frontend → backend iletişimi `NEXT_PUBLIC_API_URL` olmadan bozulur | Low | Default'u boş bırak, `.env.local.example`'a zorunlu alan olarak işaretle | S |
| 8 | **`hmac.new` → `hmac.new` deprecation** — `binance.py:19` Python 3.12'de `hmac.new` yerine `hmac.HMAC` tercih edilir; ruff `UP` kuralı zaten uyarıyor olmalı | Low | `hmac.new(...)` → `hmac.new(...)` değişim yok, ama type checker uyarısı kontrol et | S |

---

### Kesin Olmalı (industry standard)

- **Authentication + Authorization** — herhangi bir kullanıcı verisi sunan API'de auth zorunlu; exchange API key'leri çok hassas veri
- **Test coverage** — exchange adapter'lar ve portfolio service için en az unit test; mock exchange yanıtlarıyla
- **Type hints eksiksiz** — `List[tuple]` gibi gevşek tipler refüse edilmeli
- **CI pipeline** — `ruff check` + `pytest` + `pnpm lint` otomatik çalışmalı
- **Environment validation** — `ENCRYPTION_KEY` eksikse uygulama başlamasın (zaten var, ama `JWT_SECRET` de eklenince kontrol edilmeli)

### Kesin Değişmeli (mevcut sorunlar)

- `binance.py:32` `await` bug — production'da Binance balance fetch çalışmıyor
- Auth yokluğu — tüm kullanıcı verisi public, kabul edilemez
- `docker-compose.yml` production volume mount — kod dizini container'a mount edilmemeli
- `init_db` + Alembic çakışması — ikisi aynı anda çalışmamalı

### Nice-to-Have (diferansiasyon)

- **OpenAPI → TypeScript codegen**: backend şema değişince frontend otomatik güncellenir
- **Structured logging** (structlog/loguru): JSON formatında, trace ID ile; production observability
- **Health endpoint genişletme**: `/health` DB + Redis bağlantısını da kontrol etmeli (`db.execute("SELECT 1")`)
- **Exchange adapter test harness**: `AbstractExchangeAdapter` için fixture set; yeni exchange ekleyince testler koşsun
- **Makefile**: mevcut `Makefile` var, `make test`, `make lint`, `make migrate` gibi standart target'lar
- **Pre-commit hooks**: ruff + mypy otomatik; kötü kod commit'lenemez
- **`mypy` veya `pyright` strict mode**: tip güvenliği garanti altına alınsın

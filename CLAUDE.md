# CoinHQ — Claude Code

Genel kurallar (calisma tarzi, tool-first, maliyet, dil, model, hata yonetimi) `~/.claude/CLAUDE.md` ve ust dizin `CLAUDE.md`'den devralinir. Bu dosya **yalnizca projeye ozel** kurallari icerir.

---

## 1. Framework ve komutlar

- **Framework:** FastAPI (Python 3.12) + Next.js 14
- **Paket yoneticisi:** uv (backend), pnpm (frontend)
- **Test:** pytest (backend), pnpm test (frontend)
- **Lint:** ruff check . (backend), pnpm lint (frontend)

### Commit oncesi

```bash
uv run ruff check . → uv run pytest → pnpm lint → pnpm test
```

---

## 2. Jira

- **Proje anahtari:** COIN
- Detay: `docs/CLAUDE_JIRA.md`

---

## 3. Guvenlik kurallari

- Exchange API key/secret **ASLA** loglanmaz, commit edilmez, HTTP response'a yazilmaz
- DB'ye yazmadan once her zaman `security.py` encrypt fonksiyonu kullanilir
- `.env` dosyasi `.gitignore`'da; sadece `.env.example` commit edilir
- Frontend'den API secret **hicbir zaman** gonderilmez — yalnizca backend isler
- Read-only API key validasyonu: exchange'e baglantida write izni varsa KEY REDDEDILIR

## 4. Mimari notlar

- Multi-profile: her profil bir kisi/hesap seti — login yok, profil secici var
- Exchange adapter pattern: `backend/app/exchanges/` — yeni exchange eklemek icin sadece base.py implemente et
- Fiyat verisi: CoinGecko free API, Redis'te 60s cache
- Rate limiting: slowapi ile `/portfolio` endpoint'lerde

## 5. Notlar

- Phase 1 odak: dashboard + profil + API key yonetimi
- Trade/write izni Phase 2'ye kadar implemente edilmez

# Deployment Rehberi — Render + Supabase + Upstash + Vercel

## Mimari

```
Vercel (Frontend)  →  Render (Backend / FastAPI, Docker)  →  Supabase (PostgreSQL)
coinhq-app.vercel.app   https://<svc>.onrender.com          ↘  Upstash (Redis)
```

> Postgres = **Supabase**, Redis = **Upstash** (dış yönetilen). Render yalnızca backend compute.
> Bağlantı bilgileri `~/.claude/secrets/projects/coinhq.env` içinde.
> (Railway daha önce denendi; trial bitti → Render'a geçildi. `railway.toml` repoda referans olarak duruyor.)

---

## 0. Kod hazırlığı (deploy'u bloke eden noktalar — düzeltildi)

- `backend/app/core/config.py` → `DATABASE_URL` otomatik `postgresql+asyncpg://`'ye çevrilir.
- `backend/Dockerfile` → uv ile build, `alembic upgrade head` + uvicorn `--proxy-headers`, `$PORT` dinler.
- `render.yaml` → Docker web service, `healthCheckPath: /health`, free plan.

---

## 1. Supabase (Postgres) — IPv4 Session Pooler

Render egress **IPv4**; Supabase *direct* host (`db.<ref>.supabase.co`) IPv6-only.
Bu yüzden **Session Pooler** connection string'i kullanılır (IPv4):

```
DATABASE_URL=postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres
```
- Supabase → Project Settings → Database → **Connection string → Session pooler**.
- Parola `[...]` parantezi İÇİNDE olmamalı (Supabase placeholder'ı çıplak parola ile değiştirilir).
- `+asyncpg` eklemek gerekmez (kod ekler).

## 2. Upstash (Redis)

```
REDIS_URL=rediss://default:<token>@<host>.upstash.io:6379
```
`rediss://` (TLS) — `redis.asyncio.from_url` native destekler.

---

## 3. Render — Backend

### 3.1 Servis oluştur

Repo public; iki yol:
- **Dashboard:** New → **Blueprint** → CoinHQ repo'yu seç → `render.yaml` okunur.
- **veya API** (`RENDER_API_KEY` ile): Docker web service, `repo=…/CoinHQ`, `branch=main`, `dockerfilePath=./backend/Dockerfile`, `dockerContext=./backend`.

### 3.2 Environment variables (Render → Environment)

```
DATABASE_URL=<supabase session pooler url>     # §1
REDIS_URL=<upstash rediss url>                 # §2
ENCRYPTION_KEY=<fernet-key>                     # python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
JWT_SECRET=<openssl rand -hex 32>
GOOGLE_CLIENT_ID=<google-client-id>            # mevcut client (backend/.env) yeniden kullanılabilir
GOOGLE_CLIENT_SECRET=<google-client-secret>
BACKEND_URL=https://<svc>.onrender.com         # ilk deploy + URL belli olunca set et
FRONTEND_URL=https://coinhq-app.vercel.app
CORS_ORIGINS=["https://coinhq-app.vercel.app"]
DEBUG=false
```

### 3.3 Notlar
- `/health` DB+Redis kontrol eder → bağlantılar boot'ta çalışmalı yoksa healthcheck düşer.
- Free web service 15 dk inaktivite sonrası uyur (ilk istek ~50s cold start).

---

## 4. Google OAuth

Mevcut OAuth client yeniden kullanılır; sadece prod redirect URI eklenir:
1. console.cloud.google.com → Credentials → Web client → **Authorized redirect URIs → Add**:
   ```
   https://<svc>.onrender.com/api/v1/auth/google/callback
   ```
   (`BACKEND_URL` ile birebir aynı host.)

---

## 5. Vercel — Frontend

`NEXT_PUBLIC_*` **build-time** gömülür → deploy'dan önce set et:
```bash
echo "https://<svc>.onrender.com" | vercel env add NEXT_PUBLIC_API_URL production
vercel --prod --yes
```
Not: proje "Deployment Protection" açıksa public erişim için kapat (Vercel → Settings → Deployment Protection).

---

## 6. Sıra

1. Supabase pooler URL + Upstash URL hazırla (§1, §2)
2. Render servisini oluştur + env var'ları gir (`BACKEND_URL` hariç) → ilk deploy
3. `onrender.com` URL'i al → `BACKEND_URL` + `CORS_ORIGINS` güncelle → redeploy
4. Google Console'a prod redirect URI ekle (§4)
5. Vercel `NEXT_PUBLIC_API_URL` = Render URL → `vercel --prod`; Deployment Protection'ı kapat
6. Test: `https://coinhq-app.vercel.app` → Google login → dashboard

---

## 7. Ücretsiz tier

| Servis | Ücretsiz |
|--------|----------|
| Vercel | Sınırsız deploy, 100GB bandwidth/ay |
| Render | 750 saat/ay web service (15dk sonra uyur) |
| Supabase | 500MB DB |
| Upstash | 256MB, 500K komut/ay |

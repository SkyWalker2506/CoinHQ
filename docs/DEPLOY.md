# Deployment Rehberi — Railway + Vercel

## Mimari

```
Vercel (Frontend)  →  Railway (Backend)  →  Railway (PostgreSQL + Redis)
https://coinhq.vercel.app    https://coinhq-backend.railway.app
```

---

## 1. Railway — Backend + Veritabanı

### 1.1 Proje oluştur

1. https://railway.app → **New Project → Deploy from GitHub repo**
2. Repo seç: `CoinHQ`
3. Railway otomatik `railway.toml`'u okur → backend deploy eder

### 1.2 PostgreSQL ve Redis ekle

Railway dashboard'da **New Service** ile:
- **PostgreSQL** plugin ekle → `DATABASE_URL` otomatik set edilir
- **Redis** plugin ekle → `REDIS_URL` otomatik set edilir

### 1.3 Backend environment variables

Railway → Backend service → **Variables** tabı:

```
ENCRYPTION_KEY=<fernet-key>        # python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
JWT_SECRET=<random-32-hex>         # openssl rand -hex 32
GOOGLE_CLIENT_ID=<google-client-id>
GOOGLE_CLIENT_SECRET=<google-client-secret>
FRONTEND_URL=https://coinhq.vercel.app
CORS_ORIGINS=["https://coinhq.vercel.app"]
```

`DATABASE_URL` ve `REDIS_URL` plugin'ler tarafından otomatik eklenir.

### 1.4 Railway domain al

Railway → Backend → **Settings → Networking → Generate Domain**  
Örnek: `coinhq-backend.up.railway.app`

---

## 2. Google OAuth

1. https://console.cloud.google.com → **APIs & Services → Credentials → Create OAuth Client ID**
2. Application type: **Web application**
3. Authorized redirect URIs:
   ```
   https://coinhq-backend.up.railway.app/api/v1/auth/google/callback
   ```
4. Client ID ve Secret'ı Railway variables'a ekle

---

## 3. Vercel — Frontend

### 3.1 Deploy

1. https://vercel.com → **New Project → Import Git Repository**
2. Root directory: `frontend`
3. Framework: **Next.js** (otomatik algılar)

### 3.2 Environment variables

Vercel → Project → **Settings → Environment Variables**:

```
NEXT_PUBLIC_API_URL=https://coinhq-backend.up.railway.app
```

### 3.3 Domain

Vercel ücretsiz domain: `coinhq.vercel.app`  
Kendi domain için: **Settings → Domains → Add**

---

## 4. Sıra önemli

1. Railway'de backend deploy et → domain al
2. Google Console'a redirect URI ekle
3. Railway'e Google credentials ekle
4. Vercel'e `NEXT_PUBLIC_API_URL` ekle → frontend deploy et
5. Test: `https://coinhq.vercel.app`

---

## 5. Ücretsiz tier limitleri

| Servis | Ücretsiz |
|--------|----------|
| Vercel | Sınırsız deploy, 100GB bandwidth/ay |
| Railway | $5 credit/ay (~500 saat compute) |
| Railway PostgreSQL | 1GB storage |
| Railway Redis | 256MB |

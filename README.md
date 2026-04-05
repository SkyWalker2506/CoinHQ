# CoinHQ — Multi-User Crypto Portfolio Tracker

> Self-hosted crypto portfolio dashboard with Google authentication. Track your portfolios across Binance, Bybit, and OKX — each user sees only their own data. Share read-only portfolio links with anyone.

---

## What is CoinHQ?

CoinHQ is a **self-hosted, multi-user** dashboard for tracking crypto portfolios across multiple exchanges.

- Sign in with **Google** — no passwords
- Add **profiles** (e.g. Binance Main, Bybit Trading)
- Each profile holds encrypted read-only API keys
- View per-profile or **aggregate** portfolio across all your profiles
- Generate **public share links** for read-only portfolio views (no login required for viewers)

---

## User & Profile Model

```
Google Login → User Account
              ├── Profile: "Binance Main"
              │   ├── Binance API Key (read-only)
              │   └── Bybit API Key (read-only)
              └── Profile: "OKX Trading"
                  └── OKX API Key (read-only)

Views:
  - Switch to "Binance Main" → see that profile's portfolio
  - Aggregate → see all your profiles combined
  - Share link → public read-only view (configurable visibility)
```

Each user can only see and manage their own profiles. Profiles are isolated per Google account.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Next.js Frontend                        │
│  /login (Google OAuth)  →  /dashboard  →  /settings        │
│  ProfileSwitcher → PortfolioSummary → AllocationChart       │
│  ShareLinkManager → CreateShareLinkModal                    │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP (REST) + Bearer JWT
┌────────────────────▼────────────────────────────────────────┐
│                     FastAPI Backend                          │
│  /api/v1/auth/google   (OAuth callback, JWT issue)          │
│  /api/v1/profiles      (user-scoped CRUD)                   │
│  /api/v1/keys          (encrypted API key management)       │
│  /api/v1/portfolio     (rate limited, cached)               │
│  /api/v1/share         (link management, auth required)     │
│  /api/v1/public/share  (public read-only, no auth)         │
│                                                              │
│  PortfolioService → ExchangeAdapters (Binance/Bybit/OKX)   │
└──────┬──────────────────────┬───────────────────────────────┘
       │                      │
┌──────▼──────┐    ┌──────────▼──────┐
│ PostgreSQL  │    │     Redis        │
│ users       │    │  60s balance     │
│ profiles    │    │  cache           │
│ enc. keys   │    └─────────────────┘
│ share_links │
└─────────────┘
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.12), SQLAlchemy (async), Alembic |
| Frontend | Next.js 14 (App Router), Tailwind CSS |
| Auth | Google OAuth 2.0 + JWT (python-jose) |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| Encryption | Python `cryptography` (Fernet/AES-256) |
| Charts | Recharts |
| Rate Limiting | `slowapi` |
| Containerization | Docker + Docker Compose |

---

## Security Model

### Authentication
- Google OAuth 2.0 — no passwords stored
- JWT tokens (7-day expiry), signed with `JWT_SECRET`
- Every protected endpoint validates the token via `get_current_user` dependency
- Users can only access their own profiles and keys

### API Key Storage
- Exchange API keys are **never stored in plaintext**
- Keys are encrypted with **AES-256 (Fernet)** before writing to the database
- The master encryption key lives in `ENCRYPTION_KEY` env var — never in the database

### Read-Only Enforcement
- Only read-only API key scopes are accepted
- Exchange adapters only call `GET` endpoints — no order placement
- Key validation rejects keys with write permissions

### Share Links
- Public share links expose only what the owner explicitly allows (via `show_*` flags)
- Links can have an optional expiry date
- Raw key/secret values never appear in any share response

### What is NOT logged
- Raw API keys or secrets
- JWT tokens
- Decrypted values only exist in-memory during exchange API calls

---

## Setup Instructions

### Prerequisites
- Docker & Docker Compose
- A Google Cloud project with OAuth 2.0 credentials

### 1. Clone and configure

```bash
git clone https://github.com/SkyWalker2506/CoinHQ
cd CoinHQ
cp .env.example .env
```

Edit `.env`:
```bash
# Generate with: python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=your-fernet-key

# Generate with: openssl rand -hex 32
JWT_SECRET=your-jwt-secret

DATABASE_URL=postgresql+asyncpg://coinhq:coinhq@postgres:5432/coinhq
REDIS_URL=redis://redis:6379/0
CORS_ORIGINS=http://localhost:3000
FRONTEND_URL=http://localhost:3000

# From Google Cloud Console → APIs & Services → Credentials
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 2. Google OAuth setup

1. Go to [Google Cloud Console](https://console.cloud.google.com) → APIs & Services → Credentials
2. Create an **OAuth 2.0 Client ID** (Web application)
3. Add Authorized redirect URI: `http://localhost:8000/api/v1/auth/google/callback`
4. Copy Client ID and Client Secret into `.env`

### 3. Start services

```bash
make dev
# or: docker-compose up --build
```

### 4. Run migrations

```bash
make migrate
# or: docker-compose exec backend alembic upgrade head
```

### 5. Open the app

- Frontend: http://localhost:3000
- Backend API docs: http://localhost:8000/docs

### 6. Sign in and add your first profile

1. Go to http://localhost:3000 → click **Sign in with Google**
2. After login → **Settings** → **Add Profile**
3. Add a name (e.g. "Binance Main")
4. Click **Add API Key**, select exchange, paste your read-only key and secret
5. Go to **Dashboard** — your portfolio loads

---

## Share Links

Portfolio owners can create public share links from Settings:

- Choose which data to expose: total value, coin amounts, exchange names, allocation %
- Optional expiry date
- Viewers open the link without any login — read-only, filtered view

---

## Roadmap

| Phase | Goal | Key Features |
|-------|------|-------------|
| Phase 1 | MVP | Google Auth, dashboard, multi-exchange read-only, share links |
| Phase 2 | Delegated Access | Grant view/trade permissions to other users |
| Phase 3 | Advanced Analytics | PnL, trade history, charts, Telegram notifications |
| Phase 4 | AI Layer | Insight suggestions, trend analysis, Q&A |
| Phase 5 | Premium | Trade automation (opt-in), smart alerts |

### Milestone Checklist

- [ ] Phase 1 complete → MVP launch
- [ ] Phase 2 complete → Delegated access
- [ ] Phase 3 complete → Analytics + notifications
- [ ] Phase 4 complete → AI insights
- [ ] Phase 5 complete → Premium features

---

> **Vision:** "See, understand, and prepare to manage your entire crypto portfolio from one place."

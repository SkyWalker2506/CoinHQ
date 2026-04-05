# CoinHQ — Multi-Profile Crypto Portfolio Tracker

> Self-hosted, read-only crypto portfolio dashboard. Track multiple people's portfolios across Binance, Bybit, and OKX in one app — no logins, no OAuth, no SaaS overhead.

---

## What is CoinHQ?

CoinHQ is a **local/self-hosted** dashboard for tracking crypto portfolios across multiple exchanges. It is **not** a multi-tenant SaaS with user accounts. Instead, it works like a profile switcher:

- You add **profiles** (e.g. Musab, Ali, Ayşe)
- Each profile has its own exchange API keys
- Switch between profiles to see each person's portfolio
- Or view an **aggregate view** of all profiles combined

There is no authentication system. Profiles are simply named sets of encrypted API keys. This is designed to run on a private server or locally.

---

## Multi-Profile Model

```
CoinHQ App
├── Profile: Musab
│   ├── Binance API Key (read-only)
│   └── Bybit API Key (read-only)
├── Profile: Ali
│   └── OKX API Key (read-only)
└── Profile: Ayşe
    ├── Binance API Key (read-only)
    └── OKX API Key (read-only)

Views:
  - Switch to "Musab" → see Musab's portfolio
  - Switch to "Ali" → see Ali's portfolio
  - Aggregate → see all portfolios combined
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Next.js Frontend                      │
│  ProfileSwitcher → PortfolioSummary → AllocationChart   │
│  AddProfileModal → AddKeyModal → ExchangeList           │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP (REST)
┌────────────────────▼────────────────────────────────────┐
│                   FastAPI Backend                        │
│  /api/v1/profiles  /api/v1/keys  /api/v1/portfolio      │
│                                                          │
│  PortfolioService → ExchangeAdapters                    │
│  (Binance / Bybit / OKX)                               │
└──────┬──────────────────────┬───────────────────────────┘
       │                      │
┌──────▼──────┐    ┌──────────▼──────┐
│ PostgreSQL  │    │     Redis        │
│ (profiles,  │    │  (60s balance   │
│  enc. keys) │    │   cache)        │
└─────────────┘    └─────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.12), SQLAlchemy (async), Alembic |
| Frontend | Next.js 14 (App Router), Tailwind CSS, shadcn/ui |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| Encryption | Python `cryptography` library (Fernet/AES-256) |
| Exchange SDKs | `python-binance`, `pybit`, `python-okx` |
| Charts | Recharts |
| Rate Limiting | `slowapi` (FastAPI) |
| Containerization | Docker + Docker Compose |

---

## Security Model

### API Key Storage
- Exchange API keys are **never stored in plaintext**
- Keys are encrypted with **AES-256 (Fernet)** before being written to the database
- The encryption master key is stored as an environment variable (`ENCRYPTION_KEY`) — never in the database
- Encrypted tokens are stored as base64 strings in PostgreSQL

### Read-Only Enforcement
- Only read-only API key scopes are accepted (balance queries, no trading)
- Exchange adapters only call `GET` endpoints (no order placement)
- Key validation confirms read-only permissions before saving

### Transport Security
- HTTPS in production (configure reverse proxy — Nginx/Caddy)
- CORS restricted to configured origins
- Rate limiting on portfolio endpoints (slowapi)

### What is NOT logged
- Raw API keys or secrets are never logged
- Decrypted values only exist in-memory during exchange API calls

---

## Setup Instructions

### Prerequisites
- Docker & Docker Compose
- `make` (optional, for convenience)

### 1. Clone and configure

```bash
git clone https://github.com/SkyWalker2506/CoinHQ
cd CoinHQ
cp .env.example .env
```

Edit `.env`:
```bash
# Generate encryption key: python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=your-generated-fernet-key

DATABASE_URL=postgresql+asyncpg://coinhq:coinhq@postgres:5432/coinhq
REDIS_URL=redis://redis:6379/0
CORS_ORIGINS=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 2. Start services

```bash
make dev
# or: docker-compose up --build
```

### 3. Run migrations

```bash
make migrate
# or: docker-compose exec backend alembic upgrade head
```

### 4. Open the app

- Frontend: http://localhost:3000
- Backend API docs: http://localhost:8000/docs

### 5. Add your first profile

1. Go to **Settings** → click **Add Profile**
2. Enter a name (e.g. "Musab")
3. Click **Add API Key**, select exchange, paste your read-only API key and secret
4. Go to **Dashboard** — your portfolio will load

---

## 🚀 Roadmap

| Phase | Duration | Goal | Features | Notes |
|-------|----------|------|----------|-------|
| Phase 1 | 1–2 weeks | MVP Launch | Dashboard, Multi-exchange read-only, Portfolio view, API key integration | Fast launch, collect feedback |
| Phase 2 | 2–4 weeks | Advanced Analytics | Coin-level performance, PnL calculation, Trade history, Charts | Optional trade permissions toggle |
| Phase 3 | 4–6 weeks | AI Layer | Insight suggestions, Trend prediction, Q&A interface, Risk analysis | Requires Phase 2 data pipeline |
| Phase 4 | 6–8 weeks | Expansion & UX | Mobile responsive, Push notifications, Multi-currency support | UI/UX polish, retention features |
| Phase 5 | 8–12 weeks | Premium Features | Trade automation (opt-in), Portfolio comparison, Smart alerts | Beta users, marketing-ready |

### Milestone Checklist

- [ ] Phase 1 complete → MVP launch
- [ ] Phase 2 complete → Analytics dashboard
- [ ] Phase 3 complete → AI insights layer
- [ ] Phase 4 complete → Mobile UX & notifications
- [ ] Phase 5 complete → Premium features & marketing-ready

---

> **Vision:** "See, understand, and prepare to manage your entire crypto portfolio from one place."

# CoinHQ E2E — Demo-mode UI verification

Uçtan uca UI doğrulaması: gerçek tarayıcıda (Playwright) demo-mode backend +
seed data ile tüm akışları test eder ve `/tmp/e2e-shots` altına screenshot alır.

## Çalıştırma

```bash
# 1) Backend (demo mode + sqlite + redis)
cd backend
export DEMO_MODE=true DATABASE_URL='sqlite+aiosqlite:////tmp/coinhq-demo.db' \
  REDIS_URL='redis://localhost:6379/0' JWT_SECRET=dev-secret \
  ENCRYPTION_KEY="$(python -c 'from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())')"
uv run python scripts/seed_demo.py > /tmp/seed.json   # kullanıcılar + JWT + share token
uv run uvicorn app.main:app --port 8000 &

# 2) Frontend
cd ../frontend && pnpm build && pnpm start -p 3000 &

# 3) E2E
cd ../e2e && npm install && SEED_JSON=/tmp/seed.json node run-e2e.mjs
```

Ortam değişkenleri: `FRONTEND_URL` (default http://localhost:3000),
`SEED_JSON` (default /tmp/seed.json), `SHOT_DIR` (default /tmp/e2e-shots).

Kapsam: login, dashboard (toplam+chart+exchange listesi), settings (profil/key
rozetleri/share/owner trade), public share (open-trade paneli + limit reddi,
masked maskeleme, expired/revoked), pricing. 22 kontrol.

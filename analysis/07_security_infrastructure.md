# Security & Infrastructure Audit — CoinHQ
_Date: 2026-04-10 · Lead: SecLead (A13) · Model: Opus 4.6_

## Executive Summary

CoinHQ has **materially improved** since 2026-04-06: auth, tenant isolation, encryption, read-only key validation, structured logging, and Alembic migrations are all in place and correctly wired on every protected route. However, the recent COIN-3 / COIN-4 / COIN-5 work has introduced new high-impact issues, and several pre-existing weaknesses (OAuth state store, token-in-URL delivery, localStorage JWT, 24 h access TTL, absent HSTS/TrustedHost) remain. **Overall posture: 6.5 / 10** — good fundamentals, but the public share surface has a real data-leak bug and the COIN-4 "Sentry with scrubbing" claim is not met.

**Top 5 immediate actions:**
1. **Fix share-link visibility leak** — `public_share_view` returns `usd_value`, `total_usd`, and `profile_name` regardless of visibility flags (`backend/app/api/v1/share.py:208-243`). `show_total_value=False` is trivially reversible.
2. **Sentry PII scrubbing** — backend Sentry does **not exist** (grep: 0 matches); frontend Sentry has **no** `beforeSend` hook and will ship share tokens, referrers, and balance-bearing exceptions (`frontend/src/lib/sentry.ts:11-22`).
3. **Replace in-memory OAuth state store** — breaks CSRF on multi-replica / restart scenarios (`backend/app/api/v1/auth.py:29`).
4. **Shorten JWT access TTL + stop delivering tokens via URL + stop using localStorage** — current TTL is **1440 minutes** (`core/config.py:21`), token is passed through the query string in the OAuth callback (`auth.py:149-153`) and then stashed in `localStorage` (`frontend/src/app/auth/callback/page.tsx:10-13`).
5. **Add rate limits to `/auth/*`, `/admin/*`, `/profiles/*/keys/*`, `POST /share`** — currently only `/portfolio` and `/public/share` are limited.

## Delta vs 2026-04-06

| Area | Before | Now | Status |
|---|---|---|---|
| Auth (JWT + Google OAuth) | Missing | Implemented on every protected route | ✅ Fixed |
| Tenant isolation (`profile.user_id` filter) | Missing | Enforced in profiles, keys, portfolio, share, followed | ✅ Fixed |
| Read-only key enforcement | Missing | Binance/Bybit/OKX OK; Coinbase + Binance TR still no-op | 🟡 Partial |
| Binance `await` bug | Sync | Now `async with ... await client.get(...)` | ✅ Fixed |
| Share-link CRUD auth | Open | Auth-gated + ownership-checked | ✅ Fixed |
| CORS `allow_methods=["*"]` | Wide | `GET/POST/DELETE/OPTIONS/PATCH` | ✅ Fixed |
| Alembic migrations | Missing | Present; Railway runs `alembic upgrade head` | ✅ Fixed |
| Key encryption rotation | Single Fernet | `MultiFernet` helper defined but **unused** | 🟡 Half-done |
| Structured logging | Missing | structlog + JSON, never logs plaintext key | ✅ Fixed |
| Public share view (COIN-3) | N/A | **Visibility-flag leak (C-1)** | 🔴 New Critical |
| Sentry (COIN-4) | N/A | **Backend absent, frontend un-scrubbed (C-2)** | 🔴 New Critical |
| Admin endpoint (COIN-5) | N/A | Gated by `tier == "admin"` but no audit, no rate limit, weak column type | 🟠 New High |
| HSTS / TrustedHost / HTTPS redirect | Absent | Still absent | 🟠 Open |
| `pip-audit` in CI | Missing | Dev dep only; no CI workflow in repo | 🟡 Half-done |

## Threat Model (brief)

| Asset | Value | Primary threats |
|---|---|---|
| Exchange API keys (Fernet-encrypted at rest) | Critical — plaintext loss = fund-drain risk if any key is not truly read-only | DB dump, log leak, ENCRYPTION_KEY leak, write-capable key slipping past validation |
| JWTs | High — bearer = full account access | XSS via localStorage, Referer/browser history leak of callback URL, 24 h TTL, no revocation |
| Share-link tokens | Medium — public by design but must honour `show_*` flags | Link enumeration, hidden-field leak, view-count scrape |
| User PII (email, Google ID) | Medium | Admin endpoint, un-scrubbed Sentry, logs |
| Admin tier flag | High — full read across all tenants | DB-level role escalation, missing audit trail |

## Findings

### 🔴 Critical

#### C-1 — Share link visibility flags not enforced for `usd_value` / `total_usd` / `profile_name`
**Severity:** Critical (CVSS ~7.5 confidentiality)
**Location:** `backend/app/api/v1/share.py:208-243`

```python
for bal in ex.balances:
    ...
    assets.append(SharedAsset(
        asset=bal.asset,
        amount=bal.total if link.show_coin_amounts else None,
        usd_value=bal.usd_value,                 # ← always leaked
        allocation_pct=alloc_pct,
    ))
filtered_exchanges.append(SharedExchange(
    exchange_name=exchange_label,
    assets=assets,
    total_usd=ex.total_usd,                      # ← always leaked
))

return SharedPortfolioView(
    token=token,
    profile_name=profile.name,                   # ← always leaked
    total_usd=portfolio.total_usd if link.show_total_value else None,
    ...
)
```

**Impact:** A link with `show_total_value=False` still exposes per-asset `usd_value` and per-exchange `total_usd`; summing them reproduces the supposedly-hidden total. `show_coin_amounts=False` hides `amount` but the client can back-compute `amount = usd_value / public_price` (< 0.5 % error). `profile_name` — commonly containing PII / nicknames — is **always** returned, and is additionally indexed into OG metadata in `frontend/src/app/share/[token]/page.tsx:13`.

**Remediation:** Gate `usd_value`, `total_usd`, and `profile_name` on the appropriate flag; add a new `show_profile_name` flag (default False) to `ShareLink` model, `ShareLinkCreate`, and the UI; migrate existing rows to the safer default.

#### C-2 — Frontend Sentry has no PII scrubbing; backend Sentry does not exist
**Severity:** Critical
**Location:** `frontend/src/lib/sentry.ts:11-22`; `backend/app/main.py` (Sentry absent — `grep -ri sentry backend/` returns 0 matches)

```ts
Sentry.init({
  dsn,
  tracesSampleRate: 0.1,
  environment: process.env.NODE_ENV,
});
```

No `beforeSend`, no `beforeBreadcrumb`, no `denyUrls`, `sendDefaultPii` defaults on. Performance tracing is enabled (`0.1`) and will ship URLs — including `/share/<token>` and any referrer containing the OAuth callback `?token=…&refresh_token=…`. React error-boundary events will embed React props, which in this app carry portfolio balances and profile names.

CLAUDE.md hard rule: exchange keys never leak to logs. Sentry is effectively an external log sink; an un-scrubbed Sentry violates that rule even before any exception is thrown.

**Remediation:** Add a `beforeSend` that rewrites `/share/<token>` to `/share/<redacted>`, strips query strings from request/breadcrumb URLs, and drops `event.user.email`, `ip_address`, `cookies`, `authorization`. Set `tracesSampleRate: 0.0` until URL scrubbing is proven. Either wire a properly-scrubbed backend Sentry (if that was COIN-4's intent) or close the ticket as frontend-only.

#### C-3 — JWT delivered via query string → stored in `localStorage` → 24 h lifetime → no revocation
**Severity:** Critical (XSS chain)
**Locations:**
- `backend/app/core/config.py:21` — `JWT_ACCESS_EXPIRE_MINUTES: int = 1440`
- `backend/app/api/v1/auth.py:149-153` — token in redirect URL
- `frontend/src/app/auth/callback/page.tsx:10-13` — `localStorage.setItem('token', token)`
- `frontend/src/lib/api.ts:15,35` — `localStorage.getItem("token")`

```python
frontend_redirect = (
    f"{settings.FRONTEND_URL}/auth/callback"
    f"?token={access_token}&refresh_token={refresh_token}"
)
return RedirectResponse(url=frontend_redirect)
```

**Impact:** Three independently bad choices compound. Query-string tokens get logged in browser history, Referer headers to any resource loaded by the callback page, analytics, and Sentry. `localStorage` is fully JS-readable so any reflected/stored XSS exfiltrates the token. 24 h TTL with no `jti`, no revocation list, and no session table means a compromised token is active for a full day.

**Remediation:** Set `access_token` as a `HttpOnly; Secure; SameSite=Lax` cookie on the callback redirect; reduce access TTL to 15 min; add a `jti` claim checked against a Redis deny-list in `get_current_user`; rotate refresh on use; remove every `localStorage.getItem("token")` in the frontend and use `credentials: "include"`.

#### C-4 — In-memory OAuth `state` store breaks multi-instance deploys and restarts
**Severity:** Critical on Railway / any non-pinned-replica environment
**Location:** `backend/app/api/v1/auth.py:29`

```python
_oauth_states: dict[str, float] = {}
_STATE_TTL_SECONDS = 600
```

**Impact:** Any scale-out, blue/green deploy, or crash between `/auth/google` and `/callback` produces "Invalid OAuth state — possible CSRF attack" and 100 % login failure. Also not thread-safe across workers of the same process.

**Remediation:** Store state in Redis with TTL.

### 🟠 High

**H-1 — No rate limiting on `/auth/*`, `/admin/*`, `/profiles/*/keys/*`, `POST /share`.** Only `portfolio` (`10/min`) and `public_share_view` (`30/min`) are limited. Brute-force on `/auth/refresh`, admin enumeration, and mass exchange-sandbox key validation DoS are unlimited. Fix: `5/min` auth, `20/min` admin, `10/min` keys.

**H-2 — `ENCRYPTION_KEY` rotation scaffold is unused.** `backend/app/core/security.py:24-48` — `get_multi_fernet()` exists but `encrypt`/`decrypt` use single-key. No rotation script. Fix: `ENCRYPTION_KEYS: list[str]` + `MultiFernet` + `scripts/rotate_keys.py`.

**H-3 — Admin endpoint has no audit trail and `tier` field is loose `String(50)`.** `backend/app/api/v1/admin.py:15-49`, `backend/app/models/user.py:24`. Anyone with DB write access can self-promote. Fix: `Enum(UserTier)` + CHECK constraint + audit log + `ADMIN_EMAILS` double-gate.

**H-4 — No TrustedHost, HSTS, or HTTPS redirect; `/health` is verbose.** `backend/app/main.py:40-79`. `/health` reveals DB + Redis error strings (DSN leak). Fix: `TrustedHostMiddleware`, security-headers middleware, `/health/deep` behind shared secret.

**H-5 — Coinbase & Binance TR read-only validation is a documented no-op.** `backend/app/exchanges/coinbase.py:69-90`, `backend/app/exchanges/binancetr.py:61-78`. Both comment that they cannot detect write permissions and `return True`. Violates CLAUDE.md hard rule. Fix: enumerate Coinbase OAuth scopes or refuse to enable; probe Binance TR or remove adapter.

**H-6 — OKX passphrase smuggled through `api_secret` as `"secret|passphrase"`.** `backend/app/exchanges/okx.py:17-23`. Silently corrupts if real secret contains `|`. Fix: explicit `encrypted_passphrase` column + schema field + backfill.

**H-7 — `api_key` / `api_secret` in `ExchangeKeyCreate` are plain `str`, not `SecretStr`.** `backend/app/schemas/exchange_key.py:7-9`. Any future `HTTPException(detail=payload.model_dump())` leaks plaintext. Fix: `SecretStr` + `.get_secret_value()` at `keys.py:64,77-78`.

### 🟡 Medium

- **M-1** `view_count` increment happens before any bot filtering (`share.py:192-197`). Slack/Discord/iMessage unfurlers bump counters. Skip for known preview-bot UAs and `Purpose: prefetch`.
- **M-2** `public/share/{token}` runs full exchange fetch every call subject only to `30/min`. Six exchanges × 30/min burns quotas. Add Redis cache keyed on `(token, minute)`.
- **M-3** `get_current_user` returns `User` without checking `is_active` flag (`core/security.py:113-116`). No way to lock compromised account. Add `is_active: bool = True`.
- **M-4** `init_db()` (`main.py:30-31`) runs on `DEBUG=True`, bypassing Alembic. If DEBUG leaks to prod, schema drifts silently.
- **M-5** `CORS_ORIGINS` defaults to `["http://localhost:3000"]`; no startup assertion that production origins are set.
- **M-6** `python-jose` is effectively abandoned with CVE history. FastAPI recommends `pyjwt`; `authlib>=1.3.0` already a dep.
- **M-7** `python-binance`, `pybit`, `python-okx` are dependencies (`pyproject.toml:19-21`) but **unused** — adapters are hand-rolled. Dead deps expand attack surface.
- **M-8** Docker image runs as root (`backend/Dockerfile`). No `USER` directive; still uses `requirements.txt` while canonical manager is `uv`.
- **M-9** `docker-compose.yml:7-9` hard-codes postgres password `coinhq`. Use `${POSTGRES_PASSWORD:?}`.
- **M-10** `/auth/refresh` (`auth.py:160-164`) returns new access but **not** rotated refresh token; in-memory state means no revocation mechanism.
- **M-11** `docker-compose.prod.yml` — verify: non-root user, Postgres/Redis *not* published, separate internal network. Dev compose exposes `5432`/`6379` on host.

### 🟢 Hardening

- **G-1** Next.js middleware CSP to limit XSS blast radius.
- **G-2** GitHub Actions workflow (`.github/workflows/ci.yml` missing) — `ruff`, `pytest`, `pip-audit`, Bandit/Semgrep.
- **G-3** Nightly canary job re-decrypts sample `ExchangeKey` to detect rotation mistakes.
- **G-4** `Cache-Control: no-store` on all authenticated routes.
- **G-5** `frame-ancestors 'none'` CSP on `/share/[token]`.
- **G-6** `Vary: Authorization` on authenticated routes to prevent CDN cross-user caching.
- **G-7** Remove `init_db()` branch in `main.py`, drive all schema via Alembic.
- **G-8** Ship `SECURITY.md` and rotation runbook for `ENCRYPTION_KEY` and `JWT_SECRET`.

## Checklist Results

| # | Item | Status | Notes |
|---|---|---|---|
| 1 | Secrets in code | ✅ | No hard-coded keys |
| 2 | Logging PII | ✅ | structlog; `_mask_key()`; plaintext never logged |
| 3 | Response leakage of secrets | 🟡 | `ExchangeKeyRead` strips; share view leaks balances (C-1) |
| 4 | SQL injection | ✅ | ORM only |
| 5 | XSS | ✅ | React escaped; no `dangerouslySetInnerHTML` |
| 6 | CSRF (OAuth state + SameSite) | 🟡 | `state` present but in-memory (C-4); no cookies (C-3) |
| 7 | CORS whitelist | ✅ | Narrow, explicit origins |
| 8 | Rate limiting coverage | 🔴 | Only portfolio + public share (H-1) |
| 9 | Auth bypass | ✅ | `Depends(get_current_user)` on every protected route |
| 10 | Tenant isolation | ✅ | All queries filter by `user_id` |
| 11 | Share-link flag leak | 🔴 | C-1 |
| 12 | Admin gate | 🟡 | Works, weak column type + no audit (H-3) |
| 13 | Sentry PII scrubbing | 🔴 | C-2 |
| 14 | JWT hygiene | 🔴 | C-3 |
| 15 | Encryption at rest | 🟡 | Fernet OK, rotation unused (H-2) |
| 16 | Read-only key validation | 🟡 | Binance/Bybit/OKX OK; Coinbase/BinanceTR no-op (H-5) |
| 17 | Dependencies | 🟡 | pip-audit not in CI; python-jose stale; dead SDK deps |
| 18 | Docker non-root | 🟡 | Runs as root (M-8) |
| 19 | HTTPS / HSTS | 🔴 | Nothing set (H-4) |
| 20 | Error messages in prod | 🟡 | `/health` verbose (H-4) |

**Score:** 10 ✅ / 7 🟡 / 4 🔴 — big jump from 2026-04-06.

## Action Items (prioritized)

| # | Action | Severity | Effort | Files |
|---|---|---|---|---|
| 1 | Gate `usd_value`/`total_usd`/`profile_name` behind visibility flags; add `show_profile_name` | 🔴 | 2 h | `share.py`, `schemas/share_link.py`, `models/share_link.py`, Alembic, `ShareLinkManager.tsx`, `share/[token]/page.tsx` |
| 2 | Frontend Sentry `beforeSend` scrubber; disable tracing; decide on backend Sentry | 🔴 | 1 h | `frontend/src/lib/sentry.ts`, `backend/app/main.py` |
| 3 | Move OAuth `state` to Redis | 🔴 | 1 h | `backend/app/api/v1/auth.py` |
| 4 | JWT TTL 15 min; httpOnly cookie; `jti` + Redis deny-list; remove `localStorage` | 🔴 | 1 d | `config.py`, `security.py`, `auth.py`, frontend `api.ts` |
| 5 | Rate-limit `/auth/*`, `/admin/*`, keys, `POST /share` | 🟠 | 2 h | multiple |
| 6 | Enforce read-only for Coinbase / Binance TR or refuse | 🟠 | 4 h | `exchanges/coinbase.py`, `exchanges/binancetr.py` |
| 7 | Wire `MultiFernet` + `ENCRYPTION_KEYS` + rotation script | 🟠 | 4 h | `security.py`, `config.py`, new `scripts/rotate_keys.py` |
| 8 | Admin audit logging + `Enum(UserTier)` CHECK + `ADMIN_EMAILS` double-gate | 🟠 | 2 h | `admin.py`, `user.py`, Alembic |
| 9 | TrustedHost + security-headers middleware + trim `/health` | 🟠 | 1 h | `main.py`, `config.py` |
| 10 | `SecretStr` on ExchangeKeyCreate; explicit OKX `passphrase` field + column | 🟠 | 1 h | `schemas/exchange_key.py`, `keys.py`, `okx.py`, Alembic |
| 11 | Non-root Docker user; drop dead SDK deps; replace `python-jose` | 🟡 | 3 h | `Dockerfile`, `pyproject.toml`, `security.py` |
| 12 | Skip view-count bump for preview bots / prefetch | 🟡 | 30 m | `share.py` |
| 13 | `User.is_active` + dependency check | 🟡 | 1 h | `user.py`, `security.py`, Alembic |
| 14 | CI workflow: ruff + pytest + pip-audit + bandit/semgrep | 🟡 | 2 h | `.github/workflows/ci.yml` |
| 15 | CSP / Referrer-Policy / frame-ancestors on share page | 🟢 | 1 h | `frontend/next.config.js` |

## References
- Previous audit — `analysis/archive_2026-04-06/07_security_infrastructure.md`
- OWASP ASVS v4.0.3 §2 §3 §6 §8 §10; OWASP Top 10 2021 A01/A02/A05/A07
- RFC 6749 §10.12 (OAuth CSRF), §10.14 (redirect URI)

**Totals:** 4 🔴 / 7 🟠 / 11 🟡 / 8 🟢 = **30 findings**

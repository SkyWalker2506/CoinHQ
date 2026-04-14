# CoinHQ — Sprint Planı
> Kaynak: MASTER_ANALYSIS.md | Tarih: 2026-04-06 | Jira: COIN

---

## Özet

| Sprint | Odak | SP | Öncelik |
|--------|------|----|---------|
| Sprint 1 | Security & Critical Fixes | 28 SP | P0 |
| Sprint 2 | Performance & Architecture | 30 SP | P1 |
| Sprint 3 | UX & Accessibility | 32 SP | P1-P2 |
| Sprint 4 | Analytics & Growth | 28 SP | P2 |
| Sprint 5 | Monetization & Competitive | 22 SP | P2-P3 |

---

## Sprint 1 — Security & Critical Fixes (28 SP)

### Epic: [Sprint 1] Security & Critical Fixes

| # | Başlık (İngilizce) | Label | Öncelik | SP |
|---|-------------------|-------|---------|-----|
| S1-1 | Implement JWT authentication middleware | security, arch | P0/Highest | 5 |
| S1-2 | Implement Google OAuth 2.0 login flow | security, arch | P0/Highest | 5 |
| S1-3 | Add multi-user data isolation (user_id scoping) | security, arch | P0/Highest | 3 |
| S1-4 | Fix Binance adapter missing `await` in get_balances | perf, arch | P0/Highest | 1 |
| S1-5 | Implement read-only API key enforcement per exchange | security | P1/High | 3 |
| S1-6 | Protect share link CRUD endpoints with auth | security | P1/High | 2 |
| S1-7 | Narrow CORS allow_methods and allow_headers | security | P1/High | 1 |
| S1-8 | Remove source code volume mount from production docker-compose | security, arch | P1/High | 1 |
| S1-9 | Disable init_db create_all in production (use Alembic only) | arch | P1/High | 2 |
| S1-10 | Add pip-audit to CI pipeline | security | P1/High | 1 |
| S1-11 | Add get_db AsyncGenerator return type annotation | arch | P1/High | 1 |
| S1-12 | Add exchange factory explicit ValueError on unknown exchange | arch | P1/High | 1 |
| S1-13 | Add structured audit logging (structlog) | security, analytics | P2/Medium | 2 |

---

## Sprint 2 — Performance & Architecture (30 SP)

### Epic: [Sprint 2] Performance & Architecture

| # | Başlık (İngilizce) | Label | Öncelik | SP |
|---|-------------------|-------|---------|-----|
| S2-1 | Parallelize exchange balance fetches with asyncio.gather | perf | P1/High | 2 |
| S2-2 | Consolidate CoinGecko price fetches into single bulk request | perf | P1/High | 2 |
| S2-3 | Fix aggregate portfolio N+1 query with parallel fetch | perf | P1/High | 3 |
| S2-4 | Fix Redis singleton async race condition at startup | perf, arch | P1/High | 2 |
| S2-5 | Add SWR or React Query for frontend data caching | perf, ui | P1/High | 3 |
| S2-6 | Reuse httpx.AsyncClient via app.state lifespan | perf | P2/Medium | 2 |
| S2-7 | Add separate Redis cache for CoinGecko price data (30s TTL) | perf | P2/Medium | 2 |
| S2-8 | Add Fernet singleton to avoid per-call object creation | perf | P2/Medium | 1 |
| S2-9 | Add SQLAlchemy engine pool_size and max_overflow config | perf | P2/Medium | 1 |
| S2-10 | Add test infrastructure: pytest fixtures and exchange mocks | arch | P1/High | 3 |
| S2-11 | Add tests for portfolio service and exchange adapters | arch | P1/High | 3 |
| S2-12 | Set up CI pipeline: ruff + pytest + pnpm lint + pnpm test | arch | P1/High | 2 |
| S2-13 | Add OpenAPI to TypeScript codegen (openapi-typescript) | arch | P2/Medium | 2 |
| S2-14 | Add bundle analyzer and lazy-import recharts | perf | P2/Medium | 2 |

---

## Sprint 3 — UX & Accessibility (32 SP)

### Epic: [Sprint 3] UX & Accessibility

| # | Başlık (İngilizce) | Label | Öncelik | SP |
|---|-------------------|-------|---------|-----|
| S3-1 | Build login page with Google OAuth button and tagline | ui, growth | P1/High | 3 |
| S3-2 | Add navigation sidebar/navbar with active route highlight | ui | P1/High | 3 |
| S3-3 | Add skeleton loading cards for PortfolioSummary and ExchangeList | ui | P1/High | 2 |
| S3-4 | Replace window.confirm() with custom confirmation modal | ui, a11y | P1/High | 2 |
| S3-5 | Define design token system in tailwind.config.ts | ui | P1/High | 2 |
| S3-6 | Add favicon and og:image to layout.tsx | ui, seo | P1/High | 1 |
| S3-7 | Replace focus:outline-none with focus-visible:ring-2 | a11y | P1/High | 2 |
| S3-8 | Add ARIA role="dialog", aria-modal, aria-labelledby to modals | a11y | P1/High | 2 |
| S3-9 | Add ESC key close support to all modals | a11y | P1/High | 1 |
| S3-10 | Add focus trap to modals (Tab/Shift+Tab stays inside) | a11y | P1/High | 2 |
| S3-11 | Fix label htmlFor and input id associations | a11y | P1/High | 1 |
| S3-12 | Add aria-label to contextual buttons (Copy URL, Revoke) | a11y | P1/High | 1 |
| S3-13 | Add role="img" and aria-label to AllocationChart | a11y | P2/Medium | 2 |
| S3-14 | Add role="alert" to error messages | a11y | P2/Medium | 1 |
| S3-15 | Add loading state aria-live="polite" announcements | a11y | P2/Medium | 1 |
| S3-16 | Add "Powered by CoinHQ" CTA on share page | growth, ui | P1/High | 2 |
| S3-17 | Add cached indicator badge to PortfolioSummary | ui | P2/Medium | 1 |
| S3-18 | Add "Show all assets" toggle in ExchangeList | ui | P2/Medium | 2 |

---

## Sprint 4 — Analytics & Growth (28 SP)

### Epic: [Sprint 4] Analytics & Growth

| # | Başlık (İngilizce) | Label | Öncelik | SP |
|---|-------------------|-------|---------|-----|
| S4-1 | Integrate Plausible or Umami analytics (privacy-first) | analytics | P2/Medium | 2 |
| S4-2 | Add view_count and last_viewed_at to share_links table | analytics, growth | P2/Medium | 2 |
| S4-3 | Integrate Sentry or Glitchtip for frontend error tracking | analytics | P2/Medium | 3 |
| S4-4 | Add backend structured logging with structlog | analytics, arch | P2/Medium | 2 |
| S4-5 | Add custom event tracking for key user actions | analytics | P2/Medium | 2 |
| S4-6 | Add robots.txt and sitemap.xml to public/ | seo | P1/High | 1 |
| S4-7 | Add Open Graph and Twitter Card metadata to share pages | seo, growth | P1/High | 2 |
| S4-8 | Add generateMetadata() for dynamic share page titles | seo | P1/High | 2 |
| S4-9 | Build onboarding wizard: profile → exchange → share (3 steps) | growth, ui | P2/Medium | 5 |
| S4-10 | Add empty state designs with CTA for all data sections | growth, ui | P2/Medium | 3 |
| S4-11 | Add /admin/stats endpoint for basic product metrics | analytics | P2/Medium | 2 |
| S4-12 | Expand /health endpoint with DB + Redis + exchange checks | analytics | P2/Medium | 2 |

---

## Sprint 5 — Monetization & Competitive (22 SP)

### Epic: [Sprint 5] Monetization & Competitive

| # | Başlık (İngilizce) | Label | Öncelik | SP |
|---|-------------------|-------|---------|-----|
| S5-1 | Add Coinbase exchange adapter | monetization, arch | P2/Medium | 5 |
| S5-2 | Add Kraken exchange adapter | monetization, arch | P2/Medium | 5 |
| S5-3 | Design and implement free/premium tier model | monetization | P2/Medium | 5 |
| S5-4 | Build pricing/landing page for cloud SaaS tier | monetization, ui | P3/Low | 3 |
| S5-5 | Add key usage audit log (which key used when) | security, analytics | P3/Low | 2 |
| S5-6 | Add Dependabot or Renovate for dependency auto-updates | arch | P3/Low | 1 |
| S5-7 | Add encryption key rotation mechanism | security | P3/Low | 1 |

---

## Bağımlılık Zinciri

```
Sprint 1 (Auth) → Sprint 2 kısmen → Sprint 3 (Login page) → Sprint 4 (Onboarding)
Binance fix (S1-4) → Sprint 2 performance çalışmaları
Sprint 2 (SWR) → Sprint 3 (Skeleton loading daha anlamlı)
Sprint 4 (Share link view_count) → Sprint 5 (viral loop ölçümü)
```

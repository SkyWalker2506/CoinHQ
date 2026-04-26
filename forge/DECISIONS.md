# Forge Decision Log — CoinHQ

Append-only ADR log for forge-driven decisions. Each decision is dated and references the run + PRs that implemented it.

---

## Run 4 — 2026-04-26

### D001: All encryption flows through MultiFernet (even with one key)
- **Decision:** `_get_fernet()` returns a `MultiFernet`, not a bare `Fernet`. Single-key configurations wrap the lone key in MultiFernet.
- **Why:** Adding past keys for rotation requires zero code changes — just an env var update.
- **Alternatives considered:** Conditional MultiFernet only when `ENCRYPTION_KEYS` is set (rejected: branching adds bugs); separate `encrypt_v2`/`decrypt_v2` parallel API (rejected: callsite churn).
- **Risk:** Microscopic perf overhead from the wrapper indirection (negligible vs network/DB latency).
- **Etkisi:** PR #34 wired this; future key-rotation operators have a documented 4-step playbook in `.env.example`.

### D002: Inline stateful test stubs over fakeredis dev-dep
- **Decision:** `_StatefulRedisStub` lives inline in `tests/test_auth.py` (≈15 LOC). No fakeredis added to `pyproject.toml`.
- **Why:** Only one test file needs it; explicit stub reads better than configuring a third-party fake.
- **Reverse trigger:** If a third test file needs the same shape, extract to `tests/stubs.py`.
- **Etkisi:** PR #35.

### D003: JWT→httpOnly cookie migration deferred to dedicated sprint
- **Decision:** Not bundled into Run 4 despite being on the Run 3 lesson list.
- **Why:** Touches `auth/callback/page.tsx`, `lib/api.ts`, `usePortfolio.ts`, OAuth callback redirect URI, plus a new server-side cookie middleware. Single cohesive migration; risky to interleave with unrelated work.
- **Plan:** Run 5 should treat this as a single dedicated task with a migration plan, feature flag, and integration test pre-flight.

### D004: Waitlist captures via localStorage queue + Plausible event (no backend yet)
- **Decision:** `WaitlistForm` writes to `localStorage` and fires `Waitlist Submitted` analytics — no backend `/api/v1/waitlist` endpoint.
- **Why:** Closes the dead CTA loop without scaffolding a half-built endpoint. Plausible captures the durable signal even when storage is blocked.
- **Reverse trigger:** When the real endpoint lands, replace the localStorage write with a `POST` and add an integration test. The form's existing API surface remains stable.
- **Etkisi:** PR #37.

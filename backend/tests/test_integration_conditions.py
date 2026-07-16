"""HTTP-level integration tests for the CoinHQ backend.

Runs the REAL FastAPI app (`app.main.app`) over httpx.AsyncClient +
ASGITransport. The lifespan does NOT run, so `app.state.redis` (stateful
stub) and `app.state.http_client` are installed by a session fixture.
The global async engine (app.core.database) is used against a SQLite file
DB; every test drops + recreates all tables for a clean slate.

Price determinism: `get_usd_prices` is monkeypatched in both
app.services.portfolio_service and app.services.trade_service to a fixed
price table — no network traffic ever happens (the "demo" adapter makes no
HTTP calls either).

Condition groups below; individual tests reference the C-xxx condition IDs
from docs/SYSTEM_TEST_PLAN.md in their docstrings:
  IC-1  auth & multi-user isolation        IC-8  delegated trade via share token
  IC-2  tier limits (profiles/exchanges)   IC-9  owner trade
  IC-3  exchange key validation/storage    IC-10 realized PnL (AVCO)
  IC-4  portfolio pricing & aggregation    IC-11 portfolio history
  IC-5  share-link permission matrix       IC-12 waitlist
  IC-6  share-link lifecycle               IC-13 admin stats
  IC-7  follow/unfollow                    IC-14 rate limiter registration

Run with:
  DATABASE_URL='sqlite+aiosqlite:////tmp/coinhq-inttest.db' JWT_SECRET=x \
  ENCRYPTION_KEY=<Fernet key> uv run --all-extras pytest tests/test_integration_conditions.py -q
"""

import os

from cryptography.fernet import Fernet

# Must happen before any app import — settings are read at import time.
_TEST_FERNET_KEY = Fernet.generate_key().decode()
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:////tmp/coinhq-inttest.db")
os.environ.setdefault("ENCRYPTION_KEY", _TEST_FERNET_KEY)
os.environ.setdefault("JWT_SECRET", "integration-test-jwt-secret")

import re
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import select

from app.api.v1 import portfolio as portfolio_api
from app.api.v1 import share as share_api
from app.core.config import settings
from app.core.database import AsyncSessionLocal, Base, engine
from app.core.security import create_access_token, encrypt, reset_fernet_cache
from app.main import app
from app.models.exchange_key import ExchangeKey
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.trade_order import TradeOrder
from app.models.user import User

API = "/api/v1"

# Fixed price table (never hit the network)
PRICES = {"BTC": 65000.0, "ETH": 3400.0, "SOL": 150.0, "USDT": 1.0, "ADA": 0.45, "DOGE": 0.12}

# DEMO adapter MAIN preset totals (free+locked) priced with PRICES
MAIN_USD = {
    "BTC": 0.43 * 65000.0,   # 27950.0
    "ETH": 3.25 * 3400.0,    # 11050.0
    "SOL": 30.0 * 150.0,     # 4500.0
    "USDT": 1500.0 * 1.0,    # 1500.0
    "ADA": 800.0 * 0.45,     # 360.0
}
MAIN_TOTAL = sum(MAIN_USD.values())  # 45360.0

# DEMO adapter ALT preset ("alt" marker in api_key)
ALT_USD = {"ETH": 0.8 * 3400.0, "DOGE": 5000.0 * 0.12, "USDT": 250.0}
ALT_TOTAL = sum(ALT_USD.values())  # 3570.0

READ_KEY = "demo-readonly-key-0001"
TRADE_KEY = "demo-trading-key-0001"
ALT_KEY = "demo-altcoins-key-0001"
SECRET = "demo-secret-000000001"


async def _fixed_prices(assets, http_client=None, redis_client=None):
    return {a: PRICES[a] for a in assets if a in PRICES}


class _RedisStub:
    """Minimal stateful async-Redis stand-in (get/set/setex/delete/ping)."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ex=None):
        self.store[key] = value
        return True

    async def setex(self, key, ttl, value):
        self.store[key] = value
        return True

    async def delete(self, key):
        return 1 if self.store.pop(key, None) is not None else 0

    async def ping(self):
        return True


@pytest.fixture(scope="session")
def app_state():
    """Lifespan replacement: install redis stub + http client on app.state."""
    app.state.redis = _RedisStub()
    app.state.http_client = httpx.AsyncClient(timeout=5.0)
    return app.state


@pytest.fixture
async def client(app_state, monkeypatch):
    # Deterministic crypto + demo exchange, restored on teardown.
    old_demo, old_enc = settings.DEMO_MODE, settings.ENCRYPTION_KEY
    settings.DEMO_MODE = True
    settings.ENCRYPTION_KEY = _TEST_FERNET_KEY
    reset_fernet_cache()

    # Fresh cache + rate-limit counters per test.
    app_state.redis.store.clear()
    for lim in (app.state.limiter, share_api.limiter, portfolio_api.limiter):
        try:
            lim.reset()
        except Exception:  # noqa: BLE001 — storage without reset support
            pass

    # Fixed prices — no network.
    monkeypatch.setattr("app.services.portfolio_service.get_usd_prices", _fixed_prices)
    monkeypatch.setattr("app.services.trade_service.get_usd_prices", _fixed_prices)

    # Clean schema per test on the global engine.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await engine.dispose()
    settings.DEMO_MODE = old_demo
    settings.ENCRYPTION_KEY = old_enc
    reset_fernet_cache()


# ── helpers ──────────────────────────────────────────────────────────────────

async def _seed_user(email: str, tier: str = "free") -> User:
    async with AsyncSessionLocal() as s:
        user = User(email=email, google_id=f"gid-{email}", name=email.split("@")[0], tier=tier)
        s.add(user)
        await s.commit()
        await s.refresh(user)
        return user


def _auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


async def _insert(*objs):
    async with AsyncSessionLocal() as s:
        s.add_all(objs)
        await s.commit()
        for o in objs:
            await s.refresh(o)
    return objs


async def _mk_profile(client, headers, name: str = "Main") -> dict:
    r = await client.post(f"{API}/profiles/", json={"name": name}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


async def _post_demo_key(client, headers, profile_id, key_type="read_only", api_key=None):
    return await client.post(
        f"{API}/profiles/{profile_id}/keys/",
        json={
            "exchange": "demo",
            "api_key": api_key or (TRADE_KEY if key_type == "trade" else READ_KEY),
            "api_secret": SECRET,
            "key_type": key_type,
        },
        headers=headers,
    )


async def _owner_with_key(client, *, tier="free", key_type="read_only",
                          email="owner@example.com", profile_name="Main", api_key=None):
    """User + profile + validated demo key, all through the HTTP API."""
    user = await _seed_user(email, tier)
    headers = _auth(user)
    profile = await _mk_profile(client, headers, profile_name)
    if key_type is not None:
        r = await _post_demo_key(client, headers, profile["id"], key_type=key_type, api_key=api_key)
        assert r.status_code == 201, r.text
    return user, headers, profile


async def _mk_share(client, headers, profile_id, **overrides) -> dict:
    r = await client.post(f"{API}/share", json={"profile_id": profile_id, **overrides}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def _naive_utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# ═════════════════════════════════ IC-1 AUTH / ISOLATION ═════════════════════

async def test_request_without_token_is_rejected(client):
    """C-013/C-014: no Authorization header → 401/403; garbage token → 401."""
    r = await client.get(f"{API}/profiles/")
    assert r.status_code in (401, 403), r.text

    r = await client.get(f"{API}/profiles/", headers={"Authorization": "Bearer not-a-jwt"})
    assert r.status_code == 401, r.text


async def test_cannot_read_foreign_profile(client):
    """C-024: GET another user's profile → 403 (or 404); own profile → 200."""
    alice, alice_h, profile = await _owner_with_key(client, email="alice@example.com", key_type=None)
    bob = await _seed_user("bob@example.com")

    r = await client.get(f"{API}/profiles/{profile['id']}", headers=_auth(bob))
    assert r.status_code in (403, 404), r.text

    r = await client.get(f"{API}/profiles/{profile['id']}", headers=alice_h)
    assert r.status_code == 200


async def test_cannot_delete_foreign_profile(client):
    """C-026: DELETE another user's profile → 403/404, profile survives."""
    alice, alice_h, profile = await _owner_with_key(client, email="alice@example.com", key_type=None)
    bob = await _seed_user("bob@example.com")

    r = await client.delete(f"{API}/profiles/{profile['id']}", headers=_auth(bob))
    assert r.status_code in (403, 404), r.text

    r = await client.get(f"{API}/profiles/{profile['id']}", headers=alice_h)
    assert r.status_code == 200, "profile must still exist after foreign delete attempt"


async def test_cannot_add_key_to_foreign_profile(client):
    """C-029: POST a key onto another user's profile → 403/404 and nothing stored."""
    alice, alice_h, profile = await _owner_with_key(client, email="alice@example.com", key_type=None)
    bob = await _seed_user("bob@example.com")

    r = await _post_demo_key(client, _auth(bob), profile["id"])
    assert r.status_code in (403, 404), r.text

    r = await client.get(f"{API}/profiles/{profile['id']}/keys/", headers=alice_h)
    assert r.status_code == 200
    assert r.json() == [], "no key may be created on a foreign profile"


# ═════════════════════════════════ IC-2 TIER LIMITS ══════════════════════════

async def test_free_tier_second_profile_rejected(client):
    """C-018/C-153: free tier is limited to 1 profile — second create → 403."""
    user = await _seed_user("free@example.com", tier="free")
    headers = _auth(user)
    await _mk_profile(client, headers, "First")

    r = await client.post(f"{API}/profiles/", json={"name": "Second"}, headers=headers)
    assert r.status_code == 403, r.text
    assert "limit" in r.json()["detail"].lower()


async def test_premium_tier_multiple_profiles_ok(client):
    """C-019/C-155: premium tier may create several profiles."""
    user = await _seed_user("prem@example.com", tier="premium")
    headers = _auth(user)
    for name in ("P1", "P2", "P3"):
        await _mk_profile(client, headers, name)

    r = await client.get(f"{API}/profiles/", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 3


async def test_free_tier_third_distinct_exchange_rejected(client):
    """C-031/C-154: free tier allows 2 distinct exchanges per profile — 3rd → 403 tier_limit."""
    user, headers, profile = await _owner_with_key(client, email="free@example.com")
    # Second distinct exchange seeded directly (only 'demo' validates offline).
    await _insert(ExchangeKey(
        profile_id=profile["id"], exchange="binance", key_type="read_only",
        encrypted_key=encrypt("k" * 16), encrypted_secret=encrypt("s" * 16),
    ))

    r = await client.post(
        f"{API}/profiles/{profile['id']}/keys/",
        json={"exchange": "bybit", "api_key": "x" * 16, "api_secret": "y" * 16},
        headers=headers,
    )
    assert r.status_code == 403, r.text
    assert "tier_limit" in r.json()["detail"]


async def test_second_key_type_for_same_exchange_does_not_count_against_limit(client):
    """C-032/C-154: read_only + trade key for the SAME exchange = one exchange slot."""
    user, headers, profile = await _owner_with_key(client, email="free@example.com")
    # Fill the free-tier limit of 2 distinct exchanges.
    await _insert(ExchangeKey(
        profile_id=profile["id"], exchange="binance", key_type="read_only",
        encrypted_key=encrypt("k" * 16), encrypted_secret=encrypt("s" * 16),
    ))

    # Adding a TRADE key for the already-present 'demo' exchange must succeed.
    r = await _post_demo_key(client, headers, profile["id"], key_type="trade")
    assert r.status_code == 201, r.text
    assert r.json()["key_type"] == "trade"


# ═════════════════════════════════ IC-3 KEY VALIDATION ═══════════════════════

async def test_unsupported_exchange_rejected(client):
    """C-030: unknown exchange name → 400."""
    user, headers, profile = await _owner_with_key(client, key_type=None)
    r = await client.post(
        f"{API}/profiles/{profile['id']}/keys/",
        json={"exchange": "hogwarts", "api_key": "x" * 16, "api_secret": "y" * 16},
        headers=headers,
    )
    assert r.status_code == 400, r.text
    assert "Unsupported exchange" in r.json()["detail"]


async def test_read_only_key_with_write_permission_rejected(client):
    """C-034: read-only key that has write permissions ('write' marker) → 400."""
    user, headers, profile = await _owner_with_key(client, key_type=None)
    r = await _post_demo_key(client, headers, profile["id"], api_key="demo-write-key-000001")
    assert r.status_code == 400, r.text
    assert "Write permissions" in r.json()["detail"]

    r = await client.get(f"{API}/profiles/{profile['id']}/keys/", headers=headers)
    assert r.json() == [], "rejected key must not be stored"


async def test_trade_key_with_withdraw_permission_rejected(client):
    """C-036: trade key that can withdraw ('withdraw' marker) → 400."""
    user, headers, profile = await _owner_with_key(client, key_type=None)
    r = await _post_demo_key(
        client, headers, profile["id"], key_type="trade", api_key="demo-withdraw-key-0001"
    )
    assert r.status_code == 400, r.text
    assert "withdraw" in r.json()["detail"].lower()


async def test_read_only_key_created_and_secrets_never_returned(client):
    """C-035/C-028: valid demo key → 201 key_type=read_only; api_key/secret never in response."""
    user, headers, profile = await _owner_with_key(client, key_type=None)
    r = await _post_demo_key(client, headers, profile["id"])
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["key_type"] == "read_only"
    assert body["exchange"] == "demo"
    assert "api_key" not in body and "api_secret" not in body
    assert "encrypted_key" not in body and "encrypted_secret" not in body
    assert READ_KEY not in r.text and SECRET not in r.text

    # List response is equally clean.
    r = await client.get(f"{API}/profiles/{profile['id']}/keys/", headers=headers)
    assert READ_KEY not in r.text and SECRET not in r.text


async def test_trade_key_created(client):
    """C-038: valid demo trade key → 201 key_type=trade."""
    user, headers, profile = await _owner_with_key(client, key_type=None)
    r = await _post_demo_key(client, headers, profile["id"], key_type="trade")
    assert r.status_code == 201, r.text
    assert r.json()["key_type"] == "trade"
    assert TRADE_KEY not in r.text and SECRET not in r.text


# ═════════════════════════════════ IC-4 PORTFOLIO ════════════════════════════

async def test_profile_portfolio_values_with_fixed_prices(client):
    """C-052 (pricing): demo MAIN preset priced with the fixed table — exact usd_value/total."""
    user, headers, profile = await _owner_with_key(client)

    r = await client.get(f"{API}/portfolio/profile/{profile['id']}", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()

    assert len(body["exchanges"]) == 1
    ex = body["exchanges"][0]
    assert ex["exchange"] == "demo"

    by_asset = {b["asset"]: b for b in ex["balances"]}
    assert set(by_asset) == set(MAIN_USD)
    for asset, usd in MAIN_USD.items():
        assert by_asset[asset]["usd_value"] == pytest.approx(usd), asset
    assert by_asset["BTC"]["total"] == pytest.approx(0.43)

    assert ex["total_usd"] == pytest.approx(MAIN_TOTAL)
    assert body["total_usd"] == pytest.approx(MAIN_TOTAL)  # 45360.0


async def test_aggregate_portfolio_sums_all_profiles(client):
    """C-056: /portfolio/aggregate — grand_total = sum of both profiles."""
    user = await _seed_user("prem@example.com", tier="premium")
    headers = _auth(user)
    p1 = await _mk_profile(client, headers, "Alpha")
    p2 = await _mk_profile(client, headers, "Beta")
    assert (await _post_demo_key(client, headers, p1["id"])).status_code == 201
    assert (await _post_demo_key(client, headers, p2["id"], api_key=ALT_KEY)).status_code == 201

    r = await client.get(f"{API}/portfolio/aggregate", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()

    assert len(body["profiles"]) == 2
    totals = {p["profile_name"]: p["total_usd"] for p in body["profiles"]}
    assert totals["Alpha"] == pytest.approx(MAIN_TOTAL)
    assert totals["Beta"] == pytest.approx(ALT_TOTAL)
    assert body["grand_total_usd"] == pytest.approx(MAIN_TOTAL + ALT_TOTAL)  # 48930.0
    assert body["asset_totals"]["ETH"] == pytest.approx(MAIN_USD["ETH"] + ALT_USD["ETH"])
    assert body["asset_totals"]["DOGE"] == pytest.approx(ALT_USD["DOGE"])


# ═════════════════════════════ IC-5 SHARE PERMISSION MATRIX ══════════════════

_ALL_ON = dict(show_total_value=True, show_coin_amounts=True,
               show_exchange_names=True, show_allocation_pct=True)


async def _shared_view(client, headers, profile_id, **flags):
    link = await _mk_share(client, headers, profile_id, **flags)
    r = await client.get(f"{API}/public/share/{link['token']}")
    assert r.status_code == 200, r.text
    return link, r.json()


async def test_share_view_all_flags_on(client):
    """C-080 (TTTT)/C-078: all flags on → totals, amounts, real exchange name, allocation visible."""
    user, headers, profile = await _owner_with_key(client)
    _, view = await _shared_view(client, headers, profile["id"], **_ALL_ON)

    assert view["total_usd"] == pytest.approx(MAIN_TOTAL)
    ex = view["exchanges"][0]
    assert ex["exchange_name"] == "demo"
    assert ex["total_usd"] == pytest.approx(MAIN_TOTAL)
    by_asset = {a["asset"]: a for a in ex["assets"]}
    assert by_asset["BTC"]["amount"] == pytest.approx(0.43)
    assert by_asset["BTC"]["usd_value"] == pytest.approx(MAIN_USD["BTC"])
    assert by_asset["BTC"]["allocation_pct"] == pytest.approx(
        round(MAIN_USD["BTC"] / MAIN_TOTAL * 100, 2)
    )
    assert sum(a["allocation_pct"] for a in ex["assets"]) == pytest.approx(100, abs=0.1)


async def test_share_view_all_flags_off(client):
    """C-080 (FFFF)/C-075/C-076/C-077: all flags off → every sensitive field is null / masked."""
    user, headers, profile = await _owner_with_key(client)
    _, view = await _shared_view(
        client, headers, profile["id"],
        show_total_value=False, show_coin_amounts=False,
        show_exchange_names=False, show_allocation_pct=False,
    )

    assert view["total_usd"] is None
    for ex in view["exchanges"]:
        assert ex["total_usd"] is None
        assert re.fullmatch(r"Exchange [0-9a-f]{8}", ex["exchange_name"]), ex["exchange_name"]
        assert "demo" not in ex["exchange_name"]
        for a in ex["assets"]:
            assert a["amount"] is None
            assert a["usd_value"] is None
            assert a["allocation_pct"] is None


async def test_share_view_total_hidden_only(client):
    """C-075: show_total_value=False → total_usd, asset.usd_value AND exchange.total_usd null."""
    user, headers, profile = await _owner_with_key(client)
    _, view = await _shared_view(client, headers, profile["id"],
                                 **{**_ALL_ON, "show_total_value": False})

    assert view["total_usd"] is None
    for ex in view["exchanges"]:
        assert ex["total_usd"] is None
        for a in ex["assets"]:
            assert a["usd_value"] is None
            assert a["amount"] is not None  # amounts stay visible


async def test_share_view_amounts_hidden_only(client):
    """C-076: show_coin_amounts=False → amount null, USD values stay visible."""
    user, headers, profile = await _owner_with_key(client)
    _, view = await _shared_view(client, headers, profile["id"],
                                 **{**_ALL_ON, "show_coin_amounts": False})

    assert view["total_usd"] == pytest.approx(MAIN_TOTAL)
    for a in view["exchanges"][0]["assets"]:
        assert a["amount"] is None
        assert a["usd_value"] is not None


async def test_share_view_exchange_names_masked_only(client):
    """C-077: show_exchange_names=False → 'Exchange <hash>' mask, real name never appears."""
    user, headers, profile = await _owner_with_key(client)
    _, view = await _shared_view(client, headers, profile["id"],
                                 **{**_ALL_ON, "show_exchange_names": False})

    ex = view["exchanges"][0]
    assert re.fullmatch(r"Exchange [0-9a-f]{8}", ex["exchange_name"]), ex["exchange_name"]
    assert "demo" not in ex["exchange_name"].lower()
    assert ex["total_usd"] == pytest.approx(MAIN_TOTAL)  # other fields unaffected


async def test_share_view_allocation_hidden_only(client):
    """C-078: show_allocation_pct=False → allocation_pct null, rest visible."""
    user, headers, profile = await _owner_with_key(client)
    _, view = await _shared_view(client, headers, profile["id"],
                                 **{**_ALL_ON, "show_allocation_pct": False})

    for a in view["exchanges"][0]["assets"]:
        assert a["allocation_pct"] is None
        assert a["usd_value"] is not None


async def test_share_view_profile_name_never_leaks(client):
    """C-082: real profile name is never exposed — label or 'Crypto Portfolio'."""
    secret_name = "SecretProfileName77"
    user, headers, profile = await _owner_with_key(client, profile_name=secret_name)

    _, view = await _shared_view(client, headers, profile["id"])
    assert view["profile_name"] == "Crypto Portfolio"
    assert secret_name not in str(view)

    _, view2 = await _shared_view(client, headers, profile["id"], label="Public Label")
    assert view2["profile_name"] == "Public Label"
    assert secret_name not in str(view2)


# ═════════════════════════════ IC-6 SHARE LIFECYCLE ══════════════════════════

async def test_expired_share_link_returns_410(client):
    """C-073: expired link → 410 Gone."""
    user, headers, profile = await _owner_with_key(client)
    link = await _mk_share(client, headers, profile["id"],
                           expires_at="2020-01-01T00:00:00Z")
    r = await client.get(f"{API}/public/share/{link['token']}")
    assert r.status_code == 410, r.text


async def test_revoked_share_link_returns_404(client):
    """C-069/C-072: owner revokes → public view 404."""
    user, headers, profile = await _owner_with_key(client)
    link = await _mk_share(client, headers, profile["id"])

    r = await client.delete(f"{API}/share/{link['id']}", headers=headers)
    assert r.status_code == 204, r.text

    r = await client.get(f"{API}/public/share/{link['token']}")
    assert r.status_code == 404, r.text


async def test_cannot_revoke_foreign_share_link(client):
    """C-070: revoking someone else's link → 404 and the link keeps working."""
    user, headers, profile = await _owner_with_key(client)
    link = await _mk_share(client, headers, profile["id"])
    mallory = await _seed_user("mallory@example.com")

    r = await client.delete(f"{API}/share/{link['id']}", headers=_auth(mallory))
    assert r.status_code == 404, r.text

    r = await client.get(f"{API}/public/share/{link['token']}")
    assert r.status_code == 200, "foreign revoke attempt must not deactivate the link"


async def test_patch_share_link_applies_immediately_to_public_view(client):
    """C-063/C-066: PATCH can_trade on/off + limit updates apply to the very next public request."""
    user, headers, profile = await _owner_with_key(client, key_type="trade")
    link = await _mk_share(client, headers, profile["id"], can_trade=True,
                           trade_max_per_order_usd=100.0)

    r = await client.get(f"{API}/public/share/{link['token']}")
    assert r.json()["can_trade"] is True
    assert r.json()["trade_max_per_order_usd"] == pytest.approx(100.0)

    r = await client.patch(
        f"{API}/share/{link['id']}",
        json={"trade_max_per_order_usd": 55.0, "trade_direction": "buy"},
        headers=headers,
    )
    assert r.status_code == 200, r.text

    view = (await client.get(f"{API}/public/share/{link['token']}")).json()
    assert view["trade_max_per_order_usd"] == pytest.approx(55.0)
    assert view["trade_direction"] == "buy"

    # Toggle trading off → next delegate trade is refused immediately.
    r = await client.patch(f"{API}/share/{link['id']}", json={"can_trade": False}, headers=headers)
    assert r.status_code == 200

    view = (await client.get(f"{API}/public/share/{link['token']}")).json()
    assert view["can_trade"] is False

    r = await client.post(
        f"{API}/public/share/{link['token']}/trade",
        json={"exchange": "demo", "asset": "BTC", "side": "buy", "usd_amount": 10},
    )
    assert r.status_code == 403, r.text


async def test_share_link_view_count_increments(client):
    """C-074: every public view bumps view_count."""
    user, headers, profile = await _owner_with_key(client)
    link = await _mk_share(client, headers, profile["id"])

    for _ in range(2):
        assert (await client.get(f"{API}/public/share/{link['token']}")).status_code == 200

    r = await client.get(f"{API}/share", params={"profile_id": profile["id"]}, headers=headers)
    assert r.status_code == 200
    row = next(x for x in r.json() if x["id"] == link["id"])
    assert row["view_count"] == 2


# ═════════════════════════════════ IC-7 FOLLOW ═══════════════════════════════

async def test_follow_disallowed_when_allow_follow_false(client):
    """C-090: allow_follow=False → follow attempt → 403."""
    user, headers, profile = await _owner_with_key(client)
    link = await _mk_share(client, headers, profile["id"], allow_follow=False)
    bob = await _seed_user("bob@example.com")

    r = await client.post(f"{API}/followed/{link['token']}", headers=_auth(bob))
    assert r.status_code == 403, r.text


async def test_follow_then_refollow_is_idempotent(client):
    """C-088/C-092: first follow → 201; second follow returns the SAME record (200/201)."""
    user, headers, profile = await _owner_with_key(client)
    link = await _mk_share(client, headers, profile["id"], allow_follow=True)
    bob = await _seed_user("bob@example.com")
    bob_h = _auth(bob)

    r1 = await client.post(f"{API}/followed/{link['token']}", headers=bob_h)
    assert r1.status_code == 201, r1.text

    r2 = await client.post(f"{API}/followed/{link['token']}", headers=bob_h)
    assert r2.status_code in (200, 201), r2.text
    assert r2.json()["id"] == r1.json()["id"], "refollow must not create a second record"

    r = await client.get(f"{API}/followed", headers=bob_h)
    assert len(r.json()) == 1


async def test_cannot_unfollow_foreign_follow_record(client):
    """C-094: DELETE another user's followed record → 404; own unfollow → 204."""
    user, headers, profile = await _owner_with_key(client)
    link = await _mk_share(client, headers, profile["id"])
    bob = await _seed_user("bob@example.com")
    carol = await _seed_user("carol@example.com")
    bob_h = _auth(bob)

    followed = (await client.post(f"{API}/followed/{link['token']}", headers=bob_h)).json()

    r = await client.delete(f"{API}/followed/{followed['id']}", headers=_auth(carol))
    assert r.status_code == 404, r.text

    r = await client.delete(f"{API}/followed/{followed['id']}", headers=bob_h)
    assert r.status_code == 204, r.text
    assert (await client.get(f"{API}/followed", headers=bob_h)).json() == []


# ═══════════════════════════ IC-8 DELEGATED TRADE ════════════════════════════

def _trade_body(usd, side="buy", asset="BTC", exchange="demo"):
    return {"exchange": exchange, "asset": asset, "side": side, "usd_amount": usd}


async def test_delegate_trade_refused_when_can_trade_false(client):
    """C-098: link with can_trade=False → 403."""
    user, headers, profile = await _owner_with_key(client, key_type="trade")
    link = await _mk_share(client, headers, profile["id"], can_trade=False)

    r = await client.post(f"{API}/public/share/{link['token']}/trade", json=_trade_body(10))
    assert r.status_code == 403, r.text


async def test_delegate_trade_direction_enforced(client):
    """C-105: sell-only link rejects a buy order → 403."""
    user, headers, profile = await _owner_with_key(client, key_type="trade")
    link = await _mk_share(client, headers, profile["id"], can_trade=True,
                           trade_direction="sell")

    r = await client.post(f"{API}/public/share/{link['token']}/trade",
                          json=_trade_body(10, side="buy"))
    assert r.status_code == 403, r.text
    assert "sell" in r.json()["detail"].lower()


async def test_delegate_trade_coin_whitelist_enforced(client):
    """C-107: coin outside the whitelist → 403."""
    user, headers, profile = await _owner_with_key(client, key_type="trade")
    link = await _mk_share(client, headers, profile["id"], can_trade=True,
                           trade_allowed_coins="BTC,ETH")

    r = await client.post(f"{API}/public/share/{link['token']}/trade",
                          json=_trade_body(10, asset="SOL"))
    assert r.status_code == 403, r.text
    assert "SOL" in r.json()["detail"]


async def test_delegate_trade_per_order_limit_enforced(client):
    """C-110: order above trade_max_per_order_usd → 403."""
    user, headers, profile = await _owner_with_key(client, key_type="trade")
    link = await _mk_share(client, headers, profile["id"], can_trade=True,
                           trade_max_per_order_usd=50.0)

    r = await client.post(f"{API}/public/share/{link['token']}/trade", json=_trade_body(60))
    assert r.status_code == 403, r.text
    assert "per-order" in r.json()["detail"]


async def test_delegate_trade_daily_limit_is_cumulative(client):
    """C-111/C-112: 24h limit $100 — 40 + 60 fill it exactly, the 3rd order (any size) → 403."""
    user, headers, profile = await _owner_with_key(client, key_type="trade")
    link = await _mk_share(client, headers, profile["id"], can_trade=True,
                           trade_daily_limit_usd=100.0)
    url = f"{API}/public/share/{link['token']}/trade"

    r1 = await client.post(url, json=_trade_body(40))
    assert r1.status_code == 200, r1.text
    r2 = await client.post(url, json=_trade_body(60))
    assert r2.status_code == 200, r2.text

    r3 = await client.post(url, json=_trade_body(10))
    assert r3.status_code == 403, r3.text
    assert "24h limit" in r3.json()["detail"]

    # Public view reports the accumulated spend.
    view = (await client.get(f"{API}/public/share/{link['token']}")).json()
    assert view["trade_spent_today_usd"] == pytest.approx(100.0)


async def test_delegate_trade_success_is_filled_and_recorded(client):
    """C-114: valid delegate order → 200 filled; TradeOrder row carries share_link_id."""
    user, headers, profile = await _owner_with_key(client, key_type="trade")
    link = await _mk_share(client, headers, profile["id"], can_trade=True)

    r = await client.post(f"{API}/public/share/{link['token']}/trade", json=_trade_body(650))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "filled"
    assert body["actor"] == "delegate"
    assert body["symbol"] == "BTCUSDT"
    assert body["exchange_order_id"], "demo adapter returns an order id"
    assert body["amount"] == pytest.approx(650 / 65000.0)  # 0.01 BTC at the fixed price

    async with AsyncSessionLocal() as s:
        row = (await s.execute(select(TradeOrder))).scalars().one()
    assert row.share_link_id == link["id"]
    assert row.actor == "delegate"
    assert row.status == "filled"
    assert row.usd_value == pytest.approx(650.0)


async def test_can_trade_link_requires_profile_trade_key(client):
    """C-061/C-065: profile without a trade key cannot get a can_trade link (create or PATCH) → 400."""
    user, headers, profile = await _owner_with_key(client)  # read_only key only

    r = await client.post(f"{API}/share",
                          json={"profile_id": profile["id"], "can_trade": True},
                          headers=headers)
    assert r.status_code == 400, r.text

    link = await _mk_share(client, headers, profile["id"])  # can_trade defaults to False
    r = await client.patch(f"{API}/share/{link['id']}", json={"can_trade": True}, headers=headers)
    assert r.status_code == 400, r.text


async def test_delegate_trade_non_positive_amount_rejected(client):
    """C-100: usd_amount <= 0 → 422 (schema gt=0) or 400."""
    user, headers, profile = await _owner_with_key(client, key_type="trade")
    link = await _mk_share(client, headers, profile["id"], can_trade=True)
    url = f"{API}/public/share/{link['token']}/trade"

    for bad in (0, -5):
        r = await client.post(url, json=_trade_body(bad))
        assert r.status_code in (400, 422), r.text


async def test_delegate_trade_invalid_side_rejected(client):
    """C-099: side outside buy|sell → 422."""
    user, headers, profile = await _owner_with_key(client, key_type="trade")
    link = await _mk_share(client, headers, profile["id"], can_trade=True)

    r = await client.post(f"{API}/public/share/{link['token']}/trade",
                          json=_trade_body(10, side="hodl"))
    assert r.status_code == 422, r.text


# ═════════════════════════════════ IC-9 OWNER TRADE ══════════════════════════

async def test_owner_trade_fills_and_ignores_share_limits(client):
    """C-120/C-121: owner trades are NOT constrained by share-link limits."""
    user, headers, profile = await _owner_with_key(client, key_type="trade")
    # A share link with tiny limits exists — must not affect the owner.
    await _mk_share(client, headers, profile["id"], can_trade=True,
                    trade_max_per_order_usd=1.0, trade_daily_limit_usd=1.0)

    r = await client.post(f"{API}/profiles/{profile['id']}/trade",
                          json=_trade_body(50_000), headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "filled"
    assert body["actor"] == "owner"
    assert body["amount"] == pytest.approx(50_000 / 65000.0)

    async with AsyncSessionLocal() as s:
        row = (await s.execute(select(TradeOrder))).scalars().one()
    assert row.share_link_id is None, "owner trades carry no share_link_id"


async def test_owner_trade_on_foreign_profile_404(client):
    """C-118: trading on someone else's profile → 404."""
    user, headers, profile = await _owner_with_key(client, key_type="trade")
    mallory = await _seed_user("mallory@example.com")

    r = await client.post(f"{API}/profiles/{profile['id']}/trade",
                          json=_trade_body(10), headers=_auth(mallory))
    assert r.status_code == 404, r.text


async def test_owner_trade_without_trade_key_400(client):
    """C-119/C-103: profile has only a read-only key → 400 'No trade key'."""
    user, headers, profile = await _owner_with_key(client)  # read_only

    r = await client.post(f"{API}/profiles/{profile['id']}/trade",
                          json=_trade_body(10), headers=headers)
    assert r.status_code == 400, r.text
    assert "No trade key" in r.json()["detail"]


async def test_trade_history_lists_owner_and_delegate_orders(client):
    """C-125/C-126/C-128: GET /profiles/{id}/trade returns the orders we placed."""
    user, headers, profile = await _owner_with_key(client, key_type="trade")
    link = await _mk_share(client, headers, profile["id"], can_trade=True)

    r = await client.post(f"{API}/profiles/{profile['id']}/trade",
                          json=_trade_body(130, asset="BTC"), headers=headers)
    assert r.status_code == 200, r.text
    r = await client.post(f"{API}/public/share/{link['token']}/trade",
                          json=_trade_body(34, asset="ETH"))
    assert r.status_code == 200, r.text

    r = await client.get(f"{API}/profiles/{profile['id']}/trade", headers=headers)
    assert r.status_code == 200
    orders = r.json()
    assert len(orders) == 2
    actors = {o["actor"] for o in orders}
    assert actors == {"owner", "delegate"}
    assets = {o["base_asset"] for o in orders}
    assert assets == {"BTC", "ETH"}


# ═════════════════════════════════ IC-10 PNL ═════════════════════════════════

async def test_pnl_avco_realized_profit(client):
    """C-132/C-136: buy $600 (0.01) + buy $700 (0.01) + sell $680 (0.01) → realized +$30 (AVCO)."""
    user, headers, profile = await _owner_with_key(client, key_type=None)
    t0 = _naive_utcnow() - timedelta(hours=1)

    def order(side, usd, minutes):
        return TradeOrder(
            profile_id=profile["id"], exchange="demo", symbol="BTCUSDT", base_asset="BTC",
            side=side, usd_value=usd, amount=0.01, actor="owner", status="filled",
            created_at=t0 + timedelta(minutes=minutes),
        )

    await _insert(order("buy", 600.0, 0), order("buy", 700.0, 1), order("sell", 680.0, 2))

    r = await client.get(f"{API}/profiles/{profile['id']}/pnl", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["assets"]) == 1
    btc = body["assets"][0]
    assert btc["base_asset"] == "BTC"
    # AVCO: avg cost = (600+700)/0.02 = 65000/unit; sell at 68000/unit → +30 on 0.01
    assert btc["realized_pnl_usd"] == pytest.approx(30.0)
    assert btc["current_qty"] == pytest.approx(0.01)
    assert btc["avg_cost"] == pytest.approx(65000.0)
    assert btc["buy_count"] == 2 and btc["sell_count"] == 1
    assert body["total_realized_pnl_usd"] == pytest.approx(30.0)


async def test_pnl_foreign_profile_forbidden(client):
    """C-129: PnL of another user's profile → 403."""
    user, headers, profile = await _owner_with_key(client, key_type=None)
    mallory = await _seed_user("mallory@example.com")

    r = await client.get(f"{API}/profiles/{profile['id']}/pnl", headers=_auth(mallory))
    assert r.status_code == 403, r.text


# ═════════════════════════════════ IC-11 HISTORY ═════════════════════════════

async def test_history_returns_snapshots_and_days_filter_works(client):
    """C-140/C-141: default window (30d) hides old snapshots; days=365 includes them."""
    user, headers, profile = await _owner_with_key(client, key_type=None)
    now = _naive_utcnow()
    await _insert(
        PortfolioSnapshot(profile_id=profile["id"], total_usd=111.0,
                          created_at=now - timedelta(days=40)),
        PortfolioSnapshot(profile_id=profile["id"], total_usd=222.0,
                          created_at=now - timedelta(hours=1)),
    )

    r = await client.get(f"{API}/profiles/{profile['id']}/history/", headers=headers)
    assert r.status_code == 200, r.text
    points = r.json()
    assert [p["total_usd"] for p in points] == [222.0]

    r = await client.get(f"{API}/profiles/{profile['id']}/history/",
                         params={"days": 365}, headers=headers)
    points = r.json()
    assert [p["total_usd"] for p in points] == [111.0, 222.0]  # oldest → newest


async def test_history_foreign_profile_forbidden(client):
    """C-138: history of another user's profile → 403."""
    user, headers, profile = await _owner_with_key(client, key_type=None)
    mallory = await _seed_user("mallory@example.com")

    r = await client.get(f"{API}/profiles/{profile['id']}/history/", headers=_auth(mallory))
    assert r.status_code == 403, r.text


# ═════════════════════════════════ IC-12 WAITLIST ════════════════════════════

async def test_waitlist_signup_is_idempotent(client):
    """C-144/C-145/C-146/C-147: first POST → 201; duplicate email → 200 with SAME record."""
    r1 = await client.post(f"{API}/waitlist", json={"email": "Neo@Example.com", "plan": "premium"})
    assert r1.status_code == 201, r1.text
    assert r1.json()["email"] == "neo@example.com"  # normalized

    r2 = await client.post(f"{API}/waitlist", json={"email": "neo@example.com"})
    assert r2.status_code == 200, r2.text
    assert r2.json()["id"] == r1.json()["id"]

    r3 = await client.post(f"{API}/waitlist", json={"email": "not-an-email"})
    assert r3.status_code == 422, r3.text


# ═════════════════════════════════ IC-13 ADMIN ═══════════════════════════════

async def test_admin_stats_forbidden_for_non_admin(client):
    """C-149: free/premium users get 403 from /admin/stats."""
    user = await _seed_user("pleb@example.com", tier="premium")
    r = await client.get(f"{API}/admin/stats", headers=_auth(user))
    assert r.status_code == 403, r.text


async def test_admin_stats_counts_are_consistent(client):
    """C-151/C-152: admin sees consistent counts (revoked share links excluded)."""
    owner, headers, profile = await _owner_with_key(client, email="owner@example.com")
    active = await _mk_share(client, headers, profile["id"])
    revoked = await _mk_share(client, headers, profile["id"])
    assert (await client.delete(f"{API}/share/{revoked['id']}", headers=headers)).status_code == 204
    admin = await _seed_user("root@example.com", tier="admin")

    r = await client.get(f"{API}/admin/stats", headers=_auth(admin))
    assert r.status_code == 200, r.text
    stats = r.json()
    assert stats["users"] == 2
    assert stats["profiles"] == 1
    assert stats["exchange_keys"] == 1
    assert stats["active_share_links"] == 1, f"revoked link must not be counted (link {active['id']} active)"
    assert stats["exchanges"] == {"demo": 1}
    assert stats["tiers"] == {"free": 1, "admin": 1}


# ═════════════════════════════ IC-14 RATE LIMITING ═══════════════════════════

async def test_rate_limits_are_registered_on_endpoints(client):
    """C-048/C-083/C-117 (presence only): slowapi limiter installed; endpoints carry limits.

    (The 30/min & 10/min ceilings are not exhausted here on purpose — presence of the
    registered limits + app.state.limiter is asserted instead.)
    """
    assert getattr(app.state, "limiter", None) is not None

    share_limits = share_api.limiter._route_limits
    assert any("public_share_view" in name for name in share_limits), share_limits.keys()
    assert any("delegate_trade" in name for name in share_limits), share_limits.keys()

    portfolio_limits = portfolio_api.limiter._route_limits
    assert any("portfolio_for_profile" in name for name in portfolio_limits)
    assert any("aggregate_portfolio" in name for name in portfolio_limits)

    # The public share view is declared at 30/minute; portfolio at settings value (10/minute).
    view_key = next(n for n in share_limits if "public_share_view" in n)
    assert "30 per 1 minute" in [str(lim.limit) for lim in share_limits[view_key]]
    prof_key = next(n for n in portfolio_limits if "portfolio_for_profile" in n)
    assert "10 per 1 minute" in [str(lim.limit) for lim in portfolio_limits[prof_key]]

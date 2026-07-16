"""Seed deterministic demo data for local development, E2E tests and UI demos.

Usage (from backend/):
    DEMO_MODE=true DATABASE_URL=sqlite+aiosqlite:////tmp/coinhq-demo.db \
    JWT_SECRET=... ENCRYPTION_KEY=... uv run python scripts/seed_demo.py

Creates (idempotent — wipes and re-creates all tables first):
  Users:    demo@coinhq.dev (free), pro@coinhq.dev (premium), admin@coinhq.dev (admin)
  Profiles: demo→"Main Portfolio" (demo read_only+trade keys)
            pro →"Trading" (demo keys), "HODL" (demo-alt read_only)
  Share links on demo/Main:
    open+trade   — all show_* true, can_trade with BTC,ETH whitelist,
                   $500/order, $2000/24h, direction both
    masked       — hide amounts+exchange names, no trade, no follow
    sell-only    — can_trade, direction sell, no other limits
    expired      — expires in the past (must 410)
    revoked      — is_active false (must 404)
  Trade history on demo/Main (filled buys+sells → non-trivial P&L)
  Portfolio snapshots (14 days, both demo profiles)
  Waitlist entries

Prints a JSON blob with user JWTs and share tokens for E2E consumption.
"""

import asyncio
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import Base, engine  # noqa: E402
from app.core.security import create_access_token, encrypt  # noqa: E402
from app.models import (  # noqa: E402
    ExchangeKey,
    PortfolioSnapshot,
    Profile,
    ShareLink,
    TradeOrder,
    User,
    Waitlist,
)

Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

NOW = datetime.now(UTC)


def _key(profile_id: int, marker: str, key_type: str) -> ExchangeKey:
    return ExchangeKey(
        profile_id=profile_id,
        exchange="demo",
        key_type=key_type,
        encrypted_key=encrypt(f"demo-{marker}-{key_type}-key-12345678"),
        encrypted_secret=encrypt(f"demo-{marker}-secret-12345678"),
    )


def _assert_safe_target() -> None:
    """Refuse to run the destructive reset against anything but a demo/test DB.

    This script drops and recreates ALL tables, so guard against ever pointing it
    at a real database (e.g. a shell that already exports a production
    DATABASE_URL). Require DEMO_MODE AND a sqlite/clearly-demo URL.
    """
    url = settings.DATABASE_URL
    is_sqlite = url.startswith("sqlite")
    looks_demo = any(marker in url for marker in ("demo", "test", ":memory:"))
    if not settings.DEMO_MODE:
        raise SystemExit("Refusing to seed: DEMO_MODE is not enabled.")
    if not (is_sqlite or looks_demo):
        raise SystemExit(
            f"Refusing to run the destructive demo seed against {url!r}: "
            "use a sqlite/demo DATABASE_URL (name must contain 'demo' or 'test')."
        )


async def seed() -> dict:
    _assert_safe_target()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with Session() as db:
        demo = User(email="demo@coinhq.dev", name="Demo User", google_id="demo-google-1", tier="free")
        pro = User(email="pro@coinhq.dev", name="Pro User", google_id="demo-google-2", tier="premium")
        admin = User(email="admin@coinhq.dev", name="Admin", google_id="demo-google-3", tier="admin")
        db.add_all([demo, pro, admin])
        await db.flush()

        p_main = Profile(user_id=demo.id, name="Main Portfolio")
        p_trading = Profile(user_id=pro.id, name="Trading")
        p_hodl = Profile(user_id=pro.id, name="HODL")
        db.add_all([p_main, p_trading, p_hodl])
        await db.flush()

        db.add_all([
            _key(p_main.id, "main", "read_only"),
            _key(p_main.id, "main", "trade"),
            _key(p_trading.id, "main", "read_only"),
            _key(p_trading.id, "main", "trade"),
            _key(p_hodl.id, "alt", "read_only"),
        ])

        links = {
            "open_trade": ShareLink(
                profile_id=p_main.id, token=ShareLink.generate_token(),
                show_total_value=True, show_coin_amounts=True,
                show_exchange_names=True, show_allocation_pct=True,
                label="Danisman (trade)", allow_follow=True,
                can_trade=True, trade_direction="both",
                trade_allowed_coins="BTC,ETH",
                trade_max_per_order_usd=500.0, trade_daily_limit_usd=2000.0,
            ),
            "masked": ShareLink(
                profile_id=p_main.id, token=ShareLink.generate_token(),
                show_total_value=True, show_coin_amounts=False,
                show_exchange_names=False, show_allocation_pct=True,
                label="Muhasebeci", allow_follow=False, can_trade=False,
            ),
            "sell_only": ShareLink(
                profile_id=p_main.id, token=ShareLink.generate_token(),
                show_total_value=True, show_coin_amounts=True,
                show_exchange_names=True, show_allocation_pct=True,
                label="Sadece satis", allow_follow=True,
                can_trade=True, trade_direction="sell",
            ),
            "expired": ShareLink(
                profile_id=p_main.id, token=ShareLink.generate_token(),
                expires_at=NOW - timedelta(days=1), label="Suresi dolmus",
            ),
            "revoked": ShareLink(
                profile_id=p_main.id, token=ShareLink.generate_token(),
                is_active=False, label="Iptal edilmis",
            ),
        }
        db.add_all(links.values())
        await db.flush()

        # Trade history → AVCO P&L: buy 0.01 BTC @60k, buy 0.01 @70k (avg 65k),
        # sell 0.01 @68k → realized +30. Plus an ETH buy and a delegate trade.
        trades = [
            TradeOrder(profile_id=p_main.id, exchange="demo", symbol="BTCUSDT", base_asset="BTC",
                       side="buy", usd_value=600.0, amount=0.01, actor="owner", status="filled",
                       exchange_order_id="demo-hist-1"),
            TradeOrder(profile_id=p_main.id, exchange="demo", symbol="BTCUSDT", base_asset="BTC",
                       side="buy", usd_value=700.0, amount=0.01, actor="owner", status="filled",
                       exchange_order_id="demo-hist-2"),
            TradeOrder(profile_id=p_main.id, exchange="demo", symbol="BTCUSDT", base_asset="BTC",
                       side="sell", usd_value=680.0, amount=0.01, actor="owner", status="filled",
                       exchange_order_id="demo-hist-3"),
            TradeOrder(profile_id=p_main.id, exchange="demo", symbol="ETHUSDT", base_asset="ETH",
                       side="buy", usd_value=340.0, amount=0.1, actor="owner", status="filled",
                       exchange_order_id="demo-hist-4"),
            TradeOrder(profile_id=p_main.id, share_link_id=links["open_trade"].id,
                       exchange="demo", symbol="ETHUSDT", base_asset="ETH",
                       side="buy", usd_value=150.0, amount=0.044, actor="delegate", status="filled",
                       exchange_order_id="demo-hist-5"),
            TradeOrder(profile_id=p_main.id, exchange="demo", symbol="SOLUSDT", base_asset="SOL",
                       side="buy", usd_value=100.0, amount=None, actor="owner", status="failed",
                       error="Demo: insufficient balance"),
        ]
        # Spread created_at over the past days for a realistic history view
        for i, t in enumerate(trades):
            t.created_at = NOW - timedelta(days=len(trades) - i, hours=3)
        db.add_all(trades)

        # 14 days of snapshots per profile (gentle upward drift)
        for profile, base in ((p_main, 30_000.0), (p_trading, 12_000.0), (p_hodl, 3_000.0)):
            for d in range(14, 0, -1):
                drift = 1 + (14 - d) * 0.01 + (0.015 if d % 3 == 0 else -0.008)
                db.add(PortfolioSnapshot(
                    profile_id=profile.id,
                    total_usd=round(base * drift, 2),
                    created_at=NOW - timedelta(days=d),
                ))

        db.add_all([
            Waitlist(email="wait1@example.com", plan="premium", source="web"),
            Waitlist(email="wait2@example.com", plan="premium", source="web"),
        ])

        await db.commit()

        return {
            "users": {
                "demo": {"id": demo.id, "email": demo.email, "jwt": create_access_token(demo.id)},
                "pro": {"id": pro.id, "email": pro.email, "jwt": create_access_token(pro.id)},
                "admin": {"id": admin.id, "email": admin.email, "jwt": create_access_token(admin.id)},
            },
            "profiles": {"main": p_main.id, "trading": p_trading.id, "hodl": p_hodl.id},
            "share_tokens": {name: link.token for name, link in links.items()},
        }


if __name__ == "__main__":
    info = asyncio.run(seed())
    print(json.dumps(info, indent=2))

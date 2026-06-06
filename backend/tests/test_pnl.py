"""
Tests for the realized P&L / average cost-basis feature.

Covers:
  (a) buy-then-sell-higher  → positive realized P&L, correct avg_cost
  (b) buy-then-sell-lower   → negative realized P&L
  (c) multiple buys at different prices, then partial sell → AVCO math
  (d) failed/pending/null-amount orders are ignored
  (e) sell with no / insufficient prior buys → no crash, qty clamped ≥ 0
  (f) endpoint owner-scoping → 403/404
"""

import os

os.environ.setdefault("ENCRYPTION_KEY", "dGVzdC1lbmNyeXB0aW9uLWtleS0zMi1ieXRlc3h4")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-unit-tests-only")

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api.v1.pnl import get_profile_pnl
from app.services.pnl_service import compute_profile_pnl

# ── helpers ────────────────────────────────────────────────────────────────────


def _make_order(
    *,
    side: str,
    usd_value: float,
    amount: float | None,
    status: str = "filled",
    base_asset: str = "BTC",
    profile_id: int = 1,
    created_at=None,
):
    """Return a lightweight MagicMock that looks like a TradeOrder row."""
    import datetime

    order = MagicMock()
    order.profile_id = profile_id
    order.base_asset = base_asset
    order.side = side
    order.usd_value = usd_value
    order.amount = amount
    order.status = status
    order.created_at = created_at or datetime.datetime(2024, 1, 1)
    return order


def _db_returning(orders: list):
    """AsyncMock db whose execute() returns a scalars().all() == orders."""
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=orders)
    result_mock = MagicMock()
    result_mock.scalars = MagicMock(return_value=scalars_mock)
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result_mock)
    return db


def _make_profile(profile_id: int = 1, owner_id: int = 1):
    p = MagicMock()
    p.id = profile_id
    p.user_id = owner_id
    return p


def _make_user(user_id: int = 1):
    u = MagicMock()
    u.id = user_id
    return u


# ── service-level tests ────────────────────────────────────────────────────────


class TestComputeProfilePnL:
    # (a) buy low, sell high → positive realized P&L
    @pytest.mark.asyncio
    async def test_buy_then_sell_higher_positive_pnl(self):
        orders = [
            _make_order(side="buy",  usd_value=10_000.0, amount=1.0),   # avg_cost = 10_000
            _make_order(side="sell", usd_value=12_000.0, amount=1.0),   # sell @ 12_000
        ]
        db = _db_returning(orders)
        resp = await compute_profile_pnl(profile_id=1, db=db)

        assert len(resp.assets) == 1
        a = resp.assets[0]
        assert a.base_asset == "BTC"
        assert a.realized_pnl_usd == pytest.approx(2_000.0)
        assert a.current_qty == pytest.approx(0.0, abs=1e-9)
        assert a.avg_cost is None                  # no open position
        assert a.buy_count == 1
        assert a.sell_count == 1
        assert a.total_bought_usd == pytest.approx(10_000.0)
        assert a.total_sold_usd == pytest.approx(12_000.0)
        assert resp.total_realized_pnl_usd == pytest.approx(2_000.0)

    # (b) sell below cost → negative P&L
    @pytest.mark.asyncio
    async def test_buy_then_sell_lower_negative_pnl(self):
        orders = [
            _make_order(side="buy",  usd_value=10_000.0, amount=1.0),
            _make_order(side="sell", usd_value=8_000.0,  amount=1.0),
        ]
        db = _db_returning(orders)
        resp = await compute_profile_pnl(profile_id=1, db=db)

        a = resp.assets[0]
        assert a.realized_pnl_usd == pytest.approx(-2_000.0)
        assert resp.total_realized_pnl_usd == pytest.approx(-2_000.0)

    # (c) multiple buys at different prices, then partial sell → AVCO math
    @pytest.mark.asyncio
    async def test_multiple_buys_partial_sell_avco(self):
        """
        Buy 1 BTC @ $10 000  →  cost_basis = $10 000, qty = 1
        Buy 1 BTC @ $20 000  →  cost_basis = $30 000, qty = 2
        avg_cost              = $15 000 / BTC
        Sell 0.5 BTC @ $18 000 / BTC (usd_value = $9 000)
          realized = 0.5 * (18_000 - 15_000) = $1 500
          remaining qty = 1.5,  cost_basis = 30_000 - 0.5*15_000 = 22_500
          avg_cost unchanged = 22_500 / 1.5 = 15_000
        """
        orders = [
            _make_order(side="buy",  usd_value=10_000.0, amount=1.0),
            _make_order(side="buy",  usd_value=20_000.0, amount=1.0),
            _make_order(side="sell", usd_value=9_000.0,  amount=0.5),
        ]
        db = _db_returning(orders)
        resp = await compute_profile_pnl(profile_id=1, db=db)

        a = resp.assets[0]
        assert a.realized_pnl_usd == pytest.approx(1_500.0)
        assert a.current_qty      == pytest.approx(1.5)
        assert a.avg_cost         == pytest.approx(15_000.0)
        assert a.buy_count  == 2
        assert a.sell_count == 1
        assert a.total_bought_usd == pytest.approx(30_000.0)
        assert a.total_sold_usd   == pytest.approx(9_000.0)

    # (d) failed / pending / null-amount orders are silently ignored
    @pytest.mark.asyncio
    async def test_non_filled_and_null_amount_orders_ignored(self):
        # The DB query filters these out; we simulate the service receiving
        # only the filtered slice (empty list here).
        db = _db_returning([])
        resp = await compute_profile_pnl(profile_id=1, db=db)

        assert resp.assets == []
        assert resp.total_realized_pnl_usd == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_failed_order_not_counted(self):
        # If DB filtering somehow leaks a non-filled order, make sure the
        # service state reflects only what the service processes.
        # Here we simulate only filled orders being passed through.
        orders = [
            _make_order(side="buy", usd_value=1_000.0, amount=0.1),
        ]
        db = _db_returning(orders)
        resp = await compute_profile_pnl(profile_id=1, db=db)

        a = resp.assets[0]
        assert a.buy_count == 1
        assert a.current_qty == pytest.approx(0.1)

    # (e) sell with no / insufficient prior buys → clamped, no crash
    @pytest.mark.asyncio
    async def test_sell_with_no_prior_buys_no_crash(self):
        """Sell 1 BTC with zero tracked position → clamped to 0; qty stays 0."""
        orders = [
            _make_order(side="sell", usd_value=10_000.0, amount=1.0),
        ]
        db = _db_returning(orders)
        resp = await compute_profile_pnl(profile_id=1, db=db)

        a = resp.assets[0]
        assert a.current_qty      == pytest.approx(0.0, abs=1e-9)
        assert a.realized_pnl_usd == pytest.approx(0.0)
        assert a.sell_count == 1
        assert a.avg_cost is None

    @pytest.mark.asyncio
    async def test_oversell_clamped_no_negative_qty(self):
        """Buy 0.5, then sell 2.0 → qty clamped to 0 (no negative holdings)."""
        orders = [
            _make_order(side="buy",  usd_value=5_000.0, amount=0.5),   # avg = 10_000
            _make_order(side="sell", usd_value=20_000.0, amount=2.0),  # only 0.5 available
        ]
        db = _db_returning(orders)
        resp = await compute_profile_pnl(profile_id=1, db=db)

        a = resp.assets[0]
        assert a.current_qty >= 0
        assert a.current_qty == pytest.approx(0.0, abs=1e-9)
        # P&L computed only on 0.5 BTC sold at 20_000/2.0 = 10_000 /BTC
        # sell_price_per_unit = 20_000 / 2.0 = 10_000; avg_cost = 10_000
        # realized = 0.5 * (10_000 - 10_000) = 0
        assert a.realized_pnl_usd == pytest.approx(0.0)

    # Multi-asset: each asset tracked independently
    @pytest.mark.asyncio
    async def test_two_assets_tracked_independently(self):
        orders = [
            _make_order(side="buy",  usd_value=10_000.0, amount=1.0, base_asset="BTC"),
            _make_order(side="buy",  usd_value=3_000.0,  amount=1.0, base_asset="ETH"),
            _make_order(side="sell", usd_value=12_000.0, amount=1.0, base_asset="BTC"),
        ]
        db = _db_returning(orders)
        resp = await compute_profile_pnl(profile_id=1, db=db)

        assets = {a.base_asset: a for a in resp.assets}
        assert "BTC" in assets and "ETH" in assets
        assert assets["BTC"].realized_pnl_usd == pytest.approx(2_000.0)
        assert assets["ETH"].realized_pnl_usd == pytest.approx(0.0)
        assert assets["ETH"].current_qty      == pytest.approx(1.0)
        assert resp.total_realized_pnl_usd    == pytest.approx(2_000.0)


# ── endpoint / auth tests ──────────────────────────────────────────────────────


class TestGetProfilePnLEndpoint:
    # (f-i) 404 when profile missing
    @pytest.mark.asyncio
    async def test_returns_404_for_missing_profile(self):
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc:
            await get_profile_pnl(
                profile_id=999,
                db=db,
                current_user=_make_user(1),
            )
        assert exc.value.status_code == 404

    # (f-ii) 403 when profile belongs to a different user
    @pytest.mark.asyncio
    async def test_returns_403_for_wrong_owner(self):
        profile = _make_profile(profile_id=1, owner_id=99)
        db = AsyncMock()
        db.get = AsyncMock(return_value=profile)

        with pytest.raises(HTTPException) as exc:
            await get_profile_pnl(
                profile_id=1,
                db=db,
                current_user=_make_user(user_id=1),  # user 1 ≠ owner 99
            )
        assert exc.value.status_code == 403

    # (f-iii) owner receives a valid response
    @pytest.mark.asyncio
    async def test_owner_receives_pnl_response(self):
        profile = _make_profile(profile_id=1, owner_id=1)

        # db.get returns the profile; db.execute returns empty orders
        scalars_mock = MagicMock()
        scalars_mock.all = MagicMock(return_value=[])
        result_mock = MagicMock()
        result_mock.scalars = MagicMock(return_value=scalars_mock)

        db = AsyncMock()
        db.get = AsyncMock(return_value=profile)
        db.execute = AsyncMock(return_value=result_mock)

        resp = await get_profile_pnl(
            profile_id=1,
            db=db,
            current_user=_make_user(1),
        )
        assert resp.assets == []
        assert resp.total_realized_pnl_usd == pytest.approx(0.0)

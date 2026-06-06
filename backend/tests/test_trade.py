"""Tests for delegated/owner trading — limit engine, adapter trade-key + order, service."""

import os

os.environ.setdefault("ENCRYPTION_KEY", "dGVzdC1lbmNyeXB0aW9uLWtleS0zMi1ieXRlc3h4")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-unit-tests-only")

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.trade_limits import TradeNotAllowedError, check_delegate_trade


def _make_link(**kwargs):
    link = MagicMock()
    link.id = kwargs.get("id", 1)
    link.can_trade = kwargs.get("can_trade", True)
    link.trade_direction = kwargs.get("trade_direction", "both")
    link.trade_allowed_coins = kwargs.get("trade_allowed_coins", None)
    link.trade_max_per_order_usd = kwargs.get("trade_max_per_order_usd", None)
    link.trade_daily_limit_usd = kwargs.get("trade_daily_limit_usd", None)
    return link


# ── Limit engine ──────────────────────────────────────────────────────────────

class TestCheckDelegateTrade:
    def test_allows_within_limits(self):
        link = _make_link()
        check_delegate_trade(link, side="buy", base_asset="BTC", usd_value=100, spent_today_usd=0)

    def test_rejects_when_trading_disabled(self):
        link = _make_link(can_trade=False)
        with pytest.raises(TradeNotAllowedError):
            check_delegate_trade(link, side="buy", base_asset="BTC", usd_value=100, spent_today_usd=0)

    def test_buy_only_rejects_sell(self):
        link = _make_link(trade_direction="buy")
        with pytest.raises(TradeNotAllowedError):
            check_delegate_trade(link, side="sell", base_asset="BTC", usd_value=10, spent_today_usd=0)

    def test_sell_only_rejects_buy(self):
        link = _make_link(trade_direction="sell")
        with pytest.raises(TradeNotAllowedError):
            check_delegate_trade(link, side="buy", base_asset="BTC", usd_value=10, spent_today_usd=0)

    def test_whitelist_rejects_unlisted_coin(self):
        link = _make_link(trade_allowed_coins="BTC,ETH")
        with pytest.raises(TradeNotAllowedError):
            check_delegate_trade(link, side="buy", base_asset="DOGE", usd_value=10, spent_today_usd=0)

    def test_whitelist_allows_listed_coin_case_insensitive(self):
        link = _make_link(trade_allowed_coins="btc, eth")
        check_delegate_trade(link, side="buy", base_asset="ETH", usd_value=10, spent_today_usd=0)

    def test_per_order_limit_enforced(self):
        link = _make_link(trade_max_per_order_usd=50)
        with pytest.raises(TradeNotAllowedError):
            check_delegate_trade(link, side="buy", base_asset="BTC", usd_value=51, spent_today_usd=0)

    def test_daily_limit_enforced(self):
        link = _make_link(trade_daily_limit_usd=200)
        with pytest.raises(TradeNotAllowedError):
            check_delegate_trade(link, side="buy", base_asset="BTC", usd_value=100, spent_today_usd=150)

    def test_daily_limit_allows_within(self):
        link = _make_link(trade_daily_limit_usd=200)
        check_delegate_trade(link, side="buy", base_asset="BTC", usd_value=49, spent_today_usd=150)

    def test_rejects_non_positive_amount(self):
        link = _make_link()
        with pytest.raises(TradeNotAllowedError):
            check_delegate_trade(link, side="buy", base_asset="BTC", usd_value=0, spent_today_usd=0)


# ── Binance trade-key validation + order placement ────────────────────────────

class TestBinanceTrading:
    @pytest.mark.asyncio
    async def test_validate_trade_key_rejects_withdrawal(self):
        from app.exchanges.binance import BinanceAdapter

        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value={"canTrade": True, "enableWithdrawals": True})
        client = AsyncMock()
        client.get = AsyncMock(return_value=resp)

        adapter = BinanceAdapter("key123456", "secret123", http_client=client)
        with pytest.raises(ValueError, match="withdraw"):
            await adapter.validate_trade_key()

    @pytest.mark.asyncio
    async def test_validate_trade_key_rejects_non_trading(self):
        from app.exchanges.binance import BinanceAdapter

        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value={"canTrade": False, "enableWithdrawals": False})
        client = AsyncMock()
        client.get = AsyncMock(return_value=resp)

        adapter = BinanceAdapter("key123456", "secret123", http_client=client)
        with pytest.raises(ValueError, match="cannot trade"):
            await adapter.validate_trade_key()

    @pytest.mark.asyncio
    async def test_validate_trade_key_accepts_trade_only(self):
        from app.exchanges.binance import BinanceAdapter

        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value={
            "canTrade": True, "enableWithdrawals": False, "enableInternalTransfer": False,
        })
        client = AsyncMock()
        client.get = AsyncMock(return_value=resp)

        adapter = BinanceAdapter("key123456", "secret123", http_client=client)
        assert await adapter.validate_trade_key() is True

    @pytest.mark.asyncio
    async def test_place_order_uses_quote_qty_market(self):
        from app.exchanges.binance import BinanceAdapter

        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value={"orderId": 555, "executedQty": "0.001"})
        client = AsyncMock()
        client.post = AsyncMock(return_value=resp)

        adapter = BinanceAdapter("key123456", "secret123", http_client=client)
        result = await adapter.place_order("btc", "buy", 100.0)

        assert result["orderId"] == 555
        _, kwargs = client.post.call_args
        params = kwargs["params"]
        assert params["symbol"] == "BTCUSDT"
        assert params["side"] == "BUY"
        assert params["type"] == "MARKET"
        assert params["quoteOrderQty"] == 100.0
        assert "signature" in params

    @pytest.mark.asyncio
    async def test_place_order_rejects_bad_side(self):
        from app.exchanges.binance import BinanceAdapter

        adapter = BinanceAdapter("key123456", "secret123", http_client=AsyncMock())
        with pytest.raises(ValueError):
            await adapter.place_order("BTC", "hodl", 100.0)


# ── Trade service ─────────────────────────────────────────────────────────────

def _make_profile(profile_id=1):
    p = MagicMock()
    p.id = profile_id
    return p


def _trade_key():
    key = MagicMock()
    key.encrypted_key = "enc_key"
    key.encrypted_secret = "enc_secret"
    return key


def _db_with_trade_key(key):
    """db.execute returns a result whose scalar_one_or_none() == key."""
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=key)
    db.execute = AsyncMock(return_value=result)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


class TestOtherExchangeTrading:
    def _post_client(self, payload):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value=payload)
        client = AsyncMock()
        client.post = AsyncMock(return_value=resp)
        return client

    @pytest.mark.asyncio
    async def test_bybit_place_order_uses_quote_market_unit(self):
        from app.exchanges.bybit import BybitAdapter

        client = self._post_client({"retCode": 0, "result": {"orderId": "x"}})
        adapter = BybitAdapter("key123456", "secret123", http_client=client)
        await adapter.place_order("btc", "buy", 100.0)

        body = json.loads(client.post.call_args.kwargs["content"])
        assert body["category"] == "spot"
        assert body["symbol"] == "BTCUSDT"
        assert body["side"] == "Buy"
        assert body["orderType"] == "Market"
        assert body["marketUnit"] == "quoteCoin"
        assert body["qty"] == "100.0"

    @pytest.mark.asyncio
    async def test_bybit_validate_trade_key_rejects_withdrawal(self):
        from app.exchanges.bybit import BybitAdapter

        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value={"result": {"readOnly": "0", "permissions": {"Withdraw": ["x"]}}})
        client = AsyncMock()
        client.get = AsyncMock(return_value=resp)
        adapter = BybitAdapter("key123456", "secret123", http_client=client)
        with pytest.raises(ValueError, match="withdraw"):
            await adapter.validate_trade_key()

    @pytest.mark.asyncio
    async def test_okx_place_order_quote_ccy_market(self):
        from app.exchanges.okx import OKXAdapter

        client = self._post_client({"code": "0", "data": [{"ordId": "1"}]})
        adapter = OKXAdapter("key123456", "secret123", http_client=client)
        await adapter.place_order("eth", "sell", 250.0)

        body = json.loads(client.post.call_args.kwargs["content"])
        assert body["instId"] == "ETH-USDT"
        assert body["ordType"] == "market"
        assert body["side"] == "sell"
        assert body["tgtCcy"] == "quote_ccy"

    @pytest.mark.asyncio
    async def test_okx_validate_trade_key_rejects_withdrawal(self):
        from app.exchanges.okx import OKXAdapter

        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value={"data": [{"perm": "read_only,trade,withdraw"}]})
        client = AsyncMock()
        client.get = AsyncMock(return_value=resp)
        adapter = OKXAdapter("key123456", "secret123", http_client=client)
        with pytest.raises(ValueError, match="withdraw"):
            await adapter.validate_trade_key()

    @pytest.mark.asyncio
    async def test_gateio_place_order_buy_uses_quote_amount(self):
        from app.exchanges.gateio import GateioAdapter

        client = self._post_client({"id": "1", "status": "closed"})
        adapter = GateioAdapter("key123456", "secret123", http_client=client)
        await adapter.place_order("btc", "buy", 100.0)

        body = json.loads(client.post.call_args.kwargs["content"])
        assert body["currency_pair"] == "BTC_USDT"
        assert body["type"] == "market"
        assert body["side"] == "buy"
        assert body["amount"] == "100.0"

    @pytest.mark.asyncio
    async def test_gateio_place_order_sell_uses_base_qty_from_price(self):
        from app.exchanges.gateio import GateioAdapter

        client = self._post_client({"id": "1"})
        adapter = GateioAdapter("key123456", "secret123", http_client=client)
        await adapter.place_order("btc", "sell", 100.0, price=50000.0)

        body = json.loads(client.post.call_args.kwargs["content"])
        assert body["side"] == "sell"
        assert body["amount"] == "0.002"  # 100 / 50000

    @pytest.mark.asyncio
    async def test_kraken_place_order_requires_price(self):
        from app.exchanges.kraken import KrakenAdapter

        adapter = KrakenAdapter("key123456", "c2VjcmV0", http_client=AsyncMock())
        with pytest.raises(ValueError, match="price"):
            await adapter.place_order("BTC", "sell", 100.0, price=None)

    def test_factory_supports_gateio(self):
        from app.exchanges.factory import SUPPORTED_EXCHANGES, get_adapter
        from app.exchanges.gateio import GateioAdapter

        assert "gateio" in SUPPORTED_EXCHANGES
        assert isinstance(get_adapter("gateio", "k", "s"), GateioAdapter)


class TestExecuteTrade:
    @pytest.mark.asyncio
    async def test_rejects_without_trade_key(self):
        from app.services import trade_service

        db = _db_with_trade_key(None)
        with pytest.raises(HTTPException) as exc:
            await trade_service.execute_trade(
                db, profile=_make_profile(), exchange="binance", side="buy",
                base_asset="BTC", usd_amount=100, actor="owner",
            )
        assert exc.value.status_code == 400
        assert "trade key" in exc.value.detail.lower()

    @pytest.mark.asyncio
    async def test_rejects_non_positive_amount(self):
        from app.services import trade_service

        db = _db_with_trade_key(_trade_key())
        with pytest.raises(HTTPException) as exc:
            await trade_service.execute_trade(
                db, profile=_make_profile(), exchange="binance", side="buy",
                base_asset="BTC", usd_amount=0, actor="owner",
            )
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_owner_trade_success_logs_filled_order(self):
        from app.services import trade_service

        db = _db_with_trade_key(_trade_key())
        adapter = AsyncMock()
        adapter.place_order = AsyncMock(return_value={"orderId": 1, "executedQty": "0.002"})

        with patch.object(trade_service, "get_adapter", return_value=adapter):
            with patch.object(trade_service, "decrypt", side_effect=lambda x: f"dec_{x}"):
                with patch.object(trade_service, "get_usd_prices", AsyncMock(return_value={"BTC": 50000.0})):
                    order = await trade_service.execute_trade(
                        db, profile=_make_profile(), exchange="binance", side="buy",
                        base_asset="btc", usd_amount=100, actor="owner",
                    )
        assert order.status == "filled"
        assert order.side == "buy"
        assert order.base_asset == "BTC"
        assert order.actor == "owner"
        adapter.place_order.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delegate_trade_blocked_by_limit_does_not_place_order(self):
        from app.services import trade_service

        db = _db_with_trade_key(_trade_key())
        link = _make_link(trade_max_per_order_usd=50)
        adapter = AsyncMock()
        adapter.place_order = AsyncMock()

        with patch.object(trade_service, "get_adapter", return_value=adapter):
            with patch.object(trade_service, "decrypt", side_effect=lambda x: x):
                with patch.object(trade_service, "spent_today_usd", AsyncMock(return_value=0.0)):
                    with pytest.raises(HTTPException) as exc:
                        await trade_service.execute_trade(
                            db, profile=_make_profile(), exchange="binance", side="buy",
                            base_asset="BTC", usd_amount=100, actor="delegate", share_link=link,
                        )
        assert exc.value.status_code == 403
        adapter.place_order.assert_not_called()

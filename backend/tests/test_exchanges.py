"""Tests for all exchange adapters — balance retrieval, filtering, and key validation."""

import os

os.environ.setdefault("ENCRYPTION_KEY", "dGVzdC1lbmNyeXB0aW9uLWtleS0zMi1ieXRlc3h4")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-unit-tests-only")

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.exchanges.binance import BinanceAdapter
from app.exchanges.binancetr import BinanceTRAdapter
from app.exchanges.bybit import BybitAdapter
from app.exchanges.coinbase import CoinbaseAdapter
from app.exchanges.kraken import KrakenAdapter, _normalize_kraken_asset
from app.exchanges.okx import OKXAdapter


def _make_mock_response(payload: dict) -> MagicMock:
    mock_response = MagicMock()
    mock_response.json.return_value = payload
    mock_response.raise_for_status = MagicMock()
    mock_response.status_code = 200
    return mock_response


def _make_mock_client(response, method: str = "get") -> AsyncMock:
    mock_client = AsyncMock()
    setattr(mock_client, method, AsyncMock(return_value=response))
    if method != "get":
        mock_client.get = AsyncMock(return_value=response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


# ══════════════════════════════════════════════════════════════════════════════
# BINANCE
# ══════════════════════════════════════════════════════════════════════════════

class TestBinanceAdapter:
    @pytest.mark.asyncio
    async def test_get_balances_returns_non_zero(self):
        adapter = BinanceAdapter("key", "secret")
        payload = {
            "balances": [
                {"asset": "BTC", "free": "0.5", "locked": "0.0"},
                {"asset": "USDT", "free": "1000.0", "locked": "0.0"},
            ]
        }
        mock_client = _make_mock_client(_make_mock_response(payload))
        with patch("app.exchanges.binance.httpx.AsyncClient", return_value=mock_client):
            balances = await adapter.get_balances()

        assert len(balances) == 2
        btc = next(b for b in balances if b.asset == "BTC")
        assert btc.free == 0.5

    @pytest.mark.asyncio
    async def test_get_balances_filters_zero(self):
        adapter = BinanceAdapter("key", "secret")
        payload = {"balances": [{"asset": "BTC", "free": "0.0", "locked": "0.0"}]}
        mock_client = _make_mock_client(_make_mock_response(payload))
        with patch("app.exchanges.binance.httpx.AsyncClient", return_value=mock_client):
            balances = await adapter.get_balances()
        assert len(balances) == 0

    @pytest.mark.asyncio
    async def test_validate_key_accepts_read_only(self):
        adapter = BinanceAdapter("key", "secret")
        payload = {"balances": [], "enableWithdrawals": False, "enableInternalTransfer": False}
        mock_client = _make_mock_client(_make_mock_response(payload))
        with patch("app.exchanges.binance.httpx.AsyncClient", return_value=mock_client):
            assert await adapter.validate_key() is True

    @pytest.mark.asyncio
    async def test_validate_key_rejects_withdrawals(self):
        adapter = BinanceAdapter("key", "secret")
        payload = {"enableWithdrawals": True, "enableInternalTransfer": False}
        mock_client = _make_mock_client(_make_mock_response(payload))
        with patch("app.exchanges.binance.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ValueError, match="Write permissions"):
                await adapter.validate_key()

    @pytest.mark.asyncio
    async def test_validate_key_rejects_internal_transfer(self):
        adapter = BinanceAdapter("key", "secret")
        payload = {"enableWithdrawals": False, "enableInternalTransfer": True}
        mock_client = _make_mock_client(_make_mock_response(payload))
        with patch("app.exchanges.binance.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ValueError, match="Write permissions"):
                await adapter.validate_key()


# ══════════════════════════════════════════════════════════════════════════════
# BYBIT
# ══════════════════════════════════════════════════════════════════════════════

class TestBybitAdapter:
    @pytest.mark.asyncio
    async def test_get_balances_returns_non_zero(self):
        adapter = BybitAdapter("key", "secret")
        payload = {
            "result": {
                "list": [
                    {
                        "coin": [
                            {"coin": "BTC", "walletBalance": "0.5", "locked": "0.1"},
                            {"coin": "ETH", "walletBalance": "0.0", "locked": "0.0"},
                        ]
                    }
                ]
            }
        }
        mock_client = _make_mock_client(_make_mock_response(payload))
        with patch("app.exchanges.bybit.httpx.AsyncClient", return_value=mock_client):
            balances = await adapter.get_balances()

        assert len(balances) == 1
        assert balances[0].asset == "BTC"
        assert balances[0].total == 0.5
        assert balances[0].locked == 0.1

    @pytest.mark.asyncio
    async def test_get_balances_filters_zero(self):
        adapter = BybitAdapter("key", "secret")
        payload = {
            "result": {
                "list": [{"coin": [{"coin": "USDT", "walletBalance": "0.0", "locked": "0.0"}]}]
            }
        }
        mock_client = _make_mock_client(_make_mock_response(payload))
        with patch("app.exchanges.bybit.httpx.AsyncClient", return_value=mock_client):
            balances = await adapter.get_balances()
        assert len(balances) == 0

    @pytest.mark.asyncio
    async def test_validate_key_accepts_read_only(self):
        adapter = BybitAdapter("key", "secret")
        payload = {"result": {"readOnly": "1"}}
        mock_client = _make_mock_client(_make_mock_response(payload))
        with patch("app.exchanges.bybit.httpx.AsyncClient", return_value=mock_client):
            assert await adapter.validate_key() is True

    @pytest.mark.asyncio
    async def test_validate_key_rejects_write(self):
        adapter = BybitAdapter("key", "secret")
        payload = {"result": {"readOnly": "0"}}
        mock_client = _make_mock_client(_make_mock_response(payload))
        with patch("app.exchanges.bybit.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ValueError, match="Write permissions"):
                await adapter.validate_key()


# ══════════════════════════════════════════════════════════════════════════════
# OKX
# ══════════════════════════════════════════════════════════════════════════════

class TestOKXAdapter:
    @pytest.mark.asyncio
    async def test_get_balances_returns_non_zero(self):
        adapter = OKXAdapter("key", "secret|passphrase")
        payload = {
            "data": [
                {
                    "details": [
                        {"ccy": "BTC", "cashBal": "1.5", "frozenBal": "0.2"},
                        {"ccy": "ETH", "cashBal": "0.0", "frozenBal": "0.0"},
                    ]
                }
            ]
        }
        mock_client = _make_mock_client(_make_mock_response(payload))
        with patch("app.exchanges.okx.httpx.AsyncClient", return_value=mock_client):
            balances = await adapter.get_balances()

        assert len(balances) == 1
        assert balances[0].asset == "BTC"
        assert balances[0].total == 1.5
        assert balances[0].locked == 0.2

    @pytest.mark.asyncio
    async def test_parses_passphrase_from_secret(self):
        adapter = OKXAdapter("key", "mysecret|mypassphrase")
        assert adapter.api_secret == "mysecret"
        assert adapter.passphrase == "mypassphrase"

    @pytest.mark.asyncio
    async def test_validate_key_accepts_read_only(self):
        adapter = OKXAdapter("key", "secret|pass")
        payload = {"data": [{"perm": "read_only"}]}
        mock_client = _make_mock_client(_make_mock_response(payload))
        with patch("app.exchanges.okx.httpx.AsyncClient", return_value=mock_client):
            assert await adapter.validate_key() is True

    @pytest.mark.asyncio
    async def test_validate_key_rejects_trade_perm(self):
        adapter = OKXAdapter("key", "secret|pass")
        payload = {"data": [{"perm": "read_only,trade"}]}
        mock_client = _make_mock_client(_make_mock_response(payload))
        with patch("app.exchanges.okx.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ValueError, match="Write permissions"):
                await adapter.validate_key()


# ══════════════════════════════════════════════════════════════════════════════
# COINBASE
# ══════════════════════════════════════════════════════════════════════════════

class TestCoinbaseAdapter:
    @pytest.mark.asyncio
    async def test_get_balances_returns_non_zero(self):
        adapter = CoinbaseAdapter("key", "secret")
        payload = {
            "accounts": [
                {
                    "currency": "BTC",
                    "available_balance": {"value": "0.3"},
                    "hold": {"value": "0.05"},
                },
                {
                    "currency": "USD",
                    "available_balance": {"value": "0.0"},
                    "hold": {"value": "0.0"},
                },
            ]
        }
        mock_client = _make_mock_client(_make_mock_response(payload))
        with patch("app.exchanges.coinbase.httpx.AsyncClient", return_value=mock_client):
            balances = await adapter.get_balances()

        assert len(balances) == 1
        assert balances[0].asset == "BTC"
        assert balances[0].free == 0.3
        assert balances[0].locked == 0.05

    @pytest.mark.asyncio
    async def test_get_balances_filters_zero(self):
        adapter = CoinbaseAdapter("key", "secret")
        payload = {
            "accounts": [
                {"currency": "ETH", "available_balance": {"value": "0.0"}, "hold": {"value": "0.0"}}
            ]
        }
        mock_client = _make_mock_client(_make_mock_response(payload))
        with patch("app.exchanges.coinbase.httpx.AsyncClient", return_value=mock_client):
            balances = await adapter.get_balances()
        assert len(balances) == 0

    @pytest.mark.asyncio
    async def test_validate_key_rejects_401(self):
        adapter = CoinbaseAdapter("key", "secret")
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_client = _make_mock_client(mock_response)
        with patch("app.exchanges.coinbase.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ValueError, match="Invalid API key"):
                await adapter.validate_key()


# ══════════════════════════════════════════════════════════════════════════════
# KRAKEN
# ══════════════════════════════════════════════════════════════════════════════

class TestKrakenAdapter:
    @pytest.mark.asyncio
    async def test_get_balances_returns_non_zero(self):
        # Kraken uses base64 secret
        import base64

        secret = base64.b64encode(b"test_secret_key_pad").decode()
        adapter = KrakenAdapter("key", secret)
        payload = {"error": [], "result": {"XXBT": "0.5", "ZUSD": "100.0", "XETH": "0.0"}}
        mock_client = _make_mock_client(_make_mock_response(payload), method="post")
        mock_client.post = AsyncMock(return_value=_make_mock_response(payload))
        with patch("app.exchanges.kraken.httpx.AsyncClient", return_value=mock_client):
            balances = await adapter.get_balances()

        assert len(balances) == 2
        assets = {b.asset for b in balances}
        assert "BTC" in assets  # XXBT normalized
        assert "USD" in assets  # ZUSD normalized

    @pytest.mark.asyncio
    async def test_validate_key_accepts_permission_denied(self):
        import base64

        secret = base64.b64encode(b"test_secret_key_pad").decode()
        adapter = KrakenAdapter("key", secret)
        payload = {"error": ["EGeneral:Permission denied"]}
        mock_resp = _make_mock_response(payload)
        mock_resp.status_code = 200
        mock_client = _make_mock_client(mock_resp, method="post")
        mock_client.post = AsyncMock(return_value=mock_resp)
        with patch("app.exchanges.kraken.httpx.AsyncClient", return_value=mock_client):
            assert await adapter.validate_key() is True


class TestKrakenAssetNormalization:
    def test_xxbt_to_btc(self):
        assert _normalize_kraken_asset("XXBT") == "BTC"

    def test_xeth_to_eth(self):
        assert _normalize_kraken_asset("XETH") == "ETH"

    def test_zusd_to_usd(self):
        assert _normalize_kraken_asset("ZUSD") == "USD"

    def test_unknown_passthrough(self):
        assert _normalize_kraken_asset("SOL") == "SOL"

    def test_four_char_x_prefix_stripped(self):
        assert _normalize_kraken_asset("XDAO") == "DAO"


# ══════════════════════════════════════════════════════════════════════════════
# BINANCE TR
# ══════════════════════════════════════════════════════════════════════════════

class TestBinanceTRAdapter:
    @pytest.mark.asyncio
    async def test_get_balances_returns_non_zero(self):
        adapter = BinanceTRAdapter("key", "secret")
        payload = {
            "data": {
                "accountAssets": [
                    {"asset": "BTC", "free": "0.5", "locked": "0.1"},
                    {"asset": "ETH", "free": "0.0", "locked": "0.0"},
                ]
            }
        }
        mock_client = _make_mock_client(_make_mock_response(payload))
        with patch("app.exchanges.binancetr.httpx.AsyncClient", return_value=mock_client):
            balances = await adapter.get_balances()

        assert len(balances) == 1
        assert balances[0].asset == "BTC"
        assert balances[0].total == 0.6

    @pytest.mark.asyncio
    async def test_get_balances_filters_zero(self):
        adapter = BinanceTRAdapter("key", "secret")
        payload = {
            "data": {"accountAssets": [{"asset": "USDT", "free": "0.0", "locked": "0.0"}]}
        }
        mock_client = _make_mock_client(_make_mock_response(payload))
        with patch("app.exchanges.binancetr.httpx.AsyncClient", return_value=mock_client):
            balances = await adapter.get_balances()
        assert len(balances) == 0

    @pytest.mark.asyncio
    async def test_validate_key_accepts_success(self):
        adapter = BinanceTRAdapter("key", "secret")
        payload = {"code": 0, "data": {"accountAssets": []}}
        mock_client = _make_mock_client(_make_mock_response(payload))
        with patch("app.exchanges.binancetr.httpx.AsyncClient", return_value=mock_client):
            assert await adapter.validate_key() is True

    @pytest.mark.asyncio
    async def test_validate_key_rejects_error_code(self):
        adapter = BinanceTRAdapter("key", "secret")
        payload = {"code": -1, "msg": "Invalid API key"}
        mock_client = _make_mock_client(_make_mock_response(payload))
        with patch("app.exchanges.binancetr.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ValueError, match="Binance TR API error"):
                await adapter.validate_key()


# ══════════════════════════════════════════════════════════════════════════════
# BASE ADAPTER
# ══════════════════════════════════════════════════════════════════════════════

class TestBaseAdapter:
    def test_mask_key_short(self):
        adapter = BinanceAdapter("abc", "secret")
        assert adapter._mask_key() == "***"

    def test_mask_key_long(self):
        adapter = BinanceAdapter("abcdefghijklmnop", "secret")
        assert adapter._mask_key() == "abcdef..."


# ══════════════════════════════════════════════════════════════════════════════
# VENUE-LOCAL PRICING
# ══════════════════════════════════════════════════════════════════════════════

class TestVenueLocalPricing:
    """`get_prices` makes an adapter authoritative for what it holds, so a wrong
    or missing quote is a mispriced portfolio, not a cosmetic issue."""

    @pytest.mark.asyncio
    async def test_okx_reads_spot_usdt_tickers(self):
        adapter = OKXAdapter("key", "secret")
        payload = {"data": [
            {"instId": "BTC-USDT", "last": "63108.6"},
            {"instId": "ADA-USDT", "last": "0.1908"},
            {"instId": "BTC-USDC", "last": "63100.0"},   # wrong quote currency
            {"instId": "ETH-USDT", "last": "1857.68"},   # not requested
        ]}
        mock_client = _make_mock_client(_make_mock_response(payload))
        with patch("app.exchanges.okx.httpx.AsyncClient", return_value=mock_client):
            prices = await adapter.get_prices(["BTC", "ADA"])
        assert prices == {"BTC": 63108.6, "ADA": 0.1908}

    @pytest.mark.asyncio
    async def test_bybit_reads_spot_usdt_tickers(self):
        adapter = BybitAdapter("key", "secret")
        payload = {"result": {"list": [
            {"symbol": "BTCUSDT", "lastPrice": "63044.7"},
            {"symbol": "SOLUSDT", "lastPrice": "72.88"},
            {"symbol": "BTCUSDC", "lastPrice": "63040.0"},
        ]}}
        mock_client = _make_mock_client(_make_mock_response(payload))
        with patch("app.exchanges.bybit.httpx.AsyncClient", return_value=mock_client):
            prices = await adapter.get_prices(["BTC", "SOL"])
        assert prices == {"BTC": 63044.7, "SOL": 72.88}

    @pytest.mark.asyncio
    async def test_kraken_resolves_internal_pair_codes_and_prefers_dollars(self):
        adapter = KrakenAdapter("key", "secret")
        pairs = {"result": {
            "XXBTZUSD": {"base": "XXBT", "quote": "ZUSD"},
            "XBTUSDT": {"base": "XXBT", "quote": "USDT"},
            "ADAEUR": {"base": "ADA", "quote": "ZEUR"},
            "ADAUSD": {"base": "ADA", "quote": "ZUSD"},
        }}
        tickers = {"result": {
            "XXBTZUSD": {"c": ["63044.7", "0.01"]},
            "XBTUSDT": {"c": ["63100.0", "0.01"]},
            "ADAEUR": {"c": ["0.175", "10"]},
            "ADAUSD": {"c": ["0.190577", "10"]},
        }}
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[
            _make_mock_response(pairs), _make_mock_response(tickers)
        ])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        with patch("app.exchanges.kraken.httpx.AsyncClient", return_value=mock_client):
            prices = await adapter.get_prices(["BTC", "ADA"])
        # XXBT resolves to BTC, the dollar pair beats the USDT one, EUR is ignored.
        assert prices == {"BTC": 63044.7, "ADA": 0.190577}

    @pytest.mark.asyncio
    async def test_coinbase_inverts_usd_exchange_rates(self):
        adapter = CoinbaseAdapter("key", "secret")
        payload = {"data": {"currency": "USD", "rates": {
            "BTC": "0.0000158588",     # BTC per dollar
            "ADA": "5.2438384897",
            "DEAD": "0",               # no market
        }}}
        mock_client = _make_mock_client(_make_mock_response(payload))
        with patch("app.exchanges.coinbase.httpx.AsyncClient", return_value=mock_client):
            prices = await adapter.get_prices(["BTC", "ADA", "DEAD", "MISSING"])
        assert prices["BTC"] == pytest.approx(63056.5, rel=1e-4)
        assert prices["ADA"] == pytest.approx(0.19070, rel=1e-4)
        assert "DEAD" not in prices, "a zero rate is no quote, not a free coin"
        assert "MISSING" not in prices

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "adapter_cls,module",
        [
            (OKXAdapter, "app.exchanges.okx"),
            (BybitAdapter, "app.exchanges.bybit"),
            (KrakenAdapter, "app.exchanges.kraken"),
            (CoinbaseAdapter, "app.exchanges.coinbase"),
        ],
    )
    async def test_unreachable_venue_yields_no_opinion(self, adapter_cls, module):
        """Never raise: an empty result hands the venue back to the global lookup."""
        adapter = adapter_cls("key", "secret")
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("connection reset"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        with patch(f"{module}.httpx.AsyncClient", return_value=mock_client):
            assert await adapter.get_prices(["BTC"]) == {}

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "adapter_cls", [OKXAdapter, BybitAdapter, KrakenAdapter, CoinbaseAdapter]
    )
    async def test_no_assets_makes_no_request(self, adapter_cls):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=AssertionError("should not be called"))
        adapter = adapter_cls("key", "secret", http_client=mock_client)
        assert await adapter.get_prices([]) == {}

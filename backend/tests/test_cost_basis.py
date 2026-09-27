"""Average buy price per coin — adapter fills parsing, AVCO maths, service, endpoint.

All HTTP is mocked; nothing here touches the network.
"""

import os

os.environ.setdefault("ENCRYPTION_KEY", "dGVzdC1lbmNyeXB0aW9uLWtleS0zMi1ieXRlc3h4")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-unit-tests-only")

from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, urlparse

import pytest

from app.exchanges.base import ExchangeAdapter, Fill
from app.exchanges.binance import BinanceAdapter
from app.exchanges.binancetr import BinanceTRAdapter
from app.exchanges.bybit import BybitAdapter
from app.exchanges.coinbase import CoinbaseAdapter
from app.exchanges.demo import DemoAdapter
from app.exchanges.gateio import GateioAdapter
from app.exchanges.kraken import KrakenAdapter
from app.exchanges.okx import OKXAdapter
from app.schemas.portfolio import Balance, ExchangeBalance, PortfolioResponse
from app.services import cost_basis_service
from app.services.cost_basis_service import compute_avco, get_cost_basis


def _resp(payload, status: int = 200) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    r.json.return_value = payload
    r.raise_for_status = MagicMock()
    if status >= 400:
        r.raise_for_status.side_effect = RuntimeError(f"HTTP {status}")
    return r


def _client(handler, method: str = "get") -> AsyncMock:
    """A fake httpx client whose GET/POST is answered by `handler(url, kwargs)`."""
    client = AsyncMock()
    calls: list = []

    async def _call(url, **kwargs):
        calls.append((url, kwargs))
        return handler(url, kwargs)

    setattr(client, method, AsyncMock(side_effect=_call))
    if method != "get":
        client.get = AsyncMock(side_effect=_call)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.calls = calls
    return client


def _query(url: str, kwargs: dict) -> dict[str, str]:
    q = {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}
    q.update({k: str(v) for k, v in (kwargs.get("params") or {}).items()})
    return q


# ══════════════════════════════════════════════════════════════════════════════
# Base contract
# ══════════════════════════════════════════════════════════════════════════════

class _Bare(ExchangeAdapter):
    async def get_balances(self):
        return []

    async def validate_key(self):
        return True


async def test_default_get_fills_is_unsupported():
    assert await _Bare("k", "s").get_fills(["BTC"]) is None


async def test_binancetr_is_unsupported():
    assert await BinanceTRAdapter("k", "s").get_fills(["BTC"]) is None


# ══════════════════════════════════════════════════════════════════════════════
# Binance
# ══════════════════════════════════════════════════════════════════════════════

def _binance_trade(tid, qty, quote_qty, buyer=True, fee="0", fee_asset="BNB", ts=1_700_000_000_000):
    return {
        "symbol": "UNIUSDT", "id": tid, "orderId": 1, "price": "5", "qty": str(qty),
        "quoteQty": str(quote_qty), "commission": fee, "commissionAsset": fee_asset,
        "time": ts, "isBuyer": buyer, "isMaker": False,
    }


async def test_binance_fills_skip_missing_symbols_and_parse():
    def handler(url, kwargs):
        q = _query(url, kwargs)
        assert "signature" in q and "timestamp" in q
        if q["symbol"] == "UNIUSDT":
            return _resp([
                _binance_trade(1, 10, 50, fee="0.01", fee_asset="UNI"),
                _binance_trade(2, 4, 24, buyer=False, fee="0.02", fee_asset="USDT"),
            ])
        return _resp({"code": -1121, "msg": "Invalid symbol."}, status=400)

    client = _client(handler)
    adapter = BinanceAdapter("key", "secret", http_client=client)
    fills = await adapter.get_fills(["UNI"])

    assert fills is not None and len(fills) == 2
    buy, sell = fills
    assert buy == Fill("UNI", "buy", 10.0, "USDT", 50.0, "UNI", 0.01, 1_700_000_000_000)
    assert sell.side == "sell" and sell.fee_asset == "USDT" and sell.fee_qty == 0.02
    # One call per quote (USDT, USDC, FDUSD); the two invalid symbols were skipped.
    symbols = [_query(u, k)["symbol"] for u, k in client.calls]
    assert symbols == ["UNIUSDT", "UNIUSDC", "UNIFDUSD"]


async def test_binance_fills_page_forward_by_from_id():
    pages = {0: [_binance_trade(i, 1, 5) for i in range(1000)], 1000: [_binance_trade(1000, 1, 5)]}

    def handler(url, kwargs):
        q = _query(url, kwargs)
        if q["symbol"] != "UNIUSDT":
            return _resp({}, status=400)
        return _resp(pages[int(q["fromId"])])

    client = _client(handler)
    fills = await BinanceAdapter("k", "s", http_client=client).get_fills(["UNI"])
    assert len(fills) == 1001
    from_ids = [_query(u, k)["fromId"] for u, k in client.calls if _query(u, k)["symbol"] == "UNIUSDT"]
    assert from_ids == ["0", "1000"]


async def test_binance_fills_respect_call_budget():
    client = _client(lambda url, kwargs: _resp([_binance_trade(1, 1, 5)]))
    assets = [f"A{i}" for i in range(30)]  # 90 symbol combos > budget
    fills = await BinanceAdapter("k", "s", http_client=client).get_fills(assets)
    assert fills is not None
    assert len(client.calls) == 40


async def test_binance_fills_return_none_on_failure():
    client = _client(lambda url, kwargs: _resp({"msg": "boom"}, status=500))
    assert await BinanceAdapter("k", "s", http_client=client).get_fills(["UNI"]) is None


async def test_binance_fills_never_log_the_key():
    client = _client(lambda url, kwargs: _resp({}, status=500))
    with patch("app.exchanges.binance.logger") as log:
        await BinanceAdapter("sekret-key-value", "sekret-secret", http_client=client).get_fills(["UNI"])
    for call in log.warning.call_args_list:
        assert "sekret" not in str(call)


# ══════════════════════════════════════════════════════════════════════════════
# Gate.io
# ══════════════════════════════════════════════════════════════════════════════

def _gate_trade(tid, pair="UNI_USDT", side="buy", amount="10", price="5", fee="0.01",
                fee_ccy="UNI", ts_ms="1700000000123"):
    return {
        "id": str(tid), "create_time": ts_ms[:10], "create_time_ms": ts_ms,
        "currency_pair": pair, "side": side, "role": "taker", "amount": amount,
        "price": price, "order_id": "1", "fee": fee, "fee_currency": fee_ccy,
        "point_fee": "0", "gt_fee": "0",
    }


async def test_gateio_fills_walk_windows_and_filter_to_held_assets():
    def handler(url, kwargs):
        q = _query(url, kwargs)
        assert int(q["to"]) - int(q["from"]) == 30 * 24 * 3600
        assert kwargs["headers"]["SIGN"]  # signed with the query string
        # Every other window has trades; each answers a short (final) page.
        return _resp([
            _gate_trade(1),
            _gate_trade(2, pair="ALPACA_USDT"),  # not held → filtered out
            _gate_trade(3, pair="UNI_BTC", side="buy", price="0.0001", fee_ccy="UNI"),
        ]) if q["page"] == "1" and int(q["to"]) % 2 == 0 else _resp([])

    client = _client(handler)
    adapter = GateioAdapter("key", "secret", http_client=client)
    with patch("app.exchanges.gateio.time.time", return_value=1_800_000_000.0):
        fills = await adapter.get_fills(["UNI"])

    assert fills is not None
    assert {f.asset for f in fills} == {"UNI"}
    usdt = [f for f in fills if f.quote_asset == "USDT"]
    assert usdt and usdt[0] == Fill("UNI", "buy", 10.0, "USDT", 50.0, "UNI", 0.01, 1_700_000_000_123)
    assert any(f.quote_asset == "BTC" for f in fills)
    # 24 windows, one page each (short pages end the window)
    assert len(client.calls) == 24
    # Windows tile backwards from "now" without gaps.
    ranges = sorted((int(_query(u, k)["from"]), int(_query(u, k)["to"])) for u, k in client.calls)
    assert ranges[-1][1] == 1_800_000_000
    for (_, prev_to), (next_from, _) in zip(ranges, ranges[1:]):
        assert prev_to == next_from


async def test_gateio_fills_page_until_short_page():
    def handler(url, kwargs):
        q = _query(url, kwargs)
        if int(q["to"]) != 1_800_000_000:
            return _resp([])
        if q["page"] == "1":
            return _resp([_gate_trade(i) for i in range(100)])  # a clamped full page
        return _resp([_gate_trade(999)])

    client = _client(handler)
    with patch("app.exchanges.gateio.time.time", return_value=1_800_000_000.0):
        fills = await GateioAdapter("k", "s", http_client=client).get_fills(["UNI"])
    assert len(fills) == 101
    pages = [_query(u, k)["page"] for u, k in client.calls if int(_query(u, k)["to"]) == 1_800_000_000]
    assert sorted(pages) == ["1", "2"]


async def test_gateio_fills_return_none_on_failure():
    client = _client(lambda url, kwargs: _resp({"label": "INVALID_KEY"}, status=401))
    assert await GateioAdapter("k", "s", http_client=client).get_fills(["UNI"]) is None


# ══════════════════════════════════════════════════════════════════════════════
# OKX
# ══════════════════════════════════════════════════════════════════════════════

def _okx_fill(bill, inst="UNI-USDT", side="buy", sz="10", px="5", fee="-0.01", fee_ccy="UNI"):
    return {"instType": "SPOT", "instId": inst, "tradeId": bill, "ordId": "1", "billId": str(bill),
            "fillPx": px, "fillSz": sz, "side": side, "fee": fee, "feeCcy": fee_ccy,
            "fillTime": "1700000000000", "ts": "1700000000000", "execType": "T"}


async def test_okx_fills_page_with_after_bill_id():
    def handler(url, kwargs):
        q = _query(url, kwargs)
        assert q["instType"] == "SPOT"
        # The signed requestPath must include the query string.
        assert "?" in url
        if "after" not in q:
            return _resp({"code": "0", "data": [_okx_fill(1000 - i) for i in range(100)]})
        assert q["after"] == "901"
        return _resp({"code": "0", "data": [_okx_fill(1, side="sell", fee="-0.05", fee_ccy="USDT")]})

    client = _client(handler)
    fills = await OKXAdapter("k", "s|p", http_client=client).get_fills(["UNI"])
    assert len(fills) == 101
    assert fills[0] == Fill("UNI", "buy", 10.0, "USDT", 50.0, "UNI", 0.01, 1_700_000_000_000)
    assert fills[-1].side == "sell" and fills[-1].fee_asset == "USDT" and fills[-1].fee_qty == 0.05


async def test_okx_fills_error_code_is_none():
    client = _client(lambda url, kwargs: _resp({"code": "50111", "msg": "Invalid OK-ACCESS-KEY"}))
    assert await OKXAdapter("k", "s|p", http_client=client).get_fills(["UNI"]) is None


# ══════════════════════════════════════════════════════════════════════════════
# Bybit
# ══════════════════════════════════════════════════════════════════════════════

def _bybit_exec(exec_id, symbol="UNIUSDT", side="Buy", qty="10", px="5", fee="0.01", fee_ccy=""):
    return {"symbol": symbol, "side": side, "execPrice": px, "execQty": qty, "execValue": "50",
            "execFee": fee, "feeCurrency": fee_ccy, "execTime": "1700000000000",
            "execId": str(exec_id), "orderId": "o1", "isMaker": False}


async def test_bybit_fills_use_7_day_windows_and_cursor():
    def handler(url, kwargs):
        q = _query(url, kwargs)
        assert q["category"] == "spot"
        assert int(q["endTime"]) - int(q["startTime"]) == 7 * 24 * 3600 * 1000
        assert kwargs["headers"]["X-BAPI-SIGN"]
        newest = int(q["endTime"]) == 1_800_000_000_000
        if newest and "cursor" not in q:
            return _resp({"retCode": 0, "result": {
                "list": [_bybit_exec(i) for i in range(100)], "nextPageCursor": "c2"}})
        if newest and q.get("cursor") == "c2":
            return _resp({"retCode": 0, "result": {
                "list": [_bybit_exec(1, side="Sell", fee="0.05", fee_ccy="USDT")],
                "nextPageCursor": ""}})
        return _resp({"retCode": 0, "result": {"list": [], "nextPageCursor": ""}})

    client = _client(handler)
    with patch("app.exchanges.bybit.time.time", return_value=1_800_000_000.0):
        fills = await BybitAdapter("k", "s", http_client=client).get_fills(["UNI"])
    assert len(fills) == 101
    # Empty feeCurrency on a spot buy → charged in the base coin.
    assert fills[0] == Fill("UNI", "buy", 10.0, "USDT", 50.0, "UNI", 0.01, 1_700_000_000_000)
    assert fills[-1].fee_asset == "USDT"
    assert len(client.calls) == 26 + 1  # 26 windows + one extra page


async def test_bybit_fills_ret_code_error_is_none():
    client = _client(lambda url, kwargs: _resp({"retCode": 10003, "retMsg": "API key is invalid."}))
    with patch("app.exchanges.bybit.time.time", return_value=1_800_000_000.0):
        assert await BybitAdapter("k", "s", http_client=client).get_fills(["UNI"]) is None


# ══════════════════════════════════════════════════════════════════════════════
# Kraken
# ══════════════════════════════════════════════════════════════════════════════

_KRAKEN_PAIRS = {
    "XXBTZUSD": {"altname": "XBTUSD", "base": "XXBT", "quote": "ZUSD"},
    "UNIUSDT": {"altname": "UNIUSDT", "base": "UNI", "quote": "USDT"},
}


def _kraken_trade(pair="XXBTZUSD", ttype="buy", vol="0.5", cost="30000", fee="30", t="1700000000.5"):
    return {"ordertxid": "O1", "pair": pair, "time": t, "type": ttype, "ordertype": "market",
            "price": "60000", "cost": cost, "fee": fee, "vol": vol, "margin": "0", "misc": ""}


async def test_kraken_fills_map_pairs_and_page_by_offset():
    def handler(url, kwargs):
        if url.endswith("/0/public/AssetPairs"):
            return _resp({"error": [], "result": _KRAKEN_PAIRS})
        body = parse_qs(kwargs["content"])
        assert kwargs["headers"]["API-Sign"]
        ofs = int(body["ofs"][0])
        if ofs == 0:
            trades = {f"T{i}": _kraken_trade() for i in range(100)}
        else:
            assert ofs == 100
            trades = {"T-last": _kraken_trade(pair="UNIUSDT", ttype="sell", vol="10", cost="50", fee="0.1")}
        return _resp({"error": [], "result": {"count": 101, "trades": trades}})

    client = _client(handler, method="post")
    fills = await KrakenAdapter("k", "c2VjcmV0", http_client=client).get_fills(["BTC", "UNI"])
    assert len(fills) == 101
    btc = fills[0]
    assert btc == Fill("BTC", "buy", 0.5, "USD", 30000.0, "USD", 30.0, 1_700_000_000_500)
    assert fills[-1] == Fill("UNI", "sell", 10.0, "USDT", 50.0, "USDT", 0.1, 1_700_000_000_500)


async def test_kraken_fills_api_error_is_none():
    def handler(url, kwargs):
        if url.endswith("/0/public/AssetPairs"):
            return _resp({"error": [], "result": _KRAKEN_PAIRS})
        return _resp({"error": ["EAPI:Invalid key"]})

    client = _client(handler, method="post")
    assert await KrakenAdapter("k", "c2VjcmV0", http_client=client).get_fills(["BTC"]) is None


# ══════════════════════════════════════════════════════════════════════════════
# Coinbase
# ══════════════════════════════════════════════════════════════════════════════

def _cb_fill(product="UNI-USD", side="BUY", price="5", size="10", in_quote=False, commission="0.1"):
    return {"entry_id": "e", "trade_id": "t", "order_id": "o", "trade_time": "2023-11-14T22:13:20Z",
            "trade_type": "FILL", "price": price, "size": size, "commission": commission,
            "product_id": product, "sequence_timestamp": "2023-11-14T22:13:20Z",
            "liquidity_indicator": "TAKER", "size_in_quote": in_quote, "user_id": "u", "side": side}


async def test_coinbase_fills_cursor_and_size_in_quote():
    def handler(url, kwargs):
        q = _query(url, kwargs)
        assert "?" not in url  # query goes via params; signed path has none
        if "cursor" not in q:
            return _resp({"fills": [_cb_fill()], "cursor": "next"})
        assert q["cursor"] == "next"
        return _resp({"fills": [_cb_fill(side="SELL", size="25", in_quote=True)], "cursor": ""})

    client = _client(handler)
    fills = await CoinbaseAdapter("k", "s", http_client=client).get_fills(["UNI"])
    assert len(fills) == 2
    assert fills[0] == Fill("UNI", "buy", 10.0, "USD", 50.0, "USD", 0.1, 1_700_000_000_000)
    # size_in_quote: size is $25 → 5 UNI at $5
    assert fills[1].qty == pytest.approx(5.0) and fills[1].quote_qty == 25.0
    assert fills[1].side == "sell"


async def test_coinbase_fills_http_error_is_none():
    client = _client(lambda url, kwargs: _resp({}, status=401))
    assert await CoinbaseAdapter("k", "s", http_client=client).get_fills(["UNI"]) is None


# ══════════════════════════════════════════════════════════════════════════════
# Demo
# ══════════════════════════════════════════════════════════════════════════════

async def test_demo_fills_are_deterministic_for_preset_assets():
    fills = await DemoAdapter("demo-readonly-key", "s").get_fills(["BTC", "ADA", "XYZ"])
    assert {f.asset for f in fills} == {"BTC", "ADA"}
    assert fills == await DemoAdapter("demo-readonly-key", "s").get_fills(["BTC", "ADA"])
    assert await DemoAdapter("demo-empty-key", "s").get_fills(["BTC"]) == []


# ══════════════════════════════════════════════════════════════════════════════
# AVCO maths
# ══════════════════════════════════════════════════════════════════════════════

def _fill(asset, side, qty, quote_qty, quote="USDT", fee_asset="", fee=0.0, ts=0):
    return Fill(asset, side, qty, quote, quote_qty, fee_asset, fee, ts)


def _one(fills, held):
    (row,) = compute_avco(fills, held)
    return row


def test_avco_two_buys():
    row = _one([_fill("UNI", "buy", 10, 40, ts=1), _fill("UNI", "buy", 10, 60, ts=2)], {"UNI": 20})
    assert row.avg_buy_price == pytest.approx(5.0)
    assert row.bought_qty == 20
    assert row.coverage == "full"


def test_avco_partial_sell_keeps_average():
    fills = [
        _fill("UNI", "buy", 10, 40, ts=1),
        _fill("UNI", "buy", 10, 60, ts=2),
        _fill("UNI", "sell", 5, 100, ts=3),  # sold high; the average cost is unaffected
    ]
    row = _one(fills, {"UNI": 15})
    assert row.avg_buy_price == pytest.approx(5.0)
    assert row.bought_qty == 20
    assert row.coverage == "full"


def test_avco_fee_in_base_asset_reduces_received_qty():
    row = _one([_fill("UNI", "buy", 10, 50, fee_asset="UNI", fee=0.5)], {"UNI": 9.5})
    assert row.bought_qty == pytest.approx(9.5)
    assert row.avg_buy_price == pytest.approx(50 / 9.5)
    assert row.coverage == "full"


def test_avco_fee_in_quote_raises_cost():
    row = _one([_fill("UNI", "buy", 10, 50, fee_asset="USDT", fee=0.5)], {"UNI": 10})
    assert row.avg_buy_price == pytest.approx(5.05)


def test_avco_fee_in_third_asset_is_ignored():
    row = _one([_fill("UNI", "buy", 10, 50, fee_asset="BNB", fee=0.001)], {"UNI": 10})
    assert row.avg_buy_price == pytest.approx(5.0)


def test_avco_non_stable_quote_makes_coverage_partial():
    fills = [_fill("UNI", "buy", 10, 50, ts=1), _fill("UNI", "buy", 10, 0.002, quote="BTC", ts=2)]
    row = _one(fills, {"UNI": 20})
    assert row.avg_buy_price == pytest.approx(5.0)
    assert row.bought_qty == 10
    assert row.coverage == "partial"


def test_avco_only_non_stable_quote_is_none():
    row = _one([_fill("ADA", "buy", 800, 0.006, quote="BTC")], {"ADA": 800})
    assert row.avg_buy_price is None
    assert row.coverage == "none"


def test_avco_deposit_only_is_none():
    row = _one([], {"UNI": 20})
    assert row.avg_buy_price is None and row.coverage == "none" and row.bought_qty == 0


def test_avco_deposit_plus_buy_is_partial():
    row = _one([_fill("UNI", "buy", 10, 50)], {"UNI": 20})
    assert row.avg_buy_price == pytest.approx(5.0)
    assert row.coverage == "partial"


def test_avco_full_coverage_tolerates_one_percent_dust():
    row = _one([_fill("UNI", "buy", 9.95, 49.75)], {"UNI": 10})
    assert row.coverage == "full"


def test_avco_sell_more_than_bought_is_clamped():
    fills = [_fill("UNI", "buy", 10, 50, ts=1), _fill("UNI", "sell", 30, 150, ts=2)]
    row = _one(fills, {"UNI": 5})
    assert row.coverage == "none"  # the explained position was fully sold


def test_avco_processes_fills_in_time_order():
    fills = [_fill("UNI", "sell", 10, 100, ts=2), _fill("UNI", "buy", 10, 50, ts=1)]
    row = _one(fills, {"UNI": 10})
    assert row.coverage == "none"  # buy then sell → nothing left explained


def test_avco_rows_sorted_and_only_for_held_assets():
    fills = [_fill("B", "buy", 1, 1), _fill("A", "buy", 1, 2), _fill("ZZZ", "buy", 1, 1)]
    rows = compute_avco(fills, {"B": 1, "A": 1})
    assert [r.asset for r in rows] == ["A", "B"]


# ══════════════════════════════════════════════════════════════════════════════
# Service
# ══════════════════════════════════════════════════════════════════════════════

def _key(exchange, key_type="read_only", key_id=1):
    k = MagicMock()
    k.id = key_id
    k.exchange = exchange
    k.key_type = key_type
    k.profile_id = 1
    k.encrypted_key = "enc-k"
    k.encrypted_secret = "enc-s"
    return k


def _portfolio(exchanges: dict[str, list[Balance]]) -> PortfolioResponse:
    return PortfolioResponse(
        profile_id=1, profile_name="p",
        exchanges=[ExchangeBalance(exchange=e, balances=b, total_usd=sum(x.usd_value or 0 for x in b))
                   for e, b in exchanges.items()],
        total_usd=0.0,
    )


def _bal(asset, total, usd):
    return Balance(asset=asset, free=total, locked=0, total=total, usd_value=usd)


class _FakeAdapter:
    def __init__(self, fills):
        self._fills = fills
        self.asked: list[list[str]] = []

    async def get_fills(self, assets):
        self.asked.append(list(assets))
        if isinstance(self._fills, Exception):
            raise self._fills
        return self._fills


@pytest.fixture
def _no_decrypt():
    with patch.object(cost_basis_service, "decrypt", side_effect=lambda v: "plain"):
        yield


async def test_service_runs_exchanges_in_parallel_and_isolates_failures(_no_decrypt):
    gate = _FakeAdapter([_fill("UNI", "buy", 10, 50)])
    okx = _FakeAdapter(None)
    boom = _FakeAdapter(RuntimeError("boom"))
    adapters = {"gateio": gate, "okx": okx, "kraken": boom}

    portfolio = _portfolio({
        "gateio": [_bal("UNI", 10, 50), _bal("USDT", 100, 100), _bal("DUST", 1, 0.01)],
        "okx": [_bal("BTC", 1, 60000)],
        "kraken": [_bal("ETH", 1, 3000)],
    })
    with patch.object(cost_basis_service, "get_portfolio", AsyncMock(return_value=portfolio)), \
         patch.object(cost_basis_service, "get_adapter", side_effect=lambda ex, k, s, http_client=None: adapters[ex]):
        result = await get_cost_basis(1, "p", [_key("gateio"), _key("okx"), _key("kraken")])

    by_ex = {e.exchange: e for e in result.exchanges}
    assert by_ex["gateio"].supported is True
    assert [a.asset for a in by_ex["gateio"].assets] == ["DUST", "UNI"]  # stablecoin excluded
    uni = next(a for a in by_ex["gateio"].assets if a.asset == "UNI")
    assert uni.avg_buy_price == pytest.approx(5.0) and uni.coverage == "full"
    assert by_ex["okx"].supported is False and by_ex["okx"].assets == []
    assert by_ex["kraken"].supported is False
    # Adapters are asked in descending USD value so call budgets drop dust last.
    assert gate.asked == [["UNI", "DUST"]]
    assert result.computed_at.tzinfo is not None


async def test_service_prefers_read_only_key_per_exchange(_no_decrypt):
    seen: list = []

    def fake_adapter(ex, k, s, http_client=None):
        return _FakeAdapter([])

    portfolio = _portfolio({"gateio": [_bal("UNI", 10, 50)]})
    keys = [_key("gateio", "trade", key_id=7), _key("gateio", "read_only", key_id=8)]
    with patch.object(cost_basis_service, "get_portfolio", AsyncMock(return_value=portfolio)), \
         patch.object(cost_basis_service, "get_adapter", side_effect=fake_adapter), \
         patch.object(cost_basis_service, "decrypt", side_effect=lambda v: seen.append(v) or "x"):
        await get_cost_basis(1, "p", keys)
    assert seen == ["enc-k", "enc-s"]  # exactly one key decrypted


async def test_service_caches_in_memo_and_redis(_no_decrypt):
    adapter = _FakeAdapter([_fill("UNI", "buy", 10, 50)])
    portfolio = _portfolio({"gateio": [_bal("UNI", 10, 50)]})
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    with patch.object(cost_basis_service, "get_portfolio", AsyncMock(return_value=portfolio)) as gp, \
         patch.object(cost_basis_service, "get_adapter", return_value=adapter):
        first = await get_cost_basis(1, "p", [_key("gateio")], redis=redis)
        second = await get_cost_basis(1, "p", [_key("gateio")], redis=redis)
    assert first == second
    assert gp.await_count == 1 and len(adapter.asked) == 1
    redis.setex.assert_awaited_once()
    assert redis.setex.await_args.args[1] == 15 * 60


async def test_service_reads_redis_when_memo_cold(_no_decrypt):
    cached = '{"profile_id": 1, "computed_at": "2026-09-27T12:00:00Z", "exchanges": []}'
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=cached)
    with patch.object(cost_basis_service, "get_portfolio", AsyncMock()) as gp:
        result = await get_cost_basis(1, "p", [_key("gateio")], redis=redis)
    assert result.exchanges == [] and gp.await_count == 0


async def test_service_survives_redis_outage(_no_decrypt):
    redis = AsyncMock()
    redis.get = AsyncMock(side_effect=ConnectionError("down"))
    portfolio = _portfolio({"gateio": [_bal("UNI", 10, 50)]})
    with patch.object(cost_basis_service, "get_portfolio", AsyncMock(return_value=portfolio)), \
         patch.object(cost_basis_service, "get_adapter", return_value=_FakeAdapter([])):
        result = await get_cost_basis(1, "p", [_key("gateio")], redis=redis)
    assert result.exchanges[0].supported is True
    redis.setex.assert_not_awaited()


# Endpoint auth (403 foreign profile / 404 / 401) is exercised over real HTTP in
# tests/test_integration_conditions.py — the slowapi decorator on the route
# refuses anything but a genuine starlette Request, so it cannot be unit-called.


async def test_service_caches_a_failed_venue_only_briefly(_no_decrypt):
    """A venue that supports history but failed this time (timeout, 5xx) must
    not be pinned as "unsupported" for the full 15-minute window."""
    portfolio = _portfolio({"gateio": [_bal("UNI", 10, 50)]})
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    with patch.object(cost_basis_service, "get_portfolio", AsyncMock(return_value=portfolio)), \
         patch.object(cost_basis_service, "get_adapter", return_value=_FakeAdapter(None)):
        result = await get_cost_basis(1, "p", [_key("gateio")], redis=redis)
    assert result.exchanges[0].supported is False
    assert redis.setex.await_args.args[1] == cost_basis_service.COST_BASIS_DEGRADED_TTL


async def test_service_caches_a_genuinely_unsupported_venue_normally(_no_decrypt):
    """Binance TR never has fills here; recomputing it every minute buys nothing."""
    from app.exchanges.binancetr import BinanceTRAdapter

    portfolio = _portfolio({"binancetr": [_bal("BTC", 1, 60000)]})
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    with patch.object(cost_basis_service, "get_portfolio", AsyncMock(return_value=portfolio)), \
         patch.object(cost_basis_service, "get_adapter", return_value=BinanceTRAdapter("k", "s")):
        result = await get_cost_basis(1, "p", [_key("binancetr")], redis=redis)
    assert result.exchanges[0].supported is False
    assert redis.setex.await_args.args[1] == cost_basis_service.COST_BASIS_CACHE_TTL

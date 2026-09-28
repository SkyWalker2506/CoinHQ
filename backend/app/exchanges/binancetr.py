import asyncio
import hashlib
import hmac
import time
from contextlib import asynccontextmanager
from urllib.parse import urlencode

import httpx

from app.core.logging import logger
from app.exchanges.base import ExchangeAdapter, Fill
from app.schemas.portfolio import Balance

BINANCETR_BASE = "https://www.trbinance.com"

# Only the USDT book gives a dollar cost basis; TRY fills would need a lira
# rate from outside the venue, the same second-hand pricing get_prices avoids.
_FILL_QUOTE = "USDT"
_FILL_SKIP = frozenset({"USDT", "USDC", "BUSD", "FDUSD", "TUSD", "DAI", "TRY"})
_FILL_PAGE_LIMIT = 500
_FILL_MAX_PAGES = 20
_FILL_MAX_CALLS = 60
_FILL_CONCURRENCY = 5


class BinanceTRAdapter(ExchangeAdapter):
    """Binance TR (trbinance.com) adapter — uses /open/v1/ REST API.

    Deliberately does not implement `get_prices`: Binance TR quotes its book in
    lira, so its tickers would need a TRY/USD rate to be useful here, and that
    rate would come from outside the venue — exactly the second-hand pricing
    `get_prices` exists to avoid. Balances held here stay on the global lookup.
    """

    def _sign(self, params: dict) -> str:
        query = urlencode(sorted(params.items()))
        return hmac.new(self.api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()

    def _headers(self) -> dict:
        return {"X-MBX-APIKEY": self.api_key}

    @asynccontextmanager
    async def _client(self):
        if self._http_client is not None:
            yield self._http_client
        else:
            async with httpx.AsyncClient(timeout=10) as client:
                yield client

    async def get_balances(self) -> list[Balance]:
        params = {"timestamp": int(time.time() * 1000), "recvWindow": 5000}
        params["signature"] = self._sign(params)
        async with self._client() as client:
            resp = await client.get(
                f"{BINANCETR_BASE}/open/v1/account/spot",
                params=params,
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        balances = []
        for item in data.get("data", {}).get("accountAssets", []):
            free = float(item.get("free", 0))
            locked = float(item.get("locked", 0))
            total = free + locked
            if total > 0:
                balances.append(
                    Balance(
                        asset=item["asset"],
                        free=free,
                        locked=locked,
                        total=total,
                    )
                )
        return balances

    async def get_fills(self, assets: list[str]) -> list[Fill] | None:
        """GET /open/v1/orders/trades per `<ASSET>_USDT` symbol.

        `assets` arrives by descending value, so the shared call budget drops
        the dust first. A symbol Binance TR does not list fails on its own and
        simply contributes no fills.
        """
        wanted = [a.upper() for a in assets if a.upper() not in _FILL_SKIP]
        if not wanted:
            return []
        sem = asyncio.Semaphore(_FILL_CONCURRENCY)
        budget = {"calls": 0}
        failed: list[str] = []

        async def one(client: httpx.AsyncClient, asset: str) -> list[Fill]:
            async with sem:
                try:
                    return await self._symbol_fills(client, asset, budget)
                except Exception:  # noqa: BLE001 — an unlisted pair is normal
                    failed.append(asset)
                    return []

        try:
            async with self._client() as client:
                results = await asyncio.gather(*(one(client, a) for a in wanted))
        except Exception as exc:  # noqa: BLE001 — best-effort, never raise
            logger.warning("exchange_fills_fetch_failed", exchange="binancetr", error=str(exc))
            return None
        if len(failed) == len(wanted):
            logger.warning("exchange_fills_fetch_failed", exchange="binancetr", error="every symbol failed")
            return None
        return [f for fills in results for f in fills]

    async def _symbol_fills(
        self, client: httpx.AsyncClient, asset: str, budget: dict
    ) -> list[Fill]:
        fills: list[Fill] = []
        from_id = ""
        for _ in range(_FILL_MAX_PAGES):
            if budget["calls"] >= _FILL_MAX_CALLS:
                logger.warning(
                    "exchange_fills_call_budget_exhausted", exchange="binancetr", calls=budget["calls"]
                )
                break
            budget["calls"] += 1
            params: dict = {
                "symbol": f"{asset}_{_FILL_QUOTE}",
                "limit": _FILL_PAGE_LIMIT,
                "timestamp": int(time.time() * 1000),
                "recvWindow": 5000,
            }
            if from_id:
                params["fromId"] = from_id
                params["direction"] = "next"
            params["signature"] = self._sign(params)
            resp = await client.get(
                f"{BINANCETR_BASE}/open/v1/orders/trades",
                params=params,
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") not in (None, 0, "0"):
                raise ValueError(f"Binance TR API error: {data.get('msg', 'unknown')}")
            rows = (data.get("data") or {}).get("list") or []
            for row in rows:
                fill = self._parse_fill(asset, row)
                if fill is not None:
                    fills.append(fill)
            if len(rows) < _FILL_PAGE_LIMIT:
                break
            from_id = str(rows[-1].get("tradeId") or "")
            if not from_id:
                break
        return fills

    @staticmethod
    def _parse_fill(asset: str, row: dict) -> Fill | None:
        try:
            qty = float(row["qty"])
            price = float(row["price"])
            return Fill(
                asset=asset,
                side="buy" if str(row.get("isBuyer")).lower() in ("1", "true") else "sell",
                qty=qty,
                quote_asset=_FILL_QUOTE,
                quote_qty=float(row.get("quoteQty") or qty * price),
                fee_asset=str(row.get("commissionAsset") or "").upper(),
                fee_qty=max(float(row.get("commission") or 0.0), 0.0),
                ts_ms=int(row["time"]),
            )
        except (KeyError, TypeError, ValueError):
            return None

    async def validate_key(self) -> bool:
        params = {"timestamp": int(time.time() * 1000), "recvWindow": 5000}
        params["signature"] = self._sign(params)
        async with self._client() as client:
            resp = await client.get(
                f"{BINANCETR_BASE}/open/v1/account/spot",
                params=params,
                headers=self._headers(),
            )
        resp.raise_for_status()
        data = resp.json()

        # Binance TR doesn't expose canTrade/enableWithdrawals in account endpoint
        # We accept the key if we can read balances successfully
        if data.get("code") not in (None, 0, "0", 200):
            raise ValueError(f"Binance TR API error: {data.get('msg', 'Unknown error')}")

        return True

    async def validate_trade_key(self) -> bool:
        """Binance TR does not expose permission flags, so we can only verify the key
        works. CoinHQ never calls any withdrawal endpoint, so funds cannot leave the
        account regardless — but users should still create a no-withdrawal key."""
        await self.validate_key()
        return True

    async def place_order(
        self, base_asset: str, side: str, quote_quantity_usd: float, price: float | None = None
    ) -> dict:
        """Spot MARKET order via the Binance TR open API (/open/v1/orders).

        side encoding follows the open API: 0=BUY, 1=SELL; type 2=MARKET. Buys are
        sized by quote (quoteOrderQty); sells are sized by base quantity.
        """
        side_l = side.lower()
        if side_l not in ("buy", "sell"):
            raise ValueError("side must be 'buy' or 'sell'")
        params: dict = {
            "symbol": f"{base_asset.upper()}_USDT",
            "side": 0 if side_l == "buy" else 1,
            "type": 2,  # MARKET
            "timestamp": int(time.time() * 1000),
            "recvWindow": 5000,
        }
        if side_l == "buy":
            params["quoteOrderQty"] = round(float(quote_quantity_usd), 2)
        else:
            params["quantity"] = self._base_qty(quote_quantity_usd, price)
        params["signature"] = self._sign(params)

        async with self._client() as client:
            resp = await client.post(
                f"{BINANCETR_BASE}/open/v1/orders",
                params=params,
                headers=self._headers(),
            )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") not in (None, 0, "0", 200):
            raise ValueError(f"Binance TR order error: {data.get('msg', 'unknown')}")
        return data.get("data", data)

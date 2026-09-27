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

BINANCE_BASE = "https://api.binance.com"

# Trade history is per symbol, so every held asset costs one call per quote it
# might have been bought with. Only symbols Binance actually lists are asked
# for: guessing all three quotes per coin spent most of a 40-call budget on
# markets that do not exist, which left 39 of 53 real holdings with no
# history at all. /api/v3/myTrades weighs 20 of the 6000/min IP budget, so
# 150 calls is half a minute's allowance, spent at most once per 15-minute
# cost-basis cache window.
_FILL_QUOTES = ("USDT", "USDC", "FDUSD")
_FILL_PAGE_LIMIT = 1000
_FILL_MAX_CALLS = 150
_FILL_CONCURRENCY = 8


class BinanceAdapter(ExchangeAdapter):
    def _sign(self, params: dict) -> dict:
        query = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode(), query.encode(), hashlib.sha256
        ).hexdigest()
        params["signature"] = signature
        return params

    def _headers(self) -> dict:
        return {"X-MBX-APIKEY": self.api_key}

    @asynccontextmanager
    async def _client(self):
        if self._http_client is not None:
            yield self._http_client
        else:
            async with httpx.AsyncClient(timeout=10) as client:
                yield client

    async def get_prices(self, assets: list[str]) -> dict[str, float]:
        """Price against Binance's own USDT tickers (public, no auth)."""
        if not assets:
            return {}
        wanted = {a.upper() for a in assets}
        try:
            async with self._client() as client:
                resp = await client.get(f"{BINANCE_BASE}/api/v3/ticker/price", timeout=15)
                resp.raise_for_status()
                tickers = resp.json()
        except Exception as exc:  # noqa: BLE001 — best-effort, caller falls back
            logger.warning("exchange_price_fetch_failed", exchange="binance", error=str(exc))
            return {}

        prices: dict[str, float] = {}
        for t in tickers:
            symbol = t.get("symbol", "")
            if not symbol.endswith("USDT"):
                continue
            base = symbol[: -len("USDT")]
            if base not in wanted:
                continue
            try:
                prices[base] = float(t["price"])
            except (TypeError, ValueError, KeyError):
                continue
        return prices

    async def get_balances(self) -> list[Balance]:
        params = self._sign({"timestamp": int(time.time() * 1000)})
        async with self._client() as client:
            resp = await client.get(
                f"{BINANCE_BASE}/api/v3/account",
                params=params,
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        balances = []
        for item in data.get("balances", []):
            free = float(item["free"])
            locked = float(item["locked"])
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

    async def _listed_symbols(self, client: httpx.AsyncClient) -> set[str] | None:
        """Every symbol Binance currently lists (public ticker, weight 4), or
        None if that could not be fetched — callers then guess every quote."""
        try:
            resp = await client.get(f"{BINANCE_BASE}/api/v3/ticker/price", timeout=15)
            resp.raise_for_status()
            return {t["symbol"] for t in resp.json() if isinstance(t, dict) and "symbol" in t}
        except Exception as exc:  # noqa: BLE001 — degrade to guessing, never raise
            logger.warning("exchange_symbol_list_failed", exchange="binance", error=str(exc))
            return None

    async def get_fills(self, assets: list[str]) -> list[Fill] | None:
        """GET /api/v3/myTrades per listed <ASSET><QUOTE> symbol, paged forward by fromId.

        Symbols are checked against Binance's own listing first so the call
        budget is spent on markets that exist. A symbol that still answers 400
        (-1121 "Invalid symbol") is skipped. Trades are walked from id 0
        upward so old history comes first — the default (no fromId) would
        return only the most recent page. `assets` arrive most valuable first,
        and symbols claim their first call in that order, so if the budget
        runs out it is the dust that goes without history.
        """
        try:
            async with self._client() as client:
                listed = await self._listed_symbols(client)
                symbols = [
                    (base, quote)
                    for base in (a.upper() for a in assets)
                    for quote in _FILL_QUOTES
                    if base != quote and (listed is None or f"{base}{quote}" in listed)
                ]
                budget = {"left": _FILL_MAX_CALLS, "warned": False}
                gate = asyncio.Semaphore(_FILL_CONCURRENCY)

                async def walk(base: str, quote: str) -> list[Fill]:
                    out: list[Fill] = []
                    from_id = 0
                    while True:
                        if budget["left"] <= 0:
                            if not budget["warned"]:
                                budget["warned"] = True
                                logger.warning(
                                    "exchange_fills_call_budget_exhausted",
                                    exchange="binance",
                                    calls=_FILL_MAX_CALLS,
                                )
                            return out
                        budget["left"] -= 1
                        async with gate:
                            # Signed inside the slot: Binance rejects a
                            # timestamp older than its 5s recvWindow, and a
                            # queued call can wait that long for a slot.
                            params = self._sign({
                                "symbol": f"{base}{quote}",
                                "fromId": from_id,
                                "limit": _FILL_PAGE_LIMIT,
                                "timestamp": int(time.time() * 1000),
                            })
                            resp = await client.get(
                                f"{BINANCE_BASE}/api/v3/myTrades",
                                params=params,
                                headers=self._headers(),
                            )
                        if resp.status_code == 400:
                            return out  # no such market for this base/quote
                        resp.raise_for_status()
                        rows = resp.json()
                        if not isinstance(rows, list):
                            return out
                        for row in rows:
                            fill = self._parse_fill(row, base, quote)
                            if fill is not None:
                                out.append(fill)
                        if len(rows) < _FILL_PAGE_LIMIT:
                            return out
                        try:
                            from_id = int(rows[-1]["id"]) + 1
                        except (KeyError, TypeError, ValueError):
                            return out

                per_symbol = await asyncio.gather(*(walk(b, q) for b, q in symbols))
        except Exception as exc:  # noqa: BLE001 — best-effort, never raise
            logger.warning("exchange_fills_fetch_failed", exchange="binance", error=str(exc))
            return None
        return [fill for batch in per_symbol for fill in batch]

    @staticmethod
    def _parse_fill(row: dict, base: str, quote: str) -> Fill | None:
        try:
            return Fill(
                asset=base,
                side="buy" if row.get("isBuyer") else "sell",
                qty=float(row["qty"]),
                quote_asset=quote,
                quote_qty=float(row["quoteQty"]),
                fee_asset=str(row.get("commissionAsset") or ""),
                fee_qty=max(float(row.get("commission") or 0.0), 0.0),
                ts_ms=int(row["time"]),
            )
        except (KeyError, TypeError, ValueError):
            return None

    async def validate_key(self) -> bool:
        params = self._sign({"timestamp": int(time.time() * 1000)})
        async with self._client() as client:
            resp = await client.get(
                f"{BINANCE_BASE}/api/v3/account",
                params=params,
                headers=self._headers(),
            )
        resp.raise_for_status()
        data = resp.json()

        # Reject keys that have withdrawal or futures permissions
        # canTrade can be true even on read-only keys (Binance sets it by default)
        # The real danger signals are withdrawals and internal transfers
        if data.get("enableWithdrawals") or data.get("enableInternalTransfer"):
            logger.error("exchange_write_permissions_rejected", exchange="binance", key=self._mask_key())
            raise ValueError("Write permissions detected. Only read-only API keys are accepted.")

        return True

    async def validate_trade_key(self) -> bool:
        """Accept keys that can trade spot but cannot withdraw/transfer."""
        params = self._sign({"timestamp": int(time.time() * 1000)})
        async with self._client() as client:
            resp = await client.get(
                f"{BINANCE_BASE}/api/v3/account",
                params=params,
                headers=self._headers(),
            )
        resp.raise_for_status()
        data = resp.json()

        # A trade key must NOT be able to move funds off the account.
        if data.get("enableWithdrawals") or data.get("enableInternalTransfer"):
            logger.error("trade_key_withdrawal_rejected", exchange="binance", key=self._mask_key())
            raise ValueError(
                "This key can withdraw or transfer funds. Trade keys must have "
                "withdrawals and transfers disabled."
            )
        if not data.get("canTrade"):
            raise ValueError("This key cannot trade. Enable spot trading on the key (withdrawals off).")

        return True

    async def place_order(
        self, base_asset: str, side: str, quote_quantity_usd: float, price: float | None = None
    ) -> dict:
        """Place a spot MARKET order quoted in USDT (quoteOrderQty)."""
        side_u = side.upper()
        if side_u not in ("BUY", "SELL"):
            raise ValueError("side must be 'buy' or 'sell'")
        params = self._sign({
            "symbol": f"{base_asset.upper()}USDT",
            "side": side_u,
            "type": "MARKET",
            "quoteOrderQty": round(float(quote_quantity_usd), 2),
            "timestamp": int(time.time() * 1000),
        })
        async with self._client() as client:
            resp = await client.post(
                f"{BINANCE_BASE}/api/v3/order",
                params=params,
                headers=self._headers(),
            )
        resp.raise_for_status()
        return resp.json()

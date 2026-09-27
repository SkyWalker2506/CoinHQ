import hashlib
import hmac
import json
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

import httpx

from app.core.logging import logger
from app.exchanges.base import ExchangeAdapter, Fill
from app.schemas.portfolio import Balance

COINBASE_BASE = "https://api.coinbase.com"

# /api/v3/brokerage/orders/historical/fills is cursor-paged; the whole
# account's fills come back in one series and are filtered locally.
_FILL_PAGE_LIMIT = 100
_FILL_MAX_PAGES = 10


class CoinbaseAdapter(ExchangeAdapter):
    def _sign(self, timestamp: str, method: str, path: str, body: str = "") -> str:
        message = timestamp + method.upper() + path + body
        return hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

    def _headers(self, timestamp: str, signature: str) -> dict:
        return {
            "CB-ACCESS-KEY": self.api_key,
            "CB-ACCESS-SIGN": signature,
            "CB-ACCESS-TIMESTAMP": timestamp,
        }

    @asynccontextmanager
    async def _client(self):
        if self._http_client is not None:
            yield self._http_client
        else:
            async with httpx.AsyncClient(timeout=10) as client:
                yield client

    async def get_prices(self, assets: list[str]) -> dict[str, float]:
        """Price against Coinbase's own USD exchange rates (public, no auth).

        The endpoint answers "how much of this asset is one dollar worth", so
        each rate is inverted. A zero or missing rate means Coinbase has no
        quote and the asset is left out.
        """
        if not assets:
            return {}
        wanted = {a.upper() for a in assets}
        try:
            async with self._client() as client:
                resp = await client.get(
                    f"{COINBASE_BASE}/v2/exchange-rates",
                    params={"currency": "USD"},
                    timeout=15,
                )
                resp.raise_for_status()
                rates = resp.json().get("data", {}).get("rates", {})
        except Exception as exc:  # noqa: BLE001 — best-effort, caller falls back
            logger.warning("exchange_price_fetch_failed", exchange="coinbase", error=str(exc))
            return {}

        prices: dict[str, float] = {}
        for asset in wanted:
            try:
                per_usd = float(rates[asset])
            except (TypeError, ValueError, KeyError):
                continue
            if per_usd > 0:
                prices[asset] = 1 / per_usd
        return prices

    async def get_balances(self) -> list[Balance]:
        path = "/api/v3/brokerage/accounts"
        timestamp = str(int(time.time()))
        signature = self._sign(timestamp, "GET", path)

        async with self._client() as client:
            resp = await client.get(
                f"{COINBASE_BASE}{path}",
                headers=self._headers(timestamp, signature),
            )
            resp.raise_for_status()
            data = resp.json()

        balances = []
        for account in data.get("accounts", []):
            available = float(account.get("available_balance", {}).get("value", 0))
            hold = float(account.get("hold", {}).get("value", 0))
            total = available + hold
            currency = account.get("currency", "")
            if total > 0:
                balances.append(
                    Balance(
                        asset=currency,
                        free=available,
                        locked=hold,
                        total=total,
                    )
                )
        return balances

    async def get_fills(self, assets: list[str]) -> list[Fill] | None:
        """GET /api/v3/brokerage/orders/historical/fills, cursor-paged.

        The legacy HMAC signature (the scheme this adapter already uses)
        covers the request path without its query string. `size_in_quote`
        says whether `size` is a quote amount; `commission` is always quote.
        """
        wanted = {a.upper() for a in assets}
        if not wanted:
            return []
        fills: list[Fill] = []
        cursor = ""
        try:
            async with self._client() as client:
                for _ in range(_FILL_MAX_PAGES):
                    path = "/api/v3/brokerage/orders/historical/fills"
                    params: dict[str, str] = {"limit": str(_FILL_PAGE_LIMIT)}
                    if cursor:
                        params["cursor"] = cursor
                    timestamp = str(int(time.time()))
                    resp = await client.get(
                        f"{COINBASE_BASE}{path}",
                        params=params,
                        headers=self._headers(timestamp, self._sign(timestamp, "GET", path)),
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    rows = data.get("fills") or []
                    for row in rows:
                        fill = self._parse_fill(row)
                        if fill is not None and fill.asset in wanted:
                            fills.append(fill)
                    cursor = str(data.get("cursor") or "")
                    if not cursor or not rows:
                        break
        except Exception as exc:  # noqa: BLE001 — best-effort, never raise
            logger.warning("exchange_fills_fetch_failed", exchange="coinbase", error=str(exc))
            return None
        return fills

    @staticmethod
    def _parse_fill(row: dict) -> Fill | None:
        try:
            base, quote = str(row["product_id"]).split("-", 1)
            price = float(row["price"])
            size = float(row["size"])
            if row.get("size_in_quote"):
                quote_qty = size
                qty = size / price if price > 0 else 0.0
            else:
                qty = size
                quote_qty = size * price
            trade_time = str(row["trade_time"]).replace("Z", "+00:00")
            ts_ms = int(datetime.fromisoformat(trade_time).timestamp() * 1000)
            return Fill(
                asset=base.upper(),
                side=str(row["side"]).lower(),
                qty=qty,
                quote_asset=quote.upper(),
                quote_qty=quote_qty,
                fee_asset=quote.upper(),
                fee_qty=max(float(row.get("commission") or 0.0), 0.0),
                ts_ms=ts_ms,
            )
        except (KeyError, TypeError, ValueError):
            return None

    async def validate_key(self) -> bool:
        """Validate key — Coinbase Advanced Trade read-only (view) keys are accepted."""
        path = "/api/v3/brokerage/accounts"
        timestamp = str(int(time.time()))
        signature = self._sign(timestamp, "GET", path)

        async with self._client() as client:
            resp = await client.get(
                f"{COINBASE_BASE}{path}",
                headers=self._headers(timestamp, signature),
            )

        if resp.status_code == 401:
            logger.error("exchange_key_invalid", exchange="coinbase", key=self._mask_key())
            raise ValueError("Invalid API key or secret for Coinbase")

        resp.raise_for_status()

        # Coinbase Advanced Trade does not expose permission flags in account list response.
        # Keys with trade/order scopes cannot be detected here — documented limitation.
        # Users must create view-only keys (portfolios:read, accounts:read).
        return True

    async def validate_trade_key(self) -> bool:
        """Coinbase does not expose permission flags, so we only verify the key works.
        CoinHQ never calls any withdrawal endpoint; create a trade-only (no transfer)
        key for safety."""
        await self.validate_key()
        return True

    async def place_order(
        self, base_asset: str, side: str, quote_quantity_usd: float, price: float | None = None
    ) -> dict:
        """Spot MARKET (market_market_ioc) order. Buy sized by quote, sell by base."""
        side_u = side.upper()
        if side_u not in ("BUY", "SELL"):
            raise ValueError("side must be 'buy' or 'sell'")
        if side_u == "BUY":
            config = {"market_market_ioc": {"quote_size": str(round(float(quote_quantity_usd), 2))}}
        else:
            config = {"market_market_ioc": {"base_size": str(self._base_qty(quote_quantity_usd, price))}}
        body = json.dumps({
            "client_order_id": str(uuid.uuid4()),
            "product_id": f"{base_asset.upper()}-USDT",
            "side": side_u,
            "order_configuration": config,
        })
        path = "/api/v3/brokerage/orders"
        timestamp = str(int(time.time()))
        signature = self._sign(timestamp, "POST", path, body)
        headers = {**self._headers(timestamp, signature), "Content-Type": "application/json"}
        async with self._client() as client:
            resp = await client.post(f"{COINBASE_BASE}{path}", content=body, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        if data.get("success") is False:
            raise ValueError(f"Coinbase order error: {data.get('error_response', data)}")
        return data

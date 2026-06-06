import hashlib
import hmac
import json
import time
import uuid
from contextlib import asynccontextmanager

import httpx

from app.core.logging import logger
from app.exchanges.base import ExchangeAdapter
from app.schemas.portfolio import Balance

COINBASE_BASE = "https://api.coinbase.com"


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

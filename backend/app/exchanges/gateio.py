import hashlib
import hmac
import json
import time
from contextlib import asynccontextmanager

import httpx

from app.core.logging import logger
from app.exchanges.base import ExchangeAdapter
from app.schemas.portfolio import Balance

GATEIO_BASE = "https://api.gateio.ws"
GATEIO_PREFIX = "/api/v4"


class GateioAdapter(ExchangeAdapter):
    """Gate.io spot adapter (API v4)."""

    def _headers(self, method: str, path: str, query: str = "", body: str = "") -> dict:
        timestamp = str(int(time.time()))
        hashed_payload = hashlib.sha512(body.encode()).hexdigest()
        signature_string = f"{method}\n{path}\n{query}\n{hashed_payload}\n{timestamp}"
        sign = hmac.new(
            self.api_secret.encode(), signature_string.encode(), hashlib.sha512
        ).hexdigest()
        return {
            "KEY": self.api_key,
            "Timestamp": timestamp,
            "SIGN": sign,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @asynccontextmanager
    async def _client(self):
        if self._http_client is not None:
            yield self._http_client
        else:
            async with httpx.AsyncClient(timeout=10) as client:
                yield client

    async def get_balances(self) -> list[Balance]:
        path = f"{GATEIO_PREFIX}/spot/accounts"
        async with self._client() as client:
            resp = await client.get(
                f"{GATEIO_BASE}{path}",
                headers=self._headers("GET", path),
            )
            resp.raise_for_status()
            data = resp.json()

        balances = []
        for item in data:
            free = float(item.get("available", 0))
            locked = float(item.get("locked", 0))
            total = free + locked
            if total > 0:
                balances.append(
                    Balance(asset=item["currency"], free=free, locked=locked, total=total)
                )
        return balances

    async def validate_key(self) -> bool:
        path = f"{GATEIO_PREFIX}/spot/accounts"
        async with self._client() as client:
            resp = await client.get(
                f"{GATEIO_BASE}{path}",
                headers=self._headers("GET", path),
            )
        if resp.status_code in (401, 403):
            logger.error("exchange_key_invalid", exchange="gateio", key=self._mask_key())
            raise ValueError("Invalid API key or secret for Gate.io")
        resp.raise_for_status()
        # Gate.io does not expose withdrawal permission on this endpoint. Read access
        # here is sufficient for a read-only key.
        return True

    async def validate_trade_key(self) -> bool:
        """Gate.io does not expose permission flags here, so we verify connectivity.
        CoinHQ never calls any withdrawal endpoint; create a key with Spot trade
        permission and without withdrawal permission."""
        await self.validate_key()
        return True

    async def place_order(
        self, base_asset: str, side: str, quote_quantity_usd: float, price: float | None = None
    ) -> dict:
        """Spot MARKET order. Gate.io buys are sized by quote (USDT); sells by base."""
        side_l = side.lower()
        if side_l not in ("buy", "sell"):
            raise ValueError("side must be 'buy' or 'sell'")
        if side_l == "buy":
            amount = str(round(float(quote_quantity_usd), 2))
        else:
            amount = str(self._base_qty(quote_quantity_usd, price))
        path = f"{GATEIO_PREFIX}/spot/orders"
        body = json.dumps({
            "currency_pair": f"{base_asset.upper()}_USDT",
            "type": "market",
            "account": "spot",
            "side": side_l,
            "amount": amount,
            "time_in_force": "ioc",
        })
        async with self._client() as client:
            resp = await client.post(
                f"{GATEIO_BASE}{path}",
                content=body,
                headers=self._headers("POST", path, "", body),
            )
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and data.get("label"):
            raise ValueError(f"Gate.io order error: {data.get('message', data['label'])}")
        return data

import hashlib
import hmac
import time
from contextlib import asynccontextmanager
from urllib.parse import urlencode

import httpx

from app.core.logging import logger
from app.exchanges.base import ExchangeAdapter
from app.schemas.portfolio import Balance

BINANCETR_BASE = "https://www.trbinance.com"


class BinanceTRAdapter(ExchangeAdapter):
    """Binance TR (trbinance.com) adapter — uses /open/v1/ REST API."""

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

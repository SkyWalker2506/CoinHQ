import hashlib
import hmac
import time
from contextlib import asynccontextmanager
from urllib.parse import urlencode

import httpx

from app.core.logging import logger
from app.exchanges.base import ExchangeAdapter
from app.schemas.portfolio import Balance

BINANCE_BASE = "https://api.binance.com"


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

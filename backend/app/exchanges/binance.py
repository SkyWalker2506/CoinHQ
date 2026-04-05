import hashlib
import hmac
import time
from typing import List
from urllib.parse import urlencode

import httpx

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

    async def get_balances(self) -> List[Balance]:
        params = self._sign({"timestamp": int(time.time() * 1000)})
        async with httpx.AsyncClient(timeout=10) as client:
            resp = client.get(
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
        try:
            params = self._sign({"timestamp": int(time.time() * 1000)})
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{BINANCE_BASE}/api/v3/account",
                    params=params,
                    headers=self._headers(),
                )
            return resp.status_code == 200
        except Exception:
            return False

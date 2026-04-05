import base64
import hashlib
import hmac
import time
from datetime import datetime, timezone
from typing import List

import httpx

from app.exchanges.base import ExchangeAdapter
from app.schemas.portfolio import Balance

OKX_BASE = "https://www.okx.com"


class OKXAdapter(ExchangeAdapter):
    def __init__(self, api_key: str, api_secret: str, passphrase: str = ""):
        super().__init__(api_key, api_secret)
        # OKX requires a passphrase; store it in api_secret as "secret|passphrase"
        if "|" in api_secret:
            self.api_secret, self.passphrase = api_secret.split("|", 1)
        else:
            self.passphrase = passphrase

    def _sign(self, timestamp: str, method: str, path: str, body: str = "") -> str:
        msg = f"{timestamp}{method}{path}{body}"
        sig = hmac.new(self.api_secret.encode(), msg.encode(), hashlib.sha256).digest()
        return base64.b64encode(sig).decode()

    def _headers(self, method: str, path: str) -> dict:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        sign = self._sign(timestamp, method, path)
        return {
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": sign,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json",
        }

    async def get_balances(self) -> List[Balance]:
        path = "/api/v5/account/balance"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{OKX_BASE}{path}",
                headers=self._headers("GET", path),
            )
            resp.raise_for_status()
            data = resp.json()

        balances = []
        for account in data.get("data", []):
            for detail in account.get("details", []):
                total = float(detail.get("cashBal", 0))
                frozen = float(detail.get("frozenBal", 0))
                free = total - frozen
                if total > 0:
                    balances.append(
                        Balance(
                            asset=detail["ccy"],
                            free=free,
                            locked=frozen,
                            total=total,
                        )
                    )
        return balances

    async def validate_key(self) -> bool:
        try:
            path = "/api/v5/account/balance"
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{OKX_BASE}{path}",
                    headers=self._headers("GET", path),
                )
            return resp.status_code == 200
        except Exception:
            return False

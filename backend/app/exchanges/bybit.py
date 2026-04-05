import hashlib
import hmac
import time
import json
from typing import List

import httpx

from app.exchanges.base import ExchangeAdapter
from app.schemas.portfolio import Balance

BYBIT_BASE = "https://api.bybit.com"


class BybitAdapter(ExchangeAdapter):
    def _sign(self, timestamp: str, params_str: str) -> str:
        recv_window = "5000"
        msg = f"{timestamp}{self.api_key}{recv_window}{params_str}"
        return hmac.new(self.api_secret.encode(), msg.encode(), hashlib.sha256).hexdigest()

    def _headers(self, timestamp: str, sign: str) -> dict:
        return {
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-SIGN": sign,
            "X-BAPI-RECV-WINDOW": "5000",
        }

    async def get_balances(self) -> List[Balance]:
        timestamp = str(int(time.time() * 1000))
        params_str = "accountType=UNIFIED"
        sign = self._sign(timestamp, params_str)

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{BYBIT_BASE}/v5/account/wallet-balance",
                params={"accountType": "UNIFIED"},
                headers=self._headers(timestamp, sign),
            )
            resp.raise_for_status()
            data = resp.json()

        balances = []
        for account in data.get("result", {}).get("list", []):
            for coin in account.get("coin", []):
                total = float(coin.get("walletBalance", 0))
                locked = float(coin.get("locked", 0))
                free = total - locked
                if total > 0:
                    balances.append(
                        Balance(
                            asset=coin["coin"],
                            free=free,
                            locked=locked,
                            total=total,
                        )
                    )
        return balances

    async def validate_key(self) -> bool:
        try:
            timestamp = str(int(time.time() * 1000))
            params_str = "accountType=UNIFIED"
            sign = self._sign(timestamp, params_str)
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{BYBIT_BASE}/v5/account/wallet-balance",
                    params={"accountType": "UNIFIED"},
                    headers=self._headers(timestamp, sign),
                )
            return resp.status_code == 200
        except Exception:
            return False

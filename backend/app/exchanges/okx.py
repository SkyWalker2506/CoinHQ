import base64
import hashlib
import hmac
import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import httpx

from app.core.logging import logger
from app.exchanges.base import ExchangeAdapter
from app.schemas.portfolio import Balance

OKX_BASE = "https://www.okx.com"


class OKXAdapter(ExchangeAdapter):
    def __init__(self, api_key: str, api_secret: str, passphrase: str = "", http_client: httpx.AsyncClient | None = None):
        super().__init__(api_key, api_secret, http_client=http_client)
        # OKX requires a passphrase; store it in api_secret as "secret|passphrase"
        if "|" in api_secret:
            self.api_secret, self.passphrase = api_secret.split("|", 1)
        else:
            self.passphrase = passphrase

    def _sign(self, timestamp: str, method: str, path: str, body: str = "") -> str:
        msg = f"{timestamp}{method}{path}{body}"
        sig = hmac.new(self.api_secret.encode(), msg.encode(), hashlib.sha256).digest()
        return base64.b64encode(sig).decode()

    @asynccontextmanager
    async def _client(self):
        if self._http_client is not None:
            yield self._http_client
        else:
            async with httpx.AsyncClient(timeout=10) as client:
                yield client

    def _headers(self, method: str, path: str, body: str = "") -> dict:
        timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        sign = self._sign(timestamp, method, path, body)
        return {
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": sign,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json",
        }

    async def get_balances(self) -> list[Balance]:
        path = "/api/v5/account/balance"
        async with self._client() as client:
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
        path = "/api/v5/users/me"
        async with self._client() as client:
            resp = await client.get(
                f"{OKX_BASE}{path}",
                headers=self._headers("GET", path),
            )
        resp.raise_for_status()
        data = resp.json()

        # Reject keys that have trade permissions — perm field contains "trade" for write-enabled keys
        perm = ""
        if data.get("data"):
            perm = data["data"][0].get("perm", "")
        if "trade" in perm.lower():
            logger.error("exchange_write_permissions_rejected", exchange="okx", key=self._mask_key())
            raise ValueError("Write permissions detected. Only read-only API keys are accepted.")

        return True

    async def validate_trade_key(self) -> bool:
        """Accept keys with trade permission but reject withdrawal permission."""
        path = "/api/v5/users/me"
        async with self._client() as client:
            resp = await client.get(f"{OKX_BASE}{path}", headers=self._headers("GET", path))
        resp.raise_for_status()
        data = resp.json()
        perm = ""
        if data.get("data"):
            perm = data["data"][0].get("perm", "")
        perm_l = perm.lower()
        if "withdraw" in perm_l:
            logger.error("trade_key_withdrawal_rejected", exchange="okx", key=self._mask_key())
            raise ValueError("This key can withdraw funds. Trade keys must have withdrawals disabled.")
        if "trade" not in perm_l:
            raise ValueError("This key cannot trade. Enable trade permission (withdrawals off).")
        return True

    async def place_order(
        self, base_asset: str, side: str, quote_quantity_usd: float, price: float | None = None
    ) -> dict:
        """Spot MARKET order; sz denominated in quote currency (tgtCcy=quote_ccy)."""
        side_l = side.lower()
        if side_l not in ("buy", "sell"):
            raise ValueError("side must be 'buy' or 'sell'")
        path = "/api/v5/trade/order"
        body = json.dumps({
            "instId": f"{base_asset.upper()}-USDT",
            "tdMode": "cash",
            "side": side_l,
            "ordType": "market",
            "sz": str(round(float(quote_quantity_usd), 2)),
            "tgtCcy": "quote_ccy",
        })
        async with self._client() as client:
            resp = await client.post(
                f"{OKX_BASE}{path}",
                content=body,
                headers=self._headers("POST", path, body),
            )
        resp.raise_for_status()
        data = resp.json()
        if str(data.get("code", "0")) != "0":
            raise ValueError(f"OKX order error: {data.get('msg', 'unknown')}")
        return data.get("data", [{}])[0] if data.get("data") else data

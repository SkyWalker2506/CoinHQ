import hashlib
import hmac
import json
import time
from contextlib import asynccontextmanager

import httpx

from app.core.logging import logger
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

    @asynccontextmanager
    async def _client(self):
        if self._http_client is not None:
            yield self._http_client
        else:
            async with httpx.AsyncClient(timeout=10) as client:
                yield client

    async def get_balances(self) -> list[Balance]:
        timestamp = str(int(time.time() * 1000))
        params_str = "accountType=UNIFIED"
        sign = self._sign(timestamp, params_str)

        async with self._client() as client:
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
        timestamp = str(int(time.time() * 1000))
        params_str = ""
        sign = self._sign(timestamp, params_str)
        async with self._client() as client:
            resp = await client.get(
                f"{BYBIT_BASE}/v5/user/query-api",
                headers=self._headers(timestamp, sign),
            )
        resp.raise_for_status()
        data = resp.json()

        # Reject keys that are not read-only (readOnly: 0 means write access enabled)
        result = data.get("result", {})
        if str(result.get("readOnly", "1")) == "0":
            logger.error("exchange_write_permissions_rejected", exchange="bybit", key=self._mask_key())
            raise ValueError("Write permissions detected. Only read-only API keys are accepted.")

        return True

    async def validate_trade_key(self) -> bool:
        """Accept keys that can trade spot but cannot withdraw."""
        timestamp = str(int(time.time() * 1000))
        sign = self._sign(timestamp, "")
        async with self._client() as client:
            resp = await client.get(
                f"{BYBIT_BASE}/v5/user/query-api",
                headers=self._headers(timestamp, sign),
            )
        resp.raise_for_status()
        result = resp.json().get("result", {})

        permissions = result.get("permissions", {}) or {}
        if permissions.get("Withdraw"):
            logger.error("trade_key_withdrawal_rejected", exchange="bybit", key=self._mask_key())
            raise ValueError(
                "This key can withdraw funds. Trade keys must have withdrawals disabled."
            )
        spot = permissions.get("Spot") or []
        if str(result.get("readOnly", "1")) != "0" and not spot:
            raise ValueError("This key cannot trade. Enable spot trading (withdrawals off).")
        return True

    async def place_order(
        self, base_asset: str, side: str, quote_quantity_usd: float, price: float | None = None
    ) -> dict:
        """Spot MARKET order; qty denominated in the quote coin (marketUnit=quoteCoin)."""
        side_t = side.capitalize()
        if side_t not in ("Buy", "Sell"):
            raise ValueError("side must be 'buy' or 'sell'")
        body = json.dumps({
            "category": "spot",
            "symbol": f"{base_asset.upper()}USDT",
            "side": side_t,
            "orderType": "Market",
            "qty": str(round(float(quote_quantity_usd), 2)),
            "marketUnit": "quoteCoin",
        })
        timestamp = str(int(time.time() * 1000))
        sign = self._sign(timestamp, body)
        headers = {**self._headers(timestamp, sign), "Content-Type": "application/json"}
        async with self._client() as client:
            resp = await client.post(
                f"{BYBIT_BASE}/v5/order/create",
                content=body,
                headers=headers,
            )
        resp.raise_for_status()
        data = resp.json()
        if data.get("retCode") not in (0, None):
            raise ValueError(f"Bybit order error: {data.get('retMsg', 'unknown')}")
        return data.get("result", data)

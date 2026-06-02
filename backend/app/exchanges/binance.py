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

    async def validate_trade_key(self) -> bool:
        """Accept keys that can trade spot but cannot withdraw/transfer."""
        params = self._sign({"timestamp": int(time.time() * 1000)})
        async with self._client() as client:
            resp = await client.get(
                f"{BINANCE_BASE}/api/v3/account",
                params=params,
                headers=self._headers(),
            )
        resp.raise_for_status()
        data = resp.json()

        # A trade key must NOT be able to move funds off the account.
        if data.get("enableWithdrawals") or data.get("enableInternalTransfer"):
            logger.error("trade_key_withdrawal_rejected", exchange="binance", key=self._mask_key())
            raise ValueError(
                "This key can withdraw or transfer funds. Trade keys must have "
                "withdrawals and transfers disabled."
            )
        if not data.get("canTrade"):
            raise ValueError("This key cannot trade. Enable spot trading on the key (withdrawals off).")

        return True

    async def place_order(self, base_asset: str, side: str, quote_quantity_usd: float) -> dict:
        """Place a spot MARKET order quoted in USDT (quoteOrderQty)."""
        side_u = side.upper()
        if side_u not in ("BUY", "SELL"):
            raise ValueError("side must be 'buy' or 'sell'")
        params = self._sign({
            "symbol": f"{base_asset.upper()}USDT",
            "side": side_u,
            "type": "MARKET",
            "quoteOrderQty": round(float(quote_quantity_usd), 2),
            "timestamp": int(time.time() * 1000),
        })
        async with self._client() as client:
            resp = await client.post(
                f"{BINANCE_BASE}/api/v3/order",
                params=params,
                headers=self._headers(),
            )
        resp.raise_for_status()
        return resp.json()

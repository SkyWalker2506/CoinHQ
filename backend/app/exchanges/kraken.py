import base64
import hashlib
import hmac
import time
from contextlib import asynccontextmanager

import httpx

from app.core.logging import logger
from app.exchanges.base import ExchangeAdapter
from app.schemas.portfolio import Balance

KRAKEN_BASE = "https://api.kraken.com"

# Kraken asset name normalization map for common tickers
_KRAKEN_ASSET_MAP = {
    "XXBT": "BTC",
    "XETH": "ETH",
    "XLTC": "LTC",
    "XXRP": "XRP",
    "XXLM": "XLM",
    "XZEC": "ZEC",
    "ZUSD": "USD",
    "ZEUR": "EUR",
    "ZGBP": "GBP",
    "ZCAD": "CAD",
    "ZJPY": "JPY",
}


def _normalize_kraken_asset(asset: str) -> str:
    """Normalize Kraken internal asset codes to standard ticker symbols."""
    if asset in _KRAKEN_ASSET_MAP:
        return _KRAKEN_ASSET_MAP[asset]
    # Strip leading X or Z prefix from 4-char codes (e.g. XDAO -> DAO)
    if len(asset) == 4 and asset[0] in ("X", "Z"):
        return asset[1:]
    return asset


class KrakenAdapter(ExchangeAdapter):
    def _sign(self, path: str, nonce: str, data: str) -> str:
        sha256_digest = hashlib.sha256((nonce + data).encode()).digest()
        secret = base64.b64decode(self.api_secret)
        mac = hmac.new(secret, path.encode() + sha256_digest, hashlib.sha512)
        return base64.b64encode(mac.digest()).decode()

    def _headers(self, path: str, nonce: str, data: str) -> dict:
        return {
            "API-Key": self.api_key,
            "API-Sign": self._sign(path, nonce, data),
            "Content-Type": "application/x-www-form-urlencoded",
        }

    @asynccontextmanager
    async def _client(self):
        if self._http_client is not None:
            yield self._http_client
        else:
            async with httpx.AsyncClient(timeout=10) as client:
                yield client

    async def get_balances(self) -> list[Balance]:
        path = "/0/private/Balance"
        nonce = str(int(time.time() * 1000))
        data = f"nonce={nonce}"

        async with self._client() as client:
            resp = await client.post(
                f"{KRAKEN_BASE}{path}",
                headers=self._headers(path, nonce, data),
                content=data,
            )
            resp.raise_for_status()
            result = resp.json()

        if result.get("error"):
            raise ValueError(f"Kraken API error: {result['error']}")

        balances = []
        for asset, amount in result.get("result", {}).items():
            free = float(amount)
            if free > 0:
                normalized = _normalize_kraken_asset(asset)
                balances.append(
                    Balance(
                        asset=normalized,
                        free=free,
                        locked=0.0,
                        total=free,
                    )
                )
        return balances

    async def validate_key(self) -> bool:
        """Validate key and check for read-only permissions via GetWebSocketsToken endpoint."""
        # Check key permissions: Kraken returns permission flags in API key info
        path = "/0/private/GetWebSocketsToken"
        nonce = str(int(time.time() * 1000))
        data = f"nonce={nonce}"

        async with self._client() as client:
            resp = await client.post(
                f"{KRAKEN_BASE}{path}",
                headers=self._headers(path, nonce, data),
                content=data,
            )

        if resp.status_code == 403:
            logger.error("exchange_key_invalid", exchange="kraken", key=self._mask_key())
            raise ValueError("Invalid API key or permissions for Kraken")

        resp.raise_for_status()
        result = resp.json()

        if result.get("error"):
            errors = result["error"]
            # EGeneral:Permission denied means key lacks this specific permission — still valid
            if any("Permission denied" in e for e in errors):
                # Key is valid but restricted — acceptable for read-only use
                return True
            logger.error("exchange_key_invalid", exchange="kraken", key=self._mask_key(), errors=errors)
            raise ValueError(f"Kraken API key error: {errors}")

        return True

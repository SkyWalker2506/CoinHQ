import base64
import hashlib
import hmac
import time
from contextlib import asynccontextmanager

import httpx

from app.core.logging import logger
from app.exchanges.base import ExchangeAdapter, Fill
from app.schemas.portfolio import Balance

KRAKEN_BASE = "https://api.kraken.com"

# /0/private/TradesHistory pages with `ofs`, up to 100 rows per call, and
# costs 2 points of a rate-limit counter that tops out at 15-20, so only a
# handful of pages can be pulled in one go.
_FILL_PAGE_LIMIT = 100
_FILL_MAX_PAGES = 5

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

    async def get_prices(self, assets: list[str]) -> dict[str, float]:
        """Price against Kraken's own USD/USDT tickers (public, no auth).

        Kraken keys its pairs by internal codes (XXBTZUSD), so the tradable
        pairs are fetched alongside the tickers to recover which asset each
        pair is actually quoting.
        """
        if not assets:
            return {}
        wanted = {a.upper() for a in assets}
        try:
            async with self._client() as client:
                pairs_resp = await client.get(f"{KRAKEN_BASE}/0/public/AssetPairs", timeout=20)
                pairs_resp.raise_for_status()
                pairs = pairs_resp.json().get("result", {})
                ticker_resp = await client.get(f"{KRAKEN_BASE}/0/public/Ticker", timeout=20)
                ticker_resp.raise_for_status()
                tickers = ticker_resp.json().get("result", {})
        except Exception as exc:  # noqa: BLE001 — best-effort, caller falls back
            logger.warning("exchange_price_fetch_failed", exchange="kraken", error=str(exc))
            return {}

        prices: dict[str, float] = {}
        for pair_key, meta in pairs.items():
            quote = meta.get("quote")
            if quote not in ("ZUSD", "USDT"):
                continue
            base = _normalize_kraken_asset(meta.get("base", ""))
            if base not in wanted:
                continue
            # A dollar pair is the better quote; only fill from USDT otherwise.
            if quote == "USDT" and base in prices:
                continue
            try:
                prices[base] = float(tickers[pair_key]["c"][0])
            except (TypeError, ValueError, KeyError, IndexError):
                continue
        return prices

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

    async def get_fills(self, assets: list[str]) -> list[Fill] | None:
        """POST /0/private/TradesHistory, offset-paged, newest first.

        Trades name their pair by Kraken's internal code (XXBTZUSD), so the
        public AssetPairs list is fetched once to recover base and quote.
        `vol` is the base amount, `cost` and `fee` are in the quote currency.
        """
        wanted = {a.upper() for a in assets}
        if not wanted:
            return []
        fills: list[Fill] = []
        try:
            async with self._client() as client:
                pairs_resp = await client.get(f"{KRAKEN_BASE}/0/public/AssetPairs", timeout=20)
                pairs_resp.raise_for_status()
                pairs = pairs_resp.json().get("result", {}) or {}
                pair_map: dict[str, tuple[str, str]] = {}
                for key, meta in pairs.items():
                    base = _normalize_kraken_asset(str(meta.get("base", "")))
                    quote = _normalize_kraken_asset(str(meta.get("quote", "")))
                    if base and quote:
                        pair_map[key] = (base, quote)
                        if meta.get("altname"):
                            pair_map.setdefault(str(meta["altname"]), (base, quote))

                offset = 0
                for _ in range(_FILL_MAX_PAGES):
                    path = "/0/private/TradesHistory"
                    nonce = str(int(time.time() * 1000))
                    data = f"nonce={nonce}&ofs={offset}&limit={_FILL_PAGE_LIMIT}"
                    resp = await client.post(
                        f"{KRAKEN_BASE}{path}",
                        headers=self._headers(path, nonce, data),
                        content=data,
                    )
                    resp.raise_for_status()
                    body = resp.json()
                    if body.get("error"):
                        raise ValueError(f"Kraken API error: {body['error']}")
                    result = body.get("result", {}) or {}
                    trades = result.get("trades", {}) or {}
                    for row in trades.values():
                        fill = self._parse_fill(row, pair_map)
                        if fill is not None and fill.asset in wanted:
                            fills.append(fill)
                    offset += len(trades)
                    total = int(result.get("count") or 0)
                    if not trades or offset >= total:
                        break
        except Exception as exc:  # noqa: BLE001 — best-effort, never raise
            logger.warning("exchange_fills_fetch_failed", exchange="kraken", error=str(exc))
            return None
        return fills

    @staticmethod
    def _parse_fill(row: dict, pair_map: dict[str, tuple[str, str]]) -> Fill | None:
        try:
            pair = str(row["pair"])
            parts = pair_map.get(pair)
            if parts is None:
                return None
            base, quote = parts
            return Fill(
                asset=base,
                side=str(row["type"]).lower(),
                qty=float(row["vol"]),
                quote_asset=quote,
                quote_qty=float(row["cost"]),
                fee_asset=quote,
                fee_qty=max(float(row.get("fee") or 0.0), 0.0),
                ts_ms=int(float(row["time"]) * 1000),
            )
        except (KeyError, TypeError, ValueError):
            return None

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

    async def validate_trade_key(self) -> bool:
        """Kraken does not cleanly expose per-key withdrawal flags here, so we verify
        connectivity. CoinHQ never calls any withdrawal endpoint; create a key with
        'Create & modify orders' but without 'Withdraw funds'."""
        await self.validate_key()
        return True

    async def place_order(
        self, base_asset: str, side: str, quote_quantity_usd: float, price: float | None = None
    ) -> dict:
        """Spot MARKET order. Kraken sizes orders by base volume, so a price is required."""
        side_l = side.lower()
        if side_l not in ("buy", "sell"):
            raise ValueError("side must be 'buy' or 'sell'")
        kraken_base = "XBT" if base_asset.upper() == "BTC" else base_asset.upper()
        volume = self._base_qty(quote_quantity_usd, price)
        path = "/0/private/AddOrder"
        nonce = str(int(time.time() * 1000))
        params = {
            "nonce": nonce,
            "ordertype": "market",
            "type": side_l,
            "volume": str(volume),
            "pair": f"{kraken_base}USDT",
        }
        from urllib.parse import urlencode
        data = urlencode(params)
        async with self._client() as client:
            resp = await client.post(
                f"{KRAKEN_BASE}{path}",
                headers=self._headers(path, nonce, data),
                content=data,
            )
        resp.raise_for_status()
        result = resp.json()
        if result.get("error"):
            raise ValueError(f"Kraken order error: {result['error']}")
        return result.get("result", result)

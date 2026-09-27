import asyncio
import hashlib
import hmac
import json
import time
from contextlib import asynccontextmanager
from urllib.parse import urlencode

import httpx

from app.core.logging import logger
from app.exchanges.base import ExchangeAdapter, Fill
from app.schemas.portfolio import Balance

GATEIO_BASE = "https://api.gateio.ws"
GATEIO_PREFIX = "/api/v4"

# /spot/my_trades: with no time filter only the last 7 days come back, and a
# from/to range may not span more than 30 days (official v4 docs). History is
# therefore walked backwards in 30-day windows. `limit` is documented as
# max 1000, but the older docs said 100, so a page is treated as "possibly
# full" from 100 rows and the next page is requested — a clamped server can
# never make us drop trades.
_FILL_WINDOW_SECONDS = 30 * 24 * 3600
_FILL_MAX_WINDOWS = 24  # ~2 years
_FILL_PAGE_LIMIT = 1000
_FILL_FULL_PAGE = 100
_FILL_MAX_CALLS = 60
_FILL_CONCURRENCY = 4


class GateioAdapter(ExchangeAdapter):
    """Gate.io spot adapter (API v4)."""

    def _headers(self, method: str, path: str, query: str = "", body: str = "") -> dict:
        timestamp = str(int(time.time()))
        hashed_payload = hashlib.sha512(body.encode()).hexdigest()
        signature_string = f"{method}\n{path}\n{query}\n{hashed_payload}\n{timestamp}"
        sign = hmac.new(
            self.api_secret.encode(), signature_string.encode(), hashlib.sha512
        ).hexdigest()
        return {
            "KEY": self.api_key,
            "Timestamp": timestamp,
            "SIGN": sign,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @asynccontextmanager
    async def _client(self):
        if self._http_client is not None:
            yield self._http_client
        else:
            async with httpx.AsyncClient(timeout=10) as client:
                yield client

    async def get_prices(self, assets: list[str]) -> dict[str, float]:
        """Price against Gate.io's own USDT tickers (public, no auth).

        Gate.io lists many low-cap tokens whose tickers collide with unrelated
        coins elsewhere, so its own quotes are the only correct source for
        balances held here.
        """
        if not assets:
            return {}
        wanted = {a.upper() for a in assets}
        try:
            async with self._client() as client:
                resp = await client.get(
                    f"{GATEIO_BASE}{GATEIO_PREFIX}/spot/tickers", timeout=15
                )
                resp.raise_for_status()
                tickers = resp.json()
        except Exception as exc:  # noqa: BLE001 — best-effort, caller falls back
            logger.warning("exchange_price_fetch_failed", exchange="gateio", error=str(exc))
            return {}

        prices: dict[str, float] = {}
        for t in tickers:
            pair = t.get("currency_pair", "")
            if not pair.endswith("_USDT"):
                continue
            base = pair[: -len("_USDT")]
            if base not in wanted:
                continue
            try:
                prices[base] = float(t["last"])
            except (TypeError, ValueError, KeyError):
                continue
        return prices

    async def get_balances(self) -> list[Balance]:
        path = f"{GATEIO_PREFIX}/spot/accounts"
        async with self._client() as client:
            resp = await client.get(
                f"{GATEIO_BASE}{path}",
                headers=self._headers("GET", path),
            )
            resp.raise_for_status()
            data = resp.json()

        balances = []
        for item in data:
            free = float(item.get("available", 0))
            locked = float(item.get("locked", 0))
            total = free + locked
            if total > 0:
                balances.append(
                    Balance(asset=item["currency"], free=free, locked=locked, total=total)
                )
        return balances

    async def get_fills(self, assets: list[str]) -> list[Fill] | None:
        """GET /spot/my_trades across all pairs, 30-day windows back from now.

        One window series covers every pair at once (currency_pair is
        optional), so the cost does not grow with the number of held assets;
        the result is filtered to `assets` afterwards. Windows are fetched a
        few at a time; each window pages until a short page arrives.
        """
        wanted = {a.upper() for a in assets}
        if not wanted:
            return []
        now = int(time.time())
        windows = [
            (now - (i + 1) * _FILL_WINDOW_SECONDS, now - i * _FILL_WINDOW_SECONDS)
            for i in range(_FILL_MAX_WINDOWS)
        ]
        budget = {"calls": 0}
        sem = asyncio.Semaphore(_FILL_CONCURRENCY)

        async def fetch_window(client: httpx.AsyncClient, start: int, end: int) -> list[dict]:
            rows: list[dict] = []
            page = 1
            async with sem:
                while True:
                    if budget["calls"] >= _FILL_MAX_CALLS:
                        logger.warning(
                            "exchange_fills_call_budget_exhausted",
                            exchange="gateio",
                            calls=budget["calls"],
                        )
                        return rows
                    budget["calls"] += 1
                    path = f"{GATEIO_PREFIX}/spot/my_trades"
                    query = urlencode({
                        "from": start,
                        "to": end,
                        "limit": _FILL_PAGE_LIMIT,
                        "page": page,
                    })
                    resp = await client.get(
                        f"{GATEIO_BASE}{path}?{query}",
                        headers=self._headers("GET", path, query),
                    )
                    resp.raise_for_status()
                    batch = resp.json()
                    if not isinstance(batch, list):
                        return rows
                    rows.extend(batch)
                    if len(batch) < _FILL_FULL_PAGE:
                        return rows
                    page += 1

        try:
            async with self._client() as client:
                results = await asyncio.gather(
                    *(fetch_window(client, s, e) for s, e in windows)
                )
        except Exception as exc:  # noqa: BLE001 — best-effort, never raise
            logger.warning("exchange_fills_fetch_failed", exchange="gateio", error=str(exc))
            return None

        fills: list[Fill] = []
        for rows in results:
            for row in rows:
                fill = self._parse_fill(row)
                if fill is not None and fill.asset in wanted:
                    fills.append(fill)
        return fills

    @staticmethod
    def _parse_fill(row: dict) -> Fill | None:
        try:
            pair = str(row["currency_pair"])
            base, quote = pair.split("_", 1)
            qty = float(row["amount"])
            price = float(row["price"])
            ts_raw = row.get("create_time_ms") or row.get("create_time")
            ts = float(ts_raw)
            ts_ms = int(ts if ts > 1e11 else ts * 1000)
            return Fill(
                asset=base.upper(),
                side=str(row["side"]).lower(),
                qty=qty,
                quote_asset=quote.upper(),
                quote_qty=qty * price,
                fee_asset=str(row.get("fee_currency") or "").upper(),
                fee_qty=max(float(row.get("fee") or 0.0), 0.0),
                ts_ms=ts_ms,
            )
        except (KeyError, TypeError, ValueError):
            return None

    async def validate_key(self) -> bool:
        path = f"{GATEIO_PREFIX}/spot/accounts"
        async with self._client() as client:
            resp = await client.get(
                f"{GATEIO_BASE}{path}",
                headers=self._headers("GET", path),
            )
        if resp.status_code in (401, 403):
            logger.error("exchange_key_invalid", exchange="gateio", key=self._mask_key())
            raise ValueError("Invalid API key or secret for Gate.io")
        resp.raise_for_status()
        # Gate.io does not expose withdrawal permission on this endpoint. Read access
        # here is sufficient for a read-only key.
        return True

    async def validate_trade_key(self) -> bool:
        """Gate.io does not expose permission flags here, so we verify connectivity.
        CoinHQ never calls any withdrawal endpoint; create a key with Spot trade
        permission and without withdrawal permission."""
        await self.validate_key()
        return True

    async def place_order(
        self, base_asset: str, side: str, quote_quantity_usd: float, price: float | None = None
    ) -> dict:
        """Spot MARKET order. Gate.io buys are sized by quote (USDT); sells by base."""
        side_l = side.lower()
        if side_l not in ("buy", "sell"):
            raise ValueError("side must be 'buy' or 'sell'")
        if side_l == "buy":
            amount = str(round(float(quote_quantity_usd), 2))
        else:
            amount = str(self._base_qty(quote_quantity_usd, price))
        path = f"{GATEIO_PREFIX}/spot/orders"
        body = json.dumps({
            "currency_pair": f"{base_asset.upper()}_USDT",
            "type": "market",
            "account": "spot",
            "side": side_l,
            "amount": amount,
            "time_in_force": "ioc",
        })
        async with self._client() as client:
            resp = await client.post(
                f"{GATEIO_BASE}{path}",
                content=body,
                headers=self._headers("POST", path, "", body),
            )
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and data.get("label"):
            raise ValueError(f"Gate.io order error: {data.get('message', data['label'])}")
        return data

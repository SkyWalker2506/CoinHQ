"""Demo (paper) exchange adapter — deterministic fake data for local/dev use.

Only registered in the factory when settings.DEMO_MODE is true. No network
calls are ever made. Behavior is driven by markers in the api_key so tests
and demos can exercise both happy paths and rejection paths:

- api_key containing "write"    → validate_key() rejects (write permissions)
- api_key containing "withdraw" → validate_trade_key() rejects (withdrawal perms)
- api_key containing "alt"      → smaller "altcoin" balance preset
- api_key containing "empty"    → no balances
- otherwise                     → main balance preset

place_order() simulates an immediate MARKET fill and returns a Binance-like
response, sizing executedQty from the supplied price (or canned demo prices).
"""

import uuid

from app.exchanges.base import ExchangeAdapter
from app.schemas.portfolio import Balance

# Deterministic demo prices. Used both to size simulated fills and (in DEMO_MODE)
# by the price service, so demos/E2E always see the same portfolio total.
# MAIN preset total = .43*65000 + 3.25*3400 + 30*150 + 1500*1 + 800*.45 = 45360.
DEMO_PRICES: dict[str, float] = {
    "BTC": 65_000.0,
    "ETH": 3_400.0,
    "SOL": 150.0,
    "ADA": 0.45,
    "DOGE": 0.12,
    "USDT": 1.0,
    "USDC": 1.0,
}

_PRESET_MAIN = [
    ("BTC", 0.4200, 0.0100),
    ("ETH", 3.2500, 0.0000),
    ("SOL", 25.000, 5.0000),
    ("USDT", 1500.0, 0.0000),
    ("ADA", 800.00, 0.0000),
]

_PRESET_ALT = [
    ("ETH", 0.8000, 0.0000),
    ("DOGE", 5000.0, 0.0000),
    ("USDT", 250.00, 0.0000),
]


class DemoAdapter(ExchangeAdapter):
    """Paper exchange: deterministic balances, always-valid keys, simulated fills."""

    def _preset(self) -> list[tuple[str, float, float]]:
        key = self.api_key.lower()
        if "empty" in key:
            return []
        if "alt" in key:
            return _PRESET_ALT
        return _PRESET_MAIN

    async def get_balances(self) -> list[Balance]:
        return [
            Balance(asset=asset, free=free, locked=locked, total=free + locked)
            for asset, free, locked in self._preset()
        ]

    async def validate_key(self) -> bool:
        if "write" in self.api_key.lower():
            raise ValueError("Write permissions detected. Only read-only API keys are accepted.")
        return True

    async def validate_trade_key(self) -> bool:
        if "withdraw" in self.api_key.lower():
            raise ValueError(
                "This key can withdraw or transfer funds. Trade keys must have "
                "withdrawals and transfers disabled."
            )
        return True

    async def place_order(
        self, base_asset: str, side: str, quote_quantity_usd: float, price: float | None = None
    ) -> dict:
        side_u = side.upper()
        if side_u not in ("BUY", "SELL"):
            raise ValueError("side must be 'buy' or 'sell'")
        asset = base_asset.upper()
        px = price or DEMO_PRICES.get(asset)
        executed_qty = round(quote_quantity_usd / px, 8) if px and px > 0 else None
        return {
            "orderId": f"demo-{uuid.uuid4().hex[:12]}",
            "symbol": f"{asset}USDT",
            "side": side_u,
            "status": "FILLED",
            "executedQty": str(executed_qty) if executed_qty is not None else None,
            "cummulativeQuoteQty": str(round(quote_quantity_usd, 2)),
        }

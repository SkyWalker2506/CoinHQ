from abc import ABC, abstractmethod

import httpx

from app.schemas.portfolio import Balance


class ExchangeAdapter(ABC):
    """Abstract base class for exchange adapters. Phase 1: read-only."""

    def __init__(self, api_key: str, api_secret: str, http_client: httpx.AsyncClient | None = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self._http_client = http_client

    @abstractmethod
    async def get_balances(self) -> list[Balance]:
        """Fetch non-zero balances from the exchange."""
        ...

    @abstractmethod
    async def validate_key(self) -> bool:
        """Validate that the API key works and has read permissions.

        Implementations MUST:
        - Return True if the key is valid and read-only.
        - Raise ValueError("Write permissions detected. Only read-only API keys are accepted.")
          if the key has any write / trade permissions.
        - Return False (or raise) on connectivity / auth errors.
        """
        ...

    # ── Trading (Phase 2) ────────────────────────────────────────────────────
    # Default implementations refuse trading. Adapters that support spot trading
    # override these. Withdrawals/transfers are NEVER implemented.

    async def validate_trade_key(self) -> bool:
        """Validate that the API key can trade (spot) but CANNOT withdraw/transfer.

        Implementations MUST:
        - Return True if the key can place spot orders and withdrawals are disabled.
        - Raise ValueError if the key can withdraw or transfer funds.
        - Raise ValueError if the key cannot trade.
        """
        raise NotImplementedError(
            f"Trading is not supported for {self.__class__.__name__} yet."
        )

    async def place_order(
        self,
        base_asset: str,
        side: str,
        quote_quantity_usd: float,
        price: float | None = None,
    ) -> dict:
        """Place a spot MARKET order for ~quote_quantity_usd of base_asset against USDT.

        `side` is "buy" or "sell". `price` is the USD price of base_asset, supplied
        by the caller so adapters whose API needs a base quantity (e.g. for sells)
        can convert quote→base. Returns the raw exchange order response.
        """
        raise NotImplementedError(
            f"Trading is not supported for {self.__class__.__name__} yet."
        )

    @staticmethod
    def _base_qty(quote_quantity_usd: float, price: float | None) -> float:
        """Convert a USD quote amount to a base-asset quantity using `price`."""
        if not price or price <= 0:
            raise ValueError("Could not determine the asset price to size this order.")
        return round(quote_quantity_usd / price, 8)

    def _mask_key(self) -> str:
        """Return masked API key for logging."""
        return self.api_key[:6] + "..." if len(self.api_key) > 6 else "***"

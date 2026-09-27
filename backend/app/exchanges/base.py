from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

from app.schemas.portfolio import Balance


@dataclass(frozen=True)
class Fill:
    """One executed spot trade as reported by the venue's own trade history.

    Convention (all adapters MUST follow it so the cost-basis maths is uniform):
    - `asset` is the base symbol, normalised the same way `get_balances` does.
    - `qty` is the GROSS base amount of the fill, before any fee.
    - `quote_qty` is the GROSS quote amount (price × qty), before any fee.
    - The fee is reported separately as `fee_asset`/`fee_qty` (always >= 0;
      rebates are reported as 0). A buy whose fee is charged in the base asset
      therefore credited `qty - fee_qty` to the account; a fee in the quote
      asset raised the effective cost to `quote_qty + fee_qty`.
    """

    asset: str
    side: str  # "buy" | "sell"
    qty: float
    quote_asset: str
    quote_qty: float
    fee_asset: str
    fee_qty: float
    ts_ms: int


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

    async def get_prices(self, assets: list[str]) -> dict[str, float]:
        """USD(T) prices for `assets`, quoted by THIS exchange. Best-effort.

        Prices must come from the venue that actually holds the balance:
        ticker symbols are not globally unique (ATLAS, WOJAK, PUMP and friends
        exist as different tokens on different venues), so pricing a Gate.io
        balance from a global symbol lookup can be off by orders of magnitude.

        A non-empty return makes this adapter AUTHORITATIVE for everything it
        holds: assets missing from the result are treated as having no
        realisable price at this venue rather than falling back to a global
        lookup. That is deliberate — an exchange that has closed a pair will
        not let the holder sell, so crediting them with an outside price
        overstates the portfolio.

        Returning {} means "no opinion" and hands the whole venue to the global
        price service. Implementations must never raise.
        """
        return {}

    async def get_fills(self, assets: list[str]) -> list[Fill] | None:
        """This venue's own spot trade history for `assets`. Best-effort.

        Returns None when the venue does not expose trade history through
        this adapter (or the fetch failed), [] when it does but there are no
        trades, otherwise the fills in any order. `assets` is ordered by
        descending USD value so adapters with a per-asset call budget drop
        the dust first. Implementations must never raise and must never log
        the key.
        """
        return None

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

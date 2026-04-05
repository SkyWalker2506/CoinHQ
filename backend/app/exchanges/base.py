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

    def _mask_key(self) -> str:
        """Return masked API key for logging."""
        return self.api_key[:6] + "..." if len(self.api_key) > 6 else "***"

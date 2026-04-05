from abc import ABC, abstractmethod
from typing import List
from app.schemas.portfolio import Balance


class ExchangeAdapter(ABC):
    """Abstract base class for exchange adapters. Phase 1: read-only."""

    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret

    @abstractmethod
    async def get_balances(self) -> List[Balance]:
        """Fetch non-zero balances from the exchange."""
        ...

    @abstractmethod
    async def validate_key(self) -> bool:
        """Validate that the API key works and has read permissions."""
        ...

    def _mask_key(self) -> str:
        """Return masked API key for logging."""
        return self.api_key[:6] + "..." if len(self.api_key) > 6 else "***"

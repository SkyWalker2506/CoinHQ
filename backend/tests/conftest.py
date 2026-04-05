from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

# Test DB (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture
async def mock_binance_response():
    return {"balances": [{"asset": "BTC", "free": "0.5", "locked": "0.0"}, {"asset": "ETH", "free": "2.0", "locked": "0.0"}]}

@pytest.fixture
def mock_http_client():
    client = AsyncMock(spec=AsyncClient)
    return client

@pytest.fixture
async def mock_coingecko_prices():
    return {"bitcoin": {"usd": 65000}, "ethereum": {"usd": 3500}}

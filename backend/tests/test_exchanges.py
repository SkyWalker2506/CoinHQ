from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.exchanges.binance import BinanceAdapter


def _make_mock_response(payload: dict) -> AsyncMock:
    mock_response = MagicMock()
    mock_response.json.return_value = payload
    mock_response.raise_for_status = MagicMock()
    return mock_response


def _make_mock_client(response) -> AsyncMock:
    """Build a mock that works as an async context manager for httpx.AsyncClient."""
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=response)
    # Support `async with httpx.AsyncClient(...) as client:`
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


@pytest.mark.asyncio
async def test_binance_get_balances_returns_non_zero():
    adapter = BinanceAdapter("test_key", "test_secret")
    payload = {
        "balances": [
            {"asset": "BTC", "free": "0.5", "locked": "0.0"},
            {"asset": "USDT", "free": "1000.0", "locked": "0.0"},
        ]
    }
    mock_response = _make_mock_response(payload)
    mock_client = _make_mock_client(mock_response)

    with patch("app.exchanges.binance.httpx.AsyncClient", return_value=mock_client):
        balances = await adapter.get_balances()

    assert len(balances) > 0
    btc = next((b for b in balances if b.asset == "BTC"), None)
    assert btc is not None
    assert btc.free == 0.5


@pytest.mark.asyncio
async def test_binance_empty_balances_filtered():
    # Zero balances should be filtered out
    adapter = BinanceAdapter("test_key", "test_secret")
    payload = {
        "balances": [
            {"asset": "BTC", "free": "0.0", "locked": "0.0"},
        ]
    }
    mock_response = _make_mock_response(payload)
    mock_client = _make_mock_client(mock_response)

    with patch("app.exchanges.binance.httpx.AsyncClient", return_value=mock_client):
        balances = await adapter.get_balances()

    assert len(balances) == 0

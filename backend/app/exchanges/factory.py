import httpx

from app.core.config import settings
from app.exchanges.base import ExchangeAdapter


def get_adapter(
    exchange: str,
    api_key: str,
    api_secret: str,
    http_client: httpx.AsyncClient | None = None,
) -> ExchangeAdapter:
    """Return the appropriate exchange adapter."""
    exchange = exchange.lower()
    if exchange == "demo" and settings.DEMO_MODE:
        from app.exchanges.demo import DemoAdapter
        return DemoAdapter(api_key, api_secret, http_client=http_client)
    if exchange == "binance":
        from app.exchanges.binance import BinanceAdapter
        return BinanceAdapter(api_key, api_secret, http_client=http_client)
    elif exchange == "bybit":
        from app.exchanges.bybit import BybitAdapter
        return BybitAdapter(api_key, api_secret, http_client=http_client)
    elif exchange == "okx":
        from app.exchanges.okx import OKXAdapter
        return OKXAdapter(api_key, api_secret, http_client=http_client)
    elif exchange == "coinbase":
        from app.exchanges.coinbase import CoinbaseAdapter
        return CoinbaseAdapter(api_key, api_secret, http_client=http_client)
    elif exchange == "kraken":
        from app.exchanges.kraken import KrakenAdapter
        return KrakenAdapter(api_key, api_secret, http_client=http_client)
    elif exchange == "binancetr":
        from app.exchanges.binancetr import BinanceTRAdapter
        return BinanceTRAdapter(api_key, api_secret, http_client=http_client)
    elif exchange == "gateio":
        from app.exchanges.gateio import GateioAdapter
        return GateioAdapter(api_key, api_secret, http_client=http_client)
    else:
        raise ValueError(f"Unsupported exchange: '{exchange}'. Supported: {', '.join(SUPPORTED_EXCHANGES)}")


SUPPORTED_EXCHANGES = ["binance", "bybit", "okx", "coinbase", "kraken", "binancetr", "gateio"]


def supported_exchanges() -> list[str]:
    """Exchanges accepted by the API right now ("demo" only in DEMO_MODE)."""
    if settings.DEMO_MODE:
        return [*SUPPORTED_EXCHANGES, "demo"]
    return list(SUPPORTED_EXCHANGES)

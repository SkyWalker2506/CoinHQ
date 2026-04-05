import httpx

from app.exchanges.base import ExchangeAdapter


def get_adapter(
    exchange: str,
    api_key: str,
    api_secret: str,
    http_client: httpx.AsyncClient | None = None,
) -> ExchangeAdapter:
    """Return the appropriate exchange adapter."""
    exchange = exchange.lower()
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
    else:
        raise ValueError(f"Unsupported exchange: '{exchange}'. Supported: binance, bybit, okx, coinbase, kraken")


SUPPORTED_EXCHANGES = ["binance", "bybit", "okx", "coinbase", "kraken"]


from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "CoinHQ"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://coinhq:coinhq@localhost:5432/coinhq"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    ENCRYPTION_KEY: str  # Fernet key — required

    # JWT
    JWT_SECRET: str  # required
    JWT_ACCESS_EXPIRE_MINUTES: int = 1440   # 24 hours
    JWT_REFRESH_EXPIRE_MINUTES: int = 10080  # 7 days

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = ""

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    @property
    def cors_origins(self) -> list[str]:
        origins = list(self.CORS_ORIGINS)
        if self.FRONTEND_URL and self.FRONTEND_URL not in origins:
            origins.append(self.FRONTEND_URL)
        return origins

    # Rate limiting
    RATE_LIMIT_PORTFOLIO: str = "10/minute"

    # CoinGecko (legacy, unused)
    COINGECKO_BASE_URL: str = "https://api.coingecko.com/api/v3"

    # CoinMarketCap
    CMC_API_KEY: str = ""  # optional — enables CMC as fallback price provider
    CMC_BASE_URL: str = "https://pro-api.coinmarketcap.com"

    # Cache TTL (seconds)
    PORTFOLIO_CACHE_TTL: int = 60

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

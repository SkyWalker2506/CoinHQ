
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
    ENCRYPTION_KEY: str  # Fernet key — required (used as primary if ENCRYPTION_KEYS unset)
    # Optional CSV of additional past Fernet keys for rotation. The first non-empty
    # entry in the merged list (ENCRYPTION_KEY first, then ENCRYPTION_KEYS) is used
    # to encrypt new ciphertexts; all entries are tried for decryption.
    # Example: ENCRYPTION_KEYS="oldkey1=,oldkey2="
    ENCRYPTION_KEYS: str = ""

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

    # CoinGecko
    COINGECKO_BASE_URL: str = "https://api.coingecko.com/api/v3"

    # Cache TTL (seconds)
    PORTFOLIO_CACHE_TTL: int = 60

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

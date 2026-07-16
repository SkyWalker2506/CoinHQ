
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    APP_NAME: str = "CoinHQ"
    DEBUG: bool = False
    # Demo mode: enables the "demo" paper exchange (deterministic fake balances,
    # simulated order fills). Never enable in production.
    DEMO_MODE: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://coinhq:coinhq@localhost:5432/coinhq"

    @field_validator("DATABASE_URL")
    @classmethod
    def _force_asyncpg_driver(cls, v: str) -> str:
        """Normalize the DB URL to the async driver.

        Managed hosts (Railway/Heroku/Render) inject `postgres://` or
        `postgresql://`, but the app + Alembic use SQLAlchemy's async engine which
        needs `postgresql+asyncpg://`. Also strip libpq-only query params (e.g.
        sslmode) that asyncpg does not understand.
        """
        if v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://"):]
        if v.startswith("postgresql://"):
            v = "postgresql+asyncpg://" + v[len("postgresql://"):]
        if v.startswith("postgresql+asyncpg://") and "?" in v:
            v = v.split("?", 1)[0]
        return v

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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

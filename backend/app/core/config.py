"""
Application configuration using Pydantic Settings
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://localhost/viral_weather"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    CACHE_TTL_SECONDS: int = 300  # 5 minutes default

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # External APIs
    AVIATIONSTACK_API_KEY: str = ""
    SOCRATA_APP_TOKEN: str = ""
    MAPBOX_TOKEN: str = ""

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100

    # Data
    DATA_STALENESS_WARNING_DAYS: int = 14
    DATA_STALENESS_HIDE_DAYS: int = 30

    @property
    def async_database_url(self) -> str:
        """Ensure database URL uses asyncpg driver."""
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()

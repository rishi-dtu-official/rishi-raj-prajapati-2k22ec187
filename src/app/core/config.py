"""Application settings for Boostly service."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven configuration values."""

    model_config = SettingsConfigDict(
        env_prefix="BOOSTLY_",
        env_file=".env",
        case_sensitive=False,
    )

    database_url: str = Field(
        default="postgresql+psycopg2://postgres:postgres@localhost:5432/boostly",
        description="SQLAlchemy database URL for PostgreSQL instance.",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()

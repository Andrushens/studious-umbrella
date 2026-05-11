"""Application settings loaded from environment + optional .env file."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = "sqlite+aiosqlite:///./aegis.db"

    etherscan_api_key: str = ""
    etherscan_base_url: str = "https://api.etherscan.io/api"

    alchemy_api_key: str = ""
    alchemy_base_url_tmpl: str = "https://eth-mainnet.g.alchemy.com/v2/{api_key}"

    log_level: str = "INFO"
    log_format: str = "console"

    scheduler_enabled: bool = True
    scan_interval_minutes: int = 60
    scan_concurrency: int = 4

    http_timeout_seconds: float = 10.0

    sentry_dsn: str = ""
    env: str = "development"


def get_settings() -> Settings:
    """Build Settings; tests override via env or kwargs."""
    return Settings()

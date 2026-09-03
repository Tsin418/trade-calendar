from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_prefix="CALENDAR_",
        extra="ignore",
    )

    app_name: str = "Trade Calendar API"
    environment: str = "development"
    database_url: str = "sqlite+aiosqlite:///./calendar.db"
    user_timezone: str = "Asia/Shanghai"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    log_level: str = "INFO"
    session_secret: SecretStr = SecretStr("development-only-change-me")
    feishu_webhook_url: SecretStr | None = None
    finnhub_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("CALENDAR_FINNHUB_API_KEY", "FINNHUB_API_KEY"),
    )
    ics_token: SecretStr = SecretStr("development-ics-token")
    config_dir: Path = Path("../../config")
    public_base_url: str = "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()

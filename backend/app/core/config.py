from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_base_url: str = "http://127.0.0.1:8000"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://127.0.0.1:5173"])

    database_url: str = "postgresql+psycopg://hem:hem@postgres:5432/hem"
    redis_url: str = "redis://redis:6379/0"

    session_cookie_name: str = "hem_session"
    session_ttl_seconds: int = 12 * 60 * 60
    secret_key: str = "change-me-in-.env"

    file_storage_root: Path = Path("/data/files")
    upload_max_bytes: int = 6 * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


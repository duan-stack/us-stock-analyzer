from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    futu_host: str = "127.0.0.1"
    futu_port: int = 11111
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    sqlite_path: str = str(BACKEND_DIR / "data" / "app.db")
    kline_cache_ttl_day_sec: int = 3600
    kline_cache_ttl_minute_sec: int = 300
    news_cache_ttl_sec: int = 1800
    report_cache_ttl_sec: int = 6 * 3600
    cors_origins: str = ""

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

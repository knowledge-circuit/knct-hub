from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_db_url() -> str:
    path = Path.home() / ".knct" / "hub.db"
    return f"sqlite+aiosqlite:///{path}"


def _default_dashboard_dist() -> str:
    # server/src/knct_hub/config.py → server/ is parents[2]
    server_root = Path(__file__).resolve().parents[2]
    return str(server_root.parent / "dashboard" / "dist")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="KNCT_",
        extra="ignore",
    )

    database_url: str = _default_db_url()
    host: str = "127.0.0.1"
    port: int = 8765
    auto_migrate: bool = True
    log_level: str = "INFO"
    dashboard_dist: str = _default_dashboard_dist()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

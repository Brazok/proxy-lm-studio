"""Application configuration loaded from environment variables and .env file."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings sourced from environment variables with PROXY_ prefix.

    All values can be overridden by setting the corresponding environment variable
    (e.g. PROXY_PORT=8443) or by placing them in a .env file at the project root.
    """

    model_config = SettingsConfigDict(
        env_prefix="PROXY_",
        env_file=(".env",),
        env_ignore_empty=True,
        extra="forbid",
    )

    host: str = "0.0.0.0"  # noqa: S104
    port: int = Field(default=443, ge=1, le=65535)
    cert_file: Path = Path("./certs/server.crt")
    key_file: Path = Path("./certs/server.key")
    responses_dir: Path = Path("./responses")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    env: Literal["development", "production", "test"] = "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings (singleton).

    Returns:
        The Settings instance, constructed once and cached for the process lifetime.
    """
    return Settings()

from __future__ import annotations

import logging
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False, env_file=".env", extra="ignore"
    )

    app_name: str
    app_version: str
    app_description: str

    debug: bool = False
    log_level: int = logging.INFO

    redis_host: str
    redis_port: int
    redis_db: int
    redis_url: str

    google_api_key: str
    mediastack_api_key: str

    # Audit Logging
    audit_enabled: bool = True
    audit_retention_days: int = 30

    openai_api_base: str
    openai_api_key: str

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.debug:
            self.log_level = logging.DEBUG


@lru_cache
def get_settings() -> Settings:
    return Settings()

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from functools import lru_cache

class CoreSettings(BaseSettings):
    app_name: str = "Atlas"
    environment: str = "development"
    debug: bool = True
    database_url: str = "postgresql://postgres:postgres@localhost:5432/atlas"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

@lru_cache
def get_settings() -> CoreSettings:
    return CoreSettings()

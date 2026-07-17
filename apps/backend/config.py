from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    app_name: str = Field(default="Atlas Backend API")
    version: str = Field(default="1.0.0")
    debug: bool = Field(default=False)
    environment: str = Field(default="development")
    
    # Database Configuration
    database_url: str = Field(default="sqlite:///./atlas.db")
    
    # API configuration
    api_v1_prefix: str = Field(default="/api/v1")

    # Authentication
    jwt_secret: str = Field(default="dev-secret-key-do-not-use-in-production")
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_expire_minutes: int = Field(default=60)
    admin_emails: list[str] = Field(default_factory=lambda: ["admin@example.com"])

    # Logging
    log_level: str = Field(default="INFO")
    logging_format: str = Field(default="console") # "console" or "json"

    # Celery Configuration
    celery_broker_url: str = Field(default="redis://localhost:6379/0")
    celery_result_backend: str = Field(default="redis://localhost:6379/0")
    celery_task_always_eager: bool = Field(default=False)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

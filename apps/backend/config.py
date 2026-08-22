from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )

    # Authentication
    jwt_secret: str = Field(default="dev-secret-key-do-not-use-in-production")
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_expire_minutes: int = Field(default=60)
    admin_emails: list[str] = Field(default_factory=lambda: ["admin@example.com"])

    # Worker authentication (bearer token for /api/v1/internal/workers)
    worker_auth_token: str | None = Field(default=None)

    # Artifact storage (evaluation artifact base directory)
    artifact_base_dir: str | None = Field(default=None)

    # Logging
    log_level: str = Field(default="INFO")
    logging_format: str = Field(default="console")  # "console" or "json"

    # Celery Configuration
    celery_broker_url: str = Field(default="redis://localhost:6379/0")
    celery_result_backend: str = Field(default="redis://localhost:6379/0")
    celery_task_always_eager: bool = Field(default=False)

    # Outbox Configuration
    outbox_batch_size: int = Field(default=100)
    outbox_poll_interval: int = Field(default=5)

    # Worker wake (API -> Render worker fire-and-forget nudge, post-commit)
    worker_wake_url: str | None = Field(default=None)
    # Worker self-keepalive (worker pings this public URL while a sweep runs)
    worker_public_url: str | None = Field(default=None)
    render_keepalive_interval_seconds: int = Field(default=300)

    # LLM & Agent Configuration
    gemini_api_key: str | None = Field(default=None)
    xai_api_key: str | None = Field(default=None)
    mistral_api_key: str | None = Field(default=None)
    grok_model: str = Field(default="grok-2", validation_alias="GROK_MODEL")
    mistral_model: str = Field(default="mistral-small-latest", validation_alias="MISTRAL_MODEL")
    gemini_model: str = Field(default="gemini-3.5-flash-lite", validation_alias="GEMINI_MODEL")
    llm_provider_timeout_seconds: float = Field(
        default=30.0, validation_alias="LLM_PROVIDER_TIMEOUT"
    )

    # Billing Configuration (Stripe & Razorpay)
    stripe_api_key: str = Field(default="")
    stripe_webhook_secret: str = Field(default="")
    razorpay_key_id: str = Field(default="")
    razorpay_key_secret: str = Field(default="")
    razorpay_webhook_secret: str = Field(default="")

    # Billing Configuration (PayPal)
    paypal_environment: str = Field(default="sandbox", validation_alias="PAYPAL_ENVIRONMENT")
    paypal_client_id: str = Field(default="", validation_alias="PAYPAL_CLIENT_ID")
    # Accept both conventional PAYPAL_CLIENT_SECRET and the pre-existing
    # PAYPAL_SECRET name found on Atlas developer machines.
    paypal_client_secret: str = Field(
        default="",
        validation_alias=AliasChoices("PAYPAL_CLIENT_SECRET", "PAYPAL_SECRET"),
    )
    paypal_webhook_id: str = Field(default="", validation_alias="PAYPAL_WEBHOOK_ID")

    @property
    def stripe_enabled(self) -> bool:
        return bool(self.stripe_api_key)

    @property
    def razorpay_enabled(self) -> bool:
        return bool(self.razorpay_key_id and self.razorpay_key_secret)

    @property
    def paypal_enabled(self) -> bool:
        return bool(self.paypal_client_id and self.paypal_client_secret)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def _validate_environment(self) -> "Settings":
        if self.environment not in ("development", "production"):
            raise ValueError(
                f"ENVIRONMENT={self.environment!r} must be 'development' or 'production'"
            )
        return self

    @model_validator(mode="after")
    def _guard_production_secrets(self) -> "Settings":
        if (
            self.environment == "production"
            and self.jwt_secret == "dev-secret-key-do-not-use-in-production"
        ):
            raise ValueError("JWT_SECRET must be set to a unique value when ENVIRONMENT=production")
        return self


settings = Settings()

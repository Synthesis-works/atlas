from pydantic_settings import BaseSettings


class DatabaseConfig(BaseSettings):
    """Database configuration loaded from environment variables."""

    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "atlas"

    @property
    def database_url(self) -> str:
        import os

        return os.getenv(
            "DATABASE_URL",
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}",
        )

    @property
    def async_database_url(self) -> str:
        import os

        return os.getenv(
            "ASYNC_DATABASE_URL",
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}",
        )


config = DatabaseConfig()

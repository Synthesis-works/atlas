import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "packages", "database"))
)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from apps.backend.logger import logger, setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for the FastAPI application.
    Handles startup and shutdown events.
    """
    # Startup actions
    setup_logging()
    logger.info("Starting Atlas Backend API...")

    # Initialize database schemas and tables on startup for development/SQLite mode
    from apps.backend.config import settings

    if "sqlite" in settings.database_url or settings.environment == "development":
        try:
            from atlas_db.core.initialize import initialize_database_schema
            from atlas_db.core.session import engine

            initialize_database_schema(engine)
        except Exception as e:
            logger.critical(f"Database schema initialization failed: {e}")
            raise RuntimeError(f"Database schema initialization failed: {e}") from e

    yield  # Application is running

    # Shutdown actions
    logger.info("Shutting down Atlas Backend API...")
    # Clean up resources (e.g., close DB connections)

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


    yield  # Application is running

    # Shutdown actions
    logger.info("Shutting down Atlas Backend API...")
    # Clean up resources (e.g., close DB connections)

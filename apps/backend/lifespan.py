from contextlib import asynccontextmanager
from fastapi import FastAPI
from apps.backend.logger import setup_logging, logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for the FastAPI application.
    Handles startup and shutdown events.
    """
    # Startup actions
    setup_logging()
    logger.info("Starting Atlas Backend API...")
    
    # Optional: We could initialize database connections or pre-load caches here
    
    yield  # Application is running
    
    # Shutdown actions
    logger.info("Shutting down Atlas Backend API...")
    # Clean up resources (e.g., close DB connections)

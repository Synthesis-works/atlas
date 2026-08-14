import logging
from sqlalchemy.engine import Engine
from sqlalchemy import inspect
from atlas_db.core.base import Base

# Import all models to register them on the metadata
import atlas_db.models
import packages.execution_engine.persistence.models

logger = logging.getLogger(__name__)

REQUIRED_TABLES = [
    "datasets",
    "benchmarks",
    "benchmark_versions",
    "tasks",
    "prompts",
    "test_cases",
    "executions",
    "model_outputs",
    "evaluation_results",
    "reports",
    "report_versions",
]

def initialize_database_schema(engine: Engine) -> None:
    """
    Initialize database schemas and tables on the target engine.
    Ensures all models are fully registered, and verifies that the required tables exist.
    """
    logger.info(f"Initializing database schema on engine: {engine.url}")
    
    # 1. Create tables
    Base.metadata.create_all(bind=engine)
    
    # 2. Verify all required tables exist
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    logger.info(f"Existing tables in database: {existing_tables}")
    
    missing_tables = [table for table in REQUIRED_TABLES if table not in existing_tables]
    if missing_tables:
        err_msg = f"Database initialization failed. Missing required tables: {missing_tables}"
        logger.error(err_msg)
        raise RuntimeError(err_msg)
        
    logger.info("Database schema initialized and verified successfully.")

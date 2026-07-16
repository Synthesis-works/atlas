import logging
import sys
from apps.backend.config import settings

def setup_logging():
    """
    Configure structured logging for the application.
    """
    # Define log format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Configure root logger
    logging.basicConfig(
        level=settings.log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # You can also configure specific loggers here, e.g. for SQLAlchemy
    # logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    logger = logging.getLogger("atlas.backend")
    logger.info("Logging configured successfully.")
    return logger

logger = logging.getLogger("atlas.backend")

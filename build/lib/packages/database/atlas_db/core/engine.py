from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine

from .config import config

if config.database_url.startswith("sqlite"):
    engine = create_engine(
        config.database_url,
        pool_pre_ping=True,
        connect_args={"timeout": 30, "check_same_thread": False},
    )
else:
    engine = create_engine(config.database_url, pool_pre_ping=True)

if config.async_database_url.startswith("sqlite"):
    async_engine = create_async_engine(config.async_database_url, pool_pre_ping=True)
else:
    async_engine = create_async_engine(config.async_database_url, pool_pre_ping=True)

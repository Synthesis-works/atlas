import os

from sqlalchemy import create_engine, pool
from sqlalchemy.ext.asyncio import create_async_engine

from .config import config


def _resolve_pool_class() -> type[pool.Pool] | None:
    """Return NullPool when DATABASE_POOL_CLASS=null (serverless/Vercel), else None (dialect default)."""
    if os.getenv("DATABASE_POOL_CLASS", "queue").lower() == "null":
        return pool.NullPool
    return None


if config.database_url.startswith("sqlite"):
    engine = create_engine(
        config.database_url,
        pool_pre_ping=True,
        connect_args={"timeout": 30, "check_same_thread": False},
    )
else:
    engine = create_engine(
        config.database_url,
        pool_pre_ping=True,
        poolclass=_resolve_pool_class(),
    )

if config.async_database_url.startswith("sqlite"):
    async_engine = create_async_engine(config.async_database_url, pool_pre_ping=True)
else:
    async_engine = create_async_engine(config.async_database_url, pool_pre_ping=True)

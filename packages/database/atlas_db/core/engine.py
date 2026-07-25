from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine

from .config import config

engine = create_engine(config.database_url, pool_pre_ping=True)
async_engine = create_async_engine(config.async_database_url, pool_pre_ping=True)

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Session, sessionmaker

from .engine import async_engine, engine

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=async_engine)


def get_db() -> Session:  # type: ignore
    """Dependency for providing a synchronous DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncSession:  # type: ignore
    """Dependency for providing an asynchronous DB session."""
    async with AsyncSessionLocal() as session:
        yield session

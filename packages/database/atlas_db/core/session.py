from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from .engine import engine, async_engine

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=async_engine)

def get_db() -> Session:
    """Dependency for providing a synchronous DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_async_db() -> AsyncSession:
    """Dependency for providing an asynchronous DB session."""
    async with AsyncSessionLocal() as session:
        yield session

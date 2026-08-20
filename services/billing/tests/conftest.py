"""
Shared fixtures for billing tests: SQLite in-memory database with the Atlas
metadata, plus SQLite compiler shims for Postgres JSONB/ENUM columns.

Mirrors the conventions in packages/database/tests/conftest.py.
"""

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from atlas_db.core.base import Base


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):  # pragma: no cover - compiler shim
    return "JSON"


@compiles(ENUM, "sqlite")
def _compile_enum_sqlite(type_, compiler, **kw):  # pragma: no cover - compiler shim
    return "VARCHAR"


@pytest.fixture(scope="session")
def engine():
    """Shared in-memory database (one connection via StaticPool so TestClient
    threads see the same data); rows are truncated before each test so
    service-level commits never leak between tests."""
    engine = create_engine(
        "sqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    import atlas_db.models  # noqa: F401  (register all models)

    Base.metadata.create_all(engine)
    return engine


@pytest.fixture()
def session(engine):
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def db_session(session):
    """Alias matching the name used by other Atlas service test suites."""
    return session

import pytest
import sqlalchemy
from atlas_db.core.base import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB, ENUM

@compiles(JSONB, "sqlite")
def compile_jsonb(type_, compiler, **kw):
    return "JSON"

@compiles(ENUM, "sqlite")
def compile_enum(type_, compiler, **kw):
    return "VARCHAR"


@pytest.fixture(scope="session")
def engine():
    engine = create_engine("sqlite:///:memory:", echo=False)

    @sqlalchemy.event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


@pytest.fixture(scope="session")
def init_db(engine):
    import packages.database.atlas_db.models  # Ensure all models are registered
    Base.metadata.create_all(engine)
    yield
    # No need to drop_all for an in-memory DB; avoids SQLite cyclic drop issues


@pytest.fixture
def session(engine, init_db):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()

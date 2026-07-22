import pytest
import sqlalchemy
from atlas_db.core.base import Base
from sqlalchemy import create_engine
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
from sqlalchemy.orm import sessionmaker


def visit_JSONB(self, type_, **kw):
    return "JSON"


def visit_ENUM(self, type_, **kw):
    return "VARCHAR"


SQLiteTypeCompiler.visit_JSONB = visit_JSONB
SQLiteTypeCompiler.visit_ENUM = visit_ENUM


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

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from atlas_db.core.base import Base

@pytest.fixture(scope="session")
def engine():
    return create_engine("sqlite:///:memory:", echo=False)

@pytest.fixture(scope="session")
def init_db(engine):
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)

@pytest.fixture
def session(engine, init_db):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from app.api.routers.reports import get_db, router
from atlas_db.core.base import Base
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

app = FastAPI()
app.include_router(router)


@pytest.fixture
def db_session():
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    # Needs SQLite JSONB compilation hook
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy.ext.compiler import compiles

    @compiles(JSONB, "sqlite")
    def compile_jsonb_sqlite(type_, compiler, **kw):
        return "JSON"

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_get_leaderboard_empty(client):
    response = client.get("/reports/leaderboard")
    assert response.status_code == 200
    assert response.json() == []


# In a real test, we would insert mock DB records and test /evaluations/{id}, /capabilities/{id}, /metrics

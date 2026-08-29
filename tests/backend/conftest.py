"""Shared fixtures for backend API tests."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from atlas_db.core.base import Base


@pytest.fixture
def db_session():
    """A fresh in-memory sqlite session with the full atlas_db schema.

    The published benchmark discovery surface exercises real repository and
    authorization queries, so these tests run against actual tables rather than
    mocks.
    """
    import atlas_db.models.authoring  # noqa: F401
    import atlas_db.models.billing  # noqa: F401
    import atlas_db.models.core  # noqa: F401
    import atlas_db.models.dataset  # noqa: F401
    import atlas_db.models.execution  # noqa: F401
    import atlas_db.models.leaderboard  # noqa: F401
    import atlas_db.models.outbox  # noqa: F401
    import atlas_db.models.tasks  # noqa: F401

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()

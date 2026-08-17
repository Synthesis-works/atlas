import uuid
import pytest
import os
import subprocess
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from alembic.config import Config
from alembic import command
from atlas_db.core.base import Base
import atlas_db.models  # LOAD ALL MODELS

from atlas_db.models.core import Project
from atlas_db.models.dataset import Dataset, DatasetVersion
from atlas_db.models.tasks import Task, Prompt, TestCase, EvaluationRule
from atlas_db.services.dataset_extraction import DatasetExtractionService

# Assuming standard developer postgres resides here based on Makefile
BASE_PG_URL = "postgresql://postgres:postgres@localhost:5432/postgres"

# Removed run_alembic_upgrade to prevent template1 isolation bypass


@pytest.fixture(scope="module")
def postgres_engine():
    # Only run this if we can connect to PG
    try:
        base_engine = create_engine(BASE_PG_URL, isolation_level="AUTOCOMMIT")
        with base_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        pytest.skip(f"PostgreSQL not accessible at localhost:5432: {e}")

    # Generate isolated DB
    test_db_name = f"d2_test_{str(uuid.uuid4()).replace('-', '')}"
    with base_engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE {test_db_name}"))

    test_url = f"postgresql://postgres:postgres@localhost:5432/{test_db_name}"

    engine = create_engine(test_url)

    # Initialize the schema dynamically safely mapping ORM bounds strictly avoiding template inheritance bugs:
    Base.metadata.create_all(engine)

    yield engine

    # Cleanup
    engine.dispose()
    with base_engine.connect() as conn:
        conn.execute(text(f"DROP DATABASE {test_db_name} WITH (FORCE)"))


@pytest.fixture
def pg_session(postgres_engine):
    with Session(postgres_engine) as session:
        yield session


def setup_d2_fixtures(session):
    test_project = Project(id=uuid.uuid4(), slug=f"tp-{uuid.uuid4()}", name="Test PG Proj")
    session.add(test_project)
    session.flush()
    test_dataset = Dataset(id=uuid.uuid4(), project_id=test_project.id, name=f"DS-{uuid.uuid4()}")
    session.add(test_dataset)
    session.flush()
    dv1 = DatasetVersion(
        id=uuid.uuid4(),
        dataset_id=test_dataset.id,
        version_string="v1",
        storage_path="/",
        lifecycle="VALID",
    )
    session.add(dv1)
    session.flush()
    return dv1.id


def test_pg_jsonb_metadata_allowlist(pg_session):
    """
    Test 10: IMPORTANT METADATA TEST against Real PostgreSQL JSONB natively.
    """
    dv1 = setup_d2_fixtures(pg_session)
    t = Task(
        id=uuid.uuid4(),
        dataset_version_id=dv1,
        name="LeakTask",
        order_index=0,
        metadata_={
            "entry_point": "foo",
            "evaluation_secret": "DO_NOT_LEAK",
            "hidden_test_logic": "SECRET",
            "grader_config": {"secret": True},
            "private_assertions": ["assert False"],
            "future_unknown_key": "SECRET",
        },
    )
    p = Prompt(task_id=t.id, template="DEF")
    tc = TestCase(task_id=t.id, input_data={}, expected_output="pass", is_hidden=False)

    # Check EvaluationRule isolation in Postgres
    rule = EvaluationRule(task_id=t.id, rule_definition="R1", context_setup="S1", is_challenge=True)

    pg_session.add_all([t, p, tc, rule])
    pg_session.commit()

    svc = DatasetExtractionService(pg_session)
    ex = svc.get_training_examples(dv1)[0]

    assert ex.metadata == {"entry_point": "foo"}
    dump = ex.model_dump_json()

    # Nothing should leak!
    disallowed = [
        "DO_NOT_LEAK",
        "SECRET",
        "grader_config",
        "private_assertions",
        "future_unknown_key",
        "R1",
        "S1",
    ]
    for d in disallowed:
        assert d not in dump, f"Leaked {d}!"


def test_pg_deterministic_ordering(pg_session):
    """
    Test deterministic ordering with actual DB engine.
    """
    dv1 = setup_d2_fixtures(pg_session)
    for i in range(3):
        t = Task(
            id=uuid.uuid4(),
            dataset_version_id=dv1,
            name=f"Task-{i}",
            order_index=i,
            metadata_={"entry_point": "foo"},
        )
        p = Prompt(task_id=t.id, template="def foo():\n")
        tc = TestCase(task_id=t.id, input_data={}, expected_output="pass", is_hidden=False)
        pg_session.add_all([t, p, tc])
    pg_session.commit()

    import json

    svc1 = DatasetExtractionService(pg_session)
    extract1 = svc1.get_training_examples(dv1)

    svc2 = DatasetExtractionService(pg_session)
    extract2 = svc2.get_training_examples(dv1)

    dump1 = json.dumps([json.loads(ex.model_dump_json()) for ex in extract1], sort_keys=True)
    dump2 = json.dumps([json.loads(ex.model_dump_json()) for ex in extract2], sort_keys=True)

    assert dump1 == dump2
    for i in range(3):
        assert extract1[i].task_name == f"Task-{i}"

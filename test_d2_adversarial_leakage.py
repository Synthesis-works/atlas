import uuid
import sys
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from atlas_db.core.base import Base
from atlas_db.models.core import Project
from atlas_db.models.dataset import Dataset, DatasetVersion
from atlas_db.models.tasks import Task, Prompt, TestCase, EvaluationRule
from atlas_db.services.dataset_extraction import DatasetExtractionService


def setup_db():
    from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

    def visit_JSONB(self, type_, **kw):
        return "JSON"

    def visit_ENUM(self, type_, **kw):
        return "VARCHAR"

    SQLiteTypeCompiler.visit_JSONB = visit_JSONB
    SQLiteTypeCompiler.visit_ENUM = visit_ENUM

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


def test_leakage():
    engine = setup_db()
    with Session(engine) as session:
        test_project = Project(slug="l-proj", name="L-Proj")
        session.add(test_project)
        session.flush()

        test_dataset = Dataset(project_id=test_project.id, name="DS")
        session.add(test_dataset)
        session.flush()

        dv = DatasetVersion(
            dataset_id=test_dataset.id, version_string="v1", storage_path="/", lifecycle="VALID"
        )
        session.add(dv)
        session.commit()

        dv_id = dv.id

    with Session(engine) as session:
        t = Task(
            id=uuid.uuid4(),
            dataset_version_id=dv_id,
            name="Test",
            metadata_={
                "entry_point": "foo",
                "test_setup_code": "SECRET_SETUP",
                "challenge_tests": ["SECRET_ASSERT"],
                "evaluation_secret": "DO_NOT_LEAK",
                "hidden_test_logic": "DO_NOT_LEAK_2",
                "future_unknown_key": "DO_NOT_LEAK_3",
                "grader_config": "DO_NOT_LEAK_4",
                "private_assertions": "DO_NOT_LEAK_5",
            },
        )
        p = Prompt(task_id=t.id, template="def foo():\n")
        tc = TestCase(task_id=t.id, input_data={}, expected_output="pass", is_hidden=False)
        session.add_all([t, p, tc])
        session.commit()

    with Session(engine) as session:
        service = DatasetExtractionService(session)
        ex = service.get_training_examples(dv_id)[0]

        # Verify metadata exact equality bounds against allowlist
        assert ex.metadata == {"entry_point": "foo"}, (
            "Metadata dictionary leaked forbidden structures!"
        )

        dump = ex.model_dump_json()
        print("DUMP:", dump)

        leaked = False
        disallowed_strings = [
            "SECRET_SETUP",
            "SECRET_ASSERT",
            "DO_NOT_LEAK",
            "DO_NOT_LEAK_2",
            "DO_NOT_LEAK_3",
            "DO_NOT_LEAK_4",
            "DO_NOT_LEAK_5",
            "hidden_test_logic",
            "future_unknown_key",
            "grader_config",
        ]

        for string in disallowed_strings:
            if string in dump:
                print(f"FAIL: {string} LEAKED!")
                leaked = True

        if not leaked:
            print("PASS")

        if leaked:
            sys.exit(1)


if __name__ == "__main__":
    test_leakage()

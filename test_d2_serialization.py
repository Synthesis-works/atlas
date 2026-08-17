import uuid
import sys
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from atlas_db.core.base import Base
from atlas_db.models.core import Project
from atlas_db.models.dataset import Dataset, DatasetVersion
from atlas_db.models.tasks import Task, Prompt, TestCase
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


def run_serialization_matrix(engine):
    with Session(engine) as session:
        test_project = Project(slug="p-ser", name="P-Ser")
        session.add(test_project)
        session.flush()
        test_dataset = Dataset(project_id=test_project.id, name="DS-Ser")
        session.add(test_dataset)
        session.flush()
        dv = DatasetVersion(
            dataset_id=test_dataset.id, version_string="v1", storage_path="/", lifecycle="VALID"
        )
        session.add(dv)
        session.commit()

        def execute_case(expected_output, target_assertion):
            t = Task(id=uuid.uuid4(), dataset_version_id=dv.id, name="Test", metadata_={})
            p = Prompt(task_id=t.id, template="T")
            tc = TestCase(
                task_id=t.id, input_data={}, expected_output=expected_output, is_hidden=False
            )
            session.add_all([t, p, tc])
            session.commit()

            service = DatasetExtractionService(session)
            ex = service.get_training_examples(dv.id)[0]
            answer = ex.canonical_answer

            session.delete(tc)
            session.delete(p)
            session.delete(t)
            session.commit()

            if answer != target_assertion:
                return f"FAIL: Expected '{target_assertion}', got '{answer}'"
            return "PASS"

        tests = [
            ("1. Plain string", "def foo(): pass", "def foo(): pass"),
            ("2. Wrapped string", {"output": "def foo(): pass"}, "def foo(): pass"),
            ("3. Wrapped structured", {"output": {"a": 1, "b": [2, 3]}}, '{"a": 1, "b": [2, 3]}'),
            ("4. Unwrapped dict", {"expected_array": [1, 2]}, '{"expected_array": [1, 2]}'),
            (
                "5. Unwrapped list",
                ["assert a == 1", "assert b == 2"],
                '["assert a == 1", "assert b == 2"]',
            ),
            ("6. Numeric value", 5, "5"),
            ("7. Boolean value", True, "true"),
            ("8. Null value", None, "null"),
            (
                "9. Nested mixed JSON",
                {"a": [1, {"b": True}], "c": None},
                '{"a": [1, {"b": true}], "c": null}',
            ),
            ("10. HumanEval Canonical", {"output": "    return a + b"}, "    return a + b"),
            (
                "11. MBPP Canonical",
                {"output": "def sum(a, b): return a + b"},
                "def sum(a, b): return a + b",
            ),
        ]

        failures = False
        for name, input_val, assertion in tests:
            res = execute_case(input_val, assertion)
            print(f"{name.ljust(30)}: {res}")
            if "FAIL" in res:
                failures = True

        if failures:
            sys.exit(1)
        print("ALL TESTS PASSED")


if __name__ == "__main__":
    engine = setup_db()
    run_serialization_matrix(engine)

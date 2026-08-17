import sys
import uuid
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


def test_deterministic():
    engine = setup_db()
    with Session(engine) as session:
        t_proj = Project(slug="dt-proj", name="DT-Proj")
        session.add(t_proj)
        session.flush()

        t_ds = Dataset(project_id=t_proj.id, name="DT-DS")
        session.add(t_ds)
        session.flush()

        dv = DatasetVersion(
            dataset_id=t_ds.id, version_string="v1", storage_path="/", lifecycle="VALID"
        )
        session.add(dv)
        session.commit()
        dv_id = dv.id

        # Add 3 Tasks with identical properties but different order index
        for i in range(3):
            t = Task(
                id=uuid.uuid4(),
                dataset_version_id=dv_id,
                name=f"Task-{i}",
                order_index=i,
                metadata_={"entry_point": "foo"},
            )
            p = Prompt(task_id=t.id, template="def foo():\n")
            tc = TestCase(task_id=t.id, input_data={}, expected_output="pass", is_hidden=False)
            session.add_all([t, p, tc])
        session.commit()

    with Session(engine) as session:
        svc = DatasetExtractionService(session)
        extract1 = svc.get_training_examples(dv_id)

    with Session(engine) as session:
        svc2 = DatasetExtractionService(session)
        extract2 = svc2.get_training_examples(dv_id)

    dump1 = json.dumps([json.loads(ex.model_dump_json()) for ex in extract1], sort_keys=True)
    dump2 = json.dumps([json.loads(ex.model_dump_json()) for ex in extract2], sort_keys=True)

    assert dump1 == dump2, "Extraction is not deterministic!"

    for i in range(3):
        assert extract1[i].task_name == f"Task-{i}", "Order index not respected!"

    print("DETERMINISTIC EXTRACTION: PASS")


if __name__ == "__main__":
    test_deterministic()

import uuid
import sys
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from atlas_db.core.base import Base
from atlas_db.models.core import Project
from atlas_db.models.dataset import Dataset, DatasetVersion
from atlas_db.repositories.dataset import DatasetVersionRepository
from atlas_db.repositories.tasks import (
    TaskRepository,
    PromptRepository,
    TestCaseRepository,
    ConstraintRepository,
    EvaluationRuleRepository,
)
from atlas_db.models.tasks import Task as DBTask, Prompt, TestCase, EvaluationRule
from packages.datasets.models import DatasetPack, DatasetManifest
from packages.datasets.importers.humaneval import HumanEvalMapper
from packages.datasets.importers.mbpp import MBPPMapper
from atlas_db.services.dataset_service import DatasetPersistenceService
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


def test_humaneval_e2e(engine):
    print("--- 1. HUMAN EVAL END-TO-END ---")
    raw = {
        "task_id": "HumanEval/99",
        "prompt": "def dummy():\n",
        "canonical_solution": "    pass\n",
        "entry_point": "dummy",
        "test": "def check(): assert dummy() == None\n",
    }

    # 1. Mapper
    mapper = HumanEvalMapper()
    task = mapper.map(raw)

    # 2. Pack
    manifest = DatasetManifest(
        id="he-pack",
        name="HE Pack",
        version="1.0",
        source="test",
        license="test",
        citation="test",
        language="python",
        evaluation="execution",
        metric="pass@1",
        tags=[],
        tasks=1,
    )
    pack = DatasetPack(manifest=manifest, tasks=[task])

    with Session(engine) as session:
        t_proj = Project(slug="he-proj", name="heProj")
        session.add(t_proj)
        session.flush()
        t_ds = Dataset(project_id=t_proj.id, name="heDS")
        session.add(t_ds)
        session.flush()

        test_dv = DatasetVersion(
            dataset_id=t_ds.id, version_string="v1", storage_path="/", lifecycle="VALID"
        )
        session.add(test_dv)
        session.flush()

        svc = DatasetPersistenceService(
            dataset_version_repo=DatasetVersionRepository(session),
            task_repo=TaskRepository(session),
            prompt_repo=PromptRepository(session),
            test_case_repo=TestCaseRepository(session),
            constraint_repo=ConstraintRepository(session),
            evaluation_rule_repo=EvaluationRuleRepository(session),
        )
        svc.persist_dataset_pack(dataset_version_id=test_dv.id, pack=pack)
        session.commit()

        dv_id = test_dv.id

    with Session(engine) as session:
        # 4. DB Evaluation Check
        db_tasks = session.query(DBTask).filter_by(dataset_version_id=dv_id).all()
        assert len(db_tasks) == 1, "Only 1 DB Task"
        t = db_tasks[0]

        # 5. Extraction
        ext = DatasetExtractionService(session)
        examples = ext.get_training_examples(dv_id)

        assert len(examples) == 1, "Exactly one TrainingExample produced!"
        ex = examples[0]

        assert ex.prompt == raw["prompt"], "Prompt preserved exactly"
        assert ex.canonical_answer == raw["canonical_solution"], "Solution preserved exactly"
        assert ex.metadata["entry_point"] == raw["entry_point"], "Entry point metadata survives"
        assert raw["test"] not in ex.prompt and raw["test"] not in ex.canonical_answer, (
            "Test hidden"
        )
        print("HumanEval E2E: PASS")


def test_mbpp_e2e(engine):
    print("--- 2. MBPP END-TO-END ---")
    raw = {
        "task_id": 1,
        "text": "Write dummy.",
        "code": "def dummy(): pass",
        "test_list": ["assert dummy()", "assert dummy_hidden()"],
        "test_setup_code": "import math",
        "challenge_test_list": ["assert dummy() == None"],
    }

    mapper = MBPPMapper()
    task = mapper.map(raw)

    manifest = DatasetManifest(
        id="mb-pack",
        name="MB Pack",
        version="1.0",
        source="test",
        license="test",
        citation="test",
        language="python",
        evaluation="execution",
        metric="pass@1",
        tags=[],
        tasks=1,
    )
    pack = DatasetPack(manifest=manifest, tasks=[task])

    with Session(engine) as session:
        t_proj = Project(slug="mb-proj", name="mbProj")
        session.add(t_proj)
        session.flush()
        t_ds = Dataset(project_id=t_proj.id, name="mbDS")
        session.add(t_ds)
        session.flush()
        test_dv = DatasetVersion(
            dataset_id=t_ds.id, version_string="v1", storage_path="/", lifecycle="VALID"
        )
        session.add(test_dv)
        session.flush()

        svc = DatasetPersistenceService(
            dataset_version_repo=DatasetVersionRepository(session),
            task_repo=TaskRepository(session),
            prompt_repo=PromptRepository(session),
            test_case_repo=TestCaseRepository(session),
            constraint_repo=ConstraintRepository(session),
            evaluation_rule_repo=EvaluationRuleRepository(session),
        )
        svc.persist_dataset_pack(dataset_version_id=test_dv.id, pack=pack)
        session.commit()
        dv_id = test_dv.id

    with Session(engine) as session:
        ext = DatasetExtractionService(session)
        examples = ext.get_training_examples(dv_id)

        ex = examples[0]
        assert raw["code"] == ex.canonical_answer, "Code exact match"

        dump = ex.model_dump_json()
        assert raw["test_list"][1] not in dump, "No test list"
        assert raw["test_setup_code"] not in dump, "No setup code"
        assert raw["challenge_test_list"][0] not in dump, "No challenge code"
        print("MBPP E2E: PASS")


if __name__ == "__main__":
    engine = setup_db()
    test_humaneval_e2e(engine)
    test_mbpp_e2e(engine)

import uuid
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from atlas_db.core.base import Base
from atlas_db.models.core import Project
from atlas_db.models.dataset import Dataset, DatasetVersion
from atlas_db.models.tasks import Task, Prompt, TestCase, EvaluationRule
from atlas_db.services.dataset_extraction import DatasetExtractionService

def setup_db():
    from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
    def visit_JSONB(self, type_, **kw): return "JSON"
    def visit_ENUM(self, type_, **kw): return "VARCHAR"
    SQLiteTypeCompiler.visit_JSONB = visit_JSONB
    SQLiteTypeCompiler.visit_ENUM = visit_ENUM

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine

def test_adversarial_matrix(engine):
    with Session(engine) as session:
        random_suffix = str(uuid.uuid4())[:8]
        test_project = Project(slug=f"p-{random_suffix}", name=f"P-{random_suffix}")
        session.add(test_project)
        session.flush()
        
        test_dataset = Dataset(project_id=test_project.id, name=f"DS-{random_suffix}")
        session.add(test_dataset)
        session.flush()
        
        dv = DatasetVersion(dataset_id=test_dataset.id, version_string=f"v-{random_suffix}", storage_path="/", lifecycle="VALID")
        session.add(dv)
        session.commit()
    
        def execute_case(name, prompts, public_tcs, hidden_tcs):
            t = Task(id=uuid.uuid4(), dataset_version_id=dv.id, name=name, metadata_={})
            session.add(t)
            session.flush()
            for i in range(prompts):
                session.add(Prompt(task_id=t.id, template="T"))
            for i in range(public_tcs):
                session.add(TestCase(task_id=t.id, input_data={}, expected_output={"output":f"{i}"}, is_hidden=False))
            for i in range(hidden_tcs):
                session.add(TestCase(task_id=t.id, input_data={}, expected_output={"output":f"H{i}"}, is_hidden=True))
            session.commit()
            
            try:
                service = DatasetExtractionService(session)
                res = service.get_training_examples(dv.id)
                session.delete(t)
                session.commit()
                return "PASS"
            except Exception as e:
                session.delete(t)
                session.commit()
                return f"FAIL: {str(e)}"
                
        print("CASE A [1 Prompt | 1 Public TC]:", execute_case("CaseA", 1, 1, 0))
        print("CASE B [1 Prompt | 1 Public TC | 10 Hidden TC]:", execute_case("CaseB", 1, 1, 10))
        print("CASE C [0 Prompt | 1 Public TC]:", execute_case("CaseC", 0, 1, 0))
        print("CASE D [2 Prompt | 1 Public TC]:", execute_case("CaseD", 2, 1, 0))
        print("CASE E [1 Prompt | 0 Public TC]:", execute_case("CaseE", 1, 0, 0))
        print("CASE F [1 Prompt | 2 Public TC]:", execute_case("CaseF", 1, 2, 0))
        print("CASE G [1 Prompt | 0 Public TC | 10 Hidden TC]:", execute_case("CaseG", 1, 0, 10))

if __name__ == "__main__":
    engine = setup_db()
    test_adversarial_matrix(engine)

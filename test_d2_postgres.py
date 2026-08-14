import uuid
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from atlas_db.core.base import Base
from atlas_db.models.core import Project
from atlas_db.models.dataset import Dataset, DatasetVersion
from atlas_db.models.tasks import Task, Prompt, TestCase, EvaluationRule
from atlas_db.services.dataset_extraction import DatasetExtractionService
import test_d2

POSTGRES_URL = "postgresql://postgres:postgres@localhost:5432/postgres"

def main():
    engine = create_engine(POSTGRES_URL)
    
    # Ensure tables exist. Drop first to clear alembic collisions
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    
    with Session(engine) as session:
        test_d2.test_d2_humaneval_extraction_and_leakage(session)
    with Session(engine) as session:
        test_d2.test_d2_dataset_version_isolation(session)
    with Session(engine) as session:
        test_d2.test_d2_cardinality_multiple_rules(session)
    with Session(engine) as session:
        test_d2.test_d2_ambiguity_fails_loudly(session)
    with Session(engine) as session:
        test_d2.test_empty_dataset(session)
        
    Base.metadata.drop_all(engine)
    print("ALL D2 EXTRACTION TESTS PASSED ON POSTGRES!")

if __name__ == "__main__":
    main()

import uuid
import json
import pytest
from atlas_db.models.core import Project
from atlas_db.models.dataset import Dataset, DatasetVersion
from atlas_db.models.tasks import Task, Prompt, TestCase, EvaluationRule
from atlas_db.services.dataset_extraction import DatasetExtractionService

def setup_d2_fixtures(session):
    test_project = Project(id=uuid.uuid4(), slug=f"tp-{uuid.uuid4()}", name="Test Proj")
    session.add(test_project)
    session.flush()
    test_dataset = Dataset(id=uuid.uuid4(), project_id=test_project.id, name=f"DS-{uuid.uuid4()}")
    session.add(test_dataset)
    session.flush()
    dv1 = DatasetVersion(id=uuid.uuid4(), dataset_id=test_dataset.id, version_string="v1", storage_path="/", lifecycle="VALID")
    session.add(dv1)
    session.flush()
    return dv1.id, test_project.id

def test_cardinality_missing_prompt(session):
    dv1, proj_id = setup_d2_fixtures(session)
    t = Task(id=uuid.uuid4(), dataset_version_id=dv1, name="Miss", metadata_={})
    tc = TestCase(task_id=t.id, input_data={}, expected_output="a")
    session.add_all([t, tc])
    session.commit()
    
    svc = DatasetExtractionService(session)
    with pytest.raises(ValueError, match="Ambiguity/Missing Error"):
        svc.get_training_examples(dv1)

def test_cardinality_multiple_prompts(session):
    dv1, proj_id = setup_d2_fixtures(session)
    t = Task(id=uuid.uuid4(), dataset_version_id=dv1, name="Mult", metadata_={})
    p1 = Prompt(task_id=t.id, template="P1")
    p2 = Prompt(task_id=t.id, template="P2")
    tc = TestCase(task_id=t.id, input_data={}, expected_output="A")
    session.add_all([t, p1, p2, tc])
    session.commit()
    
    svc = DatasetExtractionService(session)
    with pytest.raises(ValueError, match="Ambiguity Error"):
        svc.get_training_examples(dv1)

def test_serialization_matrix(session):
    dv1, proj_id = setup_d2_fixtures(session)
    # Test valid JSON structs natively bypassing Python string bugs
    cases = [
        ("str", "solution"),
        ("dict_output", {"output": "pass"}),
        ("nested_dict", {"output": {"a": [1, True]}}),
        ("arbitrary_dict", {"a": [1, True], "b": None}),
        ("empty_list", []),
        ("str_list", ["assert x == 1"]),
        ("null_val", None)
    ]
    
    tasks = []
    for i, (name, expected) in enumerate(cases):
        t = Task(id=uuid.uuid4(), dataset_version_id=dv1, name=name, order_index=i, metadata_={})
        p = Prompt(task_id=t.id, template="P")
        tc = TestCase(task_id=t.id, input_data={}, expected_output=expected, is_hidden=False)
        tasks.extend([t, p, tc])
        
    session.add_all(tasks)
    session.commit()
    
    svc = DatasetExtractionService(session)
    examples = svc.get_training_examples(dv1)
    
    # Verify outputs
    answers = {ex.task_name: ex.canonical_answer for ex in examples}
    assert answers["str"] == "solution"
    assert answers["dict_output"] == "pass"
    assert answers["nested_dict"] == '{"a": [1, true]}'
    assert answers["arbitrary_dict"] == '{"a": [1, true], "b": null}'
    assert answers["empty_list"] == '[]'
    assert answers["str_list"] == '["assert x == 1"]'
    assert answers["null_val"] == 'null'

def test_humaneval_e2e_fidelity(session):
    from packages.datasets.importers.humaneval import HumanEvalMapper
    dv1, proj_id = setup_d2_fixtures(session)
    
    raw = {
        "task_id": "HumanEval/1",
        "prompt": "def has_close_elements",
        "entry_point": "has_close_elements",
        "canonical_solution": "    pass",
        "test": "def check(candidate):\n    assert True"
    }
    
    # Simulate execution path
    mapper = HumanEvalMapper()
    task_pydantic = mapper.map(raw)
    from atlas_db.services.dataset_service import DatasetPersistenceService
    from packages.datasets.models import DatasetPack
    
    pack = DatasetPack(
        project_id=proj_id,
        dataset_name="Mock",
        version="v1",
        tasks=[task_pydantic],
        manifest={
            "id": "mock-eval",
            "name": "Mock Eval",
            "version": "1.0",
            "source": "Mocker",
            "license": "MIT",
            "language": "python",
            "evaluation": "exec",
            "metric": "pass@1",
            "tasks": 1
        }
    )
    
    from atlas_db.repositories.dataset import DatasetVersionRepository
    from atlas_db.repositories.tasks import TaskRepository, PromptRepository, TestCaseRepository, ConstraintRepository, EvaluationRuleRepository
    persistence = DatasetPersistenceService(
        DatasetVersionRepository(session),
        TaskRepository(session),
        PromptRepository(session),
        TestCaseRepository(session),
        ConstraintRepository(session),
        EvaluationRuleRepository(session)
    )
    persistence.persist_dataset_pack(dv1, pack)
    session.commit()
    
    svc = DatasetExtractionService(session)
    ex = svc.get_training_examples(dv1)[0]
    
    assert ex.task_name == "humaneval-1"
    assert ex.prompt == "def has_close_elements"
    assert ex.canonical_answer == "    pass"
    assert ex.metadata == {"entry_point": "has_close_elements"}
    
    dump = ex.model_dump_json()
    assert "def check(candidate)" not in dump

def test_mbpp_e2e_fidelity(session):
    from packages.datasets.importers.mbpp import MBPPMapper
    dv1, proj_id = setup_d2_fixtures(session)
    
    raw = {
        "task_id": 1,
        "text": "Write dummy.",
        "code": "def dummy(): pass",
        "test_list": ["assert dummy()"],
        "test_setup_code": "import math",
        "challenge_test_list": ["assert dummy() == None"]
    }
    
    mapper = MBPPMapper()
    task_pydantic = mapper.map(raw)
    from atlas_db.services.dataset_service import DatasetPersistenceService
    from packages.datasets.models import DatasetPack
    
    pack = DatasetPack(
        project_id=proj_id,
        dataset_name=f"MockMBPP-{uuid.uuid4()}",
        version="v1",
        tasks=[task_pydantic],
        manifest={
            "id": "mock-mbpp",
            "name": "Mock MBPP",
            "version": "1.0",
            "source": "Mocker",
            "license": "MIT",
            "language": "python",
            "evaluation": "exec",
            "metric": "pass@1",
            "tasks": 1
        }
    )
    
    from atlas_db.repositories.dataset import DatasetVersionRepository
    from atlas_db.repositories.tasks import TaskRepository, PromptRepository, TestCaseRepository, ConstraintRepository, EvaluationRuleRepository
    persistence = DatasetPersistenceService(
        DatasetVersionRepository(session),
        TaskRepository(session),
        PromptRepository(session),
        TestCaseRepository(session),
        ConstraintRepository(session),
        EvaluationRuleRepository(session)
    )
    persistence.persist_dataset_pack(dv1, pack)
    session.commit()
    
    svc = DatasetExtractionService(session)
    ex = svc.get_training_examples(dv1)[0]
    
    assert ex.task_name == "mbpp-1"
    assert "assert dummy()" in ex.prompt # Intended! Example string is in prompt.
    assert ex.canonical_answer == "def dummy(): pass"
    assert ex.metadata == {} # No entry point
    
    dump = ex.model_dump_json()
    assert "import math" not in dump
    assert "assert dummy() == None" not in dump

def test_adversarial_metadata_leakage(session):
    dv1, proj_id = setup_d2_fixtures(session)
    t = Task(id=uuid.uuid4(), dataset_version_id=dv1, name="Malicious", metadata_={
        "entry_point": "foo",
        "evaluation_secret": "DO_NOT_LEAK",
        "grader_config": "SECRET",
        "future_unknown_key": "SECRET"
    })
    p = Prompt(task_id=t.id, template="P")
    tc = TestCase(task_id=t.id, input_data={}, expected_output="A", is_hidden=False)
    session.add_all([t, p, tc])
    session.commit()
    
    svc = DatasetExtractionService(session)
    ex = svc.get_training_examples(dv1)[0]
    
    assert ex.metadata == {"entry_point": "foo"}

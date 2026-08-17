import uuid
import pytest
from atlas_db.models.core import Project
from atlas_db.models.dataset import Dataset, DatasetVersion
from atlas_db.models.tasks import Task, Prompt, TestCase, EvaluationRule
from atlas_db.services.dataset_extraction import DatasetExtractionService


def setup_d2_fixtures(session):
    random_suffix = str(uuid.uuid4())[:8]
    test_project = Project(
        id=uuid.uuid4(), slug=f"test-proj-{random_suffix}", name=f"Test Project {random_suffix}"
    )
    session.add(test_project)
    session.flush()

    test_dataset = Dataset(
        id=uuid.uuid4(), project_id=test_project.id, name=f"Test DS {random_suffix}"
    )
    session.add(test_dataset)
    session.flush()

    dv1 = DatasetVersion(
        id=uuid.uuid4(),
        dataset_id=test_dataset.id,
        version_string="v1",
        storage_path="/",
        lifecycle="VALID",
    )
    dv2 = DatasetVersion(
        id=uuid.uuid4(),
        dataset_id=test_dataset.id,
        version_string="v2",
        storage_path="/",
        lifecycle="VALID",
    )
    session.add_all([dv1, dv2])
    session.flush()

    return dv1.id, dv2.id


def test_d2_humaneval_extraction_and_leakage(session):
    dv1, _ = setup_d2_fixtures(session)

    task_id = uuid.uuid4()
    task = Task(
        id=task_id,
        dataset_version_id=dv1,
        name="HumanEval/0",
        order_index=0,
        metadata_={"entry_point": "has_close_elements"},
    )
    prompt = Prompt(
        task_id=task_id,
        template='def has_close_elements(numbers: list[float], threshold: float) -> bool:\n    """ Check if in given list of numbers, are any two numbers closer to each other than\n    given threshold.\n    """\n',
    )
    test_case = TestCase(
        task_id=task_id,
        input_data={"input": "def has_close_elements..."},
        expected_output={"output": "    pass"},
        is_hidden=False,
    )

    rule = EvaluationRule(
        task_id=task_id,
        rule_definition="METADATA_SECRET_RULE",
        context_setup="SECRET_SETUP",
        is_challenge=False,
    )

    session.add_all([task, prompt, test_case, rule])
    session.commit()

    service = DatasetExtractionService(session)
    examples = service.get_training_examples(dv1)

    assert len(examples) == 1
    ex = examples[0]

    assert ex.task_name == "HumanEval/0"
    assert ex.metadata.get("entry_point") == "has_close_elements"
    assert ex.canonical_answer == "    pass"

    # LEAKAGE CHECKS
    serialized = ex.model_dump_json()
    assert "METADATA_SECRET_RULE" not in serialized
    assert "SECRET_SETUP" not in serialized


def test_d2_dataset_version_isolation(session):
    dv1, dv2 = setup_d2_fixtures(session)

    # T1 -> DV1, T2 -> DV2, T3 -> NULL (Benchmark Only)
    t1 = Task(id=uuid.uuid4(), dataset_version_id=dv1, name="T1", metadata_={})
    p1 = Prompt(task_id=t1.id, template="T1_prompt")
    tc1 = TestCase(task_id=t1.id, input_data={}, expected_output={"output": "1"})

    t2 = Task(id=uuid.uuid4(), dataset_version_id=dv2, name="T2", metadata_={})
    p2 = Prompt(task_id=t2.id, template="T2_prompt")
    tc2 = TestCase(task_id=t2.id, input_data={}, expected_output={"output": "2"})

    # Requires benchmark mock
    from atlas_db.models.authoring import Benchmark, BenchmarkVersion

    proj = session.query(Project).first()

    b1 = Benchmark(name="b1", project_id=proj.id, author_id=None)
    session.add(b1)
    session.flush()
    bv1 = BenchmarkVersion(benchmark_id=b1.id, version_string="v1")
    session.add(bv1)
    session.flush()

    t3 = Task(
        id=uuid.uuid4(),
        benchmark_version_id=bv1.id,
        dataset_version_id=None,
        name="T3",
        metadata_={},
    )
    p3 = Prompt(task_id=t3.id, template="T3_prompt")
    tc3 = TestCase(task_id=t3.id, input_data={}, expected_output={"output": "3"})

    t4 = Task(
        id=uuid.uuid4(),
        benchmark_version_id=bv1.id,
        dataset_version_id=dv1,
        name="T4",
        metadata_={},
    )
    p4 = Prompt(task_id=t4.id, template="T4_prompt")
    tc4 = TestCase(task_id=t4.id, input_data={}, expected_output={"output": "4"})

    session.add_all([t1, p1, tc1, t2, p2, tc2, t3, p3, tc3, t4, p4, tc4])
    session.commit()

    service = DatasetExtractionService(session)
    dv1_examples = service.get_training_examples(dv1)

    # Should only pull T1 and T4
    assert len(dv1_examples) == 2
    names = {ex.task_name for ex in dv1_examples}
    assert "T1" in names
    assert "T4" in names
    assert "T2" not in names
    assert "T3" not in names


def test_d2_adversarial_unknown_key(session):
    dv1, _ = setup_d2_fixtures(session)
    t1 = Task(
        id=uuid.uuid4(),
        dataset_version_id=dv1,
        name="AdvRule",
        order_index=5,
        metadata_={"entry_point": "safe_point", "THIS_KEY_MUST_NEVER_LEAK": "SECRET"},
    )
    p1 = Prompt(task_id=t1.id, template="P")
    tc1 = TestCase(task_id=t1.id, input_data={}, expected_output={}, is_hidden=False)
    session.add_all([t1, p1, tc1])
    session.commit()

    svc = DatasetExtractionService(session)
    examples = svc.get_training_examples(dv1)
    ex = examples[-1]

    rep = ex.model_dump_json()
    assert "SECRET" not in rep, (
        "Adversarial structural leakage detected across Extraction boundary."
    )
    assert "THIS_KEY_MUST_NEVER_LEAK" not in rep, (
        "Metadata blocklist failed closed boundary restriction!"
    )
    assert "safe_point" in rep, "Correct payload lost."


def test_d2_cardinality_multiple_rules(session):
    dv1, _ = setup_d2_fixtures(session)
    t1 = Task(id=uuid.uuid4(), dataset_version_id=dv1, name="MultRule", metadata_={})
    p1 = Prompt(task_id=t1.id, template="P")
    tc1 = TestCase(task_id=t1.id, input_data={}, expected_output={})
    r1 = EvaluationRule(task_id=t1.id, rule_definition="R1")
    r2 = EvaluationRule(task_id=t1.id, rule_definition="R2")
    r3 = EvaluationRule(task_id=t1.id, rule_definition="R3")

    session.add_all([t1, p1, tc1, r1, r2, r3])
    session.commit()

    service = DatasetExtractionService(session)
    ex = service.get_training_examples(dv1)
    assert len(ex) == 1


def test_d2_ambiguity_fails_loudly(session):
    dv1, _ = setup_d2_fixtures(session)
    t1 = Task(id=uuid.uuid4(), dataset_version_id=dv1, name="Bad", metadata_={})
    p1 = Prompt(task_id=t1.id, template="P1")
    p2 = Prompt(task_id=t1.id, template="P2")
    tc1 = TestCase(task_id=t1.id, input_data={}, expected_output={})

    session.add_all([t1, p1, p2, tc1])
    session.commit()

    service = DatasetExtractionService(session)
    with pytest.raises(ValueError):
        service.get_training_examples(dv1)


def test_empty_dataset(session):
    dv1, _ = setup_d2_fixtures(session)
    service = DatasetExtractionService(session)
    assert service.get_training_examples(dv1) == []

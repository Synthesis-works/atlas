import pytest
import uuid
from unittest.mock import MagicMock
from atlas_db.models.authoring import BenchmarkState, Benchmark, BenchmarkVersion, BenchmarkCategory, Capability
from atlas_db.services.benchmark_service import BenchmarkService, InvalidStateTransitionError, InvariantViolationError

@pytest.fixture
def service():
    mock_benchmark_repo = MagicMock()
    mock_lifecycle_repo = MagicMock()
    mock_version_repo = MagicMock()
    mock_category_repo = MagicMock()
    mock_capability_repo = MagicMock()
    service = BenchmarkService(
        benchmark_repo=mock_benchmark_repo,
        lifecycle_repo=mock_lifecycle_repo,
        version_repo=mock_version_repo,
        category_repo=mock_category_repo,
        capability_repo=mock_capability_repo
    )
    return service

def create_valid_benchmark(state):
    b = Benchmark(
        id=uuid.uuid4(),
        status=state,
        project_id=uuid.uuid4(),
        author_id=uuid.uuid4()
    )
    # Give it categories/capabilities to pass invariant checks
    b.categories = [BenchmarkCategory(id=uuid.uuid4(), name="Test")]
    b.capabilities = [Capability(id=uuid.uuid4(), name="Test")]
    return b

def create_valid_version(benchmark_id):
    v = BenchmarkVersion(
        id=uuid.uuid4(),
        benchmark_id=benchmark_id,
        version_string="v1.0",
        dataset_version_ids=[uuid.uuid4()],
        evaluation_strategy_id=uuid.uuid4()
    )
    return v

# Exhaustive edges:
allowed_edges = [
    (BenchmarkState.PROPOSAL, BenchmarkState.DESIGN),
    (BenchmarkState.PROPOSAL, BenchmarkState.ARCHIVE),
    (BenchmarkState.DESIGN, BenchmarkState.DRAFT),
    (BenchmarkState.DESIGN, BenchmarkState.ARCHIVE),
    (BenchmarkState.DRAFT, BenchmarkState.VALIDATION),
    (BenchmarkState.DRAFT, BenchmarkState.DESIGN),
    (BenchmarkState.DRAFT, BenchmarkState.ARCHIVE),
    (BenchmarkState.VALIDATION, BenchmarkState.REVIEW),
    (BenchmarkState.VALIDATION, BenchmarkState.DRAFT),
    (BenchmarkState.REVIEW, BenchmarkState.PUBLISHED),
    (BenchmarkState.REVIEW, BenchmarkState.DRAFT),
    (BenchmarkState.PUBLISHED, BenchmarkState.ARCHIVE),
]

all_states = list(BenchmarkState)

def test_exhaustive_transitions(service):
    for from_state in all_states:
        for to_state in all_states:
            if from_state == to_state:
                continue
                
            b = create_valid_benchmark(from_state)
            service.benchmark_repo.get_for_update.return_value = b
            service.benchmark_repo.update.return_value = b
            
            # Setup permissions
            service.can_edit = MagicMock(return_value=True)
            service.can_publish = MagicMock(return_value=True)
            service.can_archive = MagicMock(return_value=True)
            
            if (from_state, to_state) in allowed_edges:
                # Positive test
                updated, events = service.transition_state(b.id, to_state, b.author_id, "project_write")
                assert events[0].changes["to_state"] == str(to_state)
            else:
                # Negative test
                with pytest.raises(InvalidStateTransitionError):
                    service.transition_state(b.id, to_state, b.author_id, "project_write")

def test_validation_action_positive(service):
    b = create_valid_benchmark(BenchmarkState.DRAFT)
    v = create_valid_version(b.id)
    service.version_repo.get.return_value = v
    service.benchmark_repo.get.return_value = b
    service.benchmark_repo.get_for_update.return_value = b
    
    updated_v, events = service.validate_version(v.id, b.author_id, "project_write")
    assert events[0].changes["to_state"] == BenchmarkState.VALIDATION

def test_validation_action_negative_missing_datasets(service):
    b = create_valid_benchmark(BenchmarkState.DRAFT)
    v = create_valid_version(b.id)
    v.dataset_version_ids = None # Missing dataset
    service.version_repo.get.return_value = v
    service.benchmark_repo.get.return_value = b
    
    with pytest.raises(InvariantViolationError):
        service.validate_version(v.id, b.author_id, "project_write")

def test_publish_action_positive(service):
    b = create_valid_benchmark(BenchmarkState.REVIEW)
    v = create_valid_version(b.id)
    service.version_repo.get.return_value = v
    service.benchmark_repo.get.return_value = b
    service.benchmark_repo.get_for_update.return_value = b
    service.can_publish = MagicMock(return_value=True)
    
    updated_v, events = service.publish_version(v.id, b.author_id, "project_admin")
    assert events[0].changes["to_state"] == BenchmarkState.PUBLISHED

def test_archive_action_positive(service):
    b = create_valid_benchmark(BenchmarkState.PUBLISHED)
    v = create_valid_version(b.id)
    service.version_repo.get.return_value = v
    service.benchmark_repo.get.return_value = b
    service.benchmark_repo.get_for_update.return_value = b
    service.can_archive = MagicMock(return_value=True)
    
    updated_v, events = service.archive_version(v.id, b.author_id, "org_admin")
    assert events[0].changes["to_state"] == BenchmarkState.ARCHIVE

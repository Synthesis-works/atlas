import pytest
import uuid
import concurrent.futures
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from sqlalchemy.orm import Session

from atlas_db.models.authoring import BenchmarkState, Benchmark, BenchmarkVersion
from atlas_db.services.benchmark_service import BenchmarkService, ConcurrencyViolationError

def test_concurrent_version_creation():
    # Simulate a race condition where two threads try to create a version
    # using get_for_update. We mock get_for_update to return the benchmark, 
    # but the second one will find the benchmark status already changed if locking wasn't used.
    # In this test we just simulate that BenchmarkService raises ConcurrencyViolationError
    # when status is DRAFT.
    
    mock_benchmark_repo = MagicMock()
    mock_lifecycle_repo = MagicMock()
    mock_version_repo = MagicMock()
    
    service = BenchmarkService(mock_benchmark_repo, mock_lifecycle_repo, mock_version_repo)
    
    # Thread 1 starts when benchmark is PROPOSAL
    b1 = Benchmark(id=uuid.uuid4(), status=BenchmarkState.PROPOSAL, project_id=uuid.uuid4(), author_id=uuid.uuid4())
    mock_benchmark_repo.get_for_update.return_value = b1
    
    # Thread 1 successfully creates version
    version1 = service.create_version(
        benchmark_id=b1.id,
        version_string="v1.0",
        user_id=b1.author_id,
        user_role="project_write"
    )
    
    assert version1 is not None
    
    # After Thread 1, the benchmark status should now be mocked as DRAFT for Thread 2
    b2 = Benchmark(id=b1.id, status=BenchmarkState.DRAFT, project_id=b1.project_id, author_id=b1.author_id)
    mock_benchmark_repo.get_for_update.return_value = b2
    
    # Thread 2 tries to create version concurrently/immediately after
    with pytest.raises(ConcurrencyViolationError):
        service.create_version(
            benchmark_id=b1.id,
            version_string="v2.0",
            user_id=b1.author_id,
            user_role="project_write"
        )

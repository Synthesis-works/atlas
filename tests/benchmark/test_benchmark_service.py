import unittest
import uuid
from unittest.mock import MagicMock
from atlas_db.services.benchmark_service import (
    BenchmarkService,
    PermissionDeniedError,
    InvalidStateTransitionError,
    InvariantViolationError
)
from atlas_db.models.authoring import Benchmark, BenchmarkState, BenchmarkVersion

class TestBenchmarkService(unittest.TestCase):
    def setUp(self):
        self.benchmark_repo = MagicMock()
        self.lifecycle_repo = MagicMock()
        self.version_repo = MagicMock()
        
        self.service = BenchmarkService(
            benchmark_repo=self.benchmark_repo,
            lifecycle_repo=self.lifecycle_repo,
            version_repo=self.version_repo
        )
        
        self.project_id = uuid.uuid4()
        self.author_id = uuid.uuid4()
        self.other_user_id = uuid.uuid4()

    def test_create_benchmark(self):
        # mock repo return
        fake_benchmark = Benchmark(id=uuid.uuid4(), project_id=self.project_id, author_id=self.author_id, status=BenchmarkState.PROPOSAL)
        self.benchmark_repo.create.return_value = fake_benchmark
        
        bench = self.service.create_benchmark(
            project_id=self.project_id,
            author_id=self.author_id,
            name="Test Bench"
        )
        self.assertEqual(bench.project_id, self.project_id)
        self.assertEqual(bench.author_id, self.author_id)
        self.assertEqual(bench.status, BenchmarkState.PROPOSAL)
        self.assertTrue(self.benchmark_repo.create.called)
        self.assertTrue(self.lifecycle_repo.create.called)

    def test_transition_to_design_success(self):
        bench = Benchmark(id=uuid.uuid4(), status=BenchmarkState.PROPOSAL, author_id=self.author_id)
        self.benchmark_repo.get_for_update.return_value = bench
        
        updated_bench = Benchmark(id=bench.id, status=BenchmarkState.DESIGN, author_id=self.author_id)
        self.benchmark_repo.update.return_value = updated_bench
        
        # Author with project write access
        updated = self.service.transition_state(
            benchmark_id=bench.id,
            target_state=BenchmarkState.DESIGN,
            user_id=self.author_id,
            user_role="project_write"
        )
        self.assertEqual(updated.status, BenchmarkState.DESIGN)

    def test_transition_permission_denied(self):
        bench = Benchmark(id=uuid.uuid4(), status=BenchmarkState.PROPOSAL, author_id=self.author_id)
        self.benchmark_repo.get_for_update.return_value = bench
        
        # User with read access only
        with self.assertRaises(PermissionDeniedError):
            self.service.transition_state(
                benchmark_id=bench.id,
                target_state=BenchmarkState.DESIGN,
                user_id=self.other_user_id,
                user_role="project_read"
            )

    def test_transition_publish_success(self):
        bench = Benchmark(id=uuid.uuid4(), status=BenchmarkState.REVIEW, author_id=self.author_id)
        
        # Fake invariant validation
        bench.categories = ["cat"]
        bench.capabilities = ["cap"]
        
        version = BenchmarkVersion()
        version._has_datasets = True
        version._has_evaluators = True
        version._has_metrics = True
        bench.versions = [version]
        
        self.benchmark_repo.get_for_update.return_value = bench
        
        updated_bench = Benchmark(id=bench.id, status=BenchmarkState.PUBLISHED, author_id=self.author_id)
        self.benchmark_repo.update.return_value = updated_bench

        updated = self.service.transition_state(
            benchmark_id=bench.id,
            target_state=BenchmarkState.PUBLISHED,
            user_id=self.author_id,
            user_role="project_write"
        )
        self.assertEqual(updated.status, BenchmarkState.PUBLISHED)
        
    def test_transition_publish_invalid_state(self):
        bench = Benchmark(id=uuid.uuid4(), status=BenchmarkState.PROPOSAL, author_id=self.author_id)
        self.benchmark_repo.get_for_update.return_value = bench
        
        with self.assertRaises(InvalidStateTransitionError):
            self.service.transition_state(
                benchmark_id=bench.id,
                target_state=BenchmarkState.PUBLISHED,
                user_id=self.author_id,
                user_role="project_write"
            )

    def test_invariants_missing_category(self):
        bench = Benchmark(id=uuid.uuid4(), status=BenchmarkState.DRAFT, author_id=self.author_id)
        bench.categories = [] # missing category
        bench.capabilities = ["cap"]
        self.benchmark_repo.get_for_update.return_value = bench
        
        with self.assertRaises(InvariantViolationError):
            self.service.transition_state(
                benchmark_id=bench.id,
                target_state=BenchmarkState.VALIDATION,
                user_id=self.author_id,
                user_role="project_write"
            )

if __name__ == '__main__':
    unittest.main()

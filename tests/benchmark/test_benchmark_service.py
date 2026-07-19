import unittest
import uuid
from unittest.mock import MagicMock
from atlas_db.services.benchmark_service import (
    BenchmarkService,
    PermissionDeniedError,
    InvalidStateTransitionError,
    ValidationError
)
from atlas_db.models.authoring import Benchmark, BenchmarkState, BenchmarkVersion

class TestBenchmarkService(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock()
        self.service = BenchmarkService(self.db)
        
        self.project_id = uuid.uuid4()
        self.author_id = uuid.uuid4()
        self.other_user_id = uuid.uuid4()

    def test_create_benchmark(self):
        bench = self.service.create_benchmark(
            project_id=self.project_id,
            author_id=self.author_id,
            name="Test Bench"
        )
        self.assertEqual(bench.project_id, self.project_id)
        self.assertEqual(bench.author_id, self.author_id)
        self.assertEqual(bench.status, BenchmarkState.PROPOSAL)
        self.assertTrue(self.db.add.called)
        self.assertTrue(self.db.commit.called)

    def test_transition_to_design_success(self):
        bench = Benchmark(id=uuid.uuid4(), status=BenchmarkState.PROPOSAL, author_id=self.author_id)
        
        # Author with project write access
        updated = self.service.transition_state(
            benchmark=bench,
            target_state=BenchmarkState.DESIGN,
            user_id=self.author_id,
            user_role="project_write"
        )
        self.assertEqual(updated.status, BenchmarkState.DESIGN)

    def test_transition_permission_denied(self):
        bench = Benchmark(id=uuid.uuid4(), status=BenchmarkState.PROPOSAL, author_id=self.author_id)
        
        # User with read access only
        with self.assertRaises(PermissionDeniedError):
            self.service.transition_state(
                benchmark=bench,
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
        
        updated = self.service.transition_state(
            benchmark=bench,
            target_state=BenchmarkState.PUBLISHED,
            user_id=self.author_id,
            user_role="project_write"
        )
        self.assertEqual(updated.status, BenchmarkState.PUBLISHED)
        
    def test_transition_publish_invalid_state(self):
        bench = Benchmark(id=uuid.uuid4(), status=BenchmarkState.PROPOSAL, author_id=self.author_id)
        
        with self.assertRaises(InvalidStateTransitionError):
            self.service.transition_state(
                benchmark=bench,
                target_state=BenchmarkState.PUBLISHED,
                user_id=self.author_id,
                user_role="project_write"
            )

    def test_invariants_missing_category(self):
        bench = Benchmark(id=uuid.uuid4(), status=BenchmarkState.DRAFT, author_id=self.author_id)
        bench.categories = [] # missing category
        bench.capabilities = ["cap"]
        
        with self.assertRaises(ValidationError):
            self.service.transition_state(
                benchmark=bench,
                target_state=BenchmarkState.VALIDATION,
                user_id=self.author_id,
                user_role="project_write"
            )

if __name__ == '__main__':
    unittest.main()

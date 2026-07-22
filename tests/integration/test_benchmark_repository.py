import unittest
from unittest.mock import MagicMock

from atlas_db.repositories.authoring import Benchmark, BenchmarkRepository
from sqlalchemy.orm import Session


class TestBenchmarkRepositoryIntegration(unittest.TestCase):
    def setUp(self):
        self.session = MagicMock(spec=Session)
        self.repo = BenchmarkRepository(db=self.session)

    def test_get_for_update_uses_pessimistic_locking(self):
        mock_query = self.session.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_with_for_update = mock_filter.with_for_update.return_value

        expected_bench = Benchmark(name="Test")
        mock_with_for_update.first.return_value = expected_bench

        bench = self.repo.get_for_update(1)

        self.session.query.assert_called_with(Benchmark)
        self.assertTrue(mock_filter.with_for_update.called)
        self.assertEqual(bench, expected_bench)

    def test_create_respects_commit_flag(self):
        # With commit=True
        self.repo.create(obj_in={"name": "Test1", "project_id": 1}, commit=True)
        self.assertTrue(self.session.commit.called)
        self.session.commit.reset_mock()

        # With commit=False
        self.repo.create(obj_in={"name": "Test2", "project_id": 2}, commit=False)
        self.assertFalse(self.session.commit.called)
        self.assertTrue(self.session.flush.called)

    def test_update_respects_commit_flag(self):
        db_obj = Benchmark(name="Old")

        # With commit=True
        self.repo.update(db_obj=db_obj, obj_in={"name": "New1"}, commit=True)
        self.assertTrue(self.session.commit.called)
        self.session.commit.reset_mock()

        # With commit=False
        self.repo.update(db_obj=db_obj, obj_in={"name": "New2"}, commit=False)
        self.assertFalse(self.session.commit.called)
        self.assertTrue(self.session.flush.called)


if __name__ == "__main__":
    unittest.main()

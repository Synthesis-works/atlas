import uuid
from unittest.mock import MagicMock, Mock

import pytest
from sqlalchemy.orm import Session

from packages.database.atlas_db.repositories.leaderboard import LeaderboardRepository


@pytest.fixture
def mock_db_session():
    return MagicMock(spec=Session)


@pytest.fixture
def leaderboard_repo(mock_db_session):
    return LeaderboardRepository(db=mock_db_session)


def test_get_benchmark_leaderboard(leaderboard_repo, mock_db_session):
    benchmark_version_id = uuid.uuid4()

    # Mock the return of the final .all() query
    mock_query = MagicMock()
    mock_query.offset.return_value.limit.return_value.all.return_value = [
        ("model_a", 95.5, 10, "2023-01-01T00:00:00Z", uuid.uuid4()),
        ("model_b", 92.0, 10, "2023-01-02T00:00:00Z", uuid.uuid4()),
    ]

    # Set up the chain
    mock_db_session.query.return_value.join.return_value.filter.return_value.order_by.return_value = mock_query

    results, total = leaderboard_repo.get_benchmark_leaderboard(
        benchmark_version_id=benchmark_version_id, limit=10, offset=0
    )

    assert total == 10
    assert len(results) == 2
    assert results[0][0] == "model_a"
    assert results[0][1] == 95.5
    assert results[0][2] == 1  # Benchmark count is strictly 1 for benchmark leaderboard


def test_get_benchmark_leaderboard_empty(leaderboard_repo, mock_db_session):
    benchmark_version_id = uuid.uuid4()

    mock_query = MagicMock()
    mock_query.offset.return_value.limit.return_value.all.return_value = []

    mock_db_session.query.return_value.join.return_value.filter.return_value.order_by.return_value = mock_query

    results, total = leaderboard_repo.get_benchmark_leaderboard(
        benchmark_version_id=benchmark_version_id, limit=10, offset=0
    )

    assert total == 0
    assert len(results) == 0


def test_get_capability_leaderboard(leaderboard_repo, mock_db_session):
    capability_id = uuid.uuid4()

    # Mock the scalar() for total count
    mock_count_query = MagicMock()
    mock_count_query.join.return_value.join.return_value.filter.return_value.scalar.return_value = 5

    # Mock the all() for results
    mock_main_query = MagicMock()
    mock_main_query.join.return_value.join.return_value.filter.return_value.group_by.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [
        ("model_c", 88.0, 3, "2023-01-01T00:00:00Z", uuid.uuid4())
    ]

    # We need to configure the db.query mock to return the count query for the first call
    # and the main query for the second call.
    mock_db_session.query.side_effect = [
        MagicMock(),  # CTE query
        mock_count_query,  # Count query
        mock_main_query,  # Main query
    ]

    results, total = leaderboard_repo.get_capability_leaderboard(
        capability_id=capability_id, limit=10, offset=0
    )

    assert total == 5
    assert len(results) == 1
    assert results[0][0] == "model_c"
    assert results[0][1] == 88.0
    assert results[0][2] == 3

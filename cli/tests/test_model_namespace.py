"""Regression guard for Pydantic ``model_*`` protected-namespace warnings.

Pydantic < 2.10 warns when fields are named ``model_name`` / ``model_output_id``
(default protected namespaces).  The 4 shipped model classes opt out explicitly
so users on older Pydantic 2.x never see the warning; this test keeps them
honest and verifies serialization/validation are unchanged.
"""

from __future__ import annotations

import warnings
from datetime import UTC, datetime
from uuid import UUID

from atlas_sdk.models.dashboard import DashboardCapability
from atlas_sdk.models.evaluation import EvaluationResultItemRead
from atlas_sdk.models.leaderboard import LeaderboardEntryRead

from cli.agent.tools.library import _ModelNameArgs


def _build_all() -> list[object]:
    return [
        DashboardCapability(model_name="gpt-x", provider="test", rank=1, score=0.9),
        EvaluationResultItemRead(
            model_output_id=UUID("00000000-0000-0000-0000-000000000001"),
            strategy_version_id=UUID("00000000-0000-0000-0000-000000000002"),
            status="PASSED",
            passed=True,
        ),
        LeaderboardEntryRead(
            rank=1,
            model_name="gpt-x",
            overall_score=0.9,
            benchmark_count=1,
            last_updated=datetime(2026, 1, 1, tzinfo=UTC),
        ),
        _ModelNameArgs(model_name="gpt-x"),
    ]


def test_no_protected_namespace_warnings() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _build_all()
    namespace_warnings = [w for w in caught if "protected namespace" in str(w.message)]
    assert namespace_warnings == []


def test_field_names_and_serialization_unchanged() -> None:
    capability = DashboardCapability(model_name="gpt-x", provider="test", rank=1, score=0.9)
    assert list(DashboardCapability.model_fields) == [
        "model_name",
        "provider",
        "rank",
        "score",
        "capabilities",
    ]
    assert capability.model_dump()["model_name"] == "gpt-x"

    result = EvaluationResultItemRead(
        model_output_id=UUID("00000000-0000-0000-0000-000000000001"),
        strategy_version_id=UUID("00000000-0000-0000-0000-000000000002"),
        status="PASSED",
        passed=True,
    )
    assert "model_output_id" in result.model_dump()

    entry = LeaderboardEntryRead(
        rank=1,
        model_name="gpt-x",
        overall_score=0.9,
        benchmark_count=1,
        last_updated=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert entry.model_dump()["model_name"] == "gpt-x"

    args = _ModelNameArgs(model_name="gpt-x")
    assert args.model_name == "gpt-x"

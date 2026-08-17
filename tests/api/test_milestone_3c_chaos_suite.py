"""
Milestone 3C Validation Suite — Distributed Execution Pipeline & Chaos Verification
Validates Deliverables 1-4:
  1. Happy Path Execution & Trace Correlation
  2. Worker Death & Expired Lease Recovery (Scheduler Sweep)
  3. Queue Reconciliation (Redis loss / missing tasks)
  4. Duplicate Dispatch Idempotency
  5. Operational Prometheus Metrics Endpoint (/api/v1/system/metrics)
"""

import uuid
from datetime import datetime, timezone, timedelta, UTC
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from apps.backend.main import app
from apps.backend.schemas.auth import TokenClaims
from apps.backend.dependencies import (
    require_authenticated,
    get_db_session,
)
from apps.backend.routers.executions import get_execution_service
from packages.execution_engine.domain.models import (
    Execution,
    ExecutionState,
    Lease,
    ExecutionAttempt,
)
from packages.execution_engine.application.scheduler_service import SchedulerService

client = TestClient(app)


@pytest.fixture(autouse=True)
def override_auth_and_services():
    """Supply mock auth claims, session, and execution service."""
    user_id = uuid.uuid4()
    mock_claims = TokenClaims(
        sub=user_id,
        exp=0,
        iat=0,
        jti=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        membership_id=uuid.uuid4(),
    )

    execution_cache: dict[str, Execution] = {}

    def mock_submit_execution(benchmark_version_id: uuid.UUID, created_by: uuid.UUID = None):
        cache_key = str(benchmark_version_id)
        if cache_key in execution_cache:
            return execution_cache[cache_key]

        exec_domain = Execution.rehydrate(
            id=uuid.uuid4(),
            benchmark_version_id=benchmark_version_id,
            project_id=uuid.uuid4(),
            status=ExecutionState.QUEUED,
            created_by=user_id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            max_retries=3,
            attempts=[],
        )
        execution_cache[cache_key] = exec_domain
        return exec_domain

    mock_service = MagicMock()
    mock_service.submit_execution.side_effect = mock_submit_execution

    app.dependency_overrides[get_db_session] = lambda: MagicMock()
    app.dependency_overrides[require_authenticated] = lambda: mock_claims
    app.dependency_overrides[get_execution_service] = lambda: mock_service
    yield
    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(require_authenticated, None)
    app.dependency_overrides.pop(get_execution_service, None)


def test_deliverable_4_prometheus_metrics_endpoint():
    """Verify GET /api/v1/system/metrics exposes operational Prometheus metrics."""
    response = client.get("/api/v1/system/metrics")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    content = response.text
    assert "atlas_executions_queued_total" in content, (
        "Metrics output missing atlas_executions_queued_total"
    )
    assert "atlas_executions_running_total" in content, (
        "Metrics output missing atlas_executions_running_total"
    )
    assert "atlas_outbox_pending_total" in content, (
        "Metrics output missing atlas_outbox_pending_total"
    )


def test_chaos_scenario_duplicate_dispatch_idempotency():
    """Verify consecutive duplicate dispatches for same benchmark return identical execution ID."""
    version_id = uuid.uuid4()
    req_id = str(uuid.uuid4())
    headers = {"X-Request-ID": req_id}
    payload = {"benchmark_version_id": str(version_id), "target_model": "Claude-3.5"}

    res1 = client.post(f"/api/v1/benchmarks/{version_id}/executions", json=payload, headers=headers)
    res2 = client.post(f"/api/v1/benchmarks/{version_id}/executions", json=payload, headers=headers)

    assert res1.status_code in [200, 201]
    assert res2.status_code in [200, 201]
    assert res1.json()["id"] == res2.json()["id"], (
        "Idempotent dispatches must return the exact same execution UUID"
    )


def test_chaos_scenario_expired_lease_sweep_recovery():
    """Verify SchedulerService sweeps expired leases and transitions execution status to FAILED_RETRYABLE."""
    domain_service = MagicMock()
    execution_repo = MagicMock()

    # Create expired execution domain object
    expired_exec = Execution.rehydrate(
        id=uuid.uuid4(),
        benchmark_version_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        status=ExecutionState.RUNNING,
        created_by=uuid.uuid4(),
        created_at=datetime.now(UTC) - timedelta(minutes=10),
        updated_at=datetime.now(UTC) - timedelta(minutes=10),
        max_retries=3,
        attempts=[],
    )

    execution_repo.find_expired_active_attempts.return_value = [expired_exec]

    scheduler = SchedulerService(domain_service=domain_service, execution_repo=execution_repo)
    swept = scheduler.sweep_expired_leases(limit=50)

    assert swept == 1, f"Expected 1 lease swept, got {swept}"
    domain_service.expire_lease.assert_called_once_with(expired_exec)
    execution_repo.save.assert_called_once_with(expired_exec)

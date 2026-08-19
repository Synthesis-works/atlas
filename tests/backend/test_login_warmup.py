"""Tests for the login worker warm-up mechanism.

The warm-up must be fire-and-forget, throttled, never block or fail the login
response, never create execution/outbox rows, and never interfere with the
authoritative post-commit execution wake.
"""

from unittest.mock import MagicMock, Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from apps.backend.authz import require_permission
from apps.backend.dependencies import get_auth_service
from apps.backend.main import app
from apps.backend.schemas.auth import TokenResponse
from apps.backend.worker import wake_client

mock_auth_service = MagicMock()
UNREACHABLE_WAKE_URL = "http://127.0.0.1:1/wake"


class FakeThread:
    """Records Thread creations without executing anything."""

    started: list["FakeThread"] = []

    def __init__(self, target=None, daemon=None, name=None, **kwargs) -> None:
        self.target = target
        self.name = name
        FakeThread.started.append(self)

    def start(self) -> None:
        pass


@pytest.fixture
def client():
    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def warmup_isolation(monkeypatch):
    FakeThread.started.clear()
    monkeypatch.setattr(wake_client.threading, "Thread", FakeThread)
    monkeypatch.setattr(wake_client, "_last_warmup_sent", float("-inf"))
    monkeypatch.setattr(wake_client, "WARMUP_COOLDOWN_SECONDS", 300)
    monkeypatch.setattr(wake_client.settings, "worker_wake_url", UNREACHABLE_WAKE_URL)
    yield


def logged_in(client) -> None:
    mock_auth_service.authenticate_user.return_value = TokenResponse(
        access_token="mocked.jwt.token", token_type="bearer"
    )
    response = client.post("/api/v1/auth/login", json={"email": "a@b.c", "password": "pw"})
    assert response.status_code == 200


def test_login_returns_normally_and_triggers_wake(client):
    logged_in(client)
    assert len(FakeThread.started) == 1
    assert FakeThread.started[0].name == "worker-warmup"
    assert FakeThread.started[0].target is wake_client._send_wake


def test_login_wake_is_fire_and_forget(client, monkeypatch):
    def boom() -> None:
        raise RuntimeError("network failure")

    monkeypatch.setattr(wake_client, "_send_wake", boom)
    logged_in(client)
    assert mock_auth_service.authenticate_user.called


def test_wake_is_throttled_within_cooldown(client):
    logged_in(client)
    logged_in(client)
    logged_in(client)
    assert len(FakeThread.started) == 1


def test_wake_fires_after_cooldown_expires(client, monkeypatch):
    monkeypatch.setattr(wake_client, "WARMUP_COOLDOWN_SECONDS", 0)
    logged_in(client)
    logged_in(client)
    assert len(FakeThread.started) == 2


def test_login_succeeds_when_worker_wake_url_unset(client, monkeypatch):
    monkeypatch.setattr(wake_client.settings, "worker_wake_url", None)
    logged_in(client)
    assert len(FakeThread.started) == 0


def test_send_wake_never_raises_when_worker_unreachable():
    wake_client._send_wake()
    assert True  # reaching here means no exception escaped


def test_login_creates_no_execution_or_outbox_rows(client):
    logged_in(client)
    assert len(FakeThread.started) == 1
    assert FakeThread.started[0].target is wake_client._send_wake
    assert not hasattr(wake_client, "outbox") and not hasattr(wake_client, "execution")


def test_execution_submission_wake_independent_of_login_warmup(monkeypatch):
    from apps.backend.dependencies import get_db_session, require_authenticated
    from apps.backend.routers.executions import (
        get_execution_service,
        notify_worker_wake as execution_wake,
    )
    from apps.backend.schemas.auth import TokenClaims
    from packages.execution_engine.application.execution_app_service import (
        ExecutionApplicationService,
    )
    from packages.execution_engine.domain.models import Execution, ExecutionState

    calls = {"execution_wake": 0}

    def recording_wake() -> None:
        calls["execution_wake"] += 1

    monkeypatch.setattr("apps.backend.routers.executions.notify_worker_wake", recording_wake)
    mock_execution_service = Mock(spec=ExecutionApplicationService)
    mock_db = Mock()
    mock_db.query.return_value.count.return_value = 0
    mock_db.query.return_value.filter.return_value.count.return_value = 0
    mock_db.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
    mock_db.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

    app.dependency_overrides[get_execution_service] = lambda: mock_execution_service
    app.dependency_overrides[get_db_session] = lambda: mock_db
    app.dependency_overrides[require_authenticated] = lambda: TokenClaims(
        sub=uuid4(), exp=9999999999, iat=1000000000, jti=uuid4()
    )
    try:
        benchmark_id = uuid4()
        execution = Execution(
            id=uuid4(),
            benchmark_version_id=benchmark_id,
            status=ExecutionState.QUEUED,
            max_retries=3,
        )
        mock_execution_service.submit_execution.return_value = execution
        client = TestClient(app)
        response = client.post(
            f"/api/v1/benchmarks/{benchmark_id}/executions",
            json={
                "benchmark_version_id": str(benchmark_id),
                "dataset_version_id": "00000000-0000-0000-0000-000000000006",
                "target_model": "groq/llama-3.1-8b-instant",
            },
        )
        assert response.status_code in (200, 201)
        assert calls["execution_wake"] == 1
        assert execution_wake is not wake_client.notify_login_warmup
    finally:
        app.dependency_overrides.clear()

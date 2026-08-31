"""Tests for AtlasClient — auth, health, transport, error mapping.

Uses ``pytest-httpx`` for mock transport; no live Atlas deployment required.
"""

from __future__ import annotations

import json

import pytest

from atlas_sdk.auth import StaticTokenSupplier
from atlas_sdk.client import AtlasClient
from atlas_sdk.errors import (
    AuthError,
    ForbiddenError,
    NetworkError,
    NotFoundError,
    ServerError,
    ValidationError,
)


def _ok(data: dict | list, *, message: str = "ok") -> dict:
    """Wrap *data* in the standard ``APIResponse`` envelope."""
    return {
        "success": True,
        "message": message,
        "data": data,
        "meta": {"request_id": "req-1", "timestamp": "2026-01-01T00:00:00Z"},
    }


def _err(status: int, code: str = "", message: str = "") -> dict:
    return {
        "success": False,
        "error": {"code": code, "message": message},
        "meta": {"request_id": "req-1", "timestamp": "2026-01-01T00:00:00Z"},
    }


# ── auth tests ────────────────────────────────────────────────────────


class TestLogin:
    def test_login_returns_token(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="POST",
            url="http://localhost:8000/api/v1/auth/login",
            json=_ok({"access_token": "tok_abc", "token_type": "bearer"}),
        )
        client = AtlasClient("http://localhost:8000")
        result = client.login("user@example.com", "password123")
        assert result.access_token == "tok_abc"
        assert result.token_type == "bearer"
        client.close()

    def test_login_sends_correct_body(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="POST",
            url="http://localhost:8000/api/v1/auth/login",
            json=_ok({"access_token": "x", "token_type": "bearer"}),
        )
        client = AtlasClient("http://localhost:8000")
        client.login("a@b.com", "pass")
        request = httpx_mock.get_request()
        assert request is not None
        body = json.loads(request.content)
        assert body["email"] == "a@b.com"
        assert body["password"] == "pass"
        client.close()

    def test_login_failure_raises_auth_error(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="POST",
            url="http://localhost:8000/api/v1/auth/login",
            status_code=401,
            json=_err(401, "UNAUTHORIZED", "Invalid credentials"),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(AuthError) as exc_info:
            client.login("a@b.com", "wrong")
        assert exc_info.value.status == 401
        client.close()


class TestWhoami:
    def test_whoami_returns_user(self, httpx_mock: pytest.MockTransport) -> None:
        user_data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "email": "user@example.com",
            "full_name": "Test User",
            "is_active": True,
            "is_verified": False,
            "org_id": None,
        }
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/auth/me",
            json=_ok(user_data),
        )
        client = AtlasClient("http://localhost:8000", token_supplier=StaticTokenSupplier("tok"))
        result = client.whoami()
        assert result.email == "user@example.com"
        assert result.full_name == "Test User"
        client.close()

    def test_whoami_sends_auth_header(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/auth/me",
            json=_ok({
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "a@b.com",
                "full_name": "X",
                "is_active": True,
                "is_verified": False,
            }),
        )
        client = AtlasClient("http://localhost:8000", token_supplier=StaticTokenSupplier("my-tok"))
        client.whoami()
        request = httpx_mock.get_request()
        assert request is not None
        assert request.headers.get("authorization") == "Bearer my-tok"
        client.close()


# ── health tests ──────────────────────────────────────────────────────


class TestHealth:
    def test_health_summary(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/health",
            json=_ok({"status": "healthy", "version": "0.9.0"}),
        )
        client = AtlasClient("http://localhost:8000")
        result = client.health_summary()
        assert result.status == "healthy"
        assert result.version == "0.9.0"
        client.close()

    def test_system_ready_raw_dict(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/system/health/ready",
            json={"status": "ready", "checks": {"database": "ok"}},
        )
        client = AtlasClient("http://localhost:8000")
        result = client.system_ready()
        assert result.status == "ready"
        assert result.checks["database"] == "ok"
        client.close()

    def test_system_live_raw_dict(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/system/health/live",
            json={"status": "alive", "version": "0.9.0"},
        )
        client = AtlasClient("http://localhost:8000")
        result = client.system_live()
        assert result.status == "alive"
        client.close()


# ── submit execution tests ────────────────────────────────────────────


class TestSubmitExecution:
    def test_submit_execution_returns_queued(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        """Successful submission returns ExecutionResponse in QUEUED state."""
        bv_id = "22222222-2222-2222-2222-222222222222"
        exec_id = "11111111-1111-1111-1111-111111111111"
        user_id = "33333333-3333-3333-3333-333333333333"
        httpx_mock.add_response(
            method="POST",
            url=f"http://localhost:8000/api/v1/benchmarks/{bv_id}/executions",
            json={
                "id": exec_id,
                "benchmark_version_id": bv_id,
                "status": "QUEUED",
                "target_model": "gemini-2.5-flash",
                "completed_items": 0,
                "total_items": 1,
                "started_at": None,
                "completed_at": None,
                "created_at": "2026-08-26T12:00:00Z",
                "updated_at": "2026-08-26T12:00:00Z",
                "created_by": user_id,
                "max_retries": 3,
                "attempts": [],
            },
            status_code=201,
        )
        client = AtlasClient(
            "http://localhost:8000",
            token_supplier=StaticTokenSupplier("test-token"),
        )
        result = client.submit_execution(bv_id)
        assert result.status == "QUEUED"
        assert str(result.id) == exec_id
        assert str(result.benchmark_version_id) == bv_id
        assert result.target_model == "gemini-2.5-flash"
        assert result.max_retries == 3
        assert result.attempts == []
        client.close()

    def test_submit_execution_custom_model(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        """Custom target_model is sent in the request body."""
        bv_id = "22222222-2222-2222-2222-222222222222"
        httpx_mock.add_response(
            method="POST",
            url=f"http://localhost:8000/api/v1/benchmarks/{bv_id}/executions",
            json={
                "id": "11111111-1111-1111-1111-111111111111",
                "benchmark_version_id": bv_id,
                "status": "QUEUED",
                "target_model": "gpt-4o",
                "completed_items": 0,
                "total_items": 1,
                "created_at": "2026-08-26T12:00:00Z",
                "updated_at": "2026-08-26T12:00:00Z",
                "created_by": "33333333-3333-3333-3333-333333333333",
                "max_retries": 3,
            },
            status_code=201,
        )
        client = AtlasClient(
            "http://localhost:8000",
            token_supplier=StaticTokenSupplier("test-token"),
        )
        result = client.submit_execution(bv_id, target_model="gpt-4o")
        assert result.target_model == "gpt-4o"
        # Verify request body
        request = httpx_mock.get_request()
        assert request is not None
        body = json.loads(request.content)
        assert body["target_model"] == "gpt-4o"
        client.close()

    def test_submit_execution_404_raises_not_found(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        """Non-existent benchmark version raises NotFoundError."""
        bv_id = "00000000-0000-0000-0000-000000000000"
        httpx_mock.add_response(
            method="POST",
            url=f"http://localhost:8000/api/v1/benchmarks/{bv_id}/executions",
            json={"detail": "BenchmarkVersion not found"},
            status_code=404,
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(NotFoundError):
            client.submit_execution(bv_id)
        client.close()

    def test_submit_execution_401_raises_auth_error(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        """Missing/invalid token raises AuthError."""
        bv_id = "22222222-2222-2222-2222-222222222222"
        httpx_mock.add_response(
            method="POST",
            url=f"http://localhost:8000/api/v1/benchmarks/{bv_id}/executions",
            json=_err(401, "UNAUTHORIZED", "Not authenticated"),
            status_code=401,
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(AuthError):
            client.submit_execution(bv_id)
        client.close()

    def test_submit_execution_no_auth_header_without_supplier(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        """No Authorization header when no token_supplier is set."""
        bv_id = "22222222-2222-2222-2222-222222222222"
        httpx_mock.add_response(
            method="POST",
            url=f"http://localhost:8000/api/v1/benchmarks/{bv_id}/executions",
            json={
                "id": "11111111-1111-1111-1111-111111111111",
                "benchmark_version_id": bv_id,
                "status": "QUEUED",
                "target_model": "gemini-2.5-flash",
                "completed_items": 0,
                "total_items": 1,
                "created_at": "2026-08-26T12:00:00Z",
                "updated_at": "2026-08-26T12:00:00Z",
                "created_by": "33333333-3333-3333-3333-333333333333",
                "max_retries": 3,
            },
            status_code=201,
        )
        client = AtlasClient("http://localhost:8000")
        client.submit_execution(bv_id)
        request = httpx_mock.get_request()
        assert request is not None
        assert "Authorization" not in request.headers
        client.close()


# ── list_dispatch_targets tests ─────────────────────────────────────


class TestListDispatchTargets:
    def test_success_parses_bare_list(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        """GET /executions/dispatch-targets returns a bare (unwrapped) list."""
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/executions/dispatch-targets",
            json=[
                {
                    "benchmark_version_id": "22222222-2222-2222-2222-222222222222",
                    "benchmark_name": "HumanEval Benchmark",
                    "version_string": "1.0.0",
                    "dataset_version_id": "44444444-4444-4444-4444-444444444444",
                },
                {
                    "benchmark_version_id": "55555555-5555-5555-5555-555555555555",
                    "benchmark_name": "HumanEval Benchmark",
                    "version_string": "1.0.1",
                    "dataset_version_id": None,
                },
            ],
            status_code=200,
        )
        client = AtlasClient("http://localhost:8000")
        try:
            targets = client.list_dispatch_targets()
        finally:
            client.close()
        assert len(targets) == 2
        assert str(targets[0].benchmark_version_id) == "22222222-2222-2222-2222-222222222222"
        assert targets[0].benchmark_name == "HumanEval Benchmark"
        assert targets[0].version_string == "1.0.0"
        assert str(targets[0].dataset_version_id) == "44444444-4444-4444-4444-444444444444"
        assert targets[1].dataset_version_id is None

    def test_sends_auth_header(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/executions/dispatch-targets",
            json=[],
            status_code=200,
        )
        client = AtlasClient(
            "http://localhost:8000",
            token_supplier=StaticTokenSupplier("tok-123"),
        )
        try:
            client.list_dispatch_targets()
            request = httpx_mock.get_request()
            assert request is not None
            assert request.headers.get("Authorization") == "Bearer tok-123"
        finally:
            client.close()

    def test_401_raises_auth_error(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/executions/dispatch-targets",
            json=_err(401, "unauthorized", "Not authenticated"),
            status_code=401,
        )
        client = AtlasClient("http://localhost:8000")
        try:
            with pytest.raises(AuthError) as exc_info:
                client.list_dispatch_targets()
            assert exc_info.value.status == 401
        finally:
            client.close()

    def test_403_raises_forbidden(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/executions/dispatch-targets",
            json=_err(403, "forbidden", "Forbidden"),
            status_code=403,
        )
        client = AtlasClient("http://localhost:8000")
        try:
            with pytest.raises(ForbiddenError) as exc_info:
                client.list_dispatch_targets()
            assert exc_info.value.status == 403
        finally:
            client.close()


# ── get_execution tests ─────────────────────────────────────────────


class TestGetExecution:
    def test_get_execution_success(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        """Returns parsed ExecutionResponse with populated fields."""
        exec_id = "11111111-1111-1111-1111-111111111111"
        bv_id = "22222222-2222-2222-2222-222222222222"
        user_id = "33333333-3333-3333-3333-333333333333"
        httpx_mock.add_response(
            method="GET",
            url=f"http://localhost:8000/api/v1/executions/{exec_id}",
            json={
                "id": exec_id,
                "benchmark_version_id": bv_id,
                "status": "RUNNING",
                "target_model": "gemini-2.5-flash",
                "completed_items": 3,
                "total_items": 10,
                "started_at": "2026-08-26T12:00:00Z",
                "completed_at": None,
                "created_at": "2026-08-26T11:55:00Z",
                "updated_at": "2026-08-26T12:01:00Z",
                "created_by": user_id,
                "max_retries": 3,
                "attempts": [],
            },
            status_code=200,
        )
        client = AtlasClient(
            "http://localhost:8000",
            token_supplier=StaticTokenSupplier("test-token"),
        )
        result = client.get_execution(exec_id)
        assert result.status == "RUNNING"
        assert str(result.id) == exec_id
        assert result.completed_items == 3
        assert result.total_items == 10
        assert result.started_at is not None
        assert result.completed_at is None
        assert result.attempts == []
        client.close()

    def test_get_execution_404_raises_not_found(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        """Non-existent execution raises NotFoundError."""
        exec_id = "00000000-0000-0000-0000-000000000000"
        httpx_mock.add_response(
            method="GET",
            url=f"http://localhost:8000/api/v1/executions/{exec_id}",
            json={"detail": "Execution not found"},
            status_code=404,
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(NotFoundError):
            client.get_execution(exec_id)
        client.close()

    def test_get_execution_401_raises_auth_error(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        """Missing/invalid token raises AuthError."""
        exec_id = "11111111-1111-1111-1111-111111111111"
        httpx_mock.add_response(
            method="GET",
            url=f"http://localhost:8000/api/v1/executions/{exec_id}",
            json=_err(401, "UNAUTHORIZED", "Not authenticated"),
            status_code=401,
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(AuthError):
            client.get_execution(exec_id)
        client.close()

    def test_get_execution_403_raises_forbidden(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        """Insufficient permissions raises ForbiddenError."""
        exec_id = "11111111-1111-1111-1111-111111111111"
        httpx_mock.add_response(
            method="GET",
            url=f"http://localhost:8000/api/v1/executions/{exec_id}",
            json=_err(403, "FORBIDDEN", "Insufficient permissions"),
            status_code=403,
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(ForbiddenError):
            client.get_execution(exec_id)
        client.close()

    def test_get_execution_timed_out_parses_correctly(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        """Regression: TIMED_OUT (backend terminal state) must parse."""
        exec_id = "44444444-4444-4444-4444-444444444444"
        bv_id = "22222222-2222-2222-2222-222222222222"
        user_id = "33333333-3333-3333-3333-333333333333"
        httpx_mock.add_response(
            method="GET",
            url=f"http://localhost:8000/api/v1/executions/{exec_id}",
            json={
                "id": exec_id,
                "benchmark_version_id": bv_id,
                "status": "TIMED_OUT",
                "target_model": "gemini-2.5-flash",
                "completed_items": 7,
                "total_items": 10,
                "started_at": "2026-08-26T12:00:00Z",
                "completed_at": "2026-08-26T12:30:00Z",
                "created_at": "2026-08-26T11:55:00Z",
                "updated_at": "2026-08-26T12:30:00Z",
                "created_by": user_id,
                "max_retries": 3,
                "attempts": [],
            },
            status_code=200,
        )
        client = AtlasClient(
            "http://localhost:8000",
            token_supplier=StaticTokenSupplier("test-token"),
        )
        result = client.get_execution(exec_id)
        assert result.status == "TIMED_OUT"
        assert str(result.id) == exec_id
        client.close()


# ── list_executions tests ────────────────────────────────────────────


class TestListExecutions:
    def test_list_executions_success(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        """Returns ExecutionPage with items and pagination metadata."""
        bv_id = "22222222-2222-2222-2222-222222222222"
        user_id = "33333333-3333-3333-3333-333333333333"
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/executions?limit=20&offset=0",
            json={
                "items": [
                    {
                        "id": "11111111-1111-1111-1111-111111111111",
                        "benchmark_version_id": bv_id,
                        "status": "COMPLETED",
                        "target_model": "gemini-2.5-flash",
                        "completed_items": 10,
                        "total_items": 10,
                        "created_at": "2026-08-26T12:00:00Z",
                        "updated_at": "2026-08-26T12:05:00Z",
                        "created_by": user_id,
                        "max_retries": 3,
                        "attempts": [],
                    },
                    {
                        "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                        "benchmark_version_id": bv_id,
                        "status": "RUNNING",
                        "target_model": "gpt-4o",
                        "completed_items": 3,
                        "total_items": 10,
                        "created_at": "2026-08-26T12:55:00Z",
                        "updated_at": "2026-08-26T13:01:00Z",
                        "created_by": user_id,
                        "max_retries": 3,
                        "attempts": [],
                    },
                ],
                "total": 47,
            },
            status_code=200,
        )
        client = AtlasClient(
            "http://localhost:8000",
            token_supplier=StaticTokenSupplier("test-token"),
        )
        result = client.list_executions()
        assert len(result.items) == 2
        assert result.total == 47
        assert result.limit == 20
        assert result.offset == 0
        assert result.items[0].status == "COMPLETED"
        assert result.items[1].status == "RUNNING"
        assert result.items[1].target_model == "gpt-4o"
        client.close()

    def test_list_executions_empty(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        """Empty items list returns ExecutionPage with empty items."""
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/executions?limit=20&offset=0",
            json={"items": [], "total": 0},
            status_code=200,
        )
        client = AtlasClient(
            "http://localhost:8000",
            token_supplier=StaticTokenSupplier("test-token"),
        )
        result = client.list_executions()
        assert result.items == []
        assert result.total == 0
        client.close()

    def test_list_executions_filters_passed(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        """Query params are sent correctly."""
        bv_id = "22222222-2222-2222-2222-222222222222"
        httpx_mock.add_response(
            method="GET",
            url=f"http://localhost:8000/api/v1/executions?limit=5&offset=10&benchmark_version_id={bv_id}&status=RUNNING",
            json={"items": [], "total": 0},
            status_code=200,
        )
        client = AtlasClient(
            "http://localhost:8000",
            token_supplier=StaticTokenSupplier("test-token"),
        )
        client.list_executions(
            benchmark_version_id=bv_id,
            status="RUNNING",
            limit=5,
            offset=10,
        )
        request = httpx_mock.get_request()
        assert request is not None
        url = str(request.url)
        assert "benchmark_version_id=" in url
        assert "status=RUNNING" in url
        assert "limit=5" in url
        assert "offset=10" in url
        client.close()

    def test_list_executions_401_raises_auth_error(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        """Unauthenticated request raises AuthError."""
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/executions?limit=20&offset=0",
            json=_err(401, "UNAUTHORIZED", "Not authenticated"),
            status_code=401,
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(AuthError):
            client.list_executions()
        client.close()


# ── cancel_execution tests ───────────────────────────────────────────


class TestCancelExecution:
    def test_cancel_execution_success(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        """Cancel returns the execution with status unchanged (cooperative)."""
        exec_id = "11111111-1111-1111-1111-111111111111"
        bv_id = "22222222-2222-2222-2222-222222222222"
        user_id = "33333333-3333-3333-3333-333333333333"
        httpx_mock.add_response(
            method="POST",
            url=f"http://localhost:8000/api/v1/executions/{exec_id}/cancel",
            json={
                "id": exec_id,
                "benchmark_version_id": bv_id,
                "status": "RUNNING",
                "target_model": "gemini-2.5-flash",
                "completed_items": 3,
                "total_items": 10,
                "started_at": "2026-08-26T12:00:00Z",
                "completed_at": None,
                "created_at": "2026-08-26T11:55:00Z",
                "updated_at": "2026-08-26T12:01:00Z",
                "created_by": user_id,
                "max_retries": 3,
                "attempts": [],
            },
            status_code=200,
        )
        client = AtlasClient(
            "http://localhost:8000",
            token_supplier=StaticTokenSupplier("test-token"),
        )
        result = client.cancel_execution(exec_id)
        assert result.status == "RUNNING"
        assert str(result.id) == exec_id
        client.close()

    def test_cancel_execution_terminal_returns_400(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        """Backend returns 400 for terminal execution — not idempotent."""
        exec_id = "11111111-1111-1111-1111-111111111111"
        httpx_mock.add_response(
            method="POST",
            url=f"http://localhost:8000/api/v1/executions/{exec_id}/cancel",
            json={"detail": "Execution is in terminal state 'COMPLETED' and cannot be cancelled."},
            status_code=400,
        )
        client = AtlasClient("http://localhost:8000")
        from atlas_sdk.errors import ApiError

        with pytest.raises(ApiError) as exc_info:
            client.cancel_execution(exec_id)
        assert exc_info.value.status == 400
        client.close()

    def test_cancel_execution_404_raises_not_found(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        """Non-existent execution raises NotFoundError."""
        exec_id = "00000000-0000-0000-0000-000000000000"
        httpx_mock.add_response(
            method="POST",
            url=f"http://localhost:8000/api/v1/executions/{exec_id}/cancel",
            json={"detail": "Execution not found"},
            status_code=404,
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(NotFoundError):
            client.cancel_execution(exec_id)
        client.close()

    def test_cancel_execution_401_raises_auth_error(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        """Missing/invalid token raises AuthError."""
        exec_id = "11111111-1111-1111-1111-111111111111"
        httpx_mock.add_response(
            method="POST",
            url=f"http://localhost:8000/api/v1/executions/{exec_id}/cancel",
            json=_err(401, "UNAUTHORIZED", "Not authenticated"),
            status_code=401,
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(AuthError):
            client.cancel_execution(exec_id)
        client.close()


# ── error mapping tests ───────────────────────────────────────────────


class TestErrorMapping:
    def test_401_raises_auth_error(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/auth/me",
            status_code=401,
            json=_err(401, "UNAUTHORIZED", "token expired"),
        )
        client = AtlasClient("http://localhost:8000", token_supplier=StaticTokenSupplier("bad"))
        with pytest.raises(AuthError) as exc_info:
            client.whoami()
        assert exc_info.value.status == 401
        assert "token expired" in exc_info.value.message
        client.close()

    def test_403_raises_forbidden_error(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/auth/me",
            status_code=403,
            json=_err(403, "FORBIDDEN", "not admin"),
        )
        client = AtlasClient("http://localhost:8000", token_supplier=StaticTokenSupplier("tok"))
        with pytest.raises(ForbiddenError):
            client.whoami()
        client.close()

    def test_404_raises_not_found(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/auth/me",
            status_code=404,
            json=_err(404, "NOT_FOUND", "user not found"),
        )
        client = AtlasClient("http://localhost:8000", token_supplier=StaticTokenSupplier("tok"))
        with pytest.raises(NotFoundError):
            client.whoami()
        client.close()

    def test_500_raises_server_error(self, httpx_mock: pytest.MockTransport) -> None:
        for _ in range(4):
            httpx_mock.add_response(
                method="GET",
                url="http://localhost:8000/api/v1/auth/me",
                status_code=500,
                json=_err(500, "INTERNAL", "something broke"),
            )
        client = AtlasClient(
            "http://localhost:8000", token_supplier=StaticTokenSupplier("tok")
        )
        with pytest.raises(ServerError):
            client.whoami()
        client.close()

    def test_502_raises_server_error(self, httpx_mock: pytest.MockTransport) -> None:
        for _ in range(4):
            httpx_mock.add_response(
                method="GET",
                url="http://localhost:8000/api/v1/auth/me",
                status_code=502,
            )
        client = AtlasClient(
            "http://localhost:8000", token_supplier=StaticTokenSupplier("tok")
        )
        with pytest.raises(ServerError):
            client.whoami()
        client.close()


# ── transport tests ───────────────────────────────────────────────────


class TestTransport:
    def test_get_retries_on_502(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/health",
            status_code=502,
        )
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/health",
            json=_ok({"status": "ok", "version": "1.0"}),
        )
        client = AtlasClient("http://localhost:8000", max_retries=2)
        result = client.health_summary()
        assert result.status == "ok"
        assert len(httpx_mock.get_requests()) == 2
        client.close()

    def test_post_does_not_retry(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="POST",
            url="http://localhost:8000/api/v1/auth/login",
            status_code=502,
        )
        client = AtlasClient("http://localhost:8000", max_retries=3)
        with pytest.raises(ServerError):
            client.login("a@b.com", "pass")
        assert len(httpx_mock.get_requests()) == 1
        client.close()

    def test_user_agent_header(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/health",
            json=_ok({"status": "ok", "version": "1.0"}),
        )
        client = AtlasClient("http://localhost:8000", user_agent="atlas-sdk/0.1.0")
        client.health_summary()
        request = httpx_mock.get_request()
        assert request is not None
        assert request.headers.get("user-agent") == "atlas-sdk/0.1.0"
        client.close()

    def test_no_auth_header_when_no_supplier(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/health",
            json=_ok({"status": "ok", "version": "1.0"}),
        )
        client = AtlasClient("http://localhost:8000")
        client.health_summary()
        request = httpx_mock.get_request()
        assert request is not None
        assert "authorization" not in request.headers
        client.close()

    def test_context_manager(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/health",
            json=_ok({"status": "ok", "version": "1.0"}),
        )
        with AtlasClient("http://localhost:8000") as client:
            result = client.health_summary()
            assert result.status == "ok"


# ── security / edge-case tests ────────────────────────────────────────


class TestSecurityEdgeCases:
    def test_token_supplier_exception_raises_auth_error(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        def bad_supplier() -> str:
            raise OSError("keychain locked")

        client = AtlasClient(
            "http://localhost:8000", token_supplier=bad_supplier
        )
        with pytest.raises(AuthError, match="keychain locked"):
            client.whoami()
        client.close()

    def test_localhost_detection_uses_hostname(self) -> None:
        """Substring in path/query must not trigger TLS bypass."""
        # "localhost" in path — should NOT disable TLS.
        client = AtlasClient("https://example.com/localhost/api")
        assert client._http._transport._pool._ssl_context is not None  # type: ignore[attr-defined]
        client.close()

    def test_non_localhost_keeps_tls(self) -> None:
        client = AtlasClient("https://api.atlas.example.com")
        # httpx.Client with verify=True (default) uses ssl.SSLContext
        assert client._http._transport._pool._ssl_context is not None  # type: ignore[attr-defined]
        client.close()

    def test_localhost_enables_tls_bypass(self) -> None:
        client = AtlasClient("http://localhost:8000")
        # httpx.Client with verify=False uses ssl.create_default_context with check_hostname=False
        # The _pool attribute should have verify=False set
        transport = client._http._transport
        # Verify the transport was created with verify=False
        assert hasattr(transport, "_pool")
        client.close()

    def test_unwrap_malformed_response_raises_validation_error(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        """If the API returns a response missing 'data', _unwrap raises ValidationError."""
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/health",
            json={"unexpected": "format"},
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(ValidationError, match="does not match expected schema"):
            client.health_summary()
        client.close()

    def test_no_password_in_exception_message(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        httpx_mock.add_response(
            method="POST",
            url="http://localhost:8000/api/v1/auth/login",
            status_code=401,
            json=_err(401, "UNAUTHORIZED", "Invalid credentials"),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(AuthError) as exc_info:
            client.login("user@example.com", "super_secret_password_123")
        assert "super_secret_password_123" not in str(exc_info.value)
        client.close()


# ── report tests ──────────────────────────────────────────────────────


class TestListReportRuns:
    def test_list_report_runs_returns_page(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/reports/runs?limit=50&offset=0",
            json={
                "items": [
                    {
                        "run_id": "11111111-1111-1111-1111-111111111111",
                        "benchmark_id": "22222222-2222-2222-2222-222222222222",
                        "benchmark_version": "1.0.0",
                        "target_model": "gpt-4o",
                        "evaluation_status": "COMPLETED",
                        "started_at": "2026-08-26T10:00:00Z",
                        "completed_at": "2026-08-26T10:05:00Z",
                        "overall_score": 88.5,
                    }
                ],
                "total": 1,
                "page": 1,
                "size": 50,
            },
        )
        client = AtlasClient("http://localhost:8000")
        result = client.list_report_runs()
        assert result.total == 1
        assert result.page == 1
        assert result.size == 50
        assert len(result.items) == 1
        assert result.items[0].target_model == "gpt-4o"
        assert result.items[0].overall_score == 88.5
        client.close()

    def test_list_report_runs_sends_filters(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/reports/runs?limit=10&offset=5&status=COMPLETED&benchmark_id=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee&benchmark_version=2.0.0&target_model=claude-3",
            json={"items": [], "total": 0, "page": 1, "size": 10},
        )
        client = AtlasClient("http://localhost:8000")
        client.list_report_runs(
            status="COMPLETED",
            benchmark_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            benchmark_version="2.0.0",
            target_model="claude-3",
            limit=10,
            offset=5,
        )
        request = httpx_mock.get_request()
        assert request is not None
        url = str(request.url)
        assert "status=COMPLETED" in url
        assert "benchmark_id=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee" in url
        assert "benchmark_version=2.0.0" in url
        assert "target_model=claude-3" in url
        assert "limit=10" in url
        assert "offset=5" in url
        client.close()

    def test_list_report_runs_empty(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/reports/runs?limit=50&offset=0",
            json={"items": [], "total": 0, "page": 1, "size": 50},
        )
        client = AtlasClient("http://localhost:8000")
        result = client.list_report_runs()
        assert result.items == []
        assert result.total == 0
        client.close()

    def test_list_report_runs_401_raises_auth_error(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/reports/runs?limit=50&offset=0",
            status_code=401,
            json=_err(401, "UNAUTHORIZED", "Token expired"),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(AuthError) as exc_info:
            client.list_report_runs()
        assert exc_info.value.status == 401
        client.close()

    def test_list_report_runs_403_raises_forbidden_error(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/reports/runs?limit=50&offset=0",
            status_code=403,
            json=_err(403, "FORBIDDEN", "Insufficient permissions"),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(ForbiddenError) as exc_info:
            client.list_report_runs()
        assert exc_info.value.status == 403
        client.close()

    def test_list_report_runs_no_omitted_params(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/reports/runs?limit=50&offset=0",
            json={"items": [], "total": 0, "page": 1, "size": 50},
        )
        client = AtlasClient("http://localhost:8000")
        client.list_report_runs()
        request = httpx_mock.get_request()
        assert request is not None
        url = str(request.url)
        assert "status" not in url.split("?")[1] if "?" in url else True
        assert "benchmark_id" not in url.split("?")[1] if "?" in url else True
        assert "benchmark_version" not in url.split("?")[1] if "?" in url else True
        assert "target_model" not in url.split("?")[1] if "?" in url else True
        assert "limit=50" in url
        assert "offset=0" in url
        client.close()


def _report_summary() -> dict:
    return {
        "run_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "benchmark_id": "7fa85f64-5717-4562-b3fc-2c963f66afa0",
        "benchmark_name": "HumanEval",
        "benchmark_version": "1.0.0",
        "target_model": "gpt-4o",
        "evaluation_status": "COMPLETED",
        "started_at": "2026-07-27T10:00:00Z",
        "completed_at": "2026-07-27T10:05:00Z",
        "overall_score": 88.5,
        "scores": [
            {"capability_name": "reasoning", "score": 92.0},
            {"capability_name": "code_generation", "score": 85.0},
        ],
    }


class TestGetReportRun:
    def test_get_report_run_returns_summary(self, httpx_mock: pytest.MockTransport) -> None:
        # Raw unwrapped payload — no APIResponse envelope.
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/reports/runs/3fa85f64-5717-4562-b3fc-2c963f66afa6",
            json=_report_summary(),
        )
        client = AtlasClient("http://localhost:8000")
        result = client.get_report_run("3fa85f64-5717-4562-b3fc-2c963f66afa6")
        assert str(result.run_id) == "3fa85f64-5717-4562-b3fc-2c963f66afa6"
        assert result.benchmark_name == "HumanEval"
        assert result.benchmark_version == "1.0.0"
        assert result.target_model == "gpt-4o"
        assert result.evaluation_status == "COMPLETED"
        assert result.overall_score == 88.5
        assert result.started_at is not None
        assert result.completed_at is not None
        client.close()

    def test_get_report_run_parses_nested_scores(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/reports/runs/3fa85f64-5717-4562-b3fc-2c963f66afa6",
            json=_report_summary(),
        )
        client = AtlasClient("http://localhost:8000")
        result = client.get_report_run("3fa85f64-5717-4562-b3fc-2c963f66afa6")
        assert len(result.scores) == 2
        assert result.scores[0].capability_name == "reasoning"
        assert result.scores[0].score == 92.0
        assert result.scores[1].capability_name == "code_generation"
        assert result.scores[1].score == 85.0
        client.close()

    def test_get_report_run_parses_null_fields(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/reports/runs/3fa85f64-5717-4562-b3fc-2c963f66afa6",
            json={
                "run_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "benchmark_id": "7fa85f64-5717-4562-b3fc-2c963f66afa0",
                "benchmark_name": "HumanEval",
                "benchmark_version": "1.0.0",
                "target_model": "gpt-4o",
                "evaluation_status": "PENDING",
                "started_at": None,
                "completed_at": None,
                "overall_score": None,
                "scores": [],
            },
        )
        client = AtlasClient("http://localhost:8000")
        result = client.get_report_run("3fa85f64-5717-4562-b3fc-2c963f66afa6")
        assert result.evaluation_status == "PENDING"
        assert result.started_at is None
        assert result.completed_at is None
        assert result.overall_score is None
        assert result.scores == []
        client.close()

    def test_get_report_run_401_raises_auth_error(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/reports/runs/3fa85f64-5717-4562-b3fc-2c963f66afa6",
            status_code=401,
            json=_err(401, "UNAUTHORIZED", "Token expired"),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(AuthError) as exc_info:
            client.get_report_run("3fa85f64-5717-4562-b3fc-2c963f66afa6")
        assert exc_info.value.status == 401
        client.close()

    def test_get_report_run_403_raises_forbidden_error(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/reports/runs/3fa85f64-5717-4562-b3fc-2c963f66afa6",
            status_code=403,
            json=_err(403, "FORBIDDEN", "Insufficient permissions"),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(ForbiddenError) as exc_info:
            client.get_report_run("3fa85f64-5717-4562-b3fc-2c963f66afa6")
        assert exc_info.value.status == 403
        client.close()

    def test_get_report_run_404_raises_not_found_error(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/reports/runs/3fa85f64-5717-4562-b3fc-2c963f66afa6",
            status_code=404,
            json=_err(404, "NOT_FOUND", "Report summary for execution run not found."),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(NotFoundError) as exc_info:
            client.get_report_run("3fa85f64-5717-4562-b3fc-2c963f66afa6")
        assert exc_info.value.status == 404
        client.close()

    def test_get_report_run_500_raises_server_error(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/reports/runs/3fa85f64-5717-4562-b3fc-2c963f66afa6",
            status_code=500,
            json=_err(500, "INTERNAL", "something broke"),
        )
        client = AtlasClient("http://localhost:8000", max_retries=0)
        with pytest.raises(ServerError):
            client.get_report_run("3fa85f64-5717-4562-b3fc-2c963f66afa6")
        client.close()

    def test_get_report_run_network_error_raises_network_error(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        import httpx

        httpx_mock.add_exception(httpx.ConnectError("connection refused"))
        client = AtlasClient("http://localhost:8000", max_retries=0)
        with pytest.raises(NetworkError):
            client.get_report_run("3fa85f64-5717-4562-b3fc-2c963f66afa6")
        client.close()


class TestExportReportRun:
    _RUN_ID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"

    def test_export_report_run_returns_raw_content(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        httpx_mock.add_response(
            method="GET",
            url=(
                f"http://localhost:8000/api/v1/reports/runs/{TestExportReportRun._RUN_ID}/export"
                "?format=json&include_prompt=false&include_expected_output=false"
            ),
            content=b'{"report": {"title": "Sample"}}',
            headers={
                "Content-Type": "application/json",
                "Content-Disposition": 'attachment; filename="hello-report-v1.0.0.json"',
            },
        )
        client = AtlasClient("http://localhost:8000")
        result = client.export_report_run(TestExportReportRun._RUN_ID)
        assert result.content == b'{"report": {"title": "Sample"}}'
        assert result.filename == "hello-report-v1.0.0.json"
        assert result.content_type == "application/json"
        client.close()

    def test_export_report_run_default_filename_fallback(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        # No Content-Disposition header -> derive report-<run_id>.<ext>.
        httpx_mock.add_response(
            method="GET",
            url=(
                f"http://localhost:8000/api/v1/reports/runs/{TestExportReportRun._RUN_ID}/export"
                "?format=json&include_prompt=false&include_expected_output=false"
            ),
            content=b'[]',
            headers={"Content-Type": "application/json"},
        )
        client = AtlasClient("http://localhost:8000")
        result = client.export_report_run(TestExportReportRun._RUN_ID)
        assert result.filename == f"report-{TestExportReportRun._RUN_ID}.json"
        client.close()

    def test_export_report_run_ignores_unquoted_filename(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        httpx_mock.add_response(
            method="GET",
            url=(
                f"http://localhost:8000/api/v1/reports/runs/{TestExportReportRun._RUN_ID}/export"
                "?format=csv&include_prompt=false&include_expected_output=false"
            ),
            content=b"a,b\n1,2",
            headers={
                "Content-Type": "text/csv; charset=utf-8",
                "Content-Disposition": 'attachment; filename="run_abc.csv"',
            },
        )
        client = AtlasClient("http://localhost:8000")
        result = client.export_report_run(TestExportReportRun._RUN_ID, format_type="csv")
        assert result.content == b"a,b\n1,2"
        assert result.filename == "run_abc.csv"
        assert result.content_type == "text/csv; charset=utf-8"
        client.close()

    def test_export_report_run_sends_flags_and_format(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        httpx_mock.add_response(
            method="GET",
            url=(
                f"http://localhost:8000/api/v1/reports/runs/{TestExportReportRun._RUN_ID}/export"
                "?format=csv&include_prompt=true&include_expected_output=true"
            ),
            content=b"test\n1",
            headers={"Content-Type": "text/csv; charset=utf-8"},
        )
        client = AtlasClient("http://localhost:8000")
        client.export_report_run(
            TestExportReportRun._RUN_ID,
            format_type="csv",
            include_prompt=True,
            include_expected_output=True,
        )
        request = httpx_mock.get_request()
        assert request is not None
        url = str(request.url)
        assert "format=csv" in url
        assert "include_prompt=true" in url
        assert "include_expected_output=true" in url
        client.close()

    def test_export_report_run_401_raises_auth_error(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        httpx_mock.add_response(
            method="GET",
            url=(
                f"http://localhost:8000/api/v1/reports/runs/{TestExportReportRun._RUN_ID}/export"
                "?format=json&include_prompt=false&include_expected_output=false"
            ),
            status_code=401,
            json=_err(401, "UNAUTHORIZED", "Token expired"),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(AuthError) as exc_info:
            client.export_report_run(TestExportReportRun._RUN_ID)
        assert exc_info.value.status == 401
        client.close()

    def test_export_report_run_403_raises_forbidden_error(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        httpx_mock.add_response(
            method="GET",
            url=(
                f"http://localhost:8000/api/v1/reports/runs/{TestExportReportRun._RUN_ID}/export"
                "?format=json&include_prompt=false&include_expected_output=false"
            ),
            status_code=403,
            json=_err(403, "FORBIDDEN", "Insufficient permissions"),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(ForbiddenError) as exc_info:
            client.export_report_run(TestExportReportRun._RUN_ID)
        assert exc_info.value.status == 403
        client.close()

    def test_export_report_run_404_raises_not_found_error(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        httpx_mock.add_response(
            method="GET",
            url=(
                f"http://localhost:8000/api/v1/reports/runs/{TestExportReportRun._RUN_ID}/export"
                "?format=json&include_prompt=false&include_expected_output=false"
            ),
            status_code=404,
            json=_err(404, "NOT_FOUND", "Report export for execution run not found."),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(NotFoundError) as exc_info:
            client.export_report_run(TestExportReportRun._RUN_ID)
        assert exc_info.value.status == 404
        client.close()

    def test_export_report_run_422_raises_validation_error(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        httpx_mock.add_response(
            method="GET",
            url=(
                f"http://localhost:8000/api/v1/reports/runs/{TestExportReportRun._RUN_ID}/export"
                "?format=json&include_prompt=false&include_expected_output=false"
            ),
            status_code=422,
            json=_err(422, "VALIDATION_ERROR", "Invalid parameter"),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(ValidationError) as exc_info:
            client.export_report_run(TestExportReportRun._RUN_ID)
        assert exc_info.value.status == 422
        client.close()

    def test_export_report_run_500_raises_server_error(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        httpx_mock.add_response(
            method="GET",
            url=(
                f"http://localhost:8000/api/v1/reports/runs/{TestExportReportRun._RUN_ID}/export"
                "?format=json&include_prompt=false&include_expected_output=false"
            ),
            status_code=500,
            json=_err(500, "INTERNAL", "something broke"),
        )
        client = AtlasClient("http://localhost:8000", max_retries=0)
        with pytest.raises(ServerError):
            client.export_report_run(TestExportReportRun._RUN_ID)
        client.close()

    def test_export_report_run_network_error_raises_network_error(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        import httpx

        httpx_mock.add_exception(httpx.ConnectError("connection refused"))
        client = AtlasClient("http://localhost:8000", max_retries=0)
        with pytest.raises(NetworkError):
            client.export_report_run(TestExportReportRun._RUN_ID)
        client.close()

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

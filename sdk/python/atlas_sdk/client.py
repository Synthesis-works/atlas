"""AtlasClient — the single SDK entry point.

Provides a thin HTTP client whose methods return typed DTOs and raise
typed errors.  Contains **zero** Atlas business logic.

Dependency chain:  cli → atlas-sdk (this module) → httpx → /api/v1
"""

from __future__ import annotations

import logging
import time
from typing import Any, TypeVar
from urllib.parse import urlparse

import httpx

from atlas_sdk.auth import TokenSupplier
from atlas_sdk.errors import (
    AuthError,
    NetworkError,
    ValidationError,
    error_for_status,
)
from atlas_sdk.models.auth import AuthUserRead, TokenResponse
from atlas_sdk.models.benchmarks import (
    BenchmarkRead,
    BenchmarkVersionRead,
    PageResponse,
)
from atlas_sdk.models.executions import ExecutionResponse
from atlas_sdk.models.health import HealthData, LivenessResponse, ReadinessResponse
from atlas_sdk.models.responses import APIResponse

logger = logging.getLogger(__name__)

T = TypeVar("T")

_DEFAULT_CONNECT_TIMEOUT = 10.0
_DEFAULT_TOTAL_TIMEOUT = 60.0
_MAX_RETRIES = 3
_RETRY_BACKOFF_BASE = 0.5  # seconds; multiplied by 2^attempt
_RETRYABLE_STATUSES = {429, 502, 503, 504}
_USER_AGENT = "atlas-sdk/0.1.0"


def _is_retryable(status: int) -> bool:
    return status in _RETRYABLE_STATUSES or status >= 500


class AtlasClient:
    """Thin HTTP client for the Atlas ``/api/v1`` control plane.

    Parameters:
        base_url: Root URL of the Atlas API (e.g. ``http://localhost:8000``).
        token_supplier: Callable returning a bearer token.  The CLI owns
            credential storage; the SDK only calls this to attach the header.
        timeout: Total request timeout in seconds.
        connect_timeout: TCP connect timeout in seconds.
        max_retries: Maximum retry attempts for idempotent GET/HEAD requests.
        user_agent: User-Agent header value.
    """

    def __init__(
        self,
        base_url: str,
        *,
        token_supplier: TokenSupplier | None = None,
        timeout: float = _DEFAULT_TOTAL_TIMEOUT,
        connect_timeout: float = _DEFAULT_CONNECT_TIMEOUT,
        max_retries: int = _MAX_RETRIES,
        user_agent: str = _USER_AGENT,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token_supplier = token_supplier
        self._max_retries = max_retries
        self._user_agent = user_agent

        # Determine if localhost (for TLS exception) — hostname-level check only.
        parsed = urlparse(self._base_url)
        is_localhost = parsed.hostname in ("localhost", "127.0.0.1", "::1", "0.0.0.0")

        transport_kwargs: dict[str, Any] = {}
        if is_localhost:
            logger.warning(
                "TLS verification disabled for localhost target: %s",
                self._base_url,
            )
            transport_kwargs["verify"] = False  # noqa: S501 — deliberate localhost exception

        self._http = httpx.Client(
            base_url=self._base_url,
            timeout=httpx.Timeout(timeout, connect=connect_timeout),
            headers={"User-Agent": self._user_agent},
            **transport_kwargs,
        )

    # ── internal helpers ──────────────────────────────────────────────

    def _auth_headers(self) -> dict[str, str]:
        if self._token_supplier is not None:
            try:
                token = self._token_supplier()
            except Exception as exc:
                raise AuthError(
                    status=0,
                    message=f"Token supplier failed: {exc}",
                ) from exc
            return {"Authorization": f"Bearer {token}"}
        return {}

    def _build_url(self, path: str) -> str:
        # path is e.g. "/api/v1/auth/me" — already absolute.
        return path

    def _do_request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
        retry: bool = False,
    ) -> httpx.Response:
        """Execute an HTTP request with retry logic for idempotent methods.

        Retries apply only when *retry* is True (GET/HEAD) and the failure
        is transient (network error, 429, 5xx).
        """
        url = self._build_url(path)
        headers = self._auth_headers()
        attempts = 0
        last_exc: BaseException | None = None

        while True:
            try:
                response = self._http.request(
                    method,
                    url,
                    json=json,
                    params=params,
                    headers=headers,
                )
                # Retry on transient server errors (GET only).
                if retry and _is_retryable(response.status_code) and attempts < self._max_retries:
                    delay = _RETRY_BACKOFF_BASE * (2**attempts)
                    logger.debug(
                        "Retrying %s %s in %.1fs (status %d, attempt %d/%d)",
                        method,
                        path,
                        delay,
                        response.status_code,
                        attempts + 1,
                        self._max_retries,
                    )
                    time.sleep(delay)
                    attempts += 1
                    continue
                return response
            except httpx.TransportError as exc:
                last_exc = exc
                if retry and attempts < self._max_retries:
                    delay = _RETRY_BACKOFF_BASE * (2**attempts)
                    logger.debug(
                        "Retrying %s %s in %.1fs after transport error (attempt %d/%d): %s",
                        method,
                        path,
                        delay,
                        attempts + 1,
                        self._max_retries,
                        exc,
                    )
                    time.sleep(delay)
                    attempts += 1
                    continue
                raise NetworkError(
                    message=f"Request failed: {exc}",
                    wrapped=exc,
                ) from exc

        # Unreachable but keeps mypy happy.
        raise NetworkError(message="Request failed", wrapped=last_exc)  # pragma: no cover

    def _raise_for_status(self, response: httpx.Response) -> None:
        """Raise a typed ``ApiError`` for non-2xx responses."""
        if response.status_code < 400:
            return

        # Try to parse the standard error envelope.
        code = ""
        message = ""
        details: Any = None
        try:
            body = response.json()
            if isinstance(body, dict) and "error" in body:
                err = body["error"]
                code = err.get("code", "")
                message = err.get("message", "")
                details = err.get("details")
            elif isinstance(body, dict):
                message = body.get("detail", "")
        except Exception:
            message = response.text[:500]

        raise error_for_status(
            response.status_code,
            code=code,
            message=message,
            details=details,
        )

    def _unwrap(self, response: httpx.Response, model: type[T]) -> T:
        """Parse and unwrap ``APIResponse[T]`` envelope, returning ``T``."""
        self._raise_for_status(response)
        try:
            envelope: APIResponse[T] = APIResponse[model].model_validate(response.json())  # type: ignore[valid-type]
        except Exception as exc:
            raise ValidationError(
                status=response.status_code,
                message=f"Response does not match expected schema: {exc}",
            ) from exc
        return envelope.data

    def _get(self, path: str, *, params: dict[str, Any] | None = None) -> httpx.Response:
        return self._do_request("GET", path, params=params, retry=True)

    def _post(
        self,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        return self._do_request("POST", path, json=json, params=params, retry=False)

    def _post_raw(
        self,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """POST with error handling but no response unwrapping.

        Use for endpoints that do NOT wrap their response in ``APIResponse``
        (e.g. execution submit/get/cancel).
        """
        response = self._post(path, json=json, params=params)
        self._raise_for_status(response)
        return response

    def _get_raw(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """GET with error handling but no response unwrapping.

        Use for endpoints that do NOT wrap their response in ``APIResponse``
        (e.g. execution endpoints).
        """
        response = self._get(path, params=params)
        self._raise_for_status(response)
        return response

    # ── public API (Phase 1 subset) ──────────────────────────────────

    # -- auth --

    def login(self, email: str, password: str) -> TokenResponse:
        """Authenticate and return tokens.

        ``POST /api/v1/auth/login``
        """
        response = self._post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        return self._unwrap(response, TokenResponse)

    def whoami(self) -> AuthUserRead:
        """Return the current user profile.

        ``GET /api/v1/auth/me``
        """
        response = self._get("/api/v1/auth/me")
        return self._unwrap(response, AuthUserRead)

    # -- health --

    def health_summary(self) -> HealthData:
        """Basic liveness check.

        ``GET /health``
        """
        response = self._get("/health")
        return self._unwrap(response, HealthData)

    def system_ready(self) -> ReadinessResponse:
        """Readiness probe (checks DB connectivity).

        ``GET /api/v1/system/health/ready``

        Note: this endpoint returns a raw dict without the ``APIResponse``
        envelope — unlike most other endpoints.
        """
        response = self._get("/api/v1/system/health/ready")
        self._raise_for_status(response)
        return ReadinessResponse.model_validate(response.json())

    def system_live(self) -> LivenessResponse:
        """Liveness probe.

        ``GET /api/v1/system/health/live``

        Note: this endpoint returns a raw dict without the ``APIResponse``
        envelope.
        """
        response = self._get("/api/v1/system/health/live")
        self._raise_for_status(response)
        return LivenessResponse.model_validate(response.json())

    # -- benchmarks --

    def list_benchmarks(
        self,
        *,
        limit: int = 50,
        offset: int | None = None,
    ) -> PageResponse[BenchmarkRead]:
        """List benchmarks.

        ``GET /api/v1/benchmarks``

        Returns published benchmarks with pagination metadata.
        """
        params: dict[str, Any] = {"limit": limit}
        if offset is not None:
            params["offset"] = offset
        response = self._get("/api/v1/benchmarks", params=params)
        return self._unwrap(response, PageResponse[BenchmarkRead])

    def get_benchmark(self, benchmark_id: str) -> BenchmarkRead:
        """Fetch a single benchmark by ID.

        ``GET /api/v1/benchmarks/{benchmark_id}``
        """
        response = self._get(f"/api/v1/benchmarks/{benchmark_id}")
        return self._unwrap(response, BenchmarkRead)

    def list_benchmark_versions(
        self, benchmark_id: str
    ) -> list[BenchmarkVersionRead]:
        """List versions for a benchmark.

        ``GET /api/v1/benchmarks/{benchmark_id}/versions``

        Returns all versions (not paginated).
        """
        response = self._get(
            f"/api/v1/benchmarks/{benchmark_id}/versions"
        )
        return self._unwrap(response, list[BenchmarkVersionRead])

    # -- executions --

    def submit_execution(
        self,
        benchmark_version_id: str,
        *,
        target_model: str = "gemini-2.5-flash",
        dataset_version_id: str | None = None,
    ) -> ExecutionResponse:
        """Submit a new execution for a benchmark version.

        ``POST /api/v1/benchmarks/{benchmark_version_id}/executions``

        Returns the created execution in QUEUED state.

        Note: this endpoint returns ``ExecutionResponse`` directly (not
        wrapped in ``APIResponse``), unlike most other Atlas endpoints.
        """
        body: dict[str, Any] = {"target_model": target_model}
        if dataset_version_id is not None:
            body["dataset_version_id"] = dataset_version_id
        response = self._post_raw(
            f"/api/v1/benchmarks/{benchmark_version_id}/executions",
            json=body,
        )
        return ExecutionResponse.model_validate(response.json())

    def get_execution(self, execution_id: str) -> ExecutionResponse:
        """Fetch execution details by ID.

        ``GET /api/v1/executions/{execution_id}``

        Returns the execution with populated attempts list.
        """
        response = self._get_raw(f"/api/v1/executions/{execution_id}")
        return ExecutionResponse.model_validate(response.json())

    def list_executions(
        self,
        *,
        benchmark_version_id: str | None = None,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ExecutionResponse]:
        """List executions with optional filters.

        ``GET /api/v1/executions``

        Returns all matching executions (not paginated in the ``PageResponse``
        sense — the backend returns ``ExecutionListResponse`` with ``items``
        and ``total``). This method returns the items list directly.
        """
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if benchmark_version_id is not None:
            params["benchmark_version_id"] = benchmark_version_id
        if status is not None:
            params["status"] = status
        response = self._get_raw("/api/v1/executions", params=params)
        data = response.json()
        return [ExecutionResponse.model_validate(item) for item in data["items"]]

    # ── lifecycle ─────────────────────────────────────────────────────

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._http.close()

    def __enter__(self) -> AtlasClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

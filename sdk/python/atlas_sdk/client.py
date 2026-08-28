"""AtlasClient — the single SDK entry point.

Provides a thin HTTP client whose methods return typed DTOs and raise
typed errors.  Contains **zero** Atlas business logic.

Dependency chain:  cli → atlas-sdk (this module) → httpx → /api/v1
"""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable
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
from atlas_sdk.models.dashboard import DashboardSnapshot
from atlas_sdk.models.executions import ExecutionPage, ExecutionResponse
from atlas_sdk.models.health import HealthData, LivenessResponse, ReadinessResponse
from atlas_sdk.models.history import ExecutionHistoryRead, ModelActivityRead
from atlas_sdk.models.leaderboard import (
    LeaderboardRead,
    ModelBenchmarkHistory,
    ModelSummary,
    TrendPoint,
)
from atlas_sdk.models.reports import (
    DownloadResult,
    PaginatedReportRunsRead,
    ReportSummaryRead,
)
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


def _parse_content_disposition(value: str | None) -> str | None:
    """Extract the ``filename`` parameter from a ``Content-Disposition`` header.

    Supports both ``filename="x.json"`` and ``filename=x.json`` forms.
    Returns ``None`` when the header is missing or has no usable filename.
    """
    if not value:
        return None
    match = re.search(r'filename="?([^";]+)', value)
    if not match:
        return None
    parsed = match.group(1).strip()
    if not parsed:
        return None
    return parsed


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

    def _parse_bare(
        self, response: httpx.Response, builder: Callable[[Any], T]
    ) -> T:
        """Validate and build a bare (non-enveloped) response payload.

        Used for endpoints that return the model directly instead of
        wrapping it in ``APIResponse``.
        """
        try:
            return builder(response.json())
        except Exception as exc:
            raise ValidationError(
                status=response.status_code,
                message=f"Response does not match expected schema: {exc}",
            ) from exc

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
    ) -> ExecutionPage:
        """List executions with optional filters.

        ``GET /api/v1/executions``

        Returns an ``ExecutionPage`` containing items and pagination
        metadata (total, limit, offset) so callers can render pagination
        hints.
        """
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if benchmark_version_id is not None:
            params["benchmark_version_id"] = benchmark_version_id
        if status is not None:
            params["status"] = status
        response = self._get_raw("/api/v1/executions", params=params)
        data = response.json()
        items = [ExecutionResponse.model_validate(item) for item in data["items"]]
        return ExecutionPage(
            items=items,
            total=data["total"],
            limit=limit,
            offset=offset,
        )

    def cancel_execution(self, execution_id: str) -> ExecutionResponse:
        """Request cancellation of a running or queued execution.

        ``POST /api/v1/executions/{execution_id}/cancel``

        Returns the execution with the cancellation flag set.  The actual
        state transition to CANCELLED is cooperative — the worker picks
        it up after its current unit of work.

        Note: the backend returns 409 Conflict if the execution is
        already in a terminal state (COMPLETED, FAILED, CANCELLED,
        TIMED_OUT).  This is *not* idempotent.
        """
        response = self._post_raw(f"/api/v1/executions/{execution_id}/cancel")
        return ExecutionResponse.model_validate(response.json())

    # -- leaderboard --

    def get_benchmark_leaderboard(
        self,
        benchmark_version_id: str,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> LeaderboardRead:
        """Fetch the leaderboard for a benchmark version.

        ``GET /api/v1/benchmarks/{benchmark_version_id}/leaderboard``

        Returns a ``LeaderboardRead`` with entries ranked by overall
        score.  The backend clamps ``limit`` to 1..100.

        Note: this endpoint returns ``LeaderboardRead`` directly (not
        wrapped in ``APIResponse``), like the execution endpoints.
        """
        response = self._get_raw(
            f"/api/v1/benchmarks/{benchmark_version_id}/leaderboard",
            params={"limit": limit, "offset": offset},
        )
        return LeaderboardRead.model_validate(response.json())

    def get_model_summary(self, model_name: str) -> ModelSummary:
        """Fetch the aggregate performance summary for a model.

        ``GET /api/v1/models/{model_name}/summary``

        Returns a ``ModelSummary``.  Unknown model names are not a
        404: the backend returns a 200 with ``benchmarks == 0`` and
        null statistics.

        Note: this endpoint returns ``ModelSummary`` directly (not
        wrapped in ``APIResponse``), like the execution endpoints.
        """
        response = self._get_raw(f"/api/v1/models/{model_name}/summary")
        return ModelSummary.model_validate(response.json())

    def get_model_history(self, model_name: str) -> list[TrendPoint]:
        """Fetch a model's performance history, one point per execution.

        ``GET /api/v1/models/{model_name}/history``

        Returns a chronological list of ``TrendPoint``.  Unknown model
        names are not a 404: the backend returns a 200 with an empty
        list.

        Note: this endpoint returns ``list[TrendPoint]`` directly (not
        wrapped in ``APIResponse``), like the execution endpoints.
        """
        response = self._get_raw(f"/api/v1/models/{model_name}/history")
        return self._parse_bare(
            response,
            lambda raw: [TrendPoint.model_validate(item) for item in raw],
        )

    def get_model_benchmarks(
        self, model_name: str
    ) -> list[ModelBenchmarkHistory]:
        """Fetch a model's performance history grouped by benchmark.

        ``GET /api/v1/models/{model_name}/benchmarks``

        Returns a list of ``ModelBenchmarkHistory``, each with the
        benchmark name and per-version ``TrendPoint`` timelines.  Unknown
        model names are not a 404: the backend returns a 200 with an
        empty list.

        Note: this endpoint returns ``list[ModelBenchmarkHistory]``
        directly (not wrapped in ``APIResponse``), like the execution
        endpoints.
        """
        response = self._get_raw(f"/api/v1/models/{model_name}/benchmarks")
        return self._parse_bare(
            response,
            lambda raw: [
                ModelBenchmarkHistory.model_validate(item) for item in raw
            ],
        )

    def get_dashboard(self) -> DashboardSnapshot:
        """Fetch the aggregated workspace dashboard snapshot.

        ``GET /api/v1/dashboard``

        Returns a ``DashboardSnapshot`` with run counters, resource
        hierarchy, recent executions, activity timeline, and runtime
        metrics.

        Note: this endpoint returns the dict directly (not wrapped in
        ``APIResponse``).
        """
        response = self._get_raw("/api/v1/dashboard")
        return self._parse_bare(response, DashboardSnapshot.model_validate)

    # -- activity --

    def get_recent_benchmarks(self, *, limit: int = 10) -> list[BenchmarkRead]:
        """Fetch the most recently published benchmarks globally.

        ``GET /api/v1/history/benchmarks/recent``
        """
        response = self._get(
            "/api/v1/history/benchmarks/recent", params={"limit": limit}
        )
        return self._unwrap(response, list[BenchmarkRead])

    def get_recent_executions(
        self, *, limit: int = 10
    ) -> list[ExecutionHistoryRead]:
        """Fetch the most recent executions globally.

        ``GET /api/v1/history/executions/recent``
        """
        response = self._get(
            "/api/v1/history/executions/recent", params={"limit": limit}
        )
        return self._unwrap(response, list[ExecutionHistoryRead])

    def get_recent_models(self, *, limit: int = 10) -> list[ModelActivityRead]:
        """Fetch the most recently active target models globally.

        ``GET /api/v1/history/models/recent``
        """
        response = self._get(
            "/api/v1/history/models/recent", params={"limit": limit}
        )
        return self._unwrap(response, list[ModelActivityRead])

    # -- reports --

    def list_report_runs(
        self,
        *,
        status: str | None = None,
        benchmark_id: str | None = None,
        benchmark_version: str | None = None,
        target_model: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedReportRunsRead:
        """List report runs with optional filters.

        ``GET /api/v1/reports/runs``

        Returns a paginated list of report run summaries.

        Note: this endpoint returns ``PaginatedReportRunsRead`` directly
        (not wrapped in ``APIResponse``), like the execution endpoints.
        """
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if status is not None:
            params["status"] = status
        if benchmark_id is not None:
            params["benchmark_id"] = benchmark_id
        if benchmark_version is not None:
            params["benchmark_version"] = benchmark_version
        if target_model is not None:
            params["target_model"] = target_model
        response = self._get_raw("/api/v1/reports/runs", params=params)
        return PaginatedReportRunsRead.model_validate(response.json())

    def get_report_run(self, run_id: str) -> ReportSummaryRead:
        """Fetch the detailed report summary for a single run.

        ``GET /api/v1/reports/runs/{run_id}``

        Returns a ``ReportSummaryRead`` with benchmark context, status,
        timing, overall score, and the capability score breakdown.

        Note: this endpoint returns ``ReportSummaryRead`` directly (not
        wrapped in ``APIResponse``), like the execution endpoints.
        """
        response = self._get_raw(f"/api/v1/reports/runs/{run_id}")
        return ReportSummaryRead.model_validate(response.json())

    def export_report_run(
        self,
        run_id: str,
        *,
        format_type: str = "json",
        include_prompt: bool = False,
        include_expected_output: bool = False,
    ) -> DownloadResult:
        """Export the report for a run as raw JSON or CSV bytes.

        ``GET /api/v1/reports/runs/{run_id}/export``

        Returns a ``DownloadResult`` with the raw response bytes, the
        response ``Content-Type``, and a filename parsed from
        ``Content-Disposition`` (falling back to ``report-<run_id>.<ext>``
        when no usable filename is supplied).
        """
        params: dict[str, Any] = {
            "format": format_type,
            "include_prompt": include_prompt,
            "include_expected_output": include_expected_output,
        }
        response = self._get_raw(f"/api/v1/reports/runs/{run_id}/export", params=params)
        return DownloadResult(
            content=response.content,
            content_type=response.headers.get("content-type"),
            filename=(
                _parse_content_disposition(response.headers.get("content-disposition"))
                or f"report-{run_id}.{format_type}"
            ),
        )

    # ── lifecycle ─────────────────────────────────────────────────────

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._http.close()

    def __enter__(self) -> AtlasClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

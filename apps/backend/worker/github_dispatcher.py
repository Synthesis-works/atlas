"""GitHub Actions execution backend dispatcher.

Routes benchmark executions to GitHub-hosted runners:

    Atlas outbox -> Celery -> this dispatcher -> repository_dispatch
        -> GitHub-hosted runner -> Docker Engine -> benchmark container
        -> driver writes results/provenance directly to the Atlas DB

Security invariants:
- The dispatch payload carries ONLY opaque identifiers (execution_id,
  correlation_id). No prompts, outputs, credentials, or provider secrets ever
  travel through GitHub APIs, argv, or logs.
- Payload fields are validated (UUID) before use and are never interpolated
  into shell commands inside workflows; they flow through environment vars.
- The token is a fine-grained PAT scoped to Actions:write on exactly one repo.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import httpx
import structlog
from sqlalchemy.orm import Session

from atlas_db.models.execution import (
    AttemptStatus,
    Execution,
    ExecutionAttempt,
    ExecutionStatus,
)

logger = structlog.get_logger(__name__)

ACTIVE_ATTEMPT_STATUSES = (
    AttemptStatus.PENDING,
    AttemptStatus.CONTAINER_CREATED,
    AttemptStatus.RUNNING,
)


class ExecutionDispatchError(RuntimeError):
    """The execution could not be dispatched to GitHub Actions."""


class DuplicateDispatchError(ExecutionDispatchError):
    """An active attempt already exists for this execution."""


def validate_execution_id(raw: str | None) -> uuid.UUID:
    """Strictly parse an execution id from an untrusted source."""
    if not raw:
        raise ExecutionDispatchError("execution_id payload field is missing")
    try:
        return uuid.UUID(str(raw))
    except ValueError as exc:
        raise ExecutionDispatchError(f"execution_id {raw!r} is not a valid UUID") from exc


def create_dispatch_attempt(
    db: Session,
    execution_id: uuid.UUID,
    correlation_id: str,
) -> ExecutionAttempt:
    """Create the PENDING github_actions attempt that reserves the dispatch.

    The partial unique index ``uq_active_attempt_per_execution`` makes this
    atomic: a second concurrent dispatch for the same execution raises
    IntegrityError here instead of double-executing on two runners.
    """
    execution = db.get(Execution, execution_id)
    if execution is None:
        raise ExecutionDispatchError(f"Execution {execution_id} does not exist")
    if execution.status != ExecutionStatus.QUEUED:
        raise ExecutionDispatchError(
            f"Execution {execution_id} is {execution.status}, expected QUEUED"
        )

    latest = (
        db.query(ExecutionAttempt)
        .filter(ExecutionAttempt.execution_id == execution_id)
        .order_by(ExecutionAttempt.attempt_number.desc())
        .first()
    )
    attempt = ExecutionAttempt(
        execution_id=execution_id,
        attempt_number=(latest.attempt_number + 1) if latest else 1,
        status=AttemptStatus.PENDING,
        executor_type="github_actions",
        correlation_id=correlation_id,
    )
    db.add(attempt)
    try:
        db.flush()
    except Exception as exc:  # IntegrityError from the partial unique index
        db.rollback()
        raise DuplicateDispatchError(
            f"Execution {execution_id} already has an active attempt"
        ) from exc
    return attempt


def dispatch_to_github(
    execution_id: uuid.UUID,
    correlation_id: str,
    *,
    token: str,
    repo: str,
    event_type: str,
    timeout_seconds: float = 15.0,
    transport: httpx.BaseTransport | None = None,
) -> None:
    """Fire a repository_dispatch carrying only opaque identifiers.

    Returns on HTTP 204. Any other response raises ExecutionDispatchError so
    the caller's retry/backoff machinery can handle transient failures.
    """
    url = f"https://api.github.com/repos/{repo}/dispatches"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    payload = {
        "event_type": event_type,
        "client_payload": {
            "execution_id": str(execution_id),
            "correlation_id": correlation_id,
        },
    }
    started = datetime.now(UTC)
    try:
        if transport is not None:
            with httpx.Client(transport=transport, timeout=timeout_seconds) as client:
                response = client.post(url, headers=headers, json=payload)
        else:
            response = httpx.post(
                url,
                headers=headers,
                json=payload,
                timeout=timeout_seconds,
            )
    except httpx.HTTPError as exc:
        raise ExecutionDispatchError(f"GitHub dispatch request failed: {exc}") from exc
    latency_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
    logger.info(
        "github_dispatch_attempted",
        execution_id=str(execution_id),
        correlation_id=correlation_id,
        status_code=response.status_code,
        latency_ms=latency_ms,
    )
    if response.status_code != 204:
        # Never include the token or response body (may echo payloads).
        raise ExecutionDispatchError(
            f"GitHub dispatch returned HTTP {response.status_code} for execution {execution_id}"
        )


def run_github_dispatch(
    db: Session,
    execution_id_str: str,
    correlation_id: str | None,
    *,
    token: str,
    repo: str,
    event_type: str,
    transport: httpx.BaseTransport | None = None,
) -> None:
    """Full dispatch pipeline: validate -> reserve attempt -> fire API call.

    Raises ExecutionDispatchError subtypes; caller owns retry/failure policy.
    """
    execution_id = validate_execution_id(execution_id_str)
    correlation_id = correlation_id or f"gha-{execution_id}"
    create_dispatch_attempt(db, execution_id, correlation_id)
    db.commit()
    dispatch_to_github(
        execution_id,
        correlation_id,
        token=token,
        repo=repo,
        event_type=event_type,
        transport=transport,
    )

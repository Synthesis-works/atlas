"""Optional per-user abuse limits for the Atlas Agent API.

These are DB-backed sliding-window counters (serverless-safe: no Redis or
in-memory process state), gated behind ``agent_rate_limit_enabled``. They are a
minimal practical abuse control only -- not a billing-grade quota subsystem.
"""

from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.backend.config import settings
from apps.backend.dependencies import get_db_session, require_authenticated
from apps.backend.schemas.auth import TokenClaims


def _consume(db: Session, key: str, max_count: int, window_seconds: int) -> None:
    """Increment ``key``'s counter; raise 429 once ``max_count`` is exceeded."""
    from atlas_db.models.agent import ApiUsageCounter

    now = datetime.now(UTC)
    counter = db.query(ApiUsageCounter).filter(ApiUsageCounter.key == key).first()
    if counter is None:
        db.add(
            ApiUsageCounter(
                key=key,
                count=1,
                window_until=now + timedelta(seconds=window_seconds),
            )
        )
        db.flush()
        return

    # SQLite stores timezone-aware columns as naive datetimes; treat them as UTC.
    window_until = counter.window_until
    if window_until.tzinfo is None:
        window_until = window_until.replace(tzinfo=UTC)

    if window_until <= now:
        counter.count = 1
        counter.window_until = now + timedelta(seconds=window_seconds)
        db.flush()
        return

    if counter.count >= max_count:
        retry_after = max(int((window_until - now).total_seconds()), 1)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Agent request rate limit exceeded for the current window. "
                f"Retry after {retry_after}s."
            ),
            headers={"Retry-After": str(retry_after)},
        )

    counter.count += 1
    db.flush()


def enforce_agent_minute_rate_limit(
    claims: TokenClaims = Depends(require_authenticated),
    db: Session = Depends(get_db_session),
) -> TokenClaims:
    """Per-user per-minute cap on agent listing and mutation endpoints."""
    if settings.agent_rate_limit_enabled:
        _consume(db, f"agent:user:{claims.sub}", settings.agent_rate_limit_max_per_minute, 60)
    return claims


def enforce_agent_task_create_limit(
    claims: TokenClaims = Depends(require_authenticated),
    db: Session = Depends(get_db_session),
) -> TokenClaims:
    """Per-user per-calendar-day cap on agent task creation."""
    if settings.agent_rate_limit_enabled:
        day_key = datetime.now(UTC).strftime("%Y%m%d")
        _consume(
            db,
            f"agent:tasks:user:{claims.sub}:{day_key}",
            settings.agent_rate_limit_max_tasks_per_day,
            86_400,
        )
    return claims

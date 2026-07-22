from atlas_db.models.core import User
from fastapi import APIRouter, Depends

from apps.backend.authz import require_superuser
from apps.backend.schemas.responses import APIResponse
from apps.backend.worker.celery_app import celery_app

router = APIRouter(prefix="/system", tags=["System"])


@router.get("/celery/health", response_model=APIResponse[dict])
def celery_health(user: User = Depends(require_superuser)):
    """
    Check the health of the Celery worker cluster.
    Requires administrative RBAC.
    """
    try:
        inspector = celery_app.control.inspect()
        active = inspector.active() or {}
        scheduled = inspector.scheduled() or {}
        reserved = inspector.reserved() or {}
        stats = inspector.stats() or {}

        status = "ok" if active or stats else "degraded"

        return APIResponse.success_response(
            data={
                "status": status,
                "workers": len(stats.keys()) if stats else 0,
                "tasks": {
                    "active": sum(len(tasks) for tasks in active.values()) if active else 0,
                    "scheduled": sum(len(tasks) for tasks in scheduled.values())
                    if scheduled
                    else 0,
                    "reserved": sum(len(tasks) for tasks in reserved.values()) if reserved else 0,
                },
            }
        )
    except Exception as e:
        return APIResponse.error_response(
            message=f"Failed to fetch Celery health: {str(e)}", status_code=503
        )


@router.get("/health/live")
async def health_live():
    """
    Liveness probe. Returns 200 OK if the process is running.
    """
    return {"status": "alive", "version": "0.9.0"}


from atlas_db.session import get_db
from sqlalchemy import text
from sqlalchemy.orm import Session


@router.get("/health/ready")
async def health_ready(db: Session = Depends(get_db)):
    """
    Readiness probe. Returns 200 OK if dependencies are available.

    Dependencies checked:
    - Database (PostgreSQL)

    Not checked (handled by other services):
    - Celery workers
    - Redis (message broker)
    """
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        return APIResponse.error_response(message="Database connection failed", status_code=503)

    return {"status": "ready", "checks": {"database": db_status}}


from fastapi.responses import PlainTextResponse


@router.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """
    Exposes metrics for Prometheus scraping.
    """
    # This would typically return `prometheus_client.generate_latest()`
    # We return a placeholder for now since we haven't configured a full prometheus registry
    return "# HELP atlas_health_checks_total Total health checks\n# TYPE atlas_health_checks_total counter\natlas_health_checks_total 1.0\n"

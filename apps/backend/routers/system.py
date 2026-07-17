from fastapi import APIRouter, Depends
from atlas_db.models.core import User
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
        
        return APIResponse.success_response(data={
            "status": status,
            "workers": len(stats.keys()) if stats else 0,
            "tasks": {
                "active": sum(len(tasks) for tasks in active.values()) if active else 0,
                "scheduled": sum(len(tasks) for tasks in scheduled.values()) if scheduled else 0,
                "reserved": sum(len(tasks) for tasks in reserved.values()) if reserved else 0
            }
        })
    except Exception as e:
        return APIResponse.error_response(
            message=f"Failed to fetch Celery health: {str(e)}",
            status_code=503
        )

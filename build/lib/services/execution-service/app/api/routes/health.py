from typing import Any

from app.services.health_service import HealthService
from fastapi import APIRouter, Depends

router = APIRouter()


def get_health_service() -> HealthService:
    return HealthService()


@router.get("/health")
def health(health_service: HealthService = Depends(get_health_service)) -> dict[str, Any]:
    """
    Returns the current snapshot of the Execution Engine health.
    """
    return health_service.snapshot()

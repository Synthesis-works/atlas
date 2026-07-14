from fastapi import APIRouter, Depends
from typing import Dict, Any

from app.services.health_service import HealthService
# In a real FastAPI app, we'd have a dependency injection method for HealthService here
# For the sake of the architecture example, we assume it's injected.

router = APIRouter()

def get_health_service() -> HealthService:
    # Dummy dependency for illustration
    raise NotImplementedError()

@router.get("/health")
def health(health_service: HealthService = Depends(get_health_service)) -> Dict[str, Any]:
    """
    Returns the current snapshot of the Execution Engine health.
    """
    return health_service.snapshot()

from fastapi import APIRouter, Request
from pydantic import BaseModel
from apps.backend.schemas.responses import APIResponse, ResponseMeta
from datetime import datetime, timezone

router = APIRouter(tags=["Health"])

class HealthData(BaseModel):
    status: str
    version: str

@router.get("/health", response_model=APIResponse[HealthData])
async def health_check(request: Request):
    """
    Basic health check endpoint to verify the API is running.
    """
    from apps.backend.config import settings
    
    data = HealthData(status="ok", version=settings.version)
    meta = ResponseMeta(
        request_id=getattr(request.state, "request_id", "unknown"),
        timestamp=datetime.now(timezone.utc)
    )
    return APIResponse(success=True, data=data, meta=meta)

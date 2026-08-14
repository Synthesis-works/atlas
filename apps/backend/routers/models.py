from fastapi import APIRouter
from apps.backend.adapters.factory import AdapterFactory
from apps.backend.schemas.responses import APIResponse

router = APIRouter(prefix="/models", tags=["Models"])

@router.get("", response_model=APIResponse[list[dict]])
def list_models():
    """
    List available models from the execution adapters.
    """
    try:
        models = AdapterFactory.get_available_models()
        return APIResponse.success_response(data=models)
    except Exception as e:
        return APIResponse.error_response(message=str(e))

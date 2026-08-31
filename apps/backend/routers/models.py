"""Execution-target model catalog endpoint (``GET /api/v1/models``, Slice 7).

Lists the target models ``run submit --target-model`` accepts for THIS
deployment, sourced from the same provider configuration and availability the
execution path uses.  ``NOT_CONFIGURED`` means Atlas knows the model but this
deployment lacks the credentials/host to execute it — not that it is invalid.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from apps.backend.adapters.factory import AdapterFactory
from apps.backend.dependencies import require_authenticated
from apps.backend.schemas.auth import TokenClaims
from apps.backend.schemas.models import ModelRead
from apps.backend.schemas.responses import APIResponse

router = APIRouter(prefix="/models", tags=["Models"])


@router.get(
    "",
    response_model=APIResponse[list[ModelRead]],
    summary="List executable target models",
)
def list_models(
    claims: Annotated[TokenClaims, Depends(require_authenticated)],
) -> APIResponse[list[ModelRead]]:
    """
    List the execution target models this deployment can run.

    Every ``id`` is a canonical value accepted by ``run submit --target-model``
    (``mock`` or ``provider/model``).  ``status`` reflects the same provider
    availability check the execution path applies: ``AVAILABLE`` when
    credentials/host are configured, ``NOT_CONFIGURED`` otherwise.
    """
    return APIResponse.success_response(data=AdapterFactory.get_available_models())

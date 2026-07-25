from datetime import UTC, datetime

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from apps.backend.schemas.responses import APIErrorResponse, ErrorDetail, ResponseMeta
from packages.execution_engine.domain.exceptions import (
    DomainException,
    ExecutionNotFoundError,
    ImmutableExecutionError,
    InvalidStateTransitionError,
    LeaseOwnershipError,
)


def _get_meta(request: Request) -> ResponseMeta:
    return ResponseMeta(
        request_id=getattr(request.state, "request_id", "unknown"), timestamp=datetime.now(UTC)
    )


async def custom_http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """
    Handle generic HTTP exceptions and format them according to the API contract.
    """
    error_response = APIErrorResponse(
        error=ErrorDetail(code=f"HTTP_{exc.status_code}", message=str(exc.detail)),
        meta=_get_meta(request),
    )
    return JSONResponse(status_code=exc.status_code, content=error_response.model_dump(mode="json"))


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handle Pydantic validation errors and format them according to the API contract.
    """
    error_response = APIErrorResponse(
        error=ErrorDetail(
            code="VALIDATION_ERROR", message="The request payload is invalid.", details=exc.errors()
        ),
        meta=_get_meta(request),
    )
    return JSONResponse(status_code=422, content=error_response.model_dump(mode="json"))


async def domain_exception_handler(request: Request, exc: DomainException) -> JSONResponse:
    """
    Handle domain exceptions gracefully.
    """
    status_code = 400
    if isinstance(exc, (InvalidStateTransitionError, ImmutableExecutionError)):
        status_code = 409
    elif isinstance(exc, ExecutionNotFoundError):
        status_code = 404
    elif isinstance(exc, LeaseOwnershipError):
        status_code = 403

    error_response = APIErrorResponse(
        error=ErrorDetail(code=exc.__class__.__name__, message=str(exc)), meta=_get_meta(request)
    )
    return JSONResponse(status_code=status_code, content=error_response.model_dump(mode="json"))


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all handler for unhandled server errors.
    """
    # Note: In a production app, log the traceback here.
    error_response = APIErrorResponse(
        error=ErrorDetail(code="INTERNAL_SERVER_ERROR", message="An unexpected error occurred."),
        meta=_get_meta(request),
    )
    return JSONResponse(status_code=500, content=error_response.model_dump(mode="json"))

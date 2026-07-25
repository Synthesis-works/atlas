from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class ResponseMeta(BaseModel):
    request_id: str = Field(..., description="Unique identifier for the request")
    timestamp: datetime = Field(..., description="UTC ISO-8601 timestamp of the response")


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Application-specific error code")
    message: str = Field(..., description="Human-readable error message")
    details: Any | None = Field(default=None, description="Additional context or validation errors")


class APIResponse(BaseModel, Generic[DataT]):
    """
    Standard generic success response envelope.
    """

    success: bool = Field(default=True, description="Indicates if the request was successful")
    message: str = Field(
        default="Request processed successfully", description="Optional success message"
    )
    data: DataT = Field(..., description="The response payload")
    meta: ResponseMeta

    @classmethod
    def success_response(
        cls, data: DataT, message: str = "Request processed successfully"
    ) -> "APIResponse[DataT]":
        return cls(
            data=data,
            message=message,
            meta=ResponseMeta(request_id="temp-id", timestamp=datetime.now(UTC)),
        )


class APIErrorResponse(BaseModel):
    """
    Standard error response envelope.
    """

    success: bool = Field(default=False, description="Always false for errors")
    error: ErrorDetail
    meta: ResponseMeta


class PaginationMeta(BaseModel):
    total: int = Field(..., description="Total number of items")
    offset: int = Field(..., description="Number of items skipped")
    limit: int = Field(..., description="Maximum number of items returned")


class PaginatedData(BaseModel, Generic[DataT]):
    items: list[DataT]
    pagination: PaginationMeta


class PaginatedResponse(APIResponse[PaginatedData[DataT]], Generic[DataT]):
    """
    Standard paginated response envelope.
    """

    pass

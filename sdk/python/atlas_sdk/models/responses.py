"""Standard API response envelopes — mirror of ``apps/backend/schemas/responses.py``."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

DataT = TypeVar("DataT")


class ResponseMeta(BaseModel):
    request_id: str
    timestamp: datetime


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any | None = None


class APIResponse(BaseModel, Generic[DataT]):
    """Standard success response envelope."""

    success: bool = True
    message: str = "Request processed successfully"
    data: DataT
    meta: ResponseMeta


class APIErrorResponse(BaseModel):
    """Standard error response envelope."""

    success: bool = False
    error: ErrorDetail
    meta: ResponseMeta

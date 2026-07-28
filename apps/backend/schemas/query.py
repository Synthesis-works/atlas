from datetime import datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field


T = TypeVar("T")
SortFieldT = TypeVar("SortFieldT")


class PageRequest(BaseModel):
    """
    Standard pagination request parameters.
    Prefers cursor-based pagination for large datasets, falls back to offset.
    """
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(50, ge=1, le=100, description="Maximum number of items to return")
    offset: int | None = Field(None, ge=0, description="Number of items to skip")
    cursor: str | None = Field(None, description="Preferred evolution path for large datasets")


class PageResponse(BaseModel, Generic[T]):
    """
    Standard paginated response envelope.
    """
    items: list[T]
    total: int
    limit: int
    offset: int | None = None
    next_cursor: str | None = None


class SortRequest(BaseModel, Generic[SortFieldT]):
    """
    Standard sorting request parameters.
    """
    model_config = ConfigDict(extra="forbid")

    sort: SortFieldT | None = Field(None, description="Field to sort by")
    order: Literal["asc", "desc"] = Field("desc", description="Sort order")


class BaseFilterRequest(BaseModel):
    """
    Universally applicable filters.
    Domain-specific filters should inherit from this class.
    """
    model_config = ConfigDict(extra="forbid")

    created_after: datetime | None = Field(None, description="Filter items created after this time")
    created_before: datetime | None = Field(None, description="Filter items created before this time")

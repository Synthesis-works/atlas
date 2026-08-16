from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SearchRequest(BaseModel):
    """
    Unified search request schema.
    """

    model_config = ConfigDict(extra="forbid")

    q: str = Field(..., description="String query")
    entity_types: list[str] | None = Field(
        None, description="List of entities to search (e.g., benchmark, dataset, model)"
    )
    limit: int = Field(20, ge=1, le=100)
    cursor: str | None = None


class SearchResult(BaseModel):
    """
    Standardized shape for a search result across the platform.
    """

    model_config = ConfigDict(extra="forbid")

    id: UUID | str
    entity_type: str = Field(..., description="The type of entity (e.g., 'benchmark', 'execution')")
    title: str
    subtitle: str | None = None
    description: str | None = None
    url: str
    score: float = Field(..., ge=0.0, le=1.0, description="Normalized relevance score")
    metadata: dict[str, Any] | None = Field(
        default=None, description="Optional entity-specific metadata"
    )

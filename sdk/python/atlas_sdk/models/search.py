"""Retrieval/search DTOs mirroring ``apps.backend.schemas.search``.

Field-for-field correspondence — no renaming.
"""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    """A single ranked search result (mirror of SearchResult)."""

    id: uuid.UUID | str
    entity_type: str
    title: str
    subtitle: str | None = None
    description: str | None = None
    url: str
    score: float = Field(..., ge=0.0, le=1.0)
    metadata: dict[str, Any] | None = None

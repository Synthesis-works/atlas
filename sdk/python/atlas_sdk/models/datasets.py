"""Dataset DTOs — field-for-field mirror of ``apps/backend/schemas/datasets.py``."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class DatasetVersionRead(BaseModel):
    """Single dataset version from ``POST /projects/{pid}/datasets/{did}/tasks``."""

    id: uuid.UUID
    dataset_id: uuid.UUID
    version_string: str
    storage_path: str
    checksum: str | None = None
    schema_def: dict[str, Any] | list[Any] | None = None
    lifecycle: str
    version_number: int
    created_at: datetime
    created_by_id: uuid.UUID | None = None


class DatasetRead(BaseModel):
    """A dataset (create/get/list/update response)."""

    id: uuid.UUID
    project_id: uuid.UUID
    created_by_member_id: uuid.UUID | None = None
    status: str
    created_at: datetime
    updated_at: datetime
    name: str
    description: str | None = None
    registry_id: uuid.UUID | None = None
    source_id: uuid.UUID | None = None
    license_id: uuid.UUID | None = None
    versions: list[DatasetVersionRead] | None = None
    total_tasks: int = 0
    sample_tasks: list[Any] = []


class DatasetValidationResult(BaseModel):
    """Result of ``POST /projects/{pid}/datasets/{did}/validate``."""

    dataset_id: uuid.UUID
    version_id: uuid.UUID | None = None
    lifecycle: str
    valid: bool
    task_count: int = 0
    messages: list[str] = []

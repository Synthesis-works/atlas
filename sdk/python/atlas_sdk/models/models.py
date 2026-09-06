"""Model catalog DTOs — field-for-field mirror of ``apps/backend/schemas/models.py``."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class ModelStatus(StrEnum):
    """Execution availability of a model on the current deployment.

    ``NOT_CONFIGURED`` means Atlas knows the model but this deployment lacks
    the credentials/host to execute it — the id is still a legal
    ``run submit --target-model`` value.
    """

    AVAILABLE = "AVAILABLE"
    NOT_CONFIGURED = "NOT_CONFIGURED"


class ModelRead(BaseModel):
    """Single execution-target model entry from ``GET /api/v1/models``.

    ``id`` is the canonical string accepted by ``run submit --target-model``
    (``mock`` or ``provider/model``).
    """

    id: str
    provider: str
    display_name: str
    status: ModelStatus
    is_test_only: bool = False

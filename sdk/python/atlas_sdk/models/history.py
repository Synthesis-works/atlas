"""Recent-activity DTOs — mirror ``apps/backend/schemas/executions.py``.

Returned (wrapped in ``APIResponse``) by the ``/api/v1/history/*/recent``
endpoints.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from atlas_sdk.models.executions import ExecutionState


class ExecutionHistoryRead(BaseModel):
    """A single recent execution row.

    Mirrors ``apps/backend/schemas/executions.py::ExecutionHistoryRead``.
    """

    id: str
    benchmark_name: str
    target_model: str
    status: ExecutionState
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration: int | None = None
    project_id: str


class ModelActivityRead(BaseModel):
    """A single recently active model.

    Mirrors ``apps/backend/schemas/executions.py::ModelActivityRead``.
    """

    name: str
    last_executed_at: datetime
    execution_count: int

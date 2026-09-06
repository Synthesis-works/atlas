from atlas_db.models.execution import (
    Artifact,
    Execution,
    ExecutionAdapter,
    ExecutionAdapterVersion,
    ModelOutput,
)

from .base import BaseRepository


class ExecutionAdapterRepository(BaseRepository[ExecutionAdapter]):
    model = ExecutionAdapter


class ExecutionAdapterVersionRepository(BaseRepository[ExecutionAdapterVersion]):
    model = ExecutionAdapterVersion


from sqlalchemy.orm import joinedload
from sqlalchemy import func
from datetime import datetime


class ExecutionRepository(BaseRepository[Execution]):
    model = Execution

    def get_executions_paginated(
        self,
        limit: int = 50,
        offset: int = 0,
        sort_field: str | None = None,
        sort_order: str = "desc",
        project_ids: list | None = None,
    ) -> tuple[list[Execution], int]:
        from atlas_db.repositories.query_utils import (
            apply_pagination,
            apply_sorting,
            get_paginated_results,
        )
        from typing import cast

        query = self.db.query(self.model)

        if project_ids is not None:
            query = query.filter(self.model.project_id.in_(project_ids))

        if sort_field:
            query = apply_sorting(query, self.model, sort_field, sort_order)
        else:
            query = apply_sorting(query, self.model, "created_at", "desc")

        return cast(tuple[list[Execution], int], get_paginated_results(query, limit, offset))

    def get_recent_models(
        self, limit: int = 10, project_ids: list | None = None
    ) -> list[tuple[str, datetime, int]]:
        from typing import cast

        query = self.db.query(
            self.model.target_model,
            func.max(self.model.created_at).label("last_executed_at"),
            func.count(self.model.id).label("execution_count"),
        )

        # The security filter applies to the underlying execution rows BEFORE the
        # target_model aggregation: a project that is not accessible to the caller
        # can never contribute a model to the activity stream.
        if project_ids is not None:
            query = query.filter(self.model.project_id.in_(project_ids))

        query = query.group_by(self.model.target_model)
        query = query.order_by(func.max(self.model.created_at).desc())
        query = query.limit(limit)
        return cast(list[tuple[str, datetime, int]], query.all())


class ModelOutputRepository(BaseRepository[ModelOutput]):
    model = ModelOutput


class ArtifactRepository(BaseRepository[Artifact]):
    model = Artifact

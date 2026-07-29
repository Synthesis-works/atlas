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
    ) -> tuple[list[Execution], int]:
        from atlas_db.repositories.query_utils import (
            apply_pagination,
            apply_sorting,
            get_paginated_results,
        )

        query = self.db.query(self.model)

        if sort_field:
            query = apply_sorting(query, self.model, sort_field, sort_order)
        else:
            query = apply_sorting(query, self.model, "created_at", "desc")

        return get_paginated_results(query, limit, offset)

    def get_recent_models(self, limit: int = 10) -> list[tuple[str, datetime, int]]:
        query = (
            self.db.query(
                self.model.target_model,
                func.max(self.model.created_at).label("last_executed_at"),
                func.count(self.model.id).label("execution_count"),
            )
            .group_by(self.model.target_model)
            .order_by(func.max(self.model.created_at).desc())
            .limit(limit)
        )
        return query.all()


class ModelOutputRepository(BaseRepository[ModelOutput]):
    model = ModelOutput


class ArtifactRepository(BaseRepository[Artifact]):
    model = Artifact

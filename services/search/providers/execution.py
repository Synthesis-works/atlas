from sqlalchemy import or_
from sqlalchemy.orm import Session

from apps.backend.schemas.search import SearchRequest, SearchResult
from packages.database.atlas_db.models.execution import Execution
from packages.database.atlas_db.repositories.query_utils import apply_pagination
from services.search.providers.base import SearchProvider


class ExecutionSearchProvider(SearchProvider):
    def __init__(self, db: Session):
        self.db = db

    @property
    def entity_type(self) -> str:
        return "execution"

    def search(self, request: SearchRequest) -> list[SearchResult]:
        query = self.db.query(Execution)

        if request.q:
            search_term = f"%{request.q}%"
            # Match UUID explicitly if requested, otherwise match target model or status
            # Wait, Execution.id is UUID. Using ilike on UUID might crash in Postgres if not casted to string.
            # Safe strategy: match on target_model or cast ID to string.
            from sqlalchemy import cast, String

            query = query.filter(
                or_(
                    cast(Execution.id, String).ilike(search_term),
                    Execution.target_model.ilike(search_term),
                )
            )

        query = apply_pagination(query, limit=request.limit)
        executions = query.all()

        results = []
        for e in executions:
            score = 0.5
            if request.q:
                q_lower = request.q.lower()
                target_lower = e.target_model.lower()
                id_str = str(e.id).lower()
                if q_lower in (id_str, target_lower):
                    score = 1.0
                elif id_str.startswith(q_lower) or target_lower.startswith(q_lower):
                    score = 0.8

            results.append(
                SearchResult(
                    id=str(e.id),
                    entity_type=self.entity_type,
                    title=f"Execution for {e.target_model}",
                    subtitle=f"Status: {e.status.value}",
                    description=None,
                    url=f"/executions/{e.id}",
                    score=score,
                    metadata={
                        "target_model": e.target_model,
                        "status": e.status.value,
                        "project_id": str(e.project_id),
                        "benchmark_version_id": str(e.benchmark_version_id),
                    },
                )
            )

        return results

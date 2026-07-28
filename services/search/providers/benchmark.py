from sqlalchemy import or_
from sqlalchemy.orm import Session

from apps.backend.schemas.search import SearchRequest, SearchResult
from packages.database.atlas_db.models.authoring import Benchmark
from packages.database.atlas_db.repositories.query_utils import apply_pagination
from services.search.providers.base import SearchProvider


class BenchmarkSearchProvider(SearchProvider):
    def __init__(self, db: Session):
        self.db = db

    @property
    def entity_type(self) -> str:
        return "benchmark"

    def search(self, request: SearchRequest) -> list[SearchResult]:
        query = self.db.query(Benchmark)

        if request.q:
            search_term = f"%{request.q}%"
            # Simple V1 ranking: matching name is better than description
            # Since we return a flat list, we'll assign arbitrary scores here
            # and sort locally before returning.
            # In V2, we would use PostgreSQL full-text search (tsvector).
            
            # For now, just fetch all that match
            query = query.filter(
                or_(
                    Benchmark.name.ilike(search_term),
                    Benchmark.description.ilike(search_term)
                )
            )

        # We don't want to pull millions, limit to what is requested
        # Even if multiple providers run, returning up to request.limit is safe
        query = apply_pagination(query, limit=request.limit)
        
        benchmarks = query.all()
        
        results = []
        for b in benchmarks:
            # V1 scoring heuristic
            score = 0.5 # Substring match base
            if request.q:
                q_lower = request.q.lower()
                name_lower = b.name.lower()
                if q_lower == name_lower:
                    score = 1.0 # Exact match
                elif name_lower.startswith(q_lower):
                    score = 0.8 # Prefix match

            results.append(
                SearchResult(
                    id=str(b.id),
                    entity_type=self.entity_type,
                    title=b.name,
                    subtitle=f"Status: {b.status}",
                    description=b.description,
                    url=f"/benchmarks/{b.id}",
                    score=score,
                    metadata={
                        "project_id": str(b.project_id),
                        "status": b.status
                    }
                )
            )
            
        return results

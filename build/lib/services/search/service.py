from apps.backend.schemas.search import SearchRequest, SearchResult
from services.search.registry import SearchRegistry


class SearchService:
    def __init__(self, registry: SearchRegistry):
        self.registry = registry

    def search_all(self, request: SearchRequest) -> list[SearchResult]:
        results: list[SearchResult] = []
        providers = self.registry.providers()

        # Distribute request to all providers (they should filter by entity_type internally or we filter here)
        # It's cleaner to filter providers if entity_types is specified.
        if request.entity_types:
            requested_types = set(request.entity_types)
            providers = [p for p in providers if p.entity_type in requested_types]

        for provider in providers:
            # Aggregate everything
            results.extend(provider.search(request))

        # Rank globally by score
        results.sort(key=lambda x: x.score, reverse=True)

        # Trim last
        return results[: request.limit]

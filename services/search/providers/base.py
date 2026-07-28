from typing import Protocol

from apps.backend.schemas.search import SearchRequest, SearchResult


class SearchProvider(Protocol):
    """
    Protocol for domain-specific search providers.
    Providers should not handle HTTP parsing or pagination semantics
    beyond the requested limit/cursor.
    """
    @property
    def entity_type(self) -> str:
        """The type of entity this provider handles (e.g., 'benchmark')."""
        ...

    def search(self, request: SearchRequest) -> list[SearchResult]:
        """
        Execute a search for this specific domain.
        Must normalize relevance score to a 0.0 - 1.0 scale.
        Should return up to the requested limit.
        """
        ...

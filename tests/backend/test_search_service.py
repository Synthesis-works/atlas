import unittest

from apps.backend.schemas.search import SearchRequest, SearchResult
from services.search.providers.base import SearchProvider
from services.search.registry import SearchRegistry
from services.search.service import SearchService


class MockProvider(SearchProvider):
    def __init__(self, entity_type: str, results: list[SearchResult]):
        self._entity_type = entity_type
        self._results = results
        
    @property
    def entity_type(self) -> str:
        return self._entity_type
        
    def search(self, request: SearchRequest) -> list[SearchResult]:
        return self._results


class TestSearchService(unittest.TestCase):
    def setUp(self):
        self.r1 = SearchResult(
            id="1", entity_type="benchmark", title="B1", url="/b1", score=0.9
        )
        self.r2 = SearchResult(
            id="2", entity_type="execution", title="E1", url="/e1", score=0.5
        )
        self.r3 = SearchResult(
            id="3", entity_type="benchmark", title="B2", url="/b2", score=0.95
        )
        
        self.p1 = MockProvider("benchmark", [self.r1, self.r3])
        self.p2 = MockProvider("execution", [self.r2])
        
        self.registry = SearchRegistry()
        self.registry.register(self.p1)
        self.registry.register(self.p2)
        
        self.service = SearchService(self.registry)
        
    def test_search_all_aggregates_and_sorts(self):
        req = SearchRequest(q="test", limit=10)
        results = self.service.search_all(req)
        
        self.assertEqual(len(results), 3)
        # Should be sorted by score desc: B2 (0.95), B1 (0.9), E1 (0.5)
        self.assertEqual(results[0].id, "3")
        self.assertEqual(results[1].id, "1")
        self.assertEqual(results[2].id, "2")
        
    def test_search_filters_by_entity_type(self):
        req = SearchRequest(q="test", limit=10, entity_types=["execution"])
        results = self.service.search_all(req)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, "2")
        
    def test_search_respects_limit(self):
        req = SearchRequest(q="test", limit=2)
        results = self.service.search_all(req)
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].id, "3")
        self.assertEqual(results[1].id, "1")

from typing import Any, Dict
from sqlalchemy.orm import Session

from apps.backend.agent.memory import SemanticMemoryStore
from apps.backend.agent.state import AgentPermission
from apps.backend.agent.tools.base import BaseTool


class SearchMemoryTool(BaseTool):
    name = "search_memory"
    description = "Search historical agent task experiences, benchmark notes, failure repair strategies, and reports using semantic similarity."
    required_permission = AgentPermission.READ
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Semantic query string (e.g. 'dataset validation missing expected output')."},
            "limit": {"type": "integer", "description": "Maximum results to retrieve (default 5)."},
        },
        "required": ["query"],
    }

    def __init__(self, semantic_store: SemanticMemoryStore = None):
        self.semantic_store = semantic_store or SemanticMemoryStore()

    def execute(self, db: Session, query: str, limit: int = 5, **kwargs: Any) -> Any:
        if not self.semantic_store.is_available:
            return {
                "query": query,
                "available": False,
                "results": [],
                "note": "Semantic memory offline (Ollama unreachable). Current relational DB state remains active.",
            }

        results = self.semantic_store.search(query, limit=limit)
        return {
            "query": query,
            "available": True,
            "total_matches": len(results),
            "results": results,
        }

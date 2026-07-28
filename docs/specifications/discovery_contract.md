# Discovery & Query Layer (Phase D Contract)

The Query Layer provides the foundation for all read-oriented operations in Atlas (Search, History, Discovery, Leaderboards, Analytics).

## 1. Query Principles

To prevent fragmented and inconsistent APIs, every new feature must adhere to the following principles:
1. **All collection endpoints must support pagination.** Unbounded lists are strictly prohibited.
2. **All sorting fields must be explicitly enumerated.** Never accept raw string inputs for sorting columns.
3. **Filters are additive.** Multiple filter conditions act as logical `AND` unless explicitly documented otherwise.
4. **Query parameters should remain backward compatible.** Additions are allowed; removals require versioning.
5. **New collection endpoints must reuse the shared query infrastructure** rather than implementing bespoke pagination or filtering.

---

## 2. Shared Query Objects

### 2.1 Pagination
All collection endpoints must use standard pagination requests.

> **Note on Cursor Pagination:** While the initial API contract uses offset-based pagination (`limit`/`offset`), internal design and future API evolutions must prefer **cursor-based pagination**. For tables with millions of rows (like executions or evaluation results), cursor pagination is required. The `PageRequest` object explicitly supports this evolution path.

**PageRequest (Query Parameters)**
```python
class PageRequest(BaseModel):
    limit: int = Field(50, ge=1, le=100)
    offset: int | None = Field(None, ge=0)
    cursor: str | None = Field(None, description="Preferred evolution path for large datasets")
```

**PageResponse (Response Model)**
```python
class PageResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int | None = None
    next_cursor: str | None = None
```

### 2.2 Sorting
Sort fields are explicitly defined per-resource using Enums to prevent SQL injection and invalid queries.

Example:
```python
class BenchmarkSortField(str, Enum):
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    NAME = "name"

class SortRequest(BaseModel, Generic[SortFieldT]):
    sort: SortFieldT | None = None
    order: Literal["asc", "desc"] = "desc"
```

### 2.3 Filtering
Filter requests are divided into a generic base and domain-specific extensions.

**BaseFilterRequest**
Contains only universally applicable filters:
```python
class BaseFilterRequest(BaseModel):
    created_after: datetime | None = None
    created_before: datetime | None = None
```

**Domain-Specific Examples:**
```python
class BenchmarkFilterRequest(BaseFilterRequest):
    tags: list[str] | None = None
    owner_id: UUID | None = None
    capabilities: list[str] | None = None
    status: BenchmarkStatus | None = None
```

---

## 3. Global Search

A unified endpoint for omnibar and global search across the platform, abstracting over individual `SearchProvider` implementations.

**Endpoint:** `GET /api/v1/search`

**SearchRequest:**
```python
class SearchRequest(BaseModel):
    q: str = Field(..., description="String query")
    entity_types: list[str] | None = Field(None, description="List of entities to search (e.g., benchmark, dataset, model)")
    limit: int = Field(20, ge=1, le=100)
    cursor: str | None = None
```

**Response (Standardized Shape):**
```json
{
  "items": [
    {
      "id": "uuid",
      "entity_type": "benchmark",
      "title": "HumanEval",
      "subtitle": "Python coding benchmark",
      "description": "Standard benchmark for python generation",
      "url": "/benchmarks/uuid",
      "score": 0.91,
      "metadata": {
        "author": "OpenAI",
        "difficulty": "Hard"
      }
    }
  ]
}
```

### 3.1 Search Ranking Rules
Every `SearchProvider` must normalize its relevance into a scale between `0.0` and `1.0`. The `SearchService` aggregates results across all providers, ranks globally by score, and then trims to the requested limit.

**Current Ranking Logic (V1):**
1. Exact Match (Score `1.0`)
2. Prefix Match (Score `0.8`)
3. Substring Match (Score `0.5`)
4. Provider Score (Normalized)

**Future Ranking Roadmap:**
1. BM25 (Term Frequency / Inverse Document Frequency)
2. Hybrid Lexical Search
3. Embeddings
4. Vector Search

---

## 4. History / Recent Activity

History endpoints are explicitly scoped to the most recently created or executed items globally or for an organization, rather than user-specific access history. User-specific "recently viewed" functionality is deferred to a future milestone when user sessions and activity tracking are introduced.

**Endpoints:**
- `GET /api/v1/history/executions/recent` (Most recently started executions)
- `GET /api/v1/history/benchmarks/recent` (Most recently published benchmarks)
- `GET /api/v1/history/models/recent` (Models with recent executions)

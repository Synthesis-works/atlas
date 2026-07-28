from fastapi import APIRouter, Depends

from apps.backend.dependencies import get_search_service
from apps.backend.schemas.query import PageResponse
from apps.backend.schemas.search import SearchRequest, SearchResult
from services.search.service import SearchService

router = APIRouter(tags=["Search"])


@router.get("/search", response_model=PageResponse[SearchResult])
def global_search(
    request: SearchRequest = Depends(), search_service: SearchService = Depends(get_search_service)
):
    """
    Unified global search across all domains.
    Results are globally ranked and trimmed to the requested limit.
    """
    results = search_service.search_all(request)
    return PageResponse(
        items=results,
        total=len(
            results
        ),  # We don't have global total easily, so we can just return the returned length for now, or adapt PageResponse
        limit=request.limit,
        offset=0,
    )

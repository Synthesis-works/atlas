"""Anonymous, read-only endpoints for the public marketing site.

The organisation site (Synthesis Works) is a separate deployment on its own
origin and has no session, so anything served here must be safe to hand to an
unknown visitor: published benchmarks only, no tenant identifiers, and a short
cache lifetime so the CDN absorbs the traffic.
"""

from fastapi import APIRouter, Depends, Response

from apps.backend.dependencies import get_benchmark_app_service
from apps.backend.schemas.benchmarks import BenchmarkSortField, PublicBenchmarkRead
from apps.backend.schemas.query import PageRequest, PageResponse, SortRequest
from apps.backend.schemas.responses import APIResponse
from apps.backend.services.benchmarks import BenchmarkApplicationService

router = APIRouter(prefix="/public", tags=["Public"])


@router.get(
    "/benchmarks",
    response_model=APIResponse[PageResponse[PublicBenchmarkRead]],
    summary="List published benchmarks",
)
def list_published_benchmarks(
    response: Response,
    page_req: PageRequest = Depends(),
    sort_req: SortRequest[BenchmarkSortField] = Depends(),
    app_service: BenchmarkApplicationService = Depends(get_benchmark_app_service),
) -> APIResponse[PageResponse[PublicBenchmarkRead]]:
    """The published benchmark catalogue, readable without authentication.

    Drafts are never returned, whatever their project's visibility, and the
    owning project id is not part of the payload.
    """
    response.headers["Cache-Control"] = "public, max-age=60"

    page = app_service.get_published_benchmarks_paginated(
        page_req=page_req,
        sort_req=sort_req,
    )
    return APIResponse.success_response(data=page)

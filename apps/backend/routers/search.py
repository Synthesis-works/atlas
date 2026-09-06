import uuid

from atlas_db.models.core import OrganizationRole
from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from apps.backend.authz import ProjectAuthorizationService, get_project_authz_service
from apps.backend.dependencies import (
    get_db_session,
    get_search_service,
    require_authenticated,
)
from apps.backend.schemas.auth import TokenClaims
from apps.backend.schemas.query import PageResponse
from apps.backend.schemas.search import SearchRequest, SearchResult
from services.search.service import SearchService, resolve_accessible_project_ids

router = APIRouter(tags=["Search"])

READ_ROLES = [
    OrganizationRole.OWNER,
    OrganizationRole.ADMIN,
    OrganizationRole.MEMBER,
    OrganizationRole.VIEWER,
]


def _to_page(results: list[SearchResult], request: SearchRequest) -> PageResponse[SearchResult]:
    return PageResponse(
        items=results,
        total=len(
            results
        ),  # We don't have global total easily, so we can just return the returned length for now, or adapt PageResponse
        limit=request.limit,
        offset=0,
    )


@router.get("/search", response_model=PageResponse[SearchResult])
def global_search(
    request: SearchRequest = Depends(),
    claims: TokenClaims = Depends(require_authenticated),
    db: Session = Depends(get_db_session),
    search_service: SearchService = Depends(get_search_service),
):
    """
    Unified search across the caller's accessible projects.
    The caller must be authenticated; results are scoped to the projects the
    user is an active member of (membership -> org -> project).
    """
    project_ids = resolve_accessible_project_ids(db, user_id=claims.sub)
    results = search_service.search_all(request, project_ids=project_ids)
    return _to_page(results, request)


@router.get("/projects/{project_id}/search", response_model=PageResponse[SearchResult])
def project_search(
    project_id: uuid.UUID = Path(...),
    request: SearchRequest = Depends(),
    claims: TokenClaims = Depends(require_authenticated),
    authz_service: ProjectAuthorizationService = Depends(get_project_authz_service),
    search_service: SearchService = Depends(get_search_service),
):
    """
    Project-scoped unified search.
    The caller must be an active member of the project's organization; results
    are strictly scoped to the single requested project.
    """
    authz_service.authorize_project_access(
        project_id=project_id, user_id=claims.sub, allowed_roles=READ_ROLES
    )
    results = search_service.search_all(request, project_ids=[project_id])
    return _to_page(results, request)

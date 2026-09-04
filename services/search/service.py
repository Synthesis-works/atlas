from apps.backend.schemas.search import SearchRequest, SearchResult
from atlas_db.models.core import MembershipStatus, OrganizationMember, Project
from services.search.registry import SearchRegistry


def resolve_accessible_project_ids(db, user_id) -> list:
    """Projects the authenticated user may read, via active org membership.

    A user's access to projects is org-granular: the user must be an ACTIVE
    member of the organization that owns a project. This resolves every
    project the user can access so callers can scope searches to exactly that
    set (B1 hardening of the global ``/search`` endpoint). It reuses the same
    membership rule the existing ``ProjectAuthorizationService`` enforces for
    per-project access, rather than introducing a parallel access model.
    """
    org_ids = [
        org_id
        for (org_id,) in db.query(OrganizationMember.organization_id)
        .filter(
            OrganizationMember.user_id == user_id,
            OrganizationMember.status == MembershipStatus.ACTIVE,
        )
        .all()
    ]
    if not org_ids:
        return []
    return [
        project_id
        for (project_id,) in db.query(Project.id).filter(Project.org_id.in_(org_ids)).all()
    ]


class SearchService:
    def __init__(self, registry: SearchRegistry):
        self.registry = registry

    def search_all(
        self, request: SearchRequest, project_ids: list | None = None
    ) -> list[SearchResult]:
        """Run a unified search, optionally scoped to a set of project ids.

        ``project_ids`` restricts every provider to rows belonging to one of the
        given projects. Passing ``None`` falls back to the provider's unscoped
        behavior (used only by callers that have already enforced access
        control, e.g. the global search endpoint after resolving the caller's
        accessible projects).
        """
        results: list[SearchResult] = []
        providers = self.registry.providers()

        # Distribute request to all providers (they should filter by entity_type internally or we filter here)
        # It's cleaner to filter providers if entity_types is specified.
        if request.entity_types:
            requested_types = set(request.entity_types)
            providers = [p for p in providers if p.entity_type in requested_types]

        for provider in providers:
            # Aggregate everything
            results.extend(provider.search(request, project_ids=project_ids))

        # Rank globally by score
        results.sort(key=lambda x: x.score, reverse=True)

        # Trim last
        return results[: request.limit]

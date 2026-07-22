from collections.abc import Callable
from uuid import UUID

from atlas_db.models.core import MembershipStatus, OrganizationMember, OrganizationRole, User
from atlas_db.repositories.core import OrganizationMemberRepository
from fastapi import Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from apps.backend.config import settings
from apps.backend.dependencies import get_db_session, require_authenticated
from apps.backend.schemas.auth import TokenClaims


def require_superuser(
    claims: TokenClaims = Depends(require_authenticated), db: Session = Depends(get_db_session)
) -> User:
    user = db.query(User).filter(User.id == claims.sub).first()
    if not user or user.email not in settings.admin_emails:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="System administrative access required."
        )
    return user


def require_org_member(
    org_id: UUID = Path(...),
    claims: TokenClaims = Depends(require_authenticated),
    db: Session = Depends(get_db_session),
) -> OrganizationMember:
    member_repo = OrganizationMemberRepository(db)
    # We look up by user_id (claims.sub) and org_id
    member = member_repo.get_by_user_and_org(user_id=claims.sub, org_id=org_id)

    if not member or member.status != MembershipStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an active member of this organization.",
        )
    return member


def require_role(allowed_roles: list[OrganizationRole]) -> Callable:
    def role_checker(member: OrganizationMember = Depends(require_org_member)):
        if member.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required role: {', '.join([r.value for r in allowed_roles])}",
            )
        return member

    return role_checker


class ProjectAuthorizationService:
    def __init__(self, db: Session):
        self.db = db
        self.member_repo = OrganizationMemberRepository(db)

    def authorize_project_access(
        self, project_id: UUID, user_id: UUID, allowed_roles: list[OrganizationRole]
    ) -> OrganizationMember:
        from atlas_db.repositories.core import ProjectRepository

        project_repo = ProjectRepository(self.db)
        project = project_repo.get(project_id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        member = self.member_repo.get_by_user_and_org(user_id=user_id, org_id=project.org_id)
        if not member or member.status != MembershipStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not an active member of the project's organization",
            )

        if member.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required role: {', '.join([r.value for r in allowed_roles])}",
            )

        return member


def get_project_authz_service(db: Session = Depends(get_db_session)) -> ProjectAuthorizationService:
    return ProjectAuthorizationService(db)

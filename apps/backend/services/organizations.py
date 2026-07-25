import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from atlas_db.models.core import (
    Invitation,
    InvitationStatus,
    MembershipStatus,
    Organization,
    OrganizationMember,
    OrganizationRole,
)
from atlas_db.repositories.core import (
    InvitationRepository,
    OrganizationMemberRepository,
    OrganizationRepository,
)
from fastapi import HTTPException

from apps.backend.schemas.organizations import InvitationCreate, OrganizationCreate


class OrganizationService:
    def __init__(
        self,
        org_repo: OrganizationRepository,
        member_repo: OrganizationMemberRepository,
        invite_repo: InvitationRepository,
    ):
        self.org_repo = org_repo
        self.member_repo = member_repo
        self.invite_repo = invite_repo

    def list_for_user(self, user_id: UUID) -> list[Organization]:
        # For now, we fetch memberships and return the orgs
        # (A custom query in repo would be better, but this works for mocked flow)
        memberships = (
            self.member_repo.db.query(OrganizationMember)
            .filter(
                OrganizationMember.user_id == user_id,
                OrganizationMember.status == MembershipStatus.ACTIVE,
            )
            .all()
        )
        org_ids = [m.organization_id for m in memberships]
        return self.org_repo.db.query(Organization).filter(Organization.id.in_(org_ids)).all()

    def create(self, user_id: UUID, data: OrganizationCreate) -> Organization:
        org = self.org_repo.create(
            obj_in={"name": data.name, "slug": data.slug, "display_name": data.display_name}
        )

        # Creator is OWNER
        self.member_repo.create(
            obj_in={
                "user_id": user_id,
                "organization_id": org.id,
                "role": OrganizationRole.OWNER,
                "status": MembershipStatus.ACTIVE,
            }
        )
        return org

    def get(self, org_id: UUID) -> Organization | None:
        return self.org_repo.get(org_id)

    def list_members(self, org_id: UUID) -> list[OrganizationMember]:
        return (
            self.member_repo.db.query(OrganizationMember)
            .filter(OrganizationMember.organization_id == org_id)
            .all()
        )

    def invite_member(
        self, org_id: UUID, data: InvitationCreate, invited_by_user_id: UUID
    ) -> Invitation:
        # Check if invite already exists and is pending
        existing = (
            self.invite_repo.db.query(Invitation)
            .filter(
                Invitation.organization_id == org_id,
                Invitation.email == data.email,
                Invitation.status == InvitationStatus.PENDING,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=409, detail="Pending invitation already exists for this email"
            )

        token = secrets.token_urlsafe(32)
        return self.invite_repo.create(
            obj_in={
                "organization_id": org_id,
                "email": data.email,
                "role": data.role,
                "token": token,
                "status": InvitationStatus.PENDING,
                "invited_by": invited_by_user_id,
                "expires_at": datetime.now(UTC) + timedelta(days=7),
            }
        )

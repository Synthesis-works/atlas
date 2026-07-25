from uuid import UUID

from atlas_db.models.core import OrganizationMember, OrganizationRole
from fastapi import APIRouter, Depends, HTTPException, status

from apps.backend.authz import require_org_member, require_role
from apps.backend.dependencies import get_org_service, require_authenticated
from apps.backend.schemas.auth import TokenClaims
from apps.backend.schemas.organizations import (
    InvitationCreate,
    InvitationRead,
    OrganizationCreate,
    OrganizationMemberRead,
    OrganizationRead,
)
from apps.backend.schemas.responses import APIResponse
from apps.backend.services.organizations import OrganizationService

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.get("", response_model=APIResponse[list[OrganizationRead]])
def list_organizations(
    claims: TokenClaims = Depends(require_authenticated),
    org_service: OrganizationService = Depends(get_org_service),
):
    orgs = org_service.list_for_user(claims.sub)
    return APIResponse.success_response(data=orgs)


@router.post("", response_model=APIResponse[OrganizationRead], status_code=status.HTTP_201_CREATED)
def create_organization(
    data: OrganizationCreate,
    claims: TokenClaims = Depends(require_authenticated),
    org_service: OrganizationService = Depends(get_org_service),
):
    org = org_service.create(claims.sub, data)
    return APIResponse.success_response(data=org, message="Organization created successfully")


@router.get("/{org_id}", response_model=APIResponse[OrganizationRead])
def get_organization(
    org_id: UUID,
    member: OrganizationMember = Depends(require_org_member),
    org_service: OrganizationService = Depends(get_org_service),
):
    org = org_service.get(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return APIResponse.success_response(data=org)


@router.get("/{org_id}/members", response_model=APIResponse[list[OrganizationMemberRead]])
def list_members(
    org_id: UUID,
    member: OrganizationMember = Depends(require_org_member),
    org_service: OrganizationService = Depends(get_org_service),
):
    members = org_service.list_members(org_id)
    return APIResponse.success_response(data=members)


@router.post(
    "/{org_id}/members",
    response_model=APIResponse[InvitationRead],
    status_code=status.HTTP_201_CREATED,
)
def invite_member(
    org_id: UUID,
    data: InvitationCreate,
    member: OrganizationMember = Depends(
        require_role([OrganizationRole.ADMIN, OrganizationRole.OWNER])
    ),
    org_service: OrganizationService = Depends(get_org_service),
):
    invite = org_service.invite_member(org_id, data, invited_by_user_id=member.user_id)
    return APIResponse.success_response(data=invite, message="Invitation sent successfully")

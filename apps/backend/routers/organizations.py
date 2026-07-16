from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID

from apps.backend.schemas.responses import APIResponse
from apps.backend.schemas.organizations import (
    OrganizationCreate, OrganizationRead, OrganizationMemberRead, 
    InvitationCreate, InvitationRead
)
from apps.backend.services.organizations import OrganizationService
from apps.backend.dependencies import get_org_service, get_current_member

router = APIRouter(prefix="/organizations", tags=["Organizations"])

@router.get("", response_model=APIResponse[List[OrganizationRead]])
def list_organizations(
    current_member: OrganizationMemberRead = Depends(get_current_member),
    org_service: OrganizationService = Depends(get_org_service)
):
    orgs = org_service.list_for_user(current_member.user_id)
    return APIResponse.success_response(data=orgs)

@router.post("", response_model=APIResponse[OrganizationRead], status_code=status.HTTP_201_CREATED)
def create_organization(
    data: OrganizationCreate,
    current_member: OrganizationMemberRead = Depends(get_current_member),
    org_service: OrganizationService = Depends(get_org_service)
):
    org = org_service.create(current_member.user_id, data)
    return APIResponse.success_response(
        data=org,
        message="Organization created successfully"
    )

@router.get("/{org_id}", response_model=APIResponse[OrganizationRead])
def get_organization(
    org_id: UUID,
    current_member: OrganizationMemberRead = Depends(get_current_member),
    org_service: OrganizationService = Depends(get_org_service)
):
    org = org_service.get(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return APIResponse.success_response(data=org)

@router.get("/{org_id}/members", response_model=APIResponse[List[OrganizationMemberRead]])
def list_members(
    org_id: UUID,
    current_member: OrganizationMemberRead = Depends(get_current_member),
    org_service: OrganizationService = Depends(get_org_service)
):
    members = org_service.list_members(org_id)
    return APIResponse.success_response(data=members)

@router.post("/{org_id}/members", response_model=APIResponse[InvitationRead], status_code=status.HTTP_201_CREATED)
def invite_member(
    org_id: UUID,
    data: InvitationCreate,
    current_member: OrganizationMemberRead = Depends(get_current_member),
    org_service: OrganizationService = Depends(get_org_service)
):
    invite = org_service.invite_member(org_id, data, invited_by_user_id=current_member.user_id)
    return APIResponse.success_response(
        data=invite,
        message="Invitation sent successfully"
    )

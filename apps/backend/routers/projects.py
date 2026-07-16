from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID

from apps.backend.schemas.responses import APIResponse
from apps.backend.schemas.projects import ProjectCreate, ProjectRead
from apps.backend.schemas.organizations import OrganizationMemberRead
from apps.backend.services.projects import ProjectService
from apps.backend.dependencies import get_project_service, get_current_member

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.get("/{project_id}", response_model=APIResponse[ProjectRead])
def get_project(
    project_id: UUID,
    current_member: OrganizationMemberRead = Depends(get_current_member),
    project_service: ProjectService = Depends(get_project_service)
):
    project = project_service.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return APIResponse.success_response(data=project)

# Note: The GET/POST for projects under an organization are conventionally routed 
# through the organizations router or prefix to explicitly enforce ownership, but 
# can also be here with an explicit /organizations/{org_id}/projects prefix.
# We will define a nested router for this purpose.

org_projects_router = APIRouter(prefix="/organizations/{org_id}/projects", tags=["Organization Projects"])

@org_projects_router.get("", response_model=APIResponse[List[ProjectRead]])
def list_org_projects(
    org_id: UUID,
    current_member: OrganizationMemberRead = Depends(get_current_member),
    project_service: ProjectService = Depends(get_project_service)
):
    projects = project_service.list_for_org(org_id)
    return APIResponse.success_response(data=projects)

@org_projects_router.post("", response_model=APIResponse[ProjectRead], status_code=status.HTTP_201_CREATED)
def create_project(
    org_id: UUID,
    data: ProjectCreate,
    current_member: OrganizationMemberRead = Depends(get_current_member),
    project_service: ProjectService = Depends(get_project_service)
):
    project = project_service.create(org_id, member_id=current_member.id, data=data)
    return APIResponse.success_response(
        data=project,
        message="Project created successfully"
    )

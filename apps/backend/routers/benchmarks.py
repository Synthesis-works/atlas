from fastapi import APIRouter, Depends, status, HTTPException
from typing import List
from uuid import UUID

from apps.backend.schemas.responses import APIResponse
from apps.backend.schemas.benchmarks import BenchmarkCreate, BenchmarkUpdate, BenchmarkRead
from apps.backend.services.benchmarks import BenchmarkApplicationService
from apps.backend.dependencies import (
    require_authenticated, 
    get_benchmark_app_service, 
    TokenClaims
)
from apps.backend.authz import get_project_authz_service, ProjectAuthorizationService
from atlas_db.models.core import OrganizationRole

# Router for project-level endpoints
project_benchmarks_router = APIRouter(prefix="/projects/{project_id}/benchmarks", tags=["Benchmarks"])

# Router for root-level endpoints
benchmarks_router = APIRouter(prefix="/benchmarks", tags=["Benchmarks"])

def map_member_role_to_string(role: OrganizationRole) -> str:
    if role in [OrganizationRole.ADMIN, OrganizationRole.OWNER]:
        return "org_admin"
    if role == OrganizationRole.MEMBER:
        return "project_write"
    return "project_read"

@project_benchmarks_router.post("", response_model=APIResponse[BenchmarkRead], status_code=status.HTTP_201_CREATED)
def create_benchmark(
    project_id: UUID,
    data: BenchmarkCreate,
    claims: TokenClaims = Depends(require_authenticated),
    project_authz: ProjectAuthorizationService = Depends(get_project_authz_service),
    app_service: BenchmarkApplicationService = Depends(get_benchmark_app_service)
):
    member = project_authz.authorize_project_access(
        project_id=project_id,
        user_id=claims.sub,
        allowed_roles=[OrganizationRole.MEMBER, OrganizationRole.ADMIN, OrganizationRole.OWNER]
    )
    
    benchmark = app_service.create_benchmark(
        project_id=project_id,
        author_id=claims.sub,
        data=data
    )
    
    return APIResponse.success_response(data=benchmark)

@project_benchmarks_router.get("", response_model=APIResponse[List[BenchmarkRead]])
def list_benchmarks(
    project_id: UUID,
    claims: TokenClaims = Depends(require_authenticated),
    project_authz: ProjectAuthorizationService = Depends(get_project_authz_service),
    app_service: BenchmarkApplicationService = Depends(get_benchmark_app_service)
):
    member = project_authz.authorize_project_access(
        project_id=project_id,
        user_id=claims.sub,
        allowed_roles=[OrganizationRole.VIEWER, OrganizationRole.MEMBER, OrganizationRole.ADMIN, OrganizationRole.OWNER]
    )
    
    benchmarks = app_service.get_benchmarks(project_id)
    return APIResponse.success_response(data=benchmarks)

@benchmarks_router.get("/{benchmark_id}", response_model=APIResponse[BenchmarkRead])
def get_benchmark(
    benchmark_id: UUID,
    claims: TokenClaims = Depends(require_authenticated),
    project_authz: ProjectAuthorizationService = Depends(get_project_authz_service),
    app_service: BenchmarkApplicationService = Depends(get_benchmark_app_service)
):
    # Fetch benchmark first to get project_id, so we can authorize
    benchmark = app_service.get_benchmark(benchmark_id)
    
    member = project_authz.authorize_project_access(
        project_id=benchmark.project_id,
        user_id=claims.sub,
        allowed_roles=[OrganizationRole.VIEWER, OrganizationRole.MEMBER, OrganizationRole.ADMIN, OrganizationRole.OWNER]
    )
    
    return APIResponse.success_response(data=benchmark)

@benchmarks_router.put("/{benchmark_id}", response_model=APIResponse[BenchmarkRead])
def update_benchmark(
    benchmark_id: UUID,
    data: BenchmarkUpdate,
    claims: TokenClaims = Depends(require_authenticated),
    project_authz: ProjectAuthorizationService = Depends(get_project_authz_service),
    app_service: BenchmarkApplicationService = Depends(get_benchmark_app_service)
):
    # Authorize based on project
    benchmark_read = app_service.get_benchmark(benchmark_id)
    
    member = project_authz.authorize_project_access(
        project_id=benchmark_read.project_id,
        user_id=claims.sub,
        allowed_roles=[OrganizationRole.MEMBER, OrganizationRole.ADMIN, OrganizationRole.OWNER]
    )
    
    user_role = map_member_role_to_string(member.role)
    
    updated_benchmark = app_service.update_benchmark(
        benchmark_id=benchmark_id,
        user_id=claims.sub,
        user_role=user_role,
        data=data
    )
    
    return APIResponse.success_response(data=updated_benchmark)

@benchmarks_router.delete("/{benchmark_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_benchmark(
    benchmark_id: UUID,
    claims: TokenClaims = Depends(require_authenticated),
    project_authz: ProjectAuthorizationService = Depends(get_project_authz_service),
    app_service: BenchmarkApplicationService = Depends(get_benchmark_app_service)
):
    benchmark_read = app_service.get_benchmark(benchmark_id)
    
    member = project_authz.authorize_project_access(
        project_id=benchmark_read.project_id,
        user_id=claims.sub,
        allowed_roles=[OrganizationRole.MEMBER, OrganizationRole.ADMIN, OrganizationRole.OWNER]
    )
    
    user_role = map_member_role_to_string(member.role)
    
    app_service.delete_benchmark(
        benchmark_id=benchmark_id,
        user_id=claims.sub,
        user_role=user_role
    )
    # Return nothing for 204
    return None

from apps.backend.schemas.benchmarks import BenchmarkVersionCreate, BenchmarkVersionUpdate, BenchmarkVersionRead

@benchmarks_router.post("/{benchmark_id}/versions", response_model=APIResponse[BenchmarkVersionRead], status_code=status.HTTP_201_CREATED)
def create_benchmark_version(
    benchmark_id: UUID,
    data: BenchmarkVersionCreate,
    claims: TokenClaims = Depends(require_authenticated),
    project_authz: ProjectAuthorizationService = Depends(get_project_authz_service),
    app_service: BenchmarkApplicationService = Depends(get_benchmark_app_service)
):
    benchmark = app_service.get_benchmark(benchmark_id)
    
    member = project_authz.authorize_project_access(
        project_id=benchmark.project_id,
        user_id=claims.sub,
        allowed_roles=[OrganizationRole.MEMBER, OrganizationRole.ADMIN, OrganizationRole.OWNER]
    )
    
    user_role = map_member_role_to_string(member.role)
    
    version = app_service.create_version(
        benchmark_id=benchmark_id,
        user_id=claims.sub,
        user_role=user_role,
        data=data
    )
    
    return APIResponse.success_response(data=version)

@benchmarks_router.get("/{benchmark_id}/versions", response_model=APIResponse[List[BenchmarkVersionRead]])
def list_benchmark_versions(
    benchmark_id: UUID,
    claims: TokenClaims = Depends(require_authenticated),
    project_authz: ProjectAuthorizationService = Depends(get_project_authz_service),
    app_service: BenchmarkApplicationService = Depends(get_benchmark_app_service)
):
    benchmark = app_service.get_benchmark(benchmark_id)
    
    member = project_authz.authorize_project_access(
        project_id=benchmark.project_id,
        user_id=claims.sub,
        allowed_roles=[OrganizationRole.VIEWER, OrganizationRole.MEMBER, OrganizationRole.ADMIN, OrganizationRole.OWNER]
    )
    
    versions = app_service.get_versions(benchmark_id)
    return APIResponse.success_response(data=versions)

benchmark_versions_router = APIRouter(prefix="/benchmark-versions", tags=["Benchmark Versions"])

@benchmark_versions_router.put("/{version_id}", response_model=APIResponse[BenchmarkVersionRead])
def update_benchmark_version(
    version_id: UUID,
    data: BenchmarkVersionUpdate,
    claims: TokenClaims = Depends(require_authenticated),
    project_authz: ProjectAuthorizationService = Depends(get_project_authz_service),
    app_service: BenchmarkApplicationService = Depends(get_benchmark_app_service)
):
    # This requires looking up the version and its benchmark
    # However we can get benchmark_id from the version using repo directly?
    # No, we can just let app_service do it, but we need to check authz first.
    # To authorize, we need project_id.
    # We can fetch the version, get its benchmark_id, then get benchmark, then authorize.
    # Alternatively we can let app_service handle fetching for authz.
    
    # We fetch it indirectly:
    # Actually, we can retrieve version from domain_service inside app_service, but we need it here.
    version = app_service.domain_service.version_repo.get(version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
        
    benchmark = app_service.get_benchmark(version.benchmark_id)
    
    member = project_authz.authorize_project_access(
        project_id=benchmark.project_id,
        user_id=claims.sub,
        allowed_roles=[OrganizationRole.MEMBER, OrganizationRole.ADMIN, OrganizationRole.OWNER]
    )
    
    user_role = map_member_role_to_string(member.role)
    
    updated = app_service.update_version(
        version_id=version_id,
        user_id=claims.sub,
        user_role=user_role,
        data=data
    )
    
    return APIResponse.success_response(data=updated)

@benchmark_versions_router.post("/{version_id}/validate", status_code=status.HTTP_202_ACCEPTED)
def validate_benchmark_version(
    version_id: UUID,
    claims: TokenClaims = Depends(require_authenticated),
    project_authz: ProjectAuthorizationService = Depends(get_project_authz_service),
    app_service: BenchmarkApplicationService = Depends(get_benchmark_app_service)
):
    version = app_service.domain_service.version_repo.get(version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
        
    benchmark = app_service.get_benchmark(version.benchmark_id)
    
    member = project_authz.authorize_project_access(
        project_id=benchmark.project_id,
        user_id=claims.sub,
        allowed_roles=[OrganizationRole.MEMBER, OrganizationRole.ADMIN, OrganizationRole.OWNER]
    )
    
    user_role = map_member_role_to_string(member.role)
    app_service.validate_version(version_id, claims.sub, user_role)
    return None

@benchmark_versions_router.post("/{version_id}/publish", status_code=status.HTTP_200_OK)
def publish_benchmark_version(
    version_id: UUID,
    claims: TokenClaims = Depends(require_authenticated),
    project_authz: ProjectAuthorizationService = Depends(get_project_authz_service),
    app_service: BenchmarkApplicationService = Depends(get_benchmark_app_service)
):
    version = app_service.domain_service.version_repo.get(version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
        
    benchmark = app_service.get_benchmark(version.benchmark_id)
    
    member = project_authz.authorize_project_access(
        project_id=benchmark.project_id,
        user_id=claims.sub,
        allowed_roles=[OrganizationRole.ADMIN, OrganizationRole.OWNER]
    )
    
    user_role = map_member_role_to_string(member.role)
    app_service.publish_version(version_id, claims.sub, user_role)
    return None

@benchmark_versions_router.post("/{version_id}/archive", status_code=status.HTTP_200_OK)
def archive_benchmark_version(
    version_id: UUID,
    claims: TokenClaims = Depends(require_authenticated),
    project_authz: ProjectAuthorizationService = Depends(get_project_authz_service),
    app_service: BenchmarkApplicationService = Depends(get_benchmark_app_service)
):
    version = app_service.domain_service.version_repo.get(version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
        
    benchmark = app_service.get_benchmark(version.benchmark_id)
    
    member = project_authz.authorize_project_access(
        project_id=benchmark.project_id,
        user_id=claims.sub,
        allowed_roles=[OrganizationRole.ADMIN, OrganizationRole.OWNER]
    )
    
    user_role = map_member_role_to_string(member.role)
    app_service.archive_version(version_id, claims.sub, user_role)
    return None

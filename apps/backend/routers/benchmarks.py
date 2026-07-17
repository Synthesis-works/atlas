import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from apps.backend.schemas.benchmarks import BenchmarkRead, BenchmarkCreate, BenchmarkVersionRead, BenchmarkVersionCreate
from apps.backend.services.benchmarks import BenchmarkService
from apps.backend.authz import ProjectAuthorizationService, get_project_authz_service
from apps.backend.dependencies import (
    get_benchmark_service,
    require_authenticated
)
from atlas_db.models.core import OrganizationRole
from apps.backend.schemas.auth import TokenClaims

router = APIRouter(
    prefix="/projects/{project_id}/benchmarks",
    tags=["benchmarks"]
)

@router.get("", response_model=List[BenchmarkRead])
def list_benchmarks(
    project_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    claims: TokenClaims = Depends(require_authenticated),
    authz_service: ProjectAuthorizationService = Depends(get_project_authz_service),
    benchmark_service: BenchmarkService = Depends(get_benchmark_service)
):
    """List all non-archived benchmarks for a project."""
    authz_service.authorize_project_access(
        project_id=project_id, 
        user_id=claims.sub, 
        allowed_roles=[OrganizationRole.OWNER, OrganizationRole.ADMIN, OrganizationRole.MEMBER, OrganizationRole.VIEWER]
    )
    return benchmark_service.list_benchmarks(project_id, skip=skip, limit=limit)

@router.post("", response_model=BenchmarkRead, status_code=status.HTTP_201_CREATED)
def create_benchmark(
    project_id: uuid.UUID,
    data: BenchmarkCreate,
    claims: TokenClaims = Depends(require_authenticated),
    authz_service: ProjectAuthorizationService = Depends(get_project_authz_service),
    benchmark_service: BenchmarkService = Depends(get_benchmark_service)
):
    """Create a new benchmark and its initial version."""
    authz_service.authorize_project_access(
        project_id=project_id, 
        user_id=claims.sub, 
        allowed_roles=[OrganizationRole.OWNER, OrganizationRole.ADMIN, OrganizationRole.MEMBER]
    )
    
    # In a real app we might get the exact organization_member.id for created_by_member_id.
    # For now, following Slice 4 pattern, we use claims.sub (user_id) assuming it maps well.
    # (Actually Dataset uses user_id for now or we just pass it)
    return benchmark_service.create_benchmark(project_id, claims.sub, data)

@router.get("/{benchmark_id}", response_model=BenchmarkRead)
def get_benchmark(
    project_id: uuid.UUID,
    benchmark_id: uuid.UUID,
    claims: TokenClaims = Depends(require_authenticated),
    authz_service: ProjectAuthorizationService = Depends(get_project_authz_service),
    benchmark_service: BenchmarkService = Depends(get_benchmark_service)
):
    """Get a specific benchmark."""
    authz_service.authorize_project_access(
        project_id=project_id, 
        user_id=claims.sub, 
        allowed_roles=[OrganizationRole.OWNER, OrganizationRole.ADMIN, OrganizationRole.MEMBER, OrganizationRole.VIEWER]
    )
    benchmark = benchmark_service.get_benchmark(benchmark_id)
    if not benchmark or benchmark.project_id != project_id:
        raise HTTPException(status_code=404, detail="Benchmark not found")
    return benchmark

@router.post("/{benchmark_id}/versions", response_model=BenchmarkVersionRead, status_code=status.HTTP_201_CREATED)
def create_benchmark_version(
    project_id: uuid.UUID,
    benchmark_id: uuid.UUID,
    data: BenchmarkVersionCreate,
    claims: TokenClaims = Depends(require_authenticated),
    authz_service: ProjectAuthorizationService = Depends(get_project_authz_service),
    benchmark_service: BenchmarkService = Depends(get_benchmark_service)
):
    """Append a new, immutable version to an existing benchmark."""
    authz_service.authorize_project_access(
        project_id=project_id, 
        user_id=claims.sub, 
        allowed_roles=[OrganizationRole.OWNER, OrganizationRole.ADMIN, OrganizationRole.MEMBER]
    )
    benchmark = benchmark_service.get_benchmark(benchmark_id)
    if not benchmark or benchmark.project_id != project_id:
        raise HTTPException(status_code=404, detail="Benchmark not found")

    try:
        return benchmark_service.create_benchmark_version(benchmark_id, claims.sub, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

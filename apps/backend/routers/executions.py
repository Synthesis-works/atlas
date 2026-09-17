from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, cast

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from apps.backend.authz import ProjectAuthorizationService, get_project_authz_service
from apps.backend.dependencies import TokenClaims, get_db_session, require_authenticated
from atlas_db.models.core import MembershipStatus, OrganizationMember, OrganizationRole, Project
from atlas_db.repositories.authoring import BenchmarkRepository
from packages.execution_engine.api.dtos import (
    ArtifactResponse,
    DispatchTargetResponse,
    ExecutionAttemptResponse,
    ExecutionCreateRequest,
    ExecutionListResponse,
    ExecutionResponse,
)
from packages.execution_engine.application.execution_app_service import ExecutionApplicationService
from packages.execution_engine.domain.models import Execution
from packages.execution_engine.domain.services import ExecutionService
from packages.execution_engine.persistence.repository import SqlAlchemyExecutionRepository
from services.search.service import resolve_accessible_project_ids
from apps.backend.worker.wake_client import notify_worker_wake

if TYPE_CHECKING:
    from atlas_db.models.execution import Execution as DBExecution

benchmark_executions_router = APIRouter(tags=["Executions"])
executions_router = APIRouter(tags=["Executions"])

READ_ROLES = [
    OrganizationRole.OWNER,
    OrganizationRole.ADMIN,
    OrganizationRole.MEMBER,
    OrganizationRole.VIEWER,
]

WRITE_ROLES = [
    OrganizationRole.OWNER,
    OrganizationRole.ADMIN,
    OrganizationRole.MEMBER,
]


def _resolve_execution_project_or_404(db: Session, execution_id: uuid.UUID) -> uuid.UUID:
    """Resolve an execution's owning project from the authoritative DB row.

    Raises 404 (without leaking existence) when the execution does not exist.
    """
    from atlas_db.models.execution import Execution as DBExecution

    db_item = db.query(DBExecution).filter(DBExecution.id == execution_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Execution not found")
    return cast("uuid.UUID", db_item.project_id)


def get_execution_service(db: Session = Depends(get_db_session)) -> ExecutionApplicationService:
    domain_service = ExecutionService()
    execution_repo = SqlAlchemyExecutionRepository(db)
    benchmark_repo = BenchmarkRepository(db)
    return ExecutionApplicationService(domain_service, execution_repo, benchmark_repo)


def map_db_item_to_response(db_item: DBExecution) -> ExecutionResponse:
    """Map an authoritative ``executions`` row to the API response.

    This is the single mapping used by both the list and single-get surfaces so
    they cannot drift.  Engine-internal aggregates (attempts/leases) are not part
    of the authoritative record and are intentionally not surfaced here.
    """
    return ExecutionResponse(
        id=db_item.id,
        benchmark_version_id=db_item.benchmark_version_id,
        status=db_item.status,
        target_model=db_item.target_model or "gemini-2.5-flash",
        completed_items=db_item.completed_items or 0,
        total_items=db_item.total_items or 1,
        started_at=db_item.started_at,
        completed_at=db_item.completed_at,
        created_at=db_item.created_at,
        updated_at=db_item.updated_at,
        created_by=db_item.submitted_by_id or uuid.uuid4(),
        max_retries=getattr(db_item, "max_retries", 3) or 3,
        attempts=[],
    )


def map_to_response(execution: Execution) -> ExecutionResponse:
    return ExecutionResponse(
        id=execution.id,
        benchmark_version_id=execution.benchmark_version_id,
        status=execution.status,
        target_model=getattr(execution, "target_model", "gemini-2.5-flash") or "gemini-2.5-flash",
        completed_items=getattr(execution, "completed_items", 0) or 0,
        total_items=getattr(execution, "total_items", 1) or 1,
        started_at=getattr(execution, "started_at", None),
        completed_at=getattr(execution, "completed_at", None),
        created_at=execution.created_at,
        updated_at=execution.updated_at,
        created_by=execution.created_by,
        max_retries=execution.max_retries,
        attempts=[
            ExecutionAttemptResponse(
                id=a.id,
                run_id=execution.id,
                task_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
                worker_id=a.lease.worker_id
                if a.lease
                else uuid.UUID("00000000-0000-0000-0000-000000000000"),
                status=str(a.status.value) if hasattr(a.status, "value") else str(a.status),
                started_at=a.started_at,
                finished_at=a.finished_at,
                error_message=a.error_message,
                artifacts=[
                    ArtifactResponse(id=art.id, type=art.type, storage_uri=art.storage_uri)
                    for art in a.artifacts
                ],
            )
            for a in execution.attempts
        ],
    )


@benchmark_executions_router.post(
    "/benchmarks/{benchmark_version_id}/executions",
    response_model=ExecutionResponse,
    status_code=201,
)
def create_execution(
    benchmark_version_id: uuid.UUID,
    payload: ExecutionCreateRequest = Body(default_factory=ExecutionCreateRequest),
    db: Session = Depends(get_db_session),
    service: ExecutionApplicationService = Depends(get_execution_service),
    project_authz: ProjectAuthorizationService = Depends(get_project_authz_service),
    claims: TokenClaims = Depends(require_authenticated),
):
    """
    Creates and queues a new execution for a specific benchmark version.

    Submission is authorized for published benchmarks (public artifacts) or for
    drafts owned by an organization the caller is an active member of.
    """
    from atlas_db.models.authoring import Benchmark, BenchmarkVersion

    benchmark_version = (
        db.query(BenchmarkVersion).filter(BenchmarkVersion.id == benchmark_version_id).first()
    )
    if not benchmark_version:
        raise HTTPException(
            status_code=404, detail=f"BenchmarkVersion {benchmark_version_id} not found"
        )

    benchmark = db.query(Benchmark).filter(Benchmark.id == benchmark_version.benchmark_id).first()
    if not benchmark:
        raise HTTPException(
            status_code=404, detail=f"Benchmark {benchmark_version.benchmark_id} not found"
        )

    if str(benchmark.status).lower() != "published":
        project_authz.authorize_project_access(
            project_id=benchmark.project_id,
            user_id=claims.sub,
            allowed_roles=[
                OrganizationRole.VIEWER,
                OrganizationRole.MEMBER,
                OrganizationRole.ADMIN,
                OrganizationRole.OWNER,
            ],
        )

    user_id = claims.sub

    target_model = (
        payload.target_model if payload and payload.target_model else "groq/llama-3.1-8b-instant"
    )

    dataset_version_id = getattr(payload, "dataset_version_id", None)
    if dataset_version_id is None and hasattr(benchmark_version, "primary_dataset_version_id"):
        raw_dv = benchmark_version.primary_dataset_version_id
        if isinstance(raw_dv, uuid.UUID):
            dataset_version_id = raw_dv
        elif isinstance(raw_dv, str):
            try:
                dataset_version_id = uuid.UUID(raw_dv)
            except ValueError:
                pass

    # Executions target a concrete, reproducible dataset version. Fabricating a
    # value (e.g. an arbitrary TestCase row or a random UUID) would silently run
    # against the wrong data or a non-existent version, so an unknown or missing
    # dataset version is rejected explicitly instead.
    if dataset_version_id is None:
        raise HTTPException(
            status_code=422,
            detail=(
                f"No dataset version is configured for benchmark_version "
                f"{benchmark_version_id}; provide or attach a dataset_version_id."
            ),
        )

    try:
        dataset_version_id = uuid.UUID(str(dataset_version_id))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid dataset_version_id: {dataset_version_id}",
        )

    linked_dataset_versions = {
        dv.id for dv in (benchmark_version.dataset_versions or []) if dv is not None
    }
    if linked_dataset_versions and dataset_version_id not in linked_dataset_versions:
        raise HTTPException(
            status_code=422,
            detail=(
                f"dataset_version_id {dataset_version_id} is not associated with "
                f"benchmark_version {benchmark_version_id}."
            ),
        )

    idempotency_key = getattr(payload, "idempotency_key", None)
    if idempotency_key:
        from atlas_db.models.execution import Execution as DBExecution

        existing = (
            db.query(DBExecution).filter(DBExecution.idempotency_key == idempotency_key).first()
        )
        if existing:
            # A matching submission was already accepted; resolve to that
            # execution record instead of queuing a duplicate.
            return map_db_item_to_response(existing)

    execution = service.submit_execution(
        benchmark_version_id=benchmark_version_id,
        dataset_version_id=dataset_version_id,
        submitted_by=user_id,
        target_model=target_model,
        idempotency_key=idempotency_key,
    )
    if hasattr(service, "execution_repo") and hasattr(service.execution_repo, "session"):
        service.execution_repo.session.commit()

    # Post-commit, fire-and-forget: nudge the Render worker so it wakes and
    # drains the outbox row committed above. Submission never fails on this.
    notify_worker_wake()

    return map_to_response(execution)


@executions_router.get("/executions/dispatch-targets", response_model=list[DispatchTargetResponse])
def list_dispatch_targets(
    db: Session = Depends(get_db_session),
    claims: TokenClaims = Depends(require_authenticated),
):
    """
    Lists benchmark versions that can be dispatched, each with a resolved dataset version.

    Published benchmarks are dispatchable by any authenticated user. Drafts are
    dispatchable only when the caller is an active member of the organization
    owning the benchmark's project.
    """
    from atlas_db.models.authoring import Benchmark, BenchmarkVersion

    active_org_ids = [
        row[0]
        for row in db.query(OrganizationMember.organization_id)
        .filter(
            OrganizationMember.user_id == claims.sub,
            OrganizationMember.status == MembershipStatus.ACTIVE,
        )
        .all()
    ]

    visible = or_(Benchmark.status == "published", Project.org_id.in_(active_org_ids))

    rows = (
        db.query(
            BenchmarkVersion.id,
            Benchmark.name,
            BenchmarkVersion.version_string,
            BenchmarkVersion.primary_dataset_version_id,
        )
        .join(Benchmark, Benchmark.id == BenchmarkVersion.benchmark_id)
        .join(Project, Project.id == Benchmark.project_id)
        .filter(visible)
        .order_by(Benchmark.name, BenchmarkVersion.created_at.desc())
        .all()
    )

    targets = []
    for bv_id, name, version_string, primary_dv in rows:
        # dataset_version_id is left unsatisfied (None) when the benchmark version
        # declares no primary dataset version, so an empty target surfaces the
        # misconfiguration instead of attaching an arbitrary unrelated dataset.
        targets.append(
            DispatchTargetResponse(
                benchmark_version_id=bv_id,
                benchmark_name=name,
                version_string=version_string,
                dataset_version_id=primary_dv,
            )
        )
    return targets


@executions_router.get("/executions/{execution_id}", response_model=ExecutionResponse)
def get_execution(
    execution_id: uuid.UUID,
    db: Session = Depends(get_db_session),
    authz_service: ProjectAuthorizationService = Depends(get_project_authz_service),
    claims: TokenClaims = Depends(require_authenticated),
):
    """
    Retrieves an execution from the authoritative ``executions`` record.

    The same row that feeds reports, listing, and the dashboard — guaranteeing
    status, progress, and timestamps cannot drift across surfaces. Access is
    scoped to the execution's owning project.
    """
    from atlas_db.models.execution import Execution as DBExecution

    project_id = _resolve_execution_project_or_404(db, execution_id)
    authz_service.authorize_project_access(
        project_id=project_id, user_id=claims.sub, allowed_roles=READ_ROLES
    )

    db_item = db.query(DBExecution).filter(DBExecution.id == execution_id).first()
    return map_db_item_to_response(db_item)


@executions_router.post("/executions/{execution_id}/cancel", response_model=ExecutionResponse)
def cancel_execution(
    execution_id: uuid.UUID,
    db: Session = Depends(get_db_session),
    service: ExecutionApplicationService = Depends(get_execution_service),
    authz_service: ProjectAuthorizationService = Depends(get_project_authz_service),
    claims: TokenClaims = Depends(require_authenticated),
):
    """
    Cancels a running or queued execution.

    Cancellation is a write operation scoped to the execution's owning project
    and requires a write role (OWNER/ADMIN/MEMBER); VIEWERs cannot cancel.
    """
    project_id = _resolve_execution_project_or_404(db, execution_id)
    authz_service.authorize_project_access(
        project_id=project_id, user_id=claims.sub, allowed_roles=WRITE_ROLES
    )
    execution = service.cancel_execution(execution_id)
    return map_to_response(execution)


@executions_router.get("/executions", response_model=ExecutionListResponse)
def list_executions(
    benchmark_version_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db_session),
    claims: TokenClaims = Depends(require_authenticated),
):
    """
    Lists executions directly from the database, scoped to the projects the
    caller is an active member of (membership -> org -> project). Empty
    membership yields no rows.
    """
    from atlas_db.models.execution import Execution as DBExecution

    accessible_ids = resolve_accessible_project_ids(db, user_id=claims.sub)

    query = db.query(DBExecution)
    if accessible_ids:
        query = query.filter(DBExecution.project_id.in_(accessible_ids))
    else:
        query = query.filter(DBExecution.project_id.in_([]))
    if benchmark_version_id:
        query = query.filter(DBExecution.benchmark_version_id == benchmark_version_id)
    if status:
        query = query.filter(DBExecution.status == status)

    total = query.count()
    db_items = query.order_by(DBExecution.created_at.desc()).offset(offset).limit(limit).all()

    return ExecutionListResponse(
        items=[map_db_item_to_response(db_item) for db_item in db_items],
        total=total,
    )

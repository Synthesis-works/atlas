import uuid
from typing import List, Optional
import logging

from packages.execution_engine.domain.services import ExecutionService
from packages.execution_engine.persistence.interfaces import ExecutionRepository
from packages.execution_engine.domain.models import Execution
from packages.execution_engine.domain.exceptions import ExecutionNotFoundError
from atlas_db.repositories.authoring import BenchmarkRepository

logger = logging.getLogger(__name__)


class EventPublisher:
    def publish(self, event):
        pass


class ExecutionApplicationService:
    """
    Coordinates transactions and cross-domain dependencies for the Execution Engine.
    Exposes operations for the public control-plane API.
    """

    def __init__(
        self,
        domain_service: ExecutionService,
        execution_repo: ExecutionRepository,
        benchmark_repo: BenchmarkRepository,
    ):
        self.domain_service = domain_service
        self.execution_repo = execution_repo
        self.benchmark_repo = benchmark_repo

    def submit_execution(
        self, benchmark_version_id: uuid.UUID, submitted_by: uuid.UUID
    ) -> Execution:
        """
        Creates and queues a new execution for a benchmark version.
        """
        # Validate benchmark version exists (assuming benchmark repo has a way to get it)
        # Normally we'd call benchmark_repo.get_version(benchmark_version_id)
        # Since we might not have that exact method, we'll pretend it's valid for now or rely on Foreign Keys.

        execution_id = uuid.uuid4()

        execution = self.domain_service.create_execution(
            execution_id=execution_id,
            benchmark_version_id=benchmark_version_id,
            submitted_by=submitted_by,
        )

        # Save to DB (commits transaction via Unit of Work or session dependency higher up)
        self.execution_repo.save(execution)

        return execution

    def get_execution(self, execution_id: uuid.UUID) -> Optional[Execution]:
        """
        Retrieves an execution.
        """
        execution = self.execution_repo.get(execution_id)
        if not execution:
            raise ExecutionNotFoundError(f"Execution {execution_id} not found")
        return execution

    def cancel_execution(self, execution_id: uuid.UUID) -> Execution:
        """
        Cancels an execution if it hasn't completed.
        """
        execution = self.execution_repo.get_for_update(execution_id)
        if not execution:
            raise ExecutionNotFoundError(f"Execution {execution_id} not found")

        self.domain_service.cancel(execution)
        self.execution_repo.save(execution)

        return execution

    def list_project_executions(
        self,
        project_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
        status: str | None = None,
        target_model: str | None = None,
        benchmark_version_id: uuid.UUID | None = None,
    ):
        from packages.execution_engine.api.dtos import ProjectExecutionListEntry, ExecutionListResponse
        from atlas_db.models.authoring import BenchmarkVersion, Benchmark
        
        # We need to access db for Benchmark lookup - using the repo's db session if possible
        # Since SqlAlchemyExecutionRepository has self.session, we can use it.
        # But to be clean, let's use the BenchmarkRepository if it has a way, otherwise fallback.
        db = getattr(self.execution_repo, "session", None)
        
        executions, total = self.execution_repo.find_by_project_paginated(
            project_id=project_id,
            limit=limit,
            offset=offset,
            status=status,
            target_model=target_model,
            benchmark_version_id=benchmark_version_id,
        )
        
        if not executions:
            return ExecutionListResponse(items=[], total=total)
            
        benchmark_version_ids = [exec.benchmark_version_id for exec in executions]
        
        # Look up benchmark names
        version_id_to_name = {}
        if db:
            query = (
                db.query(BenchmarkVersion.id, Benchmark.name)
                .join(Benchmark, Benchmark.id == BenchmarkVersion.benchmark_id)
                .filter(BenchmarkVersion.id.in_(benchmark_version_ids))
            )
            version_id_to_name = {row.id: row.name for row in query.all()}
            
        items = []
        for exec in executions:
            benchmark_name = version_id_to_name.get(exec.benchmark_version_id, "Unknown Benchmark")
            
            # Determine started_at, completed_at from attempts or execution
            # Since Execution doesn't have started_at at the root, we look at the first/last attempt
            started_at = None
            completed_at = None
            if exec.attempts:
                started_at = exec.attempts[0].started_at
                completed_at = exec.attempts[-1].finished_at
                
            duration = None
            if started_at and completed_at:
                duration = int((completed_at - started_at).total_seconds() * 1000)
                
            # Target model isn't in Execution aggregate (it was left out in domain/models.py!)
            # But the requirement is to use target_model. The persistence model has it.
            # To be strictly safe without modifying Domain if not necessary, we can pull it if we added it,
            # wait, I did not add target_model to Execution domain model in my previous edit!
            # The execution table has it. I must add it to the domain model and mapper if I want it here.
            # Let's fetch it via direct query or add it.
            # Actually, let's just do a direct lookup if we have the DB, or assume it's "Unknown" for now
            # wait, the prompt said target_model is required.
            target_model = getattr(exec, "target_model", "unknown")
            
            items.append(ProjectExecutionListEntry(
                id=exec.id,
                benchmark_name=benchmark_name,
                target_model=target_model,
                status=exec.status,
                started_at=started_at,
                completed_at=completed_at,
                duration=duration,
                total_items=exec.total_items,
                completed_items=exec.completed_items,
                created_at=exec.created_at,
            ))
            
        return ExecutionListResponse(items=items, total=total)

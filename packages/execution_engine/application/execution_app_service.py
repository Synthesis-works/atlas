import uuid
from typing import List, Optional
import logging

from packages.execution_engine.domain.services import ExecutionService
from packages.execution_engine.persistence.interfaces import ExecutionRepository
from packages.execution_engine.domain.models import Execution
from packages.execution_engine.domain.exceptions import ExecutionNotFoundError
from atlas_db.repositories.authoring import BenchmarkRepository
from atlas_db.models.authoring import BenchmarkVersion

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
        bv = self.benchmark_repo.db.query(BenchmarkVersion).get(benchmark_version_id)
        if not bv:
            raise ValueError(f"BenchmarkVersion {benchmark_version_id} not found")
        project_id = bv.benchmark.project_id

        execution_id = uuid.uuid4()

        execution = self.domain_service.create_execution(
            execution_id=execution_id,
            benchmark_version_id=benchmark_version_id,
            project_id=project_id,
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

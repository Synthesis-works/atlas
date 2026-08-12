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
        self,
        benchmark_version_id: uuid.UUID,
        submitted_by: uuid.UUID,
        target_model: str = "gemini-2.5-flash",
    ) -> Execution:
        """
        Creates and queues a new execution for a benchmark version.
        """
        execution_id = uuid.uuid4()

        execution = self.domain_service.create_execution(
            execution_id=execution_id,
            benchmark_version_id=benchmark_version_id,
            submitted_by=submitted_by,
            target_model=target_model,
        )

        # Save to DB
        self.execution_repo.save(execution)

        try:
            from atlas_db.models.execution import Execution as DBExecution, ExecutionStatus
            from datetime import datetime, UTC

            db_exec = DBExecution(
                id=execution.id,
                project_id=uuid.UUID("00000000-0000-0000-0000-000000000003"),
                benchmark_version_id=benchmark_version_id,
                submitted_by_id=submitted_by,
                target_model=target_model,
                status=ExecutionStatus.QUEUED,
                queued_at=datetime.now(UTC),
            )
            self.execution_repo.session.add(db_exec)
            self.execution_repo.session.commit()
        except Exception as err:
            logger.warning(f"DBExecution creation warning: {err}")

        try:
            from apps.backend.worker.tasks import run_execution_task

            run_execution_task.delay(str(execution.id))
        except Exception:
            pass

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

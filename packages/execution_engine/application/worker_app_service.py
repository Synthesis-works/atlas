import uuid
from typing import Optional, List
import logging
from datetime import timedelta

from packages.execution_engine.domain.services import ExecutionService
from packages.execution_engine.persistence.interfaces import ExecutionRepository
from packages.execution_engine.domain.models import Execution, Artifact, ArtifactType, ExecutionState, AttemptStatus
from packages.execution_engine.domain.exceptions import ExecutionNotFoundError, LeaseOwnershipError
from packages.execution_engine.api.worker_dtos import AcquireResponse, ArtifactDTO
from packages.execution_engine.application.execution_app_service import EventPublisher

logger = logging.getLogger(__name__)

class WorkerApplicationService:
    def __init__(self, 
                 domain_service: ExecutionService, 
                 execution_repo: ExecutionRepository,
                 event_publisher: EventPublisher = EventPublisher()):
        self.domain_service = domain_service
        self.execution_repo = execution_repo
        self.event_publisher = event_publisher

    def acquire_work(self, worker_id: uuid.UUID) -> Optional[AcquireResponse]:
        """
        Polls for schedulable work. If found, grants a lease and returns a LeaseGrant.
        """
        executions = self.execution_repo.find_schedulable(limit=1)
        if not executions:
            return None
            
        execution = executions[0]
        
        # Domain logic validates and sets up the lease natively
        self.domain_service.acquire_lease(execution, worker_id, lease_duration_seconds=300)
        self.domain_service.start_execution(execution, worker_id)
        
        # Save to persist lock
        self.execution_repo.save(execution)
        
        for event in execution.pull_events():
            self.event_publisher.publish(event)
            
        attempt = execution.current_attempt
        if not attempt or not attempt.lease:
            raise RuntimeError("Lease was not acquired correctly.")

        return AcquireResponse(
            lease_id=attempt.lease.id,
            execution_id=execution.id,
            attempt_id=attempt.id,
            heartbeat_interval_seconds=60,
            lease_duration_seconds=300,
            benchmark_version_id=execution.benchmark_version_id
        )

    def heartbeat(self, execution_id: uuid.UUID, worker_id: uuid.UUID) -> str:
        """
        Extends the lease if the worker still holds it.
        Returns the new ISO expiration string.
        """
        execution = self.execution_repo.get_for_update(execution_id)
        if not execution:
            raise ExecutionNotFoundError(f"Execution {execution_id} not found")
            
        attempt = execution.current_attempt
        if not attempt or not attempt.lease:
            raise LeaseOwnershipError("No active lease exists for this execution.")
            
        if attempt.lease.worker_id != worker_id:
            raise LeaseOwnershipError("Worker does not own the active lease.")
            
        if attempt.lease.expires_at <= self.domain_service.clock.now():
            raise LeaseOwnershipError("Lease has already expired.")
            
        # Renew lease
        attempt.lease.expires_at = self.domain_service.clock.now() + timedelta(seconds=300)
        
        self.execution_repo.save(execution)
        return attempt.lease.expires_at.isoformat()

    def complete_success(self, execution_id: uuid.UUID, worker_id: uuid.UUID, artifacts: List[ArtifactDTO]) -> None:
        """
        Atomically processes a successful execution completion.
        """
        execution = self.execution_repo.get_for_update(execution_id)
        if not execution:
            raise ExecutionNotFoundError(f"Execution {execution_id} not found")

        # Idempotency check: If already completed successfully by this worker, ignore
        if execution.status == ExecutionState.COMPLETED:
            # Note: Strict protocol might verify if the current worker was the one who completed it.
            # But domain `complete` handles idempotency.
            return
            
        attempt = execution.current_attempt
        if not attempt or not attempt.lease or attempt.lease.worker_id != worker_id:
            raise LeaseOwnershipError("Worker does not hold the active lease.")
            
        if attempt.lease.expires_at <= self.domain_service.clock.now():
            raise LeaseOwnershipError("Lease has expired. Cannot complete.")

        for art_dto in artifacts:
            attempt.add_artifact(Artifact(
                id=uuid.uuid4(),
                attempt_id=attempt.id,
                type=art_dto.type,
                storage_uri=art_dto.storage_uri
            ))

        self.domain_service.complete(execution, worker_id)
        self.execution_repo.save(execution)
        
        for event in execution.pull_events():
            self.event_publisher.publish(event)

    def complete_failure(self, execution_id: uuid.UUID, worker_id: uuid.UUID, error_message: str, artifacts: List[ArtifactDTO]) -> None:
        """
        Atomically processes a failed execution completion.
        """
        execution = self.execution_repo.get_for_update(execution_id)
        if not execution:
            raise ExecutionNotFoundError(f"Execution {execution_id} not found")

        if execution.status in (ExecutionState.FAILED, ExecutionState.RETRYING):
            return

        attempt = execution.current_attempt
        if not attempt or not attempt.lease or attempt.lease.worker_id != worker_id:
            raise LeaseOwnershipError("Worker does not hold the active lease.")
            
        if attempt.lease.expires_at <= self.domain_service.clock.now():
            raise LeaseOwnershipError("Lease has expired. Cannot fail.")

        for art_dto in artifacts:
            attempt.add_artifact(Artifact(
                id=uuid.uuid4(),
                attempt_id=attempt.id,
                type=art_dto.type,
                storage_uri=art_dto.storage_uri
            ))

        self.domain_service.fail(execution, error_message=error_message, worker_id=worker_id)
        self.execution_repo.save(execution)
        
        for event in execution.pull_events():
            self.event_publisher.publish(event)

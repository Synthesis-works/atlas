import logging
from typing import List
from sqlalchemy.orm import Session

from packages.execution_engine.domain.services import ExecutionService
from packages.execution_engine.persistence.interfaces import ExecutionRepository
from packages.execution_engine.application.interfaces import EventPublisher

logger = logging.getLogger(__name__)

class SchedulerService:
    """
    Background orchestrator responsible for Sweeping expired leases.
    """
    def __init__(self, 
                 domain_service: ExecutionService,
                 execution_repo: ExecutionRepository,
                 event_publisher: EventPublisher):
        self.domain_service = domain_service
        self.execution_repo = execution_repo
        self.event_publisher = event_publisher

    def sweep_expired_leases(self, limit: int = 50) -> int:
        """
        Detects expired leases and expires them natively via the domain service.
        Uses best-effort independent batching: if one execution fails to process,
        it moves on to the next.
        Returns the number of leases successfully swept.
        """
        swept_count = 0
        
        # Pull executions with expired active attempts (SKIP LOCKED)
        try:
            executions = self.execution_repo.find_expired_active_attempts(limit=limit)
        except Exception as e:
            logger.error(f"Failed to query expired leases: {e}")
            return 0
            
        for execution in executions:
            try:
                # Expire the lease. The domain decides if it is a retry or failure.
                self.domain_service.expire_lease(execution)
                
                # Persist the state transition
                self.execution_repo.save(execution)
                
                # Pull events (preserving causal order)
                events = execution.pull_events()
                
                # Note: Publish failure does not roll back the DB commit in this model.
                # In a robust system, an outbox pattern should be used.
                try:
                    self.event_publisher.publish(events)
                except Exception as e:
                    logger.error(f"Failed to publish events for execution {execution.id}: {e}")
                    
                swept_count += 1
            except Exception as e:
                logger.error(f"Failed to process expired lease for execution {execution.id}: {e}")
                # Continue with the next execution
                continue
                
        return swept_count

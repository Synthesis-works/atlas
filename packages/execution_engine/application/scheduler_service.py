import logging
from typing import List
from sqlalchemy.orm import Session

from packages.execution_engine.domain.services import ExecutionService
from packages.execution_engine.persistence.interfaces import ExecutionRepository
from packages.execution_engine.application.interfaces import EventPublisher
from apps.backend.core.telemetry import (
    set_correlation_id, set_trace_id, generate_uuidv7, get_logger
)

logger = get_logger("SCHEDULER")

class SchedulerService:
    """
    Background orchestrator responsible for Sweeping expired leases.
    """
    def __init__(self, 
                 domain_service: ExecutionService,
                 execution_repo: ExecutionRepository):
        self.domain_service = domain_service
        self.execution_repo = execution_repo

    def sweep_expired_leases(self, limit: int = 50) -> int:
        """
        Detects expired leases and expires them natively via the domain service.
        Uses best-effort independent batching: if one execution fails to process,
        it moves on to the next.
        Returns the number of leases successfully swept.
        """
        # Generate a correlation ID for this entire scheduler sweep
        sweep_correlation_id = generate_uuidv7()
        set_correlation_id(sweep_correlation_id)
        
        swept_count = 0
        
        # Pull executions with expired active attempts (SKIP LOCKED)
        try:
            executions = self.execution_repo.find_expired_active_attempts(limit=limit)
        except Exception as e:
            logger.error("Failed to query expired leases", exc_info=True)
            return 0
            
        for execution in executions:
            # Derive a child context for this specific execution
            set_trace_id(generate_uuidv7())
            
            try:
                # Expire the lease. The domain decides if it is a retry or failure.
                self.domain_service.expire_lease(execution)
                
                # Persist the state transition (and outbox events)
                self.execution_repo.save(execution)
                
                swept_count += 1
            except Exception as e:
                logger.error(f"Failed to process expired lease for execution {execution.id}", exc_info=True)
                # Continue with the next execution
                continue
                
        return swept_count

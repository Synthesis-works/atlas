import logging
from .bus import (
    ExecutionEventBus, 
    ExecutionEvent, 
    ExecutionCompleted, 
    ExecutionStarted, 
    ExecutionFailed, 
    ExecutionCancelled
)

logger = logging.getLogger(__name__)

class CeleryExecutionEventBus(ExecutionEventBus):
    """
    Concrete implementation of Event Bus that enqueues downstream Celery tasks.
    """
    def emit(self, event: ExecutionEvent) -> None:
        logger.info(f"Event emitted: {event.__class__.__name__} for execution {event.execution_id}")
        
        if isinstance(event, ExecutionCompleted):
            # Enqueue the evaluation service downstream
            from apps.backend.worker.tasks import run_evaluation_task
            logger.info(f"Dispatching Evaluation Task for execution {event.execution_id}")
            run_evaluation_task.delay(str(event.execution_id), correlation_id=event.correlation_id)
        
        elif isinstance(event, ExecutionStarted):
            pass # Hook for future notifications/dashboards
            
        elif isinstance(event, ExecutionFailed):
            pass # Hook for future alerts
            
        elif isinstance(event, ExecutionCancelled):
            pass # Hook for cleanup or metrics

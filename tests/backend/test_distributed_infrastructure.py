import uuid
from unittest.mock import patch

from apps.backend.events.bus import ExecutionCompleted
from apps.backend.events.celery_bus import CeleryExecutionEventBus
from apps.backend.worker.celery_app import celery_app
from apps.backend.worker.tasks import run_evaluation_task

# Force Celery eager mode for tests just to be safe
celery_app.conf.update(task_always_eager=True)


def test_event_bus_dispatches_evaluation_task():
    """
    Test that CeleryExecutionEventBus.emit(ExecutionCompleted) actually
    enqueues the evaluation task.
    """
    execution_id = uuid.uuid4()
    bus = CeleryExecutionEventBus()
    event = ExecutionCompleted(
        execution_id=execution_id,
        event_time="2024-01-01T00:00:00Z",
        aggregate_id=str(execution_id),
        correlation_id="test",
    )

    with patch("apps.backend.worker.tasks.run_evaluation_task.delay") as mock_delay:
        bus.emit(event)
        mock_delay.assert_called_once_with(str(execution_id), "test")


@patch("apps.backend.services.evaluation.EvaluationService.evaluate_execution")
def test_evaluation_task(mock_evaluate):
    """
    Test that the celery evaluation task correctly instantiates
    the service and calls evaluate_execution.
    """
    execution_id = uuid.uuid4()

    # Run synchronously
    run_evaluation_task.apply(args=(str(execution_id),))

    # Verify it delegates
    mock_evaluate.assert_called_once_with(execution_id, force=False)

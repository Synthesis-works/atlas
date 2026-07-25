import uuid
from unittest.mock import patch

from apps.backend.worker.celery_app import celery_app
from apps.backend.worker.tasks import run_execution_task

# Force Celery eager mode for tests just to be safe
celery_app.conf.update(task_always_eager=True)


@patch("apps.backend.worker.tasks.ExecutionWorker")
@patch("apps.backend.worker.tasks.SessionLocal")
def test_run_execution_task(mock_session_local, mock_execution_worker):
    """
    Test that the celery execution task correctly instantiates
    the worker and calls process.
    """
    execution_id = uuid.uuid4()

    # Call directly bypassing celery backend
    run_execution_task(str(execution_id))

    # Verify it delegates
    mock_execution_worker.return_value.process.assert_called_once_with(execution_id, correlation_id=None)

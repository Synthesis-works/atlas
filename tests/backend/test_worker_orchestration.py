import uuid
from unittest.mock import Mock, patch

from atlas_db.models.execution import ExecutionStatus
from sqlalchemy.orm import Session

from apps.backend.worker.execution_runner import ExecutionRunner
from apps.backend.worker.execution_worker import ExecutionWorker


def test_execution_runner_success():
    db = Mock(spec=Session)
    runner = ExecutionRunner(db)

    # Mock data
    execution = Mock()
    execution.id = uuid.uuid4()
    execution.benchmark_version_id = uuid.uuid4()
    execution.target_model = "mock"
    execution.cancellation_requested = False

    mock_test_case = Mock()
    mock_test_case.id = uuid.uuid4()
    mock_test_case.input_data = {"text": "hello"}

    mock_prompt = Mock()
    mock_prompt.template = "Translate {text}"

    mock_task = Mock()
    mock_task.prompts = [mock_prompt]
    mock_task.test_cases = [mock_test_case]

    db.query.return_value.filter.return_value.all.return_value = [mock_task]

    # Run
    outputs = runner.run(execution)

    assert len(outputs) == 1
    output = outputs[0]
    assert output.execution_id == execution.id
    assert output.test_case_id == mock_test_case.id
    assert output.raw_output == "mocked_output"
    assert output.tokens_used == 10


def test_execution_worker_success():
    db = Mock(spec=Session)
    worker = ExecutionWorker(db)

    execution = Mock()
    execution.id = uuid.uuid4()
    execution.status = ExecutionStatus.QUEUED
    execution.cancellation_requested = False

    # Mock db queries
    db.query.return_value.filter.return_value.first.return_value = execution

    with patch.object(ExecutionRunner, "run") as mock_run:
        mock_output = Mock()
        mock_run.return_value = [mock_output]

        with patch(
            "apps.backend.worker.execution_worker.CeleryExecutionEventBus.emit"
        ) as mock_emit:
            worker.process(execution.id)

            # Verify status transitions
            assert execution.status == ExecutionStatus.COMPLETED

            # Verify runner was called
            mock_run.assert_called_once_with(execution)

            # Verify persistence
            db.add_all.assert_called_once_with([mock_output])
            assert db.commit.call_count >= 2

            # Verify event was emitted
            assert mock_emit.called


def test_execution_worker_failure_skips_evaluation():
    db = Mock(spec=Session)
    worker = ExecutionWorker(db)

    execution = Mock()
    execution.id = uuid.uuid4()
    execution.status = ExecutionStatus.QUEUED
    execution.cancellation_requested = False

    # db returns execution correctly
    db.query.return_value.filter.return_value.first.return_value = execution

    with patch.object(ExecutionRunner, "run") as mock_run:
        mock_run.side_effect = Exception("Runner crashed")

        with patch(
            "apps.backend.worker.execution_worker.CeleryExecutionEventBus.emit"
        ) as mock_emit:
            worker.process(execution.id)

            # Verify status is FAILED
            assert execution.status == ExecutionStatus.FAILED

            # Verify db rolled back before failing
            db.rollback.assert_called_once()

            # Verify event emitted
            assert mock_emit.called

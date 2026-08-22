import uuid
from unittest.mock import Mock, patch, MagicMock, AsyncMock

from atlas_db.models.execution import ExecutionStatus, AttemptStatus
from sqlalchemy.orm import Session

from apps.backend.worker.execution_runner import ExecutionRunner
from apps.backend.worker.execution_worker import ExecutionWorker
from apps.backend.worker.executor_init import init_executors
from packages.execution_engine.application.executor import (
    ExecutionContext,
    ExecutionProvenance,
    ExecutionResult,
)


# Initialize executors for tests
init_executors()


def test_execution_runner_success():
    db = Mock(spec=Session)
    runner = ExecutionRunner(db)

    # Mock data
    execution = Mock()
    execution.id = uuid.uuid4()
    execution.benchmark_version_id = uuid.uuid4()
    execution.dataset_version_id = uuid.uuid4()
    execution.target_model = "mock"
    execution.cancellation_requested = False
    execution.execution_config = {}
    execution.attempts = []  # New: attempts relationship

    mock_test_case = Mock()
    mock_test_case.id = uuid.uuid4()
    mock_test_case.input_data = {"text": "hello"}

    mock_prompt = Mock()
    mock_prompt.template = "Translate {text}"

    mock_task = Mock()
    mock_task.prompts = [mock_prompt]
    mock_test_case.task = mock_task

    # run() issues two queries: TestCase lookup, then existing ModelOutput ids
    # (M-3 duplicate guard). Configure them separately.
    tc_query = Mock()
    tc_query.filter.return_value.all.return_value = [mock_test_case]
    mo_query = Mock()
    mo_query.filter.return_value.all.return_value = []  # no outputs persisted yet
    db.query.side_effect = [tc_query, mo_query]

    # Mock the executor to return a successful result
    mock_output = Mock()
    mock_output.execution_id = execution.id
    mock_output.test_case_id = mock_test_case.id
    mock_output.raw_output = "mocked_output"
    mock_output.tokens_used = 10
    mock_output.duration_ms = 100

    mock_provenance = ExecutionProvenance(
        executor_type="local",
        termination_reason="completed",
    )
    mock_result = ExecutionResult(
        provenance=mock_provenance,
        model_outputs=[
            {
                "execution_id": str(execution.id),
                "test_case_id": str(mock_test_case.id),
                "raw_output": "mocked_output",
                "duration_ms": 100,
                "tokens_used": 10,
            }
        ],
    )

    with patch.object(runner, "_get_executor") as mock_get_executor:
        mock_executor = Mock()
        mock_executor.executor_type = "local"
        mock_executor.execute = AsyncMock(return_value=mock_result)
        mock_get_executor.return_value = mock_executor

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

    # Mock db queries (called for Execution then ExecutionModel)
    db.query.return_value.filter.return_value.first.side_effect = [
        execution,
        None,
        execution,
        None,
        execution,
        None,
    ]

    mock_output = Mock()
    mock_output.execution_id = execution.id
    mock_output.test_case_id = uuid.uuid4()
    mock_output.raw_output = "mocked_output"
    mock_output.tokens_used = 10
    mock_output.duration_ms = 100

    with patch.object(ExecutionRunner, "run") as mock_run:
        mock_run.return_value = [mock_output]

        with patch(
            "apps.backend.worker.execution_worker.CeleryExecutionEventBus.emit"
        ) as mock_emit:
            worker.process(execution.id)

            # Verify status transitions
            assert execution.status == ExecutionStatus.COMPLETED

            # Verify runner was called
            mock_run.assert_called_once_with(execution)

            # Verify persistence - runner does its own db.add calls, worker does final commit
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
    db.query.return_value.filter.return_value.first.side_effect = [
        execution,
        None,
        execution,
        None,
        execution,
        None,
    ]

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

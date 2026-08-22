"""Regression tests for M-1 (provenance survives failure) and M-3 (no duplicate outputs)."""

import uuid
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from apps.backend.worker.execution_runner import ExecutionRunner
from packages.execution_engine.application import executor as executor_mod
from packages.execution_engine.application.executor import (
    ExecutionContext,
    ExecutionProvenance,
    ExecutorTimeout,
)


@pytest.fixture()
def registry_with(monkeypatch):
    """Register a stub executor under an isolated registry dict."""

    def _install(executor):
        monkeypatch.setattr(executor_mod.executor_registry, "_executors", {"docker": executor})
        return executor

    return _install


def _execution_mock(tc_id: UUID):
    execution = Mock()
    execution.id = uuid.uuid4()
    execution.benchmark_version_id = uuid.uuid4()
    execution.dataset_version_id = uuid.uuid4()
    execution.target_model = "mock"
    execution.cancellation_requested = False
    execution.execution_config = {}
    execution.attempts = []
    execution.status = None

    tc = Mock()
    tc.id = tc_id
    tc.input_data = {"text": "hello"}
    prompt = Mock()
    prompt.template = "Echo {text}"
    task = Mock()
    task.prompts = [prompt]
    tc.task = task

    return execution, tc


def _context_stub():
    return ExecutionContext(
        execution_id=uuid.uuid4(),
        attempt_id=uuid.uuid4(),
        attempt_number=1,
        target_model="mock",
        benchmark_version_id=uuid.uuid4(),
        dataset_version_id=uuid.uuid4(),
        test_cases=[],
        execution_config={},
    )


class TestProvenanceSurvivesTimeout:
    def test_timeout_provenance_recorded_on_attempt(self, registry_with):
        """M-1: a raised ExecutorTimeout carrying provenance must populate the
        attempt row with timed_out/termination_reason/container telemetry."""
        tc_id = uuid.uuid4()
        execution, tc = _execution_mock(tc_id)

        db = Mock(spec=Session)
        # Query order: TestCase lookup, github_actions attempt adoption (none),
        # then existing ModelOutput ids.
        tc_query = Mock()
        tc_query.filter.return_value.all.return_value = [tc]
        adopt_query = Mock()
        adopt_query.filter.return_value.order_by.return_value.first.return_value = None
        mo_query = Mock()
        mo_query.filter.return_value.all.return_value = []

        prov = ExecutionProvenance(
            executor_type="docker",
            container_id="abc123def456",
            image_ref="atlas-benchmark-runner:sha-x",
            exit_code=137,
            termination_reason="timeout",
            timed_out=True,
            oom_killed=False,
        )
        exc = ExecutorTimeout("Execution timed out after 30s")
        exc.provenance = prov  # type: ignore[attr-defined]

        failing_executor = Mock()
        failing_executor.executor_type = "docker"
        failing_executor.execute = AsyncMock(side_effect=exc)
        registry_with(failing_executor)

        db.query.side_effect = [tc_query, adopt_query]

        runner = ExecutionRunner(db, executor_type="docker")
        with pytest.raises(ExecutorTimeout):
            runner.run(execution)

        # The runner persists the attempt via db.add; capture it there.
        added = [c.args[0] for c in db.add.call_args_list]
        attempt = next(a for a in added if type(a).__name__ == "ExecutionAttempt")
        assert attempt.status == "TIMED_OUT"
        assert attempt.timed_out is True
        assert attempt.termination_reason == "timeout"
        assert attempt.container_id == "abc123def456"
        assert attempt.exit_code == 137


class TestNoDuplicateOutputs:
    def test_existing_outputs_are_skipped(self, registry_with):
        """M-3: outputs already persisted for this execution are not re-inserted."""
        tc_id = uuid.uuid4()
        execution, tc = _execution_mock(tc_id)

        db = Mock(spec=Session)
        # Query order: TestCase lookup, attempt adoption, ModelOutput ids.
        tc_query = Mock()
        tc_query.filter.return_value.all.return_value = [tc]
        adopt_query = Mock()
        adopt_query.filter.return_value.order_by.return_value.first.return_value = None
        mo_query = Mock()
        mo_query.filter.return_value.all.return_value = [(tc_id,)]  # already persisted
        db.query.side_effect = [tc_query, adopt_query, mo_query]

        ok_executor = Mock()
        ok_executor.executor_type = "docker"
        ok_executor.execute = AsyncMock(
            return_value=Mock(
                provenance=ExecutionProvenance(
                    executor_type="docker", termination_reason="completed"
                ),
                model_outputs=[
                    {
                        "test_case_id": str(tc_id),
                        "raw_output": "mocked_output",
                        "duration_ms": 5,
                        "tokens_used": 10,
                    }
                ],
                error_message=None,
            )
        )
        registry_with(ok_executor)

        runner = ExecutionRunner(db, executor_type="docker")
        outputs = runner.run(execution)

        assert outputs == []  # skipped, not duplicated
        added_types = [type(c.args[0]).__name__ for c in db.add.call_args_list]
        assert "ModelOutput" not in added_types  # only the ExecutionAttempt was added


class TestGithubActionsAttemptAdoption:
    def test_runner_adopts_claimed_github_actions_attempt(self, registry_with):
        """Under the GH Actions backend the runner must reuse the
        dispatcher-created/claimed attempt instead of creating a second one
        (the partial unique index forbids two active attempts)."""
        tc_id = uuid.uuid4()
        execution, tc = _execution_mock(tc_id)

        claimed_attempt = Mock()
        claimed_attempt.executor_type = "github_actions"
        claimed_attempt.status = "CONTAINER_CREATED"

        db = Mock(spec=Session)
        tc_query = Mock()
        tc_query.filter.return_value.all.return_value = [tc]
        adopt_query = Mock()
        (adopt_query.filter.return_value.order_by.return_value.first.return_value) = claimed_attempt
        mo_query = Mock()
        mo_query.filter.return_value.all.return_value = []
        db.query.side_effect = [tc_query, adopt_query, mo_query]

        ok_executor = Mock()
        ok_executor.executor_type = "docker"
        ok_executor.execute = AsyncMock(
            return_value=Mock(
                provenance=ExecutionProvenance(
                    executor_type="docker", termination_reason="completed"
                ),
                model_outputs=[
                    {
                        "test_case_id": str(tc_id),
                        "raw_output": "mocked_output",
                        "duration_ms": 5,
                        "tokens_used": 10,
                    }
                ],
                error_message=None,
            )
        )
        registry_with(ok_executor)

        runner = ExecutionRunner(db, executor_type="docker")
        runner.run(execution)

        # Adopted attempt carried through the whole lifecycle to completion;
        # no second ExecutionAttempt was ever created.
        assert claimed_attempt.status == "COMPLETED"
        added_types = [type(c.args[0]).__name__ for c in db.add.call_args_list]
        assert "ExecutionAttempt" not in added_types

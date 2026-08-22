import logging
import time
import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from atlas_db.models.execution import (
    Execution,
    ExecutionAttempt,
    ExecutionStatus,
    ModelOutput,
    AttemptStatus,
)
from atlas_db.models.tasks import TestCase
from sqlalchemy.orm import Session

from apps.backend.adapters.factory import AdapterFactory
from apps.backend.worker.prompt_resolver import PromptResolver
from packages.execution_engine.application.executor import (
    ExecutionContext,
    ExecutorUnavailable,
    executor_registry,
)
from packages.execution_engine.application.local_executor import LocalExecutor

logger = logging.getLogger(__name__)


class ExecutionRunner:
    def __init__(self, db: Session, executor_type: str | None = None):
        self.db = db
        self._executor_type = executor_type

    def _get_executor(self):
        if self._executor_type:
            executor = executor_registry.get(self._executor_type)
            if executor is None:
                # An explicitly requested executor type that is not registered is a
                # configuration error. Never silently fall back to another executor.
                raise ExecutorUnavailable(
                    f"Executor type '{self._executor_type}' was explicitly requested but "
                    f"is not registered. Registered: {executor_registry.registered_types}"
                )
            return executor
        return executor_registry.get_default()

    def run(self, execution: Execution) -> list[ModelOutput]:
        """
        Executes the tasks in a benchmark against a model using the configured executor.
        Returns a list of uncommitted ModelOutput objects.
        """
        from atlas_db.models.execution import ExecutionAttempt

        executor = self._get_executor()
        if not executor:
            raise RuntimeError("No executor available. Configure at least one executor.")

        dv_id = execution.dataset_version_id
        if not dv_id:
            logger.error(f"Execution {execution.id} lacks dataset_version_id. Failing explicitly.")
            raise ValueError(
                f"Execution {execution.id} lacks dataset_version_id. Execution isolated runs require a dataset_version_id."
            )

        # Load isolated test cases for the exact dataset version
        test_cases = self.db.query(TestCase).filter(TestCase.dataset_version_id == dv_id).all()

        if not test_cases:
            logger.error(f"No test cases found for dataset_version_id {dv_id}")
            raise ValueError(
                f"No test cases found for dataset_version_id {dv_id} in execution {execution.id}"
            )

        # Calculate total test cases for progress tracking
        execution.total_items = len(test_cases)
        execution.completed_items = 0
        self.db.commit()

        # Prepare test cases data for executor
        test_cases_data = []
        for tc in test_cases:
            test_cases_data.append(
                {
                    "id": str(tc.id),
                    "input_data": tc.input_data,
                    "task": {
                        "prompts": [{"template": p.template} for p in tc.task.prompts]
                        if tc.task and tc.task.prompts
                        else []
                    },
                }
            )

        # Create execution attempt record. When running under the GitHub
        # Actions backend, ADOPT the dispatcher-created github_actions attempt
        # instead of creating a second one: the partial unique index
        # (uq_active_attempt_per_execution) forbids two active attempts, and
        # a single attempt keeps dispatch->run->container provenance unified.
        adopted = (
            self.db.query(ExecutionAttempt)
            .filter(
                ExecutionAttempt.execution_id == execution.id,
                ExecutionAttempt.executor_type == "github_actions",
                ExecutionAttempt.status.in_(
                    [AttemptStatus.PENDING, AttemptStatus.CONTAINER_CREATED]
                ),
            )
            .order_by(ExecutionAttempt.attempt_number.desc())
            .first()
        )
        if adopted is not None:
            attempt = adopted
            attempt.status = AttemptStatus.RUNNING
        else:
            attempt_number = len(execution.attempts) + 1
            attempt = ExecutionAttempt(
                execution_id=execution.id,
                attempt_number=attempt_number,
                status=AttemptStatus.PENDING,
                executor_type=executor.executor_type,
                trace_id=str(uuid.uuid4()),
            )
            self.db.add(attempt)
        self.db.commit()
        self.db.refresh(attempt)
        attempt_number = attempt.attempt_number

        # Build execution context
        context = ExecutionContext(
            execution_id=execution.id,
            attempt_id=attempt.id,
            attempt_number=attempt_number,
            target_model=execution.target_model,
            benchmark_version_id=execution.benchmark_version_id,
            dataset_version_id=dv_id,
            test_cases=test_cases_data,
            execution_config=execution.execution_config or {},
            correlation_id=attempt.trace_id,
            trace_id=attempt.trace_id,
        )

        # Update attempt status to RUNNING
        attempt.status = AttemptStatus.RUNNING
        attempt.started_at = datetime.now(UTC)
        self.db.commit()

        # Execute via executor
        try:
            import asyncio

            result = asyncio.run(executor.execute(context))

            # Update attempt with provenance
            prov = result.provenance
            attempt.status = (
                AttemptStatus.COMPLETED
                if prov.termination_reason == "completed"
                else AttemptStatus.FAILED
            )
            attempt.finished_at = prov.finished_at or datetime.now(UTC)
            attempt.container_id = prov.container_id
            attempt.image_ref = prov.image_ref
            attempt.image_digest = prov.image_digest
            attempt.exit_code = prov.exit_code
            attempt.termination_reason = prov.termination_reason
            attempt.oom_killed = prov.oom_killed
            attempt.timed_out = prov.timed_out
            attempt.cpu_seconds = prov.cpu_seconds
            attempt.peak_memory_bytes = prov.peak_memory_bytes
            attempt.pids_peak = prov.pids_peak
            attempt.network_rx_bytes = prov.network_rx_bytes
            attempt.network_tx_bytes = prov.network_tx_bytes
            attempt.error_message = result.error_message

            self.db.commit()

            # Convert executor results to ModelOutput objects.
            # M-3: retries/duplicate dispatches must not duplicate rows; skip
            # test cases that already have a persisted output for this execution.
            existing_tc_ids = {
                str(row[0])
                for row in self.db.query(ModelOutput.test_case_id)
                .filter(ModelOutput.execution_id == execution.id)
                .all()
            }
            outputs: list[ModelOutput] = []
            for out_data in result.model_outputs:
                if str(out_data["test_case_id"]) in existing_tc_ids:
                    continue
                output = ModelOutput(
                    execution_id=execution.id,
                    test_case_id=UUID(out_data["test_case_id"]),
                    raw_output=out_data["raw_output"],
                    duration_ms=out_data.get("duration_ms"),
                    tokens_used=out_data.get("tokens_used"),
                )
                outputs.append(output)
                self.db.add(output)

            # Update execution progress
            execution.completed_items = len(outputs)
            if prov.termination_reason == "completed":
                execution.status = ExecutionStatus.COMPLETED
            self.db.commit()

            return outputs

        except Exception as e:
            logger.exception(f"Execution {execution.id} attempt {attempt_number} failed: {e}")
            # M-1: executors attach their provenance to raised exceptions so
            # timeout/OOM classification and stats survive the failure path.
            prov = getattr(e, "provenance", None)
            attempt.status = (
                AttemptStatus.TIMED_OUT
                if getattr(prov, "timed_out", False)
                else AttemptStatus.FAILED
            )
            attempt.finished_at = getattr(prov, "finished_at", None) or datetime.now(UTC)
            if prov is not None:
                attempt.container_id = prov.container_id
                attempt.image_ref = prov.image_ref
                attempt.image_digest = prov.image_digest
                attempt.exit_code = prov.exit_code
                attempt.oom_killed = prov.oom_killed
                attempt.timed_out = prov.timed_out
                attempt.cpu_seconds = prov.cpu_seconds
                attempt.peak_memory_bytes = prov.peak_memory_bytes
                attempt.pids_peak = prov.pids_peak
                attempt.network_rx_bytes = prov.network_rx_bytes
                attempt.network_tx_bytes = prov.network_tx_bytes
                attempt.termination_reason = prov.termination_reason or "error"
                if not attempt.error_message:
                    attempt.error_message = prov.error_message
            else:
                attempt.termination_reason = "error"
            attempt.error_message = str(e)[:5000] or attempt.error_message
            self.db.commit()
            raise

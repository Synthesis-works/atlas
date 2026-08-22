import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from apps.backend.adapters.factory import AdapterFactory
from apps.backend.worker.prompt_resolver import PromptResolver
from atlas_db.models.execution import ModelOutput
from packages.execution_engine.application.executor import (
    ExecutionContext,
    ExecutionProvenance,
    ExecutionResult,
    Executor,
    ExecutorError,
    ExecutorTimeout,
)


class LocalExecutor(Executor):
    """Development-only executor that runs benchmark tasks inline in the worker process.
    
    This executor provides NO isolation. It is intended ONLY for local development
    and testing where Docker is not available. It MUST NOT be used in production.
    """

    @property
    def executor_type(self) -> str:
        return "local"

    async def is_available(self) -> bool:
        return True

    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        started_at = datetime.now(UTC)
        provenance = ExecutionProvenance(
            executor_type=self.executor_type,
            created_at=started_at,
            started_at=started_at,
            trace_id=context.trace_id,
            correlation_id=context.correlation_id,
            worker_id=context.worker_id,
        )

        try:
            adapter = AdapterFactory.get_adapter(context.target_model)
            resolver = PromptResolver()

            outputs_data: list[dict] = []

            for test_case in context.test_cases:
                task = test_case.get("task")
                if not task:
                    continue
                prompts = task.get("prompts", [])
                prompt_template = prompts[0].get("template", "{text}") if prompts else "{text}"

                hydrated_prompt = resolver.resolve(prompt_template, test_case.get("input_data", {}))

                prediction_result = adapter.predict(hydrated_prompt)

                output = ModelOutput(
                    execution_id=context.execution_id,
                    test_case_id=UUID(test_case["id"]),
                    raw_output=prediction_result.output_text,
                    duration_ms=prediction_result.latency_ms,
                    tokens_used=prediction_result.token_usage,
                )

                outputs_data.append({
                    "execution_id": str(context.execution_id),
                    "test_case_id": test_case["id"],
                    "raw_output": prediction_result.output_text,
                    "duration_ms": prediction_result.latency_ms,
                    "tokens_used": prediction_result.token_usage,
                })

            finished_at = datetime.now(UTC)
            provenance.finished_at = finished_at
            provenance.termination_reason = "completed"
            provenance.cpu_seconds = (finished_at - started_at).total_seconds()

            return ExecutionResult(
                provenance=provenance,
                model_outputs=outputs_data,
            )

        except Exception as e:
            finished_at = datetime.now(UTC)
            provenance.finished_at = finished_at
            provenance.termination_reason = "error"
            provenance.error_message = str(e)
            raise ExecutorError(f"Local execution failed: {e}") from e

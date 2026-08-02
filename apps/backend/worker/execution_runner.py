import logging
import time

from atlas_db.models.execution import Execution, ModelOutput
from atlas_db.models.tasks import Task
from sqlalchemy.orm import Session

from apps.backend.adapters.factory import AdapterFactory
from apps.backend.worker.prompt_resolver import PromptResolver

logger = logging.getLogger(__name__)


class ExecutionRunner:
    def __init__(self, db: Session):
        self.db = db

    def run(self, execution: Execution) -> list[ModelOutput]:
        """
        Executes the tasks in a benchmark against a model.
        Returns a list of uncommitted ModelOutput objects.
        """
        adapter = AdapterFactory.get_adapter(execution.target_model)
        resolver = PromptResolver()

        # Load tasks for the benchmark version
        tasks = (
            self.db.query(Task)
            .filter(Task.benchmark_version_id == execution.benchmark_version_id)
            .all()
        )

        # Calculate total test cases for progress tracking
        execution.total_items = sum(len(task.test_cases) for task in tasks)
        execution.completed_items = 0
        self.db.commit()

        outputs = []
        batch_size = 10
        batch_count = 0
        last_commit_time = time.time()

        for task in tasks:
            # Assume 1 prompt per task for this implementation.
            prompt = task.prompts[0] if task.prompts else None
            # If no prompt, fallback to a basic format that expects 'text'
            prompt_template = prompt.template if prompt else "{text}"

            for test_case in task.test_cases:
                # Cooperative cancellation check
                self.db.refresh(execution)
                if execution.cancellation_requested:
                    logger.info(f"Cancellation requested during Execution {execution.id}. Halting.")
                    return outputs

                # Hydrate prompt
                hydrated_prompt = resolver.resolve(prompt_template, test_case.input_data)

                # Invoke adapter
                prediction_result = adapter.predict(hydrated_prompt)

                # Build ModelOutput
                output = ModelOutput(
                    execution_id=execution.id,
                    test_case_id=test_case.id,
                    raw_output=prediction_result.output_text,
                    duration_ms=prediction_result.latency_ms,
                    tokens_used=prediction_result.token_usage,
                )
                outputs.append(output)
                self.db.add(output)

                # Progress batching
                execution.completed_items += 1
                batch_count += 1
                current_time = time.time()

                if batch_count >= batch_size or (current_time - last_commit_time) >= 5.0:
                    self.db.commit()
                    batch_count = 0
                    last_commit_time = current_time
                    logger.info(
                        f"Execution {execution.id} progress: {execution.completed_items}/{execution.total_items}"
                    )

        # Final commit
        if batch_count > 0:
            self.db.commit()

        return outputs

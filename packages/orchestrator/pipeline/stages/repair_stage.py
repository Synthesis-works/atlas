import time

from packages.orchestrator.agents.ollama_repair import OllamaRepairAgent
from packages.orchestrator.models import TaskRunResult, TaskRunState
from packages.orchestrator.pipeline.base import PipelineStage


class RepairStage(PipelineStage):
    """
    If a task failed during EXECUTION or EVALUATION, attempts to repair it using an agent.
    """

    def __init__(self, max_retries: int = 1):
        self.max_retries = max_retries
        self.agent = OllamaRepairAgent()

    def execute(self, context: dict, state: TaskRunResult) -> TaskRunResult:
        if (
            state.state != TaskRunState.FAILED
            and getattr(state, "evaluation_status", None) != "fail"
        ):
            return state

        retries = context.get("repair_retries", 0)
        job_config = context.get("job_config")
        if retries >= self.max_retries:
            return state

        print(
            f"[{state.task_id}] Attempting automatic repair (Retry {retries + 1}/{self.max_retries})..."
        )
        context["repair_retries"] = retries + 1

        # We need original prompt, code, and error
        err_msg = state.error_message or state.exception or state.stderr or "Unknown Error"

        start_time = time.time()
        repaired_code = self.agent.generate_repair(
            task_id=state.task_id,
            original_prompt=state.prompt or "",
            failed_code=state.extracted_code or "",
            error_message=err_msg,
            model=job_config.model,
        )
        latency = int((time.time() - start_time) * 1000)

        if not repaired_code:
            print(f"[{state.task_id}] Repair agent failed to generate a fix.")
            return state

        # Re-inject and revert state so it can be re-executed
        print(f"[{state.task_id}] Repair generated successfully. Re-queueing for execution.")
        state.extracted_code = repaired_code
        state.generation_latency_ms = (state.generation_latency_ms or 0) + latency
        state.state = TaskRunState.GENERATED
        state.error_message = None
        state.exception = None
        state.execution_status = None
        state.evaluation_status = None

        # Context flag to notify orchestrator that this needs a re-run
        context["needs_reexecution"] = True

        return state

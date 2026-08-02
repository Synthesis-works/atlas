from abc import ABC, abstractmethod
from datetime import UTC, datetime

from atlas_db.models.execution import AtlasRun, AtlasTask


class RecoveryAction:
    RETRY = "RETRY"
    FAIL_TASK = "FAIL_TASK"
    FAIL_RUN = "FAIL_RUN"
    SKIP = "SKIP"


class RecoveryDecisionPolicy(ABC):
    @abstractmethod
    def evaluate_task(self, task: AtlasTask, run: AtlasRun) -> str:
        """
        Evaluates what action should be taken for a failing/expired task.
        Returns one of the RecoveryAction constants.
        """
        pass


class RetryPolicy(RecoveryDecisionPolicy):
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

    def evaluate_task(self, task: AtlasTask, run: AtlasRun) -> str:
        if task.status.value in ["COMPLETED", "FAILED"]:
            return RecoveryAction.SKIP

        if task.attempt_number <= self.max_retries:
            return RecoveryAction.RETRY
        return RecoveryAction.FAIL_TASK


class TimeoutPolicy(RecoveryDecisionPolicy):
    def __init__(self, max_run_duration_seconds: int = 3600):
        self.max_duration = max_run_duration_seconds

    def evaluate_task(self, task: AtlasTask, run: AtlasRun) -> str:
        if task.status.value in ["COMPLETED", "FAILED"]:
            return RecoveryAction.SKIP

        if run.started_at:
            duration = (datetime.now(UTC) - run.started_at).total_seconds()
            if duration > self.max_duration:
                return RecoveryAction.FAIL_RUN

        return RecoveryAction.RETRY  # Fallback to retry if not timed out


class CompositeRecoveryPolicy(RecoveryDecisionPolicy):
    def __init__(self, policies: list[RecoveryDecisionPolicy]):
        self.policies = policies

    def evaluate_task(self, task: AtlasTask, run: AtlasRun) -> str:
        for policy in self.policies:
            action = policy.evaluate_task(task, run)
            if action != RecoveryAction.RETRY:
                return action
        return RecoveryAction.RETRY

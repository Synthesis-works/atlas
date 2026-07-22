from pydantic import UUID4, BaseModel


class SchedulingDecision(BaseModel):
    task_id: UUID4
    worker_id: UUID4
    policy: str
    priority: int


class SchedulerMetrics(BaseModel):
    tasks_examined: int = 0
    tasks_scheduled: int = 0
    policy_rejections: int = 0
    no_worker_available: int = 0
    failed_claim_attempts: int = 0

    def record_examined(self):
        self.tasks_examined += 1

    def record_scheduled(self):
        self.tasks_scheduled += 1

    def record_policy_rejection(self):
        self.policy_rejections += 1

    def record_no_worker(self):
        self.no_worker_available += 1

    def record_failed_claim(self):
        self.failed_claim_attempts += 1

    def summary(self) -> str:
        return (
            f"Scheduler Metrics -> "
            f"Examined: {self.tasks_examined}, "
            f"Scheduled: {self.tasks_scheduled}, "
            f"Policy Rejections: {self.policy_rejections}, "
            f"No Worker: {self.no_worker_available}, "
            f"Failed Claims: {self.failed_claim_attempts}"
        )

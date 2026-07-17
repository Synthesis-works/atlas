import sys
content = """
    def execute_recovery_decision(self, task_id: UUID) -> str:
        \"\"\"
        Evaluates the recovery policy for a failing task and executes the decision.
        \"\"\"
        task = self.db.query(AtlasTask).filter_by(id=task_id).with_for_update().one()
        run = self.db.query(AtlasRun).filter_by(id=task.atlas_run_id).with_for_update().one()
        
        if not self.recovery_policy:
            raise ValueError("No recovery policy configured.")
            
        action = self.recovery_policy.evaluate_task(task, run)
        
        if action == RecoveryAction.SKIP:
            self.event_publisher.publish_event(
                run_id=str(run.id),
                event_type=EventType.RECOVERY_SKIPPED,
                message="Recovery skipped by policy.",
                metadata={"task_id": str(task.id)}
            )
        elif action == RecoveryAction.RETRY:
            task.status = TaskStatus.QUEUED
            task.assigned_worker_id = None
            task.attempt_number += 1
            task.error_message = None
            task.error_code = None
            task.started_at = None
            task.claimed_at = None
            task.lease_expires_at = None
            
            self.event_publisher.publish_event(
                run_id=str(run.id),
                event_type=EventType.TASK_REQUEUED,
                message=f"Task requeued for attempt {task.attempt_number}",
                metadata={"task_id": str(task.id), "attempt": task.attempt_number}
            )
        elif action == RecoveryAction.FAIL_TASK:
            task.status = TaskStatus.FAILED
            run.running_tasks -= 1
            run.failed_tasks += 1
            self.event_publisher.publish_event(
                run_id=str(run.id),
                event_type=EventType.TASK_FAILED,
                message="Task failed permanently (retries exhausted).",
                metadata={"task_id": str(task.id)}
            )
            self._check_run_completion(run, datetime.now(timezone.utc))
        elif action == RecoveryAction.FAIL_RUN:
            run.status = RunStatus.FAILED
            run.completed_at = datetime.now(timezone.utc)
            task.status = TaskStatus.FAILED
            self.event_publisher.publish_event(
                run_id=str(run.id),
                event_type=EventType.RUN_TIMEOUT,
                message="Run failed due to timeout.",
                metadata={"task_id": str(task.id)}
            )
            
        self.db.commit()
        return action
"""
with open('services/execution-service/app/controllers/task_controller.py', 'a', encoding='utf-8') as f:
    f.write(content)

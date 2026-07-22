import json
import os
from typing import Any

from .models import JobConfig, TaskRunResult


class StateManager:
    def __init__(self, base_dir: str = "results/jobs"):
        self.base_dir = base_dir

    def _get_job_dir(self, job_id: str) -> str:
        return os.path.join(self.base_dir, job_id)

    def _get_tasks_dir(self, job_id: str) -> str:
        return os.path.join(self._get_job_dir(job_id), "tasks")

    def init_job(self, config: JobConfig, task_ids: list[str]):
        job_dir = self._get_job_dir(config.job_id)
        tasks_dir = self._get_tasks_dir(config.job_id)

        os.makedirs(job_dir, exist_ok=True)
        os.makedirs(tasks_dir, exist_ok=True)

        # Write config
        config_path = os.path.join(job_dir, "config.json")
        with open(config_path, "w") as f:
            f.write(config.model_dump_json(indent=2))

        # Init state if not exists
        state_path = os.path.join(job_dir, "state.json")
        if not os.path.exists(state_path):
            state = {
                "total": len(task_ids),
                "completed": 0,
                "status": "pending",
                "pending_tasks": task_ids,
            }
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)

    def save_task_result(self, job_id: str, result: TaskRunResult):
        tasks_dir = self._get_tasks_dir(job_id)
        path = os.path.join(tasks_dir, f"{result.task_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write(result.model_dump_json(indent=2))

        # Update state
        state_path = os.path.join(self._get_job_dir(job_id), "state.json")
        if os.path.exists(state_path):
            with open(state_path, encoding="utf-8") as f:
                state = json.load(f)

            if result.task_id in state["pending_tasks"]:
                state["pending_tasks"].remove(result.task_id)
                state["completed"] += 1

            if len(state["pending_tasks"]) == 0:
                state["status"] = "completed"

            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)

    def load_pending_tasks(self, job_id: str) -> list[str]:
        state_path = os.path.join(self._get_job_dir(job_id), "state.json")
        if os.path.exists(state_path):
            with open(state_path, encoding="utf-8") as f:
                state = json.load(f)
            return state.get("pending_tasks", [])  # type: ignore
        return []

    def load_all_results(self, job_id: str) -> list[TaskRunResult]:
        tasks_dir = self._get_tasks_dir(job_id)
        results = []
        if os.path.exists(tasks_dir):
            for filename in os.listdir(tasks_dir):
                if filename.endswith(".json"):
                    path = os.path.join(tasks_dir, filename)
                    with open(path, encoding="utf-8") as f:
                        data = json.load(f)
                        results.append(TaskRunResult(**data))
        return results

    def save_profile(self, job_id: str, profile: dict[str, Any]):
        path = os.path.join(self._get_job_dir(job_id), "profile.json")
        with open(path, "w") as f:
            json.dump(profile, f, indent=2)

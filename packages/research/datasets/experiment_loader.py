import os
import json
from typing import List, Dict, Any

class ExperimentLoader:
    def __init__(self, base_dir: str = "results/experiments"):
        self.base_dir = base_dir
        
    def load_summary(self, exp_id: str) -> Dict[str, Any]:
        summary_path = os.path.join(self.base_dir, exp_id, "summary.json")
        if not os.path.exists(summary_path):
            raise FileNotFoundError(f"Summary not found for experiment {exp_id}")
        with open(summary_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_config(self, exp_id: str) -> Dict[str, Any]:
        config_path = os.path.join(self.base_dir, exp_id, "experiment_config.json")
        if not os.path.exists(config_path):
            return {}
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
            
    def load_tasks(self, exp_id: str, state_filter: str = None) -> List[Dict[str, Any]]:
        tasks_dir = os.path.join(self.base_dir, exp_id, "tasks")
        if not os.path.exists(tasks_dir):
            raise FileNotFoundError(f"Tasks directory not found for experiment {exp_id}")
            
        tasks = []
        for filename in os.listdir(tasks_dir):
            if filename.endswith(".json"):
                with open(os.path.join(tasks_dir, filename), "r", encoding="utf-8") as f:
                    task = json.load(f)
                    if state_filter and task.get("evaluation_status") != state_filter:
                        continue
                    tasks.append(task)
        return tasks
        
    def load_failures(self, exp_id: str) -> List[Dict[str, Any]]:
        return self.load_tasks(exp_id, state_filter="FAIL")
        
    def load_successes(self, exp_id: str) -> List[Dict[str, Any]]:
        return self.load_tasks(exp_id, state_filter="PASS")

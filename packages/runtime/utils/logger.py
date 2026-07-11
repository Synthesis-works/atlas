import os
import json
from datetime import datetime
from ..models.execution_result import ExecutionResult

class RuntimeLogger:
    def __init__(self, logs_dir: str = "logs"):
        self.logs_dir = logs_dir
        
    def log_execution(self, task_id: str, model_id: str, result: ExecutionResult) -> str:
        date_str = datetime.now().strftime("%Y-%m-%d")
        day_dir = os.path.join(self.logs_dir, date_str)
        os.makedirs(day_dir, exist_ok=True)
        
        base_path = os.path.join(day_dir, f"{result.execution_id}")
        json_path = f"{base_path}.json"
        txt_path = f"{base_path}.log"
        
        log_data = {
            "execution_id": result.execution_id,
            "task_id": task_id,
            "model": model_id,
            "status": result.status.value,
            "runtime_ms": result.runtime_ms,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.exit_code,
            "exception": result.exception
        }
        
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2)
            
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"Execution ID: {result.execution_id}\n")
            f.write(f"Task ID: {task_id}\n")
            f.write(f"Model: {model_id}\n")
            f.write(f"Status: {result.status.value}\n")
            f.write(f"Runtime: {result.runtime_ms} ms\n")
            f.write(f"Exit Code: {result.exit_code}\n")
            f.write(f"--- Stdout ---\n{result.stdout}\n")
            f.write(f"--- Stderr ---\n{result.stderr}\n")
            if result.exception:
                f.write(f"--- Exception ---\n{result.exception}\n")
                
        return json_path

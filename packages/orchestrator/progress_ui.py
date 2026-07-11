import os
import sys
import time

class ProgressUI:
    def __init__(self, job_id, dataset, model, prompt_version, total_tasks):
        self.job_id = job_id
        self.dataset = dataset
        self.model = model
        self.prompt_version = prompt_version
        self.total_tasks = total_tasks
        self.start_time = time.time()
        self.completed = 0
        self.passed = 0
        self.failed = 0
        self.latencies = []
        self.runtimes = []
        self.repair_attempts = 0
        self.repair_successes = 0
        
    def update(self, result):
        self.completed += 1
        
        if result.status == "PASS":
            self.passed += 1
            if hasattr(result, "repair_retries") and result.repair_retries > 0:
                self.repair_successes += 1
        else:
            self.failed += 1
            
        if hasattr(result, "repair_retries") and result.repair_retries > 0:
            self.repair_attempts += result.repair_retries
            
        if hasattr(result, "generation_latency_ms") and result.generation_latency_ms is not None:
            self.latencies.append(result.generation_latency_ms)
            
        if hasattr(result, "execution_time_ms") and result.execution_time_ms is not None:
            self.runtimes.append(result.execution_time_ms)
            
    def render(self):
        os.system("cls" if os.name == "nt" else "clear")
        
        pass_at_1 = (self.passed / self.completed * 100) if self.completed > 0 else 0
        
        avg_lat_s = (sum(self.latencies) / len(self.latencies) / 1000.0) if self.latencies else 0
        avg_runtime_ms = (sum(self.runtimes) / len(self.runtimes)) if self.runtimes else 0
        
        # ETA calculation
        elapsed = time.time() - self.start_time
        if self.completed > 0:
            time_per_task = elapsed / self.completed
            remaining_tasks = self.total_tasks - self.completed
            eta_seconds = time_per_task * remaining_tasks
            hours, remainder = divmod(eta_seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            eta_str = f"{int(hours)}h {int(minutes)}m"
        else:
            eta_str = "Calculating..."
            
        # Progress bar
        bar_length = 30
        filled_length = int(bar_length * self.completed // self.total_tasks) if self.total_tasks > 0 else bar_length
        bar = "#" * filled_length + "-" * (bar_length - filled_length)
        
        output = f"""=====================================================
Atlas Experiment
=====================================================

Dataset     : {self.dataset}
Model       : {self.model}
Prompt      : {self.prompt_version}
Tasks       : {self.total_tasks}

-----------------------------------------------------

Progress

{bar}

Completed : {self.completed} / {self.total_tasks}
Passed    : {self.passed}
Failed    : {self.failed}

Pass@1    : {pass_at_1:.2f}%

Generation

Avg Latency : {avg_lat_s:.1f} s

Execution

Avg Runtime : {avg_runtime_ms:.0f} ms

Repair

Attempts  : {self.repair_attempts}
Succeeded : {self.repair_successes}

ETA

{eta_str}

Results

results/experiments/{self.job_id}

=====================================================
"""
        sys.stdout.write(output)
        sys.stdout.flush()

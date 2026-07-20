from abc import ABC, abstractmethod
from typing import Dict, Optional

class ConcurrencyPolicy(ABC):
    @abstractmethod
    def can_schedule(self, task, current_running_global: int, current_running_worker: int, current_running_model: int) -> bool:
        """
        Evaluates if a task can be scheduled under this policy.
        """
        pass

class GlobalConcurrencyPolicy(ConcurrencyPolicy):
    def __init__(self, max_running: int):
        self.max_running = max_running
        
    def can_schedule(self, task, current_running_global: int, current_running_worker: int, current_running_model: int) -> bool:
        return current_running_global < self.max_running

class PerWorkerConcurrencyPolicy(ConcurrencyPolicy):
    def __init__(self, max_running: int):
        self.max_running = max_running
        
    def can_schedule(self, task, current_running_global: int, current_running_worker: int, current_running_model: int) -> bool:
        return current_running_worker < self.max_running

class PerModelConcurrencyPolicy(ConcurrencyPolicy):
    def __init__(self, limits: Dict[str, Optional[int]]):
        self.limits = limits
        
    def can_schedule(self, task, current_running_global: int, current_running_worker: int, current_running_model: int) -> bool:
        model = task.run.target_model
        if model not in self.limits:
            return True # No limit configured
        
        limit = self.limits[model]
        if limit is None:
            return True
            
        return current_running_model < limit

class CompositePolicy(ConcurrencyPolicy):
    def __init__(self, policies: list[ConcurrencyPolicy]):
        self.policies = policies
        
    def can_schedule(self, task, current_running_global: int, current_running_worker: int, current_running_model: int) -> bool:
        for policy in self.policies:
            if not policy.can_schedule(task, current_running_global, current_running_worker, current_running_model):
                return False
        return True

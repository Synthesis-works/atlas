from pydantic import BaseModel, UUID4
from typing import Optional, Dict, Any
from datetime import datetime

class RegisterWorkerCommand(BaseModel):
    adapter_id: UUID4
    name: str
    version: str
    hostname: str
    platform: str
    region: Optional[str] = None
    hardware_info: Optional[Dict[str, Any]] = None
    capabilities: Optional[Dict[str, Any]] = None

class HeartbeatWorkerCommand(BaseModel):
    worker_id: UUID4
    current_load: int
    health: str
    active_tasks: int = 0
    queue_length: int = 0
    errors: int = 0
    cpu_usage: Optional[float] = None
    ram_usage: Optional[float] = None
    gpu_usage: Optional[float] = None

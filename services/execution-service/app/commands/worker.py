from typing import Any

from pydantic import UUID4, BaseModel


class RegisterWorkerCommand(BaseModel):
    adapter_id: UUID4
    name: str
    version: str
    hostname: str
    platform: str
    region: str | None = None
    hardware_info: dict[str, Any] | None = None
    capabilities: dict[str, Any] | None = None


class HeartbeatWorkerCommand(BaseModel):
    worker_id: UUID4
    current_load: int
    health: str
    active_tasks: int = 0
    queue_length: int = 0
    errors: int = 0
    cpu_usage: float | None = None
    ram_usage: float | None = None
    gpu_usage: float | None = None

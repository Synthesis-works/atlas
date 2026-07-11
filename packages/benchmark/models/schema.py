from pydantic import BaseModel, Field
from typing import List, Optional

class ExecutionConfig(BaseModel):
    python_version: Optional[str] = None
    required_packages: List[str] = Field(default_factory=list)
    docker_image: Optional[str] = None
    gpu_required: bool = False
    network_access: bool = False
    timeout: Optional[int] = Field(None, description="Timeout in seconds")

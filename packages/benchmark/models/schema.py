from pydantic import BaseModel, Field


class ExecutionConfig(BaseModel):
    python_version: str | None = None
    required_packages: list[str] = Field(default_factory=list)
    docker_image: str | None = None
    gpu_required: bool = False
    network_access: bool = False
    timeout: int | None = Field(None, description="Timeout in seconds")

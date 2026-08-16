from pydantic import BaseModel, Field


class RuntimeConfig(BaseModel):
    default_timeout: int = Field(default=2, description="Default timeout in seconds")
    max_timeout: int = Field(default=10, description="Maximum allowed timeout")
    default_memory_limit: int = Field(default=256, description="Default memory limit in MB")
    sandbox_dir: str = Field(
        default=".sandbox", description="Base directory for temporary sandboxes"
    )

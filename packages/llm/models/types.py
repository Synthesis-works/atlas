from pydantic import BaseModel


class ModelInfo(BaseModel):
    name: str
    size: int
    family: str
    parameter_size: str
    quantization: str

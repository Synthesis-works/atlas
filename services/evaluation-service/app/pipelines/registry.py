from typing import Dict, Type
from .base import EvaluationPipeline

class PipelineRegistry:
    _pipelines: Dict[str, Type[EvaluationPipeline]] = {}

    @classmethod
    def register(cls, name: str, pipeline_cls: Type[EvaluationPipeline]) -> None:
        cls._pipelines[name] = pipeline_cls

    @classmethod
    def get(cls, name: str) -> Type[EvaluationPipeline]:
        if name not in cls._pipelines:
            raise ValueError(f"Pipeline '{name}' not found in registry.")
        return cls._pipelines[name]

    @classmethod
    def clear(cls) -> None:
        cls._pipelines.clear()

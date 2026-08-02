from .base import EvaluationPipeline


class PipelineRegistry:
    _pipelines: dict[str, type[EvaluationPipeline]] = {}

    @classmethod
    def register(cls, name: str, pipeline_cls: type[EvaluationPipeline]) -> None:
        cls._pipelines[name] = pipeline_cls

    @classmethod
    def get(cls, name: str) -> type[EvaluationPipeline]:
        if name not in cls._pipelines:
            raise ValueError(f"Pipeline '{name}' not found in registry.")
        return cls._pipelines[name]

    @classmethod
    def clear(cls) -> None:
        cls._pipelines.clear()

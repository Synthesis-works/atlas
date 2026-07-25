import abc
import uuid
from typing import Any


class RawMeasurements:
    """
    Encapsulates raw facts extracted during evaluation.
    """

    def __init__(self, raw_data: dict[str, Any], artifacts: dict[str, str] | None = None):
        self.raw_data = raw_data
        self.artifacts = artifacts or {}  # mapping of artifact name to local filepath/uri


class EvaluatorContext:
    def __init__(
        self,
        execution_id: uuid.UUID,
        benchmark_version: str,
        dataset_version: str,
        environment: str,
        seed: int | None = None,
    ):
        self.execution_id = execution_id
        self.benchmark_version = benchmark_version
        self.dataset_version = dataset_version
        self.environment = environment
        self.seed = seed


class BaseEvaluator(abc.ABC):
    """
    Base Evaluator Plugin interface.
    Extracts raw facts from execution outputs.
    """

    @abc.abstractmethod
    def prepare(self, context: EvaluatorContext) -> None:
        """
        Setup phase. Download datasets, launch Docker, init remote APIs, etc.
        """
        pass

    @abc.abstractmethod
    def evaluate(self, execution_output: dict[str, Any]) -> RawMeasurements:
        """
        Extract facts and measurements from execution output.
        """
        pass

    @abc.abstractmethod
    def postprocess(self, measurements: RawMeasurements) -> None:
        """
        Post-processing phase, e.g. packaging artifacts, uploading logs.
        """
        pass

    @abc.abstractmethod
    def cleanup(self) -> None:
        """
        Teardown phase. Kill Docker containers, remove temp files, etc.
        """
        pass

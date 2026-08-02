from ..interfaces.importer import BaseImporter
from ..models import (
    Benchmark,
    BenchmarkCategory,
    BenchmarkMetadata,
    Difficulty,
    ExecutionConfig,
    LicenseType,
    Task,
)


class DummyBenchmarkImporter(BaseImporter):
    """An importer for a custom dummy benchmark to validate architecture."""

    def import_data(self, source: str, **kwargs) -> Benchmark:
        metadata = BenchmarkMetadata(  # type: ignore
            benchmark_id="dummy-bench-001",
            name="Dummy Architecture Benchmark",
            description="A minimal benchmark to validate the Atlas Benchmark Foundation architecture.",
            author="Atlas Core Team",
            version="1.0.0",
            license=LicenseType.MIT,
            difficulty=Difficulty.EASY,
            category=BenchmarkCategory.CODING,
        )

        task1 = Task(  # type: ignore
            task_id="task-1",
            title="Addition",
            description="Add two numbers",
            input={"a": 1, "b": 2},
            expected_output=3,
        )

        task2 = Task(  # type: ignore
            task_id="task-2",
            title="String Reversal",
            description="Reverse a string",
            input="hello",
            expected_output="olleh",
        )

        task3 = Task(  # type: ignore
            task_id="task-3",
            title="List Sorting",
            description="Sort a list of integers",
            input=[3, 1, 2],
            expected_output=[1, 2, 3],
        )

        return Benchmark(
            metadata=metadata, config=ExecutionConfig(timeout=30), tasks=[task1, task2, task3]
        )

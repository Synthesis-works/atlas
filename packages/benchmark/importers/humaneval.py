from ..interfaces.importer import BaseImporter
from ..models import (
    Benchmark, 
    BenchmarkMetadata, 
    Task, 
    ExecutionConfig, 
    BenchmarkCategory, 
    Difficulty, 
    LicenseType
)
from ..exceptions import ImporterError
import json
import os

class HumanEvalImporter(BaseImporter):
    """Imports the HumanEval dataset into the Atlas Benchmark format."""
    
    def import_data(self, source: str, **kwargs) -> Benchmark:
        """
        source: path to humaneval.jsonl
        """
        if not os.path.exists(source):
            raise ImporterError(f"HumanEval source file not found: {source}")
            
        tasks = []
        try:
            with open(source, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    item = json.loads(line)
                    task = Task(
                        task_id=item.get("task_id", ""),
                        title=f"HumanEval {item.get('task_id', '')}",
                        description=item.get("prompt", ""),
                        input=item.get("prompt", ""),
                        expected_output=item.get("canonical_solution", ""),
                        hidden_tests=item.get("test", "")
                    )
                    tasks.append(task)
        except Exception as e:
            raise ImporterError(f"Failed to parse HumanEval dataset: {e}")
            
        metadata = BenchmarkMetadata(
            benchmark_id="humaneval-001",
            name="HumanEval",
            description="OpenAI HumanEval dataset for code generation.",
            author="OpenAI",
            version="1.0.0",
            license=LicenseType.MIT,
            difficulty=Difficulty.HIGH,
            category=BenchmarkCategory.CODING
        )
        
        return Benchmark(
            metadata=metadata,
            config=ExecutionConfig(timeout=10, required_packages=["pytest"]),
            tasks=tasks
        )

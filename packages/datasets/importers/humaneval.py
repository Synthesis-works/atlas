import gzip
import json
import httpx
import tempfile
import os
from typing import Any, List
from .base import BaseImporter
from ..mapper import BaseMapper
from ..models import DatasetManifest
from packages.benchmark.models.task import Task, EvaluationConfig

class HumanEvalMapper(BaseMapper):
    def map(self, raw_record: Any) -> Task:
        return Task(
            task_id=raw_record["task_id"].replace("/", "-").lower(),
            title=f"HumanEval {raw_record['task_id']}",
            description=f"Complete the Python function `{raw_record['entry_point']}`.",
            input=raw_record["prompt"],
            expected_output=raw_record["canonical_solution"],
            hidden_tests=raw_record["test"],
            evaluation=EvaluationConfig(
                extractor="code_block",
                normalizer="noop",
                judge="exact_match",
                metrics=["accuracy"]
            ),
            metadata={"entry_point": raw_record["entry_point"]}
        )

class HumanEvalImporter(BaseImporter):
    DATASET_URL = "https://github.com/openai/human-eval/raw/master/data/HumanEval.jsonl.gz"
    
    def __init__(self):
        super().__init__(mapper=HumanEvalMapper())
        
    def get_manifest(self) -> DatasetManifest:
        return DatasetManifest(
            id="humaneval",
            name="HumanEval",
            version="1.0",
            source="OpenAI",
            license="MIT",
            citation="Evaluating Large Language Models Trained on Code (Chen et al. 2021)",
            language="python",
            evaluation="execution",
            metric="pass@1",
            tasks=164,
            tags=["coding", "python", "generation"]
        )
        
    def fetch_dataset(self) -> List[Any]:
        with httpx.Client(follow_redirects=True) as client:
            response = client.get(self.DATASET_URL)
            response.raise_for_status()
            
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(response.content)
                tmp_path = tmp.name
                
        records = []
        try:
            with gzip.open(tmp_path, 'rt', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        records.append(json.loads(line))
        finally:
            os.remove(tmp_path)
            
        return records

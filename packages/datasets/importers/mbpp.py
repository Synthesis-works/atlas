import json
import httpx
from typing import Any, List
from .base import BaseImporter
from ..mapper import BaseMapper
from ..models import DatasetManifest
from packages.benchmark.models.task import Task, EvaluationConfig

class MBPPMapper(BaseMapper):
    def map(self, raw_record: Any) -> Task:
        return Task(
            task_id=f"mbpp-{raw_record['task_id']}",
            title=f"MBPP {raw_record['task_id']}",
            description=raw_record["text"],
            input=raw_record["text"],
            expected_output=raw_record["code"],
            hidden_tests=raw_record.get("test_list", []),
            evaluation=EvaluationConfig(
                extractor="code_block",
                normalizer="noop",
                judge="exact_match",
                metrics=["accuracy"]
            ),
            metadata={"test_setup_code": raw_record.get("test_setup_code", "")}
        )

class MBPPImporter(BaseImporter):
    DATASET_URL = "https://raw.githubusercontent.com/google-research/google-research/master/mbpp/mbpp.jsonl"
    
    def __init__(self):
        super().__init__(mapper=MBPPMapper())
        
    def get_manifest(self) -> DatasetManifest:
        return DatasetManifest(
            id="mbpp",
            name="Mostly Basic Python Problems",
            version="1.0",
            source="Google Research",
            license="CC-BY-4.0",
            citation="Program Synthesis with Large Language Models (Austin et al. 2021)",
            language="python",
            evaluation="execution",
            metric="pass@1",
            tasks=974,
            tags=["coding", "python", "generation", "basic"]
        )
        
    def fetch_dataset(self) -> List[Any]:
        with httpx.Client(follow_redirects=True) as client:
            response = client.get(self.DATASET_URL)
            response.raise_for_status()
            
        records = []
        for line in response.text.splitlines():
            if line.strip():
                records.append(json.loads(line))
        return records
